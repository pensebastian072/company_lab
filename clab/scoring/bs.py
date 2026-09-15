"""BS - Balance Sheet & Survivability /10.

Allocation (rubric A5, unspecified by the framework): leverage 2, coverage 2,
current ratio 1, cash vs opex 1, dilution 1, maturity wall 1, stress test 2.

Leverage thresholds are multiplied by the sector profile's leverage_multiplier,
because a REIT or a regulated utility carrying 4x net debt/EBITDA is structurally
levered rather than distressed.
"""
from __future__ import annotations

from . import rubric, stress
from .context import SymbolContext, num, pct, subtest
from .types import ComponentScore

CODE = "BS"


def score(ctx: SymbolContext) -> ComponentScore:
    M = ctx.metrics
    mult = ctx.profile.leverage_multiplier
    sts = []

    # ------------------------------------------------------------ leverage /2
    nde = M.raw("net_debt_ebitda")
    bands = tuple(b * mult for b in rubric.BS_NET_DEBT_EBITDA_BANDS)
    pts = rubric.band_from_thresholds_asc(nde, bands, (2, 2, 1, 0))
    sts.append(subtest(
        ctx, "bs_net_debt_ebitda", "Net debt / EBITDA", 2, value=nde, points=pts,
        inputs={"net_debt": M.raw("net_debt"), "ebitda_ttm": M.raw("ebitda_ttm"),
                "net_debt_ebitda": nde,
                "debt_ebitda_incl_leases": M.raw("debt_ebitda_incl_leases"),
                "leverage_multiplier": mult},
        prov_keys=("net_debt", "total_debt", "ebitda_ttm"),
        note=f"net debt/EBITDA {num(nde)} vs bands {tuple(round(b, 2) for b in bands)}",
    ))

    # ------------------------------------------------------------ coverage /2
    cov = M.raw("interest_coverage")
    pts = rubric.band_from_thresholds(cov, rubric.BS_COVERAGE_BANDS, (2, 2, 1, 0))
    sts.append(subtest(
        ctx, "bs_interest_coverage", "Interest coverage", 2, value=cov, points=pts,
        inputs={"interest_coverage": cov,
                "capped": M.raw("interest_coverage_uncapped"),
                "operating_income_ttm": M.raw("operating_income_ttm"),
                "interest_expense_ttm": M.raw("interest_expense_ttm")},
        prov_keys=("interest_coverage",),
        note=(f"coverage {num(cov)} vs bands {rubric.BS_COVERAGE_BANDS}"
              + (" (capped: effectively debt-free)" if M.raw("interest_coverage_uncapped") else "")),
        na_reason=("interest expense is a cost of revenue for this filer type, "
                   "not a solvency burden"),
    ))

    # ------------------------------------------------------------ current ratio /1
    cr = M.raw("current_ratio")
    pts = rubric.band_from_thresholds(cr, rubric.BS_CURRENT_RATIO_BANDS, (1, 1, 0))
    sts.append(subtest(
        ctx, "bs_current_ratio", "Current ratio", 1, value=cr, points=pts,
        inputs={"current_ratio": cr, "assets_current": M.raw("assets_current"),
                "liabilities_current": M.raw("liabilities_current")},
        prov_keys=("assets_current", "liabilities_current"),
        note=f"current ratio {num(cr)} vs bands {rubric.BS_CURRENT_RATIO_BANDS}",
        na_reason="this filer does not present a classified balance sheet",
    ))

    # ------------------------------------------------------------ cash vs opex /1
    cash = M.raw("cash_sti")
    opex = M.raw("operating_expenses_ttm")
    if opex is None:
        rev, opm = M.raw("revenue_ttm"), M.raw("operating_margin")
        opex = rev * (1.0 - opm) if (rev is not None and opm is not None) else None
    years = (cash / opex) if (cash is not None and opex not in (None, 0) and opex > 0) else None
    pts = rubric.band_from_thresholds(years, rubric.BS_CASH_RUNWAY_YEARS_BANDS, (1, 1, 0))
    sts.append(subtest(
        ctx, "bs_cash_vs_opex", "Cash position vs annual operating expense", 1,
        value=years, points=pts,
        inputs={"cash_sti": cash, "operating_expenses_ttm": opex, "years_of_opex": years},
        prov_keys=("cash_sti",),
        note=f"cash covers {num(years)} years of operating expense",
    ))

    # ------------------------------------------------------------ dilution /1
    dil = M.raw("dilution_yoy")
    pts = rubric.band_from_thresholds_asc(dil, rubric.BS_DILUTION_BANDS, (1, 1, 0, 0))
    sts.append(subtest(
        ctx, "bs_dilution", "Share dilution", 1, value=dil, points=pts,
        inputs={"dilution_yoy": dil,
                "diluted_shares_ttm": M.raw("diluted_shares_ttm"),
                "diluted_shares_ttm_prior": M.raw("diluted_shares_ttm_prior"),
                "buybacks_ttm": M.raw("buybacks_ttm"),
                "sbc_pct_revenue": M.raw("sbc_pct_revenue")},
        prov_keys=("dilution_yoy",),
        note=f"diluted share count {pct(dil)} YoY vs bands {rubric.BS_DILUTION_BANDS}",
    ))

    # ------------------------------------------------------------ maturity wall /1
    sts.append(_maturity_wall(ctx))

    # ------------------------------------------------------------ stress test /2
    sim = stress.simulate(M)
    sts.append(subtest(
        ctx, "bs_stress_test", "Downturn survival test", 2,
        value=None if sim["verdict"] == stress.NO_DATA else sim["verdict"],
        points=sim["points"], inputs=sim,
        prov_keys=("revenue_ttm", "operating_income_ttm", "capex_ttm"),
        note=(f"revenue -{rubric.STRESS_REVENUE_HAIRCUT:.0%}, margins "
              f"-{rubric.STRESS_MARGIN_HAIRCUT:.0%} relative, financing "
              f"+{rubric.STRESS_INTEREST_UPLIFT:.0%} -> {sim['verdict']}"),
        na_reason="the stress model's operating-margin basis is not defined for this filer",
    ))

    comp = ComponentScore(
        code=CODE, label=rubric.COMPONENTS[CODE][0],
        max_points=rubric.COMPONENTS[CODE][1], subtests=sts,
        note=("Leverage 2 / coverage 2 / current ratio 1 / cash-vs-opex 1 / "
              "dilution 1 / maturity wall 1 / stress test 2."),
    )
    comp.check_points()
    return comp


def _maturity_wall(ctx: SymbolContext):
    """Near-term maturities. The precise tag is sparsely filed (rubric A7), so a
    documented proxy stands in rather than silently awarding the point."""
    M = ctx.metrics
    cash = M.raw("cash_sti") or 0.0
    fcf = M.raw("fcf_ttm") or 0.0
    capacity = cash + max(fcf, 0.0)

    due = M.raw("maturity_1y")
    source = "LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths"
    if due is None:
        due = M.raw("debt_long_current")
        source = "LongTermDebtCurrent (proxy - the precise maturity tag is not filed)"
    if due is None or capacity <= 0:
        return subtest(ctx, "bs_maturity_wall", "Near-term debt maturities", 1,
                       value=None, points=None,
                       inputs={"due_within_1y": due, "cash_sti": M.raw("cash_sti"),
                               "fcf_ttm": M.raw("fcf_ttm"), "source": source},
                       na_reason="no near-term maturity disclosure and no proxy available")

    ratio = due / capacity
    pts = rubric.band_from_thresholds_asc(ratio, rubric.BS_MATURITY_PROXY_BANDS, (1, 1, 0))
    return subtest(
        ctx, "bs_maturity_wall", "Near-term debt maturities", 1,
        value=ratio, points=pts,
        inputs={"due_within_1y": due, "cash_sti": M.raw("cash_sti"),
                "fcf_ttm": M.raw("fcf_ttm"), "coverage_capacity": capacity,
                "due_over_capacity": ratio, "source": source},
        prov_keys=("maturity_1y", "debt_long_current", "cash_sti"),
        note=f"{pct(ratio)} of (cash + TTM FCF) is due within a year; source: {source}",
    )
