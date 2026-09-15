"""Pin the corpus state to a dated JSON, so a count can never be quoted bare.

The unverifiable rate alone has been quoted as 0.077%, 0.134%, 1.607%, 1.22% and
0.980% - every one of them true of a different corpus on a different day. A rate
without its corpus is not a number, it is an anecdote. This writes the same shape
as the hand-built CORPUS_SNAPSHOT_2026-09-09.json so the two are comparable.

    .venv\Scripts\python.exe scripts\corpus_snapshot.py [--as-of YYYY-MM-DD]

Reads only. Writes one file under external/reports/.
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import pandas as pd

from clab import config
from clab.external.store import ExternalStore

#: SELF_ATTESTED is reported beside the rate, never folded into its denominator: it
#: is a claim we chose not to check, not a claim that failed a check.
UNCHECKED = "SELF_ATTESTED"


def build(as_of: str | None = None) -> dict:
    store = ExternalStore()
    current = store.latest_companies()
    current_tickers = {r["ticker"] for r in current}

    with store.connect() as con:
        by_status = dict(con.execute(
            "SELECT verify_status, count(*) FROM external_claim GROUP BY 1").fetchall())
        rows_total = con.execute("SELECT count(*) FROM company_external").fetchone()[0]
        any_arm = [r[0] for r in con.execute(
            "SELECT DISTINCT ticker FROM company_external").fetchall()]
        objects_total = con.execute(
            "SELECT count(*) FROM industry_intelligence").fetchone()[0]
        #: `status` is NULL on every row - the live flag is `superseded_at IS NULL`.
        #: Filtering on `status` silently returns nothing and reads as "no active
        #: objects", which is how this was nearly miscounted.
        objects_active = con.execute(
            "SELECT count(*) FROM industry_intelligence "
            "WHERE superseded_at IS NULL").fetchone()[0]

    checked = sum(v for k, v in by_status.items() if k != UNCHECKED)
    unverifiable = by_status.get("UNVERIFIABLE", 0)
    book_size = len(pd.read_parquet(config.SCORES_PARQUET))
    retired_only = sorted(set(any_arm) - current_tickers)

    return {
        "as_of": as_of or date.today().isoformat(),
        "book_size": book_size,
        "claims_by_status": dict(sorted(by_status.items())),
        "claims_total": sum(by_status.values()),
        "companies_with_current_research": len(current_tickers),
        "companies_with_only_retired_arms": len(retired_only),
        "company_rows_total": rows_total,
        "company_tickers_any_arm": len(any_arm),
        "coverage_pct": round(100 * len(current_tickers) / book_size, 2),
        "industry_objects_active": objects_active,
        "industry_objects_total": objects_total,
        "orphan_sample": retired_only[:10],
        "unverifiable_rate_pct": round(100 * unverifiable / checked, 3) if checked else None,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--as-of", default=None, help="date label, defaults to today")
    args = ap.parse_args(argv)

    snap = build(args.as_of)
    out = Path(config.EXTERNAL_ROOT) / "reports" / f"CORPUS_SNAPSHOT_{snap['as_of']}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snap, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(snap, indent=2))
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
