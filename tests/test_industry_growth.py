"""`structural_growth` from the members' own revenue, and the four ways it refuses.

Every guard is proved in BOTH directions - that it refuses the case it exists for, and that
it passes a clean unit. A guard only ever seen refusing is indistinguishable from a guard
that cannot pass anything, which is how E34's first draft reported 147 companies clean.

The refusal cases are the REAL ones measured on 2026-09-12, with the real numbers: tobacco's
62% top member, specialty_stores' 14.6-point aggregate-to-median gap. A synthetic fixture
would not have told us the bars are set where the data actually separates.
"""
from __future__ import annotations

from clab.external import industry_growth as IG

DEFL = 0.034


def _rev(**pairs):
    """ticker -> (revenue_now, revenue_prior)."""
    return {t: (float(n), float(p)) for t, (n, p) in pairs.items()}


def _even(n, growth=0.05, size=100.0):
    """n equal-sized members all growing at the same rate - the clean case."""
    return {f"T{i:02d}": (size * (1 + growth), size) for i in range(n)}


# --------------------------------------------------------------- the clean case
def test_an_even_unit_growing_above_inflation_reads_MODERATE():
    r = IG.growth_for_industry("u", list(_even(6, 0.08)), _even(6, 0.08), deflator=DEFL)
    assert r["ok"]
    assert r["peers"] == 6
    assert abs(r["nominal_growth"] - 0.08) < 1e-9
    assert abs(r["real_growth"] - (0.08 - DEFL)) < 1e-9
    assert r["value"] == "MODERATE"


def test_a_unit_growing_slower_than_prices_is_DECLINING_not_growing():
    """The arithmetic the whole module exists for: +2% of dollars against +3.4% of price is
    a shrinking industry, and the nominal figure alone would have read as a healthy one."""
    r = IG.growth_for_industry("u", list(_even(6, 0.02)), _even(6, 0.02), deflator=DEFL)
    assert r["ok"]
    assert r["nominal_growth"] > 0 and r["real_growth"] < 0
    assert r["value"] == "FLAT"          # -1.4% real, inside the wide FLAT band
    r2 = IG.growth_for_industry("u", list(_even(6, -0.02)), _even(6, -0.02), deflator=DEFL)
    assert r2["value"] == "DECLINING"    # -5.4% real


def test_the_bands_are_read_off_real_growth_at_every_step():
    assert IG.band_for(-0.10) == "DECLINING"
    assert IG.band_for(-0.021) == "DECLINING"
    assert IG.band_for(-0.019) == "FLAT"
    assert IG.band_for(0.0) == "FLAT"
    assert IG.band_for(0.019) == "FLAT"
    assert IG.band_for(0.03) == "MODERATE"
    assert IG.band_for(0.08) == "HIGH"
    assert IG.band_for(0.25) == "EXCEPTIONAL"


# ------------------------------------------------------------ MIN_PEERS
def test_two_companies_are_not_an_industry():
    """brewers (SAM, TAP) and distillers_vintners (BF-B, STZ) both hit this on 2026-09-12."""
    r = IG.growth_for_industry("brewers", ["A", "B"], _rev(A=(105, 100), B=(98, 100)),
                               deflator=DEFL)
    assert not r["ok"] and "under the 4-peer floor" in r["reason"]


def test_a_member_missing_a_revenue_window_is_dropped_from_the_count_not_from_one_total():
    """Both windows or nothing. A peer counted in one total and not the other moves the
    aggregate for a reason that has nothing to do with the industry."""
    rev = _rev(A=(105, 100), B=(105, 100), C=(105, 100))
    r = IG.growth_for_industry("u", ["A", "B", "C", "D"], rev, deflator=DEFL)
    assert r["usable"] == 3 and r["coverage"] == 0.75
    assert not r["ok"] and "under the 4-peer floor" in r["reason"]


# ------------------------------------------------------------ MAX_TOP_SHARE
def test_one_member_carrying_most_of_the_revenue_is_REFUSED():
    """Tobacco, for real: the aggregate read +4.9% while the median member read -0.6%,
    because Philip Morris is 62% of the unit. An industry ordinal taken from that would
    have been Philip Morris's growth wearing the industry's name."""
    rev = _rev(BIG=(620, 560), A=(100, 101), B=(100, 101), C=(100, 100), D=(100, 100))
    r = IG.growth_for_industry("tobacco", list(rev), rev, deflator=DEFL)
    assert not r["ok"]
    assert "BIG is 61% of the unit's revenue" in r["reason"]
    # and it still reports the numbers, so a caller can say WHY it refused
    assert r["top_ticker"] == "BIG" and r["top_share"] > IG.MAX_TOP_SHARE


def test_a_unit_just_under_the_concentration_bar_still_passes():
    rev = _rev(BIG=(480, 457), A=(180, 171), B=(180, 171), C=(160, 152))
    r = IG.growth_for_industry("u", list(rev), rev, deflator=DEFL)
    assert r["top_share"] < IG.MAX_TOP_SHARE
    assert r["ok"]


# ------------------------------------------------------- MAX_AGG_MEDIAN_GAP
def test_an_aggregate_that_does_not_describe_the_median_member_is_REFUSED():
    """specialty_stores, for real: +18.4% aggregate against a +3.8% median member. Nothing
    is wrong with either number; they are answers to different questions, and only one of
    them is the industry's growth."""
    rev = _rev(A=(135, 100), B=(136, 100), C=(104, 100), D=(104, 100), E=(104, 100))
    r = IG.growth_for_industry("specialty_stores", list(rev), rev, deflator=DEFL)
    assert not r["ok"]
    assert "not describing the typical member" in r["reason"]
    assert abs(r["nominal_growth"] - r["median_growth"]) > IG.MAX_AGG_MEDIAN_GAP


# ------------------------------------------------------------ STRUCTURAL_MOVE
def test_an_acquirer_is_excluded_from_BOTH_totals_not_just_counted_oddly():
    """A company that buys a competitor grows its revenue without competing better for a
    dollar of it. Left in, it moves the unit's whole aggregate."""
    rev = _rev(A=(105, 100), B=(105, 100), C=(105, 100), D=(105, 100), M=(300, 100))
    r = IG.growth_for_industry("u", list(rev), rev, deflator=DEFL)
    assert r["excluded"] == ["M"]
    assert r["ok"] and abs(r["nominal_growth"] - 0.05) < 1e-9


def test_a_divester_is_excluded_the_same_way_as_an_acquirer():
    """Both directions. An earlier module in this repo guarded only the upside."""
    rev = _rev(A=(105, 100), B=(105, 100), C=(105, 100), D=(105, 100), M=(30, 100))
    r = IG.growth_for_industry("u", list(rev), rev, deflator=DEFL)
    assert r["excluded"] == ["M"]
    assert r["ok"] and abs(r["nominal_growth"] - 0.05) < 1e-9


def test_a_refusal_always_says_why_and_never_looks_like_missing_data():
    """Every refusal carries `ok` False AND a reason. A caller must never be able to read a
    guard's refusal as 'this industry has no revenue data' - the journal reports the three
    kinds of refusal separately and they are not interchangeable."""
    for members, rev in ((["A", "B"], _rev(A=(105, 100), B=(105, 100))),
                         (list("ABCDE"), _rev(A=(620, 560), B=(100, 101), C=(100, 101),
                                              D=(100, 100), E=(100, 100)))):
        r = IG.growth_for_industry("u", members, rev, deflator=DEFL)
        assert r["ok"] is False
        assert r.get("reason")
        assert "industry_id" in r and "usable" in r


def test_the_deflator_is_required_and_is_not_silently_zero():
    """A missing deflator would turn every nominal figure into a real one and quietly
    promote a shrinking industry to a growing one - the exact error this module is for."""
    import pytest
    with pytest.raises(TypeError):
        IG.growth_for_industry("u", list(_even(5)), _even(5))        # no deflator


# ------------------------------------------------------------ the window
def _win(n, growth_1y, growth_3y, size=100.0):
    """Two windows over the same n members, each at its own annualised rate."""
    one = {f"T{i:02d}": (size * (1 + growth_1y), size) for i in range(n)}
    three = {f"T{i:02d}": (size * (1 + growth_1y), size * (1 + growth_1y)
                           / (1 + growth_3y) ** 3) for i in range(n)}
    return {1: one, 3: three}


def test_growth_is_annualised_so_a_band_means_the_same_at_every_window():
    """A unit that doubled over three years grew 26% a year, not 100%. Without
    annualisation every 3-year read would land in EXCEPTIONAL and the bands would mean two
    different things depending on which window produced them."""
    rev = {t: (200.0, 100.0) for t in ("A", "B", "C", "D")}
    r1 = IG.growth_for_industry("u", list(rev), rev, deflator=0.0, window_years=1)
    r3 = IG.growth_for_industry("u", list(rev), rev, deflator=0.0, window_years=3)
    assert abs(r1["nominal_growth"] - 1.0) < 1e-9
    assert abs(r3["nominal_growth"] - (2 ** (1 / 3) - 1)) < 1e-9
    assert r3["window_years"] == 3


def test_the_structural_guard_compares_annualised_rates_not_raw_changes():
    """On a three-year window a raw-percentage bar of 0.40 would admit a company that
    TRIPLED as if it had grown 40% - the acquirer the guard exists to exclude."""
    # A-D grew 15% over three years, 4.8% a year. M quintupled: 71% a year, which is 66
    # points clear of the median and excluded. As a RAW change M is +400% and A-D +15%,
    # so a raw bar of 0.40 would have excluded all five and returned nothing.
    rev = {"A": (115.0, 100.0), "B": (115.0, 100.0), "C": (115.0, 100.0),
           "D": (115.0, 100.0), "M": (500.0, 100.0)}
    r = IG.growth_for_industry("u", list(rev), rev, deflator=0.0, window_years=3)
    assert r["excluded"] == ["M"]
    assert abs(r["nominal_growth"] - (1.15 ** (1 / 3) - 1)) < 1e-9


def test_an_unknown_window_is_refused_rather_than_guessed():
    import pytest
    with pytest.raises(ValueError):
        IG.growth_for_industry("u", list(_even(5)), _even(5), deflator=DEFL,
                               window_years=2)
    with pytest.raises(ValueError):
        IG.load_revenue(window_years=7)


# ------------------------------------------------------- agreeing_growth
def test_both_windows_must_agree_before_an_ordinal_is_written():
    """The test that retracted three of this module's own units on 2026-09-12."""
    rev = _win(5, 0.05, 0.05)
    r = IG.agreeing_growth("u", list(rev[1]), rev, {1: 0.0, 3: 0.0})
    assert r["ok"] and r["value"] == "MODERATE"
    assert r["agreed_bands"] == {1: "MODERATE", 3: "MODERATE"}
    assert r["windows_tested"] == [1, 3]


def test_windows_landing_in_different_bands_are_REFUSED_and_both_are_reported():
    """leisure_products, for real: FLAT at one year, DECLINING at three. The refusal has
    to carry BOTH numbers, because the next reader's question is always 'by how much'."""
    # one year: +3.4% nominal against a 3.4% deflator is 0.0% real -> FLAT
    # three years: -5.0% a year against 2.9% is -7.9% real      -> DECLINING
    rev = {1: {t: (103.4, 100.0) for t in "ABCDE"},
           3: {t: (103.4, 103.4 / 0.95 ** 3) for t in "ABCDE"}}
    r = IG.agreeing_growth("leisure_products", list("ABCDE"), rev, {1: 0.034, 3: 0.029})
    assert not r["ok"]
    assert "the windows disagree" in r["reason"]
    assert "1y" in r["reason"] and "3y" in r["reason"]
    assert "FLAT" in r["reason"] and "DECLINING" in r["reason"]
    assert r.get("agreed_bands") is None


def test_a_window_that_cannot_measure_the_unit_refuses_the_whole_thing():
    """An industry whose three-year history is too concentrated to measure is not rescued
    by its one-year history being wider. civil_aerospace failed exactly this way."""
    members = ["BIG", "A", "B", "C", "D"]
    rev = {1: {t: (105.0, 100.0) for t in members},
           3: {"BIG": (620.0, 500.0), "A": (100.0, 95.0), "B": (100.0, 95.0),
               "C": (100.0, 95.0), "D": (100.0, 95.0)}}
    r = IG.agreeing_growth("u", members, rev, {1: 0.0, 3: 0.0})
    assert not r["ok"]
    assert "3y window:" in r["reason"] and "BIG" in r["reason"]
    assert r["windows"][1]["ok"] and not r["windows"][3]["ok"]


def test_one_window_cannot_test_its_own_stability():
    import pytest
    with pytest.raises(ValueError):
        IG.agreeing_growth("u", list(_even(5)), {1: _even(5)}, {1: DEFL})


def test_the_headline_is_the_shorter_window_and_every_window_is_kept():
    """The caller reports the agreement, so it needs all of it - an earlier draft returned
    only the winning band and the claim could not say what it agreed with."""
    rev = _win(5, 0.05, 0.045)
    r = IG.agreeing_growth("u", list(rev[1]), rev, {1: 0.0, 3: 0.0})
    assert r["ok"]
    assert r["window_years"] == 1
    assert set(r["windows"]) == {1, 3}
    assert all(r["windows"][w]["ok"] for w in (1, 3))


# ------------------------------------------------------ MAX_SHARE_GROWTH
def test_growth_that_arrived_with_new_shares_is_REFUSED():
    """Real Estate, for real: retail REITs grew revenue 11.5% a year over three years while
    issuing 4.9% a year of new shares, so about 43% of the growth was bought. The assets were
    bought from owners OUTSIDE the listed set, so the listed aggregate grew while the property
    sector did not - and no other guard can see it, because every member is doing the same
    thing, nobody is concentrated, and both windows agree."""
    rev = {t: (111.5, 100.0) for t in "ABCDE"}
    sh = {t: (104.9, 100.0) for t in "ABCDE"}
    r = IG.growth_for_industry("retail_reits", list(rev), rev, deflator=DEFL, shares=sh)
    assert not r["ok"]
    assert "share count grew +4.9% a year" in r["reason"]
    assert "bought, not earned" in r["reason"]
    assert r["share_growth"] > IG.MAX_SHARE_GROWTH


def test_growth_with_a_flat_share_count_passes():
    """hotel_resort_reits and real_estate_services both have share counts flat to negative,
    which is why they are the two Real Estate units that survived."""
    rev = {t: (108.0, 100.0) for t in "ABCDE"}
    sh = {t: (100.1, 100.0) for t in "ABCDE"}
    r = IG.growth_for_industry("u", list(rev), rev, deflator=DEFL, shares=sh)
    assert r["ok"] and r["value"] == "MODERATE"
    assert r["share_growth"] < IG.MAX_SHARE_GROWTH
    assert abs(r["revenue_per_share_growth"] - (1.08 / 1.001 - 1)) < 1e-9


def test_a_buyback_never_counts_as_growth_it_only_fails_to_block_it():
    """The guard is one-sided on purpose. Shrinking the share count does not make revenue
    growth more real, so a buyback must not be allowed to EARN anything - it simply does not
    trip the issuance test. office_reits' share count is -1.7% a year and its growth was
    refused anyway, on the window disagreement."""
    rev = {t: (108.0, 100.0) for t in "ABCDE"}
    sh = {t: (95.0, 100.0) for t in "ABCDE"}
    r = IG.growth_for_industry("u", list(rev), rev, deflator=DEFL, shares=sh)
    assert r["ok"]
    assert r["share_growth"] < 0
    assert r["value"] == "MODERATE"          # the band still comes off REVENUE, not per-share


def test_missing_share_counts_REFUSE_rather_than_skip_the_guard():
    """Graceful degradation here would silently disable the guard for exactly the units whose
    filings are most awkward - the recurring failure mode in this repo."""
    rev = {t: (111.0, 100.0) for t in "ABCDE"}
    sh = {t: (100.0, 100.0) for t in "ABCD"}       # E missing
    r = IG.growth_for_industry("u", list(rev), rev, deflator=DEFL, shares=sh)
    assert not r["ok"]
    assert "share counts are missing for 1 of 5 members" in r["reason"]


def test_the_guard_is_off_when_no_share_data_is_passed_at_all():
    """Callers that predate the guard keep working, and the validation comparisons in the
    module docstring stay reproducible."""
    rev = {t: (111.0, 100.0) for t in "ABCDE"}
    r = IG.growth_for_industry("u", list(rev), rev, deflator=DEFL)
    assert r["ok"]
    assert "share_growth" not in r


def test_agreeing_growth_threads_shares_into_every_window():
    rev = {1: {t: (104.0, 100.0) for t in "ABCDE"},
           3: {t: (104.0, 100.0 / 1.04 ** 2) for t in "ABCDE"}}
    sh = {1: {t: (110.0, 100.0) for t in "ABCDE"},
          3: {t: (110.0, 100.0) for t in "ABCDE"}}
    r = IG.agreeing_growth("u", list("ABCDE"), rev, {1: 0.0, 3: 0.0}, sh)
    assert not r["ok"]
    assert "1y window:" in r["reason"] and "bought, not earned" in r["reason"]
