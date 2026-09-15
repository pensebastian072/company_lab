"""Tab order is a human contract, and the external layer lives in the same workbook.

The person opening this file wants the rankings first and should never hunt for them.
Build order is not tab order - sheets are built when their data is ready - so the order
is applied at the end and pinned here. Without this test, adding a sheet in the middle of
`build_workbook` could quietly put something in front of Rank.
"""
from __future__ import annotations

import pytest

pytest.importorskip("openpyxl")

from clab.export import xlsx_export as X  # noqa: E402
from conftest import skip_if_locked


def _rows():
    return [
        {"ticker": "AAA", "cik": "1", "score": 70, "band": "INVESTABLE",
         "sector": "Financials", "sub_industry": "Regional Banks"},
        {"ticker": "BBB", "cik": "2", "score": 40, "band": "INSUFFICIENT_DATA",
         "sector": "Energy", "sub_industry": "Oil & Gas Refining & Marketing"},
    ]


@pytest.fixture()
def no_external(tmp_path, monkeypatch):
    """An absent external database is a legitimate state, not a failure."""
    monkeypatch.setattr(X.config, "EXTERNAL_DB", tmp_path / "nope.duckdb")
    return tmp_path


def test_rank_is_the_first_tab(no_external):
    wb = X.build_workbook(_rows(), cards=[])
    assert wb.sheetnames[0] == "Rank"


def test_the_two_ranking_sheets_lead_the_workbook(no_external):
    """Company rank then sector rank - the two things the workbook exists to show."""
    wb = X.build_workbook(_rows(), cards=[])
    assert wb.sheetnames[:2] == ["Rank", "Sectors"]


def test_back_end_sheets_are_on_the_right(no_external):
    wb = X.build_workbook(_rows(), cards=[])
    names = wb.sheetnames
    assert names[-1] == "Meta"
    for backend in ("Components", "Subtests"):
        if backend in names:
            assert names.index(backend) > names.index("Findings")


def test_the_order_follows_sheet_order_exactly(no_external):
    wb = X.build_workbook(_rows(), cards=[])
    present = [n for n in X.SHEET_ORDER if n in wb.sheetnames]
    assert wb.sheetnames == present


def test_an_unlisted_sheet_cannot_land_in_front_of_rank(no_external):
    """A new sheet someone forgets to add to SHEET_ORDER goes to the END, never the
    front. Silently demoting Rank would be the worst possible default."""
    wb = X.build_workbook(_rows(), cards=[])
    wb.create_sheet("SomethingNew")
    X._apply_sheet_order(wb)
    assert wb.sheetnames[0] == "Rank"
    assert wb.sheetnames[-1] == "SomethingNew"


def test_sheet_order_and_all_sheets_do_not_drift_apart():
    """Every buildable sheet has a place in the order. A sheet in ALL_SHEETS with no
    entry in SHEET_ORDER would silently sort to the far right forever."""
    ordered = {n.lower() for n in X.SHEET_ORDER}
    missing = [s for s in X.ALL_SHEETS if s not in ordered]
    assert not missing, f"in ALL_SHEETS but not SHEET_ORDER: {missing}"


# ------------------------------------------------------------- external folding


def test_an_absent_external_database_does_not_break_the_workbook(no_external):
    """The weekly artifact must not depend on the research layer existing."""
    wb = X.build_workbook(_rows(), cards=[])
    assert "Rank" in wb.sheetnames
    assert "External" not in wb.sheetnames


def test_a_broken_external_database_is_loud_not_silent(tmp_path, monkeypatch):
    """Defensive about ABSENCE, loud about BREAKAGE. A file that exists and cannot be
    read is a wiring bug, and shipping a workbook that quietly lost a sheet is the
    failure this repo keeps rediscovering."""
    broken = tmp_path / "broken.duckdb"
    broken.write_bytes(b"this is not a duckdb file")
    monkeypatch.setattr(X.config, "EXTERNAL_DB", broken)
    with pytest.raises(Exception):
        X.build_workbook(_rows(), cards=[])


def test_the_freshness_columns_are_present():
    """'How old is this research' has to be answerable in the workbook, without
    opening a database. These are the columns the weekend refresh keys on."""
    for col in ("last_research_date", "next_refresh_due", "days_since_research",
                "refresh_due"):
        assert col in X.EXTERNAL_COLUMNS


def test_the_industry_sheet_reads_the_active_corpus_only():
    """Same rule as the standalone export: latest version, nothing superseded."""
    import inspect
    src = inspect.getsource(X._active_industry_rows)
    assert "select_active_industries" in src
    assert "row_number() OVER" not in src


def test_claims_sit_on_the_back_end_side_of_the_workbook():
    """Evidence rows are an audit trail, not a reading sheet."""
    order = list(X.SHEET_ORDER)
    assert order.index("Claims") > order.index("External")
    assert order.index("Claims") > order.index("Rank")


def test_a_timezone_aware_timestamp_cannot_reach_a_cell():
    """The store's date columns are TIMESTAMPTZ and Excel refuses them. This raised at
    SAVE time, so the workbook built cleanly and then died writing the file - every
    sheet looked right and nothing shipped."""
    import datetime as dt
    aware = dt.datetime(2026, 9, 7, 12, 0, tzinfo=dt.timezone.utc)
    assert X._excel_safe(aware).tzinfo is None
    naive = dt.datetime(2026, 9, 7, 12, 0)
    assert X._excel_safe(naive) == naive
    assert X._excel_safe(dt.date(2026, 9, 7)) == dt.date(2026, 9, 7)
    assert X._excel_safe(["a", "b"]) == "['a', 'b']"
    assert X._excel_safe(None) is None
    assert X._excel_safe(3) == 3


@skip_if_locked
def test_the_real_workbook_saves_with_the_external_sheets(tmp_path):
    """Builds AND saves against the live store. The tz bug only appeared on save."""
    import pandas as pd
    from clab import config
    if not config.EXTERNAL_DB.exists() or not config.SCORES_PARQUET.exists():
        pytest.skip("no live store on this box")
    rows = pd.read_parquet(config.SCORES_PARQUET).head(40).to_dict("records")
    wb = X.build_workbook(rows, cards=[])
    out = tmp_path / "wb.xlsx"
    wb.save(out)
    assert out.stat().st_size > 5000
    assert wb.sheetnames[0] == "Rank"
