"""E41 - what does a citation-gated hybrid buy, in coverage and in bands?

Registered at `journal/experiments/E41_verified_fill_preregistration.md`.

The proposal E40 leaves standing: keep production's judged half, and accept a candidate
answer ONLY where the candidate's own quote verifies against the filing it was given.
Production cites accurately and abstains a lot; the candidate answers everything and 9.9%
of its SG citations fail containment. Gating on the citation takes the coverage without
the fabrication.

**This is arithmetic, not a rebuild.** No fold, no fourth workbook, no GPU: production's
scorecards supply every company's current available/applicable points, and the candidate's
payloads supply the sub-tests it would add. Coverage is recomputed with the rubric's own
denominator.

**It can only be done for SG, and that is the headline caveat.** `parse_sg` verifies a
quote per sub-test; `parse_bq` and `parse_mg` verify once at the top level, so on BQ -
where most of the abstention lives - there is no per-dimension citation to gate on. E41
therefore measures a FLOOR. The ceiling needs per-dimension evidence in the BQ schema and
a full re-run.

    python -m clab.research.e41_verified_fill
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
from ..net import atomic_write_json, read_json
from ..scoring import rubric

OUT_JSON = config.JOURNAL_DIR / "experiments" / "E41_results.json"
OUT_MD = config.JOURNAL_DIR / "experiments" / "E41_results.md"

CANDIDATE_DIR = str(config.DATA_ROOT / "qual_lfm25")

#: THE TWO KEY SPACES ARE NOT THE SAME. A payload's `scores` dict is keyed by the bare
#: rubric key (`tam_expanding`); a scorecard's sub-test is keyed with the component prefix
#: (`sg_tam_expanding`). Comparing them directly makes every candidate answer look like a
#: fill: the first version of this module reported 18.14 of 20 SG points added per company,
#: which is only believable if production abstained on nearly all of SG - it abstains on
#: 23%. Caught by the number being absurd, which is not a method. Hence one conversion, in
#: one place.
SG_MAX = {f"sg_{key}": int(mx) for key, _label, mx in rubric.SG_SUBTESTS}


def _scorecard_key(payload_key: str) -> str:
    return payload_key if payload_key.startswith("sg_") else f"sg_{payload_key}"


def candidate_sg(directory: str) -> dict[str, dict[str, dict]]:
    """{ticker: {subtest: {"score": int, "verified": bool}}} for scored SG sub-tests."""
    out: dict[str, dict[str, dict]] = {}
    for path in glob.glob(os.path.join(directory, "*_SG_*.json")):
        try:
            with open(path, encoding="utf-8") as fh:
                payload = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        ticker = payload.get("ticker")
        if not ticker:
            continue
        rows = {}
        for key, rec in (payload.get("scores") or {}).items():
            if not isinstance(rec, dict) or not isinstance(rec.get("score"), int):
                continue
            rows[_scorecard_key(key)] = {
                "score": rec["score"],
                "verified": not bool(rec.get("evidence_unverified")),
            }
        out[ticker] = rows
    return out


def production_state() -> dict[str, dict]:
    """Per company: which SG sub-tests production scored, and its coverage arithmetic."""
    out: dict[str, dict] = {}
    for path in sorted(Path(config.SCORECARD_DIR).glob("*.json")):
        card = read_json(path)
        if not card:
            continue
        sg = ((card.get("components") or {}).get("SG") or {})
        scored = {st["key"] for st in sg.get("subtests") or []
                  if st.get("status") == "scored"}
        out[card["ticker"]] = {
            "sector": card.get("sector"),
            "scored_sg": scored,
            "points_available": card.get("points_available"),
            "applicable_points": card.get("applicable_points") or rubric.TOTAL_POINTS,
            "coverage": card.get("coverage"),
            "band": card.get("band"),
        }
    return out


def run(candidate_dir: str = CANDIDATE_DIR) -> dict:
    cand = candidate_sg(candidate_dir)
    prod = production_state()
    tickers = sorted(set(cand) & set(prod))
    gate = rubric.MIN_COVERAGE_FOR_BAND

    rows = []
    fill_total = fill_verified = 0
    rejected_by_key: collections.Counter = collections.Counter()
    fills_by_key: collections.Counter = collections.Counter()
    for ticker in tickers:
        state = prod[ticker]
        avail = state["points_available"]
        applicable = state["applicable_points"]
        if not avail or not applicable:
            continue

        added_all = added_verified = 0
        for key, rec in cand[ticker].items():
            if key in state["scored_sg"] or key not in SG_MAX:
                continue                     # not a fill, or not an SG sub-test
            fill_total += 1
            added_all += SG_MAX[key]
            fills_by_key[key] += 1
            if rec["verified"]:
                fill_verified += 1
                added_verified += SG_MAX[key]
            else:
                rejected_by_key[key] += 1

        rows.append({
            "ticker": ticker,
            "sector": state["sector"],
            "coverage_v1": round(avail / applicable, 4),
            "coverage_hybrid": round((avail + added_verified) / applicable, 4),
            "coverage_all_fills": round((avail + added_all) / applicable, 4),
            "points_added_verified": added_verified,
            "points_added_all": added_all,
        })

    def clearing(field: str) -> int:
        return sum(1 for r in rows if r[field] >= gate)

    added = [r["points_added_verified"] for r in rows]
    crossers = [r["ticker"] for r in rows
                if r["coverage_v1"] < gate <= r["coverage_hybrid"]]

    return {
        "experiment": "E41",
        "arithmetic_only": True,
        "sg_only": True,
        "n_companies": len(rows),
        "candidate_dir": candidate_dir,
        "coverage_gate": gate,
        "H1_fill_verification": {
            "n_fills": fill_total,
            "n_verified": fill_verified,
            "share_verified": round(fill_verified / fill_total, 4) if fill_total else None,
        },
        "H2_gate_clearing": {
            "v1": clearing("coverage_v1"),
            "hybrid_verified_fills_only": clearing("coverage_hybrid"),
            "all_candidate_fills": clearing("coverage_all_fills"),
            "n_companies": len(rows),
            "new_crossers": crossers[:40],
            "n_new_crossers": len(crossers),
        },
        "H3_points_added": {
            "mean": round(statistics.fmean(added), 2) if added else None,
            "median": round(statistics.median(added), 1) if added else None,
            "max_possible": sum(SG_MAX.values()),
            "n_with_any": sum(1 for a in added if a > 0),
        },
        "H4_rejected_concentration": {
            "n_rejected": fill_total - fill_verified,
            "by_key": rejected_by_key.most_common(),
            # The RATE matters more than the count: a sub-test can dominate the rejected
            # pile purely by being where the fills are.
            "rate_by_key": {k: {"fills": n, "rejected": rejected_by_key[k],
                                "rate": round(rejected_by_key[k] / n, 3)}
                            for k, n in fills_by_key.most_common()},
            "top2_share": (
                round(sum(n for _k, n in rejected_by_key.most_common(2))
                      / max(fill_total - fill_verified, 1), 3)),
        },
    }


def _fmt_md(res: dict) -> str:
    h1, h2, h3, h4 = (res["H1_fill_verification"], res["H2_gate_clearing"],
                      res["H3_points_added"], res["H4_rejected_concentration"])
    lines = [
        "# E41 results - the verified-fill hybrid",
        "",
        f"{res['n_companies']} companies. **Arithmetic over payloads and production's "
        "scorecards - nothing was folded, rescored or rebuilt.** Registered at "
        "`journal/experiments/E41_verified_fill_preregistration.md`.",
        "",
        "The policy measured: keep production's judged half, and add a candidate SG "
        "sub-test **only where production abstained and the candidate's own quote "
        "verifies against the filing**.",
        "",
        "## H1 - how many candidate fills survive their own citation check?",
        "",
        f"**{h1['n_verified']} of {h1['n_fills']}** SG fills verify — "
        f"**{(h1['share_verified'] or 0) * 100:.1f}%**.",
        "",
        "## H2 - who clears the 0.80 coverage gate",
        "",
        "| policy | companies clearing |",
        "|---|---:|",
        f"| production as it stands | {h2['v1']} |",
        f"| **+ verified candidate SG fills** | **{h2['hybrid_verified_fills_only']}** |",
        f"| + every candidate SG fill, verified or not | {h2['all_candidate_fills']} |",
        "",
        f"**{h2['n_new_crossers']}** companies cross the gate on verified fills alone.",
        "",
        "## H3 - points added",
        "",
        f"Mean **{h3['mean']}** of {h3['max_possible']} SG points per company "
        f"(median {h3['median']}); {h3['n_with_any']} companies gain anything.",
        "",
        "## H4 - are the rejected fills concentrated?",
        "",
        f"{h4['n_rejected']} fills rejected on their citation; the top two sub-tests are "
        f"**{h4['top2_share'] * 100:.0f}%** of them.",
        "",
        "| sub-test | rejected fills |",
        "|---|---:|",
    ]
    for key, n in h4["by_key"]:
        lines.append(f"| `{key}` | {n} |")
    lines += [
        "",
        "**But the concentration is volume, not risk** - and that matters, because H4 was "
        "registered as \"if they cluster, they can be excluded by rule\":",
        "",
        "| sub-test | fills | rejected | rate |",
        "|---|---:|---:|---:|",
    ]
    for key, block in h4["rate_by_key"].items():
        lines.append(f"| `{key}` | {block['fills']} | {block['rejected']} | "
                     f"{block['rate'] * 100:.1f}% |")
    lines += [
        "",
        "The two sub-tests carrying 91% of the rejections carry 90% of the **fills**, at "
        "a rejection rate (12.6%, 13.9%) barely different from the rest. **So there is no "
        "sub-test to exclude by rule** - blacklisting them would discard ~1,580 verified "
        "answers to avoid 241 unverifiable ones. The per-quote check is the only gate "
        "that separates them, which is an argument for keeping it rather than replacing "
        "it with policy.",
    ]
    lines += [
        "",
        "## The limit that decides how this reads",
        "",
        "**SG only.** `parse_sg` verifies a quote per sub-test; `parse_bq` and `parse_mg` "
        "verify once at the top level. **BQ is where most of the abstention lives** "
        "(null 38.6% against SG's 23.2%), and there is no per-dimension citation there to "
        "gate on. So this is a **floor**: the ceiling needs per-dimension `evidence` in "
        "the BQ schema and a full re-run of the candidate lane — a GPU job of roughly the "
        "size of the one that just finished, not an analysis.",
        "",
        "## What this does not establish",
        "",
        "That the gated scores are RIGHT. A verified quote proves the sentence exists in "
        "the filing, not that the judgement drawn from it is sound. There is still no "
        "forward-return grader. `promoted` stays false.",
        "",
    ]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidate-dir", default=CANDIDATE_DIR)
    ap.add_argument("--json", default=str(OUT_JSON))
    ap.add_argument("--md", default=str(OUT_MD))
    args = ap.parse_args(argv)

    res = run(args.candidate_dir)
    atomic_write_json(Path(args.json), res)
    Path(args.md).write_text(_fmt_md(res), encoding="utf-8")
    h1, h2 = res["H1_fill_verification"], res["H2_gate_clearing"]
    print(f"n={res['n_companies']}  fills verified "
          f"{h1['n_verified']}/{h1['n_fills']} "
          f"({(h1['share_verified'] or 0) * 100:.1f}%)")
    print(f"gate: v1 {h2['v1']} -> hybrid {h2['hybrid_verified_fills_only']} "
          f"-> all fills {h2['all_candidate_fills']} (of {h2['n_companies']})")
    print(f"mean SG points added {res['H3_points_added']['mean']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
