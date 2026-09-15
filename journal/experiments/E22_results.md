# E22 results - is the judgement half stable? (2026-08-22)

ADVISORY / SHADOW. This is a RELIABILITY test, not a return test. Two
cross-sections cannot carry a claim about forward returns, so none is made and
no Deflated Sharpe is computed. `promoted` stays false.

203 companies, two readings each - the 10-K current a year ago
and two years ago, with fundamentals as first filed. 4 companies lost a reading and are excluded.

## R1 - does a component say the same thing a year later?

| component | pairs | Spearman | >= 0.5 | median change | unchanged | parse fails |
|---|---:|---:|---|---:|---:|---:|
| SG | 199 | 0.6033 | PASS | 2.0 | 0.206 | 0 |
| BQ | 197 | 0.6276 | PASS | 0.318 | 0.137 | 0 |
| MG | 165 | 0.2907 | FAIL | 0.0 | 0.515 | 0 |

## R2 - churn, reported with no bar

| component | share moving more than the bar | bar | median sub-tests scored (t-2 -> t-1) | median change in count |
|---|---:|---:|---|---:|
| SG | 0.151 | 4 | 4 -> 4 | 0 |
| BQ | 0.0 | 2 | 6 -> 7 | 1 |
| MG | 0.0 | 2 | 1 -> 1 | 0 |

## R3 - is it restating the financials?

Rank correlation of the judgement half against the measured half: **0.2924** over 202 companies. The registered bar is 0.8 - above it, the LLM is largely re-deriving numbers the measured half already has, and 50 points are buying less than they cost.

_measured half is TODAY's quant_normalized, not point-in-time - an approximation, stated rather than hidden_

