# E45 - the coverage blocker breaks, and the funnel question still has no answer

45 companies, request `71245bc7adbc298fd13e`, research version `2026-09-02+E45-rest`.
36 priority + 9 matched control, none previously researched.

## The delivery

| | |
|---|---|
| accepted / rejected | 45 / 0 |
| non-UNKNOWN at finalize | 412, **all citation-backed**, zero demotions |
| after the FDIC fill | 425 of 540 resolved; 115 UNKNOWN, **all results, 0 gaps** |
| claims | 540 from 62 sources, 5 independence domains |
| verification | 535 VERIFIED_LOCAL, 5 SELF_ATTESTED, **0 UNVERIFIABLE** |
| corpus unverifiable rate | **0.26%** over 1,564 checked |
| searches | 315 + 45 cache hits |

Three batches in a row now with zero rejections, zero demotions and zero UNKNOWN gaps.

## THE COVERAGE BLOCKER BROKE

`competitive_position_trend` was UNKNOWN for **all 40** companies in E44 and was the
single field keeping 38 of them below the evidence floor. E45 asked for a different
approach - rank-order against named peers on a shared metric, rather than a market-share
series - and it **resolved for 27 of 45**:

| group | metric that worked | companies |
|---|---|---|
| regional banks | NIM rank order | 15 |
| P&C insurers | combined-ratio rank order | 4 |
| payments | same-period revenue growth | 5 |
| semiconductor equipment | operating growth | 3 |

The result on coverage:

```
E44   clear the 0.80 floor:  2 of 40    median coverage 0.70
E45   clear the 0.80 floor: 12 of 45    median coverage 0.75
```

That is the constraint that had blocked the whole layer since the pilot, and it was
never a data problem - it was a **question-framing** problem. "What is this company's
market share trend" needs a share series nobody publishes. "Is this company's NIM
improving relative to its named peers over the same two periods" needs four filings
everybody publishes. Same conclusion, obtainable evidence.

FDIC filled `market_share_direction` for 13 more banks. Seven remain unmatched and
correctly UNKNOWN. No computed result overwrote a researched one.

## THE FUNNEL RESULT: still not answerable, and the reported lift is mostly mix

Reported: E44+E45 priority 0.279 flags per company against control 0.118, "approximately
2.38x, directionally supportive". The arithmetic is right. The reading is not.

**Predicting each arm from its industry mix alone:**

```
priority   observed 0.279   expected from industry mix 0.263   ARM EFFECT +0.016
control    observed 0.118   expected from industry mix 0.183   ARM EFFECT -0.065
```

The priority arm's own industry composition predicts 0.263 of its 0.279. **The arm
itself adds +0.016 flags per company** - about 6% of the apparent lift. This is better
than E43, where observed equalled expected to three decimals and the arms explained
literally nothing, but it is not a result.

**Within-industry, which is the only fair comparison:**

```
industry                   P n   P/co  C n   C/co    diff
life_insurance               3   0.00    1   0.00   +0.00
midstream                    6   0.17    2   0.00   +0.17
payments                     5   0.80    1   0.00   +0.80
pc_insurance                 9   0.11    2   0.00   +0.11
refining                     4   0.50    1   0.00   +0.50
regional_banking            31   0.03    8   0.12   -0.09
semiconductor_equipment      4   1.25    1   1.00   +0.25
upstream_oil_gas             1   0.00    1   0.00   +0.00

control-weighted: priority 0.198  control 0.118  diff +0.080
```

**Read the largest row.** `regional_banking` is the only stratum with real numbers on
both sides - 31 priority against 8 control - and it goes the **wrong way**: priority
0.03, control 0.12. Every stratum supporting the lift has a control cell of ONE
or TWO companies.

Significance over the whole thing: 18 flagged companies of 85, control drew 17 and
caught 2 against an expected 3.60. **P(control catches <= 2) = 0.240.**

So the honest verdict after three batches and 85 companies is that **the priority
engine has not been shown to beat chance.** The one stratum large enough to speak
inverts, and the aggregate lift is carried by single-company control cells.

That is not a reason to abandon it - a priority engine can be worth having for reasons
other than flag discovery, and 85 companies with 18 flag events is a thin base for any
conclusion. It is a reason to stop quoting "2.38x" as if it meant something.

## What would actually settle it

The flag rate is roughly 0.2 per company, so detecting an arm effect of the size
plausibly on offer needs several hundred companies, not 85. Two cheaper options:

1. **Test priority against a within-industry random control on a single large
   industry.** `regional_banking` has 89 companies in the book and 39 researched. Its
   current answer is negative; finishing it would give one clean, adequately powered
   stratum instead of eight underpowered ones.
2. **Change what is being counted.** Flags are rare and mostly industry-determined.
   Priority might be measured better on something denser - coverage achieved per search,
   or the size of the SG/BQ disagreement it surfaces.

## Moat trajectory against the financial history

Three more: **DINO, WBS, WU**. Running total across all batches is eleven.

## Status

127 of the 226 industry-covered companies researched. Nothing promoted, `promoted`
remains false, and none of this is evidence about future returns.
