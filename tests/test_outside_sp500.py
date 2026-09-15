"""Ranking the non-S&P-500 companies while the judgement half is still filling.

The trap this guards: a company with no SG/BQ/MG scores 0 on 50 of the 100 points, so
sorting the raw table ranks it near the bottom for its position in a QUEUE rather than
anything about the business. Half the universe is in that state today.
"""
from __future__ import annotations

import pandas as pd
import pytest

from clab.research import outside_sp500 as mod


def _row(ticker, *, composite, coverage, sg=20, mg=15, sector="Industrials"):
    return {"ticker": ticker, "name": f"{ticker} Inc", "sector": sector,
            "composite_strict": composite, "coverage": coverage,
            "sg_available": sg, "mg_available": mg, "band": "INVESTABLE",
            "qual_available": True}


def test_a_company_still_waiting_on_the_judgement_half_is_excluded_not_ranked_low():
    df = pd.DataFrame([
        _row("AAA", composite=70, coverage=0.95),
        _row("BBB", composite=30, coverage=0.95, sg=0, mg=0),   # not scored yet
    ])
    out = mod.eligible(df)
    assert list(out["ticker"]) == ["AAA"]


def test_a_company_under_the_coverage_floor_is_excluded():
    """Hard rule 3: below 80% coverage a company gets no band, so no rank either."""
    df = pd.DataFrame([
        _row("AAA", composite=70, coverage=0.95),
        _row("BBB", composite=90, coverage=0.50),      # high score, thin data
    ])
    out = mod.eligible(df)
    assert list(out["ticker"]) == ["AAA"]


def test_a_partial_judgement_half_does_not_qualify():
    """SG present but MG missing is still an incomplete judgement half."""
    df = pd.DataFrame([_row("AAA", composite=70, coverage=0.95, mg=0)])
    assert mod.eligible(df).empty


def test_system_rank_is_computed_over_the_ELIGIBLE_population(monkeypatch):
    """Not over the raw table. A rank out of 1,497 when 818 are blank is meaningless."""
    df = pd.DataFrame([
        _row("BIG1", composite=90, coverage=0.95),
        _row("SML1", composite=80, coverage=0.95),
        _row("BIG2", composite=70, coverage=0.95),
        _row("SML2", composite=60, coverage=0.95),
        _row("NONE", composite=99, coverage=0.95, sg=0, mg=0),   # excluded entirely
    ])
    monkeypatch.setattr(mod.pd, "read_parquet", lambda *_a, **_k: df)
    monkeypatch.setattr(mod, "_sp500_tickers", lambda: {"BIG1", "BIG2"})

    res = mod.run(top=10)
    assert res["eligible"] == 4                 # NONE is not counted
    assert res["excluded_no_judgement_or_coverage"] == 1
    top = res["top"]
    assert list(top["ticker"]) == ["SML1", "SML2"]
    # SML1 is 2nd of the four eligible, not 2nd of five rows
    assert list(top["system_rank"]) == [2, 4]


def test_an_unavailable_sp500_list_yields_nothing_rather_than_everything(monkeypatch):
    """Failing open here would present the whole S&P 500 as 'outside the S&P 500'."""
    df = pd.DataFrame([_row("AAA", composite=70, coverage=0.95)])
    monkeypatch.setattr(mod.pd, "read_parquet", lambda *_a, **_k: df)
    monkeypatch.setattr(mod, "_sp500_tickers", set)

    res = mod.run(top=10)
    assert res["top"].empty
    assert "Nothing outside the S&P 500 is rankable" in mod.render(res, 10)


def test_the_report_always_carries_the_never_validated_warning(monkeypatch):
    df = pd.DataFrame([_row("AAA", composite=70, coverage=0.95)])
    monkeypatch.setattr(mod.pd, "read_parquet", lambda *_a, **_k: df)
    monkeypatch.setattr(mod, "_sp500_tickers", lambda: {"ZZZ"})

    md = mod.render(mod.run(top=10), 10)
    assert "never been validated against forward returns" in md
    assert "-7.6%" in md or "−7.6%" in md
    assert "promoted` is false" in md


def test_the_excluded_count_reconciles_with_the_universe(monkeypatch):
    """A count you can predict independently - the rule that caught this week's bugs."""
    rows = [_row(f"T{i}", composite=50 + i, coverage=0.95) for i in range(6)]
    rows += [_row(f"X{i}", composite=99, coverage=0.95, sg=0, mg=0) for i in range(4)]
    df = pd.DataFrame(rows)
    monkeypatch.setattr(mod.pd, "read_parquet", lambda *_a, **_k: df)
    monkeypatch.setattr(mod, "_sp500_tickers", lambda: set())

    res = mod.run(top=10)
    assert res["eligible"] + res["excluded_no_judgement_or_coverage"] == \
        res["universe_rows"] == 10
