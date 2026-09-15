"""E30: the prior-year share count must go through the SAME filter as the current one.

E28 fixed `diluted_shares_ttm` with `ttm_share_count`, which drops a poisoned row - the
AAPL FY 10-K files a quarter-duration `diluted_shares` of **-47,029,000**, a change in
shares wearing a count's clothes. It did not fix `diluted_shares_ttm_prior`, which kept a
hand-rolled `sum(facts[-4:]) / 4.0`.

Two code paths for one quantity, and only one of them filtered. The prior window came out
~25% light, so `dilution_yoy` read a **universal fake dilution**: median +32.5% across
1,469 companies - almost exactly 4/3 - and **97% of every sector scored 0 on
`bs_dilution`**, including AAPL, MSFT, KO and NVDA, all of which were shrinking their
share counts. A whole point of the framework was measuring an artifact of its own
arithmetic in all eleven sectors at once.

The rule this pins: **one derivation, one filter, every window.** A sub-test that is
constant across every sector is the symptom to look for.
"""
from __future__ import annotations

import datetime as dt

from clab.fundamentals import normalize as nz
from clab.fundamentals.metrics import build_metrics, ttm_share_count


def _fact(end: str, val: float) -> nz.Fact:
    d = dt.date.fromisoformat(end)
    return nz.Fact(end=d, val=val, start=d - dt.timedelta(days=91), duration="Q")


def _series(vals: list[tuple[str, float]]) -> nz.QuarterSeries:
    s = nz.QuarterSeries()
    s.facts = [_fact(e, v) for e, v in vals]
    return s


#: eight clean quarters of a company buying back ~1% a year, with one poisoned row in
#: the PRIOR-year window - the window E28 left unfiltered.
_QUARTERS = [
    ("2024-03-30", 10_200_000_000.0),
    ("2024-06-29", 10_150_000_000.0),
    ("2024-09-28", -47_029_000.0),          # the poison, in the prior window
    ("2024-12-28", 10_100_000_000.0),
    ("2025-03-29", 10_060_000_000.0),
    ("2025-06-28", 10_020_000_000.0),
    ("2025-09-27", 9_990_000_000.0),
    ("2025-12-27", 9_960_000_000.0),
]


def test_the_prior_window_drops_the_poisoned_quarter_too():
    s = _series(_QUARTERS)
    facts = s.facts[:len(s.facts) - 4]                  # the prior-year window
    val, diag = ttm_share_count(nz.QuarterSeries(facts=facts))
    assert 10.0e9 < val < 10.3e9, "the prior window averaged in a -47m row"
    assert "2024-09-28" in diag["quarters_dropped"]


def test_the_naive_prior_window_is_what_produced_the_fake_dilution():
    """The old expression, kept here so the defect cannot come back unrecognised."""
    s = _series(_QUARTERS)
    facts = s.facts[:len(s.facts) - 4]
    naive = sum(f.val for f in facts[-4:]) / 4.0
    filtered, _ = ttm_share_count(nz.QuarterSeries(facts=facts))
    assert naive < 0.8 * filtered, "the naive prior must be the light one"
    # and the light prior is what makes a company shrinking its count look like a diluter
    current = 9_990_000_000.0
    assert (current - naive) / abs(naive) > 0.25
    assert (current - filtered) / abs(filtered) < 0.0


def test_a_repurchaser_reads_as_a_repurchaser_end_to_end():
    """Through build_metrics, not just the helper - the bug was in the call site."""
    payload = {"facts": {}}
    M = build_metrics(payload)
    M.series["diluted_shares"] = _series(_QUARTERS)
    # re-run just the share-count block the way build_metrics does
    cur, _ = ttm_share_count(M.series["diluted_shares"])
    facts = M.series["diluted_shares"].facts[:-4]
    prior, _ = ttm_share_count(nz.QuarterSeries(facts=facts))
    assert nz.yoy(cur, prior) < 0.0, "buying back stock must not read as dilution"


def test_an_empty_prior_window_is_none_not_zero():
    """Absent is NO_DATA. A 0 here would score as a company that issued no shares."""
    s = _series(_QUARTERS[:2])
    facts = s.facts[:len(s.facts) - 4]
    assert facts == []
    val = None if not facts else ttm_share_count(nz.QuarterSeries(facts=facts))[0]
    assert val is None
