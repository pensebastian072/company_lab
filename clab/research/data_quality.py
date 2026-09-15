"""What the fundamentals layer refused to score, and why.

Companion to `DATA_QUALITY_FAIL`. A metric that fails its plausibility checks is nulled
and withheld rather than scored, which is the right behaviour and also a silent one - if
nothing counts the refusals, a systematic XBRL defect looks exactly like a quiet run.

Reads published artifacts only (scorecards + `scores.parquet`), so it is safe to run at
any time and never re-crawls.

    python -m clab.research.data_quality
    python -m clab.research.data_quality --json out.json
"""
from __future__ import annotations

import argparse
import collections
import json

from .. import config
from ..net import read_json
from ..scoring.types import Status

FAIL = Status.DATA_QUALITY_FAIL.value


def measure() -> dict:
    by_subtest: collections.Counter = collections.Counter()
    by_sector: collections.Counter = collections.Counter()
    by_reason: collections.Counter = collections.Counter()
    companies: dict[str, list] = {}
    n_cards = 0
    n_with_fail = 0
    points_withheld = 0

    for path in config.SCORECARD_DIR.glob("*.json"):
        card = read_json(path)
        if not isinstance(card, dict):
            continue
        n_cards += 1
        ticker = card.get("ticker") or path.stem
        sector = (card.get("sector") or "?").strip() or "?"
        hits = []
        for comp in (card.get("components") or {}).values():
            for st in (comp or {}).get("subtests") or []:
                if st.get("status") != FAIL:
                    continue
                key = st.get("key", "?")
                by_subtest[key] += 1
                points_withheld += int(st.get("max_points") or 0)
                reason = (st.get("rationale") or "").split(" - ")[0][:70]
                by_reason[reason] += 1
                hits.append(key)
        if hits:
            n_with_fail += 1
            by_sector[sector] += 1
            companies[str(ticker)] = sorted(hits)

    # the raw bounds, straight off the published table - catches anything the scoring
    # layer never reached because the company failed earlier
    out_of_range: dict[str, int] = {}
    try:
        import pandas as pd
        df = pd.read_parquet(config.SCORES_PARQUET)
        for metric, (lo, hi) in _bounds().items():
            if metric not in df.columns:
                continue
            s = df[metric]
            out_of_range[metric] = int(((s < lo) | (s > hi)).sum())
        universe = int(len(df))
    except Exception as exc:                    # noqa: BLE001 - report degrades, never dies
        out_of_range = {"error": f"{type(exc).__name__}: {exc}"}
        universe = 0

    return {
        "scorecards": n_cards,
        "universe_rows": universe,
        "companies_with_a_failure": n_with_fail,
        "points_withheld": points_withheld,
        "by_subtest": dict(by_subtest.most_common()),
        "by_sector": dict(by_sector.most_common()),
        "by_reason": dict(by_reason.most_common(10)),
        "still_out_of_range_in_the_table": out_of_range,
        "companies": dict(sorted(companies.items())[:60]),
    }


def _bounds() -> dict:
    from ..scoring import rubric
    return rubric.QUALITY_BOUNDS


def render(r: dict) -> str:
    n = r["scorecards"]
    L = [f"{n} scorecards; **{r['companies_with_a_failure']} have at least one metric "
         f"withheld** as not believable, costing {r['points_withheld']} points of "
         f"coverage across the universe.", ""]
    if r["by_subtest"]:
        L.append("by sub-test:")
        for k, v in r["by_subtest"].items():
            L.append(f"  {k:<28} {v:5d}")
        L.append("")
    if r["by_sector"]:
        L.append("by sector:")
        for k, v in r["by_sector"].items():
            L.append(f"  {k:<28} {v:5d}")
        L.append("")
    if r["by_reason"]:
        L.append("most common reasons:")
        for k, v in r["by_reason"].items():
            L.append(f"  {v:5d}  {k}")
        L.append("")
    oor = r["still_out_of_range_in_the_table"]
    L.append("values STILL outside their bounds in scores.parquet "
             "(should be 0 after a re-crawl; anything else is a metric the "
             "quality layer does not cover yet):")
    for k, v in oor.items():
        L.append(f"  {k:<28} {v}")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", help="also write the raw measurement here")
    args = ap.parse_args(argv)
    r = measure()
    print(render(r))
    if args.json:
        from pathlib import Path
        Path(args.json).write_text(json.dumps(r, indent=2), encoding="utf-8")
        print(f"\nwritten: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
