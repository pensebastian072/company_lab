"""E38 - draw the control lane's order over the companies BOTH lanes have already scored.

Registered at `journal/experiments/E38_control_lane_preregistration.md`. The control is
`qwen2.5:7b` run with the v2 lane's schema and token budget, which is the one cell the
E36 design is missing:

    (qwen-structured - qwen-v1)        = the FORMAT effect
    (LFM2.5 - qwen-structured)         = the MODEL effect

Both differences are only meaningful **paired on the same companies**, so the pool here is
the intersection: a v1 score, and a payload set in the v2 lane's cache. A company scored
by only one lane contributes to neither difference and is left out rather than filled in.

Stratification is E36's - 11 GICS sectors x 3 within-sector market-cap terciles, shuffled
under a recorded seed - reused rather than re-implemented, so any prefix of the order is
itself a stratified sample. That property is the whole reason this run can be stopped by
the clock without becoming a large-cap-only sample.

Usage:
    python -m clab.research.e38_draw_control --v2-dir D:\\company_lab_data\\qual_lfm25
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os

import pandas as pd

from .. import config
from ..net import atomic_write_json
from .e36_draw_sample import eligible, stratified_draw

OUT = config.JOURNAL_DIR / "experiments" / "E38_control_sample.json"

#: A company counts as scored by the v2 lane only with all three components cached. Two of
#: three is a company mid-flight when the box went off, and comparing against a partial
#: judged half would put a missing component into the MODEL difference.
COMPONENTS_REQUIRED = 3


def v2_complete_tickers(v2_dir: str) -> set[str]:
    have: collections.Counter = collections.Counter()
    for path in glob.glob(os.path.join(v2_dir, "*.json")):
        have[os.path.basename(path).split("_")[0]] += 1
    out: set[str] = set()
    for path in glob.glob(os.path.join(v2_dir, "*_SG_*.json")):
        cik = os.path.basename(path).split("_")[0]
        if have.get(cik, 0) < COMPONENTS_REQUIRED:
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                payload = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("ticker"):
            out.add(payload["ticker"])
    return out


def draw(v2_dir: str, n: int | None, seed: int) -> dict:
    df = pd.read_parquet(config.SCORES_PARQUET)
    from ..qual.scorer import load_universe_multi
    universe = {r["ticker"] for r in load_universe_multi("all")}

    scored_by_v2 = v2_complete_tickers(v2_dir)
    pool = eligible(df, universe)
    pool = pool[pool["ticker"].isin(scored_by_v2)]
    if pool.empty:
        raise SystemExit(
            f"no companies are in BOTH lanes - is {v2_dir} the v2 cache? "
            "An empty pool here is a wiring failure, not a small sample."
        )
    picked, take, total = stratified_draw(pool, n or len(pool), seed)

    return {
        "experiment": "E38",
        "seed": seed,
        "v2_dir": v2_dir,
        "requested": n or len(pool),
        "drawn": len(picked),
        "eligible_pool": int(total),
        "v2_complete": len(scored_by_v2),
        "min_for_reporting": 100,
        "strata": {f"{s}|{t}": c for (s, t), c in sorted(take.items()) if c},
        "sector_counts": {
            s: sum(c for (sec, _t), c in take.items() if sec == s)
            for s in sorted({sec for sec, _t in take})
        },
        "order": picked,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--v2-dir", default=r"D:\company_lab_data\qual_lfm25")
    ap.add_argument("--n", type=int, default=None,
                    help="default: the whole paired pool. The run stops where the clock "
                         "stops; a prefix is still stratified.")
    ap.add_argument("--seed", type=int, default=38)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    res = draw(args.v2_dir, args.n, args.seed)
    print(f"drawn {res['drawn']} of {res['eligible_pool']} paired companies "
          f"({res['v2_complete']} complete in the v2 cache), seed {res['seed']}")
    for sector, count in res["sector_counts"].items():
        print(f"  {sector:<24} {count:>4}")
    print(f"\nfirst 10 in run order: {', '.join(res['order'][:10])}")
    if args.dry_run:
        print("\n(dry run - nothing written)")
        return 0
    atomic_write_json(OUT, res)
    print(f"\nwritten: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
