"""Modules the scheduled tasks run must be printable on a cp1252 console.

Found 2026-08-17 while checking the daily chain: `outside_sp500` crashed with
`UnicodeEncodeError: 'charmap' codec can't encode character '\u2212'` - a typographic
minus sign in its caveat text. It is wired into the 12:15 CompanyLabQual task, so the
report would have silently failed to write every single day.

Python on this box encodes stdout as cp1252 even when redirected to a file, so "it works
in my terminal" proves nothing about what Task Scheduler sees. CLAUDE.md already requires
ASCII-only .ps1 files for the same reason; this extends the rule to anything a task
prints.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

#: every module the scheduled chain in scripts/run_clab.ps1 invokes and prints
TASK_MODULES = [
    "clab/research/outside_sp500.py",
    "clab/research/data_quality.py",
    "clab/runner/batch.py",
    "clab/runner/fold_qual.py",
    "clab/runner/watchdog.py",
    "clab/runner/snapshot.py",
    "clab/export/refresh.py",
    "clab/export/xlsx_export.py",
    "clab/qual/scorer.py",
]


@pytest.mark.parametrize("rel", TASK_MODULES)
def test_a_scheduled_module_is_pure_ascii(rel):
    src = (REPO / rel).read_text(encoding="utf-8")
    bad = sorted({hex(ord(c)) for c in src if ord(c) > 127})
    assert not bad, (
        f"{rel} contains non-ASCII {bad}. Python prints stdout as cp1252 under Task "
        f"Scheduler, so this raises UnicodeEncodeError and the task's output is lost."
    )


def test_the_rendered_report_is_encodable_as_cp1252():
    """Belt and braces: the SOURCE being ASCII does not guarantee the OUTPUT is."""
    from clab.research import outside_sp500 as mod
    res = {"eligible": 2, "universe_rows": 3, "outside_eligible": 1,
           "min_coverage": 0.8, "top": _one_row()}
    mod.render(res, 5).encode("cp1252")          # raises if it ever regresses


def _one_row():
    import pandas as pd
    return pd.DataFrame([{"system_rank": 1, "ticker": "AAA", "name": "A Co",
                          "sector": "Industrials", "composite_strict": 80.0,
                          "coverage": 0.95, "band": "INVESTABLE"}])
