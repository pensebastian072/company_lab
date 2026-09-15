"""MG is measured. It was reported as model judgement for two experiments.

E25 removed the five model-scored CEO attributes and E26 cut the block 8 -> 2, but
`rubric.LLM_COMPONENTS` kept listing MG, so 9 measured points were counted as judgement
and excluded from every measured-half column. 19.8% of companies carried a wrong
`quant_band` as a result. See journal/experiments/mg_label_correction.md.

These tests fail if any part of that arrangement comes back.
"""
from __future__ import annotations

import json
import pathlib

import pytest

from clab import config
from clab.scoring import rubric, mg


def test_mg_is_not_judged():
    assert "MG" not in rubric.JUDGED_COMPONENTS
    assert "MG" in rubric.MEASURED_COMPONENTS


def test_mg_is_still_generated():
    """MG's payload still supplies the display-only ceo_summary rationale.

    Dropping MG from the generation list would silently delete that string from every
    scorecard - a data loss dressed as a cleanup.
    """
    assert "MG" in rubric.GENERATED_COMPONENTS


def test_no_mg_attribute_is_model_scored():
    """The root cause. If an attribute ever carries source "llm" again, MG is partly
    judged and the constants above must be revisited in the same commit."""
    assert all(src == "data" for _k, _lbl, src in rubric.MG_CEO_ATTRIBUTES)
    assert mg._LLM_ATTRS == ()


def test_the_split_is_59_measured_35_judged():
    assert rubric.MEASURED_POINTS == 59
    assert rubric.JUDGED_POINTS == 35
    assert rubric.MEASURED_POINTS + rubric.JUDGED_POINTS == rubric.TOTAL_POINTS


def test_every_component_is_in_exactly_one_half():
    """No component may be counted twice or dropped - that is how the halves stopped
    summing to the total in the first place."""
    judged = set(rubric.JUDGED_COMPONENTS)
    measured = set(rubric.MEASURED_COMPONENTS)
    assert judged & measured == set()
    assert judged | measured == set(rubric.COMPONENT_ORDER)


def test_generated_is_a_superset_of_judged():
    """A component may be generated without being judged (MG). The reverse is a bug:
    a judged component with no payload would score NO_DATA forever."""
    assert set(rubric.JUDGED_COMPONENTS) <= set(rubric.GENERATED_COMPONENTS)


def test_mg_is_measured_in_every_scorecard_on_disk():
    """The behaviour the label was hiding, asserted against real output rather than
    against the constants that were themselves wrong.

    Every MG sub-test must carry measured provenance and the component must not be
    flagged as model-scored. Skips when the book has not been built.
    """
    cards = sorted(pathlib.Path("data/scorecards").glob("*.json"))
    if len(cards) < 20:
        pytest.skip("no scorecard book on disk")
    checked = 0
    for f in cards[:200]:
        card = json.loads(f.read_text(encoding="utf-8"))
        comp = (card.get("components") or {}).get("MG")
        if not comp:
            continue
        assert comp["is_llm"] is False, f"{f.name}: MG flagged as model-scored"
        for st in comp.get("subtests") or []:
            prov = st.get("provenance")
            assert prov != "llm", f"{f.name}: MG sub-test {st.get('key')} provenance={prov}"
        checked += 1
    assert checked >= 20, "no MG components found to check"


def test_stale_ceo_scores_in_old_payloads_are_inert():
    """The v1 lane predates E25 and its MG payloads still carry the five attributes
    that used to be model-scored - `founder_led`, `tenure`, `ownership`,
    `execution_history`, `industry_expertise` - with real 0-2 scores in them.

    They are dead weight: `_ceo_block` only reads an attribute when its source is
    "llm", and none is. This test proves the inertness rather than assuming the
    payloads are clean, because they are not. If a rubric edit ever re-marks an
    attribute as "llm", those stale scores would silently come back to life across the
    whole v1 book - months-old model opinions resurrected as current.
    """
    qual_dir = config.QUAL_DIR
    payloads = sorted(qual_dir.glob("*_MG_*.json"))[:400] if qual_dir.exists() else []
    if len(payloads) < 20:
        pytest.skip("no MG payloads on disk")

    with_scores = []
    for f in payloads:
        ceo = json.loads(f.read_text(encoding="utf-8")).get("ceo") or {}
        if any(isinstance(v, dict) and v.get("score") is not None for v in ceo.values()):
            with_scores.append(f)
    if not with_scores:
        pytest.skip("no stale scored ceo blocks in this lane")

    # Whatever those payloads say, the scorecard built from them must still be measured.
    checked = 0
    for f in with_scores[:50]:
        cik = f.name.split("_")[0]
        for card_path in pathlib.Path("data/scorecards").glob(f"{cik}_*.json"):
            comp = (json.loads(card_path.read_text(encoding="utf-8"))
                    .get("components") or {}).get("MG")
            if not comp:
                continue
            assert comp["is_llm"] is False, f"{card_path.name}: stale ceo scores revived"
            for st in comp.get("subtests") or []:
                assert st.get("provenance") != "llm", (
                    f"{card_path.name}: MG sub-test {st.get('key')} took a stale model score")
            checked += 1
    assert checked >= 1, "found stale payloads but no matching scorecard to check"
