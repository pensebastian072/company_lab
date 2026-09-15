"""Compare two external research arms, company by company.

Written for E42 - arm 1 with no citation rule against arm 2 with it - but the arms are
arguments, so it also serves the V2-vs-V3 comparison the plan asks for once a wider run
exists.

## What it refuses to do

It does not pool. Three companies compared on a mean is a mean of three, and this repo
has already been burned by a pooled number that a sample skew manufactured: the
options-desk backtest's n=369 was 41 date-clusters, and E03's headline survived only
because it was re-cut per fold. Every number here is per company, and the summary is a
count of directions rather than an average of magnitudes.

It does not rank the arms. It reports what moved and by how much; whether more evidence
is better is a question about forward returns that nothing in this repo can answer yet.
"""
from __future__ import annotations

import argparse
import json

from .. import config
from ..external import contradiction as C
from ..external import gates as G
from ..external import score as SC
from ..external.store import ExternalStore

FIELDS = ("external_score", "coverage", "external_confidence",
          "conviction_score", "conviction_band")


def _arm(version: str, store: ExternalStore, df) -> dict[str, dict]:
    scored = {r["ticker"]: r for r in
              SC.score_all(research_version=version, store=store)}
    out: dict[str, dict] = {}
    gates = []
    records = store.companies(version)
    peers_by_industry: dict[str, list[dict]] = {}
    for rec in records:
        peers_by_industry.setdefault(rec.get("industry_id") or "", []).append(rec)
    for rec in records:
        t = rec["ticker"]
        local = (df.loc[t].to_dict() if t in df.index else {})
        local["ticker"] = t
        claims = [c for c in store.claims_for(t)
                  if not rec.get("request_id")
                  or c.get("request_id") == rec["request_id"]]
        peers = [p for p in peers_by_industry.get(rec.get("industry_id") or "", [])
                 if p.get("ticker") != rec["ticker"]]
        flags = C.flags_for(local, rec, claims, peers=peers)
        g = G.evaluate(local, rec, scored.get(t, {}), flags)
        g["_t"] = t
        gates.append(g)
        s = scored.get(t, {})
        out[t] = {
            "ticker": t,
            "external_score": s.get("external_score"),
            "coverage": s.get("coverage"),
            "external_confidence": s.get("external_confidence"),
            "claims": len(claims),
            "verified": sum(1 for c in claims
                            if c.get("verify_status") == "VERIFIED_LOCAL"),
            "domains": s.get("evidence", {}).get("domains"),
            "scored_fields": len(s.get("scored_fields") or []),
            "unbacked_fields": len(s.get("unbacked_fields") or []),
            "flags": flags,
            "research_depth": rec.get("research_depth"),
        }
    for g in G.rank(gates):
        out[g["_t"]]["conviction_score"] = g["conviction_score"]
        out[g["_t"]]["conviction_band"] = g["conviction_band"]
        out[g["_t"]]["conviction_rank"] = g["conviction_rank"]
        out[g["_t"]]["verified_high"] = g["high_conviction_verified"]
    return out


def compare(version_a: str, version_b: str, *,
            store: ExternalStore | None = None) -> dict:
    import pandas as pd

    store = store or ExternalStore()
    df = pd.read_parquet(config.SCORES_PARQUET).set_index("ticker")
    a, b = _arm(version_a, store, df), _arm(version_b, store, df)

    tickers = sorted(set(a) | set(b))
    rows = []
    for t in tickers:
        ra, rb = a.get(t), b.get(t)
        row = {"ticker": t, "in_a": ra is not None, "in_b": rb is not None}
        for f in FIELDS:
            va = (ra or {}).get(f)
            vb = (rb or {}).get(f)
            row[f"a_{f}"], row[f"b_{f}"] = va, vb
            if isinstance(va, (int, float)) and isinstance(vb, (int, float)) \
                    and not isinstance(va, bool) and not isinstance(vb, bool):
                row[f"d_{f}"] = round(vb - va, 3)
        for f in ("claims", "verified", "domains", "scored_fields",
                  "unbacked_fields"):
            row[f"a_{f}"], row[f"b_{f}"] = (ra or {}).get(f), (rb or {}).get(f)
        fa, fb = set((ra or {}).get("flags") or []), set((rb or {}).get("flags") or [])
        row["flags_gained"] = sorted(fb - fa)
        row["flags_lost"] = sorted(fa - fb)
        rows.append(row)

    def direction(field):
        up = sum(1 for r in rows if (r.get(f"d_{field}") or 0) > 0)
        down = sum(1 for r in rows if (r.get(f"d_{field}") or 0) < 0)
        same = len(rows) - up - down
        return {"up": up, "down": down, "unchanged": same}

    return {
        "version_a": version_a, "version_b": version_b,
        "n": len(rows), "rows": rows,
        # Counts of direction, never a mean. Three companies averaged is a mean of
        # three, and a pooled number is exactly what this repo keeps getting caught by.
        "directions": {f: direction(f) for f in
                       ("external_score", "coverage", "external_confidence",
                        "conviction_score")},
        "flags_gained": sorted({f for r in rows for f in r["flags_gained"]}),
        "flags_lost": sorted({f for r in rows for f in r["flags_lost"]}),
        "totals": {
            "a_claims": sum((r["a_claims"] or 0) for r in rows),
            "b_claims": sum((r["b_claims"] or 0) for r in rows),
            "a_scored_fields": sum((r["a_scored_fields"] or 0) for r in rows),
            "b_scored_fields": sum((r["b_scored_fields"] or 0) for r in rows),
            "a_unbacked_fields": sum((r["a_unbacked_fields"] or 0) for r in rows),
            "b_unbacked_fields": sum((r["b_unbacked_fields"] or 0) for r in rows),
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Compare two external research arms")
    ap.add_argument("--a", required=True, help="baseline research_version")
    ap.add_argument("--b", required=True, help="comparison research_version")
    ap.add_argument("--json", default=None, help="write the full result here")
    args = ap.parse_args(argv)

    res = compare(args.a, args.b)
    if not res["n"]:
        print("no companies in either arm")
        return 1

    print(f"A = {res['version_a']}")
    print(f"B = {res['version_b']}")
    print(f"companies: {res['n']}\n")
    head = (f"{'ticker':<7}{'ext A':>7}{'ext B':>7}{'d':>7}   "
            f"{'cov A':>6}{'cov B':>6}   {'conv A':>7}{'conv B':>7}   "
            f"{'clm A':>6}{'clm B':>6}")
    print(head)
    print("-" * len(head))
    for r in res["rows"]:
        def f(v, w=7, p=1):
            return f"{v:>{w}.{p}f}" if isinstance(v, (int, float)) else f"{'-':>{w}}"
        print(f"{r['ticker']:<7}{f(r['a_external_score'])}{f(r['b_external_score'])}"
              f"{f(r.get('d_external_score'))}   "
              f"{f(r['a_coverage'], 6, 2)}{f(r['b_coverage'], 6, 2)}   "
              f"{f(r['a_conviction_score'])}{f(r['b_conviction_score'])}   "
              f"{str(r['a_claims'] or '-'):>6}{str(r['b_claims'] or '-'):>6}")

    print("\ndirection counts (never a mean - three companies averaged is a mean of three):")
    for field, d in res["directions"].items():
        print(f"  {field:<22} up {d['up']}  down {d['down']}  unchanged {d['unchanged']}")
    print(f"\nevidence: claims {res['totals']['a_claims']} -> {res['totals']['b_claims']}"
          f"   scored fields {res['totals']['a_scored_fields']} -> "
          f"{res['totals']['b_scored_fields']}"
          f"   uncited assertions {res['totals']['a_unbacked_fields']} -> "
          f"{res['totals']['b_unbacked_fields']}")
    if res["flags_gained"]:
        print(f"flags gained in B: {res['flags_gained']}")
    if res["flags_lost"]:
        print(f"flags LOST in B:   {res['flags_lost']}")

    print("\nThis compares evidence density and what it changes. It does NOT establish "
          "that either arm predicts returns; nothing in this repo can answer that yet.")

    if args.json:
        from pathlib import Path
        Path(args.json).write_text(json.dumps(res, indent=2, default=str),
                                   encoding="utf-8")
        print(f"\nwritten: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
