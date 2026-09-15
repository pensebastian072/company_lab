"""P3's verdicts, pinned before the data exists.

The whole value of a registered prediction is that the thresholds were fixed before
anyone saw the numbers. These tests are the receipt: every verdict boundary is exercised
on synthetic values, so the evaluator cannot be quietly retuned once the real five come
back and someone dislikes the answer.
"""
from __future__ import annotations

import pytest

from clab.external.schema import UNKNOWN
from clab.research import e56_p3 as P3


class _FakeStore:
    """Stands in for ExternalStore.industry(), which is all the evaluator uses."""

    def __init__(self, values: dict):
        self._values = values

    def industry(self, industry_id, version=None, **kw):
        if industry_id not in self._values:
            return None
        return {"industry_id": industry_id,
                "structural_growth": self._values[industry_id]}


def _all(*values):
    return _FakeStore(dict(zip(P3.E56_OBJECTS, values)))


def test_incomplete_until_every_object_is_ingested():
    store = _FakeStore({P3.E56_OBJECTS[0]: "MODERATE"})
    res = P3.evaluate(store=store)
    assert res["verdict"] == "INCOMPLETE"
    assert res["n_missing"] == 4


def test_confirmed_when_the_clustering_repeats():
    res = P3.evaluate(store=_all("MODERATE", "MODERATE", "MODERATE", "MODERATE", "HIGH"))
    assert res["verdict"] == "CONFIRMED"
    assert res["modal_share"] == 0.8
    assert res["modal_value"] == "MODERATE"


def test_refuted_when_they_spread():
    res = P3.evaluate(store=_all("MODERATE", "HIGH", "FLAT", "MODERATE", "DECLINING"))
    assert res["verdict"] == "REFUTED"
    assert res["modal_share"] == 0.4


def test_the_threshold_is_inclusive_at_exactly_eighty_percent():
    """4 of 5 is 0.8 and the registration says >= 0.8. A boundary that drifted by one
    object would change the verdict, so it is pinned rather than assumed."""
    res = P3.evaluate(store=_all("MODERATE", "MODERATE", "MODERATE", "MODERATE", "FLAT"))
    assert res["modal_share"] == P3.MODAL_THRESHOLD
    assert res["verdict"] == "CONFIRMED"


def test_two_answers_cannot_confirm_p3():
    """THE HOLE THIS EVALUATOR WAS WRITTEN TO CLOSE.

    UNKNOWN is NO_DATA and never enters the denominator, so without a floor a single
    MODERATE among four refusals scores a modal share of 1.0 and 'confirms' the
    prediction on a sample of one.
    """
    res = P3.evaluate(store=_all("MODERATE", "MODERATE", UNKNOWN, UNKNOWN, UNKNOWN))
    assert res["n_answered"] == 2
    assert res["verdict"] == "INDETERMINATE"
    assert res["modal_share"] == 1.0          # computable, and deliberately not decisive


def test_one_answer_is_indeterminate_not_confirmed():
    res = P3.evaluate(store=_all("MODERATE", UNKNOWN, UNKNOWN, UNKNOWN, UNKNOWN))
    assert res["verdict"] == "INDETERMINATE"


def test_three_answers_is_the_registered_minimum():
    res = P3.evaluate(store=_all("MODERATE", "MODERATE", "MODERATE", UNKNOWN, UNKNOWN))
    assert res["n_answered"] == P3.MIN_ANSWERED
    assert res["verdict"] == "CONFIRMED"


def test_unknown_is_never_counted_as_a_value():
    """If UNKNOWN leaked into the distribution it could become the modal 'answer' and
    a sector nobody could read would look like a sector everyone agreed on."""
    res = P3.evaluate(store=_all(UNKNOWN, UNKNOWN, UNKNOWN, "HIGH", "FLAT"))
    assert UNKNOWN not in res["distribution"]
    assert res["n_unknown"] == 3
    assert res["verdict"] == "INDETERMINATE"


def test_every_reading_names_the_confound_or_the_limit():
    """A verdict that does not say what it fails to establish is how a small-n result
    gets quoted later as settled."""
    confirmed = P3.evaluate(store=_all("MODERATE", "MODERATE", "MODERATE",
                                       "MODERATE", "HIGH"))["reading"]
    assert "not excluded" in confirmed or "confound" in confirmed
    indet = P3.evaluate(store=_all("MODERATE", UNKNOWN, UNKNOWN,
                                   UNKNOWN, UNKNOWN))["reading"]
    assert "not evidence either way" in indet


@pytest.mark.parametrize("iid", P3.E56_OBJECTS)
def test_the_five_objects_are_the_ones_the_taxonomy_creates(iid):
    """A typo here would evaluate P3 against an object that does not exist, and
    INCOMPLETE would look like a research failure instead of a test bug."""
    from clab.external import taxonomy as T
    assert iid in set(T.INDUSTRY_OVERRIDES.values())
