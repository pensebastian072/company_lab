"""Sector-neutral ranking: where does a company sit against its OWN peers?

E03 R1 found that a large share of this score's ranking power was sector selection, and
the workbook still shows it - Information Technology averages 60.1 against Utilities 42.3
on `composite_strict`. Asking whether an energy company at 68 beats a software company at
78 is mostly asking which sector you prefer.

**E05's F1 already tried to fix this and FAILED.** F1 made the five FE margin/returns
sub-tests sector-relative. Within-sector IC improved (0.0170 -> 0.0233) but the sector
spread only fell 24.1 -> 19.2 points against a criterion of under 10.7, under all three
sector definitions. Read `journal/experiments/E05_results.md` before treating any of this
as new ground.

This is a stronger change than F1 in one specific way: F1 re-based five sub-tests INSIDE
the score, and the surviving spread came from everything it did not touch. A percentile
transform of the FINAL score removes the spread by construction, because a percentile is
defined relative to the peer group.

It is also NOT a replacement. `composite_strict` remains the headline and is untouched;
these are additional columns. Whether the neutral score ranks better is an empirical
question for E13, pre-registered separately - a transform that removes sector spread by
construction has proved nothing by doing so.

**2026-08-25 - these columns became the CROSS-SECTOR headline in the workbook.** Nothing
here was recomputed and no weight moved; the Rank sheet now carries `sector_rank` and
`sector_neutral_score` beside `score`, and says which of the two answers which question.
The reason is measured, not aesthetic: median score runs from Information Technology 59
down to Real Estate 33, a 26-point spread, and Real Estate is banded at 34% against IT's
94%. The absolute score is usable WITHIN a sector and misleading across them, and the
workbook led with the misleading one. E14 is the supporting result - ranking within each
sector beat ranking raw by 2.7 points annualised - and it still fails the promotion gate,
so this is a change of PRESENTATION and carries no claim that either column predicts
returns.
"""
from __future__ import annotations

import bisect
from collections import defaultdict

#: A percentile against four peers is noise dressed as a statistic. Matches
#: `rubric.VA_MIN_PEERS`, which governs the same judgement for peer multiples.
MIN_PEERS = 5

SUB_INDUSTRY = "sub_industry"
SECTOR = "sector"


def _percentile(sorted_vals: list[float], v: float) -> float:
    """Share of peers at or below `v`. Higher score -> higher percentile."""
    return bisect.bisect_right(sorted_vals, v) / len(sorted_vals)


def _groups(rows, key: str, score_col: str) -> dict[str, list[float]]:
    out: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        g = (r.get(key) or "").strip()
        v = r.get(score_col)
        if not g or not isinstance(v, (int, float)):
            continue
        out[g].append(float(v))
    for vals in out.values():
        vals.sort()
    return out


def _rank_desc(sorted_vals: list[float], v: float) -> int:
    """Standard competition rank, 1 = highest. Ties share a rank and the next one skips."""
    return len(sorted_vals) - bisect.bisect_right(sorted_vals, v) + 1


def neutralize(rows: list[dict], score_col: str = "composite_strict") -> list[dict]:
    """Add raw_score, sub_industry_percentile, sector_percentile, sector_neutral_score.

    Sub-industry is the primary unit and sector is the fallback, because semiconductors
    and enterprise software should not share margin and ROIC expectations - collapsing
    them into "Information Technology" is most of what the sector effect IS.

    Every row records `sector_neutral_basis` so a percentile computed against 6 peers is
    never mistaken for one computed against 60. Where neither group clears MIN_PEERS the
    neutral score is None: abstaining is the same choice `va.py` already makes for peer
    multiples, and a made-up percentile would be worse than none.

    `sector_rank` / `sector_rank_n` are a plain count, not a statistic - "12th of 190 in
    Information Technology" - so they are emitted whenever the sector has ANY scored
    company, without the MIN_PEERS floor the percentiles carry.

    Every row also records `sector_neutral_score_col`. The percentile is taken over
    `composite_strict`, while the workbook's headline `score` is the ex-entry sum
    normalised to 100, and those two do not rank identically. A reader who assumes the
    neutral column is a percentile of the column beside it will be wrong on the rows
    where they disagree, so the basis travels on the row.
    """
    by_sub = _groups(rows, SUB_INDUSTRY, score_col)
    by_sec = _groups(rows, SECTOR, score_col)

    for r in rows:
        v = r.get(score_col)
        r["raw_score"] = v
        r["sub_industry_percentile"] = None
        r["sector_percentile"] = None
        r["sector_neutral_score"] = None
        r["sector_neutral_basis"] = "none"
        r["sector_neutral_n"] = 0
        r["sector_neutral_score_col"] = score_col
        r["sector_rank"] = None
        r["sector_rank_n"] = 0
        if not isinstance(v, (int, float)):
            continue
        v = float(v)

        sub = (r.get(SUB_INDUSTRY) or "").strip()
        sec = (r.get(SECTOR) or "").strip()
        sub_vals = by_sub.get(sub) or []
        sec_vals = by_sec.get(sec) or []

        if sec_vals:
            r["sector_rank"] = _rank_desc(sec_vals, v)
            r["sector_rank_n"] = len(sec_vals)

        if len(sub_vals) >= MIN_PEERS:
            r["sub_industry_percentile"] = round(_percentile(sub_vals, v), 4)
        if len(sec_vals) >= MIN_PEERS:
            r["sector_percentile"] = round(_percentile(sec_vals, v), 4)

        if r["sub_industry_percentile"] is not None:
            r["sector_neutral_score"] = round(100 * r["sub_industry_percentile"], 1)
            r["sector_neutral_basis"] = SUB_INDUSTRY
            r["sector_neutral_n"] = len(sub_vals)
        elif r["sector_percentile"] is not None:
            r["sector_neutral_score"] = round(100 * r["sector_percentile"], 1)
            r["sector_neutral_basis"] = SECTOR
            r["sector_neutral_n"] = len(sec_vals)
    return rows


#: Every column `neutralize` writes. A workbook that leads with one of these must not be
#: able to render it blank, so `ensure` checks for all of them rather than a sentinel.
COLUMNS = ("raw_score", "sub_industry_percentile", "sector_percentile",
           "sector_neutral_score", "sector_neutral_basis", "sector_neutral_n",
           "sector_neutral_score_col", "sector_rank", "sector_rank_n")


def ensure(rows: list[dict], score_col: str = "composite_strict") -> bool:
    """Neutralize `rows` only if the columns are not already there. Returns True if run.

    The crawl calls `neutralize` before writing the parquet, so on the normal path this
    is a no-op. It exists because the workbook can also be built from a parquet written
    by an EARLIER version of this module - `sector_rank` did not exist before
    2026-08-25 - and a headline column that renders blank because an old file lacks it is
    exactly the silent-degradation failure this repo keeps getting bitten by. Percentiles
    are cross-sectional, so this is only correct over a whole population; `build_workbook`
    is passed the full row set and the UI's sheet filter selects SHEETS, never rows.
    """
    if rows and all(all(c in r for c in COLUMNS) for r in rows):
        return False
    neutralize(rows, score_col=score_col)
    return True


def spread_report(rows: list[dict], score_col: str = "composite_strict") -> dict:
    """Sector spread before and after, which is the only claim this change can make.

    A percentile transform flattens the spread by construction, so this number is a
    CHECK THAT THE TRANSFORM RAN, not evidence that the ranking improved. E05's F1 is
    the cautionary case: it moved the spread and still failed, because moving a spread
    is not the same as ranking better.
    """
    def _means(col):
        acc: dict[str, list[float]] = defaultdict(list)
        for r in rows:
            sec = (r.get(SECTOR) or "").strip()
            v = r.get(col)
            if sec and isinstance(v, (int, float)):
                acc[sec].append(float(v))
        return {s: sum(v) / len(v) for s, v in acc.items() if v}

    raw, neu = _means(score_col), _means("sector_neutral_score")
    def _spread(d):
        return (max(d.values()) - min(d.values())) if len(d) > 1 else None
    return {
        "sector_mean_raw": {k: round(v, 1) for k, v in sorted(raw.items())},
        "sector_mean_neutral": {k: round(v, 1) for k, v in sorted(neu.items())},
        "spread_raw": (None if _spread(raw) is None else round(_spread(raw), 1)),
        "spread_neutral": (None if _spread(neu) is None else round(_spread(neu), 1)),
        "scored": sum(1 for r in rows if r.get("sector_neutral_score") is not None),
        "by_basis": {
            b: sum(1 for r in rows if r.get("sector_neutral_basis") == b)
            for b in (SUB_INDUSTRY, SECTOR, "none")
        },
        "note": ("A percentile transform removes sector spread BY CONSTRUCTION. This "
                 "confirms the transform ran; it is not evidence of a better ranking. "
                 "E05's F1 moved the spread and still failed its criterion."),
    }
