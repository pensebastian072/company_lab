"""The gauge for the two things E54 passed every existing check while doing.

E54 built 15 industry objects, verified 75 of 75 claims, answered 41 of 45 structural
fields - and drew EXACTLY 5 claims on every object while never once using the end of a
scale. `compare()` cannot see either: it watches company fill rates, and E54's problem was
not abstention. These tests pin the two signals and, more importantly, pin that the module
reports rather than judges - a mature sector sitting in the middle is not a defect.
"""
from __future__ import annotations

from clab.external import batch_health as BH
from clab.external.schema import UNKNOWN


class _FakeStore:
    """Two fixed result sets, chosen by which table the SQL names."""

    def __init__(self, objects, claim_counts):
        self._objects = objects
        self._counts = claim_counts

    def connect(self):
        objects, counts = self._objects, self._counts

        class _Con:
            def __enter__(self_):
                return self_

            def __exit__(self_, *a):
                return False

            def execute(self_, sql, params=None):
                if "industry_intelligence" in sql:
                    # Build rows from the SELECT list rather than a fixed tuple, so
                    # adding a column to the query does not silently truncate the zip
                    # and drop the ordinals off the end.
                    cols = sql.split("SELECT ")[1].split(" FROM ")[0].split(", ")
                    self_._out = [tuple(o.get(c) for c in cols) for o in objects]
                else:
                    self_._out = list(counts.items())
                return self_

            def fetchall(self_):
                return self_._out

        return _Con()


def _obj(iid, sector, sg, rd, sr, *, version="2026-09-06", status=None):
    return {"industry_id": iid, "sector_id": sector, "structural_growth": sg,
            "replication_difficulty": rd, "substitution_risk": sr,
            "version": version, "status": status}


def test_uniform_depth_is_flagged_and_varied_depth_is_not():
    objs = [_obj(f"i{n}", "financials", "MODERATE", "HIGH", "MODERATE") for n in range(4)]
    store = _FakeStore(objs, {f"i{n}": 5 for n in range(4)})
    res = BH.object_health(store=store, sector_id="financials")
    assert res["subject"]["claims"]["uniform"] is True
    assert res["subject"]["claims"]["distinct_counts"] == 1

    store = _FakeStore(objs, {"i0": 4, "i1": 7, "i2": 5, "i3": 11})
    res = BH.object_health(store=store, sector_id="financials")
    assert res["subject"]["claims"]["uniform"] is False
    assert res["subject"]["claims"] == {"min": 4, "max": 11, "distinct_counts": 4,
                                        "uniform": False}


def test_a_single_object_is_not_called_uniform():
    """One object cannot have varied depth. Calling that a quota would be noise."""
    store = _FakeStore([_obj("i0", "financials", "MODERATE", "HIGH", "LOW")], {"i0": 5})
    assert BH.object_health(store=store, sector_id="financials")["subject"]["claims"]["uniform"] is False


def test_endpoint_and_modal_share_measure_the_middle_reach():
    """E54's shape: everything MODERATE, no end of any scale."""
    middle = [_obj(f"m{n}", "financials", "MODERATE", "HIGH", "MODERATE") for n in range(9)]
    middle.append(_obj("m9", "financials", "HIGH", "MODERATE", "ELEVATED"))
    spread = [
        _obj("s0", "energy", "DECLINING", "EXTREME", "SEVERE"),
        _obj("s1", "energy", "FLAT", "MODERATE", "LOW"),
        _obj("s2", "energy", "EXCEPTIONAL", "LOW", "ELEVATED"),
        _obj("s3", "energy", "MODERATE", "HIGH", "MODERATE"),
    ]
    store = _FakeStore(middle + spread, {o["industry_id"]: 5 for o in middle + spread})
    res = BH.object_health(store=store, sector_id="financials")

    sg = res["subject"]["fields"]["structural_growth"]
    assert sg["modal_share"] == 0.9
    assert sg["endpoint_share"] == 0.0
    assert res["subject"]["fields"]["replication_difficulty"]["endpoint_share"] == 0.0

    base = res["baseline"]["fields"]
    assert base["structural_growth"]["endpoint_share"] == 0.5   # DECLINING + EXCEPTIONAL
    assert base["replication_difficulty"]["endpoint_share"] == 0.5  # EXTREME + LOW


def test_unknown_is_excluded_from_the_denominator_not_counted_as_middle():
    """UNKNOWN is NO_DATA. Counting it as a value would read a refusal as a mid answer."""
    objs = [
        _obj("i0", "financials", UNKNOWN, UNKNOWN, UNKNOWN),
        _obj("i1", "financials", "MODERATE", "HIGH", "LOW"),
    ]
    store = _FakeStore(objs, {"i0": 5, "i1": 5})
    sg = BH.object_health(store=store, sector_id="financials")["subject"]["fields"]["structural_growth"]
    assert sg["answered"] == 1
    assert sg["distribution"] == {"MODERATE": 1}


def test_it_reports_and_does_not_judge():
    """No verdict, no REGRESSION, no pass/fail. A mature sector may sit in the middle."""
    objs = [_obj(f"i{n}", "financials", "MODERATE", "HIGH", "MODERATE") for n in range(5)]
    store = _FakeStore(objs, {f"i{n}": 5 for n in range(5)})
    res = BH.object_health(store=store, sector_id="financials")
    assert "verdict" not in res
    assert set(res) == {"sector_id", "subject", "baseline"}


def test_no_sector_describes_the_corpus_with_no_baseline():
    objs = [_obj("i0", "financials", "MODERATE", "HIGH", "LOW"),
            _obj("i1", "energy", "FLAT", "EXTREME", "SEVERE")]
    store = _FakeStore(objs, {"i0": 5, "i1": 9})
    res = BH.object_health(store=store)
    assert res["baseline"] is None
    assert res["subject"]["n_objects"] == 2
