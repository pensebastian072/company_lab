"""FE - Financial Engine /15. Fully quantitative.

Allocation (rubric A4, not specified by the framework): 6 growth / 6 quality /
3 margin expansion. The framework's stated key test - "are margins expanding as
revenue grows" - deliberately gets a fifth of the component rather than being
buried inside "quality", and its top score is gated on FCF conversion, because
margin expansion on paper with no cash behind it has not been earned.
"""
from __future__ import annotations

from . import rubric
from .context import SymbolContext, num, pct, subtest
from .types import ComponentScore

CODE = "FE"


def _growth_points(cagr_3y, cagr_1y, cagr_5y, max_points: int):
    """Band the 3Y CAGR, with 1Y and 5Y as corroboration."""
    if cagr_3y is None:
        base = cagr_1y if cagr_1y is not None else cagr_5y
        if base is None:
            return None, ""
        cagr_3y = base
    b = rubric.FE_REVENUE_CAGR_BANDS      # (0.20, 0.12, 0.06, 0.02)
    # Point ladders per sub-test maximum. The 3-point ladder arrived with the v2
    # reweighting, which moved 3 points from Entry into revenue growth, FCF growth
    # and the margin-expansion key test.
    ladders = {
        3: (3, 2, 2, 1, 0),
        2: (2, 2, 1, 1, 0),
        1: (1, 1, 1, 0, 0),
    }
    pts = ladders.get(max_points, ladders[1])
    val = rubric.band_from_thresholds(cagr_3y, b, pts)
    return val, f"3Y CAGR {pct(cagr_3y)} vs bands {b} -> {val}/{max_points}"


def _margin_points(ctx: SymbolContext, key: str, metric: str, value,
                   mx: int, bands: tuple):
    """(points, note, basis) - sector-relative where possible, absolute otherwise.

    F1, from E03 R1. Scoring a 25% operating margin as full marks is a software
    threshold: it made the framework a sector bet, with mean scores running from
    Financials 62.6% to Utilities 41.2%. A percentile within the company's own sector
    asks "is this a good utility" instead.
    """
    if value is None:
        return None, "", "none"
    peers = ctx.peers or {}
    pctile = peers.get(f"{metric}_sector_pctile")
    n_peers = int(peers.get(f"{metric}_sector_n") or 0)
    if (rubric.SECTOR_RELATIVE_ENABLED and key in rubric.SECTOR_RELATIVE_METRICS
            and pctile is not None and n_peers >= rubric.SECTOR_RELATIVE_MIN_PEERS):
        ladder = {2: (2, 2, 1, 0), 1: (1, 1, 0, 0)}.get(mx, (1, 1, 0, 0))
        pts = rubric.band_from_thresholds(pctile, rubric.SECTOR_PCTILE_BANDS, ladder)
        return (pts,
                f"{pct(value)} is the {pctile:.0%} percentile of {n_peers} peers in "
                f"{ctx.sector or 'its sector'}",
                "sector_relative")
    # The ladder length must follow the band count. ROIC has FOUR thresholds while this
    # hardcoded a four-entry ladder, so every company with ROIC below the lowest band
    # raised IndexError and lost the whole 18-point component to NO_DATA.
    pts = rubric.band_from_thresholds(value, bands, rubric.ladder_for(bands, mx))
    reason = ("too few sector peers" if rubric.SECTOR_RELATIVE_ENABLED
              and key in rubric.SECTOR_RELATIVE_METRICS else "absolute by design")
    return pts, f"{pct(value)} vs absolute bands {bands} ({reason})", "absolute"


def score(ctx: SymbolContext) -> ComponentScore:
    M = ctx.metrics
    sts = []

    # ------------------------------------------------------------ growth /6
    growth_alloc = {k: m for k, _l, m in rubric.FE_SUBTESTS}
    for key, label, metric in (
        ("fe_revenue_growth", "Revenue CAGR 1Y / 3Y / 5Y", "revenue"),
        ("fe_eps_growth", "EPS growth", "eps"),
        ("fe_fcf_growth", "FCF growth", "fcf"),
        ("fe_operating_income_growth", "Operating income growth", "operating_income"),
    ):
        mx = growth_alloc[key.removeprefix("fe_")]
        c3 = M.raw(f"{metric}_cagr_3y")
        c1 = M.raw(f"{metric}_cagr_1y")
        c5 = M.raw(f"{metric}_cagr_5y")
        pts, note = _growth_points(c3, c1, c5, mx)
        sts.append(subtest(
            ctx, key, label, mx, value=c3 if c3 is not None else (c1 or c5), points=pts,
            inputs={f"{metric}_cagr_1y": c1, f"{metric}_cagr_3y": c3,
                    f"{metric}_cagr_5y": c5},
            prov_keys=(f"{metric}_ttm",) if metric != "fcf" else ("cfo_ttm", "capex_ttm"),
            note=note,
        ))

    # ------------------------------------------------------------ quality /6
    for key, label, mx, metric, bands in (
        ("fe_gross_margin", "Gross margin", 1, "gross_margin", rubric.FE_GROSS_MARGIN_BANDS),
        ("fe_operating_margin", "Operating margin", 1, "operating_margin",
         rubric.FE_OPERATING_MARGIN_BANDS),
        ("fe_fcf_margin", "FCF margin", 1, "fcf_margin", rubric.FE_FCF_MARGIN_BANDS),
    ):
        v = M.raw(metric)
        pts, note, basis = _margin_points(ctx, key, metric, v, mx, bands)
        sts.append(subtest(
            ctx, key, label, mx, value=v, points=pts,
            inputs={metric: v, "scoring_basis": basis,
                    "sector_pctile": (ctx.peers or {}).get(f"{metric}_sector_pctile"),
                    "sector_peers": (ctx.peers or {}).get(f"{metric}_sector_n")},
            prov_keys=("revenue_ttm", "gross_profit_ttm", "operating_income_ttm"),
            note=note,
            na_reason=("this filer's income statement has no gross-profit line"
                       if metric == "gross_margin" and not M.raw("has_gross_profit_line")
                       else ""),
        ))

    roic = M.raw("roic")
    roic_pts, roic_note, roic_basis = _margin_points(
        ctx, "fe_roic", "roic", roic, 2, rubric.FE_ROIC_BANDS)
    sts.append(subtest(
        ctx, "fe_roic", "ROIC", 2, value=roic, points=roic_pts,
        inputs={"roic": roic, "nopat_ttm": M.raw("nopat_ttm"),
                "invested_capital": M.raw("invested_capital"),
                "effective_tax_rate": M.raw("effective_tax_rate"),
                "scoring_basis": roic_basis,
                "sector_pctile": (ctx.peers or {}).get("roic_sector_pctile")},
        prov_keys=("roic", "nopat_ttm", "invested_capital"),
        note=roic_note,
    ))

    roe = M.raw("roe")
    roe_pts, roe_note, roe_basis = _margin_points(
        ctx, "fe_roe", "roe", roe, 1, rubric.FE_ROE_BANDS)
    sts.append(subtest(
        ctx, "fe_roe", "ROE", 1, value=roe, points=roe_pts,
        inputs={"roe": roe, "scoring_basis": roe_basis,
                "sector_pctile": (ctx.peers or {}).get("roe_sector_pctile")},
        prov_keys=("roe",), note=roe_note,
    ))

    # ------------------------------------------------- margin expansion /3 (key test)
    sts.append(_margin_expansion(ctx))

    comp = ComponentScore(
        code=CODE, label=rubric.COMPONENTS[CODE][0],
        max_points=rubric.COMPONENTS[CODE][1], subtests=sts,
        note=("Growth 6 / quality 6 / margin-expansion 3. The margin-expansion "
              "sub-test is the framework's stated key test and its top score is "
              "gated on FCF conversion."),
    )
    comp.check_points()
    return comp


def _margin_expansion(ctx: SymbolContext):
    """The key test: are margins expanding while revenue grows, with cash behind it?"""
    M = ctx.metrics
    slope = M.raw("margin_trend_bps_yr")
    rev_growth = M.raw("revenue_cagr_1y")
    if rev_growth is None:
        rev_growth = M.raw("revenue_yoy")
    conv = M.raw("fcf_conversion")
    n_q = M.raw("margin_trend_quarters")

    inputs = {
        "margin_trend_bps_yr": slope,
        "margin_quarters": n_q,
        "revenue_growth": rev_growth,
        "fcf_conversion": conv,
        "margin_first_last": M.raw("margin_first_last"),
    }
    mx = {k: m for k, _l, m in rubric.FE_SUBTESTS}["margin_expansion"]
    if slope is None or rev_growth is None:
        # maximum read from the rubric here too: hardcoding 3 on this path survived the
        # reweighting and made FE's sub-tests sum to 17 instead of 18
        return subtest(ctx, "fe_margin_expansion",
                       "Margins expanding as revenue grows (key test)", mx,
                       value=None, points=None, inputs=inputs,
                       na_reason="needs 4+ quarters of operating margin and a revenue growth rate")

    growing = rev_growth > 0
    if slope >= rubric.FE_MARGIN_SLOPE_STRONG_BPS and growing:
        pts, why = mx, f"margin +{slope:.0f}bps/yr with revenue growing {pct(rev_growth)}"
    elif slope >= 0 and growing:
        pts, why = mx - 2, f"margin flat-to-up ({slope:+.0f}bps/yr) with revenue growing"
    elif slope >= rubric.FE_MARGIN_SLOPE_FLAT_BPS:
        pts, why = 1, f"margin mildly compressing ({slope:+.0f}bps/yr)"
    else:
        pts, why = 0, f"margin compressing {slope:+.0f}bps/yr"
    pts = max(0, min(pts, mx))

    # cash gate: paper margin expansion without cash behind it does not earn full marks
    if pts == mx and conv is not None and conv < rubric.FE_FCF_CONVERSION_GATE:
        pts = mx - 1
        why += (f"; capped at {pts} because FCF conversion is {num(conv)} "
                f"(<{rubric.FE_FCF_CONVERSION_GATE})")

    return subtest(
        ctx, "fe_margin_expansion", "Margins expanding as revenue grows (key test)", mx,
        value=slope, points=pts, inputs=inputs,
        prov_keys=("margin_trend_bps_yr",), note=why,
    )
