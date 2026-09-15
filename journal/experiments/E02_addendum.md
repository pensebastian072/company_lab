# E02 addendum — what we got wrong, what we should have seen, what we couldn't

> **B8 pairing note, added 2026-09-10. THIS FILE DESCRIBES AN EARLIER RUN THAN
> `E02_results.md`.**
>
> This addendum was written 2026-08-10 18:31 against the run whose panel is
> `E02_panel.parquet` — **57,610 observations, 495 companies**. The current
> `E02_results.md` / `E02_results.json` are from a later run on 2026-08-12 10:48 over
> **67,889 month-ends and 675 companies**. They are not the same study population and the
> scoreboard below does not describe them.
>
> **The divergence is not cosmetic: Q1 changes verdict.**
>
> | | this addendum (08-10, n=495) | `E02_results` (08-12, n=675) |
> |---|---|---|
> | Q1 top decile beats bottom | 3 of 10 years | **6 of 10 years** |
> | Q1 mean monthly IC | +0.013 | **+0.043** |
> | Q1 recorded verdict | **FAIL** | **`passes: true`** |
> | Q3 bad rate | 11.1% vs 9.8% base | 13.93% |
>
> **Neither verdict is endorsed here and E02's conclusion is not being changed.** Which
> run is canonical is an open decision — see `B8_E02_PAIRING_2026-09-10.md`. Note also
> that the later run's panel was never saved: the only E02 panels on disk are this one
> (57,610 / 495) and `E02b_panel.parquet` (53,486 / 483).

Written after seeing results. Pre-registration unedited.

Panel: 57,610 point-in-time observations, 495 companies, 2016-08 to 2026-08, median
38 of 45 points available. The LLM half is excluded throughout.

## Scoreboard

| Question | Result |
|---|---|
| Q1 measured score ranks forward returns | **FAIL** — mean IC +0.013, top decile beat bottom in 3/10 years |
| Q2 detection timing on the winners | **22 of 25 could not have been seen** |
| Q3 top decile avoids disasters | **FAIL** — 11.1% bad rate vs 9.8% universe base rate |
| Q4 component attribution | FE +0.025, VA +0.017, BS −0.006, **EN −0.033** |
| Q5 bands order returns | **FAIL** — non-monotone; REJECT (+21.1%) beat EXCEPTIONAL (+17.9%) |
| Q6 score falls before price | **FAIL** — led the drawdown in 39.1% of cases, worse than a coin flip |

## Read the biggest caveat FIRST, because it cuts against the headline

The universe is **today's 495 index members**. Companies that scored badly and then
went to zero are *not in this dataset* — they were removed from the index and their
price series is absent. So the bottom decile is not "low-scoring companies", it is
**low-scoring companies that survived**, which is close to a definition of names that
were beaten down and then recovered.

That means the two most eye-catching results — the U-shaped decile curve and REJECT
out-earning EXCEPTIONAL — are substantially **survivorship artifacts and should not be
believed**. The honest statement is: within companies that made it to 2026, a low
measured score did not predict poor returns. It says nothing about the low-scoring
companies that did not make it.

Balance-sheet quality suffers most from this. BS looks useless here (IC −0.006), but
BS exists to avoid permanent loss, and every company it would have saved you from is
missing from the sample by construction. **BS is untested, not disproven.**

## Q2 is the real answer to "what should we have seen?"

Only **3 of the 25 biggest winners** were scoring above 70% of available points before
their move: **NVDA** (70.7% at 2022-09, first crossed 70% back in 2016), **FIX**
(71.1%, FE 12/15), **GNRC** (89.5%, FE 14/15). Those three the framework genuinely
caught, NVDA most impressively.

The other 22 had weak fundamentals *at the start of the move*:

| | 3y return | score at start | FE at start |
|---|---:|---:|---:|
| CVNA | +9,410% | 33% | 2/15 |
| APP | +5,910% | 31% | 6/15 |
| PLTR | +2,730% | 60% | 8/15 |
| TSLA | +1,948% | 38% | 4/15 |
| HOOD | +1,337% | 17% | 1/15 |

CVNA in December 2022 was nearly bankrupt. The framework said FE 2/15 and it was
**right** — and the stock then went up 94x. This is not a scoring bug to fix. It is
structural:

> **A fundamentals score cannot catch this kind of winner early, because the
> fundamentals arrive after the price move.** The earnings that justify the move are
> published one to three years later.

So: **couldn't have seen — 22 of 25.** Filed under honest limits, not defects.

## The one genuine defect Q2 exposed: cyclicals score high at the top

Look at what the score was doing 12 months *before* these moves began versus at the
start of them:

| | score 12m before | score at move start | what happened |
|---|---:|---:|---|
| LITE | 88% | 29% | score peaked, earnings collapsed, then the stock 20x'd |
| WDC | 83% | 32% | same |
| STX | 76% | 21% | same |
| MU | 71% | 29% | same — **the exact name from E01** |
| CIEN | 78% | 49% | same |

For memory, storage and optical hardware the framework is **anti-correlated with the
right entry**: it scores highest when TTM earnings peak, which is precisely when the
cycle is about to turn down, and lowest at the trough, which is precisely when the
next up-cycle starts. Five of the top 25 winners follow this pattern exactly.

This is a fixable flaw and the highest-value change available. TTM earnings are the
wrong denominator for a cyclical. Candidates:

1. **Mid-cycle earnings for cyclicals** — score FE and VA off a 5-to-7-year average
   margin and revenue rather than TTM, for SIC groups that are structurally cyclical
   (semis, memory, hardware, energy, materials, autos).
2. **An explicit cycle-position input** — TTM margin as a percentile of its own 7-year
   range. Near the top of the range should *reduce* confidence in a high FE, not
   confirm it.
3. Both, pre-registered separately, tested on this panel before any scoring change.

## What Q3 says about top scores

The top decile lost more than 20% over the following year **more often** than the
universe (11.1% vs 9.8%), and the worst cases had near-perfect scores: META scored
100% of available points at 2021-10 and fell 71%; TSLA 87% then −69%; ALGN 83% then
−69%; IT 82-87% across five consecutive months then −67%.

A high measured score offered **no downside protection at all** over this window. The
pattern in those names is a high multiple meeting a growth disappointment — which is
exactly what the ER component (expectations vs reality) is meant to catch, and ER is
the one component this study could not reconstruct. That is an argument for taking ER
seriously in live scoring, not evidence about it.

## Q4: what to actually change in the scoring

| Component | Mean IC | Verdict |
|---|---:|---|
| FE | **+0.025** | the only component carrying signal; positive in 64% of months |
| VA | +0.017 | weakly positive |
| BS | −0.006 | ~zero here, but untested for its real purpose (see caveat above) |
| EN | **−0.033** | actively counterproductive, positive in only 39% of months |

**EN is now failing twice independently.** E01 showed signal entries underperformed
random entries in the same names; E02 shows its IC is the most negative of the four.
Two pre-registered studies, same direction.

Recommended change — **and I want your decision before I touch the framework**:
reduce EN from 5 points to **2**, or to 0, and move the freed points to FE. But note
what that costs: EN is the component that encodes your own discipline about not
overpaying at a top. Its low IC may be measuring "this window rewarded buying
extension", not "entry timing is worthless forever". A 2016-2025 window contains no
prolonged bear market.

My honest recommendation: **cut EN to 2 points, give 3 to FE, and re-run this battery.
Do not drop EN to zero** — one bull-market decade is not enough evidence to delete a
risk-management rule, and this dataset cannot see the scenario EN protects against.

## What must happen before any of this is trusted

**Fix survivorship.** `D:\ohlcv_1m` holds 411 monthly files, 1992-2026, and
**retains delisted tickers**; `stock_xsect_lab/src/universe.py` already builds a
point-in-time eligibility universe from it, and `src/delisting.py` handles the
survivorship problem directly. Rebuilding this panel on that basis would:

- include the companies that scored badly and died, which is the whole test of BS and
  probably reverses the U-shape;
- extend the window back through 2000-2002 and 2008, the only periods in which the
  entry rule's premise can be tested at all;
- answer the question actually worth answering — **the best companies at any time**,
  not the best among those that survived to today.

That is the next study, and until it exists every number above carries an asterisk.

## Status

Nothing here is promoted. No scoring change has been made. `promoted` remains false.
