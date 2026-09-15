"""Every scoring threshold and every framework-ambiguity resolution, in one place.

The 100-point framework is the user's and is implemented exactly: the eight
component maxima below are fixed. What the framework does NOT specify - how the
points inside a component divide, what "margins -25%" means, how 11 moat
dimensions map to 15 points - is resolved here rather than buried across eight
modules, so a disagreement is a one-line edit and not an archaeology project.

Each resolution is labelled with its ambiguity id (A1..A10) so it can be traced
back to the design discussion.
"""
from __future__ import annotations

# ------------------------------------------------------------------ components
# code -> (label, max_points).  Weight on the normalized sub-score == max/100,
# so the raw point sum IS the composite. tests/test_weights.py pins that.
# Weights v2, 2026-08-10. Changed from the original 15/5 split between FE and EN on
# the evidence of two independent pre-registered studies:
#
#   E01  signal entries underperformed random entries in the same names
#   E02  EN had the most negative IC of the four measured components (-0.033,
#        positive in only 39% of months) while FE had the most positive (+0.025)
#
# So 3 points move from Entry to Financial Engine. EN is cut to 2 rather than 0
# deliberately: the 2016-2025 window contains no prolonged bear market, so it cannot
# test what EN protects against, and deleting a risk-management rule on one
# bull-market decade would be overfitting to the sample.
COMPONENTS: dict[str, tuple[str, int]] = {
    "SG": ("Structural Growth", 20),
    "BQ": ("Business Quality & Moat", 15),
    "FE": ("Financial Engine", 18),
    "MG": ("Management & Capital Allocation", 9),
    "BS": ("Balance Sheet & Survivability", 10),
    "VA": ("Valuation", 15),
    "ER": ("Expectations vs Reality", 5),
    "EN": ("Entry Opportunity", 2),
}
# E26: 94, not 100. The CEO block shrank to the two measured attributes it
# still asks (2 points, down from 8), and the framework should say how many
# questions it asks rather than carry six points it no longer poses. The band
# score is normalised to 100 separately - see composite.selection_score.
TOTAL_POINTS = 94
COMPONENT_ORDER = ("SG", "BQ", "FE", "MG", "BS", "VA", "ER", "EN")
# Three lists, because "which components does the model generate" and "which points are
# model judgement" stopped being the same question at E25 and the code kept one name for
# both for two experiments afterwards.
#
# THE CORRECTION (V3 P0, measured before it was made): MG is 100% MEASURED at runtime.
# E25 removed the five model-scored CEO attributes and E26 cut the block 8 -> 2, so
# MG_CEO_ATTRIBUTES now carries source "data" for both survivors, mg._LLM_ATTRS is an
# EMPTY tuple, every sub-test comes back source=edgar, ComponentScore.is_llm is False,
# and every LFM2.5 MG payload on disk carries `ceo = {}`. The only thing MG still takes
# from the model is a display-only `ceo_summary` string used as the block's rationale.
# Nevertheless MG stayed in the judged list, so its 9 measured points were counted as
# judgement and excluded from quant_only_50 / quant_normalized / quant_band. The
# docstrings said "9.4 of MG's 15 points are measured and 5.6 are model judgement" -
# stale by two experiments and two component-size changes.
#
# The honest split is 59 measured / 35 judged. See journal/experiments/mg_label_correction.md.

#: What the score treats as model judgement. SG 20 + BQ 15 = 35.
JUDGED_COMPONENTS = ("SG", "BQ")
#: What the score treats as measured. FE 18 + MG 9 + BS 10 + VA 15 + ER 5 + EN 2 = 59.
MEASURED_COMPONENTS = ("FE", "MG", "BS", "VA", "ER", "EN")
#: What the qual pipeline GENERATES a payload for. MG is here and not in
#: JUDGED_COMPONENTS on purpose: the model still writes MG's `ceo_summary` rationale,
#: it just no longer scores any of MG's points. Dropping MG here would silently delete
#: that rationale from every scorecard.
GENERATED_COMPONENTS = ("SG", "BQ", "MG")


def points_in(components: tuple[str, ...]) -> int:
    """Total max points across a set of component codes.

    E33: every user-facing label derives from this rather than carrying a literal. The
    framework went 100 -> 94 at E26 and the explanatory text did not follow, so the
    workbook was still telling readers "50 of 100 points" months later. A label that
    restates a number the code already knows will drift from it; one that asks cannot.
    `tests/test_label_drift.py` fails the build if a literal comes back.
    """
    return sum(COMPONENTS[c][1] for c in components if c in COMPONENTS)


#: 35 judged (SG 20 + BQ 15) against 59 measured (FE 18 + MG 9 + BS 10 + VA 15 + ER 5 + EN 2).
JUDGED_POINTS = points_in(JUDGED_COMPONENTS)
MEASURED_POINTS = points_in(MEASURED_COMPONENTS)

# ------------------------------------------------------------------ bands
BANDS = (
    (90, "EXCEPTIONAL"),
    (80, "HIGH_CONVICTION"),
    (70, "INVESTABLE"),
    (60, "WATCHLIST"),
    (50, "WEAK"),
    (0, "REJECT"),
)
# Assigning "High Conviction" to a company scored on 60% of the framework would
# be the most dangerous thing this system could do. Below this coverage it
# refuses to label at all.
MIN_COVERAGE_FOR_BAND = 0.80
INSUFFICIENT_BAND = "INSUFFICIENT_DATA"

# ------------------------------------------------------------------ SG /20 (LLM)
# Sub-test allocation is the user's, taken verbatim from the framework.
SG_SUBTESTS = (
    ("tam_expanding", "Industry TAM expanding rapidly", 4),
    ("revenue_growth_sustainable", "Revenue growth accelerating / sustainable", 4),
    ("demand_drivers_3_5yr", "Clear 3-5 year demand drivers", 4),
    ("capacity_backlog_contracts", "Capacity / backlog / contracts support growth", 3),
    ("secular_not_cyclical", "Secular rather than cyclical-only growth", 3),
    ("multiple_independent_drivers", "Multiple independent growth drivers", 2),
)

# ------------------------------------------------------------------ BQ /15 (LLM)
# A2: the framework scores 11 moat dimensions 0-5 (55 raw) into a 15-point
# component without saying how. Resolution: MEAN of the scored dimensions,
# rescaled to 15. Mean not sum, because a business with two overwhelming moats
# (network effects + switching costs) should not rank below one with eleven weak
# ones - a sum punishes focus. All 11 raw scores are stored and displayed so the
# user can rescore from raw if they disagree.
BQ_DIMENSIONS = (
    ("technological_advantage", "Technological advantage"),
    ("economies_of_scale", "Economies of scale"),
    ("switching_costs", "Switching costs"),
    ("network_effects", "Network effects"),
    ("intellectual_property", "Intellectual property"),
    ("brand", "Brand"),
    ("regulatory_barriers", "Regulatory barriers"),
    ("manufacturing_complexity", "Manufacturing complexity"),
    ("distribution", "Distribution"),
    ("customer_relationships", "Customer relationships"),
    ("data_advantages", "Data advantages"),
)
BQ_DIMENSION_MAX = 5
BQ_MIN_DIMENSIONS_SCORED = 6      # E19: a REPORTING threshold, no longer a cliff.
#: Below it the component used to be worth ZERO; it is now assessed on the share of
#: dimensions the filing supported (see clab/scoring/bq.py). Kept because the
#: workbook and the fold still report 'thinly assessed' against it.
# The killer question carries no points but is the most useful line on the page.
BQ_KILLER_QUESTION = "If this industry doubles, why does THIS company win?"

# ------------------------------------------------------------------ MG /15 (LLM+data)
# A3: 7 CEO attributes into 8 points, no allocation given. Resolution: each
# attribute 0-2 (14 raw) -> round(raw/14*8). Two of the seven are genuinely
# measurable - guidance hit-rate from the earnings surprise history, and
# downturn navigation from the 2008/2020 revenue+margin drawdowns in EDGAR - so
# those are computed from data and the LLM scores only the other five. That
# moves ~2.3 points from opinion to evidence at no cost.
# E25: the five model-scored attributes are gone. The block is fully MEASURED.
#
# E22 put MG's year-over-year stability at 0.29 against a 0.5 bar. E24 tested the obvious
# excuse - that founder_led, tenure and ownership are DEF 14A facts and the pack held only
# the 10-K - by putting the proxy in MG's pack. It fixed AVAILABILITY outright (ownership
# 4 -> 163 companies scored, tenure 4 -> 139) and did not fix RELIABILITY: stability rose
# only to 0.405.
#
# Tenure settles it. How long a CEO has served increments by one a year, is stated plainly
# in the proxy, and the model reproduced it twelve months apart at kappa 0.29. That is not
# a missing document; it is the model failing to extract a fact it was handed.
#
# The proxy machinery stays (`evidence.proxy_pool`, `edgar_filings.proxy_text`) - it works
# and it is tested. It is simply not a fix for this.
MG_CEO_ATTRIBUTES = (
    ("hits_guidance", "Hits guidance", "data"),
    ("navigated_downturns", "Navigated previous downturns", "data"),
)
MG_CEO_ATTRIBUTE_MAX = 2
# E26: 2, down from 8. Seven attributes on a 14-point raw scale were worth 8;
# the two measured survivors are 4 of those 14 raw points, so the block is worth
# 2. Leaving it at 8 made deleting a question EASIER to pass - 56 companies
# crossed the band gate on MG availability alone.
MG_CEO_POINTS = 2
MG_CAPALLOC_POINTS = 7
MG_MIN_ATTRIBUTES_SCORED = 2      # E25: both measured attributes. E19: not a cliff - see
#: clab/scoring/mg.py. 121 companies sat at exactly 3 of 15 on MG because of it.
# Capital allocation /7, split across measurable behaviours.
MG_CAPALLOC_SUBTESTS = (
    ("reinvestment_quality", "Reinvestment: capex + R&D vs FCF, and the ROIC it earns", 2),
    ("buyback_discipline", "Buybacks when cheap, not at peak multiples", 2),
    ("ma_track_record", "M&A accretive, not goodwill-impairing", 2),
    ("balance_sheet_stewardship", "Debt used productively, not for financial engineering", 1),
)

# ------------------------------------------------------------------ FE /15 (data)
# A4: the framework lists metrics but no internal allocation. Resolution below.
# The stated "key test" - are margins expanding as revenue grows - deliberately
# gets a fifth of the component rather than being buried in "quality".
# FE /18 after the v2 reweighting. The 3 extra points go to the three sub-tests with
# the clearest link to compounding rather than being spread thinly: revenue growth,
# FCF growth, and the framework's own stated key test.
FE_SUBTESTS = (
    ("revenue_growth", "Revenue CAGR 1Y / 3Y / 5Y", 3),
    ("eps_growth", "EPS growth", 1),
    ("fcf_growth", "FCF growth", 3),
    ("operating_income_growth", "Operating income growth", 1),
    ("gross_margin", "Gross margin", 1),
    ("operating_margin", "Operating margin", 1),
    ("fcf_margin", "FCF margin", 1),
    ("roic", "ROIC", 2),
    ("roe", "ROE", 1),
    ("margin_expansion", "Margins expanding as revenue grows (key test)", 4),
)
# Growth bands, applied to the 3Y CAGR with the 1Y/5Y as corroboration.
FE_REVENUE_CAGR_BANDS = (0.20, 0.12, 0.06, 0.02)    # -> 2, 2, 1, 1, 0 (see fe.py)
# ------------------------------------------------------------------ F1: sector-relative
# E03 R1: 95.6% of the score's ranking power was sector selection. An operating margin
# of 25% is full marks under the absolute bands below - a threshold built for software
# and meaningless for a utility, which is why mean scores ran from Financials 62.6% down
# to Utilities 41.2%. These five metrics are now scored as a PERCENTILE WITHIN SECTOR
# when enough peers exist, falling back to the absolute bands when they do not.
SECTOR_RELATIVE_METRICS = ("fe_gross_margin", "fe_operating_margin", "fe_fcf_margin",
                           "fe_roic", "fe_roe")
SECTOR_RELATIVE_MIN_PEERS = 8
#: percentile -> points, for a 1-point sub-test and a 2-point sub-test
SECTOR_PCTILE_BANDS = (0.80, 0.60, 0.40)
SECTOR_RELATIVE_ENABLED = True

FE_GROSS_MARGIN_BANDS = (0.55, 0.35, 0.20)
FE_OPERATING_MARGIN_BANDS = (0.25, 0.15, 0.07)
FE_FCF_MARGIN_BANDS = (0.20, 0.10, 0.04)
FE_ROIC_BANDS = (0.20, 0.12, 0.08, 0.04)
FE_ROE_BANDS = (0.20, 0.12, 0.06)
FE_MARGIN_SLOPE_STRONG_BPS = 50.0    # bps/yr of operating margin expansion for full marks
FE_MARGIN_SLOPE_FLAT_BPS = -25.0
FE_MARGIN_QUARTERS = 8               # regression window
FE_FCF_CONVERSION_GATE = 0.70        # FCF/NI below this caps margin_expansion at 2

# ------------------------------------------------------------------ BS /10 (data)
# A5: 8 metrics + a stress test, no allocation. Resolution:
BS_SUBTESTS = (
    ("net_debt_ebitda", "Net debt / EBITDA", 2),
    ("interest_coverage", "Interest coverage", 2),
    ("current_ratio", "Current ratio", 1),
    ("cash_vs_opex", "Cash position vs annual operating expense", 1),
    ("dilution", "Share dilution", 1),
    ("maturity_wall", "Near-term debt maturities", 1),
    ("stress_test", "Downturn survival test", 2),
)
BS_NET_DEBT_EBITDA_BANDS = (0.0, 1.5, 3.0)      # <=0 net cash -> 2; <=1.5 -> 2; <=3 -> 1
BS_COVERAGE_BANDS = (8.0, 3.0, 1.5)
BS_CURRENT_RATIO_BANDS = (1.5, 1.0)
BS_CASH_RUNWAY_YEARS_BANDS = (1.0, 0.5)
BS_DILUTION_BANDS = (0.005, 0.02, 0.05)          # YoY diluted share growth
# A7: the LongTermDebtMaturities* tag family is sparsely filed. Attempt it,
# expect NO_DATA on most names, and use LongTermDebtCurrent / (cash + TTM FCF)
# as a documented proxy rather than silently awarding the point.
BS_MATURITY_PROXY_BANDS = (0.25, 0.60)

# A6: "margins -25%" is read as RELATIVE (a 40% margin becomes 30%), not 25
# percentage points. Absolute drives most of the index to negative operating
# income, so everything scores 0 and the sub-test carries no information.
STRESS_REVENUE_HAIRCUT = 0.20        # revenue -20%
STRESS_MARGIN_HAIRCUT = 0.25         # RELATIVE margin haircut
STRESS_INTEREST_UPLIFT = 0.50        # financing costs +50%
STRESS_CAPEX_CUT = 0.30              # management cuts capex 30% in a downturn
STRESS_COMFORT = {"coverage": 3.0, "leverage": 3.0}
STRESS_SURVIVE = {"coverage": 1.5, "leverage": 5.0, "runway_years": 2.0}

# ------------------------------------------------------------------ VA /15 (data)
# A4: allocation not specified. Resolution: relative multiples 7, PEG 3,
# reverse DCF 5.
VA_SUBTESTS = (
    ("pe_vs_own_history", "P/E vs own 5Y average", 2),
    ("fwd_pe", "Forward P/E vs growth", 1),
    ("ev_ebitda_vs_peers", "EV/EBITDA vs sub-industry", 2),
    ("ev_sales_vs_peers", "EV/Sales vs sub-industry", 1),
    ("p_fcf", "P/FCF absolute and vs history", 1),
    ("peg", "Growth-adjusted P/E (PEG)", 3),
    ("reverse_dcf", "Reverse DCF: growth the price requires", 5),
)
VA_PEG_BANDS = (1.0, 1.5, 2.5)
VA_P_FCF_BANDS = (18.0, 28.0, 45.0)
VA_PERCENTILE_CHEAP = 0.30           # own-history percentile below this = cheap
VA_PERCENTILE_RICH = 0.70
VA_MIN_PEERS = 5                     # fewer scored peers -> NO_DATA, not "cheap"

# Reverse DCF assumptions. Every one is stamped `assumed` in provenance and the
# UI shows a wacc +/-2% sensitivity strip, because a single reverse-DCF number
# carries far more apparent authority than it deserves.
DCF_YEARS = 10
DCF_TERMINAL_GROWTH = 0.025
DCF_EQUITY_RISK_PREMIUM = 0.045
DCF_WACC_FLOOR = 0.06
DCF_WACC_CEIL = 0.14
DCF_DEFAULT_RISK_FREE = 0.042
DCF_DEFAULT_BETA = 1.0
DCF_FADE_START_YEAR = 6              # g fades linearly to terminal over years 6-10
DCF_SOLVE_BOUNDS = (-0.20, 0.60)
DCF_SENSITIVITY_WACC = 0.02
# Scoring: implied growth well below what the company already does / analysts
# expect = cheap.
DCF_IMPLIED_VS_REALIZED_BANDS = (-0.06, -0.02, 0.03, 0.08)

# ------------------------------------------------------------------ ER /5 (data)
ER_SUBTESTS = (
    ("earnings_surprise", "Realized results vs consensus", 2),
    ("estimate_revisions", "Estimate revision direction", 2),
    ("growth_vs_expectation", "Realized growth vs expected growth", 1),
)
ER_SURPRISE_QUARTERS = 8
ER_SURPRISE_BANDS = (0.75, 0.50)     # share of last 8 quarters that beat
ER_REVISION_BANDS = (0.02, 0.0, -0.02)

# ------------------------------------------------------------------ EN /5 (data)
# A8: these are technical inputs, in tension with "this is not a trading
# signal". It is 5 of 100 points and the user's framing is entry timing on a
# company already wanted, not signal generation. Implemented as specified, with
# a composite_ex_entry (/95) column so the ranking can be read with zero
# technical input.
# EN v2, specified by the user 2026-08-09. Two pillars, and the multiple matters
# MORE than the moving average:
#
#   "the average PE ratio for that stock ... stocks with higher PEs are higher
#    growth. So a stock with a high PE on average goes to a lower PE ... and the
#    thirty PE is the lowest it's been in I don't know how many years - that's
#    probably the price you wanna buy it at. And if both of those combined, it's
#    even better."
#
# So: P/E percentile against its own history carries 2 points, the EMA structure
# carries 2, and the confluence of both carries the last 1. Drawdown-from-ATH and
# swing-low proximity are demoted to context - they are still computed and shown on
# the scorecard, they just no longer earn points, because a drawdown is a fact about
# the chart while a compressed multiple on a grower is a fact about the price paid
# for earnings.
# EN /2 after the v2 reweighting. The two pillars survive at 1 point each and keep
# their relative ordering (the multiple still outranks the average - it is listed
# first and is the one that gets the confluence credit). Confluence is folded into
# the P/E pillar rather than kept as a separate point: at 2 points total a third
# sub-test would be scoring noise.
EN_SUBTESTS = (
    ("valuation_trough", "P/E near the low end of its own history", 1),
    ("vs_emas", "Price at the 20 / 72 EMA on daily, weekly or monthly", 1),
)
# EMA spans and timeframes the user watches. A touch of the 20 on the WEEKLY or
# MONTHLY is the rare setup; a 20-day touch is ordinary noise, so higher
# timeframes score higher.
EN_EMA_SPANS = (20, 72)
EN_TIMEFRAMES = ("daily", "weekly", "monthly")
EN_TIMEFRAME_WEIGHT = {"monthly": 3, "weekly": 2, "daily": 1}
# "At" the EMA means NEAR it, on either side - price coming down to meet the line.
# Bounded below as well as above: INTU showed up as "at the 20 EMA on the MONTHLY"
# while sitting 33% underneath it, which is not a touch, it is a broken trend. Far
# below a long-term EMA is a drawdown, and drawdown is reported as context rather
# than scored here.
EN_AT_EMA_TOLERANCE = 0.04           # up to 4% ABOVE still counts as at the line
EN_AT_EMA_BELOW = 0.12               # and up to 12% below; further is not a touch
# P/E percentile bands for the entry pillar - deliberately stricter than VA's,
# because this asks "is this an unusually good price", not "is it reasonable".
EN_PE_PCTILE_BANDS = (0.15, 0.30, 0.50)   # -> 2, 2, 1, 0
EN_CONFLUENCE_PCTILE = 0.35          # cheap enough to count toward confluence
EN_CONFLUENCE_MIN_TF_WEIGHT = 2      # must be at a weekly or monthly EMA
# retained as context only
EN_DRAWDOWN_BANDS = (0.30, 0.15, 0.05)
EN_SUPPORT_PROXIMITY = 0.08
EN_PIVOT_WINDOW = 20
EN_WEEKLY_EMA_SPAN = 50

# ------------------------------------------------------------------ misc
# ------------------------------------------------------------------ data quality
# Bounds a metric must satisfy to be SCORED at all. A value outside them is not a low
# score - it is evidence the XBRL tag pairing is wrong, and scoring it would launder a
# broken derivation into a number. Measured 2026-08-16 on 1,496 companies: 24 gross
# margins outside 0-100%, 74 operating margins outside +/-100%, 35 |ROIC| > 200%, and
# DXCM at -15,208%.
#
# The bounds are deliberately WIDE. They exist to catch derivations that are broken, not
# businesses that are unusual, and a real company must never be failed for being extreme.
QUALITY_BOUNDS = {
    "gross_margin": (0.0, 1.0),
    "operating_margin": (-1.0, 1.0),
    "net_margin": (-5.0, 1.0),
    "fcf_margin": (-5.0, 1.0),
    "roic": (-2.0, 2.0),
    "roe": (-5.0, 5.0),
    "net_debt_ebitda": (-50.0, 50.0),
}

# How far the two independent gross-margin derivations may differ before neither is
# trusted. 10 percentage points is wide enough that rounding, a stub period or a small
# reclassification passes, and narrow enough to catch the measured failures: INTU is out
# by ~51pp, ORCL ~26pp, FICO ~41pp, EXEL ~67pp.
GROSS_MARGIN_MAX_DISAGREEMENT = 0.10

# How much larger the combined debt tag must be than the assembled components before it
# is preferred. 20% is well beyond a rounding or lease-classification difference and well
# below a genuinely missing long-term borrowing line.
DEBT_PARTS_TOLERANCE = 0.20

# A margin's numerator and denominator must cover the same twelve months. One quarter of
# drift is tolerated because a filer can tag one line a period later than another; six
# years - INTU's actual gap - is not a margin at all.
RATIO_PERIOD_MAX_GAP_DAYS = 120

# Invested capital below this fraction of the largest input is treated as unusable rather
# than divided by. ROIC is a ratio, and a denominator that has nearly cancelled to zero
# produces a number about arithmetic, not about the business.
INVESTED_CAPITAL_MIN_FRACTION = 0.05

#: subtest key -> the metric whose quality decides it. Keeps `context.subtest` free of
#: call-site changes: the key already names the metric in every case.
QUALITY_METRIC_FOR_SUBTEST = {
    "fe_gross_margin": "gross_margin",
    "fe_operating_margin": "operating_margin",
    "fe_fcf_margin": "fcf_margin",
    "fe_roic": "roic",
    "fe_roe": "roe",
    "bs_net_debt_ebitda": "net_debt_ebitda",
}

EFFECTIVE_TAX_FLOOR = 0.05
EFFECTIVE_TAX_CEIL = 0.40
EFFECTIVE_TAX_DEFAULT = 0.21
MIN_QUARTERS_FOR_TTM = 4
CAGR_MIN_YEARS = 1


# ------------------------------------------------------------------ horizon (F4)
# E03 R3: the measured score's IC is +0.013 at one year and +0.063 at three, positive
# in 84.5% of months. The framework is built for multi-year compounding, so the default
# horizon for presentation and for any future validation is three years. Presentation
# only - this changes no score.
DEFAULT_HORIZON = "3y"
HORIZON_LABEL = "3-year"
# Figures below are from the SURVIVORSHIP-FREE holdout (E05, 675 symbols, 67,889 rows),
# not the biased panel the fix was designed on. The caveat is part of the note on purpose:
# the rank correlation is positive while the top decile's MEDIAN excess over SPY is
# negative, so a favourable IC must not be read as "this beats the index".
HORIZON_NOTE = ("This framework ranks companies for multi-year holding: on the "
                "survivorship-free panel its measured half ranks 3-year forward returns "
                "better than 1-year (IC +0.081 vs +0.043, positive in 92% of months). "
                "But the top decile's MEDIAN 3-year excess over SPY is -7.6% and only "
                "45% of its picks beat SPY - the positive average comes from a few large "
                "winners. Read it as a research ranking, not as an index-beating rule.")

# ------------------------------------------------------------------ hysteresis (F3)
# E03 R4: bands change in 27.2% of months and the median time in a band is 2 months.
# A band now changes only after this many consecutive readings agree. Applied
# symmetrically - an asymmetric rule that let downgrades through immediately would
# quietly bias the whole ranking downward.
BAND_CONFIRM_READINGS = 2


def advance_band(current: str | None, pending: str | None, streak: int, raw: str,
                 confirm: int = BAND_CONFIRM_READINGS,
                 same_day: bool = False) -> tuple[str, str | None, int]:
    """One step of the hysteresis state machine: -> (band_shown, pending, streak).

    The live scorer sees ONE reading at a time and cannot replay a company's history on
    every crawl, so the state (current / pending / streak) is carried on the scorecard and
    advanced here. `smooth_bands` below is written in terms of this function so the live
    path and the study cannot drift apart - a second implementation of a rule this fiddly
    would diverge and then both numbers would be untrustworthy.
    """
    if current is None:
        return raw, None, 0                       # first ever reading: nothing to confirm
    if confirm <= 1:
        return raw, None, 0
    if INSUFFICIENT_BAND in (current, raw):
        # Crossing the coverage gate is a DATA-AVAILABILITY change, not the score
        # wobbling across a threshold, so hysteresis does not apply to it. F3 exists to
        # stop a label flipping every other month on noise; INSUFFICIENT_DATA -> a real
        # band means the framework became applicable, which is new information.
        #
        # It also has to be exempt to work at all here: the judgement half is filled in
        # at 100 companies a day and each is re-scored ONCE, so a pending band would
        # never get its second confirming reading and the company would sit at
        # INSUFFICIENT_DATA indefinitely. Symmetric in both directions, so it cannot
        # bias the ranking up or down - the concern the F3 pre-registration raised.
        #
        # E33, 2026-08-25: this check now runs BEFORE the same-day one below, and the
        # ordering is the whole point. E27 added the same-day no-op above it, which
        # returned `current` and so short-circuited this exemption - the exemption whose
        # own comment says it "has to be exempt to work at all here". A company whose
        # coverage crossed 0.80 on a day it was re-scored stayed INSUFFICIENT_DATA until
        # the next calendar day. Measured that day: 13 companies were displayed as
        # unrankable while holding a real band_raw, BMY among them at coverage 0.894 and
        # score 72 with band_raw INVESTABLE. Crossing the coverage gate is new
        # information whatever the calendar says.
        return raw, None, 0
    if same_day:
        # E27: a READING is a calendar day, not an invocation. Counting invocations meant
        # 15 re-scores in three days advanced every company's hysteresis 15 times, and a
        # run that changed zero of 1,500 scores confirmed 54 bands on no new information.
        # Re-scoring the same company twice in one day is now a no-op for the band, which
        # is the property that was missing. It applies to score wobble only - the
        # coverage-gate crossing above is exempt from it.
        return current, pending, streak
    if raw == current:
        return current, None, 0                   # back to the shown band: cancel pending
    if raw == pending:
        streak += 1
        if streak >= confirm:
            return raw, None, 0                   # confirmed: the change takes effect
        return current, pending, streak
    return current, raw, 1                        # a new candidate starts its own streak


def smooth_bands(sequence: list[str], confirm: int = BAND_CONFIRM_READINGS) -> list[str]:
    """Require `confirm` consecutive readings before a band change takes effect.

    Pure function over an ordered sequence of raw bands, oldest first, so it is
    testable without a scorecard and reusable by both the live scorer and a study.
    """
    if confirm <= 1 or not sequence:
        return list(sequence)
    out: list[str] = []
    current: str | None = None
    pending: str | None = None
    streak = 0
    for raw in sequence:
        current, pending, streak = advance_band(current, pending, streak, raw, confirm)
        out.append(current)
    return out


def band_for(points: float, coverage: float) -> str:
    """Band label, or INSUFFICIENT_DATA when too little of the framework was scored."""
    if coverage < MIN_COVERAGE_FOR_BAND:
        return INSUFFICIENT_BAND
    for floor, label in BANDS:
        if points >= floor:
            return label
    return BANDS[-1][1]


def ladder_for(bands: tuple, mx: int) -> tuple:
    """A points ladder of the right length for `bands`, worth `mx` at the top.

    Exists because the length of the ladder must track the number of thresholds, and
    hardcoding a 4-entry ladder beside a 4-threshold band list silently produced an
    IndexError for every value below the lowest threshold - see band_from_thresholds.

    Convention, matching the ladders already written out for revenue CAGR:
        3 bands, mx=1 -> (1, 1, 1, 0)      3 bands, mx=2 -> (2, 2, 1, 0)
        4 bands, mx=1 -> (1, 1, 1, 0, 0)   4 bands, mx=2 -> (2, 2, 1, 1, 0)
    Full marks for the top two bands, then a decay to zero below the lowest.
    """
    n = len(bands)
    if mx <= 1:
        return tuple([mx] * min(3, n) + [0] * (n + 1 - min(3, n)))
    steps = [mx, mx]
    remaining = n - 1                       # entries left before the trailing zero
    val = mx
    while len(steps) < n:
        val = max(1, val - 1) if len(steps) >= 2 else val
        steps.append(val)
    return tuple(steps[:n] + [0])


def band_from_thresholds(value: float | None, bands: tuple, points: tuple) -> int | None:
    """Descending-threshold banding helper.

    bands must be descending; points has len(bands)+1 entries (last = below all).
    """
    if value is None:
        return None
    if len(points) != len(bands) + 1:
        # A length mismatch used to surface as an IndexError from deep inside a scorer,
        # which the engine caught as "FE scoring failed" and turned into NO_DATA for the
        # whole 18-point component. Any company with ROIC below the lowest band lost FE
        # entirely. Fail with something that names the problem instead.
        raise ValueError(
            f"points has {len(points)} entries for {len(bands)} bands; it needs "
            f"{len(bands) + 1} (the last is 'below every threshold'). "
            f"bands={bands} points={points}")
    for i, edge in enumerate(bands):
        if value >= edge:
            return points[i]
    return points[len(bands)]


def band_from_thresholds_asc(value: float | None, bands: tuple, points: tuple) -> int | None:
    """Ascending-threshold banding: lower value is better (leverage, multiples)."""
    if value is None:
        return None
    for i, edge in enumerate(bands):
        if value <= edge:
            return points[i]
    return points[len(bands)]
