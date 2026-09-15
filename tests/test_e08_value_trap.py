"""E08 implementation must stay faithful to its pre-registration."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from clab.research import e08_value_trap as e08


def _panel() -> pd.DataFrame:
    dates = pd.to_datetime(["2020-01-31", "2020-03-31", "2023-01-31"])
    rows = []
    for date in dates:
        for i in range(10):
            rows.append({
                "ticker": f"T{i}", "date": date, "sub_industry": "one",
                "revenue_ttm": (i + 1) * (2 if date.year == 2023 and i == 0 else 1),
                "operating_margin": 0.1 + i / 100,
                "measured_pct": float(i),
            })
    return pd.DataFrame(rows)


def test_build_matches_36_month_lag_on_calendar(monkeypatch):
    raw = _panel()
    monkeypatch.setattr(pd, "read_parquet", lambda _path: raw.copy())
    monkeypatch.setattr(e08.battery, "attach_benchmark", lambda p: p)

    built = e08.build("unused.parquet")
    now = built[(built.ticker == "T0") & (built.date == pd.Timestamp("2023-01-31"))].iloc[0]
    assert now["share_then"] == pytest.approx(1 / 55)
    assert now["share"] == pytest.approx(2 / 56)


def test_build_rejects_duplicate_ticker_month(monkeypatch):
    raw = pd.concat([_panel(), _panel().iloc[[0]]], ignore_index=True)
    monkeypatch.setattr(pd, "read_parquet", lambda _path: raw.copy())
    monkeypatch.setattr(e08.battery, "attach_benchmark", lambda p: p)

    with pytest.raises(ValueError, match="ticker-month"):
        e08.build("unused.parquet")


def test_h3_excludes_decliners_but_retains_no_data():
    rows = []
    for date in pd.date_range("2015-01-31", periods=e08.MIN_DATE_CLUSTERS, freq="ME"):
        rows.extend([
            {"date": date, "top_decile": True, "d_share_3y": np.nan,
             "merger_like": False, "excess_1y": 0.3, "excess_3y": 0.3},
            {"date": date, "top_decile": True, "d_share_3y": 0.01,
             "merger_like": False, "excess_1y": -0.1, "excess_3y": -0.1},
            {"date": date, "top_decile": True, "d_share_3y": -0.01,
             "merger_like": False, "excess_1y": -0.5, "excess_3y": -0.5},
        ])

    result = e08.h3_filtered_top_decile(pd.DataFrame(rows))
    primary = result["3y"]["filtered_excluding_declining_share"]
    assert primary["n"] == e08.MIN_DATE_CLUSTERS * 2
    assert primary["median"] > 0
    assert result["3y"]["rising_share_only"]["median"] < 0
    assert result["passes"] is True


def test_h2_requires_harvesting_to_be_worse_than_all_other_quadrants():
    p = pd.DataFrame({
        "date": pd.to_datetime(["2020-01-31"] * 4),
        "quadrant": ["harvesting", "winning", "losing", "buying_share"],
        "top_decile": [True] * 4,
        "excess_1y": [-0.2, 0.1, 0.0, -0.3],
        "excess_3y": [-0.2, 0.1, 0.0, -0.3],
    })
    result = e08.h2_quadrants(p)
    assert result["checks"]["harvesting_worse_than_buying_share"] is False
    assert result["passes"] is False


def test_console_safe_escapes_unencodable_characters():
    assert e08._console_safe("needs >=5; actual \u22655", "cp1252") == (
        "needs >=5; actual \\u22655")
