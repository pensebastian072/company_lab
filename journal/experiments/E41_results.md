# E41 results - the verified-fill hybrid

1472 companies. **Arithmetic over payloads and production's scorecards - nothing was folded, rescored or rebuilt.** Registered at `journal/experiments/E41_verified_fill_preregistration.md`.

The policy measured: keep production's judged half, and add a candidate SG sub-test **only where production abstained and the candidate's own quote verifies against the filing**.

## H1 - how many candidate fills survive their own citation check?

**1766 of 2030** SG fills verify — **87.0%**.

## H2 - who clears the 0.80 coverage gate

| policy | companies clearing |
|---|---:|
| production as it stands | 1184 |
| **+ verified candidate SG fills** | **1321** |
| + every candidate SG fill, verified or not | 1337 |

**137** companies cross the gate on verified fills alone.

## H3 - points added

Mean **4.2** of 20 SG points per company (median 4.0); 1124 companies gain anything.

## H4 - are the rejected fills concentrated?

264 fills rejected on their citation; the top two sub-tests are **91%** of them.

| sub-test | rejected fills |
|---|---:|
| `sg_tam_expanding` | 125 |
| `sg_capacity_backlog_contracts` | 116 |
| `sg_multiple_independent_drivers` | 18 |
| `sg_secular_not_cyclical` | 3 |
| `sg_revenue_growth_sustainable` | 1 |
| `sg_demand_drivers_3_5yr` | 1 |

**But the concentration is volume, not risk** - and that matters, because H4 was registered as "if they cluster, they can be excluded by rule":

| sub-test | fills | rejected | rate |
|---|---:|---:|---:|
| `sg_tam_expanding` | 992 | 125 | 12.6% |
| `sg_capacity_backlog_contracts` | 832 | 116 | 13.9% |
| `sg_multiple_independent_drivers` | 94 | 18 | 19.1% |
| `sg_revenue_growth_sustainable` | 87 | 1 | 1.1% |
| `sg_secular_not_cyclical` | 22 | 3 | 13.6% |
| `sg_demand_drivers_3_5yr` | 3 | 1 | 33.3% |

The two sub-tests carrying 91% of the rejections carry 90% of the **fills**, at a rejection rate (12.6%, 13.9%) barely different from the rest. **So there is no sub-test to exclude by rule** - blacklisting them would discard ~1,580 verified answers to avoid 241 unverifiable ones. The per-quote check is the only gate that separates them, which is an argument for keeping it rather than replacing it with policy.

## The limit that decides how this reads

**SG only.** `parse_sg` verifies a quote per sub-test; `parse_bq` and `parse_mg` verify once at the top level. **BQ is where most of the abstention lives** (null 38.6% against SG's 23.2%), and there is no per-dimension citation there to gate on. So this is a **floor**: the ceiling needs per-dimension `evidence` in the BQ schema and a full re-run of the candidate lane — a GPU job of roughly the size of the one that just finished, not an analysis.

## What this does not establish

That the gated scores are RIGHT. A verified quote proves the sentence exists in the filing, not that the judgement drawn from it is sound. There is still no forward-return grader. `promoted` stays false.
