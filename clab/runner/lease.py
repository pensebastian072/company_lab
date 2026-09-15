"""Advisory file leases: one implementation, two users.

The GPU lease already existed in `clab/qual/ollama.py` and works. What did not exist was
anything protecting the DATA path, and on 2026-08-16 that cost real work: a qual fill's
fold and a second batch launched while it was still running raced each other, and

  * seven companies failed with PermissionError on `<scorecard>.json.tmp`,
  * `scores.parquet` failed its atomic rename and reported itself STALE,
  * the fill's final `write_state_flag` crashed, so a completed 302-company run exited 1.

A GPU lease does not help here: `batch` and `fold_qual` never touch the GPU, so both were
free to run and both wrote the same files. The lock has to be on the writes.

The TTL is what makes an advisory lease safe on this box. A process killed by one of the
box's unclean reboots cannot deadlock the pipeline forever - it holds the lease only
until it expires, and a dead PID is detected before that.
"""
from __future__ import annotations

import os
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from ..net import atomic_write_json, read_json, utc_now_iso


def _expired(lease: dict) -> bool:
    exp = lease.get("expires_at")
    if not exp:
        return True
    try:
        when = datetime.fromisoformat(exp)
    except (TypeError, ValueError):
        return True
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) > when


def pid_alive(pid: int) -> bool:
    try:
        import ctypes
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if not handle:
            return False
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    except Exception:      # noqa: BLE001 - unknown means assume alive; the TTL still frees it
        return True


def holder(path) -> dict | None:
    """The current live lease on `path`, or None if absent, expired or dead."""
    lease = read_json(path)
    if not isinstance(lease, dict):
        return None
    if _expired(lease):
        return None
    pid = lease.get("pid")
    if isinstance(pid, int) and pid != os.getpid() and not pid_alive(pid):
        return None
    return lease


@contextmanager
def advisory_lease(path, *, minutes: float = 120.0, wait: bool = False,
                   poll_seconds: float = 15.0, max_wait_minutes: float = 0.0,
                   label: str = "", on_wait=None):
    """Yields True when held, False when someone else holds it.

    Re-entrant for the SAME process: `fold_qual` calls `batch.main()` in-process, so a
    nested acquisition must not deadlock against itself.
    """
    deadline = time.monotonic() + max_wait_minutes * 60
    announced = False
    while True:
        h = holder(path)
        if h is None or h.get("pid") == os.getpid():
            break
        if not wait or time.monotonic() > deadline:
            yield False
            return
        if on_wait and not announced:
            on_wait(h)
            announced = True
        time.sleep(poll_seconds)

    lease = {
        "pid": os.getpid(),
        "repo": "company_lab",
        "label": label,
        "acquired_at": utc_now_iso(),
        "expires_at": (datetime.now(timezone.utc)
                       + timedelta(minutes=minutes)).isoformat(),
    }
    try:
        atomic_write_json(path, lease)
    except Exception:      # noqa: BLE001 - an unwritable lease must not block the work
        pass
    try:
        yield True
    finally:
        try:
            current = read_json(path)
            if isinstance(current, dict) and current.get("pid") == os.getpid():
                path.unlink(missing_ok=True)
        except OSError:
            pass


def renew(path, *, minutes: float = 120.0) -> None:
    """Extend our own lease so a long batch does not expire under itself."""
    current = read_json(path)
    if isinstance(current, dict) and current.get("pid") == os.getpid():
        current["expires_at"] = (datetime.now(timezone.utc)
                                 + timedelta(minutes=minutes)).isoformat()
        try:
            atomic_write_json(path, current)
        except Exception:  # noqa: BLE001
            pass
