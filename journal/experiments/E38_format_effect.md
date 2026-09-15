# E38_format_effect results - a lane comparison

as_of 2026-09-01T19:56:07.706297+00:00  ·  incumbent `qwen2.5:7b`  ·  candidate `LFM2.5-2.6B-Finance`

Registered at `journal/experiments/E38_format_effect_control_lane_preregistration.md`. The probe's 10 companies are excluded - they were read before the criteria were fixed.

## C1 + C2 - abstention, and whether it was earned

| component | companies | v1 null | v2 null | v1 degenerate | v2 degenerate | mean score delta |
|---|---:|---:|---:|---:|---:|---:|
| SG | 1471 | 22.9% | 22.8% | 0.0% | 0.0% | +0.01 |
| BQ | 1471 | 38.7% | 40.0% | 21.7% | 19.7% | +0.00 |
| MG | 1471 | 65.9% | n/a | 0.1% | n/a | n/a |

**A degenerate rationale is the pack's header line (`chrome`) or the literal word null/none/empty (`empty`), measured identically for both lanes.** A short-but-real judgement is `terse` and is NOT counted - see amendment 1, where lumping the two produced a 40.4% figure for the incumbent that was mostly the character threshold. Degeneracy is counted only where a score was actually given: an abstention has nothing to justify. `evidence_unverified` is NOT the check here - a page header is verbatim pack text, so it verifies.

## E12's four watched dimensions

| dimension | n | v1 null | v2 null | v1 degen | v2 degen |
|---|---:|---:|---:|---:|---:|
| network_effects | 1469 | 83.4% | 87.6% | 10.1% | 6.6% |
| manufacturing_complexity | 1469 | 72.8% | 74.3% | 11.8% | 10.3% |
| data_advantages | 1468 | 73.6% | 79.6% | 13.1% | 10.3% |
| economies_of_scale | 1469 | 61.2% | 61.8% | 7.7% | 7.6% |

## What this does and does not establish

Neither judged half has ever been graded against forward returns - there is no grader in this repo yet. E36 can say which model abstains less and whether the scores it gave instead were justified. It cannot say which is *better*. `promoted` stays false.
