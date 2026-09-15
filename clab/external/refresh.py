"""What external research is DUE, and the weekend batch that acts on it.

## Why this exists

`next_refresh_due` has been written by `finalize` and `research_ingest` since the layer
was built, printed on a sheet, and **read by nothing**. There was no query anywhere that
answered "what is stale this weekend", so the field was decoration. This module makes it
load-bearing.

## Weekly JOB, not weekly REFRESH

The job runs every weekend. It does not re-research the book. It selects what is DUE,
because the cadences are not weekly and pretending they are would be expensive and wrong:

- an industry object is `STRUCTURAL` - biotechnology's replication difficulty does not
  change between Saturdays, and rewriting it weekly buys unchanged text;
- **re-judging on unchanged evidence manufactures rank churn that is not signal.** E22
  measured a model-scored block at 0.29 year-over-year stability. Movement produced that
  way arrives in the workbook looking like news.

What genuinely moves weekly is price, multiples and the measured half, and those already
refresh in `CompanyLabCrawl`. This module is for the half that moves on a filing.

## What it can and cannot do

External research needs a Codex session, which cannot be driven from a Scheduled Task. So
the weekend job goes as far as it honestly can and stops: it selects the due set, freezes
a request, writes a prompt, and reports. A human hands that prompt over. **It never
pretends to have researched anything** - a task that "succeeded" without a payload would
be the graceful-degradation failure this repo keeps hitting.

Throughput is `config.REFRESH_WEEKLY_BUDGET`, one number, 115 by default - roughly a
quarterly cadence over a 1,500-company book. Raise it to 200 or 500 and nothing else
changes; the selector takes more off the same ordered list.
"""
from __future__ import annotations

import argparse
import datetime as dt

from .. import config
from .schema import UNKNOWN


def _as_date(v) -> dt.date | None:
    if v is None:
        return None
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def _due_date(explicit, last_seen, refresh_class) -> dt.date | None:
    """When this record next needs looking at.

    An explicit `next_refresh_due` wins. Otherwise the cadence for its `refresh_class`
    is added to when it was last researched. A record with neither is due NOW rather
    than never - never would let a row hide from the queue forever.
    """
    d = _as_date(explicit)
    if d is not None:
        return d
    seen = _as_date(last_seen)
    if seen is None:
        return None
    days = config.REFRESH_DAYS.get(
        str(refresh_class or "").upper(), config.REFRESH_DAYS_DEFAULT)
    return seen + dt.timedelta(days=days)


def due(*, store=None, today: dt.date | None = None, budget: int | None = None,
        filers: dict | None = None) -> dict:
    """The due list, most overdue first, and what the next batch should be.

    Companies never researched are NOT in the due list. They are coverage, not refresh,
    and mixing them would let a refresh run quietly become a coverage run - the two have
    different prompts and different registrations.

    `filers` is the EVENT half, from `earnings_watch.recent_filers()["filers"]`:
    `{ticker: {"form": "10-Q", "filed": "2026-09-08"}}`. A company that has FILED since it
    was last researched jumps the queue whatever its clock says, because the numbers we
    researched are the ones the filing just replaced. A filing OLDER than the research is
    not a jump - we already read it.

    An event jump sorts ahead of everything time-based. A 10-K that landed yesterday is a
    better use of the next batch than a company that drifted one day past its 91.

    Nothing is fetched here. The caller passes filers in, so this stays offline, testable,
    and unable to turn a quiet Saturday into a network failure.
    """
    from .store import ExternalStore

    today = today or dt.date.today()
    budget = config.REFRESH_WEEKLY_BUDGET if budget is None else budget
    st = store or ExternalStore(config.EXTERNAL_DB)

    companies = st.latest_companies()
    with st.connect() as con:
        objects = con.execute(
            "SELECT industry_id, sector_id, next_refresh_due, refresh_class, "
            "last_updated, status FROM industry_intelligence").fetchall()

    co_rows = []
    for row in companies:
        tkr = row.get("ticker")
        iid = row.get("industry_id")
        ver = row.get("research_version")
        nxt = row.get("next_refresh_due")
        cls = row.get("refresh_class")
        seen = row.get("last_research_date")
        filed_on = _as_date((filers or {}).get(tkr, {}).get("filed"))
        researched_on = _as_date(seen)
        # FILED SINCE WE LOOKED: the facts moved, so the clock does not get a vote.
        # Requires a known research date - without one we cannot say the filing is
        # newer, and guessing would queue the same company every week forever.
        event = bool(filed_on and researched_on and filed_on > researched_on)

        d = _due_date(nxt, seen, cls)
        if not event and (d is None or d > today):
            continue
        co_rows.append({"ticker": tkr, "industry_id": iid,
                        "due": d if d is not None else filed_on,
                        "overdue_days": (today - d).days if d is not None else 0,
                        "refresh_class": cls, "research_version": ver,
                        "event": event,
                        "event_form": (filers or {}).get(tkr, {}).get("form") if event
                                      else None,
                        "event_filed": filed_on.isoformat() if event and filed_on
                                       else None})
    # Event jumps first, then most overdue. A filing that landed yesterday beats a
    # company one day past its cadence.
    co_rows.sort(key=lambda r: (not r["event"], -r["overdue_days"], r["ticker"]))

    ob_rows = []
    for iid, sid, nxt, cls, seen, status in objects:
        if str(status or "").upper() == "SUPERSEDED":
            continue
        d = _due_date(nxt, seen, cls)
        if d is None or d > today:
            continue
        ob_rows.append({"industry_id": iid, "sector_id": sid, "due": d,
                        "overdue_days": (today - d).days, "refresh_class": cls})
    ob_rows.sort(key=lambda r: (-r["overdue_days"], r["industry_id"]))

    take = co_rows[:budget]
    batches = [take[i:i + config.REFRESH_BATCH_SIZE]
               for i in range(0, len(take), config.REFRESH_BATCH_SIZE)]
    return {
        "today": today.isoformat(),
        "budget": budget,
        "batch_size": config.REFRESH_BATCH_SIZE,
        "companies_due": len(co_rows),
        "companies_taken": len(take),
        "event_jumps": sum(1 for r in co_rows if r["event"]),
        "event_jumps_taken": sum(1 for r in take if r["event"]),
        "objects_due": len(ob_rows),
        "batches": [[r["ticker"] for r in b] for b in batches],
        "company_rows": take,
        "object_rows": ob_rows,
        "backlog": max(0, len(co_rows) - len(take)),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="What external research is due")
    ap.add_argument("--budget", type=int, default=None,
                    help=f"companies to queue (default {config.REFRESH_WEEKLY_BUDGET})")
    ap.add_argument("--today", default=None, help="YYYY-MM-DD, for testing")
    ap.add_argument("--limit", type=int, default=20, help="rows to print")
    ap.add_argument("--no-events", action="store_true",
                    help="skip the EDGAR filing check (offline / time-only)")
    ap.add_argument("--event-days", type=int, default=None,
                    help="lookback for recent filings (default earnings_watch's)")
    a = ap.parse_args(argv)

    filers = None
    if not a.no_events:
        from .earnings_watch import recent_filers, LOOKBACK_DAYS
        ev = recent_filers(days=a.event_days or LOOKBACK_DAYS,
                           today=_as_date(a.today))
        filers = ev["filers"]
        if not ev.get("feed_ok"):
            # A dead feed must not read as "nothing filed". Say so and carry on with
            # the time-based half rather than silently dropping the event half.
            print("WARNING: EDGAR daily index unreachable - event jumps are NOT applied "
                  "this run. This is not evidence that nothing was filed.")
            for e in ev["errors"][:3]:
                print("   ", e)
            filers = None
        else:
            print("filings seen: %d company(ies) in the last %d days"
                  % (len(filers), a.event_days or LOOKBACK_DAYS))

    plan = due(today=_as_date(a.today), budget=a.budget, filers=filers)
    print(f"as of {plan['today']}   budget {plan['budget']}   "
          f"batch size {plan['batch_size']}")
    print(f"companies due {plan['companies_due']}   taking {plan['companies_taken']}   "
          f"backlog {plan['backlog']}")
    print(f"event jumps  {plan['event_jumps']} due, {plan['event_jumps_taken']} in "
          f"this batch")
    print(f"industry objects due {plan['objects_due']}")
    print()
    if plan["companies_taken"]:
        print(f"{len(plan['batches'])} batch(es):")
        for n, b in enumerate(plan["batches"], 1):
            print(f"  batch {n}: {len(b)}  {','.join(b[:8])}"
                  f"{' ...' if len(b) > 8 else ''}")
        print()
        print("most overdue:")
        for r in plan["company_rows"][:a.limit]:
            tag = ("FILED %s %s" % (r["event_form"], r["event_filed"])
                   if r.get("event") else r["refresh_class"] or "-")
            print("  %-8s %-32s due %s  %4d days  %s" % (
                r["ticker"], r["industry_id"] or "?", r["due"],
                r["overdue_days"], tag))
    if plan["object_rows"]:
        print()
        print("industry objects due:")
        for r in plan["object_rows"][:a.limit]:
            print("  %-40s due %s  %4d days  %s" % (
                r["industry_id"], r["due"], r["overdue_days"],
                r["refresh_class"] or "-"))
    if not plan["companies_taken"] and not plan["object_rows"]:
        print("nothing due. This is a real answer, not a failure - say so and stop.")
    return 0


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(main())
