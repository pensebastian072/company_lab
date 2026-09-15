"""E37 - the 46 downgrades, and the v1/v2 comparison on common support.

Registered at `journal/experiments/E37_downgrades_preregistration.md`, including
amendment 1, which is the thing to read first: `score` is

    100 * (points_earned - EN_earned) / (TOTAL_POINTS - EN_max)      # /92, FIXED

so a `NO_DATA` sub-test contributes nothing to the numerator and nothing to the
denominator. **Filling an abstention can never lower a score.** Every downgrade is
therefore a genuine loss of earned points, and the whole job of this module is to say
which of three places it came from:

  1. a sub-test SCORED in both lanes, lower in v2   -> judgement disagreement
  2. a sub-test SCORED -> NULL                      -> a schema-constrained lane abstaining
  3. the measured half moving between the two folds -> not the model at all

**Common support** is the format-free comparison: recompute both lanes over only the
sub-tests *both* lanes scored. Nothing can enter one numerator and not the other, so what
is left is disagreement and nothing else.

Nothing here changes a score, and nothing here can say which lane is *right* - there is no
forward-return grader in this repo (hard rule 1).

    python -m clab.research.e37_downgrades \
        --v2-parquet    D:\\company_lab_data\\e37_snapshot\\v2_scores.parquet \
        --v2-scorecards D:\\company_lab_data\\e37_snapshot\\v2_scorecards
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
from pathlib import Path

from .. import config
from ..net import atomic_write_json, read_json
from ..scoring import rubric

OUT_JSON = config.JOURNAL_DIR / "experiments" / "E37_results.json"
OUT_MD = config.JOURNAL_DIR / "experiments" / "E37_results.md"

#: EN is excluded from `score` (E21), so every points figure here is ex-entry to stay on
#: the same basis as the column the workbook ranks on.
ENTRY_COMPONENT = "EN"
JUDGED = ("SG", "BQ", "MG")
#: The registered threshold for "kept its drop" in C1.
DROP_POINTS = 3


#: Input keys whose value depends on the COHORT that has been folded, not on the company.
#: A partial universe changes peer medians, peer counts and sector percentiles, so a
#: measured sub-test can move without one number about the company changing.
COHORT_INPUT_KEYS = ("peer_median", "n_peers", "sector_pctile", "sector_n",
                     "sector_median", "peer_n", "n_sector")


def _split_inputs(inputs: dict) -> tuple[dict, dict]:
    """(own, cohort) - the company's own numbers vs the ones the cohort supplies."""
    own, cohort = {}, {}
    for k, v in (inputs or {}).items():
        (cohort if any(c in k for c in COHORT_INPUT_KEYS) else own)[k] = v
    return own, cohort


def _differs(a: dict, b: dict, rel: float = 1e-6) -> bool:
    """Value-wise comparison that treats floats within `rel` as equal."""
    for k in set(a) | set(b):
        va, vb = a.get(k), b.get(k)
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
            scale = max(abs(va), abs(vb), 1.0)
            if abs(va - vb) > rel * scale:
                return True
        elif va != vb:
            return True
    return False


def classify_measured_move(sa: dict, sb: dict) -> str:
    """Why did an AUDITABLE sub-test move between two lanes reading the same cache?

    'vintage'     - a number about the company itself changed (a refreshed feed).
    'cohort'      - only peer/sector-derived inputs changed: the partial universe.
    'unexplained' - identical inputs, different points. That would be a code or threshold
                    difference between the lanes and is the one worth chasing.
    """
    own_a, coh_a = _split_inputs(sa.get("inputs"))
    own_b, coh_b = _split_inputs(sb.get("inputs"))
    if _differs(own_a, own_b):
        return "vintage"
    if _differs(coh_a, coh_b):
        return "cohort"
    return "unexplained"


def _score_denominator() -> int:
    """/92 - the fixed divisor `selection_score` uses. Read from the rubric, never typed
    in, so a framework change cannot leave this module quietly on the old scale."""
    return rubric.TOTAL_POINTS - rubric.COMPONENTS[ENTRY_COMPONENT][1]


def load_subtests(path: Path) -> dict:
    """One scorecard -> {subtest_key: {...}} plus the company header.

    `effective` is the point value after any override; `earned` is what the scorer said.
    The composite sums `effective` and only for SCORED, so that is what is read here.
    """
    card = read_json(path)
    if not card:
        return {}
    subtests = {}
    for code, comp in (card.get("components") or {}).items():
        for st in comp.get("subtests") or []:
            key = st.get("key")
            if not key:
                continue
            status = str(st.get("status") or "").lower()
            eff = st.get("effective")
            if eff is None:
                eff = st.get("earned")
            subtests[key] = {
                "component": code,
                "status": status,
                "points": int(eff or 0) if status == "scored" else 0,
                "max_points": int(st.get("max_points") or 0),
                "scored": status == "scored",
                "model": ((st.get("provenance") or {}).get("model") or ""),
                "rationale": st.get("rationale"),
                "inputs": st.get("inputs") or {},
            }
    return {
        "ticker": card.get("ticker"),
        "cik": card.get("cik"),
        "name": card.get("name"),
        "sector": card.get("sector"),
        "score": card.get("score"),
        "band": card.get("band"),
        "band_raw": card.get("band_raw"),
        "coverage": card.get("coverage"),
        "subtests": subtests,
    }


def index_scorecards(directory: Path) -> dict[str, dict]:
    """{ticker: parsed scorecard}. Files are `<CIK>_<TICKER>.json`; `history/` is skipped
    because it holds prior readings of the same company under the same ticker."""
    out: dict[str, dict] = {}
    for path in sorted(Path(directory).glob("*.json")):
        parsed = load_subtests(path)
        ticker = parsed.get("ticker")
        if ticker:
            out[ticker] = parsed
    return out


def compare_company(v1: dict, v2: dict) -> dict:
    """Decompose one company's movement into the three sources amendment 1 names."""
    a, b = v1["subtests"], v2["subtests"]
    keys = sorted(set(a) | set(b))

    transitions: list[dict] = []
    measured_delta = 0            # ex-entry, measured components only
    judged_agree_delta = 0        # scored in both lanes
    judged_fill_delta = 0         # NULL -> SCORED
    judged_lost_delta = 0         # SCORED -> NULL
    common_v1 = common_v2 = 0     # common-support points, ex-entry

    for key in keys:
        sa, sb = a.get(key), b.get(key)
        if sa is None or sb is None:
            # A sub-test present in one framework build and not the other. Both lanes run
            # the same rubric, so this should not happen; it is recorded rather than
            # silently dropped.
            transitions.append({"key": key, "kind": "absent_one_side",
                                "component": (sa or sb or {}).get("component", "?")})
            continue
        comp = sa["component"]
        if comp == ENTRY_COMPONENT:
            continue                      # not in `score` at all
        delta = sb["points"] - sa["points"]

        if sa["scored"] and sb["scored"]:
            common_v1 += sa["points"]
            common_v2 += sb["points"]
            if delta:
                kind = "disagree"
                if comp in JUDGED:
                    judged_agree_delta += delta
                else:
                    measured_delta += delta
                tr = {
                    "key": key, "component": comp, "kind": kind,
                    "v1": sa["points"], "v2": sb["points"], "max": sa["max_points"],
                    "delta": delta,
                }
                if comp not in JUDGED:
                    tr["why"] = classify_measured_move(sa, sb)
                transitions.append(tr)
            continue

        if not sa["scored"] and sb["scored"]:
            kind = "fill"
            if comp in JUDGED:
                judged_fill_delta += delta
            else:
                measured_delta += delta
        elif sa["scored"] and not sb["scored"]:
            kind = "lost"
            if comp in JUDGED:
                judged_lost_delta += delta
            else:
                measured_delta += delta
        else:
            continue                      # unscored in both: no points either way
        tr = {
            "key": key, "component": comp, "kind": kind,
            "v1_status": sa["status"], "v2_status": sb["status"],
            "v1": sa["points"], "v2": sb["points"], "max": sa["max_points"],
            "delta": delta,
        }
        if comp not in JUDGED:
            tr["why"] = classify_measured_move(sa, sb)
        transitions.append(tr)

    denom = _score_denominator()
    return {
        "ticker": v1["ticker"],
        "name": v1.get("name"),
        "sector": v1.get("sector"),
        "score_v1": v1.get("score"),
        "score_v2": v2.get("score"),
        "score_delta": (v2.get("score") or 0) - (v1.get("score") or 0),
        "coverage_v1": v1.get("coverage"),
        "coverage_v2": v2.get("coverage"),
        "coverage_delta": round((v2.get("coverage") or 0) - (v1.get("coverage") or 0), 4),
        "band_v1": v1.get("band"),
        "band_v2": v2.get("band"),
        "measured_points_delta": measured_delta,
        "judged_disagree_delta": judged_agree_delta,
        "judged_fill_delta": judged_fill_delta,
        "judged_lost_delta": judged_lost_delta,
        # Common support, expressed in the same 0-100 units as `score`.
        "common_points_v1": common_v1,
        "common_points_v2": common_v2,
        "common_score_delta": round(100.0 * (common_v2 - common_v1) / denom, 2),
        "n_common_subtests": sum(
            1 for k in keys
            if a.get(k) and b.get(k) and a[k]["scored"] and b[k]["scored"]
            and a[k]["component"] != ENTRY_COMPONENT
        ),
        "transitions": transitions,
    }


def run(v2_parquet: Path, v2_scorecards: Path, v1_scorecards: Path | None = None) -> dict:
    v1_dir = Path(v1_scorecards or config.SCORECARD_DIR)
    v1 = index_scorecards(v1_dir)
    v2 = index_scorecards(Path(v2_scorecards))
    common = sorted(set(v1) & set(v2))

    rows = [compare_company(v1[t], v2[t]) for t in common]
    downgrades = sorted((r for r in rows if r["score_delta"] < 0),
                        key=lambda r: r["score_delta"])
    upgrades = [r for r in rows if r["score_delta"] > 0]

    # C1 - of the downgrades, how many keep a >= DROP_POINTS drop on common support
    c1_kept = [r for r in downgrades if r["common_score_delta"] <= -DROP_POINTS]

    # C2 - any measured-half movement at all
    c2_moved = [r for r in rows if r["measured_points_delta"] != 0]
    # ...and WHERE it moved. The measured half is supposed to be identical between the
    # lanes; it is not, and the breakdown is the difference between "the data moved" and
    # "the peer set moved", which are not the same problem.
    # PINNED, deliberately. E37 ran against rubric.QUANT_COMPONENTS as it stood then -
    # FE/BS/VA/ER/EN, with MG excluded because MG was still (wrongly) listed as judged.
    # V3 P0 corrected that list to MEASURED_COMPONENTS, which adds MG. Pointing this
    # study at the corrected constant would silently change numbers already written to
    # E37_results.json. A settled study keeps the definition it ran under.
    _E37_MEASURED_AS_RUN = ("FE", "BS", "VA", "ER", "EN")
    measured_tr = [t for r in rows for t in r["transitions"]
                   if t.get("component") in _E37_MEASURED_AS_RUN
                   and t.get("component") != ENTRY_COMPONENT]
    measured_by_key: dict[str, dict] = {}
    measured_why: collections.Counter = collections.Counter()
    for t in measured_tr:
        d = measured_by_key.setdefault(t["key"], {"n": 0, "sum_delta": 0,
                                                  "kinds": collections.Counter(),
                                                  "why": collections.Counter()})
        d["n"] += 1
        d["sum_delta"] += t.get("delta", 0)
        d["kinds"][t.get("kind", "?")] += 1
        d["why"][t.get("why", "?")] += 1
        measured_why[t.get("why", "?")] += 1
    unexplained = [(r["ticker"], t) for r in rows for t in r["transitions"]
                   if t.get("why") == "unexplained"]

    # C3 - SCORED -> NULL, over every comparable company
    lost = [(r["ticker"], t) for r in rows for t in r["transitions"]
            if t.get("kind") == "lost"]
    lost_judged = [(tk, t) for tk, t in lost if t["component"] in JUDGED]
    lost_measured = [(tk, t) for tk, t in lost if t["component"] not in JUDGED]
    n_scored_v1 = sum(
        1 for t in common
        for st in v1[t]["subtests"].values()
        if st["scored"] and st["component"] != ENTRY_COMPONENT
    )

    # C4 - is the disagreement concentrated in particular sub-tests?
    disagree = [(r["ticker"], t) for r in rows for t in r["transitions"]
                if t.get("kind") == "disagree"]
    by_key: collections.Counter = collections.Counter(t["key"] for _, t in disagree)
    signed_by_key: dict[str, dict] = {}
    for _, t in disagree:
        d = signed_by_key.setdefault(t["key"], {"n": 0, "sum_delta": 0, "n_down": 0,
                                                "component": t["component"]})
        d["n"] += 1
        d["sum_delta"] += t["delta"]
        d["n_down"] += 1 if t["delta"] < 0 else 0

    # C5 - the whole-set mean on common support
    cs_deltas = [r["common_score_delta"] for r in rows]
    raw_deltas = [r["score_delta"] for r in rows]
    denom = _score_denominator()

    return {
        "experiment": "E37",
        "n_comparable": len(common),
        "n_v1_scorecards": len(v1),
        "n_v2_scorecards": len(v2),
        "v2_parquet": str(v2_parquet),
        "v2_scorecards": str(v2_scorecards),
        "score_denominator": _score_denominator(),
        "raw": {
            "mean_delta": round(statistics.fmean(raw_deltas), 2) if raw_deltas else None,
            "n_up": len(upgrades),
            "n_down": len(downgrades),
            "n_flat": len(rows) - len(upgrades) - len(downgrades),
        },
        # Where the raw +N actually comes from. The four parts are disjoint by
        # construction and sum to the ex-entry points delta, so this is the whole story
        # of the headline rather than a re-description of it.
        "decomposition_mean_points": {
            part: round(statistics.fmean(r[part] for r in rows), 3) if rows else None
            for part in ("measured_points_delta", "judged_disagree_delta",
                         "judged_fill_delta", "judged_lost_delta")
        } | {
            "total": round(statistics.fmean(
                r["measured_points_delta"] + r["judged_disagree_delta"]
                + r["judged_fill_delta"] + r["judged_lost_delta"] for r in rows), 3)
            if rows else None,
            "in_score_units": {
                part: round(100.0 * statistics.fmean(r[part] for r in rows) / denom, 2)
                for part in ("measured_points_delta", "judged_disagree_delta",
                             "judged_fill_delta", "judged_lost_delta")
            } if rows else None,
        },
        "C1_downgrades_kept_on_common_support": {
            "n_downgrades": len(downgrades),
            "threshold_points": DROP_POINTS,
            "n_kept": len(c1_kept),
            "share": round(len(c1_kept) / len(downgrades), 4) if downgrades else None,
        },
        "C2_measured_half_moved": {
            "n": len(c2_moved),
            "share": round(len(c2_moved) / len(rows), 4) if rows else None,
            "worst": sorted(
                ({"ticker": r["ticker"], "delta": r["measured_points_delta"]}
                 for r in c2_moved),
                key=lambda d: abs(d["delta"]), reverse=True)[:15],
            "total_points": sum(r["measured_points_delta"] for r in rows),
            "why": dict(measured_why),
            "unexplained_examples": [
                {"ticker": tk, "key": t["key"], "v1": t["v1"], "v2": t["v2"]}
                for tk, t in unexplained[:15]
            ],
            "by_key": [
                {"key": k, "n": v["n"], "sum_delta": v["sum_delta"],
                 "kinds": dict(v["kinds"]), "why": dict(v["why"])}
                for k, v in sorted(measured_by_key.items(),
                                   key=lambda kv: kv[1]["n"], reverse=True)
            ],
        },
        "C3_scored_to_null": {
            "n": len(lost),
            "n_judged": len(lost_judged),
            "n_measured": len(lost_measured),
            "n_scored_subtests_v1": n_scored_v1,
            "share_of_scored": round(len(lost) / n_scored_v1, 5) if n_scored_v1 else None,
            "by_key": collections.Counter(t["key"] for _, t in lost).most_common(15),
            "companies": sorted({tk for tk, _ in lost}),
            "judged_companies": sorted({tk for tk, _ in lost_judged}),
            # A company whose whole judged component vanished is a generation failure, not
            # a judgement: counted separately so the two cannot be read as one number.
            "judged_points_lost_by_company": sorted(
                (
                    {"ticker": tk,
                     "points": sum(-t["delta"] for t2k, t in lost_judged if t2k == tk)}
                    for tk in sorted({tk for tk, _ in lost_judged})
                ),
                key=lambda d: d["points"], reverse=True)[:20],
        },
        "C4_disagreement_concentration": {
            "n_disagreements": len(disagree),
            "n_distinct_keys": len(by_key),
            "top_keys": [
                {"key": k, "component": v["component"], "n": v["n"],
                 "mean_delta": round(v["sum_delta"] / v["n"], 2),
                 "share_down": round(v["n_down"] / v["n"], 3)}
                for k, v in sorted(signed_by_key.items(),
                                   key=lambda kv: kv[1]["n"], reverse=True)[:20]
            ],
        },
        "C5_common_support_mean": {
            "mean": round(statistics.fmean(cs_deltas), 3) if cs_deltas else None,
            "median": round(statistics.median(cs_deltas), 3) if cs_deltas else None,
            "n_up": sum(1 for d in cs_deltas if d > 0),
            "n_down": sum(1 for d in cs_deltas if d < 0),
            "n_flat": sum(1 for d in cs_deltas if d == 0),
        },
        "downgrades": [
            {k: v for k, v in r.items() if k != "transitions"} | {
                "top_losses": sorted(
                    (t for t in r["transitions"] if t.get("delta", 0) < 0),
                    key=lambda t: t["delta"])[:6],
            }
            for r in downgrades
        ],
    }


def _fmt_md(res: dict) -> str:
    c1 = res["C1_downgrades_kept_on_common_support"]
    c2 = res["C2_measured_half_moved"]
    c3 = res["C3_scored_to_null"]
    c4 = res["C4_disagreement_concentration"]
    c5 = res["C5_common_support_mean"]
    raw = res["raw"]
    lines = [
        "# E37 results - the downgrades, and the comparison on common support",
        "",
        f"n = {res['n_comparable']} comparable companies  ·  score denominator "
        f"/{res['score_denominator']} (fixed)  ·  registered at "
        "`journal/experiments/E37_downgrades_preregistration.md`",
        "",
        "## Headline",
        "",
        "| | raw | on common support |",
        "|---|---:|---:|",
        f"| mean score delta | {raw['mean_delta']:+} | {c5['mean']:+} |",
        f"| companies up | {raw['n_up']} | {c5['n_up']} |",
        f"| companies down | {raw['n_down']} | {c5['n_down']} |",
        f"| companies unchanged | {raw['n_flat']} | {c5['n_flat']} |",
        "",
        "Common support = only the sub-tests **both lanes actually scored**. No sub-test "
        "can enter one numerator and not the other, so what is left is disagreement.",
        "",
        "## Where the headline comes from",
        "",
        "| part | mean points | in score units |",
        "|---|---:|---:|",
    ]
    dec = res["decomposition_mean_points"]
    su = dec["in_score_units"]
    for part, label in (("judged_fill_delta", "judged: abstention filled (NULL -> SCORED)"),
                        ("judged_disagree_delta", "judged: disagreement (scored in both)"),
                        ("judged_lost_delta", "judged: new abstention (SCORED -> NULL)"),
                        ("measured_points_delta", "measured half (should be zero)")):
        lines.append(f"| {label} | {dec[part]:+} | {su[part]:+} |")
    lines += [
        f"| **total** | **{dec['total']:+}** | **{raw['mean_delta']:+}** |",
        "",
        "The four parts are disjoint and sum to the ex-entry points delta. Score units "
        f"are points/{res['score_denominator']} x 100 - the same scale the workbook ranks "
        "on.",
        "",
        "## Registered criteria",
        "",
        f"**C1** - of {c1['n_downgrades']} downgrades, **{c1['n_kept']}** keep a drop of "
        f"at least {c1['threshold_points']} points on common support "
        f"({(c1['share'] or 0) * 100:.1f}%).",
        "",
        f"**C2** - measured-half movement in **{c2['n']}** of {res['n_comparable']} "
        f"companies ({(c2['share'] or 0) * 100:.1f}%), net "
        f"{c2['total_points']:+} points. The measured half is supposed to be identical "
        "between the lanes.",
        "",
        "Why it moved, over every measured transition: "
        + ", ".join(f"**{v} {k}**" for k, v in sorted(c2["why"].items(),
                                                      key=lambda kv: -kv[1]))
        + ". `cohort` = only peer/sector-derived inputs changed, so the *partial "
          "universe* moved the score and not one number about the company; `vintage` = a "
          "company number changed between the folds; `unexplained` = identical inputs, "
          "different points.",
        "",
        "| measured sub-test | n moved | net points | kinds | why |",
        "|---|---:|---:|---|---|",
    ]
    for k in c2["by_key"][:12]:
        kinds = ", ".join(f"{kk} {vv}" for kk, vv in sorted(k["kinds"].items()))
        why = ", ".join(f"{kk} {vv}" for kk, vv in sorted(k["why"].items()))
        lines.append(f"| `{k['key']}` | {k['n']} | {k['sum_delta']:+} | {kinds} | {why} |")
    lines += [
        "",
        f"**C3** - `SCORED -> NULL`: **{c3['n']}** transitions over "
        f"{c3['n_scored_subtests_v1']} sub-tests the incumbent scored "
        f"({(c3['share_of_scored'] or 0) * 100:.2f}%), across {len(c3['companies'])} "
        f"companies - **{c3['n_measured']}** in the measured half and "
        f"**{c3['n_judged']}** in the judged half "
        f"({len(c3['judged_companies'])} companies).",
        "",
        f"**C4** - **{c4['n_disagreements']}** sub-test disagreements over "
        f"{c4['n_distinct_keys']} distinct keys.",
        "",
        "| sub-test | component | n | mean delta | share down |",
        "|---|---|---:|---:|---:|",
    ]
    for k in c4["top_keys"]:
        lines.append(f"| `{k['key']}` | {k['component']} | {k['n']} | {k['mean_delta']:+} "
                     f"| {k['share_down'] * 100:.0f}% |")
    lines += [
        "",
        f"**C5** - mean common-support delta **{c5['mean']:+}** points "
        f"(median {c5['median']:+}).",
        "",
        "## The downgrades",
        "",
        "| ticker | score | common support | measured | judged disagree | judged lost | "
        "coverage |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in res["downgrades"][:60]:
        lines.append(
            f"| {r['ticker']} | {r['score_v1']} -> {r['score_v2']} "
            f"({r['score_delta']:+}) | {r['common_score_delta']:+} | "
            f"{r['measured_points_delta']:+} | {r['judged_disagree_delta']:+} | "
            f"{r['judged_lost_delta']:+} | {r['coverage_delta']:+.3f} |")
    lines += [
        "",
        "Point columns are raw framework points (ex-entry); `common support` is in "
        "`score` units.",
        "",
        "## Reading",
        "",
        f"**Half of E36's +8.9 is not coverage.** {su['judged_fill_delta']:+} of it is "
        "the candidate scoring where the incumbent abstained - the artefact E36 named - "
        f"but {su['judged_disagree_delta']:+} of it is the candidate awarding **more "
        "points on the very sub-tests both lanes answered**. That half survives common "
        "support, so it is not the schema making a missing key impossible. It is the "
        "candidate being more generous on the same evidence.",
        "",
        f"**It is one question, mostly.** `bq_moat` moves in "
        f"{c4['top_keys'][0]['n'] if c4['top_keys'] else 0} companies at a mean of "
        f"{c4['top_keys'][0]['mean_delta'] if c4['top_keys'] else 0:+} points of a "
        f"{15}-point sub-test, and BQ is 15 of the framework's 94. A single question "
        "carries most of the disagreement half.",
        "",
        "**The schema did not abolish abstention, it moved it.** The judged half still "
        f"lost {c3['n_judged']} scored sub-tests across "
        f"{len(c3['judged_companies'])} companies - not one dimension at a time, but a "
        "whole component failing to generate, which is why the worst downgrades are "
        "large and lopsided.",
        "",
        "**Common support is a selected subset, and selected by the incumbent.** It "
        "conditions on qwen having scored the sub-test, and qwen abstained most where "
        "the evidence was thinnest. So the disagreement measured here lives on the "
        "*easier* items, and there is no reason to assume it is the same size on the "
        "ones the incumbent refused.",
        "",
        "## What this does not establish",
        "",
        "Which lane is *right*. There is no forward-return grader in this repo, so a "
        "disagreement is a disagreement and nothing more - a more generous scorer is not "
        "a better one. E36's confound is unrepaired: the candidate still ran "
        "schema-constrained at 2,500 tokens against an unconstrained 700, so its "
        "leniency could be either the model or the budget. **The qwen-structured control "
        "is still the only thing that separates them.** `promoted` stays false.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--v2-parquet", required=True)
    ap.add_argument("--v2-scorecards", required=True)
    ap.add_argument("--v1-scorecards", default=None)
    ap.add_argument("--json", default=str(OUT_JSON))
    ap.add_argument("--md", default=str(OUT_MD))
    args = ap.parse_args()

    res = run(Path(args.v2_parquet), Path(args.v2_scorecards), args.v1_scorecards)
    atomic_write_json(Path(args.json), res)
    Path(args.md).write_text(_fmt_md(res), encoding="utf-8")
    c5 = res["C5_common_support_mean"]
    print(f"n={res['n_comparable']}  raw mean {res['raw']['mean_delta']:+}  "
          f"common-support mean {c5['mean']:+}")
    print(f"downgrades {res['raw']['n_down']}, kept on common support "
          f"{res['C1_downgrades_kept_on_common_support']['n_kept']}")
    print(f"wrote {args.json} and {args.md}")


if __name__ == "__main__":
    main()
