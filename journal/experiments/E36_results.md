# E36 results - the v2 lane

as_of 2026-08-30T03:36:15.662537+00:00  ·  incumbent `qwen2.5:7b`  ·  candidate `LFM2.5-2.6B-Finance`

Registered at `journal/experiments/E36_v2_lane_preregistration.md`. The probe's 10 companies are excluded - they were read before the criteria were fixed.

## C1 + C2 - abstention, and whether it was earned

| component | companies | v1 null | v2 null | v1 degenerate | v2 degenerate | mean score delta |
|---|---:|---:|---:|---:|---:|---:|
| SG | 1090 | 23.3% | 0.2% | 0.0% | 0.0% | +0.39 |
| BQ | 1090 | 38.9% | 0.0% | 22.7% | 0.1% | +0.60 |
| MG | 1090 | 66.6% | n/a | 0.1% | n/a | n/a |

**A degenerate rationale is the pack's header line (`chrome`) or the literal word null/none/empty (`empty`), measured identically for both lanes.** A short-but-real judgement is `terse` and is NOT counted - see amendment 1, where lumping the two produced a 40.4% figure for the incumbent that was mostly the character threshold. Degeneracy is counted only where a score was actually given: an abstention has nothing to justify. `evidence_unverified` is NOT the check here - a page header is verbatim pack text, so it verifies.

## E12's four watched dimensions

| dimension | n | v1 null | v2 null | v1 degen | v2 degen |
|---|---:|---:|---:|---:|---:|
| network_effects | 1087 | 83.6% | 0.0% | 10.2% | 0.2% |
| manufacturing_complexity | 1087 | 73.6% | 0.0% | 11.8% | 0.1% |
| data_advantages | 1086 | 74.2% | 0.1% | 13.4% | 0.2% |
| economies_of_scale | 1087 | 59.1% | 0.0% | 8.0% | 0.1% |

## What this does and does not establish

Neither judged half has ever been graded against forward returns - there is no grader in this repo yet. E36 can say which model abstains less and whether the scores it gave instead were justified. It cannot say which is *better*. `promoted` stays false.
