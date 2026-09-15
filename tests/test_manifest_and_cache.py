"""Manifest resume semantics, retry classification, and cache failure modes."""
from __future__ import annotations

import gzip
import urllib.error

import pytest

from clab import net
from clab.runner.manifest import FAILED, OK, Manifest, chunked
from clab.sources import edgar_tickers as et
from clab.sources.base import Source
from clab.sources.edgar_facts import filer_cik_from_accn


# ------------------------------------------------------------------ manifest
@pytest.fixture()
def man(tmp_path):
    return Manifest.load(tmp_path / "m.json", tier="sp500")


def test_manifest_round_trips_atomically(man, tmp_path):
    man.record_success("AAPL", coverage=0.9, composite=72)
    man.save()
    assert not list(tmp_path.glob("*.tmp"))       # tmp is renamed, never left behind
    again = Manifest.load(tmp_path / "m.json")
    assert again.status_of("AAPL") == OK
    assert again.data["symbols"]["AAPL"]["composite"] == 72


def test_manifest_rejects_a_foreign_version(tmp_path):
    p = tmp_path / "m.json"
    p.write_text('{"version": 999, "symbols": {"X": {"status": "ok"}}}', encoding="utf-8")
    m = Manifest.load(p)
    assert m.data["version"] == 1
    assert m.data["symbols"] == {}                # a stale schema is discarded, not trusted


def test_resume_skips_completed_symbols(man):
    man.record_success("AAPL")
    todo = man.pending(["AAPL", "MSFT", "NVDA"])
    assert todo == ["MSFT", "NVDA"]


def test_resume_preserves_universe_order(man):
    man.record_success("MSFT")
    assert man.pending(["AAPL", "MSFT", "NVDA", "AMZN"]) == ["AAPL", "NVDA", "AMZN"]


def test_permanent_failures_stay_out_until_asked_for(man):
    man.record_failure("BADCO", "edgar_facts", "HTTPError: 404", transient=False)
    assert man.pending(["BADCO", "AAPL"]) == ["AAPL"]
    assert man.pending(["BADCO", "AAPL"], retry_failed=True) == ["BADCO", "AAPL"]


def test_transient_failures_come_back_automatically(man):
    man.record_failure("AAPL", "yf_market", "URLError: timeout", transient=True)
    assert "AAPL" in man.pending(["AAPL"])


def test_attempts_increment_per_failure(man):
    for _ in range(3):
        man.record_failure("X", "edgar_facts", "boom")
    assert man.data["symbols"]["X"]["attempts"] == 3
    assert man.status_of("X") == FAILED


def test_stage_is_the_resume_granularity(man):
    man.record_stage("AAPL", "yf_market", note="halfway")
    assert man.entry("AAPL")["stage"] == "yf_market"


def test_summary_counts(man):
    man.record_success("A", coverage=0.9, elapsed_s=2.0)
    man.record_success("B", coverage=0.7, elapsed_s=4.0)
    man.record_failure("C", "x", "y")
    s = man.summary()
    assert s["n_ok"] == 2 and s["n_failed"] == 1
    assert s["mean_elapsed_s"] == pytest.approx(3.0)


def test_chunked_batches_of_ten():
    assert chunked(list(range(25)), 10) == [list(range(10)), list(range(10, 20)),
                                            [20, 21, 22, 23, 24]]
    assert chunked([], 10) == []


# ------------------------------------------------------------------ retry classification
def test_transient_vs_permanent():
    assert net.is_transient(net.HttpError(503, "u", "busy"))
    assert net.is_transient(net.HttpError(429, "u", "slow down"))
    assert net.is_transient(net.HttpError(None, "u", "connection reset"))
    assert net.is_transient(urllib.error.URLError("no route"))
    assert net.is_transient(TimeoutError())
    assert not net.is_transient(net.HttpError(404, "u", "gone"))
    assert not net.is_transient(net.HttpError(403, "u", "forbidden"))
    assert not net.is_transient(ValueError("bad payload"))


def test_retry_gives_up_on_permanent_errors_immediately():
    calls = []

    def boom():
        calls.append(1)
        raise net.HttpError(404, "u", "gone")

    with pytest.raises(net.HttpError):
        net.retry(boom, attempts=3, backoff=(0, 0, 0))
    assert len(calls) == 1


def test_retry_retries_transient_then_succeeds():
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise net.HttpError(503, "u", "busy")
        return "ok"

    assert net.retry(flaky, attempts=3, backoff=(0, 0, 0)) == "ok"
    assert len(calls) == 3


# ------------------------------------------------------------------ cache behaviour
class FakeSource(Source):
    source_id = "fake"

    def __init__(self, path, payload=None, fail=False):
        self.path = path
        self.payload = payload or {"v": 1}
        self.fail = fail
        self.calls = 0

    def _cache_path(self):
        return self.path

    def _cache_ttl_hours(self):
        return 24.0

    def _load_cache(self):
        return net.read_gzip_json(self.path)

    def _write_cache(self, payload):
        net.atomic_write_gzip_json(self.path, payload)

    def _fetch_raw(self):
        self.calls += 1
        if self.fail:
            raise net.HttpError(503, "u", "busy")
        return self.payload


def test_second_fetch_is_served_from_disk(tmp_path):
    s = FakeSource(tmp_path / "c.json.gz")
    assert s.fetch().from_cache is False
    r2 = FakeSource(tmp_path / "c.json.gz").fetch()
    assert r2.from_cache is True and r2.payload == {"v": 1}


def test_corrupt_cache_refetches_instead_of_crashing(tmp_path):
    p = tmp_path / "c.json.gz"
    p.write_bytes(b"not gzip at all")
    s = FakeSource(p, payload={"v": 2})
    res = s.fetch()
    assert res.ok and res.payload == {"v": 2}
    assert s.calls == 1


def test_unwritable_cache_still_returns_data(tmp_path, monkeypatch):
    s = FakeSource(tmp_path / "c.json.gz")

    def explode(*_a, **_k):
        raise OSError("disk full")

    monkeypatch.setattr(s, "_write_cache", explode)
    res = s.fetch()
    assert res.ok and res.payload == {"v": 1}        # a cache write never fails a request


def test_fresh_cache_short_circuits_before_the_network(tmp_path):
    p = tmp_path / "c.json.gz"
    net.atomic_write_gzip_json(p, {"v": "old"})
    s = FakeSource(p, fail=True)
    res = s.fetch()
    assert res.payload == {"v": "old"} and res.from_cache and res.ok
    assert s.calls == 0          # a fresh cache is never re-paid for


def test_network_failure_falls_back_to_stale_cache(tmp_path):
    """force=True skips the cache read, so this exercises the network path and the
    degrade-to-cache fallback behind it."""
    p = tmp_path / "c.json.gz"
    net.atomic_write_gzip_json(p, {"v": "old"})
    res = FakeSource(p, fail=True).fetch(force=True)
    assert res.payload == {"v": "old"}
    assert res.stale and res.from_cache and res.error


def test_network_failure_with_no_cache_reports_not_ok(tmp_path):
    res = FakeSource(tmp_path / "missing.json.gz", fail=True).fetch()
    assert res.ok is False and res.payload is None and "HttpError" in res.error


def test_force_bypasses_a_fresh_cache(tmp_path):
    p = tmp_path / "c.json.gz"
    net.atomic_write_gzip_json(p, {"v": "old"})
    s = FakeSource(p, payload={"v": "new"})
    assert s.fetch(force=True).payload == {"v": "new"}


def test_gzip_read_of_a_truncated_file_returns_none(tmp_path):
    p = tmp_path / "t.gz"
    good = gzip.compress(b'{"a": 1}')
    p.write_bytes(good[: len(good) // 2])
    assert net.read_gzip_json(p) is None


def test_atomic_write_leaves_no_temp_file(tmp_path):
    p = tmp_path / "out.json"
    net.atomic_write_json(p, {"a": 1})
    assert p.exists() and not list(tmp_path.glob("*.tmp"))


# ------------------------------------------------------------------ ticker mapping
def test_class_share_normalization():
    assert et.normalize_ticker("brk.b") == "BRK-B"
    assert et.normalize_ticker(" bf.b ") == "BF-B"
    assert et.normalize_ticker("AAPL") == "AAPL"


def test_cik_zero_padding():
    assert et.pad_cik(320193) == "0000320193"
    assert et.pad_cik("1045810") == "0001045810"


def test_predecessor_cik_read_from_accession_prefix():
    """Measured on XOM: company_tickers maps it to a new registrant CIK whose
    companyfacts holds a handful of rows, while the accessions on those rows begin
    with the historical filer's CIK."""
    payload = {"facts": {"us-gaap": {"Revenues": {"units": {"USD": [
        {"start": "2026-01-01", "end": "2026-03-31", "val": 1, "filed": "2026-05-01",
         "accn": "0000034088-26-000093"}]}}}}}
    assert filer_cik_from_accn(payload) == "0000034088"


def test_predecessor_cik_none_when_absent():
    assert filer_cik_from_accn({"facts": {}}) is None
    assert filer_cik_from_accn({}) is None
