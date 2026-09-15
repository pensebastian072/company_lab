# E26 verdict - accepted, having failed three of its four bars, and why the bars were wrong

Written 2026-08-23 after the re-score. E26 is **kept**. That decision is recorded here
with the failures in full, because a change that fails its own pre-registered criteria and
ships anyway is exactly the thing this journal exists to make visible.

## The bars, and how they went

| | before E25 | after E25 + E26 | bar | |
|---|---:|---:|---|---|
| **N1** companies with no band | 331 | **324** | within +/-15 | **PASS** |
| **N2** median coverage | 0.880 | **0.894** | within 0.01 | **FAIL** (+0.014) |
| **N3** worst within-sector Spearman | - | **0.959** (Utilities) | > 0.97 | **FAIL** |
| **N4** companies keeping a band they lacked before E25 | - | **45** | at most 15 | **FAIL** |

Median `mg_available` went 14 -> 9 and median `composite_strict` 49 -> 45 on the shorter
94-point scale, so the correction moved everything in the intended direction. It simply
did not land on neutrality.

## Why neutrality was an incoherent target

**A change that removes real content cannot be neutral.** E25 deleted five model-scored
CEO attributes. Companies that had been scored on them lose points; companies that never
were do not. Companies whose MG was thin lose *less* coverage than before, because the
denominator shrank from 15 to 9. Every one of those is the change working, and every one
registers as a neutrality failure.

Utilities makes it concrete. The sector's rank correlation fell to 0.959 because its
largest movers are precisely the companies that had model-scored CEO points:

| | composite | MG | MG available |
|---|---|---|---|
| D | 44 -> 37 | 10 -> 4 | 11 -> 5 |
| EIX | 58 -> 52 | 8 -> 2 | 11 -> 5 |
| ED | 48 -> 42 | 11 -> 5 | 15 -> 9 |
| PEG | 44 -> 38 | 11 -> 5 | 15 -> 9 |
| MDU | 25 -> 25 | 4 -> 4 | 5 -> 5 |
| BKH | 34 -> 35 | 2 -> 2 | 4 -> 3 |

Utility CEOs are long-tenured and the model scored them readily, so utilities carried more
of the removed content than any other sector. The reorder is the deletion landing where
the deleted thing was - not a scoring accident.

**I wrote N1-N4 to catch an arithmetic artefact and they cannot tell an artefact from a
genuine removal.** That is a design error in the test, and it is mine.

## What was NOT done

The bars were not redefined after seeing them fail, and no bar was quietly widened to
turn a FAIL into a PASS. The failures stand in the table above. What changed is the
conclusion drawn from them, and the reasoning for that is this document.

## Why E26 is kept anyway

1. The evidence against the removed attributes is unaffected by any of this: `tenure` -
   a stated fact that increments by one a year - round-tripped at **kappa 0.29** with the
   proxy in front of the model (E24).
2. The shrink is principled rather than tuned: seven attributes on a 14-point raw scale
   were worth 8 points, and the two survivors are 4 of those 14, so the block is worth 2.
   No number here was chosen to hit a target.
3. The alternative is worse. Reverting to E25 keeps a framework where **deleting a
   question made it easier to pass** - 56 companies over the band gate on threshold
   arithmetic. Reverting further restores an input measured to be unreliable.

## What a reader should hold against this

The framework is **94 points**, the judged share is **44 against 50 measured**, and
`composite_strict` is no longer comparable to any figure quoted before 2026-08-23. Every
study on the Findings sheet predates the change. The band thresholds still read 0-100
because `selection_score` normalises to 100 explicitly - that is deliberate and tested,
but it means the headline sum and the banded score now live on different scales, and
anyone reading them side by side needs to know it.

`promoted` stays false. None of this is about returns.
