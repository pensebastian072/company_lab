"""Sub-test invariants, the sector profile, stress arithmetic and the reverse DCF."""
from __future__ import annotations

import pytest

from clab.fundamentals import metrics as mx
from clab.fundamentals import profile as pf
from clab.scoring import reverse_dcf, rubric, stress
from clab.scoring.types import Status, SubTest, no_data, not_applicable, scored


# ------------------------------------------------------------------ SubTest
def test_earned_must_be_an_integer():
    with pytest.raises(TypeError):
        SubTest(key="k", label="l", max_points=4, earned=3.7, status=Status.SCORED)


def test_bool_is_not_an_integer_score():
    with pytest.raises(TypeError):
        SubTest(key="k", label="l", max_points=4, earned=True, status=Status.SCORED)


def test_earned_must_be_in_range():
    with pytest.raises(ValueError):
        scored("k", "l", 4, 5)
    with pytest.raises(ValueError):
        scored("k", "l", 4, -1)


def test_scored_status_requires_a_score():
    with pytest.raises(ValueError):
        SubTest(key="k", label="l", max_points=4, earned=None, status=Status.SCORED)


def test_no_data_is_not_a_zero():
    st = no_data("k", "l", 4, "tag absent")
    assert st.earned is None
    assert st.status == Status.NO_DATA
    assert st.effective is None
    zero = scored("k", "l", 4, 0)
    assert zero.earned == 0 and zero.status == Status.SCORED
    assert st.status != zero.status


def test_override_wins_when_set():
    st = scored("k", "l", 4, 1)
    assert st.effective == 1
    st.override = 4
    assert st.effective == 4


def test_llm_provenance_is_detectable():
    assert scored("k", "l", 4, 2, provenance={"source": "llm"}).is_llm
    assert not scored("k", "l", 4, 2, provenance={"source": "edgar"}).is_llm


# ------------------------------------------------------------------ profile
def test_sic_maps_to_profiles():
    """Updated 2026-08-17: REIT_UTILITY was split, and insurers got their own name.

    6331 used to answer FINANCIAL. INSURANCE currently suppresses exactly the same
    sub-tests, so nothing about an insurer's score changes today - the split exists so
    the two can diverge (combined ratio, book-value growth) without re-labelling every
    bank at that point.
    """
    assert pf.profile_for_sic("6021").name == pf.FINANCIAL     # national bank
    assert pf.profile_for_sic("6331").name == pf.INSURANCE     # insurer
    assert pf.profile_for_sic("6798").name == pf.REIT          # equity REIT
    assert pf.profile_for_sic("6512").name == pf.REIT          # real-estate operator
    assert pf.profile_for_sic("4911").name == pf.UTILITY       # electric utility
    assert pf.profile_for_sic("3571").name == pf.STANDARD      # computers
    assert pf.profile_for_sic(None).name == pf.STANDARD
    assert pf.profile_for_sic("nonsense").name == pf.STANDARD


def test_insurance_suppresses_no_less_than_financial_did():
    """The split must not accidentally start scoring a bank sub-test on an insurer."""
    fin = pf.PROFILES[pf.FINANCIAL].not_applicable
    ins = pf.PROFILES[pf.INSURANCE].not_applicable
    assert fin <= ins


def test_sub_industry_separates_a_mortgage_reit_from_an_equity_reit():
    """Both file SIC 6798. One owns buildings, the other is a levered bond book."""
    assert pf.profile_for("6798", "Real Estate", "Mortgage REITs").name == pf.MORTGAGE_REIT
    assert pf.profile_for("6798", "Real Estate", "Industrial REITs").name == pf.REIT


def test_a_real_estate_company_no_longer_falls_through_to_STANDARD():
    """TRNO, EFC, JLL and 7 others were scored as though they were manufacturers."""
    assert pf.profile_for("6512", "Real Estate").name == pf.REIT
    assert pf.profile_for(None, "Real Estate").name == pf.REIT
    assert pf.profile_for(None, "Utilities").name == pf.UTILITY


def test_the_threshold_override_hook_defaults_to_the_rubric():
    """The mechanism exists; no profile sets a band yet, and inventing one without a
    backtest is what this repo refuses to do."""
    p = pf.PROFILES[pf.REIT]
    assert p.bands("FE_ROIC_BANDS", (0.20, 0.12, 0.08, 0.04)) == (0.20, 0.12, 0.08, 0.04)
    assert all(not prof.thresholds for prof in pf.PROFILES.values())


def test_na_requires_both_nomination_and_absence():
    """The rule that stops a SIC code throwing away real data. UNH is SIC 6324
    (nominally FINANCIAL) but files gross profit, capex and current assets."""
    fin = pf.PROFILES[pf.FINANCIAL]
    assert fin.resolve_status("fe_gross_margin", value_present=True) == "scored"
    assert fin.resolve_status("fe_gross_margin", value_present=False) == "not_applicable"
    # a sub-test the profile does not nominate is missing data, not n/a
    assert fin.resolve_status("fe_revenue_growth", value_present=False) == "no_data"


def test_standard_profile_nominates_nothing():
    std = pf.PROFILES[pf.STANDARD]
    for key in ("fe_gross_margin", "bs_current_ratio", "va_reverse_dcf"):
        assert std.resolve_status(key, value_present=False) == "no_data"


def test_reit_relaxes_leverage():
    assert pf.PROFILES[pf.REIT_UTILITY].leverage_multiplier > 1.0
    assert pf.PROFILES[pf.STANDARD].leverage_multiplier == 1.0


# ------------------------------------------------------------------ stress
class FakeBundle:
    def __init__(self, **vals):
        self._v = vals

    def raw(self, k):
        return self._v.get(k)


def healthy(**over):
    v = dict(revenue_ttm=1000.0, operating_margin=0.30, dep_amort_ttm=50.0,
             capex_ttm=60.0, interest_expense_ttm=10.0, effective_tax_rate=0.21,
             cash_sti=500.0, net_debt=-200.0)
    v.update(over)
    return FakeBundle(**v)


def test_stress_arithmetic_matches_hand_calculation():
    sim = stress.simulate(healthy())
    s = sim["simulated"]
    assert s["revenue"] == pytest.approx(800.0)          # -20%
    assert s["operating_margin"] == pytest.approx(0.225)  # 0.30 x (1 - 0.25) RELATIVE
    assert s["operating_income"] == pytest.approx(180.0)
    assert s["interest_expense"] == pytest.approx(15.0)   # +50%
    assert s["ebitda"] == pytest.approx(230.0)
    assert s["capex"] == pytest.approx(42.0)              # -30%
    assert s["fcf"] == pytest.approx(180.0 * 0.79 + 50.0 - 42.0 - 15.0)
    assert sim["verdict"] == stress.SURVIVES_COMFORTABLY
    assert sim["points"] == 2


def test_margin_haircut_is_relative_not_absolute():
    """rubric A6: absolute would take a 30% margin to 5% and drive most of the
    index to a non-discriminating zero."""
    sim = stress.simulate(healthy(operating_margin=0.40))
    assert sim["simulated"]["operating_margin"] == pytest.approx(0.30)


def test_stress_stressed_is_a_real_zero_not_missing():
    sim = stress.simulate(healthy(operating_margin=0.04, interest_expense_ttm=200.0,
                                  net_debt=5000.0, cash_sti=1.0))
    assert sim["verdict"] == stress.STRESSED
    assert sim["points"] == 0


def test_stress_missing_input_is_no_data_not_stressed():
    for missing in ("operating_margin", "revenue_ttm", "dep_amort_ttm", "capex_ttm"):
        sim = stress.simulate(healthy(**{missing: None}))
        assert sim["verdict"] == stress.NO_DATA
        assert sim["points"] is None
        assert missing in sim["missing"]


def test_stress_middle_band():
    sim = stress.simulate(healthy(operating_margin=0.08, interest_expense_ttm=40.0,
                                  net_debt=600.0, cash_sti=300.0, capex_ttm=40.0))
    assert sim["verdict"] in (stress.SURVIVES, stress.STRESSED)
    assert sim["points"] in (0, 1)


# ------------------------------------------------------------------ reverse DCF
def test_dcf_is_monotone_in_growth():
    ev_low = reverse_dcf.enterprise_value(100.0, 0.02, 0.09)
    ev_high = reverse_dcf.enterprise_value(100.0, 0.20, 0.09)
    assert ev_high > ev_low


def test_dcf_is_monotone_in_wacc():
    assert reverse_dcf.enterprise_value(100.0, 0.08, 0.07) > \
        reverse_dcf.enterprise_value(100.0, 0.08, 0.12)


def test_implied_growth_round_trips():
    wacc = 0.09
    for g in (0.0, 0.05, 0.12, 0.25):
        ev = reverse_dcf.enterprise_value(100.0, g, wacc)
        assert reverse_dcf.implied_growth(ev, 100.0, wacc) == pytest.approx(g, abs=2e-3)


def test_implied_growth_none_on_non_positive_fcf():
    """A pre-FCF company must not be scored as cheap or expensive."""
    assert reverse_dcf.implied_growth(1e9, 0.0, 0.09) is None
    assert reverse_dcf.implied_growth(1e9, -50.0, 0.09) is None


def test_wacc_is_clamped_and_flags_assumptions():
    w, prov = reverse_dcf.wacc_for(beta=None, risk_free=None)
    assert rubric.DCF_WACC_FLOOR <= w <= rubric.DCF_WACC_CEIL
    assert prov["beta_assumed"] and prov["risk_free_assumed"] and prov["assumed"]

    w_hi, prov_hi = reverse_dcf.wacc_for(beta=5.0, risk_free=0.05)
    assert w_hi == rubric.DCF_WACC_CEIL and prov_hi["clamped"]


def test_growth_path_fades_to_terminal():
    path = reverse_dcf._growth_path(0.20, rubric.DCF_YEARS)
    assert len(path) == rubric.DCF_YEARS
    assert path[0] == pytest.approx(0.20)
    assert path[-1] == pytest.approx(rubric.DCF_TERMINAL_GROWTH)
    assert path == sorted(path, reverse=True)


# ------------------------------------------------------------------ metrics guards
def test_coverage_is_capped_never_infinite():
    """inf does not survive JSON, parquet or CSV round-trips."""
    assert mx.COVERAGE_CAP == 999.0


def test_band_helpers():
    assert rubric.band_from_thresholds(0.25, (0.20, 0.12), (2, 1, 0)) == 2
    assert rubric.band_from_thresholds(0.15, (0.20, 0.12), (2, 1, 0)) == 1
    assert rubric.band_from_thresholds(0.01, (0.20, 0.12), (2, 1, 0)) == 0
    assert rubric.band_from_thresholds(None, (0.20,), (1, 0)) is None
    # ascending: lower is better
    assert rubric.band_from_thresholds_asc(0.5, (1.0, 2.0), (2, 1, 0)) == 2
    assert rubric.band_from_thresholds_asc(3.0, (1.0, 2.0), (2, 1, 0)) == 0
    assert rubric.band_from_thresholds_asc(None, (1.0,), (1, 0)) is None


def test_pharma_is_not_biotech():
    """SIC 2834 covers Eli Lilly AND a clinical-stage startup.

    Mapping it to BIOTECH tagged LLY ($1.05T), JNJ, MRK, PFE and BMY as biotechs - 28 of
    60 assignments on 2026-08-17. BIOTECH suppresses PEG, P/FCF and the reverse DCF,
    which are meaningless for a pre-revenue filer and perfectly meaningful for a
    profitable mega-cap pharma. The two-part rule meant no score was actually wrong, but
    the label would have mis-banded them the moment BIOTECH carries its own thresholds.
    """
    assert pf.profile_for_sic("2834").name == pf.STANDARD      # pharma preparations
    assert pf.profile_for_sic("2836").name == pf.STANDARD      # biological products
    assert pf.profile_for_sic("8731").name == pf.BIOTECH       # research services


def test_biotech_comes_from_the_sub_industry_not_the_sic():
    """GICS "Biotechnology" is the precise signal and it is checked first."""
    assert pf.profile_for("2834", "Health Care", "Biotechnology").name == pf.BIOTECH
    assert pf.profile_for("2834", "Health Care", "Pharmaceuticals").name == pf.STANDARD
    assert pf.profile_for("3841", "Health Care", "Health Care Equipment").name == pf.STANDARD
