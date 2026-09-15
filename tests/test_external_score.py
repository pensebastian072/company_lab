"""Every external number is computed here, so every rule that produces one is pinned.

The framework's own rules, applied to a second kind of evidence: absent data is NO_DATA
and never a zero, coverage is scored over applicable, and the extrapolated form is
withheld below the floor rather than shown as a low number.
"""
from __future__ import annotations

from datetime import date

import pytest

from clab import config
from clab.external import score as SC
from clab.external import schema as S
from clab.external.store import ExternalStore
from conftest import skip_if_locked


def _claim(field, cid="c_0123456789ab", status="VERIFIED_LOCAL",
           domain="REGULATOR", source_date="2026-06-01", request_id="r1"):
    return {"claim_id": cid, "field": field, "verify_status": status,
            "independence_domain": domain, "source_date": source_date,
            "request_id": request_id}


def _record(**over):
    rec = {"ticker": "TEST", "research_version": "v1", "request_id": "r1",
           "research_depth": 3}
    for f in S.COMPANY_ORDINALS:
        rec[f] = S.UNKNOWN
    rec.update(over)
    return rec


TODAY = date(2026, 9, 2)


# ------------------------------------------------------------- the point budget
def test_the_dimensions_sum_to_one_hundred():
    assert SC.TOTAL_POINTS == 100


def test_cheapness_quality_is_retired_not_merely_unscored():
    """Retired 2026-09-02 on measurement across 46 stored records: UNKNOWN in 42 of
    them, and exactly ONE claim in the whole corpus cites it. Under the citation rule
    that is 1 of 43 answered.

    It stays a legal vocabulary so historical rows parse and finalize still accepts it,
    but it is out of the scored set and out of the coverage denominator, and it is out
    of the prompt so nobody spends a search on it again.
    """
    assert "cheapness_quality" in S.RETIRED_ORDINALS
    assert "cheapness_quality" not in S.COMPANY_ORDINALS
    assert "cheapness_quality" in S.COMPANY_ORDINALS_ALL
    assert "cheapness_quality" not in SC.SCORED_FIELDS
    assert S.is_valid("cheapness_quality", "STRUCTURAL")


def test_a_retired_field_is_still_accepted_by_the_finalizer():
    """Rejecting it would break every payload built against the previous prompt."""
    from clab.external import finalize as F
    assert "cheapness_quality" in F.ALLOWED_CATEGORICALS


def test_the_scored_set_and_the_asked_set_are_now_the_same_size():
    """12 fields asked, 12 fields scored. A question the layer cannot answer should not
    sit in the contract pretending it might."""
    assert len(S.COMPANY_ORDINALS) == len(SC.SCORED_FIELDS) == 12
    assert set(S.COMPANY_ORDINALS) == set(SC.SCORED_FIELDS)


def test_a_maximal_cheapness_reading_cannot_move_the_score():
    a = SC.score_company(_record(current_moat_strength="STRONG"),
                         [_claim("current_moat_strength")], today=TODAY)
    b = SC.score_company(_record(current_moat_strength="STRONG",
                                 cheapness_quality="STRUCTURAL"),
                         [_claim("current_moat_strength")], today=TODAY)
    assert a["external_score"] == b["external_score"]


def test_every_scored_field_belongs_to_exactly_one_dimension():
    seen = [f for d in SC.DIMENSIONS.values() for f in d]
    assert len(seen) == len(set(seen))


# ------------------------------------------------- a field scores only if cited
def test_an_uncited_assertion_does_not_score():
    """Checked HERE, not trusted from the finalizer. Arm 1 was finalized without the
    citation rule and its records still hold 26 uncited assertions."""
    res = SC.score_company(_record(current_moat_strength="EXCEPTIONAL"), [],
                           today=TODAY)
    f = res["dimensions"]["moat_strength"]["fields"]["current_moat_strength"]
    assert f["status"] == "UNBACKED"
    assert f["points"] is None
    assert "current_moat_strength" in res["unbacked_fields"]


def test_an_uncited_assertion_lowers_coverage_rather_than_scoring_zero():
    """The distinction rule 2 of the framework exists to protect: a company with no
    evidence is not a company with terrible evidence."""
    res = SC.score_company(_record(current_moat_strength="EXCEPTIONAL"), [],
                           today=TODAY)
    assert res["dimensions"]["moat_strength"]["available"] == 0
    assert res["coverage"] < 1.0


def test_a_cited_field_scores():
    res = SC.score_company(_record(current_moat_strength="EXCEPTIONAL"),
                           [_claim("current_moat_strength")], today=TODAY)
    f = res["dimensions"]["moat_strength"]["fields"]["current_moat_strength"]
    assert f["status"] == "SCORED"
    assert f["points"] == 10.0                      # EXCEPTIONAL normalises to 1.0


def test_an_unverifiable_claim_cannot_back_a_score():
    """We fetched the page and the quote was not in it. That is the most direct
    fabrication evidence available here."""
    res = SC.score_company(_record(current_moat_strength="EXCEPTIONAL"),
                           [_claim("current_moat_strength", status="UNVERIFIABLE")],
                           today=TODAY)
    assert res["dimensions"]["moat_strength"]["available"] == 0


def test_a_self_attested_claim_DOES_back_a_score():
    """A 403 or a timeout is our failure to check, not evidence about the company.
    Refusing to score it would turn network conditions into a penalty."""
    res = SC.score_company(_record(current_moat_strength="EXCEPTIONAL"),
                           [_claim("current_moat_strength", status="SELF_ATTESTED")],
                           today=TODAY)
    assert res["dimensions"]["moat_strength"]["fields"][
        "current_moat_strength"]["status"] == "SCORED"


def test_unknown_never_scores_as_zero_even_when_cited():
    """A researcher may cite evidence and still conclude UNKNOWN - VRT's market-share
    direction is exactly that, backed by competitors' growth. It is NO_DATA."""
    res = SC.score_company(_record(market_share_direction=S.UNKNOWN),
                           [_claim("market_share_direction")], today=TODAY)
    f = res["dimensions"]["company_capture"]["fields"]["market_share_direction"]
    assert f["status"] == "NO_DATA"
    assert f["points"] is None


# --------------------------------------------------------- strict vs normalized
def test_strict_is_the_headline_and_a_weak_dimension_cannot_be_escaped():
    """The exact trap that made this the headline.

    Normalizing over `available` was tried and reverted: it gave VRT the HIGHEST score
    of the three while its whole company_capture dimension had zero available points,
    because excluding a dimension from the denominator is indistinguishable from acing
    it. VRT's finding is "industry growing, capture unproven" and the arithmetic was
    paying it for the second half.

    Modelled here: a company that scores BADLY on capture, versus the same company that
    simply could not evidence capture at all. Strict must punish the second at least as
    much as the first; normalized rewards it, which is why normalized is not the
    headline.
    """
    best = {f: S.VOCABULARIES[f][-2] for f in SC.SCORED_FIELDS}   # -1 is UNKNOWN
    claims = [_claim(f, cid=f"c_{i:012x}") for i, f in enumerate(SC.SCORED_FIELDS)]

    # (a) capture measured, and bad
    bad = _record(**{**best, "company_specific_capture": "NONE",
                     "market_share_direction": "LOSING"})
    a = SC.score_company(bad, claims, today=TODAY)

    # (b) capture not evidenced at all
    unmeasured = _record(**{**best, "company_specific_capture": S.UNKNOWN,
                            "market_share_direction": S.UNKNOWN})
    capture_fields = ("company_specific_capture", "market_share_direction")
    b = SC.score_company(unmeasured,
                         [c for c in claims if c["field"] not in capture_fields],
                         today=TODAY)

    # strict: failing to evidence a dimension is no better than scoring zero on it
    assert b["external_score"] <= a["external_score"]
    # normalized: being unmeasurable looks BETTER, which is the trap
    assert b["external_normalized"] > a["external_normalized"]
    # ...and coverage is what exposes it
    assert b["coverage"] < a["coverage"]


def test_normalized_is_flagged_but_never_withheld_below_the_floor():
    res = SC.score_company(_record(current_moat_strength="STRONG"),
                           [_claim("current_moat_strength")], today=TODAY)
    assert res["coverage"] < config.EXTERNAL_MIN_COVERAGE
    # NOT withheld - a ranking ranks everyone. Coverage travels beside it as a column.
    assert res["external_normalized"] is not None
    assert res["insufficient_coverage"] is True
    assert res["insufficient"] is True


def test_strict_is_still_reported_below_the_floor():
    """composite_strict is always shown; only the extrapolation is withheld."""
    res = SC.score_company(_record(current_moat_strength="STRONG"),
                           [_claim("current_moat_strength")], today=TODAY)
    assert res["external_score"] is not None
    assert 0 <= res["external_score"] <= 100


def test_a_company_with_no_evidence_at_all_scores_zero_not_none():
    """Evidence Quality is always applicable: an absence of evidence is a real 0 there,
    not NO_DATA, because it measures the evidence we hold rather than the company."""
    res = SC.score_company(_record(), [], today=TODAY)
    assert res["external_score"] == 0.0
    # Evidence Quality is always applicable, so there is always a denominator and the
    # normalized form is a real 0.0 - not None. A ranking ranks everyone.
    assert res["external_normalized"] == 0.0
    assert res["insufficient_coverage"] is True


# ------------------------------------------------------------ evidence quality
def test_evidence_quality_counts_domains_not_claims():
    """Ten trade-press rewrites of one press release is one domain. Measured on E42:
    COMPANY_IR grew 5 of 14 to 11 of 32 when citations were demanded."""
    many_one_domain = [_claim("current_moat_strength", cid=f"c_{i:012x}",
                              domain="COMPANY_IR") for i in range(10)]
    few_many_domains = [
        _claim("current_moat_strength", cid="c_00000000000a", domain="REGULATOR"),
        _claim("current_moat_strength", cid="c_00000000000b", domain="ACADEMIC"),
        _claim("current_moat_strength", cid="c_00000000000c", domain="CUSTOMER"),
        _claim("current_moat_strength", cid="c_00000000000d", domain="SUPPLIER"),
    ]
    a, _ = SC.evidence_quality(many_one_domain, today=TODAY)
    b, _ = SC.evidence_quality(few_many_domains, today=TODAY)
    assert b > a


def test_evidence_quality_rewards_local_verification():
    ver = [_claim("f", cid="c_00000000000a", status="VERIFIED_LOCAL")]
    att = [_claim("f", cid="c_00000000000a", status="SELF_ATTESTED")]
    assert SC.evidence_quality(ver, today=TODAY)[0] > \
        SC.evidence_quality(att, today=TODAY)[0]


def test_evidence_quality_of_nothing_is_zero_not_a_crash():
    pts, detail = SC.evidence_quality([], today=TODAY)
    assert pts == 0.0 and detail["claims"] == 0


def test_a_claim_with_no_date_does_not_crash_freshness():
    pts, detail = SC.evidence_quality(
        [_claim("f", source_date=None)], today=TODAY)
    assert detail["fresh_share"] is None
    assert pts >= 0


# ------------------------------------------------------------------ confidence
def test_confidence_never_multiplies_the_score():
    """Its only mechanical jobs are gating reconciliation and being a column."""
    rec = _record(current_moat_strength="EXCEPTIONAL")
    claims = [_claim("current_moat_strength")]
    a = SC.score_company(rec, claims, today=TODAY)["external_score"]
    conf, _ = SC.confidence(rec, claims, today=TODAY)
    assert conf is not None and conf < 1.0
    assert a == SC.score_company(rec, claims, today=TODAY)["external_score"]


def test_an_unverifiable_claim_caps_confidence():
    rec = _record(current_moat_strength="EXCEPTIONAL")
    good = [_claim("current_moat_strength", cid=f"c_{i:012x}",
                   domain=d) for i, d in enumerate(
                       ["REGULATOR", "ACADEMIC", "CUSTOMER", "SUPPLIER"])]
    conf_clean, _ = SC.confidence(rec, good, today=TODAY)
    conf_dirty, parts = SC.confidence(
        rec, good + [_claim("x", cid="c_ffffffffffff", status="UNVERIFIABLE")],
        today=TODAY)
    assert conf_clean > 0.5
    assert conf_dirty <= 0.5
    assert parts.get("unverifiable_cap") is True


def test_confidence_with_no_usable_claims_is_none_not_zero():
    """None is "we cannot say"; 0.0 is "we are certain it is bad"."""
    conf, _ = SC.confidence(_record(), [], today=TODAY)
    assert conf is None


# ------------------------------------------------- arms must not contaminate
def test_scoring_one_arm_never_borrows_another_arms_claims(tmp_path):
    """Claims are keyed by claim_id, not by research version, so claims_for(ticker)
    returns every arm's evidence. The first draft scored FICO's 11-claim cited arm on
    14 claims, borrowing three findings from an arm run under a different rule."""
    from clab.external.schema import Claim
    store = ExternalStore(tmp_path / "t.duckdb")

    store.upsert_company({"ticker": "FICO", "research_version": "arm1",
                          "request_id": "r1", "research_depth": 3,
                          "current_moat_strength": "STRONG"})
    store.upsert_company({"ticker": "FICO", "research_version": "arm2",
                          "request_id": "r2", "research_depth": 3,
                          "current_moat_strength": "STRONG"})
    store.insert_claims([Claim(claim_id="c_00000000000a", field="current_moat_strength",
                               text="t", ticker="FICO",
                               verify_status="VERIFIED_LOCAL", overlap=1.0)],
                        request_id="r1")
    store.insert_claims([Claim(claim_id="c_00000000000b", field="moat_trajectory",
                               text="t", ticker="FICO",
                               verify_status="VERIFIED_LOCAL", overlap=1.0)],
                        request_id="r2")

    a1 = SC.score_all(research_version="arm1", store=store, today=TODAY)[0]
    a2 = SC.score_all(research_version="arm2", store=store, today=TODAY)[0]
    # Isolation: each arm sees only its own claim. arm2's claim cites moat_trajectory,
    # which its record leaves UNKNOWN, so it backs no score - but it still counts as
    # evidence held, the way VRT's Eaton and Schneider claims back an honest UNKNOWN.
    assert a1["scored_fields"] == ["current_moat_strength"]
    assert a2["scored_fields"] == []
    assert a1["evidence"]["claims"] == 1
    assert a2["evidence"]["claims"] == 1
    # the proof of isolation: arm2 holds arm1's field value but NOT arm1's claim
    assert "current_moat_strength" in a2["unbacked_fields"]


# ------------------------------------------------------ against the live catalog
@skip_if_locked
def test_the_cited_arm_scores_and_the_uncited_arm_does_not():
    """The measured result of E42, asserted so a regression is visible.

    **Coverage floor moved 0.70 -> 0.65 on 2026-09-11, and that is a CHANGE IN THE
    CORPUS, not a relaxed test.** Making exact containment the bar for VERIFIED_LOCAL
    demoted 139 claims that had passed on vocabulary overlap alone, two of them NVDA's
    in this arm, and NVDA's coverage fell 0.70 -> 0.67. The floor is lowered to just
    under the new measured minimum so the test still catches a COLLAPSE while recording
    that the restatement cost this arm real evidence. Full transitions:
    journal/experiments/CONTAINMENT_RESTATEMENT_2026-09-11.md.
    """
    if not config.EXTERNAL_DB.exists():
        pytest.skip("no catalog on disk")
    store = ExternalStore()
    cited = {r["ticker"]: r for r in
             SC.score_all(research_version="2026-09-02+E42-cited", store=store)}
    if not cited:
        pytest.skip("cited arm not in the catalog")
    # E42's arm property was "every non-UNKNOWN field is cited". The 2026-09-11
    # containment restatement broke it for this arm by demoting the claims that did the
    # citing, so the known damage is PINNED rather than tolerated: these four fields are
    # asserted with no surviving citation, they earn NOTHING (status UNBACKED, and the
    # scorer keeps them in the denominator), and any NEW unbacked field fails here.
    RESTATEMENT_DAMAGE_2026_09_11 = {
        "NVDA": ["company_specific_capture", "moat_trajectory", "regulatory_risk"],
        "VRT": ["current_moat_strength"],
    }
    for t, r in cited.items():
        assert r["coverage"] >= 0.65, f"{t} coverage collapsed: {r['coverage']}"
        assert sorted(r["unbacked_fields"]) == sorted(
            RESTATEMENT_DAMAGE_2026_09_11.get(t, [])), (
            f"{t} unbacked fields moved: {r['unbacked_fields']}")
    assert cited["FICO"]["external_score"] < cited["NVDA"]["external_score"], (
        "FICO is the deteriorating-moat case and must not outscore NVDA")


def test_confidence_falls_when_less_of_the_picture_is_evidenced():
    """Without coverage as a term this returned 1.0 for arm 1's FICO - four claims,
    four domains, all verified, all fresh - against 0.945 for the same company in arm 2
    with eleven claims. Arm 1 had evidenced 38% of the picture and arm 2 had evidenced
    80%, and the more complete record scored LOWER. A confidence that ignores how much
    was cited is maximised by researching one field impeccably and skipping the rest.
    """
    rec = _record(current_moat_strength="EXCEPTIONAL")
    claims = [_claim("current_moat_strength", cid=f"c_{i:012x}", domain=d)
              for i, d in enumerate(["REGULATOR", "ACADEMIC", "CUSTOMER", "SUPPLIER"])]
    thin, _ = SC.confidence(rec, claims, coverage=0.38, today=TODAY)
    full, _ = SC.confidence(rec, claims, coverage=0.95, today=TODAY)
    assert full > thin
    assert thin < 1.0


def test_coverage_is_a_weighted_term_not_a_veto():
    """A perfectly evidenced narrow record is still worth something - it just cannot be
    maximally confident."""
    rec = _record(current_moat_strength="EXCEPTIONAL")
    claims = [_claim("current_moat_strength", cid=f"c_{i:012x}", domain=d)
              for i, d in enumerate(["REGULATOR", "ACADEMIC", "CUSTOMER", "SUPPLIER"])]
    v, parts = SC.confidence(rec, claims, coverage=0.0, today=TODAY)
    assert 0.0 < v < 1.0
    assert parts["coverage"] == 0.0


@skip_if_locked
def test_the_better_evidenced_arm_is_the_more_confident_one():
    """Asserted against the live catalog: the E42 result must not silently invert.

    **Confidence is `>=` and not `>` since 2026-09-11.** VRT's two arms now TIE at 0.5
    because the containment restatement demoted evidence in both: the cited arm lost
    what made it more confident. The direction is what E42 established and the direction
    is what this guards - an INVERSION still fails - but a tie is now a real state of
    the corpus and pretending otherwise would hide what the restatement cost. Coverage
    and score are still strictly ordered, so only the confidence term moved.
    """
    if not config.EXTERNAL_DB.exists():
        pytest.skip("no catalog on disk")
    store = ExternalStore()
    a1 = {r["ticker"]: r for r in
          SC.score_all(research_version="2026-09-02", store=store)}
    a2 = {r["ticker"]: r for r in
          SC.score_all(research_version="2026-09-02+E42-cited", store=store)}
    if not a1 or not a2:
        pytest.skip("both E42 arms not in the catalog")
    # NVDA's confidence INVERTED on 2026-09-11 and it is recorded, not smoothed over.
    # The containment restatement demoted three of the cited arm's claims - the arm that
    # was more confident BECAUSE it cited specific pages was the arm with more to lose -
    # so E42's confidence result no longer holds for NVDA. Coverage and score are still
    # strictly ordered, which is the part of E42 that survives.
    INVERTED_BY_THE_RESTATEMENT = {"NVDA"}
    for t in set(a1) & set(a2):
        assert a2[t]["coverage"] > a1[t]["coverage"], t
        assert a2[t]["external_score"] > a1[t]["external_score"], t
        if t in INVERTED_BY_THE_RESTATEMENT:
            assert a2[t]["external_confidence"] < a1[t]["external_confidence"], (
                f"{t} is pinned as INVERTED by the restatement; if it recovered, "
                f"delete it from the set and say so")
        else:
            assert a2[t]["external_confidence"] >= a1[t]["external_confidence"], t


# --------------------------------------------- a computed claim is not another arm's work
def test_a_computed_claim_survives_the_arm_filter():
    """`marketshare.apply_to` files its FDIC claim under `fdic_sod:<version>`, which never
    equals a company's request_id, so the arm filter discarded it: the field was written
    onto the record and then refused points for having no backing claim. Nothing broke in
    practice only because the researcher had cited the field while answering UNKNOWN."""
    rec = {"ticker": "RF", "request_id": "0f796aae25b60d4865e5"}
    computed = {"field": "market_share_direction", "request_id": "fdic_sod:2026-09-08+x"}
    other_arm = {"field": "moat_trajectory", "request_id": "someotherarm00000000"}
    own = {"field": "pricing_power", "request_id": "0f796aae25b60d4865e5"}
    assert SC._is_computed_claim(computed)
    assert not SC._is_computed_claim(other_arm)
    assert SC._is_arm_claim(own, rec)
    assert not SC._is_arm_claim(other_arm, rec)
    kept = [c for c in (computed, other_arm, own)
            if SC._is_arm_claim(c, rec) or SC._is_computed_claim(c)]
    assert kept == [computed, own]


def test_another_arms_research_is_still_excluded():
    """The contamination this filter exists for: FICO's cited arm has 11 claims and an
    early draft scored it on 14."""
    rec = {"ticker": "FICO", "request_id": "armA0000000000000000"}
    assert not SC._is_arm_claim({"request_id": "armB0000000000000000"}, rec)
    assert not SC._is_computed_claim({"request_id": "armB0000000000000000"})


def test_a_record_with_no_request_id_keeps_every_claim():
    assert SC._is_arm_claim({"request_id": "anything"}, {"ticker": "X"})
