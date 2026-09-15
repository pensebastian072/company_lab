# E17 verdict: the mechanism works, and it cuts E16's headline in half

Run 2026-08-18, 52 repair calls over the same 59 under-floor and 20 control companies as
E16. Raw records in `journal/experiments/E17_raw/`. The base call was not re-run; each
company's production result was read from its `E16_raw` record, generated the same day
from the same packs.

| | measured | bar | |
|---|---|---|---|
| R1 floor clearance, **strict** gate | **21 of 59 (35.6%)** | >= 35% | **PASS** |
| R3 controls losing a dimension | 0 | 0 | **PASS** |
| R4 `economies_of_scale`, **strict** gate | **22.4%** | >= 50% | **FAIL** |
| R2 yield per gate | reported below | no bar | described |

**The registered rule is R1 AND R3 AND R4. R4 fails, so the repair pass does not reach
production.** It stays where E15 and E16 left it: a measured, unshipped change.

## What R4 actually says about E16

E16 reported `economies_of_scale` recovered for **67.8%** of the under-floor sample, and
that number carried its whole result - E16's own composition table showed that without
`economies_of_scale`, most of the 21 newly cleared companies would still have been under
the floor. Requiring the sentence to exist in the filing takes that 67.8% to **22.4%**.

The same cut runs through the headline. Floor clearance by gate, of 59:

| | cleared |
|---|---:|
| base call alone, no repair | 10 |
| repair, no verification (E16's construction) | 22 |
| repair, production 0.60 gate | 22 |
| repair, strict substring | **21** |

E16 measured 52.5%. Read it as **35.6%**. About two thirds of what the repair pass
"recovered" could not be traced to a sentence in the evidence pack.

Note the honest shape of that: the mechanism did not fail. It did exactly what it was
registered to do - it dropped what could not be verified, and what remained still cleared
R1. What failed is the size of the effect once the unverifiable part is removed.

## R2 - and the prediction that was wrong

Registered prediction, written before the run: *the strict gate kills 30-60% of recovered
dimensions, and production's 0.60 gate keeps over 90% of what strict rejects, which would
mean the current defence catches invention but not recombination.*

| gate | dimensions kept | of 73 proposed |
|---|---:|---:|
| has_quote | 33 | 45.2% |
| production 0.60 | 33 | 45.2% |
| tight 0.90 | 33 | 45.2% |
| strict substring | 29 | 39.7% |

The first half held: strict kills 60.3%, at the top edge of the predicted band. **The
second half was wrong.** Strict rejects 44 of the 73 proposed dimensions and production
rescues **4** of them - 9%, not the 90% predicted.

The reason is the part the instrument was not built to look for. **40 of the 73 proposed
dimensions arrived with no quote at all** - the model offered a score and simply did not
cite anything. Of the 33 that did carry a quote, the median token overlap with the pack is
**1.0**: when this model quotes, it copies verbatim. It does not paraphrase.

So the failure mode is not recombination. It is **omission**, and the three gates barely
differ because they are all arguing over the same 33 quotes while 40 scores walked past
without one. That is a finding about the **existing** system and it stands whatever
happens to the repair pass: production's `_token_overlap >= 0.60` rule is a reasonable
defence against the thing that actually happens here, and the exposure worth worrying
about is a scored dimension with no evidence attached, not a cleverly worded one.

Whether production's base call has the same 40-of-73 omission rate is **not measured
here** - E17 only instrumented the repair call. That is the next question, and it is
cheap: it reads existing cache records rather than calling the model.

## What this does not establish

Nothing about whether BQ predicts anything. A verified quote means the sentence exists in
the filing, not that the score is right, and not that a company with six dimensions is
better assessed than one with five. There is no forward-return grader. `promoted` stays
false, and the 463 companies scoring 0 of 15 on Business Quality are still scoring 0.
