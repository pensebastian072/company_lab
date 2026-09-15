# E03 — the questions nobody asked yet (pre-registration)

Written 2026-08-10 before any of these were computed. These are mine, not the user's:
things I think the framework needs answered and that had not come up.

Run against the point-in-time panel (`clab/research/panel.py`). Same limits as E02:
measured half only, no LLM, today's index members, so survivorship applies throughout
and is restated in every output.

---

## R1 — Is the framework a quality bet or just a sector bet?

Concern: the framework may be measuring "own technology" rather than "own good
companies". Tech dominated 2016-2025, and if the score simply loads on sector then the
whole exercise is an expensive sector tilt.

Test: Spearman IC **within sector** each month (demean the score by sector, demean the
forward return by sector), against the raw pooled IC.
*Interpretation*: if within-sector IC collapses toward zero while pooled IC is
positive, the score is a sector bet. If within-sector IC survives, it is picking
companies.

## R2 — Does the CHANGE in score beat the LEVEL of the score?

Concern: the framework asks "is this good now". It never asks "is this getting
better". Improving-from-mediocre may be a stronger signal than statically-good, and
the framework has no way to express it.

Test: IC of the 12-month change in `measured_pct` against forward 1y return, compared
with the IC of the level. Also the 2x2: high level / low level crossed with improving /
deteriorating.
*Interpretation*: if change beats level, the framework is missing a momentum-of-
fundamentals dimension and should gain one.

## R3 — Does the framework need a longer horizon than we have been testing?

Concern: everything so far used 1y and 3y. The user's whole thesis is multi-year
compounding, and a quality tilt may simply need more time than a year.

Test: IC and decile spread at 1y, 3y and 5y on the same rows.
*Interpretation*: if IC rises monotonically with horizon, the framework is fine and
the tests were too short. If it does not, horizon is not the explanation.

## R4 — Is the score stable enough to act on?

Concern: nobody has checked whether a company's score is steady or whether it
oscillates monthly. A score that flips 20 points a quarter is unusable regardless of
its IC, because you cannot hold a position through it.

Test: month-to-month absolute change in `measured_pct`; share of companies whose band
changes per quarter; median months spent in a band before leaving it.
*No pass/fail* - this is a usability measurement, and it also tells us how often the
dashboard's answer actually changes.

## R5 — Does the cyclical fix work? (from E02's one genuine defect)

E02 found the score peaks at the earnings top for memory/storage/optical and troughs
at the bottom - anti-correlated with the right entry. Proposed remedy: score FE and VA
off **mid-cycle** figures rather than TTM for structurally cyclical filers.

Test: recompute FE using a 7-year median operating margin and 7-year revenue CAGR
instead of TTM, for SIC groups 3600-3699 (electronics/semis), 3570-3579 (computer
hardware), 1300-1399 and 2911 (energy), 3300-3399 (primary metals), 3711 (autos).
Compare IC and, specifically, the score trajectory of LITE/WDC/STX/MU/CIEN around
their known moves.
*Passes* if within cyclical names the mid-cycle IC exceeds the TTM IC **and** the
score no longer peaks within 12 months before a >100% move.

## R6 — What does the framework systematically never own?

Concern: an honest ranking should be able to say what it structurally excludes, so the
user knows the shape of the hole.

Test: characterise the bottom decile - sector mix, median size, profitability rate,
median P/E, share with negative FCF - and the same for companies that were never once
in the top 3 deciles across the whole decade.
*No pass/fail*. The deliverable is a plain description of what this framework will
never buy, so the user can decide whether that exclusion is intentional.

---

## Reporting rules

Unchanged from E01/E02: per-year before pooled, medians beside means, n everywhere, no
claim on n < 30, survivorship restated, negative results reported as plainly as
positive ones. Nothing here promotes anything.

## Honest note on R5 and the reweighting

The EN 5->2 and FE 15->18 change applied on 2026-08-10 was motivated by E01 (an
independent study) and E02 Q4. Re-running E02 on the new weights measures the
**mechanical** effect of the change on the same data that suggested it. That is
in-sample and is not evidence the change generalises. It is reported as a sanity check
only, and labelled as such wherever it appears.

## Outputs

`journal/experiments/E03_results.json` / `.md`
