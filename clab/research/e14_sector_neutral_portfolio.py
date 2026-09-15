"""E14 - does sector-neutral ranking pick better companies, or just more diversified ones?

Pre-registered in `journal/experiments/E14_sector_neutral_preregistration.md` BEFORE any
sector-neutral portfolio return was computed. The variants, `n_trials = 6` and the pass
criteria are fixed there; this file only executes them.

The confound the study exists to catch: E13 found that **concentration hurts
monotonically**, and a sector-neutral top-20 is mechanically spread across more sectors
than a raw top-20, because the raw ranking piles into whichever sectors score high. So an
improvement over raw top-20 is most likely DIVERSIFICATION rather than better selection.
Hence P3 - the gain must survive against raw top-EIGHTY - and hence the sector-composition
columns, which make the mechanism visible instead of arguable.

    python -m clab.research.e14_sector_neutral_portfolio
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from .. import config
from ..net import utc_now_iso
from ..scoring import sector_neutral as sn
from .e13_topn_portfolio import (COST_ROUND_TRIP, HOLD_MONTHS, MIN_COVERAGE, SCORE_COL,
                                 TOP_N, coverage_proxy, top_n_by_date)

RANKINGS = (SCORE_COL, "measured_pct_sector_neutral")
N_TRIALS = len(RANKINGS) * len(TOP_N)          # = 6, registered
DEFAULT_PANEL = "E14_panel_v2.parquet"


def add_monthly_sector_neutral(panel: pd.DataFrame) -> pd.DataFrame:
    """Within-month percentile of `measured_pct`, sub-industry first.

    Computed PER MONTH, never once over the pooled panel. Pooling would let a 2016
    company's rank be set by peers that did not report until 2026 - look-ahead dressed as
    a normalisation, and it is exactly the sort of thing that would inflate the result
    without leaving a trace in the output.
    """
    out = []
    for date, grp in panel.groupby("date", sort=True):
        rows = grp.to_dict("records")
        sn.neutralize(rows, score_col=SCORE_COL)
        g = pd.DataFrame(rows)
        # 0-100 -> 0-1 so both rankings share a scale; only the ORDER matters to top-N
        g["measured_pct_sector_neutral"] = g["sector_neutral_score"] / 100.0
        out.append(g)
    return pd.concat(out, ignore_index=True)


def _composition(by_date: dict, panel: pd.DataFrame) -> dict:
    """Sector spread of the held portfolio - the registered diversification control."""
    sec = panel.drop_duplicates(["ticker"]).set_index("ticker")["sector"].to_dict()
    n_sectors, top_weight = [], []
    for _d, names in by_date.items():
        secs = [(sec.get(t) or "?") for t in names]
        if not secs:
            continue
        counts: dict[str, int] = {}
        for s in secs:
            counts[s] = counts.get(s, 0) + 1
        n_sectors.append(len(counts))
        top_weight.append(max(counts.values()) / len(secs))
    if not n_sectors:
        return {}
    return {
        "mean_distinct_sectors": round(float(np.mean(n_sectors)), 2),
        "min_distinct_sectors": int(min(n_sectors)),
        "mean_largest_sector_weight": round(float(np.mean(top_weight)), 3),
        "max_largest_sector_weight": round(float(max(top_weight)), 3),
    }


def run(panel_path: str) -> dict:
    from .e11_investability import (_describe, _gate, _sign_test, cohort_series,
                                    monthly_returns)

    panel = pd.read_parquet(panel_path)
    panel["date"] = pd.to_datetime(panel["date"])
    panel["coverage_proxy"] = coverage_proxy(panel)
    kept = panel[panel["coverage_proxy"] >= MIN_COVERAGE].copy()
    print(f"{len(panel):,} rows -> {len(kept):,} after coverage; "
          f"{kept['ticker'].nunique()} symbols", flush=True)

    print("computing within-month sector-neutral percentiles...", flush=True)
    kept = add_monthly_sector_neutral(kept)

    symbols = sorted(set(kept["ticker"]) | {"SPY"})
    print(f"loading monthly returns for {len(symbols)} symbols...", flush=True)
    rets = monthly_returns(symbols)
    if rets.empty or "SPY" not in rets.columns:
        raise RuntimeError("no monthly returns, or SPY missing")
    spy = rets["SPY"]

    out: dict = {
        "study": "E14_sector_neutral_portfolio",
        "as_of": utc_now_iso(),
        "preregistration":
            "journal/experiments/E14_sector_neutral_preregistration.md",
        "panel": panel_path,
        "grades": ("the MEASURED HALF (FE+BS+VA+EN) only, as E13 does"),
        "coverage": {"panel_rows": int(len(panel)),
                     "rows_after_coverage_filter": int(len(kept)),
                     "symbols": int(kept["ticker"].nunique())},
        "construction": {"hold_months": HOLD_MONTHS,
                         "cost_round_trip": COST_ROUND_TRIP,
                         "n_trials_registered": N_TRIALS,
                         "percentile_scope": "within each month, never pooled"},
        "variants": {},
    }

    monthly_cost = COST_ROUND_TRIP / HOLD_MONTHS
    for ranking in RANKINGS:
        for n in TOP_N:
            by_date = top_n_by_date(kept, n, score_col=ranking)
            series = cohort_series(by_date, rets)
            gross = (series["ret"] - spy.reindex(series.index)).dropna()
            net = (series["ret"] - spy.reindex(series.index)
                   - np.where(series["in_market"], monthly_cost, 0.0)).dropna()
            net_ex = net[net.index.year != 2020]
            label = "raw" if ranking == SCORE_COL else "neutral"
            out["variants"][f"{label}_top{n}"] = {
                "ranking": ranking, "n": n,
                "months": int(len(net)),
                "annualised_excess_net": float(net.mean() * 12) if len(net) else None,
                "annualised_excess_net_ex2020": (float(net_ex.mean() * 12)
                                                 if len(net_ex) else None),
                "breakeven_cost_bps": (float(gross.mean() * 12 * 10_000)
                                       if len(gross) else None),
                "monthly_excess_net": _describe(net),
                "sign_test_post_hoc": _sign_test(
                    float((net > 0).mean()) if len(net) else None, len(net)),
                "composition": _composition(by_date, kept),
                "gate": _gate(net.values, n_trials=N_TRIALS),
            }
    _criteria(out)
    return out


def _criteria(out: dict) -> None:
    v = out["variants"]

    def _a(k):
        return (v.get(k) or {}).get("annualised_excess_net")

    n20, r20, r80 = _a("neutral_top20"), _a("raw_top20"), _a("raw_top80")
    p1 = ((v.get("neutral_top20") or {}).get("annualised_excess_net_ex2020") or -9) > 0
    p2 = (None if None in (n20, r20) else n20 > r20)
    # P3: the registered diversification control. Beating raw top-20 is not enough when
    # E13 already showed a WIDER portfolio wins for reasons unrelated to selection.
    p3 = (None if None in (n20, r80) else n20 > r80)
    p4 = (((v.get("neutral_top20") or {}).get("monthly_excess_net") or {})
          .get("median") or -9) > 0
    g = (v.get("neutral_top20") or {}).get("gate") or {}
    p5 = bool(g.get("available")) and bool(g.get("passes"))

    out["criteria"] = {
        "P1_neutral_top20_positive_ex2020": p1,
        "P2_beats_raw_top20": p2,
        "P3_survives_the_diversification_control": p3,
        "P4_median_month_above_zero": p4,
        "P5_deflated_sharpe_and_pbo": p5,
    }
    out["overall_registered"] = "PASS" if (p2 and p3) else "FAIL"
    out["status"] = "SHADOW"
    out["promoted"] = False
    out["headline"] = (
        "P2 without P3 is the diversification result wearing a better hat: a "
        "sector-neutral top-20 holds more sectors than a raw top-20, and E13 already "
        "established that a wider portfolio wins for reasons unrelated to stock "
        "selection." if (p2 and not p3) else "")


def _pct(x):
    return "n/a" if x is None else f"{x * 100:.1f}%"


def render(res: dict) -> str:
    L = ["# E14 results — sector-neutral ranking vs raw", "",
         f"as_of {res['as_of']}  ·  pre-registered at `{res['preregistration']}`", "",
         f"Panel `{res['panel']}` — {res['coverage']['rows_after_coverage_filter']:,} "
         f"rows after coverage, {res['coverage']['symbols']} symbols. Percentiles "
         f"computed {res['construction']['percentile_scope']}. "
         f"n_trials={res['construction']['n_trials_registered']}.", "",
         "| variant | ann. net | ex-2020 | median mo | share + | sign p | breakeven | "
         "sectors held | largest sector |",
         "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for k, v in res["variants"].items():
        d, st, c = v["monthly_excess_net"], v.get("sign_test_post_hoc") or {}, v.get("composition") or {}
        L.append(
            f"| {k} | {_pct(v['annualised_excess_net'])} | "
            f"{_pct(v['annualised_excess_net_ex2020'])} | {_pct(d.get('median'))} | "
            f"{_pct(d.get('share_positive'))} | "
            f"{st.get('p_value_two_sided', float('nan')):.2f} | "
            f"{v['breakeven_cost_bps']:.0f} bps | "
            f"{c.get('mean_distinct_sectors', '-')} | "
            f"{_pct(c.get('mean_largest_sector_weight'))} |")
    L += ["", "## Gate", ""]
    for k, v in res["variants"].items():
        g = v.get("gate") or {}
        if not g.get("available"):
            L.append(f"- **{k}: NOT COMPUTED** — {g.get('error')}. Not a pass.")
            continue
        L.append(f"- {k}: DSR {(g.get('deflated_sharpe') or {}).get('ratio')}, "
                 f"PBO {g.get('pbo')}, passes={g.get('passes')}")
    L += ["", "## Pre-registered criteria", ""]
    for k, val in res["criteria"].items():
        L.append(f"- `{k}`: **{'PASS' if val else 'FAIL'}**")
    L += ["", f"**Registered verdict: {res['overall_registered']}** "
              f"(P2 AND P3 both required) · **Status: {res['status']}**"]
    if res.get("headline"):
        L += ["", f"> {res['headline']}"]
    L += ["", "Nothing is promoted. `promoted` stays false."]
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    exp = config.JOURNAL_DIR / "experiments"
    ap.add_argument("--panel", default=str(exp / DEFAULT_PANEL))
    args = ap.parse_args(argv)
    res = run(args.panel)
    (exp / "E14_results.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    md = render(res)
    (exp / "E14_results.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
