# E25 - the proxy fixed availability and not reliability, so the cut goes back

Registered 2026-08-23, after E24 reported and before the code changes again. This
reinstates E23. It exists as its own entry rather than as a quiet revert because E24
promised exactly that, and because the next person to look at MG deserves to know the
proxy was tried.

## The three-step story, in order

| | question | answer |
|---|---|---|
| **E22** | is the judgement half stable year over year? | SG 0.60 and BQ 0.63 pass; **MG 0.29 fails** a 0.5 bar |
| **E23** | cut MG's five model-scored CEO attributes? | registered and coded, then reverted when the cause was found |
| **E24** | is MG unstable because it reads the wrong document? | **availability yes, reliability no** |
| **E25** | so what? | reinstate E23's cut, with E24's evidence attached |

## What E24 established

`founder_led`, `tenure` and `ownership` are DEF 14A facts, and MG's evidence pack held
only the 10-K. Putting the proxy in the pack - MG's pack only, leaving SG and BQ byte
identical - fixed the availability problem outright:

| attribute | companies scored, before | after |
|---|---:|---:|
| ownership | 4 | **163** |
| tenure | 4 | **139** |
| founder_led | 6 | **42** |

**P1 passed. P2 did not.** Year-over-year Spearman rose 0.332 -> **0.405** against a bar of
0.5, on the 73 companies present in both runs.

## Why this is not a metric problem

A 3-point ordinal scale with most mass on one value makes Spearman a weak instrument, and
that objection was raised before the final number came in. Chance-corrected agreement was
computed to test it:

| attribute | observed | chance | kappa |
|---|---:|---:|---:|
| founder_led | 0.81 | 0.55 | **0.58** |
| industry_expertise | 0.79 | 0.67 | 0.37 |
| tenure | 0.73 | 0.61 | **0.29** |
| ownership | 0.57 | 0.39 | **0.29** |
| execution_history | 0.71 | 0.65 | **0.17** |

**Tenure is the one that settles it.** How long a CEO has served is a stated fact that
increments by one a year. Reading the same proxy language twelve months apart, the model
reproduces it at kappa 0.29. That is not a missing document, an unlucky statistic or a
retrieval gap - it is the model failing to extract a fact it was handed.

`founder_led` at 0.58 is the exception, and it is the one attribute that is nearly binary
and nearly permanent.

## The change

Exactly E23's, restored:

* `MG_CEO_ATTRIBUTES` keeps only `hits_guidance` and `navigated_downturns`, both computed
  from filed data.
* `MG_MIN_ATTRIBUTES_SCORED` returns to 2.
* The CEO block stays worth `MG_CEO_POINTS`, now carried by two measured attributes. It is
  NOT shrunk to 8 x 2/7 with the remainder left NO_DATA - that would drop every company's
  coverage and push borderline names under the 0.80 band gate, which is the mistake E19's
  first version made.
* The proxy machinery **stays in the codebase**: `edgar_filings.proxy_text`,
  `evidence.proxy_pool`, and the MG-only wiring in `build_pack`. It works, it is tested,
  and it is the right foundation for anything that later wants to read a proxy. What it
  is not is a fix for this.
* The framework is **no longer 50/50** - roughly 44 judgement / 56 measured - and
  `rubric.py` and `CLAUDE.md` say so.

## What must be reported afterwards

Band changes both directions, within-sector Spearman of the new composite against the old
over every company in the sector, and the new judgement/measured split as a number in the
Meta sheet.

## Prediction, stated before running

Unchanged from E23, since it is the same change: median composite falls 1-2 points,
**20-60 band changes skewed downward**, within-sector Spearman above 0.97. Above 100 band
changes means the CEO block carried more than the evidence suggests and the change should
be reconsidered rather than accepted.

## What this does NOT establish

That management quality is unmeasurable - only that **this** model, reading **these**
documents, cannot reproduce its own answers a year later well enough to be worth 5.6
points. A different instrument (structured extraction of tenure from a table rather than
a 0-2 judgement, say) is a different experiment, and E24's plumbing is already in place
for it.

Nothing here is about returns. `promoted` stays false.
