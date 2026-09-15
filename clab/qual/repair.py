"""A second, targeted look at the sub-tests the first call declined to score.

The production call gives every component ONE embedding query and eight chunks. E15
measured what that costs: `economies_of_scale` was null for 61% of the universe, and
scored for 18 of 20 companies as soon as it had a query of its own. E16 turned that into a
conditional repair pass, and E17 established the rule this module enforces:

    a repaired sub-test counts ONLY if it carries a verbatim quote that verifies
    against the pack it was given.

Everything else about the rubric is unchanged. A repair may only fill a `null`; it can
never overwrite a score the production call produced, never raise a score, and never lower
the BQ floor. Unquoted repairs are stored - the workbook shows them - but they do not
reach `earned`, `available`, `coverage` or the band.

Cache shape. Repairs live beside the original call inside the same payload, never on top
of it:

    {"dimensions": {...},                       # the production call, untouched
     "repairs": {"economies_of_scale": {"score": 3, "rationale": "...",
                 "quote": "...", "gate": "strict", "overlap": 1.0,
                 "source": "repair", "run_id": "...", "generated_at": "..."}}}
"""
from __future__ import annotations

import re

from ..net import utc_now_iso
from ..scoring import rubric
from ..scoring.repair_merge import (MG_LLM, REPAIRS_KEY, SCORING_GATE, SPEC,
                                    merged_items, null_items, repaired_points,
                                    repaired_summary)
from . import evidence as ev_mod
from . import ollama, prompts
from .scorer import _token_overlap, extract_json

#: chunks retrieved per null sub-test, as run in E15-E18
CHUNKS_PER_ITEM = 2
#: today's production rule, kept so the two can be compared rather than swapped silently
PRODUCTION_OVERLAP = 0.60
TIGHT_OVERLAP = 0.90
#: One retrieval query per sub-test, each naming the language a 10-K actually uses rather
#: than the rubric's label. Pre-registered in E15 (BQ) and E18 (SG, MG) before any result
#: was seen; changing one changes what the repair can find, so treat it as rubric-adjacent
#: and record the change in the journal.
QUERIES = {
    "BQ": {
        "network_effects": ("platform users, marketplace participants, subscribers, "
                            "merchants and buyers, ecosystem, more users attract more "
                            "customers, two-sided marketplace, installed base"),
        "manufacturing_complexity": ("manufacturing facilities, plants, production "
                                     "process, capacity utilisation, fabrication, supply "
                                     "chain, specialised equipment, yield, tooling, "
                                     "capital intensity"),
        "data_advantages": ("proprietary data, data sets, analytics, machine learning "
                            "models, customer usage data, telemetry, algorithms trained "
                            "on our data, information advantage"),
        "economies_of_scale": ("scale, fixed cost leverage, purchasing power, unit "
                               "costs, operating leverage, distribution density, cost "
                               "per unit declines with volume, largest in the industry"),
    },
    "SG": {
        "tam_expanding": ("total addressable market, industry size and growth rate, "
                          "market opportunity, penetration of a larger market"),
        "revenue_growth_sustainable": ("revenue increased, growth rate, organic growth, "
                                       "same-store sales, comparable sales, net sales "
                                       "grew"),
        "demand_drivers_3_5yr": ("demand drivers, long term trends, customer adoption, "
                                 "regulation driving demand, replacement cycle, "
                                 "multi-year outlook"),
        "capacity_backlog_contracts": ("backlog, remaining performance obligations, "
                                       "contracted revenue, capacity expansion, new "
                                       "plants, bookings, order book"),
        "secular_not_cyclical": ("secular trend, structural shift, cyclical demand, end "
                                 "market cyclicality, recession sensitivity, commodity "
                                 "prices"),
        "multiple_independent_drivers": ("segments, product lines, geographies, "
                                         "diversified revenue streams, multiple end "
                                         "markets"),
    },
    # E24: aimed at the PROXY, which is where these facts live. Before the proxy was in
    # the pack these queries searched a 10-K that does not state who founded the company
    # or what the CEO owns - `founder_led` was scored 9 times in 200.
    # E25: MG has no model-scored sub-tests left to repair. The proxy queries that
    # lived here are preserved in E24's registration if the block ever returns.
    "MG": {},
}

_TASK = {
    "SG": "score STRUCTURAL GROWTH for this company.",
    "BQ": "score these moat dimensions for this company.",
    "MG": "score these MANAGEMENT QUALITY attributes for this company's CEO.",
}


# ------------------------------------------------------------------ verification
def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def verify(quote: str | None, pack: str) -> dict:
    """Every gate's verdict for one quote, so the choice of gate stays visible."""
    if not quote or not isinstance(quote, str):
        return {"has_quote": False, "strict": False, "tight": False,
                "production": False, "overlap": 0.0}
    ov = _token_overlap(quote, pack)
    return {
        "has_quote": True,
        "strict": _norm(quote)[:600] in _norm(pack),
        "tight": ov >= TIGHT_OVERLAP,
        "production": ov >= PRODUCTION_OVERLAP,
        "overlap": round(ov, 3),
    }


# ------------------------------------------------------------------ generating
def targeted_body(ctx, keys, component: str, pool: dict) -> tuple[str, dict]:
    """Fact sheet plus CHUNKS_PER_ITEM chunks retrieved per NULL sub-test.

    `pool` is `evidence.chunk_pool(ctx)` - a dict, not a tuple. The research modules that
    proved this out carried their own tuple-shaped copy; production reads the real one.
    """
    chunks = pool["chunks"]
    vectors = pool["vectors"]
    fmeta = pool["filing"]
    queries = QUERIES[component]
    picked: list[str] = []
    methods: dict[str, str] = {}
    for key in keys:
        query = queries.get(key)
        if not query:
            continue
        got, method = ev_mod.retrieve(chunks, query, k=CHUNKS_PER_ITEM,
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
    return "\n".join(parts), {"n_chunks_picked": len(picked), "retrieval": methods}


def repair_prompt(component: str, evidence: str,
                  items: list[tuple[str, str, int]]) -> str:
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


def parse_repair(raw: str, pack: str, items: list[tuple[str, str, int]],
                 *, run_id: str) -> dict:
    """One repair record per sub-test the model answered.

    Out of range is REJECTED, never clamped (rubric rule 4), and a rejected value is kept
    on the record so the workbook can show that the model answered and the parser refused.
    """
    data = extract_json(raw)
    out: dict[str, dict] = {}
    if not data:
        return out
    now = utc_now_iso()
    for key, _label, mx in items:
        rec = data.get(key)
        if not isinstance(rec, dict):
            continue
        raw_score = rec.get("score")
        score, rejected = None, None
        if isinstance(raw_score, bool):
            rejected = raw_score
        elif isinstance(raw_score, (int, float)) and float(raw_score).is_integer():
            v = int(raw_score)
            score, rejected = (v, None) if 0 <= v <= mx else (None, raw_score)
        elif isinstance(raw_score, str) and raw_score.strip().isdigit():
            v = int(raw_score.strip())
            score, rejected = (v, None) if 0 <= v <= mx else (None, raw_score)
        elif raw_score is not None:
            rejected = raw_score
        quote = rec.get("evidence") if isinstance(rec.get("evidence"), str) else None
        v = verify(quote, pack)
        gate = ("strict" if v["strict"] else
                "tight" if v["tight"] else
                "production" if v["production"] else
                "unverified" if v["has_quote"] else "no_quote")
        out[key] = {
            "score": score,
            "rejected_value": rejected,
            "rationale": str(rec.get("rationale") or "")[:300],
            "quote": (quote or "")[:600] or None,
            "gate": gate,
            "overlap": v["overlap"],
            "source": "repair",
            "run_id": run_id,
            "generated_at": now,
        }
    return out


def repair_component(ctx, component: str, payload: dict, pool, *,
                     run_id: str, model: str | None = None,
                     timeout: float = 900.0) -> tuple[dict, dict]:
    """One repair call for one component. Returns (repairs, meta).

    `pool` is `evidence.chunk_pool(ctx)` - passed in rather than rebuilt, because it is
    the expensive step and all three components share it.
    """
    nulls = null_items(payload, component)
    # Only sub-tests this module has a retrieval query for. Asking about one it cannot
    # retrieve evidence for is asking the model to answer from nothing, which is how an
    # abstention becomes a guess - and BQ's queries cover the four dimensions E12 named,
    # not all eleven, because those four are what E15-E17 actually tested.
    nulls = [n for n in nulls if n[0] in QUERIES[component]]
    if not nulls:
        return {}, {"skipped": "no null sub-test has a targeted query"}
    body, meta = targeted_body(ctx, [k for k, _l, _m in nulls], component, pool)
    raw = ollama.chat(repair_prompt(component, body, nulls),
                      system=prompts.SYSTEM, model=model, timeout=timeout)
    reps = parse_repair(raw, body, nulls, run_id=run_id)
    meta.update({"nulls": [k for k, _l, _m in nulls], "n_repairs": len(reps)})
    return reps, meta
