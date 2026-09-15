"""CIK resolution when the index page has no CIK column.

The S&P 400 Wikipedia table carries no CIK. `r.get("cik") or et.cik_for(...)` looked
like a correct fallback and was not: **NaN is truthy**, so the missing value won, every
row became CIK "0000000nan", they all collided in the dedupe, and a 400-company crawl
ran as ONE company and reported "0 scored, 1 failed" without anything looking wrong.

Two defences are tested here: resolve the CIK properly, and refuse to crawl a universe
that lost most of its members to deduplication.
"""
from __future__ import annotations

import math

import pandas as pd
import pytest

from clab.runner import batch


@pytest.mark.parametrize("bad", [None, float("nan"), "", "  ", "nan", "NaN", "None",
                                 "<NA>"])
def test_missing_cik_reads_as_missing(bad):
    assert batch._clean_cik(bad) is None


@pytest.mark.parametrize("good,want", [("0000320193", "0000320193"), (320193, "320193"),
                                       (320193.0, "320193"), (" 320193 ", "320193")])
def test_present_cik_is_kept(good, want):
    assert batch._clean_cik(good) == want


def test_nan_is_truthy_which_is_why_the_or_fallback_failed():
    """Pins the language behaviour the bug depended on, so it stays understood."""
    assert bool(float("nan")) is True
    assert (float("nan") or "fallback") is not "fallback"  # noqa: F632


def _frame(n=40, with_cik=False):
    return pd.DataFrame([
        {"ticker": f"T{i:03d}", "name": f"Co {i}",
         "cik": (f"{i:010d}" if with_cik else math.nan),
         "gics_sector": "Industrials", "gics_sub_industry": "Machinery"}
        for i in range(n)])


def test_universe_without_a_cik_column_resolves_from_the_ticker_map(monkeypatch):
    df = _frame(40, with_cik=False)
    monkeypatch.setattr(batch.uni, "fetch_universe", lambda tier, force=False: df)
    monkeypatch.setattr(batch.et, "load_map", lambda: {})
    monkeypatch.setattr(batch.et, "cik_for",
                        lambda t, mapping=None: str(int(t[1:]) + 1).zfill(10))

    rows = batch.load_universe("sp400")
    assert len(rows) == 40, "every company must survive when the map can resolve it"
    assert len({r["cik"] for r in rows}) == 40, "CIKs must not all collide"


def test_collapsing_universe_raises_instead_of_crawling_one_company(monkeypatch):
    """The actual failure: 400 companies became 1 and the run reported success."""
    df = _frame(40, with_cik=False)
    monkeypatch.setattr(batch.uni, "fetch_universe", lambda tier, force=False: df)
    monkeypatch.setattr(batch.et, "load_map", lambda: {})
    monkeypatch.setattr(batch.et, "cik_for", lambda t, mapping=None: "0000000001")

    with pytest.raises(ValueError, match="collapsed"):
        batch.load_universe("sp400")


def test_genuine_dual_class_dedupe_still_works(monkeypatch):
    """GOOG/GOOGL share a CIK and must collapse to one - that is not the failure mode."""
    df = pd.DataFrame([
        {"ticker": "GOOG", "name": "Alphabet", "cik": "0001652044",
         "gics_sector": "Communication Services", "gics_sub_industry": "Interactive"},
        {"ticker": "GOOGL", "name": "Alphabet", "cik": "0001652044",
         "gics_sector": "Communication Services", "gics_sub_industry": "Interactive"},
        {"ticker": "MSFT", "name": "Microsoft", "cik": "0000789019",
         "gics_sector": "Information Technology", "gics_sub_industry": "Software"},
    ])
    monkeypatch.setattr(batch.uni, "fetch_universe", lambda tier, force=False: df)
    monkeypatch.setattr(batch.et, "load_map", lambda: {})
    monkeypatch.setattr(batch.et, "cik_for", lambda t, mapping=None: None)

    rows = batch.load_universe("sp500")
    assert len(rows) == 2                      # under the 20-row guard, no raise
    assert {r["ticker"] for r in rows} == {"GOOG", "MSFT"}


def test_non_numeric_cik_is_skipped_not_crawled(monkeypatch):
    df = _frame(3, with_cik=False)
    monkeypatch.setattr(batch.uni, "fetch_universe", lambda tier, force=False: df)
    monkeypatch.setattr(batch.et, "load_map", lambda: {})
    monkeypatch.setattr(batch.et, "cik_for", lambda t, mapping=None: "abc")
    assert batch.load_universe("sp400") == []
