# E12 — is the BQ floor measuring an absent moat, or an inapplicable question?

Pre-registration written 2026-08-16, **before any rubric, prompt or threshold is
changed**. E11 is reserved for the E10 follow-up (is the small-cap insider edge
investable); this is a separate question about the scoring framework itself.

## The question

Rubric A2 awards BQ points only when at least **6 of its 11 moat dimensions** are
scored. **254 of 1,005 companies (25.3%) sit under that floor** and therefore score
**0 of 15** on Business Quality — not a low moat score, no score at all, which then
propagates into `composite_strict` and the coverage figure.

The floor was written to stop a moat verdict resting on two dimensions. The question is
whether the companies under it are companies the model could not assess, or companies
whose moat simply does not live in 6 of these 11 dimensions.

## What is already measured, before this is registered

Stated plainly so nothing below is presented as a prediction that was really a
retrodiction. All of the following was computed on 2026-08-16 and **motivated** this
pre-registration:

**The degraded-Ollama hypothesis is mostly wrong.** The overnight re-run covered 172 of
the 215 flagged companies before it was stopped at 03:52. Against the floor now:

| | n | still below 6 | median dims |
|---|---|---|---|
| re-run on a healthy server | 172 | **139 (80.8%)** | 5 |
| never re-run | 43 | 39 (90.7%) | 4 |

Re-generating on a healthy server moved 10 percentage points. It did not move the floor
problem. The population under the floor is **stable**, which is the condition the
2026-08-15 handoff named in advance as the one where the floor must not be lowered.

**Every null is a deliberate abstention, not a failure.** Across the 1,005 best-per-CIK
BQ payloads: `parse_ok` is **1005/1005**, **0** of the 3,981 nulls came from a rejected
out-of-range value, and raw responses run 933–2,906 characters, so nothing is truncated.
The nulls are the model returning `"score": null` with an empty rationale — exactly what
`prompts._RULES` instructs: *"Score ONLY from the material above. If it does not support
a sub-test, use null"*, reinforced by *"If you cannot quote it, use null."*

**The floor is therefore in direct tension with the prompt.** The prompt rewards
abstention; the floor punishes it. Nothing is malfunctioning — two correct components
disagree.

**Abstention is wildly uneven across dimensions** (share of the 1,005 with no score):

| dimension | null | | dimension | null |
|---|---|---|---|---|
| network_effects | **81.7%** | | intellectual_property | 23.9% |
| manufacturing_complexity | **71.2%** | | distribution | 21.7% |
| data_advantages | **70.9%** | | regulatory_barriers | 17.7% |
| economies_of_scale | **53.6%** | | brand | 14.5% |
| technological_advantage | 25.2% | | switching_costs | 9.7% |
| | | | customer_relationships | 6.1% |

**And it is sector-structured** (% of companies under the floor, and null rate for the
four worst dimensions):

| sector | n | below floor | net.eff | mfg.cplx | data.adv | econ.scale |
|---|---|---|---|---|---|---|
| Real Estate | 66 | **65.2%** | 93.9 | 97.0 | 92.4 | 74.2 |
| Energy | 40 | **55.0%** | 90.0 | 72.5 | 82.5 | 55.0 |
| Financials | 162 | 30.2% | 81.5 | 93.2 | 58.6 | 72.2 |
| Utilities | 54 | 25.9% | 94.4 | 96.3 | 72.2 | 25.9 |
| Information Technology | 135 | 23.0% | **80.0** | 60.0 | 75.6 | 68.9 |
| Industrials | 200 | 21.5% | 81.0 | 56.5 | 71.0 | 52.0 |
| Consumer Discretionary | 103 | 21.4% | 75.7 | 72.8 | 64.1 | 47.6 |
| Health Care | 108 | 15.7% | 84.3 | 63.0 | 75.9 | 51.9 |
| Communication Services | 35 | 14.3% | 40.0 | 74.3 | 40.0 | 42.9 |
| Materials | 58 | 8.6% | 79.3 | 41.4 | 74.1 | 22.4 |
| Consumer Staples | 43 | 7.0% | 93.0 | 74.4 | 81.4 | 14.0 |

## Two competing explanations, which need opposite fixes

**H1 — inapplicability.** The dimension is genuinely absent for the business. A REIT has
no manufacturing complexity (97% null); a utility has no network effects (94%). Under H1
the denominator is wrong and the honest fix is the same machinery the measured half
already uses: `NOT_APPLICABLE`, which per the existing rule requires **both profile
nomination AND actual absence**.

**H2 — the evidence pack cannot support the question.** The pack is three 10-K sections
(business, MD&A, risk factors) and the prompt demands a quotable basis. Under H2 the
dimension is applicable but unevidenced, and changing the denominator would **launder a
retrieval failure into a scoring rule**.

**The tell that H2 is live, and that this is not purely an applicability story:
`network_effects` is 80.0% null in Information Technology and 84.3% in Health Care.**
Software and platform companies are the archetypal network-effect businesses. A
denominator fix that drops `network_effects` globally would delete a real signal in the
one sector where it discriminates most.

So the answer is almost certainly **both**, in different proportions per dimension, and
the work is separating them — not choosing one.

## The trap this must avoid

Lowering the floor from 6 to 4 would make ~254 companies score tomorrow. It is one line,
it makes every chart look better, and it is precisely the threshold-tuning this project
refuses. **A floor is not evidence. Moving a floor until the output looks complete is
fitting the rubric to the data.** The floor stays at 6 of the *applicable* dimensions
under every outcome below.

## Sequencing constraint, fixed now

**E12 must not run before E07.** The model bake-off is already pre-registered and
invalidates the whole ~1,000-company cache; the prompt-overflow fix (every pack is
~10,000 tokens against an 8,192-token window, so the front — where the schema sits — is
truncated) invalidates it too. Abstention rate is a **property of the model and the
pack**, not of the company. A model with a larger context window, seeing a schema that
was not cut off, may abstain far less.

Fixing the denominator first would mean permanently re-shaping the rubric to compensate
for a model deficiency that a model swap removes. So:

**E07 runs first and reports the per-dimension abstention rate for every candidate model
as a first-class output, not a footnote.** E12 is then computed on the winner's cache.
If the winning model's abstention on the four worst dimensions falls below ~35%, the
floor problem has substantially dissolved and E12 reduces to the applicability question
alone.

## Pass criteria, fixed now

Computed **per sector**, never pooled — E05 already established that this score is
substantially a sector bet, and BQ availability being sector-structured is a mechanism
by which that happens.

| | passes if |
|---|---|
| **P1** | On the E07 winner's cache, the share of companies under the floor falls below **10%** overall. If so, no rubric change is made and E12 closes as "the model was the problem." |
| **P2** | For each of the four worst dimensions, abstention is **concentrated by sector** — the gap between the highest and lowest sector null rate exceeds **40 percentage points**. That is the H1 signature. `network_effects` currently fails this (40.0% to 94.4% is a 54pt spread, but the floor is 75%+ in 9 of 11 sectors), and `manufacturing_complexity` passes it (41.4% to 97.0%). |
| **P3** | A dimension may be marked `NOT_APPLICABLE` for a sector **only if** it clears P2 **and** a named, written business reason exists — the same two-part test the measured half already enforces. No dimension is dropped on its null rate alone. |
| **P4** | After any denominator change, the **rank correlation of `composite_strict` against its current value, within each sector, is reported**. A change that reshuffles the ranking inside a sector is doing more than filling gaps and must be described as such. |

**P3 is required for any change at all.** P1 alone can close the experiment with no
change, which is the outcome I would prefer.

## Prior, stated before computing

I expect **P1 to fail** — a larger context window will help, but `network_effects` being
80% null in IT looks like a retrieval and prompt problem that a bigger model does not
fix by itself, because the 10-K sections chosen rarely discuss network effects in
quotable terms. I expect **`manufacturing_complexity` and `data_advantages` to pass P2**
(clean sector structure) and **`network_effects` to fail it** (null nearly everywhere),
which would mean the honest outcome is a *sector-applicability* denominator for two
dimensions and an *evidence-retrieval* fix for `network_effects` — not a floor change,
and not a global drop of four dimensions.

Stating that now so a null is not later called expected, and so that "drop the four
worst dimensions", which is the convenient answer, has to beat a written prediction that
it is wrong.

## What this experiment cannot establish

**Nothing here tests whether BQ predicts anything.** There is no forward-return grader
yet — it needs ~50 weekly snapshots and the `as_first_filed` restatement view. A
denominator change alters the composite of 254 companies with **no way to check whether
the new scores are better**, only whether they are more internally consistent. Any
write-up must say that in those words. `promoted` stays false regardless.

## Outputs

`journal/experiments/E12_results.json` / `.md`, and a per-sector table before any pooled
number.
