"""Source ABC — the common contract for every feed.

Structure and failure semantics ported from copper_brain/copper_brain/sources/base.py.
The payload contract is widened: copper returns a tidy [date, series, value]
long frame, which is wrong for deeply nested JSON like EDGAR companyfacts, so
`payload` here is `dict | DataFrame | None`.

Three properties are load-bearing and must survive any refactor:
  1. fetch() NEVER raises. Errors become FetchResult(ok=False) carrying cache.
  2. A corrupt cache file degrades to re-fetch, not a crash.
  3. A cache-write failure never fails the request.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .. import config
from ..net import atomic_write_json, utc_now_iso


@dataclass
class FetchResult:
    """Outcome of one source pull: payload plus a freshness record."""

    source_id: str
    payload: Any = None                  # dict | pd.DataFrame | None
    ok: bool = True
    from_cache: bool = False
    stale: bool = False                  # served from cache past its TTL
    error: str | None = None
    data_through: str | None = None      # ISO date of the newest datum, if known
    fetched_at: str = field(default_factory=utc_now_iso)
    meta: dict = field(default_factory=dict)

    @property
    def age_days(self) -> int | None:
        if not self.data_through:
            return None
        try:
            last = datetime.fromisoformat(self.data_through).date()
        except ValueError:
            return None
        return (datetime.now(timezone.utc).date() - last).days

    def health(self) -> str:
        if not self.ok:
            return "error"
        if self.payload is None:
            return "empty"
        if self.stale:
            return "stale"
        age = self.age_days
        if age is not None and age > config.SOURCE_STALE_DAYS:
            return f"stale_{age}d"
        return "ok"

    def freshness_record(self) -> dict:
        return {
            "source": self.source_id,
            "ok": self.ok,
            "health": self.health(),
            "from_cache": self.from_cache,
            "data_through": self.data_through,
            "age_days": self.age_days,
            "fetched_at": self.fetched_at,
            "error": self.error,
        }


class Source(ABC):
    """Base class for a feed. Subclasses implement _fetch_raw() and cache paths."""

    source_id: str = "base"

    # ------------------------------------------------------------ subclass API
    @abstractmethod
    def _fetch_raw(self) -> Any:
        """Pull from the network. May raise; fetch() converts that to ok=False."""
        raise NotImplementedError

    def _cache_path(self) -> Path:
        raise NotImplementedError

    def _load_cache(self) -> Any:
        """Read the cache. MUST return None rather than raise on corruption."""
        return None

    def _write_cache(self, payload: Any) -> None:
        """Persist. MUST NOT raise - a cache failure never fails the request."""
        return None

    def _cache_ttl_hours(self) -> float | None:
        """None = the cached artifact is immutable and never expires."""
        return None

    def _is_cacheable(self, payload: Any) -> bool:
        """Refuse to cache data that is still moving (livevol.is_cacheable)."""
        return payload is not None

    def _data_through(self, payload: Any) -> str | None:
        return None

    # ------------------------------------------------------------ the contract
    def fetch(self, *, force: bool = False) -> FetchResult:
        """disk cache (free) -> network. Never raises."""
        from ..net import file_age_hours

        path = None
        try:
            path = self._cache_path()
        except NotImplementedError:
            pass

        if not force and path is not None and path.exists():
            ttl = self._cache_ttl_hours()
            age = file_age_hours(path)
            fresh = ttl is None or (age is not None and age <= ttl)
            if fresh:
                cached = self._load_cache()
                if cached is not None:
                    return FetchResult(
                        self.source_id, cached, ok=True, from_cache=True,
                        data_through=self._data_through(cached),
                    )
                # corrupt cache -> fall through and re-fetch

        try:
            payload = self._fetch_raw()
        except Exception as exc:  # noqa: BLE001 - log-and-degrade, never crash a crawl
            cached = self._load_cache() if path is not None and path.exists() else None
            return FetchResult(
                self.source_id, cached, ok=cached is not None, from_cache=cached is not None,
                stale=cached is not None, error=f"{type(exc).__name__}: {exc}",
                data_through=self._data_through(cached) if cached is not None else None,
            )

        if self._is_cacheable(payload):
            try:
                self._write_cache(payload)
            except Exception:  # noqa: BLE001 - deliberate: never fail on cache write
                pass
        return FetchResult(
            self.source_id, payload, ok=True, from_cache=False,
            data_through=self._data_through(payload),
        )


def write_freshness(records: list[dict]) -> None:
    """Per-source freshness manifest, atomic."""
    atomic_write_json(
        config.FRESHNESS_FILE,
        {"generated_at": utc_now_iso(), "sources": {r["source"]: r for r in records}},
    )
