"""Fold every cached judgement score that has not reached a scorecard yet.

A qual batch only fills the CACHE. Until the scorecards are rebuilt the new scores are
invisible to the UI, the workbook and every study.

The daily task used to fold by BATCH MANIFEST - the list the scorer just touched - which
strands anything scored outside that run. A 215-company catch-up finishing at 03:50
would have been overwritten by the next day's manifest and never folded at all.

So this asks the durable question instead: which companies have a complete cached
judgement half that their scorecard does not reflect? It self-heals regardless of how
the cache got ahead, including an interrupted run, a manual --symbols batch, or a
scorecard rewritten by a quant-only crawl.
"""
from __future__ import annotations

import argparse
import json

from .. import config
from ..net import read_json
from ..scoring.repair_merge import merged_items


#: rubric A2: BQ needs this many of its 11 moat dimensions scored before it awards points
BQ_MIN_DIMENSIONS = 6


def _cache_has_any_score(cik: str, component: str) -> bool:
    """Does the cached component hold at least one non-null score?

    A component whose cached payload is entirely `null` awards no points, and a
    scorecard showing 0 for it is CORRECT rather than behind. Without this, MFP - whose
    SG, BQ and MG are all cached and all fully abstained - was re-flagged as stale on
    every run, re-folded to no effect, and flagged again. That is an unfixable loop, and
    once the fold started reporting failure loudly it would have turned the watchdog
    permanently red for a company that has nothing wrong with it.
    """
    for p in config.QUAL_DIR.glob(f"{cik}_{component}_*.json"):
        payload = read_json(p)
        if not isinstance(payload, dict):
            continue
        for bucket in ("scores", "dimensions", "ceo"):
            # merged, not raw: a score the first call declined and the repair pass
            # recovered with a verified quote is a real score. Counting only the raw
            # bucket would leave the repaired company looking up to date while its
            # scorecard still says NO_DATA - the fold would skip it forever.
            for v in merged_items(payload, bucket).values():
                if isinstance(v, dict) and v.get("score") is not None:
                    return True
    return False


def _cached_bq_dimensions(cik: str) -> int | None:
    """Scored moat dimensions in the CURRENT cached BQ payload, or None if absent.

    Counts repaired dimensions too. A company whose sixth dimension came from the repair
    pass clears the floor only after the merge, and if this counted the raw payload the
    fold would never notice it had crossed.
    """
    best = None
    for p in config.QUAL_DIR.glob(f"{cik}_BQ_*.json"):
        payload = read_json(p)
        if not isinstance(payload, dict):
            continue
        dims = merged_items(payload, "dimensions")
        n = sum(1 for v in dims.values()
                if isinstance(v, dict) and v.get("score") is not None)
        best = n if best is None else max(best, n)
    return best


def stale_tickers() -> list[str]:
    """Companies whose scorecard is BEHIND their cached judgement half.

    Two distinct ways a scorecard falls behind, and both must be caught:

      * it has no judgement half at all - the cache was filled after the scorecard was
        written, or a quant-only crawl stripped it;
      * it HAS one, but a component was since re-generated and now scores where it did
        not. Tonight's case: 215 companies whose BQ was produced during a degraded
        Ollama window scored below the 6-dimension floor and were re-run. Checking only
        for a missing SG would call every one of them up to date.
    """
    from ..qual.scorer import ciks_with_all_components

    done = ciks_with_all_components()
    out = []
    for path in config.SCORECARD_DIR.glob("*.json"):
        cik = path.name.split("_")[0]
        if cik not in done:
            continue
        card = read_json(path)
        if not isinstance(card, dict):
            continue
        comps = card.get("components") or {}
        ticker = card.get("ticker")
        if not ticker:
            continue
        # SG and BQ are pure judgement. MG is deliberately a mixture - 9.4 of its 15
        # points come from filed data - so it has availability with no LLM at all and
        # cannot be used to tell whether the judgement half landed.
        if ((comps.get("SG") or {}).get("available_points", 0) <= 0
                and _cache_has_any_score(cik, "SG")):
            out.append(str(ticker))
            continue
        # E19 removed the 6-of-11 cliff: ANY cached dimension now buys availability, so
        # a scorecard showing zero while the cache holds one is behind. The old test
        # asked whether the cache cleared the floor, which under E19 would strand every
        # company assessed on one to five dimensions.
        bq_avail = (comps.get("BQ") or {}).get("available_points", 0)
        if bq_avail <= 0 and (_cached_bq_dimensions(cik) or 0) >= 1:
            out.append(str(ticker))
    return sorted(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--print-only", action="store_true",
                    help="write the comma-separated list to stdout and nothing else")
    args = ap.parse_args(argv)

    stale = stale_tickers()

    # A ticker whose CIK cannot be resolved can never be re-scored through --symbols:
    # batch logs "skip: no CIK" and moves on, so the fold reports failure forever with
    # no way to act on it. KMT is the live case - its scorecard is 0000055242_KMT.json
    # but et.cik_for("KMT") returns None. Name it as a DIFFERENT problem needing a
    # different fix, rather than burying it in the stale count.
    from ..sources import edgar_tickers as et
    unresolvable = [t for t in stale if not et.cik_for(t)]
    if unresolvable:
        print(f"WARNING: {len(unresolvable)} stale tickers have no resolvable CIK and "
              f"CANNOT be folded by --symbols: {', '.join(unresolvable)}")
        print("  their scorecards exist, so the CIK lookup is what is broken, not the "
              "company. Fix the ticker->CIK mapping; re-running the fold will not help.")
        stale = [t for t in stale if t not in set(unresolvable)]

    if args.print_only:
        print(",".join(stale))
        return 0

    print(f"{len(stale)} companies have cached judgement scores their scorecard "
          f"does not show")
    if not stale:
        return 0
    print(f"  {', '.join(stale[:20])}{' ...' if len(stale) > 20 else ''}")
    if args.dry_run:
        return 0

    from . import batch as batch_mod

    # The probe gate (>50 symbols needs a probe under 7 days old) exists to stop an
    # unplanned COLD crawl. A fold is not one: every company here already has a
    # scorecard, so its EDGAR and yfinance data is on D:, and the fold measured 0.8 s
    # per symbol on 2026-08-15 against the 3.6 s/company the gate is calibrated for.
    # On 2026-08-16 the gate refused a 99-company fold because the probe had aged out,
    # and the day's judgement scores stayed invisible. Bypass it, but say so in the log.
    if len(stale) > config.PROBE_GATE_SYMBOLS:
        print(f"  bypassing the probe gate: all {len(stale)} are already crawled, "
              f"this re-scores from disk (~0.8s/symbol), it is not a cold crawl")

    # --symbols bypasses the resume manifest, which is the whole point: these companies
    # are already marked done and a tier crawl would skip them.
    rc = batch_mod.main(["--symbols", ",".join(stale), "--i-know"])
    remaining = stale_tickers()
    if remaining:
        # Loud, and non-zero. A fold that leaves scorecards behind their cache is the
        # exact failure this module was written to end - it must never exit 0.
        print(f"ERROR: after folding, {len(remaining)} scorecards are STILL behind "
              f"their cache: {', '.join(remaining[:20])}"
              f"{' ...' if len(remaining) > 20 else ''}")
        return rc or 2
    print("after folding: 0 still stale")
    return 0 if rc == 0 else rc


if __name__ == "__main__":
    raise SystemExit(main())
