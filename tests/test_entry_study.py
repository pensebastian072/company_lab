"""Regression tests for the saved E01 study summary."""
from __future__ import annotations

import pandas as pd

from clab.research import entry_study as E01


def _row(value, *, year=2020):
    row = {
        "ticker": "T", "date": "2020-01-02", "year": year,
        "en": 4, "confluence": True,
    }
    for horizon in E01.HORIZONS:
        row[f"ret_{horizon}"] = value
        row[f"spy_{horizon}"] = 0.0 if value is not None else None
    return row


def test_hit_rates_use_only_observed_returns_and_report_both_ns():
    study = E01.Study(
        rows=[_row(1.0), _row(-0.5), _row(None)],
        randoms=[_row(1.0), _row(-0.5), _row(None), _row(None)],
    )
    watch = pd.DataFrame([{"ticker": "T"}])

    result = E01.summarise(study, watch, threshold=4, top=1)

    for horizon in E01.HORIZONS:
        pooled = result["pooled"][horizon]
        assert pooled["signal_hit_n"] == 2
        assert pooled["signal_hit_rate"] == 0.5
        assert pooled["random_hit_n"] == 2
        assert pooled["random_hit_rate"] == 0.5

    rendered = E01.render(result)
    assert "signal hit n" in rendered
    assert "random hit n" in rendered
