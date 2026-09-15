"""The highest-value tests in the repo: restatements, durations, de-cumulation.

Every fixture shape here is taken from real companyfacts behaviour measured on
this box, not invented:
  - up to 4 rows share one (start, end) for AAPL revenue (restatements);
  - NKE has 44 quarter-duration rows and only 25 framed, so `frame` cannot be the
    series backbone;
  - AAPL operating cash flow arrives as a mix of qtr/half/9mo/ann rows, so
    quarters must be derived by differencing YTD values.
"""
from __future__ import annotations

from datetime import date

import pytest

from clab.fundamentals import normalize as nz


def row(start, end, val, filed, accn="a-1", form="10-Q", frame=None):
    r = {"start": start, "end": end, "val": val, "filed": filed, "accn": accn,
         "form": form, "fy": int(end[:4]), "fp": "Q1"}
    if frame:
        r["frame"] = frame
    return r


# ------------------------------------------------------------------ classify
@pytest.mark.parametrize("start,end,expected", [
    ("2026-01-01", "2026-03-31", "Q"),      # 89 days
    ("2026-01-01", "2026-06-30", "H"),      # 180
    ("2026-01-01", "2026-09-30", "9M"),     # 272
    ("2026-01-01", "2026-12-31", "FY"),     # 364
    ("2026-01-01", "2026-02-01", "OTHER"),  # 31
    (None, "2026-03-31", "INSTANT"),
])
def test_classify_by_duration(start, end, expected):
    assert nz.classify({"start": start, "end": end}) == expected


def test_classify_handles_53_week_fiscal_year():
    # 52/53-week retail calendars drift a few days; the FY band must be wide enough
    assert nz.classify({"start": "2025-01-29", "end": "2026-02-01"}) == "FY"


# ------------------------------------------------------------------ restatements
def test_dedupe_current_view_takes_latest_filing():
    rows = [
        row("2026-01-01", "2026-03-31", 100, "2026-04-30"),
        row("2026-01-01", "2026-03-31", 105, "2026-07-30"),
        row("2026-01-01", "2026-03-31", 107, "2027-01-30"),
        row("2026-01-01", "2026-03-31", 106, "2026-10-30"),
    ]
    facts = nz.dedupe(rows, "current")
    assert len(facts) == 1
    assert facts[0].val == 107
    assert facts[0].n_restatements == 3


def test_dedupe_as_first_filed_takes_earliest():
    """The point-in-time view. Grading forward returns on restated numbers is
    look-ahead bias, so this view must exist and must differ."""
    rows = [
        row("2026-01-01", "2026-03-31", 100, "2026-04-30"),
        row("2026-01-01", "2026-03-31", 107, "2027-01-30"),
    ]
    assert nz.dedupe(rows, "as_first_filed")[0].val == 100
    assert nz.dedupe(rows, "current")[0].val == 107


def test_dedupe_ties_break_on_accession():
    rows = [
        row("2026-01-01", "2026-03-31", 1, "2026-04-30", accn="0000-26-000001"),
        row("2026-01-01", "2026-03-31", 2, "2026-04-30", accn="0000-26-000002"),
    ]
    assert nz.dedupe(rows, "current")[0].val == 2


def test_dedupe_skips_unparseable_rows():
    rows = [row("2026-01-01", "2026-03-31", 10, "2026-04-30"),
            {"start": "x", "end": None, "val": 5, "filed": "2026-04-30"},
            {"start": "2026-01-01", "end": "2026-03-31", "val": "not a number",
             "filed": "2026-05-30"}]
    facts = nz.dedupe(rows)
    assert [f.val for f in facts] == [10]


# ------------------------------------------------------------------ de-cumulation
def _ytd_year(year, q1, h, m9, fy, filed="2027-02-01"):
    """One fiscal year filed the way most cash-flow statements are: Q1 discrete,
    then cumulative half, nine-month and full-year figures."""
    s = f"{year}-01-01"
    return [
        row(s, f"{year}-03-31", q1, filed),
        row(s, f"{year}-06-30", h, filed),
        row(s, f"{year}-09-30", m9, filed),
        row(s, f"{year}-12-31", fy, filed),
    ]


def test_decumulation_derives_q2_q3_q4():
    rows = _ytd_year(2026, 100, 250, 420, 600)
    series = nz.discrete_quarters(rows)
    vals = [f.val for f in series.facts]
    assert vals == [100, 150, 170, 180]        # Q2=H-Q1, Q3=9M-H, Q4=FY-9M
    assert series.n_direct == 1
    assert series.n_derived == 3
    derived = [f.derivation for f in series.facts[1:]]
    assert all(d.startswith("derived_from_ytd") for d in derived)


def test_decumulation_never_double_counts_a_year():
    """The failure this guards: naive summation of a mixed-duration series adds a
    quarter, its half, its nine-month and its full-year value together."""
    rows = _ytd_year(2026, 100, 250, 420, 600)
    series = nz.discrete_quarters(rows)
    assert sum(f.val for f in series.facts) == 600      # not 1370


def test_direct_quarters_win_over_derived():
    rows = _ytd_year(2026, 100, 250, 420, 600)
    rows.append(row("2026-04-01", "2026-06-30", 999, "2027-03-01"))   # discrete Q2
    series = nz.discrete_quarters(rows)
    q2 = [f for f in series.facts if f.end == date(2026, 6, 30)][0]
    assert q2.val == 999
    assert q2.derived is False


def test_suspect_derived_quarter_is_dropped():
    """A derived quarter far below the trailing mean is a de-cumulation artefact.
    Dropping it to NO_DATA beats scoring on garbage."""
    rows = []
    for y in (2022, 2023, 2024, 2025):
        rows += _ytd_year(y, 100, 200, 300, 400, filed=f"{y + 1}-02-01")
    # 2026: FY far below the 9M figure -> a large negative derived Q4
    rows += _ytd_year(2026, 100, 200, 300, -900, filed="2027-02-01")
    series = nz.discrete_quarters(rows)
    assert series.n_suspect >= 1
    assert all(f.val > -500 for f in series.facts)
    assert any("suspect" in n for n in series.notes)


def test_frame_is_not_the_series_backbone():
    """NKE-shaped fixture: real quarters exist but only some carry a `frame`.
    Series construction must not depend on frames or quarters silently vanish."""
    rows = [
        row("2026-01-01", "2026-03-31", 10, "2026-04-30", frame="CY2026Q1"),
        row("2026-04-01", "2026-06-30", 11, "2026-07-30"),              # unframed
        row("2026-07-01", "2026-09-30", 12, "2026-10-30"),              # unframed
        row("2026-10-01", "2026-12-31", 13, "2027-01-30", frame="CY2026Q4"),
    ]
    series = nz.discrete_quarters(rows)
    assert len(series) == 4
    framed = [f for f in series.facts if f.frame]
    assert len(framed) == 2      # proves the fixture really is frame-sparse


# ------------------------------------------------------------------ TTM
def test_ttm_needs_four_consecutive_quarters():
    rows = [row("2026-01-01", "2026-03-31", 10, "2026-04-30"),
            row("2026-04-01", "2026-06-30", 11, "2026-07-30")]
    val, diag = nz.ttm(nz.discrete_quarters(rows))
    assert val is None                       # NOT 0 - absent data is not a zero
    assert diag["reason"] == "insufficient_quarters"


def test_ttm_sums_the_last_four():
    rows = _ytd_year(2026, 100, 250, 420, 600)
    val, diag = nz.ttm(nz.discrete_quarters(rows))
    assert val == 600
    assert len(diag["quarters_used"]) == 4
    assert diag["any_derived"] is True


def test_ttm_rejects_non_consecutive_quarters():
    rows = [row("2020-01-01", "2020-03-31", 1, "2020-04-30"),
            row("2026-01-01", "2026-03-31", 2, "2026-04-30"),
            row("2026-04-01", "2026-06-30", 3, "2026-07-30"),
            row("2026-07-01", "2026-09-30", 4, "2026-10-30")]
    val, diag = nz.ttm(nz.discrete_quarters(rows))
    assert val is None
    assert diag["reason"] == "non_consecutive_quarters"


def test_ttm_at_offset_gives_prior_year():
    rows = _ytd_year(2025, 50, 100, 150, 200, filed="2026-02-01") + \
        _ytd_year(2026, 100, 250, 420, 600)
    series = nz.discrete_quarters(rows)
    assert nz.ttm(series)[0] == 600
    assert nz.ttm_at(series, 4)[0] == 200


# ------------------------------------------------------------------ arithmetic
def test_cagr_returns_none_for_undefined_cases():
    assert nz.cagr(200, 100, 1) == pytest.approx(1.0)
    assert nz.cagr(None, 100, 3) is None
    assert nz.cagr(100, 0, 3) is None          # zero base
    assert nz.cagr(100, -50, 3) is None        # sign change makes the root meaningless
    assert nz.cagr(-100, 50, 3) is None
    assert nz.cagr(100, 50, 0) is None


def test_yoy_uses_absolute_base_for_sign_sanity():
    assert nz.yoy(110, 100) == pytest.approx(0.10)
    assert nz.yoy(-50, -100) == pytest.approx(0.5)     # a smaller loss is an improvement
    assert nz.yoy(10, 0) is None


def test_linreg_slope():
    assert nz.linreg_slope([1, 2, 3, 4]) == pytest.approx(1.0)
    assert nz.linreg_slope([4, 3, 2, 1]) == pytest.approx(-1.0)
    assert nz.linreg_slope([1, 1]) is None            # needs 3 points


def test_instants_have_no_start_and_sort_by_end():
    rows = [{"end": "2026-03-31", "val": 5, "filed": "2026-04-30", "accn": "a"},
            {"end": "2025-03-31", "val": 3, "filed": "2025-04-30", "accn": "b"}]
    seq = nz.instants(rows)
    assert [f.val for f in seq] == [3, 5]
    assert nz.latest_instant(rows).val == 5
