"""The lock guard itself, asserted in both directions.

A guard that silently never fires is worse than no guard, and this repo has the worked
example: E34's check filtered on `s.get("note")` where the field was `threshold_note`,
read None for every row, and reported clean over 147 companies with real buybacks. So the
skip path is proven to fire AND the raise path is proven to still raise.
"""
from __future__ import annotations

import pytest

from conftest import skip_if_locked


def test_a_held_lock_skips_rather_than_failing():
    @skip_if_locked
    def locked():
        raise OSError('IO Error: Cannot open file "x.duckdb": The process cannot '
                      'access the file because it is being used by another process.')

    with pytest.raises(pytest.skip.Exception):
        locked()


def test_every_other_error_still_fails():
    """The narrow match is the point. A broad except here would hide exactly the wiring
    errors the live-catalog tests exist to catch."""
    @skip_if_locked
    def broken():
        raise ValueError("coverage collapsed to 0.0")

    with pytest.raises(ValueError):
        broken()


def test_a_passing_test_is_untouched():
    @skip_if_locked
    def fine():
        return 42

    assert fine() == 42
