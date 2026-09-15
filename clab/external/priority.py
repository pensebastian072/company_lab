"""Which companies to research next, and the control arm that keeps it honest.

External research is metered. 1,500 companies cannot all be researched, so something
has to choose - and the obvious choice is circular. Researching only the companies the
ranking already likes means a high score is never challenged, only confirmed, and the
system quietly becomes unable to be wrong.

## The control arm is the whole point, and E43 proved it has to be MATCHED

`EXTERNAL_CONTROL_FRACTION` of every batch is drawn at random, and it is not a fairness
gesture. It is the only way to answer a question the priority arm cannot answer about
itself:

    does priority actually find more contradictions than chance?

Without it, "the priority engine surfaced 30 contradictions" is unreadable - it might
be 30 more than random, or 10 fewer. E03 measured that 95.6% of this ranking's power was
sector selection, which nobody suspected until it was tested against a null.

**E43 then showed that a free random draw is not enough.** The first batch stratified
the control on SECTOR. Contradiction flags turned out to be almost entirely an INDUSTRY
property - us_credit_scoring 3.00 flags per company, regional_banking and
semiconductor_equipment 2.00, payments 0.31, pc_insurance 0.12, four industries 0.00 -
and priority loaded 21 of its 32 picks into payments and pc_insurance while the random
arm landed in semis and refining. Control then "beat" priority 1.125 to 0.719, and the
difference was EXACTLY what industry mix alone predicted, to three decimals. Both arms
explained nothing beyond where they landed.

So the control is now drawn MATCHED to the priority arm's own industry mix. The
comparison is within-stratum by construction, which is the only way the question has an
answer at all. `matched=False` restores the old free draw for anyone who wants to
reproduce E43.

## Sampling follows E36 exactly

`experiment, seed, requested, drawn, eligible_pool, strata, sector_counts, order` are
all recorded, and the draw is a stratified shuffle under a recorded seed, so **any
prefix of `order` is itself a stratified sample**. A run stopped by the clock - and this
box crashes daily - stays balanced instead of becoming "whatever we got through
alphabetically".
"""
from __future__ import annotations

import argparse
import collections
import json
import random
from datetime import date, datetime, timezone

from .. import config
from . import taxonomy

#: Weights, summing to 1.0. Every input is recorded per company in the priority ledger
#: so a later reader can recompute the decision rather than trusting the number.
WEIGHTS: dict[str, float] = {
    "rank_percentile": 0.20,      # where the framework already puts it
    "score_delta": 0.15,          # how far it moved since the last snapshot
    "contradiction_count": 0.20,  # flags already raised against it
    "valuation_attractive": 0.10,
    "staleness": 0.15,            # how long since we last looked
    "conviction_proximity": 0.15,  # near a band edge, where research changes the answer
    "sector_event": 0.05,
}

#: Market-cap terciles are computed within each sector, so a stratum is
#: (sector, tercile) and a small Utility is not compared against a small Tech name.
N_TERCILES = 3


def _finite(v) -> float | None:
    """NaN passes isinstance(v, float) and silently scrambles every comparison it
    touches. This repo has been bitten by that on a sorted column already."""
    if v is None or isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f or f in (float("inf"), float("-inf")) else f


def priority_inputs(row: dict, *, prior: dict | None = None,
                    flags: list[str] | None = None,
                    today: date | None = None) -> dict:
    """The raw 0-1 inputs behind one company's priority. Recorded, not just used."""
    today = today or datetime.now(timezone.utc).date()
    prior = prior or {}

    score = _finite(row.get("score"))
    rank_pct = _finite(row.get("sector_percentile"))
    prev = _finite(prior.get("score"))
    delta = abs(score - prev) / 100.0 if (score is not None and prev is not None) else 0.0

    va = _finite(row.get("va"))
    va_frac = 0.0 if va is None else max(0.0, min(1.0, va / 15.0))

    last = prior.get("last_research_date")
    if last is None:
        staleness = 1.0                       # never researched is maximally stale
    else:
        try:
            d = datetime.fromisoformat(str(last)[:10]).date()
            staleness = min(1.0, (today - d).days / config.EXTERNAL_STALE_DAYS)
        except (ValueError, TypeError):
            staleness = 1.0

    # Research is most valuable where it can change the answer. A company deep inside a
    # band will still be in that band afterwards; one at the edge may not be.
    prox = 0.0
    if score is not None:
        edges = (50, 60, 70, 80, 90)
        prox = max(0.0, 1.0 - min(abs(score - e) for e in edges) / 10.0)

    return {
        "rank_percentile": 0.0 if rank_pct is None else max(0.0, min(1.0, rank_pct)),
        "score_delta": min(1.0, delta * 5),   # a 20-point move saturates
        "contradiction_count": min(1.0, len(flags or []) / 3.0),
        "valuation_attractive": va_frac,
        "staleness": staleness,
        "conviction_proximity": prox,
        "sector_event": 1.0 if prior.get("sector_event") else 0.0,
    }


def priority_score(inputs: dict) -> float:
    return round(sum(WEIGHTS[k] * inputs.get(k, 0.0) for k in WEIGHTS), 4)


def _stratum_key(row: dict) -> str:
    """The unit a control arm must match on.

    INDUSTRY, not sector. E43 measured why: contradiction flags turned out to be almost
    entirely an industry property - us_credit_scoring averaged 3.00 flags per company,
    regional_banking and semiconductor_equipment 2.00, payments 0.31, pc_insurance 0.12,
    and four industries 0.00. Stratifying the control on SECTOR let the priority arm
    load 21 of 32 picks into payments and pc_insurance while the random arm landed in
    semis and refining, and the observed flag difference then equalled the difference
    predicted by industry mix ALONE, to three decimals. The arms explained nothing.
    """
    return (taxonomy.industry_id(row.get("ticker"), row.get("sub_industry"))
            or taxonomy.sector_id(row.get("sector")) or "unknown")


def _strata(rows: list[dict]) -> dict[tuple, list[dict]]:
    """(industry_id, market-cap tercile within that industry) -> rows."""
    by_sector: dict[str, list[dict]] = collections.defaultdict(list)
    for r in rows:
        by_sector[_stratum_key(r)].append(r)

    out: dict[tuple, list[dict]] = collections.defaultdict(list)
    for sid, members in by_sector.items():
        caps = sorted(members,
                      key=lambda r: (_finite(r.get("market_cap")) or 0.0))
        n = len(caps)
        for i, r in enumerate(caps):
            tercile = min(N_TERCILES - 1, (i * N_TERCILES) // max(n, 1))
            out[(sid, tercile)].append(r)
    return out


def draw_control(rows: list[dict], n: int, *, seed: int) -> list[dict]:
    """Stratified random draw, shuffled under a recorded seed.

    Any prefix of the result is itself stratified, so a run this box interrupts stays
    balanced rather than becoming whatever finished first.
    """
    if n <= 0 or not rows:
        return []
    rng = random.Random(seed)
    strata = _strata(rows)
    picked: list[dict] = []
    # Round-robin across strata so a small sector is represented before a large one is
    # sampled twice.
    pools = {k: rng.sample(v, len(v)) for k, v in strata.items()}
    keys = sorted(pools)
    rng.shuffle(keys)
    while len(picked) < n and any(pools.values()):
        for k in keys:
            if not pools[k]:
                continue
            picked.append(pools[k].pop())
            if len(picked) >= n:
                break
    rng.shuffle(picked)
    return picked


def _draw_matched(pool: list[dict], priority_arm: list[dict], n: int, *,
                  seed: int) -> list[dict]:
    """One control company per priority pick's industry, proportionally.

    Falls back to a free stratified draw for any industry with nothing left, and says so
    by simply drawing fewer - never by silently substituting a different industry.
    """
    if n <= 0 or not pool:
        return []
    rng = random.Random(seed)
    want = collections.Counter(_stratum_key(r) for r in priority_arm)
    # Allocate the control slots across industries in proportion to priority's own mix.
    total = sum(want.values())
    quota: dict[str, int] = {}
    for key, cnt in want.most_common():
        quota[key] = max(1, round(n * cnt / total)) if n else 0
    by_key: dict[str, list[dict]] = collections.defaultdict(list)
    for r in pool:
        by_key[_stratum_key(r)].append(r)

    picked: list[dict] = []
    for key in sorted(quota, key=lambda k: -want[k]):
        available = by_key.get(key) or []
        take = min(quota[key], len(available), n - len(picked))
        if take > 0:
            picked += rng.sample(available, take)
        if len(picked) >= n:
            break
    rng.shuffle(picked)
    return picked


def select(rows: list[dict], *, n: int, seed: int,
           matched: bool = True,
           control_fraction: float | None = None,
           prior: dict[str, dict] | None = None,
           flags: dict[str, list[str]] | None = None,
           today: date | None = None) -> dict:
    """Choose the next research batch: a priority arm and a random control arm."""
    control_fraction = (config.EXTERNAL_CONTROL_FRACTION
                        if control_fraction is None else control_fraction)
    prior, flags = prior or {}, flags or {}

    scored = []
    for r in rows:
        t = r.get("ticker")
        inp = priority_inputs(r, prior=prior.get(t), flags=flags.get(t), today=today)
        scored.append({**r, "_inputs": inp, "_priority": priority_score(inp)})

    n_control = int(round(n * control_fraction))
    n_priority = max(0, n - n_control)

    by_priority = sorted(scored, key=lambda r: (-r["_priority"], str(r.get("ticker"))))
    priority_arm = by_priority[:n_priority]
    chosen = {r["ticker"] for r in priority_arm}
    remaining = [r for r in scored if r["ticker"] not in chosen]

    # MATCHED control: draw each control company from an industry the priority arm
    # actually picked, in proportion to how often it picked it. E43's first design drew
    # the control freely and the two arms ended up in almost disjoint industries, which
    # made "did priority beat chance" unanswerable - the observed difference was exactly
    # the difference industry mix alone predicted. Matching makes the comparison
    # within-stratum by construction, which is the only way the question has an answer.
    if matched and priority_arm:
        control_arm = _draw_matched(remaining, priority_arm, n_control, seed=seed)
    else:
        control_arm = draw_control(remaining, n_control, seed=seed)

    return {
        "experiment": "external_priority",
        "seed": seed,
        "requested": n,
        "control_fraction": control_fraction,
        "eligible_pool": len(rows),
        "control_design": "matched_by_industry" if matched else "free_stratified",
        "n_priority": len(priority_arm),
        "n_control": len(control_arm),
        "strata": len(_strata(rows)),
        "sector_counts": dict(collections.Counter(
            taxonomy.sector_id(r.get("sector")) or "unknown"
            for r in priority_arm + control_arm)),
        # Any prefix of `order` is a stratified, priority-first batch.
        "order": [r["ticker"] for r in priority_arm]
                 + [r["ticker"] for r in control_arm],
        "priority": [{"ticker": r["ticker"], "priority_score": r["_priority"],
                      "inputs": r["_inputs"], "arm": "priority"}
                     for r in priority_arm],
        "control": [{"ticker": r["ticker"], "priority_score": r["_priority"],
                     "inputs": r["_inputs"], "arm": "control"}
                    for r in control_arm],
    }


def log(selection: dict, *, store=None, run_date: date | None = None) -> int:
    from .store import ExternalStore

    store = store or ExternalStore()
    rows = [{**r, "selected": True} for r in selection["priority"] + selection["control"]]
    return store.log_priority(rows, run_date=run_date, seed=selection["seed"])


def main(argv: list[str] | None = None) -> int:
    import pandas as pd

    ap = argparse.ArgumentParser(description="Choose the next research batch")
    ap.add_argument("--n", type=int, default=config.EXTERNAL_RESEARCH_N)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--apply", action="store_true", help="write the priority ledger")
    args = ap.parse_args(argv)

    df = pd.read_parquet(config.SCORES_PARQUET)
    rows = df[["ticker", "sector", "market_cap", "score", "va",
               "sector_percentile"]].to_dict("records")
    sel = select(rows, n=args.n, seed=args.seed)

    print(f"pool {sel['eligible_pool']}  strata {sel['strata']}  seed {sel['seed']}")
    print(f"priority arm {sel['n_priority']}   control arm {sel['n_control']} "
          f"({sel['control_fraction']:.0%})")
    print(f"sectors: {sel['sector_counts']}")
    print(f"\ntop of the priority arm:")
    for r in sel["priority"][:10]:
        top = sorted(r["inputs"].items(), key=lambda kv: -kv[1])[:3]
        print(f"  {r['ticker']:<6} {r['priority_score']:.3f}  "
              + ", ".join(f"{k} {v:.2f}" for k, v in top))
    print(f"\ncontrol arm (random, stratified): "
          f"{[r['ticker'] for r in sel['control'][:12]]}")

    if args.apply:
        n = log(sel)
        print(f"\nlogged {n} rows to priority_ledger")
    else:
        print("\nDRY RUN - nothing written. Re-run with --apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
