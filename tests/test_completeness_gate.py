"""An object that says nothing does not get to exist.

E61 is why this gate exists. Its 25 Industrials objects passed every check the layer had -
138 of 138 claims VERIFIED_LOCAL, no non-UNKNOWN field without a claim naming it, lifecycle
guards intact - and **20 of 25 answered nothing at all**, with `replication_difficulty`
UNKNOWN on every single object. 259 companies were about to be judged against objects that
assert nothing.

That is the E54 abstention collapse one layer up: perfect quality metrics over an empty
answer. These tests pin the gate that catches it, and pin that a retirement RETAINS rather
than erases.
"""
from __future__ import annotations

import datetime as dt

import pytest

from clab.external import batch_health as BH
from clab.external.schema import UNKNOWN
from clab.external.store import ExternalStore

pytest.importorskip("duckdb")


def _obj(iid, sg, rd, sr, sector="industrials"):
    return {"industry_id": iid, "version": "v1", "sector_id": sector,
            "brief": "b", "structural_growth": sg, "moat_mechanism": "m",
            "replication_difficulty": rd, "substitution_risk": sr,
            "key_metrics": ["a"], "refresh_class": "STRUCTURAL",
            "last_updated": dt.datetime(2026, 9, 8),
            "next_refresh_due": dt.date(2026, 12, 1)}


@pytest.fixture()
def store(tmp_path):
    st = ExternalStore(tmp_path / "t.duckdb")
    st.upsert_industry(_obj("full", "MODERATE", "HIGH", "LOW"))
    st.upsert_industry(_obj("two", "MODERATE", "HIGH", UNKNOWN))
    st.upsert_industry(_obj("one", UNKNOWN, UNKNOWN, "MODERATE"))
    st.upsert_industry(_obj("empty", UNKNOWN, UNKNOWN, UNKNOWN))
    return st


def test_the_bar_is_every_structural_field_not_most(store):
    r = BH.completeness(store=store)
    assert r["required"] == 3
    assert {x["industry_id"] for x in r["passed"]} == {"full"}
    assert {x["industry_id"] for x in r["failed"]} == {"two", "one", "empty"}


def test_unknown_is_not_an_answer(store):
    """UNKNOWN is NO_DATA. An object whose fields are all UNKNOWN concluded nothing,
    however well-sourced its claims are."""
    r = BH.completeness(store=store)
    empty = next(x for x in r["failed"] if x["industry_id"] == "empty")
    assert empty["answered"] == 0


def test_a_well_evidenced_object_that_concludes_nothing_still_fails():
    """The E61 shape exactly: every quality metric clean, nothing asserted. Evidence
    quality and answer coverage are different questions and this gate asks the second."""
    r = BH.completeness(store=_FakeEmpty())
    assert r["n_pass"] == 0
    assert r["n_fail"] == 1


class _FakeEmpty:
    def connect(self):
        class _Con:
            def __enter__(self_):
                return self_

            def __exit__(self_, *a):
                return False

            def execute(self_, sql, params=None):
                self_._out = [("perfectly_sourced", "industrials",
                               UNKNOWN, UNKNOWN, UNKNOWN)]
                return self_

            def fetchall(self_):
                return self_._out
        return _Con()


def test_only_an_object_that_answered_NOTHING_is_auto_retired(store):
    """THE TWO BARS, and the difference is load-bearing.

    3-of-3 is the SHIP bar. Auto-retire is ZERO answers. This repo's own standard rules
    say a reasoned UNKNOWN is a RESULT, not a gap - E53's utilities were correctly 0 of 59
    on market_share_direction because a regulated utility has no contestable share.

    A strict 3-of-3 auto-retire deleted both cases on 2026-09-09: 20 empty Industrials
    objects AND 11 working ones including regional_banking at 2 of 3, which blocked a
    staged 42-company batch. Deleting an honest refusal is the abstention error wearing a
    quality check's clothes.
    """
    out = BH.enforce(store=store)
    assert out["applied"] is False
    assert out["would_retire"] == ["empty"]
    assert sorted(out["below_ship_bar"]) == ["one", "two"]


def test_enforce_retires_the_empty_one_but_retains_it(store):
    """Retired operationally, retained evidentially - the row stays readable."""
    out = BH.enforce(store=store, apply=True)
    assert out["applied"] is True
    assert out["n"] == 1

    r = BH.completeness(store=store)
    assert r["n_objects"] == 3                      # empty is gone, partials survive
    assert {x["industry_id"] for x in r["passed"]} == {"full"}
    assert {x["industry_id"] for x in r["failed"]} == {"one", "two"}

    row = store.industry("empty", include_superseded=True)
    assert row is not None
    assert row["status"] == "SUPERSEDED"
    assert "answered" in (row["superseded_reason"] or "")


def test_a_partial_object_survives_and_is_reported_for_justification(store):
    """An object at 1 or 2 of 3 is kept and flagged. Only the RESEARCHER knows whether
    each UNKNOWN is a reasoned refusal or an abstention, so the prompt requires a written
    reason per UNKNOWN rather than the gate guessing."""
    BH.enforce(store=store, apply=True)
    assert store.industry("two") is not None
    assert store.industry("one") is not None
    assert store.industry("empty") is None          # active lookup omits it


def test_a_retirement_names_no_replacement(store):
    """There is no replacement - the unit needs re-researching. Leaving superseded_by
    empty is what makes resolution OMIT rather than fall back to an older arm, which is
    the E53 mistake."""
    BH.enforce(store=store, apply=True)
    row = store.industry("empty", include_superseded=True)
    assert not row["superseded_by"]


def test_sector_scoping(store):
    store.upsert_industry(_obj("elsewhere", UNKNOWN, UNKNOWN, UNKNOWN,
                               sector="financials"))
    r = BH.completeness(store=store, sector_id="industrials")
    assert all(x["sector_id"] == "industrials" for x in r["failed"])
    assert "elsewhere" not in {x["industry_id"] for x in r["failed"]}


def test_the_gate_can_return_a_non_zero_pass_count(store):
    """When a check reports failures, confirm it can also report a pass - a gate that
    fails everything is as broken as one that passes everything."""
    r = BH.completeness(store=store)
    assert r["n_pass"] >= 1
    assert r["n_fail"] >= 1
