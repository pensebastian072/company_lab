# E47 - Utilities is complete, and the external layer cannot rank it

59 companies, request `a9dcab461a277de4f72a`, plus 7 new industry objects. Second sector
finished at 100%. Verified against the store, not taken from the report.

## The delivery

| | |
|---|---|
| Phase A | 7 industry objects, 35 claims, all VERIFIED_LOCAL |
| Phase B | 59 accepted, 0 rejected |
| claims | 708 from 122 URLs, **708 of 708 VERIFIED_LOCAL** |
| non-UNKNOWN fields | 433, all citation-backed |
| UNKNOWN | 275, all with blocking claims, zero gaps |
| searches | 266, against a 400-500 budget |

Five batches now with zero rejections, zero demotions and zero UNKNOWN gaps. HE and PCG
correctly carry peer-relative wildfire risk - the two SEVERE readings in the sector.

## Four fields are dead in this sector, and that is the correct answer

```
field                         utilities (59)   energy (71)
current_moat_strength                 59            71
industry_structural_growth            59            71
demand_visibility                     59            71
pricing_power                         59            66
technology_risk                       59            70
disruption_risk                       59            69
regulatory_risk                       59            68
competitive_position                  20            25
competitive_position_trend             0            15
moat_trajectory                        0            35
company_specific_capture               0            29
market_share_direction                 0             0
```

A rate-regulated monopoly has no contestable share, no competitive position trend against
peers it does not compete with, and no company-specific capture of an industry growth rate
its commission sets. Codex returned UNKNOWN with blocking claims rather than forcing a
non-comparable metric, which is right. **The fields are not broken; they are inapplicable,
and the vocabulary has no way to say so.**

That distinction matters because `score.py:217` computes `strict = earned / applicable`
and counts an unevidenced dimension in `applicable`. So four inapplicable fields cost
utilities points. External scores run 28.5-44.0 against Energy's 22.5-78.0 - the same
structural shift the measured half shows on VA and BS, now repeated in the external layer.

## The E30 symptom, in the external layer

This is the finding. Of the eight fields that DID resolve, most take one value:

```
technology_risk             MODERATE 59                      <- literally constant
disruption_risk             MODERATE 57, SEVERE 2                    97% one value
regulatory_risk             MODERATE 57, SEVERE 2                    97%
demand_visibility           HIGH 54, MODERATE 5                      92%
pricing_power               MODERATE 52, LOW 7                       88%
industry_structural_growth  MODERATE 44, FLAT 9, HIGH 6      <- industry-determined
current_moat_strength       MODERATE 34, STRONG 25           <- the only one that splits
competitive_position        UNKNOWN 39, LEADER 9, SN2 9, CHALLENGER 2
```

And the resulting score barely separates the sector:

```
                distinct values   sd     range   mode share
utilities (59)        14         4.67    15.5      37%   <- 22 companies tied at 32.5
energy    (71)        47        12.98    55.5      18%
```

**708 verified claims and 266 searches produced a sector ranking that puts 22 of 59
companies on the identical score.** Its discriminating power rests on one field
(`current_moat_strength`, 34/25) plus a `competitive_position` that is 66% UNKNOWN.

**This is not Codex failing the instruction. It is Codex following it correctly.** The
peer-relative rule says a company must be worse than its industry peers for a risk flag to
fire. In a sector where every member faces the same regulator and the same technology,
peer-relative honestly returns "everyone is MODERATE". The rule was written to stop the
E44 pathology of 39-of-40 flagging; here it produces 59-of-59 not flagging, and both are
the same rule reporting the truth about a homogeneous population.

So the general result: **peer-relative risk fields carry information in heterogeneous
industries and are structurally empty in homogeneous regulated ones.** That is worth
knowing before spending the budget on the next regulated sector.

## What this says about the plan's framing

The E47 plan said "what the external layer adds here is evidence, not a rescue". The
evidence arrived and is impeccable - 708 of 708 verified. But as a *ranking* input in
Utilities it carries almost nothing, and the plan should have predicted that: a sector
whose measured half is compressed because its companies are structurally alike will have
an external half compressed for the same reason. Homogeneity is not a measurement problem
to be solved by adding a third source of truth.

## E48 verification - and one hypothesis of mine that is refuted

Codex's E48 numbers reproduce. A_local to B_evidence: Spearman 0.7889, Kendall 0.6451,
median move 7 of 71, `ORDER_CHANGING`. B_evidence to C_full: 0.9173, median move 3,
`ORDER_PRESERVING`. Pre-registered thresholds, written before the computation.

Seeing BKR fall from rank 2 to 30 and SLB from 10 to 35 while AESI rose 30 places, I
predicted the evidence score was tilting toward small comparable pure-plays and against
diversified majors that rank-order against nobody - the VRT bug in a new place.

**Measured, and it is wrong:**

```
Spearman(external_coverage, log market cap) = +0.218
Spearman(rank move A->B,    log market cap) = +0.129

tercile    n   median coverage   median move
small     24        0.56           -3.25
mid       23        0.62           -1.00
large     23        0.75           +2.00
```

Coverage rises with size and large caps moved UP on median. There is no size tilt, and the
majors that fell did so for an ordinary reason: BKR and SLB sat at ranks 2 and 10 locally
on middling 0.62 coverage, so a blend pulled them toward the middle, while WHD (0.95) and
AESI (0.83) were pulled up from low local ranks. The biggest movers are wherever local
rank and evidence coverage disagree most, which is what a blend does.

What survives is narrower and still worth acting on: **`external_coverage` is a property
of how researchable a company is, not of the company**, and in the conviction score it
currently reorders more than every substantive conclusion combined. Whether it belongs
there at all is now a measured question rather than a design preference.

One confound in the decomposition, which does not overturn it. B adds four dense terms
(coverage, confidence, depth, core fields) and C adds two sparse ones (moat trajectory,
flags) - and in Energy `moat_trajectory` resolved for only 35 of 71. So part of "evidence
reorders more than conclusions" is that there were not many conclusions to reorder with.
That is the same finding in different clothes, not a rescue of it.

## Neutralization decision

Recorded, not implemented: `industry_id` when n>=4, then GICS `sub_industry` when n>=5,
then sector. It changes the peer key for 56 of 59 Utilities companies. No predictive
claim attaches to it. Note the Utilities consequence before shipping it - under
`industry_id`, `renewable_electricity` (2) and the AES singleton fall through to
`sub_industry` and then to sector, so the fallback chain does the work for exactly the
buckets the taxonomy fix created.

## Status

Two sectors complete: Energy 71/71, Utilities 59/59. 238 companies researched. Corpus
unverifiable rate 0.13% (4 of 3,033 claims). Nothing promoted; `promoted` remains false,
and none of this is evidence about future returns.
