# E21 - entry timing stops deciding WHICH company, and only informs WHEN

Pre-registered 2026-08-20, before the scoring change. Decision taken by the user after a
review flagged it; verified against the live table before it was accepted.

## The problem, measured

`EN` is a 2-point component inside `composite_strict`. E01 tested entry timing three
separate ways - waiting for a 20-EMA touch, a low own-history P/E percentile, and a
confluence of both - and **it failed three times**. That result is on the Findings sheet
of every workbook shipped since.

Those 2 points are nevertheless ordering the top of the ranking today:

| rank by composite_strict | | rank by composite_ex_entry |
|---|---|---|
| RAMP 84 (1 EN) | | NVDA 83 |
| NVDA 83 (0 EN) | | RAMP 83 |
| PTC 82 (**2 EN**) | | INTU 81 |
| INTU 82 (1 EN) | | PTC 80 |
| EXEL 81 (1 EN) | | EXEL 80 |

PTC and VRT each carry the full 2 entry points; NVDA and JLL carry none. So the difference
between #1, #2 and #3 is currently being set by the one factor this project has
explicitly falsified.

## The change

**The selection ranking becomes the ex-entry score. EN stays in the framework and stays
on the sheet as an execution overlay.**

Two candidate constructions, and the choice is fixed here rather than after seeing which
looks better:

* **A - band on the raw ex-entry sum (0-98).** Every company loses 0-2 points against
  thresholds calibrated for a 0-100 sum, so companies holding entry points are
  systematically downgraded. Rejected: that is a re-calibration disguised as a removal.
* **B - band on the ex-entry sum rescaled to the same 100-point basis**, i.e.
  `selection_score = round(100 * composite_ex_entry / 98)`. **Chosen.** It removes the
  factor without moving the band thresholds, so a band change means the company's
  standing changed rather than the ruler.

`composite_strict` is still computed, still exported and still the eight-component sum, so
every prior study, snapshot and journal entry stays comparable. Nothing about the 100-point
framework's weights changes.

## What must be reported afterwards

1. **Band changes in both directions**, with counts - not just the ones that improved.
2. **Within-sector Spearman** of the new selection score against `composite_strict`, over
   every company in the sector, per E12's P4 duty. A correlation near 1.0 means this
   reordered the top without disturbing the body of the ranking, which is the intent.
3. The **new top 20** beside the old, so the change is visible rather than asserted.

## Prediction, stated before running

Within-sector Spearman **above 0.99** - 2 points on a 100-point scale cannot reorder much
below the top, where scores are densely packed. **Fewer than 15 band changes**, mostly at
threshold edges, roughly balanced up and down because rescaling by 100/98 gives back
about as much as removing EN takes away. The top 5 reorders: NVDA takes #1 from RAMP.

If instead this produces dozens of band changes, the rescale is doing more work than the
removal and the whole change should be reconsidered rather than accepted.

## What this does NOT do

It does not make the ranking predictive. E13 measured the measured-half top-20 at **-0.5%
annualised net** against SPY with a breakeven of -13 bps, and every Deflated Sharpe
negative. Removing a falsified 2-point factor removes a known error; it does not add an
edge, and `promoted` stays false.
