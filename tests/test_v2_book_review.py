"""The book-level read of the v2 workbook - descriptive, so what is pinned is honesty.

Two things here could mislead a reader without ever raising:

  * **A dead component must be counted as dead, not as a zero.** `*_available == 0` means
    the component produced nothing usable; if that were read as "scored zero" the book
    review would report a company as merely weak when it was never judged.
  * **Band counts must cover every band the rubric can emit.** A hardcoded list that
    silently drops a band would make the distribution add up to less than the book and
    look tidy doing it.
"""
from __future__ import annotations

import pandas as pd

from clab.research import v2_book_review as bookrev
from clab.scoring import rubric


def test_band_order_covers_every_band_the_rubric_emits():
    emitted = {rubric.band_for(score, 1.0) for score in range(0, 101)}
    emitted.add(rubric.band_for(90, 0.5))          # below the coverage gate
    assert emitted <= set(bookrev.BAND_ORDER)


def test_bands_counts_every_row_once():
    df = pd.DataFrame({"band": ["INVESTABLE", "REJECT", "REJECT", "INSUFFICIENT_DATA"]})
    counts = bookrev._bands(df)
    assert counts["REJECT"] == 2
    assert counts["INVESTABLE"] == 1
    assert counts["INSUFFICIENT_DATA"] == 1
    assert sum(v for k, v in counts.items() if k != "other") + counts["other"] == len(df)


def test_an_unexpected_band_lands_in_other_rather_than_vanishing():
    df = pd.DataFrame({"band": ["INVESTABLE", "SOMETHING_NEW"]})
    counts = bookrev._bands(df)
    assert counts["other"] == 1


def test_spearman_refuses_a_sample_too_small_to_mean_anything():
    a = pd.Series(range(5))
    assert bookrev._spearman(a, a) is None
    b = pd.Series(range(20))
    assert bookrev._spearman(b, b) == 1.0


def test_dist_drops_nan_rather_than_propagating_it():
    """Three of 1,501 production rows have a null score, and NaN scrambles a sort rather
    than skewing it - the same trap `xlsx_export._finite` exists for."""
    s = pd.Series([1.0, 2.0, None, 3.0])
    assert bookrev._dist(s) == {"n": 3, "mean": 2.0, "p25": 1.5, "median": 2.0,
                                "p75": 2.5, "max": 3.0}
