# E16 results - conditional BQ repair pass (2026-08-18)

ADVISORY / SHADOW. This measures whether dimensions get SCORED, not whether the
scores are right. There is no forward-return grader. `promoted` stays false.

Sample: 59 under-floor, 20 controls; the repair call
ran on 52 of them.

| criterion | measured | bar | verdict |
|---|---|---|---|
| Q1 under-floor companies clearing the floor | 10 -> 31 of 59 (52.5%) | >= 35% | PASS |
| Q2 unverified quotes, REPAIR call only | 1.92% (1 of 52) | <= 1.0% | FAIL |
| Q3 controls losing a dimension | 0 | 0 | PASS |
| Q4 economies_of_scale recovered | 67.8% | >= 60% | PASS |

Median dimensions scored, under-floor: 5 -> 6. Median repair cost 23.9 s.

## What the repair call actually recovered

| dimension | companies |
|---|---:|
| economies_of_scale | 40 |
| manufacturing_complexity | 13 |
| data_advantages | 3 |
| network_effects | 2 |

## Q5 - what the newly cleared companies are made of

The floor exists so a moat verdict cannot rest on a handful of dimensions. If
every newly cleared company clears on the same six, the floor was cleared on a
technicality.

| dimension | appears in |
|---|---:|
| switching_costs | 21 of 21 |
| customer_relationships | 20 of 21 |
| economies_of_scale | 18 of 21 |
| regulatory_barriers | 18 of 21 |
| brand | 15 of 21 |
| distribution | 14 of 21 |
| intellectual_property | 9 of 21 |
| technological_advantage | 7 of 21 |
| manufacturing_complexity | 4 of 21 |
| network_effects | 2 of 21 |
| data_advantages | 2 of 21 |
