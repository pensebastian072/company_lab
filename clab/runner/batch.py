"""The crawler: 10 symbols at a time, checkpointed, resumable, isolated.

Batch size 10 is the user's choice and is the checkpoint granularity. After every
batch the scores table is rewritten, so the dashboard improves while the crawl is
still running rather than staying blank until it finishes.

Failure isolation is per symbol (`except Exception`): one malformed companyfacts
blob cannot kill a 500-name run. Transient failures (5xx, 429, timeout) retry up
to 3 times with backoff; permanent ones (404, missing CIK, parse failure) are
recorded and need --retry-failed or --force to come back.

Usage:
  python -m clab.runner.batch --tier sp500 --resume
  python -m clab.runner.batch --limit 50 --skip-qual        # the fast first pass
  python -m clab.runner.batch --symbols AAPL,MSFT,NVDA --force
  python -m clab.runner.batch --queue                      # drain the earnings queue
  python -m clab.runner.batch --status
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

from .. import config
from ..net import (atomic_write_json, is_transient, log_stamp, read_json,
                   trust_windows_certs, utc_now_iso, utc_today)
from ..scoring import rubric
from ..scoring import va as va_mod
from ..sources import edgar_tickers as et
from ..sources import universe as uni
from ..sources import yf_prices
from . import engine
from .manifest import Manifest, chunked

MARKET_CAP_CACHE = config.UNIVERSE_DIR / "market_caps.json"


def log(msg: str) -> None:
    # Local time with its offset - see net.log_stamp. Stored `as_of` fields stay UTC.
    print(f"[{log_stamp()}] {msg}", flush=True)


# ------------------------------------------------------------------ universe
def load_universe(tier: str, *, force: bool = False) -> list[dict]:
    """[{ticker, cik, name, sector, sub_industry}], deduped by CIK.

    Dual-class listings (GOOG/GOOGL, FOX/FOXA) share one CIK and one set of
    fundamentals. They are deduped to the primary listing so the ranking cannot
    count the same company twice.
    """
    df = uni.fetch_universe(tier, force=force)
    cik_map = et.load_map()
    if df.empty:
        return []
    rows, seen_cik = [], set()
    n_missing_cik = 0
    for _i, r in df.iterrows():
        ticker = str(r["ticker"])
        # NaN IS TRUTHY, so `r.get("cik") or et.cik_for(...)` happily kept a missing
        # value and never consulted the ticker map. The S&P 400 table carries no CIK
        # column at all, so every row became CIK "0000000nan", they all collided, and
        # the dedupe silently reduced 400 companies to ONE.
        cik = _clean_cik(r.get("cik"))
        if cik is None:
            n_missing_cik += 1
            cik = et.cik_for(ticker, mapping=cik_map)
        if not cik:
            log(f"  skip {ticker}: no CIK in company_tickers.json")
            continue
        cik = str(cik).zfill(10)
        if not cik.isdigit():
            log(f"  skip {ticker}: non-numeric CIK {cik!r}")
            continue
        if cik in seen_cik:
            continue
        seen_cik.add(cik)
        rows.append({
            "ticker": ticker, "cik": cik, "name": str(r.get("name") or ""),
            "sector": str(r.get("gics_sector") or ""),
            "sub_industry": str(r.get("gics_sub_industry") or ""),
        })

    if n_missing_cik:
        log(f"  {n_missing_cik} of {len(df)} rows had no CIK in the index page; "
            f"resolved via company_tickers.json")
    # Dual-class dedupe should remove a handful of names (GOOG/GOOGL, FOX/FOXA). Losing
    # most of the universe means the CIKs collided, which is a bug, not a dual listing.
    if len(df) >= 20 and len(rows) < 0.5 * len(df):
        raise ValueError(
            f"CIK dedupe collapsed {len(df)} {tier} companies to {len(rows)}. That is a "
            f"CIK resolution failure, not dual-class listings - refusing to crawl a "
            f"universe that lost more than half its members.")
    return rows


def _clean_cik(value) -> str | None:
    """A usable CIK string, or None. Treats NaN / 'nan' / '' as missing."""
    if value is None:
        return None
    if isinstance(value, float):
        # math.isnan on a float covers the pandas missing-value case
        import math

        if math.isnan(value):
            return None
        value = int(value)
    s = str(value).strip()
    if s.lower() in ("", "nan", "none", "<na>"):
        return None
    return s


def order_universe(rows: list[dict], how: str = "marketcap") -> list[dict]:
    """Descending market cap where known, so batch 1 is the largest names.

    The cap map is populated opportunistically as symbols are scored, so the very
    first crawl on a fresh box falls back to index order and says so. Every crawl
    after that is correctly ordered.
    """
    if how != "marketcap":
        return rows
    caps = read_json(MARKET_CAP_CACHE) or {}
    if not caps:
        log("  market-cap order unavailable on a cold cache - using index order "
            "(the cache fills as symbols are scored)")
        return rows
    known = sum(1 for r in rows if caps.get(r["ticker"]))
    log(f"  ordering by market cap ({known}/{len(rows)} known)")
    return sorted(rows, key=lambda r: -(caps.get(r["ticker"]) or 0))


def _update_cap_cache(updates: dict[str, float]) -> None:
    if not updates:
        return
    caps = read_json(MARKET_CAP_CACHE) or {}
    caps.update({k: v for k, v in updates.items() if isinstance(v, (int, float)) and v > 0})
    try:
        atomic_write_json(MARKET_CAP_CACHE, caps)
    except Exception:  # noqa: BLE001
        pass


# ------------------------------------------------------------------ outputs
def write_scores_table(cards: list[dict]) -> int:
    """Rewrite data/scores.parquet - the only artifact the UI table reads."""
    if not cards:
        return 0
    import pandas as pd

    # Sector-neutral percentiles are inherently cross-sectional - a company's rank
    # against its sub-industry cannot be known while scoring it alone - so they are
    # computed here, over the whole population, rather than per company. Additive:
    # `composite_strict` is untouched and remains the headline.
    from ..scoring import sector_neutral
    sector_neutral.neutralize(cards)

    df = pd.DataFrame(cards)
    if "composite_strict" in df.columns:
        df = df.sort_values("composite_strict", ascending=False)
    df = _sanitize_for_parquet(df)
    try:
        tmp = config.SCORES_PARQUET.with_suffix(".parquet.tmp")
        df.to_parquet(tmp, index=False)
        tmp.replace(config.SCORES_PARQUET)
    except Exception as exc:  # noqa: BLE001 - parquet failure must not lose the crawl
        # LOUD, and it says what it costs. This failed silently for a whole crawl: a
        # single 'Infinity' string in `pe` blocked every write, scores.parquet stayed
        # frozen at 1,139 companies while scores.csv had 1,497, and the run reported
        # success. scores.parquet is what the UI and every study read.
        log(f"  ERROR could not write scores.parquet: {exc}")
        log(f"  ERROR scores.parquet is now STALE - the UI and every study read it. "
            f"scores.csv has the current {len(df)} rows.")
    # CSV alongside it: readable with no dependencies, and the fallback if
    # pyarrow ever breaks.
    try:
        df.to_csv(config.DATA_DIR / "scores.csv", index=False, encoding="utf-8-sig")
    except Exception:  # noqa: BLE001
        pass
    return len(df)


#: values that mean "not a finite number" once a float has been through JSON. Python's
#: json module writes float('inf') as the bare token Infinity, and a round trip can leave
#: it as either a float or this string, which then poisons the whole parquet column.
_NON_FINITE_STRINGS = frozenset({"inf", "-inf", "infinity", "-infinity", "nan",
                                 "+infinity", "+inf"})


def _sanitize_for_parquet(df):
    """Replace non-finite numerics with None so a single bad cell cannot block the write.

    CLAUDE.md already says inf must never reach parquet, and interest coverage is capped
    for exactly this reason. `pe` had no such cap: one company with a zero-or-negative
    EPS produced 'Infinity', pyarrow refused the column, and EVERY write failed for a
    whole crawl while the error was swallowed as a warning.
    """
    import math

    import pandas as pd

    out = df.copy()
    for col in out.columns:
        s = out[col]
        if s.dtype.kind == "f":
            out[col] = s.where(pd.notna(s) & ~s.isin([float("inf"), float("-inf")]),
                               other=None)
        elif s.dtype == object:
            def _clean(v):
                if isinstance(v, float) and not math.isfinite(v):
                    return None
                if isinstance(v, str) and v.strip().lower() in _NON_FINITE_STRINGS:
                    return None
                return v

            out[col] = s.map(_clean)
    return out


def collect_scorecard_rows() -> list[dict]:
    """Flat rows rebuilt from every scorecard on disk (survives a partial crawl)."""
    rows = []
    import time as _time

    now = _time.time()
    for p in sorted(config.SCORECARD_DIR.glob("*.json")):
        d = read_json(p)
        if isinstance(d, dict) and d.get("ticker"):
            row = _row_from_scorecard(d)
            # A company that has left the index keeps its scorecard - E04 showed dropping
            # removed constituents is what created the survivorship bias in the first
            # place - but it stops being re-scored, and a row last written days ago looks
            # identical to one written tonight. AVB and EQR sat in the table at 3.5 days
            # old after their tickers left the S&P 500 lists.
            row["scorecard_age_days"] = round((now - p.stat().st_mtime) / 86400.0, 2)
            rows.append(row)
    return rows


def _row_from_scorecard(d: dict) -> dict:
    from ..scoring import rubric

    row = {k: d.get(k) for k in (
        "ticker", "cik", "name", "sector", "sub_industry", "profile", "as_of",
        "data_through", "price_as_of", "composite_strict", "composite_normalized",
        "composite_ex_entry", "score", "selection_score", "band", "coverage", "quant_only_50", "quant_normalized",
        "quant_band", "quant_coverage", "qual_available", "n_subtests_no_data",
        "points_earned", "points_available",
    )}
    comps = d.get("components") or {}
    for code in rubric.COMPONENT_ORDER:
        c = comps.get(code) or {}
        low = code.lower()
        row[low] = c.get("earned_points")
        row[f"{low}_max"] = rubric.COMPONENTS[code][1]
        row[f"{low}_available"] = c.get("available_points")
        row[f"{low}_is_llm"] = c.get("is_llm", False)
    metrics = d.get("metrics") or {}
    for key in (
        "revenue_ttm", "revenue_cagr_1y", "revenue_cagr_3y", "revenue_cagr_5y",
        "eps_ttm", "fcf_ttm", "gross_margin", "operating_margin", "fcf_margin",
        "margin_trend_bps_yr", "roic", "roe", "fcf_conversion", "net_debt",
        "net_debt_ebitda", "interest_coverage", "current_ratio", "dilution_yoy",
        "stress_verdict", "price", "market_cap", "pe", "fwd_pe", "peg",
        "ev_ebitda", "ev_sales", "p_fcf", "reverse_dcf_implied_growth",
        "reverse_dcf_wacc", "analyst_growth_3y", "drawdown_from_ath",
        # entry v2: the multiple against its own history, and EMA distances by
        # timeframe. These live in the scorecard already - keep this list in step
        # with csv_export.COLUMNS or the workbook silently loses columns.
        "pe_current", "pe_pctile_own", "pe_median_own", "pe_min_own", "pe_max_own",
        "pe_history_n", "pe_history_years",
        # what the targeted repair pass added, and what it offered but could not cite
        "repaired_points_quoted", "repaired_points_unquoted", "repaired_subtests",
        "repaired_subtests_unquoted", "coverage_before_repair",
        # E20 forward DCF - display only, never an input to a score
        "dcf_fair_value", "dcf_margin_of_safety", "dcf_bear", "dcf_bull", "dcf_growth",
        "dcf_growth_basis", "dcf_wacc", "dcf_implausible", "dcf_reason",
        "dcf_shares_basis", "dcf_shares_disputed", "dcf_shares_filed_vs_market",
        "en_best_timeframe_weight", "en_confluence",
        "pct_vs_ema20_daily", "pct_vs_ema72_daily",
        "pct_vs_ema20_weekly", "pct_vs_ema72_weekly",
        "pct_vs_ema20_monthly", "pct_vs_ema72_monthly",
        "ema20_daily", "ema72_daily", "ema20_weekly", "ema72_weekly",
        "ema20_monthly", "ema72_monthly",
    ):
        row[key] = metrics.get(key)
    return row


def write_state_flag(summary: dict, rows: list[dict], *, status: str = "ok") -> None:
    """The flag file sibling repos read. Contract: as_of, data_through, stale."""
    cov = [r.get("coverage") for r in rows if isinstance(r.get("coverage"), (int, float))]
    through = [r.get("data_through") for r in rows if r.get("data_through")]
    atomic_write_json(config.STATE_FLAG, {
        "as_of": utc_now_iso(),
        "data_through": max(through) if through else None,
        "stale": False,
        "status": status,
        "promoted": False,          # never promoted: no forward-return validation exists
        "advisory": config.ADVISORY_BANNER,
        "symbols_scored": summary.get("n_ok"),
        "symbols_failed": summary.get("n_failed"),
        "coverage_median": (sorted(cov)[len(cov) // 2] if cov else None),
        "qual_available": any(r.get("qual_available") for r in rows),
        "n_qual_scored": sum(1 for r in rows if r.get("qual_available")),
        "tier": summary.get("tier"),
        "batches_done": summary.get("batches_done"),
        "batches_total": summary.get("batches_total"),
    })


# ------------------------------------------------------------------ probe gate
def probe_is_fresh() -> tuple[bool, str]:
    hits = sorted(config.PROBE_DIR.glob("probe_*.json"))
    if not hits:
        return False, "no probe report exists"
    d = read_json(hits[-1]) or {}
    when = (d.get("as_of") or "")[:10]
    if not when:
        return False, f"probe report {hits[-1].name} has no as_of"
    from datetime import date
    try:
        age = (date.today() - date.fromisoformat(when)).days
    except ValueError:
        return False, "unparseable probe date"
    if age > config.PROBE_MAX_AGE_DAYS:
        return False, f"newest probe is {age} days old (max {config.PROBE_MAX_AGE_DAYS})"
    return True, f"probe {hits[-1].name} is {age} days old"


# ------------------------------------------------------------------ the crawl
def run(**kwargs) -> dict:
    """Serialise the whole write path, then crawl.

    On 2026-08-16 a qual fill's fold and a second batch ran at once. Both write the same
    scorecards, the same scores.parquet and the same state flag, so seven companies died
    on `<scorecard>.json.tmp`, the parquet failed its atomic rename and declared itself
    STALE, and a completed 302-company run exited 1 on the state-flag write.

    Nothing prevented it: the GPU lease does not apply because neither process touches
    the GPU. This does. It WAITS rather than refusing, because the common case is a
    scheduled task overlapping a manual run and queueing is the useful behaviour; it
    gives up loudly rather than writing concurrently.
    """
    from .lease import advisory_lease

    def _announce(h):
        log(f"waiting for the write lease held by pid {h.get('pid')} "
            f"({h.get('label') or 'unlabelled'}, expires {h.get('expires_at')}) - "
            f"up to {config.WRITE_LEASE_WAIT_MINUTES} min")

    with advisory_lease(config.WRITE_LEASE,
                        minutes=config.WRITE_LEASE_TTL_MINUTES,
                        wait=True,
                        max_wait_minutes=config.WRITE_LEASE_WAIT_MINUTES,
                        label="batch", on_wait=_announce) as held:
        if not held:
            log(f"REFUSING to run: another process has held the write lease for over "
                f"{config.WRITE_LEASE_WAIT_MINUTES} min. Running anyway would corrupt "
                f"scorecards and scores.parquet, which is exactly what happened on "
                f"2026-08-16.")
            return {"ok": False, "error": "write lease held elsewhere"}
        return _run_locked(**kwargs)


def _run_locked(
    *,
    tier: str = config.DEFAULT_TIER,
    cached_market: bool = False,
    symbols: list[str] | None = None,
    limit: int | None = None,
    batch_size: int = config.BATCH_SIZE,
    resume: bool = True,
    force: bool = False,
    skip_qual: bool = False,
    retry_failed: bool = False,
    order: str = "marketcap",
    dry_run: bool = False,
    queue: bool = False,
    i_know: bool = False,
    prefetch_prices: bool = True,
) -> dict:
    trust_windows_certs()
    if not config.ensure_data_root():
        log(f"FATAL: data root {config.DATA_ROOT} is unavailable "
            f"(D: not mounted?). Refusing to write ~2 GB onto the C: spinner.")
        return {"ok": False, "error": "data root unavailable"}

    t_start = time.perf_counter()
    log(f"universe: tier={tier}")
    rows = load_universe(tier, force=force)
    if not rows:
        log("FATAL: empty universe")
        return {"ok": False, "error": "empty universe"}
    by_ticker = {r["ticker"]: r for r in rows}
    log(f"  {len(rows)} companies after CIK dedupe")

    if queue:
        q = read_json(config.EARNINGS_QUEUE) or []
        wanted = [e["ticker"] for e in q if isinstance(e, dict) and e.get("ticker")]
        rows = [by_ticker[t] for t in wanted if t in by_ticker]
        log(f"  earnings queue: {len(rows)} symbols")
    elif symbols:
        wanted = [et.normalize_ticker(s) for s in symbols]
        missing = [s for s in wanted if s not in by_ticker]
        rows = [by_ticker[s] for s in wanted if s in by_ticker]
        # A symbol absent from THIS tier is almost always present in another one, and
        # falling straight through to a bare CIK row hands the engine an empty
        # `sub_industry` - which silently REWRITES the company's profile, because
        # sub-industry is the only thing separating a mortgage REIT from an equity REIT.
        # Measured 2026-08-25: `--symbols NLY,STWD,...` (all sp400/sp600 names) re-scored
        # all nine mortgage REITs as equity REITs, moving NLY's coverage 0.500 -> 0.446.
        # `--symbols` is the documented way to re-score one name, so the same company
        # scored two ways depending on how the crawl was invoked. Search every tier first.
        if missing:
            for other in ("sp500", "sp400", "sp600"):
                if not missing or other == tier:
                    continue
                try:
                    extra = {r["ticker"]: r for r in load_universe(other, force=False)}
                except Exception as exc:  # noqa: BLE001 - a tier fetch must not kill a run
                    log(f"  WARN could not consult {other} for {len(missing)} symbols: {exc}")
                    continue
                found = [s for s in missing if s in extra]
                for s in found:
                    rows.append(extra[s])
                    log(f"  {s} is not in {tier}; taking its classification from {other}")
                missing = [s for s in missing if s not in extra]
        for s in missing:
            cik = et.cik_for(s)
            if cik:
                rows.append({"ticker": s, "cik": cik, "name": "", "sector": "",
                             "sub_industry": ""})
                # LOUD, and it says what it costs: an empty sub_industry is not thin data,
                # it changes which sub-tests the company is even asked.
                log(f"  WARN {s} is in no tier; scoring via its SEC CIK with NO sector "
                    f"or sub-industry - its profile will fall back to the SIC code and "
                    f"may differ from a tier crawl's")
            else:
                log(f"  skip {s}: no CIK")
    else:
        rows = order_universe(rows, order)

    man = Manifest.load(tier=tier)
    universe_tickers = [r["ticker"] for r in rows]
    todo_tickers = universe_tickers if (symbols or queue or force) else man.pending(
        universe_tickers, resume=resume, retry_failed=retry_failed)
    if limit:
        todo_tickers = todo_tickers[:limit]
    todo = [by_ticker.get(t) or next(r for r in rows if r["ticker"] == t)
            for t in todo_tickers]

    if len(todo) > config.PROBE_GATE_SYMBOLS and not i_know:
        ok, why = probe_is_fresh()
        if not ok:
            log(f"REFUSING a {len(todo)}-symbol crawl: {why}.")
            log("  Run `python -m clab.runner.probe --n 10` first (it prints a "
                "projected wall clock and disk footprint), or pass --i-know.")
            return {"ok": False, "error": f"probe gate: {why}"}
        log(f"  probe gate ok: {why}")

    log(f"crawl: {len(todo)} symbols, batch size {batch_size}, "
        f"qual={'not generated' if skip_qual else 'read from cache'} "
        f"(cached scores are always read)")
    if dry_run:
        for i, b in enumerate(chunked(todo, batch_size), 1):
            log(f"  batch {i}: {', '.join(r['ticker'] for r in b)}")
        return {"ok": True, "dry_run": True, "n_symbols": len(todo)}

    batches = chunked(todo, batch_size)
    man.data["batches_total"] = len(batches)
    as_of = utc_now_iso()
    peers = _load_peer_stats()
    sector_stats = _load_sector_stats()
    n_ok = n_fail = 0
    caps: dict[str, float] = {}

    for bi, batch in enumerate(batches, 1):
        tickers = [r["ticker"] for r in batch]
        log(f"batch {bi}/{len(batches)}: {', '.join(tickers)}")

        if prefetch_prices:
            try:
                yf_prices.fetch_prices(tickers, force=force, group_size=batch_size)
            except Exception as exc:  # noqa: BLE001 - prices are one component, not the run
                log(f"  WARN price prefetch failed for this batch: {exc}")

        for r in batch:
            sym = r["ticker"]
            t0 = time.perf_counter()
            try:
                card, meta = _score_with_retry(
                    r, as_of=as_of, force=force, skip_qual=skip_qual, peers=peers,
                    sector_stats=sector_stats)
                engine.write_scorecard(card)
                elapsed = time.perf_counter() - t0
                man.record_success(
                    sym, cik=card.cik, latest_accn=meta.get("latest_accn"),
                    data_through=card.data_through, coverage=round(card.coverage, 4),
                    composite=card.composite_strict, quant_50=card.quant_only_50,
                    band=card.band, elapsed_s=round(elapsed, 2),
                    profile=card.profile,
                )
                mc = card.metrics.get("market_cap")
                if isinstance(mc, (int, float)) and mc > 0:
                    caps[sym] = float(mc)
                n_ok += 1
                log(f"  {sym:6s} {card.composite_strict:3d}/{rubric.TOTAL_POINTS} "
                    f"(quant {card.quant_only_50:2d}/{rubric.MEASURED_POINTS}) cov {card.coverage:.0%} "
                    f"{card.band:17s} {elapsed:5.1f}s")
            except Exception as exc:  # noqa: BLE001 - per-symbol isolation, hard requirement
                n_fail += 1
                man.record_failure(sym, man.entry(sym).get("stage", "unknown"),
                                   f"{type(exc).__name__}: {exc}",
                                   transient=is_transient(exc))
                log(f"  {sym:6s} FAILED {type(exc).__name__}: {exc}")

        man.data["batches_done"] = bi
        man.save()
        _update_cap_cache(caps)
        rows_all = collect_scorecard_rows()
        peers = _refresh_peer_stats(rows_all)
        sector_stats = _load_sector_stats()
        n = write_scores_table(rows_all)
        write_state_flag(man.summary(), rows_all)
        log(f"  checkpoint: manifest saved, scores table has {n} companies")

    summary = man.summary()
    rows_all = collect_scorecard_rows()
    write_scores_table(rows_all)
    write_state_flag(summary, rows_all)
    _write_exports(rows_all)
    elapsed = time.perf_counter() - t_start
    log(f"done: {n_ok} scored, {n_fail} failed, {elapsed / 60:.1f} min "
        f"({elapsed / max(n_ok + n_fail, 1):.1f}s per symbol)")
    return {"ok": True, "n_ok": n_ok, "n_failed": n_fail,
            "elapsed_s": round(elapsed, 1), "summary": summary}


def _score_with_retry(row: dict, *, as_of: str, force: bool, skip_qual: bool,
                      peers: dict, sector_stats: dict | None = None,
                      cached_market: bool = False):
    """Retry transient failures only; permanent ones raise on the first attempt."""
    last: BaseException | None = None
    for attempt in range(config.RETRY_TRANSIENT_ATTEMPTS):
        try:
            return engine.score_symbol(
                row["ticker"], row["cik"], as_of=as_of, name=row.get("name", ""),
                sector=row.get("sector", ""), sub_industry=row.get("sub_industry", ""),
                force=force,
                peers=peers.get(row.get("sub_industry") or row.get("sector") or "", {}),
                sector_stats=(sector_stats or {}).get(row.get("sector") or "", {}),
            )
        except Exception as exc:  # noqa: BLE001
            last = exc
            if not is_transient(exc) or attempt == config.RETRY_TRANSIENT_ATTEMPTS - 1:
                raise
            time.sleep(config.RETRY_BACKOFF_SECONDS[
                min(attempt, len(config.RETRY_BACKOFF_SECONDS) - 1)])
    raise last  # pragma: no cover


PEER_STATS_FILE = config.DATA_DIR / "peer_stats.json"


def _load_peer_stats() -> dict:
    return read_json(PEER_STATS_FILE) or {}


SECTOR_STATS_FILE = config.DATA_DIR / "sector_stats.json"


def _refresh_peer_stats(rows: list[dict]) -> dict:
    stats = va_mod.peer_stats(rows)
    try:
        atomic_write_json(PEER_STATS_FILE, stats)
    except Exception:  # noqa: BLE001
        pass
    # F1: within-sector distributions for the margin and returns metrics. Written
    # separately so a crawl that dies mid-way still leaves the previous ones usable.
    try:
        atomic_write_json(SECTOR_STATS_FILE, va_mod.sector_stats(rows))
    except Exception:  # noqa: BLE001
        pass
    return stats


def _load_sector_stats() -> dict:
    return read_json(SECTOR_STATS_FILE) or {}


def _write_exports(rows: list[dict]) -> None:
    """CSV + xlsx on disk after every completed crawl, so the artifact exists
    even when the UI is down."""
    if not rows:
        return
    try:
        from ..export import csv_export, xlsx_export

        day = utc_today()
        csv_path = config.EXPORT_DIR / f"scores_{day}.csv"
        csv_export.write_csv_file(csv_path, rows)
        log(f"  export: {csv_path}")
        xlsx_path = config.EXPORT_DIR / f"company_lab_{day}.xlsx"
        xlsx_export.write_workbook_file(xlsx_path, rows)
        log(f"  export: {xlsx_path}")
        # Stable names as well as dated ones. The dated files are the archive; these two
        # are what a person opens every week, so the path in a shortcut or a pinned Excel
        # window keeps working instead of pointing at last week's file.
        for stable, dated in ((config.LATEST_XLSX, xlsx_path),
                              (config.LATEST_CSV, csv_path)):
            try:
                shutil.copyfile(dated, stable)
                log(f"  export: {stable} (latest)")
            except PermissionError:
                # Excel locks an open workbook, and Saturday 03:00 is exactly when the
                # file might still be open from Friday. Silently leaving last week's file
                # in place would be the worst outcome - the user would read stale numbers
                # believing they were fresh - so put the refresh beside it under an
                # obvious name and say so.
                pending = stable.with_name(stable.stem + "_PENDING" + stable.suffix)
                try:
                    shutil.copyfile(dated, pending)
                    log(f"  WARN {stable.name} is open in another program, so it still "
                        f"holds LAST run's data. Fresh copy written to {pending.name} - "
                        f"close the file and it will refresh on the next run.")
                except Exception as exc:  # noqa: BLE001
                    log(f"  WARN could not refresh {stable.name} ({exc}); the dated file "
                        f"{dated.name} is still correct")
            except Exception as exc:  # noqa: BLE001 - exports must never fail a crawl
                log(f"  WARN could not refresh {stable.name}: {exc}")
    except Exception as exc:  # noqa: BLE001 - exports are a convenience, not the run
        log(f"  WARN export failed: {exc}")


def show_status() -> None:
    man = Manifest.load()
    print(json.dumps(man.summary(), indent=2))
    flag = read_json(config.STATE_FLAG)
    if flag:
        print("\nstate flag:")
        print(json.dumps(flag, indent=2))
    failed = sorted(man.failed_symbols())
    if failed:
        print(f"\n{len(failed)} failed: {', '.join(failed[:40])}"
              + (" ..." if len(failed) > 40 else ""))
        for s in failed[:10]:
            print(f"  {s}: {man.data['symbols'][s].get('error')}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tier", default=config.DEFAULT_TIER, choices=config.UNIVERSE_TIERS)
    ap.add_argument("--symbols", help="comma-separated tickers instead of the tier")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--batch-size", type=int, default=config.BATCH_SIZE)
    ap.add_argument("--no-resume", action="store_true", help="re-score everything")
    ap.add_argument("--force", action="store_true", help="ignore cache AND manifest")
    ap.add_argument("--cached-market", action="store_true",
                    help="score from the cached yfinance snapshot instead of refreshing "
                         "it. Measured 2026-08-23: yf_market is 76%% of a re-score's "
                         "time, so a run that only re-applies a SCORING change should "
                         "not pay for it. Never use this for the weekly crawl - it "
                         "would freeze prices.")
    ap.add_argument("--skip-qual", action="store_true",
                    help="do not GENERATE the LLM half (batch never does anyway). "
                         "Cached judgement scores are still read and kept - skipping "
                         "the read deleted them from scorecards")
    ap.add_argument("--retry-failed", action="store_true")
    ap.add_argument("--order", default="marketcap", choices=("marketcap", "universe"))
    ap.add_argument("--queue", action="store_true", help="drain the earnings queue")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--i-know", action="store_true",
                    help="bypass the probe gate on a large crawl")
    args = ap.parse_args(argv)

    if args.status:
        show_status()
        return 0

    res = run(
        tier=args.tier,
        symbols=[s for s in (args.symbols or "").split(",") if s.strip()] or None,
        limit=args.limit, batch_size=args.batch_size, resume=not args.no_resume,
        force=args.force, skip_qual=args.skip_qual, retry_failed=args.retry_failed,
        cached_market=args.cached_market,
        order=args.order, dry_run=args.dry_run, queue=args.queue, i_know=args.i_know,
    )
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
