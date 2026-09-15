"""EN - Entry Opportunity /5, v2.

The user's framing, unchanged: "I already want the company - is the market giving me
an unusually attractive price?" This is entry timing on a name already chosen on its
fundamentals, not signal generation.

What changed on 2026-08-09, at the user's direction: the **multiple matters more
than the moving average**. A high-multiple grower whose P/E has compressed to the
low end of its own multi-year range is the setup worth catching - the case where an
absolute valuation screen says "expensive" while the company's own history says
"this is as cheap as this has been". So:

    valuation_trough  2   P/E percentile against its own reconstructed history
    vs_emas           2   price at the 20 / 72 EMA, weighted by timeframe
    confluence        1   both at once

Drawdown-from-ATH and swing-low proximity are still computed and displayed, but no
longer score: a drawdown describes the chart, whereas a compressed multiple on a
growing business describes what you are paying for the earnings.

Higher timeframes score higher. Price reaching the 20-period EMA on a MONTHLY chart
is twenty months of trend catching up to it; the same touch on a daily chart is
noise. Both are reported so the scorecard shows which timeframe fired.
"""
from __future__ import annotations

from . import rubric
from .context import SymbolContext, num, pct, subtest
from .types import ComponentScore

CODE = "EN"


def _ema_hits(P: dict) -> tuple[list[dict], int]:
    """Every (timeframe, span) the price is at or below, with the best weight."""
    hits: list[dict] = []
    best = 0
    price = P.get("price")
    if price is None:
        return hits, best
    for tf in rubric.EN_TIMEFRAMES:
        weight = rubric.EN_TIMEFRAME_WEIGHT[tf]
        for span in rubric.EN_EMA_SPANS:
            val = P.get(f"ema{span}_{tf}")
            if not val:
                continue
            dist = (price - val) / val
            # near the line on EITHER side - see EN_AT_EMA_BELOW in rubric.py for
            # why being far underneath does not count
            at_line = -rubric.EN_AT_EMA_BELOW <= dist <= rubric.EN_AT_EMA_TOLERANCE
            if at_line:
                hits.append({"timeframe": tf, "span": span, "ema": val,
                             "pct_vs_ema": dist, "weight": weight,
                             "below": dist < 0})
                best = max(best, weight)
            elif dist < -rubric.EN_AT_EMA_BELOW:
                hits.append({"timeframe": tf, "span": span, "ema": val,
                             "pct_vs_ema": dist, "weight": 0,
                             "below": True, "far_below": True})
    hits.sort(key=lambda h: (-h["weight"], h["span"]))
    return hits, best


def _first_scoring_hit(hits: list[dict]) -> dict | None:
    for h in hits:
        if h.get("weight", 0) > 0:
            return h
    return None


def score(ctx: SymbolContext) -> ComponentScore:
    P = ctx.prices or {}
    peers = ctx.peers or {}
    sts = []

    # ------------------------------------------------- 1. P/E vs own history /1
    pctile = peers.get("pe_pctile_own")
    pe_inputs = {
        "pe_pctile_own": pctile,
        "pe_current": peers.get("pe_current"),
        "pe_median_own": peers.get("pe_median_own"),
        "pe_min_own": peers.get("pe_min_own"),
        "pe_max_own": peers.get("pe_max_own"),
        "pe_history_n": peers.get("pe_history_n"),
        "pe_history_years": peers.get("pe_history_years"),
        "pe_history_note": peers.get("pe_history_note"),
    }
    if pctile is not None:
        # /1 after the v2 reweighting: the point is earned in the cheapest ~30% of the
        # company's own range, with confluence folded in below.
        pts = rubric.band_from_thresholds_asc(
            pctile, rubric.EN_PE_PCTILE_BANDS, (1, 1, 0, 0))
        why = (f"P/E {num(peers.get('pe_current'))} sits at the {pctile:.0%} "
               f"percentile of its own {num(peers.get('pe_history_years'), 1)}y range "
               f"({num(peers.get('pe_min_own'))} - {num(peers.get('pe_max_own'))}, "
               f"median {num(peers.get('pe_median_own'))})")
    else:
        pts = None
        why = ""
    sts.append(subtest(
        ctx, "en_valuation_trough", "P/E near the low end of its own history", 1,
        value=pctile, points=pts, inputs=pe_inputs,
        provenance={"source": "derived",
                    "formula": "close / TTM diluted EPS, EPS applied from its filing date",
                    "inputs_from": ["yfinance daily closes", "EDGAR EarningsPerShareDiluted"]},
        note=why,
        na_reason=(peers.get("pe_history_note")
                   or "no positive-earnings history to build a P/E series from"),
    ))

    # ------------------------------------------------- 2. price vs the EMAs /2
    hits, best_weight = _ema_hits(P)
    ema_inputs = {
        "price": P.get("price"),
        "hits": hits,
        "best_timeframe_weight": best_weight,
        "bars": {tf: P.get(f"{tf}_bars") for tf in rubric.EN_TIMEFRAMES},
    }
    for tf in rubric.EN_TIMEFRAMES:
        for span in rubric.EN_EMA_SPANS:
            ema_inputs[f"ema{span}_{tf}"] = P.get(f"ema{span}_{tf}")
            ema_inputs[f"pct_vs_ema{span}_{tf}"] = P.get(f"pct_vs_ema{span}_{tf}")

    have_any = any(P.get(f"ema{s}_{tf}") for tf in rubric.EN_TIMEFRAMES
                   for s in rubric.EN_EMA_SPANS)
    hit = _first_scoring_hit(hits)
    far_below = [h for h in hits if h.get("far_below")]
    # /1 after the v2 reweighting: the point requires a HIGHER-timeframe touch. A
    # daily-only touch no longer scores - at one point it would have been the easiest
    # condition in the framework to satisfy by accident.
    if not have_any:
        pts, why = None, ""
    elif hit and best_weight >= rubric.EN_TIMEFRAME_WEIGHT["monthly"]:
        pts = 1
        why = (f"at the {hit['span']} EMA on the MONTHLY "
               f"({pct(hit['pct_vs_ema'])} away) - the rare one")
    elif hit and best_weight >= rubric.EN_TIMEFRAME_WEIGHT["weekly"]:
        pts = 1
        why = f"at the {hit['span']} EMA on the WEEKLY ({pct(hit['pct_vs_ema'])} away)"
    elif hit:
        pts = 0
        why = (f"at the {hit['span']} EMA on the daily only "
               f"({pct(hit['pct_vs_ema'])} away) - daily alone no longer scores")
    elif far_below:
        pts = 0
        deepest = min(far_below, key=lambda h: h["pct_vs_ema"])
        why = (f"{pct(deepest['pct_vs_ema'])} below the {deepest['span']} "
               f"{deepest['timeframe']} EMA - a drawdown, not a touch")
    else:
        pts = 0
        why = "above every 20 / 72 EMA on all three timeframes - no discount"
    # Confluence is now recorded as context on this sub-test rather than earning a
    # point of its own: at 2 points total, a third sub-test would be scoring noise.
    cheap = pctile is not None and pctile <= rubric.EN_CONFLUENCE_PCTILE
    at_higher_tf = best_weight >= rubric.EN_CONFLUENCE_MIN_TF_WEIGHT
    ema_inputs.update({
        "cheap_vs_own_history": cheap,
        "pe_pctile_own": pctile,
        "at_higher_timeframe_ema": at_higher_tf,
        "confluence": bool(cheap and at_higher_tf),
        "drawdown_from_ath": P.get("drawdown_from_ath"),
        "pct_above_support": P.get("pct_above_support"),
        "volume_z": P.get("volume_z"),
    })
    if cheap and at_higher_tf and pts:
        why += " | CONFLUENCE: the multiple is compressed too"
    sts.append(subtest(
        ctx, "en_vs_emas", "Price at the 20 / 72 EMA on daily, weekly or monthly", 1,
        value=P.get("price") if pts is not None else None, points=pts,
        inputs=ema_inputs,
        provenance={"source": "yfinance daily OHLCV, resampled to weekly and monthly"},
        note=why,
    ))

    comp = ComponentScore(
        code=CODE, label=rubric.COMPONENTS[CODE][0],
        max_points=rubric.COMPONENTS[CODE][1], subtests=sts,
        note=("I already want the company - is the market giving me an unusually "
              "attractive price? Cut from 5 points to 2 on the evidence of E01 and "
              "E02: entry timing added no value over 2016-2025 and had the most "
              "negative IC of the four measured components. Kept non-zero because "
              "that window contains no prolonged bear market, so it cannot test what "
              "this component protects against."),
    )
    comp.check_points()
    return comp
