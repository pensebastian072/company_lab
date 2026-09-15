"""The two rules the external layer cannot survive losing.

1. UNKNOWN is not the bottom of a scale. It is off the scale.
2. A categorical outside its vocabulary is REJECTED, not coerced.

Both have direct precedent in this repo: an out-of-range LLM score is rejected rather
than clamped (rubric A-rules), and absent data is NO_DATA rather than 0. The external
layer takes input from a web-research agent, which has a larger surface for both
mistakes than a filing reader does.
"""
from __future__ import annotations

import pytest

from clab.external import schema as S


# ---------------------------------------------------------------- UNKNOWN
def test_unknown_is_in_every_ordinal_vocabulary():
    for field in S.ORDINAL_FIELDS:
        assert S.UNKNOWN in S.VOCABULARIES[field], field


def test_unknown_never_scores_as_zero():
    """The single most damaging bug available here: UNKNOWN scoring as the floor
    turns every unresearched company into a maximally bad one."""
    for field in S.ORDINAL_FIELDS:
        assert S.ordinal(field, S.UNKNOWN) is None, field
        assert S.normalized(field, S.UNKNOWN) is None, field


def test_unknown_is_distinguishable_from_the_worst_real_value():
    """`ordinal` must not return the same thing for "we did not look" and "it is as
    bad as it gets"."""
    worst = S.VOCABULARIES["current_moat_strength"][0]
    assert S.ordinal("current_moat_strength", worst) == 0
    assert S.ordinal("current_moat_strength", S.UNKNOWN) is None
    assert S.normalized("current_moat_strength", worst) == 0.0
    assert S.normalized("current_moat_strength", S.UNKNOWN) is None


# ---------------------------------------------------------- closed vocabularies
def test_out_of_vocabulary_value_is_rejected_not_coerced():
    reasons = S.validate_categoricals({"moat_trajectory": "GREAT"})
    assert len(reasons) == 1
    assert "moat_trajectory" in reasons[0]
    assert "not in vocabulary" in reasons[0]


def test_unknown_field_is_rejected():
    assert S.validate_categoricals({"vibes": "GOOD"})


def test_clean_input_yields_no_reasons():
    assert S.validate_categoricals({
        "moat_trajectory": "WEAKENING",
        "current_moat_strength": "STRONG",
        "regulatory_risk": "ELEVATED",
        "company_specific_capture": S.UNKNOWN,
    }) == []


def test_is_valid_raises_on_an_unknown_field_but_returns_false_on_a_bad_value():
    """A bad FIELD is our bug and must be loud; a bad VALUE is their input and must be
    a rejection reason we can write into the manifest."""
    with pytest.raises(KeyError):
        S.is_valid("no_such_field", "X")
    assert S.is_valid("stance", "NOPE") is False
    assert S.is_valid("stance", "SUPPORTS") is True


def test_non_string_values_are_never_valid():
    for bad in (None, 3, 3.0, True, ["STRONG"], {"v": "STRONG"}):
        assert S.is_valid("current_moat_strength", bad) is False
        assert S.ordinal("current_moat_strength", bad) is None


# --------------------------------------------------------------- orientation
def test_higher_normalized_always_means_better_for_the_company():
    """Risk scales read SEVERE..LOW, quality scales read NONE..EXCEPTIONAL. Both must
    normalise so that 1.0 is good, or score.py would add a risk to a strength."""
    assert S.normalized("current_moat_strength", "EXCEPTIONAL") == 1.0
    assert S.normalized("current_moat_strength", "NONE") == 0.0
    assert S.normalized("regulatory_risk", "LOW") == 1.0
    assert S.normalized("regulatory_risk", "SEVERE") == 0.0
    assert S.normalized("disruption_risk", "LOW") == 1.0
    assert S.normalized("technology_risk", "SEVERE") == 0.0
    # cheapness: STRUCTURAL cheapness is the bad kind (a value trap), NOT_CHEAP is
    # the benign end of the axis this field measures.
    assert S.normalized("cheapness_quality", "STRUCTURAL") == 0.0


def test_every_ordinal_scale_spans_zero_to_one():
    for field in S.ORDINAL_FIELDS:
        scale = [v for v in S.VOCABULARIES[field] if v != S.UNKNOWN]
        got = {S.normalized(field, v) for v in scale}
        assert 0.0 in got and 1.0 in got, field
        assert all(0.0 <= g <= 1.0 for g in got), field


# ------------------------------------------------------------------- limits
def test_text_over_its_cap_is_rejected():
    assert S.validate_texts({"bull_case": "x" * 801})
    assert S.validate_texts({"bull_case": "x" * 800}) == []
    assert S.validate_texts({"bull_case": None}) == []


def test_non_string_text_is_rejected_rather_than_stringified():
    assert S.validate_texts({"why_is_it_cheap": 42})


def test_depth_rejects_bool_because_isinstance_bool_int_is_true():
    """`isinstance(True, int)` is True in Python. The same class of silent-degradation
    bug as NaN passing `isinstance(v, (int, float))`, which this repo has already been
    bitten by."""
    assert S.validate_depth(True)
    assert S.validate_depth(False)
    assert S.validate_depth(0) == []
    assert S.validate_depth(4) == []
    assert S.validate_depth(5)
    assert S.validate_depth(-1)
    assert S.validate_depth(2.0)


def test_depth_zero_is_a_real_depth_not_an_absence():
    """0 is cache-reuse. A company nobody looked at has no record at all, which is a
    different state and must stay different."""
    assert S.validate_depth(0) == []
    assert S.DEPTH_LABELS[0] == "cache_reuse"


# ------------------------------------------------------------------ records
def test_claim_defaults_to_unverifiable():
    """A claim is guilty until verify.py says otherwise. The default must never be a
    status that counts toward confidence."""
    c = S.Claim(claim_id="c_1", field="moat_trajectory", text="x")
    assert c.verify_status == "UNVERIFIABLE"
    assert c.overlap is None


def test_claim_is_frozen_so_verification_cannot_be_edited_in_place():
    c = S.Claim(claim_id="c_1", field="moat_trajectory", text="x")
    with pytest.raises(Exception):
        c.verify_status = "VERIFIED_LOCAL"      # type: ignore[misc]


def test_flags_and_sectors_are_stable_sets():
    assert len(S.SECTOR_IDS) == 11
    assert len(set(S.FLAGS)) == len(S.FLAGS)
    assert "EVIDENCE_FABRICATION_RISK" in S.FLAGS
