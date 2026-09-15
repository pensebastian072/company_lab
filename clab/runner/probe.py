"""Timing probe - the gate before any large crawl.

A 6.5-hour run has been wasted on this box for want of five minutes of
arithmetic, so the batch runner refuses a >50-symbol crawl unless a probe report
newer than PROBE_MAX_AGE_DAYS exists. This runs the FULL pipeline on a small
sample, reports per-stage p50/p90, and projects wall clock and disk footprint for
the whole universe.

Usage:
  python -m clab.runner.probe --n 10
  python -m clab.runner.probe --symbols AAPL,JPM,XOM --force
"""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

from .. import config
from ..scoring import rubric
from ..net import atomic_write_json, trust_windows_certs, utc_now_iso, utc_today
from . import batch, engine

STAGES = ("edgar_facts", "edgar_submissions", "normalize", "yf_market",
          "yf_prices", "score_total")


def _p(vals: list[float], q: float) -> float | None:
    if not vals:
        return None
    s = sorted(vals)
    i = min(int(q * (len(s) - 1) + 0.5), len(s) - 1)
    return s[i]


def _dir_bytes(path: Path) -> int:
    try:
        return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    except OSError:
        return 0


def run(n: int = 10, symbols: list[str] | None = None, *, tier: str = config.DEFAULT_TIER,
        force: bool = False, skip_qual: bool = True) -> dict:
    trust_windows_certs()
    if not config.ensure_data_root():
        print(f"FATAL: {config.DATA_ROOT} unavailable")
        return {"ok": False}

    rows = batch.load_universe(tier, force=force)
    if symbols:
        wanted = [s.strip().upper().replace(".", "-") for s in symbols]
        by = {r["ticker"]: r for r in rows}
        sample = [by[s] for s in wanted if s in by]
    else:
        sample = batch.order_universe(rows, "marketcap")[:n]
    if not sample:
        print("FATAL: empty sample")
        return {"ok": False}

    disk_before = _dir_bytes(config.DATA_ROOT)
    print(f"probe: {len(sample)} symbols from {tier} "
          f"({'forced re-fetch' if force else 'cache allowed'})")
    print(f"  {', '.join(r['ticker'] for r in sample)}\n")

    timings: dict[str, list[float]] = {s: [] for s in STAGES}
    results = []
    as_of = utc_now_iso()
    t_all = time.perf_counter()

    for r in sample:
        t0 = time.perf_counter()
        try:
            card, meta = engine.score_symbol(
                r["ticker"], r["cik"], as_of=as_of, name=r.get("name", ""),
                sector=r.get("sector", ""), sub_industry=r.get("sub_industry", ""),
                force=force,
            )
            total = time.perf_counter() - t0
            for stage in STAGES[:-1]:
                v = (meta.get("timings") or {}).get(stage)
                if v is not None:
                    timings[stage].append(v)
            timings["score_total"].append(total)
            results.append({
                "ticker": r["ticker"], "ok": True, "elapsed_s": round(total, 2),
                "composite": card.composite_strict, "quant_50": card.quant_only_50,
                "coverage": round(card.coverage, 3), "band": card.band,
                "profile": card.profile, "data_through": card.data_through,
                "no_data_subtests": card.n_subtests_no_data,
                "warnings": card.warnings[:3],
            })
            print(f"  {r['ticker']:6s} {total:5.1f}s  {card.composite_strict:3d}/{rubric.TOTAL_POINTS}  "
                  f"quant {card.quant_only_50:2d}/{rubric.MEASURED_POINTS}  cov {card.coverage:5.0%}  "
                  f"{card.band}")
        except Exception as exc:  # noqa: BLE001
            total = time.perf_counter() - t0
            results.append({"ticker": r["ticker"], "ok": False,
                            "elapsed_s": round(total, 2),
                            "error": f"{type(exc).__name__}: {exc}"})
            print(f"  {r['ticker']:6s} {total:5.1f}s  FAILED {type(exc).__name__}: {exc}")

    wall = time.perf_counter() - t_all
    disk_delta = max(_dir_bytes(config.DATA_ROOT) - disk_before, 0)
    ok = [r for r in results if r.get("ok")]
    per_symbol = statistics.median([r["elapsed_s"] for r in ok]) if ok else None
    universe_n = len(rows)

    print("\nper-stage seconds (p50 / p90):")
    stage_stats = {}
    for stage in STAGES:
        vals = timings[stage]
        if not vals:
            continue
        stage_stats[stage] = {"p50": round(_p(vals, 0.5), 3), "p90": round(_p(vals, 0.9), 3),
                              "n": len(vals)}
        print(f"  {stage:20s} {_p(vals, 0.5):7.3f} / {_p(vals, 0.9):7.3f}   (n={len(vals)})")

    projection = {}
    if per_symbol:
        quant_minutes = per_symbol * universe_n / 60.0
        projection = {
            "universe_size": universe_n,
            "median_seconds_per_symbol": round(per_symbol, 2),
            "quant_only_minutes": round(quant_minutes, 1),
            "quant_only_hours": round(quant_minutes / 60.0, 2),
            "disk_bytes_per_symbol": int(disk_delta / max(len(sample), 1)),
            "projected_disk_gb": round(disk_delta / max(len(sample), 1)
                                       * universe_n / 1e9, 2),
        }
        print(f"\nprojection for {universe_n} companies (quant only):")
        print(f"  median {per_symbol:.1f}s/symbol -> {quant_minutes:.0f} min "
              f"({quant_minutes / 60:.1f} h)")
        print(f"  disk {disk_delta / max(len(sample), 1) / 1e6:.1f} MB/symbol -> "
              f"{disk_delta / max(len(sample), 1) * universe_n / 1e9:.1f} GB on "
              f"{config.DATA_ROOT}")
        print(f"  NOTE the LLM qualitative half is NOT in this number - measure it "
              f"separately with clab.qual.scorer --probe before scheduling it.")

    coverage = [r["coverage"] for r in ok if r.get("coverage") is not None]
    report = {
        "as_of": utc_now_iso(),
        "date": utc_today(),
        "tier": tier,
        "n_sample": len(sample),
        "n_ok": len(ok),
        "n_failed": len(results) - len(ok),
        "forced": force,
        "skip_qual": skip_qual,
        "wall_seconds": round(wall, 2),
        "stages": stage_stats,
        "projection": projection,
        "median_coverage": round(statistics.median(coverage), 3) if coverage else None,
        "results": results,
    }
    path = config.PROBE_DIR / f"probe_{utc_today()}_{len(sample)}.json"
    atomic_write_json(path, report)
    print(f"\nreport: {path}")
    if coverage:
        print(f"median coverage on the quant half: {statistics.median(coverage):.0%}")
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--symbols")
    ap.add_argument("--tier", default=config.DEFAULT_TIER, choices=config.UNIVERSE_TIERS)
    ap.add_argument("--force", action="store_true",
                    help="ignore caches - measures true cold-start network time")
    ap.add_argument("--with-qual", action="store_true", help="also read the LLM cache")
    args = ap.parse_args(argv)
    r = run(args.n, [s for s in (args.symbols or "").split(",") if s.strip()] or None,
            tier=args.tier, force=args.force, skip_qual=not args.with_qual)
    return 0 if r.get("ok", True) else 1


if __name__ == "__main__":
    sys.exit(main())
