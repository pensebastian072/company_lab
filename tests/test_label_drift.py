"""E33: a user-facing label may not restate a total the framework already knows.

The framework went from 100 points to 94 at E26 - MG fell 15 -> 9 and the CEO block 8 -> 2
- and the explanatory text did not follow. Weeks later the workbook's Findings sheet still
read *"Qualitative half (SG, BQ, MG - 50 of 100 points)"*, the dashboard still said
*"Measured /50 ... /100 adds"*, and the company page said *"Excluding Entry: /95"* - which
was wrong twice over, because ex-entry is the total minus EN and EN itself had already
dropped from 5 points to 2.

None of that was economically serious. All of it was avoidable: a label that restates a
number will drift from it, and one that asks cannot. So every total is now derived from
`rubric.COMPONENTS`, and this test fails the build if a literal comes back.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from clab.scoring import rubric

ROOT = Path(__file__).resolve().parents[1] / "clab"

#: files that render a total to a human. Research scripts and journal files are exempt -
#: they record what was true on the day they ran, which is the point of them.
SURFACES = [
    ROOT / "export" / "xlsx_export.py",
    ROOT / "runner" / "batch.py",
    ROOT / "runner" / "probe.py",
    ROOT / "ui" / "templates" / "dashboard.html",
    ROOT / "ui" / "templates" / "company.html",
]

#: `/100` is legitimate where the quantity really is normalised to 100 -
#: `composite_normalized` and `selection_score` both are, by construction.
_LEGITIMATE = re.compile(r"(Normalized /100|normalis\w+ to 100|/100\s*\*|percent)", re.I)

#: a points-context literal: "/100 full", "50 of 100 points", "Measured /50", "/95"
_DRIFT = re.compile(
    r"(?:/(?:100|95|94|50|44)\b(?!\s*\*)"          # "/100 full", "/95"
    r"|\b(?:50|44)\s+of\s+(?:100|94)\s+points\b)"   # "50 of 100 points"
)


@pytest.mark.parametrize("path", SURFACES, ids=lambda p: p.name)
def test_no_hardcoded_framework_total_in_a_user_facing_label(path):
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#") or _LEGITIMATE.search(line):
            continue
        hit = _DRIFT.search(line)
        assert not hit, (
            f"{path.name}:{i} hardcodes a framework total ({hit.group(0)!r}) in a "
            f"user-facing label. Derive it from rubric.TOTAL_POINTS / JUDGED_POINTS / "
            f"MEASURED_POINTS instead:\n    {stripped}")


def test_the_derived_totals_agree_with_the_components():
    assert rubric.JUDGED_POINTS == sum(rubric.COMPONENTS[c][1] for c in rubric.JUDGED_COMPONENTS)
    assert rubric.MEASURED_POINTS == sum(rubric.COMPONENTS[c][1]
                                         for c in rubric.MEASURED_COMPONENTS)
    assert rubric.JUDGED_POINTS + rubric.MEASURED_POINTS == rubric.TOTAL_POINTS


def test_the_totals_are_what_the_framework_says_today():
    """Pins today's numbers so a component change is a deliberate, visible edit."""
    # V3 P0: was (94, 44, 50). MG's 9 points are measured, not judged - E25 removed its
    # five model-scored CEO attributes and the constant never followed.
    assert (rubric.TOTAL_POINTS, rubric.JUDGED_POINTS, rubric.MEASURED_POINTS) == (94, 35, 59)


def test_points_in_ignores_an_unknown_code_rather_than_raising():
    assert rubric.points_in(("SG", "NOPE")) == rubric.COMPONENTS["SG"][1]
