# E26 - the CEO block is worth what it still asks, and the framework is 94 points

Registered 2026-08-23, before the code changes. Triggered by E25's own pre-registered
stop condition, which fired.

## Why

E25 removed MG's five model-scored CEO attributes. The re-score came back with **148 band
changes** against a registered trip-wire of 100, and the direction was the opposite of the
one the trip-wire was written to catch:

* MG availability **rose** for 405 companies and fell for 11, mean **+1.26 points**
* **66 companies gained a band**, and **56 of those moved on MG availability alone**
* their median coverage went 0.76 -> **0.817**, stepping over the 0.80 gate
* their median `mg_available` went 9 -> **14**

The mechanism is arithmetic, not evidence. The old CEO block needed **4 of 7** attributes
and the model-scored ones were sparse, so many companies sat below the threshold and took
proportional credit. The new block needs **2 of 2**, and 1,350 of 1,500 companies have
both measured attributes, so they take the whole 8 points.

**Deleting a question made the framework easier to pass.** That is the trap E12's
registration named in advance - *"moving a floor until the output looks complete is
fitting the rubric to the data"* - arriving by a side door.

## The change

**The CEO block shrinks to what it still measures.** It carried 7 attributes worth 8
points on a 14-point raw scale; the two survivors are 4 of those 14 raw points, so the
block becomes **2 points**, and MG becomes **9** (CEO 2 + capital allocation 7).

Consequences, stated rather than discovered later:

* **`TOTAL_POINTS` becomes 94.** The framework asks fewer questions than it did, and the
  denominator should say so instead of pretending the missing 6 points are unmeasured.
  `tests/test_composite.py` already asserts the component maxima sum to `TOTAL_POINTS`,
  so this stays internally consistent by construction.
* **The band score is normalised to 100 explicitly.** `selection_score` currently rescales
  by the framework total, which would silently make every band harder to reach on a
  94-point scale - the same class of error as E19's first version. It now divides by the
  applicable total and multiplies by 100, so `BANDS` keeps its calibration no matter what
  the framework's raw total becomes.
* The 6 released points are **not** redistributed. Handing them to capital allocation
  would be inventing weight for a block on no evidence.

## Pass criteria

This is a correction, so its bar is neutrality against the state BEFORE E25, not
improvement:

| | passes if |
|---|---|
| **N1** | Companies with no band land within **+/- 15** of the pre-E25 count of 331. Neither the artefact nor an over-correction survives. |
| **N2** | Median coverage lands within **0.01** of pre-E25. |
| **N3** | Within-sector Spearman of the new composite against pre-E25 stays above **0.97** - this reweights, it must not reorder. |
| **N4** | The 56 companies that gained a band on MG availability alone are re-checked: **at most 15** of them still hold a band they did not have before E25. |

## Prediction, stated before running

N1 and N2 pass close to dead-on, because the change is calibrated to undo an arithmetic
artefact rather than to move anything. N3 passes above 0.99. **N4 is the one I am least
sure of** - I expect 5-20 companies to keep the band, because for some the CEO block was
genuinely most of what was missing and 2 honest points still tips them over. If N4 comes
back above 30, the shrink is too small and the block is still buying coverage it has not
earned.

## What this does not do

It does not make MG more predictive, and it does not restore anything E25 removed. It
makes the framework's denominator honest about how many questions it still asks.
`promoted` stays false.
