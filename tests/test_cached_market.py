"""`--cached-market`: a re-score should not pay for data the change did not touch.

Measured 2026-08-23 with the engine's own per-stage timings over eight companies:

    yf_market   0.47s mean, 0.01s median, 2.38s max   76% of build_context
    normalize   0.06s
    edgar_facts 0.05s
    yf_prices   0.03s
    pe_history  0.01s

The mean and median differ by 47x because `yf_market` is free when the cache is fresh and
a network round-trip when it is not. A rubric edit re-scores 1,500 companies and pays that
toll for every stale one, to arrive at prices the edit had no opinion about.

The danger is the obvious one: a flag that silently freezes prices. So it must be
impossible to reach by accident (never a default, never on the weekly crawl) and it must
say so in the scorecard's provenance.
"""
import pytest

from clab.runner import engine
from clab.sources.yf_market import YfMarket


def test_cached_market_never_calls_fetch(monkeypatch):
    """The whole point. If this still reaches the network the flag buys nothing."""
    calls = []

    def _boom(self, *a, **kw):
        calls.append(self.ticker)
        raise AssertionError("fetch() called under --cached-market")

    monkeypatch.setattr(YfMarket, "fetch", _boom)
    monkeypatch.setattr(YfMarket, "latest_cached",
                        lambda self: {"info": {"currentPrice": 10.0}})

    ctx, meta = engine.build_context(
        "AAPL", "0000320193", as_of="2026-08-23T00:00:00+00:00",
        cached_market=True, with_prices=False)
    assert calls == []
    assert meta["sources"]["yf_market"]["cached_only"] is True


def test_the_default_still_refreshes(monkeypatch):
    """A flag that freezes prices must never be reachable by accident - the weekly
    crawl has to keep fetching."""
    called = []

    class _Res:
        payload = {"info": {"currentPrice": 10.0}}

        def freshness_record(self):
            return {"source_id": "yf_market", "ok": True}

    monkeypatch.setattr(YfMarket, "fetch",
                        lambda self, **kw: (called.append(self.ticker), _Res())[1])
    _ctx, meta = engine.build_context(
        "AAPL", "0000320193", as_of="2026-08-23T00:00:00+00:00", with_prices=False)
    assert called == ["AAPL"]
    assert meta["sources"]["yf_market"].get("cached_only") is None


def test_a_company_with_no_cached_snapshot_warns_loudly(monkeypatch):
    """Thin data is a fallback; scoring a company with NO market data at all and saying
    nothing is the failure mode this repo keeps rediscovering."""
    monkeypatch.setattr(YfMarket, "fetch",
                        lambda self, **kw: pytest.fail("should not fetch"))
    monkeypatch.setattr(YfMarket, "latest_cached", lambda self: None)

    _ctx, meta = engine.build_context(
        "AAPL", "0000320193", as_of="2026-08-23T00:00:00+00:00",
        cached_market=True, with_prices=False)
    assert any("no cached yf_market snapshot" in w for w in meta["warnings"])
    assert meta["sources"]["yf_market"]["ok"] is False
