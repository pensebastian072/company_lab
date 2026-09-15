# E51 results - symmetric abstention incentive restores the four fields

> **Dated note, 2026-09-09 — scoring generation.** The external scores in this file
> were computed BEFORE the 2026-09-09 re-score. `score_all --apply` was run that day
> across all 13 research versions, applying two instrument changes that post-dated
> this study: the A1 UNVERIFIABLE doctrine
> (`A1_UNVERIFIABLE_SCORING_DECISION_2026-09-08.md`) and the FDIC-computed
> `market_share_direction`. For this arm that moved **5** stored scores.
> Largest moves: NYT 74.1->57.6, ROKU 79.1->67.1, TTD 78.1->66.1, PINS 69.7->61.1, PPLI 43.6->40.2.
> The pre-re-score values are frozen at
> `D:/company_lab_data/external/reports/prescore_snapshot_2026-09-09.json`
> (sha256 `a8189d864f7981508c26ab136050a1b28ed10ab9f4d0a80106f2f14a4e920272`).
> Numbers in this file are NOT restated; see `SCORE_STALENESS_2026-09-09.md`.


Evaluated 2026-09-05 after finalization, full local verification, computed revenue share,
scoring, and `batch_health`. Request `cb5a414ee0f1d181394b` became research version
`2026-09-06+E51-commservices-symmetric`.

## Execution and evidence integrity

| check | result |
|---|---:|
| companies | 47 of 47 accepted; 0 rejected |
| claims | 611 of 611 `VERIFIED_LOCAL` |
| non-UNKNOWN fields at finalization | 517 of 517 citation-backed |
| finalizer demotions | 0 |
| four registered fields | 188 of 188 resolved (100.0%) |
| UNKNOWN classifications | 47 evidence absent; 0 stopped short |
| searches / cache hits | 282 / 282 |
| distinct source URLs / independence domains | 97 / 4 |
| external-score range | 32.9 to 83.6 |
| `batch_health` | `OK`; within-industry fill delta +1.000 |

> **Correction recorded 2026-09-07:** the table preserves E51's original verification
> result. After PDF extraction-state and numeric-quote guards, this request has 601
> VERIFIED_LOCAL and 10 UNVERIFIABLE claims. This does not rewrite the registered
> criterion or verdict; it lowers current confidence in the evidence verification. The
> research remains SHADOW; see
> `verification_rate_correction_2026-09-07.md`.

Every remaining UNKNOWN was `market_share_direction`, deliberately left to the filed-
revenue computation. The computation subsequently filled 23 companies: 6 GAINING,
11 FLAT, and 6 LOSING, with no researched/computed conflicts. The citation requirement
stopped no answer.

## Registered predictions

Arm A was the frozen E49 record: 0 of 188 rank-order slots filled and external-score
standard deviation 2.90. Standard deviations below are sample standard deviations.

| # | registered criterion | actual | verdict |
|---|---|---:|---|
| 1 | arm B rank-order fill >=25% | 100.0% (188/188) | PASS |
| 2 | arm B minus arm A >=20 points | +100.0 points | PASS |
| 3 | demotions <=5% of assertions | 0.0% (0 demotions) | PASS |
| 4 | UNVERIFIABLE claims = 0 | 0 (611/611 locally verified) | PASS |
| 5 | arm B external-score sd >6.0 | 14.00 | PASS |

**Result: 5 of 5 passed.** Under the registered outcome map, the symmetric incentive
block replaces the one-sided UNKNOWN praise. Coverage returned without any loss of
citation discipline. This validates a research-process correction, not the ranking:
status remains SHADOW and `promoted` remains false. Utilities was not rerun as part of
this result.


## E52 post-E51 remeasurement

Replacing E49's 47 records with E51's 47 records keeps the comparison at n=289. The
registered calculation produces:

| sector | n | v1 sd | v2 sd | v2 higher? |
|---|---:|---:|---:|---|
| Communication Services | 47 | 10.78 | 13.06 | yes |
| Energy | 71 | 12.20 | 9.11 | no |
| Financials | 87 | 6.20 | 6.80 | yes |
| Information Technology | 18 | 8.21 | 13.02 | yes |
| Utilities | 59 | 2.29 | 4.38 | yes |
| pooled | 289 | 12.91 | 10.62 | **no** |

That is 4 of 5 sectors, but pooled dispersion falls. The registered ship rule required
both conditions, so v2 does not ship.

The rerun also exposed an error in E52's original measurement path. Its published v1
numbers reproduce exactly only when `evaluate()` receives an empty scored-evidence
object, while v2 receives the stored claim totals. That zeroes v1's external coverage
and confidence criteria and makes the comparison asymmetric. Recomputing both versions
from the same scored evidence gives the following fair audit:

| sector | n | corrected v1 sd | corrected v2 sd | v2 higher? |
|---|---:|---:|---:|---|
| Communication Services | 47 | 10.78 | 13.06 | yes |
| Energy | 71 | 15.70 | 9.11 | no |
| Financials | 87 | 7.56 | 6.80 | no |
| Information Technology | 18 | 8.09 | 13.02 | yes |
| Utilities | 59 | 3.62 | 4.38 | yes |
| pooled | 289 | 16.04 | 10.62 | **no** |

The corrected audit is 3 of 5 sectors and again lowers pooled dispersion. The decision
is therefore robust to the E52 measurement bug: v1 remains live, v2 remains unshipped,
and no promotion state changes.
