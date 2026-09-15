# E06 — CANNOT BE RUN on the LSE feed. Measured 2026-08-13.

The pre-registration (`E06_insider_signal_preregistration.md`) stands unchanged. This file
records why it was not executed, so that nobody later mistakes an absent result for an
untried idea — and so nobody runs a degraded version and reports it as the study.

## What the catalogue advertises

`insider_trades`: **11,317,197 rows, 2003-12 → 2026-08**. That number is what made this the
"prize" dataset for company_lab in `docs/lse_data_source.md`.

## What is actually reachable

Probed directly against the live API, 15 large-cap symbols
(AAPL MSFT NVDA JPM XOM PLTR FICO PYPL LMT COST UNH KO CVX ORCL CRM):

| | measured |
|---|---|
| deduplicated corporate transactions, all 15 symbols | **486** |
| filing-date span | **2025-09-02 → 2026-02-12** — five months, not 23 years |
| staleness | newest filing is **2026-02-12**; today is 2026-08-13, so the feed is ~6 months behind |
| symbols returning nothing | FICO — one of the three companies the user specifically asked about |
| **open-market purchases (`P-Purchase`) across all 15 symbols** | **4** |

Per-year probe on AAPL: zero rows for every year 2015-2023, two rows in 2024, then data
from 2025. Same shape on MSFT, JPM, XOM, NVDA and PLTR. A no-symbol query for 2020-06
returns zero rows, so this is not a per-symbol quirk.

## Why that kills the study as pre-registered

1. **No forward returns exist.** Data begins 2025-09. A 1-year forward return from the
   earliest signal date lands in 2026-09, which is in the future. The 3-year horizon —
   the one E03 R3 showed the framework actually works at — is impossible by years.
2. **The primary signal has n=4.** S1 is open-market buying by an officer or director.
   Four events across 15 major companies in five months. The pre-registration forbids a
   verdict below 40 date clusters; this is not close.
3. **The benchmark comparison is impossible.** The whole question the user asked — does
   following insiders beat just holding the S&P 500 — is a statement about excess return
   over SPY, and there is no window in which to measure one.

Running it anyway would produce a table of numbers with no evidential content. That is
worse than no study, because the table would survive into the workbook.

## Two ways forward, and the honest recommendation

**Option A — wait.** The feed grows forward. By roughly 2027-09 there would be one year of
1-year forward returns. The 3-year test arrives in 2029. This costs nothing but answers
nothing for years, and it depends on the vendor backfilling the staleness.

**Option B — take Form 4 from SEC EDGAR directly. Recommended.** Form 4 is a public filing.
EDGAR has every one of them back to 2003, free, with no row cap and no vendor
deduplication problem. This repo already has the EDGAR infrastructure: `clab/net.py` rate
limiting, `clab/sources/edgar_facts.py`, and the daily-index approach already verified for
`earnings_watch` — `form.YYYYMMDD.idx` is a single ~1.19 MB request covering every filer
for a day, and past-day index files are immutable so re-scans are free.

The work is a Form 4 XML parser plus an index walker. It is more work than a vendor call,
and it is the only route to a real test. The three data disciplines in the
pre-registration (filing_date not transaction_date; congressional rows excluded;
mechanical transactions separated from discretionary) carry over unchanged — EDGAR Form 4
has no congressional rows at all, which removes one of them for free.

## A real defect found and fixed on the way

The feed **re-ingests the same filing many times**. On AAPL, 4,980 corporate rows collapsed
to **27 real transactions**, and a single transaction — Parekh Kevan, 500 shares,
2025-10-16 — appeared **320 times** under 160 distinct `created_at` values. Only `id`,
`created_at` and (across two genuine transactions) `price`/`securities_owned` varied.

`lse.insider_trades()` now deduplicates on
`LSE.INSIDER_IDENTITY_FIELDS` by default, keeping the earliest `created_at`. Without it any
count-based signal is inflated by roughly 160x, and **S3 "cluster buying (≥3 distinct
insiders)" would have fired on essentially every company** — a fabricated signal that would
have looked strong.

## Pagination, also measured

`offset`, `page`, `from`/`to`, `date_from`/`date_to`, `year` and `sort` are all **silently
ignored** on `/ref/insider_trades`. Only `start`/`end` filter, and they filter on the
**transaction** date. With a hard 5,000-row cap and no paging, the only way to walk history
is a sequence of date windows. Recorded in the `lse.py` docstring.

## Status

E06 is **BLOCKED, not failed**. No hypothesis was tested; nothing is promoted. The
pre-registration is untouched so the disciplines survive intact for whichever source
eventually supplies the data.
