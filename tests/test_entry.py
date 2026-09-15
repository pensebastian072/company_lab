"""EN v2 and the reconstructed P/E history.

The framework owner's spec, 2026-08-09: the multiple against its own history
outranks the moving average, higher timeframes outrank lower ones, and both
together is the best setup.
"""
from __future__ import annotations

import pandas as pd
import pytest

from clab.fundamentals import pe_history
from clab.scoring import en, rubric
from clab.scoring.context import SymbolContext


def ctx_for(*, prices: dict | None = None, peers: dict | None = None) -> SymbolContext:
    return SymbolContext(ticker="T", cik="0000000001",
                         as_of="2026-08-09T00:00:00+00:00",
                         prices=prices or {}, peers=peers or {})


def emas(price: float, **overrides) -> dict:
    """Price plus a full EMA grid, all far ABOVE price by default (no touch)."""
    p = {"price": price}
    for tf in rubric.EN_TIMEFRAMES:
        p[f"{tf}_bars"] = 500
        for span in rubric.EN_EMA_SPANS:
            p[f"ema{span}_{tf}"] = price * 2.0        # price is 50% below -> far below
    p.update(overrides)
    return p


def sub(comp, key):
    return next(s for s in comp.subtests if s.key == key)


# ------------------------------------------------------------------ allocation
def test_en_allocation_matches_the_spec():
    """EN was cut from 5 points to 2 on 2026-08-10 (E01 + E02 evidence). The two
    pillars survive at 1 point each; confluence became context rather than a point."""
    alloc = dict((k, m) for k, _l, m in rubric.EN_SUBTESTS)
    assert alloc == {"valuation_trough": 1, "vs_emas": 1}
    assert sum(alloc.values()) == rubric.COMPONENTS["EN"][1] == 2


def test_pe_pillar_is_worth_at_least_as_much_as_the_ema_pillar():
    """The user's explicit ordering: the multiple matters more than the average."""
    alloc = {k: m for k, _l, m in rubric.EN_SUBTESTS}
    assert alloc["valuation_trough"] >= alloc["vs_emas"]


# ------------------------------------------------------------------ P/E pillar
@pytest.mark.parametrize("pctile,expected", [
    (0.02, 1), (0.15, 1), (0.16, 1), (0.30, 1), (0.31, 0), (0.50, 0), (0.51, 0), (0.95, 0),
])
def test_pe_percentile_bands(pctile, expected):
    c = ctx_for(prices=emas(100.0), peers={"pe_pctile_own": pctile, "pe_current": 20.0})
    assert sub(en.score(c), "en_valuation_trough").earned == expected


def test_pe_pillar_no_data_without_history():
    c = ctx_for(prices=emas(100.0), peers={"pe_history_note": "no positive-EPS periods"})
    st = sub(en.score(c), "en_valuation_trough")
    assert st.status.value == "no_data"
    assert st.earned is None            # absent history is never scored as expensive


def test_a_high_absolute_pe_can_still_be_a_cheap_entry():
    """The PLTR case: 148x is expensive in absolute terms and the 11th percentile of
    its own range. The framework is asked about the latter."""
    c = ctx_for(prices=emas(100.0),
                peers={"pe_pctile_own": 0.11, "pe_current": 148.0,
                       "pe_median_own": 208.0, "pe_min_own": 122.0, "pe_max_own": 462.0})
    assert sub(en.score(c), "en_valuation_trough").earned == 1


# ------------------------------------------------------------------ EMA pillar
def test_monthly_touch_scores_full():
    p = emas(100.0)
    p["ema20_monthly"] = 101.0          # price 1% below the monthly 20
    comp = en.score(ctx_for(prices=p, peers={"pe_pctile_own": 0.9}))
    st = sub(comp, "en_vs_emas")
    assert st.earned == 1
    assert "MONTHLY" in st.threshold_note


def test_weekly_touch_scores_full():
    p = emas(100.0)
    p["ema20_weekly"] = 100.5
    st = sub(en.score(ctx_for(prices=p, peers={"pe_pctile_own": 0.9})), "en_vs_emas")
    assert st.earned == 1
    assert "WEEKLY" in st.threshold_note


def test_daily_only_touch_no_longer_scores():
    """At 1 point, a daily touch would be the easiest condition in the framework to
    satisfy by accident, so the point now requires a higher timeframe."""
    p = emas(100.0)
    p["ema20_daily"] = 100.5
    st = sub(en.score(ctx_for(prices=p, peers={"pe_pctile_own": 0.9})), "en_vs_emas")
    assert st.earned == 0
    assert "daily" in st.threshold_note


def test_above_every_ema_scores_zero():
    p = emas(100.0)
    for tf in rubric.EN_TIMEFRAMES:
        for span in rubric.EN_EMA_SPANS:
            p[f"ema{span}_{tf}"] = 50.0      # price 100% above every line
    st = sub(en.score(ctx_for(prices=p, peers={"pe_pctile_own": 0.9})), "en_vs_emas")
    assert st.earned == 0
    assert "no discount" in st.threshold_note


def test_far_below_an_ema_is_a_drawdown_not_a_touch():
    """The INTU bug: it reported 'at the 20 EMA on the MONTHLY' while 33% under it."""
    p = emas(100.0)
    p["ema20_monthly"] = 150.0            # price 33% below
    st = sub(en.score(ctx_for(prices=p, peers={"pe_pctile_own": 0.9})), "en_vs_emas")
    assert st.earned == 0
    assert "drawdown, not a touch" in st.threshold_note


def test_slightly_below_still_counts_as_a_touch():
    p = emas(100.0)
    p["ema20_weekly"] = 100.0 / (1 - rubric.EN_AT_EMA_BELOW * 0.5)
    st = sub(en.score(ctx_for(prices=p, peers={"pe_pctile_own": 0.9})), "en_vs_emas")
    assert st.earned == 1


def test_ema_pillar_no_data_without_price_history():
    st = sub(en.score(ctx_for(prices={"price": 100.0})), "en_vs_emas")
    assert st.status.value == "no_data"


# ------------------------------------------------------------------ confluence
def test_confluence_is_recorded_as_context_not_a_point():
    """After the cut to 2 points, confluence is reported on the EMA sub-test rather
    than earning a point of its own - a third sub-test at 2 points total would be
    scoring noise."""
    keys = {k for k, _l, _m in rubric.EN_SUBTESTS}
    assert "confluence" not in keys

    cheap = {"pe_pctile_own": 0.10, "pe_current": 20.0}
    rich = {"pe_pctile_own": 0.90, "pe_current": 20.0}
    at_weekly = emas(100.0)
    at_weekly["ema20_weekly"] = 100.5
    extended = emas(100.0)
    for tf in rubric.EN_TIMEFRAMES:
        for span in rubric.EN_EMA_SPANS:
            extended[f"ema{span}_{tf}"] = 50.0

    both = sub(en.score(ctx_for(prices=at_weekly, peers=cheap)), "en_vs_emas")
    assert both.inputs["confluence"] is True
    assert "CONFLUENCE" in both.threshold_note

    ema_only = sub(en.score(ctx_for(prices=at_weekly, peers=rich)), "en_vs_emas")
    assert ema_only.inputs["confluence"] is False

    cheap_only = sub(en.score(ctx_for(prices=extended, peers=cheap)), "en_vs_emas")
    assert cheap_only.inputs["confluence"] is False


def test_confluence_requires_a_higher_timeframe():
    """A daily touch plus a cheap multiple is not the confluence setup."""
    p = emas(100.0)
    p["ema20_daily"] = 100.5
    st = sub(en.score(ctx_for(prices=p, peers={"pe_pctile_own": 0.10})), "en_vs_emas")
    assert st.inputs["confluence"] is False


def test_perfect_entry_scores_the_component_maximum():
    p = emas(100.0)
    p["ema20_monthly"] = 100.5
    comp = en.score(ctx_for(prices=p, peers={"pe_pctile_own": 0.04, "pe_current": 20.0}))
    assert comp.earned_points == rubric.COMPONENTS["EN"][1]


def test_drawdown_and_support_are_context_not_points():
    keys = {k for k, _l, _m in rubric.EN_SUBTESTS}
    assert "drawdown_from_ath" not in keys
    assert "near_support" not in keys
    comp = en.score(ctx_for(prices=emas(100.0), peers={"pe_pctile_own": 0.5}))
    st = sub(comp, "en_vs_emas")
    assert "drawdown_from_ath" in st.inputs      # still reported


# ------------------------------------------------------------------ P/E history
def _facts(eps_rows):
    return {"facts": {"us-gaap": {"EarningsPerShareDiluted": {"units": {
        "USD/shares": eps_rows}}}}}


def _q(year, qtr, val, filed):
    se = {1: (f"{year}-01-01", f"{year}-03-31"), 2: (f"{year}-04-01", f"{year}-06-30"),
          3: (f"{year}-07-01", f"{year}-09-30"), 4: (f"{year}-10-01", f"{year}-12-31")}
    s, e = se[qtr]
    return {"start": s, "end": e, "val": val, "filed": filed, "accn": "a", "form": "10-Q"}


def _prices(start, days, price):
    idx = pd.bdate_range(start, periods=days)
    return pd.DataFrame({"date": idx, "close": [price] * len(idx)})


def test_pe_series_uses_filing_dates_not_period_ends():
    """EPS must apply from when it was PUBLISHED, or the series looks into the future."""
    rows = [_q(2024, q, 1.0, f"2024-{q * 3 + 1:02d}-15") for q in range(1, 5)]
    rows.append(_q(2025, 1, 1.0, "2025-04-15"))
    h = pe_history.build(_facts(rows), _prices("2024-01-01", 400, 40.0))
    assert len(h) > 0
    # first P/E cannot exist before the fourth quarter was filed
    assert h.series.index.min() >= pd.Timestamp("2025-01-15")


def test_pe_series_skips_negative_earnings():
    rows = [_q(2024, q, -1.0, f"2024-{q * 3 + 1:02d}-15") for q in range(1, 5)]
    h = pe_history.build(_facts(rows), _prices("2024-01-01", 400, 40.0))
    assert len(h) == 0


def test_percentile_needs_enough_history():
    rows = [_q(2024, q, 1.0, f"2024-{q * 3 + 1:02d}-15") for q in range(1, 5)]
    h = pe_history.build(_facts(rows), _prices("2025-01-20", 30, 40.0))
    assert not h.usable
    assert "pe_pctile_own" not in h.stats()


def test_percentile_places_the_current_value_correctly():
    rows = []
    for y in (2020, 2021, 2022, 2023, 2024, 2025):
        for q in range(1, 5):
            rows.append(_q(y, q, 1.0, f"{y}-{q * 3 + 1:02d}-15"))
    idx = pd.bdate_range("2021-01-01", periods=1100)
    # price ramps up then collapses at the end -> the current P/E is near the bottom
    closes = list(range(40, 40 + len(idx)))
    closes[-1] = 20
    px = pd.DataFrame({"date": idx, "close": [float(c) for c in closes]})
    st = pe_history.build(_facts(rows), px).stats()
    assert st["pe_pctile_own"] < 0.05
    assert st["pe_min_own"] <= st["pe_current"] <= st["pe_max_own"]


def test_pe_history_never_raises_on_junk():
    assert len(pe_history.build({}, pd.DataFrame())) == 0
    assert len(pe_history.build({"facts": {}}, _prices("2024-01-01", 10, 5.0))) == 0
