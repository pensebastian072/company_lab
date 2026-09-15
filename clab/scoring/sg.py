"""SG - Structural Growth /20. Read from the LLM qual cache; never calls Ollama.

This module contains no judgement of its own. It reads a cached payload written
by clab.qual.scorer, validates every score as an integer inside range, attaches
`source: "llm"` provenance, and returns NO_DATA for everything when the cache is
absent. The batch path and the request path both read cached JSON only.

Where a quantitative check can corroborate an LLM claim it is attached beside the
score as an independent field rather than folded into it - so a contradiction is
visible on the scorecard instead of averaged away.
"""
from __future__ import annotations

from . import rubric
from .context import SymbolContext
from . import repair_merge
from .types import ComponentScore, SubTest, Status, no_data, scored

CODE = "SG"


def _llm_prov(payload: dict, key: str, rec: dict | None = None) -> dict:
    """Provenance for one sub-test.

    A repaired sub-test says so. The UI marks LLM points with a purple chip and the
    workbook carries a `source` column; a point that came from a second, targeted look
    must not be indistinguishable from one the first call produced.
    """
    rec = rec or {}
    prov = {
        "source": rec.get("source") or "llm",
        "origin": rec.get("origin") or "first_call",
        "model": payload.get("model"),
        "prompt_sha1": payload.get("prompt_sha1"),
        "evidence_sha1": payload.get("evidence_sha1"),
        "generated_at": payload.get("generated_at"),
        "subtest": key,
    }
    if rec.get("origin") == "repair":
        prov["repair_gate"] = rec.get("repair_gate")
        prov["repair_run_id"] = rec.get("repair_run_id")
    return prov


def read_llm_subtests(
    ctx: SymbolContext,
    component: str,
    spec: tuple[tuple[str, str, int], ...],
    prefix: str,
) -> list[SubTest]:
    """Shared reader for the three LLM components.

    Rejection rules (all deliberate, all tested):
      - a non-integer score is rejected, not rounded;
      - an out-of-range score is rejected, not clamped - clamping would launder a
        hallucinated 9/4 into a top score;
      - `null` is the model's explicit "I don't know" channel and maps to NO_DATA;
      - evidence that does not overlap the supplied pack is kept but tagged
        evidence_unverified, which the UI renders as a warning chip.
    """
    payload = (ctx.qual or {}).get(component) or {}
    bucket = repair_merge.SPEC.get(component, ("scores", ()))[0]
    scores = repair_merge.merged_items(payload, bucket)
    out: list[SubTest] = []
    for key, label, mx in spec:
        full_key = f"{prefix}_{key}"
        rec = scores.get(key)
        if not isinstance(rec, dict):
            out.append(no_data(full_key, label, mx,
                               "no LLM qualitative score cached for this company"))
            continue
        raw = rec.get("score")
        if raw is None:
            out.append(no_data(full_key, label, mx,
                               rec.get("rationale") or "model declined to score",
                               provenance=_llm_prov(payload, key, rec)))
            continue
        if isinstance(raw, bool) or not isinstance(raw, int) or not 0 <= raw <= mx:
            out.append(no_data(
                full_key, label, mx,
                f"rejected model score {raw!r}: must be an integer in 0..{mx}",
                provenance={**_llm_prov(payload, key, rec), "rejected_value": raw},
            ))
            continue
        out.append(scored(
            full_key, label, mx, raw,
            rationale=(rec.get("rationale") or "")[:300],
            evidence=(rec.get("evidence") or None),
            evidence_unverified=bool(rec.get("evidence_unverified")),
            provenance=_llm_prov(payload, key, rec),
            inputs=rec.get("inputs") or {},
            threshold_note=f"model score {raw}/{mx}",
        ))
    return out


def score(ctx: SymbolContext) -> ComponentScore:
    sts = read_llm_subtests(ctx, "SG", rubric.SG_SUBTESTS, "sg")

    # Independent quantitative corroboration of the growth claim. Attached, not
    # scored - the measured number sits beside the model's integer so a
    # disagreement is visible.
    measured = {
        "revenue_accelerating_measured": ctx.metrics.raw("revenue_accelerating"),
        "revenue_yoy_last4": ctx.metrics.raw("revenue_yoy_last4"),
        "revenue_cagr_3y": ctx.metrics.raw("revenue_cagr_3y"),
        "revenue_cagr_5y": ctx.metrics.raw("revenue_cagr_5y"),
    }
    for st in sts:
        if st.key == "sg_revenue_growth_sustainable":
            st.inputs = {**st.inputs, **measured}
            claim = st.earned
            acc = measured["revenue_accelerating_measured"]
            if claim is not None and acc is not None:
                high_claim = claim >= 3
                if high_claim and acc is False:
                    st.inputs["contradiction"] = (
                        "model scored growth as accelerating/sustainable while the "
                        "measured quarterly YoY series is decelerating"
                    )

    payload = (ctx.qual or {}).get("SG") or {}
    comp = ComponentScore(
        code=CODE, label=rubric.COMPONENTS[CODE][0],
        max_points=rubric.COMPONENTS[CODE][1], subtests=sts,
        note=(payload.get("summary") or
              "LLM-scored from 10-K business/risk/MD&A sections, news and the quant fact sheet."),
    )
    comp.check_points()
    return comp


def all_no_data(code: str) -> ComponentScore:
    """Every sub-test NO_DATA - what an unavailable Ollama produces."""
    spec = {"SG": (rubric.SG_SUBTESTS, "sg")}[code]
    label, mx = rubric.COMPONENTS[code]
    subtests = [no_data(f"{spec[1]}_{k}", lbl, m, "LLM qualitative scoring unavailable")
                for k, lbl, m in spec[0]]
    comp = ComponentScore(code=code, label=label, max_points=mx, subtests=subtests)
    comp.check_points()
    return comp


__all__ = ["score", "read_llm_subtests", "all_no_data", "Status"]
