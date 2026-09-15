# E34 - "did not repurchase" is a fact, not a gap

Pre-registration written 2026-08-25, **before any scoring code changes**. Raised by the
coverage diagnosis behind E33: of the 314 companies at `INSUFFICIENT_DATA`,
`mg_buyback_discipline` is `no_data` for **268** of them with the generic reason
`"input unavailable"`, worth 2 points each.

## The question

`clab/scoring/mg.py` scores two sibling capital-allocation sub-tests from filed cash-flow
tags, and they treat absence in **opposite** ways:

| sub-test | when the input is absent |
|---|---|
| `mg_ma_track_record` | **scores 2** - *"no acquisitions and no impairments in the trailing year"* |
| `mg_buyback_discipline` | **`no_data`** - *"input unavailable"* |

A company that did not acquire anything is credited with a clean M&A record ten lines
above a company that did not repurchase anything being told we could not measure it.
Both absences are the same kind of fact: the cash flow did not happen.

## What is already measured, before this is registered

* **268** companies read `no_data` on `mg_buyback_discipline`; 217 on
  `mg_reinvestment_quality`. Together 485 sub-tests.
* The tag chain is **not** the cause and that was checked first. A/B over 240 cached
  filings: adding `PaymentsForRepurchaseOfEquity` and friends as extra chain members
  changed 50 filers but **rescued only 6** - the other 44 were existing values *perturbed*,
  one by 19%. Restricting it to a substitute that fires only when the primary series is
  empty rescued **0**, because those filers lack four consecutive quarters for a TTM. **So
  the absent buyback tag is a real absence, not a retrieval gap**, and no chain change is
  proposed. That measurement is why this experiment is about semantics rather than tags.
* `dilution_yoy` became usable **today**. It was broken until this morning's E33 fix -
  3.1% of companies earned its point, now **78.7%** - so "no buybacks **and** a flat or
  shrinking share count" can be distinguished from "no buybacks **while** diluting" for
  the first time.

## The change

When `buybacks_ttm` is absent **and** the company is not otherwise unmeasurable, score
`mg_buyback_discipline` from the share count instead of abstaining:

| observed | reading | points (of 2) |
|---|---|---|
| no buybacks, share count **flat or shrinking** (`dilution_yoy <= 0`) | did not need to repurchase and did not dilute | 2 |
| no buybacks, dilution **inside** the tolerated band (`0 < dilution_yoy <= BS_DILUTION_BANDS[1]`) | ordinary share-based compensation, not funded by buybacks | 1 |
| no buybacks, dilution **above** it | issuing shares and not offsetting it | 0 |
| **`dilution_yoy` also absent** | genuinely unmeasurable | **`no_data`, unchanged** |

The last row is the one that keeps this honest: this converts *"we could not measure it"*
into a score **only where a second measured series answers the question**. It is not a
default and it is not a floor change.

`mg_reinvestment_quality` is **NOT** in scope. Its input is capex, capex is filed by 95%
of filers, and a company with no capex line is a different and rarer case that this
argument does not cover. Doing one and saying so beats doing both and arguing later.

## Pass criteria, fixed now

| | passes if |
|---|---|
| **P1** | The sibling asymmetry is genuine - `mg_ma_track_record` really does score its analogous absence. Verified above; restated here so the whole argument is falsifiable in one place. |
| **P2** | **No company gains points where `dilution_yoy` is absent.** A company with neither series must stay `no_data`. This is the criterion that separates a measurement from a default. |
| **P3** | **Direction is not uniformly favourable.** If every affected company gains 2 points, the rule is a gift rather than a measurement. At least 15% of them must score 0 or 1. |
| **P4** | **Within-sector Spearman of `composite_strict` stays above 0.98** - E12's P4 duty. This should reweight, not reorder. |

**P2 and P3 are binding.** If P3 fails - if the rule turns out to hand almost everyone
full marks - the honest conclusion is that "no buybacks" is not informative and the
sub-test should stay `no_data`.

## Prior, stated before computing

I expect **roughly 200-260 of the 268** to gain a score, most of the rest lacking
`dilution_yoy` too. I expect the distribution to be **skewed toward 2 points** - most
S&P constituents are not diluting - but for **20-35%** to land at 0 or 1, which would
clear P3.

I expect **fewer than 40 companies to gain a band**, because 2 points on a 94-point
framework moves coverage by about 2 percentage points and the median
`INSUFFICIENT_DATA` company sits at 0.750 coverage, five points below the gate. **Most of
the 268 will still be unbanded afterwards**, and saying so now stops a small number being
reported later as a disappointment or dressed up as a success.

## What this cannot establish

Nothing here tests whether any of it predicts anything. There is no forward-return grader
- it needs ~50 weekly snapshots and the `as_first_filed` view, and **5** exist. This
changes what a few hundred companies are scored on with **no way to check whether the new
scores are better**, only whether they are more internally consistent. `promoted` stays
false.

**And it changes the framework**, so the snapshot series is discontinuous at this date for
the affected companies - unlike E33's fixes, which corrected arithmetic and display and
left the framework identical.

## Outputs

`journal/experiments/E34_results.md`, carrying P1-P4, the four required reports (coverage
per sector, band changes both directions, within-sector Spearman, and the count still
`INSUFFICIENT_DATA` with its reason breakdown), and the prior scored honestly.
