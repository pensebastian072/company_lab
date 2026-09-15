"""E03 — the questions nobody asked, run against the point-in-time panel.

Pre-registration: journal/experiments/E03_questions_not_asked_preregistration.md

R1 sector bet or company picking?
R2 does the CHANGE in score beat the LEVEL?
R3 does it need a longer horizon?
R4 is the score stable enough to act on?
R5 does the cyclical fix work?
R6 what does the framework never own?

Usage:
  python -m clab.research.questions --panel journal/experiments/E02_panel.parquet
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

from .. import config
from ..net import atomic_write_json, utc_now_iso

MIN_N = 30

# SIC groups that are structurally cyclical - the R5 population
CYCLICAL_SIC = [(3600, 3699), (3570, 3579), (1300, 1399), (2911, 2911),
                (3300, 3399), (3711, 3711)]
CYCLICAL_HINT = ("Semiconductors", "Technology Hardware", "Oil, Gas",
                 "Metals & Mining", "Automobile", "Electronic")


def _spearman(a: pd.Series, b: pd.Series) -> float | None:
    d = pd.DataFrame({"a": a, "b": b}).dropna()
    if len(d) < 10:
        return None
    return float(d["a"].rank().corr(d["b"].rank()))


def _ic_series(d: pd.DataFrame, score: str, ret: str) -> pd.Series:
    return d.groupby("date").apply(
        lambda g: _spearman(g[score], g[ret]), include_groups=False).dropna()


def _summary(ics: pd.Series) -> dict:
    return {"n_months": int(len(ics)),
            "mean_ic": float(ics.mean()) if len(ics) else None,
            "median_ic": float(ics.median()) if len(ics) else None,
            "share_positive": float((ics > 0).mean()) if len(ics) else None}


# ------------------------------------------------------------------ R1
def r1_sector_bet(p: pd.DataFrame) -> dict:
    """Does the score survive when sector is removed?"""
    out = {"question": "Is the framework a quality bet or a sector bet?"}
    d = p.dropna(subset=["measured_pct", "fwd_1y"]).copy()
    if d.empty or "sector" not in d:
        return {**out, "verdict": "no data"}

    pooled = _ic_series(d, "measured_pct", "fwd_1y")
    out["pooled_ic"] = _summary(pooled)

    # demean both score and return within (date, sector)
    g = d.groupby(["date", "sector"])
    d["score_dm"] = d["measured_pct"] - g["measured_pct"].transform("mean")
    d["ret_dm"] = d["fwd_1y"] - g["fwd_1y"].transform("mean")
    within = _ic_series(d, "score_dm", "ret_dm")
    out["within_sector_ic"] = _summary(within)

    # how much of the score is explained by sector alone?
    ss_total = float(((d["measured_pct"] - d["measured_pct"].mean()) ** 2).sum())
    ss_within = float((d["score_dm"] ** 2).sum())
    out["share_of_score_variance_explained_by_sector"] = (
        1.0 - ss_within / ss_total if ss_total else None)

    pooled_m = out["pooled_ic"]["mean_ic"]
    within_m = out["within_sector_ic"]["mean_ic"]
    out["ic_retained_within_sector"] = (
        (within_m / pooled_m) if (pooled_m and within_m is not None and pooled_m != 0)
        else None)
    out["verdict"] = (
        "score survives sector removal - it is picking companies"
        if (within_m is not None and pooled_m is not None and within_m > 0
            and within_m >= 0.5 * pooled_m)
        else "score largely disappears within sector - it is substantially a sector bet"
        if (within_m is not None and pooled_m is not None and pooled_m > 0)
        else "inconclusive: pooled IC is not positive to begin with")
    # per-sector mean score, so a tilt is visible
    out["mean_score_by_sector"] = {
        k: round(float(v), 4) for k, v in
        d.groupby("sector")["measured_pct"].mean().sort_values(ascending=False).items()}
    return out


# ------------------------------------------------------------------ R2
def r2_change_vs_level(p: pd.DataFrame) -> dict:
    """Improving-from-mediocre versus statically-good."""
    out = {"question": "Does the CHANGE in score beat the LEVEL?"}
    d = p.sort_values(["ticker", "date"]).copy()
    d["score_12m_ago"] = d.groupby("ticker")["measured_pct"].shift(12)
    d["score_change_12m"] = d["measured_pct"] - d["score_12m_ago"]
    dd = d.dropna(subset=["measured_pct", "score_change_12m", "fwd_1y"])
    if len(dd) < 100:
        return {**out, "verdict": "insufficient overlapping history"}

    out["level_ic"] = _summary(_ic_series(dd, "measured_pct", "fwd_1y"))
    out["change_ic"] = _summary(_ic_series(dd, "score_change_12m", "fwd_1y"))

    # 2x2: level above/below median, change positive/negative
    med_level = dd["measured_pct"].median()
    cells = {}
    for lvl in ("high_level", "low_level"):
        for chg in ("improving", "deteriorating"):
            m = ((dd["measured_pct"] >= med_level) if lvl == "high_level"
                 else (dd["measured_pct"] < med_level))
            m &= ((dd["score_change_12m"] > 0) if chg == "improving"
                  else (dd["score_change_12m"] <= 0))
            grp = dd[m]["fwd_1y"]
            cells[f"{lvl}__{chg}"] = {
                "n": int(len(grp)),
                "mean": float(grp.mean()) if len(grp) else None,
                "median": float(grp.median()) if len(grp) else None}
    out["two_by_two_1y"] = cells
    lm = out["level_ic"]["mean_ic"]
    cm = out["change_ic"]["mean_ic"]
    out["change_beats_level"] = bool(cm is not None and lm is not None and cm > lm)
    out["verdict"] = ("the trajectory carries more signal than the level - the "
                      "framework is missing a fundamentals-momentum dimension"
                      if out["change_beats_level"] else
                      "the level carries at least as much as the trajectory")
    return out


# ------------------------------------------------------------------ R3
def r3_horizon(p: pd.DataFrame) -> dict:
    out = {"question": "Does the framework need a longer horizon?"}
    res = {}
    for h in ("1y", "3y"):
        col = f"fwd_{h}"
        if col not in p:
            continue
        d = p.dropna(subset=["measured_pct", col])
        if len(d) < 100:
            continue
        ics = _ic_series(d, "measured_pct", col)
        d = d.copy()
        d["decile"] = d.groupby("date")["measured_pct"].transform(
            lambda s: pd.qcut(s.rank(method="first"), 10, labels=False,
                              duplicates="drop") if s.notna().sum() >= 10 else np.nan)
        dd = d.dropna(subset=["decile"])
        top = dd[dd.decile == dd.decile.max()][col]
        bot = dd[dd.decile == dd.decile.min()][col]
        res[h] = {**_summary(ics),
                  "top_decile_mean": float(top.mean()) if len(top) else None,
                  "bottom_decile_mean": float(bot.mean()) if len(bot) else None,
                  "top_minus_bottom": (float(top.mean() - bot.mean())
                                       if len(top) and len(bot) else None),
                  "n": int(len(d))}
    out["by_horizon"] = res
    ics = [(h, v["mean_ic"]) for h, v in res.items() if v["mean_ic"] is not None]
    out["ic_rises_with_horizon"] = (
        bool(len(ics) > 1 and all(ics[i][1] <= ics[i + 1][1] for i in range(len(ics) - 1))))
    out["verdict"] = ("IC improves with horizon - earlier tests were too short"
                      if out["ic_rises_with_horizon"] else
                      "horizon does not explain the weak ranking power")
    return out


# ------------------------------------------------------------------ R4
def r4_stability(p: pd.DataFrame) -> dict:
    out = {"question": "Is the score stable enough to act on?"}
    d = p.sort_values(["ticker", "date"]).copy()
    d["prev"] = d.groupby("ticker")["measured_pct"].shift(1)
    d["abs_change"] = (d["measured_pct"] - d["prev"]).abs()
    ch = d["abs_change"].dropna()
    if ch.empty:
        return {**out, "verdict": "no data"}
    out["month_to_month_abs_change"] = {
        "median": float(ch.median()), "mean": float(ch.mean()),
        "p90": float(ch.quantile(0.90)),
        "share_over_5pts": float((ch > 0.05).mean()),
        "share_over_10pts": float((ch > 0.10).mean())}

    edges = [(0.90, "EXCEPTIONAL"), (0.80, "HIGH_CONVICTION"), (0.70, "INVESTABLE"),
             (0.60, "WATCHLIST"), (0.50, "WEAK"), (0.0, "REJECT")]

    def band(v):
        if pd.isna(v):
            return None
        for e, name in edges:
            if v >= e:
                return name
        return "REJECT"

    d["band"] = d["measured_pct"].map(band)
    d["prev_band"] = d.groupby("ticker")["band"].shift(1)
    changed = d.dropna(subset=["band", "prev_band"])
    out["band_change_rate_per_month"] = (
        float((changed["band"] != changed["prev_band"]).mean()) if len(changed) else None)

    # median run length in a band
    runs = []
    for _t, grp in d.groupby("ticker"):
        cur, n = None, 0
        for b in grp["band"]:
            if b == cur:
                n += 1
            else:
                if cur is not None:
                    runs.append(n)
                cur, n = b, 1
        if cur is not None:
            runs.append(n)
    out["median_months_in_a_band"] = float(np.median(runs)) if runs else None
    out["note"] = ("A band that changes every month or two cannot be traded on "
                   "regardless of its IC. This is a usability number, not a "
                   "pass/fail.")
    return out


# ------------------------------------------------------------------ R5
def r5_cyclical(p: pd.DataFrame) -> dict:
    """Is the score anti-correlated with the right entry inside cyclicals?"""
    out = {"question": "Does the score peak at the earnings top for cyclicals?"}
    if "sub_industry" not in p:
        return {**out, "verdict": "no sub_industry data"}
    mask = p["sub_industry"].fillna("").str.contains("|".join(CYCLICAL_HINT),
                                                    case=False, regex=True)
    cyc = p[mask]
    non = p[~mask]
    out["n_cyclical_rows"] = int(len(cyc))
    out["n_other_rows"] = int(len(non))
    out["cyclical_sub_industries"] = sorted(cyc["sub_industry"].dropna().unique().tolist())[:20]
    if len(cyc) < 100:
        return {**out, "verdict": "too few cyclical rows"}

    for label, part in (("cyclical", cyc), ("other", non)):
        d = part.dropna(subset=["measured_pct", "fwd_1y"])
        out[f"{label}_ic_1y"] = _summary(_ic_series(d, "measured_pct", "fwd_1y"))
        d3 = part.dropna(subset=["measured_pct", "fwd_3y"])
        out[f"{label}_ic_3y"] = _summary(_ic_series(d3, "measured_pct", "fwd_3y"))

    # the direct test: within cyclicals, do HIGH scores precede BAD 3y outcomes?
    d = cyc.dropna(subset=["measured_pct", "fwd_3y"]).copy()
    d["decile"] = d.groupby("date")["measured_pct"].transform(
        lambda s: pd.qcut(s.rank(method="first"), 5, labels=False,
                          duplicates="drop") if s.notna().sum() >= 5 else np.nan)
    dd = d.dropna(subset=["decile"])
    q = {}
    for quint, grp in dd.groupby("decile"):
        q[int(quint)] = {"n": int(len(grp)), "mean_3y": float(grp["fwd_3y"].mean()),
                         "median_3y": float(grp["fwd_3y"].median())}
    out["cyclical_quintiles_3y"] = q
    if len(q) >= 2:
        lo, hi = min(q), max(q)
        out["cyclical_top_minus_bottom_3y"] = q[hi]["mean_3y"] - q[lo]["mean_3y"]
        out["verdict"] = (
            "confirmed: inside cyclicals a HIGH score preceded WORSE 3y outcomes"
            if out["cyclical_top_minus_bottom_3y"] < 0 else
            "not confirmed on quintiles: high-scoring cyclicals did better")
    return out


# ------------------------------------------------------------------ R6
def r6_never_owns(p: pd.DataFrame) -> dict:
    out = {"question": "What does the framework structurally never own?"}
    d = p.dropna(subset=["measured_pct"]).copy()
    d["decile"] = d.groupby("date")["measured_pct"].transform(
        lambda s: pd.qcut(s.rank(method="first"), 10, labels=False,
                          duplicates="drop") if s.notna().sum() >= 10 else np.nan)
    dd = d.dropna(subset=["decile"])
    bot = dd[dd.decile == dd.decile.min()]
    top = dd[dd.decile == dd.decile.max()]

    def describe(part: pd.DataFrame) -> dict:
        return {
            "n": int(len(part)),
            "median_market_cap": (float(part["market_cap"].median())
                                  if "market_cap" in part else None),
            "median_pe": (float(part["pe_current"].median())
                          if "pe_current" in part and part["pe_current"].notna().any()
                          else None),
            "share_negative_fcf": (float((part["fcf_ttm"] <= 0).mean())
                                   if "fcf_ttm" in part else None),
            "median_revenue_cagr_3y": (float(part["revenue_cagr_3y"].median())
                                       if "revenue_cagr_3y" in part else None),
            "median_operating_margin": (float(part["operating_margin"].median())
                                        if "operating_margin" in part else None),
            "top_sectors": (part.groupby("sector").size().sort_values(ascending=False)
                            .head(5).to_dict() if "sector" in part else {}),
        }

    out["bottom_decile"] = describe(bot)
    out["top_decile"] = describe(top)

    # companies never once in the top 3 deciles across the whole panel
    dd = dd.copy()
    dd["in_top3"] = dd["decile"] >= dd["decile"].max() - 2
    per_sym = dd.groupby("ticker")["in_top3"].max()
    never = sorted(per_sym[~per_sym].index.tolist())
    out["n_never_in_top3_deciles"] = len(never)
    out["never_in_top3_examples"] = never[:30]
    if never:
        nsub = p[p.ticker.isin(never)]
        out["never_in_top3_profile"] = {
            "top_sectors": (nsub.groupby("sector").size().sort_values(ascending=False)
                            .head(6).to_dict() if "sector" in nsub else {}),
            "median_fwd_1y": (float(nsub["fwd_1y"].median())
                              if nsub["fwd_1y"].notna().any() else None),
            "median_operating_margin": (float(nsub["operating_margin"].median())
                                        if nsub["operating_margin"].notna().any() else None),
        }
    out["note"] = ("This is the shape of the hole. Every ranking excludes something; "
                   "the question is whether this exclusion is intentional.")
    return out


# ------------------------------------------------------------------ render
def render(res: dict) -> str:
    L, a = [], lambda s: L.append(s)
    a("# E03 — the questions nobody asked\n")
    a(f"Run {res['as_of']}. Pre-registered: "
      f"`journal/experiments/E03_questions_not_asked_preregistration.md`\n")
    m = res["panel"]
    a(f"Panel: {m['rows']} month-ends, {m['symbols']} companies, {m['start']} to "
      f"{m['end']}. Measured half only; survivorship applies throughout.\n")

    r = res["r1"]
    a("\n## R1 — quality bet, or sector bet?\n")
    a(f"- pooled IC **{_n(r.get('pooled_ic', {}).get('mean_ic'))}**")
    a(f"- within-sector IC **{_n(r.get('within_sector_ic', {}).get('mean_ic'))}**")
    a(f"- IC retained after removing sector: **{_pct(r.get('ic_retained_within_sector'))}**")
    a(f"- share of score variance explained by sector alone: "
      f"**{_pct(r.get('share_of_score_variance_explained_by_sector'))}**")
    a(f"\n**{r.get('verdict')}**\n")
    ms = r.get("mean_score_by_sector") or {}
    if ms:
        a("\nMean score by sector (a tilt would show here):\n")
        a("| sector | mean score |")
        a("|---|---:|")
        for k, v in list(ms.items())[:12]:
            a(f"| {k} | {_pct(v)} |")

    r = res["r2"]
    a("\n## R2 — does the trajectory beat the level?\n")
    a(f"- IC of the score LEVEL: **{_n(r.get('level_ic', {}).get('mean_ic'))}**")
    a(f"- IC of the 12-month CHANGE: **{_n(r.get('change_ic', {}).get('mean_ic'))}**")
    a(f"\n**{r.get('verdict')}**\n")
    cells = r.get("two_by_two_1y") or {}
    if cells:
        a("\n| cell | n | mean 1y | median 1y |")
        a("|---|---:|---:|---:|")
        for k, v in cells.items():
            a(f"| {k.replace('__', ' + ')} | {v['n']} | {_pct(v['mean'])} "
              f"| {_pct(v['median'])} |")

    r = res["r3"]
    a("\n## R3 — is the horizon the problem?\n")
    a("| horizon | n | mean IC | share positive | top decile | bottom decile | spread |")
    a("|---|---:|---:|---:|---:|---:|---:|")
    for h, v in (r.get("by_horizon") or {}).items():
        a(f"| {h} | {v['n']} | {_n(v['mean_ic'])} | {_s(v['share_positive'])} "
          f"| {_pct(v['top_decile_mean'])} | {_pct(v['bottom_decile_mean'])} "
          f"| {_pct(v['top_minus_bottom'])} |")
    a(f"\n**{r.get('verdict')}**\n")

    r = res["r4"]
    a("\n## R4 — is it stable enough to act on?\n")
    c = r.get("month_to_month_abs_change") or {}
    a(f"- median month-to-month move in the score: **{_pct(c.get('median'))}** "
      f"(p90 {_pct(c.get('p90'))})")
    a(f"- months where the score moved more than 10 points: {_s(c.get('share_over_10pts'))}")
    a(f"- band changes per month: **{_s(r.get('band_change_rate_per_month'))}**")
    a(f"- median months spent in a band before leaving: "
      f"**{r.get('median_months_in_a_band')}**")
    a(f"\n{r.get('note', '')}\n")

    r = res["r5"]
    a("\n## R5 — the cyclical defect\n")
    a(f"{r.get('n_cyclical_rows')} cyclical rows vs {r.get('n_other_rows')} others.\n")
    a("| population | mean IC 1y | mean IC 3y |")
    a("|---|---:|---:|")
    for lab in ("cyclical", "other"):
        a(f"| {lab} | {_n((r.get(f'{lab}_ic_1y') or {}).get('mean_ic'))} "
          f"| {_n((r.get(f'{lab}_ic_3y') or {}).get('mean_ic'))} |")
    q = r.get("cyclical_quintiles_3y") or {}
    if q:
        a("\nCyclicals by score quintile, 3-year forward:\n")
        a("| quintile | n | mean 3y | median 3y |")
        a("|---|---:|---:|---:|")
        for k, v in sorted(q.items()):
            a(f"| {k} | {v['n']} | {_pct(v['mean_3y'])} | {_pct(v['median_3y'])} |")
        a(f"\ntop minus bottom quintile: "
          f"**{_pct(r.get('cyclical_top_minus_bottom_3y'))}**")
    a(f"\n**{r.get('verdict')}**\n")

    r = res["r6"]
    a("\n## R6 — what it never owns\n")
    for lab in ("bottom_decile", "top_decile"):
        v = r.get(lab) or {}
        a(f"\n**{lab.replace('_', ' ')}** (n={v.get('n')}): "
          f"median P/E {_num(v.get('median_pe'))}, "
          f"median 3y revenue CAGR {_pct(v.get('median_revenue_cagr_3y'))}, "
          f"median operating margin {_pct(v.get('median_operating_margin'))}, "
          f"negative FCF in {_s(v.get('share_negative_fcf'))} of rows")
        a(f"  sectors: {', '.join(f'{k} {n}' for k, n in (v.get('top_sectors') or {}).items())}")
    a(f"\n**{r.get('n_never_in_top3_deciles')} companies were never once in the top 3 "
      f"deciles** in ten years.")
    ex = r.get("never_in_top3_examples") or []
    if ex:
        a(f"\nExamples: {', '.join(ex[:24])}")
    prof = r.get("never_in_top3_profile") or {}
    if prof:
        a(f"\nThose names: median 1y return {_pct(prof.get('median_fwd_1y'))}, "
          f"median operating margin {_pct(prof.get('median_operating_margin'))}")
        a(f"sectors: {', '.join(f'{k} {n}' for k, n in (prof.get('top_sectors') or {}).items())}")
    a(f"\n{r.get('note', '')}\n")

    a("\n## Limits that apply to every line above\n")
    for c in res["caveats"]:
        a(f"- {c}")
    return "\n".join(L) + "\n"


def _pct(v) -> str:
    if v is None:
        return "-"
    try:
        return f"{float(v) * 100:+.1f}%"
    except (TypeError, ValueError):
        return str(v)


def _s(v) -> str:
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


def _num(v) -> str:
    if v is None:
        return "-"
    try:
        return f"{float(v):,.1f}"
    except (TypeError, ValueError):
        return str(v)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--panel",
                    default=str(config.JOURNAL_DIR / "experiments" / "E02_panel.parquet"))
    ap.add_argument("--tag", default="E03")
    args = ap.parse_args(argv)

    p = pd.read_parquet(args.panel)
    p["date"] = pd.to_datetime(p["date"])
    res = {
        "study": "E03_questions_not_asked",
        "as_of": utc_now_iso(),
        "panel_file": args.panel,
        "panel": {"rows": int(len(p)), "symbols": int(p.ticker.nunique()),
                  "start": str(p.date.min().date()), "end": str(p.date.max().date())},
        "caveats": [
            "Measured half only - the LLM half cannot be backtested without hindsight.",
            "Universe is today's index members, so survivorship inflates every long "
            "result and makes the bottom decile 'low scores that survived'.",
            "2016-2025 contains no prolonged bear market.",
            "ER, PEG, forward P/E and the reverse DCF are not reconstructible.",
        ],
        "r1": r1_sector_bet(p),
        "r2": r2_change_vs_level(p),
        "r3": r3_horizon(p),
        "r4": r4_stability(p),
        "r5": r5_cyclical(p),
        "r6": r6_never_owns(p),
    }
    out_json = config.JOURNAL_DIR / "experiments" / f"{args.tag}_results.json"
    out_md = config.JOURNAL_DIR / "experiments" / f"{args.tag}_results.md"
    atomic_write_json(out_json, res)
    md = render(res)
    out_md.write_text(md, encoding="utf-8")
    print(md)
    print(f"written: {out_json}\nwritten: {out_md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
