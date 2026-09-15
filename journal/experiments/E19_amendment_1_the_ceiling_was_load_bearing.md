# E19 Amendment 1 - the floor was doing two jobs, and I only meant to remove one

Written 2026-08-19 after measuring E19 on 899 re-scored companies, **before** the rule is
changed again. The registered prediction was wrong, and wrong in the direction that hurts
the thing the change was made for.

## What was predicted, and what happened

| | predicted | measured |
|---|---|---|
| companies gaining a band | 200-260 | **47** |
| median coverage | 0.84 -> ~0.88 | 0.84 -> **0.83** |
| companies with no band | fewer | 549 -> **561** |
| coverage >= 0.90 | more | 470 -> **254** |

The half that worked: companies with **zero** BQ fell 423 -> 234, and 47 companies that
had no band now have one. That is the cliff being removed, as intended.

The half I did not foresee: **57 companies LOST their band.**

## The mechanism

The old rule awarded **all 15 BQ points at 6 of 11 dimensions**. It was not only a cliff -
it was also a **ceiling that granted full credit for a partial read**. Proportional
availability removed both at once.

Of 1,075 companies that had full BQ availability yesterday, only 461 still do:

| new BQ availability | companies | dimensions scored |
|---:|---:|---:|
| 15 | 461 | 11 |
| 14 | 21 | 10 |
| 12 | 140 | 9 |
| 11 | 162 | 8 |
| 10 | 133 | 7 |
| 8 | 158 | 6 |

Mean loss **2.66 points**, which is ~2.7pp of coverage, which is enough to push a company
sitting at 0.88-0.91 under the 0.80 band gate once it compounds with other gaps. RJF
0.91 -> 0.79, FITB 0.90 -> 0.79, DTE 0.88 -> 0.76.

**Both readings are defensible.** A company assessed on 7 of 11 dimensions arguably never
had "full" BQ coverage, and saying so is more honest. But the change was made to stop
deleting companies, and it deleted 57 different ones instead. That is not the trade the
user asked for.

## The amendment

**Asymmetric, and it says exactly what it believes:**

* **at or above 6 of 11 dimensions - full 15 points of availability**, as before. The
  framework already held that six dimensions are enough to judge a moat; that judgement
  is unchanged and was never the problem.
* **below 6 - proportional**, `round(15 * n / 11)`, instead of zero. This is the cliff
  removal, and it is the only part of the original E19 that survives.

MG's CEO block takes the same shape: full 8 points at 4 of 7 attributes, proportional
below.

So the floor stops being a cliff and stops being a ceiling only where it was doing harm.
A company at 3 dimensions gets 4 points and enters the ranking; a company at 7 keeps
what it had yesterday.

## The honest cost of the amendment

This is a threshold being re-tuned **after seeing the outcome**, which is exactly what
this project refuses in research code. Three things make it defensible, and they are
stated so a reader can disagree:

1. The 6-of-11 threshold is **not new and not fitted** - it is the framework's existing
   A2 resolution, unchanged since before any of this.
2. The change is **monotone**: no company scores lower than it did yesterday, and none
   scores higher than it did under the pre-E19 rule. It cannot manufacture a winner.
3. It is a **coverage** rule, not a scoring rule. `composite_strict` for a fully assessed
   company is untouched either way.

What it does not fix, and what a reader should hold against it: the asymmetry means a
company at 6 dimensions and one at 11 both report full BQ coverage, so **coverage
overstates how much of the moat was actually read for 614 companies**. The `Subtests`
sheet carries `n_dimensions_scored` for anyone who wants the real number, and the
Findings sheet must say this in words.

## Re-measurement required

Everything the original E19 asked for, re-run on all three tiers under the amended rule:
band changes both ways, the distribution of dimensions behind newly banded companies, the
sector mix, and within-sector Spearman. If the amended rule still costs any company its
band, that is a finding and it goes in the workbook.
