"""E31: an UNDEFINED quantity is suppressed whether or not arithmetic produces a number.

`resolve_status` grants NOT_APPLICABLE only when the profile nominates the sub-test AND
the value is genuinely absent. That two-part test is load-bearing - UNH is nominally a
FINANCIAL filer and files a full income statement, so its margins are scored - but it
means a suppression whose reason is "meaningless" rather than "missing" almost never
fires: 93.8% of banks carried an interest-coverage score.

E31 adds a second, stronger nomination kind for quantities that **do not exist** for a
filer type, and its bar refused nearly everything. What these tests pin is both halves:
the new rule fires regardless of the value, AND the old rule is untouched, because the
old rule is what protects the framework from a coarse profile assignment.
"""
from __future__ import annotations

import pytest

from clab.fundamentals.profile import PROFILES, MORTGAGE_REIT, FINANCIAL, REIT


def test_an_undefined_metric_is_suppressed_even_when_the_number_exists():
    """The whole point. A mortgage REIT's EV is computable and meaningless."""
    p = PROFILES[MORTGAGE_REIT]
    assert p.is_undefined("va_ev_sales_vs_peers")
    assert p.resolve_status("va_ev_sales_vs_peers", value_present=True) == "not_applicable"


def test_a_MISSING_metric_still_requires_the_value_to_be_absent():
    """The UNH precedent, untouched: a nominated sub-test with a real number is SCORED."""
    p = PROFILES[FINANCIAL]
    assert not p.is_undefined("fe_gross_margin")
    assert p.resolve_status("fe_gross_margin", value_present=True) == "scored"
    assert p.resolve_status("fe_gross_margin", value_present=False) == "not_applicable"


def test_the_subtest_builder_consults_undefined_BEFORE_looking_at_the_value():
    """The mechanism only works if it is checked first - `context.subtest` reaches
    `resolve_status` only on a None value, so a computable number would never get there."""
    from clab.fundamentals.metrics import MetricBundle
    from clab.scoring.context import SymbolContext, subtest

    ctx = SymbolContext(ticker="NLY", cik="1", profile=PROFILES[MORTGAGE_REIT],
                        metrics=MetricBundle())
    st = subtest(ctx, "fe_roic", "ROIC", 2, value=0.31, points=2)
    assert st.status.value == "not_applicable"
    assert st.earned is None, "an undefined metric must not carry points"


def test_an_undefined_metric_leaves_the_coverage_denominator():
    """NOT_APPLICABLE excludes a sub-test from availability, so the filer is scored on
    what it actually has rather than penalised for what it cannot have."""
    from clab.fundamentals.metrics import MetricBundle
    from clab.scoring.context import SymbolContext, subtest
    from clab.scoring.types import ComponentScore

    ctx = SymbolContext(ticker="NLY", cik="1", profile=PROFILES[MORTGAGE_REIT],
                        metrics=MetricBundle())
    sts = [subtest(ctx, "fe_roic", "ROIC", 2, value=0.31, points=2),
           subtest(ctx, "fe_revenue_growth", "Revenue growth", 2, value=0.1, points=1)]
    c = ComponentScore(code="FE", label="FE", max_points=4, subtests=sts)
    assert c.not_applicable_points == 2
    assert c.available_points == 2, "the undefined 2 points must leave availability"
    assert c.earned_points == 1


# ------------------------------------------------------------------ the refusals
@pytest.mark.parametrize("key", [
    "va_ev_sales_vs_peers", "va_ev_ebitda_vs_peers", "bs_interest_coverage",
    "bs_net_debt_ebitda", "fe_roic", "fe_fcf_margin", "fe_margin_expansion",
])
def test_FINANCIAL_admits_NOTHING_as_undefined(key):
    """Every FINANCIAL candidate was refused on P2, and the counter-examples are real:
    the profile holds Visa, Mastercard, CME, S&P Global, ICE and BlackRock, plus Dolby
    (87.6% gross margin) and Alarm.com (65.8%) - companies for which these are the
    PRIMARY metrics. A hard suppression there would delete measured signal on 63 of 192
    filers that are not banks at all."""
    assert not PROFILES[FINANCIAL].is_undefined(key)


def test_REIT_admits_nothing_as_undefined():
    """`fe_margin_expansion` scores for 86.7% of REITs and E29 already ruled the same
    sub-test out for Utilities on the record: a computable margin that is not expanding
    is a TRUE LOW SCORE, not a question with no referent."""
    assert PROFILES[REIT].undefined == frozenset()
    assert PROFILES[REIT].na_candidate("fe_margin_expansion"), "still soft-nominated"


def test_the_admitted_set_is_exactly_the_five_that_were_argued():
    """A guard against quiet growth: every entry needs a written definitional argument
    in E31_undefined_map.md, so the set cannot be extended without that document."""
    assert PROFILES[MORTGAGE_REIT].undefined == frozenset({
        "va_ev_ebitda_vs_peers", "va_ev_sales_vs_peers",
        "bs_net_debt_ebitda", "bs_interest_coverage", "fe_roic",
    })
    others = [n for n, p in PROFILES.items() if p.undefined and n != MORTGAGE_REIT]
    assert others == [], f"undefined entries added without a map document: {others}"


def test_P3_the_redirected_metric_is_actually_available():
    """A profile may suppress ROIC only because it redirects returns to ROE. Suppressing
    it while ROE were also unavailable would delete the returns question entirely."""
    p = PROFILES[MORTGAGE_REIT]
    assert p.returns_metric == "roe"
    assert not p.is_undefined("fe_roe") and not p.na_candidate("fe_roe")


# ------------------------------------------------------------------ the sector veto
# SIC 6700-6799 is "Holding and Other Investment Offices" and holds operating companies
# wearing a financial wrapper: 6792 oil royalty traders, 6794 patent owners and lessors,
# 6795 mineral royalty traders. Measured 2026-08-25, nine companies carried a profile
# whose own note contradicted their stored sector - Dolby, an Application Software filer,
# was being told that gross margin and FCF "are not defined" for it.
def test_a_patent_licensor_is_not_a_bank():
    from clab.fundamentals.profile import profile_for
    assert profile_for("6794", "Information Technology", "Application Software").name \
        == "STANDARD"


def test_an_oil_royalty_trader_is_not_a_bank():
    from clab.fundamentals.profile import profile_for
    assert profile_for("6792", "Energy", "Oil & Gas Exploration & Production").name \
        == "STANDARD"


def test_a_real_bank_keeps_its_profile():
    from clab.fundamentals.profile import profile_for
    assert profile_for("6022", "Financials", "Regional Banks").name == "FINANCIAL"


def test_managed_care_keeps_INSURANCE_across_sectors():
    """UNH files SIC 6324 and sits in GICS Health Care - the veto must be generous
    enough not to break the precedent the whole two-part test was built around."""
    from clab.fundamentals.profile import profile_for
    assert profile_for("6324", "Health Care", "Managed Health Care").name == "INSURANCE"


def test_a_mortgage_reit_survives_the_veto_in_either_sector():
    """GICS files mortgage REITs under both Financials and Real Estate."""
    from clab.fundamentals.profile import profile_for
    for sector in ("Real Estate", "Financials"):
        assert profile_for("6798", sector, "Mortgage REITs").name == "MORTGAGE_REIT"


def test_the_veto_never_invents_a_suppression():
    """It can only fall BACK to STANDARD, which asks every sub-test. A veto that could
    move a filer INTO an archetype would be a way to suppress sub-tests by accident."""
    from clab.fundamentals.profile import PROFILES, profile_for
    assert PROFILES["STANDARD"].not_applicable == frozenset()
    assert PROFILES["STANDARD"].undefined == frozenset()
    assert profile_for("3711", "Consumer Discretionary", "Automobiles").name == "STANDARD"


def test_no_gics_sector_vetoes_nothing():
    """The bare-CIK path has no sector, and absence of evidence must not reclassify."""
    from clab.fundamentals.profile import profile_for
    assert profile_for("6022", None, None).name == "FINANCIAL"
    assert profile_for("6798", None, None).name == "REIT"
