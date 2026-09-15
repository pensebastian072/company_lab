"""Daily OHLCV for the Entry component: EMAs, drawdown, support, capitulation.

Stored append-only as one parquet per symbol on D:, merged on write, so a re-run
only pulls the tail. Batched via yf.download in groups so 500 symbols is ~10
requests rather than 500.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .. import config

COLUMNS = ["date", "open", "high", "low", "close", "volume"]


def price_path(ticker: str) -> Path:
    return config.PRICES_DIR / f"{ticker.upper()}.parquet"


def load_prices(ticker: str) -> pd.DataFrame:
    p = price_path(ticker)
    if not p.exists():
        return pd.DataFrame(columns=COLUMNS)
    try:
        df = pd.read_parquet(p)
    except Exception:  # noqa: BLE001 - corrupt parquet degrades to empty, then re-fetch
        return pd.DataFrame(columns=COLUMNS)
    return df.sort_values("date").reset_index(drop=True)


def _store(ticker: str, df: pd.DataFrame) -> None:
    if df is None or df.empty:
        return
    p = price_path(ticker)
    p.parent.mkdir(parents=True, exist_ok=True)
    merged = df
    if p.exists():
        try:
            merged = pd.concat([pd.read_parquet(p), df], ignore_index=True)
        except Exception:  # noqa: BLE001
            pass
    merged = (merged.drop_duplicates(subset=["date"], keep="last")
                    .sort_values("date").reset_index(drop=True))
    try:
        tmp = p.with_suffix(".parquet.tmp")
        merged.to_parquet(tmp, index=False)
        tmp.replace(p)
    except Exception:  # noqa: BLE001 - a cache write must never fail the request
        pass


def _tidy(raw: pd.DataFrame) -> pd.DataFrame:
    if raw is None or raw.empty:
        return pd.DataFrame(columns=COLUMNS)
    df = raw.reset_index()
    ren = {}
    for c in df.columns:
        lc = str(c).lower()
        if lc in ("date", "datetime", "index"):
            ren[c] = "date"
        elif lc in ("open", "high", "low", "close", "volume"):
            ren[c] = lc
        elif lc == "adj close":
            ren[c] = "adj_close"
    df = df.rename(columns=ren)
    if "date" not in df.columns:
        return pd.DataFrame(columns=COLUMNS)
    df["date"] = pd.to_datetime(df["date"], utc=True, errors="coerce").dt.tz_localize(None)
    keep = [c for c in COLUMNS if c in df.columns]
    df = df[keep].dropna(subset=["date"]).sort_values("date")
    for c in ("open", "high", "low", "close", "volume"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=["close"]).reset_index(drop=True)


def fetch_prices(
    tickers: list[str], *, period: str = "10y", force: bool = False,
    group_size: int = 10,
) -> dict[str, pd.DataFrame]:
    """Download (batched) and merge into the per-symbol parquet store.

    Symbols with a store already covering the last 3 sessions are skipped unless
    force is set, so a same-day re-run is pure disk.
    """
    import yfinance as yf

    out: dict[str, pd.DataFrame] = {}
    todo: list[str] = []
    cutoff = pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(days=4)
    for t in tickers:
        have = load_prices(t)
        if not force and not have.empty and have["date"].max() >= cutoff:
            out[t] = have
        else:
            todo.append(t)

    for i in range(0, len(todo), group_size):
        chunk = todo[i:i + group_size]
        try:
            # auto_adjust=True is REQUIRED, not a preference. With raw closes a
            # 4-for-1 split reads as a 75% single-day crash: measured on this box,
            # 26 of 500 symbols carried such artifacts (KDP -82% on its spinoff,
            # GL -53%, DXCM -41%, FISV -44%). Those corrupt EMAs for a whole EMA
            # span afterwards, corrupt the P/E series' price basis against
            # split-restated EPS, and corrupt every forward return in a study.
            raw = yf.download(chunk, period=period, interval="1d",
                              auto_adjust=True, progress=False,
                              group_by="ticker", threads=True)
        except Exception:  # noqa: BLE001 - a failed batch leaves each symbol on cache
            for t in chunk:
                out[t] = load_prices(t)
            continue
        for t in chunk:
            sub = None
            try:
                if isinstance(raw.columns, pd.MultiIndex):
                    if t in raw.columns.get_level_values(0):
                        sub = raw[t]
                elif len(chunk) == 1:
                    sub = raw
            except Exception:  # noqa: BLE001
                sub = None
            tidy = _tidy(sub) if sub is not None else pd.DataFrame(columns=COLUMNS)
            if not tidy.empty:
                _store(t, tidy)
            out[t] = load_prices(t)
    return out


# ------------------------------------------------------------------ data quality
#: A single-day move beyond this is far more likely an unadjusted corporate action
#: than a real print. Real crashes do happen (PCG's bankruptcy, the 2020 oil
#: collapse), so this FLAGS for inspection rather than silently repairing.
SUSPECT_DAILY_DROP = -0.35
SUSPECT_DAILY_RISE = 0.60


def price_quality(df: pd.DataFrame) -> dict:
    """Flag implausible single-day moves. Cheap guard against silent split damage."""
    if df is None or df.empty or "close" not in df.columns or len(df) < 3:
        return {"ok": False, "reason": "insufficient history"}
    r = df.sort_values("date")["close"].astype(float).pct_change()
    worst, best = float(r.min()), float(r.max())
    suspects = int(((r < SUSPECT_DAILY_DROP) | (r > SUSPECT_DAILY_RISE)).sum())
    return {
        "ok": suspects == 0,
        "worst_day": round(worst, 4),
        "best_day": round(best, 4),
        "n_suspect_days": suspects,
        "note": ("possible unadjusted split or spinoff - verify before trusting "
                 "EMAs, the P/E series or any return computed from this"
                 if suspects else "no implausible single-day moves"),
    }


def audit_store() -> list[dict]:
    """Quality report across the whole price store."""
    out = []
    for p in sorted(config.PRICES_DIR.glob("*.parquet")):
        q = price_quality(load_prices(p.stem))
        if not q.get("ok"):
            out.append({"ticker": p.stem, **q})
    return out


# ------------------------------------------------------------------ indicators
def ema(series: pd.Series, span: int) -> float | None:
    if series is None or len(series) < span:
        return None
    val = series.ewm(span=span, adjust=False).mean().iloc[-1]
    return None if pd.isna(val) else float(val)


#: The spans the user actually watches, on each timeframe they watch them on.
#: Touching the 20 on the WEEKLY or MONTHLY is the rare, high-quality entry - on a
#: monthly chart a 20-period EMA is twenty months of trend, so price reaching it
#: means something very different from touching a 20-day line.
EMA_SPANS = (20, 72)
TIMEFRAMES = ("daily", "weekly", "monthly")


def _resample(df: pd.DataFrame, rule: str) -> pd.Series:
    """Proper calendar resample to weekly/monthly closes (not every-nth-row)."""
    s = df.set_index(pd.to_datetime(df["date"]))["close"].astype(float)
    return s.resample(rule).last().dropna()


def timeframe_emas(df: pd.DataFrame) -> dict:
    """EMA 20 and 72 on daily, weekly and monthly closes, plus distance to each."""
    out: dict = {}
    if df is None or df.empty or "close" not in df.columns:
        return out
    last = float(df["close"].astype(float).iloc[-1])
    frames = {
        "daily": df["close"].astype(float).reset_index(drop=True),
        "weekly": _resample(df, "W").reset_index(drop=True),
        "monthly": _resample(df, "ME").reset_index(drop=True),
    }
    for tf, series in frames.items():
        out[f"{tf}_bars"] = int(len(series))
        for span in EMA_SPANS:
            key = f"ema{span}_{tf}"
            val = ema(series, span)
            out[key] = val
            out[f"pct_vs_{key}"] = ((last - val) / val) if val else None
    return out


def price_features(df: pd.DataFrame) -> dict:
    """Everything the Entry component needs. Missing history -> None, never 0."""
    if df is None or df.empty or "close" not in df.columns:
        return {}
    close = df["close"].astype(float)
    last = float(close.iloc[-1])
    feats: dict = {
        "price": last,
        "price_as_of": str(df["date"].iloc[-1])[:10],
        "n_sessions": int(len(df)),
        "ema50": ema(close, 50),
        "ema200": ema(close, 200),
    }
    feats.update(timeframe_emas(df))
    weekly = _resample(df, "W").reset_index(drop=True)
    feats["weekly_ema50"] = ema(weekly, 50)

    ath = float(close.max())
    feats["ath"] = ath
    feats["drawdown_from_ath"] = (ath - last) / ath if ath > 0 else None

    for k in ("ema50", "ema200", "weekly_ema50"):
        v = feats.get(k)
        feats[f"pct_vs_{k}"] = ((last - v) / v) if v else None

    # major support: swing lows via a rolling-window pivot, nearest below price
    win = 20
    if len(close) > 2 * win + 1:
        lows = df["low"].astype(float) if "low" in df.columns else close
        pivots: list[float] = []
        vals = lows.tolist()
        for i in range(win, len(vals) - win):
            window = vals[i - win:i + win + 1]
            if vals[i] == min(window):
                pivots.append(vals[i])
        below = [p for p in pivots if p <= last]
        if below:
            support = max(below)
            feats["support"] = support
            feats["pct_above_support"] = (last - support) / support if support > 0 else None
        feats["n_pivots"] = len(pivots)

    # volume capitulation: z-score of the latest volume against a 60-session base
    if "volume" in df.columns and len(df) > 60:
        vol = df["volume"].astype(float)
        base = vol.iloc[-60:]
        sd = float(base.std())
        feats["volume_z"] = ((float(vol.iloc[-1]) - float(base.mean())) / sd) if sd > 0 else None
        ret = close.pct_change().iloc[-1]
        feats["last_day_down"] = bool(ret < 0) if pd.notna(ret) else None

    # 52-week range position
    if len(close) >= 250:
        w = close.iloc[-250:]
        lo, hi = float(w.min()), float(w.max())
        feats["pct_of_52w_range"] = ((last - lo) / (hi - lo)) if hi > lo else None
    return feats
