"""What the repair pass did to the ranking, not just to the coverage count.

E12's P4 fixed this duty before any denominator work started: after a change that fills
gaps, report the **within-sector rank correlation** of `composite_strict` against its
previous value. A change that reshuffles a sector's ordering is doing more than filling
gaps, and the write-up has to say so in those words.

Compares a snapshot of `scores.parquet` taken before the repair fold against the current
one, over the companies the repair actually touched.

    python -m clab.research.repair_impact --before journal/snapshots/pre_repair.parquet
"""
from __future__ import annotations

import argparse
import json

from .. import config
from ..net import utc_now_iso


def _spearman(a: list[float], b: list[float]) -> float | None:
    """Rank correlation without scipy, which is not installed in this venv."""
    n = len(a)
    if n < 3:
        return None

    def ranks(xs):
        order = sorted(range(len(xs)), key=lambda i: xs[i])
        out = [0.0] * len(xs)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                out[order[k]] = avg
            i = j + 1
        return out

    ra, rb = ranks(a), ranks(b)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    da = sum((x - ma) ** 2 for x in ra) ** 0.5
    db = sum((y - mb) ** 2 for y in rb) ** 0.5
    return round(num / (da * db), 4) if da and db else None


def measure(before_path, after_path=None) -> dict:
    import pandas as pd
    before = pd.read_parquet(before_path)
    after = pd.read_parquet(after_path or config.SCORES_PARQUET)
    key = "ticker"
    b = before.set_index(key)
    a = after.set_index(key)
    common = [t for t in a.index if t in b.index]

    touched = [t for t in common
               if float(a.loc[t].get("repaired_points_quoted") or 0) > 0]
    cov_b = {t: float(b.loc[t].get("coverage") or 0) for t in common}
    cov_a = {t: float(a.loc[t].get("coverage") or 0) for t in common}

    def crossings(threshold):
        up = [t for t in common if cov_b[t] < threshold <= cov_a[t]]
        down = [t for t in common if cov_a[t] < threshold <= cov_b[t]]
        return {"gained": len(up), "lost": len(down), "lost_tickers": sorted(down)[:20]}

    # Over the WHOLE sector, not just the repaired names. Correlating the repaired
    # companies against themselves cannot detect the thing E12 P4 asks about - a repaired
    # company overtaking peers that were not repaired - and returns a near-tautological
    # 1.0 whenever the repair did not reorder that small group among itself.
    by_sector = {}
    sectors = {str(a.loc[t].get("sector") or "?") for t in touched}
    for sector in sorted(sectors):
        peers = [t for t in common if str(a.loc[t].get("sector") or "?") == sector]
        repaired_here = [t for t in peers if t in set(touched)]
        if len(peers) < 3:
            by_sector[sector] = {"n": len(repaired_here), "peers": len(peers),
                                 "spearman": None, "note": "fewer than 3 in sector"}
            continue
        # `or 0` on a missing score sends it to the BOTTOM of the ranking, which is not
        # "unknown" - it is a strong claim. Two companies dropped out of the index and
        # kept stale scorecards, and treating their missing values as zero produced a
        # Real Estate rank correlation of -0.52 that looked like a scoring catastrophe
        # and was a measurement artefact. A company missing on either side is excluded.
        pairs = [(b.loc[t].get("composite_strict"), a.loc[t].get("composite_strict"))
                 for t in peers]
        pairs = [(float(x), float(y)) for x, y in pairs
                 if x is not None and y is not None and x == x and y == y]
        if len(pairs) < 3:
            by_sector[sector] = {"n": len(repaired_here), "peers": len(peers),
                                 "spearman": None,
                                 "note": "fewer than 3 companies scored on both sides"}
            continue
        xb = [p[0] for p in pairs]
        xa = [p[1] for p in pairs]
        moved = [t for t in repaired_here
                 if float(a.loc[t].get("composite_strict") or 0)
                 != float(b.loc[t].get("composite_strict") or 0)]
        by_sector[sector] = {"n": len(repaired_here), "peers": len(peers),
                             "spearman": _spearman(xb, xa),
                             "repaired_whose_score_moved": len(moved)}

    bands_b = {t: str(b.loc[t].get("band")) for t in common}
    bands_a = {t: str(a.loc[t].get("band")) for t in common}
    band_changes = {}
    for t in common:
        if bands_b[t] != bands_a[t]:
            band_changes.setdefault(f"{bands_b[t]} -> {bands_a[t]}", []).append(t)

    return {
        "as_of": utc_now_iso(),
        "companies_compared": len(common),
        "companies_repaired": len(touched),
        "coverage_median_before": round(
            sorted(cov_b.values())[len(cov_b) // 2], 4) if cov_b else None,
        "coverage_median_after": round(
            sorted(cov_a.values())[len(cov_a) // 2], 4) if cov_a else None,
        "threshold_0_80": crossings(0.80),
        "threshold_0_90": crossings(0.90),
        "within_sector_spearman": by_sector,
        "band_changes": {k: {"n": len(v), "tickers": sorted(v)[:20]}
                         for k, v in sorted(band_changes.items(),
                                            key=lambda kv: -len(kv[1]))},
    }


def render(s: dict) -> str:
    L = [f"# Repair pass impact ({s['as_of'][:10]})", "",
         "ADVISORY / SHADOW. This measures what the repair did to COVERAGE and to the",
         "ORDERING. It says nothing about accuracy - there is no forward-return grader.",
         "",
         f"{s['companies_repaired']} of {s['companies_compared']} companies gained at "
         f"least one quote-backed sub-test.", "",
         f"Median coverage {s['coverage_median_before']} -> "
         f"{s['coverage_median_after']}.", "",
         "| threshold | companies gained | companies lost |", "|---|---:|---:|",
         f"| coverage >= 0.80 | {s['threshold_0_80']['gained']} | "
         f"{s['threshold_0_80']['lost']} |",
         f"| coverage >= 0.90 | {s['threshold_0_90']['gained']} | "
         f"{s['threshold_0_90']['lost']} |", "",
         "## E12 P4 - within-sector rank correlation of composite_strict", "",
         "A repair that only fills gaps leaves the ordering inside a sector alone. A",
         "correlation well below 1.0 means it reshuffled the sector, which is a bigger",
         "change than 'more coverage' and must be described as one.", "",
         "Computed over every company in the sector, not only the repaired ones: a",
         "correlation among the repaired names alone cannot see one of them overtaking a",
         "peer that was not repaired.", "",
         "| sector | repaired | of peers | scores moved | Spearman |",
         "|---|---:|---:|---:|---:|"]
    for sector, d in sorted(s["within_sector_spearman"].items(),
                            key=lambda kv: -(kv[1]["n"])):
        L.append(f"| {sector} | {d['n']} | {d.get('peers', 'n/a')} | "
                 f"{d.get('repaired_whose_score_moved', 'n/a')} | "
                 f"{d['spearman'] if d['spearman'] is not None else d.get('note', 'n/a')} |")
    if s["band_changes"]:
        L += ["", "## Band changes", "", "| change | companies |", "|---|---:|"]
        for k, d in s["band_changes"].items():
            L.append(f"| {k} | {d['n']} |")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--before", required=True,
                    help="scores.parquet snapshot taken before the repair fold")
    ap.add_argument("--after", default=None)
    args = ap.parse_args(argv)

    s = measure(args.before, args.after)
    exp = config.JOURNAL_DIR / "experiments"
    (exp / "repair_impact.json").write_text(json.dumps(s, indent=2), encoding="utf-8")
    md = render(s)
    (exp / "repair_impact.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
