"""Composite assembly: eight ComponentScores -> one auditable Scorecard.

The honest-composite decision, in one place:

    points_earned    = sum of earned points across components        0..100
    points_available = sum of points that COULD have been earned    <=100
    n_a_points       = points ruled NOT_APPLICABLE by sector profile
    coverage         = points_available / (100 - n_a_points)

    composite_strict     = points_earned            <- HEADLINE, default sort
    composite_normalized = 100 * earned / available <- extrapolated, shown beside coverage

composite_strict is the headline because missing data costing you points is the
conservative treatment: the system does not get to guess. composite_normalized
exists so a well-covered name is not buried purely by a thin filing history, but
it is never displayed without its coverage number next to it.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import rubric
from .types import ComponentScore, Status


@dataclass
class Scorecard:
    ticker: str
    cik: str
    name: str = ""
    as_of: str = ""                     # injected, never read from the clock in here
    data_through: str | None = None     # fundamentals (EDGAR)
    price_as_of: str | None = None      # market data (moves daily; see rubric A8)
    sector: str = ""
    sub_industry: str = ""
    profile: str = "STANDARD"
    # F3 hysteresis state, carried forward from the previous scorecard. The live scorer
    # sees one reading at a time and must not replay a company's whole history on every
    # crawl, so the state machine's state travels on the scorecard itself. All-None means
    # "first ever reading", which shows the raw band with nothing to confirm.
    prior_band: str | None = None
    prior_band_pending: str | None = None
    prior_band_streak: int = 0
    #: the date of the reading that produced `prior_band`. E27: hysteresis advances per
    #: calendar day, so a same-day re-score leaves the band exactly where it was.
    prior_band_reading_date: str | None = None
    components: dict[str, ComponentScore] = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)     # the flat metric bundle used
    sources: dict = field(default_factory=dict)     # freshness per feed
    warnings: list[str] = field(default_factory=list)

    # ------------------------------------------------------------ aggregates
    @property
    def points_earned(self) -> int:
        return sum(c.earned_points for c in self.components.values())

    @property
    def points_available(self) -> int:
        return sum(c.available_points for c in self.components.values())

    @property
    def not_applicable_points(self) -> int:
        return sum(c.not_applicable_points for c in self.components.values())

    @property
    def no_data_points(self) -> int:
        return sum(c.no_data_points for c in self.components.values())

    @property
    def applicable_points(self) -> int:
        return rubric.TOTAL_POINTS - self.not_applicable_points

    @property
    def coverage(self) -> float:
        denom = self.applicable_points
        return 0.0 if denom <= 0 else self.points_available / denom

    @property
    def composite_strict(self) -> int:
        return self.points_earned

    @property
    def composite_normalized(self) -> float | None:
        avail = self.points_available
        return None if avail == 0 else round(100.0 * self.points_earned / avail, 1)

    @property
    def selection_score(self) -> int:
        """The ranking that decides WHICH company - entry timing excluded (E21).

        E01 tested entry timing three ways and it failed three times, yet its 2 points
        were ordering the top of the book: PTC and VRT carried the full 2, NVDA and JLL
        carried none, and that alone separated #1 from #3.

        Rescaled to the same 100-point basis rather than left as a raw /98 sum. Banding a
        0-98 score against thresholds calibrated for 0-100 would systematically downgrade
        every company holding entry points - a re-calibration disguised as a removal. This
        way a band change means the company moved, not the ruler.
        """
        # Normalised to 100, NOT to the framework total. E26 took the total to 94, and
        # rescaling by the total would have quietly made every band harder to reach on a
        # shorter scale - the same error E19's first version made by removing a ceiling
        # along with a cliff. `rubric.BANDS` is calibrated in 0-100 points and stays that
        # way however many questions the framework asks.
        en_max = rubric.COMPONENTS["EN"][1]
        denom = rubric.TOTAL_POINTS - en_max
        return int(round(100.0 * self.composite_ex_entry / denom)) if denom else 0

    @property
    def band_raw(self) -> str:
        """This reading's band, before hysteresis. Kept beside the shown band so a
        smoothed label can always be traced back to the number that produced it.

        Reads `selection_score`, not `composite_strict`: entry timing informs WHEN to
        buy, never WHETHER the company is good (E21).
        """
        return rubric.band_for(self.selection_score, self.coverage)

    @property
    def band_reading_date(self) -> str:
        """The calendar day this reading belongs to, from `as_of` - never the clock."""
        return (self.as_of or "")[:10]

    @property
    def _band_state(self) -> tuple[str, str | None, int]:
        same_day = bool(self.prior_band_reading_date
                        and self.prior_band_reading_date == self.band_reading_date)
        return rubric.advance_band(self.prior_band, self.prior_band_pending,
                                   self.prior_band_streak, self.band_raw,
                                   same_day=same_day)

    @property
    def band(self) -> str:
        """The band SHOWN, with F3 hysteresis applied.

        E03 R4 measured raw bands changing in 27.2% of months with a median 2-month life;
        a label that flips that often cannot be held through, and the dashboard's answer
        would depend on the week you looked. Symmetric by design - letting downgrades
        through immediately would quietly bias the ranking downward.
        """
        return self._band_state[0]

    @property
    def band_pending(self) -> str | None:
        """A band waiting for confirmation, so the UI can show "may become X"."""
        return self._band_state[1]

    @property
    def band_pending_streak(self) -> int:
        return self._band_state[2]

    def _subset(self, codes) -> tuple[int, int, int]:
        earned = avail = na = 0
        for code in codes:
            c = self.components.get(code)
            if c is None:
                continue
            earned += c.earned_points
            avail += c.available_points
            na += c.not_applicable_points
        return earned, avail, na

    @property
    def quant_only_50(self) -> int:
        """The 50 points that contain zero LLM content. First-class, not a footnote."""
        return self._subset(rubric.MEASURED_COMPONENTS)[0]

    @property
    def quant_coverage(self) -> float:
        earned, avail, na = self._subset(rubric.MEASURED_COMPONENTS)
        applicable = sum(rubric.COMPONENTS[c][1] for c in rubric.MEASURED_COMPONENTS) - na
        return 0.0 if applicable <= 0 else avail / applicable

    @property
    def quant_normalized(self) -> float | None:
        """The measured half rescaled to 0-100 so it is directly comparable to the
        full composite. This is what makes the system useful on day one: the LLM
        half takes overnight runs across several days, and until it exists every
        full band is INSUFFICIENT_DATA by design."""
        _e, avail, _na = self._subset(rubric.MEASURED_COMPONENTS)
        return None if avail == 0 else round(100.0 * self.quant_only_50 / avail, 1)

    @property
    def quant_band(self) -> str:
        """Band on the measured half alone. Labelled "measured-half" in the UI so
        it is never mistaken for the full-framework band."""
        qn = self.quant_normalized
        return rubric.INSUFFICIENT_BAND if qn is None else \
            rubric.band_for(qn, self.quant_coverage)

    @property
    def qual_only_50(self) -> int:
        return self._subset(rubric.JUDGED_COMPONENTS)[0]

    @property
    def qual_available(self) -> bool:
        return self._subset(rubric.JUDGED_COMPONENTS)[1] > 0

    @property
    def composite_ex_entry(self) -> int:
        """/95 - the ranking with zero technical input (rubric A8)."""
        en = self.components.get("EN")
        return self.points_earned - (en.earned_points if en else 0)

    @property
    def n_subtests_no_data(self) -> int:
        return sum(
            1 for c in self.components.values()
            for st in c.subtests if st.status == Status.NO_DATA
        )

    # ------------------------------------------------------------ serialization
    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "cik": self.cik,
            "name": self.name,
            "as_of": self.as_of,
            "data_through": self.data_through,
            "price_as_of": self.price_as_of,
            "sector": self.sector,
            "sub_industry": self.sub_industry,
            "profile": self.profile,
            "composite_strict": self.composite_strict,
            "composite_normalized": self.composite_normalized,
            "composite_ex_entry": self.composite_ex_entry,
            "score": self.selection_score,
            "selection_score": self.selection_score,   # old name, kept
                                                       # so studies and
                                                       # snapshots written
                                                       # before 2026-08-23
                                                       # still resolve
            "band": self.band,
            "band_raw": self.band_raw,
            "band_pending": self.band_pending,
            "band_pending_streak": self.band_pending_streak,
            "band_reading_date": self.band_reading_date,
            "band_confirm_readings": rubric.BAND_CONFIRM_READINGS,
            "coverage": round(self.coverage, 4),
            "points_earned": self.points_earned,
            "points_available": self.points_available,
            "applicable_points": self.applicable_points,
            "not_applicable_points": self.not_applicable_points,
            "no_data_points": self.no_data_points,
            "n_subtests_no_data": self.n_subtests_no_data,
            "quant_only_50": self.quant_only_50,
            "quant_normalized": self.quant_normalized,
            "quant_band": self.quant_band,
            "quant_coverage": round(self.quant_coverage, 4),
            "qual_only_50": self.qual_only_50,
            "qual_available": self.qual_available,
            "components": {
                code: self.components[code].to_dict()
                for code in rubric.COMPONENT_ORDER if code in self.components
            },
            "metrics": self.metrics,
            "sources": self.sources,
            "warnings": self.warnings,
            "advisory": rubric_banner(),
        }

    def table_row(self) -> dict:
        """Flat row for data/scores.parquet - the only thing the UI table reads."""
        row = {
            "ticker": self.ticker,
            "cik": self.cik,
            "name": self.name,
            "sector": self.sector,
            "sub_industry": self.sub_industry,
            "profile": self.profile,
            "as_of": self.as_of,
            "data_through": self.data_through,
            "price_as_of": self.price_as_of,
            "composite_strict": self.composite_strict,
            "composite_normalized": self.composite_normalized,
            "composite_ex_entry": self.composite_ex_entry,
            "score": self.selection_score,
            "selection_score": self.selection_score,   # old name, kept
                                                       # so studies and
                                                       # snapshots written
                                                       # before 2026-08-23
                                                       # still resolve
            "band": self.band,
            "band_raw": self.band_raw,
            "band_pending": self.band_pending,
            "coverage": round(self.coverage, 4),
            "quant_only_50": self.quant_only_50,
            "quant_normalized": self.quant_normalized,
            "quant_band": self.quant_band,
            "quant_coverage": round(self.quant_coverage, 4),
            "qual_available": self.qual_available,
            "n_subtests_no_data": self.n_subtests_no_data,
        }
        for code in rubric.COMPONENT_ORDER:
            c = self.components.get(code)
            low = code.lower()
            row[low] = c.earned_points if c else None
            row[f"{low}_max"] = rubric.COMPONENTS[code][1]
            row[f"{low}_available"] = c.available_points if c else 0
            row[f"{low}_is_llm"] = bool(c.is_llm) if c else False
        # headline metrics surfaced on the table
        for key in (
            "revenue_ttm", "revenue_cagr_1y", "revenue_cagr_3y", "revenue_cagr_5y",
            "eps_ttm", "fcf_ttm", "gross_margin", "operating_margin", "fcf_margin",
            "margin_trend_bps_yr", "roic", "roe", "fcf_conversion",
            "net_debt", "net_debt_ebitda", "interest_coverage", "current_ratio",
            "dilution_yoy", "stress_verdict", "price", "market_cap",
            "pe", "fwd_pe", "peg", "ev_ebitda", "ev_sales", "p_fcf",
            "reverse_dcf_implied_growth", "reverse_dcf_wacc", "analyst_growth_3y",
            "pe_current", "pe_pctile_own", "pe_median_own", "pe_min_own",
            "pe_max_own", "pe_history_n", "pe_history_years",
            "en_best_timeframe_weight", "en_confluence", "drawdown_from_ath",
            "pct_vs_ema20_daily", "pct_vs_ema72_daily",
            "pct_vs_ema20_weekly", "pct_vs_ema72_weekly",
            "pct_vs_ema20_monthly", "pct_vs_ema72_monthly",
        ):
            row[key] = self.metrics.get(key)
        return row


def rubric_banner() -> str:
    from .. import config

    return config.ADVISORY_BANNER


def build_scorecard(
    *,
    ticker: str,
    cik: str,
    name: str,
    as_of: str,
    components: dict[str, ComponentScore],
    metrics: dict | None = None,
    data_through: str | None = None,
    price_as_of: str | None = None,
    sector: str = "",
    sub_industry: str = "",
    profile: str = "STANDARD",
    sources: dict | None = None,
    warnings: list[str] | None = None,
    prior_band: str | None = None,
    prior_band_pending: str | None = None,
    prior_band_streak: int = 0,
    prior_band_reading_date: str | None = None,
    validate: bool = True,
) -> Scorecard:
    """Assemble and validate. Deterministic: no clock, no RNG, no dict-order reliance."""
    if validate:
        for code, comp in components.items():
            if code not in rubric.COMPONENTS:
                raise ValueError(f"unknown component code {code!r}")
            expected = rubric.COMPONENTS[code][1]
            if comp.max_points != expected:
                raise ValueError(
                    f"{code}: max_points {comp.max_points} != framework {expected}"
                )
            comp.check_points()
    return Scorecard(
        ticker=ticker, cik=cik, name=name, as_of=as_of,
        data_through=data_through, price_as_of=price_as_of,
        sector=sector, sub_industry=sub_industry, profile=profile,
        prior_band=prior_band, prior_band_pending=prior_band_pending,
        prior_band_streak=prior_band_streak,
        prior_band_reading_date=prior_band_reading_date,
        components=dict(components),
        metrics=dict(metrics or {}),
        sources=dict(sources or {}),
        warnings=list(warnings or []),
    )


def empty_component(code: str, why: str = "not scored") -> ComponentScore:
    """A component with every sub-test NO_DATA. Used when a whole stage is absent."""
    from .types import no_data

    label, mx = rubric.COMPONENTS[code]
    return ComponentScore(
        code=code, label=label, max_points=mx,
        subtests=[no_data(f"{code.lower()}_all", label, mx, why)],
        note=why,
    )


def weighted_composite01(components: dict[str, ComponentScore]) -> float:
    """The framework's weighted-normalized form.

    composite01 = .20(SG/20) + .15(BQ/15) + ... + .05(EN/5)

    Every weight equals max_points/100 and the weights sum to 1.00, so this is
    arithmetically identical to the raw point sum / 100. tests/test_weights.py
    asserts the two agree to 1e-9 over 10,000 random vectors, so the code cannot
    drift from the framework's stated form.
    """
    total = 0.0
    for code, (_, mx) in rubric.COMPONENTS.items():
        comp = components.get(code)
        if comp is None:
            continue
        weight = mx / rubric.TOTAL_POINTS
        total += weight * (comp.earned_points / mx)
    return total
