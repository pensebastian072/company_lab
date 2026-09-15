"""E08 - is the discount deserved? Moat DIRECTION as a value-trap filter.

Pre-registered in journal/experiments/E08_value_trap_preregistration.md. Hypotheses and
pass criteria were fixed before any statistic here was computed.

The idea is the user's: a deep discount is usually deep for a reason, and the reason is
normally a decaying moat. FICO's revenue rises on price while its position erodes; PayPal is
cheap because the growth case is gone. The measured half awards VA points for cheapness and
never asks whether the cheapness is deserved - a plausible mechanism for E05's finding that
the top decile's median 3-year excess over SPY is -7.6%.

Moat DIRECTION, not level, is the measurable. Share of sub-industry peer revenue per filing
vintage, and its 3-year change, both from the panel already on disk.

LIMIT, on every line: the peer group is S&P 500 members only, so this is share of large-cap
listed peers, not true market share. Private, foreign and small-cap competitors are
invisible, so a company losing real share to a private entrant can read as flat here.
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

from .. import config
from ..net import atomic_write_json, utc_now_iso
from . import battery, questions

MIN_PEERS = 5                 # a share number from 4 peers is noise, not a position
SHARE_WINDOW_MONTHS = 36      # "3-year" share change
#: a share move this large in 3y is more likely an acquisition than competitive advance,
#: so it is reported separately rather than quietly trusted
MERGER_LIKE_SHARE_JUMP = 0.10
MIN_DATE_CLUSTERS = 40
H3_REQUIRED_MEDIAN_EXCESS = 0.0


def build(panel_path: str) -> pd.DataFrame:
    """Attach share, 3-year share change, and the margin/share quadrant."""
    p = battery.attach_benchmark(pd.read_parquet(panel_path))
    p["date"] = pd.to_datetime(p["date"])
    p = p.sort_values(["ticker", "date"]).reset_index(drop=True)

    # share of sub-industry peer revenue, point-in-time (revenue_ttm is as-first-filed)
    grp = p.groupby(["date", "sub_industry"])
    peer_rev = grp["revenue_ttm"].transform("sum")
    peer_n = grp["revenue_ttm"].transform(lambda s: s.notna().sum())
    p["peer_n"] = peer_n
    p["share"] = np.where((peer_n >= MIN_PEERS) & (peer_rev > 0)
                          & p["revenue_ttm"].notna(),
                          p["revenue_ttm"] / peer_rev, np.nan)

    # 36-month change, per ticker, matched on the CALENDAR not on row position.
    # groupby().shift(36) would assume 36 contiguous monthly rows; removed constituents
    # and late listings have gaps, so for them a 36-row shift is not a 3-year change and
    # the "3-year" label would be silently wrong for exactly the survivorship-fix names.
    p["ym"] = p["date"].dt.year * 12 + p["date"].dt.month
    duplicate_month = p.duplicated(["ticker", "ym"], keep=False)
    if duplicate_month.any():
        examples = p.loc[duplicate_month, ["ticker", "date"]].head(5).to_dict("records")
        raise ValueError(f"multiple panel rows for one ticker-month: {examples}")
    lag = p[["ticker", "ym", "share", "operating_margin"]].copy()
    lag["ym"] = lag["ym"] + SHARE_WINDOW_MONTHS
    lag = lag.rename(columns={"share": "share_then",
                              "operating_margin": "margin_then"})
    p = p.merge(lag, on=["ticker", "ym"], how="left", validate="one_to_one")

    p["d_share_3y"] = p["share"] - p["share_then"]
    p["merger_like"] = p["d_share_3y"].abs() > MERGER_LIKE_SHARE_JUMP
    p["d_margin_3y"] = p["operating_margin"] - p["margin_then"]

    def _quadrant(r):
        dm, ds = r["d_margin_3y"], r["d_share_3y"]
        if pd.isna(dm) or pd.isna(ds):
            return None
        if ds >= 0:
            return "winning" if dm >= 0 else "buying_share"
        return "harvesting" if dm >= 0 else "losing"

    p["quadrant"] = p.apply(_quadrant, axis=1)
    p["share_rising"] = np.where(p["d_share_3y"].notna(), p["d_share_3y"] >= 0, None)

    # top decile of the score, per date
    p["decile"] = p.groupby("date")["measured_pct"].transform(
        lambda s: pd.qcut(s.rank(method="first"), 10, labels=False, duplicates="drop")
        if s.notna().sum() >= 10 else np.nan)
    p["top_decile"] = p["decile"] == p.groupby("date")["decile"].transform("max")
    return p


def _stats(s: pd.Series, dates: pd.Series | None = None) -> dict:
    s = s.dropna()
    out = {"n": int(len(s)),
           "mean": float(s.mean()) if len(s) else None,
           "median": float(s.median()) if len(s) else None,
           "share_above_zero": float((s > 0).mean()) if len(s) else None}
    if dates is not None:
        out["n_dates"] = int(dates.loc[s.index].nunique())
    return out


# ------------------------------------------------------------------ H1
def h1_share_direction(p: pd.DataFrame) -> dict:
    """Inside the top decile, does declining share predict worse excess over SPY?"""
    out = {"hypothesis": "H1: within the top decile, rising share beats declining share"}
    top = p[p.top_decile & p.d_share_3y.notna()]
    for h in ("1y", "3y"):
        col = f"excess_{h}"
        if col not in top:
            continue
        rising = top[top.d_share_3y >= 0]
        falling = top[top.d_share_3y < 0]
        out[h] = {"rising_share": _stats(rising[col], rising["date"]),
                  "declining_share": _stats(falling[col], falling["date"])}
        # excluding merger-like jumps, so a deal cannot manufacture the result
        clean = top[~top.merger_like]
        out[h]["rising_share_ex_mergers"] = _stats(
            clean[clean.d_share_3y >= 0][col], clean["date"])
        out[h]["declining_share_ex_mergers"] = _stats(
            clean[clean.d_share_3y < 0][col], clean["date"])

    checks = {}
    for h in ("1y", "3y"):
        if h not in out:
            continue
        r, f = out[h]["rising_share"], out[h]["declining_share"]
        enough = min(r.get("n_dates") or 0,
                     f.get("n_dates") or 0) >= MIN_DATE_CLUSTERS
        checks[h] = bool(enough and r["mean"] is not None and f["mean"] is not None
                         and r["mean"] > f["mean"] and r["median"] > f["median"])
    out["checks"] = checks
    out["passes"] = bool(checks and all(checks.values()))
    return out


# ------------------------------------------------------------------ H2
def h2_quadrants(p: pd.DataFrame) -> dict:
    """Is 'harvesting' (margin up, share down) the worst quadrant - the FICO case?"""
    out = {"hypothesis": "H2: harvesting is the worst quadrant, worse than plain losing"}
    d = p[p.quadrant.notna()]
    for h in ("1y", "3y"):
        col = f"excess_{h}"
        if col not in d:
            continue
        out[h] = {q: _stats(g[col], g["date"])
                  for q, g in d.groupby("quadrant")}
        out[f"{h}_top_decile_only"] = {
            q: _stats(g[col], g["date"])
            for q, g in d[d.top_decile].groupby("quadrant")}
    q3 = out.get("3y", {})
    harv = (q3.get("harvesting") or {}).get("median")
    lose = (q3.get("losing") or {}).get("median")
    win = (q3.get("winning") or {}).get("median")
    buy = (q3.get("buying_share") or {}).get("median")
    out["checks"] = {
        "harvesting_worse_than_winning": bool(harv is not None and win is not None
                                              and harv < win),
        "harvesting_worse_than_losing": bool(harv is not None and lose is not None
                                             and harv < lose),
        "harvesting_worse_than_buying_share": bool(
            harv is not None and buy is not None and harv < buy)}
    out["passes"] = bool(all(out["checks"].values()))
    return out


# ------------------------------------------------------------------ H3 (decisive)
def h3_filtered_top_decile(p: pd.DataFrame) -> dict:
    """THE test: does screening out declining share lift the top decile above SPY?

    Median, not mean. E05's whole lesson is that this distribution's mean is carried by a
    few very large winners, so a mean improvement proves nothing.
    """
    out = {"hypothesis": ("H3: excluding declining-share names raises the top decile's "
                          "MEDIAN excess over SPY above zero"),
           "criterion": f"median excess > {H3_REQUIRED_MEDIAN_EXCESS}"}
    top = p[p.top_decile]
    for h in ("1y", "3y"):
        col = f"excess_{h}"
        if col not in top:
            continue
        have = top[top.d_share_3y.notna()]
        # This is a veto test, not a data-availability screen: names whose share
        # direction is unknown remain eligible. Dropping NO_DATA would test a much
        # narrower universe than the pre-registered "exclude declining share" rule.
        kept = top[top.d_share_3y.isna() | (top.d_share_3y >= 0)]
        out[h] = {
            "unfiltered": _stats(top[col], top["date"]),
            "unfiltered_where_share_known": _stats(have[col], have["date"]),
            "filtered_excluding_declining_share": _stats(kept[col], kept["date"]),
            "rising_share_only": _stats(have[have.d_share_3y >= 0][col],
                                        have["date"]),
            "rising_share_only_ex_mergers": _stats(
                have[(have.d_share_3y >= 0) & (~have.merger_like)][col], have["date"]),
            "excluded_declining_share": _stats(have[have.d_share_3y < 0][col],
                                               have["date"]),
            "unknown_share_retained": _stats(top[top.d_share_3y.isna()][col],
                                             top["date"]),
        }
        out[h]["share_of_top_decile_excluded"] = (
            float((top.d_share_3y < 0).mean()) if len(top) else None)

    f3 = (out.get("3y") or {}).get("filtered_excluding_declining_share") or {}
    med = f3.get("median")
    out["checks"] = {
        "median_3y_excess_above_zero": bool(med is not None
                                            and med > H3_REQUIRED_MEDIAN_EXCESS),
        "enough_date_clusters": bool((f3.get("n_dates") or 0) >= MIN_DATE_CLUSTERS)}
    out["passes"] = bool(all(out["checks"].values()))
    return out


# ------------------------------------------------------------------ H4
def h4_independent_of_score(p: pd.DataFrame) -> dict:
    """Does share direction say anything the score does not already say?"""
    out = {"hypothesis": "H4: d_share_3y carries information independent of the score"}
    for h in ("1y", "3y"):
        col = f"excess_{h}"
        d = p.dropna(subset=["d_share_3y", "measured_pct", col])
        if len(d) < 500:
            continue
        raw = questions._summary(questions._ic_series(d, "d_share_3y", col))
        # partial out the score: rank-residualise both sides within each date
        dd = d.copy()
        for c in ("d_share_3y", col):
            dd[f"{c}_r"] = dd.groupby("date")[c].rank(pct=True)
        dd["score_r"] = dd.groupby("date")["measured_pct"].rank(pct=True)

        def _resid(g, c):
            x, y = g["score_r"], g[c]
            if len(g) < 10 or x.std(ddof=0) == 0:
                return y - y.mean()
            beta = np.cov(x, y, ddof=0)[0, 1] / np.var(x)
            return y - (y.mean() + beta * (x - x.mean()))

        parts = []
        for _dt, g in dd.groupby("date"):
            gg = g.copy()
            gg["ds_res"] = _resid(g, "d_share_3y_r")
            gg["ret_res"] = _resid(g, f"{col}_r")
            parts.append(gg)
        res = pd.concat(parts)
        partial = questions._summary(questions._ic_series(res, "ds_res", "ret_res"))
        out[h] = {"raw_ic": raw, "partial_ic_controlling_for_score": partial,
                  "n": int(len(d))}

    p3 = (out.get("3y") or {}).get("partial_ic_controlling_for_score") or {}
    out["checks"] = {"partial_ic_3y_positive": bool(p3.get("mean_ic") is not None
                                                    and p3["mean_ic"] > 0)}
    out["passes"] = bool(all(out["checks"].values()))
    return out


# ------------------------------------------------------------------ per-year
def per_year(p: pd.DataFrame) -> dict:
    """Per-year table before any pooled claim, as the reporting rules require."""
    top = p[p.top_decile & p.d_share_3y.notna()].copy()
    top["year"] = top["date"].dt.year
    out = {}
    for y, g in top.groupby("year"):
        r = g[g.d_share_3y >= 0]["excess_3y"].dropna()
        f = g[g.d_share_3y < 0]["excess_3y"].dropna()
        out[int(y)] = {
            "rising_n": int(len(r)),
            "rising_median": float(r.median()) if len(r) else None,
            "declining_n": int(len(f)),
            "declining_median": float(f.median()) if len(f) else None}
    return out


def _pct(v):
    return "n/a" if v is None or (isinstance(v, float) and pd.isna(v)) else f"{v * 100:.1f}%"


def render(res: dict) -> str:
    L, A = [], None
    A = L.append
    A("# E08 results — is the discount deserved?\n")
    A(f"as_of {res['as_of']}\n")
    c = res["coverage"]
    A(f"Panel: {c['rows']:,} rows, {c['symbols']} symbols. Share computable on "
      f"{_pct(c['share_computable_share_of_rows'])} of rows "
      f"(needs ≥{MIN_PEERS} sub-industry peers); 3-year share change on "
      f"{_pct(c['d_share_computable_share_of_rows'])}.\n")
    A("**Limit, and it is not a small one:** the peer group is S&P 500 members only, so "
      "this is share of large-cap LISTED peers, not true market share. A company losing "
      "real ground to a private or foreign competitor can read as flat here.\n")

    h3 = res["h3"]
    A("\n## H3 — the decisive test: does the filter beat SPY?\n")
    A(f"**{'PASS' if h3['passes'] else 'FAIL'}**\n")
    A("| top decile, 3y excess over SPY | n | mean | **median** | share > 0 |")
    A("|---|---:|---:|---:|---:|")
    for key, label in (("unfiltered", "unfiltered"),
                       ("unfiltered_where_share_known", "where share is known"),
                       ("filtered_excluding_declining_share",
                        "**declining share excluded; NO_DATA retained**"),
                       ("rising_share_only", "rising share only (diagnostic)"),
                       ("rising_share_only_ex_mergers",
                        "rising share only, ex-mergers (diagnostic)"),
                       ("excluded_declining_share", "declining share (excluded)")):
        s = (h3.get("3y") or {}).get(key) or {}
        A(f"| {label} | {s.get('n', 0):,} | {_pct(s.get('mean'))} "
          f"| **{_pct(s.get('median'))}** | {_pct(s.get('share_above_zero'))} |")
    A(f"\nThe filter drops {_pct((h3.get('3y') or {}).get('share_of_top_decile_excluded'))} "
      f"of the top decile. Criterion: median above zero.\n")

    h1 = res["h1"]
    A("\n## H1 — share direction inside the top decile\n")
    A(f"**{'PASS' if h1['passes'] else 'FAIL'}** — {h1.get('checks')}\n")
    A("| horizon | group | n | mean | median | share > 0 |")
    A("|---|---|---:|---:|---:|---:|")
    for h in ("1y", "3y"):
        for key in ("rising_share", "declining_share"):
            s = (h1.get(h) or {}).get(key) or {}
            A(f"| {h} | {key.replace('_', ' ')} | {s.get('n', 0):,} "
              f"| {_pct(s.get('mean'))} | {_pct(s.get('median'))} "
              f"| {_pct(s.get('share_above_zero'))} |")

    h2 = res["h2"]
    A("\n## H2 — the four quadrants (the FICO case is 'harvesting')\n")
    A(f"**{'PASS' if h2['passes'] else 'FAIL'}** — {h2.get('checks')}\n")
    A("| quadrant | n | 3y mean | 3y median | share > 0 |")
    A("|---|---:|---:|---:|---:|")
    for q in ("winning", "buying_share", "harvesting", "losing"):
        s = (h2.get("3y") or {}).get(q) or {}
        A(f"| {q} | {s.get('n', 0):,} | {_pct(s.get('mean'))} "
          f"| {_pct(s.get('median'))} | {_pct(s.get('share_above_zero'))} |")

    h4 = res["h4"]
    A("\n## H4 — is it independent of the score?\n")
    A(f"**{'PASS' if h4['passes'] else 'FAIL'}**\n")
    A("| horizon | raw IC | partial IC controlling for the score |")
    A("|---|---:|---:|")
    for h in ("1y", "3y"):
        b = h4.get(h) or {}
        A(f"| {h} | {_pct((b.get('raw_ic') or {}).get('mean_ic'))} "
          f"| {_pct((b.get('partial_ic_controlling_for_score') or {}).get('mean_ic'))} |")

    A("\n## Per year — top decile 3y median excess, rising vs declining share\n")
    A("| year | rising n | rising median | declining n | declining median |")
    A("|---|---:|---:|---:|---:|")
    for y, v in sorted((res.get("per_year") or {}).items()):
        A(f"| {y} | {v['rising_n']:,} | {_pct(v['rising_median'])} "
          f"| {v['declining_n']:,} | {_pct(v['declining_median'])} |")

    A("\nNothing here is promoted. `promoted` stays false. A scoring change requires its "
      "own pre-registration and only if H3 passed.\n")
    return "\n".join(L)


def _console_safe(text: str, encoding: str | None) -> str:
    """Keep Windows' legacy console encoding from turning a completed run into exit 1."""
    encoding = encoding or "utf-8"
    return text.encode(encoding, errors="backslashreplace").decode(encoding)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    exp = config.JOURNAL_DIR / "experiments"
    ap.add_argument("--panel", default=str(exp / "E05_panel_abs.parquet"))
    args = ap.parse_args(argv)

    p = build(args.panel)
    res = {
        "study": "E08_value_trap",
        "as_of": utc_now_iso(),
        "coverage": {
            "rows": int(len(p)), "symbols": int(p.ticker.nunique()),
            "share_computable_share_of_rows": float(p.share.notna().mean()),
            "d_share_computable_share_of_rows": float(p.d_share_3y.notna().mean()),
            "median_peer_n": float(p.peer_n.median()),
            "merger_like_share_of_rows": float(p.merger_like.mean()),
            "limit": ("peer group is S&P 500 members only - share of large-cap LISTED "
                      "peers, not true market share"),
        },
        "h1": h1_share_direction(p),
        "h2": h2_quadrants(p),
        "h3": h3_filtered_top_decile(p),
        "h4": h4_independent_of_score(p),
        "per_year": per_year(p),
    }
    atomic_write_json(exp / "E08_results.json", res)
    md = render(res)
    (exp / "E08_results.md").write_text(md, encoding="utf-8")
    p.to_parquet(exp / "E08_share_panel.parquet", index=False)
    print(_console_safe(md, getattr(sys.stdout, "encoding", None)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
