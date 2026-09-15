"""The forward DCF must be the reverse DCF's arithmetic seen from the other side.

E20's V1 is an identity, not a judgement: feed a fair value's own enterprise value back
through the solver and it must return the growth that produced it. A failure means one of
the two models is wrong, and both are already wired into the workbook.

The rest of these pin the refusals. A DCF that quietly defaults a growth rate, floors a
negative cash flow at zero or values a bank off CFO-minus-capex produces a number for
every company and means nothing.
"""
import pytest

from clab.scoring import forward_dcf, rubric
from clab.scoring.context import SymbolContext
from clab.scoring.reverse_dcf import enterprise_value, implied_growth


class _M:
    """Minimal stand-in for the metrics bundle."""

    def __init__(self, **vals):
        self._v = vals

    def raw(self, key):
        return self._v.get(key)

    def as_flat(self):
        return dict(self._v)


def _ctx(*, sector="Industrials", profile="STANDARD", price=100.0, **metrics):
    ctx = SymbolContext(ticker="T", cik="1", sector=sector)
    ctx.metrics = _M(**metrics)
    ctx.market = {"price": price, "beta": 1.0, "risk_free": 0.042}
    ctx.prices = {"price": price}
    ctx.profile = type("P", (), {"name": profile})()
    return ctx


def _healthy(**over):
    base = dict(fcf_ttm=1_000_000_000.0, diluted_shares_ttm=100_000_000.0,
                net_debt=0.0, fcf_cagr_5y=0.08, fcf_cagr_3y=0.08,
                revenue_cagr_3y=0.07)
    base.update(over)
    return base


# ------------------------------------------------------------------ V1, the identity
def test_forward_and_reverse_dcf_reconcile():
    ctx = _ctx(**_healthy())
    res = forward_dcf.analyse(ctx)
    rec = forward_dcf.reconcile(ctx, res)
    assert rec["checked"]
    assert rec["abs_error"] < 1e-4


@pytest.mark.parametrize("g", [-0.05, 0.0, 0.03, 0.08, 0.15, 0.25])
def test_the_identity_holds_across_the_growth_band(g):
    fcf0, wacc = 5.0e8, 0.09
    ev = enterprise_value(fcf0, g, wacc)
    assert abs(implied_growth(ev, fcf0, wacc) - g) < 1e-4


# ------------------------------------------------------------------ V3, the strip
def test_the_strip_is_monotone_and_brackets_the_base_case():
    res = forward_dcf.analyse(_ctx(**_healthy()))
    s = res["strip"]
    assert s["bear"] < s["base"] < s["bull"]


def test_a_higher_discount_rate_lowers_the_value():
    res = forward_dcf.analyse(_ctx(**_healthy()))
    w = res["wacc_sensitivity"]
    assert w["wacc_plus"] < res["fair_value_per_share"] < w["wacc_minus"]


# ------------------------------------------------------------------ the refusals
def test_negative_free_cash_flow_is_refused_not_floored():
    res = forward_dcf.analyse(_ctx(**_healthy(fcf_ttm=-2.0e8)))
    assert res["fair_value_per_share"] is None
    assert "negative" in res["reason"]


def test_a_bank_is_refused_with_a_reason():
    res = forward_dcf.analyse(_ctx(sector="Financials", **_healthy()))
    assert res["fair_value_per_share"] is None
    assert "borrowing is the raw material" in res["reason"]


def test_an_unusable_growth_series_refuses_rather_than_defaulting():
    """A 60% five-year FCF CAGR is a recovery, not a forecast. Clamping it to the
    boundary would invent a fair value out of the number the bounds exist to reject."""
    res = forward_dcf.analyse(_ctx(**_healthy(fcf_cagr_5y=0.60, fcf_cagr_3y=0.55,
                                              revenue_cagr_3y=0.40)))
    assert res["fair_value_per_share"] is None
    assert res["reason"] == "no usable growth rate"
    assert res["growth"]["rejected"]["fcf_cagr_5y"] == 0.60


def test_a_peer_median_is_the_last_resort_not_the_first():
    metrics = _healthy(fcf_cagr_5y=None, fcf_cagr_3y=None, revenue_cagr_3y=None)
    res = forward_dcf.analyse(_ctx(**metrics), peer_median=0.06)
    assert res["growth"] == 0.06
    assert res["growth_provenance"]["basis"] == "sub_industry_median"
    # ...and a company with its own series never reaches for the peer median
    own = forward_dcf.analyse(_ctx(**_healthy()), peer_median=0.20)
    assert own["growth_provenance"]["basis"] == "fcf_cagr_5y"


def test_growth_preference_order_prefers_fcf_over_revenue():
    res = forward_dcf.analyse(_ctx(**_healthy(fcf_cagr_5y=None)))
    assert res["growth_provenance"]["basis"] == "fcf_cagr_3y"
    res2 = forward_dcf.analyse(_ctx(**_healthy(fcf_cagr_5y=None, fcf_cagr_3y=None)))
    assert res2["growth_provenance"]["basis"] == "revenue_cagr_3y_proxy"


def test_net_debt_lowers_the_equity_value():
    no_debt = forward_dcf.analyse(_ctx(**_healthy(net_debt=0.0)))
    debt = forward_dcf.analyse(_ctx(**_healthy(net_debt=5.0e9)))
    assert debt["fair_value_per_share"] < no_debt["fair_value_per_share"]
    gap = no_debt["fair_value_per_share"] - debt["fair_value_per_share"]
    assert abs(gap - 5.0e9 / 100_000_000.0) < 1e-6


def test_an_absurd_fair_value_is_flagged_not_hidden():
    res = forward_dcf.analyse(_ctx(price=0.5, **_healthy()))
    assert res["implausible"] is True
    assert res["fair_value_per_share"] is not None      # reported, just flagged


def test_margin_of_safety_sign_matches_the_comparison():
    """Prices chosen INSIDE the plausible band on purpose. The old test used $10 and
    $10,000 against a ~$226 fair value - ratios of 22.6x and 0.02x, both of which are now
    withheld as implausible, so it was asserting the sign of a number the model does not
    stand behind."""
    cheap = forward_dcf.analyse(_ctx(price=100.0, **_healthy()))
    rich = forward_dcf.analyse(_ctx(price=300.0, **_healthy()))
    assert cheap["implausible"] is False and rich["implausible"] is False
    assert cheap["margin_of_safety"] > 0
    assert rich["margin_of_safety"] < 0


# ------------------------------------------------------------------ E33: the MOS guard
def test_a_negative_fair_value_reports_NO_margin_of_safety():
    """The bug this replaces: `(fv - price) / fv` with `if fv` as its only guard catches
    fv == 0 and nothing else, so a NEGATIVE fair value flipped the sign of numerator and
    denominator together and came out POSITIVE. Measured on the real universe: HR's fair
    value of -$0.008 reported a **+251,695%** margin of safety and VST's -$0.76 reported
    +17,846%. The DCF sheet sorts on this column, so the most broken DCFs ranked as the
    cheapest companies in the workbook."""
    res = forward_dcf.analyse(_ctx(price=100.0, **_healthy(net_debt=1.0e12)))
    assert res["fair_value_per_share"] < 0
    assert res["margin_of_safety"] is None
    assert "zero or negative" in res["reason"]


def test_an_implausible_fair_value_reports_no_margin_of_safety_but_keeps_the_value():
    res = forward_dcf.analyse(_ctx(price=0.5, **_healthy()))
    assert res["implausible"] is True
    assert res["fair_value_per_share"] is not None      # reported, just flagged
    assert res["margin_of_safety"] is None
    assert "not an opportunity" in res["reason"]


def test_every_flagged_dcf_carries_a_written_reason():
    """A flag with no explanation beside it is half a finding, and `reason` was None for
    all 125 flagged companies."""
    for price in (0.5, 20_000.0):
        res = forward_dcf.analyse(_ctx(price=price, **_healthy()))
        assert res["implausible"] is True
        assert isinstance(res["reason"], str) and res["reason"]


def test_a_plausible_dcf_still_has_no_reason_and_a_real_number():
    res = forward_dcf.analyse(_ctx(price=200.0, **_healthy()))
    assert res["implausible"] is False
    assert res["reason"] is None
    assert res["margin_of_safety"] is not None


def test_terminal_growth_below_wacc_is_enforced():
    """`enterprise_value` returns inf when wacc <= terminal growth; the caller must
    refuse rather than pass an infinity into a per-share division."""
    assert enterprise_value(1e9, 0.05, rubric.DCF_TERMINAL_GROWTH) == float("inf")


# ------------------------------------------------------------------ the input bug
def test_a_poisoned_share_quarter_is_not_averaged_in():
    """AAPL's FY 10-K filed a Q-duration `diluted_shares` row of -47,029,000 - a CHANGE
    in shares, not a count. Averaging it with three real quarters gave 11.05bn against a
    true ~14.8bn, and universe-wide the TTM count ran 25% light. Every per-share number
    inherited it; the forward DCF is what made it visible, as a median margin of safety
    of +24%.

    normalize.py's derived-quarter guard cannot catch this one: the row is DIRECT, filed
    with a ~91-day duration, so nothing about it looks derived.
    """
    import datetime as dt

    from clab.fundamentals import normalize as nz
    from clab.fundamentals.metrics import ttm_share_count

    def fact(end, val):
        d = dt.date.fromisoformat(end)
        return nz.Fact(end=d, val=val, start=d - dt.timedelta(days=91), duration="Q")

    s = nz.QuarterSeries()
    s.facts = [fact("2025-03-29", 15_056_133_000.0),
               fact("2025-06-28", 14_948_179_000.0),
               fact("2025-09-27", -47_029_000.0),        # the poison
               fact("2025-12-27", 14_810_356_000.0),
               fact("2026-03-28", 14_725_873_000.0)]
    val, diag = ttm_share_count(s)
    assert 14.6e9 < val < 15.1e9              # a real share count, not 11bn
    assert "2025-09-27" in diag["quarters_dropped"]


def test_a_share_series_with_nothing_usable_returns_none():
    from clab.fundamentals import normalize as nz
    from clab.fundamentals.metrics import ttm_share_count

    val, diag = ttm_share_count(nz.QuarterSeries())
    assert val is None
    assert diag["quarters_used"] == []


# ------------------------------------------------------------------ E28: share counts
def test_mcd_files_shares_in_millions_and_the_dcf_survives_it():
    """MCD files WeightedAverageNumberOfDilutedSharesOutstanding as 714.525 - MILLIONS.

    The DCF divided a $170bn equity value by 715 and reported a fair value of
    $238,644,091 per share. The >10x implausibility gate flagged it, which is not the same
    as getting it right.
    """
    ctx = _ctx(price=270.95, **_healthy(fcf_ttm=7.761e9, diluted_shares_ttm=714.525,
                                        net_debt=42.5085e9, fcf_cagr_5y=0.0184))
    ctx.market["market_cap"] = 191_735_480_320.0
    res = forward_dcf.analyse(ctx)
    fv = res["fair_value_per_share"]
    assert 0.1 * 270.95 < fv < 10 * 270.95        # a number a human could act on
    assert res["shares_provenance"]["basis"] == "market_cap_over_price"
    assert res["shares_provenance"]["disputed"] is True


def test_a_disagreement_is_reported_not_hidden():
    """NFLX split 10:1 inside the TTM window, so its FILED count is ~9.6x the current
    one and its units are perfectly correct. The row has to say so."""
    ctx = _ctx(price=100.0, **_healthy(diluted_shares_ttm=1_000_000_000.0))
    ctx.market["market_cap"] = 10_000_000_000.0     # implies 100m shares, 10x fewer
    _shares, prov = forward_dcf.shares_for(ctx)
    assert prov["disputed"] is True
    assert prov["ratio"] == pytest.approx(0.1)


def test_agreement_leaves_the_healthy_majority_alone():
    """1,409 of 1,439 companies already agree within 2x; the fix must not re-value them."""
    ctx = _ctx(price=100.0, **_healthy(diluted_shares_ttm=100_000_000.0))
    ctx.market["market_cap"] = 10_000_000_000.0     # implies exactly 100m
    shares, prov = forward_dcf.shares_for(ctx)
    assert shares == pytest.approx(100_000_000.0)
    assert prov["disputed"] is False


def test_the_filing_is_the_fallback_when_there_is_no_market_cap():
    ctx = _ctx(price=100.0, **_healthy(diluted_shares_ttm=250_000_000.0))
    ctx.market.pop("market_cap", None)
    shares, prov = forward_dcf.shares_for(ctx)
    assert shares == 250_000_000.0
    assert prov["basis"] == "diluted_shares_ttm"
