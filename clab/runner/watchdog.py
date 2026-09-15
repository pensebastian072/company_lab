"""Did the crawl actually happen, and is what it produced sane?

Reads only published artifacts. Appends findings to journal/runs and exits 0 on
OK / 1 on MISS, so Task Scheduler's last-result column is meaningful. No Telegram:
company_lab holds no secrets and a stale fundamentals crawl is not urgent.

Usage:
  python -m clab.runner.watchdog
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
from datetime import datetime, timezone

from .. import config
from ..net import read_json, utc_now_iso

OK = "OK"
MISS = "MISS"
WARN = "WARN"


#: a qual batch writes into the cache continuously, so the scorecards are LEGITIMATELY
#: behind while one is running. Only complain once the cache has been quiet this long.
QUAL_QUIET_HOURS = 3.0


def _cache_quiet_hours() -> float | None:
    """Hours since the qual cache was last written, or None if it is empty."""
    newest = 0.0
    for p in config.QUAL_DIR.glob("*.json"):
        try:
            newest = max(newest, p.stat().st_mtime)
        except OSError:
            continue
    if not newest:
        return None
    return (time.time() - newest) / 3600.0


def _qual_findings() -> list[str]:
    """The two quiet failures of 2026-08-16, neither of which anything was watching.

    1. Scorecards behind their cache. The daily fold was refused by the probe gate and
       the task still exited 0, so 99 companies' judgement scores stayed invisible to
       the UI, the workbook and every study for a day. The only signal was a log line.
    2. A company scored on a DEGRADED evidence pack. yfinance occasionally fails with
       an HTTP/2 error (curl 16) mid-batch; `_fetch_raw` records it per endpoint rather
       than swallowing it, but `stable_key` is cik+accn+data_through and knows nothing
       about market data, so the company is cached permanently with no price in its
       fact sheet and will never be re-scored on its own.
    """
    out: list[str] = []

    quiet = _cache_quiet_hours()
    if quiet is not None and quiet >= QUAL_QUIET_HOURS:
        try:
            from .fold_qual import stale_tickers
            stale = stale_tickers()
        except Exception as exc:                      # noqa: BLE001 - never break the watchdog
            out.append(f"could not check the qual fold: {type(exc).__name__}: {exc}")
        else:
            if stale:
                out.append(f"{len(stale)} scorecards are behind their cache "
                           f"({', '.join(stale[:5])}...) - the fold did not run or was "
                           f"refused; those judgement scores are invisible")

    corrupt: list[str] = []
    degraded = _companies_without_a_price(corrupt)
    if degraded:
        out.append(f"{len(degraded)} companies have no usable price in their newest "
                   f"market payload ({', '.join(degraded[:5])}) - their cached "
                   f"judgement was scored on a degraded fact sheet")
    if corrupt:
        out.append(f"{len(corrupt)} market payloads are CORRUPT and unreadable "
                   f"({', '.join(corrupt[:5])}) - re-fetch with "
                   f"`batch --symbols {','.join(corrupt[:5])} --force`")
    return out


def _companies_without_a_price(corrupt: list | None = None) -> list[str]:
    """Tickers whose newest market payload carries no usable price.

    `corrupt` collects tickers whose payload could not be read at all - a different
    problem from having no price, and one that needs a re-fetch rather than a re-score.
    """
    out = []
    corrupt = corrupt if corrupt is not None else []
    if not config.YF_DIR.exists():
        return out
    for d in sorted(config.YF_DIR.iterdir()):
        if not d.is_dir():
            continue
        hits = sorted(d.glob("market_*.json.gz"))
        if not hits:
            continue
        try:
            with gzip.open(hits[-1], "rt", encoding="utf-8") as fh:
                payload = json.load(fh)
        except Exception:      # noqa: BLE001
            # Deliberately broad. A TRUNCATED gzip raises zlib.error, which is neither
            # OSError nor ValueError, and it crashed the whole watchdog on 2026-08-16 -
            # a monitoring tool that dies on one bad file reports nothing about the
            # other 1,496. Corrupt payloads are surfaced by name below instead.
            corrupt.append(d.name)
            continue
        info = payload.get("info") or payload.get("fast_info") or {}
        if not isinstance(info, dict):
            info = {}
        if not any(info.get(k) is not None for k in
                   ("currentPrice", "regularMarketPrice", "lastPrice", "last_price")):
            out.append(d.name)
    return out


def check() -> dict:
    findings: list[str] = []
    flag = read_json(config.STATE_FLAG)
    if not flag:
        return {"status": MISS, "reasons": ["no state flag has ever been written"],
                "checked_at": utc_now_iso()}

    as_of = flag.get("as_of")
    age_h = None
    if as_of:
        try:
            when = datetime.fromisoformat(as_of)
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            age_h = (datetime.now(timezone.utc) - when).total_seconds() / 3600.0
        except ValueError:
            findings.append(f"unparseable as_of {as_of!r}")
    if age_h is None:
        findings.append("state flag has no usable as_of")
    elif age_h > config.STATE_STALE_HOURS:
        findings.append(f"last crawl was {age_h:.0f}h ago "
                        f"(threshold {config.STATE_STALE_HOURS}h)")

    if flag.get("status") not in (None, "ok"):
        findings.append(f"crawl status is {flag.get('status')!r}")

    scored = flag.get("symbols_scored") or 0
    failed = flag.get("symbols_failed") or 0
    if scored == 0:
        findings.append("no companies scored")
    if scored and failed / max(scored + failed, 1) > 0.10:
        findings.append(f"{failed} of {scored + failed} companies failed (>10%)")

    cov = flag.get("coverage_median")
    if isinstance(cov, (int, float)) and cov < 0.40:
        findings.append(f"median coverage is only {cov:.0%} - the data spine may be broken")

    if not config.SCORES_PARQUET.exists():
        findings.append("scores.parquet is missing")

    snaps = sorted(config.SNAPSHOT_DIR.glob("scores_*.parquet"))
    if not snaps:
        findings.append("no point-in-time snapshot has ever been written - the "
                        "forward-return grader will have nothing to grade")

    findings.extend(_qual_findings())

    hard = [f for f in findings if "ago" in f or "no companies" in f
            or "missing" in f or "status is" in f or "behind their cache" in f]
    status = MISS if hard else (WARN if findings else OK)
    return {"status": status, "reasons": findings, "age_hours": age_h,
            "symbols_scored": scored, "symbols_failed": failed,
            "coverage_median": cov, "n_snapshots": len(snaps),
            "checked_at": utc_now_iso()}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    res = check()
    line = f"[{res['checked_at']}] {res['status']}"
    if res["reasons"]:
        line += " - " + "; ".join(res["reasons"])
    if not args.quiet:
        print(line)
    try:
        log = config.RUNS_DIR / f"watchdog_{res['checked_at'][:10].replace('-', '')}.log"
        with log.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass
    return 0 if res["status"] in (OK, WARN) else 1


if __name__ == "__main__":
    sys.exit(main())
