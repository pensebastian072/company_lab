"""An explicit --symbols list must not be silently narrowed by the tier default.

Asking the qual scorer to re-score 215 companies scored 93 of them and reported a
clean finish: `--symbols` was intersected with the DEFAULT tier (sp500), so every
S&P 400 and 600 name was dropped without a word. A --symbols list is a statement about
which companies to score, not a filter to apply to one index.
"""
from __future__ import annotations

import pytest

from clab.qual import scorer


class _Recorder:
    """Captures what run() would have scored, without touching Ollama or EDGAR."""

    def __init__(self, tiers):
        self.tiers = tiers
        self.calls = []

    def __call__(self, tier):
        self.calls.append(tier)
        return self.tiers.get(tier, [])


def _row(t, cik):
    return {"ticker": t, "cik": cik, "name": f"{t} Inc", "sector": "", "sub_industry": ""}


SP500 = [_row("AAPL", "1"), _row("MSFT", "2")]
ALL = SP500 + [_row("AEIS", "3"), _row("KNSL", "4")]


def test_symbols_outside_the_default_tier_are_found_not_dropped(monkeypatch, capsys):
    rec = _Recorder({"sp500": SP500, "all": ALL})
    monkeypatch.setattr(scorer, "load_universe_multi", rec)
    monkeypatch.setattr(scorer.ollama, "available", lambda: (True, "up"))
    monkeypatch.setattr(scorer, "trust_windows_certs", lambda: None)

    # stop before any scoring work: an empty gpu lease context is enough
    monkeypatch.setattr(scorer.ollama, "gpu_lease",
                        lambda **kw: _NullCtx())
    res = scorer.run(symbols=["AAPL", "AEIS", "KNSL"], limit=None)
    out = capsys.readouterr().out
    assert "searching all tiers" in out
    assert "all" in rec.calls, "must widen to every tier"
    assert res is not None


def test_symbols_in_no_universe_are_reported_loudly(monkeypatch, capsys):
    rec = _Recorder({"sp500": SP500, "all": ALL})
    monkeypatch.setattr(scorer, "load_universe_multi", rec)
    monkeypatch.setattr(scorer.ollama, "available", lambda: (True, "up"))
    monkeypatch.setattr(scorer, "trust_windows_certs", lambda: None)
    monkeypatch.setattr(scorer.ollama, "gpu_lease", lambda **kw: _NullCtx())

    scorer.run(symbols=["AAPL", "NOSUCHTICKER"], limit=None)
    out = capsys.readouterr().out
    assert "WARNING" in out and "NOSUCHTICKER" in out


def test_tier_all_does_not_trigger_a_second_lookup(monkeypatch, capsys):
    rec = _Recorder({"all": ALL})
    monkeypatch.setattr(scorer, "load_universe_multi", rec)
    monkeypatch.setattr(scorer.ollama, "available", lambda: (True, "up"))
    monkeypatch.setattr(scorer, "trust_windows_certs", lambda: None)
    monkeypatch.setattr(scorer.ollama, "gpu_lease", lambda **kw: _NullCtx())

    scorer.run(tier="all", symbols=["AAPL", "AEIS"], limit=None)
    assert rec.calls == ["all"], "already the widest universe; no need to re-load"


class _NullCtx:
    def __enter__(self):
        return True

    def __exit__(self, *a):
        return False


@pytest.mark.parametrize("given,expected", [("aapl", "AAPL"), ("brk.b", "BRK-B"),
                                            (" msft ", "MSFT")])
def test_symbol_normalisation(given, expected):
    assert given.strip().upper().replace(".", "-") == expected
