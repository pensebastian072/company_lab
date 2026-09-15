"""The 'every prompt quotes the standard block' rule, actually enforced.

`docs/CODEX_STANDARD_RULES.md` exists because the abstention rules drifted invisibly
across eight batches and cost 45 of the 100 external points. Its own text says the block
must be copied verbatim into every prompt - but nothing checked, and the first prompt
written after the fix (E54) carried a condensed paraphrase that dropped the three
sentences making the two errors symmetric. An unenforced invariant is a comment.

The block GROWS - E55 added the blind-pass and competitive_position_trend sections - so
this checks it section by section rather than as one string. A prompt written before a
section existed is not retroactively wrong; a prompt shipping an ALTERED copy of a
section is, which is the case that matters.

Two limits worth knowing before trusting a pass:

- Only the researcher-facing text is checked - the part inside the ````` fence. The
  surrounding sections are written for us, and they SHOULD discuss the streak, because
  that is the diagnosis.
- Standard rule 1 ("never quote a streak back at the researcher") is checked as a
  pattern, not as meaning. It catches the exact form that caused the drift - a metric
  followed by hold/maintain/keep - and it cannot catch a fresh way of saying it.

If a CORE section is reworded later, already-sent prompts here will fail. That is the
intended prompt: update them (they stay usable as templates) or move them to HISTORIC.
Historic prompts predate the fix and are frozen; a NEW prompt file fails this test until
it is classified, which is the point.
"""
from __future__ import annotations

import io
import re
from pathlib import Path

import pytest

DOCS = Path(__file__).resolve().parents[1] / "docs"
RULES = DOCS / "CODEX_STANDARD_RULES.md"

# Written before the fix in E51. Frozen as history - do not add to this list.
HISTORIC = {
    "CODEX_COMPANY_PROMPT.md",
    "CODEX_E42_CITED_PROMPT.md",
    "CODEX_E43_BATCH_PROMPT.md",
    "CODEX_E44_PROMPT.md",
    "CODEX_E45_PROMPT.md",
    "CODEX_E46_ENERGY_PROMPT.md",
    "CODEX_E47_UTILITIES_PROMPT.md",
    "CODEX_E49_COMMSERVICES_PROMPT.md",
    "CODEX_PHASE0_CONTINUE.md",
    "CODEX_PHASE0_PROMPT.md",
}

# Every prompt written after the fix. Add new prompts here, not to HISTORIC.
CURRENT = {
    "CODEX_E57_HEALTHCARE_PHASE_A.md",
    "CODEX_E61_INDUSTRIALS_PHASE_A.md",
    "CODEX_E51_RERUN_PROMPT.md",
    "CODEX_E54_FINANCIALS_PHASE_A.md",
    "CODEX_E56_FINANCIALS_RECUT.md",
    "CODEX_E59_FINANCIALS_PHASEB_B1.md",
    "CODEX_E65_IT_PHASE_A.md",
    "CODEX_E76_HEALTH_CARE_PHASE_A_RERESEARCH.md",
    "CODEX_E79_INDUSTRIALS_PHASE_A_RERESEARCH.md",
    "CODEX_E59_FINANCIALS_PHASEB_B2.md",
    "CODEX_E59_FINANCIALS_PHASEB_B3.md",
    "CODEX_E80_UTILITIES_PHASEB.md",
}

# The sections carrying the two-errors symmetry. Every post-fix prompt sends all three.
CORE = (
    "## THE TWO ERRORS COST THE SAME",
    "## WHAT UNKNOWN MEANS",
    "## CITATIONS ARE REQUIRED, AND THEY ARE NOT A REASON TO ABSTAIN",
)

# The form the drift actually took: a streak, then an instruction to sustain it.
STREAK_IMPERATIVE = re.compile(
    r"\b(hold|maintain|sustain)\s+(that|it|this|the\s+streak)\b"
    r"|\bkeep\s+(it|that)\s+up\b",
    re.I,
)


def _read(path: Path) -> str:
    return io.open(path, encoding="utf-8").read()


def _researcher_text(name: str) -> str:
    """The part of a prompt doc that is actually sent to Codex."""
    m = re.search(r"^`````\n(.*?)\n`````", _read(DOCS / name), re.S | re.M)
    assert m, f"{name} has no ````` -fenced prompt body"
    return m.group(1)


def standard_block() -> str:
    m = re.search(r"## THE BLOCK.*?\n```\n(.*?)\n```", _read(RULES), re.S)
    assert m, "CODEX_STANDARD_RULES.md no longer contains a fenced THE BLOCK section"
    return m.group(1).rstrip()


def block_sections() -> dict:
    """The canonical block, split into its `## ` sections."""
    parts = re.split(r"^(## .+)$", standard_block(), flags=re.M)
    return {
        head.strip(): (head + body).rstrip()
        for head, body in zip(parts[1::2], parts[2::2])
    }


def test_the_block_is_extractable_and_states_both_errors():
    secs = block_sections()
    for name in CORE:
        assert name in secs, f"the canonical block lost its {name!r} section"
    body = secs["## THE TWO ERRORS COST THE SAME"]
    assert "ASSERTING what you cannot evidence" in body
    assert "ABSTAINING when you could have" in body
    assert "not a way to avoid being wrong" in body


def test_every_prompt_is_classified():
    on_disk = {
        p.name for p in DOCS.glob("CODEX_*.md") if p.name != "CODEX_STANDARD_RULES.md"
    }
    unclassified = on_disk - HISTORIC - CURRENT
    assert not unclassified, (
        f"new Codex prompt(s) {sorted(unclassified)} must be added to CURRENT in this "
        "test and must quote the standard rules block verbatim"
    )
    missing = (HISTORIC | CURRENT) - on_disk
    assert not missing, f"classified prompt(s) no longer on disk: {sorted(missing)}"


@pytest.mark.parametrize("name", sorted(CURRENT))
def test_current_prompt_sends_the_core_sections_verbatim(name):
    text = _researcher_text(name)
    secs = block_sections()
    for head in CORE:
        assert secs[head] in text, (
            f"{name} does not send {head!r} VERBATIM - a paraphrase is how the drift "
            "happened; copy it from CODEX_STANDARD_RULES.md unchanged"
        )


@pytest.mark.parametrize("name", sorted(CURRENT))
def test_current_prompt_does_not_edit_a_section_it_includes(name):
    """A prompt may predate a section. It may not ship an altered copy of one."""
    text = _researcher_text(name)
    for head, canonical in block_sections().items():
        if head in text:
            assert canonical in text, (
                f"{name} contains {head!r} but not the canonical wording - a local edit "
                "to a shared section is exactly the drift this file exists to stop"
            )


@pytest.mark.parametrize("name", sorted(CURRENT))
def test_current_prompt_sets_no_streak_target(name):
    hit = STREAK_IMPERATIVE.search(_researcher_text(name))
    assert not hit, (
        f"{name} tells the researcher to sustain a streak ({hit.group(0)!r}) - "
        "standard rule 1 forbids it; past performance belongs in our report"
    )
