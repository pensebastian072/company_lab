"""ticker <-> CIK mapping from SEC company_tickers.json.

Verified live: 200, 795 KB, 10,398 entries, 0.32s.
Shape: {"0": {"cik_str": 1045810, "ticker": "NVDA", "title": "NVIDIA CORP"}, ...}

Two traps this module handles:

  - Class shares. EDGAR and yfinance write BRK-B / BF-B; Wikipedia writes
    BRK.B. normalize_ticker() collapses them onto the EDGAR form.
  - Several tickers share one CIK (GOOG/GOOGL, FOX/FOXA). CIK is therefore the
    join key for fundamentals and ticker is the key for market data. The UI
    table dedupes by CIK so a dual-class name is not double-counted in the
    ranking.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .. import config
from ..net import (SEC_LIMITER, atomic_write_gzip_json, http_get_json,
                   read_gzip_json)
from .base import Source


def normalize_ticker(ticker: str) -> str:
    """Wikipedia's BRK.B -> EDGAR/yfinance's BRK-B."""
    return ticker.strip().upper().replace(".", "-")


def pad_cik(cik: str | int) -> str:
    return str(int(cik)).zfill(10)


@dataclass(frozen=True)
class CikRecord:
    cik: str          # zero-padded 10 digits
    ticker: str
    title: str


class EdgarTickers(Source):
    source_id = "edgar_tickers"

    def _cache_path(self) -> Path:
        return config.EDGAR_TICKERS_FILE

    def _cache_ttl_hours(self) -> float:
        return config.TICKERS_TTL_DAYS * 24.0

    def _load_cache(self):
        return read_gzip_json(self._cache_path())

    def _write_cache(self, payload) -> None:
        atomic_write_gzip_json(self._cache_path(), payload)

    def _fetch_raw(self) -> dict:
        return http_get_json(config.EDGAR_TICKERS_URL, limiter=SEC_LIMITER)


_MAP_CACHE: dict[str, CikRecord] | None = None


def load_map(*, force: bool = False) -> dict[str, CikRecord]:
    """ticker -> CikRecord. Empty dict if the feed and cache are both unavailable."""
    global _MAP_CACHE
    if _MAP_CACHE is not None and not force:
        return _MAP_CACHE
    res = EdgarTickers().fetch(force=force)
    out: dict[str, CikRecord] = {}
    if isinstance(res.payload, dict):
        for row in res.payload.values():
            try:
                tkr = normalize_ticker(str(row["ticker"]))
                out[tkr] = CikRecord(pad_cik(row["cik_str"]), tkr, str(row.get("title", "")))
            except (KeyError, TypeError, ValueError):
                continue
    _MAP_CACHE = out
    return out


def cik_for(ticker: str, *, mapping: dict[str, CikRecord] | None = None) -> str | None:
    m = mapping if mapping is not None else load_map()
    rec = m.get(normalize_ticker(ticker))
    return rec.cik if rec else None
