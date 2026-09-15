# E35 - the panel has 41,733 rows and about 2,272 observations

Pre-registration written 2026-08-26, **before any statistic is recomputed**. This one is
unusual: it does not propose a change to the scoring framework. It proposes to **re-state
the confidence of results this project has already published**, and it may make several of
them weaker rather than stronger.

## The defect

`E04_panel_nosurv.parquet` is **monthly** — 128 snapshot dates, 2016-01-31 to 2026-08-31,
644 symbols, 63,185 rows. The labels are `fwd_1y` and `fwd_3y`.

A 3-year label attached to a monthly snapshot **overlaps the next snapshot's label by 35 of
36 months**. Consecutive rows for one company are not two observations of anything; they
are one observation reported 36 times with the start shifted by a month.

| | `fwd_3y` | `fwd_1y` |
|---|---:|---:|
| non-null rows | **41,733** | 55,568 |
| adjacent-row label overlap | **97.2%** | 91.7% |
| non-overlapping windows per symbol (10.6 yrs) | 3.5 | 10.6 |
| **effective independent observations** | **~2,272** | ~6,815 |
| **standard errors understated by** | **~4.3x** | ~2.9x |

Every IC, t-statistic, decile spread and confidence interval computed on that panel treats
41,733 as the sample size. The honest figure for a 3-year label is closer to **2,272**, and
the cross-section is correlated on top of that: every company in a given month shares the
market's move, so even 2,272 is generous.

E22 already understood this for its own two-cross-section design — *"the effective sample
for a return test is closer to n=2 than n=1,000... a Deflated Sharpe or PBO figure computed
on this would be theatre"* — and then declined to compute one. **The same reasoning was
never applied to the E04 panel**, which is where E02, E03, E05, E13 and E14 were computed.

## What this puts in question

Not the point estimates — the **confidence** attached to them. Specifically:

* **E03 R1's "95.6% of the ranking's power is sector selection"** and R3's 1y-vs-3y IC
  comparison. R3 is the reason this workbook is labelled 3-year.
* **E05's decile results**, including "the median top-decile pick loses to SPY" and the
  +11.9% mean / −7.6% median split.
* **E13's "top-20 is flat"** and **E14's "+1.2% vs −0.9% annualised excess"**, which is
  the strongest result in the project and already fails the promotion gate.

A result can survive this and several probably will — a 4.3x wider interval on a large
effect still excludes zero. **The point is that nobody has checked**, and some of these
are quoted in the workbook's Findings sheet to three significant figures.

## The change

No scoring code moves. Two things are added to the research layer:

1. **A temporal buffer.** When forming non-overlapping observations, require a gap of at
   least the label horizon between a symbol's consecutive rows, so a 3-year test draws at
   most one observation per symbol per 3 years.
2. **Overlap-aware standard errors** on the pooled statistics that keep the full panel:
   Newey-West with a lag of at least the label horizon in months, and a cluster on date to
   absorb the shared market move. Report the effective sample size beside every figure.

Both go in the pre-registration rather than a code comment, because changing how an
interval is computed after seeing whether a result survives is the same failure this file
exists to prevent.

## Pass criteria, fixed now

This is a measurement, not a promotion, so the criteria govern what gets **reported**:

| | |
|---|---|
| **P1** | Every recomputed statistic is published with its **effective sample size** beside the raw row count. A figure without one is not reported. |
| **P2** | Results are reported **both ways** — original and overlap-aware — never replaced silently. A reader must be able to see what changed. |
| **P3** | Any conclusion on the Findings sheet whose sign or significance changes is **updated on the sheet**, not just in this journal file. The workbook is what gets read. |
| **P4** | The buffered estimate is computed on **all** available start offsets and averaged, not on one arbitrary anchor. Picking the anchor after seeing the answer is the obvious way to cheat this. |

## Prior, stated before computing

I expect **E03 R1's sector finding to survive comfortably** — 95.6% is an enormous effect
and E30 independently failed to move the sector gap by fixing four data bugs, which is
corroboration from a different direction.

I expect **E05's decile results to widen a lot and stay directionally intact**. The
mean/median split is a distributional fact, not a significance claim, so the buffer should
barely touch it.

I expect **E13 and E14 to be the casualties.** E14's +1.2% annualised excess is already
marginal — it passed four registered criteria and still failed the gate on DSR −0.51 — and
a 4.3x wider interval on an effect that small will not clear zero. **If E14's headline
loses significance, the honest consequence is that the strongest result in the project
becomes "not distinguishable from noise", and the sector-neutral presentation change
(2026-08-25) keeps its justification only from E03 R1 and not from E14.**

Stating that now so a weakened E14 is not later described as "still directionally
positive", which is what one says when an interval has swallowed the estimate.

## What this cannot establish

It cannot make any result *better*. It can only widen intervals and, at best, leave a
conclusion standing. There is still no forward-return grader for the judged half — 5 weekly
snapshots of the ~50 needed — and the judged half is untestable for a separate reason
(see the contamination section in `CLAUDE.md`, added today: a null there proves nothing in
either direction).

`promoted` stays false, and nothing here changes a score.

## Outputs

`journal/experiments/E35_results.md`, a helper in `clab/research/` for buffered sampling
and overlap-aware SEs, and — if P3 fires — edits to the Findings sheet text.
