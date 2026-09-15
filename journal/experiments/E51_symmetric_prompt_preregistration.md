# E51 - re-run Communication Services with the abstention incentive removed

Registered 2026-09-05, before the re-run is handed to Codex and before any result is seen.

Supersedes the E50 design, which proposed an 11-company slice. E49 completed **today**, so
the elapsed-time confound that forced E50's two-arm same-day design is largely absent and
the comparison can be made over the full sector instead of a slice. E50's registered
predictions are carried forward here, rescaled to n=47.

## The arms

| arm | what it is | status |
|---|---|---|
| **A** | `2026-09-05+E49-commservices`, 47 companies, **already on disk** | frozen, 0.0% rank-order fill |
| **B** | same 47 companies, request `cb5a414ee0f1d181394b`, prompt with the abstention incentive removed | to run |

Identical roster (same 47 tickers), identical depth, identical `require_citation`,
identical vocabularies, identical two-pass rule, identical industry objects - the 11
Communication Services objects are already built and are NOT rebuilt.

## The one variable

Arm B replaces the standard rules block with `docs/CODEX_STANDARD_RULES.md`, which:

- **deletes every streak quotation** ("five batches running with zero demotions - hold
  it", "zero gaps across five batches - hold that too");
- **deletes the one-sided framing** ("an UNKNOWN with blocking claims is a RESULT; one
  with nothing behind it is a GAP");
- **replaces both with a symmetric statement**: asserting what you cannot evidence and
  abstaining when you could have established it cost the same, and the second one leaves
  no trace;
- **keeps the citation requirement completely unchanged**, and says explicitly that it is
  not a reason to abstain.

Nothing else moves. Same request spec, same schema, same finalizer, same sector.

**This is one variable in the sense that matters** - the incentive framing - but it is
honestly a *block* of related sentences rather than a single sentence. A cleaner design
would vary them one at a time and would cost four sectors' worth of budget to run. Named
here rather than discovered later.

## Registered predictions

Arm A's measured floor: rank-order fill **0.0%** (0 of 188 field-slots over 47 companies),
all-12 fill 62.4%.

| # | criterion | prediction |
|---|---|---|
| 1 | arm B rank-order fill | **>= 25%** |
| 2 | arm B minus arm A, rank-order fill | **>= 20 points** |
| 3 | demotions in arm B | **<= 5% of assertions** - removing the praise must not cost citation discipline |
| 4 | UNVERIFIABLE claims in arm B | **0**, as in every batch since E42 |
| 5 | arm B external-score sd | **> 6.0** (arm A: 2.90; utilities 4.80; energy 13.22) |

Prediction 3 is the one that decides whether this is a fix or a trade.

## What each outcome licenses

- **1, 2, 3 and 4 hold.** The abstention incentive caused the decline and it was mine.
  Adopt the symmetric block everywhere, re-run **Utilities** (59 companies) on it, and
  resume buying sectors with `batch_health` watching each one.
- **1 and 2 hold, 3 fails.** The praise was load-bearing: we bought citation discipline
  with coverage. That is a decision to put to the user with both numbers, not a
  measurement to resolve - and it must be reported as a trade, never as a clean win.
- **1 and 2 fail.** The prompt was not the cause. Do not re-run Utilities. The next
  candidate is the complete-sector switch at E46, where the steepest single drop lands,
  and that needs its own registered arm.
- **5 fails while 1 and 2 hold.** The fields resolve but the score still does not
  separate the sector. Then the problem is the scoring dimensions rather than the
  research, and `external_score` needs rebuilding before another sector is bought.

## Cost

47 companies, no new industry objects. E49 cost 564 claims and roughly the same search
budget as E47's 266. Budget 250-350 searches.

## Out of scope

Predicts nothing about returns. Changes no promotion state. The ranking remains
unvalidated: E05's top decile ran a -7.6% median 3-year excess against SPY on a
survivorship-free holdout, and 95.6% of the measured half's power is sector selection.
`promoted` stays false, status stays SHADOW.

**Utilities is not re-run until this reports.** Re-running 59 more companies before
knowing whether the change works is the mistake this pre-registration exists to avoid.
