"""E32 - how much of a sector's score is a CONSTANT OFFSET rather than a measurement?

E30 found sub-tests that award the same number to nearly every company in a sector. Such
a sub-test cannot separate two companies inside that sector, but it still moves the
composite - so part of every score is an offset that carries no information about the
company, only about its sector. That is the market-state workbook's failure exactly: 6 of
12 layers constant, so a "12-layer confluence tally" was really a 6-layer tally plus an
offset, and nobody could see it from the total.

**This module changes nothing and proposes no thresholds.** `SectorProfile.thresholds`
exists for per-sector re-banding and is empty on purpose - "the mechanism exists, the
calibration does not, and inventing thresholds without a backtest is exactly what this
repo refuses to do". There is no forward-return grader, so there is no way to calibrate a
per-sector band honestly. What CAN be done without one is to say how large the
uninformative part is, per sector, so a reader knows what a 4-point gap between two
sectors is actually made of.

Two numbers per sector:

  * **constant points** - the points contributed by sub-tests where at least
    `CONSTANT_SHARE` of the sector's scored companies land on the same value. Present for
    everyone in the sector, so it shifts the sector's whole distribution and separates
    nobody inside it.
  * **discriminating points** - the rest, which is what actually ranks companies within
    the sector.

    python -m clab.research.e32_constant_offset
    python -m clab.research.e32_constant_offset --json journal/experiments/E32_results.json
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
from pathlib import Path

from .. import config
from ..net import read_json
from ..scoring import rubric

#: same floors E30 and E29 use, repeated so this module reads on its own
MIN_SECTOR_N = 30
CONSTANT_SHARE = 0.95


def _cards() -> list[dict]:
    out = []
    for p in sorted(config.SCORECARD_DIR.glob("*.json")):
        d = read_json(p)
        if isinstance(d, dict) and d.get("components"):
            out.append(d)
    return out


def _subtests(card: dict):
    for comp in rubric.COMPONENT_ORDER:
        c = (card.get("components") or {}).get(comp) or {}
        for s in (c.get("subtests") or []):
            if s.get("key"):
                yield comp, s


def measure(cards: list[dict]) -> dict:
    by_sector: dict[str, list[dict]] = {}
    for c in cards:
        by_sector.setdefault(str(c.get("sector") or "?").strip() or "?", []).append(c)

    out: dict[str, dict] = {}
    for sector, rs in sorted(by_sector.items()):
        if len(rs) < MIN_SECTOR_N or sector == "?":
            continue
        # earned points per sub-test across the sector's SCORED rows
        earned: dict[str, list[int]] = collections.defaultdict(list)
        mx: dict[str, int] = {}
        for card in rs:
            for _comp, s in _subtests(card):
                if str(s.get("status")) != "scored":
                    continue
                e = s.get("earned")
                if isinstance(e, (int, float)):
                    earned[s["key"]].append(int(e))
                    mx[s["key"]] = max(mx.get(s["key"], 0), int(s.get("max_points") or 0))

        constant, discriminating = [], []
        for key, vals in earned.items():
            if not vals:
                continue
            top_val, top_n = collections.Counter(vals).most_common(1)[0]
            rec = {
                "subtest": key, "n_scored": len(vals), "max_points": mx.get(key, 0),
                "modal_value": top_val,
                "modal_share": round(top_n / len(vals), 4),
                "mean_earned": round(statistics.fmean(vals), 3),
            }
            (constant if rec["modal_share"] >= CONSTANT_SHARE
             else discriminating).append(rec)

        const_pts = sum(r["mean_earned"] for r in constant)
        disc_pts = sum(r["mean_earned"] for r in discriminating)
        scores = sorted(c["score"] for c in rs if isinstance(c.get("score"), (int, float)))
        out[sector] = {
            "n": len(rs),
            "median_score": scores[len(scores) // 2] if scores else None,
            "constant_subtests": sorted(constant, key=lambda r: -r["mean_earned"]),
            "discriminating_subtests": len(discriminating),
            "constant_points": round(const_pts, 2),
            "discriminating_points": round(disc_pts, 2),
            "constant_share_of_earned": (round(const_pts / (const_pts + disc_pts), 4)
                                         if (const_pts + disc_pts) else None),
        }
    return {
        "companies": len(cards),
        "min_sector_n": MIN_SECTOR_N,
        "constant_share": CONSTANT_SHARE,
        "sectors": out,
        "note": ("Descriptive only. No threshold is proposed and nothing is changed: "
                 "there is no forward-return grader, so a per-sector band cannot be "
                 "calibrated honestly. This says how much of a sector's score separates "
                 "nobody inside it."),
    }


def _report(r: dict) -> None:
    print(f"{r['companies']} scorecards; a sub-test is CONSTANT when >= "
          f"{r['constant_share']:.0%} of a sector's scored rows share one value\n")
    print(f"{'sector':24s} {'n':>4s} {'median':>7s} {'const':>7s} {'disc':>7s} "
          f"{'const%':>7s}  constant sub-tests")
    for sec, d in sorted(r["sectors"].items(),
                         key=lambda kv: -(kv[1]["constant_share_of_earned"] or 0)):
        names = ", ".join(f"{c['subtest']}={c['modal_value']}" for c in d["constant_subtests"])
        share = d["constant_share_of_earned"]
        print(f"{sec[:24]:24s} {d['n']:>4d} {str(d['median_score']):>7s} "
              f"{d['constant_points']:>7.2f} {d['discriminating_points']:>7.2f} "
              f"{(share or 0):>7.1%}  {names or '-'}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="E32 constant-offset measurement")
    ap.add_argument("--json", type=Path, default=None)
    a = ap.parse_args(argv)
    r = measure(_cards())
    _report(r)
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps(r, indent=2), encoding="utf-8")
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
