"""Flags, reconciliation and the conviction gate.

Reconciliation is the only path by which external evidence moves a point in the
94-point framework, so every constraint on it is pinned here: rule-based, evidence-
gated, capped, reversible, and refusing to act on absence.
"""
from __future__ import annotations

import pytest

from clab import config
from clab.external import contradiction as C
from clab.external import gates as G
from clab.external import reconcile as RC
from clab.external import schema as S


def _claim(field, cid="c_0123456789ab", status="VERIFIED_LOCAL", stance="CONTRADICTS",
           domain="REGULATOR"):
    return {"claim_id": cid, "field": field, "verify_status": status,
            "stance": stance, "independence_domain": domain}


def _local(**over):
    d = {"ticker": "TEST", "sg": 16, "bq": 11, "fe": 16, "va": 8,
         "band": "HIGH_CONVICTION", "coverage": 0.95,
         "revenue_cagr_3y": 0.20, "stress_verdict": "SURVIVES_COMFORTABLY"}
    d.update(over)
    return d


def _external(**over):
    d = {"ticker": "TEST", "research_depth": 3}
    for f in S.COMPANY_ORDINALS:
        d[f] = S.UNKNOWN
    d.update(over)
    return d


def _scored(**over):
    d = {"coverage": 0.95, "external_confidence": 0.9}
    d.update(over)
    return d


# ================================================================== flags
def test_a_flag_needs_a_verified_claim_not_an_assertion():
    """A flag that fires on an uncited categorical is E39 wearing a warning label."""
    ext = _external(moat_trajectory="WEAKENING")
    assert C.flags_for(_local(), ext, []) == []
    got = C.flags_for(_local(), ext, [_claim("moat_trajectory")])
    assert "COMPETITIVE_POSITION_DETERIORATING" in got


def test_a_self_attested_claim_can_raise_a_flag_but_never_moves_a_point():
    """Recording a concern is cheaper than changing the incumbent's answer."""
    ext = _external(moat_trajectory="WEAKENING")
    attested = [_claim("moat_trajectory", status="SELF_ATTESTED")]
    assert C.flags_for(_local(), ext, attested) == []          # flags need VERIFIED too
    res = RC.reconcile(_local(), ext, attested, _scored())
    assert res["applied"] == []


def test_unknown_with_nothing_behind_it_raises_no_flag():
    """Nobody looked. That is not a finding."""
    assert C.flags_for(_local(sg=19), _external(), []) == []


def test_unknown_with_contradicting_evidence_raises_unverified_core_thesis():
    """VRT: SG 19/20 from the judged half, and competitors' own growth cited to block
    the share-gain inference. Looked and could not establish is not the same as did
    not look."""
    got = C.flags_for(
        _local(sg=19), _external(company_specific_capture=S.UNKNOWN),
        [_claim("company_specific_capture", cid="c_00000000000a"),
         _claim("company_specific_capture", cid="c_00000000000b", domain="COMPETITOR_FILING")])
    assert "UNVERIFIED_CORE_THESIS" in got


def test_value_trap_risk_carries_the_e08_caveat_in_its_reason():
    """E08 tested this on measured inputs and it failed AND inverted. This variant adds
    external evidence, so it is a new hypothesis and must say so."""
    flags = C.evaluate(
        _local(va=13), _external(moat_trajectory="WEAKENING",
                                 cheapness_quality="STRUCTURAL"),
        [_claim("moat_trajectory"), _claim("cheapness_quality", cid="c_00000000000b")])
    vt = [f for f in flags if f["flag"] == "VALUE_TRAP_RISK"]
    assert vt and "E08" in vt[0]["reason"] and "inverted" in vt[0]["reason"]


def test_balance_sheet_stress_reuses_the_measured_verdict():
    """Not reimplemented. A second derivation of one quantity is how dilution_yoy came
    to read +32.5% across the whole universe."""
    assert "BALANCE_SHEET_STRESS" in C.flags_for(
        _local(stress_verdict="FAIL"), _external(), [])
    assert "BALANCE_SHEET_STRESS" not in C.flags_for(
        _local(stress_verdict="STRESSED"), _external(), [])


def test_fabrication_risk_fires_above_the_rate_not_on_a_single_claim():
    ten = [_claim("moat_trajectory", cid=f"c_{i:012x}") for i in range(10)]
    one_bad = ten[:9] + [_claim("x", cid="c_ffffffffffff", status="UNVERIFIABLE")]
    assert "EVIDENCE_FABRICATION_RISK" not in C.flags_for(_local(), _external(), one_bad)
    two_bad = ten[:8] + [_claim("x", cid=f"c_fffffffffff{i}", status="UNVERIFIABLE")
                         for i in range(2)]
    assert "EVIDENCE_FABRICATION_RISK" in C.flags_for(_local(), _external(), two_bad)


def test_every_flag_carries_auditable_claim_ids():
    """A flag a reader cannot audit is a rumour."""
    for f in C.evaluate(_local(), _external(regulatory_risk="SEVERE"),
                        [_claim("regulatory_risk")]):
        assert "reason" in f and isinstance(f["claim_ids"], list)


def test_flags_are_returned_in_schema_order_and_deduped():
    got = C.flags_for(_local(va=13),
                      _external(moat_trajectory="WEAKENING",
                                cheapness_quality="STRUCTURAL",
                                regulatory_risk="SEVERE"),
                      [_claim("moat_trajectory"),
                       _claim("cheapness_quality", cid="c_00000000000b"),
                       _claim("regulatory_risk", cid="c_00000000000c")])
    assert got == [f for f in S.FLAGS if f in set(got)]
    assert len(got) == len(set(got))


# ========================================================== reconciliation
def test_depth_zero_moves_nothing():
    """Absence of external research is not bearish."""
    ext = _external(research_depth=0, moat_trajectory="WEAKENING")
    claims = [_claim("moat_trajectory", cid=f"c_{i:012x}",
                     domain=d) for i, d in enumerate(["REGULATOR", "ACADEMIC"])]
    res = RC.reconcile(_local(), ext, claims, _scored())
    assert res["applied"] == []
    assert res["delta_sg"] == 0 and res["delta_bq"] == 0
    assert any("research_depth" in b for b in res["blocked"])


def test_a_record_below_the_coverage_floor_may_not_reconcile():
    """E42 arm 1 cleared the 0.60 confidence bar at 0.845 on 38% coverage. A record with
    no external score has not earned an opinion about the judged half."""
    ext = _external(moat_trajectory="WEAKENING")
    claims = [_claim("moat_trajectory", cid=f"c_{i:012x}", domain=d)
              for i, d in enumerate(["REGULATOR", "ACADEMIC"])]
    res = RC.reconcile(_local(), ext, claims, _scored(coverage=0.38))
    assert res["applied"] == []
    assert any("coverage" in b for b in res["blocked"])


def test_low_confidence_blocks_reconciliation():
    res = RC.reconcile(_local(), _external(), [], _scored(external_confidence=0.4))
    assert any("confidence" in b for b in res["blocked"])


def test_r3_fires_on_the_fico_shape():
    """A high judged moat against evidenced deterioration, two domains."""
    ext = _external(moat_trajectory="WEAKENING")
    claims = [_claim("moat_trajectory", cid="c_00000000000a", domain="REGULATOR"),
              _claim("moat_trajectory", cid="c_00000000000b", domain="COMPETITOR_FILING")]
    res = RC.reconcile(_local(bq=13), ext, claims, _scored())
    assert [a["rule_id"] for a in res["applied"]] == ["R3_MOAT_TRAJECTORY_WEAKENING"]
    assert res["bq_before"] == 13 and res["bq_after"] == 11


def test_one_domain_is_not_enough_for_r3():
    """Two claims from one regulator is one line of evidence, not two."""
    claims = [_claim("moat_trajectory", cid=f"c_{i:012x}", domain="REGULATOR")
              for i in range(2)]
    res = RC.reconcile(_local(bq=13), _external(moat_trajectory="WEAKENING"),
                       claims, _scored())
    assert res["applied"] == []


def test_unknown_capture_never_triggers_the_capture_deduction():
    """R1 requires an actual LOW or NONE reading. UNKNOWN is not a negative, however
    much contradicting evidence sits behind it - that is R5's job, and R5 is a flag."""
    claims = [_claim("company_specific_capture", cid=f"c_{i:012x}", domain=d)
              for i, d in enumerate(["REGULATOR", "COMPETITOR_FILING"])]
    res = RC.reconcile(_local(sg=19), _external(company_specific_capture=S.UNKNOWN),
                       claims, _scored())
    assert res["applied"] == []


def test_the_joint_cap_holds():
    ext = _external(moat_trajectory="WEAKENING", company_specific_capture="NONE")
    claims = (
        [_claim("moat_trajectory", cid=f"c_a{i:011x}", domain=d)
         for i, d in enumerate(["REGULATOR", "ACADEMIC"])]
        + [_claim("company_specific_capture", cid=f"c_b{i:011x}", domain=d)
           for i, d in enumerate(["CUSTOMER", "COMPETITOR_FILING"])])
    res = RC.reconcile(_local(sg=18, bq=13), ext, claims, _scored())
    assert abs(res["delta_sg"]) <= config.EXTERNAL_MAX_DELTA_SG
    assert abs(res["delta_bq"]) <= config.EXTERNAL_MAX_DELTA_BQ
    assert abs(res["delta_sg"]) + abs(res["delta_bq"]) <= config.EXTERNAL_MAX_DELTA_TOTAL


def test_a_component_cannot_go_below_zero():
    claims = [_claim("moat_trajectory", cid=f"c_{i:012x}", domain=d)
              for i, d in enumerate(["REGULATOR", "ACADEMIC"])]
    res = RC.reconcile(_local(bq=11), _external(moat_trajectory="WEAKENING"),
                       claims, _scored())
    assert res["bq_after"] >= 0


def test_the_ledger_makes_every_adjustment_reversible():
    """The whole licence for letting external evidence move points."""
    claims = [_claim("moat_trajectory", cid="c_00000000000a", domain="REGULATOR"),
              _claim("moat_trajectory", cid="c_00000000000b", domain="ACADEMIC")]
    res = RC.reconcile(_local(bq=13), _external(moat_trajectory="WEAKENING"),
                       claims, _scored())
    rows = RC.ledger_rows(res, request_id="r1")
    assert len(rows) == 1
    row = rows[0]
    assert row["before_points"] - row["after_points"] == -row["delta"]
    assert row["after_points"] - row["delta"] == row["before_points"]
    assert row["claim_ids"] == ["c_00000000000a", "c_00000000000b"]
    assert row["rule_id"] == "R3_MOAT_TRAJECTORY_WEAKENING"


def test_reconcile_never_mutates_its_inputs():
    local, ext = _local(bq=13), _external(moat_trajectory="WEAKENING")
    before = dict(local)
    claims = [_claim("moat_trajectory", cid=f"c_{i:012x}", domain=d)
              for i, d in enumerate(["REGULATOR", "ACADEMIC"])]
    RC.reconcile(local, ext, claims, _scored())
    assert local == before


# =================================================================== gates
# Conviction is a SCORE, not a bouncer. The first version answered one boolean and
# returned False for all three pilot companies, which tells a ranking system nothing.


def test_the_criteria_weights_sum_to_one_hundred():
    assert G.CRITERIA_TOTAL == 100


def test_every_company_gets_a_score_and_a_rank_nobody_is_excluded():
    rows = [G.evaluate(_local(band=b), _external(), _scored(), [])
            for b in ("EXCEPTIONAL", "WEAK", "REJECT")]
    ranked = G.rank(rows)
    assert [r["conviction_rank"] for r in ranked] == [1, 2, 3]
    assert all(r["conviction_score"] >= 0 for r in ranked)
    assert all(r["conviction_band"] for r in ranked)


def test_a_flag_costs_points_rather_than_slamming_a_door():
    ext = _external(current_moat_strength="EXCEPTIONAL", moat_trajectory="STABLE",
                    company_specific_capture="HIGH")
    clean = G.evaluate(_local(), ext, _scored(), [])
    flagged = G.evaluate(_local(), ext, _scored(), ["REGULATORY_IMPAIRMENT"])
    assert flagged["conviction_score"] < clean["conviction_score"]
    assert flagged["conviction_score"] > 0
    assert flagged["flag_penalty"] == G.FLAG_PENALTY["REGULATORY_IMPAIRMENT"]


def test_a_near_miss_outranks_a_distant_one():
    """Criteria are continuous, not binary, or every shortfall would cost the same."""
    near = G.evaluate(_local(fe=12), _external(), _scored(), [])
    far = G.evaluate(_local(fe=6), _external(), _scored(), [])
    assert near["conviction_score"] > far["conviction_score"]


def test_value_trap_risk_costs_nothing_because_e08_inverted():
    """E08 tested this on measured inputs and it failed AND inverted. Deducting for an
    unvalidated flag whose measured ancestor pointed the other way would be acting on a
    belief this repo has already measured as wrong."""
    assert G.FLAG_PENALTY["VALUE_TRAP_RISK"] == 0
    ext = _external(current_moat_strength="STRONG", moat_trajectory="STABLE",
                    company_specific_capture="HIGH")
    a = G.evaluate(_local(), ext, _scored(), [])
    b = G.evaluate(_local(), ext, _scored(), ["VALUE_TRAP_RISK"])
    assert a["conviction_score"] == b["conviction_score"]


def test_the_flag_is_still_reported_even_though_it_costs_nothing():
    ext = _external(company_specific_capture="HIGH")
    g = G.evaluate(_local(), ext, _scored(), ["VALUE_TRAP_RISK"])
    assert any(p["flag"] == "VALUE_TRAP_RISK" for p in g["penalties"])


def test_capture_is_weighted_above_the_other_core_fields():
    """The VRT case exists because industry growth and company capture are different
    claims. Weighting capture as one of three equal thirds made VRT rank FIRST at
    VERIFIED_HIGH with capture unestablished."""
    assert G.CORE_FIELD_WEIGHTS["company_specific_capture"] >         G.CORE_FIELD_WEIGHTS["current_moat_strength"]
    known_capture = G.evaluate(
        _local(), _external(company_specific_capture="HIGH"), _scored(), [])
    known_moat = G.evaluate(
        _local(), _external(current_moat_strength="STRONG"), _scored(), [])
    assert (known_capture["criteria"]["core_fields_known"]["earned"]
            > known_moat["criteria"]["core_fields_known"]["earned"])


def test_unestablished_capture_withholds_the_label_but_not_the_rank():
    """It costs the label, not the ranking. The company keeps its points and its
    position; only the top label is withheld."""
    ext = _external(current_moat_strength="EXCEPTIONAL", moat_trajectory="STRENGTHENING",
                    company_specific_capture=S.UNKNOWN)
    g = G.evaluate(_local(band="EXCEPTIONAL"), ext, _scored(), [])
    assert g["conviction_score"] > 0
    assert g["high_conviction_verified"] is False
    assert any("company_specific_capture" in d for d in g["disqualified_by"])


def test_unknown_capture_at_shallow_depth_does_not_withhold_the_label():
    """At depth 1 nobody claimed to have looked hard, so the silence says nothing."""
    ext = _external(research_depth=1, company_specific_capture=S.UNKNOWN)
    g = G.evaluate(_local(), ext, _scored(), [])
    assert not any("company_specific_capture" in d for d in g["disqualified_by"])


def test_a_clean_deeply_researched_company_reaches_verified_high():
    ext = _external(research_depth=3, current_moat_strength="EXCEPTIONAL",
                    moat_trajectory="STRENGTHENING", company_specific_capture="HIGH")
    g = G.evaluate(_local(band="EXCEPTIONAL"), ext, _scored(), [])
    assert g["conviction_band"] == "VERIFIED_HIGH"
    assert g["high_conviction_verified"] is True, g["shortfalls"]


@pytest.mark.parametrize("flag", G.HARD_DISQUALIFIERS)
def test_a_hard_disqualifier_withholds_the_label_without_erasing_the_company(flag):
    ext = _external(research_depth=3, current_moat_strength="EXCEPTIONAL",
                    moat_trajectory="STRENGTHENING", company_specific_capture="HIGH")
    g = G.evaluate(_local(band="EXCEPTIONAL"), ext, _scored(), [flag])
    assert g["high_conviction_verified"] is False
    assert flag in g["disqualified_by"]
    assert g["conviction_score"] > 0          # still ranked


def test_ranking_ties_break_on_unpenalised_criteria():
    """A flag must never reorder two otherwise-identical companies arbitrarily."""
    a = G.evaluate(_local(ticker="AAA"), _external(), _scored(), [])
    b = G.evaluate(_local(ticker="BBB"), _external(), _scored(), [])
    ranked = G.rank([b, a])
    assert [r["ticker"] for r in ranked] == ["AAA", "BBB"]


def test_the_score_says_WHY_through_its_criteria():
    g = G.evaluate(_local(band="WEAK", fe=4), _external(), _scored(coverage=0.1), [])
    assert g["shortfalls"]
    assert sum(c["max"] for c in g["criteria"].values()) == 100
    assert all("note" in c for c in g["criteria"].values())


def test_the_score_can_never_go_negative():
    g = G.evaluate(_local(band="REJECT", fe=0, stress_verdict="FAIL", coverage=0.0),
                   _external(research_depth=0, moat_trajectory="DETERIORATING"),
                   _scored(coverage=0.0, external_confidence=0.0),
                   list(G.FLAG_PENALTY))
    assert g["conviction_score"] == 0.0
    assert g["conviction_band"] == "UNSUPPORTED"


# ------------------------------------------- risk flags are PEER-RELATIVE (E44)
def _peer(level, field="regulatory_risk", n=6):
    return [_external(**{field: level}) for _ in range(n)]


def test_a_risk_flag_cannot_fire_without_peer_context():
    """Without peers there is no way to separate a company signal from an industry
    constant, so silence is the correct answer."""
    ext = _external(regulatory_risk="SEVERE")
    assert C.flags_for(_local(), ext, [_claim("regulatory_risk")], peers=None) == []


def test_a_risk_level_matching_its_industry_raises_no_flag():
    """E44: REGULATORY_IMPAIRMENT fired for 39 of 40 companies, and inside
    regional_banking both risk flags fired for 19 of 19 - two distinct flag-sets across
    nineteen banks. "Banking is regulated" is not a finding about a bank."""
    ext = _external(regulatory_risk="ELEVATED")
    got = C.flags_for(_local(), ext, [_claim("regulatory_risk")],
                      peers=_peer("ELEVATED"))
    assert "REGULATORY_IMPAIRMENT" not in got


def test_a_risk_level_worse_than_its_industry_does_raise_a_flag():
    ext = _external(regulatory_risk="SEVERE")
    got = C.flags_for(_local(), ext, [_claim("regulatory_risk")],
                      peers=_peer("MODERATE"))
    assert "REGULATORY_IMPAIRMENT" in got


def test_too_few_peers_is_not_a_passed_comparison():
    """An unmeasurable comparison is not a passed one - the rule the framework already
    applies to peer multiples."""
    ext = _external(regulatory_risk="SEVERE")
    assert C.flags_for(_local(), ext, [_claim("regulatory_risk")],
                       peers=_peer("MODERATE", n=C.MIN_PEERS_FOR_RISK - 1)) == []


def test_peers_that_all_answered_unknown_do_not_count_as_peers():
    ext = _external(regulatory_risk="SEVERE")
    assert C.flags_for(_local(), ext, [_claim("regulatory_risk")],
                       peers=_peer(S.UNKNOWN)) == []


def test_the_reason_names_the_peer_comparison():
    """A flag a reader cannot audit is a rumour, and 'worse than peers' is the claim."""
    flags = C.evaluate(_local(), _external(regulatory_risk="SEVERE"),
                       [_claim("regulatory_risk")], peers=_peer("MODERATE"))
    reg = [f for f in flags if f["flag"] == "REGULATORY_IMPAIRMENT"]
    assert reg and "industry median" in reg[0]["reason"]


def test_a_non_risk_flag_is_unaffected_by_peers():
    """Only the risk flags are industry-relative; moat deterioration is a company fact."""
    ext = _external(moat_trajectory="WEAKENING")
    got = C.flags_for(_local(), ext, [_claim("moat_trajectory")], peers=None)
    assert "COMPETITIVE_POSITION_DETERIORATING" in got
