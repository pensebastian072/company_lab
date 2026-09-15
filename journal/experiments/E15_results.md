# E15 results - BQ targeted retrieval (2026-08-18)

ADVISORY / SHADOW. This measures whether dimensions get SCORED, not whether
the scores are right. There is no forward-return grader. `promoted` stays false.

Sample: 20 under-floor companies, 10 controls.

| criterion | measured | bar | verdict |
|---|---|---|---|
| P1 median dimensions scored | 4.5 -> 4.0 (+-0.5) | >= +1.5 | FAIL |
| P2 unverified quote rate (arm B) | 3.33% (A: 0.0%) | <= 1.0% | FAIL |
| P3 controls losing a dimension | 7 of 10 | <= 1 | FAIL |
| P4 added seconds per company | 2.2 | <= 25 | PASS |

Companies clearing the 6-dimension floor: **3 -> 5** of 20.

## Per weak dimension (under-floor sample)

| dimension | scored in A | scored in B | of |
|---|---:|---:|---:|
| network_effects | 0 | 1 | 20 |
| manufacturing_complexity | 3 | 4 | 20 |
| data_advantages | 0 | 1 | 20 |
| economies_of_scale | 2 | 18 | 20 |

## Exploratory, NOT pre-registered

Arm C (A's call unioned with the targeted weak call) reaches a median of 5.0 dimensions and clears the floor for 9 of 20. It cannot lose a dimension by construction, so it is not comparable to B on this table - it needs its own registered run before it can be preferred.

Controls that lost a dimension: AVGO, DASH, DXC, GRBK, GT, SYY, ULTA
