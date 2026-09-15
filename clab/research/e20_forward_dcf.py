"""E20 - run the forward DCF over the whole universe and report what it refuses.

Registered in `journal/experiments/E20_forward_dcf_preregistration.md`. The scoring lives
in `clab/scoring/forward_dcf.py`; this is the harness that runs it, checks the identity
that keeps it honest, and writes the table.

Reads SCORECARDS, not live sources: every input a DCF needs is already on disk in the
`metrics` block, so 1,500 companies take seconds instead of an hour of EDGAR calls, and
the run is reproducible against a fixed snapshot rather than against whatever yfinance
says this minute.

    python -m clab.research.e20_forward_dcf
    python -m clab.research.e20_forward_dcf --report
"""
from __future__ import annotations

import argparse
import json
import statistics

from .. import config
from ..net import log_stamp, read_json, utc_now_iso
from ..scoring import forward_dcf

OUT_CSV = config.DATA_DIR / "exports" / "forward_dcf.csv"


def log(msg: str) -> None:
    print(f"[{log_stamp()}] {msg}", flush=True)


class _Metrics:
    """The scorecard's metrics block, wearing the interface `forward_dcf` expects."""

    def __init__(self, flat: dict):
        self._v = flat or {}

    def raw(self, key):
        return self._v.get(key)

    def as_flat(self):
        return dict(self._v)


class _Ctx:
    def __init__(self, card: dict):
        m = card.get("metrics") or {}
        self.ticker = card.get("ticker")
        self.cik = card.get("cik")
        self.sector = card.get("sector") or ""
        self.sub_industry = card.get("sub_industry") or ""
        self.metrics = _Metrics(m)
        self.market = m
        self.prices = m
        self.profile = type("P", (), {"name": card.get("profile") or "STANDARD"})()

    def mk(self, key):
        return self.market.get(key)


def load_cards() -> list[dict]:
    out = []
    for path in sorted(config.SCORECARD_DIR.glob("*.json")):
        card = read_json(path)
        if isinstance(card, dict) and card.get("ticker"):
            out.append(card)
    return out


def peer_medians(rows: list[dict]) -> dict[str, float]:
    """Sub-industry median of the growth rates that DID resolve, for the last resort."""
    by: dict[str, list[float]] = {}
    for r in rows:
        g = r.get("growth")
        if isinstance(g, (int, float)) and r.get("sub_industry"):
            by.setdefault(r["sub_industry"], []).append(float(g))
    return {k: statistics.median(v) for k, v in by.items() if len(v) >= 3}


def run() -> dict:
    cards = load_cards()
    log(f"{len(cards)} scorecards")

    # first pass: everything that can stand on its own series
    rows = []
    for card in cards:
        ctx = _Ctx(card)
        res = forward_dcf.analyse(ctx)
        rows.append({
            "ticker": card.get("ticker"), "cik": card.get("cik"),
            "name": card.get("name"), "sector": ctx.sector,
            "sub_industry": ctx.sub_industry, "profile": ctx.profile.name,
            "band": card.get("band"), "composite_strict": card.get("composite_strict"),
            **{k: res.get(k) for k in (
                "fair_value_per_share", "margin_of_safety", "price",
                "fair_value_over_price", "growth", "wacc", "implausible", "reason")},
            "growth_basis": (res.get("growth_provenance") or {}).get("basis"),
            "bear": (res.get("strip") or {}).get("bear"),
            "bull": (res.get("strip") or {}).get("bull"),
            "wacc_minus": (res.get("wacc_sensitivity") or {}).get("wacc_minus"),
            "wacc_plus": (res.get("wacc_sensitivity") or {}).get("wacc_plus"),
            "_res": res, "_ctx": ctx,
        })

    # second pass: the peer median, computed only from companies that resolved on their
    # own. A median of medians would let one thin sub-industry bootstrap itself.
    medians = peer_medians(rows)
    rescued = 0
    for row in rows:
        if row["fair_value_per_share"] is not None:
            continue
        if row["reason"] != "no usable growth rate":
            continue
        med = medians.get(row["sub_industry"])
        if med is None:
            continue
        res = forward_dcf.analyse(row["_ctx"], peer_median=med)
        if res.get("fair_value_per_share") is None:
            continue
        rescued += 1
        row.update({k: res.get(k) for k in (
            "fair_value_per_share", "margin_of_safety", "price",
            "fair_value_over_price", "growth", "wacc", "implausible", "reason")})
        row["growth_basis"] = (res.get("growth_provenance") or {}).get("basis")
        row["bear"] = (res.get("strip") or {}).get("bear")
        row["bull"] = (res.get("strip") or {}).get("bull")
        row["_res"] = res
    log(f"peer median rescued {rescued} companies in "
        f"{len(medians)} sub-industries")

    # V1: the identity, checked on every company that produced a value
    worst = 0.0
    checked = 0
    for row in rows:
        rec = forward_dcf.reconcile(row["_ctx"], row["_res"])
        if rec.get("checked") and rec.get("abs_error") is not None:
            checked += 1
            worst = max(worst, rec["abs_error"])

    valued = [r for r in rows if r["fair_value_per_share"] is not None]
    mos = [r["margin_of_safety"] for r in valued
           if isinstance(r["margin_of_safety"], (int, float))]
    strip_ok = all(
        (r["bear"] is None or r["bull"] is None
         or r["bear"] < r["fair_value_per_share"] < r["bull"]) for r in valued)

    reasons: dict[str, int] = {}
    for r in rows:
        if r["fair_value_per_share"] is None:
            key = (r["reason"] or "unknown").split(" - ")[0][:60]
            reasons[key] = reasons.get(key, 0) + 1
    bases: dict[str, int] = {}
    for r in valued:
        bases[r["growth_basis"]] = bases.get(r["growth_basis"], 0) + 1

    by_sector = {}
    for sector in sorted({r["sector"] for r in valued if r["sector"]}):
        vals = [r["margin_of_safety"] for r in valued
                if r["sector"] == sector
                and isinstance(r["margin_of_safety"], (int, float))
                and not r["implausible"]]
        if len(vals) >= 5:
            by_sector[sector] = {"n": len(vals),
                                 "median_margin_of_safety": round(
                                     statistics.median(vals), 4)}

    summary = {
        "as_of": utc_now_iso(),
        "companies": len(rows),
        "valued": len(valued),
        "V1_identity_checked": checked,
        "V1_worst_abs_growth_error": worst,
        "V1_pass": checked > 0 and worst < 1e-3,
        "V2_pass": len(valued) >= 1000,
        "V3_strip_monotone": strip_ok,
        "V3_pass": strip_ok,
        "implausible": sum(1 for r in valued if r["implausible"]),
        "median_margin_of_safety": round(statistics.median(mos), 4) if mos else None,
        "share_with_positive_margin": round(
            sum(1 for m in mos if m > 0) / len(mos), 4) if mos else None,
        "growth_basis": dict(sorted(bases.items(), key=lambda kv: -kv[1])),
        "refusals": dict(sorted(reasons.items(), key=lambda kv: -kv[1])),
        "by_sector": by_sector,
        "peer_median_rescued": rescued,
    }
    _write_csv(rows)
    return summary


def _write_csv(rows: list[dict]) -> None:
    import csv
    cols = ["ticker", "name", "sector", "sub_industry", "profile", "band",
            "composite_strict", "price", "fair_value_per_share", "margin_of_safety",
            "fair_value_over_price", "bear", "bull", "wacc_minus", "wacc_plus",
            "growth", "growth_basis", "wacc", "implausible", "reason"]
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in sorted(rows, key=lambda x: -(x["margin_of_safety"] or -9)):
            w.writerow(r)
    log(f"wrote {OUT_CSV}")


def render(s: dict) -> str:
    def v(flag):
        return "PASS" if flag else "FAIL"
    L = [f"# E20 results - forward DCF ({s['as_of'][:10]})", "",
         "ADVISORY / SHADOW. A fair value is four assumptions in a trench coat - the",
         "growth rate, where it fades, the terminal rate and the discount rate. Nothing",
         "here is validated against forward returns and `promoted` stays false.", "",
         "| criterion | measured | bar | verdict |", "|---|---|---|---|",
         f"| V1 forward/reverse identity | worst growth error "
         f"{s['V1_worst_abs_growth_error']:.2e} over {s['V1_identity_checked']} "
         f"companies | < 1e-3 | {v(s['V1_pass'])} |",
         f"| V2 coverage | {s['valued']} of {s['companies']} valued | >= 1,000 | "
         f"{v(s['V2_pass'])} |",
         f"| V3 bear < base < bull | {s['V3_strip_monotone']} | all | "
         f"{v(s['V3_pass'])} |", "",
         f"Median margin of safety **{s['median_margin_of_safety']}**; "
         f"{s['share_with_positive_margin']:.0%} of valued companies screen cheap. "
         f"{s['implausible']} fair values are flagged implausible (>10x or <0.1x price) "
         f"and are excluded from the sector table below.", "",
         "## Where the growth rate came from", "",
         "| basis | companies |", "|---|---:|"]
    for k, n in s["growth_basis"].items():
        L.append(f"| {k} | {n} |")
    L += ["", "## Why the rest got no fair value", "", "| reason | companies |",
          "|---|---:|"]
    for k, n in s["refusals"].items():
        L.append(f"| {k} | {n} |")
    L += ["", "## V4 - margin of safety by sector, reported not scored", "",
          "If the median company in a sector looks 50% cheap, the model is wrong before",
          "the market is.", "", "| sector | n | median margin of safety |",
          "|---|---:|---:|"]
    for sector, d in sorted(s["by_sector"].items(),
                            key=lambda kv: -kv[1]["median_margin_of_safety"]):
        L.append(f"| {sector} | {d['n']} | {d['median_margin_of_safety']:.1%} |")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", action="store_true",
                    help="re-render from the stored summary")
    args = ap.parse_args(argv)

    exp = config.JOURNAL_DIR / "experiments"
    if args.report:
        s = read_json(exp / "E20_results.json")
        if not isinstance(s, dict):
            log("no stored summary")
            return 1
    else:
        s = run()
        (exp / "E20_results.json").write_text(json.dumps(s, indent=2), encoding="utf-8")
    md = render(s)
    (exp / "E20_results.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
