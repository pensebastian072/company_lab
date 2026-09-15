"""E30: a revenue series dwarfed by its own components is a fragment, not a total.

Found by the per-sector audit, which asked a question coverage cannot: does this
sub-test DISCRIMINATE inside this sector? Real Estate and Financials both came back
with ~17% of companies carrying an impossible revenue figure - operating income larger
than revenue, market cap 100,000x revenue - and the cause was one guard short in two
different places.

Measured 2026-08-25, on real filings:

  * **EQR** revenue_ttm $216,000 against a true ~$2.9bn. `Revenues` ($2.70bn) lost to
    `RevenueFromContractWithCustomerIncludingAssessedTax` ($384k of management fees) on
    chain order. Fixed in `tags._prefer_consolidated`.
  * **FITB** revenue_ttm $614m against interest and dividend income of $11.35bn plus
    non-interest income of $3.49bn. The bank substitute existed and was correct, but its
    trigger was `len(revenue) == 0` and FITB's chain was non-empty, so it never ran.
  * **HUM** (Humana) $6.18bn against $137.2bn - so this is not a REIT-and-bank story.
    **URI** (United Rentals), a plain STANDARD industrial, went $6.9bn -> $16.4bn.

The rule both fixes share, and the reason it is safe: **an empty series is a fallback; a
series dwarfed by a more consolidated measurement of the same thing is a bug.** A revenue
component cannot exceed its own total, so preferring the larger can only ever move
towards the consolidated line. On a 220-company sample 10 changed and every one
increased.
"""
from __future__ import annotations

from clab.fundamentals import metrics as mx
from clab.fundamentals import normalize as nz


def _q(year, quarter, val):
    import datetime as dt
    end = [dt.date(year, 3, 31), dt.date(year, 6, 30),
           dt.date(year, 9, 30), dt.date(year, 12, 31)][quarter - 1]
    return nz.Fact(end=end, val=float(val), start=end - dt.timedelta(days=91),
                   duration="Q")


def _series(vals):
    s = nz.QuarterSeries()
    s.facts = [_q(y, q, v) for y, q, v in vals]
    return s


_PERIODS = [(2025, 1), (2025, 2), (2025, 3), (2025, 4)]


def _pair(small, big):
    return (_series([(y, q, small) for y, q in _PERIODS]),
            _series([(y, q, big) for y, q in _PERIODS]))


# ------------------------------------------------------------------ _dominates
def test_a_fragment_is_dominated_by_the_consolidated_line():
    frag, whole = _pair(154_000_000, 3_700_000_000)      # FITB's shape
    assert mx._dominates(whole, frag)


def test_a_comparable_series_does_NOT_dominate():
    """A reclassification or a rounding difference must not reshuffle the chain."""
    a, b = _pair(1_000_000_000, 1_060_000_000)
    assert not mx._dominates(b, a)


def test_an_empty_incumbent_is_dominated_by_anything():
    """The original 'no revenue tag at all' fallback, preserved exactly."""
    _frag, whole = _pair(1, 3_700_000_000)
    assert mx._dominates(whole, nz.QuarterSeries())


def test_nothing_dominates_an_empty_candidate():
    _frag, whole = _pair(1, 3_700_000_000)
    assert not mx._dominates(nz.QuarterSeries(), whole)


def test_series_with_no_shared_period_leave_each_other_alone():
    """Two series covering different years say nothing about each other's completeness."""
    old = _series([(2019, q, 5_000_000_000) for q in (1, 2, 3, 4)])
    new = _series([(2025, q, 100_000_000) for q in (1, 2, 3, 4)])
    assert not mx._dominates(old, new)


def test_the_ratio_is_a_median_so_one_odd_quarter_cannot_decide_it():
    incumbent = _series([(2025, 1, 1_000), (2025, 2, 1_000),
                         (2025, 3, 1_000), (2025, 4, 1_000)])
    # one huge quarter, three comparable ones -> the median ratio is ~1, not dominance
    candidate = _series([(2025, 1, 900_000), (2025, 2, 1_050),
                         (2025, 3, 1_010), (2025, 4, 1_020)])
    assert not mx._dominates(candidate, incumbent)


def test_a_zero_incumbent_cannot_be_divided_by():
    incumbent = _series([(2025, q, 0) for q in (1, 2, 3, 4)])
    candidate = _series([(2025, q, 5_000) for q in (1, 2, 3, 4)])
    assert not mx._dominates(candidate, incumbent)


# ------------------------------------------------------------------ end to end
# ------------------------------------------------------------------ lessor revenue
# Three cases, all three found by A/B-ing the change over 260 real filings BEFORE it was
# committed. The first is the fix; the other two are regressions the first draft caused.
def test_a_lessor_stranded_in_the_past_is_rescued_by_its_lease_income():
    """EQR's `Revenues` AND its contract-revenue tag both stop at 2020-03-31, while
    `OperatingLeaseLeaseIncome` runs to the present. Without the substitute the company
    is scored on six-year-old revenue and its growth rates describe 2020."""
    incumbent = _series([(2019, q, 675_000_000) for q in (1, 2, 3, 4)])
    lease = _series([(2019, q, 660_000_000) for q in (1, 2, 3, 4)]
                    + [(y, q, 780_000_000) for y in (2024, 2025) for q in (1, 2, 3, 4)])
    assert mx._reaches_further(lease, incumbent)
    r = mx._overlap_ratio(lease, incumbent)
    assert mx.SUBSTITUTE_MIN_OVERLAP_RATIO <= r <= mx.SUBSTITUTE_MAX_OVERLAP_RATIO


def test_two_HALVES_of_one_business_never_substitute_for_each_other():
    """Iron Mountain: storage rent runs 1.72x its contract-revenue tag over their shared
    periods, because those are two halves of $7.56bn. Dominance is valid INSIDE the
    revenue chain, where every member is a candidate total; lease income is not one."""
    contract = _series([(y, q, 420_000_000) for y in (2021, 2022) for q in (1, 2, 3, 4)])
    lease = _series([(y, q, 723_000_000) for y in (2021, 2022) for q in (1, 2, 3, 4)])
    assert mx._overlap_ratio(lease, contract) > mx.SUBSTITUTE_MAX_OVERLAP_RATIO
    assert not mx._reaches_further(lease, contract), "and it is not fresher either"


def test_a_lease_series_sharing_NO_period_says_nothing_and_must_not_substitute():
    """The first draft replaced a $7.56bn series with a $2.99bn one on freshness alone."""
    incumbent = _series([(y, q, 1_890_000_000) for y in (2025, 2026) for q in (1, 2)])
    lease = _series([(y, q, 750_000_000) for y in (2018, 2019) for q in (1, 2, 3, 4)])
    assert mx._overlap_ratio(lease, incumbent) is None


# ------------------------------------------------------------------ stranded lines
def test_a_stranded_income_statement_line_is_rescued_by_its_derivation():
    """The lessor rule generalised one line down.

    A filer that stops tagging `GrossProfit` or `OperatingIncomeLoss` leaves a
    FULL-LENGTH series stranded years in the past. It passes the length test, then pairs
    a 2020 numerator with 2026 revenue, and `RATIO_PERIOD_MAX_GAP_DAYS` correctly refuses
    the ratio - so the point was withheld while `revenue - cogs` (or the EBIT
    reconstruction) sat there current and usable. Measured over 235 filings:
    `GrossProfit` stale for 6.4%, `OperatingIncomeLoss` for 4.7%.

    A/B over 240 filings: 8 quality failures resolved, 0 newly failing, and the recovered
    numbers check out against reality - BMY 70.2% gross / 27.7% operating, Nucor 15.5% /
    11.8%, H&R Block 23.7% operating.
    """
    stranded = _series([(y, q, 1_000) for y in (2018, 2019) for q in (1, 2, 3, 4)])
    derived = _series([(y, q, 1_020) for y in (2018, 2019) for q in (1, 2, 3, 4)]
                      + [(y, q, 1_180) for y in (2025, 2026) for q in (1, 2, 3, 4)])
    assert mx._rescues_a_stranded_series(derived, stranded)


def test_a_derivation_that_DISAGREES_where_it_overlaps_does_not_rescue():
    """Otherwise this is the fragment bug wearing a new hat."""
    stranded = _series([(y, q, 1_000) for y in (2018, 2019) for q in (1, 2, 3, 4)])
    disagreeing = _series([(y, q, 250) for y in (2018, 2019) for q in (1, 2, 3, 4)]
                          + [(y, q, 260) for y in (2025, 2026) for q in (1, 2, 3, 4)])
    assert not mx._rescues_a_stranded_series(disagreeing, stranded)


def test_a_current_line_is_never_replaced_by_its_derivation():
    """Only a STRANDED incumbent is rescued; a filed, current line keeps priority."""
    current = _series([(y, q, 1_000) for y in (2025, 2026) for q in (1, 2, 3, 4)])
    derived = _series([(y, q, 1_010) for y in (2025, 2026) for q in (1, 2, 3, 4)])
    assert not mx._rescues_a_stranded_series(derived, current)


def test_the_bank_substitute_fires_on_a_NON_EMPTY_fragment():
    """The whole bug: the substitute was correct and simply never ran.

    Rebuilt the way build_metrics does it, because the defect was at the call site and
    not in the arithmetic.
    """
    fragment = _series([(y, q, 154_000_000) for y, q in _PERIODS])      # card fees
    interest = _series([(y, q, 2_836_000_000) for y, q in _PERIODS])
    noninterest = _series([(y, q, 871_000_000) for y, q in _PERIODS])
    substitute = mx._add_series(interest, noninterest)

    assert len(fragment) > 0, "the old `len(revenue) == 0` trigger would not fire here"
    assert mx._dominates(substitute, fragment)
    val, _ = nz.ttm(substitute)
    assert 14.0e9 < val < 15.5e9
