# E18 - does targeted retrieval repair SG and MG, the way it repaired BQ?

Pre-registered 2026-08-18, **before the module is written**, after E15/E16/E17 settled the
BQ case. BQ is proven; SG and MG are not, and the coverage projection that motivates the
whole repair pass rests mostly on them:

| repaired | companies >= 90% coverage | >= 80% | median |
|---|---:|---:|---:|
| nothing (today) | 426 | 872 | 0.82 |
| BQ only | 527 | 1,108 | 0.86 |
| BQ + SG | 825 | 1,258 | 0.91 |
| BQ + SG + MG | **1,198** | 1,440 | 0.96 |

Adopting SG and MG on the strength of the BQ result would be exactly the move E15 was
written to prevent. So they are measured first, on their own bars.

## What is different about SG and MG

* **SG** has six sub-tests (`rubric.SG_SUBTESTS`, 4/4/4/3/3/2 points) and **already asks
  for a per-sub-test evidence quote**, which BQ did not. Its nulls are therefore not a
  quoting problem; they are a retrieval problem or a genuine absence.
* **MG** has five LLM attributes (`rubric.MG_CEO_ATTRIBUTES` where source is `llm`, 2
  points each) behind a floor of `MG_MIN_ATTRIBUTES_SCORED = 4`, so like BQ it can lose
  its whole CEO block to abstention. Its other 9.4 points are measured from filings and
  are untouched by any of this.
* Both are read through `clab/scoring/sg.py:read_llm_subtests`, so a repair that merges
  cleanly for one merges for the other.

## Design

Identical in shape to E17, which is the arm that passed with a citation requirement:

* one embedding query **per null sub-test**, 2 chunks each, from the same chunk pool
  `evidence.build_pack` assembles - the query is the only thing that differs from
  production;
* **one call per component**, carrying only that company's nulls;
* every recovered sub-test must carry a **verbatim quote**, and a sub-test whose quote
  does not verify is **dropped, not scored**. Three gates are recorded - strict substring,
  token overlap >= 0.90, and production's >= 0.60 - so the yield of each is visible.

Sample: the same 59 under-floor + 20 control companies as E16 and E17, so all four
experiments compose into one picture of the same universe slice.

## Pass criteria, fixed now

| | passes if |
|---|---|
| **S1** | Median **availability gain** on the sample, counting only strict-gated repairs, is **>= 3 points** for the component. Points, not sub-tests: SG's sub-tests are worth 2-4 each and MG's 2, so a sub-test count would flatter SG. |
| **S2** | **Quote yield per sub-test is reported**, with the count of scores offered with no quote at all. No bar - E17's yield (33 of 73 proposed) is the thing to compare against, and a bar here would invite tuning. |
| **S3** | **Zero control regressions.** Guaranteed by construction (a repair only fills a null); a failure is a wiring bug, not a result. |
| **S4** | **<= 40 s per company** for both components together, so a 1,000-company pass stays inside one overnight window. |

**A component that fails S1 is not included in the production pass.** Partial adoption -
SG in, MG out, or the reverse - is the expected outcome, not a disappointment.

## Prediction, stated before running

**SG fails S1 and MG passes.** SG already demands a quote per sub-test, so its nulls are
the ones the model could not evidence even when asked properly - re-asking with a better
query should move it least. MG's five attributes are biographical (founder-led, tenure,
ownership, execution history, industry expertise) and a 10-K states those plainly in the
directors and executive-officers discussion, which a single MG query about "management
experience, capital allocation, acquisitions" retrieves badly.

If that is right, the honest headline is that the coverage projection above is
**optimistic for SG**, and the realistic ceiling is nearer the BQ+MG line than the
BQ+SG+MG line.

## What this cannot establish

Nothing about whether SG or MG predicts anything. A verified quote means the sentence is
in the filing, not that the score is right. There is no forward-return grader.
`promoted` stays false, and more coverage means more companies get a band, not that the
bands are correct.

## Outputs

`journal/experiments/E18_results.json` / `.md`, per sub-test and per gate, never a single
pooled number.
