"""The write lease, added after two batches stomped each other on 2026-08-16.

Seven companies failed on `<scorecard>.json.tmp`, scores.parquet failed its atomic
rename and declared itself STALE, and a completed 302-company run exited 1 writing the
state flag. The GPU lease did not help: neither process touches the GPU.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pytest

from clab.net import atomic_write_json
from clab.runner import lease as lease_mod


@pytest.fixture()
def lock(tmp_path):
    return tmp_path / "write_lease.json"


def _write(path, *, pid, minutes=60):
    atomic_write_json(path, {
        "pid": pid, "label": "batch",
        "expires_at": (datetime.now(timezone.utc)
                       + timedelta(minutes=minutes)).isoformat(),
    })


def test_an_uncontended_lease_is_granted(lock):
    with lease_mod.advisory_lease(lock) as held:
        assert held
        assert lock.exists()
    assert not lock.exists()          # released on the way out


def test_a_live_foreign_holder_blocks(lock, monkeypatch):
    _write(lock, pid=999999)
    monkeypatch.setattr(lease_mod, "pid_alive", lambda pid: True)
    with lease_mod.advisory_lease(lock, wait=False) as held:
        assert held is False


def test_the_SAME_process_is_re_entrant(lock):
    """fold_qual calls batch.main() in-process; a nested acquire must not deadlock."""
    _write(lock, pid=os.getpid())
    with lease_mod.advisory_lease(lock, wait=False) as held:
        assert held is True


def test_a_dead_holder_does_not_deadlock_the_pipeline(lock, monkeypatch):
    """This box reboots uncleanly. A killed batch must not block every future run."""
    _write(lock, pid=999999)
    monkeypatch.setattr(lease_mod, "pid_alive", lambda pid: False)
    with lease_mod.advisory_lease(lock, wait=False) as held:
        assert held is True


def test_an_expired_lease_is_ignored(lock):
    atomic_write_json(lock, {
        "pid": 999999,
        "expires_at": (datetime.now(timezone.utc)
                       - timedelta(minutes=5)).isoformat(),
    })
    with lease_mod.advisory_lease(lock, wait=False) as held:
        assert held is True


def test_a_lease_with_no_expiry_is_treated_as_expired(lock):
    """A malformed lease must fail OPEN, not wedge the daily task forever."""
    atomic_write_json(lock, {"pid": 999999})
    with lease_mod.advisory_lease(lock, wait=False) as held:
        assert held is True


def test_releasing_does_not_delete_someone_elses_lease(lock, monkeypatch):
    """If our TTL lapsed and another process took over, we must not unlink theirs."""
    with lease_mod.advisory_lease(lock) as held:
        assert held
        _write(lock, pid=999999)      # someone else took it while we ran
    assert lock.exists()              # still theirs


def test_batch_run_refuses_rather_than_writing_concurrently(monkeypatch, tmp_path):
    """The whole point: a blocked batch returns ok=False instead of corrupting data."""
    from clab import config
    from clab.runner import batch as batch_mod

    lock = tmp_path / "wl.json"
    _write(lock, pid=999999)
    monkeypatch.setattr(config, "WRITE_LEASE", lock)
    monkeypatch.setattr(config, "WRITE_LEASE_WAIT_MINUTES", 0)
    monkeypatch.setattr(lease_mod, "pid_alive", lambda pid: True)

    def _boom(**kwargs):
        raise AssertionError("the crawl must not start while the lease is held")

    monkeypatch.setattr(batch_mod, "_run_locked", _boom)

    res = batch_mod.run(tier="sp500")
    assert res["ok"] is False
    assert "write lease" in res["error"]


def test_batch_run_proceeds_when_free(monkeypatch, tmp_path):
    from clab import config
    from clab.runner import batch as batch_mod

    monkeypatch.setattr(config, "WRITE_LEASE", tmp_path / "free.json")
    monkeypatch.setattr(batch_mod, "_run_locked", lambda **kw: {"ok": True, "kw": kw})

    res = batch_mod.run(tier="sp600", limit=5)
    assert res["ok"] is True
    assert res["kw"]["tier"] == "sp600" and res["kw"]["limit"] == 5
