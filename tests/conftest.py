import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import functools

import pytest

#: Six tests deliberately assert against the LIVE catalog rather than a fixture, because
#: they pin measured results - the E42 arm comparison, the workbook saving with real rows -
#: so a regression is visible instead of merely possible. That is a design choice and it
#: stays.
#:
#: What does NOT stay is a lock reading as a failure. DuckDB takes a single-writer file
#: lock, so while the other session of this two-chat setup writes the store, these tests
#: raise `IO Error: ... being used by another process`. On 2026-09-09 that produced five
#: red tests in the other session - including `test_sheet_order_and_external` - which went
#: green on a re-run, at the same moment a bulk write in this session was failing mid-loop
#: against the same lock. Neither session could see the cause from its own output, and the
#: temptation on both sides was to shrug at a transient.
#:
#: A lock says nothing about correctness, so it SKIPS. Everything else still fails: the
#: match below is deliberately narrow, because a broad except here would hide exactly the
#: wiring errors the live-catalog tests exist to catch.
_LOCK_SIGNATURES = (
    "being used by another process",
    "could not set lock",
    "conflicting lock",
)


def skip_if_locked(fn):
    """Decorate a live-catalog test so a held lock SKIPS it and nothing else does.

    It wraps the whole test body on purpose. `ExternalStore()` does not touch the file -
    `store.py` opens a connection per call and never holds one - so the lock does not
    raise on construction, it raises somewhere inside the first query. A wrapper around
    the constructor would have looked correct and caught nothing.
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:                   # noqa: BLE001 - re-raised below
            text = str(exc)
            if any(sig in text for sig in _LOCK_SIGNATURES):
                pytest.skip(f"live catalog is locked by another process: {text[:140]}")
            raise
    return wrapper
