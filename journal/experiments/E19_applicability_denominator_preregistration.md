# E19 - the floor becomes a WEIGHT, not a cliff

Decision taken by the user 2026-08-19, after E12's measurement and the E15-E18 repair
work established that the abstention it punishes is mostly real and mostly structural.
Registered before any scoring code changes.

## The decision, in the user's terms

> "It's not fair that Real Estate isn't included... I just want every single company
> counted in some way. I don't want five hundred companies I can't even look at."

That is a rubric change and it is theirs to make. What follows fixes exactly what changes,
what does not, and what has to be reported afterwards so the change can be judged.

## What is wrong today

BQ awards **15 points if 6 of 11 moat dimensions are scored and 0 otherwise**. MG's CEO
block awards **8 points if 4 of 5 attributes are scored and 0 otherwise**. Both are
cliffs, and the measurement says the cliff lands on business models rather than on bad
companies:

* **423 companies score 0 of 15 on BQ.** 184 of them are **one dimension short**; only 1
  has no 10-K at all. Nothing is missing - the model declined.
* Abstention within that group is dimension-specific: `network_effects` 99.1% null,
  `data_advantages` 98.8%, `economies_of_scale` 96.9%, against `customer_relationships`
  22.0% off the same evidence pack.
* And it is sector-structured: of the 549 companies with no band, **Financials 116, Real
  Estate 84**. A REIT has no manufacturing complexity. A bank has no network effects. The
  rubric asks all eleven of everyone and then zeroes the component when the filing does
  not discuss what the business does not have.
* **121 companies sit at exactly 3 of 15 on MG**, the same cliff one component over.

The prompt tells the model to abstain when it cannot quote. The floor treats that
abstention as failure. Two correct rules disagreeing, and the company pays.

## The change

**Availability becomes proportional to what was assessed.**

| | today | after |
|---|---|---|
| BQ, n dimensions scored | 15 points if n >= 6, else **0** | `round(15 * n / 11)` |
| BQ, points earned | `round(mean(scored)/5 * 15)` | `round(mean(scored)/5 * available)` |
| MG CEO block, n attributes | 8 points if n >= 4, else **0** | `round(8 * n / 5)` |

Nothing else moves. `composite_strict` still sums earned points, `coverage` still divides
available by max, the 0.80 band gate still stands, and a company assessed on two
dimensions still cannot look like one assessed on eleven - **it carries 3 points of
availability instead of 15, so it is down-weighted rather than deleted.** The floor
becomes a weight, which is what it should have been.

This is deliberately the version with **no sector map in it**. A REIT scored on 5 of 11
dimensions gets 7 points of BQ availability rather than 0, but its coverage is still lower
than a software company's. Fixing that is the separate, harder half below.

## What this does NOT do, stated plainly

* It does **not** make the scores more accurate. It makes more of them exist. There is no
  forward-return grader, `promoted` stays false, and a company that appears with a band
  tomorrow is not better understood than it was today.
* It **weakens the protection the floor provided**. A moat verdict resting on two
  dimensions is now possible where it was impossible. The mitigation is the weight, not a
  rule: two dimensions buy 3 of 15 points, so such a company cannot rank near a fully
  assessed one on `composite_strict`. On `composite_normalized` - which extrapolates from
  coverage - it can, and that is exactly why the workbook never shows normalized without
  its coverage figure.
* A company whose **10-K could not be read at all** still reports `INSUFFICIENT_DATA` and
  says so. That is 1 company on BQ today, plus the 9 whole-document-fallback filers.

## Required reporting after the change

1. **Within-sector Spearman of `composite_strict`**, before vs after, over every company
   in the sector - E12's P4 duty, the same instrument used for the repair pass.
2. **Counts**: companies gaining a band, and the distribution of `n_dimensions_scored`
   among newly banded companies. If most new bands rest on 3 dimensions, that is the
   finding, and it belongs in the workbook's Findings sheet next to the number.
3. **The sector mix of the newly banded companies**, since the whole complaint was that
   the cliff was a sector artefact. If Financials and Real Estate do not move
   disproportionately, the cliff was not the sector problem it looked like.

## The second half, NOT done here

A REIT should not be *asked* about manufacturing complexity at all. That needs a
per-sector applicability map, and E12's P3 requires each entry to carry a **named written
business reason** - not a null rate. E12's P2 measurement is already on disk
(`E12_abstention_2026-08-18.json`) and its amendment established the rule: a dimension may
be dropped for a sector only if the model can answer it somewhere (best sector at or under
40% null), otherwise the drop launders a retrieval failure into a scoring rule.

Under that test only `economies_of_scale` qualified. So the map is a small, argued
document, not a bulk deletion, and it comes after this change is measured.

## Prediction, stated before running

Roughly **200-260 companies gain a band**, most of them the 184 sitting one dimension
short, and the newly banded skew to Financials and Real Estate. Median coverage rises
from 0.84 to about 0.88. Within-sector Spearman stays above 0.95 - this reweights rather
than reorders, because the companies affected were previously at zero and are entering
the ranking from below.
