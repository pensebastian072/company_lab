"""E29's measurement - the instrument that decides whether a question has a referent.

E29 came back with an EMPTY map, so nothing in production reads this module. That is
exactly why it is pinned: the next time someone asks "should a REIT be asked about
backlog?", this script is the thing that answers, and a criterion that quietly stops
discriminating would return an empty map for the wrong reason and look identical.

The properties that matter:

  * Rule C (P2) must refuse a sub-test the model cannot answer ANYWHERE, because dropping
    it would launder a retrieval failure into a scoring rule - E12 Amendment 1's whole
    point;
  * P5 must separate "this sector's filings cannot be read" from "this question has no
    referent here", which is the job P5 was rewritten to do (E29 Amendment 1);
  * P3 must never be computable. If a script could decide it, it would be a null rate
    wearing prose;
  * the loss itemisation must keep category error and scored shortfall apart, because
    only the first is ever in scope and adding them overstates what a map can do.
"""
from __future__ import annotations

from clab.research import e29_applicability as e29


def _card(ticker, sector, subtests, comp="SG"):
    return {"ticker": ticker, "cik": ticker, "sector": sector,
            "components": {comp: {"subtests": subtests}}}


def _st(key, status, mx=4, earned=None):
    return {"key": key, "status": status, "max_points": mx, "earned": earned}


def _universe(sector_specs):
    """sector -> {subtest: (n_null, n_scored)} -> a list of scorecards."""
    cards = []
    for sector, spec in sector_specs.items():
        n = max(nn + ns for nn, ns in spec.values())
        for i in range(n):
            subs = []
            for key, (n_null, _n_scored) in spec.items():
                status = "no_data" if i < n_null else "scored"
                subs.append(_st(key, status, 4, None if status == "no_data" else 2))
            cards.append(_card(f"{sector[:2]}{i}", sector, subs))
    return cards


# ------------------------------------------------------------------ the matrix
def test_the_matrix_reports_every_sector_not_a_worst_four_view():
    """A spread cannot be computed from a table that drops its own minimum."""
    cards = _universe({
        "Alpha": {"q": (0, 40)},
        "Beta": {"q": (40, 0)},
    })
    m = e29.matrix(cards)
    assert set(m["subtests"]["q"]["by_sector"]) == {"Alpha", "Beta"}
    assert m["subtests"]["q"]["by_sector"]["Alpha"]["null_pct"] == 0.0
    assert m["subtests"]["q"]["by_sector"]["Beta"]["null_pct"] == 100.0


def test_the_e19_unassessed_weights_are_not_candidates():
    """`bq_moat_unassessed` carries points, not a question - it can never be dropped."""
    cards = [_card("A", "Alpha", [_st("bq_moat_unassessed", "no_data", 8)], comp="BQ")]
    assert "bq_moat_unassessed" not in e29.matrix(cards)["subtests"]


# ------------------------------------------------------------------ Rule C, P2
def test_a_question_the_model_cannot_answer_anywhere_is_REFUSED():
    """P2 / Rule C. Null everywhere is a retrieval failure, not an applicability fact."""
    cards = _universe({
        "Alpha": {"q": (36, 4), "other": (0, 40)},      # 90% null
        "Beta": {"q": (40, 0), "other": (0, 40)},       # 100% null
    })
    q = [c for c in e29.evaluate(e29.matrix(cards)) if c["subtest"] == "q"]
    assert q, "the pair should be evaluated, then refused"
    assert not any(c["P2_answerable_somewhere"] for c in q)
    assert not any(c["machine_criteria_pass"] for c in q)


def test_a_question_answered_in_one_sector_and_absent_in_another_is_ADMITTED():
    cards = _universe({
        "Alpha": {"q": (4, 36), "other": (0, 40)},      # 10% null - answerable
        "Beta": {"q": (38, 2), "other": (0, 40)},       # 95% null - near-total
    })
    beta = next(c for c in e29.evaluate(e29.matrix(cards))
                if c["subtest"] == "q" and c["sector"] == "Beta")
    assert beta["P1_spread"] and beta["P2_answerable_somewhere"]
    assert beta["P4_near_total_in_sector"] and beta["P5_sector_specific"]
    assert beta["machine_criteria_pass"]


def test_a_sector_that_is_merely_mixed_fails_P4():
    """65% null is a mixture of companies, and this instrument cannot split it."""
    cards = _universe({
        "Alpha": {"q": (4, 36), "other": (0, 40)},
        "Beta": {"q": (26, 14), "other": (0, 40)},      # 65% null, like REIT backlog
    })
    beta = next(c for c in e29.evaluate(e29.matrix(cards))
                if c["subtest"] == "q" and c["sector"] == "Beta")
    assert not beta["P4_near_total_in_sector"]
    assert not beta["machine_criteria_pass"]


# ------------------------------------------------------------------ P5
def test_a_sector_whose_whole_component_is_unreadable_is_REFUSED_by_P5():
    """The failure P4 cannot see: the pack cannot be read for this sector at all."""
    cards = _universe({
        "Alpha": {"q": (4, 36), "other": (0, 40), "third": (0, 40)},
        # Beta abstains on EVERYTHING, so `q` says nothing about Beta's business
        "Beta": {"q": (38, 2), "other": (37, 3), "third": (37, 3)},
    })
    beta = next(c for c in e29.evaluate(e29.matrix(cards))
                if c["subtest"] == "q" and c["sector"] == "Beta")
    assert beta["P4_near_total_in_sector"], "P4 alone would have admitted it"
    assert not beta["P5_sector_specific"], "P5 must catch the flat-null sector"
    assert not beta["machine_criteria_pass"]


def test_P5_is_measured_against_the_sectors_own_baseline_not_the_universes():
    cards = _universe({
        "Alpha": {"q": (4, 36), "other": (0, 40)},
        "Beta": {"q": (38, 2), "other": (2, 38)},       # baseline 5%, q at 95%
    })
    beta = next(c for c in e29.evaluate(e29.matrix(cards))
                if c["subtest"] == "q" and c["sector"] == "Beta")
    assert beta["component_baseline_null_pct"] == 5.0
    assert beta["specificity_pp"] == 90.0


# ------------------------------------------------------------------ P3
def test_P3_is_never_computed_and_says_so():
    """A script that could decide P3 would be a null rate wearing prose."""
    cards = _universe({"Alpha": {"q": (4, 36), "other": (0, 40)},
                       "Beta": {"q": (38, 2), "other": (0, 40)}})
    out = e29.evaluate(e29.matrix(cards))
    for c in out:
        assert "REQUIRED" in c["P3_written_business_reason"]
    # and the machine verdict must never be named as a pass of the WHOLE bar, because
    # P3 is still outstanding on every row it marks true
    assert "machine_criteria_pass" in out[0]
    assert not {"pass", "passes", "admitted", "approved"} & set(out[0])


def test_a_small_sector_never_sets_a_spread_endpoint():
    """Without a floor a 2-company sector defines both ends of every spread."""
    cards = _universe({
        "Alpha": {"q": (4, 36), "other": (0, 40)},     # 10% null, n=40
        "Beta": {"q": (20, 20), "other": (0, 40)},     # 50% null, n=40
        "Tiny": {"q": (2, 0), "other": (0, 2)},        # n=2, 100% null
    })
    out = e29.evaluate(e29.matrix(cards))
    assert out, "the two big sectors must still be evaluated"
    assert all(c["sector"] != "Tiny" for c in out)
    assert all(c["worst_sector"] != "Tiny" for c in out)
    # Tiny would have set the top of the spread at 100%; without it the spread is 40pp
    assert next(c for c in out if c["subtest"] == "q")["spread_pp"] == 40.0


# ------------------------------------------------------------------ itemisation
def test_category_error_and_scored_shortfall_are_never_added_together():
    """Only the first is ever in scope; summing them overstates what a map can do."""
    cards = [
        _card("A", "Alpha", [_st("q", "no_data", 4), _st("r", "scored", 4, 1)]),
        _card("B", "Alpha", [_st("q", "no_data", 4), _st("r", "scored", 4, 0)]),
    ]
    it = e29.itemise(cards)["Alpha"]
    assert it["category_error"] == {"q": 8}
    assert it["scored_shortfall"] == {"r": 7}
    assert it["category_error_total"] == 8
    assert it["scored_shortfall_total"] == 7


def test_the_unassessed_weight_counts_as_category_error():
    """E19's weight IS the loss, even though it is not a question."""
    cards = [_card("A", "Alpha", [_st("bq_moat", "scored", 7, 3),
                                  _st("bq_moat_unassessed", "no_data", 8)], comp="BQ")]
    it = e29.itemise(cards)["Alpha"]
    assert it["category_error"] == {"bq_moat_unassessed": 8}
    assert it["scored_shortfall"] == {"bq_moat": 4}
