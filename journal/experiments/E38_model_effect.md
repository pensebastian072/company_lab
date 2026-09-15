# E38_model_effect results - a lane comparison

as_of 2026-09-01T20:00:13.096316+00:00  ·  incumbent `qwen2.5:7b (structured)`  ·  candidate `LFM2.5-2.6B-Finance (structured)`

Registered at `journal/experiments/E38_model_effect_control_lane_preregistration.md`. The probe's 10 companies are excluded - they were read before the criteria were fixed.

## C1 + C2 - abstention, and whether it was earned

| component | companies | v1 null | v2 null | v1 degenerate | v2 degenerate | mean score delta |
|---|---:|---:|---:|---:|---:|---:|
| SG | 1471 | 22.8% | 0.2% | 0.0% | 0.0% | +0.35 |
| BQ | 1471 | 40.0% | 0.0% | 19.7% | 0.1% | +0.59 |
| MG | 1471 | n/a | n/a | n/a | n/a | n/a |

**A degenerate rationale is the pack's header line (`chrome`) or the literal word null/none/empty (`empty`), measured identically for both lanes.** A short-but-real judgement is `terse` and is NOT counted - see amendment 1, where lumping the two produced a 40.4% figure for the incumbent that was mostly the character threshold. Degeneracy is counted only where a score was actually given: an abstention has nothing to justify. `evidence_unverified` is NOT the check here - a page header is verbatim pack text, so it verifies.

## E12's four watched dimensions

| dimension | n | v1 null | v2 null | v1 degen | v2 degen |
|---|---:|---:|---:|---:|---:|
| network_effects | 1471 | 87.5% | 0.0% | 6.6% | 0.1% |
| manufacturing_complexity | 1471 | 74.2% | 0.0% | 10.3% | 0.1% |
| data_advantages | 1471 | 79.5% | 0.1% | 10.3% | 0.1% |
| economies_of_scale | 1471 | 61.7% | 0.0% | 7.5% | 0.1% |

## What this does and does not establish

Neither judged half has ever been graded against forward returns - there is no grader in this repo yet. E36 can say which model abstains less and whether the scores it gave instead were justified. It cannot say which is *better*. `promoted` stays false.
