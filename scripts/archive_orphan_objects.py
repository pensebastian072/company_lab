"""Move industry objects that no company in the book resolves to out of the live tree.

## What they are

E79 re-taxonomised Industrials, splitting coarse units into finer ones - `building_products`
became `building_fixtures_access` and others, `industrial_machinery_supplies_components` became
`engineered_motion_components`, `flow_filtration_equipment` and so on. The finer objects were
written; **the coarse ones were left on disk.** Their `key_participants` lists still name
tickers, but every one of those tickers now resolves through `taxonomy.industry_id` to a
different unit, so nothing reads them and no company is judged against them.

Measured 2026-09-12: **233 objects on disk, 208 units with members, 25 orphans.** Every orphan
answers 0 of 3, so they were 25 of the 61 objects the acceptance gate's `structural_ordinals`
check was failing - which made a corpus-wide audit read worse than the corpus is, and hid the
36 live objects that genuinely conclude nothing.

## What this does, and does not do

It **moves**, never deletes: the directory goes to `industries_orphaned_<stamp>/` beside the
live tree, with its claims intact. Several of them carry real evidence (`research_consulting_
services` has 9 claims, `diversified_support_services` 9) that a later pass may want to
re-point at whichever finer unit inherited those members, so deleting would lose work.

It refuses to move an object that ANY company resolves to, recomputed from the book at run
time rather than trusted from a list. That is the whole safety property: the orphan set is
derived, not typed.

Status is left as SHADOW rather than rewritten to RETIRED, because `research_ingest.
validate_industry` requires SHADOW and a retired-but-invalid artifact is worse than a moved
valid one. Retirement is the store's job (`lifecycle.py`), and these were never in the store.
"""
from __future__ import annotations

import collections
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, r"C:\Users\<your-user>\company_lab")

import pandas as pd

from clab.external import taxonomy as T

ROOT = Path(r"D:\company_lab_data\external\research\industries")
BOOK = Path(r"C:\Users\<your-user>\company_lab\data\scores.parquet")


def orphans() -> list[str]:
    book = pd.read_parquet(BOOK)
    live = collections.Counter()
    for r in book.to_dict("records"):
        live[T.industry_id(r.get("ticker"), r.get("sub_industry"))] += 1
    on_disk = {p.parent.name for p in ROOT.glob("*/industry_state.json")}
    return sorted(on_disk - set(live))


def main(apply: bool = False) -> int:
    found = orphans()
    if not found:
        print("no orphans: every object on disk has at least one company resolving to it")
        return 0
    dest = ROOT.parent / f"industries_orphaned_{datetime.now():%Y%m%d-%H%M}"
    print(f"{len(found)} orphan object(s); destination {dest}\n")
    for iid in found:
        p = ROOT / iid / "industry_state.json"
        obj = json.loads(p.read_text(encoding="utf-8"))
        print(f"  {iid:54} claims={len(obj.get('claims') or []):2} "
              f"listed_members={len(obj.get('key_participants') or []):2}")
        if apply:
            dest.mkdir(parents=True, exist_ok=True)
            shutil.move(str(ROOT / iid), str(dest / iid))
    print("\nDRY RUN - nothing moved" if not apply else f"\nmoved {len(found)} to {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(apply="--apply" in sys.argv[1:]))
