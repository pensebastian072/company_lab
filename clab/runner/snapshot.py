"""Weekly point-in-time snapshot of the scores table.

This runs from day one and it is the one task whose absence cannot be repaired
later: a snapshot of what the system believed on a past date cannot be
reconstructed after the fact. Every week without it pushes the forward-return
validation a week further out.

Each snapshot is immutable. journal/snapshots/scores_YYYY-MM-DD.parquet.

Usage:
  python -m clab.runner.snapshot
  python -m clab.runner.snapshot --status
"""
from __future__ import annotations

import argparse
import sys

from .. import config
from ..net import utc_now_iso, utc_today


def write_snapshot(*, day: str | None = None, force: bool = False) -> dict:
    day = day or utc_today()
    out = config.SNAPSHOT_DIR / f"scores_{day}.parquet"
    if out.exists() and not force:
        return {"ok": True, "skipped": True, "path": str(out),
                "reason": "snapshot for this date already exists (immutable)"}
    if not config.SCORES_PARQUET.exists():
        return {"ok": False, "reason": "no scores.parquet to snapshot yet"}
    try:
        import pandas as pd

        df = pd.read_parquet(config.SCORES_PARQUET)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": f"could not read scores.parquet: {exc}"}
    if df.empty:
        return {"ok": False, "reason": "scores.parquet is empty"}
    df = df.copy()
    df["snapshot_date"] = day
    df["snapshot_at"] = utc_now_iso()
    try:
        tmp = out.with_suffix(".parquet.tmp")
        df.to_parquet(tmp, index=False)
        tmp.replace(out)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": f"could not write snapshot: {exc}"}
    return {"ok": True, "path": str(out), "rows": int(len(df)), "date": day}


def status() -> dict:
    hits = sorted(config.SNAPSHOT_DIR.glob("scores_*.parquet"))
    return {
        "n_snapshots": len(hits),
        "first": hits[0].name if hits else None,
        "latest": hits[-1].name if hits else None,
        "note": ("A forward-return IC grader becomes meaningful at roughly 50 weekly "
                 "snapshots. Until then this system makes no claim about predicting "
                 "returns."),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--force", action="store_true", help="overwrite today's snapshot")
    args = ap.parse_args(argv)
    if args.status:
        for k, v in status().items():
            print(f"{k}: {v}")
        return 0
    res = write_snapshot(force=args.force)
    print(res)
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
