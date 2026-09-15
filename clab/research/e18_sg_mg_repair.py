"""E18 - does targeted retrieval repair SG and MG, the way it repaired BQ?

Registered in `journal/experiments/E18_sg_mg_preregistration.md`.

Same shape as E17, which is the BQ arm that survived a citation requirement: one embedding
query per NULL sub-test, one call per component carrying only that company's nulls, and a
recovered sub-test counts only if its verbatim quote verifies against the pack it was
given.

The two components differ in a way the write-up must respect:

  * SG's six sub-tests are worth 4/4/4/3/3/2 points and are scored independently, so its
    availability gain is the sum of the points recovered;
  * MG's five LLM attributes are worth 2 each behind a floor of 4 (`MG_MIN_ATTRIBUTES_
    SCORED`), so the CEO block is all-or-nothing - recovering three attributes when the
    base call scored none is worth ZERO availability.

Research only. Does not write the qual cache, the scores table or the rubric.

    python -m clab.research.e18_sg_mg_repair
    python -m clab.research.e18_sg_mg_repair --report
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import time

from .. import config
from ..net import log_stamp, read_json, utc_now_iso
from ..qual import evidence as ev_mod
from ..qual import ollama, prompts
from ..qual.scorer import extract_json
from ..runner import engine
from ..scoring import rubric
from .e15_targeted_retrieval import CHUNKS_PER_DIM, _chunk_pool
from .e16_bq_repair_pass import RAW_DIR as E16_RAW
from .e17_verified_repair import gates

RAW_DIR = config.JOURNAL_DIR / "experiments" / "E18_raw"

#: LLM attributes only. The measured two (hits_guidance, navigated_downturns) come from
#: the filed series and are never asked of a model.
MG_LLM = tuple((k, lbl) for k, lbl, src in rubric.MG_CEO_ATTRIBUTES if src == "llm")

#: One query per sub-test, written before any result was seen, each naming the language a
#: 10-K actually uses rather than the rubric's label.
SG_QUERIES = {
    "tam_expanding": ("total addressable market, industry size and growth rate, market "
                      "opportunity, penetration of a larger market"),
    "revenue_growth_sustainable": ("revenue increased, growth rate, organic growth, "
                                   "same-store sales, comparable sales, net sales grew"),
    "demand_drivers_3_5yr": ("demand drivers, long term trends, customer adoption, "
                             "regulation driving demand, replacement cycle, multi-year "
                             "outlook"),
    "capacity_backlog_contracts": ("backlog, remaining performance obligations, "
                                   "contracted revenue, capacity expansion, new plants, "
                                   "bookings, order book"),
    "secular_not_cyclical": ("secular trend, structural shift, cyclical demand, end "
                             "market cyclicality, recession sensitivity, commodity "
                             "prices"),
    "multiple_independent_drivers": ("segments, product lines, geographies, diversified "
                                     "revenue streams, multiple end markets"),
}
MG_QUERIES = {
    "founder_led": ("founder, co-founder, founded the company, has served as chief "
                    "executive officer since inception"),
    "tenure": ("has served as our chief executive officer since, joined the company in, "
               "years of service, appointed in"),
    "ownership": ("beneficial ownership, shares held by executive officers and "
                  "directors, stock ownership guidelines, insider ownership"),
    "execution_history": ("under his leadership, executed the strategy, delivered, "
                          "integration of acquisitions, operational improvements, "
                          "restructuring results"),
    "industry_expertise": ("prior to joining, previously served as, experience in the "
                           "industry, held positions at, background in"),
}
SPEC = {
    "SG": {"bucket": "scores", "queries": SG_QUERIES,
           "items": tuple((k, lbl, mx) for k, lbl, mx in rubric.SG_SUBTESTS)},
    "MG": {"bucket": "ceo", "queries": MG_QUERIES,
           "items": tuple((k, lbl, rubric.MG_CEO_ATTRIBUTE_MAX) for k, lbl in MG_LLM)},
}


from .e22_judgement_backtest import safe_stem as _safe_stem


def log(msg: str) -> None:
    print(f"[{log_stamp()}] {msg}", flush=True)


def best_payload(cik: str, component: str) -> dict:
    """Highest-scoring cached payload for one company and component.

    A CIK holds several payloads because the cache key hashes the rendered pack, so a
    re-generation writes a NEW file beside the old one - the same trap
    `clab/research/bq_abstention.py` documents.
    """
    bucket = SPEC[component]["bucket"] if component in SPEC else "dimensions"
    best: tuple[int, dict] = (-1, {})
    for path in config.QUAL_DIR.glob(f"{cik}_{component}_*.json"):
        payload = read_json(path)
        if not isinstance(payload, dict):
            continue
        items = payload.get(bucket) or {}
        n = sum(1 for v in items.values()
                if isinstance(v, dict) and v.get("score") is not None)
        if n > best[0]:
            best = (n, payload)
    return best[1]


def null_items(payload: dict, component: str) -> list[tuple[str, str, int]]:
    """Sub-tests with no score - the only ones a repair may touch."""
    items = (payload.get(SPEC[component]["bucket"]) or {})
    out = []
    for key, label, mx in SPEC[component]["items"]:
        rec = items.get(key)
        if not isinstance(rec, dict) or rec.get("score") is None:
            out.append((key, label, mx))
    return out


def scored_keys(payload: dict, component: str) -> set:
    items = (payload.get(SPEC[component]["bucket"]) or {})
    return {k for k, v in items.items()
            if isinstance(v, dict) and v.get("score") is not None}


def targeted_body(ctx, chunks, vectors, fmeta, keys, queries) -> tuple[str, dict]:
    """Fact sheet + CHUNKS_PER_DIM chunks retrieved per NULL sub-test."""
    picked: list[str] = []
    methods = {}
    for key in keys:
        got, method = ev_mod.retrieve(chunks, queries[key], k=CHUNKS_PER_DIM,
                                      doc_vectors=vectors)
        methods[key] = method
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


_TASK = {
    "SG": "score STRUCTURAL GROWTH for this company.",
    "MG": "score these MANAGEMENT QUALITY attributes for this company's CEO.",
}


def repair_prompt(component: str, evidence: str,
                  items: list[tuple[str, str, int]]) -> str:
    """Only the null sub-tests, each REQUIRING a verbatim quote that gates the score."""
    lines = "\n".join(f"  - {k} (0..{mx}): {lbl}" for k, lbl, mx in items)
    fields = ",\n  ".join(
        f'"{k}": {{"score": <integer 0..{mx} or null>, '
        f'"rationale": "<one sentence>", "evidence": "<verbatim quote or null>"}}'
        for k, _lbl, mx in items)
    return f"""{evidence}

TASK: {_TASK[component]}

SUB-TESTS
{lines}

{prompts._RULES}
- The "evidence" quote is CHECKED against the material above. A score whose quote is not
  found there is DISCARDED. Copy the words exactly; do not paraphrase, summarise or
  reconstruct them.

Respond with ONLY this JSON object:
{{
  {fields}
}}"""


def parse_repair(raw: str, pack: str,
                 items: list[tuple[str, str, int]]) -> dict:
    """Per-sub-test score + quote + every gate's verdict."""
    data = extract_json(raw)
    out = {"parse_ok": data is not None, "items": {}}
    if not data:
        return out
    for key, _lbl, mx in items:
        rec = data.get(key)
        if not isinstance(rec, dict):
            continue
        raw_score = rec.get("score")
        score = None
        if isinstance(raw_score, bool):
            score = None
        elif isinstance(raw_score, (int, float)) and float(raw_score).is_integer():
            v = int(raw_score)
            # Out of range is REJECTED, never clamped - rubric rule 4.
            score = v if 0 <= v <= mx else None
        elif isinstance(raw_score, str) and raw_score.strip().isdigit():
            v = int(raw_score.strip())
            score = v if 0 <= v <= mx else None
        quote = rec.get("evidence") if isinstance(rec.get("evidence"), str) else None
        out["items"][key] = {"score": score, "max": mx,
                             "quote": (quote or "")[:600] or None,
                             "gates": gates(quote, pack)}
    return out


def accepted(rec: dict, gate: str) -> dict:
    """{key: max_points} for sub-tests this repair may contribute under one gate."""
    return {k: v["max"] for k, v in (rec.get("items") or {}).items()
            if v.get("score") is not None and v["gates"].get(gate)}


def availability_gain(component: str, base_keys: set, won: dict) -> int:
    """Points of AVAILABILITY the repair actually buys.

    SG's sub-tests stand alone, so the gain is the points recovered. MG's CEO block is
    all-or-nothing behind a floor of 4 attributes: recovering three when the base scored
    none buys nothing, and recovering one when the base scored three buys the whole
    8-point block.
    """
    if component == "SG":
        return sum(won.values())
    before = len(base_keys)
    after = len(base_keys | set(won))
    if before >= rubric.MG_MIN_ATTRIBUTES_SCORED:
        return 0
    return rubric.MG_CEO_POINTS if after >= rubric.MG_MIN_ATTRIBUTES_SCORED else 0


def run_one(row: dict) -> dict:
    as_of = utc_now_iso()
    ctx, _ = engine.build_context(row["ticker"], row["cik"], as_of=as_of,
                                  name=row.get("name", ""), sector=row.get("sector", ""),
                                  sub_industry=row.get("sub_industry", ""))
    chunks, vectors, fmeta = _chunk_pool(ctx)
    out = {"ticker": row["ticker"], "cik": row["cik"], "sector": row.get("sector", ""),
           "arm": row["arm"], "components": {}}
    for component in ("SG", "MG"):
        payload = best_payload(row["cik"], component)
        nulls = null_items(payload, component)
        base = scored_keys(payload, component)
        rec = {"base_scored": sorted(base), "nulls": [k for k, _l, _m in nulls]}
        if not nulls:
            rec.update({"skipped": "nothing null", "secs": 0.0})
            out["components"][component] = rec
            continue
        t0 = time.perf_counter()
        body, tmeta = targeted_body(ctx, chunks, vectors, fmeta,
                                    [k for k, _l, _m in nulls],
                                    SPEC[component]["queries"])
        parsed = parse_repair(
            ollama.chat(repair_prompt(component, body, nulls),
                        system=prompts.SYSTEM, timeout=900.0), body, nulls)
        rec.update({
            "secs": round(time.perf_counter() - t0, 1),
            "parse_ok": parsed["parse_ok"],
            "items": parsed["items"],
            "targeted_meta": tmeta,
            "gain_strict": availability_gain(component, base,
                                             accepted(parsed, "strict")),
            "gain_no_gate": availability_gain(component, base,
                                              accepted(parsed, "has_quote")),
        })
        out["components"][component] = rec
    return out


def sample_rows() -> list[dict]:
    return [{"ticker": r["ticker"], "cik": r["cik"], "sector": r["sector"],
             "name": "", "sub_industry": "", "arm": r["arm"]}
            for r in (json.loads(p.read_text(encoding="utf-8"))
                      for p in sorted(E16_RAW.glob("*.json")))]


def run(*, resume: bool = True, limit: int = 0) -> list[dict]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    rows = sample_rows()
    if limit:
        rows = rows[:limit]
    log(f"{len(rows)} companies "
        f"({sum(1 for r in rows if r['arm'] == 'under')} under-floor)")
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
            sg = rec["components"].get("SG", {})
            mg = rec["components"].get("MG", {})
            log(f"  {rec['ticker']:<6} SG +{sg.get('gain_strict', 0):>2} pts "
                f"({len(sg.get('nulls', []))} null)  "
                f"MG +{mg.get('gain_strict', 0):>2} pts "
                f"({len(mg.get('nulls', []))} null)  "
                f"{sg.get('secs', 0) + mg.get('secs', 0):.0f}s  ({i}/{len(rows)})")
    return out


def summarise(recs: list[dict]) -> dict:
    out: dict = {"n": len(recs), "components": {}}
    for component in ("SG", "MG"):
        rs = [r["components"].get(component) or {} for r in recs]
        live = [x for x in rs if x.get("items")]
        gains = [x.get("gain_strict", 0) for x in rs]
        gains_ng = [x.get("gain_no_gate", 0) for x in rs]
        proposed = sum(1 for x in live for v in x["items"].values()
                       if v.get("score") is not None)
        no_quote = sum(1 for x in live for v in x["items"].values()
                       if v.get("score") is not None and not v["gates"].get("has_quote"))
        per_item: dict[str, dict] = {}
        for x in live:
            for k, v in x["items"].items():
                d = per_item.setdefault(k, {"proposed": 0, "strict": 0,
                                            "production": 0, "null_in": 0})
                d["null_in"] += 1
                if v.get("score") is None:
                    continue
                d["proposed"] += 1
                d["strict"] += bool(v["gates"].get("strict"))
                d["production"] += bool(v["gates"].get("production"))
        kept = {g: sum(len(accepted(x, g)) for x in live)
                for g in ("has_quote", "production", "tight", "strict")}
        med = statistics.median(gains) if gains else 0.0
        out["components"][component] = {
            "companies_with_nulls": len(live),
            "median_gain_strict": med,
            "mean_gain_strict": round(statistics.mean(gains), 2) if gains else 0.0,
            "mean_gain_no_gate": (round(statistics.mean(gains_ng), 2)
                                  if gains_ng else 0.0),
            "companies_gaining": sum(1 for g in gains if g > 0),
            "S1_pass": med >= 3,
            "proposed": proposed, "kept_by_gate": kept,
            "scores_with_no_quote": no_quote,
            "per_subtest": dict(sorted(per_item.items(),
                                       key=lambda kv: -kv[1]["strict"])),
            "median_secs": round(statistics.median(
                [x.get("secs", 0.0) for x in rs]), 1) if rs else 0.0,
        }
    secs = [sum((r["components"].get(c) or {}).get("secs", 0.0) for c in ("SG", "MG"))
            for r in recs]
    out["median_secs_per_company"] = round(statistics.median(secs), 1) if secs else 0.0
    out["S4_pass"] = out["median_secs_per_company"] <= 40.0
    # S3: a repair only fills a null, so a control cannot lose a sub-test. Asserted
    # rather than assumed - a violation here is a wiring bug.
    violations = []
    for r in recs:
        for c in ("SG", "MG"):
            x = r["components"].get(c) or {}
            for k in x.get("items", {}):
                if k in set(x.get("base_scored", [])):
                    violations.append(f"{r['ticker']}:{c}:{k}")
    out["S3_repairs_touching_a_scored_subtest"] = violations
    out["S3_pass"] = not violations
    return out


def render(s: dict) -> str:
    def v(f):
        return "PASS" if f else "FAIL"
    L = [f"# E18 results - SG and MG targeted repair ({utc_now_iso()[:10]})", "",
         "ADVISORY / SHADOW. A verified quote means the sentence is in the filing, not",
         "that the score is right. No forward-return grader exists. `promoted` stays "
         "false.", "",
         f"{s['n']} companies (the same sample as E16 and E17).", "",
         "| component | median gain (strict) | companies gaining | S1 >= 3 pts |",
         "|---|---:|---:|---|"]
    for c in ("SG", "MG"):
        d = s["components"][c]
        L.append(f"| {c} | {d['median_gain_strict']} pts | "
                 f"{d['companies_gaining']} of {d['companies_with_nulls']} | "
                 f"{v(d['S1_pass'])} |")
    L += ["", f"S3 repairs touching an already-scored sub-test: "
          f"{len(s['S3_repairs_touching_a_scored_subtest'])} - {v(s['S3_pass'])}. "
          f"S4 median {s['median_secs_per_company']} s per company - "
          f"{v(s['S4_pass'])}.", ""]
    for c in ("SG", "MG"):
        d = s["components"][c]
        L += [f"## {c}", "",
              f"Mean availability gain {d['mean_gain_strict']} pts strict, "
              f"{d['mean_gain_no_gate']} pts with no gate. "
              f"{d['proposed']} scores proposed, {d['scores_with_no_quote']} of them with "
              f"no quote at all.", "",
              "| kept by gate | " + " | ".join(d["kept_by_gate"]) + " |",
              "|---" * (len(d["kept_by_gate"]) + 1) + "|",
              "| sub-tests | " + " | ".join(str(x) for x in d["kept_by_gate"].values())
              + " |", "",
              "| sub-test | null in | proposed | production 0.60 | strict |",
              "|---|---:|---:|---:|---:|"]
        for k, r in d["per_subtest"].items():
            L.append(f"| {k} | {r['null_in']} | {r['proposed']} | {r['production']} | "
                     f"{r['strict']} |")
        L.append("")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--no-resume", action="store_true")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args(argv)

    if args.report:
        recs = [json.loads(p.read_text(encoding="utf-8"))
                for p in sorted(RAW_DIR.glob("*.json"))]
    else:
        recs = run(resume=not args.no_resume, limit=args.limit)
    if not recs:
        log("nothing to summarise")
        return 1
    s = summarise(recs)
    exp = config.JOURNAL_DIR / "experiments"
    (exp / "E18_results.json").write_text(json.dumps(s, indent=2), encoding="utf-8")
    md = render(s)
    (exp / "E18_results.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
