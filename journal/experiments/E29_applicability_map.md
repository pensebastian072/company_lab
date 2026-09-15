# E29 - the applicability map, and it is EMPTY

Written 2026-08-25 from `E29_results.json`, against
`E29_applicability_map_preregistration.md` and its Amendment 1. **No rubric code changed.
No profile changed. No denominator changed. `promoted` is still false.**

E12's P3 has been open since 2026-08-16. It is discharged here by **refusing every
candidate**, which is a real outcome of the criterion and not a failure to do the work.

## The result in one line

Of **132 (sub-test, sector) pairs**, exactly **one** cleared the machine criteria
P1+P2+P4+P5 - `sg_tam_expanding` for **Consumer Staples** - and it **fails P3**, the
written-business-reason test, which the registration named as the binding one.

## The admitted entries

**None.**

## The refused entries, with their numbers

The registration requires refusals and their numbers in the same document as any
admission, because a map that lists only what it dropped is not auditable.

### `sg_tam_expanding` - Consumer Staples (85.3% null) - the only machine pass, REFUSED on P3

| P1 spread | P2 best sector | P4 sector null | P5 specificity |
|---|---|---|---|
| 63.2pp PASS | Information Technology 22.1% PASS | 85.3% PASS | +82.6pp over a 2.7% SG baseline PASS |

**Refused. A packaged-foods company has a total addressable market.** There is nothing
about the consumer-staples business model that lacks one, so the question has a referent
and this is not a category error. What the 85.3% actually says is that a mature,
low-single-digit-growth filer does not write about its TAM *expanding*, because it is
not - and the honest score for that is **low, not absent**. Marking it inapplicable would
make the sector look better by declining to measure the very thing that makes it a
staples business. That is the exclusion the registration wrote down this morning, applied
to the case it was written for.

The specificity figure is the tell that P5 worked as intended: Consumer Staples is 2.7%
null on the rest of Strategic Growth. Its filings are perfectly readable. The model is
not failing to retrieve - it is declining to claim an expansion that is not there.

### `sg_tam_expanding` - Real Estate (81.1% null) - fails P4, and would fail P3

Missed P4's 85% by 3.9 points. It would have been refused anyway: a REIT has an
addressable market - square footage in its property type and geography - and data-centre
and industrial REITs are the standard example of one that **is** expanding. The referent
exists.

### `sg_capacity_backlog_contracts` - Real Estate (65.1% null) - fails P4, and would fail P3

This was my named prediction to PASS. It does not, on either test.

**34.9% of REITs were scored on it**, which is the answer: a REIT's long-term leases
**are** contracted forward revenue - the economic analogue of a backlog - and a third of
the sector's filings say so quotably enough for the model to score it. The referent
plainly exists. The prior was wrong.

### `sg_capacity_backlog_contracts` - Consumer Staples (84.0%) and Communication Services (80.9%) - fail P4

Both under the 85% bar, and both have supply and carriage contracts.

### `economies_of_scale` (BQ moat dimension) - the one E12 Amendment 1 admitted - REFUSED on P3

E12's Rule C left exactly one candidate standing: `economies_of_scale`, best sector
Consumer Staples 31.5% null, Real Estate 81.6%. **Refused here on P3.** Scale economics in
real estate are real and ordinary - cost of capital, property-management overhead spread
across a larger portfolio, tenant relationships across markets. A REIT that is not
benefiting from them is a REIT with a weakness, not a REIT the question does not fit.

### Everything else

The remaining 127 pairs fail P1, P2 or P4 outright. The full table is in
`E29_results.json` under `candidates`.

## What the measurement found instead, which is the useful part

`sg_tam_expanding` is **22.1% null in Information Technology and 64-85% null in nine of
the other ten sectors**. That is not a sector-applicability shape. It is a **question
that only works for high-growth technology businesses**, and it is the same finding
E12's Rule C produced for `network_effects`, `manufacturing_complexity` and
`data_advantages` - routed to the evidence-and-prompt fix, not to a denominator change.

Two sub-tests carry essentially the whole judged-half category-error loss outside
`bq_moat`:

| sub-test | Real Estate | Utilities | best sector null |
|---|---:|---:|---|
| `sg_tam_expanding` | 344 pts | 188 pts | IT 22.1% |
| `sg_capacity_backlog_contracts` | 207 pts | 51 pts | Utilities 28.8% |

Both are **askable** - the model answers them routinely somewhere - so the fix is to ask
them better, not to stop asking them. That is E15-E18 territory and it has its own
unhappy history: E15 failed 3 of 4, and E17's R4 is still open.

## The loss, split the way the registration requires

Judged half only. `category_error` is availability the company never had a chance at;
`scored_shortfall` is points the model **did** assess and did not award. **The map can
only ever move the first, and it moved none of it.**

| sector | category error | scored shortfall |
|---|---:|---:|
| Financials | 2,798 | 3,079 |
| Industrials | 1,775 | 3,488 |
| **Real Estate** | **1,527** | **1,275** |
| Consumer Discretionary | 1,515 | 2,926 |
| Health Care | 1,310 | 2,152 |
| Information Technology | 1,008 | 2,298 |
| Energy | 857 | 1,021 |
| Materials | 642 | 1,191 |
| Consumer Staples | 570 | 1,152 |
| Utilities | 512 | 739 |
| Communication Services | 358 | 655 |

Real Estate's 1,527 points of category error break down as `bq_moat_unassessed` **793**,
`sg_tam_expanding` **344**, `sg_capacity_backlog_contracts` **207**, and 183 elsewhere.
Its **448 points of scored shortfall inside `bq_moat` were never in scope** - the model
assessed those dimensions and scored them low, and no applicability rule touches them.

Note the column nobody asked for: **Financials lose more to category error than Real
Estate does** (2,798), and every sector's scored shortfall exceeds its category error.
The judged half's largest problem is not that the wrong questions are asked - it is that
the answers are low.

## The prior, scored honestly

The registration predicted 2-6 entries concentrated in Real Estate. **The map has zero.**

| prediction | outcome |
|---|---|
| `sg_capacity_backlog_contracts` Real Estate **passes** | **WRONG** - fails P4 at 65.1%, and a third of REITs were scored on it |
| `sg_tam_expanding` Real Estate **fails P2** | **Right verdict, wrong reason** - it PASSES P2 (best sector 22.1%) and fails P4 |
| no BQ entry beyond `economies_of_scale` | right, and `economies_of_scale` is refused too |
| Utilities gain little | right - they gain nothing |
| median coverage moves < 0.03; Real Estate stays below 0.80 | trivially right; nothing moved |

Two of five specifics wrong, and the headline count wrong in the direction that makes the
project look worse rather than better. That is the record.

## What this does not establish

**Nothing here tests whether any of it predicts anything.** There is no forward-return
grader - it needs ~50 weekly snapshots and the `as_first_filed` view, and 5 exist. An
empty map means the scores are unchanged, so nothing was made better or worse today; what
changed is that a plausible-sounding fix was checked and refused, and the 26-point
cross-sector spread it was meant to close is still there and is still handled by
presentation (the `sector_neutral_score` column) rather than by a rubric change.

`promoted` stays false.

## Verdict

**E29 closes with no rubric change.** E12's P3 is discharged: it was applied, it was
binding, and it refused every entry the null rates offered. The remaining Real Estate gap
is not a set of inapplicable questions - it is `bq_moat` availability that E19 already
converted from a cliff into a weight, plus two askable SG questions the evidence pack
answers only for technology companies.
