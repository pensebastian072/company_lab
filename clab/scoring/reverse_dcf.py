"""Reverse DCF: what growth does today's price require?

Rather than pretending to know what a company is worth, this inverts the
question. Solve for the FCF growth rate g that makes a 10-year DCF equal the
current enterprise value, then judge whether that required growth is reasonable
against what the company already achieves and what analysts expect.

Every assumption is stamped `assumed` in provenance and the caller is handed a
wacc +/-2% sensitivity strip, because a single reverse-DCF number carries far
more apparent authority than it deserves.
"""
from __future__ import annotations

from . import rubric


def wacc_for(beta: float | None, risk_free: float | None) -> tuple[float, dict]:
    """CAPM cost of capital, clamped. Debt cost is deliberately not modelled -
    for the large-cap universe the equity cost dominates and a fabricated debt
    schedule would add false precision, not accuracy."""
    b = rubric.DCF_DEFAULT_BETA if beta is None else float(beta)
    rf = rubric.DCF_DEFAULT_RISK_FREE if risk_free is None else float(risk_free)
    raw = rf + b * rubric.DCF_EQUITY_RISK_PREMIUM
    w = min(max(raw, rubric.DCF_WACC_FLOOR), rubric.DCF_WACC_CEIL)
    return w, {
        "beta": b, "risk_free": rf, "equity_risk_premium": rubric.DCF_EQUITY_RISK_PREMIUM,
        "wacc_raw": raw, "wacc": w, "clamped": w != raw,
        "beta_assumed": beta is None, "risk_free_assumed": risk_free is None,
        "assumed": True,
    }


def _growth_path(g: float, years: int) -> list[float]:
    """g held to the fade start, then faded linearly to terminal growth."""
    gt = rubric.DCF_TERMINAL_GROWTH
    fade_start = rubric.DCF_FADE_START_YEAR
    path = []
    for t in range(1, years + 1):
        if t < fade_start:
            path.append(g)
        else:
            frac = (t - fade_start + 1) / (years - fade_start + 1)
            path.append(g + (gt - g) * frac)
    return path


def enterprise_value(fcf0: float, g: float, wacc: float, years: int | None = None) -> float:
    years = years or rubric.DCF_YEARS
    gt = rubric.DCF_TERMINAL_GROWTH
    fcf = fcf0
    pv = 0.0
    for t, gt_t in enumerate(_growth_path(g, years), start=1):
        fcf = fcf * (1.0 + gt_t)
        pv += fcf / ((1.0 + wacc) ** t)
    if wacc <= gt:
        return float("inf")
    terminal = fcf * (1.0 + gt) / (wacc - gt)
    return pv + terminal / ((1.0 + wacc) ** years)


def implied_growth(ev: float, fcf0: float, wacc: float,
                   bounds: tuple = rubric.DCF_SOLVE_BOUNDS,
                   tol: float = 1e-6, max_iter: int = 200) -> float | None:
    """Bisect for g such that DCF(g) == EV. None when EV lies outside the bracket."""
    if fcf0 is None or fcf0 <= 0 or ev is None or ev <= 0 or wacc <= rubric.DCF_TERMINAL_GROWTH:
        return None
    lo, hi = bounds
    f_lo = enterprise_value(fcf0, lo, wacc) - ev
    f_hi = enterprise_value(fcf0, hi, wacc) - ev
    if f_lo > 0:
        return lo        # even the floor growth overvalues it: cheaper than the bracket
    if f_hi < 0:
        return hi        # even the ceiling cannot justify the price
    for _ in range(max_iter):
        mid = (lo + hi) / 2.0
        f_mid = enterprise_value(fcf0, mid, wacc) - ev
        if abs(f_mid) < tol * max(ev, 1.0):
            return mid
        if f_mid < 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def analyse(ctx) -> dict:
    """Full reverse-DCF block for one company. Never raises."""
    M = ctx.metrics
    fcf0 = M.raw("fcf_ttm")
    ev = ctx.mk("ev")
    if ev is None:
        mc, nd = ctx.mk("market_cap"), M.raw("net_debt")
        ev = (mc + nd) if (mc is not None and nd is not None) else mc
    wacc, wacc_prov = wacc_for(ctx.mk("beta"), ctx.mk("risk_free"))

    out: dict = {
        "fcf_ttm": fcf0, "enterprise_value": ev, "wacc": wacc,
        "wacc_inputs": wacc_prov, "years": rubric.DCF_YEARS,
        "terminal_growth": rubric.DCF_TERMINAL_GROWTH,
        "implied_growth": None, "sensitivity": {}, "points": None,
    }
    if fcf0 is None or fcf0 <= 0:
        out["reason"] = ("TTM FCF is zero or negative - a reverse DCF on a pre-FCF "
                         "company would be meaningless, so this is NO_DATA rather "
                         "than cheap or expensive")
        return out
    if ev is None or ev <= 0:
        out["reason"] = "no enterprise value or market cap available"
        return out

    g = implied_growth(ev, fcf0, wacc)
    out["implied_growth"] = g
    if g is None:
        out["reason"] = "bisection could not bracket a solution"
        return out

    # sensitivity strip: the number moves a lot with wacc, and saying so is the point
    d = rubric.DCF_SENSITIVITY_WACC
    for label, w in (("wacc_minus", max(wacc - d, rubric.DCF_TERMINAL_GROWTH + 0.005)),
                     ("wacc_plus", wacc + d)):
        out["sensitivity"][label] = {"wacc": w, "implied_growth": implied_growth(ev, fcf0, w)}

    realized = M.raw("fcf_cagr_3y")
    if realized is None:
        realized = M.raw("revenue_cagr_3y")
    analyst = ctx.mk("analyst_growth_3y")
    if analyst is None:
        analyst = ctx.mk("analyst_growth_1y")

    out["realized_growth_3y"] = realized
    out["analyst_growth"] = analyst

    refs = [r for r in (realized, analyst) if r is not None]
    if not refs:
        out["reason"] = "no realized or analyst growth to compare the implied rate against"
        return out
    ref = sum(refs) / len(refs)
    gap = g - ref                     # negative = the price requires less than it delivers
    out["reference_growth"] = ref
    out["gap_vs_reference"] = gap
    bands = rubric.DCF_IMPLIED_VS_REALIZED_BANDS      # (-0.06, -0.02, 0.03, 0.08) ascending
    out["points"] = rubric.band_from_thresholds_asc(gap, bands, (5, 4, 3, 1, 0))
    out["note"] = (f"price requires {g:.1%} FCF growth vs {ref:.1%} reference "
                   f"(gap {gap:+.1%}) at {wacc:.1%} WACC")
    return out
