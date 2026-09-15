"""Shared low-level primitives: atomic writes, TLS trust, rate limiting, HTTP.

ONE copy of each, deliberately. options_desk has three near-duplicate
_atomic_write implementations; this module is the single home here.

Failure semantics carried over from options_desk/desk/livevol.py:
  - a corrupt cache file degrades to re-fetch, never crashes;
  - a cache-write failure never fails the request.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import ssl
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import config


# --------------------------------------------------------------- time helpers
def utc_now_iso() -> str:
    """ISO8601, timezone-aware UTC. The `as_of` convention for every flag file."""
    return datetime.now(timezone.utc).isoformat()


def utc_today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def log_stamp() -> str:
    """Local time WITH its offset, for human-readable run logs only.

    Every stored `as_of` stays UTC - that is a data convention and comparisons depend
    on it. But the run logs had two clocks writing indistinguishable timestamps: the
    Python side stamped `utc_now_iso()[:19]` and run_clab.ps1 stamped a local
    `Get-Date -Format s`, both bare. `qual_20260816.log` therefore reads 12:15 -> 16:15
    -> 13:55 for a strictly monotonic sequence, and after 20:00 EDT the UTC date rolls
    over so entries carry TOMORROW's date inside a file named for today.

    The offset is the point. A bare local stamp would read the same as the bare UTC one
    it replaces and the next reader would have no way to tell which they were looking at.
    """
    # isoformat, not strftime("%z"): %z renders "-0400" while PowerShell's "zzz" renders
    # "-04:00", and two nearly-identical stamps is how this confusion started.
    return datetime.now().astimezone().isoformat(timespec="seconds")


# --------------------------------------------------------------- atomic writes
def atomic_write_text(path: Path, text: str) -> None:
    """Write via .tmp + replace: a kill mid-write cannot corrupt the target."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def atomic_write_json(path: Path, obj: Any, indent: int = 2) -> None:
    atomic_write_text(Path(path), json.dumps(obj, indent=indent, default=str, sort_keys=False))


def atomic_write_gzip_json(path: Path, obj: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(tmp, "wt", encoding="utf-8") as fh:
        json.dump(obj, fh, default=str)
    tmp.replace(path)


def atomic_write_gzip_bytes(path: Path, data: bytes) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(tmp, "wb") as fh:
        fh.write(data)
    tmp.replace(path)


def read_gzip_json(path: Path) -> Any | None:
    """Return None on any problem — a corrupt cache means re-fetch, not a crash."""
    try:
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:  # noqa: BLE001 - deliberate: corrupt cache degrades to miss
        return None


def read_gzip_bytes(path: Path) -> bytes | None:
    try:
        with gzip.open(path, "rb") as fh:
            return fh.read()
    except Exception:  # noqa: BLE001
        return None


def read_json(path: Path) -> Any | None:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


# --------------------------------------------------------------- cache keying
def cache_key(kind: str, params: dict) -> str:
    """Stable short hash of a request. Shape taken from livevol._cache_key."""
    blob = json.dumps({"kind": kind, "params": params}, sort_keys=True, default=str)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]


def sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()


def file_age_hours(path: Path) -> float | None:
    try:
        return (time.time() - Path(path).stat().st_mtime) / 3600.0
    except OSError:
        return None


def is_fresh(path: Path, ttl_hours: float) -> bool:
    age = file_age_hours(path)
    return age is not None and age <= ttl_hours


# --------------------------------------------------------------- TLS
_CERTS_TRUSTED = False


def trust_windows_certs() -> None:
    """Make HTTPS work behind this box's TLS-intercepting proxy (nllMonFltProxy).

    Verbatim port of alpaca_gpu_lab/src/data/alpaca_backfill.py::_trust_windows_certs.
    Called explicitly at the top of every entrypoint - NOT from config.py (which
    must stay import-safe) and NOT from the UI (which makes no outbound calls).

    Idempotent: repeated calls are cheap no-ops after the first.
    """
    global _CERTS_TRUSTED
    if _CERTS_TRUSTED:
        return
    try:
        import truststore

        truststore.inject_into_ssl()
    except ImportError:
        pass
    try:
        import certifi

        bundle = config.CA_BUNDLE
        bundle.parent.mkdir(parents=True, exist_ok=True)
        parts = [Path(certifi.where()).read_text(encoding="utf-8")]
        for store in ("ROOT", "CA"):
            for der, enc_type, _trust in ssl.enum_certificates(store):
                if enc_type == "x509_asn":
                    parts.append(ssl.DER_cert_to_PEM_cert(der))
        bundle.write_text("\n".join(parts), encoding="utf-8")
        for var in ("CURL_CA_BUNDLE", "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
            os.environ[var] = str(bundle)
    except Exception:  # noqa: BLE001 - never let cert plumbing kill a run
        pass
    _CERTS_TRUSTED = True


# --------------------------------------------------------------- rate limiting
class RateLimiter:
    """Monotonic-clock spacing limiter. SEC allows 10 req/s; we use 6."""

    def __init__(self, rps: float) -> None:
        self.min_interval = 1.0 / max(rps, 0.01)
        self._last = 0.0

    def wait(self) -> None:
        now = time.monotonic()
        gap = self.min_interval - (now - self._last)
        if gap > 0:
            time.sleep(gap)
        self._last = time.monotonic()


SEC_LIMITER = RateLimiter(config.SEC_RPS)


# --------------------------------------------------------------- HTTP
class HttpError(RuntimeError):
    def __init__(self, status: int | None, url: str, msg: str) -> None:
        super().__init__(f"HTTP {status} {url}: {msg}")
        self.status = status
        self.url = url


TRANSIENT_STATUS = {408, 425, 429, 500, 502, 503, 504}


def is_transient(exc: BaseException) -> bool:
    """Transient errors are worth retrying; permanent ones are not."""
    if isinstance(exc, HttpError):
        return exc.status is None or exc.status in TRANSIENT_STATUS
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code in TRANSIENT_STATUS
    return isinstance(exc, (urllib.error.URLError, TimeoutError, OSError))


def http_get(
    url: str,
    *,
    headers: dict | None = None,
    limiter: RateLimiter | None = None,
    timeout: float | None = None,
) -> bytes:
    """GET returning decoded bytes. Raises HttpError. Handles gzip transparently."""
    hdrs = {
        "User-Agent": config.SEC_USER_AGENT,
        "Accept-Encoding": "gzip",
        "Accept": "*/*",
    }
    if headers:
        hdrs.update(headers)
    if limiter is not None:
        limiter.wait()
    req = urllib.request.Request(url, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout or config.HTTP_TIMEOUT) as resp:
            raw = resp.read()
            if resp.headers.get("Content-Encoding", "").lower() == "gzip":
                raw = gzip.decompress(raw)
            return raw
    except urllib.error.HTTPError as exc:
        raise HttpError(exc.code, url, exc.reason or "") from exc
    except urllib.error.URLError as exc:
        raise HttpError(None, url, str(exc.reason)) from exc


def http_get_json(url: str, **kw) -> Any:
    return json.loads(http_get(url, **kw).decode("utf-8", errors="replace"))


def retry(fn, *, attempts: int | None = None, backoff: tuple | None = None):
    """Retry only transient failures. Permanent errors raise on the first try."""
    attempts = attempts or config.RETRY_TRANSIENT_ATTEMPTS
    backoff = backoff or config.RETRY_BACKOFF_SECONDS
    last: BaseException | None = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            last = exc
            if not is_transient(exc) or i == attempts - 1:
                raise
            time.sleep(backoff[min(i, len(backoff) - 1)])
    raise last  # pragma: no cover
