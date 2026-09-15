# E29 Amendment 1 - P5 was P4 arithmetically restated

Written 2026-08-25, **before the measurement is run and before any scoring code moves**.
Amends `E29_applicability_map_preregistration.md`; that document stands except where this
one replaces P5. E12's Amendment 1 is the precedent: a criterion that cannot do the work
it claims is fixed in the open, in writing, before it decides anything.

## The defect

P4 and P5 as registered this morning:

> **P4** The sub-test's null rate in the nominated sector is at or above **85%**.
> **P5** If more than **15%** of the nominated sector's companies were SCORED on the
> sub-test, the referent demonstrably exists for that business model and the entry is
> refused.

A judged sub-test has three possible statuses and they partition the sector:
`no_data` + `scored` + `not_applicable` = n. So `scored_share <= 15%` follows from
`null_rate >= 85%` by subtraction. **P5 refuses nothing P4 has not already refused.**
Presented as five independent hurdles, the bar was really four.

I wrote it believing it added a second angle. It does not, and a criterion that reads as
extra protection while providing none is worse than not having it - it makes a thin map
look well-guarded.

## What P5 should have been testing

The failure mode P4 cannot see is the one that matters most here, and it is the H2
failure E12 named in a different costume:

> The sector's filings are simply hard for this pack to read, so the model abstains on
> **everything** for that sector - and the candidate sub-test is caught up in a general
> retrieval failure rather than telling us anything about the business.

If Real Estate is 90% null on `sg_capacity_backlog_contracts` and also 88% null on every
other Strategic Growth sub-test, the backlog number is not evidence that REITs have no
backlog. It is evidence that REIT 10-Ks are not yielding SG answers. Admitting it would
launder a retrieval failure into a scoring rule, which is exactly the thing Rule C exists
to prevent - Rule C just checks it **across sectors** and misses it **within one**.

## P5, replaced

> **P5 - sector specificity.** The nominated sector's null rate on the candidate sub-test
> must exceed **by more than 25 percentage points** that sector's own **median** null
> rate across the other judged sub-tests of the same component. A category error stands
> out against the sector's baseline; a pack that cannot be read produces a flat, high
> null rate across the whole component and is refused.

Stated by mechanism, and unchanged in direction: like P4 it is **one-sided** and can only
shrink the map, never grow it. The 25pp figure is chosen as a margin large enough that a
sub-test must be a clear outlier within its own component and its own sector, and it is
being written down **before the SG and MG matrices have been computed at all** - the only
per-sector judged-half numbers on disk today are E12's BQ moat-dimension matrix, which
this criterion is not applied to, because BQ is a single sub-test whose dimensions live
one level below the map's unit.

## Unchanged

P1 (spread > 40pp), P2 (Rule C: best sector at or under 40% null), P3 (a named written
business reason, still the binding one - **required for any change at all**), P4 (near
total in the nominated sector), the exclusion of `fe_margin_expansion` for Utilities and
of every scored-shortfall loss, the four required reports, the prior as written, and the
limit that matters most: **nothing here tests whether any of it predicts anything**, and
`promoted` stays false.

## Scoring the prior honestly

The prior in the registration was written against the five criteria as published. Since
P5 refused nothing, the prior is in effect a prediction against P1-P4 plus the new P5,
and the replacement can only make the map smaller. If the map comes back **smaller** than
the predicted 2-6 entries, that is the amendment doing its job and not a better result;
if it comes back larger, the prior was wrong and will be recorded as wrong.
