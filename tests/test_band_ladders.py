"""Every band/ladder pair in the rubric must be length-consistent.

A mismatch does not misprice anything - it raises IndexError from inside a scorer, the
engine catches it as "FE scoring failed", and the company loses the ENTIRE component to
NO_DATA. That is exactly what happened: FE_ROIC_BANDS has four thresholds while fe.py
hardcoded a four-entry ladder, so every company with ROIC below 4% scored FE 0/18 and
fell under the coverage gate into INSUFFICIENT_DATA. Found on small caps, but it was
hitting the live S&P 500 too.

These tests are deliberately systematic rather than example-based: a new band tuple added
to the rubric should be caught here, not by a user noticing a blank component.
"""
from __future__ import annotations

import pytest

from clab.scoring import fe as fe_mod
from clab.scoring import rubric


def test_band_from_thresholds_rejects_a_wrong_length_ladder():
    with pytest.raises(ValueError, match="needs 5"):
        rubric.band_from_thresholds(0.5, (0.4, 0.3, 0.2, 0.1), (2, 2, 1, 0))


def test_band_from_thresholds_still_returns_none_for_missing_values():
    """A missing value is NO_DATA and must not be validated into an exception."""
    assert rubric.band_from_thresholds(None, (0.4, 0.3, 0.2, 0.1), (1,)) is None


@pytest.mark.parametrize("n_bands", [2, 3, 4, 5])
@pytest.mark.parametrize("mx", [1, 2, 3])
def test_ladder_for_is_always_the_right_length(n_bands, mx):
    bands = tuple(round(0.5 - 0.1 * i, 2) for i in range(n_bands))
    ladder = rubric.ladder_for(bands, mx)
    assert len(ladder) == n_bands + 1
    # never awards more than the sub-test is worth, never negative, ends at zero
    assert max(ladder) == mx
    assert min(ladder) == 0
    assert ladder[-1] == 0
    assert all(a >= b for a, b in zip(ladder, ladder[1:])), "ladder must not increase"


def test_ladder_matches_the_existing_hand_written_convention():
    """The conventions already written out for revenue CAGR and margins."""
    assert rubric.ladder_for((0.5, 0.3, 0.1), 1) == (1, 1, 1, 0)
    assert rubric.ladder_for((0.5, 0.3, 0.1), 2) == (2, 2, 1, 0)
    assert rubric.ladder_for((0.5, 0.3, 0.1, 0.05), 1) == (1, 1, 1, 0, 0)
    assert rubric.ladder_for((0.5, 0.3, 0.1, 0.05), 2) == (2, 2, 1, 1, 0)


@pytest.mark.parametrize("value", [-5.0, -0.5, -0.0128, 0.0, 0.039, 1e9])
def test_roic_below_every_band_scores_rather_than_raising(value):
    """AAP's ROIC was -1.3%. That must be a zero, not a lost component."""
    pts = rubric.band_from_thresholds(value, rubric.FE_ROIC_BANDS,
                                      rubric.ladder_for(rubric.FE_ROIC_BANDS, 2))
    assert pts is not None
    assert 0 <= pts <= 2


def _band_tuples():
    """Every descending-band tuple the rubric defines for a scorer."""
    for name in dir(rubric):
        if not name.isupper() or not name.endswith("BANDS"):
            continue
        v = getattr(rubric, name)
        if isinstance(v, tuple) and v and all(isinstance(x, (int, float)) for x in v):
            yield name, v


@pytest.mark.parametrize("mx", [1, 2, 3])
def test_every_rubric_band_tuple_can_be_laddered(mx):
    for name, bands in _band_tuples():
        ladder = rubric.ladder_for(bands, mx)
        assert len(ladder) == len(bands) + 1, f"{name} ladder length"
        # a value below every threshold must score, not raise
        below = min(bands) - abs(min(bands)) - 1.0
        assert rubric.band_from_thresholds(below, bands, ladder) == 0, name


def test_fe_margin_points_survives_a_negative_margin():
    """The real regression: a negative margin used to take FE down with it."""
    class _Ctx:
        peers = {}
        sector = "Consumer Discretionary"

    for bands, mx in ((rubric.FE_ROIC_BANDS, 2),
                      (rubric.FE_OPERATING_MARGIN_BANDS, 1),
                      (rubric.FE_GROSS_MARGIN_BANDS, 1)):
        pts, note, basis = fe_mod._margin_points(
            _Ctx(), "fe_roic", "roic", -0.0128, mx, bands)
        assert pts == 0
        assert basis == "absolute"
        assert note
