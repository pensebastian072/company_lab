"""E37's instrument - the v1/v2 decomposition, and the arithmetic it rests on.

E37 exists to separate three things a raw score delta cannot tell apart: an abstention
being filled, the two lanes disagreeing where both spoke, and the auditable half moving
underneath the comparison. Every one of those is a different conclusion about the
candidate model, so the properties pinned here are the ones that would silently merge
them:

  * **Filling an abstention can never lower a score.** This is amendment 1 - `score` has a
    FIXED /92 denominator, so `NO_DATA` costs the numerator and never the divisor. The
    first version of E37's registered prediction was reasoned from a percentage
    denominator that does not exist in this repo, and a test is cheaper than making that
    mistake twice.
  * **Common support must exclude fills entirely.** If a fill leaks into it, the
    format-free comparison stops being format-free and E36's confound comes back wearing
    E37's name.
  * **A measured-half move must be attributed, not counted.** "The peer set shrank" and
    "the company's numbers changed" are different problems with different fixes;
    `unexplained` - same inputs, different points - is the only one that would be a bug in
    the scorer, so it must never be able to hide inside either of the others.
  * **The four parts must sum to the points delta**, or the decomposition is a
    re-description rather than an accounting.
"""
from __future__ import annotations

from clab.research import e37_downgrades as e37


def _st(key, status, earned, mx=4, inputs=None):
    return {"key": key, "status": status, "earned": earned, "effective": earned,
            "max_points": mx, "inputs": inputs or {}, "provenance": {}}


def _card(ticker, components, score=50, coverage=1.0):
    return {"ticker": ticker, "cik": "0000000001", "name": ticker, "sector": "X",
            "score": score, "band": "WEAK", "coverage": coverage,
            "components": {code: {"subtests": subs} for code, subs in components.items()}}


def _parse(card):
    """load_subtests() takes a path; this is the same shape from an in-memory card."""
    subtests = {}
    for code, comp in card["components"].items():
        for st in comp["subtests"]:
            status = st["status"]
            subtests[st["key"]] = {
                "component": code, "status": status,
                "points": int(st["earned"] or 0) if status == "scored" else 0,
                "max_points": st["max_points"], "scored": status == "scored",
                "model": "", "rationale": None, "inputs": st["inputs"],
            }
    return {k: card.get(k) for k in ("ticker", "cik", "name", "sector", "score", "band",
                                     "coverage")} | {"subtests": subtests}


def _compare(v1_card, v2_card):
    return e37.compare_company(_parse(v1_card), _parse(v2_card))


# --------------------------------------------------------------- amendment 1

def test_filling_an_abstention_never_lowers_the_score():
    """The mechanism E37's first prediction assumed. It cannot happen here."""
    v1 = _card("AAA", {"SG": [_st("sg_a", "scored", 3), _st("sg_b", "no_data", None)]})
    v2 = _card("AAA", {"SG": [_st("sg_a", "scored", 3), _st("sg_b", "scored", 0)]})
    res = _compare(v1, v2)
    # A fill scored ZERO: the worst possible fill still cannot take points away.
    assert res["judged_fill_delta"] == 0
    assert res["judged_disagree_delta"] == 0
    assert res["common_score_delta"] == 0


def test_a_fill_adds_points_and_stays_out_of_common_support():
    v1 = _card("AAA", {"SG": [_st("sg_a", "scored", 3), _st("sg_b", "no_data", None)]})
    v2 = _card("AAA", {"SG": [_st("sg_a", "scored", 3), _st("sg_b", "scored", 4)]})
    res = _compare(v1, v2)
    assert res["judged_fill_delta"] == 4
    # The whole point of common support: the filled sub-test is invisible to it.
    assert res["common_score_delta"] == 0
    assert res["n_common_subtests"] == 1


def test_disagreement_is_what_common_support_keeps():
    v1 = _card("AAA", {"BQ": [_st("bq_moat", "scored", 5, mx=15)]})
    v2 = _card("AAA", {"BQ": [_st("bq_moat", "scored", 12, mx=15)]})
    res = _compare(v1, v2)
    assert res["judged_disagree_delta"] == 7
    assert res["common_score_delta"] == round(100.0 * 7 / 92, 2)


def test_a_lost_subtest_is_counted_apart_from_a_disagreement():
    """SCORED -> NULL is a generation failure, not a judgement, and E37 must not average
    the two together - it is the difference between KGS losing all of SG and META being
    marked down."""
    v1 = _card("AAA", {"SG": [_st("sg_a", "scored", 4)]})
    v2 = _card("AAA", {"SG": [_st("sg_a", "no_data", None)]})
    res = _compare(v1, v2)
    assert res["judged_lost_delta"] == -4
    assert res["judged_disagree_delta"] == 0
    assert res["n_common_subtests"] == 0


def test_entry_points_are_excluded_everywhere():
    """EN is not in `score` (E21), so it must not appear in any part of the split."""
    v1 = _card("AAA", {"EN": [_st("en_confluence", "scored", 0, mx=2)]})
    v2 = _card("AAA", {"EN": [_st("en_confluence", "scored", 2, mx=2)]})
    res = _compare(v1, v2)
    assert res["measured_points_delta"] == 0
    assert res["common_score_delta"] == 0
    assert res["n_common_subtests"] == 0


# --------------------------------------------------- measured-half attribution

def test_cohort_move_is_not_called_a_data_change():
    """Only the peer median moved - the company's own multiple is identical. Blaming a
    refreshed feed for this would send the next reader looking in the wrong place."""
    sa = {"inputs": {"ev_ebitda": 18.9, "peer_median": 17.7, "n_peers": 32}}
    sb = {"inputs": {"ev_ebitda": 18.9, "peer_median": 21.4, "n_peers": 19}}
    assert e37.classify_measured_move(sa, sb) == "cohort"


def test_vintage_move_wins_over_a_cohort_move():
    sa = {"inputs": {"ev_ebitda": 18.9, "peer_median": 17.7}}
    sb = {"inputs": {"ev_ebitda": 20.4, "peer_median": 21.4}}
    assert e37.classify_measured_move(sa, sb) == "vintage"


def test_identical_inputs_with_different_points_is_unexplained():
    """The only classification that would mean a defect in the scorer rather than in the
    comparison. It must be reachable, or it can never be observed."""
    sa = {"inputs": {"roic": 0.21}}
    sb = {"inputs": {"roic": 0.21}}
    assert e37.classify_measured_move(sa, sb) == "unexplained"


def test_float_noise_is_not_a_data_change():
    sa = {"inputs": {"roic": 0.2100000001}}
    sb = {"inputs": {"roic": 0.21}}
    assert e37.classify_measured_move(sa, sb) == "unexplained"


# ------------------------------------------------------------- the accounting

def test_the_four_parts_sum_to_the_points_delta():
    v1 = _card("AAA", {
        "SG": [_st("sg_a", "scored", 3), _st("sg_b", "no_data", None),
               _st("sg_c", "scored", 2)],
        "FE": [_st("fe_roic", "scored", 1, mx=2, inputs={"roic": 0.2})],
    })
    v2 = _card("AAA", {
        "SG": [_st("sg_a", "scored", 1), _st("sg_b", "scored", 4),
               _st("sg_c", "no_data", None)],
        "FE": [_st("fe_roic", "scored", 2, mx=2, inputs={"roic": 0.2})],
    })
    res = _compare(v1, v2)
    parts = (res["measured_points_delta"] + res["judged_disagree_delta"]
             + res["judged_fill_delta"] + res["judged_lost_delta"])
    v1_pts = 3 + 2 + 1
    v2_pts = 1 + 4 + 2
    assert parts == v2_pts - v1_pts
    assert res["judged_fill_delta"] == 4
    assert res["judged_lost_delta"] == -2
    assert res["judged_disagree_delta"] == -2
    assert res["measured_points_delta"] == 1


def test_score_denominator_follows_the_rubric():
    """94 total minus EN's 2. Typed in, this module would keep using the old scale after
    the next framework change - which is exactly what E26 caught elsewhere."""
    from clab.scoring import rubric
    assert e37._score_denominator() == rubric.TOTAL_POINTS - rubric.COMPONENTS["EN"][1]
