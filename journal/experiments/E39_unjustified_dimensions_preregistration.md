# E39 — a score with no reason beside it: the `rationale: null` moat dimensions

Registered 2026-08-30, before the counterfactual was computed. Item 4 of
`docs/TOMORROW.md`, surfaced by E36's degeneracy check.

## The defect

Production's judged half commits **2,185 moat-dimension scores with no justification at
all** — `rationale` is the literal string `null` (1,754), `Null` (128) or empty (303) —
out of 10,178 scored dimensions. **21.5%**, all of it BQ, across **395 companies**.

This is not the candidate model's doing and has nothing to do with the v2 lane. It is a
v1 data-quality defect that E36's instrument happened to expose, and it sits underneath
`bq_moat`, which is 15 of the framework's 94 points and is scored

    BQ = round(mean(scored dimensions) / 5 * 15),   requiring >= 6 of 11 scored

so an unjustified dimension is not inert: it moves the mean and it counts toward the floor
that decides whether the company is scored on moat at all.

The dimension-level rationales are **not rendered** anywhere — not in the UI, not in the
workbook's Subtests sheet, which carry only `bq_moat`'s own summary rationale. So nobody
has been reading `null` on screen. They have been reading a moat score partly built from
dimensions the model declined to explain.

## The question, and what is NOT being decided

**Measurement only.** Nothing is rescored and no rule changes. The question is what it
would cost to require a reason:

> If every dimension with no rationale were treated as unscored, what happens to `bq_moat`,
> to the 6-of-11 floor, to coverage, and to bands?

Whether to *enforce* that is the user's call, not this experiment's — it is a framework
change, it is discontinuous at a date, and hard rule 9 means it lands in the middle of the
snapshot series the forward-return grader needs. E39 exists so that call is made against
numbers.

## Registered predictions

| # | criterion | prediction |
|---|---|---|
| **P1** | Mean 0-5 score of unjustified dimensions vs justified ones | **Unjustified are LOWER by at least 0.5.** A model with nothing to say scored low and did not bother writing why. **If so, dropping them RAISES BQ** — requiring a reason would make the framework more generous, which is the uncomfortable direction and the reason to register it first. |
| **P2** | Companies falling below the 6-of-11 floor if unjustified dimensions are dropped | **< 60.** The defect concentrates in companies that also have justified dimensions. |
| **P3** | Companies whose band changes | **< 40.** |
| **P4** | Mean `bq_moat` delta over the 395 affected | **between 0 and +1.5 points** of 15, following P1's direction. |

## What each outcome means

* **P1 confirmed** — "no rationale" is a *low-confidence low score*, and the current
  treatment is charging companies for the model's silence. That is the same shape as
  E34's buyback finding and the opposite of what "enforce rigour" sounds like.
* **P1 falsified (unjustified dimensions score the SAME or higher)** — the empty rationale
  is a formatting slip, not a judgement signal, and the cheapest fix is to stop writing
  `null` into a string field rather than to change scoring.
* **P2 large** — enforcement would delete moat scoring for a large block of companies, and
  E12's abstention tail comes back through the front door.
