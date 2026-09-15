"""BQ - Business Quality & Moat /15. Read from the LLM qual cache.

The framework scores 11 moat dimensions 0-5 (55 raw) into a 15-point component
without saying how to map them. Resolution (rubric A2):

    BQ = round(mean(scored dimensions) / 5 * 15),  requiring >= 6 of 11 scored

Mean rather than sum, because a business with two overwhelming moats (network
effects plus switching costs) should not rank below one with eleven weak ones - a
sum punishes focus. All 11 raw scores are stored and rendered, so the user can
rescore from raw if they disagree with that call.

The killer question - "if this industry doubles, why does THIS company win?" -
carries no points but is required, and is rendered at the top of the BQ block. A
weak answer there is the most useful thing on the page.
"""
from __future__ import annotations

from . import rubric
from . import repair_merge
from .context import SymbolContext
from .types import ComponentScore, SubTest, no_data, scored

CODE = "BQ"


def score(ctx: SymbolContext) -> ComponentScore:
    payload = (ctx.qual or {}).get("BQ") or {}
    # A repaired dimension is one the production call left null and a targeted second
    # call answered WITH a verbatim quote that verified. Unquoted repairs are on the
    # payload and in the workbook, but `merged_items` does not hand them over.
    dims = repair_merge.merged_items(payload, "dimensions")

    raw_scores: dict[str, int] = {}
    rejected: dict[str, object] = {}
    for key, _label in rubric.BQ_DIMENSIONS:
        rec = dims.get(key)
        if not isinstance(rec, dict):
            continue
        v = rec.get("score")
        if v is None:
            continue
        if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= rubric.BQ_DIMENSION_MAX:
            rejected[key] = v          # rejected, never clamped
            continue
        raw_scores[key] = v

    dimension_detail = {
        key: {
            "label": label,
            "score": raw_scores.get(key),
            "max": rubric.BQ_DIMENSION_MAX,
            "rationale": (dims.get(key) or {}).get("rationale", "")[:300]
            if isinstance(dims.get(key), dict) else "",
            "rejected_value": rejected.get(key),
            "source": "llm",
            "origin": ((dims.get(key) or {}).get("origin") or "first_call")
            if isinstance(dims.get(key), dict) else "first_call",
        }
        for key, label in rubric.BQ_DIMENSIONS
    }

    killer = (payload.get("killer_answer") or "").strip()
    prov = {
        "source": "llm",
        "model": payload.get("model"),
        "prompt_sha1": payload.get("prompt_sha1"),
        "evidence_sha1": payload.get("evidence_sha1"),
        "generated_at": payload.get("generated_at"),
        "mapping": "round(mean(scored dimensions) / 5 * 15)",
        "n_dimensions_scored": len(raw_scores),
        "n_dimensions_rejected": len(rejected),
    }
    inputs = {
        "dimensions": dimension_detail,
        "killer_question": rubric.BQ_KILLER_QUESTION,
        "killer_answer": killer,
        "raw_mean": (sum(raw_scores.values()) / len(raw_scores)) if raw_scores else None,
        "min_dimensions_required": rubric.BQ_MIN_DIMENSIONS_SCORED,
    }

    mx = rubric.COMPONENTS[CODE][1]
    n_dims = len(raw_scores)
    n_total = len(rubric.BQ_DIMENSIONS)
    # E19: the floor is a WEIGHT, not a cliff. It used to award 15 points at 6 of 11
    # dimensions and ZERO below, which deleted 423 companies from the ranking - 184 of
    # them one dimension short, and concentrated in Financials and Real Estate, because
    # a REIT has no manufacturing complexity and a bank has no network effects. Now the
    # component is assessed on what the filing supports: the assessed share is SCORED and
    # the rest is NO_DATA, so a company judged on two dimensions carries 3 points of
    # availability rather than 15 and cannot rank beside a fully assessed one.
    # E19 Amendment 1: ASYMMETRIC. At or above the existing 6-of-11 threshold the
    # component is worth its full 15 points exactly as before - that threshold is the
    # framework's own A2 resolution and was never the problem. Below it, proportional
    # instead of zero. Removing the ceiling as well as the cliff cost 57 companies their
    # band (RJF 0.91 -> 0.79, DTE 0.88 -> 0.76) while rescuing 47, which is not the trade
    # this change was made for.
    if n_dims >= rubric.BQ_MIN_DIMENSIONS_SCORED:
        assessed = mx
    else:
        assessed = int(round(mx * n_dims / n_total))
        if n_dims:
            assessed = max(1, min(assessed, mx))
    inputs["dimensions_assessed"] = n_dims
    inputs["points_assessed"] = assessed
    if n_dims == 0:
        st: SubTest = no_data(
            "bq_moat", "Moat strength across 11 dimensions", mx,
            "no moat dimension could be scored from this filing",
            inputs=inputs, provenance=prov,
        )
    else:
        mean = sum(raw_scores.values()) / len(raw_scores)
        points = int(round(mean / rubric.BQ_DIMENSION_MAX * assessed))
        points = max(0, min(points, assessed))
        st = scored(
            "bq_moat", "Moat strength across 11 dimensions", assessed, points,
            inputs=inputs, provenance=prov,
            rationale=(payload.get("summary") or "")[:300],
            evidence=(payload.get("evidence") or None),
            evidence_unverified=bool(payload.get("evidence_unverified")),
            threshold_note=(f"mean {mean:.2f}/5 over {len(raw_scores)} of {n_total} "
                            f"dimensions -> {points}/{assessed} assessed points"),
        )

    subtests = [st]
    remainder = mx - st.max_points
    if remainder > 0 and n_dims:
        subtests.append(no_data(
            "bq_moat_unassessed", "Moat dimensions the filing did not support", remainder,
            f"{n_total - n_dims} of {n_total} moat dimensions were not scored",
            inputs={"dimensions_missing": sorted(
                k for k, _lbl in rubric.BQ_DIMENSIONS if k not in raw_scores)},
            provenance=prov,
        ))

    comp = ComponentScore(
        code=CODE, label=rubric.COMPONENTS[CODE][0], max_points=mx, subtests=subtests,
        note=(f"{rubric.BQ_KILLER_QUESTION} {killer}" if killer
              else rubric.BQ_KILLER_QUESTION),
    )
    comp.check_points()
    return comp
