"""conviction v2: each thing counted once, and the conclusions actually read.

v2 is deliberately NOT wired into evaluate(). These tests pin the two defects it fixes
and the rule that it stays unshipped until E51 reports - see E52.
"""
from __future__ import annotations

from clab.external import gates as G
from clab.external.schema import UNKNOWN


def _ext(**kw):
    base = {"research_depth": 3, "distinct_domains": 4,
            "company_specific_capture": UNKNOWN, "current_moat_strength": UNKNOWN,
            "moat_trajectory": UNKNOWN, "competitive_position": UNKNOWN}
    base.update(kw)
    return base


LOCAL = {"band": "GOOD", "fe": 12, "coverage": 0.8, "stress_verdict": "PASS"}
#: v1 reads `coverage` and `external_confidence`; v2 reads the claim counts. A fixture
#: carrying only one pair is how E52's A/B silently starved v1 of 24 of its 100 points.
#: gates.REQUIRED_SCORED_KEYS now raises on it, and this fixture carries both.
SCORED = {"claims_total": 10, "claims_verified": 10,
          "coverage": 0.85, "external_confidence": 0.8}


def test_v2_is_not_wired_into_evaluate():
    """The whole point of E52. v1 stays live until the four fields it depends on are
    known to work again."""
    import inspect
    src = inspect.getsource(G.evaluate)
    assert "criteria_v2" not in src and "CRITERIA_WEIGHTS_V2" not in src


def test_weights_sum_to_100():
    assert sum(G.CRITERIA_WEIGHTS_V2.values()) == 100
    assert abs(sum(G.CORE_FIELD_VALUE_WEIGHTS.values()) - 1.0) < 1e-9


def test_v2_reads_what_a_core_field_SAYS_and_v1_does_not():
    """v1's core_fields_known tests `not in (None, UNKNOWN)`, so capture NONE and capture
    HIGH score identically on its 8 points. That is the deeper defect."""
    lo = G.conviction_v2(LOCAL, _ext(company_specific_capture="NONE"), SCORED)
    hi = G.conviction_v2(LOCAL, _ext(company_specific_capture="HIGH"), SCORED)
    assert hi["conviction_v2"] > lo["conviction_v2"]
    v1_lo = G.evaluate(LOCAL, _ext(company_specific_capture="NONE"), SCORED, [])
    v1_hi = G.evaluate(LOCAL, _ext(company_specific_capture="HIGH"), SCORED, [])
    assert v1_lo["conviction_score"] == v1_hi["conviction_score"], \
        "v1 is expected to be blind to the value - that is what v2 fixes"


def test_UNKNOWN_sits_in_the_MIDDLE_of_a_value_scale_never_the_floor():
    """Package-wide rule: an unanswered field is not a bad answer."""
    unk = G.conviction_v2(LOCAL, _ext(current_moat_strength=UNKNOWN), SCORED)
    worst = G.conviction_v2(LOCAL, _ext(current_moat_strength="NONE"), SCORED)
    best = G.conviction_v2(LOCAL, _ext(current_moat_strength="EXCEPTIONAL"), SCORED)
    assert worst["conviction_v2"] < unk["conviction_v2"] < best["conviction_v2"]


def test_coverage_is_not_a_v2_criterion_because_it_was_counted_three_times():
    assert "external_coverage" not in G.CRITERIA_WEIGHTS_V2
    assert "external_confidence" not in G.CRITERIA_WEIGHTS_V2
    assert "core_fields_known" not in G.CRITERIA_WEIGHTS_V2


def test_evidence_quality_excludes_coverage_and_depth():
    """It is the term that replaced external_confidence. If it moved with coverage or
    depth, the double-count would be back."""
    a = G.criteria_v2(LOCAL, _ext(research_depth=0), SCORED)["evidence_quality"]
    b = G.criteria_v2(LOCAL, _ext(research_depth=4), SCORED)["evidence_quality"]
    assert a["points"] == b["points"]


def test_flag_penalties_and_bands_are_shared_with_v1():
    clean = G.conviction_v2(LOCAL, _ext(), SCORED, [])
    flagged = G.conviction_v2(LOCAL, _ext(), SCORED, ["EVIDENCE_FABRICATION_RISK"])
    assert clean["conviction_v2"] - flagged["conviction_v2"] == \
        G.FLAG_PENALTY["EVIDENCE_FABRICATION_RISK"]
    assert flagged["band_v2"] in {n for _, n in G.CONVICTION_BANDS}


def test_omitting_v1s_evidence_inputs_RAISES_instead_of_scoring_zero():
    """The bug that made E52's first two comparisons wrong, twice. A `scored` dict with
    v2's keys and not v1's used to hand v1 a silent zero on external_coverage and
    external_confidence - 24 of its 100 points - and the published table showed v1 at
    pooled sd 12.84 when its real figure is 16.18."""
    import pytest
    with pytest.raises(KeyError, match="coverage"):
        G.criteria(LOCAL, _ext(), {"claims_total": 10, "claims_verified": 10})


def test_there_is_no_coverage_column_to_read_it_from():
    """The second wrong attempt fixed external_confidence and still passed
    coverage=None, because company_external has no coverage column. It comes from
    score.score_company(). Pinned so the next person does not lose the same hour."""
    from clab.external.store import SCHEMA_SQL
    company_block = SCHEMA_SQL.split("company_external (")[1].split(");")[0]
    assert " coverage " not in company_block
    assert "external_confidence" in company_block
