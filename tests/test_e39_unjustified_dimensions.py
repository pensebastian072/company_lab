"""E39's instrument - the counterfactual `bq_moat`, and the floor that decides everything.

E39's whole result turns on one thing: dropping an unjustified dimension can take a
company **below the 6-of-11 quorum**, and then `bq_moat` is not lower, it is gone. That is
the difference between "the ranking tightens" and "271 companies leave the ranking", so
the floor behaviour is pinned rather than trusted.

`unjustified` follows E36 amendment 1: `terse` is a judgement and must not be swept in
with a page header or the literal word null.
"""
from __future__ import annotations

from clab.research import e39_unjustified_dimensions as e39
from clab.scoring import rubric


def test_below_the_quorum_is_none_not_zero():
    """Hard rule 2, in the one place E39 could have broken it: a company judged on five
    dimensions has no moat score, not a moat score of zero."""
    assert e39.bq_points([5] * (rubric.BQ_MIN_DIMENSIONS_SCORED - 1)) is None
    assert e39.bq_points([5] * rubric.BQ_MIN_DIMENSIONS_SCORED) is not None


def test_the_mapping_is_the_rubric_mapping():
    """round(mean / 5 * 15) - rubric A2. All fives is the full component."""
    assert e39.bq_points([5] * 11) == rubric.COMPONENTS["BQ"][1]
    assert e39.bq_points([0] * 11) == 0
    # A mean of 2.5 of 5 is half the component.
    assert e39.bq_points([2, 3] * 5 + [2]) == round(
        (2 * 6 + 3 * 5) / 11 / 5 * rubric.COMPONENTS["BQ"][1])


def test_dropping_a_low_silent_score_raises_the_component():
    """The direction E39 found, and the reason 'require a reason' is not a tightening."""
    with_silent = [4, 4, 4, 4, 4, 4, 0, 0]
    without = [4, 4, 4, 4, 4, 4]
    assert e39.bq_points(without) > e39.bq_points(with_silent)


def test_a_terse_rationale_is_not_unjustified():
    assert not e39.unjustified("Strong brand in a commodity category.")
    assert not e39.unjustified("Established brand.")


def test_the_literal_null_and_the_empty_string_are_unjustified():
    """1,754 'null' + 128 'Null' + 303 '' in production. All three must be caught, and
    case must not matter - a check that missed 'Null' would report 128 fewer and look
    just as convincing."""
    assert e39.unjustified("null")
    assert e39.unjustified("Null")
    assert e39.unjustified("")
    assert e39.unjustified(None)
