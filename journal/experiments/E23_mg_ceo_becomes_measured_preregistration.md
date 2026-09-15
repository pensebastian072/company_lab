# E23 - the CEO block stops asking a 10-K questions a 10-K does not answer

Pre-registered 2026-08-22, before the scoring change. Decision taken by the user after
E22; the diagnosis below was measured first and offered as an argument against cutting,
and the user chose to cut anyway with the evidence in hand.

## What E22 found

MG failed the stability test: year-over-year Spearman **0.29** against a registered bar of
0.5, while SG (0.60) and BQ (0.63) passed. My registered prediction had MG stable and BQ
the shaky one. Wrong on both.

The mechanism is not "management quality is unmeasurable". It is that **three of the five
LLM attributes are proxy-statement facts** and the evidence pack is built from the 10-K:

| attribute | scored across ~200 companies | lives in |
|---|---:|---|
| industry_expertise | 177 | 10-K business description |
| execution_history | 67 | 10-K MD&A |
| tenure | 14 | **DEF 14A** |
| ownership | 10 | **DEF 14A** |
| founder_led | 9 | **DEF 14A** |

The median company gets **2 of 5** scored, so 0.29 is the year-over-year correlation of
one or two noisy items, not of a considered judgement about management.

## The change

**The five LLM CEO attributes are removed. The CEO block becomes fully measured.**

`MG_CEO_ATTRIBUTES` keeps only `hits_guidance` (beat rate over the reported surprise
history) and `navigated_downturns` (revenue and margin behaviour through the company's own
worst historical decline). Both come from filed data and neither involves a model.

* The CEO block **stays worth 8 points**, now carried by two measured attributes instead
  of seven mixed ones. The alternative - shrinking it to 8 x 2/7 and leaving 5.7 points
  permanently NO_DATA - would drop every company's coverage by that amount and push
  borderline names under the 0.80 band gate. That is the mistake E19's first version made,
  and it is not repeated.
* `MG_MIN_ATTRIBUTES_SCORED` drops from 4 to **2**, keeping E19's shape: full credit at or
  above the threshold, proportional below, never a cliff.
* MG's own docstring and `CLAUDE.md` change with it. **The framework is no longer 50/50.**
  It becomes roughly **44 judgement / 56 measured**, and saying "half the score is an LLM"
  after this would be false.

## What it costs, measured before the change

* The LLM CEO attributes currently contribute a mean of **2.77 raw points** per company
  (median 3, max 10) into the 8-point block. That contribution disappears.
* The measured attributes are well populated: **1,350 of 1,500 companies have both**, 142
  have one, 8 have neither. So the block does not collapse - it narrows.
* Companies with **both** measured attributes and few LLM ones will barely move.
  Companies that were leaning on LLM attributes lose points.

## What must be reported afterwards

1. Band changes in both directions, with counts.
2. Within-sector Spearman of the new composite against the old, over every company in the
   sector - E12's P4 duty.
3. The new judgement/measured split, stated as a number, in the workbook's Meta sheet.

## Prediction, stated before running

**More movement than E21, less than the share-count fix.** Median composite falls by
roughly 1-2 points because the mean 2.77 LLM raw points map to about 1.5 of the 8-point
block. **20-60 band changes, skewed downward**, since almost nothing gains from this.
Within-sector Spearman stays **above 0.97** - this removes a component from everyone
rather than reordering anyone.

If band changes come back above 100, the CEO block was carrying more weight than the
E22 evidence suggests, and the change should be reconsidered rather than accepted.

## What this does NOT establish

Nothing about returns. It removes an input measured to be unstable; it does not make the
remaining ranking predictive, and E13 still has the measured-half top-20 at -0.5%
annualised net against SPY. `promoted` stays false.

## The road not taken, recorded

Pointing the CEO attributes at the **proxy statement** would have tested whether the
instability is a source problem rather than a model problem - the filings are on the
submissions feed (23 for AAPL, 24 for FDX, 6 for JPM) and reachable with the machinery
E22 already uses. That option was offered with these numbers attached and declined in
favour of the simpler cut. If management quality is ever wanted back, that is where it
starts, and it starts with a fresh registration rather than by reverting this one.
