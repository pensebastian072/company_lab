"""E02 — the six pre-registered questions, run against the point-in-time panel.

Pre-registration: journal/experiments/E02_measured_half_battery_preregistration.md
Panel: clab/research/panel.py

Q1 does the measured score rank forward returns?
Q2 detection timing on the realised winners  <- the centrepiece
Q3 what did it flag that went badly?
Q4 which component carries any signal there is?
Q5 do the framework's own bands order returns?
Q6 does the score fall before price does?

Reporting rules from the pre-registration: per-year before pooled, medians beside
means, n everywhere, no claim on n < 30, negative results stated as plainly as
positive ones.

Usage:
  python -m clab.research.battery
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

from .. import config
from ..net import atomic_write_json, utc_now_iso

PANEL = config.JOURNAL_DIR / "experiments" / "E02_panel.parquet"
MIN_N = 30
DECILES = 10


def attach_benchmark(p: pd.DataFrame) -> pd.DataFrame:
    """Add SPY forward returns at each month-end, and excess columns.

    Absolute returns over 2016-2025 flatter everything - the market rose. The
    benchmark-relative number is the one that answers "did this beat just owning
    the index", which is the only comparison that matters for a stock picker.
    """
    from ..sources import yf_prices
    from . import entry_study as es

    spy = yf_prices.load_prices("SPY")
    if spy is None or spy.empty:
        p["spy_1y"] = None
        p["spy_3y"] = None
        p["excess_1y"] = None
        p["excess_3y"] = None
        return p
    spy = spy.copy()
    spy["date"] = pd.to_datetime(spy["date"], errors="coerce")
    s = (spy.dropna(subset=["date", "close"]).set_index("date").sort_index()
            ["close"].astype(float))
    susp = es.suspect_mask(s)

    bench: dict[pd.Timestamp, dict] = {}
    for me in sorted(p["date"].unique()):
        me = pd.Timestamp(me)
        upto = s.loc[:me]
        if upto.empty:
            continue
        anchor = upto.index[-1]
        bench[me] = {
            "spy_1y": es.forward_return(s, anchor, 252, susp),
            "spy_3y": es.forward_return(s, anchor, 756, susp),
        }
    p["spy_1y"] = p["date"].map(lambda d: (bench.get(pd.Timestamp(d)) or {}).get("spy_1y"))
    p["spy_3y"] = p["date"].map(lambda d: (bench.get(pd.Timestamp(d)) or {}).get("spy_3y"))
    for h in ("1y", "3y"):
        p[f"excess_{h}"] = p[f"fwd_{h}"] - p[f"spy_{h}"]
    return p


def _spearman(a: pd.Series, b: pd.Series) -> float | None:
    d = pd.DataFrame({"a": a, "b": b}).dropna()
    if len(d) < 10:
        return None
    return float(d["a"].rank().corr(d["b"].rank()))


def _stats(s: pd.Series) -> dict:
    s = s.dropna()
    if s.empty:
        return {"n": 0, "mean": None, "median": None, "hit": None}
    return {"n": int(len(s)), "mean": float(s.mean()), "median": float(s.median()),
            "hit": float((s > 0).mean())}


# ------------------------------------------------------------------ Q1
def q1_deciles(p: pd.DataFrame) -> dict:
    """Sort by measured_pct each month; does the top decile beat the bottom?"""
    out: dict = {"question": "Does the measured score rank forward returns?"}
    d = p.dropna(subset=["measured_pct", "fwd_1y"]).copy()
    if d.empty:
        return {**out, "verdict": "no data"}
    d["decile"] = d.groupby("date")["measured_pct"].transform(
        lambda s: pd.qcut(s.rank(method="first"), DECILES, labels=False,
                          duplicates="drop") if s.notna().sum() >= DECILES else np.nan)
    by_dec = {}
    for dec, grp in d.dropna(subset=["decile"]).groupby("decile"):
        by_dec[int(dec)] = {**_stats(grp["fwd_1y"]),
                            "mean_score_pct": float(grp["measured_pct"].mean())}
    out["by_decile_1y"] = by_dec

    ics = d.groupby("date").apply(
        lambda g: _spearman(g["measured_pct"], g["fwd_1y"]), include_groups=False)
    ics = ics.dropna()
    out["monthly_ic_1y"] = {"n_months": int(len(ics)),
                            "mean": float(ics.mean()) if len(ics) else None,
                            "median": float(ics.median()) if len(ics) else None,
                            "share_positive": float((ics > 0).mean()) if len(ics) else None}

    # the same decile split measured against the index rather than against zero
    if "excess_1y" in d:
        by_dec_ex = {}
        for dec, grp in d.dropna(subset=["decile"]).groupby("decile"):
            by_dec_ex[int(dec)] = _stats(grp["excess_1y"])
        out["by_decile_excess_1y"] = by_dec_ex
        ics_ex = d.groupby("date").apply(
            lambda g: _spearman(g["measured_pct"], g["excess_1y"]),
            include_groups=False).dropna()
        out["monthly_ic_excess_1y"] = {
            "n_months": int(len(ics_ex)),
            "mean": float(ics_ex.mean()) if len(ics_ex) else None,
            "share_positive": float((ics_ex > 0).mean()) if len(ics_ex) else None}

    per_year = {}
    for year, grp in d.dropna(subset=["decile"]).groupby(d["date"].dt.year):
        top = grp[grp.decile == grp.decile.max()]["fwd_1y"]
        bot = grp[grp.decile == grp.decile.min()]["fwd_1y"]
        top_ex = grp[grp.decile == grp.decile.max()].get("excess_1y")
        bot_ex = grp[grp.decile == grp.decile.min()].get("excess_1y")
        yic = grp.groupby("date").apply(
            lambda g: _spearman(g["measured_pct"], g["fwd_1y"]), include_groups=False).dropna()
        per_year[int(year)] = {
            "n": int(len(grp)),
            "top_decile_mean": float(top.mean()) if len(top) else None,
            "bottom_decile_mean": float(bot.mean()) if len(bot) else None,
            "top_minus_bottom": (float(top.mean() - bot.mean())
                                 if len(top) and len(bot) else None),
            "top_decile_median": float(top.median()) if len(top) else None,
            "bottom_decile_median": float(bot.median()) if len(bot) else None,
            "mean_ic": float(yic.mean()) if len(yic) else None,
            # vs the index: beat SPY or not, which is the question that matters
            "top_decile_excess": (float(top_ex.mean())
                                  if top_ex is not None and top_ex.notna().any() else None),
            "bottom_decile_excess": (float(bot_ex.mean())
                                     if bot_ex is not None and bot_ex.notna().any() else None),
            "spy_1y": (float(grp["spy_1y"].mean())
                       if "spy_1y" in grp and grp["spy_1y"].notna().any() else None),
        }
    out["per_year"] = per_year
    yrs = [v for v in per_year.values() if v["top_minus_bottom"] is not None]
    pos = sum(1 for v in yrs if v["top_minus_bottom"] > 0)
    out["years_top_beats_bottom"] = f"{pos}/{len(yrs)}"
    mean_ic = out["monthly_ic_1y"]["mean"]
    out["passes"] = bool(mean_ic is not None and mean_ic > 0 and pos >= 6)
    out["verdict"] = ("measured score ranks forward returns"
                      if out["passes"] else
                      "measured score does NOT reliably rank forward returns")
    return out


# ------------------------------------------------------------------ Q2
def q2_detection(p: pd.DataFrame, n_winners: int = 25) -> dict:
    """THE question: for the biggest realised winners, when was the score high?"""
    out: dict = {"question": "Detection timing on the realised winners",
                 "n_winners": n_winners}
    d = p.dropna(subset=["fwd_3y"]).copy()
    if d.empty:
        return {**out, "verdict": "no data"}

    # for each symbol take its single best 3y window; that is "the move"
    best = (d.sort_values("fwd_3y", ascending=False)
             .groupby("ticker").first().reset_index()
             .sort_values("fwd_3y", ascending=False).head(n_winners))

    rows = []
    for _i, w in best.iterrows():
        sym = p[p.ticker == w.ticker].sort_values("date")
        start = w["date"]
        before = sym[sym.date <= start]
        prior12 = before[before.date > start - pd.Timedelta(days=400)]
        score_at = w.get("measured_pct")
        rec = {
            "ticker": w.ticker,
            "move_start": str(pd.Timestamp(start).date()),
            "fwd_3y": float(w["fwd_3y"]),
            "score_pct_at_start": float(score_at) if pd.notna(score_at) else None,
            "score_pct_12m_before": (float(prior12.iloc[0]["measured_pct"])
                                     if len(prior12) and pd.notna(prior12.iloc[0]["measured_pct"])
                                     else None),
            "max_score_pct_before": (float(before["measured_pct"].max())
                                     if before["measured_pct"].notna().any() else None),
            "months_of_history_before": int(len(before)),
            "en_at_start": int(w["en"]) if pd.notna(w.get("en")) else None,
            "fe_at_start": int(w["fe"]) if pd.notna(w.get("fe")) else None,
            "va_at_start": int(w["va"]) if pd.notna(w.get("va")) else None,
            "pe_pctile_at_start": (float(w["pe_pctile_own"])
                                   if pd.notna(w.get("pe_pctile_own")) else None),
        }
        for thr in (0.60, 0.70):
            rec[f"crossed_{int(thr * 100)}pct_before"] = bool(
                before["measured_pct"].max() >= thr) if before["measured_pct"].notna().any() else None
            hits = before[before["measured_pct"] >= thr]
            rec[f"first_cross_{int(thr * 100)}"] = (str(hits.iloc[0]["date"].date())
                                                    if len(hits) else None)
        rows.append(rec)
    out["winners"] = rows

    # Classify each miss: was it knowable from the data at the time, or not?
    #
    #   should_have_seen   the fundamentals were already strong (FE high) but the
    #                      score was held down by valuation or entry - i.e. the
    #                      framework SAW the quality and refused the price
    #   couldnt_have_seen  the fundamentals were not yet strong at the start of the
    #                      move; the earnings arrived afterwards, so no
    #                      fundamentals-based score could have known
    #   caught             the score was already high before the move
    for r in rows:
        fe = r.get("fe_at_start")
        score = r.get("score_pct_at_start")
        if score is not None and score >= 0.70:
            r["verdict"] = "caught"
        elif fe is not None and fe >= 10:
            r["verdict"] = "should_have_seen"      # quality visible, price refused
        elif fe is not None:
            r["verdict"] = "couldnt_have_seen"     # earnings had not arrived yet
        else:
            r["verdict"] = "no_data"

    at_start = [r["score_pct_at_start"] for r in rows if r["score_pct_at_start"] is not None]
    universe_mean = float(p["measured_pct"].mean())
    out["summary"] = {
        "universe_mean_score_pct": universe_mean,
        "winners_mean_score_pct_at_start": float(np.mean(at_start)) if at_start else None,
        "winners_above_universe_mean": (
            sum(1 for v in at_start if v > universe_mean) if at_start else None),
        "share_crossing_70pct_before_move": float(np.mean(
            [1.0 if r["crossed_70pct_before"] else 0.0 for r in rows
             if r["crossed_70pct_before"] is not None])) if rows else None,
        "share_crossing_60pct_before_move": float(np.mean(
            [1.0 if r["crossed_60pct_before"] else 0.0 for r in rows
             if r["crossed_60pct_before"] is not None])) if rows else None,
    }
    verdicts: dict[str, int] = {}
    for r in rows:
        verdicts[r["verdict"]] = verdicts.get(r["verdict"], 0) + 1
    out["verdict_counts"] = verdicts
    out["verdict_meaning"] = {
        "caught": "score already >=70% of available points before the move",
        "should_have_seen": ("fundamentals were already strong (FE >= 10/15) but "
                            "valuation or entry held the score down - the framework "
                            "saw the quality and refused the price"),
        "couldnt_have_seen": ("fundamentals were not yet strong at the start; the "
                              "earnings arrived after the move, so no "
                              "fundamentals-based score could have known"),
    }
    return out


# ------------------------------------------------------------------ Q3
def q3_false_positives(p: pd.DataFrame) -> dict:
    out: dict = {"question": "What did it flag that went badly?"}
    d = p.dropna(subset=["measured_pct", "fwd_1y"]).copy()
    if d.empty:
        return {**out, "verdict": "no data"}
    d["decile"] = d.groupby("date")["measured_pct"].transform(
        lambda s: pd.qcut(s.rank(method="first"), DECILES, labels=False,
                          duplicates="drop") if s.notna().sum() >= DECILES else np.nan)
    top = d[d.decile == d.decile.max()]
    bad = top[top.fwd_1y < -0.20]
    out["n_top_decile"] = int(len(top))
    out["n_bad"] = int(len(bad))
    out["bad_rate"] = float(len(bad) / len(top)) if len(top) else None
    base_bad = float((d.fwd_1y < -0.20).mean())
    out["universe_bad_rate"] = base_bad
    out["worse_than_base_rate"] = bool(out["bad_rate"] is not None
                                       and out["bad_rate"] > base_bad)
    if len(bad):
        by_comp = {}
        for c in ("fe", "bs", "va", "en"):
            by_comp[c] = {"mean_in_bad": float(bad[c].mean()),
                          "mean_in_good": float(top[top.fwd_1y >= -0.20][c].mean())}
        out["component_means"] = by_comp
        out["worst"] = [
            {"ticker": r.ticker, "date": str(r.date.date()),
             "fwd_1y": float(r.fwd_1y), "score_pct": float(r.measured_pct),
             "fe": int(r.fe), "bs": int(r.bs), "va": int(r.va), "en": int(r.en)}
            for _i, r in bad.nsmallest(12, "fwd_1y").iterrows()]
        out["by_sector"] = (bad.groupby("sector").size()
                            .sort_values(ascending=False).head(8).to_dict())
    return out


# ------------------------------------------------------------------ Q4
def q4_component_ic(p: pd.DataFrame) -> dict:
    out: dict = {"question": "Which component carries any signal there is?"}
    d = p.dropna(subset=["fwd_1y"]).copy()
    res = {}
    for c in ("fe", "bs", "va", "en", "measured_pct"):
        if c not in d:
            continue
        ics = d.groupby("date").apply(
            lambda g, c=c: _spearman(g[c], g["fwd_1y"]), include_groups=False).dropna()
        res[c] = {"n_months": int(len(ics)),
                  "mean_ic": float(ics.mean()) if len(ics) else None,
                  "median_ic": float(ics.median()) if len(ics) else None,
                  "share_positive": float((ics > 0).mean()) if len(ics) else None}
    out["ic_1y"] = res
    if res:
        ranked = sorted(((k, v["mean_ic"]) for k, v in res.items()
                         if v["mean_ic"] is not None), key=lambda kv: -kv[1])
        out["ranked_by_mean_ic"] = ranked
    return out


# ------------------------------------------------------------------ Q5
def q5_bands(p: pd.DataFrame) -> dict:
    """Bands on the measured subset, using the same thresholds on the % scale."""
    out: dict = {"question": "Do the framework's own bands order returns?"}
    d = p.dropna(subset=["measured_pct", "fwd_1y"]).copy()
    if d.empty:
        return {**out, "verdict": "no data"}
    edges = [(0.90, "EXCEPTIONAL"), (0.80, "HIGH_CONVICTION"), (0.70, "INVESTABLE"),
             (0.60, "WATCHLIST"), (0.50, "WEAK"), (0.0, "REJECT")]

    def band(v):
        for e, name in edges:
            if v >= e:
                return name
        return "REJECT"

    d["band_measured"] = d["measured_pct"].map(band)
    order = [n for _e, n in edges]
    res = {}
    for name in order:
        grp = d[d.band_measured == name]
        if len(grp):
            res[name] = _stats(grp["fwd_1y"])
    out["by_band_1y"] = res
    means = [(n, res[n]["mean"]) for n in order if n in res and res[n]["n"] >= MIN_N]
    monotone = all(means[i][1] >= means[i + 1][1] for i in range(len(means) - 1)) \
        if len(means) > 1 else None
    out["ordering_checked"] = [n for n, _m in means]
    out["monotone"] = monotone
    out["passes"] = bool(monotone)
    return out


# ------------------------------------------------------------------ Q6
def q6_deterioration(p: pd.DataFrame) -> dict:
    out: dict = {"question": "Does the score fall before price does?"}
    d = p.sort_values(["ticker", "date"]).copy()
    d["fwd_1y_next"] = d.groupby("ticker")["fwd_1y"].shift(0)
    events = d[d.fwd_1y_next < -0.30]
    if events.empty:
        return {**out, "verdict": "no drawdown events"}
    led = 0
    total = 0
    detail = []
    for _i, ev in events.iterrows():
        sym = d[(d.ticker == ev.ticker) & (d.date <= ev.date)]
        prior = sym[sym.date > ev.date - pd.Timedelta(days=200)]
        if len(prior) < 4 or prior["measured_pct"].isna().all():
            continue
        total += 1
        change = float(prior["measured_pct"].iloc[-1] - prior["measured_pct"].iloc[0])
        if change < -0.02:
            led += 1
        detail.append({"ticker": ev.ticker, "date": str(ev.date.date()),
                       "fwd_1y": float(ev.fwd_1y_next),
                       "score_change_prior_6m": round(change, 4)})
    out["n_drawdown_events"] = total
    out["share_score_was_already_falling"] = float(led / total) if total else None
    out["examples"] = detail[:12]
    out["note"] = ("A score that falls before price would be genuinely useful. "
                   "A share near 0.5 means the score carries no early warning.")
    return out


# ------------------------------------------------------------------ render
def render(res: dict) -> str:
    L, a = [], lambda s: L.append(s)
    a("# E02 — what the measured half catches, misses, and when\n")
    a(f"Run {res['as_of']}. Pre-registered: "
      f"`journal/experiments/E02_measured_half_battery_preregistration.md`\n")
    m = res["panel"]
    a(f"Panel: **{m['rows']} month-ends** across **{m['symbols']} companies**, "
      f"{m['start']} to {m['end']}. Median available points **{m['median_avail']:.0f}"
      f" of 45** (ER, PEG, forward P/E and reverse DCF are not reconstructible; the "
      f"LLM half is excluded entirely).\n")

    q = res["q1"]
    a("\n## Q1 — does the measured score rank forward returns?\n")
    a("Absolute returns flatter everything in a rising market, so the excess-over-SPY "
      "columns are the ones that answer 'did this beat just owning the index'.\n")
    a("| year | n | SPY | top decile | bottom decile | top − bottom | top vs SPY | mean IC |")
    a("|---|---:|---:|---:|---:|---:|---:|---:|")
    for y, v in sorted(q.get("per_year", {}).items()):
        a(f"| {y} | {v['n']} | {_p(v.get('spy_1y'))} | {_p(v['top_decile_mean'])} "
          f"| {_p(v['bottom_decile_mean'])} | {_p(v['top_minus_bottom'])} "
          f"| {_p(v.get('top_decile_excess'))} | {_n(v['mean_ic'])} |")
    a(f"\nTop decile beat bottom in **{q.get('years_top_beats_bottom')}** years. "
      f"Mean monthly IC **{_n(q['monthly_ic_1y']['mean'])}**, positive in "
      f"{_p(q['monthly_ic_1y']['share_positive'])} of months.")
    a(f"\n**{'PASS' if q.get('passes') else 'FAIL'} — {q.get('verdict')}**\n")
    ex = q.get("monthly_ic_excess_1y") or {}
    if ex:
        a(f"\nAgainst the index: mean monthly IC vs **excess** return "
          f"**{_n(ex.get('mean'))}**, positive in {_s(ex.get('share_positive'))} "
          f"of months.\n")
    a("\n| decile | n | mean 1y | median 1y | hit | vs SPY | mean score |")
    a("|---|---:|---:|---:|---:|---:|---:|")
    dex = q.get("by_decile_excess_1y") or {}
    for dec, v in sorted(q.get("by_decile_1y", {}).items()):
        a(f"| {dec} | {v['n']} | {_p(v['mean'])} | {_p(v['median'])} | {_s(v['hit'])} "
          f"| {_p((dex.get(dec) or {}).get('mean'))} | {_p(v['mean_score_pct'])} |")

    q = res["q2"]
    a("\n## Q2 — detection timing on the biggest realised winners\n")
    s = q.get("summary", {})
    a(f"Universe mean score {_p(s.get('universe_mean_score_pct'))}; the winners "
      f"averaged {_p(s.get('winners_mean_score_pct_at_start'))} at the start of their "
      f"move, and {s.get('winners_above_universe_mean')} of {q.get('n_winners')} were "
      f"above the universe mean.\n")
    a(f"Share that ever crossed 70% of available points BEFORE the move: "
      f"**{_s(s.get('share_crossing_70pct_before_move'))}**; 60%: "
      f"**{_s(s.get('share_crossing_60pct_before_move'))}**.\n")
    vc = q.get("verdict_counts") or {}
    if vc:
        a("\n**What we got wrong, split by whether it was knowable at the time:**\n")
        for k in ("caught", "should_have_seen", "couldnt_have_seen", "no_data"):
            if k in vc:
                a(f"- **{k}**: {vc[k]} of {q.get('n_winners')} — "
                  f"{(q.get('verdict_meaning') or {}).get(k, '')}")
        a("")
    a("\n| ticker | move start | 3y return | score at start | 12m before | max before "
      "| crossed 70% first at | EN | FE | VA | verdict |")
    a("|---|---|---:|---:|---:|---:|---|---:|---:|---:|---|")
    for w in q.get("winners", []):
        a(f"| {w['ticker']} | {w['move_start']} | {_p(w['fwd_3y'])} "
          f"| {_p(w['score_pct_at_start'])} | {_p(w['score_pct_12m_before'])} "
          f"| {_p(w['max_score_pct_before'])} | {w.get('first_cross_70') or 'never'} "
          f"| {w['en_at_start']} | {w['fe_at_start']} | {w['va_at_start']} "
          f"| {w.get('verdict', '')} |")

    q = res["q3"]
    a("\n## Q3 — what it flagged that went badly\n")
    a(f"Top-decile rows: {q.get('n_top_decile')}. Of those, {q.get('n_bad')} lost more "
      f"than 20% over the next year — a rate of {_s(q.get('bad_rate'))} against a "
      f"universe base rate of {_s(q.get('universe_bad_rate'))}"
      f"{' (WORSE than the base rate)' if q.get('worse_than_base_rate') else ''}.\n")
    if q.get("worst"):
        a("\n| ticker | date | 1y | score | FE | BS | VA | EN |")
        a("|---|---|---:|---:|---:|---:|---:|---:|")
        for w in q["worst"]:
            a(f"| {w['ticker']} | {w['date']} | {_p(w['fwd_1y'])} | {_p(w['score_pct'])} "
              f"| {w['fe']} | {w['bs']} | {w['va']} | {w['en']} |")
    if q.get("by_sector"):
        a("\nBy sector: " + ", ".join(f"{k} {v}" for k, v in q["by_sector"].items()))

    q = res["q4"]
    a("\n## Q4 — which component carries the signal\n")
    a("| component | months | mean IC | median IC | share positive |")
    a("|---|---:|---:|---:|---:|")
    for c, v in q.get("ic_1y", {}).items():
        a(f"| {c} | {v['n_months']} | {_n(v['mean_ic'])} | {_n(v['median_ic'])} "
          f"| {_s(v['share_positive'])} |")

    q = res["q5"]
    a("\n## Q5 — do the bands order returns?\n")
    a("| band | n | mean 1y | median 1y | hit |")
    a("|---|---:|---:|---:|---:|")
    for b, v in q.get("by_band_1y", {}).items():
        a(f"| {b} | {v['n']} | {_p(v['mean'])} | {_p(v['median'])} | {_s(v['hit'])} |")
    a(f"\nMonotone across bands with n>={MIN_N} "
      f"({', '.join(q.get('ordering_checked') or [])}): "
      f"**{q.get('monotone')}** — {'PASS' if q.get('passes') else 'FAIL'}\n")

    q = res["q6"]
    a("\n## Q6 — does the score fall before price?\n")
    a(f"{q.get('n_drawdown_events')} events where the next year lost more than 30%. "
      f"The score was already falling beforehand in "
      f"**{_s(q.get('share_score_was_already_falling'))}** of them.\n")
    a(f"{q.get('note', '')}\n")

    a("\n## What none of this can tell you\n")
    for c in res["caveats"]:
        a(f"- {c}")
    return "\n".join(L) + "\n"


def _p(v) -> str:
    if v is None:
        return "-"
    try:
        return f"{float(v) * 100:+.1f}%"
    except (TypeError, ValueError):
        return str(v)


def _s(v) -> str:
    """A share or rate: no sign, since 'positive in +66.7% of months' reads wrong."""
    if v is None:
        return "-"
    try:
        return f"{float(v) * 100:.1f}%"
    except (TypeError, ValueError):
        return str(v)


def _n(v) -> str:
    if v is None:
        return "-"
    try:
        return f"{float(v):+.3f}"
    except (TypeError, ValueError):
        return str(v)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--panel", default=str(PANEL))
    args = ap.parse_args(argv)

    p = pd.read_parquet(args.panel)
    p["date"] = pd.to_datetime(p["date"])
    p = attach_benchmark(p)
    res = {
        "study": "E02_measured_half_battery",
        "as_of": utc_now_iso(),
        "panel": {"rows": int(len(p)), "symbols": int(p.ticker.nunique()),
                  "start": str(p.date.min().date()), "end": str(p.date.max().date()),
                  "median_avail": float(p.measured_avail.median())},
        "caveats": [
            "The LLM half (SG/BQ/MG, 50 points) is excluded - it cannot be "
            "backtested without hindsight.",
            "ER, PEG, forward P/E and the reverse DCF are not reconstructible, so the "
            "score is out of ~37 of 45 available points.",
            "Universe is today's index members: delisted and removed constituents are "
            "absent, which flatters every long result.",
            "2016-2025 was mostly a rising market; value-ish measured factors "
            "underperformed over it.",
        ],
        "q1": q1_deciles(p),
        "q2": q2_detection(p),
        "q3": q3_false_positives(p),
        "q4": q4_component_ic(p),
        "q5": q5_bands(p),
        "q6": q6_deterioration(p),
    }
    out_json = config.JOURNAL_DIR / "experiments" / "E02_results.json"
    out_md = config.JOURNAL_DIR / "experiments" / "E02_results.md"
    atomic_write_json(out_json, res)
    md = render(res)
    out_md.write_text(md, encoding="utf-8")
    print(md)
    print(f"written: {out_json}\nwritten: {out_md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
