"""E05 measurement harness: the parts that could silently misreport a fix.

Two failure modes worth pinning, because either would produce a plausible-looking
number rather than an error:

  * a GAP in coverage must not be counted as a band change - a symbol that stops
    reporting and resumes two years later has not changed its band;
  * smoothing must reduce churn without reordering the bands, so the ordinal IC it is
    graded on has to be computed off the same band scale in both arms.
"""
from __future__ import annotations

import pandas as pd

from clab.research import e05_measure as em
from clab.scoring import rubric


def test_band_of_uses_the_rubric_edges():
    assert em._band_of(0.95) == "EXCEPTIONAL"
    assert em._band_of(0.80) == "HIGH_CONVICTION"
    assert em._band_of(0.705) == "INVESTABLE"
    assert em._band_of(0.10) == "REJECT"
    assert em._band_of(None) is None
    assert em._band_of(float("nan")) is None


def _panel(pcts, ticker="AAA"):
    dates = pd.date_range("2018-01-31", periods=len(pcts), freq="ME")
    return pd.DataFrame({"ticker": ticker, "date": dates, "measured_pct": pcts,
                         "fwd_1y": [0.10] * len(pcts), "fwd_3y": [0.30] * len(pcts)})


def test_hysteresis_cuts_churn_on_a_flapping_series():
    # alternates across the 70% INVESTABLE edge every month: raw churns every month
    pcts = [0.71, 0.69, 0.71, 0.69, 0.71, 0.69, 0.71, 0.69]
    res = em.f3(_panel(pcts))
    raw = res["arms"]["band_raw"]
    sm = res["arms"]["band_smoothed"]
    assert raw["band_change_rate_per_month"] == 1.0, "raw should flip every month"
    assert sm["band_change_rate_per_month"] == 0.0, (
        "a strict alternation never gets two consecutive confirmations, so the smoothed "
        "band must never change")
    assert sm["median_months_in_a_band"] > raw["median_months_in_a_band"]


def test_a_sustained_move_still_changes_the_band():
    """Hysteresis must delay a real change, not suppress it."""
    pcts = [0.85] * 4 + [0.55] * 4
    res = em.f3(_panel(pcts))
    assert res["arms"]["band_smoothed"]["band_distribution"].get("WEAK", 0) > 0, (
        "a sustained drop must eventually be reflected")
    assert (res["arms"]["band_smoothed"]["band_distribution"]["HIGH_CONVICTION"]
            > res["arms"]["band_raw"]["band_distribution"]["HIGH_CONVICTION"]), (
        "the delay should leave the old band standing for an extra reading")


def test_coverage_gap_is_not_a_band_change():
    pcts = [0.85, 0.85, None, None, None, 0.85, 0.85]
    res = em.f3(_panel(pcts))
    assert res["arms"]["band_smoothed"]["band_change_rate_per_month"] == 0.0
    assert res["arms"]["band_raw"]["band_change_rate_per_month"] == 0.0


def test_confirm_readings_comes_from_the_rubric():
    res = em.f3(_panel([0.85] * 3))
    assert res["confirm_readings"] == rubric.BAND_CONFIRM_READINGS


def test_f1_criteria_are_the_preregistered_ones():
    """A moved goalpost is the easiest way to fake a pass."""
    assert em.F1_BASELINE_SECTOR_SPREAD_PTS == 21.4
    assert em.F1_SPREAD_MUST_BE_UNDER_PTS == 10.7
    assert em.F3_MAX_BAND_CHANGE_RATE == 0.12
    assert em.F3_MIN_MONTHS_IN_BAND == 4.0
    assert em.F3_MAX_IC_DELTA == 0.005
