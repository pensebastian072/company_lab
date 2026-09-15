# E27 - the band hysteresis was counting my keystrokes

Registered 2026-08-23, before the fix. Found while validating `--cached-market`, which is
how it should have been found: a run that changed **zero** of 1,500 composite scores moved
**54 bands**.

## The bug

F3 exists because E03 R4 measured raw bands flipping in **27.2% of months** with a median
2-month life. The fix was `BAND_CONFIRM_READINGS = 2`: a band changes only after two
consecutive readings agree.

A "reading" is whatever `advance_band` is called with - **one per invocation of the
scorer**, not one per unit of time. So the smoothing that was meant to represent two
months of market agreement is consumed by any two re-scores, however close together.

**I ran 15 full re-scores in three days.** Every rubric edit - E19, E21, E23, E25, E26 -
advanced every company's hysteresis by one step. The 54 bands that moved on the
`--cached-market` run were all sitting pending from an earlier run of mine, and confirmed
on an identical score: MU to HIGH_CONVICTION, GOOGL down to WATCHLIST, GLW / UBER / BSX /
TPR / LITE up to INVESTABLE, on zero new information.

The band column in the workbook has been advancing on my iteration rather than on the
companies.

## The fix

**A reading is a calendar day, not an invocation.** The scorecard gains
`band_reading_date`; `advance_band` is given the previous reading's date and today's, and
it only advances `streak` when the date differs. Re-scoring the same company twice in one
day is then **idempotent** with respect to the band - which is the property that was
missing and the one worth asserting in a test.

This is deliberately the smallest rule that fixes it. Alternatives considered and
rejected:

* **Count snapshots.** More faithful to "two months of agreement", but snapshots run
  weekly and the qual fill re-scores companies daily, so a pending band could wait weeks.
* **Wall-clock intervals.** Introduces a clock into scoring, which the code is careful to
  keep out - `build_scorecard` is deterministic and takes `as_of` from its caller.

`as_of` is already threaded through every scoring call, so the date is available without
reaching for the clock.

## What this does NOT undo

The 54 confirmations already happened, and earlier re-scores confirmed others I cannot now
identify - the streak state is a single integer on the scorecard with no history behind
it. **Any band change recorded between 2026-08-19 and 2026-08-23 may have been confirmed
by a re-score rather than by two genuine readings.** That is now written into the workbook
Findings sheet rather than left for someone to trip over.

## Pass criteria

| | passes if |
|---|---|
| **H1** | Re-scoring the same universe twice on the same day changes **zero** bands, given zero score changes. This is the bug, stated as a test. |
| **H2** | A genuine change over two different dates still confirms, so the smoothing survives. Unit test on `advance_band` directly. |
| **H3** | The first re-score after the fix changes no bands beyond those explained by score changes. |

## Prediction

H1 and H2 pass - they are properties of a small state machine. H3 is the interesting one:
I expect a handful of bands to still move on the first run because their stored state was
left mid-confirmation by the old rule, and there is no way to distinguish those from
genuine pending changes without a history the scorecards do not carry.
