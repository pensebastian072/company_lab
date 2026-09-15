"""Daily closes for DELISTED tickers, from the archive that retains them.

yfinance will not serve a delisted ticker, which is why every study so far ran on
today's index members only. `D:\\ohlcv_1m` does retain them - stock_xsect_lab reduced it
to a daily panel at `D:\\stock_xsect_data\\daily\\*.parquet` carrying 60,653 distinct
symbols including every one of the 213 companies removed from the S&P 500 since 2016.

Two warnings that travel with this source, both from stock_xsect_lab's CLAUDE.md:

  1. **It is UNADJUSTED for splits.** A handful of rows carry forward moves of order
     100,000%. company_lab's own store had the same defect and it corrupted EMAs, the
     P/E series and every return in E01's first run. Here it is handled by the same
     suspect-window filter (`research/entry_study.suspect_mask`), which drops any
     return window straddling an implausible print rather than trusting it.
  2. Per-date winsorization at 1/99 is mandatory for cross-sectional statistics on
     this panel.

`is_common` is honoured, so ADRs, warrants and preferreds are excluded the same way
stock_xsect_lab excludes them.
"""
from __future__ import annotations

import glob
from functools import lru_cache

import pandas as pd

DAILY_GLOB = r"D:\stock_xsect_data\daily\*.parquet"
COLUMNS = ["date", "open", "high", "low", "close", "volume"]

#: Last archive read error, so a silent miss is diagnosable instead of looking like
#: "this delisted company has no prices".
LAST_ERROR: dict[str, str] = {}


@lru_cache(maxsize=1)
def _files() -> tuple[str, ...]:
    return tuple(sorted(glob.glob(DAILY_GLOB)))


def available() -> bool:
    return bool(_files())


@lru_cache(maxsize=1)
def known_tickers() -> frozenset[str]:
    """Every symbol in the archive. One scan of a single column, then cached."""
    if not _files():
        return frozenset()
    try:
        import pyarrow.dataset as ds

        table = ds.dataset(list(_files()), format="parquet").to_table(columns=["ticker"])
        return frozenset(table.column("ticker").to_pylist())
    except Exception:  # noqa: BLE001
        return frozenset()


def load_prices(ticker: str) -> pd.DataFrame:
    """Daily OHLCV for one ticker in the same shape as yf_prices.load_prices.

    Returns an empty frame rather than raising when the symbol or the archive is
    absent, so callers can fall through to their normal source.
    """
    files = _files()
    if not files:
        return pd.DataFrame(columns=COLUMNS)
    try:
        import pyarrow.dataset as ds

        dataset = ds.dataset(list(files), format="parquet")
        names = set(dataset.schema.names)
        cols = [c for c in ("ticker", "date", "open", "high", "low", "close",
                            "volume", "is_common") if c in names]
        # Expression operators, not pyarrow.compute.and_ - that function does not
        # exist in this pyarrow and the resulting ArrowKeyError was being swallowed,
        # which made every delisted name look like "no prices".
        flt = ds.field("ticker") == ticker.upper()
        if "is_common" in names:
            flt = flt & (ds.field("is_common") == True)   # noqa: E712 - Expression
        table = dataset.to_table(columns=cols, filter=flt)
    except Exception as exc:  # noqa: BLE001 - optional source, but say so
        LAST_ERROR["error"] = f"{type(exc).__name__}: {exc}"
        return pd.DataFrame(columns=COLUMNS)

    df = table.to_pandas()
    if df.empty:
        return pd.DataFrame(columns=COLUMNS)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    keep = [c for c in COLUMNS if c in df.columns]
    df = (df[keep].dropna(subset=["date", "close"])
                  .drop_duplicates(subset=["date"], keep="last")
                  .sort_values("date").reset_index(drop=True))
    return df


def load_prices_any(ticker: str) -> tuple[pd.DataFrame, str]:
    """company_lab's own store first, the delisted archive second.

    Returns (frame, source) so a study can report how much of its panel came from an
    unadjusted source.
    """
    from . import yf_prices

    own = yf_prices.load_prices(ticker)
    if own is not None and not own.empty and len(own) > 200:
        return own, "yfinance"
    arch = load_prices(ticker)
    if not arch.empty:
        return arch, "archive_unadjusted"
    return (own if own is not None else pd.DataFrame(columns=COLUMNS)), "none"
