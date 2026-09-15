"""scores.parquet must be writable no matter what one company's numbers look like.

The failure this pins: a single company whose `pe` serialised as the string 'Infinity'
made pyarrow reject the whole column, so `to_parquet` raised, the exception was caught
and logged as a WARNING, and scores.parquet stayed FROZEN at 1,139 companies while
scores.csv had 1,497. Every study and the UI read the parquet, so a whole crawl's worth
of new companies was invisible while the run reported success.

CLAUDE.md already required that inf never reach parquet - interest coverage is capped at
999 for exactly this reason. `pe` had no such guard.
"""
from __future__ import annotations

import math

import pandas as pd
import pytest

from clab.runner import batch


def _cards(n=3, **overrides):
    out = []
    for i in range(n):
        row = {"ticker": f"T{i}", "cik": f"{i:010d}", "composite_strict": 50 + i,
               "pe": 12.5, "coverage": 0.9, "band": "WEAK", "name": f"Co {i}"}
        row.update(overrides if i == 0 else {})
        out.append(row)
    return out


@pytest.mark.parametrize("bad", [float("inf"), float("-inf"), "Infinity", "-Infinity",
                                 "inf", "NaN", "nan"])
def test_non_finite_values_are_nulled_not_left_to_poison_the_column(bad):
    df = pd.DataFrame(_cards(pe=bad))
    out = batch._sanitize_for_parquet(df)
    assert out["pe"].iloc[0] is None or pd.isna(out["pe"].iloc[0])
    # the other companies keep their real values
    assert float(out["pe"].iloc[1]) == 12.5


def test_sanitized_frame_actually_writes_parquet(tmp_path):
    """The real regression: this frame used to raise from pyarrow."""
    df = pd.DataFrame(_cards(pe="Infinity"))
    out = batch._sanitize_for_parquet(df)
    p = tmp_path / "scores.parquet"
    out.to_parquet(p, index=False)                # must not raise
    back = pd.read_parquet(p)
    assert len(back) == 3, "every company survives the write"


def test_write_scores_table_keeps_every_company(tmp_path, monkeypatch):
    monkeypatch.setattr(batch.config, "SCORES_PARQUET", tmp_path / "scores.parquet")
    monkeypatch.setattr(batch.config, "DATA_DIR", tmp_path)
    n = batch.write_scores_table(_cards(5, pe=float("inf")))
    assert n == 5
    assert len(pd.read_parquet(tmp_path / "scores.parquet")) == 5


def test_parquet_and_csv_do_not_disagree(tmp_path, monkeypatch):
    """The symptom that made this findable: csv had 1,497 rows, parquet had 1,139."""
    monkeypatch.setattr(batch.config, "SCORES_PARQUET", tmp_path / "scores.parquet")
    monkeypatch.setattr(batch.config, "DATA_DIR", tmp_path)
    batch.write_scores_table(_cards(4, pe="Infinity"))
    pq = pd.read_parquet(tmp_path / "scores.parquet")
    csv = pd.read_csv(tmp_path / "scores.csv")
    assert len(pq) == len(csv) == 4


def test_finite_values_are_untouched():
    df = pd.DataFrame(_cards(3))
    out = batch._sanitize_for_parquet(df)
    assert list(out["pe"]) == [12.5, 12.5, 12.5]
    assert list(out["ticker"]) == ["T0", "T1", "T2"]


def test_none_and_real_nan_still_read_as_missing():
    df = pd.DataFrame(_cards(pe=None))
    out = batch._sanitize_for_parquet(df)
    assert out["pe"].iloc[0] is None or pd.isna(out["pe"].iloc[0])
    assert math.isfinite(float(out["pe"].iloc[1]))
