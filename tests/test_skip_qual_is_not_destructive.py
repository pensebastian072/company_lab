"""A quant-only re-score must never delete the judgement half from a scorecard.

`--skip-qual` used to mean "do not read the qual cache", so re-scoring a company for an
unrelated reason silently dropped its 50-point LLM half even though the cached scores
were on disk untouched. Fixing 208 companies' sector took the judgement half off 208
scorecards with it - twice in one afternoon - and the count of companies with a full
score went 698 -> 465 without anything reporting a failure.

The flag only ever meant "do not spend GPU generating", and `batch` never generates
anyway; that is the scorer's job. Reading three cached JSON files per company costs
nothing.
"""
from __future__ import annotations

import inspect

from clab.runner import engine


def test_engine_always_reads_the_qual_cache():
    src = inspect.getsource(engine)
    assert "qual = load_qual(cik_used)" in src
    assert "load_qual(cik_used) if with_qual else {}" not in src, (
        "a quant-only re-score can delete the judgement half again")


def test_build_context_has_no_flag_to_skip_the_cache():
    """The parameter is gone entirely - a flag that silently deletes data should not
    exist, and one that does nothing invites the next confusion."""
    sig = inspect.signature(engine.build_context)
    assert "with_qual" not in sig.parameters


def test_skip_qual_help_says_the_cache_is_still_read():
    from clab.runner import batch

    src = inspect.getsource(batch)
    assert "Cached judgement scores are still read" in src


def test_no_caller_passes_with_qual_anywhere():
    """Any surviving caller would now be a TypeError at runtime."""
    import pathlib

    root = pathlib.Path(engine.__file__).parent.parent
    offenders = []
    for p in root.rglob("*.py"):
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("f\""):
                continue          # the explanatory comments name the old parameter
            if "with_qual=" in line and "roll[" not in line:
                offenders.append(f"{p.name}: {stripped[:70]}")
    assert not offenders, f"still passing with_qual: {offenders}"


def test_the_evidence_pack_does_not_read_qual():
    """Why always-reading is safe: if the pack consulted ctx.qual, loading a company's
    previous scores would change its pack hash and invalidate every cached company."""
    from clab.qual import evidence

    assert ".qual" not in inspect.getsource(evidence)
