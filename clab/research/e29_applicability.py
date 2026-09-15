"""E29 - which judged sub-tests have no referent for which sector.

Reads `journal/experiments/E29_applicability_map_preregistration.md` and its Amendment 1.
This script MEASURES; it changes nothing. The map itself is an argued document, because
E12's P3 requires a named written business reason per entry and a null rate is not one.

Three outputs, in the order the registration asks for them:

  1. the full judged sub-test x sector null matrix - every sector, never a worst-four
     view, because a spread cannot be computed from a list that drops its own minimum
     (the defect E12's Amendment 1 was written to fix);
  2. P1-P5 evaluated per (sub-test, sector) candidate, with the refusals and their
     numbers beside the admissions - a map that lists only what it dropped is not
     auditable;
  3. the points itemisation per sector, split into the part this experiment could remove
     (category error: the model was asked and abstained) and the part it CANNOT (scored
     shortfall: the model answered and the answer was low). The second is not in scope
     and reporting them together would overstate what the map can do.

    python -m clab.research.e29_applicability
    python -m clab.research.e29_applicability --json journal/experiments/E29_results.json
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
from pathlib import Path

from .. import config
from ..net import read_json

#: A sector smaller than this does not set a spread endpoint. Imported from
#: `bq_abstention.MIN_SECTOR_N` in substance and repeated here so this module reads on
#: its own: with no floor the one-company "?" sector defines both ends of every spread.
MIN_SECTOR_N = 30

#: the judged components. MG is included because `mg_ceo` is judged, even though most of
#: MG's points are measured from the filings (E26).
JUDGED = ("SG", "BQ", "MG")

#: E19 emits these to carry the availability a company lost by not being assessed. They
#: are not questions, so they never enter the candidate set - but their points ARE the
#: category-error loss, so the itemisation reads them.
UNASSESSED_SUFFIX = "_unassessed"

# ------------------------------------------------------------------ the criteria
P1_SPREAD_PP = 40.0        # across sectors with n >= MIN_SECTOR_N
P2_BEST_SECTOR_PCT = 40.0  # Rule C, imported unchanged from E12 Amendment 1
P4_SECTOR_NULL_PCT = 85.0  # near-total within the nominated sector
P5_SPECIFICITY_PP = 25.0   # above the sector's own median for the component


def _scorecards() -> list[dict]:
    out = []
    for p in sorted(config.SCORECARD_DIR.glob("*.json")):
        d = read_json(p)
        if isinstance(d, dict) and d.get("components"):
            out.append(d)
    return out


def _judged_subtests(card: dict):
    """(component, key, status, max_points, earned) for every judged sub-test."""
    for comp in JUDGED:
        c = (card.get("components") or {}).get(comp) or {}
        for s in (c.get("subtests") or []):
            key = str(s.get("key") or "")
            if not key:
                continue
            yield comp, key, str(s.get("status") or ""), int(s.get("max_points") or 0), \
                s.get("earned")


def matrix(cards: list[dict]) -> dict:
    """null / scored / not_applicable counts per (sub-test, sector).

    The denominator is the sector's company count for that sub-test, so a company whose
    scorecard predates a sub-test is not silently counted as having abstained on it.
    """
    acc: dict[str, dict[str, collections.Counter]] = {}
    sector_n: collections.Counter = collections.Counter()
    for card in cards:
        sec = str(card.get("sector") or "").strip() or "?"
        sector_n[sec] += 1
        for comp, key, status, _mx, _e in _judged_subtests(card):
            if key.endswith(UNASSESSED_SUFFIX):
                continue
            d = acc.setdefault(key, {}).setdefault(sec, collections.Counter())
            d["n"] += 1
            d[status or "?"] += 1
            d["component"] = 0          # placeholder so the key exists
            acc[key].setdefault("__component__", collections.Counter())[comp] += 1

    out: dict[str, dict] = {}
    for key, by_sec in sorted(acc.items()):
        comp = by_sec.pop("__component__").most_common(1)[0][0]
        rows = {}
        for sec, c in by_sec.items():
            n = c["n"]
            rows[sec] = {
                "n": n,
                "null": c["no_data"],
                "scored": c["scored"],
                "not_applicable": c["not_applicable"],
                "null_pct": round(100 * c["no_data"] / n, 1) if n else None,
            }
        out[key] = {"component": comp,
                    "by_sector": dict(sorted(rows.items(), key=lambda kv: -kv[1]["n"]))}
    return {"subtests": out, "sector_n": dict(sector_n.most_common())}


def _component_baseline(mtx: dict, comp: str, sector: str, exclude: str) -> float | None:
    """The sector's MEDIAN null rate across the component's OTHER judged sub-tests.

    P5's instrument. A pack that cannot be read for a sector produces a flat high null
    rate across the whole component; a category error stands out against that baseline.
    """
    vals = []
    for key, rec in mtx["subtests"].items():
        if key == exclude or rec["component"] != comp:
            continue
        row = rec["by_sector"].get(sector)
        if row and row["null_pct"] is not None:
            vals.append(row["null_pct"])
    return statistics.median(vals) if vals else None


def evaluate(mtx: dict) -> list[dict]:
    """P1-P5 for every (sub-test, sector) pair. P3 is not computable and says so."""
    big = {s for s, n in mtx["sector_n"].items() if n >= MIN_SECTOR_N and s != "?"}
    out = []
    for key, rec in mtx["subtests"].items():
        rates = {s: r["null_pct"] for s, r in rec["by_sector"].items()
                 if s in big and r["null_pct"] is not None}
        if len(rates) < 2:
            continue
        lo_sec = min(rates, key=rates.get)
        hi_sec = max(rates, key=rates.get)
        spread = rates[hi_sec] - rates[lo_sec]
        p1 = spread > P1_SPREAD_PP
        p2 = rates[lo_sec] <= P2_BEST_SECTOR_PCT
        for sec in sorted(rates, key=lambda s: -rates[s]):
            p4 = rates[sec] >= P4_SECTOR_NULL_PCT
            base = _component_baseline(mtx, rec["component"], sec, key)
            margin = None if base is None else round(rates[sec] - base, 1)
            p5 = margin is not None and margin > P5_SPECIFICITY_PP
            out.append({
                "subtest": key, "component": rec["component"], "sector": sec,
                "sector_null_pct": rates[sec],
                "best_sector": lo_sec, "best_sector_null_pct": rates[lo_sec],
                "worst_sector": hi_sec, "worst_sector_null_pct": rates[hi_sec],
                "spread_pp": round(spread, 1),
                "component_baseline_null_pct": base,
                "specificity_pp": margin,
                "P1_spread": p1, "P2_answerable_somewhere": p2,
                "P4_near_total_in_sector": p4, "P5_sector_specific": p5,
                "machine_criteria_pass": bool(p1 and p2 and p4 and p5),
                # P3 is a written business reason. It is deliberately NOT derivable here:
                # if a script could decide it, it would be a null rate wearing prose.
                "P3_written_business_reason": "REQUIRED - see E29_applicability_map.md",
            })
    out.sort(key=lambda r: (not r["machine_criteria_pass"], -r["sector_null_pct"]))
    return out


def itemise(cards: list[dict]) -> dict:
    """Points lost per (sector, sub-test), split by what this experiment can touch.

    `category_error` is availability the company never had a chance at - a NO_DATA
    sub-test, or E19's `*_unassessed` weight. `scored_shortfall` is points the model DID
    assess and did not award. The map can only ever move the first, and the registration
    requires them reported apart.
    """
    cat: dict[str, collections.Counter] = {}
    short: dict[str, collections.Counter] = {}
    for card in cards:
        sec = str(card.get("sector") or "").strip() or "?"
        for _comp, key, status, mx, earned in _judged_subtests(card):
            if key.endswith(UNASSESSED_SUFFIX) or status == "no_data":
                cat.setdefault(sec, collections.Counter())[key] += mx
            elif status == "scored" and isinstance(earned, (int, float)):
                short.setdefault(sec, collections.Counter())[key] += mx - int(earned)
    sectors = sorted(set(cat) | set(short))
    return {
        sec: {
            "category_error": dict(cat.get(sec, collections.Counter()).most_common()),
            "category_error_total": sum(cat.get(sec, collections.Counter()).values()),
            "scored_shortfall": dict(short.get(sec, collections.Counter()).most_common()),
            "scored_shortfall_total": sum(short.get(sec, collections.Counter()).values()),
        }
        for sec in sectors
    }


def measure() -> dict:
    cards = _scorecards()
    mtx = matrix(cards)
    return {
        "companies": len(cards),
        "min_sector_n": MIN_SECTOR_N,
        "criteria": {"P1_spread_pp": P1_SPREAD_PP,
                     "P2_best_sector_pct": P2_BEST_SECTOR_PCT,
                     "P4_sector_null_pct": P4_SECTOR_NULL_PCT,
                     "P5_specificity_pp": P5_SPECIFICITY_PP},
        "matrix": mtx,
        "candidates": evaluate(mtx),
        "itemisation": itemise(cards),
        "note": ("P3 - a named written business reason per entry - is not computed here "
                 "and cannot be. Nothing in this file admits an entry to the map; it "
                 "only narrows the list a human has to argue about. No forward-return "
                 "grader exists, so none of this says the resulting scores are better, "
                 "only that they are more internally consistent."),
    }


def _report(r: dict) -> None:
    print(f"{r['companies']} scorecards; sectors with n >= {r['min_sector_n']} set spreads")
    print()
    print("null rate by judged sub-test and sector (%)")
    secs = [s for s, n in r["matrix"]["sector_n"].items()
            if n >= r["min_sector_n"] and s != "?"]
    head = "  ".join(f"{s[:11]:>11s}" for s in secs)
    print(f"{'sub-test':34s}  {head}")
    for key, rec in r["matrix"]["subtests"].items():
        cells = []
        for s in secs:
            row = rec["by_sector"].get(s)
            cells.append(f"{row['null_pct']:>11.1f}" if row else f"{'-':>11s}")
        print(f"{key:34s}  " + "  ".join(cells))

    print()
    print("candidates (P1 spread / P2 answerable / P4 near-total / P5 specific)")
    passed = [c for c in r["candidates"] if c["machine_criteria_pass"]]
    for c in r["candidates"][:14]:
        flags = "".join(mark if ok else "." for mark, ok in (
            ("1", c["P1_spread"]), ("2", c["P2_answerable_somewhere"]),
            ("4", c["P4_near_total_in_sector"]), ("5", c["P5_sector_specific"])))
        print(f"  [{flags}] {c['subtest']:32s} {c['sector']:24s} "
              f"null {c['sector_null_pct']:5.1f}%  best {c['best_sector_null_pct']:5.1f}% "
              f"({c['best_sector'][:14]})  spec {c['specificity_pp']}")
    print(f"  {len(passed)} of {len(r['candidates'])} pairs clear P1+P2+P4+P5; "
          f"every one still needs P3, a written business reason.")

    print()
    print("points itemisation, judged half only")
    print(f"{'sector':26s} {'category error':>15s} {'scored shortfall':>17s}")
    for sec, d in sorted(r["itemisation"].items(),
                         key=lambda kv: -kv[1]["category_error_total"]):
        print(f"{sec:26s} {d['category_error_total']:>15,} "
              f"{d['scored_shortfall_total']:>17,}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="E29 applicability measurement")
    ap.add_argument("--json", type=Path, default=None)
    a = ap.parse_args(argv)
    r = measure()
    _report(r)
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps(r, indent=2), encoding="utf-8")
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
