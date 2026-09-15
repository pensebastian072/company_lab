"""F3 on the LIVE scoring path, not just in the research code.

`smooth_bands` sat in the rubric for a day being called only by a study, so the dashboard
and the workbook shipped the RAW band and flipped 79 of 500 companies in two days. These
tests pin the live behaviour:

  * the state machine and the sequence helper must agree - two implementations of a rule
    this fiddly would drift and then neither number could be trusted;
  * hysteresis must be symmetric, because letting downgrades through immediately would
    quietly bias the whole ranking downward;
  * a scorecard written before F3 existed must be a valid starting state, or an upgrade
    silently resets every company to "first reading" and the fix does nothing for a week.
"""
from __future__ import annotations

import pytest

from clab.scoring import composite, rubric
from clab.scoring.types import ComponentScore, scored


def _card(points: int, *, prior=None, pending=None, streak=0) -> composite.Scorecard:
    """A scorecard whose only component is FE, carrying `points` of its max."""
    comps = {}
    for code, (label, mx) in rubric.COMPONENTS.items():
        got = min(points, mx) if code == "FE" else (mx if points else 0)
        comps[code] = ComponentScore(
            code=code, label=label, max_points=mx,
            subtests=[scored(f"{code.lower()}_x", label, mx, got)])
        points = max(0, points - got) if code == "FE" else points
    return composite.build_scorecard(
        ticker="AAA", cik="1", name="A", as_of="2026-01-01T00:00:00Z",
        components=comps, prior_band=prior, prior_band_pending=pending,
        prior_band_streak=streak)


# ------------------------------------------------------------------ the state machine
def test_advance_band_matches_smooth_bands_on_the_same_sequence():
    """One rule, one implementation. smooth_bands is written in terms of advance_band."""
    seq = ["INVESTABLE", "WATCHLIST", "WATCHLIST", "WATCHLIST", "INVESTABLE",
           "WEAK", "INVESTABLE", "WEAK", "WEAK", "WEAK"]
    expected = rubric.smooth_bands(seq)

    cur, pend, streak = None, None, 0
    got = []
    for raw in seq:
        cur, pend, streak = rubric.advance_band(cur, pend, streak, raw)
        got.append(cur)
    assert got == expected


def test_first_reading_shows_the_raw_band():
    cur, pend, streak = rubric.advance_band(None, None, 0, "WEAK")
    assert (cur, pend, streak) == ("WEAK", None, 0)


def test_a_single_reading_does_not_move_the_band():
    cur, pend, streak = rubric.advance_band("INVESTABLE", None, 0, "WATCHLIST")
    assert cur == "INVESTABLE" and pend == "WATCHLIST" and streak == 1


def test_two_consecutive_readings_move_it():
    cur, pend, streak = rubric.advance_band("INVESTABLE", "WATCHLIST", 1, "WATCHLIST")
    assert cur == "WATCHLIST" and pend is None and streak == 0


def test_returning_to_the_shown_band_cancels_the_pending_change():
    cur, pend, streak = rubric.advance_band("INVESTABLE", "WATCHLIST", 1, "INVESTABLE")
    assert cur == "INVESTABLE" and pend is None and streak == 0


def test_a_different_candidate_restarts_the_streak():
    cur, pend, streak = rubric.advance_band("INVESTABLE", "WATCHLIST", 1, "WEAK")
    assert cur == "INVESTABLE" and pend == "WEAK" and streak == 1


def test_hysteresis_is_symmetric():
    """An asymmetric rule that let downgrades through immediately would bias the whole
    ranking downward, which is why the pre-registration made it symmetric."""
    up = rubric.smooth_bands(["WEAK", "INVESTABLE", "INVESTABLE"])
    down = rubric.smooth_bands(["INVESTABLE", "WEAK", "WEAK"])
    assert up == ["WEAK", "WEAK", "INVESTABLE"]
    assert down == ["INVESTABLE", "INVESTABLE", "WEAK"]


# ------------------------------------------------------------------ the scorecard
def test_scorecard_exposes_both_the_raw_and_the_shown_band():
    card = _card(rubric.COMPONENTS["FE"][1])
    d = card.to_dict()
    assert d["band_raw"] == card.band_raw
    assert d["band"] == card.band
    assert d["band_confirm_readings"] == rubric.BAND_CONFIRM_READINGS
    assert "band_pending" in d and "band_pending_streak" in d


def test_a_first_ever_scorecard_shows_its_raw_band():
    card = _card(rubric.COMPONENTS["FE"][1])
    assert card.prior_band is None
    assert card.band == card.band_raw


def test_the_shown_band_lags_a_single_move():
    full = rubric.COMPONENTS["FE"][1]
    high = _card(full)
    low = _card(0, prior=high.band)
    assert low.band_raw != high.band, "fixture must actually change the raw band"
    assert low.band == high.band, "one reading must not move the shown band"
    assert low.band_pending == low.band_raw
    assert low.band_pending_streak == 1


def test_the_shown_band_moves_on_confirmation():
    full = rubric.COMPONENTS["FE"][1]
    high = _card(full)
    first = _card(0, prior=high.band)
    second = _card(0, prior=first.band, pending=first.band_pending,
                   streak=first.band_pending_streak)
    assert second.band == second.band_raw, "a confirmed change must take effect"
    assert second.band_pending is None


def test_table_row_carries_the_raw_band_for_the_ui():
    card = _card(rubric.COMPONENTS["FE"][1])
    row = card.table_row()
    assert row["band"] == card.band and row["band_raw"] == card.band_raw


# ------------------------------------------------------------------ the upgrade path
def test_prior_state_from_a_pre_f3_scorecard(monkeypatch, tmp_path):
    """A scorecard written before F3 has no band_pending. Its stored `band` IS the raw
    band, which is a valid starting state - otherwise upgrading resets every company to
    "first reading" and the fix does nothing for a week."""
    from clab import config
    from clab.runner import engine
    from clab.net import atomic_write_json

    monkeypatch.setattr(config, "SCORECARD_DIR", tmp_path)
    atomic_write_json(tmp_path / "1_AAA.json",
                      {"ticker": "AAA", "cik": "1", "band": "INVESTABLE"})
    assert engine.band_state("1", "AAA")[:3] == ("INVESTABLE", None, 0)


def test_prior_state_round_trips_a_pending_change(monkeypatch, tmp_path):
    from clab import config
    from clab.runner import engine
    from clab.net import atomic_write_json

    monkeypatch.setattr(config, "SCORECARD_DIR", tmp_path)
    atomic_write_json(tmp_path / "1_AAA.json",
                      {"ticker": "AAA", "cik": "1", "band": "INVESTABLE",
                       "band_pending": "WATCHLIST", "band_pending_streak": 1})
    assert engine.band_state("1", "AAA")[:3] == ("INVESTABLE", "WATCHLIST", 1)


@pytest.mark.parametrize("stored", [
    {},                                             # no scorecard content at all
    {"ticker": "AAA"},                              # no band
    {"band": ""},                                   # empty band
    {"band": None},
    {"band": "WEAK", "band_pending_streak": "x"},   # junk streak
])
def test_prior_state_degrades_to_a_first_reading(monkeypatch, tmp_path, stored):
    from clab import config
    from clab.runner import engine
    from clab.net import atomic_write_json

    monkeypatch.setattr(config, "SCORECARD_DIR", tmp_path)
    atomic_write_json(tmp_path / "1_AAA.json", stored)
    band, pending, streak, _reading_date = engine.band_state("1", "AAA")
    assert pending is None and streak == 0
    assert band in (None, "WEAK")


def test_missing_scorecard_is_a_first_reading(monkeypatch, tmp_path):
    from clab import config
    from clab.runner import engine

    monkeypatch.setattr(config, "SCORECARD_DIR", tmp_path)
    assert engine.band_state("1", "NOPE") == (None, None, 0, None)
