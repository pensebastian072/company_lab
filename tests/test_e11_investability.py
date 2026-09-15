"""E11's portfolio construction, where a look-ahead bug would be invisible in the output.

A cohort formed on a month-end signal must earn the FOLLOWING month's return. If it
earned the same month's, the strategy would be reading a price it could not have traded
at and every number in E11 would be fiction that still looks plausible.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from clab.research import e11_investability as e11


@pytest.fixture()
def rets():
    """Three months, two names, hand-picked so each month is identifiable."""
    idx = pd.to_datetime(["2020-01-31", "2020-02-29", "2020-03-31"])
    return pd.DataFrame({"AAA": [0.10, 0.20, 0.30],
                         "BBB": [0.00, 0.40, 0.60]}, index=idx)


def test_a_cohort_earns_the_NEXT_month_not_its_own(rets):
    """The look-ahead test. Signal at 2020-01-31 must not collect January's return."""
    out = e11.cohort_series({pd.Timestamp("2020-01-31"): ["AAA"]}, rets)
    assert out.loc[pd.Timestamp("2020-01-31"), "ret"] == 0.0        # not yet invested
    assert out.loc[pd.Timestamp("2020-02-29"), "ret"] == pytest.approx(0.20)
    assert out.loc[pd.Timestamp("2020-03-31"), "ret"] == pytest.approx(0.30)


def test_a_cohort_is_equal_weighted_within_itself(rets):
    out = e11.cohort_series({pd.Timestamp("2020-01-31"): ["AAA", "BBB"]}, rets)
    # February: mean(0.20, 0.40)
    assert out.loc[pd.Timestamp("2020-02-29"), "ret"] == pytest.approx(0.30)


def test_overlapping_cohorts_are_averaged_not_summed(rets):
    out = e11.cohort_series({pd.Timestamp("2020-01-31"): ["AAA"],
                             pd.Timestamp("2020-02-29"): ["BBB"]}, rets)
    # March: cohort1 holds AAA (0.30), cohort2 holds BBB (0.60) -> mean 0.45
    assert out.loc[pd.Timestamp("2020-03-31"), "ret"] == pytest.approx(0.45)
    assert out.loc[pd.Timestamp("2020-03-31"), "n_cohorts"] == 2


def test_a_month_with_no_cohort_is_held_in_cash_not_dropped(rets):
    out = e11.cohort_series({}, rets)
    assert len(out) == len(rets)                      # every month survives
    assert (out["ret"] == 0.0).all()
    assert not out["in_market"].any()


def test_a_cohort_expires_after_the_holding_period():
    months = pd.date_range("2020-01-31", periods=15, freq="ME")
    r = pd.DataFrame({"AAA": [0.01] * 15}, index=months)
    out = e11.cohort_series({months[0]: ["AAA"]}, r)
    # contributes for exactly HOLD_MONTHS months, starting the month after entry
    assert int(out["in_market"].sum()) == e11.HOLD_MONTHS
    assert out.iloc[0]["in_market"] is np.False_ or not out.iloc[0]["in_market"]
    assert out.iloc[e11.HOLD_MONTHS]["in_market"]
    assert not out.iloc[e11.HOLD_MONTHS + 1]["in_market"]


def test_a_name_with_no_price_does_not_silently_shrink_the_cohort(rets):
    """An unknown ticker is skipped, but a cohort of ONLY unknowns is out of market."""
    out = e11.cohort_series({pd.Timestamp("2020-01-31"): ["AAA", "NOPE"]}, rets)
    assert out.loc[pd.Timestamp("2020-02-29"), "ret"] == pytest.approx(0.20)

    out2 = e11.cohort_series({pd.Timestamp("2020-01-31"): ["NOPE"]}, rets)
    assert not out2["in_market"].any()


def test_the_shrink_is_COUNTED_and_not_merely_survived(rets):
    """B7f. The test above asserted the surviving return and called that "not silently".

    It was not enough: the cohort really did shrink from two names to one, the mean
    really was reweighted onto the survivor, and nothing in the output said so. A
    reweighted return that reports no denominator is indistinguishable from a full one.
    """
    out = e11.cohort_series({pd.Timestamp("2020-01-31"): ["AAA", "NOPE"]}, rets)
    feb = out.loc[pd.Timestamp("2020-02-29")]
    assert feb["n_asked"] == 2                    # two names were requested
    assert feb["n_names"] == 1                    # one was actually held
    assert feb["n_dropped_no_price"] == 1         # and the loss is on the record
    assert feb["n_dropped_nan_return"] == 0


def test_a_nan_return_is_counted_separately_from_a_missing_column(rets):
    """The two losses have different causes and must not be pooled.

    A missing COLUMN is a name we never had prices for - a universe problem. A NaN
    RETURN is a name we have prices for that did not trade that month - a data problem.
    Pooling them hides which one is growing.
    """
    r = rets.copy()
    r.loc[pd.Timestamp("2020-02-29"), "BBB"] = np.nan
    out = e11.cohort_series({pd.Timestamp("2020-01-31"): ["AAA", "BBB"]}, r)
    feb = out.loc[pd.Timestamp("2020-02-29")]
    assert feb["n_asked"] == 2
    assert feb["n_names"] == 1
    assert feb["n_dropped_no_price"] == 0
    assert feb["n_dropped_nan_return"] == 1
    # the survivor's return is what gets reported, which is exactly why it needs the count
    assert feb["ret"] == pytest.approx(0.20)


def test_counting_the_drops_does_not_move_the_returns(rets):
    """B7f is a disclosure fix, not a behaviour change. Returns must be untouched."""
    out = e11.cohort_series({pd.Timestamp("2020-01-31"): ["AAA", "BBB"]}, rets)
    assert out.loc[pd.Timestamp("2020-02-29"), "ret"] == pytest.approx(0.30)
    assert out.loc[pd.Timestamp("2020-03-31"), "ret"] == pytest.approx(0.45)
    assert int(out["n_dropped_no_price"].sum()) == 0
    assert int(out["n_dropped_nan_return"].sum()) == 0


def test_the_no_op_holds_in_the_branch_the_change_actually_touched(rets):
    """The test above only pins the ZERO-drop path, which is not where the risk is.

    The counters are incremented inside the two early-exit branches, so those are the
    branches that could have moved. Pin every pre-existing output in a case where names
    really are dropped - one ghost ticker and one NaN in the same month.
    """
    r = rets.copy()
    r.loc[pd.Timestamp("2020-02-29"), "BBB"] = np.nan
    out = e11.cohort_series({pd.Timestamp("2020-01-31"): ["AAA", "BBB", "GHOST"]}, r)
    feb = out.loc[pd.Timestamp("2020-02-29")]
    # pre-existing columns, unchanged by the disclosure
    assert feb["ret"] == pytest.approx(0.20)     # AAA alone, reweighted onto the survivor
    assert feb["n_names"] == 1
    assert feb["n_cohorts"] == 1
    assert bool(feb["in_market"]) is True
    # both loss reasons in one month, kept apart
    assert feb["n_dropped_no_price"] == 1
    assert feb["n_dropped_nan_return"] == 1


def test_the_counters_partition_the_cohort_exactly(rets):
    """asked == held + no_price + nan_return, in every month.

    This is the one property that makes the counts trustworthy, and it is fragile in a
    specific way: `n_nan_return` is incremented BEFORE the `r.empty` guard. Move that
    line below the guard and every other test still passes while the accounting quietly
    stops adding up.
    """
    r = rets.copy()
    r.loc[pd.Timestamp("2020-02-29"), "BBB"] = np.nan
    r.loc[pd.Timestamp("2020-03-31"), ["AAA", "BBB"]] = np.nan   # whole cohort NaN
    out = e11.cohort_series({pd.Timestamp("2020-01-31"): ["AAA", "BBB", "GHOST"],
                             pd.Timestamp("2020-02-29"): ["GHOST"]}, r)
    total = (out["n_names"] + out["n_dropped_no_price"] + out["n_dropped_nan_return"])
    assert (out["n_asked"] == total).all()
    # and the all-dropped month is still counted as asked, not skipped
    mar = out.loc[pd.Timestamp("2020-03-31")]
    assert mar["n_asked"] > 0 and mar["n_names"] == 0
    assert not bool(mar["in_market"])


def test_a_cohort_whose_date_is_not_in_the_index_is_counted_not_vanished(rets):
    """The channel the name-level counters cannot see.

    A signal date absent from the price index is skipped before `n_asked` is touched, so
    without its own counter the disclosure reads perfectly clean while a whole cohort
    disappears. That is the survivorship case: a delisted name has no cached prices, so
    no column and possibly no month is ever created for it.
    """
    out = e11.cohort_series({pd.Timestamp("1999-12-31"): ["AAA"]}, rets)
    assert int(out["n_asked"].sum()) == 0          # nothing was ever asked
    assert int(out["n_dropped_no_price"].sum()) == 0
    assert not out["in_market"].any()
    # ...and the loss is on the record anyway
    assert (out["n_cohorts_unresolvable_date"] == 1).all()


# ------------------------------------------------------------------ the diagnostics
def test_the_sign_test_calls_a_coin_flip_a_coin_flip():
    r = e11._sign_test(61 / 120, 120)
    assert r["n_positive"] == 61
    assert r["p_value_two_sided"] > 0.9          # 61 of 120 is not evidence of anything


def test_the_sign_test_detects_a_real_skew():
    r = e11._sign_test(0.75, 120)
    assert r["p_value_two_sided"] < 0.001


def test_an_unavailable_gate_is_never_a_pass(monkeypatch):
    monkeypatch.setattr(e11, "COPPER_BRAIN", r"C:\nope\not\here")
    import sys
    monkeypatch.setitem(sys.modules, "copper_brain", None)
    g = e11._gate([0.01] * 50, n_trials=4)
    assert g["available"] is False
    assert not g.get("passes")


def test_the_registered_verdict_is_not_quietly_upgraded_by_the_gate():
    """P1+P2 decide the registered verdict; the gate decides status. Never merged."""
    out = {"variants": {"sp600_insiders_ge_1": {
        "annualised_excess_net_ex2020": 0.045,
        "monthly_excess_net": {"median": 0.001, "share_positive": 0.508, "n": 120},
        "capacity": {"blocked_share": 0.024},
        "breakeven_cost_bps": 529.0,
        "gate": {"available": True, "passes": False, "sharpe": 0.10,
                 "deflated_sharpe": {"ratio": 0.07},
                 "thresholds": {"deflated_sharpe_min": 1.645}},
    }, "sp600_insiders_ge_3": {
        "monthly_excess_net": {"median": 0.003, "share_positive": 0.55, "n": 120},
    }}}
    e11._criteria(out)
    assert out["overall_registered"] == "PASS"      # as registered
    assert out["status"] == "SHADOW"                # because the gate failed
    assert out["promoted"] is False
    assert "coin flip" in out["headline"]
