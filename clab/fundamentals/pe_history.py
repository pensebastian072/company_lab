"""Reconstructed P/E history: where does today's multiple sit against its own past?

Originally this percentile waited on accumulated weekly snapshots, which meant it
was NO_DATA for every company and would have stayed that way for months. That was
unnecessary: a real P/E series can be rebuilt today from artifacts already on disk -
10 years of daily closes per symbol, and diluted EPS by quarter from EDGAR.

    P/E(t) = close(t) / TTM diluted EPS known at t

The "known at t" part is the whole game. Each quarter's EPS is applied from its
FILING date, never its period end, so the series never uses a number the market
could not have seen. That makes the same function usable for a point-in-time study
and not just for a descriptive stat about today.

A high-multiple grower compressing toward the low end of its own range is the setup
this exists to detect - the case where an absolute P/E screen says "expensive" and
the company's own history says "this is as cheap as it gets".
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from . import normalize as nz
from . import tags

#: EPS is applied from its filing date. Where a filing date is missing, fall back
#: to the period end plus this lag - the typical gap before a 10-Q lands.
FILING_LAG_DAYS = 45
MIN_POINTS_FOR_PERCENTILE = 250      # ~1 trading year
DEFAULT_LOOKBACK_YEARS = 10


@dataclass
class PeHistory:
    series: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    eps_points: int = 0
    note: str = ""

    def __len__(self) -> int:
        return len(self.series)

    @property
    def usable(self) -> bool:
        return len(self.series) >= MIN_POINTS_FOR_PERCENTILE

    def stats(self, *, years: float = 5.0) -> dict:
        """Percentile of the latest P/E within its own trailing window."""
        if not self.usable:
            return {"pe_history_n": len(self.series), "pe_history_note": self.note}
        s = self.series.dropna()
        if s.empty:
            return {"pe_history_n": 0, "pe_history_note": "no positive-EPS periods"}
        cutoff = s.index.max() - pd.Timedelta(days=int(365.25 * years))
        window = s[s.index >= cutoff]
        if len(window) < MIN_POINTS_FOR_PERCENTILE:
            window = s
        current = float(window.iloc[-1])
        below = int((window <= current).sum())
        return {
            "pe_current": current,
            "pe_pctile_own": below / len(window),
            "pe_median_own": float(window.median()),
            "pe_min_own": float(window.min()),
            "pe_max_own": float(window.max()),
            "pe_history_n": int(len(window)),
            "pe_history_years": round(
                (window.index.max() - window.index.min()).days / 365.25, 1),
            "pe_history_note": self.note,
        }


def _ttm_eps_by_date(payload: dict, *, view: str = "current") -> pd.Series:
    """TTM diluted EPS indexed by the date it became publicly known."""
    tag, rows = tags.resolve(payload, "eps_diluted")
    if tag is None:
        return pd.Series(dtype=float)
    series = nz.discrete_quarters(rows, view=view)
    facts = series.facts
    if len(facts) < 4:
        return pd.Series(dtype=float)

    points: dict[pd.Timestamp, float] = {}
    for i in range(3, len(facts)):
        window = facts[i - 3:i + 1]
        gaps = [(window[j + 1].end - window[j].end).days for j in range(3)]
        if any(g < 55 or g > 135 for g in gaps):
            continue                     # not four consecutive quarters
        ttm = sum(f.val for f in window)
        known = window[-1].filed
        try:
            when = pd.Timestamp(known) if known else None
        except (TypeError, ValueError):
            when = None
        if when is None:
            when = pd.Timestamp(window[-1].end) + pd.Timedelta(days=FILING_LAG_DAYS)
        points[when.normalize()] = ttm
    if not points:
        return pd.Series(dtype=float)
    return pd.Series(points).sort_index()


def build(payload: dict, prices: pd.DataFrame, *, view: str = "current",
          lookback_years: float = DEFAULT_LOOKBACK_YEARS) -> PeHistory:
    """Daily P/E series. Returns an empty PeHistory rather than raising."""
    if prices is None or prices.empty or "close" not in prices.columns:
        return PeHistory(note="no price history")
    eps = _ttm_eps_by_date(payload, view=view)
    if eps.empty:
        return PeHistory(note="fewer than four consecutive quarters of diluted EPS")

    px = prices.copy()
    px["date"] = pd.to_datetime(px["date"], errors="coerce")
    px = px.dropna(subset=["date", "close"]).set_index("date").sort_index()
    if lookback_years:
        px = px[px.index >= px.index.max() - pd.Timedelta(days=int(365.25 * lookback_years))]
    if px.empty:
        return PeHistory(note="no prices in the lookback window")

    # step the EPS series onto trading days: only what was already filed applies
    aligned = eps.reindex(eps.index.union(px.index)).ffill().reindex(px.index)
    pe = px["close"].astype(float) / aligned
    pe = pe.where(aligned > 0)                       # negative EPS -> no meaningful P/E
    pe = pe.where((pe > 0) & (pe < 500))             # drop absurd values around zero EPS
    pe = pe.dropna()
    return PeHistory(series=pe, eps_points=int(len(eps)),
                     note=f"reconstructed from {len(eps)} TTM EPS points, "
                          f"applied from filing dates")
