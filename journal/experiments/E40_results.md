# E40 results - generous, or informative?

Paired on **873 companies** all three lanes have scored (control lane at 875 and still running). Registered at `journal/experiments/E40_generous_or_informative_preregistration.md`.

## D1 / D2 - does each dimension still discriminate?

Modal share = the share of companies landing on that dimension's most common score. High means the question stopped separating anyone.

| dimension | qwen-v1 modal / stdev | LFM2.5 modal / stdev | qwen-structured modal / stdev |
|---|---:|---:|---:|
| `technological_advantage` | 0.246 / 1.436 | 0.474 / 0.94 | 0.258 / 1.442 |
| `economies_of_scale` | 0.407 / 0.872 | 0.565 / 0.665 | 0.411 / 0.85 |
| `switching_costs` | 0.385 / 0.957 | 0.647 / 0.655 | 0.386 / 0.938 |
| `network_effects` | 0.399 / 1.828 | 0.541 / 0.914 | 0.419 / 1.894 |
| `intellectual_property` | 0.305 / 1.165 | 0.386 / 1.252 | 0.287 / 1.211 |
| `brand` | 0.315 / 1.074 | 0.458 / 0.894 | 0.317 / 1.12 |
| `regulatory_barriers` | 0.342 / 1.052 | 0.43 / 1.0 | 0.366 / 0.993 |
| `manufacturing_complexity` | 0.311 / 1.201 | 0.364 / 1.175 | 0.283 / 1.23 |
| `distribution` | 0.41 / 0.807 | 0.472 / 0.832 | 0.438 / 0.808 |
| `customer_relationships` | 0.326 / 1.034 | 0.385 / 0.924 | 0.336 / 1.015 |
| `data_advantages` | 0.342 / 1.361 | 0.36 / 1.109 | 0.314 / 1.484 |

Mean modal-share gap, candidate minus incumbent: **+0.118**. The candidate is the more concentrated lane on **11** of 11 dimensions.

## D3 - the fills, which are the whole question

Dimensions the incumbent abstained on and the candidate answered, against the dimensions both answered:

| | n | modal value | modal share | stdev | mean |
|---|---:|---:|---:|---:|---:|
| **fills** | 3736 | 3 | **0.328** | 1.07 | 2.331 |
| both scored | 5844 | 3 | **0.324** | 1.05 | 3.032 |

Modal-share gap: **+0.004**.

## D4 - does the evidence verify?

SG only: `parse_sg` checks each quote for containment in the evidence pack per sub-test, so this is the one place a citation from outside the filing shows up as a number.

| lane | scored SG sub-tests | unverified |
|---|---:|---:|
| qwen-v1 | 4032 | 0.5% |
| LFM2.5 | 5219 | 9.7% |
| qwen-structured | 4034 | 0.1% |

**The composition objection, answered.** The candidate scores more SG sub-tests, and the extra ones sit where the pack is thin - so the rate above could be the mix rather than the model. It is not:

| SG sub-tests | n | qwen-v1 unverified | LFM2.5 unverified |
|---|---:|---:|---:|
| **scored by BOTH lanes** | 6758 | 0.5% | **8.0%** |
| scored by the candidate only | 2028 | — | 13.0% |

On the **same sub-tests, same filings**, the candidate's citations fail containment about **sixteen times as often**. The fills are worse still, but the gap does not depend on them.

## D5 - does the judged half order companies like the auditable half?

| lane | Spearman(mean scored moat dimension, `quant_only_50`) |
|---|---:|
| qwen-v1 | 0.267 |
| LFM2.5 | 0.214 |
| qwen-structured | 0.285 |

The two halves measure different things, so this is a sanity anchor and not a quality test: a lane whose judged half is noise would show ~0, and a lane that merely re-derives the accounting would show a lot.

## Reading

**D1/D2 confirmed.** The candidate is the more concentrated lane on **11 of 11** dimensions, mean modal-share gap **+0.118**. Each individual moat question separates companies less than it did.

**D3 REFUSED, and the candidate deserves the credit.** I predicted the fills would pile onto one value - a default wearing a judgement's clothes - by at least 15pp. The gap is **+0.004**: the dimensions it answered where the incumbent abstained are spread just as widely as the ones both answered. **The extra coverage is not a constant.**

**D4 confirmed, and it is the finding that matters.** SG evidence that fails containment: qwen-v1 **0.5%**, LFM2.5 **9.7%**, qwen-structured **0.1%**. The bar is lenient - a quote fails only when **fewer than 60% of its four-letter-plus words appear anywhere in the whole evidence pack**, so a paraphrase built from the filing's own vocabulary passes it easily. The candidate fails it more than **ten times as often as either qwen lane**. Roughly one SG citation in ten points at text that is not in the filing it was given.

**D5.** All three land in the registered 0.1-0.4 band, but the candidate is the lowest (qwen-v1 0.267, LFM2.5 0.214, qwen-structured 0.285). Its judged half tracks the auditable half least closely. That is not by itself bad - the halves ask different questions - but it removes the easiest benign explanation for the extra points.

**So: more answers, genuinely varied answers, less discriminating per question, and a ten-fold higher rate of citations that are not in the filing.** That is not a model that is 'just better'. It is a model that is more willing, and willingness is exactly what a fabrication check is for.

## What this cannot say

Which lane is **better**. Better means the score predicts something, and this repo has no forward-return grader. E40 can say whether the extra answers carry information; it cannot say whether they are right. `promoted` stays false.
