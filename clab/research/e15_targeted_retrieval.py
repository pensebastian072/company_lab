"""E15 - can BQ abstention be bought back with retrieval instead of a rubric change?

Registered in `journal/experiments/E15_bq_targeted_retrieval_preregistration.md`.

BQ asks for 11 moat dimensions off 8 chunks retrieved by ONE query. Four dimensions
abstain 61-84% of the time; `customer_relationships` abstains 7.5% off the same chunks.
This measures whether asking those four separately, over chunks retrieved by a query
PER DIMENSION, recovers scores - and, decisively, whether it does so without inventing
quotes.

Research only. Nothing here writes the qual cache, the scores table or the rubric. It is
resumable per company because this box loses power (twice in 24 hours on 2026-08-17/18).

    python -m clab.research.e15_targeted_retrieval --n-under 20 --n-control 10
    python -m clab.research.e15_targeted_retrieval --report        # re-render from raw
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
from ..sources import edgar_filings

#: the four E12 named as abstaining on more than half the universe
WEAK = ("network_effects", "manufacturing_complexity", "data_advantages",
        "economies_of_scale")

#: One query per weak dimension, written before any result was seen. Each names the
#: language a 10-K would actually use, not the rubric's label - "customers on our
#: platform" is retrievable, "network effects" is a term filers rarely write down.
DIM_QUERIES = {
    "network_effects": ("platform users, marketplace participants, subscribers, "
                        "merchants and buyers, ecosystem, more users attract more "
                        "customers, two-sided marketplace, installed base"),
    "manufacturing_complexity": ("manufacturing facilities, plants, production process, "
                                 "capacity utilisation, fabrication, supply chain, "
                                 "specialised equipment, yield, tooling, capital "
                                 "intensity"),
    "data_advantages": ("proprietary data, data sets, analytics, machine learning "
                        "models, customer usage data, telemetry, algorithms trained on "
                        "our data, information advantage"),
    "economies_of_scale": ("scale, fixed cost leverage, purchasing power, unit costs, "
                           "operating leverage, distribution density, cost per unit "
                           "declines with volume, largest in the industry"),
}
CHUNKS_PER_DIM = 2
#: fixed so the sample is reproducible across re-runs and power cuts
SEED = 1337
RAW_DIR = config.JOURNAL_DIR / "experiments" / "E15_raw"
EASY = tuple(k for k, _ in rubric.BQ_DIMENSIONS if k not in WEAK)


from .e22_judgement_backtest import safe_stem as _safe_stem


def log(msg: str) -> None:
    print(f"[{log_stamp()}] {msg}", flush=True)


def _subset_prompt(evidence: str, keys: tuple[str, ...]) -> str:
    """`prompts.bq_prompt` restricted to a subset of dimensions.

    A copy rather than a production change: E15 must be able to fail without having
    touched the scorer, and the cache key is a hash of the prompt template.
    """
    labels = dict(rubric.BQ_DIMENSIONS)
    dims = "\n".join(f"  - {k}: {labels[k]}" for k in keys)
    fields = ",\n  ".join(
        f'"{k}": {{"score": <integer 0..{rubric.BQ_DIMENSION_MAX} or null>, '
        f'"rationale": "<one sentence>"}}' for k in keys)
    return f"""{evidence}

TASK: score BUSINESS QUALITY AND MOAT for this company.

Rate each moat dimension from 0 to {rubric.BQ_DIMENSION_MAX}, where 0 means a
commodity business that is easily replaced and {rubric.BQ_DIMENSION_MAX} means it
would be exceptionally difficult for a well-funded competitor to displace.

DIMENSIONS
{dims}

{prompts._RULES}

Respond with ONLY this JSON object:
{{"dimensions": {{
  {fields}
 }},
 "summary": "<one sentence on the overall moat>",
 "evidence": "<verbatim quote supporting the strongest moat, or null>"}}"""


def _chunk_pool(ctx):
    """The same chunk pool `build_pack` assembles, plus its embedding vectors.

    Mirrors `evidence.build_pack`'s round-robin cap deliberately: arm B must differ from
    arm A in the QUERY only, never in what text was available to retrieve from.
    """
    text, fmeta = edgar_filings.filing_text(ctx.cik)
    sections = edgar_filings.slice_sections(text)
    per_section: dict[str, list[str]] = {}
    for name in ("business", "risk_factors", "mdna"):
        body = sections.get(name)
        if body:
            per_section[name] = [f"[{name}] {c[:ev_mod.MAX_CHUNK_CHARS]}"
                                 for c in edgar_filings.chunk_text(body[:400_000])]
    if not per_section and text:
        per_section["_whole_document"] = [
            f"[filing] {c[:ev_mod.MAX_CHUNK_CHARS]}"
            for c in edgar_filings.chunk_text(text[:600_000]) if ev_mod._is_prose(c)]
    chunks: list[str] = []
    if per_section:
        share = max(ev_mod.MAX_CHUNKS_TOTAL // len(per_section), 1)
        for cs in per_section.values():
            chunks.extend(cs[:share])
    return chunks, ev_mod.embed_chunks(chunks), fmeta


def _targeted_body(ctx, chunks, vectors, fmeta) -> tuple[str, dict]:
    """Fact sheet + CHUNKS_PER_DIM chunks retrieved per weak dimension."""
    picked: list[str] = []
    methods = {}
    for dim in WEAK:
        got, method = ev_mod.retrieve(chunks, DIM_QUERIES[dim], k=CHUNKS_PER_DIM,
                                      doc_vectors=vectors)
        methods[dim] = method
        for c in got:
            if c not in picked:
                picked.append(c)
    parts = [ev_mod.fact_sheet(ctx), ""]
    if picked:
        parts += [f"EXCERPTS FROM THE LATEST {fmeta.get('form', 'ANNUAL REPORT')} "
                  f"(filed {fmeta.get('filed', 'n/a')}):", ""]
        parts += [f"--- excerpt {i + 1} ---\n{c}" for i, c in enumerate(picked)]
    else:
        parts += ["FILING EXCERPTS: unavailable. Use null for anything the measured "
                  "financials above do not support."]
    return "\n".join(parts), {"n_chunks_picked": len(picked), "methods": methods}


def _scored(dims: dict) -> set:
    return {k for k, v in (dims or {}).items()
            if isinstance(v, dict) and v.get("score") is not None}


def _unverified(parsed: dict) -> tuple[int, int]:
    """(flagged, total) evidence quotes that did not overlap the pack - E07's M3."""
    flagged = total = 0
    for v in (parsed.get("dimensions") or {}).values():
        if isinstance(v, dict) and "evidence_unverified" in v:
            total += 1
            flagged += bool(v.get("evidence_unverified"))
    if "evidence_unverified" in parsed:
        total += 1
        flagged += bool(parsed.get("evidence_unverified"))
    return flagged, total


def sample(n_under: int, n_control: int) -> list[dict]:
    """Under-floor companies stratified by sector, plus controls that already clear it.

    Stratified because E12 established BQ availability is sector-structured; a random
    draw would be mostly Financials and Industrials and would say nothing about whether
    the fix works where the problem is worst.
    """
    import pandas as pd
    df = pd.read_parquet(config.SCORES_PARQUET)
    df = df[df["ticker"].notna()]
    under = df[df["bq_available"] == 0]
    over = df[df["bq_available"] >= BQ_MIN_DIMENSIONS]
    want = ["Real Estate", "Energy", "Utilities", "Financials",
            "Information Technology"]
    # Seeded random draw, not the alphabetical head. Taking the first N tickers would
    # sample AAT/ABR/ADAM every time - a stable sample, but a stable BIASED one, and
    # nothing about a company's name is independent of its size or listing history.
    per = max(n_under // len(want), 1)
    rows = []
    for sec in want:
        part = under[under["sector"] == sec]
        rows += part.sample(min(per, len(part)), random_state=SEED).to_dict("records")
    rows = rows[:n_under]
    rows += over.sample(min(n_control, len(over)),
                        random_state=SEED).to_dict("records")
    return [{"ticker": r["ticker"], "cik": str(r["cik"]).zfill(10),
             "name": r.get("name", ""), "sector": r.get("sector", ""),
             "sub_industry": r.get("sub_industry", ""),
             "arm": "under" if r["bq_available"] == 0 else "control"} for r in rows]


def run_one(row: dict) -> dict:
    as_of = utc_now_iso()
    ctx, _ = engine.build_context(row["ticker"], row["cik"], as_of=as_of,
                                  name=row.get("name", ""), sector=row.get("sector", ""),
                                  sub_industry=row.get("sub_industry", ""))
    pack = ev_mod.build_pack(ctx)
    body_a = pack["components"]["BQ"]
    chunks, vectors, fmeta = _chunk_pool(ctx)
    body_b, bmeta = _targeted_body(ctx, chunks, vectors, fmeta)

    out = {"ticker": row["ticker"], "cik": row["cik"], "sector": row.get("sector", ""),
           "arm": row["arm"], "targeted_meta": bmeta}

    t0 = time.perf_counter()
    raw_a = ollama.chat(prompts.bq_prompt(body_a), system=prompts.SYSTEM, timeout=900.0)
    a = parse_bq(raw_a, body_a)
    out["A"] = {"scored": sorted(_scored(a.get("dimensions"))),
                "unverified": _unverified(a), "secs": round(time.perf_counter() - t0, 1),
                "parse_ok": bool(a.get("parse_ok"))}

    t1 = time.perf_counter()
    raw_easy = ollama.chat(_subset_prompt(body_a, EASY), system=prompts.SYSTEM,
                           timeout=900.0)
    easy = parse_bq(raw_easy, body_a)
    raw_weak = ollama.chat(_subset_prompt(body_b, WEAK), system=prompts.SYSTEM,
                           timeout=900.0)
    weak = parse_bq(raw_weak, body_b)
    merged = {k: v for k, v in (easy.get("dimensions") or {}).items() if k in EASY}
    merged.update({k: v for k, v in (weak.get("dimensions") or {}).items() if k in WEAK})
    fw, tw = _unverified(weak)
    fe_, te = _unverified(easy)
    out["B"] = {"scored": sorted(_scored(merged)),
                "unverified": (fw + fe_, tw + te),
                "secs": round(time.perf_counter() - t1, 1),
                "parse_ok": bool(easy.get("parse_ok") and weak.get("parse_ok")),
                "weak_scored": sorted(_scored(weak.get("dimensions")) & set(WEAK))}
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
                log(f"  {row['ticker']} cached ({i}/{len(rows)})")
                continue
            try:
                rec = run_one(row)
            except Exception as exc:                       # noqa: BLE001
                log(f"  {row['ticker']} FAILED: {type(exc).__name__}: {exc}")
                continue
            path.write_text(json.dumps(rec, indent=2), encoding="utf-8")
            out.append(rec)
            log(f"  {row['ticker']:<6} {rec['arm']:<7} A={len(rec['A']['scored']):>2} "
                f"B={len(rec['B']['scored']):>2} dims  "
                f"(+{rec['B']['secs']:.0f}s)  ({i}/{len(rows)})")
    return out


def summarise(recs: list[dict]) -> dict:
    under = [r for r in recs if r["arm"] == "under"]
    ctrl = [r for r in recs if r["arm"] == "control"]

    def med(rs, arm):
        return statistics.median([len(r[arm]["scored"]) for r in rs]) if rs else 0.0

    def unver(rs, arm):
        f = sum(r[arm]["unverified"][0] for r in rs)
        t = sum(r[arm]["unverified"][1] for r in rs)
        return round(100 * f / t, 2) if t else 0.0, f, t

    lost = [r["ticker"] for r in ctrl
            if set(r["A"]["scored"]) - set(r["B"]["scored"])]
    p1 = med(under, "B") - med(under, "A")
    ub, fb, tb = unver(recs, "B")
    ua, fa, ta = unver(recs, "A")
    added = [r["B"]["secs"] - r["A"]["secs"] for r in recs]
    med_added = statistics.median(added) if added else 0.0
    # ARM C - EXPLORATORY, NOT PRE-REGISTERED. Union of arm A's 11-dimension call with
    # the weak dimensions recovered by the targeted call. It cannot lose a dimension by
    # construction, which is exactly why it is not a fair test: it is reported so the
    # split-vs-additive question is visible, and it must be re-run as a registered
    # confirmatory arm before it can beat B on the strength of this table.
    c_counts = [len(set(r["A"]["scored"]) | set(r["B"].get("weak_scored") or []))
                for r in under]
    per_dim = {}
    for d in WEAK:
        per_dim[d] = {
            "A": sum(1 for r in under if d in r["A"]["scored"]),
            "B": sum(1 for r in under if d in r["B"]["scored"]),
            "n": len(under),
        }
    return {
        "n_under": len(under), "n_control": len(ctrl),
        "median_dims_A": med(under, "A"), "median_dims_B": med(under, "B"),
        "P1_median_gain": p1, "P1_pass": p1 >= 1.5,
        "unverified_pct_A": ua, "unverified_pct_B": ub,
        "unverified_counts": {"A": [fa, ta], "B": [fb, tb]},
        "P2_pass": ub <= 1.0,
        "controls_losing_a_dimension": lost,
        "P3_pass": len(lost) <= 1,
        "median_added_secs": round(med_added, 1),
        "P4_pass": med_added <= 25.0,
        "weak_dimension_recovery": per_dim,
        "cleared_floor_A": sum(1 for r in under
                               if len(r["A"]["scored"]) >= BQ_MIN_DIMENSIONS),
        "cleared_floor_B": sum(1 for r in under
                               if len(r["B"]["scored"]) >= BQ_MIN_DIMENSIONS),
        "exploratory_arm_C": {
            "note": "NOT pre-registered: A's call plus the targeted weak call, union",
            "median_dims": statistics.median(c_counts) if c_counts else 0.0,
            "cleared_floor": sum(1 for n in c_counts if n >= BQ_MIN_DIMENSIONS),
        },
    }


def render(s: dict) -> str:
    L = [f"# E15 results - BQ targeted retrieval ({utc_now_iso()[:10]})", "",
         "ADVISORY / SHADOW. This measures whether dimensions get SCORED, not whether",
         "the scores are right. There is no forward-return grader. `promoted` stays "
         "false.", "",
         f"Sample: {s['n_under']} under-floor companies, {s['n_control']} controls.", "",
         "| criterion | measured | bar | verdict |", "|---|---|---|---|",
         f"| P1 median dimensions scored | {s['median_dims_A']} -> "
         f"{s['median_dims_B']} (+{s['P1_median_gain']}) | >= +1.5 | "
         f"{'PASS' if s['P1_pass'] else 'FAIL'} |",
         f"| P2 unverified quote rate (arm B) | {s['unverified_pct_B']}% "
         f"(A: {s['unverified_pct_A']}%) | <= 1.0% | "
         f"{'PASS' if s['P2_pass'] else 'FAIL'} |",
         f"| P3 controls losing a dimension | {len(s['controls_losing_a_dimension'])} "
         f"of {s['n_control']} | <= 1 | {'PASS' if s['P3_pass'] else 'FAIL'} |",
         f"| P4 added seconds per company | {s['median_added_secs']} | <= 25 | "
         f"{'PASS' if s['P4_pass'] else 'FAIL'} |", "",
         f"Companies clearing the 6-dimension floor: **{s['cleared_floor_A']} -> "
         f"{s['cleared_floor_B']}** of {s['n_under']}.", "",
         "## Per weak dimension (under-floor sample)", "",
         "| dimension | scored in A | scored in B | of |", "|---|---:|---:|---:|"]
    for d, v in s["weak_dimension_recovery"].items():
        L.append(f"| {d} | {v['A']} | {v['B']} | {v['n']} |")
    c = s.get("exploratory_arm_C") or {}
    if c:
        L += ["", "## Exploratory, NOT pre-registered", "",
              f"Arm C (A's call unioned with the targeted weak call) reaches a median "
              f"of {c['median_dims']} dimensions and clears the floor for "
              f"{c['cleared_floor']} of {s['n_under']}. It cannot lose a dimension by "
              "construction, so it is not comparable to B on this table - it needs its "
              "own registered run before it can be preferred."]
    if s["controls_losing_a_dimension"]:
        L += ["", "Controls that lost a dimension: "
              + ", ".join(s["controls_losing_a_dimension"])]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n-under", type=int, default=20)
    ap.add_argument("--n-control", type=int, default=10)
    ap.add_argument("--no-resume", action="store_true")
    ap.add_argument("--report", action="store_true",
                    help="re-render from E15_raw/ without generating anything")
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
    (exp / "E15_results.json").write_text(json.dumps(s, indent=2), encoding="utf-8")
    md = render(s)
    (exp / "E15_results.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
