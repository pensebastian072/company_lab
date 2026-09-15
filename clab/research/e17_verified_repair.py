"""E17 - a repair call that must QUOTE, with the quote gating the score.

Registered in `journal/experiments/E16_verdict_and_E17_preregistration.md`.

E16 showed the repair pass clears the floor for half the under-floor sample, and also
showed that its fabrication criterion could not be measured: BQ emits one quote per call,
so 52 calls can only ever report 0.00% or >= 1.92%. The defence therefore moves from
measurement to mechanism - the repair call supplies a verbatim quote PER DIMENSION, and a
dimension whose quote does not verify is dropped rather than scored.

Three gates are scored for every recovered dimension, because how much "verified" means
today is itself the question:

  strict      - the quote is a substring of the pack after whitespace normalisation
  tight       - token overlap >= 0.90
  production  - token overlap >= 0.60, the rule `scorer._verify_evidence` uses now

The base (production) call is NOT re-run; each company's result is read from its E16_raw
record, generated the same day from the same packs.

Research only. Does not write the qual cache, the scores table or the rubric.

    python -m clab.research.e17_verified_repair
    python -m clab.research.e17_verified_repair --report
"""
from __future__ import annotations

import argparse
import json
import re
import statistics

from .. import config
from ..net import log_stamp, utc_now_iso
from ..qual import evidence as ev_mod
from ..qual import ollama, prompts
from ..qual.scorer import _token_overlap, extract_json
from ..runner import engine
from ..runner.fold_qual import BQ_MIN_DIMENSIONS
from ..scoring import rubric
from .e15_targeted_retrieval import WEAK, _chunk_pool, _targeted_body
from .e16_bq_repair_pass import RAW_DIR as E16_RAW

RAW_DIR = config.JOURNAL_DIR / "experiments" / "E17_raw"
TIGHT_OVERLAP = 0.90
PRODUCTION_OVERLAP = 0.60


from .e22_judgement_backtest import safe_stem as _safe_stem


def log(msg: str) -> None:
    print(f"[{log_stamp()}] {msg}", flush=True)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def gates(quote: str | None, pack: str) -> dict:
    """Every gate's verdict for one quote, so the comparison is on one object."""
    if not quote or not isinstance(quote, str):
        return {"strict": False, "tight": False, "production": False, "has_quote": False}
    ov = _token_overlap(quote, pack)
    return {
        "has_quote": True,
        "strict": _norm(quote)[:600] in _norm(pack),
        "tight": ov >= TIGHT_OVERLAP,
        "production": ov >= PRODUCTION_OVERLAP,
        "overlap": round(ov, 3),
    }


def repair_prompt(evidence: str) -> str:
    """The four weak dimensions, each REQUIRING a verbatim quote.

    The quote is not decoration here - it is the gate. A dimension whose quote does not
    verify is dropped, so the prompt says exactly that, rather than the softer "if you
    cannot quote it, use null" the shared rules carry.
    """
    labels = dict(rubric.BQ_DIMENSIONS)
    dims = "\n".join(f"  - {k}: {labels[k]}" for k in WEAK)
    fields = ",\n  ".join(
        f'"{k}": {{"score": <integer 0..{rubric.BQ_DIMENSION_MAX} or null>, '
        f'"rationale": "<one sentence>", "evidence": "<verbatim quote or null>"}}'
        for k in WEAK)
    return f"""{evidence}

TASK: score these four moat dimensions for this company.

Rate each from 0 to {rubric.BQ_DIMENSION_MAX}, where 0 means a commodity business that is
easily replaced and {rubric.BQ_DIMENSION_MAX} means it would be exceptionally difficult
for a well-funded competitor to displace.

DIMENSIONS
{dims}

{prompts._RULES}
- The "evidence" quote is CHECKED against the material above. A score whose quote is not
  found there is DISCARDED. Copy the words exactly; do not paraphrase, summarise or
  reconstruct them.

Respond with ONLY this JSON object:
{{"dimensions": {{
  {fields}
 }}}}"""


def parse_repair(raw: str, pack: str) -> dict:
    """Per-dimension score + quote + every gate's verdict. No production parser fits."""
    data = extract_json(raw)
    out = {"parse_ok": data is not None, "dimensions": {}}
    if not data:
        return out
    dims = data.get("dimensions")
    if not isinstance(dims, dict):
        dims = data
    for key in WEAK:
        rec = dims.get(key)
        if not isinstance(rec, dict):
            continue
        raw_score = rec.get("score")
        score = None
        if isinstance(raw_score, bool):
            score = None
        elif isinstance(raw_score, (int, float)) and float(raw_score).is_integer():
            v = int(raw_score)
            # Out of range is REJECTED, never clamped - the same rule the rubric uses.
            score = v if 0 <= v <= rubric.BQ_DIMENSION_MAX else None
        elif isinstance(raw_score, str) and raw_score.strip().isdigit():
            v = int(raw_score.strip())
            score = v if 0 <= v <= rubric.BQ_DIMENSION_MAX else None
        quote = rec.get("evidence")
        out["dimensions"][key] = {
            "score": score,
            "quote": (quote or "")[:600] if isinstance(quote, str) else None,
            "gates": gates(quote if isinstance(quote, str) else None, pack),
        }
    return out


def accepted(rec: dict, gate: str) -> set:
    """Dimensions this repair call may contribute under one gate."""
    return {k for k, v in (rec.get("dimensions") or {}).items()
            if v.get("score") is not None and v["gates"].get(gate)}


def e16_records() -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8"))
            for p in sorted(E16_RAW.glob("*.json"))]


def run_one(row: dict) -> dict:
    as_of = utc_now_iso()
    ctx, _ = engine.build_context(row["ticker"], row["cik"], as_of=as_of,
                                  name=row.get("name", ""), sector=row.get("sector", ""),
                                  sub_industry=row.get("sub_industry", ""))
    chunks, vectors, fmeta = _chunk_pool(ctx)
    body, tmeta = _targeted_body(ctx, chunks, vectors, fmeta)
    raw = ollama.chat(repair_prompt(body), system=prompts.SYSTEM, timeout=900.0)
    rec = parse_repair(raw, body)
    rec.update({"ticker": row["ticker"], "cik": row["cik"], "sector": row["sector"],
                "arm": row["arm"], "base_scored": row["base_scored"],
                "targeted_meta": tmeta})
    return rec


def run(*, resume: bool = True) -> list[dict]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    e16 = e16_records()
    # Only companies whose production call fell short - the same conditional E16 used,
    # read off E16's own records so the two runs cover an identical population.
    rows = [{"ticker": r["ticker"], "cik": r["cik"], "sector": r["sector"],
             "name": "", "sub_industry": "", "arm": r["arm"],
             "base_scored": r["base"]["scored"]}
            for r in e16 if r.get("repair_ran")]
    log(f"repairing {len(rows)} companies "
        f"({sum(1 for r in rows if r['arm'] == 'under')} under-floor, "
        f"{sum(1 for r in rows if r['arm'] == 'control')} control)")
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
            log(f"  {rec['ticker']:<6} scored={len(accepted(rec, 'has_quote')):>1} "
                f"strict={len(accepted(rec, 'strict')):>1} "
                f"tight={len(accepted(rec, 'tight')):>1} "
                f"prod={len(accepted(rec, 'production')):>1}  ({i}/{len(rows)})")
    return out


def summarise(recs: list[dict]) -> dict:
    under = [r for r in recs if r["arm"] == "under"]
    e16 = {r["ticker"]: r for r in e16_records()}

    def cleared(gate):
        n = 0
        for r in under:
            dims = set(r["base_scored"]) | accepted(r, gate)
            if len(dims) >= BQ_MIN_DIMENSIONS:
                n += 1
        return n

    # yield per gate: of the dimensions the model SCORED, how many survive verification
    proposed = sum(1 for r in recs for v in (r.get("dimensions") or {}).values()
                   if v.get("score") is not None)
    y = {}
    for gate in ("has_quote", "production", "tight", "strict"):
        kept = sum(len(accepted(r, gate)) for r in recs)
        y[gate] = {"kept": kept,
                   "pct": round(100 * kept / proposed, 1) if proposed else 0.0}

    per_dim = {}
    for d in WEAK:
        row = {"proposed": 0, "strict": 0, "tight": 0, "production": 0}
        for r in recs:
            v = (r.get("dimensions") or {}).get(d)
            if not v or v.get("score") is None:
                continue
            row["proposed"] += 1
            for gate in ("strict", "tight", "production"):
                row[gate] += bool(v["gates"].get(gate))
        per_dim[d] = row

    eos_strict = sum(1 for r in under if "economies_of_scale" in accepted(r, "strict"))
    n_under_e16 = sum(1 for r in e16.values() if r["arm"] == "under")
    base_cleared = sum(1 for r in e16.values()
                       if r["arm"] == "under"
                       and len(r["base"]["scored"]) >= BQ_MIN_DIMENSIONS)
    controls_lost = [r["ticker"] for r in recs if r["arm"] == "control"
                     and set(r["base_scored"]) - (set(r["base_scored"])
                                                  | accepted(r, "strict"))]
    strict_cleared = cleared("strict") + base_cleared
    return {
        "n_repaired": len(recs), "n_under_repaired": len(under),
        "n_under_total": n_under_e16,
        "cleared_base_only": base_cleared,
        "R1_cleared_strict": strict_cleared,
        "R1_cleared_strict_pct": round(100 * strict_cleared / max(n_under_e16, 1), 1),
        "R1_pass": 100 * strict_cleared / max(n_under_e16, 1) >= 35.0,
        "cleared_production_gate": cleared("production") + base_cleared,
        "cleared_no_gate": cleared("has_quote") + base_cleared,
        "R2_yield": y,
        "R2_per_dimension": per_dim,
        "R3_controls_losing_a_dimension": controls_lost, "R3_pass": not controls_lost,
        "R4_eos_strict_pct": round(100 * eos_strict / max(len(under), 1), 1),
        "R4_pass": 100 * eos_strict / max(len(under), 1) >= 50.0,
        "quotes_missing_entirely": sum(
            1 for r in recs for v in (r.get("dimensions") or {}).values()
            if v.get("score") is not None and not v["gates"].get("has_quote")),
        "median_overlap": statistics.median(
            [v["gates"]["overlap"] for r in recs
             for v in (r.get("dimensions") or {}).values()
             if v.get("score") is not None and "overlap" in v["gates"]] or [0.0]),
    }


def render(s: dict) -> str:
    def v(f):
        return "PASS" if f else "FAIL"
    y = s["R2_yield"]
    L = [f"# E17 results - the quote gates the score ({utc_now_iso()[:10]})", "",
         "ADVISORY / SHADOW. A verified quote means the sentence is in the filing, not",
         "that the score is right. No forward-return grader exists. `promoted` stays "
         "false.", "",
         f"Repair call ran on {s['n_repaired']} companies "
         f"({s['n_under_repaired']} under-floor).", "",
         "| criterion | measured | bar | verdict |", "|---|---|---|---|",
         f"| R1 floor clearance, STRICT gate | {s['R1_cleared_strict']} of "
         f"{s['n_under_total']} ({s['R1_cleared_strict_pct']}%) | >= 35% | "
         f"{v(s['R1_pass'])} |",
         f"| R3 controls losing a dimension | "
         f"{len(s['R3_controls_losing_a_dimension'])} | 0 | {v(s['R3_pass'])} |",
         f"| R4 economies_of_scale, STRICT gate | {s['R4_eos_strict_pct']}% | >= 50% | "
         f"{v(s['R4_pass'])} |", "",
         f"Floor clearance by gate: no gate **{s['cleared_no_gate']}**, production 0.60 "
         f"**{s['cleared_production_gate']}**, strict substring "
         f"**{s['R1_cleared_strict']}** of {s['n_under_total']} "
         f"(base call alone cleared {s['cleared_base_only']}).", "",
         "## R2 - what survives verification (no bar; this is a description)", "",
         "| gate | dimensions kept | of proposed |", "|---|---:|---:|"]
    for gate in ("has_quote", "production", "tight", "strict"):
        L.append(f"| {gate} | {y[gate]['kept']} | {y[gate]['pct']}% |")
    L += ["", f"Median token overlap of a proposed quote: **{s['median_overlap']}**. "
          f"Scores offered with no quote at all: {s['quotes_missing_entirely']}.", "",
          "| dimension | proposed | production 0.60 | tight 0.90 | strict substring |",
          "|---|---:|---:|---:|---:|"]
    for d, r in s["R2_per_dimension"].items():
        L.append(f"| {d} | {r['proposed']} | {r['production']} | {r['tight']} | "
                 f"{r['strict']} |")
    if s["R3_controls_losing_a_dimension"]:
        L += ["", "**WIRING BUG** - a control lost a dimension, impossible by "
              "construction: " + ", ".join(s["R3_controls_losing_a_dimension"])]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-resume", action="store_true")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args(argv)

    if args.report:
        recs = [json.loads(p.read_text(encoding="utf-8"))
                for p in sorted(RAW_DIR.glob("*.json"))]
    else:
        recs = run(resume=not args.no_resume)
    if not recs:
        log("nothing to summarise")
        return 1
    s = summarise(recs)
    exp = config.JOURNAL_DIR / "experiments"
    (exp / "E17_results.json").write_text(json.dumps(s, indent=2), encoding="utf-8")
    md = render(s)
    (exp / "E17_results.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
