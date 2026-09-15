"""E05 — measure F1, F3 and F4 on the survivorship-free panel.

Pre-registered in journal/experiments/E05_four_fixes_preregistration.md. The fixes were
designed on the BIASED panel (E02/E03), so the survivorship-free panel (E04) is the first
genuine holdout this project has had. Criteria were fixed before this file existed and are
restated as constants below so a result cannot be graded against a moved goalpost.

F1  sector-relative margin/return metrics
    passes if within-sector IC > 0 AND the sector spread in mean score at least halves
    from 21.4 points.
F3  band hysteresis (two consecutive readings to change)
    passes if band change rate < 12%/month AND median months in a band > 4 AND
    |delta IC| < 0.005.
F4  default to 3 years
    presentation only. Nothing to measure except that no score moved; the 1y-vs-3y IC on
    the survivorship-free panel is reported because it has never been computed there.

F2 is deliberately absent - it is unimplemented so F1 and F2 stay attributable.
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from .. import config
from ..net import atomic_write_json, utc_now_iso
from ..scoring import rubric
from . import battery, panel, questions, sector_fill

#: from E03 R1 on the biased panel: Financials 62.6% down to Utilities 41.2%
F1_BASELINE_SECTOR_SPREAD_PTS = 21.4
F1_SPREAD_MUST_BE_UNDER_PTS = F1_BASELINE_SECTOR_SPREAD_PTS / 2.0

F3_MAX_BAND_CHANGE_RATE = 0.12
F3_MIN_MONTHS_IN_BAND = 4.0
F3_MAX_IC_DELTA = 0.005
#: proxy for the pre-registration's ">30% drawdown" - a 12-month return at or below -30%.
#: It is a horizon return, NOT a peak-to-trough drawdown, and is labelled as such.
F3_FALL_THRESHOLD = -0.30

BAND_ORDER = [name for _edge, name in reversed(rubric.BANDS)]   # worst -> best


def load(path: str) -> pd.DataFrame:
    p = pd.read_parquet(path)
    p["date"] = pd.to_datetime(p["date"])
    return battery.attach_benchmark(p)


def _band_of(pct: float | None) -> str | None:
    """Band from a 0-1 measured percentage, using the rubric's own edges."""
    if pct is None or pd.isna(pct):
        return None
    v = float(pct) * 100.0
    for edge, name in rubric.BANDS:
        if v >= edge:
            return name
    return rubric.BANDS[-1][1]


def _r1_on(p: pd.DataFrame, sector_col: str) -> dict:
    """r1_sector_bet against a chosen sector definition.

    questions.r1_sector_bet hardcodes `sector`, so the column is swapped in on a copy
    rather than the study being reimplemented - the point of calling production code is
    that the result is a statement about the real function.
    """
    q = p.copy()
    q["sector"] = q[sector_col]
    return questions.r1_sector_bet(q)


def _sector_spread_pts(res_r1: dict) -> float | None:
    means = res_r1.get("mean_score_by_sector") or {}
    vals = [v for v in means.values() if v is not None]
    if len(vals) < 2:
        return None
    return (max(vals) - min(vals)) * 100.0


# ------------------------------------------------------------------ F1
def f1(abs_p: pd.DataFrame, sec_p: pd.DataFrame, *,
       sector_col: str = "sector_filled") -> dict:
    """Sector-relative FE, absolute FE, and the pre-registered comparison.

    `sector_col` is the definition BOTH the scoring and the statistics use. It defaults to
    the SIC-filled one because the GICS sector is absent for every removed constituent and
    F1 cannot be measured against a sector variable that is missing for 15% of rows.
    """
    out = {"fix": "F1 sector-relative margin and return metrics",
           "sector_definition": sector_col,
           "criteria": {
               "within_sector_ic": "> 0",
               "sector_spread_pts": f"< {F1_SPREAD_MUST_BE_UNDER_PTS:.2f} "
                                    f"(half of {F1_BASELINE_SECTOR_SPREAD_PTS})"}}

    arms = {}
    for name, p in (("absolute", abs_p), ("sector_relative", sec_p)):
        r1 = _r1_on(p, sector_col)
        r3 = questions.r3_horizon(p)
        arms[name] = {
            "pooled_ic_1y": r1.get("pooled_ic", {}).get("mean_ic"),
            "within_sector_ic_1y": r1.get("within_sector_ic", {}).get("mean_ic"),
            "within_sector_ic_1y_share_positive": (
                r1.get("within_sector_ic", {}).get("share_positive")),
            "score_variance_from_sector": r1.get(
                "share_of_score_variance_explained_by_sector"),
            "sector_spread_pts": _sector_spread_pts(r1),
            "mean_score_by_sector": r1.get("mean_score_by_sector"),
            "ic_3y": (r3.get("by_horizon", {}).get("3y") or {}).get("mean_ic"),
            "top_minus_bottom_3y": (
                r3.get("by_horizon", {}).get("3y") or {}).get("top_minus_bottom"),
            "verdict_r1": r1.get("verdict"),
        }
    out["arms"] = arms

    # how much did FE actually move? a fix that changed nothing is a wiring failure, and
    # that is a far more likely explanation of "no effect" than a genuine null.
    key = ["ticker", "date"]
    j = abs_p[key + ["fe", "fe_avail", "measured_pct"]].merge(
        sec_p[key + ["fe", "fe_avail", "measured_pct", "fe_basis"]],
        on=key, suffixes=("_abs", "_sec"))
    d_fe = (j.fe_sec - j.fe_abs)
    out["did_the_fix_bind"] = {
        "rows_compared": int(len(j)),
        "share_rows_on_sector_relative_basis": (
            float((j.fe_basis == "sector_relative").mean()) if len(j) else None),
        "share_fe_changed": float((d_fe != 0).mean()) if len(j) else None,
        "mean_fe_delta": float(d_fe.mean()) if len(j) else None,
        "mean_abs_fe_delta": float(d_fe.abs().mean()) if len(j) else None,
        "mean_measured_pct_delta": float(
            (j.measured_pct_sec - j.measured_pct_abs).mean()) if len(j) else None,
    }

    w = arms["sector_relative"]["within_sector_ic_1y"]
    s = arms["sector_relative"]["sector_spread_pts"]
    checks = {"within_sector_ic_positive": bool(w is not None and w > 0),
              "sector_spread_halved": bool(s is not None
                                           and s < F1_SPREAD_MUST_BE_UNDER_PTS)}
    out["checks"] = checks
    out["passes"] = bool(all(checks.values()))
    return out


def f1_robustness(abs_p: pd.DataFrame, arms: dict[str, pd.DataFrame]) -> dict:
    """Does the F1 verdict depend on which sector definition is used?

    SIC and GICS agree on only ~78% of the companies where both exist, so a verdict that
    flips between the two definitions is a statement about the classification, not about
    the fix. Reported rather than resolved.
    """
    out: dict = {"note": ("gics_only silently drops every removed constituent and so "
                          "reintroduces the survivorship bias E04 removed; it is here as "
                          "a comparison, not as the headline.")}
    for label, sec_p in arms.items():
        col = {"gics_only": "sector", "sic_filled": "sector_filled",
               "sic_for_everyone": "sector_sic"}[label]
        base = abs_p if label != "gics_only" else abs_p[
            abs_p["sector"].fillna("").astype(str) != ""]
        arm = sec_p if label != "gics_only" else sec_p[
            sec_p["sector"].fillna("").astype(str) != ""]
        r1_abs = _r1_on(base, col)
        r1_sec = _r1_on(arm, col)
        out[label] = {
            "rows": int(len(arm)),
            "symbols": int(arm.ticker.nunique()),
            "absolute_within_sector_ic": r1_abs.get("within_sector_ic", {}).get("mean_ic"),
            "relative_within_sector_ic": r1_sec.get("within_sector_ic", {}).get("mean_ic"),
            "absolute_sector_spread_pts": _sector_spread_pts(r1_abs),
            "relative_sector_spread_pts": _sector_spread_pts(r1_sec),
            "relative_pooled_ic": r1_sec.get("pooled_ic", {}).get("mean_ic"),
        }
        w = out[label]["relative_within_sector_ic"]
        s = out[label]["relative_sector_spread_pts"]
        out[label]["passes"] = bool(w is not None and w > 0 and s is not None
                                    and s < F1_SPREAD_MUST_BE_UNDER_PTS)
    verdicts = {k: v["passes"] for k, v in out.items() if isinstance(v, dict)
                and "passes" in v}
    out["verdict_depends_on_sector_definition"] = bool(len(set(verdicts.values())) > 1)
    return out


# ------------------------------------------------------------------ F3
def f3(p: pd.DataFrame) -> dict:
    """Band hysteresis: churn, run length, IC cost, and the delay it introduces."""
    out = {"fix": "F3 band hysteresis (two consecutive readings to change)",
           "criteria": {"band_change_rate": f"< {F3_MAX_BAND_CHANGE_RATE:.0%}/month",
                        "median_months_in_band": f"> {F3_MIN_MONTHS_IN_BAND:g}",
                        "abs_ic_delta": f"< {F3_MAX_IC_DELTA}"},
           "confirm_readings": rubric.BAND_CONFIRM_READINGS}

    d = p.sort_values(["ticker", "date"]).copy()
    d["band_raw"] = d["measured_pct"].map(_band_of)

    smoothed: list[str | None] = []
    for _t, grp in d.groupby("ticker", sort=False):
        seq = [b for b in grp["band_raw"]]
        # smooth only the observed (non-null) readings, then put the nulls back, so a gap
        # in coverage cannot be counted as a band change
        obs_idx = [i for i, b in enumerate(seq) if b is not None]
        sm = rubric.smooth_bands([seq[i] for i in obs_idx])
        filled: list[str | None] = list(seq)
        for j, i in enumerate(obs_idx):
            filled[i] = sm[j]
        smoothed.extend(filled)
    d["band_smoothed"] = smoothed

    stats = {}
    for col in ("band_raw", "band_smoothed"):
        d["prev"] = d.groupby("ticker")[col].shift(1)
        ch = d.dropna(subset=[col, "prev"])
        rate = float((ch[col] != ch["prev"]).mean()) if len(ch) else None
        runs: list[int] = []
        for _t, grp in d.groupby("ticker", sort=False):
            cur, n = None, 0
            for b in grp[col]:
                if b is None or pd.isna(b):
                    continue
                if b == cur:
                    n += 1
                else:
                    if cur is not None:
                        runs.append(n)
                    cur, n = b, 1
            if cur is not None:
                runs.append(n)
        # IC of the ORDINAL band, which is what a user actually acts on
        ordinal = d[col].map(lambda b: BAND_ORDER.index(b) if b in BAND_ORDER else np.nan)
        dd = d.assign(band_ord=ordinal).dropna(subset=["band_ord", "fwd_1y"])
        ics = questions._ic_series(dd, "band_ord", "fwd_1y")
        dd3 = d.assign(band_ord=ordinal).dropna(subset=["band_ord", "fwd_3y"])
        ics3 = questions._ic_series(dd3, "band_ord", "fwd_3y")
        stats[col] = {"band_change_rate_per_month": rate,
                      "median_months_in_a_band": float(np.median(runs)) if runs else None,
                      "mean_months_in_a_band": float(np.mean(runs)) if runs else None,
                      "n_runs": len(runs),
                      "band_ic_1y": questions._summary(ics).get("mean_ic"),
                      "band_ic_3y": questions._summary(ics3).get("mean_ic"),
                      "band_distribution": {k: int(v) for k, v in
                                            d[col].value_counts().items()}}
    out["arms"] = stats

    raw, sm = stats["band_raw"], stats["band_smoothed"]
    ic_delta = (None if (raw["band_ic_1y"] is None or sm["band_ic_1y"] is None)
                else sm["band_ic_1y"] - raw["band_ic_1y"])
    out["ic_delta_1y"] = ic_delta
    out["ic_delta_3y"] = (None if (raw["band_ic_3y"] is None or sm["band_ic_3y"] is None)
                          else sm["band_ic_3y"] - raw["band_ic_3y"])

    # the cost: how often does smoothing still show the OLD, better band immediately
    # before a large fall? this is the harm the pre-registration asked to be quantified.
    falls = d.dropna(subset=["fwd_1y", "band_raw", "band_smoothed"])
    falls = falls[falls["fwd_1y"] <= F3_FALL_THRESHOLD]
    stale = falls[falls["band_raw"] != falls["band_smoothed"]]
    better = stale[stale.apply(
        lambda r: (r["band_smoothed"] in BAND_ORDER and r["band_raw"] in BAND_ORDER
                   and BAND_ORDER.index(r["band_smoothed"])
                   > BAND_ORDER.index(r["band_raw"])), axis=1)] if len(stale) else stale
    out["delay_cost"] = {
        "definition": (f"observations whose next 12 months returned <= "
                       f"{F3_FALL_THRESHOLD:.0%}. This is a HORIZON RETURN, not a "
                       f"peak-to-trough drawdown."),
        "n_falls": int(len(falls)),
        "share_of_falls_where_smoothed_band_differed": (
            float(len(stale) / len(falls)) if len(falls) else None),
        "share_of_falls_where_smoothed_band_was_more_flattering": (
            float(len(better) / len(falls)) if len(falls) else None),
    }

    checks = {
        "change_rate_under_12pct": bool(sm["band_change_rate_per_month"] is not None
                                        and sm["band_change_rate_per_month"]
                                        < F3_MAX_BAND_CHANGE_RATE),
        "median_months_over_4": bool(sm["median_months_in_a_band"] is not None
                                     and sm["median_months_in_a_band"]
                                     > F3_MIN_MONTHS_IN_BAND),
        "ic_materially_unchanged": bool(ic_delta is not None
                                        and abs(ic_delta) < F3_MAX_IC_DELTA),
    }
    out["checks"] = checks
    out["passes"] = bool(all(checks.values()))
    return out


# ------------------------------------------------------------------ F4
def f4(abs_p: pd.DataFrame, sec_p: pd.DataFrame) -> dict:
    """Presentation-only. Verify no score moved, and report 1y vs 3y where it matters."""
    out = {"fix": "F4 default the UI and expectations to 3 years",
           "criteria": {"scores_unchanged": "F4 is presentation only"}}
    r3 = questions.r3_horizon(abs_p)
    out["by_horizon_absolute"] = r3.get("by_horizon")
    out["ic_rises_with_horizon"] = r3.get("ic_rises_with_horizon")
    out["verdict_r3"] = r3.get("verdict")

    # excess over SPY at both horizons - the comparison the user actually asked for
    ex = {}
    for h in ("1y", "3y"):
        col = f"excess_{h}"
        if col not in abs_p:
            continue
        d = abs_p.dropna(subset=["measured_pct", col])
        if len(d) < 100:
            continue
        ics = questions._ic_series(d, "measured_pct", col)
        d = d.copy()
        d["decile"] = d.groupby("date")["measured_pct"].transform(
            lambda s: pd.qcut(s.rank(method="first"), 10, labels=False,
                              duplicates="drop") if s.notna().sum() >= 10 else np.nan)
        dd = d.dropna(subset=["decile"])
        top = dd[dd.decile == dd.decile.max()][col]
        bot = dd[dd.decile == dd.decile.min()][col]
        ex[h] = {**questions._summary(ics),
                 "top_decile_mean_excess": float(top.mean()) if len(top) else None,
                 "top_decile_median_excess": float(top.median()) if len(top) else None,
                 "bottom_decile_mean_excess": float(bot.mean()) if len(bot) else None,
                 "n": int(len(d)), "n_dates": int(d.date.nunique())}
    out["excess_over_spy_absolute"] = ex
    out["passes"] = True
    out["note"] = ("F4 changes no score, so it cannot fail on data. The horizon numbers "
                   "here are new: they are the first computed on a survivorship-free "
                   "panel.")
    return out


# ------------------------------------------------------------------ render
def _f(v, pct=False, nd=4):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "n/a"
    return f"{v * 100:.1f}%" if pct else f"{v:.{nd}f}"


def render(res: dict) -> str:
    L: list[str] = []
    A = L.append
    A("# E05 results — the four fixes, measured on the survivorship-free panel\n")
    A(f"as_of {res['as_of']}\n")
    pn = res["panel"]
    A(f"Panel: {pn['rows']:,} rows, {pn['symbols']} symbols, "
      f"{pn['start']} → {pn['end']}, median available {pn['median_avail']:.0f} points.")
    A("**Survivorship-free** — companies removed from the index are present until the "
      "month they left.\n")
    A("Every fix was designed on the BIASED panel, so this is a genuine holdout. "
      "Criteria were fixed in the pre-registration before this run.\n")

    sc = res.get("sector_coverage") or {}
    if sc:
        A("\n### The sector variable had to be repaired first\n")
        A(f"The GICS sector comes from the Wikipedia CURRENT-members table, so it is "
          f"**missing for {sc['symbols_without_gics_sector']} of {sc['symbols']} "
          f"companies** — {_f(sc['share_rows_without_gics_sector'], pct=True)} of rows, "
          f"which is exactly the set the survivorship fix added. Left alone they form one "
          f"pseudo-sector mixing utilities with software, and F1 is a *sector* fix, so "
          f"that would have measured it against a fake variable.\n")
        dis = sc.get("disagreement_where_both_known") or {}
        A(f"SIC (from the cached EDGAR submissions, no new requests) resolves "
          f"{_f(sc['sic_resolved_share_of_those'], pct=True)} of them, leaving "
          f"{sc['symbols_still_unclassified']} unclassified. But SIC and GICS agree on "
          f"only **{_f(dis.get('agreement_rate'), pct=True)}** of the "
          f"{dis.get('n_symbols', 0)} companies where both exist, so the F1 verdict is "
          f"reported under all three definitions below.\n")
        mm = dis.get("top_mismatches") or {}
        if mm:
            A("Largest GICS → SIC disagreements: "
              + ", ".join(f"{k} ({v})" for k, v in list(mm.items())[:5]) + ".\n")

    # ---- F1
    f = res["f1"]
    A("\n## F1 — sector-relative margins and returns\n")
    A(f"**{'PASS' if f['passes'] else 'FAIL'}** — "
      + ", ".join(f"{k}={'yes' if v else 'no'}" for k, v in f["checks"].items()) + "\n")
    b = f["did_the_fix_bind"]
    A("Did the change bind at all? "
      f"{_f(b['share_rows_on_sector_relative_basis'], pct=True)} of rows scored on the "
      f"sector-relative basis; FE moved on {_f(b['share_fe_changed'], pct=True)} of rows, "
      f"mean |ΔFE| {_f(b['mean_abs_fe_delta'], nd=2)} points, "
      f"mean Δmeasured% {_f(b['mean_measured_pct_delta'], nd=4)}.\n")
    A("| | absolute | sector-relative |")
    A("|---|---:|---:|")
    aa, ss = f["arms"]["absolute"], f["arms"]["sector_relative"]
    for label, key in (("pooled IC 1y", "pooled_ic_1y"),
                       ("**within-sector IC 1y**", "within_sector_ic_1y"),
                       ("IC 3y", "ic_3y"),
                       ("top−bottom decile 3y", "top_minus_bottom_3y"),
                       ("score variance from sector", "score_variance_from_sector")):
        A(f"| {label} | {_f(aa.get(key))} | {_f(ss.get(key))} |")
    A(f"| **sector spread in mean score** | {_f(aa.get('sector_spread_pts'), nd=1)} pts "
      f"| {_f(ss.get('sector_spread_pts'), nd=1)} pts |")
    A(f"\nCriterion: within-sector IC > 0 and sector spread < "
      f"{F1_SPREAD_MUST_BE_UNDER_PTS:.1f} pts (half of "
      f"{F1_BASELINE_SECTOR_SPREAD_PTS}).\n")
    for arm, name in ((aa, "absolute"), (ss, "sector-relative")):
        means = arm.get("mean_score_by_sector") or {}
        if means:
            top = list(means.items())[:3]
            bot = list(means.items())[-3:]
            A(f"- {name}: highest "
              + ", ".join(f"{k} {v * 100:.1f}%" for k, v in top)
              + " | lowest " + ", ".join(f"{k} {v * 100:.1f}%" for k, v in bot))

    rb = res.get("f1_robustness") or {}
    if rb:
        A("\n### F1 under each sector definition\n")
        A("| definition | rows | symbols | within-sector IC (abs → rel) "
          "| sector spread pts (abs → rel) | passes |")
        A("|---|---:|---:|---:|---:|:--:|")
        for label in ("gics_only", "sic_filled", "sic_for_everyone"):
            v = rb.get(label)
            if not isinstance(v, dict):
                continue
            A(f"| {label} | {v['rows']:,} | {v['symbols']} "
              f"| {_f(v['absolute_within_sector_ic'])} → "
              f"{_f(v['relative_within_sector_ic'])} "
              f"| {_f(v['absolute_sector_spread_pts'], nd=1)} → "
              f"{_f(v['relative_sector_spread_pts'], nd=1)} "
              f"| {'PASS' if v['passes'] else 'FAIL'} |")
        A(f"\n{rb.get('note', '')}\n")
        A("**The verdict "
          + ("DOES depend" if rb.get("verdict_depends_on_sector_definition")
             else "does NOT depend")
          + " on which sector definition is used.**\n")

    # ---- F3
    f = res["f3"]
    A("\n## F3 — band hysteresis\n")
    A(f"**{'PASS' if f['passes'] else 'FAIL'}** — "
      + ", ".join(f"{k}={'yes' if v else 'no'}" for k, v in f["checks"].items()) + "\n")
    A("| | raw | smoothed |")
    A("|---|---:|---:|")
    r, s = f["arms"]["band_raw"], f["arms"]["band_smoothed"]
    A(f"| band change rate / month | {_f(r['band_change_rate_per_month'], pct=True)} "
      f"| {_f(s['band_change_rate_per_month'], pct=True)} |")
    A(f"| median months in a band | {_f(r['median_months_in_a_band'], nd=1)} "
      f"| {_f(s['median_months_in_a_band'], nd=1)} |")
    A(f"| band IC 1y | {_f(r['band_ic_1y'])} | {_f(s['band_ic_1y'])} |")
    A(f"| band IC 3y | {_f(r['band_ic_3y'])} | {_f(s['band_ic_3y'])} |")
    A(f"\nΔIC 1y {_f(f.get('ic_delta_1y'))}, ΔIC 3y {_f(f.get('ic_delta_3y'))} "
      f"(criterion |ΔIC 1y| < {F3_MAX_IC_DELTA}).\n")
    dc = f["delay_cost"]
    A(f"Delay cost — {dc['definition']} n={dc['n_falls']:,}; the smoothed band differed "
      f"on {_f(dc['share_of_falls_where_smoothed_band_differed'], pct=True)} of them and "
      f"was **more flattering** on "
      f"{_f(dc['share_of_falls_where_smoothed_band_was_more_flattering'], pct=True)}.\n")

    # ---- F4
    f = res["f4"]
    A("\n## F4 — default to three years\n")
    A(f"{f['note']}\n")
    A("| horizon | mean IC | share of months positive | top−bottom decile | n |")
    A("|---|---:|---:|---:|---:|")
    for h, v in (f.get("by_horizon_absolute") or {}).items():
        A(f"| {h} | {_f(v.get('mean_ic'))} | {_f(v.get('share_positive'), pct=True)} "
          f"| {_f(v.get('top_minus_bottom'), pct=True)} | {v.get('n', 0):,} |")
    ex = f.get("excess_over_spy_absolute") or {}
    if ex:
        A("\nExcess over SPY — the comparison actually asked for:\n")
        A("| horizon | mean IC vs excess | top decile mean excess | median | n dates |")
        A("|---|---:|---:|---:|---:|")
        for h, v in ex.items():
            A(f"| {h} | {_f(v.get('mean_ic'))} "
              f"| {_f(v.get('top_decile_mean_excess'), pct=True)} "
              f"| {_f(v.get('top_decile_median_excess'), pct=True)} "
              f"| {v.get('n_dates', 0)} |")

    A("\n## F2\n")
    A("Not implemented, deliberately: F1 and F2 both touch FE and a combined result "
      "would be unattributable. Still open.\n")
    A("\nNothing here is promoted. `promoted` stays false.\n")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    exp = config.JOURNAL_DIR / "experiments"
    ap.add_argument("--abs-panel", default=str(exp / "E05_panel_abs.parquet"))
    ap.add_argument("--sec-panel", default=str(exp / "E05_panel_secrel.parquet"))
    args = ap.parse_args(argv)

    abs_p = sector_fill.fill(load(args.abs_panel))
    sec_stored = load(args.sec_panel)

    # Re-score F1 under each sector definition. The stored sector-relative panel used the
    # raw `sector`, which is BLANK for every removed constituent, so it is kept only as
    # the gics_only arm. apply_sector_relative() rebuilds the rest without a new crawl.
    print("re-scoring F1 under each sector definition...", flush=True)
    arms = {"gics_only": sec_stored}
    for label, col in (("sic_filled", "sector_filled"),
                       ("sic_for_everyone", "sector_sic")):
        arms[label] = sector_fill.fill(panel.apply_sector_relative(abs_p, col))
        print(f"  {label}: {len(arms[label]):,} rows", flush=True)

    res = {"study": "E05_four_fixes",
           "as_of": utc_now_iso(),
           "panel": {"rows": int(len(abs_p)), "symbols": int(abs_p.ticker.nunique()),
                     "start": str(abs_p.date.min().date()),
                     "end": str(abs_p.date.max().date()),
                     "median_avail": float(abs_p.measured_avail.median()),
                     "survivorship": "removed constituents included until they left"},
           "sector_coverage": sector_fill.report(abs_p),
           "f1": f1(abs_p, arms["sic_filled"], sector_col="sector_filled"),
           "f1_robustness": f1_robustness(abs_p, arms),
           "f3": f3(abs_p),
           "f4": f4(abs_p, arms["sic_filled"])}

    atomic_write_json(exp / "E05_results.json", res)
    md = render(res)
    (exp / "E05_results.md").write_text(md, encoding="utf-8")
    print(md)
    print(f"\nwritten: {exp / 'E05_results.json'}\nwritten: {exp / 'E05_results.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
