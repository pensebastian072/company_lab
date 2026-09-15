# E49 results - the preregistered heterogeneity screen failed

> **Dated note, 2026-09-09 — scoring generation.** The external scores in this file
> were computed BEFORE the 2026-09-09 re-score. `score_all --apply` was run that day
> across all 13 research versions, applying two instrument changes that post-dated
> this study: the A1 UNVERIFIABLE doctrine
> (`A1_UNVERIFIABLE_SCORING_DECISION_2026-09-08.md`) and the FDIC-computed
> `market_share_direction`. For this arm that moved **5** stored scores.
> Largest moves: NYT 30.8->23.3, PPLI 31.0->27.7, PINS 35.8->33.8, ROKU 35.8->33.8, TTD 34.8->32.8.
> The pre-re-score values are frozen at
> `D:/company_lab_data/external/reports/prescore_snapshot_2026-09-09.json`
> (sha256 `a8189d864f7981508c26ab136050a1b28ed10ab9f4d0a80106f2f14a4e920272`).
> Numbers in this file are NOT restated; see `SCORE_STALENESS_2026-09-09.md`.


Evaluated 2026-09-05 after the blind company payload was frozen, reconciled, finalized,
verified and scored. The registered predictions were not opened during Phase A or the
blind Phase B pass.

Request `d1233fa7352dca524421`; research version
`2026-09-05+E49-commservices`; 47 companies.

## Registered predictions

| # | registered criterion | measured | verdict |
|---|---|---:|---|
| 1 | external-score population SD > 8.0 | 2.90 | FAIL |
| 2 | distinct external scores > 40% of n | 18 / 47 = 38.3% | FAIL |
| 3 | largest tied group < 25% of n | 6 / 47 = 12.8% | PASS |
| 4 | fields resolving for 0 of n: at most 1 | 4 | FAIL |
| 5 | `technology_risk` distinct values >= 3 | 2 | FAIL |

Only one of five predictions held. `sd_opmargin=0.179` did not predict a dispersed
external score in the third completed sector. This does not support using the proxy to
set the remaining sector order.

The score range was 27.3 to 38.3. The two largest ties were six companies each, at 32.5
and 35.8. The four fields resolving for zero companies were `moat_trajectory`,
`competitive_position`, `competitive_position_trend` and `company_specific_capture`.
Those were researched UNKNOWNs with blocking claims, not empty gaps.

`technology_risk` returned `MODERATE` for 36 companies and `ELEVATED` for 11; it returned
neither `LOW` nor `SEVERE`. Prediction 5 therefore fails. Per the preregistered decision
rule, the risk-field measurement must be fixed before another sector is purchased.

## Boundary and evidence audit

The E49 external pass did not research `market_share_direction`, company size, or growth
versus peers. `market_share_direction` was left UNKNOWN with the blocker "computed from
revenue share". The local arithmetic then filled 23 companies: 6 GAINING, 11 FLAT and 6
LOSING, with no conflicts against researched values.

Phase A built 11 industry objects with 55 claims. Every object has five claims across
two independence domains, and all 55 claims are VERIFIED_LOCAL. Phase B returned all 47
companies with 564 claims; all 564 are VERIFIED_LOCAL. The finalizer accepted 47,
rejected zero and demoted zero. All 329 non-UNKNOWN categorical assertions have a claim
naming the field. The report records zero UNKNOWN gaps.

All 47 companies remain `INSUFFICIENT_DATA` under the 0.80 external coverage floor. That
is consistent with the four universally unresolved fields and is another reason the
sector did not become rankable.

This is a measurement result, not a return result. The ranking remains unvalidated,
`promoted` remains false and the research status remains SHADOW.
