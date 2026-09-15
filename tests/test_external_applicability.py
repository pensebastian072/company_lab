"""NOT_APPLICABLE leaves the denominator, and everything that stops it being an excuse.

This is the only edit in the external layer that RAISES a score for an absence, so most
of what is pinned here is the brake rather than the feature. E29 measured the failure
mode in the measured half: a one-line nomination converted every abstention into
NOT_APPLICABLE, dropped it out of the coverage denominator and lifted companies over the
band gate.
"""
from __future__ import annotations

from clab.external import applicability as AP
from clab.external import score as SC
from clab.external.schema import UNKNOWN


# --------------------------------------------------------- the two-condition rule
def test_a_nominated_field_with_no_value_is_not_applicable():
    assert AP.is_not_applicable("electric_utilities", "market_share_direction", UNKNOWN)
    assert AP.is_not_applicable("water_utilities", "market_share_direction", None)


def test_a_nominated_field_that_DID_answer_is_still_scored():
    """The second condition. If a nomination is wrong, a real answer must contradict it
    in the open rather than be deleted by it."""
    assert not AP.is_not_applicable(
        "electric_utilities", "market_share_direction", "GAINING")


def test_a_company_cannot_excuse_itself_only_an_industry_can():
    """Nomination is per-industry, never per-company, so the claim is always visible and
    always about structure."""
    assert not AP.is_not_applicable("competitive_power_generation",
                                    "market_share_direction", UNKNOWN)
    assert not AP.is_not_applicable(None, "market_share_direction", UNKNOWN)
    assert not AP.is_not_applicable("", "market_share_direction", UNKNOWN)


def test_only_the_nominated_field_is_excused_in_a_nominated_industry():
    for f in ("moat_trajectory", "competitive_position_trend", "company_specific_capture"):
        assert not AP.is_not_applicable("electric_utilities", f, UNKNOWN)


# ------------------------------------- MEANINGLESS is not UNMEASURED: the whole point
def test_energy_market_share_is_UNKNOWN_and_utilities_is_NOT_APPLICABLE():
    """The field resolved for 0 of 71 Energy companies and 0 of 59 Utilities companies -
    identical emptiness, different reasons. A producer competes for acreage and barrels
    and its share genuinely moves; nobody publishes the series. A regulated utility holds
    a franchise monopoly and has no share to move. If this test ever goes green for
    upstream, the module has become the E29 mistake with a new name."""
    assert not AP.is_not_applicable("upstream_oil_gas", "market_share_direction", UNKNOWN)
    assert not AP.is_not_applicable("midstream", "market_share_direction", UNKNOWN)
    assert AP.is_not_applicable("gas_utilities", "market_share_direction", UNKNOWN)


def test_every_nomination_carries_a_written_definitional_argument():
    """An entry cannot be added without an argument someone would defend to a reader who
    wants the score to go down."""
    for industry, fields in AP.INAPPLICABLE.items():
        for f in fields:
            why = AP.WHY.get((industry, f))
            assert why and len(why) > 80, f"no argument for {industry}/{f}"
    assert set(AP.WHY) == {(i, f) for i, fs in AP.INAPPLICABLE.items() for f in fs}


def test_the_refused_candidates_stay_refused():
    """E31's bar refused 35 of 40. These three are recorded so the next reader does not
    re-derive why the obvious-looking neighbours were left out."""
    for industry, field in AP.CONSIDERED_AND_REFUSED:
        assert field not in AP.inapplicable_fields(industry)


# ------------------------------------------------------------- effect on the score
def _rec(industry, **kw):
    r = {"ticker": "T", "industry_id": industry, "research_version": "v"}
    r.update(kw)
    return r


def _claims(*fields):
    return [{"claim_id": f"c{i}", "field": f, "verify_status": "VERIFIED_LOCAL",
             "source_url": "https://x/y", "source_date": None}
            for i, f in enumerate(fields)]


def test_an_inapplicable_field_leaves_the_denominator():
    ap = SC.score_company(_rec("electric_utilities", market_share_direction=UNKNOWN),
                          _claims())["points_applicable"]
    keeps = SC.score_company(_rec("upstream_oil_gas", market_share_direction=UNKNOWN),
                             _claims())["points_applicable"]
    assert ap == keeps - 5, "market_share_direction is 5 points of Company Capture"


def test_the_exclusion_is_always_reported_never_silent():
    res = SC.score_company(_rec("electric_utilities", market_share_direction=UNKNOWN),
                           _claims())
    assert res["not_applicable_fields"] == ["market_share_direction"]


def test_a_company_with_nothing_excluded_reports_an_empty_list():
    res = SC.score_company(_rec("upstream_oil_gas", market_share_direction=UNKNOWN),
                           _claims())
    assert res["not_applicable_fields"] == []


def test_the_exclusion_cannot_manufacture_points():
    """Coverage and the strict score may rise. `points_earned` must not: excluding a
    question is not answering it."""
    a = SC.score_company(_rec("electric_utilities", market_share_direction=UNKNOWN),
                         _claims())
    b = SC.score_company(_rec("upstream_oil_gas", market_share_direction=UNKNOWN),
                         _claims())
    assert a["points_earned"] == b["points_earned"]
