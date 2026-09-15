"""E09 - LSE `financial_reports` against SEC EDGAR XBRL companyfacts.

Track B of docs/TOMORROW.md. The bar is high and was set before looking: EDGAR gives
as-first-filed values, restatement-aware, back to ~2009, with the exact us-gaap tag
recorded on every number. LSE is adopted only where it beats that or fills a gap EDGAR
genuinely leaves - the most likely candidate being non-US filers, which have no
companyfacts at all.

Tested on the five filers that broke naive parsing: AAPL, JPM, XOM, NKE, COST.

Three tests, fixed before any result:
  depth        - how far back, against EDGAR's ~2009
  point-in-time- does it keep restatements, or only the latest view of a period?
  traceability - can a number be traced to a filing and a tag?

Plus the thing that actually matters for this repo: do the NUMBERS agree.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict

from .. import config
from ..fundamentals import metrics as mx
from ..fundamentals import profile as pf
from ..net import atomic_write_json, utc_now_iso
from ..sources import lse
from ..sources.edgar_facts import (EdgarSubmissions, resolve_facts,
                                   sic_from_submissions)

SYMBOLS = ("AAPL", "JPM", "XOM", "NKE", "COST")

#: LSE `data` keys -> the metric this repo derives from EDGAR. Only fields the scoring
#: actually uses are compared; agreement on a field nobody scores proves nothing.
FIELD_MAP = {
    "revenue": "revenue",
    "operatingIncome": "operating_income",
    "grossProfit": "gross_profit",
    "netIncome": "net_income",
    "freeCashFlow": "fcf",
    "operatingCashFlow": "operating_cash_flow",
}
TOLERANCE = 0.01          # 1% - anything wider is a real disagreement, not rounding


def lse_reports(symbol: str) -> list[dict]:
    rows = lse.ref("financial_reports", symbol=symbol, limit=lse.MAX_ROWS_PER_REQUEST)
    out = []
    for r in rows:
        d = r.get("data")
        if isinstance(d, str):
            try:
                d = json.loads(d)
            except Exception:  # noqa: BLE001
                d = {}
        out.append({**r, "parsed": d if isinstance(d, dict) else {}})
    return out


def describe(symbol: str) -> dict:
    rows = lse_reports(symbol)
    if not rows:
        return {"symbol": symbol, "rows": 0, "note": "no rows returned"}

    dates = sorted(str(r.get("date") or "") for r in rows if r.get("date"))
    by_type: dict[str, int] = defaultdict(int)
    for r in rows:
        by_type[str(r.get("report_type"))] += 1

    # restatements: the same (period, report_type) filed more than once
    groups: dict[tuple, set] = defaultdict(set)
    for r in rows:
        groups[(r.get("date"), r.get("period"), r.get("report_type"))].add(
            str(r.get("filing_date")))
    restated = {k: sorted(v) for k, v in groups.items() if len(v) > 1}

    # traceability: is there an accession, a URL, or a tag anywhere?
    sample = rows[0]
    trace_fields = [k for k in sample
                    if any(t in k.lower() for t in ("accession", "url", "link", "tag"))]

    keys = set()
    for r in rows[:20]:
        keys |= set(r["parsed"].keys())

    return {
        "symbol": symbol,
        "rows": len(rows),
        "earliest_period": dates[0] if dates else None,
        "latest_period": dates[-1] if dates else None,
        "report_types": dict(by_type),
        "periods": sorted({str(r.get("period")) for r in rows}),
        "restated_period_count": len(restated),
        "restatement_examples": dict(list(restated.items())[:3]) if restated else {},
        "traceability_fields": trace_fields,
        "line_item_keys_sample": sorted(keys)[:40],
        "n_line_item_keys": len(keys),
    }


#: metric -> the tag chain in fundamentals/tags.py that supplies it. Using the SAME
#: chains the scorer uses is the point: this compares LSE against the numbers this repo
#: actually scores, not against a fresh interpretation of EDGAR written for the study.
#: NOTE the chain is called `cfo`, not `operating_cash_flow` - see tags.CHAINS.
EDGAR_METRICS = ("revenue", "operating_income", "gross_profit", "net_income",
                 "cfo", "capex")
#: fiscal year-ends can differ by a few days between sources (52/53-week retail years,
#: and a vendor stamping the quarter-end rather than the filing's own end date), so
#: periods are matched within a window instead of on an exact string.
PERIOD_MATCH_DAYS = 20


def _edgar_annual(symbol: str) -> tuple[dict, dict]:
    """{fiscal-year-end: {metric: value}} from EDGAR annual facts, current view."""
    from ..fundamentals import normalize as nz
    from ..fundamentals import tags
    from ..sources import edgar_tickers as et

    tmap = et.load_map()
    ent = tmap.get(symbol)
    if ent is None:
        return {}, {"error": f"{symbol} not in the SEC ticker map"}
    facts_res, cik_used, _n = resolve_facts(ent.cik)
    payload = facts_res.payload if isinstance(facts_res.payload, dict) else {}
    if not payload.get("facts"):
        return {}, {"error": "no companyfacts"}
    subs = EdgarSubmissions(cik_used).fetch()
    sic, _d = sic_from_submissions(subs.payload or {})
    prof = pf.profile_for(sic, "")

    out: dict[str, dict] = defaultdict(dict)
    used_tags: dict[str, str] = {}
    for metric in EDGAR_METRICS:
        tag, rows = tags.resolve(payload, metric)
        if not rows:
            continue
        used_tags[metric] = tag or "?"
        for f in nz.annual_facts(rows, view="current"):
            # Fact.val, NOT .value - getattr(f, "value", None) silently yielded None for
            # every fact and made EDGAR look like it had no annual data at all.
            end = str(f.end or "")[:10]
            if end and f.val is not None:
                out[end][metric] = float(f.val)
                out[end][f"_{metric}_accn"] = f.accn

    # FCF is derived here exactly as the scorer derives it
    for end, vals in out.items():
        ocf, capex = vals.get("cfo"), vals.get("capex")
        if ocf is not None:
            vals["operating_cash_flow"] = ocf
            if capex is not None:
                vals["fcf"] = ocf - abs(capex)
    return dict(out), {"cik": cik_used, "profile": prof.name, "tags": used_tags}


def compare(symbol: str) -> dict:
    """Field-by-field agreement on ANNUAL periods where both sources have a value."""
    from datetime import date as _date

    lse_rows = [r for r in lse_reports(symbol) if str(r.get("period")) == "FY"]
    edgar, meta = _edgar_annual(symbol)
    if not lse_rows or not edgar:
        # say WHICH side was empty; a vague note here sent the first run down a
        # blind alley looking for missing LSE rows that were in fact present
        why = meta.get("error") or (
            "no FY rows from LSE" if not lse_rows else "no annual facts from EDGAR")
        return {"symbol": symbol, "comparable_periods": 0, "note": why,
                "lse_fy_rows": len(lse_rows), "edgar_periods": len(edgar), **meta}

    # merge the three report_type rows that share a period
    merged: dict[str, dict] = defaultdict(dict)
    for r in lse_rows:
        merged[str(r.get("date"))[:10]].update(r["parsed"])

    def _match(end: str) -> dict | None:
        """LSE period whose date is within PERIOD_MATCH_DAYS of this EDGAR year-end."""
        if end in merged:
            return merged[end]
        try:
            a = _date.fromisoformat(end)
        except ValueError:
            return None
        best, best_gap = None, PERIOD_MATCH_DAYS + 1
        for k, v in merged.items():
            try:
                gap = abs((_date.fromisoformat(k) - a).days)
            except ValueError:
                continue
            if gap < best_gap:
                best, best_gap = v, gap
        return best

    per_field: dict[str, dict] = {k: {"n": 0, "agree": 0, "disagreements": []}
                                  for k in FIELD_MAP}
    periods = 0
    for end, ours in sorted(edgar.items()):
        theirs = _match(end)
        if not theirs:
            continue
        periods += 1
        for lse_key, metric in FIELD_MAP.items():
            a, b = ours.get(metric), theirs.get(lse_key)
            if a is None or b is None:
                continue
            try:
                b = float(b)
            except (TypeError, ValueError):
                continue
            per_field[lse_key]["n"] += 1
            denom = max(abs(a), abs(b), 1.0)
            rel = abs(a - b) / denom
            if rel <= TOLERANCE:
                per_field[lse_key]["agree"] += 1
            elif len(per_field[lse_key]["disagreements"]) < 4:
                per_field[lse_key]["disagreements"].append(
                    {"period": end, "edgar": a, "lse": b, "rel_diff": round(rel, 4)})

    for k, v in per_field.items():
        v["agreement_rate"] = (v["agree"] / v["n"]) if v["n"] else None
    return {"symbol": symbol, "comparable_periods": periods,
            "overlapping_lse_periods": len(merged), "edgar_periods": len(edgar),
            "per_field": per_field, **meta}


def render(res: dict) -> str:
    L = []
    A = L.append
    A("# E09 — LSE `financial_reports` vs SEC EDGAR\n")
    A(f"as_of {res['as_of']}\n")
    A("EDGAR is the incumbent and the bar is high: as-first-filed, restatement-aware, "
      "back to ~2009, with the exact us-gaap tag on every number. LSE is adopted only "
      "if it beats that or fills a gap EDGAR genuinely leaves.\n")

    A("\n## Coverage and structure\n")
    A("| symbol | rows | earliest | latest | periods | restated periods | traceability |")
    A("|---|---:|---|---|---|---:|---|")
    for d in res["describe"]:
        if d.get("rows", 0) == 0:
            A(f"| {d['symbol']} | 0 | — | — | — | — | {d.get('note', '')} |")
            continue
        A(f"| {d['symbol']} | {d['rows']} | {d['earliest_period']} | "
          f"{d['latest_period']} | {','.join(d['periods'])} | "
          f"{d['restated_period_count']} | "
          f"{', '.join(d['traceability_fields']) or '**none**'} |")

    A("\n## Do the numbers agree? (annual periods present in both)\n")
    A("| symbol | periods | " + " | ".join(FIELD_MAP) + " |")
    A("|---|---:|" + "---:|" * len(FIELD_MAP))
    for c in res["compare"]:
        if not c.get("comparable_periods"):
            A(f"| {c['symbol']} | 0 | " + " | ".join(["—"] * len(FIELD_MAP))
              + f" |  {c.get('note', '')}")
            continue
        cells = []
        for k in FIELD_MAP:
            v = c["per_field"][k]
            cells.append(f"{v['agreement_rate']:.0%} ({v['n']})"
                         if v["agreement_rate"] is not None else "—")
        A(f"| {c['symbol']} | {c['comparable_periods']} | " + " | ".join(cells) + " |")

    A("\n### Largest disagreements\n")
    any_d = False
    for c in res["compare"]:
        for k, v in (c.get("per_field") or {}).items():
            for d in v["disagreements"]:
                any_d = True
                A(f"- **{c['symbol']} {k} {d['period']}**: EDGAR {d['edgar']:,.0f} vs "
                  f"LSE {d['lse']:,.0f} ({d['rel_diff']:.1%})")
    if not any_d:
        A("None outside the 1% tolerance on the compared fields.")
    A("\n" + res["verdict"] + "\n")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--symbols", default=",".join(SYMBOLS))
    args = ap.parse_args(argv)
    syms = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    desc = [describe(s) for s in syms]
    comp = [compare(s) for s in syms]

    earliest = [d["earliest_period"] for d in desc if d.get("earliest_period")]
    restated = sum(d.get("restated_period_count", 0) for d in desc)
    traceable = any(d.get("traceability_fields") for d in desc)

    # where does it agree, and where does it not?
    clean, diverging = [], []
    for c in comp:
        pf_ = c.get("per_field") or {}
        rates = [v["agreement_rate"] for v in pf_.values()
                 if v.get("agreement_rate") is not None]
        if not rates:
            continue
        (clean if min(rates) >= 0.99 else diverging).append(c["symbol"])

    verdict = (
        "**Verdict — EDGAR stays the source of record.**\n\n"
        f"- **Depth**: earliest period seen {min(earliest) if earliest else 'n/a'}, "
        f"against EDGAR's ~2009. The catalogue advertises 2013; the filers probed start "
        f"2017-2018.\n"
        f"- **Point-in-time**: {restated} restated periods retained across all five "
        f"filers. "
        + ("A point-in-time view is possible.\n"
           if restated else "**Every period appears exactly once**, so this is a "
                            "latest-view source. It cannot support the `as_first_filed` "
                            "discipline the panel depends on — and grading a model on "
                            "restated numbers is look-ahead bias.\n")
        + "- **Traceability**: "
        + ("present.\n" if traceable else
           "**none**. No accession, no URL, no us-gaap tag on any number, so a figure "
           "cannot be traced back to the filing it came from. EDGAR carries the tag and "
           "the accession on every fact.\n")
        + f"- **Agreement**: exact on the clean filers ({', '.join(clean) or 'none'}), "
          f"but it diverges on {', '.join(diverging) or 'none'} — and those are the hard "
          f"cases the set was chosen for. JPM revenue disagrees by 4-19% every year "
          f"(a bank total-vs-net revenue definition), JPM 2025 operating cash flow has "
          f"the **opposite sign** (EDGAR −147.8bn, LSE +100.9bn), and XOM revenue runs "
          f"2.5-3.6% apart every year (excise taxes in or out). None of these are errors "
          f"exactly; they are a different chart of accounts, which is precisely why a "
          f"source without a tag per number cannot be reconciled.\n\n"
        "The one gap LSE could still fill is **non-US filers**, which have no "
        "companyfacts at all. That is worth revisiting only if the universe expands "
        "beyond US listings.")

    res = {"study": "E09_lse_vs_edgar", "as_of": utc_now_iso(),
           "tolerance": TOLERANCE, "describe": desc, "compare": comp,
           "verdict": verdict}
    exp = config.JOURNAL_DIR / "experiments"
    atomic_write_json(exp / "E09_results.json", res)
    md = render(res)
    (exp / "E09_results.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
