"""Sector profiles - which sub-tests are meaningful for which kind of filer.

The problem this solves is measured, not theoretical. JPM's companyfacts has no
GrossProfit, no OperatingIncomeLoss, no AssetsCurrent/LiabilitiesCurrent, no
capex tag and no R&D. XOM lacks GrossProfit and OperatingIncomeLoss. For a bank,
gross margin and FCF conversion are not merely missing - they are meaningless.

That is ~70 S&P 500 names (14%). Scoring them NO_DATA would drop their coverage
below the 0.80 band gate and render the entire financial sector permanently
unrankable. So those sub-tests are marked NOT_APPLICABLE, which excludes them
from both the numerator and the coverage denominator: the bank is honestly
scored on ~82 applicable points and the scorecard says so.

Sector comes from the SIC code in the EDGAR submissions feed - authoritative and
free - never from yfinance info["sector"], which is a scraped field that changes
shape without notice.
"""
from __future__ import annotations

from dataclasses import dataclass, field

STANDARD = "STANDARD"
FINANCIAL = "FINANCIAL"
#: kept as an alias so old scorecards and the E02-E13 panels stay readable
REIT_UTILITY = "REIT_UTILITY"
REIT = "REIT"
MORTGAGE_REIT = "MORTGAGE_REIT"
UTILITY = "UTILITY"
INSURANCE = "INSURANCE"
BIOTECH = "BIOTECH"


@dataclass(frozen=True)
class SectorProfile:
    name: str
    #: sub-test keys that MAY be meaningless for this filer type - candidates only.
    #: Suppressed ONLY when the value is also genuinely absent (see `resolve_status`).
    not_applicable: frozenset = field(default_factory=frozenset)
    #: sub-test keys naming a quantity that DOES NOT EXIST for this filer type, suppressed
    #: whether or not arithmetic can produce a number (E31, 2026-08-25). The distinction
    #: is "undefined" versus "missing": a REIT that happens to file a gross profit line has
    #: a meaningful gross margin, but a mortgage REIT's enterprise value is not a small
    #: number or a missing one - EV is market cap plus net debt, and for a levered bond
    #: book the debt IS the strategy, so the quantity EV is defined to measure does not
    #: exist. E31's bar is deliberately severe and almost nothing cleared it: ONE company
    #: carrying the profile for which a domain reader would call the metric meaningful
    #: refuses the entry, because `not_applicable` already handles the mixed case.
    undefined: frozenset = field(default_factory=frozenset)
    #: metric name -> replacement chain key in tags.CHAINS
    revenue_metric: str = "revenue"
    #: relax leverage thresholds where high debt is structural
    leverage_multiplier: float = 1.0
    #: prefer ROE over ROIC as the returns measure
    returns_metric: str = "roic"
    #: rubric constant name -> replacement bands, e.g. {"FE_GROSS_MARGIN_BANDS": (...)}.
    #: The archetype hook the first three profiles never had: until now a profile could
    #: only SUPPRESS a sub-test, never re-band one, because every threshold was a
    #: module-level constant read directly by the scorers. Empty for every profile today
    #: - the mechanism exists, the calibration does not, and inventing thresholds without
    #: a backtest is exactly what this repo refuses to do.
    thresholds: dict = field(default_factory=dict)
    note: str = ""

    def bands(self, name: str, default):
        """Per-archetype threshold override, falling back to the rubric constant."""
        return self.thresholds.get(name, default)

    def na_candidate(self, subtest_key: str) -> bool:
        return subtest_key in self.not_applicable or subtest_key in self.undefined

    def is_undefined(self, subtest_key: str) -> bool:
        """The quantity does not exist for this filer, whatever the arithmetic produces."""
        return subtest_key in self.undefined

    def resolve_status(self, subtest_key: str, value_present: bool) -> str:
        """"scored" | "not_applicable" | "no_data" for one sub-test.

        NOT_APPLICABLE requires BOTH that the profile nominates the sub-test AND
        that the underlying number is genuinely absent. That second condition
        matters: UNH is SIC 6324 (Hospital & Medical Service Plans, so nominally a
        FINANCIAL filer) but files a full ordinary income statement with gross
        profit, capex, current assets and operating income. Suppressing those
        sub-tests on the SIC code alone would throw away real, measured signal on
        a large company. Conversely a filer that genuinely has no such line - JPM,
        XOM - gets NOT_APPLICABLE and keeps its coverage intact.
        """
        if self.is_undefined(subtest_key):
            return "not_applicable"
        if value_present:
            return "scored"
        return "not_applicable" if self.na_candidate(subtest_key) else "no_data"

    # kept for readability at call sites that only care about nomination
    def applies(self, subtest_key: str) -> bool:
        return subtest_key not in self.not_applicable


PROFILES: dict[str, SectorProfile] = {
    STANDARD: SectorProfile(
        name=STANDARD,
        note="All framework sub-tests apply.",
    ),
    FINANCIAL: SectorProfile(
        name=FINANCIAL,
        not_applicable=frozenset({
            # income statement shape
            "fe_gross_margin",
            "fe_operating_margin",
            "fe_fcf_margin",
            "fe_fcf_growth",
            "fe_roic",
            "fe_margin_expansion",
            # balance sheet: a bank's "current ratio" and "debt/EBITDA" mean
            # nothing - deposits are funding, not leverage in the covenant sense,
            # and interest expense is cost of goods, not a solvency burden
            "bs_current_ratio",
            "bs_net_debt_ebitda",
            "bs_interest_coverage",
            "bs_stress_test",
            "bs_cash_vs_opex",
            # valuation: EV is not defined for a bank
            "va_ev_ebitda_vs_peers",
            "va_ev_sales_vs_peers",
            "va_reverse_dcf",
        }),
        returns_metric="roe",
        note=("Bank / insurer / capital-markets filer: gross margin, FCF, EV and "
              "covenant leverage are not defined. ROE carries the returns weight; "
              "Tier-1 capital substitutes for leverage where tagged."),
    ),
    # Kept under its old name and its old (narrow) suppression set so scorecards and
    # panels written before 2026-08-17 still resolve. New assignments never land here.
    REIT_UTILITY: SectorProfile(
        name=REIT_UTILITY,
        not_applicable=frozenset({
            "fe_fcf_growth",
            "fe_fcf_margin",
        }),
        leverage_multiplier=1.8,
        note=("Superseded by REIT and UTILITY on 2026-08-17. Retained so older "
              "scorecards remain readable; nothing is assigned to it now."),
    ),
    # Measured 2026-08-17 across 166 REIT_UTILITY companies: mean coverage 0.668 against
    # 0.787 for STANDARD, the worst of any profile. The cause was a 2-key suppression set
    # against a filer type that genuinely lacks eight of these lines - `fe_gross_margin`
    # was NO_DATA for 13 of 14 REITs and utilities sampled. Those points were being
    # counted as data we failed to find rather than as questions that do not apply, which
    # dragged the whole property sector under the 0.80 band gate.
    #
    # Nominating generously is SAFE here and that is the point of `resolve_status`:
    # NOT_APPLICABLE still requires the number to be genuinely absent, so a REIT that
    # does file a gross profit line is scored on it (the UNH precedent).
    REIT: SectorProfile(
        name=REIT,
        not_applicable=frozenset({
            # a REIT reports rental revenue and property operating expense; there is no
            # gross profit line and no cost of goods
            "fe_gross_margin",
            "fe_margin_expansion",
            # capex is acquisition and redevelopment, not maintenance, so FCF is not the
            # cash measure - FFO/AFFO is
            "fe_fcf_growth",
            "fe_fcf_margin",
            "va_p_fcf",
            "va_reverse_dcf",
            "mg_reinvestment_quality",
            "mg_buyback_discipline",
            # REITs file an unclassified balance sheet: no current assets/liabilities
            "bs_current_ratio",
        }),
        leverage_multiplier=1.8,
        note=("Equity REIT: FFO rather than FCF, an unclassified balance sheet, and "
              "structurally high mortgage leverage. Suppressed sub-tests are the ones "
              "the filing genuinely does not contain."),
    ),
    # E31 admitted FIVE entries and they are ALL here, because a mortgage REIT is the
    # only homogeneous bucket in this file: all 9 members are GICS "Mortgage REITs", so
    # there is no company for which a domain reader would call these metrics meaningful.
    # Every FINANCIAL and INSURANCE candidate was REFUSED on that same test - FINANCIAL
    # holds Visa, Mastercard, CME, S&P Global, ICE, BlackRock and even Dolby, for which
    # gross margin, FCF, EV and ROIC are the PRIMARY metrics. See
    # `journal/experiments/E31_undefined_map.md`.
    MORTGAGE_REIT: SectorProfile(
        name=MORTGAGE_REIT,
        undefined=frozenset({
            # EV = market cap + net debt - cash. For a levered bond book the debt IS the
            # strategy and the cash is collateral, so the quantity EV is defined to
            # measure does not exist. P/B and dividend yield are the multiples used here.
            "va_ev_ebitda_vs_peers",
            "va_ev_sales_vs_peers",
            # EBITDA is not defined for it either: interest is the cost of revenue, and
            # there is no operating income before D&A to speak of.
            "bs_net_debt_ebitda",
            # coverage = EBIT / interest expense is a FIXED-CHARGE test. Repo interest is
            # this filer's cost of goods, not a fixed charge its earnings must clear.
            "bs_interest_coverage",
            # ROIC = NOPAT / (debt + equity - cash). Invested capital so defined is the
            # portfolio, not capital employed. The profile already redirects returns to
            # ROE, and `fe_roe` is scored for 100% of these filers - E31's P3.
            "fe_roic",
        }),
        not_applicable=frozenset({
            "fe_gross_margin", "fe_operating_margin", "fe_margin_expansion",
            "fe_fcf_growth", "fe_fcf_margin", "fe_roic",
            "bs_current_ratio", "bs_net_debt_ebitda", "bs_interest_coverage",
            "bs_stress_test", "bs_cash_vs_opex", "bs_maturity_wall",
            "va_ev_ebitda_vs_peers", "va_ev_sales_vs_peers", "va_p_fcf",
            "va_reverse_dcf",
            "mg_reinvestment_quality", "mg_buyback_discipline",
        }),
        returns_metric="roe",
        leverage_multiplier=3.0,
        note=("Mortgage REIT: a levered bond portfolio wearing a REIT wrapper. Its "
              "leverage IS the strategy and its 'margin' is a net interest spread, so "
              "the operating-company sub-tests do not describe it at all."),
    ),
    UTILITY: SectorProfile(
        name=UTILITY,
        not_applicable=frozenset({
            # revenue less fuel and purchased power is not a gross margin
            "fe_gross_margin",
            # rate-base capex is mandated by the regulator, not chosen by management
            "fe_fcf_growth",
            "fe_fcf_margin",
            "mg_reinvestment_quality",
            "mg_buyback_discipline",
            "va_p_fcf",
            "va_reverse_dcf",
        }),
        leverage_multiplier=1.8,
        note=("Regulated utility: returns are set by a regulator and capex is mandated, "
              "so discretionary-capital-allocation and FCF sub-tests do not apply."),
    ),
    INSURANCE: SectorProfile(
        name=INSURANCE,
        not_applicable=frozenset({
            "fe_gross_margin", "fe_operating_margin", "fe_fcf_margin", "fe_fcf_growth",
            "fe_roic", "fe_margin_expansion",
            "bs_current_ratio", "bs_net_debt_ebitda", "bs_interest_coverage",
            "bs_stress_test", "bs_cash_vs_opex",
            "va_ev_ebitda_vs_peers", "va_ev_sales_vs_peers", "va_reverse_dcf",
        }),
        returns_metric="roe",
        note=("Insurer: float is a liability that funds an investment portfolio, so "
              "margin, EV and covenant leverage do not describe the business. Combined "
              "ratio and book-value growth are the right measures and are not yet "
              "implemented - that gap is honest NO_DATA, not a suppression."),
    ),
    BIOTECH: SectorProfile(
        name=BIOTECH,
        not_applicable=frozenset({
            # pre-revenue and early-commercial filers: these are not weak scores, they
            # are undefined ratios
            "va_peg",
            "va_p_fcf",
            "va_reverse_dcf",
        }),
        note=("Clinical-stage or early-commercial biotech: earnings-based multiples are "
              "undefined against negative or negligible earnings. NOTE the sub-tests "
              "that SHOULD exist here - pipeline stage, patent cliff, trial risk, "
              "revenue concentration - do not, so a biotech's score still says less "
              "than its number suggests. EXEL scores 95.7 normalized quant on ROIC and "
              "P/FCF with none of its actual risks represented."),
    ),
}


def profile_for_sic(sic: str | None) -> SectorProfile:
    """Map a 4-digit SIC code to a profile.

    6798 was previously the ONLY code routed to a REIT profile, so the real-estate
    operating and management codes in the 6500s fell through to STANDARD - measured
    2026-08-17, that left 10 Real Estate companies (TRNO, EFC, JLL, JOE...) scored as
    though they were manufacturers.
    """
    if not sic:
        return PROFILES[STANDARD]
    try:
        code = int(str(sic).strip()[:4])
    except (TypeError, ValueError):
        return PROFILES[STANDARD]
    if code == 6798:
        return PROFILES[REIT]
    if 6500 <= code <= 6599:                 # real estate operators, lessors, agents
        return PROFILES[REIT]
    if 6311 <= code <= 6411:                 # life, health, P&C, title, brokers
        return PROFILES[INSURANCE]
    if 6000 <= code <= 6499 or 6700 <= code <= 6799:
        return PROFILES[FINANCIAL]
    if 4900 <= code <= 4949:
        return PROFILES[UTILITY]
    # NOT 2834 (Pharmaceutical Preparations). That code covers Eli Lilly and a
    # clinical-stage startup alike, and mapping it to BIOTECH tagged LLY ($1.05T), JNJ,
    # MRK, PFE and BMY as biotechs - 28 of the 60 assignments. BIOTECH suppresses PEG,
    # P/FCF and the reverse DCF, which are meaningless for a pre-revenue filer and
    # perfectly meaningful for a profitable mega-cap pharma.
    #
    # The GICS "Biotechnology" sub-industry is checked first in profile_for() and is the
    # precise signal; 8731 (commercial physical and biological research) is kept as the
    # SIC fallback for filers with no sub-industry. Nothing else routes here on SIC.
    if code == 8731:
        return PROFILES[BIOTECH]
    return PROFILES[STANDARD]


#: GICS sub-industries that identify a filer more precisely than its SIC code does.
#: A mortgage REIT and an equity REIT share SIC 6798 and are not the same business.
_SUB_INDUSTRY_PROFILES = {
    "mortgage reits": MORTGAGE_REIT,
    "mortgage real estate investment trusts (reits)": MORTGAGE_REIT,
    "biotechnology": BIOTECH,
    "life sciences tools & services": STANDARD,
    "insurance brokers": INSURANCE,
    "life & health insurance": INSURANCE,
    "property & casualty insurance": INSURANCE,
    "reinsurance": INSURANCE,
    "multi-line insurance": INSURANCE,
}


#: GICS sectors compatible with each archetype. A profile whose stored sector is not here
#: is describing a legal wrapper rather than the business, and falls back to STANDARD.
#: Deliberately generous - INSURANCE spans Financials AND Health Care (managed care files
#: SIC 6324), MORTGAGE_REIT spans both sectors GICS puts mortgage REITs in, and UTILITY
#: covers the independent power producers GICS files under Energy.
_SECTORS_FOR_PROFILE = {
    FINANCIAL: {"financials", "financial services"},
    INSURANCE: {"financials", "financial services", "health care"},
    MORTGAGE_REIT: {"real estate", "financials", "financial services"},
    REIT: {"real estate"},
    REIT_UTILITY: {"real estate", "utilities"},
    UTILITY: {"utilities", "energy"},
    BIOTECH: {"health care"},
}


def profile_for(sic: str | None, gics_sector: str | None = None,
                sub_industry: str | None = None) -> SectorProfile:
    """SIC is authoritative; sub-industry refines it; GICS sector is the last fallback.

    Sub-industry is consulted BEFORE the SIC result is returned, because it is the only
    thing that separates a mortgage REIT from an equity REIT - both file SIC 6798, and
    one is a levered bond book while the other owns buildings.
    """
    si = (sub_industry or "").strip().lower()
    if si in _SUB_INDUSTRY_PROFILES:
        return PROFILES[_SUB_INDUSTRY_PROFILES[si]]

    prof = profile_for_sic(sic)

    # E31 follow-on, 2026-08-25: the GICS sector VETOES a SIC-derived archetype it
    # plainly contradicts. SIC 6700-6799 is "Holding and Other Investment Offices" and
    # contains operating companies wearing a financial wrapper - 6792 oil royalty traders
    # (Texas Pacific Land), 6794 patent owners and lessors (Dolby, InterDigital), 6795
    # mineral royalty traders (Royal Gold) - none of which is a financial institution.
    # Measured that day: 9 companies carried a profile whose own note contradicted their
    # stored sector, Dolby being an Application Software filer told that gross margin and
    # FCF "are not defined" for it.
    #
    # This only ever falls BACK to STANDARD, which asks every sub-test; it cannot invent
    # a suppression. An absent `gics_sector` (the bare-CIK path) vetoes nothing.
    if gics_sector and prof.name != STANDARD:
        allowed = _SECTORS_FOR_PROFILE.get(prof.name)
        if allowed and gics_sector.strip().lower() not in allowed:
            return PROFILES[STANDARD]

    if prof.name != STANDARD or not gics_sector:
        return prof
    g = gics_sector.strip().lower()
    if g in ("financials", "financial services"):
        return PROFILES[FINANCIAL]
    if g == "real estate":
        return PROFILES[REIT]
    if g == "utilities":
        return PROFILES[UTILITY]
    return prof
