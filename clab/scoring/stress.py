"""The downturn survival test.

The framework's question is "what could permanently destroy this investment?",
modelled as revenue -20%, margins -25%, financing costs up. Every intermediate is
returned so the scorecard shows the whole simulated P&L rather than a verdict word.

"Margins -25%" is read as RELATIVE (a 40% margin becomes 30%), not 25 percentage
points - rubric A6. Absolute drives most of the index to negative operating
income, so every company scores 0 and the sub-test carries no information.
"""
from __future__ import annotations

from . import rubric

SURVIVES_COMFORTABLY = "SURVIVES_COMFORTABLY"
SURVIVES = "SURVIVES"
STRESSED = "STRESSED"
NO_DATA = "NO_DATA"


def simulate(m) -> dict:
    """Run the stress scenario. Returns every intermediate plus a verdict.

    `m` is a MetricBundle. Any missing input yields verdict NO_DATA - never a
    STRESSED verdict on absent data, which would read as a real finding.
    """
    rev = m.raw("revenue_ttm")
    opm = m.raw("operating_margin")
    da = m.raw("dep_amort_ttm")
    capex = m.raw("capex_ttm")
    interest = m.raw("interest_expense_ttm")
    tax = m.raw("effective_tax_rate") or rubric.EFFECTIVE_TAX_DEFAULT
    cash = m.raw("cash_sti")
    net_debt = m.raw("net_debt")

    out: dict = {
        "inputs": {
            "revenue_ttm": rev, "operating_margin": opm, "dep_amort_ttm": da,
            "capex_ttm": capex, "interest_expense_ttm": interest,
            "effective_tax_rate": tax, "cash_sti": cash, "net_debt": net_debt,
        },
        "assumptions": {
            "revenue_haircut": rubric.STRESS_REVENUE_HAIRCUT,
            "margin_haircut_relative": rubric.STRESS_MARGIN_HAIRCUT,
            "interest_uplift": rubric.STRESS_INTEREST_UPLIFT,
            "capex_cut": rubric.STRESS_CAPEX_CUT,
        },
        "verdict": NO_DATA,
        "points": None,
    }

    missing = [k for k, v in (("operating_margin", opm), ("revenue_ttm", rev),
                              ("dep_amort_ttm", da), ("capex_ttm", capex)) if v is None]
    if missing:
        out["missing"] = missing
        out["reason"] = f"missing {', '.join(missing)}"
        return out

    interest = 0.0 if interest is None else abs(interest)
    cash = 0.0 if cash is None else cash

    rev_s = rev * (1.0 - rubric.STRESS_REVENUE_HAIRCUT)
    opm_s = opm * (1.0 - rubric.STRESS_MARGIN_HAIRCUT)
    opinc_s = rev_s * opm_s
    int_s = interest * (1.0 + rubric.STRESS_INTEREST_UPLIFT)
    ebitda_s = opinc_s + da                       # D&A is sunk, held flat
    capex_s = capex * (1.0 - rubric.STRESS_CAPEX_CUT)
    fcf_s = opinc_s * (1.0 - tax) + da - capex_s - int_s

    coverage_s = (opinc_s / int_s) if int_s > 0 else rubric.STRESS_COMFORT["coverage"] * 2
    leverage_s = (net_debt / ebitda_s) if (net_debt is not None and ebitda_s > 0) else None
    runway = float("inf") if fcf_s > 0 else (cash / max(1.0, -fcf_s))

    out["simulated"] = {
        "revenue": rev_s, "operating_margin": opm_s, "operating_income": opinc_s,
        "interest_expense": int_s, "ebitda": ebitda_s, "capex": capex_s,
        "fcf": fcf_s, "interest_coverage": coverage_s, "net_debt_ebitda": leverage_s,
        "cash_runway_years": (None if runway == float("inf") else round(runway, 2)),
        "cash_runway_infinite": runway == float("inf"),
    }

    comfort = rubric.STRESS_COMFORT
    surv = rubric.STRESS_SURVIVE
    lev_ok_comfort = leverage_s is None or leverage_s <= comfort["leverage"]
    lev_ok_surv = leverage_s is None or leverage_s <= surv["leverage"]

    if coverage_s >= comfort["coverage"] and lev_ok_comfort and fcf_s > 0:
        out["verdict"], out["points"] = SURVIVES_COMFORTABLY, 2
    elif coverage_s >= surv["coverage"] and lev_ok_surv and runway >= surv["runway_years"]:
        out["verdict"], out["points"] = SURVIVES, 1
    else:
        # a real, measured zero - not missing data
        out["verdict"], out["points"] = STRESSED, 0
    return out
