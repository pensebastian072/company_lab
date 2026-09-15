"""The weekend due-selector.

`next_refresh_due` was written by two modules, printed on a sheet, and read by nothing for
the whole life of the layer. These tests exist so it stays load-bearing: if the query ever
silently returns nothing again, that is a failure here rather than a quiet Saturday where
the job reports success and queues zero work.
"""
from __future__ import annotations

import datetime as dt

import pytest

from clab import config
from clab.external import refresh as R


class _FakeStore:
    def __init__(self, companies, objects):
        self._c, self._o = companies, objects

    def latest_companies(self):
        cols = ("ticker", "industry_id", "research_version", "next_refresh_due",
                "refresh_class", "last_research_date")
        latest = {}
        for raw in self._c:
            row = dict(zip(cols, raw))
            key = (str(row.get("last_research_date") or ""),
                   str(row.get("research_version") or ""))
            cur = latest.get(row["ticker"])
            if cur is None or key > cur[0]:
                latest[row["ticker"]] = (key, row)
        return [latest[t][1] for t in sorted(latest)]

    def connect(self):
        c, o = self._c, self._o

        class _Con:
            def __enter__(self_):
                return self_

            def __exit__(self_, *a):
                return False

            def execute(self_, sql, params=None):
                self_._out = c if "company_external" in sql else o
                return self_

            def fetchall(self_):
                return self_._out

        return _Con()


TODAY = dt.date(2026, 9, 7)


def _co(ticker, nxt=None, cls="QUARTERLY", seen=None, iid="regional_banking"):
    """(ticker, industry_id, research_version, next_refresh_due, refresh_class,
    last_research_date) - the SELECT order."""
    return (ticker, iid, "v1", nxt, cls, seen)


def _ob(iid, nxt=None, cls="STRUCTURAL", seen=None, status=None):
    return (iid, "financials", nxt, cls, seen, status)


def _store(companies=(), objects=()):
    return _FakeStore(list(companies), list(objects))


def test_an_explicit_due_date_in_the_past_is_due():
    p = R.due(store=_store([_co("AAA", nxt=dt.date(2026, 8, 1))]), today=TODAY)
    assert p["companies_due"] == 1
    assert p["company_rows"][0]["overdue_days"] == 37


def test_a_future_due_date_is_not_due():
    p = R.due(store=_store([_co("AAA", nxt=dt.date(2026, 12, 1))]), today=TODAY)
    assert p["companies_due"] == 0


def test_cadence_is_derived_from_refresh_class_when_no_explicit_date():
    """STRUCTURAL is a year, QUARTERLY is a quarter. A structural record researched six
    months ago is NOT due; a quarterly one is."""
    seen = TODAY - dt.timedelta(days=180)
    p = R.due(store=_store([_co("STRUCT", cls="STRUCTURAL", seen=seen),
                            _co("QTR", cls="QUARTERLY", seen=seen)]), today=TODAY)
    assert [r["ticker"] for r in p["company_rows"]] == ["QTR"]


def test_a_record_with_no_dates_at_all_is_not_silently_due_forever():
    """Neither an explicit date nor a last-research date means we cannot compute a
    cadence. It stays out rather than joining every batch forever."""
    p = R.due(store=_store([_co("NODATE", nxt=None, seen=None)]), today=TODAY)
    assert p["companies_due"] == 0


def test_most_overdue_comes_first():
    p = R.due(store=_store([
        _co("NEW", nxt=dt.date(2026, 9, 1)),
        _co("OLD", nxt=dt.date(2026, 1, 1)),
        _co("MID", nxt=dt.date(2026, 6, 1)),
    ]), today=TODAY)
    assert [r["ticker"] for r in p["company_rows"]] == ["OLD", "MID", "NEW"]


def test_the_budget_caps_the_take_and_reports_the_backlog():
    cos = [_co(f"T{i:03d}", nxt=dt.date(2026, 1, 1)) for i in range(50)]
    p = R.due(store=_store(cos), today=TODAY, budget=10)
    assert p["companies_due"] == 50
    assert p["companies_taken"] == 10
    assert p["backlog"] == 40


def test_raising_the_budget_is_the_only_edit_needed_to_change_throughput():
    """The user's requirement: 115 -> 200 -> 500 without touching anything else."""
    cos = [_co(f"T{i:03d}", nxt=dt.date(2026, 1, 1)) for i in range(300)]
    for b in (115, 200, 300):
        p = R.due(store=_store(cos), today=TODAY, budget=b)
        assert p["companies_taken"] == min(b, 300)


def test_batches_are_the_configured_size():
    cos = [_co(f"T{i:03d}", nxt=dt.date(2026, 1, 1)) for i in range(100)]
    p = R.due(store=_store(cos), today=TODAY, budget=100)
    sizes = [len(b) for b in p["batches"]]
    assert all(s == config.REFRESH_BATCH_SIZE for s in sizes[:-1])
    assert sum(sizes) == 100


def test_a_superseded_object_is_never_queued_for_refresh():
    """Re-researching a retired object would spend searches to refresh something no
    company resolves to."""
    p = R.due(store=_store([], [
        _ob("live", nxt=dt.date(2026, 1, 1)),
        _ob("dead", nxt=dt.date(2026, 1, 1), status="SUPERSEDED"),
    ]), today=TODAY)
    assert [r["industry_id"] for r in p["object_rows"]] == ["live"]


def test_structural_objects_do_not_come_due_weekly():
    """The whole design point. An object researched last Saturday must not be due this
    Saturday - that would spend a Codex batch rewriting unchanged text."""
    last_week = TODAY - dt.timedelta(days=7)
    p = R.due(store=_store([], [_ob("biotech", cls="STRUCTURAL", seen=last_week)]),
              today=TODAY)
    assert p["objects_due"] == 0


def test_the_selector_can_return_non_zero():
    """When a check returns zero, confirm it CAN return non-zero. The live store reads
    'nothing due' today, and that must be a real answer rather than a broken query."""
    empty = R.due(store=_store([], []), today=TODAY)
    assert empty["companies_due"] == 0
    loaded = R.due(store=_store([_co("AAA", nxt=dt.date(2026, 1, 1))]), today=TODAY)
    assert loaded["companies_due"] == 1


@pytest.mark.parametrize("cls,days", [("STRUCTURAL", 365), ("QUARTERLY", 91),
                                      ("EVENT_DRIVEN", 30)])
def test_the_registered_cadences(cls, days):
    assert config.REFRESH_DAYS[cls] == days


def test_a_company_with_several_research_versions_takes_ONE_slot():
    """company_external is keyed (ticker, research_version) and a company legitimately
    carries several arms - E51 and E53 were re-runs, and E59's batch 1 was re-run after a
    peer defect with the burned version deliberately left in the store.

    Measured on the live store 2026-09-08: 481 rows over 328 tickers, 152 with more than
    one. Treating rows as companies let one company eat several slots of the weekly
    budget and would queue a superseded arm as though it were current.
    """
    old = _co("AAA", nxt=dt.date(2026, 1, 1), seen=dt.date(2026, 1, 1))
    new = _co("AAA", nxt=dt.date(2026, 2, 1), seen=dt.date(2026, 2, 1))
    p = R.due(store=_store([old, new]), today=TODAY)
    assert p["companies_due"] == 1
    assert p["company_rows"][0]["due"] == dt.date(2026, 2, 1)


def test_the_latest_arm_wins_not_the_first_row_seen():
    """Order of rows out of the database must not decide which arm is current."""
    new = _co("AAA", nxt=dt.date(2026, 2, 1), seen=dt.date(2026, 2, 1))
    old = _co("AAA", nxt=dt.date(2026, 1, 1), seen=dt.date(2026, 1, 1))
    for rows in ([new, old], [old, new]):
        p = R.due(store=_store(rows), today=TODAY)
        assert p["company_rows"][0]["due"] == dt.date(2026, 2, 1)


# ----------------------------------------------------- EVENT_DRIVEN jumps


def test_a_filing_since_the_last_research_jumps_the_queue():
    """The facts moved, so the clock does not get a vote. A 10-K that landed yesterday
    is a better use of the batch than a company one day past its 91."""
    seen = TODAY - dt.timedelta(days=5)
    p = R.due(store=_store([_co("AAA", nxt=dt.date(2027, 1, 1), seen=seen)]),
              today=TODAY,
              filers={"AAA": {"form": "10-K", "filed": TODAY.isoformat()}})
    assert p["companies_due"] == 1
    assert p["event_jumps"] == 1
    row = p["company_rows"][0]
    assert row["event"] is True
    assert row["event_form"] == "10-K"


def test_a_filing_OLDER_than_the_research_does_not_jump():
    """We already read it. WLY filed 2026-09-04 and was researched 2026-09-05; queueing
    it would re-research a filing already in the record."""
    seen = TODAY - dt.timedelta(days=1)
    p = R.due(store=_store([_co("AAA", nxt=dt.date(2027, 1, 1), seen=seen)]),
              today=TODAY,
              filers={"AAA": {"form": "10-Q",
                              "filed": (TODAY - dt.timedelta(days=5)).isoformat()}})
    assert p["companies_due"] == 0
    assert p["event_jumps"] == 0


def test_an_event_sorts_ahead_of_a_more_overdue_company():
    p = R.due(store=_store([
        _co("OLD", nxt=dt.date(2026, 1, 1), seen=dt.date(2026, 1, 1)),
        _co("FILED", nxt=dt.date(2027, 1, 1), seen=TODAY - dt.timedelta(days=5)),
    ]), today=TODAY,
        filers={"FILED": {"form": "10-K", "filed": TODAY.isoformat()}})
    assert [r["ticker"] for r in p["company_rows"]] == ["FILED", "OLD"]


def test_a_filer_with_no_research_date_cannot_jump():
    """Without a known research date we cannot say the filing is newer, and guessing
    would re-queue the same company every week forever."""
    p = R.due(store=_store([_co("AAA", nxt=dt.date(2027, 1, 1), seen=None)]),
              today=TODAY,
              filers={"AAA": {"form": "10-K", "filed": TODAY.isoformat()}})
    assert p["event_jumps"] == 0


def test_no_filers_is_the_same_as_before_the_feature():
    seen = TODAY - dt.timedelta(days=5)
    args = dict(store=_store([_co("AAA", nxt=dt.date(2026, 1, 1), seen=seen)]),
                today=TODAY)
    assert R.due(**args)["companies_due"] == R.due(**args, filers={})["companies_due"]
    assert R.due(**args, filers=None)["event_jumps"] == 0
