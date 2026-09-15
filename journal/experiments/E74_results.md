# E74 — earnings-triggered refresh: the EVENT half of the weekly cycle

Built and verified 2026-09-09. Advisory / SHADOW; nothing here scores, ranks or promotes.
`promoted` is false and no code path sets it true.

## What it does

`refresh.due()` knew only time: a company came due 91 days after it was last researched
whether or not anything happened. That is the right default and it was not enough — a 10-K
lands and the numbers we researched are the ones the filing just replaced.

`clab/external/earnings_watch.py` reads the EDGAR daily index and `refresh.due(filers=...)`
lets a company that has **filed since it was last researched** jump the queue whatever its
clock says. Event jumps sort ahead of everything time-based: a 10-K that landed yesterday
is a better use of the batch than a company one day past its 91.

One request covers every filer. `master.20260908.idx` is 366 KB and 4,110 rows, against
500 per-symbol polls for the same answer.

## Two live defects found by asserting the inputs, not by trusting a green run

Both would have failed **silently**, reporting "nothing filed" — indistinguishable from a
quiet market.

**`form.idx` is fixed-width; only `master.idx` is pipe-delimited.** The first draft parsed
`form.YYYYMMDD.idx` on pipes and matched **zero rows against an 800 KB file full of them**.
`master.idx` also uses a different column order — `CIK|Company|Form|Date|Path` — and a
`YYYYMMDD` date with no separators.

**SEC answers 403, not 404, for a day it never published.** Measured: Saturday 09-05,
Sunday 09-06 and Labor Day 09-07 all returned 403. Keying the weekend case on 404 alone
would have reported three errors every single week, and a watcher that cries wolf is one
nobody reads. A weekday 403 stays ambiguous — unpublished or rate-limited — so it is
recorded as unavailable, and if **no** weekday index is reachable the run says so
explicitly instead of claiming a quiet market.

## Verification — a zero that was proved rather than assumed

The live run reports **59 filers in 14 days and 0 event jumps.** That is the correct
answer, and the reason is not the obvious one.

| ticker | filed | last researched | jump? |
|---|---|---|---|
| JKHY | 2026-08-28 | 2026-09-02 | no — already read |
| OKTA | 2026-08-27 | 2026-09-02 | no — already read |
| REX | 2026-09-03 | 2026-09-04 | no — already read |
| WLY | 2026-09-04 | 2026-09-05 | no — already read |

Only 4 of the 59 filers have current research at all, and **every one filed BEFORE it was
researched** — the research already read those filings. The other 55 are unresearched, so
they are coverage work, not refresh work, and `refresh.due()` deliberately excludes them.

My first explanation for the zero was "they are all unresearched." **That was wrong** —
WLY, JKHY, OKTA and REX are researched. The real reason is the filing-older-than-research
rule doing its job, which is a better answer and only surfaced by checking.

Known-positive check, because a zero must be shown able to be non-zero: a researched
company given a synthetic filing dated today produces exactly **1** jump carrying its form
and date; the same company with a 2020 filing produces **0**.

## Guards, each on a case that actually occurred

- **A filing older than the research does not jump.** The four rows above are the live
  case, not a hypothetical.
- **A company with no known research date cannot jump.** Without one we cannot say the
  filing is newer, and guessing would re-queue that company every week forever.
- **A dead feed does not read as "nothing filed."** Verified against a future date where
  SEC returns 503 on every day: the run warns, drops the event half, and still runs the
  time half.
- **8-K is not in the default forms.** It can be a CEO change or a parking-lot sale, and
  including it would put most of the book in the queue most weeks.

`due()` fetches nothing itself — the caller passes filers in — so the selector stays
offline and testable, and a quiet Saturday cannot become a network failure.

## Wired into the weekend

`CompanyLabExternalRefresh` (Saturday 13:00) runs `clab.external.refresh` with no
arguments, and events are **on by default** (`--no-events` opts out). Verified end to end
through the scheduled path, not just the CLI: exit 0, log shows `filings seen: 52
company(ies) in the last 14 days`.

Manual any time:

```powershell
Start-ScheduledTask -TaskName CompanyLabExternalRefresh
powershell -File scripts\run_clab.ps1 -Task refresh
```

## What E74 does not do

It does not research anything, does not write the request file, and does not decide what a
filing means. It says which companies' facts moved. A human still hands the batch to
Codex.

**E74 is complete.** The standing weekly cycle now has both halves: time from
`refresh_class`, events from EDGAR.
