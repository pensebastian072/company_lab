"""Why 25% of companies score 0 of 15 on Business Quality.

Rubric A2 awards BQ points only when at least 6 of 11 moat dimensions are scored. A
quarter of the universe sits under that floor. This measures WHY, because the fix
differs completely by cause:

  * a REJECTED out-of-range value, or a failed parse -> a bug in the prompt or parser;
  * a TRUNCATED response -> the prompt-overflow problem;
  * a deliberate `"score": null` -> the model abstaining, exactly as `prompts._RULES`
    instructs it to when the evidence pack does not support a dimension.

The third is what is actually happening (3,981 of 3,981 nulls on 2026-08-16), which puts
the prompt and the floor in direct tension rather than making either of them broken.

Abstention is a property of the MODEL and the PACK, not of the company, so this is meant
to be re-run against every E07 candidate's cache. See
`journal/experiments/E12_bq_denominator_preregistration.md` - its P1 closes the question
with no rubric change at all if a better model simply abstains less.

    python -m clab.research.bq_abstention                 # tables to stdout
    python -m clab.research.bq_abstention --json out.json
"""
from __future__ import annotations

import argparse
import collections
import json
import os

from .. import config
from ..net import read_json
from ..runner.fold_qual import BQ_MIN_DIMENSIONS


def _best_payload_per_cik() -> dict[str, dict]:
    """The highest-scoring BQ payload per CIK.

    A CIK can hold several payloads because the cache key is a hash of the rendered
    evidence pack, so a re-generation writes a NEW file beside the old one. Counting
    files rather than companies double-counts every re-run company and inflates the
    below-floor total - the 2026-08-15 handoff's own snippet had this bug.
    """
    best: dict[str, tuple[int, dict]] = {}
    for path in config.QUAL_DIR.glob("*_BQ_*.json"):
        cik = os.path.basename(path).split("_")[0]
        payload = read_json(path)
        if not isinstance(payload, dict):
            continue
        dims = payload.get("dimensions") or {}
        n = sum(1 for v in dims.values()
                if isinstance(v, dict) and v.get("score") is not None)
        if n >= best.get(cik, (-1, None))[0]:
            best[cik] = (n, payload)
    return {cik: p for cik, (_n, p) in best.items()}


def _sector_by_cik() -> dict[str, str]:
    """CIK -> sector from the scores table, empty if it has not been built yet."""
    try:
        import pandas as pd
        df = pd.read_parquet(config.SCORES_PARQUET)
    except Exception:
        return {}
    out = {}
    for cik, sector in zip(df.get("cik", []), df.get("sector", [])):
        out[str(cik).zfill(10)] = str(sector) if sector else "?"
    return out


def measure() -> dict:
    payloads = _best_payload_per_cik()
    sectors = _sector_by_cik()

    scored = collections.Counter()
    nulls: collections.Counter = collections.Counter()
    seen: collections.Counter = collections.Counter()
    rejected: collections.Counter = collections.Counter()
    parse_ok = collections.Counter()
    chars: list[int] = []
    by_sector: dict[str, dict] = {}

    for cik, payload in payloads.items():
        dims = payload.get("dimensions") or {}
        n = sum(1 for v in dims.values()
                if isinstance(v, dict) and v.get("score") is not None)
        scored[n] += 1
        parse_ok[bool(payload.get("parse_ok"))] += 1
        chars.append(int(payload.get("raw_response_chars") or 0))

        sec = sectors.get(cik, "?")
        s = by_sector.setdefault(sec, {"n": 0, "below": 0,
                                       "nulls": collections.Counter(),
                                       "seen": collections.Counter()})
        s["n"] += 1
        if n < BQ_MIN_DIMENSIONS:
            s["below"] += 1

        for key, rec in dims.items():
            seen[key] += 1
            # Denominator per sector AND per dimension. Dividing by the sector's company
            # count assumes every payload carries every dimension key; a payload that
            # omits one would then understate its null rate.
            s["seen"][key] += 1
            if not (isinstance(rec, dict) and rec.get("score") is not None):
                nulls[key] += 1
                s["nulls"][key] += 1
                # The distinction that decides whether this is a bug or a judgement:
                # a rejected value means the model answered and the parser refused it.
                if isinstance(rec, dict) and rec.get("rejected_value") is not None:
                    rejected[key] += 1

    chars.sort()
    n_co = sum(scored.values())
    return {
        "companies": n_co,
        "floor": BQ_MIN_DIMENSIONS,
        "below_floor": sum(v for k, v in scored.items() if k < BQ_MIN_DIMENSIONS),
        "dimensions_scored_histogram": dict(sorted(scored.items())),
        "parse_ok": {str(k): v for k, v in parse_ok.items()},
        "nulls_total": sum(nulls.values()),
        "nulls_from_a_rejected_value": sum(rejected.values()),
        "raw_response_chars": {
            "min": chars[0] if chars else 0,
            "median": chars[len(chars) // 2] if chars else 0,
            "max": chars[-1] if chars else 0,
        },
        "null_rate_by_dimension": {
            k: round(100 * nulls[k] / seen[k], 1) for k in sorted(seen, key=lambda d: -nulls[d])
        },
        "by_sector": {
            sec: {
                "n": s["n"],
                "below_floor_pct": round(100 * s["below"] / s["n"], 1),
                "null_rate": {k: round(100 * v / s["n"], 1)
                              for k, v in s["nulls"].most_common(4)},
            }
            for sec, s in sorted(by_sector.items(),
                                 key=lambda kv: -kv[1]["below"] / max(kv[1]["n"], 1))
        },
        # The whole 11 x sector grid, not just each sector's worst four. E12's P2 is a
        # statement about a dimension's SPREAD across sectors, and it cannot be computed
        # from a per-sector top-4 list: the minimum is exactly the entry a "worst four"
        # view drops.
        "null_rate_matrix": _matrix(by_sector),
        "p2": _p2(by_sector),
        "p2_min_sector_n": MIN_SECTOR_N,
    }


#: sectors smaller than this do not set a spread endpoint. Declared here rather than
#: chosen per run: with no floor, the 1-company "?" sector defines both ends of every
#: spread at 0% or 100% and P2 passes trivially. Every real GICS sector in this universe
#: is at least 46 companies.
MIN_SECTOR_N = 30

#: the registration's own qualifier on P2: `network_effects` has a 54pt spread but is
#: "75%+ in 9 of 11 sectors", which is why it was predicted to FAIL. A spread alone does
#: not distinguish "inapplicable in some sectors" from "unanswerable nearly everywhere",
#: so both numbers are reported and neither is collapsed into the other.
P2_SPREAD_PP = 40.0
P2_HIGH_FLOOR_PCT = 75.0


def _matrix(by_sector: dict) -> dict:
    return {
        sec: {k: round(100 * s["nulls"].get(k, 0) / v, 1)
              for k, v in sorted(s["seen"].items())}
        for sec, s in sorted(by_sector.items(), key=lambda kv: -kv[1]["n"])
    }


def _p2(by_sector: dict) -> dict:
    """Evaluate E12's P2 per dimension: is abstention CONCENTRATED by sector?"""
    big = {sec: s for sec, s in by_sector.items() if s["n"] >= MIN_SECTOR_N}
    dims = sorted({k for s in big.values() for k in s["seen"]})
    out = {}
    for d in dims:
        rates = {sec: 100 * s["nulls"].get(d, 0) / s["seen"][d]
                 for sec, s in big.items() if s["seen"].get(d)}
        if not rates:
            continue
        lo_sec = min(rates, key=rates.get)
        hi_sec = max(rates, key=rates.get)
        spread = rates[hi_sec] - rates[lo_sec]
        high = sum(1 for v in rates.values() if v >= P2_HIGH_FLOOR_PCT)
        out[d] = {
            "min_sector": lo_sec, "min_pct": round(rates[lo_sec], 1),
            "max_sector": hi_sec, "max_pct": round(rates[hi_sec], 1),
            "spread_pp": round(spread, 1),
            "sectors": len(rates),
            "sectors_at_or_above_75pct": high,
            "spread_over_40pp": spread > P2_SPREAD_PP,
        }
    return dict(sorted(out.items(), key=lambda kv: -kv[1]["spread_pp"]))


def _report(r: dict) -> None:
    n = r["companies"]
    print(f"{n} companies with a BQ payload; floor is {r['floor']} of 11 dimensions")
    print(f"  under the floor: {r['below_floor']} "
          f"({100 * r['below_floor'] / max(n, 1):.1f}%) - these score 0 of 15")
    print(f"  dimensions scored: {r['dimensions_scored_histogram']}")
    print()
    print("Is this a bug or an abstention?")
    print(f"  parse_ok                    {r['parse_ok']}")
    print(f"  nulls total                 {r['nulls_total']}")
    print(f"  of which REJECTED values    {r['nulls_from_a_rejected_value']}"
          f"   <- non-zero means a prompt/parser bug, not a judgement")
    c = r["raw_response_chars"]
    print(f"  raw response chars          min {c['min']}  median {c['median']}  "
          f"max {c['max']}   <- a low max would mean truncation")
    print()
    print("null rate by dimension")
    for k, pct in r["null_rate_by_dimension"].items():
        print(f"  {k:<28} {pct:5.1f}%")
    print()
    print("P2 - is abstention CONCENTRATED by sector? "
          f"(sectors with n >= {r.get('p2_min_sector_n', MIN_SECTOR_N)} only)")
    print(f"  {'dimension':<28}{'spread':>8}  {'lowest sector':<32}"
          f"{'highest sector':<32}{'>=75%':>7}")
    for d, p in r.get("p2", {}).items():
        lo = f"{p['min_sector']} {p['min_pct']}%"
        hi = f"{p['max_sector']} {p['max_pct']}%"
        print(f"  {d:<28}{p['spread_pp']:>7.1f}pp  {lo:<32}{hi:<32}"
              f"{p['sectors_at_or_above_75pct']:>3}/{p['sectors']}")
    print("  a spread over 40pp is P2's stated bar; the last column is the "
          "registration's qualifier -")
    print("  a dimension null in most sectors is unanswerable, not inapplicable, "
          "whatever its spread.")
    print()
    print("by sector (E12 reports per sector, never pooled)")
    print(f"  {'sector':<24}{'n':>5}{'below':>8}   worst dimensions")
    for sec, s in r["by_sector"].items():
        worst = ", ".join(f"{k} {v}%" for k, v in s["null_rate"].items())
        print(f"  {sec:<24}{s['n']:>5}{s['below_floor_pct']:>7.1f}%   {worst}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", help="also write the raw measurement here")
    args = ap.parse_args(argv)

    r = measure()
    _report(r)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(r, fh, indent=2)
        print(f"\nwritten: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
