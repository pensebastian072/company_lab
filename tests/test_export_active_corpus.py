"""The workbook shows the ACTIVE corpus, not every row ever stored.

`industry_intelligence` is keyed (industry_id, version) and now carries a SUPERSEDED
lifecycle, so a plain `SELECT *` returns an industry once per re-cut AND returns objects
that a re-cut retired. Both were live on the real store: `coal_consumable_fuels` had two
versions, and E56 retired three Financials buckets whose fields are all UNKNOWN.

Retired operationally, retained evidentially - so these tests pin BOTH halves: the export
must exclude them, and the store must still hold them.
"""
from __future__ import annotations

import datetime

import pytest

from clab.external.store import ExternalStore

pytest.importorskip("duckdb")
pytest.importorskip("openpyxl")

from clab.export import xlsx_external as XE  # noqa: E402
from clab.export import xlsx_export as X  # noqa: E402


def _obj(iid, version, *, sector="financials", status=None, superseded_by=None,
         updated=None, sg="MODERATE"):
    return {
        "industry_id": iid, "version": version, "sector_id": sector,
        "brief": f"{iid} {version}", "structural_growth": sg,
        "moat_mechanism": "scale", "replication_difficulty": "HIGH",
        "substitution_risk": "MODERATE", "key_metrics": ["a"],
        "refresh_class": "STRUCTURAL",
        "last_updated": updated or datetime.datetime(2026, 9, 2, 18, 0,
                                                     tzinfo=datetime.timezone.utc),
        "next_refresh_due": datetime.date(2026, 12, 1),
        "status": status, "superseded_by": superseded_by,
    }


@pytest.fixture()
def store(tmp_path):
    st = ExternalStore(tmp_path / "t.duckdb")
    # Two versions of one industry: exactly the coal_consumable_fuels shape, where the
    # OLDER row is the superseded one and its structural_growth is UNKNOWN.
    st.upsert_industry(_obj("coal", "2026-09-02", sg="UNKNOWN"))
    st.upsert_industry(_obj("coal", "2026-09-02.1", sg="DECLINING",
                            updated=datetime.datetime(2026, 9, 2, 19, 15,
                                                      tzinfo=datetime.timezone.utc)))
    # A bucket E56 retired: one version, superseded, everything UNKNOWN.
    st.upsert_industry(_obj("multi_sector_holdings", "2026-09-06", sg="UNKNOWN"))
    st.upsert_industry(_obj("diversified_banks", "2026-09-06"))
    # NOTE: `upsert_industry` does not carry the lifecycle columns, so a row can only be
    # retired with SQL. That is how the live rows were marked too. If upsert ever learns
    # these columns, this fixture can use it - but it must never OVERWRITE a status on a
    # re-ingest, or a re-ingest would quietly un-retire every superseded object.
    with st.connect() as con:
        con.execute(
            "UPDATE industry_intelligence SET status = 'SUPERSEDED', superseded_by = ? "
            "WHERE industry_id = 'coal' AND version = '2026-09-02'",
            ["coal 2026-09-02.1"])
        con.execute(
            "UPDATE industry_intelligence SET status = 'SUPERSEDED', superseded_by = ? "
            "WHERE industry_id = 'multi_sector_holdings'",
            ["multi_industry_conglomerate (BRK-B)"])
    return st


def _exported(store) -> list[dict]:
    """Calls the PRODUCTION reader. A copy of the query here would pass while the
    export still shipped every row - the failure mode this repo keeps hitting."""
    with store.connect() as con:
        return XE.active_industries(con)


def test_an_industry_appears_once_however_many_versions_it_has(store):
    rows = _exported(store)
    assert [r["industry_id"] for r in rows].count("coal") == 1


def test_the_version_kept_is_the_current_one_not_the_superseded_one(store):
    coal = next(r for r in _exported(store) if r["industry_id"] == "coal")
    assert coal["version"] == "2026-09-02.1"
    assert coal["structural_growth"] == "DECLINING"


def test_a_retired_object_is_out_of_the_workbook(store):
    assert "multi_sector_holdings" not in {r["industry_id"] for r in _exported(store)}


def test_a_live_object_is_still_in_the_workbook(store):
    assert "diversified_banks" in {r["industry_id"] for r in _exported(store)}


def test_retained_evidentially_the_store_still_holds_every_row(store):
    """The whole point of SUPERSEDED over DELETE. If this passes because the rows are
    gone, the lifecycle has become a hard delete."""
    with store.connect() as con:
        total = con.execute("SELECT count(*) FROM industry_intelligence").fetchone()[0]
        retired = con.execute(
            "SELECT count(*) FROM industry_intelligence "
            "WHERE upper(status) = 'SUPERSEDED'").fetchone()[0]
    assert total == 4
    assert retired == 2
    # `industry()` now hides a superseded object by DEFAULT - that is the
    # company-resolution rule: a company still pointing at a re-cut id must get nothing
    # back rather than an object whose own record says it describes no industry.
    # Retention is proved by asking for it explicitly, which is a stronger check than
    # the default returning it would have been.
    assert store.industry("multi_sector_holdings") is None
    row = store.industry("multi_sector_holdings", include_superseded=True)
    assert row is not None
    assert row["superseded_by"] == "multi_industry_conglomerate (BRK-B)"


def test_the_reader_can_return_non_active_rows_at_all(store):
    """Confirm the filter is doing work. A check that returns the right answer because
    it silently matched nothing is the E34 bug; assert the known-positive first."""
    with store.connect() as con:
        everything = con.execute("SELECT * FROM industry_intelligence").fetchall()
    assert len(everything) == 4
    assert [r["industry_id"] for r in _exported(store)] == ["coal", "diversified_banks"]


def test_the_industry_sheet_columns_survive_the_filter(store):
    """The sheet reads INDUSTRY_COLUMNS off these rows; a missing key would export
    blanks rather than fail."""
    with store.connect() as con:
        rows = XE.active_industries(con)
    for col in XE.INDUSTRY_COLUMNS:
        assert col in rows[0], col


@pytest.mark.parametrize("reader", [XE.active_industries, X._active_industry_rows])
def test_both_export_readers_parse_double_digit_recuts(reader, tmp_path):
    st = ExternalStore(tmp_path / "versions.duckdb")
    tied = datetime.datetime(2026, 9, 7, 12, 0, tzinfo=datetime.timezone.utc)
    st.upsert_industry(_obj("versioned", "2026-09-07.9", updated=tied,
                            sg="MODERATE"))
    st.upsert_industry(_obj("versioned", "2026-09-07.10", updated=tied,
                            sg="HIGH"))

    with st.connect() as con:
        rows = reader(con)

    row = next(r for r in rows if r["industry_id"] == "versioned")
    assert row["version"] == "2026-09-07.10"
    assert row["structural_growth"] == "HIGH"
