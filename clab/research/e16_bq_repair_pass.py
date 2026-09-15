"""E16 - a targeted repair pass for BQ, run only where the production call abstained.

Registered in `journal/experiments/E15_verdict_and_E16_preregistration.md`.

E15 killed the split (arm B): asking 7 dimensions and 4 dimensions in separate calls made
the 7 that already worked worse, and 7 of 10 controls lost a dimension. What survived is
narrow and real: `economies_of_scale` went from 2 of 20 to 18 of 20 once it had its own
retrieval query. So this runs the production 11-dimension call UNCHANGED, and only when
its result lands under the floor does a second targeted call run and merge in dimensions
the first left null.

Cheap because it is conditional: 463 of 1,498 companies are under the floor.

Research only. It does not write the qual cache, the scores table or the rubric.

    python -m clab.research.e16_bq_repair_pass --n-under 60 --n-control 20
    python -m clab.research.e16_bq_repair_pass --report
"""
from __future__ import annotations

import argparse
import json
import statistics
import time

from .. import config
from ..net import log_stamp, utc_now_iso
from ..qual import evidence as ev_mod
from ..qual import ollama, prompts
from ..qual.scorer import parse_bq
from ..runner import engine
from ..runner.fold_qual import BQ_MIN_DIMENSIONS
from ..scoring import rubric
from .e15_targeted_retrieval import (SEED, WEAK, _chunk_pool, _scored, _subset_prompt,
                                     _targeted_body, _unverified)

RAW_DIR = config.JOURNAL_DIR / "experiments" / "E16_raw"

#: where the under-floor population actually lives, from E12's 2026-08-18 measurement.
#: Sampling proportionally rather than evenly, because an even draw across five sectors
#: would over-weight Utilities (23 under-floor companies) against Financials (94).
STRATA = ("Real Estate", "Financials", "Energy", "Industrials", "Information Technology",
          "Utilities", "Consumer Discretionary", "Health Care")


from .e22_judgement_backtest import safe_stem as _safe_stem


def log(msg: str) -> None:
    print(f"[{log_stamp()}] {msg}", flush=True)


def sample(n_under: int, n_control: int) -> list[dict]:
    import pandas as pd
    df = pd.read_parquet(config.SCORES_PARQUET)
    df = df[df["ticker"].notna()]
    under = df[df["bq_available"] == 0]
    over = df[df["bq_available"] >= BQ_MIN_DIMENSIONS]
    pool = under[under["sector"].isin(STRATA)]
    rows = []
    total = len(pool)
    for sec in STRATA:
        part = pool[pool["sector"] == sec]
        want = max(round(n_under * len(part) / max(total, 1)), 1)
        rows += part.sample(min(want, len(part)), random_state=SEED).to_dict("records")
    rows = rows[:n_under]
    rows += over.sample(min(n_control, len(over)),
                        random_state=SEED + 1).to_dict("records")
    return [{"ticker": r["ticker"], "cik": str(r["cik"]).zfill(10),
             "name": r.get("name", ""), "sector": r.get("sector", ""),
             "sub_industry": r.get("sub_industry", ""),
             "arm": "under" if r["bq_available"] == 0 else "control"} for r in rows]


def run_one(row: dict) -> dict:
    """Production call, then the repair call only if the production call fell short."""
    as_of = utc_now_iso()
    ctx, _ = engine.build_context(row["ticker"], row["cik"], as_of=as_of,
                                  name=row.get("name", ""), sector=row.get("sector", ""),
                                  sub_industry=row.get("sub_industry", ""))
    pack = ev_mod.build_pack(ctx)
    body = pack["components"]["BQ"]

    t0 = time.perf_counter()
    base = parse_bq(ollama.chat(prompts.bq_prompt(body), system=prompts.SYSTEM,
                                timeout=900.0), body)
    base_dims = base.get("dimensions") or {}
    base_scored = _scored(base_dims)
    bf, bt = _unverified(base)
    out = {
        "ticker": row["ticker"], "cik": row["cik"], "sector": row.get("sector", ""),
        "arm": row["arm"],
        "base": {"scored": sorted(base_scored), "unverified": [bf, bt],
                 "secs": round(time.perf_counter() - t0, 1),
                 "parse_ok": bool(base.get("parse_ok"))},
        "repaired": None,
    }
    # The conditional. A company the production call already answered is never touched -
    # that is what keeps E15's arm-B regression (7 of 10 controls lost a dimension)
    # structurally impossible here rather than merely unlikely.
    if len(base_scored) >= BQ_MIN_DIMENSIONS:
        out["repair_ran"] = False
        out["final"] = {"scored": sorted(base_scored)}
        return out

    t1 = time.perf_counter()
    chunks, vectors, fmeta = _chunk_pool(ctx)
    body_t, tmeta = _targeted_body(ctx, chunks, vectors, fmeta)
    weak = parse_bq(ollama.chat(_subset_prompt(body_t, WEAK), system=prompts.SYSTEM,
                                timeout=900.0), body_t)
    weak_scored = _scored(weak.get("dimensions")) & set(WEAK)
    wf, wt = _unverified(weak)
    final = sorted(base_scored | weak_scored)
    out["repair_ran"] = True
    out["repaired"] = {
        "weak_scored": sorted(weak_scored),
        # Attributed to the repair call alone. E15 could only report the pair, which is
        # why its 3.33% could not be pinned on either call.
        "unverified": [wf, wt],
        "secs": round(time.perf_counter() - t1, 1),
        "parse_ok": bool(weak.get("parse_ok")),
        "targeted_meta": tmeta,
    }
    out["final"] = {"scored": final}
    return out


def run(n_under: int, n_control: int, *, resume: bool = True) -> list[dict]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    rows = sample(n_under, n_control)
    log(f"sample: {sum(1 for r in rows if r['arm'] == 'under')} under-floor, "
        f"{sum(1 for r in rows if r['arm'] == 'control')} controls")
    ok, why = ollama.available()
    if not ok:
        log(f"ollama is not usable: {why}")
        return []
    out = []
    with ollama.gpu_lease(wait=True):
        for i, row in enumerate(rows, 1):
            path = RAW_DIR / f"{_safe_stem(row['ticker'])}.json"
            if resume and path.exists():
                out.append(json.loads(path.read_text(encoding="utf-8")))
                continue
            try:
                rec = run_one(row)
            except Exception as exc:                        # noqa: BLE001
                log(f"  {row['ticker']} FAILED: {type(exc).__name__}: {exc}")
                continue
            path.write_text(json.dumps(rec, indent=2), encoding="utf-8")
            out.append(rec)
            log(f"  {rec['ticker']:<6} {rec['arm']:<7} "
                f"base={len(rec['base']['scored']):>2} "
                f"final={len(rec['final']['scored']):>2} "
                f"{'repaired' if rec['repair_ran'] else '-':<8} ({i}/{len(rows)})")
    return out


def summarise(recs: list[dict]) -> dict:
    under = [r for r in recs if r["arm"] == "under"]
    ctrl = [r for r in recs if r["arm"] == "control"]
    repaired = [r for r in recs if r.get("repair_ran")]

    cleared_before = sum(1 for r in under
                         if len(r["base"]["scored"]) >= BQ_MIN_DIMENSIONS)
    cleared_after = sum(1 for r in under
                        if len(r["final"]["scored"]) >= BQ_MIN_DIMENSIONS)
    q1 = 100 * cleared_after / max(len(under), 1)

    rf = sum(r["repaired"]["unverified"][0] for r in repaired)
    rt = sum(r["repaired"]["unverified"][1] for r in repaired)
    bf = sum(r["base"]["unverified"][0] for r in recs)
    bt = sum(r["base"]["unverified"][1] for r in recs)
    q2 = round(100 * rf / rt, 2) if rt else 0.0

    lost = [r["ticker"] for r in ctrl
            if set(r["base"]["scored"]) - set(r["final"]["scored"])]

    eos = sum(1 for r in under
              if "economies_of_scale" in (r.get("repaired") or {}).get("weak_scored", []))
    q4 = 100 * eos / max(len(under), 1)

    # Q5's first half: what the newly cleared companies are actually made of. If every
    # one clears on the same six dimensions, the floor was cleared on a technicality.
    newly = [r for r in under
             if len(r["base"]["scored"]) < BQ_MIN_DIMENSIONS
             and len(r["final"]["scored"]) >= BQ_MIN_DIMENSIONS]
    comp: dict[str, int] = {}
    for r in newly:
        for d in r["final"]["scored"]:
            comp[d] = comp.get(d, 0) + 1
    recovered: dict[str, int] = {}
    for r in under:
        for d in (r.get("repaired") or {}).get("weak_scored", []):
            recovered[d] = recovered.get(d, 0) + 1

    return {
        "n_under": len(under), "n_control": len(ctrl), "n_repaired": len(repaired),
        "cleared_before": cleared_before, "cleared_after": cleared_after,
        "Q1_cleared_pct": round(q1, 1), "Q1_pass": q1 >= 35.0,
        "Q2_repair_unverified_pct": q2, "Q2_pass": q2 <= 1.0,
        "unverified_counts": {"production": [bf, bt], "repair": [rf, rt]},
        "Q3_controls_losing_a_dimension": lost, "Q3_pass": not lost,
        "Q4_economies_of_scale_pct": round(q4, 1), "Q4_pass": q4 >= 60.0,
        "recovered_by_dimension": dict(sorted(recovered.items(), key=lambda kv: -kv[1])),
        "newly_cleared": [r["ticker"] for r in newly],
        "newly_cleared_dimension_composition": dict(
            sorted(comp.items(), key=lambda kv: -kv[1])),
        "median_repair_secs": round(statistics.median(
            [r["repaired"]["secs"] for r in repaired]), 1) if repaired else 0.0,
        "median_dims_before": statistics.median(
            [len(r["base"]["scored"]) for r in under]) if under else 0.0,
        "median_dims_after": statistics.median(
            [len(r["final"]["scored"]) for r in under]) if under else 0.0,
    }


def render(s: dict) -> str:
    def v(flag):
        return "PASS" if flag else "FAIL"
    L = [f"# E16 results - conditional BQ repair pass ({utc_now_iso()[:10]})", "",
         "ADVISORY / SHADOW. This measures whether dimensions get SCORED, not whether the",
         "scores are right. There is no forward-return grader. `promoted` stays false.", "",
         f"Sample: {s['n_under']} under-floor, {s['n_control']} controls; the repair call",
         f"ran on {s['n_repaired']} of them.", "",
         "| criterion | measured | bar | verdict |", "|---|---|---|---|",
         f"| Q1 under-floor companies clearing the floor | {s['cleared_before']} -> "
         f"{s['cleared_after']} of {s['n_under']} ({s['Q1_cleared_pct']}%) | >= 35% | "
         f"{v(s['Q1_pass'])} |",
         f"| Q2 unverified quotes, REPAIR call only | {s['Q2_repair_unverified_pct']}% "
         f"({s['unverified_counts']['repair'][0]} of "
         f"{s['unverified_counts']['repair'][1]}) | <= 1.0% | {v(s['Q2_pass'])} |",
         f"| Q3 controls losing a dimension | "
         f"{len(s['Q3_controls_losing_a_dimension'])} | 0 | {v(s['Q3_pass'])} |",
         f"| Q4 economies_of_scale recovered | {s['Q4_economies_of_scale_pct']}% | "
         f">= 60% | {v(s['Q4_pass'])} |", "",
         f"Median dimensions scored, under-floor: {s['median_dims_before']} -> "
         f"{s['median_dims_after']}. Median repair cost {s['median_repair_secs']} s.", "",
         "## What the repair call actually recovered", "",
         "| dimension | companies |", "|---|---:|"]
    for d, n in s["recovered_by_dimension"].items():
        L.append(f"| {d} | {n} |")
    L += ["", "## Q5 - what the newly cleared companies are made of", "",
          "The floor exists so a moat verdict cannot rest on a handful of dimensions. If",
          "every newly cleared company clears on the same six, the floor was cleared on a",
          "technicality.", "", "| dimension | appears in |", "|---|---:|"]
    for d, n in s["newly_cleared_dimension_composition"].items():
        L.append(f"| {d} | {n} of {len(s['newly_cleared'])} |")
    if s["Q3_controls_losing_a_dimension"]:
        L += ["", "**WIRING BUG** - a control lost a dimension, which this design makes "
              "impossible by construction: "
              + ", ".join(s["Q3_controls_losing_a_dimension"])]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n-under", type=int, default=60)
    ap.add_argument("--n-control", type=int, default=20)
    ap.add_argument("--no-resume", action="store_true")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args(argv)

    if args.report:
        recs = [json.loads(p.read_text(encoding="utf-8"))
                for p in sorted(RAW_DIR.glob("*.json"))]
    else:
        recs = run(args.n_under, args.n_control, resume=not args.no_resume)
    if not recs:
        log("nothing to summarise")
        return 1
    s = summarise(recs)
    exp = config.JOURNAL_DIR / "experiments"
    (exp / "E16_results.json").write_text(json.dumps(s, indent=2), encoding="utf-8")
    md = render(s)
    (exp / "E16_results.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
