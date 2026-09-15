"""The watchdog checks added after 2026-08-16, when two failures went unwatched.

Neither had any detector at all: the daily fold was refused by the probe gate and the
task exited 0, and a company scored during a yfinance HTTP/2 blip was cached forever
with no price in its fact sheet. The watchdog's exit code is what lands in Task
Scheduler's last-result column, so that is where both belong.
"""
from __future__ import annotations

import gzip
import json
import os
import time

import pytest

from clab import config
from clab.runner import watchdog


@pytest.fixture()
def dirs(tmp_path, monkeypatch):
    qual = tmp_path / "qual"
    yf = tmp_path / "yf"
    qual.mkdir()
    yf.mkdir()
    monkeypatch.setattr(config, "QUAL_DIR", qual)
    monkeypatch.setattr(config, "YF_DIR", yf)
    return qual, yf


def _market(yf_dir, ticker, *, price):
    d = yf_dir / ticker
    d.mkdir()
    payload = {"ticker": ticker, "ok_endpoints": 8,
               "info": {"currentPrice": price} if price is not None else {}}
    with gzip.open(d / "market_2026-08-16.json.gz", "wt", encoding="utf-8") as fh:
        json.dump(payload, fh)


# ------------------------------------------------- degraded evidence detection
def test_a_company_with_no_price_is_reported(dirs):
    _, yf = dirs
    _market(yf, "AAA", price=101.5)
    _market(yf, "BBB", price=None)
    assert watchdog._companies_without_a_price() == ["BBB"]


def test_a_priced_universe_reports_nothing(dirs):
    _, yf = dirs
    _market(yf, "AAA", price=1.0)
    _market(yf, "BBB", price=2.0)
    assert watchdog._companies_without_a_price() == []


def test_an_unreadable_payload_is_skipped_not_crashed(dirs):
    _, yf = dirs
    d = yf / "AAA"
    d.mkdir()
    (d / "market_2026-08-16.json.gz").write_bytes(b"not gzip")
    corrupt = []
    assert watchdog._companies_without_a_price(corrupt) == []
    assert corrupt == ["AAA"]


def test_a_TRUNCATED_gzip_does_not_crash_the_watchdog(dirs):
    """The case the first test missed, and the box hit for real.

    `b"not gzip"` raises BadGzipFile, an OSError, which the original `except
    (OSError, ValueError)` caught. A gzip with a valid header and a truncated body
    raises zlib.error, which is NEITHER - and it took the whole watchdog down, so
    nothing was reported about the other 1,496 companies.
    """
    _, yf = dirs
    d = yf / "AAA"
    d.mkdir()
    good = gzip.compress(json.dumps({"info": {"currentPrice": 10}}).encode())
    (d / "market_2026-08-16.json.gz").write_bytes(good[:len(good) // 2])   # truncated

    corrupt = []
    assert watchdog._companies_without_a_price(corrupt) == []
    assert corrupt == ["AAA"]


def test_a_corrupt_payload_is_reported_with_its_fix(dirs, monkeypatch):
    _, yf = dirs
    d = yf / "AAA"
    d.mkdir()
    good = gzip.compress(json.dumps({"info": {"currentPrice": 10}}).encode())
    (d / "market_2026-08-16.json.gz").write_bytes(good[:len(good) // 2])
    monkeypatch.setattr("clab.runner.fold_qual.stale_tickers", lambda: [])

    found = [f for f in watchdog._qual_findings() if "CORRUPT" in f]
    assert found and "AAA" in found[0] and "--force" in found[0]


# ------------------------------------------------------- the stale-fold check
def test_a_running_batch_does_not_trigger_the_stale_warning(dirs, monkeypatch):
    """The cache is legitimately ahead while a qual batch is writing into it."""
    qual, _ = dirs
    (qual / "0000000001_BQ_x.json").write_text("{}", encoding="utf-8")   # just written
    monkeypatch.setattr("clab.runner.fold_qual.stale_tickers", lambda: ["AAA", "BBB"])
    assert not [f for f in watchdog._qual_findings() if "behind their cache" in f]


def test_a_quiet_cache_that_is_ahead_is_reported(dirs, monkeypatch):
    qual, _ = dirs
    p = qual / "0000000001_BQ_x.json"
    p.write_text("{}", encoding="utf-8")
    old = time.time() - (watchdog.QUAL_QUIET_HOURS + 1) * 3600
    os.utime(p, (old, old))
    monkeypatch.setattr("clab.runner.fold_qual.stale_tickers", lambda: ["AAA", "BBB"])

    found = [f for f in watchdog._qual_findings() if "behind their cache" in f]
    assert found and "2 scorecards" in found[0]


def _healthy_flag(monkeypatch, tmp_path):
    """Everything else green, so a test can isolate one finding."""
    monkeypatch.setattr(watchdog, "read_json", lambda p: {
        "as_of": watchdog.utc_now_iso(), "status": "ok",
        "symbols_scored": 1497, "symbols_failed": 0, "coverage_median": 0.94,
    })
    parquet = tmp_path / "scores.parquet"
    parquet.write_bytes(b"x")
    snaps = tmp_path / "snapshots"
    snaps.mkdir()
    (snaps / "scores_2026-08-15.parquet").write_bytes(b"x")
    monkeypatch.setattr(config, "SCORES_PARQUET", parquet)
    monkeypatch.setattr(config, "SNAPSHOT_DIR", snaps)


def test_a_healthy_box_is_OK(dirs, tmp_path, monkeypatch):
    """The control: without this, a MISS assertion proves nothing."""
    _healthy_flag(monkeypatch, tmp_path)
    monkeypatch.setattr(watchdog, "_qual_findings", lambda: [])
    assert watchdog.check()["status"] == watchdog.OK


def test_being_behind_the_cache_makes_the_watchdog_exit_non_zero(dirs, tmp_path,
                                                                monkeypatch):
    """MISS, not WARN, and it must reach main()'s exit code.

    On 2026-08-16 the only signal was a log line nobody reads. The whole point of
    routing this through the watchdog is Task Scheduler's last-result column, so the
    test asserts the exit code, not just the wording.
    """
    _healthy_flag(monkeypatch, tmp_path)
    monkeypatch.setattr(
        watchdog, "_qual_findings",
        lambda: ["99 scorecards are behind their cache (AAA...) - the fold did not run"])

    res = watchdog.check()
    assert res["status"] == watchdog.MISS
    assert watchdog.main(["--quiet"]) == 1


def test_a_degraded_price_is_only_a_WARN(dirs, tmp_path, monkeypatch):
    """It costs 5 companies' fact sheets, not the run. Must not exit non-zero."""
    _healthy_flag(monkeypatch, tmp_path)
    monkeypatch.setattr(
        watchdog, "_qual_findings",
        lambda: ["5 companies have no usable price in their newest market payload "
                 "(AR, ARWR) - their cached judgement was scored on a degraded "
                 "fact sheet"])

    assert watchdog.check()["status"] == watchdog.WARN
    assert watchdog.main(["--quiet"]) == 0


def test_a_broken_fold_check_never_breaks_the_watchdog(dirs, monkeypatch):
    qual, _ = dirs
    p = qual / "0000000001_BQ_x.json"
    p.write_text("{}", encoding="utf-8")
    old = time.time() - (watchdog.QUAL_QUIET_HOURS + 1) * 3600
    os.utime(p, (old, old))

    def _boom():
        raise RuntimeError("scorer import exploded")

    monkeypatch.setattr("clab.runner.fold_qual.stale_tickers", _boom)
    found = watchdog._qual_findings()
    assert any("could not check the qual fold" in f for f in found)


def test_an_empty_cache_is_not_a_finding(dirs, monkeypatch):
    monkeypatch.setattr("clab.runner.fold_qual.stale_tickers", lambda: ["AAA"])
    assert watchdog._cache_quiet_hours() is None
    assert not [f for f in watchdog._qual_findings() if "behind their cache" in f]
