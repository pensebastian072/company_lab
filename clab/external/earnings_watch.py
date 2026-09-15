"""Which companies just FILED, so a refresh can follow the facts instead of a clock.

## Why this exists

`refresh.due()` knows only time: a company comes due 91 days after it was last researched
whether or not anything happened. That is the right default and it is not enough. A 10-K
lands and the company's numbers change that day; waiting out the remaining clock researches
stale facts, and researching a company where nothing filed spends a Codex batch on
unchanged text.

This module supplies the EVENT half. A filing lands, the company jumps the queue.

## One request, not five hundred

EDGAR publishes a daily index of every filing by every filer:

    https://www.sec.gov/Archives/edgar/daily-index/{year}/QTR{q}/master.{yyyymmdd}.idx

**Use master.idx, NOT form.idx.** They carry the same filings and only master.idx is
pipe-delimited; `form.idx` is FIXED-WIDTH. The first draft of this module parsed form.idx
on pipes, matched nothing, and reported "nothing filed" - a silent zero that would have
looked like a quiet market forever. Measured 2026-09-08: master.idx is 366 KB, 4,110 rows,
19 of them 10-K/10-Q on an off-season Tuesday.

Field order is `CIK|Company Name|Form Type|Date Filed|File Name` and the date is
`YYYYMMDD` with no separators. Do not assume it matches form.idx's column order.

Weekends and holidays have no file. **A 404 there is a normal answer, not a failure** -
the caller gets an empty day and must not treat it as an error, or the watcher will
report a problem every Saturday.

## What it does not do

It does not research anything, it does not write the request file, and it does not decide
what a filing means. It maps CIK to ticker and hands `refresh` a set of companies whose
facts moved. Nothing here reaches a broker, a score, or a promotion.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import time

from .. import config

#: The forms that change the numbers we research. A 10-K or 10-Q restates the financials;
#: an 8-K can be anything from a CEO change to a parking-lot sale, so it is deliberately
#: NOT in the default set - it would put most of the book in the queue most weeks.
DEFAULT_FORMS = ("10-K", "10-Q", "10-K/A", "10-Q/A")

#: EDGAR asks for a real contact in the UA and rate-limits on it.
IDX_URL = ("https://www.sec.gov/Archives/edgar/daily-index/"
           "{year}/QTR{qtr}/master.{stamp}.idx")

#: A filing older than this does not jump the queue - it would have been picked up by the
#: ordinary cadence already, and re-queueing it just re-researches settled facts.
LOOKBACK_DAYS = 14

#: Seconds between day requests. SEC rate-limits on the UA and answers 403.
REQUEST_PAUSE_S = 0.4


def _quarter(d: dt.date) -> int:
    return (d.month - 1) // 3 + 1


def index_url(day: dt.date) -> str:
    return IDX_URL.format(year=day.year, qtr=_quarter(day),
                          stamp=day.strftime("%Y%m%d"))


def parse_index(text: str, forms: tuple[str, ...] = DEFAULT_FORMS) -> list[dict]:
    """Rows of {form, cik, company, filed, path} for the forms we care about.

    The .idx body is pipe-delimited after a header block that ends in a line of dashes.
    Anything that does not split into five fields is skipped rather than guessed at.
    """
    wanted = {f.upper() for f in forms}
    out: list[dict] = []
    for line in text.splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) != 5:
            continue
        cik, company, form, filed, path = parts       # master.idx column order
        if form.upper() not in wanted:
            continue
        if not cik.isdigit():
            continue                                   # skips the header row too
        try:
            when = dt.datetime.strptime(filed, "%Y%m%d").date()
        except ValueError:
            continue
        out.append({"form": form, "company": company, "cik": cik.zfill(10),
                    "filed": when, "path": path})
    return out


def fetch_day(day: dt.date, *, forms: tuple[str, ...] = DEFAULT_FORMS,
              fetcher=None) -> dict:
    """One day's filings. A missing file (weekend, holiday) is an EMPTY DAY, not an error.

    Returning an error for a Saturday would make the weekend watcher cry wolf every week,
    and a watcher that cries wolf is one nobody reads.
    """
    url = index_url(day)
    try:
        if fetcher is not None:
            text = fetcher(url)
        else:
            from .. import net
            # http_get returns bytes and already sends the SEC user agent EDGAR
            # requires; it raises HttpError on 404, which is the weekend case below.
            text = net.http_get(url).decode("utf-8", "replace")
    except Exception as exc:                                  # noqa: BLE001
        msg = str(exc)
        # SEC answers 403 FORBIDDEN for a day it never published, not 404. Measured
        # 2026-09-09: Sat 09-05, Sun 09-06 and Labor Day 09-07 all returned 403. Keying
        # the weekend case on 404 alone made the watcher report three errors every week,
        # and a watcher that cries wolf is one nobody reads.
        #
        # A weekday 403 is genuinely ambiguous - not yet published, or rate-limited - so
        # it is reported as unavailable rather than silently swallowed, and
        # `recent_filers` escalates when EVERY weekday in the window is unavailable.
        if "404" in msg or "Not Found" in msg or "403" in msg or "Forbidden" in msg:
            weekend = day.weekday() >= 5
            return {"day": day.isoformat(), "url": url, "rows": [],
                    "trading_day": False,
                    "note": "no index published" if weekend else "index unavailable",
                    "weekday_miss": not weekend}
        return {"day": day.isoformat(), "url": url, "rows": [],
                "trading_day": None, "error": msg}
    return {"day": day.isoformat(), "url": url, "rows": parse_index(text, forms),
            "trading_day": True}


def _cik_to_ticker() -> dict[str, str]:
    """CIK -> ticker from the live book. The book is the authority on what we research."""
    import pandas as pd
    bk = pd.read_parquet(config.SCORES_PARQUET)
    out: dict[str, str] = {}
    for r in bk.itertuples():
        cik = getattr(r, "cik", None)
        if cik is None:
            continue
        digits = re.sub(r"\D", "", str(cik))
        if digits:
            out[digits.zfill(10)] = r.ticker
    return out


def recent_filers(*, days: int = LOOKBACK_DAYS, today: dt.date | None = None,
                  forms: tuple[str, ...] = DEFAULT_FORMS, fetcher=None) -> dict:
    """Companies IN THE BOOK that filed one of `forms` in the last `days`."""
    today = today or dt.date.today()
    mapping = _cik_to_ticker()
    hits: dict[str, dict] = {}
    checked = trading = weekday_misses = 0
    errors: list[str] = []

    for back in range(days):
        day = today - dt.timedelta(days=back)
        if back and fetcher is None:
            # SEC answers 403, not 429, when it decides you are hammering it. The first
            # live run took three 403s in four days without this.
            time.sleep(REQUEST_PAUSE_S)
        res = fetch_day(day, forms=forms, fetcher=fetcher)
        checked += 1
        if res.get("error"):
            errors.append(f"{res['day']}: {res['error']}")
            continue
        if res.get("weekday_miss"):
            weekday_misses += 1
        if res.get("trading_day"):
            trading += 1
        for row in res["rows"]:
            ticker = mapping.get(row["cik"])
            if not ticker:
                continue                       # filer is not in our book
            prev = hits.get(ticker)
            if prev is None or row["filed"] > prev["filed"]:
                hits[ticker] = row

    # Every weekday unavailable is not a quiet market, it is a broken feed. Saying
    # "nothing filed" then would be the graceful degradation this repo keeps hitting.
    if trading == 0 and weekday_misses:
        errors.append(
            f"no index reachable on any of {weekday_misses} weekday(s) - feed is down "
            "or rate-limited; this is NOT evidence that nothing was filed")

    return {
        "today": today.isoformat(),
        "days_checked": checked,
        "trading_days": trading,
        "weekday_misses": weekday_misses,
        "feed_ok": trading > 0,
        "errors": errors,
        "n_filers_in_book": len(hits),
        "filers": {t: {"form": r["form"], "filed": r["filed"].isoformat()}
                   for t, r in sorted(hits.items())},
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Who filed recently, from the EDGAR daily index")
    ap.add_argument("--days", type=int, default=LOOKBACK_DAYS)
    ap.add_argument("--today", default=None, help="YYYY-MM-DD, for testing")
    ap.add_argument("--limit", type=int, default=25)
    a = ap.parse_args(argv)

    today = dt.date.fromisoformat(a.today) if a.today else None
    res = recent_filers(days=a.days, today=today)
    print(f"as of {res['today']}   days checked {res['days_checked']}   "
          f"trading days {res['trading_days']}")
    print(f"companies in the book that filed: {res['n_filers_in_book']}")
    for err in res["errors"][:5]:
        print("  ERROR", err)
    for t, row in list(res["filers"].items())[:a.limit]:
        print("   %-8s %-8s %s" % (t, row["form"], row["filed"]))
    if not res["filers"]:
        print("nothing filed in the window. A real answer, not a failure.")
    return 0


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(main())
