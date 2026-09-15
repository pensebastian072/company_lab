"""E36 - compare the two judged halves over the SAME companies.

Reads the incumbent's payloads from the production qual cache and the candidate's from
the v2 lane's own cache, matches them by (CIK, component), and answers the four
registered criteria in `journal/experiments/E36_v2_lane_preregistration.md`.

The one that decides the experiment is C2. Abstaining less is only good news if the scores
produced instead are justified, and the containment check cannot tell: a page header is
verbatim pack text, so it verifies. C2 measures whether the rationale is a *judgement* or
a *header*, for both lanes, on the same filings.

Usage:
    python -m clab.research.e36_compare --v2-dir D:\\company_lab_data\\qual_lfm25
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import statistics
from pathlib import Path

from .. import config
from ..net import atomic_write_json, read_json
from ..scoring import rubric

OUT_JSON = config.JOURNAL_DIR / "experiments" / "E36_results.json"
OUT_MD = config.JOURNAL_DIR / "experiments" / "E36_results.md"

#: E12's four watched moat dimensions - the ones the incumbent abstains on most
WATCHED = ("network_effects", "manufacturing_complexity",
           "data_advantages", "economies_of_scale")

#: The evidence pack's header line: "<company> | <form> | <page>". A rationale that IS
#: one is not a judgement, it is chrome that happens to be verbatim pack text - which is
#: precisely why `_verify_evidence` cannot catch it.
_CHROME = re.compile(r"^[^|]{1,60}\|[^|]{1,40}\|\s*\d+\s*$")
#: rationales that are literally the word null/none/n-a - a defect, not a short sentence
_EMPTY_WORDS = {"", "null", "none", "n/a", "na", "-", "not applicable"}
TERSE_MAX_CHARS = 45


def classify_rationale(rationale: str | None) -> str:
    """One of: 'chrome', 'empty', 'terse', 'prose'.

    AMENDED after the first read of v1 data - see E36 amendment 1. The original single
    `is_degenerate` test lumped a short-but-real judgement in with a page header, and on
    the incumbent that is most of the difference: qwen writes terse rationales
    ("Established brand in healthcare equipment.", 41 chars) which ARE judgements, and it
    also emits the literal string "null" beside a score of 5, which is not. Scoring those
    the same produced a 40.4% "degenerate" rate for qwen that was mostly an artefact of
    the character threshold.

    So C2 counts **chrome + empty** only. `terse` is reported separately as description,
    because "this model writes shorter rationales" is a real difference and not a defect.
    """
    text = str(rationale or "").strip()
    if text.lower() in _EMPTY_WORDS:
        return "empty"
    if _CHROME.match(text):
        return "chrome"
    return "terse" if len(text) < TERSE_MAX_CHARS else "prose"


def is_degenerate(rationale: str | None) -> bool:
    """C2: a scored sub-test whose rationale carries no judgement at all."""
    return classify_rationale(rationale) in ("chrome", "empty")


def _payloads(qual_dir: Path, component: str) -> dict[str, dict]:
    """Newest payload per CIK for one component, from one lane's cache."""
    best: dict[str, tuple[str, dict]] = {}
    for path in qual_dir.glob(f"*_{component}_*.json"):
        cik = path.name.split("_")[0]
        data = read_json(path)
        if not isinstance(data, dict):
            continue
        stamp = str(data.get("generated_at") or "")
        if cik not in best or stamp > best[cik][0]:
            best[cik] = (stamp, data)
    return {cik: data for cik, (_stamp, data) in best.items()}


def _bucket(payload: dict, component: str) -> dict:
    return payload.get({"SG": "scores", "BQ": "dimensions", "MG": "ceo"}[component]) or {}


def compare_component(v1_dir: Path, v2_dir: Path, component: str) -> dict:
    v1, v2 = _payloads(v1_dir, component), _payloads(v2_dir, component)
    shared = sorted(set(v1) & set(v2))

    stats = {lane: {"n_items": 0, "n_null": 0, "n_degenerate": 0, "n_scored": 0,
                    "n_chrome": 0, "n_empty": 0, "n_terse": 0}
             for lane in ("v1", "v2")}
    per_dim = collections.defaultdict(
        lambda: {"v1_null": 0, "v2_null": 0, "v1_deg": 0, "v2_deg": 0, "n": 0})
    deltas: list[float] = []

    for cik in shared:
        for lane, payload in (("v1", v1[cik]), ("v2", v2[cik])):
            for key, rec in _bucket(payload, component).items():
                if not isinstance(rec, dict):
                    continue
                stats[lane]["n_items"] += 1
                if rec.get("score") is None:
                    stats[lane]["n_null"] += 1
                    per_dim[key][f"{lane}_null"] += 1
                else:
                    stats[lane]["n_scored"] += 1
                    # A degenerate rationale only matters where a SCORE was given: an
                    # abstention has nothing to justify.
                    kind = classify_rationale(rec.get("rationale"))
                    if kind in ("chrome", "empty"):
                        stats[lane]["n_degenerate"] += 1
                        stats[lane][f"n_{kind}"] += 1
                        per_dim[key][f"{lane}_deg"] += 1
                    elif kind == "terse":
                        stats[lane]["n_terse"] += 1
        # score delta where BOTH lanes committed to a number
        b1, b2 = _bucket(v1[cik], component), _bucket(v2[cik], component)
        for key in set(b1) & set(b2):
            r1, r2 = b1.get(key), b2.get(key)
            if not (isinstance(r1, dict) and isinstance(r2, dict)):
                continue
            per_dim[key]["n"] += 1
            if r1.get("score") is not None and r2.get("score") is not None:
                deltas.append(float(r2["score"]) - float(r1["score"]))

    def rate(lane: str, field: str, denom: str) -> float | None:
        d = stats[lane][denom]
        return round(stats[lane][field] / d, 4) if d else None

    return {
        "component": component,
        "companies_compared": len(shared),
        "v1": dict(stats["v1"],
                   null_rate=rate("v1", "n_null", "n_items"),
                   degenerate_rate=rate("v1", "n_degenerate", "n_scored"),
                   terse_rate=rate("v1", "n_terse", "n_scored")),
        "v2": dict(stats["v2"],
                   null_rate=rate("v2", "n_null", "n_items"),
                   degenerate_rate=rate("v2", "n_degenerate", "n_scored"),
                   terse_rate=rate("v2", "n_terse", "n_scored")),
        "mean_score_delta": round(statistics.fmean(deltas), 3) if deltas else None,
        "n_score_pairs": len(deltas),
        "per_key": {k: dict(v) for k, v in sorted(per_dim.items())},
    }


def render(res: dict) -> str:
    exp = res.get("experiment", "E36")
    title = {"E36": "the v2 lane",
             "E38": "the control lane"}.get(exp, "a lane comparison")
    lines = [f"# {exp} results - {title}", ""]
    lines.append(f"as_of {res['as_of']}  ·  incumbent `{res['v1_model']}`  ·  "
                 f"candidate `{res['v2_model']}`")
    lines.append("")
    lines.append(f"Registered at `journal/experiments/{exp}_"
                 + ("v2_lane_preregistration.md" if exp == "E36"
                    else "control_lane_preregistration.md")
                 + "`. The probe's 10 companies are excluded - they were read before the "
                   "criteria were fixed.")
    lines.append("")

    lines.append("## C1 + C2 - abstention, and whether it was earned")
    lines.append("")
    lines.append("| component | companies | v1 null | v2 null | v1 degenerate | "
                 "v2 degenerate | mean score delta |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for comp in res["components"]:
        c = res["components"][comp]
        if not c["companies_compared"]:
            continue

        def pct(x):
            return "n/a" if x is None else f"{x:.1%}"

        delta = c["mean_score_delta"]
        delta_txt = "n/a" if delta is None else f"{delta:+.2f}"
        lines.append(
            f"| {comp} | {c['companies_compared']} | {pct(c['v1']['null_rate'])} | "
            f"{pct(c['v2']['null_rate'])} | {pct(c['v1']['degenerate_rate'])} | "
            f"{pct(c['v2']['degenerate_rate'])} | {delta_txt} |")
    lines.append("")
    lines.append("**A degenerate rationale is the pack's header line (`chrome`) or the "
                 "literal word null/none/empty (`empty`), measured identically for both "
                 "lanes.** A short-but-real judgement is `terse` and is NOT counted - "
                 "see amendment 1, where lumping the two produced a 40.4% figure for the "
                 "incumbent that was mostly the character threshold. Degeneracy is "
                 "counted only where a score was actually given: an abstention has "
                 "nothing to justify. `evidence_unverified` is NOT the check here - a "
                 "page header is verbatim pack text, so it verifies.")
    lines.append("")

    bq = res["components"].get("BQ", {})
    if bq.get("per_key"):
        lines.append("## E12's four watched dimensions")
        lines.append("")
        lines.append("| dimension | n | v1 null | v2 null | v1 degen | v2 degen |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for key in WATCHED:
            k = bq["per_key"].get(key)
            if not k:
                continue
            n = max(k["n"], 1)
            lines.append(f"| {key} | {k['n']} | {k['v1_null']/n:.1%} | "
                         f"{k['v2_null']/n:.1%} | {k['v1_deg']/n:.1%} | "
                         f"{k['v2_deg']/n:.1%} |")
        lines.append("")

    lines.append("## What this does and does not establish")
    lines.append("")
    lines.append("Neither judged half has ever been graded against forward returns - "
                 "there is no grader in this repo yet. E36 can say which model abstains "
                 "less and whether the scores it gave instead were justified. It cannot "
                 "say which is *better*. `promoted` stays false.")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--v2-dir", required=True)
    ap.add_argument("--v1-dir", default=str(config.DATA_ROOT / "qual"))
    ap.add_argument("--v2-model", default="LFM2.5-2.6B-Finance")
    ap.add_argument("--v1-model", default="qwen2.5:7b")
    ap.add_argument("--exclude", default="",
                    help="comma-separated tickers to leave out (the probe's ten)")
    ap.add_argument("--print-only", action="store_true")
    # E38 runs this same instrument on a THIRD cache and must not overwrite E36's
    # results with it - the two are different experiments reading different lanes.
    ap.add_argument("--experiment", default="E36")
    ap.add_argument("--json", default=None)
    ap.add_argument("--md", default=None)
    args = ap.parse_args(argv)

    from datetime import datetime, timezone
    v1_dir, v2_dir = Path(args.v1_dir), Path(args.v2_dir)
    if not v2_dir.exists():
        raise SystemExit(f"v2 cache not found: {v2_dir}")

    res = {
        "experiment": args.experiment,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "v1_model": args.v1_model,
        "v2_model": args.v2_model,
        "v1_dir": str(v1_dir),
        "v2_dir": str(v2_dir),
        "components": {c: compare_component(v1_dir, v2_dir, c)
                       for c in rubric.GENERATED_COMPONENTS},
    }
    md = render(res)
    print(md)
    if not args.print_only:
        out_json = Path(args.json) if args.json else OUT_JSON
        out_md = Path(args.md) if args.md else OUT_MD
        atomic_write_json(out_json, res)
        out_md.write_text(md, encoding="utf-8")
        print(f"written: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
