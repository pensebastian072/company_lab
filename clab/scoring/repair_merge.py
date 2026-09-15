"""Folding a repaired sub-test into a cached payload. Pure dict logic, no LLM.

This lives in `clab/scoring/` rather than beside the generator in `clab/qual/repair.py`
for one reason: hard rule 5. `clab/ui/app.py` must never pull in `clab.qual` - a test
asserts it in a fresh interpreter - and the scorers the UI imports need to read repairs.
So the READING half has no dependency on ollama, evidence or the network, and the
GENERATING half imports this.

The rules a repair obeys, all enforced here:

  * it may only fill a `null`; a sub-test the production call scored is never touched;
  * it counts only when its verbatim quote cleared the scoring gate;
  * an unquoted repair is kept on the payload and shown in the workbook, but it does not
    reach `earned`, `available`, `coverage` or the band.
"""
from __future__ import annotations

from . import rubric

REPAIRS_KEY = "repairs"

#: The gate a repair must clear to affect a score. `strict` is a normalised substring
#: match. E17 measured that when this model quotes at all it copies exactly (median token
#: overlap 1.0), so strict costs only 4 of the 33 sub-tests the production 0.60 rule keeps.
SCORING_GATE = "strict"

MG_LLM = tuple((k, lbl) for k, lbl, src in rubric.MG_CEO_ATTRIBUTES if src == "llm")

#: component -> (payload bucket, ((key, label, max), ...))
SPEC = {
    "SG": ("scores", tuple(rubric.SG_SUBTESTS)),
    "BQ": ("dimensions", tuple((k, lbl, rubric.BQ_DIMENSION_MAX)
                               for k, lbl in rubric.BQ_DIMENSIONS)),
    "MG": ("ceo", tuple((k, lbl, rubric.MG_CEO_ATTRIBUTE_MAX) for k, lbl in MG_LLM)),
}


def null_items(payload: dict, component: str) -> list[tuple[str, str, int]]:
    """Sub-tests with no score. The only ones a repair is allowed to touch."""
    bucket, spec = SPEC[component]
    items = payload.get(bucket) or {}
    out = []
    for key, label, mx in spec:
        rec = items.get(key)
        if not isinstance(rec, dict) or rec.get("score") is None:
            out.append((key, label, mx))
    return out


def merged_items(payload: dict, bucket: str, *, gate: str = SCORING_GATE) -> dict:
    """The production call's items with gate-passing repairs filled into the nulls.

    The ONLY place a repair reaches a score. A repair that collides with a non-null
    production score is skipped rather than resolved - the collision would mean the
    generator was handed a stale payload, and silently preferring one of the two would
    hide that.
    """
    items = dict(payload.get(bucket) or {})
    for key, rep in (payload.get(REPAIRS_KEY) or {}).items():
        if not isinstance(rep, dict) or rep.get("score") is None:
            continue
        if rep.get("gate") != gate:
            continue
        existing = items.get(key)
        if isinstance(existing, dict) and existing.get("score") is not None:
            continue
        items[key] = {
            "score": rep.get("score"),
            "rationale": rep.get("rationale", ""),
            "evidence": rep.get("quote"),
            "evidence_unverified": False,        # it cleared the gate by construction
            "rejected_value": None,
            # `source` stays "llm": SubTest.is_llm and the UI's purple chip both test it,
            # and a repaired point is MORE model-generated, not less. Labelling it
            # "repair" here dropped the chip and could flip `sg_is_llm` to False in the
            # parquet - the opposite of the disclosure this was built for.
            "source": "llm",
            "origin": "repair",
            "repair_gate": rep.get("gate"),
            "repair_run_id": rep.get("run_id"),
        }
    return items


def repaired_summary(payload: dict, bucket: str | None = None) -> dict:
    """What a second look added, split by whether it could cite the filing.

    A gate-passing repair that collided with a production score is reported as
    `collided`, not as `quoted`: it changed no score, and folding it into the recovered
    list would hide the stale-payload signal the collision exists to raise.
    """
    reps = (payload or {}).get(REPAIRS_KEY) or {}
    landed = merged_items(payload, bucket) if bucket else {}
    quoted, unquoted, collided = [], [], []
    for key, rep in reps.items():
        if not isinstance(rep, dict) or rep.get("score") is None:
            continue
        if rep.get("gate") != SCORING_GATE:
            unquoted.append(key)
        elif bucket and (landed.get(key) or {}).get("origin") != "repair":
            collided.append(key)
        else:
            quoted.append(key)
    return {"quoted": sorted(quoted), "unquoted": sorted(unquoted),
            "collided": sorted(collided)}


#: what a component is worth on the 100-point framework, so a "repaired points" figure
#: can never exceed the component it belongs to
COMPONENT_MAX = {"SG": 20, "BQ": 15, "MG": rubric.MG_CEO_POINTS}


def repaired_points(payload: dict, component: str) -> tuple[int, int]:
    """(points backed by a verified quote, points offered without one).

    Points rather than sub-test counts, because SG's sub-tests are worth 2-4 each and
    counting them would flatter SG against MG's flat 2.

    Two corrections a naive sum gets wrong. BQ's eleven dimensions are worth 5 raw each
    but map onto a FIFTEEN-point component by their mean, so summing maxima reported up
    to 20 repaired points against a 15-point component - and a repaired dimension can
    even lower BQ's score, since the mapping is a mean. And a repair that collided with a
    production score is skipped by `merged_items`, so counting it here would credit points
    that never landed. Both are capped and filtered rather than explained away.
    """
    bucket, spec = SPEC[component]
    maxes = {k: mx for k, _lbl, mx in spec}
    landed = merged_items(payload, bucket)
    quoted = unquoted = 0
    for key, rep in ((payload or {}).get(REPAIRS_KEY) or {}).items():
        if not isinstance(rep, dict) or rep.get("score") is None or key not in maxes:
            continue
        if rep.get("gate") == SCORING_GATE:
            if (landed.get(key) or {}).get("origin") != "repair":
                continue          # a collision: the production score won, nothing landed
            quoted += maxes[key]
        else:
            unquoted += maxes[key]
    cap = COMPONENT_MAX.get(component, 0)
    return min(quoted, cap), min(unquoted, cap)
