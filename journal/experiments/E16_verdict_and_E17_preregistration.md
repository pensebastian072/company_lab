# E16 verdict: the repair pass works, and my own Q2 could not have measured what it claimed

Run 2026-08-18, 59 under-floor companies stratified in proportion to where the under-floor
population lives, plus 20 controls. Raw records in `journal/experiments/E16_raw/`.

| | measured | bar | |
|---|---|---|---|
| Q1 under-floor companies clearing the floor | **10 -> 31 of 59 (52.5%)** | >= 35% | **PASS** |
| Q2 unverified quotes, repair call only | 1.92% (1 of 52) | <= 1.0% | **FAIL** |
| Q3 controls losing a dimension | 0 | 0 | **PASS** |
| Q4 `economies_of_scale` recovered | 67.8% | >= 60% | **PASS** |

Median dimensions scored among the under-floor sample went **5 -> 6**. Median repair cost
**23.9 s** per company, so the full 463-company pass is about **3 h** of GPU.

## Q2 failed on a criterion that could not succeed

BQ emits **one** evidence quote per call. With 52 repair calls the only reachable outcomes
are 0.00% or >= 1.92%; nothing can land inside the 0-1% band the criterion asked for. The
single flagged quote gives a Clopper-Pearson 95% interval of **0.05% - 10.26%**, which
neither confirms nor refutes the 1% bar, and does not separate this from the incumbent's
0.28%.

Even a perfect zero would only have proven **<= 6.85%**. The criterion was mis-specified
when I wrote it, and reporting it as a clean FAIL would be as misleading as waiving it.
**It is recorded as FAIL and replaced, not waived** - E17 below changes the instrument
rather than the bar.

One more fact that a rate hides: the flagged company is **PBF Energy, and it was also the
flagged company in E15**. The same filer produces an unverifiable quote on two independent
runs. That is not noise; it is one company where retrieval and the model interact badly,
and it is worth more than the percentage.

## Q5 - the "technicality" worry did not materialise

The fear registered in advance was that every newly cleared company would clear on the
same six dimensions, with `economies_of_scale` as a rubber-stamp sixth. Composition of the
21 newly cleared companies:

| dimension | appears in |
|---|---:|
| switching_costs | 21 of 21 |
| customer_relationships | 20 of 21 |
| economies_of_scale | 18 of 21 |
| regulatory_barriers | 18 of 21 |
| brand | 15 of 21 |
| distribution | 14 of 21 |
| intellectual_property | 9 of 21 |
| technological_advantage | 7 of 21 |
| manufacturing_complexity | 4 of 21 |
| network_effects | 2 of 21 |
| data_advantages | 2 of 21 |

The tail varies company to company. `economies_of_scale` is the marginal sixth dimension
for many of them - 18 of 21 - so the repair is doing real work rather than rubber-stamping,
but the honest statement is that **without `economies_of_scale` most of these companies
would still be under the floor.**

What the repair call recovered overall: `economies_of_scale` 40, `manufacturing_complexity`
13, `data_advantages` 3, `network_effects` 2. The E15 finding replicates exactly - one
dimension was a retrieval failure and three are not.

## A separate fact worth its own line

Re-running the **unchanged** production prompt on a fresh pack moved 12 companies up, 9
down and left 19 unchanged, and **10 of the 59 under-floor companies cleared the floor on
the base call alone**, with no repair. Part of the 463 is run-to-run variance at
temperature 0.1, not structure. Any claim that the repair "recovered" a company must be
measured within a run, which is how Q1 is computed.

---

# E17 - stop measuring fabrication after the fact; make it impossible to enter the score

Pre-registered 2026-08-18, before the prompt or gate is written.

## Why the instrument changes

A post-hoc rate cannot police fabrication at this sample size, as Q2 just demonstrated:
even 208 quote slots put a single flagged event's interval at 0.01% - 2.65%. So the
defence moves from measurement to **mechanism**: the repair call must supply a **verbatim
quote per recovered dimension**, and a dimension whose quote does not verify against the
pack is **dropped**, not scored. Fabrication then cannot reach the composite at all, and
the thing being measured becomes the **yield** - how many recovered dimensions survive
verification - which is estimable at n = 52.

## The second thing this measures, which matters more

Production's fabrication defence is `_token_overlap(quote, pack) >= 0.60` - a **token-set**
check. A paraphrase built from the pack's own vocabulary passes it; only wholesale
invention fails. E17 scores every recovered dimension under three gates and reports all
three:

* **strict** - the quote appears in the pack as a substring after whitespace normalisation;
* **tight** - token overlap >= 0.90;
* **production** - token overlap >= 0.60, today's rule.

If production's gate keeps nearly everything the strict gate rejects, that is a finding
about the **existing** system - one that stands whatever happens to the repair pass.

## Method

Same 59 under-floor + 20 control companies. The base call is **not re-run**; each company's
production-call result is read from its `E16_raw` record, which was generated today from
the same packs. Only the repair call is new. ~52 calls, ~25 s each, about 25 minutes.

## Pass criteria, fixed now

| | passes if |
|---|---|
| **R1** | Floor clearance among the under-floor sample, counting only dimensions that pass the **strict** gate, is **>= 35%** (E16 reached 52.5% with no verification at all). |
| **R2** | **Yield is reported per gate and per dimension**, no bar. A yield near 100% under the strict gate is a red flag to be investigated, not a win. |
| **R3** | **No control loses a dimension.** Guaranteed by construction; a failure is a wiring bug. |
| **R4** | `economies_of_scale` recovery under the **strict** gate is **>= 50%** (E16: 67.8% unverified). |

R1, R3 and R4 must pass for the repair pass to reach production. R2 has no bar because its
purpose is to describe, and a criterion with a bar would invite exactly the threshold
tuning this project refuses.

## Prediction, stated before running

The strict gate **kills 30-60%** of recovered dimensions - a 7B model paraphrases rather
than copies, and `_RULES` asks for a verbatim quote that it only partly honours. I expect
the production 0.60 gate to keep **over 90%** of what strict rejects, which would mean the
current defence catches invention but not recombination. R1 and R4 I expect to pass with
less room than E16 suggests.

## What this cannot establish

Nothing about whether BQ predicts anything. A verified quote means the sentence exists in
the filing, not that the score is right, and not that a company with six dimensions is
better assessed than one with five. There is no forward-return grader. `promoted` stays
false.
