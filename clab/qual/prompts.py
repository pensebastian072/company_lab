"""Prompts and the parse contract.

Three prompts, not one. A 7B model asked to hold 6 + 11 + 2 sub-test rubrics at
once degrades badly; split, it holds each rubric.

Every prompt ends in a closed-vocabulary JSON schema with integer-only scores and
an explicit `null` channel. `null` matters: without a sanctioned way to say "the
material does not support a judgement", a model invents one.
"""
from __future__ import annotations

from ..scoring import rubric

SYSTEM = (
    "You are a disciplined equity analyst scoring one company against a fixed "
    "rubric. You judge ONLY from the material provided. You never invent facts, "
    "never use knowledge about this company from outside the material, and when the "
    "material does not support a judgement you return null instead of guessing. "
    "You reply with a single JSON object and no other text."
)

_RULES = """
RULES
- Score ONLY from the material above. If it does not support a sub-test, use null.
- Every score is an INTEGER within the stated range. Never a decimal.
- "evidence" must be a short VERBATIM quote copied from the material above. If you
  cannot quote it, use null for that sub-test's score.
- "rationale" is one sentence, your own words, under 200 characters.
- Do not reward a company for being large or famous. Reward what the material shows.
- Reply with ONE JSON object. No prose, no markdown, no code fences.
""".strip()


def sg_prompt(evidence: str) -> str:
    fields = ",\n ".join(
        f'"{key}": {{"score": <integer 0..{mx} or null>, "rationale": "<one sentence>", '
        f'"evidence": "<verbatim quote or null>"}}'
        for key, _label, mx in rubric.SG_SUBTESTS
    )
    lines = "\n".join(f"  - {key} (0..{mx}): {label}"
                      for key, label, mx in rubric.SG_SUBTESTS)
    return f"""{evidence}

TASK: score STRUCTURAL GROWTH for this company.

You are answering: what will demand for this company's products look like in three
to five years, and is that growth durable rather than a single cycle?

SUB-TESTS
{lines}

{_RULES}

Respond with ONLY this JSON object:
{{{fields}}}"""


def bq_prompt(evidence: str) -> str:
    dims = "\n".join(f"  - {key}: {label}" for key, label in rubric.BQ_DIMENSIONS)
    fields = ",\n  ".join(
        f'"{key}": {{"score": <integer 0..{rubric.BQ_DIMENSION_MAX} or null>, '
        f'"rationale": "<one sentence>"}}'
        for key, _label in rubric.BQ_DIMENSIONS
    )
    return f"""{evidence}

TASK: score BUSINESS QUALITY AND MOAT for this company.

Rate each moat dimension from 0 to {rubric.BQ_DIMENSION_MAX}, where 0 means a
commodity business that is easily replaced and {rubric.BQ_DIMENSION_MAX} means it
would be exceptionally difficult for a well-funded competitor to displace.

DIMENSIONS
{dims}

Then answer the decisive question in one or two sentences:
  "{rubric.BQ_KILLER_QUESTION}"
A specific, mechanism-level answer is worth far more than a flattering one. If the
material does not support an answer, say so plainly.

{_RULES}

Respond with ONLY this JSON object:
{{"dimensions": {{
  {fields}
 }},
 "killer_answer": "<one or two sentences>",
 "summary": "<one sentence on the overall moat>",
 "evidence": "<verbatim quote supporting the strongest moat, or null>"}}"""


def mg_prompt(evidence: str) -> str:
    attrs = [(k, lbl) for k, lbl, src in rubric.MG_CEO_ATTRIBUTES if src == "llm"]
    lines = "\n".join(f"  - {k} (0..{rubric.MG_CEO_ATTRIBUTE_MAX}): {lbl}"
                      for k, lbl in attrs)
    fields = ",\n  ".join(
        f'"{k}": {{"score": <integer 0..{rubric.MG_CEO_ATTRIBUTE_MAX} or null>, '
        f'"rationale": "<one sentence>"}}' for k, _lbl in attrs
    )
    return f"""{evidence}

TASK: score MANAGEMENT QUALITY for this company.

Score only the five attributes below. Two further attributes - whether management
hits guidance, and how the business fared in past downturns - are measured directly
from the filings and the reported surprise history, so do NOT score those.

ATTRIBUTES ({rubric.MG_CEO_ATTRIBUTE_MAX} = strongly true, 0 = not true)
{lines}

{_RULES}

Respond with ONLY this JSON object:
{{"ceo": {{
  {fields}
 }},
 "ceo_summary": "<one sentence on management overall>",
 "evidence": "<verbatim quote about management or leadership, or null>"}}"""


PROMPTS = {"SG": sg_prompt, "BQ": bq_prompt, "MG": mg_prompt}


def prompt_for(component: str, evidence: str) -> str:
    return PROMPTS[component](evidence)

# ------------------------------------------------------------------ structured output
def _scored_item(max_points: int, *, with_evidence: bool = False) -> dict:
    """One {"score": int|null, "rationale": str} object.

    `null` is a FIRST-CLASS type here, not an afterthought. The whole point of the
    schema is that "the material does not support a judgement" stays structurally
    expressible - a schema that forced an integer would convert every abstention into a
    fabricated number, which is the opposite of what this pipeline needs.
    """
    item = {
        "type": "object",
        "properties": {
            "score": {"type": ["integer", "null"], "minimum": 0, "maximum": max_points},
            "rationale": {"type": "string"},
        },
        "required": ["score", "rationale"],
    }
    if with_evidence:
        # Per-item `evidence` is NOT optional decoration WHERE THE PARSER READS IT.
        # `parse_sg` calls `_verify_evidence(rec.get("evidence"), pack)` per sub-test -
        # the containment check that is the concrete defence against a fabricated
        # citation. Omit it and every quote is None, `evidence_unverified` is False for
        # every sub-test, and the unverified-evidence rate reads 0.0% BY CONSTRUCTION:
        # the metric looks like a pass while having been destroyed.
        #
        # `parse_bq` and `parse_mg` read evidence only ONCE, at the top level, so asking
        # for it per dimension there would spend tokens on a field the parser discards.
        # The schema mirrors each parser exactly rather than being uniform.
        item["properties"]["evidence"] = {"type": ["string", "null"]}
    return item


def schema_for(component: str) -> dict:
    """JSON schema for one component, generated FROM THE RUBRIC.

    Ollama constrains generation to a schema passed as `format`, which makes three
    failure modes structurally impossible rather than merely discouraged: a parse
    failure, a missing key, and a prose preamble before the JSON. Measured 2026-08-28:
    LFM2.5-2.6B-Finance produced 3,417 characters of reasoning and was truncated before
    reaching any JSON, giving a 77.8% parse-failure rate that was a format artefact and
    not a judgement.

    Generated rather than hand-written so it cannot drift from the prompt the way the
    "50 of 100 points" labels drifted from the framework (E33).
    """
    comp = (component or "").upper()
    if comp == "SG":
        # SG is FLAT - the sub-test keys sit at the top level with no wrapper. This is
        # not a style choice: `sg_prompt` asks for `{<key>: {...}, ...}` and `parse_sg`
        # reads `data.get(key)` directly, with no fallback of the kind `parse_bq` has.
        # An earlier draft of this schema wrapped SG in `{"subtests": {...}}`, and
        # because a schema is ENFORCED the model complied exactly - so AAPL's SG came
        # back `parse_ok: true` with `scores: {}` after 26.4 s of GPU, and every company
        # would have silently lost all 20 SG points while the run reported success.
        # Caught by the first probe, 2026-08-29.
        props = {s[0]: _scored_item(int(s[-1]), with_evidence=True)
                 for s in rubric.SG_SUBTESTS}
        props["summary"] = {"type": "string"}
        return {"type": "object", "properties": props,
                "required": [s[0] for s in rubric.SG_SUBTESTS]}
    if comp == "BQ":
        keys = [k for k, _l in rubric.BQ_DIMENSIONS]
        props = {k: _scored_item(rubric.BQ_DIMENSION_MAX) for k in keys}
        return {"type": "object",
                "properties": {"dimensions": {"type": "object", "properties": props,
                                              "required": keys},
                               "killer_answer": {"type": ["string", "null"]},
                               "summary": {"type": "string"},
                               "evidence": {"type": ["string", "null"]}},
                "required": ["dimensions"]}
    if comp == "MG":
        keys = [k for k, _lbl, src in rubric.MG_CEO_ATTRIBUTES if src == "llm"]
        props = {k: _scored_item(rubric.MG_CEO_ATTRIBUTE_MAX) for k in keys}
        return {"type": "object",
                "properties": {"ceo": {"type": "object", "properties": props,
                                       "required": keys},
                               "ceo_summary": {"type": "string"},
                               "evidence": {"type": ["string", "null"]}},
                "required": ["ceo"]}
    raise ValueError(f"no schema for component {component!r}")
