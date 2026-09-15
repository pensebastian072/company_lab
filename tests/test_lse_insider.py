"""LSE insider rows: deduplication and congressional filtering.

Both are correctness issues, not tidiness. Measured on the live feed 2026-08-13:
4,980 AAPL corporate rows collapsed to 27 real transactions, and ONE transaction appeared
320 times under 160 distinct `created_at` values. Counting raw rows would inflate any
insider signal ~160x and make "cluster buying (>=3 distinct insiders)" fire on almost
every company - a fabricated signal that would have looked convincing.
"""
from __future__ import annotations

from clab.sources import lse


def _row(**kw):
    base = {"reporting_cik": "1", "company_cik": "320193", "symbol": "AAPL",
            "transaction_date": "2025-10-16", "filing_date": "2025-10-17",
            "transaction_type": "S-Sale", "acquisition_or_disposition": "D",
            "securities_transacted": 500, "price": 245.89, "securities_owned": 12464,
            "trade_type": "insider", "id": "1", "created_at": "2026-01-09 17:39:55"}
    base.update(kw)
    return base


def test_reingested_copies_collapse_to_one_transaction():
    rows = [_row(id=str(i), created_at=f"2026-01-09 17:{i:02d}:00") for i in range(60)]
    out = lse.dedupe_insider_rows(rows)
    assert len(out) == 1


def test_dedupe_keeps_the_earliest_sighting():
    rows = [_row(id="b", created_at="2026-02-01 00:00:00"),
            _row(id="a", created_at="2026-01-09 17:39:55"),
            _row(id="c", created_at="2026-03-01 00:00:00")]
    out = lse.dedupe_insider_rows(rows)
    assert len(out) == 1
    assert out[0]["id"] == "a", "should keep the first time the filing was seen"


def test_genuinely_different_transactions_survive():
    """The two AAPL rows that really did differ - different price and holdings."""
    rows = [_row(id="1", price=245.89, securities_owned=12464),
            _row(id="2", price=248.73, securities_owned=8765)]
    assert len(lse.dedupe_insider_rows(rows)) == 2


def test_different_insiders_same_day_are_not_merged():
    """Otherwise cluster-buying would be silently collapsed to a single insider."""
    rows = [_row(reporting_cik="1"), _row(reporting_cik="2"), _row(reporting_cik="3")]
    assert len(lse.dedupe_insider_rows(rows)) == 3


def test_same_insider_two_sizes_same_day_are_distinct():
    rows = [_row(securities_transacted=500), _row(securities_transacted=4197)]
    assert len(lse.dedupe_insider_rows(rows)) == 2


def test_identity_fields_exclude_the_volatile_ones():
    """id and created_at are exactly what the feed varies between duplicate copies."""
    assert "id" not in lse.INSIDER_IDENTITY_FIELDS
    assert "created_at" not in lse.INSIDER_IDENTITY_FIELDS
    for f in ("reporting_cik", "transaction_date", "transaction_type",
              "securities_transacted"):
        assert f in lse.INSIDER_IDENTITY_FIELDS


def test_congressional_rows_are_dropped_and_deduped(monkeypatch):
    """The trade_type query param is ignored by the API, so filtering is client-side."""
    payload = ([_row(id=str(i), created_at=f"2026-01-09 17:{i:02d}:00") for i in range(5)]
               + [_row(id="s1", trade_type="senate", reporting_cik="99"),
                  _row(id="h1", trade_type="house", reporting_cik="98")])
    monkeypatch.setattr(lse, "ref", lambda *a, **k: payload)

    corp = lse.insider_trades("AAPL")
    assert len(corp) == 1, "5 copies of one corporate transaction, congress excluded"
    assert all(r["trade_type"] == "insider" for r in corp)

    everything = lse.insider_trades("AAPL", corporate_only=False, dedupe=False)
    assert len(everything) == 7


def test_dedupe_can_be_turned_off_for_auditing(monkeypatch):
    payload = [_row(id=str(i)) for i in range(4)]
    monkeypatch.setattr(lse, "ref", lambda *a, **k: payload)
    assert len(lse.insider_trades("AAPL", dedupe=False)) == 4
    assert len(lse.insider_trades("AAPL", dedupe=True)) == 1


def test_start_end_are_forwarded(monkeypatch):
    """start/end are the ONLY filter params the endpoint honours."""
    seen = {}

    def fake_ref(dataset, **kw):
        seen.update(kw)
        return []

    monkeypatch.setattr(lse, "ref", fake_ref)
    lse.insider_trades("AAPL", start="2025-01-01", end="2025-12-31")
    assert seen["start"] == "2025-01-01" and seen["end"] == "2025-12-31"
