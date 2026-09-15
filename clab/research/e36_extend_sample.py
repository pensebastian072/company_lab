"""E36 - extend the drawn sample to the WHOLE universe, without reordering what has run.

The registered 400 was sized for a run the clock would cut off. The decision changed: the
v2 lane now goes for a complete workbook mirroring v1, so every company the scorer can
find is in scope.

Two properties have to survive that change:

* **Nothing already scored is reordered or re-drawn.** The existing 400 stays as the exact
  prefix of the new order, so the run in flight keeps its meaning and every cached payload
  stays valid. The scorer skips a cached company for free, so re-listing them costs
  nothing.
* **The tail is still stratified.** The run can still be stopped by the clock - overnight,
  a reboot, a dead GPU - and a prefix of the remainder must stay balanced across sectors
  rather than degenerating into whatever `scores.parquet` happened to list first.

The eligibility filter is deliberately WIDER than the 400's: `qual_available` is dropped,
because a company with no v1 judged half still belongs in a complete v2 workbook. It only
drops out of the v1-vs-v2 comparison, which is a different question.

Usage:
    python -m clab.research.e36_extend_sample
"""
from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict

import pandas as pd

from .. import config
from ..net import atomic_write_json
from .e36_draw_sample import OUT as SAMPLE_400
from .e36_draw_sample import TERCILE_LABELS

OUT = config.JOURNAL_DIR / "experiments" / "E36_sample_full.json"


def build(seed: int = 36) -> dict:
    prior = json.loads(SAMPLE_400.read_text(encoding="utf-8"))
    already = list(prior["order"])
    already_set = set(already)

    df = pd.read_parquet(config.SCORES_PARQUET)
    from ..qual.scorer import load_universe_multi
    universe = {r["ticker"] for r in load_universe_multi("all")}

    pool = df[df["ticker"].isin(universe)].copy()
    pool = pool[pool["sector"].notna() & (pool["sector"] != "")]
    pool = pool[pool["market_cap"].notna() & (pool["market_cap"] > 0)]
    rest = pool[~pool["ticker"].isin(already_set)]

    # Same stratification as the original draw, applied to what is LEFT.
    strata: dict[tuple[str, str], list[str]] = defaultdict(list)
    for sector, block in rest.groupby("sector"):
        if len(block) >= 3:
            labels = pd.qcut(block["market_cap"].rank(method="first"), 3,
                             labels=list(TERCILE_LABELS))
        else:
            labels = pd.Series([TERCILE_LABELS[-1]] * len(block), index=block.index)
        for ticker, lab in zip(block["ticker"], labels):
            strata[(str(sector), str(lab))].append(str(ticker))

    rng = random.Random(seed)
    for key in strata:
        strata[key].sort()
        rng.shuffle(strata[key])

    # Round-robin across strata so ANY prefix of the tail is close to balanced, rather
    # than emptying one sector before starting the next.
    keys = sorted(strata)
    rng.shuffle(keys)
    tail: list[str] = []
    i = 0
    while True:
        added = False
        for key in keys:
            if i < len(strata[key]):
                tail.append(strata[key][i])
                added = True
        if not added:
            break
        i += 1

    order = already + tail
    assert len(order) == len(set(order)), "duplicate ticker in the extended order"
    assert order[:len(already)] == already, "the already-run prefix was reordered"

    return {
        "experiment": "E36",
        "extends": str(SAMPLE_400.name),
        "seed": seed,
        "n_prior": len(already),
        "n_added": len(tail),
        "total": len(order),
        "sector_counts": {s: int(c) for s, c in
                          pool["sector"].value_counts().sort_index().items()},
        "order": order,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=36)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    res = build(args.seed)
    print(f"prior {res['n_prior']} + added {res['n_added']} = {res['total']} companies")
    print(f"tail starts: {', '.join(res['order'][res['n_prior']:res['n_prior'] + 8])}")
    if args.dry_run:
        print("(dry run - nothing written)")
        return 0
    atomic_write_json(OUT, res)
    print(f"written: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
