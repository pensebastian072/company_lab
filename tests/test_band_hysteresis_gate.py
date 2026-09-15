"""Hysteresis must not apply to the INSUFFICIENT_DATA boundary.

F3 requires two consecutive readings before a band change takes effect, which stops a
label flipping on noise. Crossing the coverage gate is not noise: it means the framework
became applicable (or stopped being).

It also has to be exempt to work at all. The judgement half is being filled in at 100
companies a day and each is re-scored ONCE afterwards, so a pending band never gets its
second confirming reading. Measured live: AEIS had coverage 0.89 and band_raw WATCHLIST
but showed INSUFFICIENT_DATA with streak 1 of 2, and nothing would ever have re-scored
it to confirm.

The exemption is symmetric, so it cannot bias the ranking up or down - the specific
concern the F3 pre-registration raised about asymmetric rules.
"""
from __future__ import annotations

import pytest

from clab.scoring import rubric

INSUF = rubric.INSUFFICIENT_BAND


def test_leaving_insufficient_data_takes_effect_immediately():
    band, pending, streak = rubric.advance_band(INSUF, None, 0, "WATCHLIST")
    assert band == "WATCHLIST"
    assert pending is None and streak == 0


def test_entering_insufficient_data_takes_effect_immediately():
    """Symmetric: losing coverage must show at once too, or the sheet claims a band the
    data no longer supports."""
    band, pending, streak = rubric.advance_band("WATCHLIST", None, 0, INSUF)
    assert band == INSUF
    assert pending is None and streak == 0


def test_ordinary_band_changes_still_need_confirmation():
    """The rule F3 was actually for is untouched."""
    band, pending, streak = rubric.advance_band("WATCHLIST", None, 0, "INVESTABLE")
    assert band == "WATCHLIST", "a single reading must not move an ordinary band"
    assert pending == "INVESTABLE" and streak == 1

    band, pending, streak = rubric.advance_band(band, pending, streak, "INVESTABLE")
    assert band == "INVESTABLE", "the second consecutive reading confirms it"


def test_a_flapping_score_still_does_not_move_the_band():
    band, pending, streak = "WATCHLIST", None, 0
    for raw in ("INVESTABLE", "WATCHLIST", "INVESTABLE", "WATCHLIST"):
        band, pending, streak = rubric.advance_band(band, pending, streak, raw)
    assert band == "WATCHLIST"


def test_the_aeis_case_end_to_end():
    """A company that gains the judgement half is shown its real band on that run."""
    band, pending, streak = INSUF, None, 0
    band, pending, streak = rubric.advance_band(band, pending, streak, "WATCHLIST")
    assert band == "WATCHLIST", (
        "a single re-score is all a company gets during the rollout")


@pytest.mark.parametrize("other", ["EXCEPTIONAL", "HIGH_CONVICTION", "INVESTABLE",
                                   "WATCHLIST", "WEAK", "REJECT"])
def test_gate_crossings_are_immediate_from_and_to_every_band(other):
    assert rubric.advance_band(INSUF, None, 0, other)[0] == other
    assert rubric.advance_band(other, None, 0, INSUF)[0] == INSUF


def test_smooth_bands_agrees_with_the_state_machine():
    """smooth_bands is written in terms of advance_band; they must not drift."""
    seq = [INSUF, "WATCHLIST", "WATCHLIST", "INVESTABLE", "WATCHLIST"]
    out = rubric.smooth_bands(seq)
    assert out[0] == INSUF
    assert out[1] == "WATCHLIST", "leaving the gate is immediate"
    assert out[3] == "WATCHLIST", "an ordinary change still needs two readings"
