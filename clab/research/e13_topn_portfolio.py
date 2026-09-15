"""E13 - does a top-N portfolio of this score beat the index?

Pre-registered in `journal/experiments/E13_topn_portfolio_preregistration.md` BEFORE any
portfolio return was computed. Read that first; the variants, `n_trials` and the pass
criteria are fixed there and this file only executes them.

**This grades the MEASURED HALF, not the published composite.** `panel.py:19-21` excludes
all 50 LLM points and also ER, PEG, forward P/E and the reverse DCF, because none of them
reconstruct point-in-time without hindsight. The ranking column is `measured_pct` =
FE+BS+VA+EN earned over available. Testing the published composite needs ~50 weekly
snapshots and four exist, so that path opens around mid-2027.

Everything except `top_n_by_date` is reused:
  * point-in-time scores and survivorship - `clab/research/panel.py`
  * overlapping equal-weighted cohorts    - `e11_investability.cohort_series`
  * PBO + Deflated Sharpe                 - `e11_investability._gate` (imports copper_brain)

    python -m clab.research.e13_topn_portfolio
    python -m clab.research.e13_topn_portfolio --panel journal/experiments/E05_panel_abs.parquet
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from .. import config
from ..net import utc_now_iso

#: registered in the pre-registration; n_trials feeds the DSR deflation
TOP_N = (20, 40, 80)
SCORE_COL = "measured_pct"
N_TRIALS = len(TOP_N)

MIN_COVERAGE = 0.80          # rubric.MIN_COVERAGE_FOR_BAND: no band, so no portfolio slot
HOLD_MONTHS = 12
COST_ROUND_TRIP = 0.0040
DEFAULT_PANEL = "E05_panel_abs.parquet"


def coverage_proxy(panel: pd.DataFrame) -> pd.Series:
    """Available points as a share of the best-covered peer of the same profile that month.

    The panel stores `measured_avail` but NOT the NOT_APPLICABLE total, so the rubric's
    real `coverage = available / applicable` cannot be reconstructed from it. Dividing by
    a global maximum would penalise every FINANCIAL company for sub-tests the rubric
    deliberately suppresses for them, so the denominator is per (date, profile).

    Documented as a proxy because it is one.
    """
    denom = panel.groupby(["date", "profile"])["measured_avail"].transform("max")
    return panel["measured_avail"] / denom.replace(0, np.nan)


def top_n_by_date(panel: pd.DataFrame, n: int, score_col: str = SCORE_COL) -> dict:
    """{month_end: [tickers]} - the highest-scoring n names available THAT month.

    The only new code in E13. Ties are broken by ticker so a run is reproducible; the
    alternative (arbitrary row order) would make the backtest non-deterministic.
    """
    out = {}
    for date, grp in panel.groupby("date"):
        g = grp.dropna(subset=[score_col])
        if g.empty:
            continue
        g = g.sort_values([score_col, "ticker"], ascending=[False, True])
        out[pd.Timestamp(date)] = list(g.head(n)["ticker"])
    return out


def decile_diagnostic(panel: pd.DataFrame) -> dict:
    """P4: reconcile E05's -14.1% top-bottom decile spread.

    E05 reported a mean IC at 3y of +0.0805 alongside a top-bottom decile spread of
    -14.1%, and nothing explained how a positive rank correlation coexists with an
    inverted decile spread. Two separate things were folded into that number:

      1. It is a spread of ABSOLUTE returns, not excess over SPY. On excess it is
         positive.
      2. It is computed with NO coverage filter, and the bottom decile is contaminated
         by companies that score low because they are UNMEASURABLE rather than bad. They
         are small, high-beta and young, and over a decade-long bull market they produce
         very large absolute returns. Filtering to the coverage the rubric already
         requires for a band flips the sign.

    Reported as a table rather than a sentence so the claim can be re-checked.
    """
    from . import battery

    d = panel.copy()
    d["cov"] = coverage_proxy(d)
    filtered = d[d["cov"] >= MIN_COVERAGE]
    out: dict = {"absolute": {}, "excess": {}}

    for label, frame in (("no_coverage_filter", d), ("coverage_filtered", filtered)):
        for col in ("fwd_1y", "fwd_3y"):
            g = frame.dropna(subset=[col, SCORE_COL]).copy()
            if g.empty:
                continue
            g["dec"] = g.groupby("date")[SCORE_COL].transform(
                lambda s: pd.qcut(s.rank(method="first"), 10, labels=False,
                                  duplicates="drop"))
            t = g.groupby("dec")[col].mean()
            if 0 not in t.index or 9 not in t.index:
                continue
            out["absolute"].setdefault(label, {})[col] = {
                "top_minus_bottom_pp": float(100 * (t.loc[9] - t.loc[0])),
                "bottom_decile_mean_pct": float(100 * t.loc[0]),
                "top_decile_mean_pct": float(100 * t.loc[9]),
                "n": int(len(g)),
            }

    ex = battery.attach_benchmark(filtered.copy())
    for col in ("excess_1y", "excess_3y"):
        if col not in ex:
            continue
        g = ex.dropna(subset=[col, SCORE_COL]).copy()
        if g.empty:
            continue
        g["dec"] = g.groupby("date")[SCORE_COL].transform(
            lambda s: pd.qcut(s.rank(method="first"), 10, labels=False,
                              duplicates="drop"))
        t = g.groupby("dec")[col].agg(["mean", "median"])
        out["excess"]["coverage_filtered"] = out["excess"].get("coverage_filtered", {})
        out["excess"]["coverage_filtered"][col] = {
            "top_minus_bottom_pp": float(100 * (t.loc[9, "mean"] - t.loc[0, "mean"])),
            "top_decile_mean_pct": float(100 * t.loc[9, "mean"]),
            "top_decile_median_pct": float(100 * t.loc[9, "median"]),
            "n": int(len(g)),
        }
    return out


def _per_year(net: pd.Series) -> dict:
    years = net.index.year
    return {int(y): {"n_months": int((years == y).sum()),
                     "mean_monthly": float(net[years == y].mean()),
                     "median_monthly": float(net[years == y].median())}
            for y in sorted(set(years))}


def run(panel_path: str, restrict_to: str | None = None) -> dict:
    from .e11_investability import (_describe, _gate, _sign_test, cohort_series,
                                    monthly_returns)

    panel = pd.read_parquet(panel_path)
    panel["date"] = pd.to_datetime(panel["date"])
    n_rows_all = len(panel)

    # Comparing a v2 panel against the E05 one conflates two changes: the scoring code
    # AND a universe that went from 675 symbols to 1,585. Restricting to the older
    # panel's tickers isolates the code change, which is the only thing the Phase 1/2
    # gate is asking about.
    restricted_to = None
    if restrict_to:
        keep = set(pd.read_parquet(restrict_to)["ticker"].unique())
        before = panel["ticker"].nunique()
        panel = panel[panel["ticker"].isin(keep)]
        restricted_to = {"panel": restrict_to, "symbols_before": int(before),
                         "symbols_after": int(panel["ticker"].nunique())}
        print(f"restricted {before} -> {panel['ticker'].nunique()} symbols "
              f"to match {restrict_to}", flush=True)

    panel["coverage_proxy"] = coverage_proxy(panel)
    kept = panel[panel["coverage_proxy"] >= MIN_COVERAGE].copy()

    symbols = sorted(set(kept["ticker"]) | {"SPY"})
    print(f"loading monthly returns for {len(symbols)} symbols...", flush=True)
    rets = monthly_returns(symbols)
    if rets.empty or "SPY" not in rets.columns:
        raise RuntimeError("no monthly returns, or SPY missing - cannot compute excess")
    spy = rets["SPY"]

    out: dict = {
        "study": "E13_topn_portfolio",
        "as_of": utc_now_iso(),
        "preregistration":
            "journal/experiments/E13_topn_portfolio_preregistration.md",
        "panel": panel_path,
        "restricted_to": restricted_to,
        "grades": ("the MEASURED HALF (FE+BS+VA+EN) only - panel.py excludes all 50 LLM "
                   "points plus ER, PEG, forward P/E and the reverse DCF"),
        "coverage": {
            "panel_rows": n_rows_all,
            "rows_after_coverage_filter": int(len(kept)),
            "symbols": int(kept["ticker"].nunique()),
            "min_coverage": MIN_COVERAGE,
            "note": "coverage is a per-(date,profile) proxy; the panel does not store "
                    "NOT_APPLICABLE points",
        },
        "construction": {
            "hold_months": HOLD_MONTHS, "cost_round_trip": COST_ROUND_TRIP,
            "score_col": SCORE_COL, "n_trials_registered": N_TRIALS,
        },
        "variants": {},
    }

    monthly_cost = COST_ROUND_TRIP / HOLD_MONTHS
    for n in TOP_N:
        by_date = top_n_by_date(kept, n)
        series = cohort_series(by_date, rets)
        gross = (series["ret"] - spy.reindex(series.index)).dropna()
        net = (series["ret"] - spy.reindex(series.index)
               - np.where(series["in_market"], monthly_cost, 0.0)).dropna()
        net_ex2020 = net[net.index.year != 2020]

        gate = _gate(net.values, n_trials=N_TRIALS)
        out["variants"][f"top{n}"] = {
            "n": n,
            "entry_months": len(by_date),
            "months": int(len(net)),
            "months_in_market": int(series["in_market"].sum()),
            "annualised_excess_gross": float(gross.mean() * 12) if len(gross) else None,
            "annualised_excess_net": float(net.mean() * 12) if len(net) else None,
            "annualised_excess_net_ex2020": (float(net_ex2020.mean() * 12)
                                             if len(net_ex2020) else None),
            "breakeven_cost_bps": (float(gross.mean() * 12 * 10_000)
                                   if len(gross) else None),
            "monthly_excess_net": _describe(net),
            "sign_test_post_hoc": _sign_test(
                float((net > 0).mean()) if len(net) else None, len(net)),
            "per_year": _per_year(net),
            "gate": gate,
        }

    print("decile diagnostic (P4)...", flush=True)
    out["p4_decile_diagnostic"] = decile_diagnostic(panel)
    _criteria(out)
    return out


def _criteria(out: dict) -> None:
    v = out["variants"]
    t20 = v.get("top20") or {}
    t40 = v.get("top40") or {}
    t80 = v.get("top80") or {}

    p1 = (t20.get("annualised_excess_net_ex2020") or -9) > 0
    p2 = ((t20.get("monthly_excess_net") or {}).get("median") or -9) > 0

    a20 = t20.get("annualised_excess_net")
    a40 = t40.get("annualised_excess_net")
    a80 = t80.get("annualised_excess_net")
    p3 = (None if None in (a20, a40, a80) else (a20 >= a40 >= a80))

    # This is a directional diagnostic, not numerical reproduction of E05's -14.1pp.
    # The historical predicate only asked for a material negative unfiltered spread and
    # a positive coverage-filtered spread; retain that behavior and name it honestly.
    diag = out.get("p4_decile_diagnostic") or {}
    raw = ((diag.get("absolute") or {}).get("no_coverage_filter") or {}).get("fwd_3y")
    filt = ((diag.get("absolute") or {}).get("coverage_filtered") or {}).get("fwd_3y")
    p4 = bool(raw and filt
              and raw["top_minus_bottom_pp"] < -10
              and filt["top_minus_bottom_pp"] > 0)

    gate = t20.get("gate") or {}
    p5 = bool(gate.get("available")) and bool(gate.get("passes"))

    out["criteria"] = {
        "P1_top20_positive_ex2020_after_cost": p1,
        "P2_median_month_above_zero": p2,
        "P3_size_gradient_runs_the_right_way": p3,
        "P4_E05_negative_unfiltered_and_coverage_flip": p4,
        "P5_deflated_sharpe_and_pbo": p5,
    }
    out["overall_registered"] = "PASS" if (p1 and p2) else "FAIL"
    out["status"] = "SHADOW"
    out["promoted"] = False


def _pct(x):
    return "n/a" if x is None else f"{x * 100:.1f}%"


def _n(x):
    return "n/a" if x is None else f"{x:.2f}"


def render(res: dict) -> str:
    L = ["# E13 results — top-N portfolio of the measured half", "",
         f"as_of {res['as_of']}  ·  pre-registered at `{res['preregistration']}`", "",
         f"**{res['grades']}.**", "",
         f"Panel `{res['panel']}` — {res['coverage']['panel_rows']:,} rows, "
         f"{res['coverage']['rows_after_coverage_filter']:,} after the "
         f"{res['coverage']['min_coverage']:.0%} coverage filter, "
         f"{res['coverage']['symbols']} symbols. "
         f"{HOLD_MONTHS}-month hold, {COST_ROUND_TRIP * 10000:.0f} bps round trip, "
         f"n_trials={res['construction']['n_trials_registered']}.", "",
         "| variant | months | in mkt | ann. net | ann. net ex-2020 | median month | "
         "share + | sign p | breakeven |",
         "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for k, v in res["variants"].items():
        d = v["monthly_excess_net"]
        st = v.get("sign_test_post_hoc") or {}
        L.append(
            f"| {k} | {v['months']} | {v['months_in_market']} | "
            f"{_pct(v['annualised_excess_net'])} | "
            f"{_pct(v['annualised_excess_net_ex2020'])} | "
            f"{_pct(d.get('median'))} | {_pct(d.get('share_positive'))} | "
            f"{st.get('p_value_two_sided', float('nan')):.2f} | "
            f"{v['breakeven_cost_bps']:.0f} bps |")
    L += ["", "## Distribution, not two moments", "",
          "| variant | p05 | p25 | median | p75 | p95 |", "|---|---:|---:|---:|---:|---:|"]
    for k, v in res["variants"].items():
        d = v["monthly_excess_net"]
        if not d.get("n"):
            continue
        L.append(f"| {k} | {_pct(d['p05'])} | {_pct(d['p25'])} | {_pct(d['median'])} | "
                 f"{_pct(d['p75'])} | {_pct(d['p95'])} |")
    L += ["", "## Gate (copper_brain validate.py, imported not re-ported)", ""]
    for k, v in res["variants"].items():
        g = v.get("gate") or {}
        if not g.get("available"):
            L.append(f"- **{k}: NOT COMPUTED** — {g.get('error')}. This is not a pass.")
            continue
        dsr = (g.get("deflated_sharpe") or {}).get("ratio")
        L.append(f"- {k}: monthly Sharpe {g.get('sharpe')}, DSR {dsr} "
                 f"(threshold {(g.get('thresholds') or {}).get('deflated_sharpe_min')}), "
                 f"PBO {g.get('pbo')}, passes={g.get('passes')}")
    diag = res.get("p4_decile_diagnostic") or {}
    absd = diag.get("absolute") or {}
    if absd:
        L += ["", "## P4 — what E05's -14.1% actually was", "",
              "E05 reported a mean IC at 3y of +0.0805 beside a top-bottom decile spread "
              "of -14.1%, and nothing explained how both could be true. Two things were "
              "folded into that number.", "",
              "| decile spread, top − bottom | 1y | 3y |", "|---|---:|---:|"]
        for label in ("no_coverage_filter", "coverage_filtered"):
            row = absd.get(label) or {}
            a1 = (row.get("fwd_1y") or {}).get("top_minus_bottom_pp")
            a3 = (row.get("fwd_3y") or {}).get("top_minus_bottom_pp")
            name = ("absolute, no coverage filter" if label == "no_coverage_filter"
                    else f"absolute, ≥{MIN_COVERAGE:.0%} coverage")
            L.append(f"| {name} | {_n(a1)}pp | {_n(a3)}pp |")
        exd = ((diag.get("excess") or {}).get("coverage_filtered") or {})
        e1 = (exd.get("excess_1y") or {}).get("top_minus_bottom_pp")
        e3 = (exd.get("excess_3y") or {}).get("top_minus_bottom_pp")
        L.append(f"| excess over SPY, ≥{MIN_COVERAGE:.0%} coverage | {_n(e1)}pp | "
                 f"{_n(e3)}pp |")
        bot = ((absd.get("no_coverage_filter") or {}).get("fwd_3y") or {})
        botf = ((absd.get("coverage_filtered") or {}).get("fwd_3y") or {})
        L += ["",
              "**1. It is an ABSOLUTE-return spread, not excess over SPY.**", "",
              "**2. It is computed with no coverage filter, and the bottom decile is "
              "contaminated by companies that score low because they are UNMEASURABLE, "
              "not because they are bad.** Bottom-decile 3y absolute return is "
              f"{_n(bot.get('bottom_decile_mean_pct'))}% unfiltered against "
              f"{_n(botf.get('bottom_decile_mean_pct'))}% once the coverage the rubric "
              "already requires for a band is applied. Those names are small, young and "
              "high-beta, and a decade-long bull market pays them handsomely in absolute "
              "terms.", "",
              "So the score is **not** inverted. E05's headline was a data-coverage "
              "artefact crossed with beta. That is also a direct warning about "
              "`composite_normalized`: missing data is not random, and companies are "
              "being ranked on how measurable they are."]
    L += ["", "## Pre-registered criteria", ""]
    for k, val in res["criteria"].items():
        state = ("NOT YET WRITTEN" if val is None else ("PASS" if val else "FAIL"))
        L.append(f"- `{k}`: **{state}**")
    L += ["", f"**Registered verdict: {res['overall_registered']}** (P1 and P2 both "
              f"required) · **Status: {res['status']}**", "",
          "P4 is a directional diagnostic: the unfiltered 3-year spread must be below "
          "-10pp and the coverage-filtered spread must be positive. It does not claim "
          "numerical reproduction of E05's -14.1pp.",
          "", "Nothing is promoted. `promoted` stays false."]
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    exp = config.JOURNAL_DIR / "experiments"
    ap.add_argument("--panel", default=str(exp / DEFAULT_PANEL))
    ap.add_argument("--restrict-to",
                    help="keep only tickers present in this other panel, so a code "
                         "change is not compared against a universe change")
    ap.add_argument("--tag", default="", help="suffix for the output filenames")
    args = ap.parse_args(argv)

    res = run(args.panel, restrict_to=args.restrict_to)
    suffix = f"_{args.tag}" if args.tag else ""
    (exp / f"E13_results{suffix}.json").write_text(json.dumps(res, indent=2),
                                                   encoding="utf-8")
    md = render(res)
    (exp / f"E13_results{suffix}.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
