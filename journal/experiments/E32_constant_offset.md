# E32 - how much of a sector's score separates nobody?

Measured 2026-08-25 with `clab/research/e32_constant_offset.py`. **Descriptive only.
Nothing was changed and no threshold is proposed.**

## Why this instead of per-sector thresholds

E30 flagged three sub-tests that award nearly every company in a sector the same number:
`bs_cash_vs_opex` in Utilities (96% score zero), `bs_current_ratio` in Materials (96%
score max), `bs_maturity_wall` in Communication Services (95% score max). Such a sub-test
cannot separate two companies inside that sector, but it still moves the composite - so
part of every score is an offset that says something about the sector and nothing about
the company.

The obvious fix is a per-sector band, and `SectorProfile.thresholds` exists for exactly
that. It is empty on purpose, and the reason is written into the field's own comment:

> the mechanism exists, the calibration does not, and **inventing thresholds without a
> backtest is exactly what this repo refuses to do**.

There is no forward-return grader - 5 weekly snapshots of the ~50 it needs - so no
per-sector band can be calibrated honestly. **What can be done without one is to say how
large the uninformative part actually is**, so a reader knows what a gap between two
sectors is made of. That is this experiment, and it is the same question the market-state
workbook needed and did not ask.

## Result

| sector | n | median score | constant pts | discriminating pts | constant share | constant sub-tests |
|---|---:|---:|---:|---:|---:|---|
| Materials | 77 | 48 | 0.96 | 47.43 | **2.0%** | `bs_current_ratio` = 1 |
| Communication Services | 47 | 51 | 0.95 | 53.29 | **1.8%** | `bs_maturity_wall` = 1 |
| Utilities | 59 | 39 | 0.04 | 42.39 | 0.1% | `bs_cash_vs_opex` = 0 |
| every other sector | - | - | 0.00 | - | **0.0%** | none |

## What it says

**The constant offset is at most one point, and at most 2.0% of a sector's earned
points.** Eight of eleven sectors have none at all.

Put beside the failure this instrument was built from, the contrast is the finding: the
market-state workbook had **6 of 12 layers constant**, so a "12-layer confluence tally"
was really a 6-layer tally plus an offset and the total concealed it. Here it is **one
sub-test in one sector**, worth about a point.

The cross-sector distortion is bounded the same way. Materials and Communication Services
each collect a point almost everyone in the sector gets; Utilities forgo one almost none
of them can get. So the widest constant-driven gap between two sectors is about **2
points, against the 27-point Information-Technology-to-Real-Estate spread** the workbook
now leads with. Constants account for at most ~7% of it.

That is a third independent explanation for the sector spread tested and found wanting,
after E29 (the rubric asks questions some sectors cannot answer - refused) and E30 (the
inputs were broken - fixed, and the spread did not move).

## Verdict

**Leave all three alone.** They are real, they are honest, and they are immaterial:

* `bs_cash_vs_opex` in Utilities is a **true statement** - a regulated utility runs on
  revolvers and regulated cash flows, not on a cash balance. It is E29's exclusion
  exactly: a true low score is not an inapplicable question. Suppressing it would flatter
  the sector; re-banding it would require calibration that does not exist.
* `bs_current_ratio` in Materials and `bs_maturity_wall` in Communication Services are
  free points, worth about 1.0 and 0.95 respectively.

Revisit only when the forward-return grader exists and a per-sector band can be tested
rather than asserted. The number to beat is written down here so a future change has to
argue against **2.0%**, not against an impression.
