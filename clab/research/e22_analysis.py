"""E22 analysis - is the judgement half stable, and does it say anything new?

Reads `journal/experiments/E22_raw/`, produced by `e22_judgement_backtest.py`.

The registration fixes what this can and cannot decide. R1 (stability) and R3 (agreement)
carry bars, because every company contributes an independent year-over-year pair and
those have real power. R2 and R4 are reported with NO bar: two cross-sections cannot
carry a return claim - the effective sample is nearer n=2 than n=200 - and putting a
threshold on an underpowered test is how a project talks itself into a result.

    python -m clab.research.e22_analysis
"""
from __future__ import annotations

import argparse
import json
import statistics

from .. import config
from ..net import log_stamp, read_json, utc_now_iso
from ..scoring import rubric
from .repair_impact import _spearman

RAW_DIR = config.JOURNAL_DIR / "experiments" / "E22_raw"
#: how far a component may move year over year before it counts as churn (R2)
CHURN = {"SG": 4, "BQ": 2, "MG": 2}


def log(msg: str) -> None:
    print(f"[{log_stamp()}] {msg}", flush=True)


def _scalar(component: str, scores: dict) -> float | None:
    """One comparable number per component per reading.

    SG is a points sum (its sub-tests are worth 2-4 each). BQ and MG are MEANS of what
    was scored, because their counts move with abstention and a sum would conflate "a
    weaker moat" with "fewer dimensions answered" - the exact confusion E12 spent a week
    untangling.
    """
    vals = [v for v in (scores or {}).values() if isinstance(v, (int, float))]
    if not vals:
        return None
    if component == "SG":
        return float(sum(vals))
    return sum(vals) / len(vals)


def _count(scores: dict) -> int:
    return sum(1 for v in (scores or {}).values() if isinstance(v, (int, float)))


def load(raw_dir=None) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8"))
            for p in sorted((raw_dir or RAW_DIR).glob("*.json"))]


def compare(baseline: list[dict], variant: list[dict], component: str = "MG") -> dict:
    """E24's P2: did putting the proxy in MG's pack lift its stability past 0.5?

    Compared on the SAME companies only. A variant run that covered a different set would
    make the two numbers incomparable, and the comparison is the whole point.
    """
    def pairs_for(recs):
        out = {}
        for rec in recs:
            r2 = (rec.get("readings") or {}).get("t_minus_2") or {}
            r1 = (rec.get("readings") or {}).get("t_minus_1") or {}
            if r2.get("error") or r1.get("error"):
                continue
            a = (r2.get("components") or {}).get(component) or {}
            b = (r1.get("components") or {}).get(component) or {}
            if not (a.get("parse_ok") and b.get("parse_ok")):
                continue
            sa, sb = _scalar(component, a.get("scores")), _scalar(component, b.get("scores"))
            if sa is None or sb is None:
                continue
            out[rec["ticker"]] = (sa, sb, _count(a.get("scores")), _count(b.get("scores")))
        return out

    base, var = pairs_for(baseline), pairs_for(variant)
    common = sorted(set(base) & set(var))
    if len(common) < 3:
        return {"component": component, "n_common": len(common),
                "note": "too few companies scored on both sides to compare"}
    rho_b = _spearman([base[t][0] for t in common], [base[t][1] for t in common])
    rho_v = _spearman([var[t][0] for t in common], [var[t][1] for t in common])
    cnt_b = statistics.median([var[t][2] for t in common])
    return {
        "component": component,
        "n_common": len(common),
        "baseline_spearman": rho_b,
        "variant_spearman": rho_v,
        "P2_bar": 0.5,
        "P2_pass": rho_v is not None and rho_v >= 0.5,
        "median_subtests_scored_baseline": statistics.median(
            [base[t][2] for t in common]),
        "median_subtests_scored_variant": cnt_b,
        "companies_only_in_variant": sorted(set(var) - set(base))[:10],
    }


def analyse(recs: list[dict]) -> dict:
    out: dict = {"as_of": utc_now_iso(), "companies": len(recs), "components": {},
                 "readings_failed": 0}
    paired: dict[str, list[tuple]] = {c: [] for c in rubric.GENERATED_COMPONENTS}
    counts: dict[str, list[tuple]] = {c: [] for c in rubric.GENERATED_COMPONENTS}
    parse_fail = {c: 0 for c in rubric.GENERATED_COMPONENTS}

    for rec in recs:
        r2 = (rec.get("readings") or {}).get("t_minus_2") or {}
        r1 = (rec.get("readings") or {}).get("t_minus_1") or {}
        if r2.get("error") or r1.get("error"):
            out["readings_failed"] += 1
            continue
        for comp in rubric.GENERATED_COMPONENTS:
            a = (r2.get("components") or {}).get(comp) or {}
            b = (r1.get("components") or {}).get(comp) or {}
            if not a.get("parse_ok") or not b.get("parse_ok"):
                parse_fail[comp] += 1
                continue
            sa, sb = _scalar(comp, a.get("scores")), _scalar(comp, b.get("scores"))
            if sa is None or sb is None:
                continue
            paired[comp].append((rec["ticker"], sa, sb))
            counts[comp].append((rec["ticker"], _count(a.get("scores")),
                                 _count(b.get("scores"))))

    for comp in rubric.GENERATED_COMPONENTS:
        pairs = paired[comp]
        n = len(pairs)
        rho = _spearman([p[1] for p in pairs], [p[2] for p in pairs]) if n >= 3 else None
        deltas = [abs(p[2] - p[1]) for p in pairs]
        churn = [abs(c[2] - c[1]) for c in counts[comp]]
        bar = CHURN[comp]
        out["components"][comp] = {
            "n_pairs": n,
            "R1_spearman": rho,
            "R1_pass": (rho is not None and rho >= 0.5),
            "median_abs_change": round(statistics.median(deltas), 3) if deltas else None,
            "share_unchanged": round(sum(1 for d in deltas if d == 0) / n, 3) if n else None,
            "R2_share_moving_more_than_bar": (
                round(sum(1 for d in deltas if d > bar) / n, 3) if n else None),
            "R2_bar": bar,
            "median_subtests_scored_t2": (
                statistics.median([c[1] for c in counts[comp]]) if counts[comp] else None),
            "median_subtests_scored_t1": (
                statistics.median([c[2] for c in counts[comp]]) if counts[comp] else None),
            "median_abs_change_in_count": (
                statistics.median(churn) if churn else None),
            "parse_failures": parse_fail[comp],
        }

    # R3: does the judgement half restate the numbers? Compared against TODAY's measured
    # half, which is an approximation - a point-in-time measured score would need the
    # full panel rebuild - and is labelled as one.
    try:
        import pandas as pd
        df = pd.read_parquet(config.SCORES_PARQUET).set_index("ticker")
        rows = []
        for rec in recs:
            r1 = (rec.get("readings") or {}).get("t_minus_1") or {}
            if r1.get("error") or rec["ticker"] not in df.index:
                continue
            qn = df.loc[rec["ticker"], "quant_normalized"]
            parts = []
            for comp in rubric.GENERATED_COMPONENTS:
                c = (r1.get("components") or {}).get(comp) or {}
                s = _scalar(comp, c.get("scores"))
                if s is not None:
                    parts.append(s if comp == "SG" else s * 4)   # crude common scale
            if parts and qn == qn:
                rows.append((sum(parts), float(qn)))
        out["R3_judgement_vs_measured"] = {
            "n": len(rows),
            "spearman": _spearman([r[0] for r in rows], [r[1] for r in rows])
            if len(rows) >= 3 else None,
            "note": "measured half is TODAY's quant_normalized, not point-in-time - an "
                    "approximation, stated rather than hidden",
        }
    except Exception as exc:                                    # noqa: BLE001
        out["R3_judgement_vs_measured"] = {"error": f"{type(exc).__name__}: {exc}"}
    return out


def render(s: dict) -> str:
    def verdict(p):
        return "PASS" if p else "FAIL"

    L = [f"# E22 results - is the judgement half stable? ({s['as_of'][:10]})", "",
         "ADVISORY / SHADOW. This is a RELIABILITY test, not a return test. Two",
         "cross-sections cannot carry a claim about forward returns, so none is made and",
         "no Deflated Sharpe is computed. `promoted` stays false.", "",
         f"{s['companies']} companies, two readings each - the 10-K current a year ago",
         f"and two years ago, with fundamentals as first filed. "
         f"{s['readings_failed']} companies lost a reading and are excluded.", "",
         "## R1 - does a component say the same thing a year later?", "",
         "| component | pairs | Spearman | >= 0.5 | median change | unchanged | parse fails |",
         "|---|---:|---:|---|---:|---:|---:|"]
    for comp, d in s["components"].items():
        L.append(f"| {comp} | {d['n_pairs']} | {d['R1_spearman']} | "
                 f"{verdict(d['R1_pass'])} | {d['median_abs_change']} | "
                 f"{d['share_unchanged']} | {d['parse_failures']} |")
    L += ["", "## R2 - churn, reported with no bar", "",
          "| component | share moving more than the bar | bar | median sub-tests scored "
          "(t-2 -> t-1) | median change in count |", "|---|---:|---:|---|---:|"]
    for comp, d in s["components"].items():
        L.append(f"| {comp} | {d['R2_share_moving_more_than_bar']} | {d['R2_bar']} | "
                 f"{d['median_subtests_scored_t2']} -> "
                 f"{d['median_subtests_scored_t1']} | "
                 f"{d['median_abs_change_in_count']} |")
    r3 = s.get("R3_judgement_vs_measured") or {}
    L += ["", "## R3 - is it restating the financials?", "",
          f"Rank correlation of the judgement half against the measured half: "
          f"**{r3.get('spearman')}** over {r3.get('n')} companies. The registered bar is "
          f"0.8 - above it, the LLM is largely re-deriving numbers the measured half "
          f"already has, and 50 points are buying less than they cost.", "",
          f"_{r3.get('note', '')}_", ""]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--compare-tag", default="",
                    help="E24: compare E22_raw_<tag> against the baseline on MG")
    ap.add_argument("--component", default="MG")
    args = ap.parse_args(argv)

    if args.compare_tag:
        variant_dir = RAW_DIR.with_name(RAW_DIR.name + "_" + args.compare_tag)
        res = compare(load(), load(variant_dir), component=args.component)
        exp = config.JOURNAL_DIR / "experiments"
        (exp / f"E24_{args.component}_stability.json").write_text(
            json.dumps(res, indent=2), encoding="utf-8")
        print(json.dumps(res, indent=2))
        rho_v = res.get("variant_spearman")
        if rho_v is not None:
            log(f"P2: {args.component} stability "
                f"{res.get('baseline_spearman')} -> {rho_v} "
                f"({'PASS' if res.get('P2_pass') else 'FAIL'} against 0.5)")
        return 0

    exp = config.JOURNAL_DIR / "experiments"
    if args.report:
        s = read_json(exp / "E22_results.json")
        if not isinstance(s, dict):
            log("no stored summary")
            return 1
    else:
        recs = load()
        if not recs:
            log("no raw records")
            return 1
        s = analyse(recs)
        (exp / "E22_results.json").write_text(json.dumps(s, indent=2), encoding="utf-8")
    md = render(s)
    (exp / "E22_results.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
