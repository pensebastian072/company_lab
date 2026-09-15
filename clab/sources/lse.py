"""London Strategic Edge vault client — HTTP history, reference datasets, exports.

One key serves the HTTP API and the live WebSocket. Key lives in `secrets/lse.json`,
which is gitignored; nothing in this module logs or returns it.

Quota is by BYTES, not calls: 50 GB/month, 16 GB/week, 200 calls/min, 5,000 rows per
request, 2 concurrent, 5 exports/hour, unlimited history depth. That still falls under
the box rule - a request must never be paid for twice - so every response is cached to
disk on D: and replayed free.

MEASURED CHARACTERISTICS (2026-08-11), because they decide what this source may be
used for:

  * Daily closes agree with the dividend-adjusted yfinance store to within ~1-2%, with a
    consistent POSITIVE offset that scales with dividend yield (NVDA +0.34%, AAPL +0.92%,
    MSFT +1.68%). LSE closes are split-adjusted but NOT dividend-adjusted. Usable on
    their own; **never mix them into a yfinance-based series**, which would inject a
    systematic bias that looks like alpha.
  * Volume is a PARTIAL feed and is not usable: 56-70% of consolidated volume for
    AAPL/MSFT and **4.4%** for NVDA. Same failure mode as Alpaca's IEX feed. Do not
    compute dollar volume, liquidity screens or volume z-scores from this.
  * Coverage is CURRENT LISTINGS ONLY. ATVI, CELG and AET return zero candles and zero
    splits, so this does NOT help the survivorship problem; `D:\\ohlcv_1m` remains the
    only delisted price source on this box.
  * Candle history begins around 2015-2016 - shallower than the 10y yfinance store.
  * `trade_type` is NOT honoured as a query parameter on /ref/insider_trades. Filter
    client-side; `insider_trades` mixes Form 4 corporate filings with congressional
    (senate/house) disclosures and conflating them would be a serious error.

What it is genuinely good for, in order:
  1. `insider_trades` - 11.3M rows back to 2003 with reporting_name, type_of_owner,
     securities_transacted, securities_owned and the SEC URL. Real data for the
     Management component, which currently guesses ownership via the LLM.
  2. `options_chain` / `options_flow` (194M rows) - relevant to options_desk, not here.
  3. `dividends` (1970+), `stock_splits` (1970+), `financial_reports` (2013+),
     `economic_calendar`, `cot`, `bond_yields` - reference and macro.
"""
from __future__ import annotations

import json
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .. import config
from ..net import (atomic_write_gzip_json, cache_key, http_get_json, is_fresh,
                   read_gzip_json)

BASE = "https://api.londonstrategicedge.com/vault"
WS_URL = "wss://data-ws.londonstrategicedge.com"
SECRET_FILE = config.BASE_DIR / "secrets" / "lse.json"
CACHE_DIR = config.DATA_ROOT / "lse"

MAX_ROWS_PER_REQUEST = 5000
DEFAULT_TTL_HOURS = 24 * 7          # reference data moves slowly
CATALOG_TTL_HOURS = 24

#: /ref/{dataset} names, from /meta
REF_DATASETS = ("bond_yields", "company_profiles", "cot", "dividends",
                "economic_calendar", "financial_reports", "insider_trades",
                "stock_fundamentals", "stock_splits")

#: insider_trades mixes sources; these are the congressional ones, which are NOT
#: corporate insider activity and must not be counted as such
CONGRESSIONAL_TRADE_TYPES = ("senate", "house")


class LseUnavailable(RuntimeError):
    pass


@dataclass
class Quota:
    bytes_used_month: int = 0
    bytes_cap_month: int = 0
    bytes_used_week: int = 0
    bytes_cap_week: int = 0
    calls_per_minute: int = 0
    max_rows_per_request: int = MAX_ROWS_PER_REQUEST
    raw: dict = None  # type: ignore[assignment]

    @property
    def month_used_pct(self) -> float | None:
        return (self.bytes_used_month / self.bytes_cap_month
                if self.bytes_cap_month else None)


def api_key() -> str:
    """Read the key from the gitignored secrets file. Never logged."""
    try:
        return json.loads(SECRET_FILE.read_text(encoding="utf-8"))["api_key"]
    except Exception as exc:  # noqa: BLE001
        raise LseUnavailable(
            f"no usable {SECRET_FILE.name} in secrets/ ({type(exc).__name__})") from exc


def available() -> bool:
    try:
        api_key()
        return True
    except LseUnavailable:
        return False


def _cache_path(path: str, params: dict) -> Path:
    h = cache_key(path, params)
    safe = path.strip("/").replace("/", "_") or "root"
    return CACHE_DIR / safe / f"{safe}_{h}.json.gz"


def get(path: str, *, ttl_hours: float = DEFAULT_TTL_HOURS,
        force: bool = False, **params) -> Any:
    """GET a vault endpoint, disk-cached. Raises LseUnavailable on failure.

    Caching is not an optimisation here - it is the box rule that a metered request is
    never paid for twice.
    """
    params = {k: v for k, v in params.items() if v is not None}
    cp = _cache_path(path, params)
    if not force and cp.exists() and is_fresh(cp, ttl_hours):
        cached = read_gzip_json(cp)
        if cached is not None:
            return cached
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    try:
        data = http_get_json(url, headers={"x-api-key": api_key(),
                                           "Accept": "application/json"},
                             timeout=config.HTTP_TIMEOUT * 3)
    except Exception as exc:  # noqa: BLE001
        stale = read_gzip_json(cp) if cp.exists() else None
        if stale is not None:
            return stale
        raise LseUnavailable(f"{type(exc).__name__}: {exc}") from exc
    try:
        atomic_write_gzip_json(cp, data)
    except Exception:  # noqa: BLE001 - a cache write must never fail the request
        pass
    return data


def usage(*, force: bool = True) -> Quota:
    d = get("/usage", ttl_hours=0.25, force=force)
    return Quota(
        bytes_used_month=d.get("bytes_used_month", 0),
        bytes_cap_month=d.get("bytes_cap_month", 0),
        bytes_used_week=d.get("bytes_used_week", 0),
        bytes_cap_week=d.get("bytes_cap_week", 0),
        calls_per_minute=d.get("calls_per_minute", 0),
        max_rows_per_request=d.get("max_rows_per_request", MAX_ROWS_PER_REQUEST),
        raw=d,
    )


def meta() -> dict:
    return get("/meta", ttl_hours=CATALOG_TTL_HOURS)


def reference() -> list[dict]:
    return get("/reference", ttl_hours=CATALOG_TTL_HOURS)


def catalog(**params) -> list[dict]:
    return get("/catalog", ttl_hours=CATALOG_TTL_HOURS, **params)


def ref(dataset: str, *, symbol: str | None = None, limit: int = MAX_ROWS_PER_REQUEST,
        **params) -> list[dict]:
    """A reference dataset. `limit` is capped by the plan at 5,000 rows per request."""
    if dataset not in REF_DATASETS:
        raise ValueError(f"unknown reference dataset {dataset!r}; "
                         f"expected one of {REF_DATASETS}")
    rows = get(f"/ref/{dataset}", symbol=symbol,
               limit=min(limit, MAX_ROWS_PER_REQUEST), **params)
    return rows if isinstance(rows, list) else []


#: fields that identify a real Form 4 transaction. `id` and `created_at` are NOT in it:
#: the feed re-ingests the same filing many times, each copy with a fresh id and
#: timestamp. Measured 2026-08-13 on AAPL: 4,980 corporate rows collapsed to 27 real
#: transactions, and ONE transaction (Parekh Kevan, 500 shares, 2025-10-16) appeared 320
#: times under 160 distinct created_at values. Counting rows without this key would
#: inflate any insider signal by roughly 160x and manufacture "cluster buying" out of
#: nothing.
INSIDER_IDENTITY_FIELDS = ("reporting_cik", "company_cik", "symbol", "transaction_date",
                           "filing_date", "transaction_type",
                           "acquisition_or_disposition", "securities_transacted",
                           "price", "securities_owned")


def dedupe_insider_rows(rows: list[dict]) -> list[dict]:
    """Collapse the feed's re-ingested copies to one row per real transaction.

    Keeps the EARLIEST `created_at` in each group, so the retained row is the first time
    the vendor saw the filing rather than an arbitrary later copy.
    """
    best: dict[tuple, dict] = {}
    for r in rows:
        key = tuple(str(r.get(f)) for f in INSIDER_IDENTITY_FIELDS)
        prev = best.get(key)
        if prev is None or str(r.get("created_at") or "") < str(prev.get("created_at") or ""):
            best[key] = r
    return list(best.values())


def insider_trades(symbol: str, *, limit: int = MAX_ROWS_PER_REQUEST,
                   corporate_only: bool = True, dedupe: bool = True,
                   start: str | None = None, end: str | None = None) -> list[dict]:
    """Form 4 corporate insider rows for one symbol, deduplicated.

    `corporate_only` filters out senate/house disclosures CLIENT-SIDE, because the
    `trade_type` query parameter is silently ignored by the API. Counting a senator's
    purchase as company-insider buying would be a serious misreading.

    `dedupe` is on by default and is not optional in any honest use - see
    INSIDER_IDENTITY_FIELDS for the measurement behind it.

    `start`/`end` are the ONLY working filter parameters on this endpoint (offset, page,
    from/to, date_from, year and sort are all silently ignored), and they filter on the
    TRANSACTION date. There is no way to page past the 5,000-row cap, so a symbol with
    more rows than that in a window is truncated - walk history in date windows instead.
    """
    rows = ref("insider_trades", symbol=symbol, limit=limit, start=start, end=end)
    if corporate_only:
        rows = [r for r in rows
                if str(r.get("trade_type", "")).lower() not in CONGRESSIONAL_TRADE_TYPES]
    return dedupe_insider_rows(rows) if dedupe else rows


def candles(symbol: str, *, dataset: str = "stocks", timeframe: str = "1d",
            start: str | None = None, end: str | None = None,
            limit: int = MAX_ROWS_PER_REQUEST) -> list[dict]:
    """OHLCV candles. Split-adjusted, NOT dividend-adjusted; volume is partial.

    See the module docstring before using these for anything: do not mix the closes
    into a dividend-adjusted series, and do not use the volume at all.
    """
    rows = get("/candles", dataset=dataset, symbol=symbol, timeframe=timeframe,
               start=start, end=end, limit=min(limit, MAX_ROWS_PER_REQUEST))
    return rows if isinstance(rows, list) else []


def candles_frame(symbol: str, **kw):
    """Candles as a DataFrame in the same shape as yf_prices.load_prices.

    `volume` is deliberately dropped: it is a partial feed (4.4% of consolidated volume
    for NVDA) and keeping the column would invite someone to use it.
    """
    import pandas as pd

    rows = candles(symbol, **kw)
    if not rows:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close"])
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["ts"], errors="coerce")
    keep = [c for c in ("date", "open", "high", "low", "close") if c in df.columns]
    return (df[keep].dropna(subset=["date", "close"])
                    .sort_values("date").reset_index(drop=True))


def splits(symbol: str) -> list[dict]:
    """Split history. Live listings only - delisted names return nothing."""
    return ref("stock_splits", symbol=symbol)


def dividends(symbol: str) -> list[dict]:
    return ref("dividends", symbol=symbol)


def company_profile(symbol: str) -> dict | None:
    rows = ref("company_profiles", symbol=symbol)
    return rows[0] if rows else None
