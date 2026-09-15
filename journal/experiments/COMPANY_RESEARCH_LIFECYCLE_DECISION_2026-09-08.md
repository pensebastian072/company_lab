# Company research lifecycle decision

Date: 2026-09-08

Status: SHADOW / instrument decision

Promoted: false

## Decision

Rejected company-research arms are retired operationally and retained evidentially.
`company_external` mirrors the existing industry-object lifecycle with four additive
columns:

- `status`
- `superseded_by`
- `superseded_reason`
- `superseded_at`

`SUPERSEDED` is the only retirement state introduced. Existing null status remains the
active state, so the migration does not reinterpret earlier accepted rows.

An explicit `store.companies(research_version)` call continues to return every row in a
retired arm. Its claims and manifest remain in the catalog. Unscoped operational readers
call `store.latest_companies()`, which removes SUPERSEDED rows before choosing the latest
row per ticker. If a newer run was burned, the company therefore falls back to its most
recent accepted research rather than disappearing or using rejected evidence.

## Batch-health baseline ruling

**A burned arm is excluded from `batch_health`'s baseline by default.**

The gauge asks whether a new batch answers less than the accepted research preceding it.
A rejected arm is evidence about process failure, but it is not a defensible reference
population. Leaving it in could flatter or condemn the next batch solely because the
known-bad arm happened to answer more or less.

The named batch under test remains an explicit read even if it is SUPERSEDED. For audit,
`include_superseded_baseline=True` reproduces the contaminated comparison. The default
baseline is one latest non-superseded row per ticker strictly before the target version.
This also prevents a repeatedly researched ticker from receiving extra baseline weight.

## Lifecycle invariants

1. No company row, claim or manifest is deleted.
2. A reason is mandatory; a version cannot supersede itself.
3. A named replacement is checked to exist before the command applies.
4. Re-ingesting the same `(ticker, research_version)` cannot clear lifecycle columns.
5. The command is dry-run by default and emits before/after store hashes, target row and
   claim counts, and the full corpus verification-status tally.
6. Applying the same transition twice is idempotent and does not rewrite its timestamp.

## Consumers changed on Chat A's side

- `clab.external.refresh` now obtains the current one-row-per-company corpus from the
  store accessor instead of implementing its own latest-row rule.
- `clab.external.batch_health` uses explicit target rows and the latest accepted
  pre-target baseline. Its history excludes retired arms unless audit mode requests them.

Chat B's readers are not edited in this change. They can replace their temporary dedupe
with `store.latest_companies()` without re-deriving lifecycle semantics.

## Live pre-application receipt

Read from `D:\company_lab_data\external\external_intelligence.duckdb` immediately before
the lifecycle implementation was applied:

| Measure | Value |
|---|---:|
| Store SHA-256 | `709fb491e14e813197354baca6902b4a75c6674db867984aa6c0f6b581462de5` |
| `company_external` rows | 481 |
| Distinct researched tickers | 328 |
| Corpus VERIFIED_LOCAL claims | 6,271 |
| Corpus UNVERIFIABLE claims | 64 |
| Corpus SELF_ATTESTED claims | 58 |

Target to retire:

- research version `2026-09-08+E59-financials-phaseb-b1`
- request `0f796aae25b60d4865e5`
- 43 company rows
- 552 VERIFIED_LOCAL claims

Accepted replacement:

- research version `2026-09-08+E59-financials-phaseb-b1-rerun`
- request `3ff6f3aa0f3608c2f126`
- 43 company rows
- 550 VERIFIED_LOCAL claims

The lifecycle transition does not change any of those claim counts. Its reason is:

> E59 batch 1 rejected: ERIE/WTW peer-evidence attribution defect; replaced by the
> verified batch-1 rerun.

## Live application receipt

The additive migration changed the store hash from the pre-application value above to
`24e9c299f8d31c6ae3ac249259a6dd445ddbdfde49c01c0e3da48daf90a02a10`. The default
dry-run then returned that same hash before and after and resolved exactly 43 active
target rows, 43 distinct tickers and 552 VERIFIED_LOCAL claims.

Applying the transition changed all 43 target rows from active/null status to
`SUPERSEDED`:

| Receipt | Value |
|---|---|
| Store SHA-256 before lifecycle write | `24e9c299f8d31c6ae3ac249259a6dd445ddbdfde49c01c0e3da48daf90a02a10` |
| Store SHA-256 after lifecycle write | `304baf51f19197fd019b3931eb48dc4612400c290f1dee8de7008bf2d9fde400` |
| Rows changed | 43 |
| Explicit burned-version read | 43 rows, all `SUPERSEDED` |
| Latest operational selection | 328 rows, 328 distinct tickers |
| Superseded rows in operational selection | 0 |
| Claims after transition | 6,271 VERIFIED_LOCAL; 64 UNVERIFIABLE; 58 SELF_ATTESTED |

The command was applied a second time with the identical target, replacement and reason.
It changed zero rows and left the SHA-256 at
`304baf51f19197fd019b3931eb48dc4612400c290f1dee8de7008bf2d9fde400`, confirming the
live transition is idempotent.

`batch_health` then read the accepted replacement version as 43 companies and returned
`OK`: rank-order fill 0.820, clean baseline fill 0.654, pooled delta +0.165 and
within-regional-banking delta +0.377. The superseded batch remains available only through
an explicit version or audit-inclusive read.

## Scoring and promotion

This decision changes which company-version row unscoped readers regard as current. It
does not edit a categorical, rescore a company, delete evidence, or authorize promotion.
All results remain SHADOW.
