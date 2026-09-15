"""DATA_QUALITY_FAIL: the number exists and is not believable.

Every case here is a real defect measured on 2026-08-16 across 1,496 companies. The four
that matter most - INTU, ORCL, FICO, EXEL - were all INSIDE 0-100% and so invisible to a
range check, and all four reported `warnings: []`.
"""
from __future__ import annotations

from datetime import date

import pytest

from clab.fundamentals import metrics as mx
from clab.fundamentals import normalize as nz
from clab.scoring import rubric
from clab.scoring.context import SymbolContext, subtest
from clab.scoring.types import Status


def _bundle(**values):
    M = mx.MetricBundle()
    for k, v in values.items():
        M.set(k, v)
    return M


def _series(*periods):
    """QuarterSeries from (start, end, val) triples."""
    s = nz.QuarterSeries()
    for start, end, val in periods:
        s.facts.append(nz.Fact(end=date.fromisoformat(end), val=val,
                               start=date.fromisoformat(start), duration="Q"))
    return s


# ------------------------------------------------------------------ the status
def test_a_failed_metric_earns_nothing_and_lowers_coverage():
    from clab.scoring.types import ComponentScore, data_quality_fail, scored
    c = ComponentScore(code="FE", label="x", max_points=3, subtests=[
        scored("a", "a", 2, 2),
        data_quality_fail("fe_roic", "roic", 1, "roic 10000 is not believable"),
    ])
    assert c.earned_points == 2
    assert c.available_points == 2          # the failed point is NOT available
    assert c.data_quality_fail_points == 1
    assert c.coverage == pytest.approx(2 / 3)


def test_data_quality_fail_is_distinct_from_no_data():
    """Thin data and a broken derivation are different problems with different fixes."""
    from clab.scoring.types import data_quality_fail, no_data
    assert no_data("k", "l", 1).status == Status.NO_DATA
    assert data_quality_fail("k", "l", 1).status == Status.DATA_QUALITY_FAIL


def test_subtest_routes_a_failed_metric_to_DATA_QUALITY_FAIL_not_NO_DATA():
    """The metric is nulled at source, so without the routing it reads as absent."""
    M = _bundle(roic=None)
    M.quality_failures["roic"] = "roic 10000 outside [-2, 2]"
    ctx = SymbolContext(ticker="X", cik="1", metrics=M)
    st = subtest(ctx, "fe_roic", "ROIC", 2, value=None, points=None)
    assert st.status == Status.DATA_QUALITY_FAIL
    assert "10000" in st.rationale


def test_an_ordinarily_absent_metric_is_still_NO_DATA():
    M = _bundle(roic=None)
    ctx = SymbolContext(ticker="X", cik="1", metrics=M)
    assert subtest(ctx, "fe_roic", "ROIC", 2,
                   value=None, points=None).status == Status.NO_DATA


# ------------------------------------------------------------------ the bounds
@pytest.mark.parametrize("metric,bad", [
    ("gross_margin", 3.40),
    ("gross_margin", -0.5),
    ("operating_margin", -12.0),
    ("roic", -152.08),        # DXCM, measured
    ("net_debt_ebitda", 900.0),
])
def test_an_implausible_value_is_failed_and_NULLED(metric, bad):
    M = _bundle(**{metric: bad})
    mx._quality_check(M)
    assert metric in M.quality_failures
    assert M.raw(metric) is None                      # nulled, so nothing downstream sees it
    assert M.provenance[metric]["rejected_value"] == bad


@pytest.mark.parametrize("metric,ok", [
    ("gross_margin", 0.96),   # ORCL-like, high but real for software
    ("gross_margin", 0.129),  # COST, thin but real
    ("operating_margin", -0.35),
    ("roic", 1.594),          # NVDA, measured and genuine
])
def test_an_unusual_but_believable_value_survives(metric, ok):
    """The bounds catch broken derivations, never unusual businesses."""
    M = _bundle(**{metric: ok})
    mx._quality_check(M)
    assert metric not in M.quality_failures
    assert M.raw(metric) == ok


# ------------------------------------------------- the stale-period defect (INTU/ORCL)
def test_a_margin_built_from_two_different_periods_is_failed():
    """INTU: revenue to 2026-04-30, cogs stopping 2020-07-31 -> 30.1% vs a true ~81.5%."""
    M = _bundle(gross_margin=0.3011)
    M.series["revenue"] = _series(("2026-02-01", "2026-04-30", 8.5e9))
    M.series["gross_profit"] = _series(("2020-05-01", "2020-07-31", 1.5e9))
    mx._stale_ratio_check(M)
    assert "gross_margin" in M.quality_failures
    assert M.raw("gross_margin") is None
    assert "2020-07-31" in M.quality_failures["gross_margin"]


def test_a_margin_whose_periods_agree_survives():
    M = _bundle(gross_margin=0.48)
    M.series["revenue"] = _series(("2026-02-01", "2026-04-30", 9e10))
    M.series["gross_profit"] = _series(("2026-02-01", "2026-04-30", 4.3e10))
    mx._stale_ratio_check(M)
    assert "gross_margin" not in M.quality_failures


def test_one_quarter_of_drift_is_tolerated():
    """A filer can tag one line a period later than another; that is not a defect."""
    M = _bundle(gross_margin=0.48)
    M.series["revenue"] = _series(("2026-02-01", "2026-04-30", 9e10))
    M.series["gross_profit"] = _series(("2025-11-01", "2026-01-31", 4.3e10))
    mx._stale_ratio_check(M)
    assert "gross_margin" not in M.quality_failures


def test_the_stale_check_does_not_swallow_a_type_error():
    """The first cut wrapped the date subtraction in `except (TypeError, ValueError):
    continue`, which hid that ends are dates rather than strings - so the check ran over
    every company and caught nothing. A guard that cannot fail loudly is the bug.

    AST, not a text search: the comment explaining this fix contains the word `except`,
    and a test that trips on prose gets weakened until it stops catching anything.
    """
    import ast
    import inspect
    import textwrap
    tree = ast.parse(textwrap.dedent(inspect.getsource(mx._stale_ratio_check)))
    handlers = [n for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler)]
    assert not handlers, "no exception may be swallowed inside the stale-period check"


# ------------------------------------------------------------------ invested capital
def test_a_near_zero_invested_capital_is_unusable_not_spectacular():
    """DXCM measured -15,208% ROIC from a denominator that had cancelled to nearly zero."""
    assert mx._invested_capital(debt=1e9, equity=1e8, cash_sti=1.09e9) is None


def test_a_normal_invested_capital_is_returned():
    assert mx._invested_capital(debt=1e9, equity=5e9, cash_sti=1e9) == pytest.approx(5e9)


def test_invested_capital_still_None_without_equity():
    assert mx._invested_capital(debt=1e9, equity=None, cash_sti=0) is None


# ------------------------------------------------------------------ sector percentiles
def test_an_implausible_value_cannot_earn_sector_relative_marks():
    """The sharpest defect found: the DISTRIBUTION was filtered and the company's own
    value was not, so roic=10000 landed at percentile 1.0 and took full marks."""
    from clab.scoring import va
    entry = {"roic_sector_values": [0.05, 0.10, 0.15, 0.20], "roic_sector_n": 4}
    assert "roic_sector_pctile" not in va.sector_percentiles(entry, {"roic": 10000.0})
    assert va.sector_percentiles(entry, {"roic": 0.18})["roic_sector_pctile"] == 0.75


# ------------------------------------------------------------------ total debt
def test_the_combined_debt_tag_wins_when_components_are_incomplete():
    """ORCL reported -0.96x net-debt/EBITDA - net CASH - against ~$97.6B of real net
    debt, because `if parts:` was true when only ONE component resolved."""
    assert rubric.DEBT_PARTS_TOLERANCE == 0.20
