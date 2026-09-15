"""E39 - what would it cost to require a reason beside a moat-dimension score?

Registered at `journal/experiments/E39_unjustified_dimensions_preregistration.md`.

Production commits ~2,185 moat-dimension scores whose rationale is the literal string
`null`/`Null` or empty. They are invisible - nothing renders dimension-level rationales -
but they are not inert, because `bq_moat` is

    round(mean(scored dimensions) / 5 * 15),   requiring >= 6 of 11 scored

so an unjustified dimension moves the mean AND counts toward the floor that decides
whether a company is scored on moat at all.

**This module changes nothing.** It recomputes `bq_moat` under one counterfactual - drop
the unjustified dimensions - and reports what would move. Whether to enforce it is a
framework decision with a date discontinuity in the middle of the snapshot series, and
that is the user's call.

    python -m clab.research.e39_unjustified_dimensions
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import statistics
from pathlib import Path

from .. import config
from ..net import atomic_write_json
from ..scoring import rubric
from .e36_compare import classify_rationale

OUT_JSON = config.JOURNAL_DIR / "experiments" / "E39_results.json"
OUT_MD = config.JOURNAL_DIR / "experiments" / "E39_results.md"


def bq_points(scores: list[int]) -> int | None:
    """rubric A2, reimplemented over raw dimension scores. None below the floor.

    Kept in step with `clab.scoring.bq` by reading the same rubric constants rather than
    the same code: this has to answer a question the scorer cannot be asked, which is
    "what if these dimensions had never been scored".
    """
    if len(scores) < rubric.BQ_MIN_DIMENSIONS_SCORED:
        return None
    mx = rubric.COMPONENTS["BQ"][1]
    return round(statistics.fmean(scores) / rubric.BQ_DIMENSION_MAX * mx)


def unjustified(rationale) -> bool:
    """A committed score with nothing said about it. `terse` does NOT count - E36's
    amendment 1 is the precedent: a short judgement is a judgement."""
    return classify_rationale(rationale) in ("chrome", "empty")


def run(scorecard_dir: str | None = None) -> dict:
    directory = scorecard_dir or str(config.SCORECARD_DIR)

    companies: list[dict] = []
    just_scores: list[int] = []
    unjust_scores: list[int] = []
    by_key: collections.Counter = collections.Counter()

    for path in sorted(glob.glob(os.path.join(directory, "*.json"))):
        with open(path, encoding="utf-8") as fh:
            card = json.load(fh)
        bq = ((card.get("components") or {}).get("BQ") or {})
        moat = next((st for st in bq.get("subtests") or []
                     if st.get("key") == "bq_moat"), None)
        if not moat:
            continue
        dims = (moat.get("inputs") or {}).get("dimensions") or {}

        kept, dropped = [], []
        for key, rec in dims.items():
            if not isinstance(rec, dict) or rec.get("score") is None:
                continue
            value = int(rec["score"])
            if unjustified(rec.get("rationale")):
                dropped.append(value)
                unjust_scores.append(value)
                by_key[key] += 1
            else:
                kept.append(value)
                just_scores.append(value)

        if not dropped:
            continue

        before = bq_points(kept + dropped)
        after = bq_points(kept)
        # P3 - the band, which is what a reader actually acts on. Losing bq_moat costs
        # its 15 points of AVAILABLE too, so coverage falls and the 0.80 gate can bite
        # even where the score barely moves. Modelling only the score would understate it.
        band_before, band_after = card.get("band_raw"), card.get("band_raw")
        ex_entry = card.get("composite_ex_entry")
        applicable = card.get("applicable_points") or rubric.TOTAL_POINTS
        available = card.get("points_available")
        if ex_entry is not None and available and before is not None:
            denom = rubric.TOTAL_POINTS - rubric.COMPONENTS["EN"][1]
            moat_max = int(moat.get("max_points") or rubric.COMPONENTS["BQ"][1])
            delta = 0 if after is None else after - before
            new_available = available - (moat_max if after is None else 0)
            new_ex_entry = ex_entry + (delta if after is not None else -before)
            band_before = rubric.band_for(int(round(100.0 * ex_entry / denom)),
                                          available / applicable)
            band_after = rubric.band_for(int(round(100.0 * new_ex_entry / denom)),
                                         new_available / applicable)
        companies.append({
            "band_before": band_before,
            "band_after": band_after,
            "ticker": card.get("ticker"),
            "sector": card.get("sector"),
            "score": card.get("score"),
            "band": card.get("band"),
            "n_dimensions": len(kept) + len(dropped),
            "n_unjustified": len(dropped),
            "bq_before": before,
            "bq_after": after,
            "bq_delta": None if after is None or before is None else after - before,
            "falls_below_floor": after is None and before is not None,
            "mean_unjustified": round(statistics.fmean(dropped), 2),
            "mean_justified": round(statistics.fmean(kept), 2) if kept else None,
        })

    deltas = [c["bq_delta"] for c in companies if c["bq_delta"] is not None]
    below = [c for c in companies if c["falls_below_floor"]]
    paired = [(c["mean_justified"], c["mean_unjustified"]) for c in companies
              if c["mean_justified"] is not None]

    return {
        "experiment": "E39",
        "scorecard_dir": directory,
        "n_companies_affected": len(companies),
        "n_unjustified_dimensions": sum(c["n_unjustified"] for c in companies),
        "n_scored_dimensions": len(just_scores) + len(unjust_scores),
        "share_unjustified": round(
            len(unjust_scores) / max(len(just_scores) + len(unjust_scores), 1), 4),
        "by_dimension": by_key.most_common(),
        "P1_mean_scores": {
            "justified": round(statistics.fmean(just_scores), 3) if just_scores else None,
            "unjustified": round(statistics.fmean(unjust_scores), 3)
            if unjust_scores else None,
            "gap": round(statistics.fmean(unjust_scores) - statistics.fmean(just_scores), 3)
            if just_scores and unjust_scores else None,
            # Within-company, so a company-level difference in how generously the whole
            # filing was read cannot masquerade as a difference between the two groups.
            "within_company_gap": round(statistics.fmean(u - j for j, u in paired), 3)
            if paired else None,
            "n_companies_paired": len(paired),
        },
        "P2_below_floor": {
            "n": len(below),
            "floor": rubric.BQ_MIN_DIMENSIONS_SCORED,
            "tickers": [c["ticker"] for c in below][:40],
        },
        "P3_band_changes": {
            "n": sum(1 for c in companies if c["band_before"] != c["band_after"]),
            "moves": collections.Counter(
                f"{c['band_before']} -> {c['band_after']}" for c in companies
                if c["band_before"] != c["band_after"]).most_common(),
        },
        "P4_bq_delta": {
            "mean": round(statistics.fmean(deltas), 3) if deltas else None,
            "median": round(statistics.median(deltas), 2) if deltas else None,
            "n_up": sum(1 for d in deltas if d > 0),
            "n_down": sum(1 for d in deltas if d < 0),
            "n_flat": sum(1 for d in deltas if d == 0),
            "n_undefined": len(below),
        },
        "companies": sorted(companies,
                            key=lambda c: (c["bq_delta"] is None, -(c["bq_delta"] or 0)))[:60],
    }


def _fmt_md(res: dict) -> str:
    p1, p2, p4 = res["P1_mean_scores"], res["P2_below_floor"], res["P4_bq_delta"]
    lines = [
        "# E39 results - the moat dimensions with a score and no reason",
        "",
        f"{res['n_unjustified_dimensions']} unjustified dimension scores over "
        f"{res['n_scored_dimensions']} scored "
        f"({res['share_unjustified'] * 100:.1f}%), affecting "
        f"{res['n_companies_affected']} companies. Registered at "
        "`journal/experiments/E39_unjustified_dimensions_preregistration.md`. "
        "**Nothing is rescored here.**",
        "",
        "## P1 - do unjustified dimensions score differently?",
        "",
        "| | mean 0-5 |",
        "|---|---:|",
        f"| with a rationale | {p1['justified']} |",
        f"| with none | {p1['unjustified']} |",
        f"| **gap** | **{p1['gap']:+}** |",
        f"| gap within the same company ({p1['n_companies_paired']} companies) | "
        f"**{p1['within_company_gap']:+}** |",
        "",
        "## P2 / P4 - what dropping them would do",
        "",
        f"* **{p2['n']}** companies fall below the {p2['floor']}-of-11 floor and lose "
        "`bq_moat` entirely.",
        f"* Of the rest: **{p4['n_up']} up, {p4['n_down']} down, {p4['n_flat']} "
        f"unchanged**, mean `bq_moat` delta **{p4['mean']:+}** of 15 "
        f"(median {p4['median']:+}).",
        f"* **{res['P3_band_changes']['n']}** companies change band (raw, before "
        "hysteresis): "
        + (", ".join(f"{move} x{n}" for move, n in res["P3_band_changes"]["moves"][:8])
           or "none"),
        "",
        "## Most affected dimensions",
        "",
        "| dimension | unjustified scores |",
        "|---|---:|",
    ]
    for key, n in res["by_dimension"][:11]:
        lines.append(f"| `{key}` | {n} |")
    lines += [
        "",
        "## Reading",
        "",
        f"**Silence is a low score.** A dimension with no rationale scores "
        f"{abs(p1['within_company_gap'])} lower than a justified one **in the same "
        "company**, on a 0-5 scale - a bigger gap than the between-company one, so it is "
        "not that unexplained dimensions cluster in badly-read filings. The model scored "
        "low and did not say why.",
        "",
        f"**And that is exactly why enforcement is not a cheap win.** "
        f"{p2['n']} of {res['n_companies_affected']} affected companies fall below the "
        f"{p2['floor']}-of-11 floor - **their moat score exists only because unexplained "
        "dimensions make up the quorum.** Dropping them does not tighten the ranking, it "
        f"deletes moat scoring for {p2['n']} companies and pushes "
        + str(sum(n for move, n in res["P3_band_changes"]["moves"]
                  if move.endswith("INSUFFICIENT_DATA")))
        + " of them out of banding entirely. The registered prediction for this was "
          "**< 60**, and it is wrong by a factor of four.",
        "",
        "**The companies that survive get *better*, not worse** - mean `bq_moat` "
        f"{p4['mean']:+} of 15, {p4['n_up']} up against {p4['n_down']} down - because "
        "removing a silent low score raises a mean. Requiring a reason is not a rigour "
        "dial: it is an abstention dial at one end and a generosity dial at the other.",
        "",
        "**So the defect is worth fixing at the source, not at the scorer.** A "
        "regenerated or repaired dimension that comes back with a reason keeps the "
        "quorum; withholding on the current payloads throws the company out. That points "
        "at the E15/E17 repair path, not at a rubric change.",
        "",
        "## What this does not decide",
        "",
        "Whether to enforce it. Requiring a rationale is a framework change, it is "
        "discontinuous at a date in the middle of the snapshot series the forward-return "
        "grader needs (hard rule 9), and it would delete moat scoring for the companies "
        "above the floor only by luck. That call is the user's, and it should be made "
        "against these numbers rather than against the word 'rigour'.",
        "",
    ]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scorecards", default=None)
    ap.add_argument("--json", default=str(OUT_JSON))
    ap.add_argument("--md", default=str(OUT_MD))
    args = ap.parse_args(argv)

    res = run(args.scorecards)
    atomic_write_json(Path(args.json), res)
    Path(args.md).write_text(_fmt_md(res), encoding="utf-8")
    p1 = res["P1_mean_scores"]
    print(f"{res['n_unjustified_dimensions']} unjustified of {res['n_scored_dimensions']} "
          f"({res['share_unjustified'] * 100:.1f}%), {res['n_companies_affected']} companies")
    print(f"P1 gap {p1['gap']:+} overall, {p1['within_company_gap']:+} within company")
    print(f"P2 below floor: {res['P2_below_floor']['n']}   "
          f"P4 mean bq delta {res['P4_bq_delta']['mean']:+}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
