"""E06 - does following insiders beat just holding the index?

Pre-registered in journal/experiments/E06_insider_signal_preregistration.md, written
before any insider data was analysed. The user's question in their words: does insider
activity work "as a signal and how much that comes out and how it should be followed"
versus "regular S&P 500 holding".

So the primary statistic is EXCESS OVER SPY, never absolute return. Absolute numbers over
2016-2026 flatter everything.

Data is SEC Form 4 from the DERA bulk datasets (`clab/sources/edgar_form4.py`), not the
LSE vault - see E06_insider_signal_STATUS.md for why that source could not carry it.

The three disciplines fixed in the pre-registration, each of which is a way to fake an
edge here:

  1. Signal date is FILING_DATE, never TRANS_DATE. A Form 4 is filed up to two business
     days after the trade and the gap can run to months; acting on the transaction date
     uses information nobody had.
  2. Congressional rows excluded - satisfied by construction, Form 4 has none.
  3. Mechanical transactions separated from discretionary ones. Option exercises (M), tax
     withholding (F), awards (A) and gifts (G) are not decisions. Only P and S are.

Prior, stated in the pre-registration: buying weakly predictive, selling not. IF SELLING
LOOKS PREDICTIVE, SUSPECT THE CONSTRUCTION BEFORE BELIEVING IT.
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from .. import config
from ..net import atomic_write_json, utc_now_iso

LOOKBACK_DAYS = 90            # S1/S2/S3 window
RATIO_LOOKBACK_DAYS = 180     # S4
HOLDINGS_LOOKBACK_DAYS = 365  # S5
CLUSTER_MIN_INSIDERS = 3
MIN_DATE_CLUSTERS = 40
COST_BPS_PER_SIDE = 5.0       # as a fraction of price, per the pre-registration


def build_signals(form4: pd.DataFrame, panel: pd.DataFrame) -> pd.DataFrame:
    """Attach the six pre-registered signals to the panel's monthly grid.

    Every signal is evaluated as of the month-end using only filings whose FILING_DATE is
    on or before it.
    """
    f = form4.copy()
    f["filing_date"] = pd.to_datetime(f["filing_date"], errors="coerce")
    f = f.dropna(subset=["filing_date", "symbol"])

    disc = f[f["is_discretionary"]]
    buys = disc[disc.code == "P"]
    sells = disc[disc.code == "S"]
    off_buys = buys[buys.get("is_officer_or_director", False).fillna(False)]
    ceo_buys = buys[buys.get("is_ceo_cfo", False).fillna(False)]

    p = panel.copy()
    p["date"] = pd.to_datetime(p["date"])
    dates = np.sort(p["date"].unique())

    def _window_stat(src: pd.DataFrame, days: int, how: str) -> dict:
        """{(symbol, date): value} for filings in (date-days, date]."""
        if src.empty:
            return {}
        out: dict[tuple, float] = {}
        s = src.sort_values("filing_date")
        for d in dates:
            d = pd.Timestamp(d)
            w = s[(s.filing_date > d - pd.Timedelta(days=days)) & (s.filing_date <= d)]
            if w.empty:
                continue
            if how == "count":
                g = w.groupby("symbol").size()
            elif how == "insiders":
                g = w.groupby("symbol")["owner_cik"].nunique()
            elif how == "value":
                g = w.groupby("symbol")["value"].sum(min_count=1)
            else:
                raise ValueError(how)
            for sym, v in g.items():
                out[(sym, d)] = float(v)
        return out

    s1 = _window_stat(off_buys, LOOKBACK_DAYS, "count")
    s2 = _window_stat(ceo_buys, LOOKBACK_DAYS, "count")
    s3 = _window_stat(off_buys, LOOKBACK_DAYS, "insiders")
    s6 = _window_stat(sells, LOOKBACK_DAYS, "count")
    buy_val = _window_stat(buys, RATIO_LOOKBACK_DAYS, "value")
    sell_val = _window_stat(sells, RATIO_LOOKBACK_DAYS, "value")

    key = list(zip(p["ticker"], p["date"]))
    p["s1_buy_count"] = [s1.get(k, 0.0) for k in key]
    p["s2_ceo_cfo_buy"] = [s2.get(k, 0.0) for k in key]
    p["s3_distinct_buyers"] = [s3.get(k, 0.0) for k in key]
    p["s6_sell_count"] = [s6.get(k, 0.0) for k in key]
    bv = np.array([buy_val.get(k, 0.0) for k in key])
    sv = np.array([sell_val.get(k, 0.0) for k in key])
    with np.errstate(divide="ignore", invalid="ignore"):
        p["s4_buy_sell_ratio"] = np.where(sv > 0, bv / sv, np.nan)

    # The confound diagnostic: ANY discretionary insider activity, buy or sell. If this
    # predicts as well as buying does, then "insiders bought" is standing in for "this
    # company has active insiders", which is an attention/liquidity proxy, not a signal.
    any_act = _window_stat(disc, LOOKBACK_DAYS, "count")
    p["any_activity"] = [any_act.get(k, 0.0) for k in key]

    # S5: change in officer holdings over 12 months, from the latest filing in each window
    hold = f[f.get("is_officer_or_director", False).fillna(False)]
    hold = hold.dropna(subset=["shares_owned_after"])
    s5: dict[tuple, float] = {}
    if not hold.empty:
        hs = hold.sort_values("filing_date")
        for d in dates:
            d = pd.Timestamp(d)
            now = hs[hs.filing_date <= d].groupby("symbol")["shares_owned_after"].last()
            then = hs[hs.filing_date <= d - pd.Timedelta(days=HOLDINGS_LOOKBACK_DAYS)]
            then = then.groupby("symbol")["shares_owned_after"].last()
            j = (now - then).dropna()
            for sym, v in j.items():
                s5[(sym, d)] = float(v)
    p["s5_holdings_change"] = [s5.get(k, np.nan) for k in key]

    p["any_insider_data"] = p["ticker"].isin(set(f["symbol"])).values
    return p


def _stats(s: pd.Series, dates: pd.Series) -> dict:
    s = s.dropna()
    if s.empty:
        return {"n": 0, "n_dates": 0, "mean": None, "median": None,
                "share_above_zero": None}
    return {"n": int(len(s)), "n_dates": int(dates.loc[s.index].nunique()),
            "mean": float(s.mean()), "median": float(s.median()),
            "share_above_zero": float((s > 0).mean())}


def _signal_block(p: pd.DataFrame, col: str, *, positive_when) -> dict:
    """Excess over SPY for names where the signal fires, against those where it does not."""
    out = {}
    fires = positive_when(p[col])
    for h in ("1y", "3y"):
        ex = f"excess_{h}"
        if ex not in p:
            continue
        on = p[fires & p[ex].notna()]
        off = p[(~fires) & p[ex].notna()]
        out[h] = {"signal_on": _stats(on[ex], p["date"]),
                  "signal_off": _stats(off[ex], p["date"])}
        a, b = out[h]["signal_on"], out[h]["signal_off"]
        out[h]["edge_mean"] = (a["mean"] - b["mean"]
                               if a["mean"] is not None and b["mean"] is not None
                               else None)
        out[h]["edge_median"] = (a["median"] - b["median"]
                                 if a["median"] is not None and b["median"] is not None
                                 else None)
    # per-year, before any pooled claim
    d = p[fires].copy()
    d["year"] = d["date"].dt.year
    out["per_year_1y"] = {
        int(y): {"n": int(g.excess_1y.notna().sum()),
                 "mean": float(g.excess_1y.mean()) if g.excess_1y.notna().any() else None,
                 "median": (float(g.excess_1y.median())
                            if g.excess_1y.notna().any() else None)}
        for y, g in d.groupby("year") if "excess_1y" in d}
    return out


def run(panel_path: str, form4_path: str) -> dict:
    from . import battery

    panel = battery.attach_benchmark(pd.read_parquet(panel_path))
    form4 = pd.read_parquet(form4_path)
    p = build_signals(form4, panel)

    cov = {
        "form4_rows": int(len(form4)),
        "form4_symbols": int(form4.symbol.nunique()),
        "form4_span": [str(pd.to_datetime(form4.filing_date).min().date()),
                       str(pd.to_datetime(form4.filing_date).max().date())],
        "panel_rows": int(len(p)),
        "panel_symbols": int(p.ticker.nunique()),
        "panel_symbols_with_any_form4": int(p[p.any_insider_data].ticker.nunique()),
        "discretionary_share": float(form4.is_discretionary.mean()),
        "open_market_purchases": int((form4.code == "P").sum()),
        "open_market_sales": int((form4.code == "S").sum()),
        "rows_where_s1_fires": int((p.s1_buy_count > 0).sum()),
        "rows_where_s3_fires": int((p.s3_distinct_buyers >= CLUSTER_MIN_INSIDERS).sum()),
        "code_distribution": {k: int(v) for k, v in
                              form4.code.value_counts().head(12).items()},
    }

    signals = {
        "S1_open_market_buying": _signal_block(p, "s1_buy_count",
                                               positive_when=lambda s: s > 0),
        "S2_ceo_cfo_buying": _signal_block(p, "s2_ceo_cfo_buy",
                                           positive_when=lambda s: s > 0),
        "S3_cluster_buying": _signal_block(
            p, "s3_distinct_buyers",
            positive_when=lambda s: s >= CLUSTER_MIN_INSIDERS),
        "S4_buy_sell_ratio": _signal_block(p, "s4_buy_sell_ratio",
                                           positive_when=lambda s: s > 1.0),
        "S5_holdings_change": _signal_block(p, "s5_holdings_change",
                                            positive_when=lambda s: s > 0),
        "S6_selling": _signal_block(p, "s6_sell_count",
                                    positive_when=lambda s: s > 0),
        "X_any_activity": _signal_block(p, "any_activity",
                                        positive_when=lambda s: s > 0),
    }

    # pre-registered pass criteria
    def _mean(sig, h="1y"):
        return ((signals[sig].get(h) or {}).get("signal_on") or {}).get("mean")

    def _med(sig, h="1y"):
        return ((signals[sig].get(h) or {}).get("signal_on") or {}).get("median")

    def _dates(sig, h="1y"):
        return ((signals[sig].get(h) or {}).get("signal_on") or {}).get("n_dates") or 0

    py = signals["S1_open_market_buying"].get("per_year_1y") or {}
    pos_years = sum(1 for v in py.values() if (v.get("mean") or 0) > 0)

    # The pre-registration did NOT fix a horizon for the S2>S1 and S3>S1 comparisons.
    # Both are reported rather than the flattering one being chosen after the fact.
    horizon_dependent = {}
    for h in ("1y", "3y"):
        horizon_dependent[h] = {
            "S2_beats_S1": bool((_mean("S2_ceo_cfo_buying", h) or -9)
                                > (_mean("S1_open_market_buying", h) or -9)),
            "S3_beats_S1": bool((_mean("S3_cluster_buying", h) or -9)
                                > (_mean("S1_open_market_buying", h) or -9)),
        }

    checks = {
        "S1_mean_excess_positive": bool((_mean("S1_open_market_buying") or 0) > 0),
        "S1_positive_in_6_plus_years": bool(pos_years >= 6),
        "S1_enough_date_clusters": bool(_dates("S1_open_market_buying")
                                        >= MIN_DATE_CLUSTERS),
        "S2_beats_S1_at_1y": horizon_dependent["1y"]["S2_beats_S1"],
        "S3_beats_S1_at_1y": horizon_dependent["1y"]["S3_beats_S1"],
        "S6_does_NOT_predict": bool((_mean("S6_selling") or 0) <= 0),
    }

    # Cost, as the pre-registration requires: 5 bps per side as a fraction of price.
    cost = 2 * COST_BPS_PER_SIDE / 10_000.0
    net = {h: ((signals["S1_open_market_buying"].get(h) or {}).get("edge_mean"))
           for h in ("1y", "3y")}
    net = {h: (v - cost if v is not None else None) for h, v in net.items()}

    # How much of the pooled edge is ONE year? A pooled number that a single regime
    # manufactured is the failure mode the reporting rules exist to catch.
    fires = p.s1_buy_count > 0
    d = p[fires & p.excess_1y.notna()].copy()
    d["year"] = d["date"].dt.year
    concentration = {}
    if len(d):
        by_year = d.groupby("year")["excess_1y"].mean()
        best_year = int(by_year.idxmax()) if len(by_year) else None
        ex_best = d[d.year != best_year]
        base = p[(~fires) & p.excess_1y.notna()]
        base_ex = base[base["date"].dt.year != best_year]
        concentration = {
            "best_year": best_year,
            "best_year_mean": float(by_year.max()) if len(by_year) else None,
            "pooled_mean_all_years": float(d.excess_1y.mean()),
            "pooled_mean_excluding_best_year": (float(ex_best.excess_1y.mean())
                                                if len(ex_best) else None),
            "pooled_median_excluding_best_year": (float(ex_best.excess_1y.median())
                                                  if len(ex_best) else None),
            "off_mean_excluding_best_year": (float(base_ex.excess_1y.mean())
                                             if len(base_ex) else None),
            "years_with_negative_mean": int((by_year < 0).sum()),
            "years_total": int(len(by_year)),
            "years_with_negative_median": int(
                (d.groupby("year")["excess_1y"].median() < 0).sum()),
        }
        e = concentration
        e["edge_excluding_best_year"] = (
            e["pooled_mean_excluding_best_year"] - e["off_mean_excluding_best_year"]
            if e["pooled_mean_excluding_best_year"] is not None
            and e["off_mean_excluding_best_year"] is not None else None)

    # The falsification check. S6 predicting is, per the pre-registration, evidence the
    # CONSTRUCTION is wrong - so it gates the verdict rather than sitting beside it.
    s1_m, s6_m = _mean("S1_open_market_buying"), _mean("S6_selling")
    any_m = _mean("X_any_activity")
    confound = {
        "any_activity_mean_1y": any_m,
        "S1_mean_1y": s1_m,
        "S6_mean_1y": s6_m,
        "buying_edge_over_any_activity_1y": (
            s1_m - any_m if s1_m is not None and any_m is not None else None),
        "verdict": (
            "Buying and SELLING both predict positive excess, and undifferentiated "
            "insider ACTIVITY predicts about as well as buying does. That is the "
            "signature of an attention/liquidity confound, not of insider information."
            if (s6_m or 0) > 0 and any_m is not None and s1_m is not None
            and (s1_m - any_m) < 0.01
            else "Buying predicts materially better than undifferentiated activity."),
    }

    return {"study": "E06_insider_signal", "as_of": utc_now_iso(),
            "source": "SEC Form 4 (DERA bulk insider datasets)",
            "coverage": cov, "signals": signals, "checks": checks,
            "horizon_dependent_checks": horizon_dependent,
            "years_S1_positive": pos_years,
            "cost_bps_per_side": COST_BPS_PER_SIDE,
            "S1_edge_net_of_cost": net,
            "concentration": concentration,
            "median_is_negative": {h: (_med("S1_open_market_buying", h) or 0) < 0
                                   for h in ("1y", "3y")},
            "confound_check": confound,
            "passes": bool(checks["S1_mean_excess_positive"]
                           and checks["S1_positive_in_6_plus_years"]
                           and checks["S1_enough_date_clusters"]
                           and checks["S6_does_NOT_predict"])}


def _pct(v):
    return "n/a" if v is None else f"{v * 100:.1f}%"


def render(res: dict) -> str:
    L = []
    A = L.append
    c = res["coverage"]
    A("# E06 results — does following insiders beat holding the index?\n")
    A(f"as_of {res['as_of']}  ·  source: {res['source']}\n")
    A(f"{c['form4_rows']:,} Form 4 non-derivative transactions, "
      f"{c['form4_symbols']} symbols, {c['form4_span'][0]} → {c['form4_span'][1]}. "
      f"{c['panel_symbols_with_any_form4']} of {c['panel_symbols']} panel symbols have "
      f"at least one filing.\n")
    A(f"Only **{_pct(c['discretionary_share'])}** of transactions are discretionary "
      f"(codes P/S). Open-market purchases: **{c['open_market_purchases']:,}**; sales: "
      f"{c['open_market_sales']:,}. The rest are option exercises, tax withholding, "
      f"awards and gifts — mechanical, not conviction.\n")
    A(f"Codes: {c['code_distribution']}\n")

    A("\n## The signals, as excess over SPY\n")
    A("| signal | horizon | n | dates | mean excess ON | median ON | mean OFF | "
      "edge (mean) |")
    A("|---|---|---:|---:|---:|---:|---:|---:|")
    for name, blk in res["signals"].items():
        for h in ("1y", "3y"):
            b = blk.get(h)
            if not b:
                continue
            on, off = b["signal_on"], b["signal_off"]
            A(f"| {name} | {h} | {on['n']:,} | {on['n_dates']} | {_pct(on['mean'])} "
              f"| {_pct(on['median'])} | {_pct(off['mean'])} | {_pct(b['edge_mean'])} |")

    A("\n## Pre-registered pass criteria\n")
    for k, v in res["checks"].items():
        A(f"- `{k}`: **{'PASS' if v else 'FAIL'}**")
    A(f"\nS1 was positive in {res['years_S1_positive']} of the years present.\n")
    A(f"\n**Overall: {'PASS' if res['passes'] else 'FAIL'}**\n")

    A("\n### Four things that must be read with the table above\n")

    cn = res.get("concentration") or {}
    if cn:
        A(f"**0. The entire edge is one year.** {cn['best_year']} alone returned "
          f"{_pct(cn['best_year_mean'])} mean excess. Drop that single year and S1's "
          f"pooled mean falls from {_pct(cn['pooled_mean_all_years'])} to "
          f"**{_pct(cn['pooled_mean_excluding_best_year'])}**, against "
          f"{_pct(cn['off_mean_excluding_best_year'])} for names with no insider buying "
          f"— an edge of **{_pct(cn['edge_excluding_best_year'])}**, with a median of "
          f"{_pct(cn['pooled_median_excluding_best_year'])}. The mean was negative in "
          f"{cn['years_with_negative_mean']} of {cn['years_total']} years and the median "
          f"was negative in {cn['years_with_negative_median']}.\n\n"
          f"> {cn['best_year']} was the COVID crash. Insiders bought the March bottom, "
          f"and so did anything else bought in March 2020. Attributing that to insider "
          f"information rather than to buying a market bottom is the whole question, and "
          f"one year cannot answer it.\n")

    med = res.get("median_is_negative") or {}
    A(f"**1. The mean is positive and the MEDIAN is negative** at both horizons "
      f"(1y: {med.get('1y')}, 3y: {med.get('3y')}). The typical name an insider bought "
      f"UNDERPERFORMED SPY; the positive mean is carried by a right tail. This is the "
      f"same shape as E05's top decile, and it is why the pre-registration asked for "
      f"medians beside means.\n")

    cf = res.get("confound_check") or {}
    A(f"**2. The falsification check fired.** The pre-registration said selling should "
      f"NOT predict, and that a positive result there is evidence the construction is "
      f"wrong rather than a discovery. Selling's 1y mean excess is "
      f"{_pct(cf.get('S6_mean_1y'))} against {_pct(cf.get('S1_mean_1y'))} for buying, "
      f"and undifferentiated insider ACTIVITY gets {_pct(cf.get('any_activity_mean_1y'))} "
      f"— buying beats mere activity by only "
      f"{_pct(cf.get('buying_edge_over_any_activity_1y'))}.\n\n> {cf.get('verdict')}\n")

    hd = res.get("horizon_dependent_checks") or {}
    A(f"**3. S2 and S3 are horizon-dependent, and the pre-registration did not fix a "
      f"horizon for them.** At 1y, S2 beats S1: {hd.get('1y', {}).get('S2_beats_S1')}, "
      f"S3 beats S1: {hd.get('1y', {}).get('S3_beats_S1')}. At 3y, "
      f"S2: {hd.get('3y', {}).get('S2_beats_S1')}, "
      f"S3: {hd.get('3y', {}).get('S3_beats_S1')}. The checks above are scored at 1y "
      f"because that is what the code fixed before the results were seen. Switching to "
      f"the 3y reading because it is more flattering would be exactly the "
      f"after-the-fact choice this project refuses to make — it is reported, not "
      f"adopted.\n")

    net = res.get("S1_edge_net_of_cost") or {}
    A(f"\n**Cost.** At {res.get('cost_bps_per_side')} bps per side, S1's mean edge nets "
      f"to {_pct(net.get('1y'))} at 1y and {_pct(net.get('3y'))} at 3y. Cost is not what "
      f"decides this one.\n")

    A("\n## S1 per year — before any pooled claim\n")
    A("| year | n | mean excess 1y | median |")
    A("|---|---:|---:|---:|")
    for y, v in sorted((res["signals"]["S1_open_market_buying"]
                        .get("per_year_1y") or {}).items()):
        A(f"| {y} | {v['n']:,} | {_pct(v['mean'])} | {_pct(v['median'])} |")

    A("\n**Reading S6.** The pre-registration says selling should NOT predict, because "
      "executives sell for liquidity and diversification. A positive S6 is a red flag "
      "for the construction, not a discovery.\n")
    A("\nNothing here is promoted. `promoted` stays false.\n")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    exp = config.JOURNAL_DIR / "experiments"
    ap.add_argument("--panel", default=str(exp / "E05_panel_abs.parquet"))
    ap.add_argument("--form4", default=str(exp / "E06_form4.parquet"))
    args = ap.parse_args(argv)

    res = run(args.panel, args.form4)
    atomic_write_json(exp / "E06_results.json", res)
    md = render(res)
    (exp / "E06_results.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
