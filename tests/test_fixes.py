"""E05 fixes: sector-relative scoring (F1), band hysteresis (F3), 3y default (F4).

Each fix came from a pre-registered finding in E03; see
journal/experiments/E05_four_fixes_preregistration.md.
"""
from __future__ import annotations

import pytest

from clab.scoring import fe, rubric, va
from clab.scoring.context import SymbolContext
from clab.fundamentals.metrics import MetricBundle


# ------------------------------------------------------------------ F3 hysteresis
def test_hysteresis_needs_two_consecutive_readings():
    """E03 R4: bands changed in 27.2% of months. A single reading no longer moves one."""
    raw = ["WEAK", "INVESTABLE", "WEAK", "WEAK", "WEAK"]
    out = rubric.smooth_bands(raw, confirm=2)
    assert out == ["WEAK", "WEAK", "WEAK", "WEAK", "WEAK"]


def test_hysteresis_lets_a_confirmed_change_through():
    raw = ["WEAK", "INVESTABLE", "INVESTABLE", "INVESTABLE"]
    out = rubric.smooth_bands(raw, confirm=2)
    assert out == ["WEAK", "WEAK", "INVESTABLE", "INVESTABLE"]


def test_hysteresis_is_symmetric_downgrades_are_not_exempt():
    """An asymmetric rule would quietly bias the whole ranking downward."""
    up = rubric.smooth_bands(["WEAK", "EXCEPTIONAL", "EXCEPTIONAL"], confirm=2)
    down = rubric.smooth_bands(["EXCEPTIONAL", "WEAK", "WEAK"], confirm=2)
    assert up == ["WEAK", "WEAK", "EXCEPTIONAL"]
    assert down == ["EXCEPTIONAL", "EXCEPTIONAL", "WEAK"]


def test_hysteresis_resets_on_a_flip_flop():
    """A flip-flop never confirms, so the band holds."""
    raw = ["WEAK", "INVESTABLE", "WEAK", "INVESTABLE", "WEAK", "INVESTABLE"]
    assert set(rubric.smooth_bands(raw, confirm=2)) == {"WEAK"}


def test_hysteresis_confirm_one_is_a_passthrough():
    raw = ["A", "B", "C"]
    assert rubric.smooth_bands(raw, confirm=1) == raw


def test_hysteresis_handles_empty_and_single():
    assert rubric.smooth_bands([]) == []
    assert rubric.smooth_bands(["WEAK"]) == ["WEAK"]


def test_hysteresis_three_readings_is_stricter():
    raw = ["WEAK", "INVESTABLE", "INVESTABLE", "INVESTABLE"]
    assert rubric.smooth_bands(raw, confirm=3) == ["WEAK", "WEAK", "WEAK", "INVESTABLE"]


# ------------------------------------------------------------------ F1 sector-relative
def test_sector_stats_collects_per_sector_distributions():
    rows = [{"sector": "Utilities", "operating_margin": 0.10 + i / 100, "roic": 0.05}
            for i in range(10)]
    rows += [{"sector": "Information Technology", "operating_margin": 0.30, "roic": 0.25}
             for _ in range(10)]
    stats = va.sector_stats(rows)
    assert stats["Utilities"]["operating_margin_sector_n"] == 10
    assert stats["Information Technology"]["operating_margin_sector_n"] == 10
    assert stats["Utilities"]["operating_margin_sector_values"] == sorted(
        stats["Utilities"]["operating_margin_sector_values"])


def test_sector_percentile_places_a_value_in_its_own_sector():
    rows = [{"sector": "Utilities", "operating_margin": m}
            for m in (0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 0.11, 0.12, 0.13, 0.14)]
    stats = va.sector_stats(rows)["Utilities"]
    top = va.sector_percentiles(stats, {"operating_margin": 0.14})
    bottom = va.sector_percentiles(stats, {"operating_margin": 0.05})
    assert top["operating_margin_sector_pctile"] == pytest.approx(1.0)
    assert bottom["operating_margin_sector_pctile"] == pytest.approx(0.1)
    assert top["operating_margin_sector_n"] == 10


def test_the_best_in_a_thin_margin_sector_now_earns_the_point():
    """The point of F1, using a value that genuinely fails the absolute bands.

    The absolute 1-point ladder is generous above 7%, so the gap shows in a sector
    whose whole distribution sits below that: a 6% operating margin is the BEST in this
    peer group and scores zero on a threshold table built for software.
    """
    thin = [{"sector": "Utilities", "operating_margin": m}
            for m in (0.010, 0.015, 0.020, 0.025, 0.030,
                      0.035, 0.040, 0.045, 0.050, 0.060)]
    stats = va.sector_stats(thin)["Utilities"]
    best = 0.060
    peers = va.sector_percentiles(stats, {"operating_margin": best})

    M = MetricBundle()
    M.set("operating_margin", best)
    ctx = SymbolContext(ticker="UTIL", cik="1", sector="Utilities", metrics=M,
                        peers=peers)
    pts, note, basis = fe._margin_points(
        ctx, "fe_operating_margin", "operating_margin", best, 1,
        rubric.FE_OPERATING_MARGIN_BANDS)
    assert basis == "sector_relative"
    assert pts == 1
    assert "percentile" in note

    # the absolute path gives the sector's best performer nothing - what F1 corrects
    absolute = rubric.band_from_thresholds(best, rubric.FE_OPERATING_MARGIN_BANDS,
                                           (1, 1, 1, 0))
    assert absolute == 0


def test_the_worst_in_a_rich_margin_sector_now_loses_the_point():
    """F1 cuts both ways, and it must: a 30% operating margin is full marks absolutely
    and bottom-decile among software companies."""
    rich = [{"sector": "Information Technology", "operating_margin": m}
            for m in (0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75)]
    stats = va.sector_stats(rich)["Information Technology"]
    worst = 0.30
    peers = va.sector_percentiles(stats, {"operating_margin": worst})
    M = MetricBundle()
    M.set("operating_margin", worst)
    ctx = SymbolContext(ticker="SW", cik="1", sector="Information Technology",
                        metrics=M, peers=peers)
    pts, _note, basis = fe._margin_points(
        ctx, "fe_operating_margin", "operating_margin", worst, 1,
        rubric.FE_OPERATING_MARGIN_BANDS)
    assert basis == "sector_relative"
    assert pts == 0
    assert rubric.band_from_thresholds(worst, rubric.FE_OPERATING_MARGIN_BANDS,
                                       (1, 1, 1, 0)) == 1


def test_sector_relative_falls_back_when_peers_are_too_few():
    rows = [{"sector": "Tiny", "operating_margin": 0.2} for _ in range(3)]
    stats = va.sector_stats(rows)["Tiny"]
    peers = va.sector_percentiles(stats, {"operating_margin": 0.2})
    M = MetricBundle()
    M.set("operating_margin", 0.30)
    ctx = SymbolContext(ticker="T", cik="1", sector="Tiny", metrics=M, peers=peers)
    _pts, note, basis = fe._margin_points(
        ctx, "fe_operating_margin", "operating_margin", 0.30, 1,
        rubric.FE_OPERATING_MARGIN_BANDS)
    assert basis == "absolute"
    assert "too few sector peers" in note


def test_absent_metric_stays_no_data_under_either_basis():
    ctx = SymbolContext(ticker="T", cik="1", sector="Utilities")
    pts, _note, basis = fe._margin_points(
        ctx, "fe_operating_margin", "operating_margin", None, 1,
        rubric.FE_OPERATING_MARGIN_BANDS)
    assert pts is None and basis == "none"


def test_only_the_nominated_metrics_go_sector_relative():
    """Growth and the margin-expansion key test stay absolute by design."""
    assert "fe_revenue_growth" not in rubric.SECTOR_RELATIVE_METRICS
    assert "fe_margin_expansion" not in rubric.SECTOR_RELATIVE_METRICS
    assert set(rubric.SECTOR_RELATIVE_METRICS) == {
        "fe_gross_margin", "fe_operating_margin", "fe_fcf_margin", "fe_roic", "fe_roe"}


def test_fe_still_sums_to_its_maximum_with_sector_relative_on():
    rows = [{"sector": "Utilities", "operating_margin": 0.10, "roic": 0.08,
             "gross_margin": 0.3, "fcf_margin": 0.1, "roe": 0.1} for _ in range(12)]
    stats = va.sector_stats(rows)["Utilities"]
    M = MetricBundle()
    for k, v in (("operating_margin", 0.10), ("roic", 0.08), ("gross_margin", 0.3),
                 ("fcf_margin", 0.1), ("roe", 0.1), ("revenue_cagr_3y", 0.05),
                 ("has_gross_profit_line", True)):
        M.set(k, v)
    peers = va.sector_percentiles(stats, M.as_flat())
    ctx = SymbolContext(ticker="U", cik="1", sector="Utilities", metrics=M, peers=peers)
    comp = fe.score(ctx)
    comp.check_points()                   # sub-test maxima must still sum to FE's max
    assert comp.max_points == rubric.COMPONENTS["FE"][1]


# ------------------------------------------------------------------ F4 horizon
def test_default_horizon_is_three_years():
    assert rubric.DEFAULT_HORIZON == "3y"
    assert "3" in rubric.HORIZON_LABEL
    assert "multi-year" in rubric.HORIZON_NOTE
