"""The EDGAR daily-index watcher.

Two things here were live defects in the first draft and are pinned so they cannot come
back, because both failed SILENTLY - the module reported "nothing filed", which is
indistinguishable from a quiet market:

1. `form.idx` is FIXED-WIDTH; only `master.idx` is pipe-delimited. Parsing the wrong one
   on pipes matched zero rows against an 800 KB file that had plenty.
2. SEC answers **403**, not 404, for a day it never published. Keying the weekend case on
   404 alone reported three errors every single week.
"""
from __future__ import annotations

import datetime as dt

import pytest

from clab.external import earnings_watch as EW

# Real master.idx shape: header block, then CIK|Company|Form|YYYYMMDD|path
SAMPLE = """Description:           Daily Index of EDGAR Dissemination Feed
Last Data Received:    Sep 8, 2026
Comments:              webmaster@sec.gov

CIK|Company Name|Form Type|Date Filed|File Name
--------------------------------------------------------------------------------
1000275|ROYAL BANK OF CANADA|424B2|20260908|edgar/data/1000275/x.txt
320193|Apple Inc.|10-Q|20260908|edgar/data/320193/y.txt
789019|MICROSOFT CORP|10-K|20260908|edgar/data/789019/z.txt
1090727|UNITED PARCEL SERVICE|8-K|20260908|edgar/data/1090727/w.txt
"""


def test_it_reads_master_idx_column_order_not_form_idx():
    """master.idx is CIK|Company|Form|Date|Path. form.idx is a different order AND is
    fixed-width. Reading the wrong layout matched nothing and looked like a quiet day."""
    rows = EW.parse_index(SAMPLE)
    assert [r["form"] for r in rows] == ["10-Q", "10-K"]
    assert rows[0]["cik"] == "0000320193"          # zero-padded to match the book
    assert rows[0]["filed"] == dt.date(2026, 9, 8)
    assert rows[0]["company"] == "Apple Inc."


def test_the_url_points_at_master_not_form():
    url = EW.index_url(dt.date(2026, 9, 8))
    assert "master.20260908.idx" in url
    assert "form." not in url
    assert "QTR3" in url


def test_8k_is_not_in_the_default_forms():
    """An 8-K can be a CEO change or a parking-lot sale. Including it by default would
    put most of the book in the queue most weeks."""
    assert "8-K" not in EW.DEFAULT_FORMS
    rows = EW.parse_index(SAMPLE)
    assert all(r["form"] != "8-K" for r in rows)
    widened = EW.parse_index(SAMPLE, forms=("8-K",))
    assert [r["form"] for r in widened] == ["8-K"]


def test_a_weekend_403_is_not_an_error():
    """SEC returns 403 for a day it never published. Saturday must not raise an alarm."""
    def boom(url):
        raise RuntimeError("HTTP 403 " + url + ": Forbidden")

    sat = dt.date(2026, 9, 5)
    assert sat.weekday() == 5
    res = EW.fetch_day(sat, fetcher=boom)
    assert res["rows"] == []
    assert "error" not in res
    assert res["note"] == "no index published"
    assert not res.get("weekday_miss")


def test_a_weekday_403_is_recorded_as_unavailable_not_as_no_filings():
    """Ambiguous - not yet published, or rate-limited. It must not read as 'nothing
    filed', which is the silent-zero failure this module already had once."""
    def boom(url):
        raise RuntimeError("HTTP 403 " + url + ": Forbidden")

    tue = dt.date(2026, 9, 8)
    assert tue.weekday() == 1
    res = EW.fetch_day(tue, fetcher=boom)
    assert res["note"] == "index unavailable"
    assert res["weekday_miss"] is True


def test_a_dead_feed_escalates_rather_than_reporting_a_quiet_market(monkeypatch):
    """If no weekday index is reachable, saying 'nothing filed' would be graceful
    degradation hiding a wiring failure."""
    monkeypatch.setattr(EW, "_cik_to_ticker", lambda: {"0000320193": "AAPL"})

    def boom(url):
        raise RuntimeError("HTTP 403 " + url + ": Forbidden")

    res = EW.recent_filers(days=3, today=dt.date(2026, 9, 9), fetcher=boom)
    assert res["feed_ok"] is False
    assert res["n_filers_in_book"] == 0
    assert any("NOT evidence that nothing was filed" in e for e in res["errors"])


def test_only_companies_in_the_book_come_back(monkeypatch):
    monkeypatch.setattr(EW, "_cik_to_ticker", lambda: {"0000320193": "AAPL"})
    res = EW.recent_filers(days=1, today=dt.date(2026, 9, 8),
                           fetcher=lambda url: SAMPLE)
    assert res["feed_ok"] is True
    assert list(res["filers"]) == ["AAPL"]          # MSFT filed but is not in this book
    assert res["filers"]["AAPL"]["form"] == "10-Q"


def test_the_newest_filing_wins_for_a_company(monkeypatch):
    """A company filing twice in the window is queued once, on its latest filing."""
    monkeypatch.setattr(EW, "_cik_to_ticker", lambda: {"0000320193": "AAPL"})
    old = SAMPLE.replace("20260908|edgar/data/320193/y.txt",
                         "20260901|edgar/data/320193/old.txt")

    def by_day(url):
        return SAMPLE if "20260908" in url else old

    res = EW.recent_filers(days=8, today=dt.date(2026, 9, 8), fetcher=by_day)
    assert res["filers"]["AAPL"]["filed"] == "2026-09-08"


@pytest.mark.parametrize("day,qtr", [(dt.date(2026, 1, 5), 1), (dt.date(2026, 4, 1), 2),
                                     (dt.date(2026, 9, 8), 3), (dt.date(2026, 12, 31), 4)])
def test_quarter_is_derived_correctly(day, qtr):
    assert f"QTR{qtr}" in EW.index_url(day)
