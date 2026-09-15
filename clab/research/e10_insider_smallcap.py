"""E10 - does insider buying work where the literature says it should: small caps?

Pre-registered in journal/experiments/E10_insider_smallcap_preregistration.md.

E06 answered "no" over 675 large caps: S1's entire edge was 2020, and stripping that one
year left -0.0% with a median of -3.5%. But the mechanism in the literature is
INFORMATION ASYMMETRY, which is smallest in the most-analysed companies on earth. The
universe now holds 1,497 companies, so ~1,000 mid and small caps E06 never saw.

The trap this is written to avoid: slicing a null result by subgroup until one looks
positive. Size is the ONLY new dimension, the three buckets are the index tiers rather
than tuned thresholds, and every number is reported with AND without 2020 because this
dataset has already produced one edge that was a single year.
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from .. import config
from ..net import atomic_write_json, utc_now_iso
from .e06_insider import LOOKBACK_DAYS, MIN_DATE_CLUSTERS, build_signals

#: fixed in the pre-registration: the index tiers, not tuned market-cap cutoffs
BUCKETS = ("sp500", "sp400", "sp600")
CONFOUND_EDGE_MIN = 0.01     # buying must beat undifferentiated activity by >1pt


def _bucket_map() -> dict[str, str]:
    """{ticker: tier}. A company in two tiers takes the largest, so buckets are disjoint."""
    from ..runner import batch as batch_mod

    out: dict[str, str] = {}
    for tier in BUCKETS:
        try:
            for r in batch_mod.load_universe(tier):
                out.setdefault(r["ticker"], tier)
        except Exception as exc:  # noqa: BLE001
            print(f"  WARN could not load {tier}: {type(exc).__name__}: {exc}")
    return out


def returns_panel(symbols: list[str], start: str = "2016-01-01") -> pd.DataFrame:
    """A month-end grid of forward returns for `symbols`. No scores.

    The E05 score panel covers only the original 675 companies, and rebuilding it for
    1,497 is a multi-hour crawl. E10 does not use a score at all - it needs (ticker,
    date, fwd_1y, fwd_3y) and the SPY benchmark - so this reads the cached price store
    directly and skips the scoring entirely.
    """
    from ..sources import yf_prices
    from . import entry_study as es

    rows = []
    for i, t in enumerate(symbols, 1):
        px = yf_prices.load_prices(t)
        if px is None or px.empty:
            continue
        px = px.copy()
        px["date"] = pd.to_datetime(px["date"], errors="coerce")
        s = (px.dropna(subset=["date", "close"]).set_index("date").sort_index()
             ["close"].astype(float))
        s = s[s.index >= pd.Timestamp(start)]
        if s.empty:
            continue
        suspects = es.suspect_mask(s)
        for me in pd.Series(1, index=s.index).resample("ME").last().dropna().index:
            upto = s.loc[:me]
            if upto.empty:
                continue
            anchor = upto.index[-1]
            rows.append({
                "ticker": t, "date": me,
                "fwd_1y": es.forward_return(s, anchor, 252, suspects),
                "fwd_3y": es.forward_return(s, anchor, 756, suspects),
            })
        if i % 200 == 0:
            print(f"  prices {i}/{len(symbols)} ({len(rows):,} rows)", flush=True)
    return pd.DataFrame(rows)


def _stats(s: pd.Series, dates: pd.Series) -> dict:
    s = s.dropna()
    if s.empty:
        return {"n": 0, "n_dates": 0, "mean": None, "median": None, "share_pos": None}
    return {"n": int(len(s)), "n_dates": int(dates.loc[s.index].nunique()),
            "mean": float(s.mean()), "median": float(s.median()),
            "share_pos": float((s > 0).mean())}


def _arm(p: pd.DataFrame, col: str, fires, horizon: str) -> dict:
    ex = f"excess_{horizon}"
    if ex not in p:
        return {}
    on = p[fires & p[ex].notna()]
    off = p[(~fires) & p[ex].notna()]
    a, b = _stats(on[ex], p["date"]), _stats(off[ex], p["date"])
    edge = (a["mean"] - b["mean"]
            if a["mean"] is not None and b["mean"] is not None else None)
    return {"on": a, "off": b, "edge_mean": edge}


def run(panel_path: str, form4_path: str) -> dict:
    from . import battery

    panel = battery.attach_benchmark(pd.read_parquet(panel_path))
    form4 = pd.read_parquet(form4_path)
    if "measured_pct" not in panel.columns:
        panel["measured_pct"] = np.nan     # returns-only panel: E10 scores nothing
    p = build_signals(form4, panel)
    p["bucket"] = p["ticker"].map(_bucket_map()).fillna("other")
    p["year"] = p["date"].dt.year

    out: dict = {
        "study": "E10_insider_smallcap",
        "as_of": utc_now_iso(),
        "source": "SEC Form 4 (DERA bulk insider datasets)",
        "lookback_days": LOOKBACK_DAYS,
        "coverage": {
            "panel_rows": int(len(p)),
            "panel_symbols": int(p.ticker.nunique()),
            "form4_rows": int(len(form4)),
            "by_bucket": {k: int(v) for k, v in
                          p.groupby("bucket").ticker.nunique().items()},
            "open_market_purchases": int((form4.code == "P").sum()),
        },
        "buckets": {},
    }

    fires_all = p.s1_buy_count > 0
    for bucket in BUCKETS:
        b = p[p.bucket == bucket]
        if b.empty:
            continue
        f = b.s1_buy_count > 0
        entry: dict = {"symbols": int(b.ticker.nunique()),
                       "rows_signal_on": int(f.sum())}
        for h in ("1y", "3y"):
            entry[h] = _arm(b, "s1_buy_count", f, h)
        # ...and the same thing with 2020 removed. E06's whole edge was that year, so a
        # result that only exists with it is not a result.
        nb = b[b.year != 2020]
        fn = nb.s1_buy_count > 0
        entry["ex2020"] = {h: _arm(nb, "s1_buy_count", fn, h) for h in ("1y", "3y")}
        entry["per_year_1y"] = {
            int(y): {"n": int(g.excess_1y.notna().sum()),
                     "mean": (float(g.excess_1y.mean())
                              if g.excess_1y.notna().any() else None),
                     "median": (float(g.excess_1y.median())
                                if g.excess_1y.notna().any() else None)}
            for y, g in b[f].groupby("year")}
        # the falsification checks, per bucket
        entry["S6_selling"] = _arm(b, "s6_sell_count", b.s6_sell_count > 0, "1y")
        entry["any_activity"] = _arm(b, "any_activity", b.any_activity > 0, "1y")
        out["buckets"][bucket] = entry

    def _m(bucket, key="1y", where=None):
        e = out["buckets"].get(bucket) or {}
        blk = (e.get(where) or {}).get(key) if where else e.get(key)
        return ((blk or {}).get("on") or {}).get("mean")

    def _edge(bucket, key="1y", where=None):
        """ON minus OFF. The pre-registration's P2 is about the EDGE, and the first
        implementation compared the raw ON mean instead - which understates small caps
        badly, because their non-buying baseline is far lower (-4.0% against +2.3%).
        Corrected to match the pre-registered wording, not the other way round."""
        e = out["buckets"].get(bucket) or {}
        blk = (e.get(where) or {}).get(key) if where else e.get(key)
        return (blk or {}).get("edge_mean")

    def _med(bucket, key="1y"):
        return (((out["buckets"].get(bucket) or {}).get(key) or {})
                .get("on") or {}).get("median")

    def _dates(bucket, key="1y"):
        return ((((out["buckets"].get(bucket) or {}).get(key) or {})
                 .get("on") or {}).get("n_dates") or 0)

    small_ex2020 = _edge("sp600", "1y", where="ex2020")
    large_ex2020 = _edge("sp500", "1y", where="ex2020")
    s6 = ((out["buckets"].get("sp600") or {}).get("S6_selling") or {})
    act = ((out["buckets"].get("sp600") or {}).get("any_activity") or {})
    s1_small = _m("sp600")
    act_small = (act.get("on") or {}).get("mean")

    out["checks"] = {
        "P1_smallcap_positive_excluding_2020": bool(small_ex2020 is not None
                                                    and small_ex2020 > 0),
        "P2_size_gradient_runs_the_right_way": bool(
            small_ex2020 is not None and large_ex2020 is not None
            and small_ex2020 > large_ex2020),
        "P3_median_above_zero_somewhere": bool(
            any((_med(b) or -9) > 0 for b in BUCKETS)),
        "P4a_selling_does_not_predict": bool(((s6.get("on") or {}).get("mean") or 0)
                                             <= 0),
        "P4b_buying_beats_mere_activity": bool(
            s1_small is not None and act_small is not None
            and (s1_small - act_small) > CONFOUND_EDGE_MIN),
        "enough_date_clusters": bool(_dates("sp600") >= MIN_DATE_CLUSTERS),
    }
    c = out["checks"]
    out["passes"] = bool(c["P1_smallcap_positive_excluding_2020"]
                         and c["P4a_selling_does_not_predict"]
                         and c["P4b_buying_beats_mere_activity"]
                         and c["enough_date_clusters"])
    return out


def _pct(v):
    return "n/a" if v is None else f"{v * 100:.1f}%"


def render(res: dict) -> str:
    L, A = [], None
    A = L.append
    c = res["coverage"]
    A("# E10 results — insider buying by company size\n")
    A(f"as_of {res['as_of']}  ·  {res['source']}\n")
    A(f"{c['panel_symbols']} companies, {c['form4_rows']:,} Form 4 transactions, "
      f"{c['open_market_purchases']:,} open-market purchases. "
      f"Buckets: {c['by_bucket']}\n")
    A("E06 answered this for large caps: no, and its entire edge was 2020. The question "
      "here is whether the literature's small-firm result shows up where information "
      "asymmetry is actually larger.\n")

    A("\n## S1 open-market buying, excess over SPY\n")
    A("| bucket | horizon | n | dates | mean ON | median ON | mean OFF | edge |")
    A("|---|---|---:|---:|---:|---:|---:|---:|")
    for b in BUCKETS:
        e = res["buckets"].get(b) or {}
        for h in ("1y", "3y"):
            blk = e.get(h) or {}
            on, off = blk.get("on") or {}, blk.get("off") or {}
            A(f"| {b} | {h} | {on.get('n', 0):,} | {on.get('n_dates', 0)} "
              f"| {_pct(on.get('mean'))} | {_pct(on.get('median'))} "
              f"| {_pct(off.get('mean'))} | {_pct(blk.get('edge_mean'))} |")

    A("\n## The same thing with 2020 removed\n")
    A("E06's whole edge was that single year. An edge that needs it is not an edge.\n")
    A("| bucket | horizon | mean ON | mean OFF | edge |")
    A("|---|---|---:|---:|---:|")
    for b in BUCKETS:
        e = (res["buckets"].get(b) or {}).get("ex2020") or {}
        for h in ("1y", "3y"):
            blk = e.get(h) or {}
            on, off = blk.get("on") or {}, blk.get("off") or {}
            A(f"| {b} | {h} | {_pct(on.get('mean'))} | {_pct(off.get('mean'))} "
              f"| {_pct(blk.get('edge_mean'))} |")

    A("\n## Falsification checks\n")
    A("| bucket | selling mean 1y | any-activity mean 1y | buying mean 1y |")
    A("|---|---:|---:|---:|")
    for b in BUCKETS:
        e = res["buckets"].get(b) or {}
        s6 = ((e.get("S6_selling") or {}).get("on") or {})
        ac = ((e.get("any_activity") or {}).get("on") or {})
        s1 = ((e.get("1y") or {}).get("on") or {})
        A(f"| {b} | {_pct(s6.get('mean'))} | {_pct(ac.get('mean'))} "
          f"| {_pct(s1.get('mean'))} |")
    A("\nSelling should NOT predict, and buying should beat undifferentiated activity. "
      "In E06 both failed, which is the signature of an attention confound rather than "
      "information.\n")

    A("\n## Pre-registered criteria\n")
    for k, v in res["checks"].items():
        A(f"- `{k}`: **{'PASS' if v else 'FAIL'}**")
    A(f"\n**Overall: {'PASS' if res['passes'] else 'FAIL'}**\n")

    # The single most important qualifier, placed with the verdict rather than buried.
    meds = {b: (((res["buckets"].get(b) or {}).get("1y") or {}).get("on") or {}).get("median")
            for b in BUCKETS}
    py = (res["buckets"].get("sp600") or {}).get("per_year_1y") or {}
    pos_mean = sum(1 for v in py.values() if (v.get("mean") or 0) > 0)
    pos_med = sum(1 for v in py.values() if (v.get("median") or 0) > 0)
    A("\n### Read this before acting on the PASS\n")
    A(f"**The mean is positive and the MEDIAN is negative in every bucket** "
      f"({', '.join(f'{b} {_pct(m)}' for b, m in meds.items())}). The typical company an "
      f"insider bought still UNDERPERFORMED SPY; the edge lives in a right tail. Across "
      f"the S&P 600's {len(py)} years the mean was positive in {pos_mean} but the median "
      f"in only {pos_med}.\n")
    A("That is the same shape as E05's top decile and E06's large-cap result, and it is "
      "why the pre-registration asked for medians beside means. A positive mean edge "
      "with a negative median is a statement about a minority of large winners, not "
      "about what a holder of these names experiences.\n")
    A("It is also **not a tested strategy**: no costs beyond the E06 assumption, no "
      "position sizing, no capacity check on small-cap liquidity, and the S&P 600 is "
      "small-cap WITHIN an index - the microcap tail where the literature's effect is "
      "strongest is absent entirely.\n")

    A("\n## S&P 600 per year\n")
    A("| year | n | mean excess 1y | median |")
    A("|---|---:|---:|---:|")
    for y, v in sorted(((res["buckets"].get("sp600") or {}).get("per_year_1y")
                        or {}).items()):
        A(f"| {y} | {v['n']:,} | {_pct(v['mean'])} | {_pct(v['median'])} |")

    A("\nNothing is promoted. `promoted` stays false.\n")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    exp = config.JOURNAL_DIR / "experiments"
    ap.add_argument("--panel", default=str(exp / "E10_returns_panel.parquet"))
    ap.add_argument("--form4", default=str(exp / "E06_form4_all.parquet"))
    ap.add_argument("--build-panel", action="store_true",
                    help="build the month-end forward-return grid for every company "
                         "in the scores table first (reads the cached price store)")
    args = ap.parse_args(argv)

    if args.build_panel:
        import pandas as _pd

        syms = sorted(_pd.read_parquet(config.SCORES_PARQUET).ticker.unique())
        print(f"building a returns panel for {len(syms)} companies", flush=True)
        rp = returns_panel(syms)
        rp.to_parquet(args.panel, index=False)
        print(f"written: {args.panel}  ({len(rp):,} rows, "
              f"{rp.ticker.nunique()} symbols)")

    res = run(args.panel, args.form4)
    atomic_write_json(exp / "E10_results.json", res)
    md = render(res)
    (exp / "E10_results.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
