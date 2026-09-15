"""E13's top-N construction and the P4 decile diagnostic.

The ranking step is where a look-ahead or a non-determinism would be invisible in the
output, and the P4 criterion must not be able to pass on a story that merely fits.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from clab.research import e13_topn_portfolio as e13


def _panel(rows):
    return pd.DataFrame(rows)


def test_top_n_picks_the_highest_scores_that_month():
    p = _panel([
        {"date": pd.Timestamp("2020-01-31"), "ticker": "A", "measured_pct": 0.9},
        {"date": pd.Timestamp("2020-01-31"), "ticker": "B", "measured_pct": 0.5},
        {"date": pd.Timestamp("2020-01-31"), "ticker": "C", "measured_pct": 0.7},
    ])
    assert e13.top_n_by_date(p, 2) == {pd.Timestamp("2020-01-31"): ["A", "C"]}


def test_ties_break_deterministically_by_ticker():
    """Arbitrary row order would make the whole backtest non-reproducible."""
    rows = [{"date": pd.Timestamp("2020-01-31"), "ticker": t, "measured_pct": 0.5}
            for t in ("D", "B", "C", "A")]
    first = e13.top_n_by_date(_panel(rows), 2)
    second = e13.top_n_by_date(_panel(list(reversed(rows))), 2)
    assert first == second == {pd.Timestamp("2020-01-31"): ["A", "B"]}


def test_each_month_is_ranked_independently():
    p = _panel([
        {"date": pd.Timestamp("2020-01-31"), "ticker": "A", "measured_pct": 0.9},
        {"date": pd.Timestamp("2020-01-31"), "ticker": "B", "measured_pct": 0.1},
        {"date": pd.Timestamp("2020-02-29"), "ticker": "A", "measured_pct": 0.1},
        {"date": pd.Timestamp("2020-02-29"), "ticker": "B", "measured_pct": 0.9},
    ])
    got = e13.top_n_by_date(p, 1)
    assert got[pd.Timestamp("2020-01-31")] == ["A"]
    assert got[pd.Timestamp("2020-02-29")] == ["B"]


def test_a_month_with_no_scores_is_skipped_not_filled():
    p = _panel([
        {"date": pd.Timestamp("2020-01-31"), "ticker": "A", "measured_pct": np.nan},
        {"date": pd.Timestamp("2020-02-29"), "ticker": "A", "measured_pct": 0.5},
    ])
    got = e13.top_n_by_date(p, 5)
    assert pd.Timestamp("2020-01-31") not in got
    assert got[pd.Timestamp("2020-02-29")] == ["A"]


def test_asking_for_more_names_than_exist_returns_what_there_is():
    p = _panel([{"date": pd.Timestamp("2020-01-31"), "ticker": "A",
                 "measured_pct": 0.5}])
    assert e13.top_n_by_date(p, 80) == {pd.Timestamp("2020-01-31"): ["A"]}


# ------------------------------------------------------------------ coverage proxy
def test_coverage_is_relative_to_the_same_profile():
    """A FINANCIAL company must not be penalised for sub-tests the rubric suppresses."""
    p = _panel([
        {"date": pd.Timestamp("2020-01-31"), "profile": "STANDARD",
         "measured_avail": 45},
        {"date": pd.Timestamp("2020-01-31"), "profile": "STANDARD",
         "measured_avail": 20},
        {"date": pd.Timestamp("2020-01-31"), "profile": "FINANCIAL",
         "measured_avail": 30},
    ])
    cov = e13.coverage_proxy(p)
    assert cov.iloc[0] == pytest.approx(1.0)      # best-covered STANDARD
    assert cov.iloc[1] == pytest.approx(20 / 45)
    assert cov.iloc[2] == pytest.approx(1.0)      # best-covered FINANCIAL, not 30/45


# ------------------------------------------------------------------ P4
def _diag(raw_3y, filtered_3y):
    return {"absolute": {
        "no_coverage_filter": {"fwd_3y": {"top_minus_bottom_pp": raw_3y}},
        "coverage_filtered": {"fwd_3y": {"top_minus_bottom_pp": filtered_3y}},
    }}


def _out(diag):
    return {"variants": {"top20": {"annualised_excess_net_ex2020": 0.01,
                                   "annualised_excess_net": 0.013,
                                   "monthly_excess_net": {"median": 0.002},
                                   "gate": {"available": True, "passes": False}},
                         "top40": {"annualised_excess_net": 0.021},
                         "top80": {"annualised_excess_net": 0.029}},
            "p4_decile_diagnostic": diag}


def test_P4_passes_for_a_material_negative_spread_that_flips_with_coverage():
    out = _out(_diag(-14.13, 18.47))
    e13._criteria(out)
    assert out["criteria"]["P4_E05_negative_unfiltered_and_coverage_flip"] is True


def test_P4_fails_if_the_unfiltered_spread_is_not_materially_negative():
    out = _out(_diag(+2.0, 18.47))
    e13._criteria(out)
    assert out["criteria"]["P4_E05_negative_unfiltered_and_coverage_flip"] is False


def test_P4_fails_if_the_correction_does_not_flip_the_sign():
    out = _out(_diag(-14.13, -9.0))
    e13._criteria(out)
    assert out["criteria"]["P4_E05_negative_unfiltered_and_coverage_flip"] is False


def test_P4_fails_when_the_diagnostic_is_missing_entirely():
    out = _out({})
    e13._criteria(out)
    assert out["criteria"]["P4_E05_negative_unfiltered_and_coverage_flip"] is False


def test_P4_does_not_require_numerical_reproduction_of_E05():
    out = _out(_diag(-25.52, 4.14))
    e13._criteria(out)
    assert out["criteria"]["P4_E05_negative_unfiltered_and_coverage_flip"] is True


# ------------------------------------------------------------------ P3
def test_P3_fails_when_a_broader_portfolio_does_better():
    """The live result: top20 1.3% < top40 2.1% < top80 2.9%. Concentration hurts."""
    out = _out(_diag(-14.13, 18.47))
    e13._criteria(out)
    assert out["criteria"]["P3_size_gradient_runs_the_right_way"] is False


def test_P3_passes_when_concentration_helps():
    out = _out(_diag(-14.13, 18.47))
    out["variants"]["top20"]["annualised_excess_net"] = 0.05
    out["variants"]["top40"]["annualised_excess_net"] = 0.03
    out["variants"]["top80"]["annualised_excess_net"] = 0.01
    e13._criteria(out)
    assert out["criteria"]["P3_size_gradient_runs_the_right_way"] is True


def test_nothing_is_ever_promoted():
    out = _out(_diag(-14.13, 18.47))
    e13._criteria(out)
    assert out["promoted"] is False
    assert out["status"] == "SHADOW"
