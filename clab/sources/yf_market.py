"""yfinance: price, market cap, multiples, analyst estimates.

EDGAR owns the statements; yfinance owns everything market-facing that EDGAR
cannot know - what the shares cost today and what analysts expect next year.

Cache is DATE-PARTITIONED and never overwritten. Yesterday's file stays on disk
forever, which is what makes a point-in-time valuation history accumulate: after
a year of daily runs, "P/E versus its own 5Y average" stops being a guess. That
is also the metered-data rule in spirit - yfinance is free but throttles, so a
re-run on the same day costs zero network.

Every endpoint is fetched defensively: yfinance surfaces upstream shape changes
as AttributeError/KeyError rather than a clean failure, so each accessor is
individually guarded and a broken one degrades to None instead of losing the
other five.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .. import config
from ..net import (atomic_write_gzip_json, cache_key, read_gzip_json, utc_now_iso,
                   utc_today)
from .base import Source

ENDPOINTS = (
    "fast_info", "info", "earnings_estimate", "revenue_estimate", "eps_trend",
    "growth_estimates", "analyst_price_targets", "earnings_dates",
)


def _jsonable(obj: Any) -> Any:
    """DataFrame/Series/Timestamp -> plain JSON. Never raises."""
    try:
        import pandas as pd

        if isinstance(obj, pd.DataFrame):
            if obj.empty:
                return {"__frame__": [], "__index__": []}
            df = obj.copy()
            df.index = [str(i) for i in df.index]
            df.columns = [str(c) for c in df.columns]
            return {"__frame__": df.where(df.notna(), None).to_dict(orient="records"),
                    "__index__": list(df.index)}
        if isinstance(obj, pd.Series):
            return {str(k): _scalar(v) for k, v in obj.items()}
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
    except Exception:  # noqa: BLE001
        pass
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    return _scalar(obj)


def _scalar(v: Any) -> Any:
    if v is None or isinstance(v, (str, bool, int)):
        return v
    try:
        import math

        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return str(v)


class YfMarket(Source):
    """One snapshot of every market-facing endpoint for one ticker."""

    source_id = "yf_market"

    def __init__(self, ticker: str, *, day: str | None = None) -> None:
        self.ticker = ticker.upper()
        self.day = day or utc_today()

    def _cache_path(self) -> Path:
        h = cache_key("yf_market", {"ticker": self.ticker, "endpoints": ENDPOINTS})
        return config.YF_DIR / self.ticker / f"market_{self.day}_{h}.json.gz"

    def _cache_ttl_hours(self) -> float:
        return float(config.YF_TTL_HOURS)

    def _load_cache(self):
        return read_gzip_json(self._cache_path())

    def _write_cache(self, payload) -> None:
        atomic_write_gzip_json(self._cache_path(), payload)

    def _is_cacheable(self, payload) -> bool:
        return isinstance(payload, dict) and payload.get("ok_endpoints", 0) > 0

    def _data_through(self, payload) -> str | None:
        return (payload or {}).get("as_of_date")

    def latest_cached(self) -> dict | None:
        """Newest snapshot on disk regardless of date - the offline fallback."""
        d = config.YF_DIR / self.ticker
        if not d.exists():
            return None
        hits = sorted(d.glob("market_*.json.gz"))
        return read_gzip_json(hits[-1]) if hits else None

    def _fetch_raw(self) -> dict:
        import yfinance as yf

        t = yf.Ticker(self.ticker)
        out: dict[str, Any] = {
            "ticker": self.ticker,
            "as_of": utc_now_iso(),
            "as_of_date": self.day,
            "errors": {},
        }
        ok = 0
        for name in ENDPOINTS:
            try:
                val = getattr(t, name)
                out[name] = _jsonable(val)
                ok += 1
            except Exception as exc:  # noqa: BLE001 - one broken endpoint must not lose the rest
                out[name] = None
                out["errors"][name] = f"{type(exc).__name__}: {exc}"
        out["ok_endpoints"] = ok
        return out


# ------------------------------------------------------------------ readers
def _info(payload: dict) -> dict:
    for key in ("info", "fast_info"):
        v = (payload or {}).get(key)
        if isinstance(v, dict) and v:
            return v
    return {}


def _pick(payload: dict, *names, default=None):
    """First present, non-None value across info then fast_info."""
    for src in ("info", "fast_info"):
        d = (payload or {}).get(src)
        if not isinstance(d, dict):
            continue
        for n in names:
            v = d.get(n)
            if v is not None:
                return v
    return default


def frame_records(payload: dict, key: str) -> list[dict]:
    blob = (payload or {}).get(key)
    if isinstance(blob, dict) and "__frame__" in blob:
        recs = blob["__frame__"]
        idx = blob.get("__index__") or []
        out = []
        for i, r in enumerate(recs):
            row = dict(r)
            row["_index"] = idx[i] if i < len(idx) else None
            out.append(row)
        return out
    return []


def market_metrics(payload: dict) -> dict:
    """Flat market metrics from a cached snapshot. Missing -> None, never 0."""
    if not isinstance(payload, dict):
        return {}
    m: dict[str, Any] = {
        "price": _pick(payload, "currentPrice", "lastPrice", "last_price",
                       "regularMarketPrice", "previousClose"),
        "market_cap": _pick(payload, "marketCap", "market_cap"),
        "shares_outstanding": _pick(payload, "sharesOutstanding", "shares"),
        "pe": _pick(payload, "trailingPE"),
        "fwd_pe": _pick(payload, "forwardPE"),
        "peg_vendor": _pick(payload, "trailingPegRatio", "pegRatio"),
        "ev": _pick(payload, "enterpriseValue"),
        "ev_ebitda": _pick(payload, "enterpriseToEbitda"),
        "ev_sales": _pick(payload, "enterpriseToRevenue"),
        "price_to_book": _pick(payload, "priceToBook"),
        "beta": _pick(payload, "beta"),
        "dividend_yield": _pick(payload, "dividendYield"),
        "sector_yf": _pick(payload, "sector"),
        "industry_yf": _pick(payload, "industry"),
        "long_name": _pick(payload, "longName", "shortName"),
        "price_as_of": payload.get("as_of_date"),
        "target_mean": None,
        "analyst_growth_1y": None,
        "analyst_growth_3y": None,
        "eps_revision_direction": None,
        "surprise_beat_rate": None,
        "next_earnings_date": None,
    }

    # analyst price target
    apt = (payload or {}).get("analyst_price_targets")
    if isinstance(apt, dict):
        m["target_mean"] = _scalar(apt.get("mean") or apt.get("median"))
        m["target_high"] = _scalar(apt.get("high"))
        m["target_low"] = _scalar(apt.get("low"))

    # growth estimates: index labels like 0q/+1q/0y/+1y/+5y
    for rec in frame_records(payload, "growth_estimates"):
        label = str(rec.get("_index") or "").strip().lower()
        val = _scalar(rec.get("stockTrend") or rec.get("growth"))
        if val is None:
            continue
        if label in ("+1y", "1y"):
            m["analyst_growth_1y"] = val
        elif label in ("+5y", "5y", "+5 years"):
            m["analyst_growth_3y"] = val      # long-term estimate; used as the 3-5y proxy

    # eps_trend: current estimate vs 7/30/60/90 days ago = the revision signal
    for rec in frame_records(payload, "eps_trend"):
        label = str(rec.get("_index") or "").strip().lower()
        if label not in ("0q", "+1q"):
            continue
        cur = _scalar(rec.get("current"))
        ago = _scalar(rec.get("days30ago") or rec.get("30daysAgo") or rec.get("days60ago"))
        if cur is not None and ago not in (None, 0):
            m["eps_revision_direction"] = (cur - ago) / abs(ago)
            break

    # earnings surprise history
    beats = total = 0
    dates: list[str] = []
    for rec in frame_records(payload, "earnings_dates"):
        surprise = _scalar(rec.get("Surprise(%)") or rec.get("surprisePercent"))
        idx = rec.get("_index")
        if idx:
            dates.append(str(idx))
        if surprise is None:
            continue
        total += 1
        if surprise > 0:
            beats += 1
    if total:
        m["surprise_beat_rate"] = beats / total
        m["surprise_quarters"] = total
    if dates:
        future = sorted(d for d in dates if d[:10] >= utc_today())
        m["next_earnings_date"] = future[0][:10] if future else None

    # forward revenue growth from revenue_estimate
    for rec in frame_records(payload, "revenue_estimate"):
        if str(rec.get("_index") or "").strip().lower() in ("+1y", "1y"):
            g = _scalar(rec.get("growth"))
            if g is not None and m["analyst_growth_1y"] is None:
                m["analyst_growth_1y"] = g
    return {k: v for k, v in m.items()}
