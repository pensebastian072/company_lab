"""Forward DCF: what is a share worth if the business grows the way it has been?

The reverse DCF already in this repo asks what growth today's price REQUIRES. This asks
the other direction with the same engine - `wacc_for`, `_growth_path` and
`enterprise_value` are imported, not reimplemented, so the two cannot drift apart. A
company whose fair value equals its price must have an implied growth equal to the g used
here, and `tests/test_forward_dcf.py` asserts that identity.

Registered in `journal/experiments/E20_forward_dcf_preregistration.md`.

Every number here rests on four assumptions - the growth rate, where it starts to fade,
the terminal rate and the discount rate - and moving any one of them moves the answer
materially. So nothing returns a bare fair value: every company that gets one also gets a
bear/base/bull strip and a WACC sensitivity, and every company that does not get one gets
a written reason instead of a default.
"""
from __future__ import annotations

import math

from . import rubric
from .reverse_dcf import enterprise_value, implied_growth, wacc_for

#: a realized growth rate outside this band is not evidence about the next ten years -
#: it is a cycle, a recovery or an accounting artefact
GROWTH_BOUNDS = (-0.10, 0.25)
#: bear and bull are the base case plus and minus this, because a single fair value
#: carries far more apparent authority than four assumptions can support
GROWTH_STRIP = 0.05
#: a fair value this far from the price is reported with a flag rather than ranked
IMPLAUSIBLE_HIGH = 10.0
IMPLAUSIBLE_LOW = 0.1

#: profiles whose free cash flow is not a valuation input. For a bank or an insurer,
#: borrowing IS the raw material - "cash from operations minus capex" describes funding
#: flows, not owner earnings. A residual income or dividend model is the right instrument
#: and it is deliberately out of scope here rather than approximated badly.
NO_FCF_PROFILES = ("FINANCIAL", "MORTGAGE_REIT", "INSURANCE")
NO_FCF_SECTORS = ("Financials",)


def _in_bounds(g) -> bool:
    return g is not None and GROWTH_BOUNDS[0] <= g <= GROWTH_BOUNDS[1]


def growth_for(ctx, peer_median: float | None = None) -> tuple[float | None, dict]:
    """The growth rate to discount, and where it came from.

    Preference order, recorded per company so a fair value can always be traced to the
    series behind it:

      1. realized 5-year FCF CAGR
      2. realized 3-year FCF CAGR
      3. 3-year revenue CAGR, as a proxy, flagged as one
      4. the sub-industry median of whatever the peers got
      5. nothing - and then NO fair value

    Step 2 is an addition to the registered order, which went straight from the 5-year FCF
    CAGR to a revenue proxy. A 3-year FCF CAGR is the same measurement over a shorter
    window and is strictly closer to the registered intent - "prefer realized free cash
    flow growth" - than a revenue proxy is, so it is inserted rather than skipped, and
    said out loud here because changing a registered procedure quietly is how a study
    stops meaning anything.
    """
    M = ctx.metrics
    for key, basis in (("fcf_cagr_5y", "fcf_cagr_5y"), ("fcf_cagr_3y", "fcf_cagr_3y")):
        g = M.raw(key)
        if _in_bounds(g):
            return float(g), {"basis": basis, "raw": g, "clamped": False}
    rev = M.raw("revenue_cagr_3y")
    if _in_bounds(rev):
        return float(rev), {"basis": "revenue_cagr_3y_proxy", "raw": rev,
                            "note": "no usable FCF growth series; revenue growth is a "
                                    "proxy and the fair value inherits its error"}
    if peer_median is not None and _in_bounds(peer_median):
        return float(peer_median), {"basis": "sub_industry_median", "raw": peer_median,
                                    "note": "this company's own series was unusable"}
    # A rate outside the bounds is reported, not used. Clamping it to the edge would
    # invent a fair value out of a number the bounds exist to reject.
    return None, {"basis": None,
                  "rejected": {"fcf_cagr_5y": M.raw("fcf_cagr_5y"),
                               "fcf_cagr_3y": M.raw("fcf_cagr_3y"),
                               "revenue_cagr_3y": rev},
                  "note": "no growth series inside "
                          f"{GROWTH_BOUNDS[0]:.0%}..{GROWTH_BOUNDS[1]:.0%}"}


#: the filed count and the market-derived one may differ this much before the row says so
SHARES_DISPUTE_RATIO = 2.0


def shares_for(ctx) -> tuple[float | None, dict]:
    """Shares outstanding for a per-share valuation, and where the number came from.

    `market_cap / price` beats the filed count on two grounds. The robustness one: MCD
    files `WeightedAverageNumberOfDilutedSharesOutstanding` as 714.525 - MILLIONS - and
    the DCF divided a $170bn equity value by 715 to get $238,644,091 a share. Six more
    filers report in thousands. The correctness one matters more: `diluted_shares_ttm` is
    a trailing four-quarter AVERAGE, so for anything that split or bought back during the
    year it is the wrong quantity even when its units are right - NFLX split 10:1 inside
    the window and its filed count is 9.6x the current one.

    Both inputs come from the same contemporaneous yfinance snapshot, so their ratio is a
    current count. The filed number stays as a cross-check, and a disagreement is
    reported on the row rather than resolved silently.
    """
    filed = ctx.metrics.raw("diluted_shares_ttm")
    mc, px = ctx.mk("market_cap"), (ctx.mk("price") or ctx.prices.get("price"))
    derived = (mc / px) if (mc and px and px > 0) else None

    ratio = None
    if derived and filed and filed > 0:
        ratio = derived / filed
    if derived and derived > 0:
        return derived, {
            "basis": "market_cap_over_price",
            "filed": filed, "derived": derived, "ratio": ratio,
            "disputed": bool(ratio and (ratio > SHARES_DISPUTE_RATIO
                                        or ratio < 1 / SHARES_DISPUTE_RATIO)),
        }
    if filed and filed > 0:
        return float(filed), {"basis": "diluted_shares_ttm", "filed": filed,
                              "derived": None, "ratio": None, "disputed": False}
    return None, {"basis": None, "filed": filed, "derived": derived, "ratio": ratio,
                  "disputed": False}


def _implausible_reason(ratio: float | None, fv: float | None) -> str | None:
    """Why a fair value is distrusted, in words, or None when it is not.

    Written rather than left as a bare boolean because the workbook shows the number
    beside the flag, and a reader who sees a $1,400 fair value on a $370 stock deserves
    to be told which end of the check it failed.
    """
    if fv is not None and math.isfinite(fv) and fv <= 0:
        return ("modelled equity value is zero or negative - the discounted cash flows do "
                "not cover net debt, so there is no fair value to take a discount from")
    if ratio is None or not math.isfinite(ratio):
        return None
    if ratio > IMPLAUSIBLE_HIGH:
        return (f"fair value is {ratio:.0f}x the price - a broken input, not an "
                f"opportunity; no margin of safety is reported")
    if ratio < IMPLAUSIBLE_LOW:
        return (f"fair value is {ratio:.2f}x the price - the growth or discount inputs "
                f"are implausible; no margin of safety is reported")
    return None


def _refusal(reason: str, **extra) -> dict:
    out = {"fair_value_per_share": None, "margin_of_safety": None, "reason": reason}
    out.update(extra)
    return out


def analyse(ctx, peer_median: float | None = None) -> dict:
    """Fair value per share for one company, or a written reason there is none."""
    M = ctx.metrics
    fcf0 = M.raw("fcf_ttm")
    price = ctx.mk("price") or ctx.prices.get("price")
    shares, shares_prov = shares_for(ctx)          # E28
    net_debt = M.raw("net_debt")
    profile = getattr(getattr(ctx, "profile", None), "name", "") or ""
    sector = ctx.sector or ""

    base = {"fcf_ttm": fcf0, "price": price, "shares": shares, "net_debt": net_debt,
            "profile": profile, "shares_provenance": shares_prov}

    if profile in NO_FCF_PROFILES or sector in NO_FCF_SECTORS:
        return _refusal(
            "free cash flow is not a valuation input for this business - for a bank or "
            "insurer, borrowing is the raw material, so CFO minus capex is a funding "
            "flow rather than owner earnings", **base)
    if fcf0 is None or fcf0 <= 0:
        return _refusal(
            "trailing free cash flow is zero or negative - a DCF started from it is "
            "arithmetic, not valuation", **base)
    if not shares or shares <= 0:
        return _refusal("no usable share count from market cap or the filing", **base)
    if price is None or price <= 0:
        return _refusal("no price to compare a fair value against", **base)

    wacc, wacc_prov = wacc_for(ctx.mk("beta"), ctx.mk("risk_free"))
    if wacc <= rubric.DCF_TERMINAL_GROWTH:
        return _refusal("discount rate is at or below the terminal growth rate, which "
                        "makes the terminal value meaningless", wacc=wacc, **base)

    g, g_prov = growth_for(ctx, peer_median)
    if g is None:
        return _refusal("no usable growth rate", growth=g_prov, wacc=wacc, **base)

    nd = net_debt or 0.0

    def per_share(growth: float, discount: float) -> float | None:
        ev = enterprise_value(fcf0, growth, discount)
        if ev == float("inf"):
            return None
        return (ev - nd) / shares

    fv = per_share(g, wacc)
    if fv is None:
        return _refusal("enterprise value did not converge", growth=g_prov, wacc=wacc,
                        **base)

    strip = {
        "bear": per_share(g - GROWTH_STRIP, wacc),
        "base": fv,
        "bull": per_share(g + GROWTH_STRIP, wacc),
    }
    d = rubric.DCF_SENSITIVITY_WACC
    wacc_strip = {
        "wacc_minus": per_share(g, max(wacc - d, rubric.DCF_TERMINAL_GROWTH + 0.005)),
        "wacc_plus": per_share(g, wacc + d),
    }
    ratio = fv / price if price else None
    # E33: `implausible` is computed BEFORE the dict so the margin of safety can be
    # withheld on it. It used to be computed inside the literal, so every flagged company
    # still shipped a number.
    implausible = bool(ratio is not None
                       and (ratio > IMPLAUSIBLE_HIGH or ratio < IMPLAUSIBLE_LOW))

    # Margin of safety is (fair - price) / fair - Graham's discount to intrinsic value -
    # and it is only meaningful when the fair value is a positive number this model
    # actually believes. The old guard was `if fv`, which catches fv == 0 and nothing
    # else, so a NEGATIVE fair value flipped the sign of both numerator and denominator
    # and came out POSITIVE. Measured 2026-08-25: HR's fair value of -$0.008 reported a
    # +251,695% margin of safety, VST's -$0.76 reported +17,846%, and 117 companies had
    # |MOS| over 500%. A model that says the equity is worthless has not found a bargain,
    # so the honest value is None - and because the DCF sheet sorts on this column,
    # emitting it made the most broken DCFs rank as the cheapest.
    usable = fv is not None and math.isfinite(fv) and fv > 0 and not implausible
    mos = (fv - price) / fv if usable else None
    return {
        "fair_value_per_share": fv,
        "margin_of_safety": mos,
        "price": price,
        "fair_value_over_price": ratio,
        "growth": g,
        "growth_provenance": g_prov,
        "wacc": wacc,
        "wacc_inputs": wacc_prov,
        "years": rubric.DCF_YEARS,
        "terminal_growth": rubric.DCF_TERMINAL_GROWTH,
        "strip": strip,
        "wacc_sensitivity": wacc_strip,
        # Reported, never silently ranked. A 20x fair value is a broken input, not a
        # buying opportunity.
        "implausible": implausible,
        "fcf_ttm": fcf0, "shares": shares, "net_debt": nd, "profile": profile,
        "shares_provenance": shares_prov,
        # A flag with no explanation beside it is half a finding. `reason` used to be
        # None for all 125 flagged companies, so the workbook showed an absurd fair value
        # with nothing saying why it was distrusted.
        "reason": _implausible_reason(ratio, fv),
    }


def reconcile(ctx, result: dict) -> dict:
    """V1: the two DCFs must be the same arithmetic seen from two sides.

    Feed the fair value's own enterprise value back through the reverse DCF's solver; the
    growth it recovers must be the growth that produced it.
    """
    if not result or result.get("fair_value_per_share") is None:
        return {"checked": False}
    fcf0 = result["fcf_ttm"]
    wacc = result["wacc"]
    ev = enterprise_value(fcf0, result["growth"], wacc)
    back = implied_growth(ev, fcf0, wacc)
    return {"checked": True, "enterprise_value": ev, "growth_in": result["growth"],
            "growth_out": back,
            "abs_error": None if back is None else abs(back - result["growth"])}
