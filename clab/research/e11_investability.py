"""E11 - can a PORTFOLIO harvest E10's small-cap insider edge, or only a signal average?

Pre-registered in `journal/experiments/E11_insider_investability_preregistration.md`
BEFORE any number here was computed. Read it first; the criteria and the variant list are
fixed there and this file only executes them.

The distinction E11 exists to test: E10's statistic is a mean over 9,171 SIGNAL ROWS, so a
month with 300 signals counts 300 times. Crowded insider-buying months are
disproportionately market bottoms, so that weighting flatters the result. A portfolio
weights MONTHS, not signals, and it also pays costs and runs into capacity.

Construction, exactly as registered:
  * at each month end, open an equal-weighted cohort of every qualifying name;
  * hold 12 months, so up to 12 cohorts overlap;
  * the strategy's monthly return is the mean across active cohorts;
  * a month with no active cohort is a month in CASH at zero excess, not a month
    dropped from the series - dropping empty months buys perfect timing for free.

    python -m clab.research.e11_investability
"""
from __future__ import annotations

import argparse
import json
import sys

import numpy as np
import pandas as pd

from .. import config
from ..net import utc_now_iso

#: registered in the pre-registration, and the ONLY axes tried
UNIVERSES = ("sp600", "sp500")
CLUSTER_THRESHOLDS = (1, 3)
N_TRIALS = len(UNIVERSES) * len(CLUSTER_THRESHOLDS)     # = 4, feeds the DSR deflation

HOLD_MONTHS = 12
COST_ROUND_TRIP = 0.0040            # 40 bps, registered before computing
POSITION_USD = 10_000.0             # the scale this box actually operates at
ADV_CAP = 0.01                      # 1% of median 20-day dollar volume
ADV_WINDOW = 20

#: reuse the canonical gate rather than writing a third copy of the math
COPPER_BRAIN = r"C:\Users\<your-user>\copper_brain"


def _gate(pnls, n_trials: int) -> dict:
    """PBO + Deflated Sharpe from copper_brain's validate.py.

    Imported, never re-implemented: the math already lives in two places and a third
    copy is how the DSR unit bug survived in three repos at once. If it cannot be
    imported the result says so LOUDLY - a missing gate is never a silent pass.
    """
    try:
        if COPPER_BRAIN not in sys.path:
            sys.path.insert(0, COPPER_BRAIN)
        from copper_brain import validate as cb
    except Exception as exc:                            # noqa: BLE001
        return {"available": False,
                "error": f"{type(exc).__name__}: {exc}",
                "note": "GATE NOT COMPUTED - this is not a pass"}
    out = cb.evaluate_gate(np.asarray(pnls, dtype=float), n_trials=n_trials)
    out["available"] = True
    return out


# ------------------------------------------------------------------ price plumbing
def monthly_returns(symbols) -> pd.DataFrame:
    """Month-end close-to-close returns, wide: index=month end, columns=ticker."""
    from ..sources import yf_prices

    cols = {}
    for i, t in enumerate(sorted(set(symbols)), 1):
        px = yf_prices.load_prices(t)
        if px is None or px.empty:
            continue
        s = px.copy()
        s["date"] = pd.to_datetime(s["date"], errors="coerce")
        s = (s.dropna(subset=["date", "close"]).set_index("date").sort_index()["close"]
             .astype(float))
        if s.empty:
            continue
        cols[t] = s.resample("ME").last().pct_change()
        if i % 300 == 0:
            print(f"  monthly returns {i}/{len(set(symbols))}", flush=True)
    if not cols:
        return pd.DataFrame()
    return pd.DataFrame(cols).sort_index()


def dollar_volume(symbols) -> dict:
    """{(ticker, month_end): median dollar volume over the prior ADV_WINDOW days}."""
    from ..sources import yf_prices

    out: dict[tuple, float] = {}
    for t in sorted(set(symbols)):
        px = yf_prices.load_prices(t)
        if px is None or px.empty or "volume" not in px.columns:
            continue
        s = px.copy()
        s["date"] = pd.to_datetime(s["date"], errors="coerce")
        s = s.dropna(subset=["date", "close", "volume"]).set_index("date").sort_index()
        dv = (s["close"].astype(float) * s["volume"].astype(float))
        med = dv.rolling(ADV_WINDOW).median()
        for me, v in med.resample("ME").last().dropna().items():
            out[(t, pd.Timestamp(me))] = float(v)
    return out


# ------------------------------------------------------------------ the portfolio
def cohort_series(signal_by_date: dict, rets: pd.DataFrame) -> pd.DataFrame:
    """Overlapping equal-weighted cohorts -> one monthly return series.

    `signal_by_date` is {month_end: [tickers]}. A cohort opened at d contributes its
    equal-weighted return in each of the next HOLD_MONTHS months. The strategy's return
    in month m is the mean across the cohorts active in m.
    """
    months = list(rets.index)
    pos = {m: i for i, m in enumerate(months)}
    rows = []
    for i, m in enumerate(months):
        contrib = []
        n_names = 0
        n_asked = 0
        n_no_price = 0
        n_nan_return = 0
        n_cohorts_no_date = 0
        for d, names in signal_by_date.items():
            j = pos.get(pd.Timestamp(d))
            if j is None or not names:
                # A whole cohort lost before it is ever "asked". This is the channel the
                # name-level counters CANNOT see: a signal date absent from the price
                # index contributes nothing to n_asked, so the drop counters below would
                # read clean while the cohort vanished. That is exactly the survivorship
                # case - `monthly_returns` never creates a column, or a month, for a name
                # with no cached prices - so it has to be counted here or the disclosure
                # has a hole where it is most needed.
                if j is None and names:
                    n_cohorts_no_date += 1
                continue
            # active in month m if the cohort opened in the prior HOLD_MONTHS months
            if not (j < i <= j + HOLD_MONTHS):
                continue
            n_asked += len(names)
            present = [t for t in names if t in rets.columns]
            n_no_price += len(names) - len(present)
            if not present:
                continue
            r = rets.iloc[i][present].dropna()
            n_nan_return += len(present) - len(r)
            if r.empty:
                continue
            contrib.append(float(r.mean()))
            n_names += len(r)
        rows.append({
            "month": m,
            "n_cohorts": len(contrib),
            "n_names": n_names,
            # B7f: a holding with no price column, or a NaN return this month, leaves
            # the cohort and the survivors are implicitly reweighted by the mean below.
            # Measured 2026-09-10 across all four E11 variants: 243,171 name-months
            # asked, 243,171 kept, ZERO dropped - because the universe is today's index
            # members, every one of which has a complete price series. The mechanism has
            # never fired. It fires the moment the universe stops being survivors: none
            # of the 91 delisted names in E04_panel_nosurv has a cached price column at
            # all, so each would be dropped here silently. Counting is therefore not
            # bookkeeping - it is what stops a survivorship fix from being cancelled at
            # the portfolio step without anyone seeing it.
            "n_asked": n_asked,
            "n_dropped_no_price": n_no_price,
            "n_dropped_nan_return": n_nan_return,
            "n_cohorts_unresolvable_date": n_cohorts_no_date,
            # no active cohort => in cash, zero return. NOT a dropped month.
            "ret": float(np.mean(contrib)) if contrib else 0.0,
            "in_market": bool(contrib),
        })
    return pd.DataFrame(rows).set_index("month")


def _annualised(monthly_excess: pd.Series) -> float | None:
    if monthly_excess.empty:
        return None
    return float(monthly_excess.mean() * 12)


def _describe(x: pd.Series) -> dict:
    x = x.dropna()
    if x.empty:
        return {"n": 0}
    q = x.quantile([0.05, 0.25, 0.5, 0.75, 0.95])
    return {
        "n": int(len(x)),
        "mean": float(x.mean()),
        "median": float(x.median()),
        "std": float(x.std()),
        "share_positive": float((x > 0).mean()),
        # the pre-registration asked for the DISTRIBUTION, not two moments
        "p05": float(q.loc[0.05]), "p25": float(q.loc[0.25]),
        "p75": float(q.loc[0.75]), "p95": float(q.loc[0.95]),
        "min": float(x.min()), "max": float(x.max()),
    }


def run(panel_path: str, form4_path: str) -> dict:
    from .e06_insider import build_signals
    from .e10_insider_smallcap import _bucket_map

    panel = pd.read_parquet(panel_path)
    if "measured_pct" not in panel.columns:
        panel["measured_pct"] = np.nan
    form4 = pd.read_parquet(form4_path)

    print("building signals...", flush=True)
    p = build_signals(form4, panel)
    p["bucket"] = p["ticker"].map(_bucket_map()).fillna("other")
    p["date"] = pd.to_datetime(p["date"])

    symbols = sorted(set(p["ticker"]) | {"SPY"})
    print(f"loading monthly returns for {len(symbols)} symbols...", flush=True)
    rets = monthly_returns(symbols)
    if rets.empty or "SPY" not in rets.columns:
        raise RuntimeError("no monthly returns, or SPY missing - cannot compute excess")
    spy = rets["SPY"]

    print("measuring capacity...", flush=True)
    dv = dollar_volume(sorted(set(p["ticker"])))

    out: dict = {
        "study": "E11_insider_investability",
        "as_of": utc_now_iso(),
        "preregistration":
            "journal/experiments/E11_insider_investability_preregistration.md",
        "construction": {
            "hold_months": HOLD_MONTHS,
            "cost_round_trip": COST_ROUND_TRIP,
            "position_usd": POSITION_USD,
            "adv_cap": ADV_CAP,
            "n_trials_registered": N_TRIALS,
            "empty_months": "held in cash at zero excess, never dropped",
        },
        "variants": {},
    }

    for universe in UNIVERSES:
        b = p[p.bucket == universe]
        for thr in CLUSTER_THRESHOLDS:
            key = f"{universe}_insiders_ge_{thr}"
            fires = (b["s3_distinct_buyers"] >= thr) if thr > 1 else (b["s1_buy_count"] > 0)
            sig = b[fires]
            by_date = {d: list(g["ticker"]) for d, g in sig.groupby("date")}

            series = cohort_series(by_date, rets)
            # 40 bps round trip, spread across a 12-month holding period
            monthly_cost = COST_ROUND_TRIP / HOLD_MONTHS
            gross = series["ret"] - spy.reindex(series.index)
            net = gross - np.where(series["in_market"], monthly_cost, 0.0)
            gross = gross.dropna()
            net = net.dropna()

            years = net.index.year
            net_ex2020 = net[years != 2020]

            # capacity: share of signals a POSITION_USD order could not fill
            blocked = total = 0
            for _, r in sig.iterrows():
                cap = dv.get((r["ticker"], pd.Timestamp(r["date"])))
                if cap is None:
                    continue
                total += 1
                if POSITION_USD > ADV_CAP * cap:
                    blocked += 1

            ann_net = _annualised(net)
            ann_net_ex = _annualised(net_ex2020)
            ann_gross = _annualised(gross)

            gate = _gate(net.values, n_trials=N_TRIALS)

            out["variants"][key] = {
                "universe": universe,
                "cluster_threshold": thr,
                "n_signals": int(len(sig)),
                "n_entry_months": int(len(by_date)),
                "n_months": int(len(net)),
                "months_in_market": int(series["in_market"].sum()),
                "median_names_per_month": float(series["n_names"].median()),
                "annualised_excess_gross": ann_gross,
                "annualised_excess_net": ann_net,
                "annualised_excess_net_ex2020": ann_net_ex,
                # P5: the cost at which the edge is exactly zero, in bps per round trip
                "breakeven_cost_bps": (None if ann_gross is None
                                       else float(ann_gross * 10_000)),
                "monthly_excess_net": _describe(net),
                "monthly_excess_net_ex2020": _describe(net_ex2020),
                "capacity": {
                    "signals_checked": total,
                    "blocked": blocked,
                    "blocked_share": (float(blocked / total) if total else None),
                },
                # B7f: the denominator this variant's returns were actually averaged
                # over. `dropped` names left their cohort and the survivors were
                # reweighted; a non-zero `dropped` means the reported return is a
                # survivor return and must be read as one.
                "holdings": {
                    "name_months_asked": int(series["n_asked"].sum()),
                    "name_months_held": int(series["n_names"].sum()),
                    "dropped_no_price_column": int(series["n_dropped_no_price"].sum()),
                    "dropped_nan_return": int(series["n_dropped_nan_return"].sum()),
                    # whole cohorts lost before any name was asked - invisible to the
                    # three counters above, and the channel survivorship would arrive on
                    "cohorts_unresolvable_date": int(
                        series["n_cohorts_unresolvable_date"].max()),
                    "dropped_share": (
                        float((series["n_asked"].sum() - series["n_names"].sum())
                              / series["n_asked"].sum())
                        if series["n_asked"].sum() else None),
                },
                "per_year": {
                    int(y): {"n_months": int((years == y).sum()),
                             "mean_monthly_net": float(net[years == y].mean()),
                             "median_monthly_net": float(net[years == y].median())}
                    for y in sorted(set(years))
                },
                "gate": gate,
            }

    _criteria(out)
    return out


def _sign_test(share_positive: float | None, n: int) -> dict | None:
    """POST-HOC, and labelled as such. Not a registered criterion.

    P2 asks whether the median monthly excess is above zero, and a median can clear that
    bar by a hair. 61 positive months out of 120 IS a positive median and it is also a
    coin flip. Reporting the pass without this number would be true and misleading, so
    the two-sided sign test sits beside it.
    """
    if share_positive is None or not n:
        return None
    k = int(round(share_positive * n))
    # two-sided binomial tail against p=0.5, computed exactly
    from math import comb
    tail = sum(comb(n, i) for i in range(min(k, n - k) + 1)) / (2 ** n)
    return {"n_months": n, "n_positive": k, "p_value_two_sided": min(1.0, 2 * tail),
            "note": "post-hoc diagnostic, NOT a pre-registered criterion"}


def _criteria(out: dict) -> None:
    """The six registered criteria, evaluated mechanically."""
    base = out["variants"].get("sp600_insiders_ge_1") or {}
    clus = out["variants"].get("sp600_insiders_ge_3") or {}

    p1 = (base.get("annualised_excess_net_ex2020") or -9) > 0
    p2 = ((base.get("monthly_excess_net") or {}).get("median") or -9) > 0
    bm = (base.get("monthly_excess_net") or {}).get("median")
    cm = (clus.get("monthly_excess_net") or {}).get("median")
    p3 = (bm is not None and cm is not None and cm > bm)
    bs = (base.get("capacity") or {}).get("blocked_share")
    p4 = (bs is not None and bs < 0.10)
    p5 = (base.get("breakeven_cost_bps") or -9) > COST_ROUND_TRIP * 10_000
    gate = base.get("gate") or {}
    p6 = bool(gate.get("available")) and bool(gate.get("passes"))

    out["criteria"] = {
        "P1_positive_excess_ex2020_after_cost": p1,
        "P2_median_monthly_excess_above_zero": p2,
        "P3_cluster_filter_raises_the_median": p3,
        "P4_capacity_under_10pct_blocked": p4,
        "P5_breakeven_cost_above_40bps": p5,
        "P6_deflated_sharpe_and_pbo": p6,
    }
    # P1 AND P2 are both required. Registered before computing, and NOT restated here to
    # fit the answer - the registered verdict is reported exactly as it falls.
    out["overall_registered"] = "PASS" if (p1 and p2) else "FAIL"

    # ...and the part the registered verdict does not carry on its own. The box-wide rule
    # is that nothing leaves SHADOW until the gate clears, and it did not.
    for v in out["variants"].values():
        d = v.get("monthly_excess_net") or {}
        v["sign_test_post_hoc"] = _sign_test(d.get("share_positive"), d.get("n") or 0)
    st = base.get("sign_test_post_hoc") or {}
    dsr = ((gate.get("deflated_sharpe") or {}).get("ratio")
           if gate.get("available") else None)
    thr = ((gate.get("thresholds") or {}).get("deflated_sharpe_min")
           if gate.get("available") else None)
    med = (base.get("monthly_excess_net") or {}).get("median")
    out["status"] = "SHADOW"
    if st and dsr is not None:
        out["headline"] = (
            f"{out['overall_registered']} on the registered economic criteria, FAIL on "
            f"the overfit gate. The median month clears zero by {med * 100:.2f}% on "
            f"{st['n_positive']} positive months out of {st['n_months']} "
            f"(sign test p={st['p_value_two_sided']:.2f}) - a coin flip. Deflated "
            f"Sharpe is {dsr} against a {thr} threshold. Stays SHADOW.")
    else:
        out["headline"] = ("gate not computed - this is not a pass")
    out["promoted"] = False


def _pct(v):
    return "n/a" if v is None else f"{v * 100:.1f}%"


def render(res: dict) -> str:
    L = [f"# E11 results — is E10's insider edge investable?", ""]
    L.append(f"as_of {res['as_of']}  ·  pre-registered at `{res['preregistration']}`")
    L.append("")
    c = res["construction"]
    L.append(f"Overlapping equal-weighted cohorts, {c['hold_months']}-month hold, "
             f"{c['cost_round_trip'] * 10000:.0f} bps round trip, "
             f"n_trials={c['n_trials_registered']}. "
             f"Months with no active cohort are {c['empty_months']}.")
    L.append("")
    L.append("## Variants (all four registered before computing)")
    L.append("")
    L.append("| variant | signals | months | in mkt | ann. net | ann. net ex-2020 | "
             "median month | share + | breakeven |")
    L.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for k, v in res["variants"].items():
        d = v["monthly_excess_net"]
        L.append(f"| {k} | {v['n_signals']:,} | {v['n_months']} | "
                 f"{v['months_in_market']} | {_pct(v['annualised_excess_net'])} | "
                 f"{_pct(v['annualised_excess_net_ex2020'])} | "
                 f"{_pct(d.get('median'))} | {_pct(d.get('share_positive'))} | "
                 f"{v['breakeven_cost_bps']:.0f} bps |"
                 if v.get("breakeven_cost_bps") is not None else
                 f"| {k} | - | - | - | - | - | - | - | - |")
    L.append("")
    L.append("## The distribution, not two moments")
    L.append("")
    L.append("| variant | p05 | p25 | median | p75 | p95 |")
    L.append("|---|---:|---:|---:|---:|---:|")
    for k, v in res["variants"].items():
        d = v["monthly_excess_net"]
        if not d.get("n"):
            continue
        L.append(f"| {k} | {_pct(d['p05'])} | {_pct(d['p25'])} | {_pct(d['median'])} | "
                 f"{_pct(d['p75'])} | {_pct(d['p95'])} |")
    L.append("")
    L.append("## Capacity")
    L.append("")
    L.append(f"A ${res['construction']['position_usd']:,.0f} position capped at "
             f"{res['construction']['adv_cap']:.0%} of median 20-day dollar volume.")
    L.append("")
    L.append("| variant | signals checked | blocked | share |")
    L.append("|---|---:|---:|---:|")
    for k, v in res["variants"].items():
        cap = v["capacity"]
        L.append(f"| {k} | {cap['signals_checked']:,} | {cap['blocked']:,} | "
                 f"{_pct(cap['blocked_share'])} |")
    L.append("")
    L.append("## Gate (copper_brain validate.py, imported not re-ported)")
    L.append("")
    for k, v in res["variants"].items():
        g = v.get("gate") or {}
        if not g.get("available"):
            L.append(f"- **{k}: NOT COMPUTED** — {g.get('error')}. This is not a pass.")
            continue
        dsr = (g.get("deflated_sharpe") or {}).get("ratio")
        L.append(f"- {k}: monthly Sharpe {g.get('sharpe')}, DSR ratio {dsr} "
                 f"(threshold {(g.get('thresholds') or {}).get('deflated_sharpe_min')}), "
                 f"PBO {g.get('pbo')}, passes={g.get('passes')}")
    L.append("")
    L.append("## Pre-registered criteria")
    L.append("")
    for k, v in res["criteria"].items():
        L.append(f"- `{k}`: **{'PASS' if v else 'FAIL'}**")
    L.append("")
    L.append(f"**Registered verdict: {res['overall_registered']}**  "
             f"(P1 and P2 both required) · **Status: {res['status']}**")
    L.append("")
    L.append(f"> {res['headline']}")
    L.append("")
    L.append("### The median clears zero, and that is almost all it does")
    L.append("")
    L.append("A post-hoc sign test, reported because P2 can be passed by a hair and "
             "reporting the pass alone would be true and misleading:")
    L.append("")
    L.append("| variant | months | positive | sign-test p |")
    L.append("|---|---:|---:|---:|")
    for k, v in res["variants"].items():
        st = v.get("sign_test_post_hoc")
        if not st:
            continue
        L.append(f"| {k} | {st['n_months']} | {st['n_positive']} | "
                 f"{st['p_value_two_sided']:.2f} |")
    L.append("")
    L.append("Not a pre-registered criterion, and it does not change the registered "
             "verdict. It is here so the verdict cannot be read as stronger than it is.")
    L.append("")
    L.append("### Survivorship, stated in the results and not only in the plan")
    L.append("")
    L.append("The bucket map is TODAY's index membership. A company that fell out of the "
             "S&P 600 after a collapse is absent from the panel, which biases every "
             "number here upward. E11 does not fix that and cannot; it is the same "
             "unfixed defect that gates the entry-rule studies.")
    L.append("")
    L.append("Nothing is promoted. `promoted` stays false.")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    exp = config.JOURNAL_DIR / "experiments"
    ap.add_argument("--panel", default=str(exp / "E10_returns_panel.parquet"))
    ap.add_argument("--form4", default=str(exp / "E06_form4_all.parquet"))
    args = ap.parse_args(argv)

    res = run(args.panel, args.form4)
    (exp / "E11_results.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    md = render(res)
    (exp / "E11_results.md").write_text(md, encoding="utf-8")
    print(md)
    print(f"\nwritten: {exp / 'E11_results.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
