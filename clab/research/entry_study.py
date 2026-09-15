"""E01 - does the EN entry rule improve timing?

Pre-registered in journal/experiments/E01_entry_timing_preregistration.md BEFORE any
result was computed. Read that first: it states the hypotheses, the thresholds, and
the three things this study cannot answer.

Point-in-time discipline, which is the only thing that makes this worth running:

  * EPS applies from its FILING date, so the P/E at t uses only what was published.
  * The P/E percentile at t ranks against the trailing 5 years up to t - an
    expanding window, never the full-sample distribution.
  * Weekly and monthly EMAs use COMPLETED bars only; the in-progress week or month
    is excluded so no future close leaks backwards.
  * Entry dates stop 1 year before the data ends so every trade has a forward return.

No LLM score is used anywhere. SG, BQ and MG are excluded by construction.

Usage:
  python -m clab.research.entry_study --top 100
  python -m clab.research.entry_study --top 100 --threshold 5
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .. import config
from ..fundamentals import pe_history
from ..net import atomic_write_json, trust_windows_certs, utc_now_iso
from ..scoring import rubric
from ..sources import yf_prices
from ..sources.edgar_facts import resolve_facts

START = "2016-01-01"
COST_BPS = 5.0                 # per side, as a FRACTION of price - never absolute
COOLDOWN_DAYS = 60             # trading days before a symbol may signal again
RANDOM_DRAWS = 200
HORIZONS = {"1y": 252, "3y": 756, "5y": 1260}
PCTILE_WINDOW_DAYS = 5 * 365
MIN_PCTILE_OBS = 250
BENCHMARK = "SPY"


def log(msg: str) -> None:
    print(msg, flush=True)


# ------------------------------------------------------------------ features
def rolling_pe_percentile(pe: pd.Series) -> pd.Series:
    """Percentile of each P/E within its own trailing 5 years, expanding window."""
    if pe.empty:
        return pe
    vals = pe.to_numpy(dtype=float)
    idx = pe.index
    out = np.full(len(vals), np.nan)
    start = 0
    for i in range(len(vals)):
        while idx[i] - idx[start] > pd.Timedelta(days=PCTILE_WINDOW_DAYS):
            start += 1
        window = vals[start:i + 1]
        if len(window) >= MIN_PCTILE_OBS:
            out[i] = float((window <= vals[i]).sum()) / len(window)
    return pd.Series(out, index=idx)


def _ema(series: pd.Series, span: int) -> pd.Series:
    """EMA at each point uses only data up to that point - ewm is causal."""
    return series.ewm(span=span, adjust=False).mean()


def timeframe_ema_frame(close: pd.Series) -> pd.DataFrame:
    """EMA 20/72 on daily, and on COMPLETED weekly and monthly bars, aligned daily."""
    out = pd.DataFrame(index=close.index)
    for span in rubric.EN_EMA_SPANS:
        out[f"ema{span}_daily"] = _ema(close, span)
    for tf, rule in (("weekly", "W"), ("monthly", "ME")):
        bars = close.resample(rule).last().dropna()
        for span in rubric.EN_EMA_SPANS:
            e = _ema(bars, span)
            # shift(1): at any day inside a period, only PREVIOUS completed periods
            # are known. Without this the current week's own close leaks in.
            aligned = e.shift(1).reindex(e.index.union(close.index)).ffill()
            out[f"ema{span}_{tf}"] = aligned.reindex(close.index)
    return out


def en_score_row(price: float, pctile: float | None, emas: dict) -> tuple[int, dict]:
    """Recompute EN with the production thresholds. Returns (score 0-5, detail)."""
    detail: dict = {"pctile": pctile}

    # pillar 1: P/E vs its own history (2)
    if pctile is None or (isinstance(pctile, float) and np.isnan(pctile)):
        pe_pts = None
    else:
        pe_pts = rubric.band_from_thresholds_asc(
            pctile, rubric.EN_PE_PCTILE_BANDS, (2, 2, 1, 0))
    detail["pe_points"] = pe_pts

    # pillar 2: distance to the 20/72 EMA, weighted by timeframe (2)
    best = 0
    for tf in rubric.EN_TIMEFRAMES:
        for span in rubric.EN_EMA_SPANS:
            val = emas.get(f"ema{span}_{tf}")
            if val is None or np.isnan(val) or val <= 0:
                continue
            dist = (price - val) / val
            if -rubric.EN_AT_EMA_BELOW <= dist <= rubric.EN_AT_EMA_TOLERANCE:
                best = max(best, rubric.EN_TIMEFRAME_WEIGHT[tf])
    detail["best_tf_weight"] = best
    if best >= rubric.EN_TIMEFRAME_WEIGHT["weekly"]:
        ema_pts = 2
    elif best >= 1:
        ema_pts = 1
    else:
        ema_pts = 0
    detail["ema_points"] = ema_pts

    # pillar 3: confluence (1)
    cheap = pe_pts is not None and pctile is not None and \
        pctile <= rubric.EN_CONFLUENCE_PCTILE
    higher = best >= rubric.EN_CONFLUENCE_MIN_TF_WEIGHT
    conf = 1 if (cheap and higher) else 0
    detail["confluence"] = bool(cheap and higher)

    total = (pe_pts or 0) + ema_pts + conf
    return total, detail


# ------------------------------------------------------------------ per symbol
@dataclass
class SymbolPanel:
    ticker: str
    close: pd.Series
    en: pd.Series
    detail: pd.DataFrame
    ok: bool = True
    note: str = ""


def build_panel(ticker: str, cik: str) -> SymbolPanel:
    px = yf_prices.load_prices(ticker)
    if px is None or px.empty:
        return SymbolPanel(ticker, pd.Series(dtype=float), pd.Series(dtype=float),
                           pd.DataFrame(), ok=False, note="no prices")
    px = px.copy()
    px["date"] = pd.to_datetime(px["date"], errors="coerce")
    px = px.dropna(subset=["date", "close"]).set_index("date").sort_index()
    close = px["close"].astype(float)

    facts, _cik_used, _note = resolve_facts(cik)
    hist = pe_history.build(facts.payload or {}, px.reset_index(),
                            lookback_years=15)
    if len(hist) == 0:
        return SymbolPanel(ticker, close, pd.Series(dtype=float), pd.DataFrame(),
                           ok=False, note="no P/E series")
    pctile = rolling_pe_percentile(hist.series).reindex(close.index).ffill()
    emas = timeframe_ema_frame(close)

    scores, details = [], []
    for dt in close.index:
        row = emas.loc[dt].to_dict()
        pc = pctile.get(dt)
        s, d = en_score_row(float(close.loc[dt]),
                            None if pd.isna(pc) else float(pc), row)
        scores.append(s)
        details.append(d)
    return SymbolPanel(ticker, close, pd.Series(scores, index=close.index),
                       pd.DataFrame(details, index=close.index))


def cluster_signals(en: pd.Series, threshold: int, cooldown: int) -> list[pd.Timestamp]:
    """Consecutive qualifying days are ONE event. Without this n is fiction."""
    events: list[pd.Timestamp] = []
    last = -10 ** 9
    arr = en.to_numpy()
    idx = en.index
    for i in range(len(arr)):
        if arr[i] >= threshold and (i - last) > cooldown:
            events.append(idx[i])
            last = i
    return events


#: Days whose single-day move is implausible for a real print. auto_adjust=True
#: handles splits and dividends but NOT spinoffs or merger reorganisations, and
#: those survive as fake -50% to -87% prints (KDP, GEN, GL, FISV measured here).
#: Any trade whose window straddles such a day is dropped rather than believed -
#: surgical, and it keeps genuine crashes (the 2020 oil collapse, DXCM's guidance
#: miss) in the sample where they belong.
SUSPECT_DROP = -0.35
SUSPECT_RISE = 0.60


def suspect_mask(close: pd.Series) -> np.ndarray:
    r = close.pct_change().to_numpy()
    return (r < SUSPECT_DROP) | (r > SUSPECT_RISE)


def forward_return(close: pd.Series, entry: pd.Timestamp, bars: int,
                   suspects: np.ndarray | None = None) -> float | None:
    """Price return over `bars` trading days, net of round-trip cost.

    Returns None when the window contains a suspect print, so a corporate-action
    artefact can never masquerade as performance.
    """
    try:
        i = close.index.get_loc(entry)
    except KeyError:
        return None
    j = i + bars
    if j >= len(close):
        return None
    if suspects is not None and suspects[i + 1:j + 1].any():
        return None
    gross = float(close.iloc[j]) / float(close.iloc[i]) - 1.0
    cost = 2 * COST_BPS / 10_000.0
    return gross - cost


# ------------------------------------------------------------------ the study
@dataclass
class Study:
    rows: list[dict] = field(default_factory=list)
    randoms: list[dict] = field(default_factory=list)
    skipped: dict = field(default_factory=dict)


def run(top: int = 100, threshold: int = 4, seed: int = 1337) -> dict:
    trust_windows_certs()
    rng = random.Random(seed)

    scores = pd.read_parquet(config.SCORES_PARQUET)
    watch = (scores.sort_values("composite_strict", ascending=False)
                   .head(top)[["ticker", "cik", "composite_strict", "band"]])
    log(f"watchlist: top {top} by composite (chosen with today's knowledge - "
        f"this is the stated selection bias)")

    bench = yf_prices.load_prices(BENCHMARK)
    if bench is None or bench.empty:
        bench = yf_prices.fetch_prices([BENCHMARK]).get(BENCHMARK)
    bench = bench.copy()
    bench["date"] = pd.to_datetime(bench["date"], errors="coerce")
    bench_close = (bench.dropna(subset=["date", "close"])
                        .set_index("date").sort_index()["close"].astype(float))

    st = Study()
    for n, (_i, r) in enumerate(watch.iterrows(), 1):
        panel = build_panel(r.ticker, r.cik)
        if not panel.ok:
            st.skipped[r.ticker] = panel.note
            log(f"  [{n}/{top}] {r.ticker:6s} skipped: {panel.note}")
            continue

        en = panel.en[panel.en.index >= pd.Timestamp(START)]
        close = panel.close
        eligible = en.index[en.index <= close.index.max() - pd.Timedelta(days=380)]
        en = en.loc[eligible]
        if en.empty:
            st.skipped[r.ticker] = "no eligible dates"
            continue

        susp = suspect_mask(close)
        events = cluster_signals(en, threshold, COOLDOWN_DAYS)
        for dt in events:
            rec = {"ticker": r.ticker, "date": str(dt.date()), "year": dt.year,
                   "en": int(panel.en.loc[dt]),
                   "pctile": _f(panel.detail.loc[dt].get("pctile")),
                   "confluence": bool(panel.detail.loc[dt].get("confluence")),
                   "best_tf_weight": int(panel.detail.loc[dt].get("best_tf_weight") or 0)}
            for h, bars in HORIZONS.items():
                rec[f"ret_{h}"] = forward_return(close, dt, bars, susp)
                rec[f"spy_{h}"] = forward_return(bench_close, dt, bars) \
                    if dt in bench_close.index else None
            st.rows.append(rec)

        # random-date control in the SAME name: holds company selection constant
        pool = [d for d in en.index]
        if pool:
            for _k in range(RANDOM_DRAWS):
                dt = pool[rng.randrange(len(pool))]
                rec = {"ticker": r.ticker, "date": str(dt.date()), "year": dt.year}
                for h, bars in HORIZONS.items():
                    rec[f"ret_{h}"] = forward_return(close, dt, bars, susp)
                st.randoms.append(rec)

        log(f"  [{n}/{top}] {r.ticker:6s} {len(events):3d} clustered signals "
            f"from {len(en)} eligible days")

    return summarise(st, watch, threshold, top)


def _f(v):
    try:
        f = float(v)
        return None if np.isnan(f) else round(f, 4)
    except (TypeError, ValueError):
        return None


def _mean(vals) -> float | None:
    clean = [v for v in vals if v is not None and not (isinstance(v, float) and np.isnan(v))]
    return float(np.mean(clean)) if clean else None


def summarise(st: Study, watch: pd.DataFrame, threshold: int, top: int) -> dict:
    sig = pd.DataFrame(st.rows)
    rnd = pd.DataFrame(st.randoms)
    out: dict = {
        "study": "E01_entry_timing",
        "as_of": utc_now_iso(),
        "preregistration": "journal/experiments/E01_entry_timing_preregistration.md",
        "watchlist_size": int(len(watch)),
        "threshold_en": threshold,
        "cooldown_trading_days": COOLDOWN_DAYS,
        "cost_bps_per_side": COST_BPS,
        "random_draws_per_symbol": RANDOM_DRAWS,
        "n_signals": int(len(sig)),
        "n_random": int(len(rnd)),
        "skipped": st.skipped,
        "caveats": [
            "Watchlist chosen with today's knowledge - survivorship and selection "
            "bias are present by construction.",
            "No LLM score used; SG/BQ/MG excluded entirely.",
            "Delisted and removed constituents absent from the price store.",
        ],
    }
    if sig.empty:
        out["verdict"] = "no signals fired - nothing to test"
        return out

    # ---------------- pooled, per horizon (reported AFTER the per-year table)
    pooled = {}
    for h in HORIZONS:
        s_mean = _mean(sig.get(f"ret_{h}", []))
        r_mean = _mean(rnd.get(f"ret_{h}", [])) if not rnd.empty else None
        spy_mean = _mean(sig.get(f"spy_{h}", []))
        signal_observed = sig[f"ret_{h}"].dropna()
        random_observed = (rnd[f"ret_{h}"].dropna()
                           if not rnd.empty else pd.Series(dtype=float))
        n_s = int(len(signal_observed))
        n_r = int(len(random_observed))
        edge = (s_mean - r_mean) if (s_mean is not None and r_mean is not None) else None
        # where does the signal mean sit in the distribution of random-draw means?
        pctile_vs_random = None
        if not rnd.empty and s_mean is not None and n_s >= 5:
            draws = []
            vals = rnd[f"ret_{h}"].dropna().to_numpy()
            if len(vals) >= n_s:
                rs = np.random.default_rng(7)
                for _ in range(2000):
                    draws.append(float(rs.choice(vals, size=n_s, replace=True).mean()))
                pctile_vs_random = float((np.array(draws) <= s_mean).mean())
        pooled[h] = {
            "n_signals": n_s,
            "signal_mean": s_mean,
            "random_mean": r_mean,
            "edge_vs_random": edge,
            "signal_mean_percentile_vs_random_draws": pctile_vs_random,
            "spy_mean": spy_mean,
            "excess_vs_spy": (s_mean - spy_mean)
            if (s_mean is not None and spy_mean is not None) else None,
            "signal_median": _f(sig[f"ret_{h}"].median()),
            "signal_hit_n": n_s,
            "signal_hit_rate": _f((signal_observed > 0).mean()),
            "random_hit_n": n_r,
            "random_hit_rate": (_f((random_observed > 0).mean())
                                if n_r else None),
        }
    out["pooled"] = pooled

    # ---------------- per year (the table that matters)
    per_year = {}
    for year, grp in sig.groupby("year"):
        rgrp = rnd[rnd.year == year] if not rnd.empty else pd.DataFrame()
        s_mean = _mean(grp.get("ret_1y", []))
        r_mean = _mean(rgrp.get("ret_1y", [])) if not rgrp.empty else None
        s_med = _f(grp["ret_1y"].median())
        r_med = _f(rgrp["ret_1y"].median()) if not rgrp.empty else None
        per_year[int(year)] = {
            "n_signals": int(grp["ret_1y"].notna().sum()),
            "signal_mean_1y": s_mean,
            "random_mean_1y": r_mean,
            "edge": (s_mean - r_mean) if (s_mean is not None and r_mean is not None) else None,
            # Median as well as mean. A handful of 10x recoveries (CVNA off its 2022
            # low) dominate any mean over this window, so the median is the more
            # informative number - reported ALONGSIDE, never instead of, because the
            # pre-registered test named the mean.
            "signal_median_1y": s_med,
            "random_median_1y": r_med,
            "edge_median": (s_med - r_med) if (s_med is not None and r_med is not None) else None,
        }
    out["per_year_1y"] = per_year
    years_positive = sum(1 for v in per_year.values()
                         if v["edge"] is not None and v["edge"] > 0)
    years_total = sum(1 for v in per_year.values() if v["edge"] is not None)
    out["years_with_positive_edge"] = f"{years_positive}/{years_total}"
    yp_med = sum(1 for v in per_year.values()
                 if v.get("edge_median") is not None and v["edge_median"] > 0)
    yt_med = sum(1 for v in per_year.values() if v.get("edge_median") is not None)
    out["years_with_positive_edge_median"] = f"{yp_med}/{yt_med}"

    # ---------------- confluence vs partial (H3)
    by_en = {}
    for en_val, grp in sig.groupby("en"):
        by_en[int(en_val)] = {"n": int(grp["ret_1y"].notna().sum()),
                             "mean_1y": _mean(grp.get("ret_1y", []))}
    out["by_en_score"] = by_en
    conf = sig[sig.confluence]
    noconf = sig[~sig.confluence]
    out["confluence"] = {
        "n_confluence": int(conf["ret_1y"].notna().sum()),
        "mean_1y_confluence": _mean(conf.get("ret_1y", [])),
        "n_no_confluence": int(noconf["ret_1y"].notna().sum()),
        "mean_1y_no_confluence": _mean(noconf.get("ret_1y", [])),
    }

    # ---------------- $10k per signal
    stake = 10_000.0
    money = {}
    for h in HORIZONS:
        s = sig[f"ret_{h}"].dropna()
        r = rnd[f"ret_{h}"].dropna() if not rnd.empty else pd.Series(dtype=float)
        money[h] = {
            "n_trades": int(len(s)),
            "total_staked": stake * len(s),
            "signal_profit": float((s * stake).sum()),
            "signal_profit_per_trade": float((s * stake).mean()) if len(s) else None,
            "random_profit_per_trade": float((r * stake).mean()) if len(r) else None,
        }
    out["ten_k_per_signal"] = money

    # ---------------- pre-registered verdicts
    p1 = pooled["1y"]
    h1 = (p1["edge_vs_random"] is not None and p1["edge_vs_random"] > 0
          and (p1["signal_mean_percentile_vs_random_draws"] or 0) > 0.60)
    h2 = years_total > 0 and years_positive >= 6
    m5 = by_en.get(5, {}).get("mean_1y")
    m34 = _mean([v for k, v in [(k, by_en.get(k, {}).get("mean_1y")) for k in (3, 4)]
                 if v is not None])
    h3 = (m5 is not None and m34 is not None and m5 > m34)
    h4 = ((p1["excess_vs_spy"] or -1) > 0
          and (pooled["3y"]["excess_vs_spy"] or -1) > 0)
    out["hypotheses"] = {
        "H1_beats_random_1y": bool(h1),
        "H2_positive_in_6_of_9_years": bool(h2),
        "H3_confluence_beats_partial": bool(h3),
        "H4_beats_spy_1y_and_3y": bool(h4),
    }
    out["verdict"] = ("entry rule shows timing value on the pre-registered tests"
                      if (h1 and h2) else
                      "entry rule does NOT clear its pre-registered tests - it should "
                      "stay a 5-of-100 tiebreaker, not a gate")
    return out


def render(res: dict) -> str:
    L = []
    a = L.append
    a("# E01 - does the EN entry rule improve timing?\n")
    a(f"Run {res['as_of']}. Pre-registered: `{res['preregistration']}`\n")
    a(f"Watchlist: top {res['watchlist_size']} by composite. "
      f"Signal: EN >= {res['threshold_en']}, {res['cooldown_trading_days']}-day cooldown. "
      f"Cost {res['cost_bps_per_side']} bps/side.\n")
    a(f"**{res['n_signals']} clustered signals**, "
      f"{res['n_random']} random-date controls.\n")

    a("\n## Per-year, 1-year holding period (this table comes first on purpose)\n")
    a("| year | n | signal mean | random mean | edge (mean) | signal med | random med | edge (med) |")
    a("|---|---:|---:|---:|---:|---:|---:|---:|")
    for y, v in sorted((res.get("per_year_1y") or {}).items()):
        a(f"| {y} | {v['n_signals']} | {_p(v['signal_mean_1y'])} | "
          f"{_p(v['random_mean_1y'])} | {_p(v['edge'])} | "
          f"{_p(v.get('signal_median_1y'))} | {_p(v.get('random_median_1y'))} | "
          f"{_p(v.get('edge_median'))} |")
    a(f"\nYears with a positive edge: **{res.get('years_with_positive_edge')}** on the "
      f"mean, **{res.get('years_with_positive_edge_median')}** on the median.")
    a("\nThe median matters here: a few 10x recoveries dominate any mean over this "
      "window. The pre-registered test named the mean, so that is what the verdict "
      "uses - the median is reported alongside, not instead.\n")

    a("\n## Pooled\n")
    a("| horizon | n | signal | random | edge | vs SPY | signal hit | signal hit n | random hit | random hit n |")
    a("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for h, v in (res.get("pooled") or {}).items():
        a(f"| {h} | {v['n_signals']} | {_p(v['signal_mean'])} | {_p(v['random_mean'])} | "
          f"{_p(v['edge_vs_random'])} | {_p(v['excess_vs_spy'])} | "
          f"{_p(v['signal_hit_rate'])} | {v.get('signal_hit_n')} | "
          f"{_p(v['random_hit_rate'])} | {v.get('random_hit_n')} |")

    a("\n## $10,000 per signal\n")
    a("| horizon | trades | staked | profit | per trade | random per trade |")
    a("|---|---:|---:|---:|---:|---:|")
    for h, v in (res.get("ten_k_per_signal") or {}).items():
        a(f"| {h} | {v['n_trades']} | ${v['total_staked']:,.0f} | "
          f"${v['signal_profit']:,.0f} | ${v['signal_profit_per_trade'] or 0:,.0f} | "
          f"${v['random_profit_per_trade'] or 0:,.0f} |")

    a("\n## By EN score, and confluence\n")
    a("| EN | n | mean 1y |")
    a("|---|---:|---:|")
    for k, v in sorted((res.get("by_en_score") or {}).items()):
        a(f"| {k} | {v['n']} | {_p(v['mean_1y'])} |")
    c = res.get("confluence") or {}
    a(f"\nConfluence: n={c.get('n_confluence')} mean {_p(c.get('mean_1y_confluence'))} "
      f"vs no-confluence n={c.get('n_no_confluence')} "
      f"mean {_p(c.get('mean_1y_no_confluence'))}\n")

    a("\n## Pre-registered hypotheses\n")
    for k, v in (res.get("hypotheses") or {}).items():
        a(f"- {'PASS' if v else 'FAIL'}  {k}")
    a(f"\n**Verdict: {res.get('verdict')}**\n")
    a("\n## What this cannot tell you\n")
    for c in res.get("caveats", []):
        a(f"- {c}")
    if res.get("skipped"):
        a(f"\nSkipped {len(res['skipped'])} names: "
          + ", ".join(f"{k} ({v})" for k, v in list(res["skipped"].items())[:10]))
    return "\n".join(L) + "\n"


def _p(v) -> str:
    if v is None:
        return "-"
    try:
        return f"{float(v) * 100:+.1f}%"
    except (TypeError, ValueError):
        return str(v)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--top", type=int, default=100)
    ap.add_argument("--threshold", type=int, default=4, choices=(3, 4, 5))
    ap.add_argument("--seed", type=int, default=1337)
    args = ap.parse_args(argv)

    res = run(top=args.top, threshold=args.threshold, seed=args.seed)
    out_json = config.JOURNAL_DIR / "experiments" / "E01_entry_timing_results.json"
    out_md = config.JOURNAL_DIR / "experiments" / "E01_entry_timing_results.md"
    atomic_write_json(out_json, res)
    md = render(res)
    out_md.write_text(md, encoding="utf-8")
    print()
    print(md)
    print(f"written: {out_json}")
    print(f"written: {out_md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
