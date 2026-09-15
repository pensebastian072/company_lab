# Roadmap to E75, and what happens after

Measured 2026-09-07 from `scores.parquet` and the live store, not estimated.

> **Progress note 2026-09-08:** Financials batch 1 accepted 43 companies and 550 verified
> claims. The live store now has 328 distinct researched tickers and 6,393 claims (6,271
> VERIFIED_LOCAL, 64 UNVERIFIABLE, 58 SELF_ATTESTED). The original snapshot below is
> retained rather than overwritten.

```
book                     1,500 companies
researched                 285 (19.0%)
remaining                1,215
Phase A rounds left          6 sectors needing industry objects
company batches left       ~32 at 43 per batch
active industry objects     66
corpus                   5,291 claims - 97.30% VERIFIED_LOCAL, 1.61% UNVERIFIABLE
```

Energy, Utilities and Communication Services are complete. Health Care has objects but no
companies. Financials has objects and batch 1 requested.

---

## Phase 1 — coverage, E59 to E72

One E per sector-phase. Phase A builds industry objects (Chat A); Phase B researches
companies in stratified batches (Chat B). The batch count is `ceil(remaining / 43)`.

| E | sector | phase | size | owner | state |
|---|---|---|---|---|---|
| E59 | Financials | B | 4 batches / 169 | B | batches 1-2 accepted; **batch 3 staged and unhanded** - Codex has no token budget (`8a545f4`) |
| ~~E60~~ | Health Care | B | 4 batches / 163 | B | **BLOCKED** - objects retired for B4; re-research is E76, its Phase B follows at E77 |
| ~~E61~~ | Industrials | A | 25 objects | A | **SUPERSEDED** - 20 of 27 objects retired by the completeness gate; re-research is **E79**, prompt written `544f14c` |
| E62 | Industrials | B | 7 batches / 259 | B | largest sector in the book; **blocked behind E79** |
| E63 | Consumer Discretionary | A | **28 objects** | A | most objects of any sector; the 27 here was understated - see the measured table below |
| E64 | Consumer Discretionary | B | 5 batches / 193 | B | |
| ~~E65~~ | Information Technology | A | 17 objects | A | **DONE** - 17 active, mixed units split (`341d676`), stance adjudicated (`522806e`) |
| E66 | Information Technology | B | 5 batches / 175 | B | Phase A is clear; waits only on a free Phase B slot |
| E67 | Real Estate | A | **16 objects** | A | the 14 here was understated; 1 already exists (`datacenter_reits`, 2026-09-01) |
| E68 | Real Estate | B | 3 batches / 103 | B | |
| E69 | Materials | A | 16 objects | A | |
| E70 | Materials | B | 2 batches / 77 | B | |
| E71 | Consumer Staples | A | 11 objects | A | |
| E72 | Consumer Staples | B | 2 batches / 75 | B | |
| E76 | Health Care | A | 11 objects | A | re-research, prompt written `9a07f9d` |
| E79 | Industrials | A | 27 objects | A | re-research, prompt written `544f14c` |

> **Object counts re-measured 2026-09-10** from `taxonomy.industry_members` over
> `scores.parquet`, because two of the numbers above were written from an estimate and a
> Phase A prompt built on them would under-build:
>
> | sector | companies | units today | this table said | singletons | unmapped |
> |---|---:|---:|---:|---:|---:|
> | Consumer Discretionary | 193 | **28** | 27 | 4 | 0 |
> | Real Estate | 105 | **16** | 14 | 1 | 0 |
> | Materials | 77 | 16 | 16 | 4 | 0 |
> | Consumer Staples | 75 | 11 | 11 | 0 | 0 |
>
> Both E79 and E76 now carry the `key_metrics` / `structural_growth` evidence standard
> (`0ddf584`), so a Phase A run after this date is held to it and E65's two weak fields
> should not repeat.

**Sequencing rule: a sector's Phase A must land and be verified before its Phase B is
requested.** A company researched against a missing or wrong industry object has to be
re-researched, and E56 is the proof — three buckets were re-cut *before* 170 companies were
researched against them, which is the only reason that cost five objects instead of 170
companies.

**Do not run two Phase B campaigns at once.** One request file, one owner.

Small item with no E of its own: **ALRM**. It is Alarm.com, home-security software,
carried into Financials by an error in the book's *sector* data. It is deliberately blocked
rather than papered over with an industry override, and it stays blocked until the sector
field is fixed. One company.

---


### Decision 2026-09-09 - Health Care moves to the end

The 11 Health Care objects were retired for B4. Re-research is **E76**, scheduled after the
standing cycle rather than now, and its Phase B follows at **E77**.

**The book is therefore no longer complete at E75.** 163 Health Care companies - 11% of the
book - stay unresearched through E75. Exit criterion 1 is met at E77. Everything else in
this roadmap still lands at E75.

The evidence is not fabricated: all 66 claims remain VERIFIED_LOCAL across 31 URLs and 5
independence domains. The defect is field assignment - exactly 11 claims per field across 6
fields, one per object per field, with `replication_difficulty` carrying zero direct
support in any of the 11. The 11 direct-support claims are kept as seeds for E76.

## Phase 2 — the review backlog, E73

`docs/AUDIT_2026-09-07_FIX_PASS.md`. A1–A6, B1, B2 and B5 are committed. What remains:

- **The unrecorded scoring change (Chat A, first).** The A1 fix moved a fetched-but-
  unreadable payload from `SELF_ATTESTED` to `UNVERIFIABLE`, and `score.py` drops
  `UNVERIFIABLE` from the usable denominator. 81 claims left scoring across **28 companies
  and 4 industry objects**. Re-score, report what moved, and register the doctrine change
  as a decision.

  > **CLOSED twice over, confirmed 2026-09-10.** The doctrine was registered in
  > `A1_UNVERIFIABLE_SCORING_DECISION_2026-09-08.md` (`d2dcbda`), which also corrected the
  > counts quoted above — 27 tickers and three industry objects plus one sector object, not
  > 28 and 4. The follow-on apply landed in `1e72f5c`. A dry recompute of every record on
  > 2026-09-10 returns **523 of 523 identical, 0 that would newly score, 0 disagreements,
  > 0 scores lost**, so it also stayed closed through the blanking (`22e290c`) and the FDIC
  > wiring (`db7d5c2`), both of which landed after that apply. Nothing left to re-score.
- **Three stale journals.** `E54_results.md`, `E56_registered.md`, `E56_results.md` carry
  a corrected rate of **0.134%** where the store says **1.607%**. Written by Codex, so
  under Rule 4 they are unowned — the user decides before either session commits them.

  > **Resolved before 2026-09-10.** All three now carry the dated correction quoting every
  > rate the figure has been given (0.077 / 0.134 / 1.607 / 1.22 / 0.980%) and the stable
  > count of 64 UNVERIFIABLE claims. Nothing left to decide.
- **B3** — E53 moat-trajectory and value-capture evidence quality. **CLOSED 2026-09-08** - reproduced in
  `AUDIT_2026-09-08_B3_E53_EVIDENCE_REPRODUCTION.md`, remediated by
  `B3_B4_REMEDIATION_DECISION_2026-09-08.md`, E53 retired whole; all 59 rows carry
  `status=SUPERSEDED` in the store. Rate quantified and the cross-version check run
  2026-09-10 in `B3_RATE_AND_CROSS_VERSION_2026-09-10.md`, which found the same defect
  **live in E46 energy for 12 companies**.
- **B4** — E57 citations assigned to fields mechanically.
- **B6** — recount overstated totals: answered-field counts, search counts, endpoint
  coverage, the E57 test count.
- **B7** — the historical items: P/E availability, EMA extra-period delay, the −35% price
  filter removing genuine crashes, stock-vs-SPY sample mismatch, index membership not
  enforced per company-month, E11/E13 portfolio reweighting.
- **B8** — E02 results file is a later rerun while its addendum discusses the original.

**Every one of these is unreproduced.** Reproduce before fixing. Do not "fix" a finding
nobody has confirmed — that is how a correct number gets replaced by a wrong one, and A1
is the worked example: I escalated a real single defect into a false class of 154 by
checking a cache without checking its consumer.

Also open from E58: **arm A is decided and written** (REFUTED at exactly the registered
boundary, 1 of 10, verdict turning on a single object), and **arm B is not testable** until
Phase B has its own `research_version`.

---

## Phase 3 — standing operation, E74 and E75

**E74 - COMPLETE 2026-09-09.** See `journal/experiments/E74_results.md`.
`earnings_watch.py` reads the EDGAR daily index and `refresh.due(filers=...)` lets a
company that filed since it was last researched jump the queue. Wired into
`CompanyLabExternalRefresh` and verified end to end through the scheduled path, events on
by default. Two silent defects were found on the way - `form.idx` is fixed-width where
only `master.idx` is pipe-delimited, and SEC answers 403 rather than 404 for an
unpublished day - both of which would have reported "nothing filed" forever.

**E74 as originally scoped -** Earnings dates on a right-hand
sheet, one to two years out. EDGAR daily index (`form.YYYYMMDD.idx`): one 1.19 MB request
covers every filer and yields ~418 10-K/10-Q rows a day, against 500 per-symbol polls. A
filing lands, that company jumps the refresh queue.

**E75 — the first full standing weekly cycle, and the build-out is done.** Everything below
already exists and only needs to run end to end with full coverage behind it:

- `CompanyLabCrawl` Sat 03:00 — the measured half.
- `CompanyLabSnapshot` Sat 12:00 — the point-in-time record. Cannot be backfilled.
- `CompanyLabExternalRefresh` Sat 13:00 — selects what is due, writes a batch, stops.
  Manual any time: `Start-ScheduledTask -TaskName CompanyLabExternalRefresh`.
- Throughput is one number: `config.REFRESH_WEEKLY_BUDGET`, currently 115. 200 or 500 needs
  no other edit.
- The workbook: rankings first, back end right, external layer folded in with freshness
  columns.

---

## After E75 — what is genuinely left, and what no amount of E's can close

**Deferred here by the user on 2026-09-09: re-research `pricing_power` for the 47
comm-services companies and `technology_risk` for the 59 utilities.** Both fields were
blanked to UNKNOWN that day after a full adjudication found the labels were not reading
their evidence — 26 of 47 `pricing_power` quotes are a different economic sense of the
token ("option-pricing model", transfer pricing, debt repricing), and 45 of 59
`technology_risk` quotes are Item 1C Cybersecurity governance boilerplate that every
utility files identically. 212 rows moved, mean −3.03, and no company fell under the
coverage floor. It is parked behind the coverage campaign deliberately: UNKNOWN is honest
in the meantime and Codex budget has first call through E75. See
`journal/experiments/KEYWORD_RETRIEVAL_2026-09-09.md`, including the two conditions that
re-research must meet.

**Still unbuilt:** `clab/thesis/` — the thesis scorecard and the INTACT / UNCERTAIN /
BROKEN tri-state. Its central rule is already decided and needs a named test: **price is
not an input to the status.** The point is to separate "the stock changed" from "the
company changed".

**The gate that is not an engineering problem.** The forward-return grader needs ~50 weekly
snapshots. There are **7**, oldest 2026-08-09. That is roughly **ten months of wall clock**
and it cannot be backfilled — grading on restated data is look-ahead bias, which is why it
was deferred rather than faked.

So the research layer finishes around E75. The question of whether this ranking *works*
does not, and it will not be answerable before mid-2027 at the earliest, and only if the
snapshots keep running every Saturday.

**Say this plainly whenever the roadmap is summarised:** E05 measured the top decile at
**−7.6% median 3-year excess** against SPY on a survivorship-free holdout, only 45.3% beat
SPY, and E03 put **95.6%** of the ranking's power in sector selection. Finishing coverage
buys completeness and honest infrastructure. It does not buy a validated model, and nothing
in this roadmap is a path to one.

`promoted` is false everywhere, no code path sets it true, and that stays true through E75.

---

## Exit criteria for "built out"

1. All 1,500 companies researched, or explicitly blocked with a written reason (ALRM is
   the only one so far).
2. Every active industry object current, none SUPERSEDED-and-serving.
3. The audit backlog closed or explicitly refused, each with a reproduction.
4. Two consecutive weekends where the refresh selector queues, a batch is researched, and
   the workbook updates without hand-holding.
5. `earnings_watch` moving at least one company into a batch on its own.

Nothing in that list mentions predictive power, on purpose.
