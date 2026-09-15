"""ER - Expectations vs Reality /5.

A company can report excellent numbers and fall 20%, because the market expected
better. The best setup is fundamentals improving FASTER than expectations, so
this component measures the gap rather than the level: realized surprise history,
the direction of estimate revisions, and realized growth against expected growth.
"""
from __future__ import annotations

from . import rubric
from .context import SymbolContext, num, pct, subtest
from .types import ComponentScore

CODE = "ER"


def score(ctx: SymbolContext) -> ComponentScore:
    M = ctx.metrics
    sts = []

    # ------------------------------------------------------------ surprise history /2
    rate = ctx.mk("surprise_beat_rate")
    n = ctx.mk("surprise_quarters")
    pts = rubric.band_from_thresholds(rate, rubric.ER_SURPRISE_BANDS, (2, 1, 0))
    sts.append(subtest(
        ctx, "er_earnings_surprise", "Realized results vs consensus", 2,
        value=rate, points=pts,
        inputs={"beat_rate": rate, "quarters": n},
        provenance={"source": "yfinance earnings_dates"},
        note=f"beat {pct(rate)} of {num(n, 0)} reported quarters vs bands {rubric.ER_SURPRISE_BANDS}",
    ))

    # ------------------------------------------------------------ revisions /2
    rev = ctx.mk("eps_revision_direction")
    pts = rubric.band_from_thresholds(rev, rubric.ER_REVISION_BANDS, (2, 1, 1, 0))
    sts.append(subtest(
        ctx, "er_estimate_revisions", "Estimate revision direction", 2,
        value=rev, points=pts,
        inputs={"eps_revision_30d": rev},
        provenance={"source": "yfinance eps_trend (current vs 30 days ago)"},
        note=f"consensus EPS revised {pct(rev)} over 30 days vs bands {rubric.ER_REVISION_BANDS}",
    ))

    # ------------------------------------------------- realized vs expected growth /1
    realized = M.raw("revenue_cagr_1y")
    if realized is None:
        realized = M.raw("revenue_yoy")
    expected = ctx.mk("analyst_growth_1y")
    if realized is not None and expected is not None:
        gap = realized - expected
        pts = 1 if gap > 0 else 0
        why = (f"realized revenue growth {pct(realized)} vs expected {pct(expected)} "
               f"(gap {pct(gap)})")
    else:
        gap, pts, why = None, None, ""
    sts.append(subtest(
        ctx, "er_growth_vs_expectation", "Realized growth vs expected growth", 1,
        value=gap, points=pts,
        inputs={"realized_growth": realized, "expected_growth": expected, "gap": gap},
        prov_keys=("revenue_ttm",), note=why,
    ))

    comp = ComponentScore(
        code=CODE, label=rubric.COMPONENTS[CODE][0],
        max_points=rubric.COMPONENTS[CODE][1], subtests=sts,
        note="Surprise history 2 / revision direction 2 / realized-vs-expected 1.",
    )
    comp.check_points()
    return comp
