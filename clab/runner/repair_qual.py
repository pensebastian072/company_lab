"""Run the targeted repair pass over companies whose judgement half has holes.

E15-E18 established what this does and what it is allowed to do. The short version: the
production call gives each component one embedding query and eight chunks, and it declines
a great deal - 70% of the coverage the low-coverage half of the universe is missing is the
LLM abstaining, not EDGAR failing. This asks again, once, with a query per null sub-test,
and keeps the answer only when it arrives with a verbatim quote that verifies.

    python -m clab.runner.repair_qual --limit 100                # the priority slice
    python -m clab.runner.repair_qual --symbols AAT,PBF --components bq
    python -m clab.runner.repair_qual --dry-run                  # selection only, no GPU

Ordering is by distance to a coverage threshold, so the workbook improves fastest per
GPU-hour: companies just under 0.9 first, then the zero-BQ block, then the rest under 0.9.

Resumable by default and checkpointed per company - this box lost power three times while
the experiments behind this were running.
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone

from .. import config
from ..net import atomic_write_json, log_stamp, read_json, utc_now_iso
from ..qual import evidence as ev_mod
from ..qual import ollama, repair
from ..scoring.repair_merge import REPAIRS_KEY, SCORING_GATE, null_items
from . import engine

COMPONENTS = ("SG", "BQ", "MG")
DONE_LOG = config.JOURNAL_DIR / "runs" / "repair_done.txt"
REPORT = config.JOURNAL_DIR / "experiments" / "repair_runs.jsonl"


def log(msg: str) -> None:
    print(f"[{log_stamp()}] {msg}", flush=True)


def payload_path(cik: str, component: str):
    """The file `engine.load_qual` will actually read for this component.

    It takes `sorted(glob)[-1]`, which is the last file by NAME - the pack hash - not the
    newest or the most complete. Writing a repair into any other payload would leave the
    scorer reading one that has none, and the run would look like it worked. So the
    selection is duplicated from `load_qual` deliberately, and `verify_written` re-reads
    through `load_qual` afterwards.
    """
    hits = sorted(config.QUAL_DIR.glob(f"{cik}_{component}_*.json"))
    return hits[-1] if hits else None


def select(limit: int = 0, symbols: list[str] | None = None,
           components: tuple[str, ...] = COMPONENTS) -> list[dict]:
    import pandas as pd
    df = pd.read_parquet(config.SCORES_PARQUET)
    df = df[df["ticker"].notna()].copy()
    df["cik"] = df["cik"].astype(str).str.zfill(10)
    if symbols:
        want = {s.strip().upper() for s in symbols if s.strip()}
        df = df[df["ticker"].str.upper().isin(want)]
        rows = df
    elif tuple(components) == ("BQ",):
        # BQ availability is ALL-OR-NOTHING: 15 points once six dimensions are scored, 0
        # below that. So a BQ-only pass can only move coverage for companies that have
        # none of it. Running it on a company already at 15 recovers dimensions that
        # change no availability at all - which is how a run produces a pile of repaired
        # sub-tests and not one point of coverage.
        zero_bq = df[df["bq_available"] == 0]
        rows = zero_bq.sort_values("coverage", ascending=False)
    else:
        near = df[(df["coverage"] >= 0.85) & (df["coverage"] < 0.9)]
        zero_bq = df[(df["bq_available"] == 0) & (~df["ticker"].isin(near["ticker"]))]
        rest = df[(df["coverage"] < 0.9)
                  & (~df["ticker"].isin(near["ticker"]))
                  & (~df["ticker"].isin(zero_bq["ticker"]))]
        rows = pd.concat([near.sort_values("coverage", ascending=False),
                          zero_bq.sort_values("coverage", ascending=False),
                          rest.sort_values("coverage", ascending=False)])
    out = [{"ticker": r["ticker"], "cik": r["cik"], "name": r.get("name", ""),
            "sector": r.get("sector", ""), "sub_industry": r.get("sub_industry", ""),
            "coverage": round(float(r.get("coverage") or 0), 4),
            "bq_available": int(r.get("bq_available") or 0)}
           for _i, r in rows.iterrows()]
    return out[:limit] if limit else out


def done_keys() -> set[str]:
    """`TICKER:COMPONENT` pairs already repaired.

    Bare tickers were wrong: a BQ-only pass logged 460 of them, and the documented
    default `--components sg,bq,mg` run would then have skipped all 460 and done nothing
    while reporting success. A line with no colon is a pre-fix BQ entry.
    """
    if not DONE_LOG.exists():
        return set()
    out = set()
    for ln in DONE_LOG.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        out.add(ln if ":" in ln else ln + ":BQ")
    return out


def verify_written(cik: str, component: str, keys: list[str]) -> bool:
    """Re-read through the scorer's own loader. A silent no-op here is the whole risk."""
    payload = (engine.load_qual(cik) or {}).get(component) or {}
    have = set((payload.get(REPAIRS_KEY) or {}))
    return set(keys).issubset(have)


def repair_one(row: dict, components: tuple[str, ...], run_id: str) -> dict:
    as_of = utc_now_iso()
    ctx, _meta = engine.build_context(row["ticker"], row["cik"], as_of=as_of,
                                      name=row.get("name", ""),
                                      sector=row.get("sector", ""),
                                      sub_industry=row.get("sub_industry", ""))
    pool = ev_mod.chunk_pool(ctx)
    out = {"ticker": row["ticker"], "cik": row["cik"], "sector": row.get("sector", ""),
           "coverage_before": row.get("coverage"), "run_id": run_id,
           "as_of": as_of, "components": {}}
    for component in components:
        path = payload_path(row["cik"], component)
        if path is None:
            out["components"][component] = {"skipped": "no cached payload"}
            continue
        payload = read_json(path)
        if not isinstance(payload, dict):
            out["components"][component] = {"skipped": "unreadable payload"}
            continue
        nulls = null_items(payload, component)
        if not nulls:
            out["components"][component] = {"skipped": "nothing null"}
            continue
        t0 = time.perf_counter()
        repairs, meta = repair.repair_component(ctx, component, payload, pool,
                                                run_id=run_id)
        if repairs:
            merged = dict(payload.get(REPAIRS_KEY) or {})
            merged.update(repairs)
            payload[REPAIRS_KEY] = merged
            payload["repaired_at"] = utc_now_iso()
            # The coverage this company had BEFORE a second look, recorded at the moment
            # it was read. Reconstructing it later would mean re-scoring with repairs
            # switched off, and a stored number cannot drift out of step with the run.
            payload.setdefault("coverage_before_repair", row.get("coverage"))
            atomic_write_json(path, payload)
            if not verify_written(row["cik"], component, list(repairs)):
                # Loud, because a write the scorer cannot see is a wiring failure that
                # would otherwise present as "the repair recovered nothing".
                raise RuntimeError(
                    f"{row['ticker']} {component}: repairs written to {path.name} are "
                    f"not visible through engine.load_qual - the scorer reads a "
                    f"different payload for this CIK")
        kept = [k for k, r in repairs.items()
                if r.get("score") is not None and r.get("gate") == SCORING_GATE]
        out["components"][component] = {
            "nulls": [k for k, _l, _m in nulls],
            "answered": [k for k, r in repairs.items() if r.get("score") is not None],
            "kept": kept,
            "secs": round(time.perf_counter() - t0, 1),
            "path": path.name,
            "retrieval": meta.get("retrieval", {}),
        }
    return out


def run(rows: list[dict], components: tuple[str, ...], *, resume: bool = True) -> dict:
    run_id = datetime.now(timezone.utc).strftime("repair_%Y%m%dT%H%M%SZ")
    done = done_keys() if resume else set()
    todo = [r for r in rows
            if any(r["ticker"] + ":" + c not in done for c in components)]
    log(f"{len(todo)} companies to repair ({len(rows) - len(todo)} already done), "
        f"components {','.join(components)}, run {run_id}")
    ok, why = ollama.available()
    if not ok:
        log(f"ollama is not usable: {why}")
        return {"ok": False, "reason": why}

    DONE_LOG.parent.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    stats = {"companies": 0, "kept": 0, "answered": 0, "failed": 0}
    t_start = time.perf_counter()
    with ollama.gpu_lease(wait=True):
        for i, row in enumerate(todo, 1):
            try:
                rec = repair_one(row, components, run_id)
            except Exception as exc:                        # noqa: BLE001
                stats["failed"] += 1
                log(f"  {row['ticker']} FAILED: {type(exc).__name__}: {exc}")
                continue
            kept = sum(len(c.get("kept", [])) for c in rec["components"].values())
            answered = sum(len(c.get("answered", []))
                           for c in rec["components"].values())
            secs = sum(c.get("secs", 0.0) for c in rec["components"].values())
            stats["companies"] += 1
            stats["kept"] += kept
            stats["answered"] += answered
            with REPORT.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec) + "\n")
            with DONE_LOG.open("a", encoding="utf-8") as fh:
                for component in components:
                    fh.write(row["ticker"] + ":" + component + "\n")
            log(f"  {row['ticker']:<6} cov {row.get('coverage', 0):.2f}  "
                f"answered {answered:>2}  kept {kept:>2}  {secs:>5.1f}s  "
                f"({i}/{len(todo)})")
    stats["minutes"] = round((time.perf_counter() - t_start) / 60, 1)
    stats["run_id"] = run_id
    write_summary()
    log(f"done: {stats['companies']} companies, {stats['answered']} answered, "
        f"{stats['kept']} kept ({SCORING_GATE} gate), {stats['failed']} failed, "
        f"{stats['minutes']} min")
    return stats


SUMMARY = config.JOURNAL_DIR / "experiments" / "repair_summary.json"


def write_summary() -> dict:
    """Cumulative totals across every repair run, rebuilt from the per-company log.

    The workbook's Findings sheet reads this, so a reader sees how much of the judgement
    half came from a second look - including the part that was offered without a quote
    and therefore scored nothing.
    """
    companies = 0
    answered = kept = 0
    by_component: dict[str, dict] = {}
    if REPORT.exists():
        seen = set()
        for line in REPORT.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            key = (rec.get("ticker"), rec.get("run_id"))
            if key in seen:
                continue
            seen.add(key)
            companies += 1
            for comp, c in (rec.get("components") or {}).items():
                d = by_component.setdefault(comp, {"answered": 0, "kept": 0,
                                                   "companies": 0})
                if c.get("answered") or c.get("kept"):
                    d["companies"] += 1
                d["answered"] += len(c.get("answered") or [])
                d["kept"] += len(c.get("kept") or [])
                answered += len(c.get("answered") or [])
                kept += len(c.get("kept") or [])
    out = {"companies": companies, "answered": answered, "kept": kept,
            "by_component": by_component, "gate": SCORING_GATE,
            "updated_at": utc_now_iso()}
    atomic_write_json(SUMMARY, out)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--symbols", help="comma-separated, overrides the priority order")
    ap.add_argument("--components", default="sg,bq,mg")
    ap.add_argument("--no-resume", action="store_true")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the selection and what is null; no GPU, no writes")
    args = ap.parse_args(argv)

    components = tuple(c.strip().upper() for c in args.components.split(",")
                       if c.strip())
    bad = [c for c in components if c not in COMPONENTS]
    if bad:
        log(f"unknown components {bad}; valid are {COMPONENTS}")
        return 2

    rows = select(args.limit, args.symbols.split(",") if args.symbols else None,
                  components)
    if args.dry_run:
        log(f"{len(rows)} companies selected")
        for r in rows[:20]:
            nulls = {}
            for c in components:
                p = payload_path(r["cik"], c)
                payload = read_json(p) if p else None
                if isinstance(payload, dict):
                    nulls[c] = len(null_items(payload, c))
            log(f"  {r['ticker']:<6} cov {r['coverage']:.2f} bq {r['bq_available']:>2} "
                f"nulls {nulls}")
        return 0

    stats = run(rows, components, resume=not args.no_resume)
    print(json.dumps(stats, indent=2))
    return 0 if stats.get("companies") else 1


if __name__ == "__main__":
    raise SystemExit(main())
