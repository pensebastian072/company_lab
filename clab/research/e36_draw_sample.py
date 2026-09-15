"""E36 - draw the v2 lane's comparison set ONCE, before any of it is scored.

Why a drawn set rather than "start at the top and stop when the day ends": the v2 lane
will not finish all 1,501 companies, so the stopping point is arbitrary. In market-cap
order an arbitrary stop yields a large-cap-only sample, and every v1-vs-v2 comparison then
confounds the MODEL with SIZE - on top of the 0.319 size tilt already entangled with the
judged half. Stratify first and the partial run is still balanced: it is a smaller sample,
not a skewed one.

Stratification is 11 GICS sectors x 3 within-sector market-cap terciles, allocated
proportionally to the live universe, then shuffled under a recorded seed so that
*prefix of the order* is itself a valid stratified sample. Stop anywhere and what you have
is balanced.

Only companies that (a) carry a v1 score to compare against and (b) are findable in a
universe file are eligible. That second filter is not paranoia: EQR sits in
`scores.parquet` and in no universe file, so the scorer refuses it with
"symbols are in no universe and will NOT be scored". A set drawn without the filter would
quietly run short of its registered size.

Usage:
    python -m clab.research.e36_draw_sample --n 300 --seed 36
"""
from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict

import pandas as pd

from .. import config
from ..net import atomic_write_json

#: written next to the other experiment artifacts so the run and its registration travel
#: together
OUT = config.JOURNAL_DIR / "experiments" / "E36_sample.json"

TERCILE_LABELS = ("small", "mid", "large")


def eligible(df: pd.DataFrame, universe: set[str]) -> pd.DataFrame:
    """v1-scored, sector-known, cap-known, and actually findable by the scorer."""
    out = df[df["ticker"].isin(universe)].copy()
    out = out[out["sector"].notna() & (out["sector"] != "")]
    out = out[out["market_cap"].notna() & (out["market_cap"] > 0)]
    # A company with no judged half in v1 has nothing to compare against.
    if "qual_available" in out.columns:
        out = out[out["qual_available"].astype(bool)]
    return out


def stratified_draw(pool: pd.DataFrame, n: int, seed: int) -> tuple[list[str], dict, int]:
    """(order, take, pool_size) - 11 sectors x 3 within-sector cap terciles.

    Split out of `draw()` so a later experiment can stratify a DIFFERENT pool the same
    way: E38's control lane draws from the companies both lanes have already scored, and
    a second copy of this arithmetic is a second chance to get the terciles wrong.
    """
    n = min(n, len(pool))

    # Terciles are computed WITHIN sector: a "large" utility and a "large" IT company are
    # not the same size, and a global tercile would put every utility in one bucket and
    # call the sample stratified.
    strata: dict[tuple[str, str], list[str]] = defaultdict(list)
    for sector, block in pool.groupby("sector"):
        if len(block) >= 3:
            labels = pd.qcut(block["market_cap"].rank(method="first"), 3,
                             labels=list(TERCILE_LABELS))
        else:
            labels = pd.Series([TERCILE_LABELS[-1]] * len(block), index=block.index)
        for ticker, lab in zip(block["ticker"], labels):
            strata[(str(sector), str(lab))].append(str(ticker))

    rng = random.Random(seed)
    for key in strata:
        strata[key].sort()          # deterministic before the shuffle
        rng.shuffle(strata[key])

    # Proportional allocation, largest-remainder so the counts sum to exactly n.
    total = sum(len(v) for v in strata.values())
    exact = {k: len(v) * n / total for k, v in strata.items()}
    take = {k: int(v) for k, v in exact.items()}
    for key in sorted(strata, key=lambda k: exact[k] - take[k], reverse=True):
        if sum(take.values()) >= n:
            break
        if take[key] < len(strata[key]):
            take[key] += 1

    picked: list[str] = []
    for key, count in take.items():
        picked.extend(strata[key][:count])

    # Shuffle the FINAL order too, so any prefix is itself stratified. This is the whole
    # point: the run will stop somewhere arbitrary and that stop must not be a selection.
    rng.shuffle(picked)
    return picked, take, total


def draw(n: int, seed: int) -> dict:
    df = pd.read_parquet(config.SCORES_PARQUET)
    from ..qual.scorer import load_universe_multi
    universe = {r["ticker"] for r in load_universe_multi("all")}

    pool = eligible(df, universe)
    if pool.empty:
        raise SystemExit("no eligible companies - is scores.parquet built?")
    picked, take, total = stratified_draw(pool, n, seed)

    return {
        "experiment": "E36",
        "seed": seed,
        "requested": n,
        "drawn": len(picked),
        "eligible_pool": int(total),
        "strata": {f"{s}|{t}": c for (s, t), c in sorted(take.items()) if c},
        "sector_counts": {
            s: sum(c for (sec, _t), c in take.items() if sec == s)
            for s in sorted({sec for sec, _t in take})
        },
        "order": picked,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, required=True,
                    help="registered set size - take it from the PROBE's measured "
                         "throughput, not from optimism")
    ap.add_argument("--seed", type=int, default=36)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    res = draw(args.n, args.seed)
    print(f"drawn {res['drawn']} of an eligible pool of {res['eligible_pool']}, "
          f"seed {res['seed']}")
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
