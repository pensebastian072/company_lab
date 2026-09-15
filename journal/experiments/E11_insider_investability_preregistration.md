# E11 — is E10's small-cap insider edge investable, or is it a right tail you cannot hold?

Pre-registration written 2026-08-16, **before any portfolio, cluster or capacity figure
was computed**. The E10 panel and the price files were opened only far enough to confirm
which columns exist (`ticker/date/fwd_1y/fwd_3y`, and daily `volume` back to 2016), which
is what makes the criteria below computable rather than aspirational.

## Why this is a new question and not a re-run

E10 is the first PASS in six studies: S&P 600 open-market insider buying, **+6.1% mean
excess over SPY at 1y excluding 2020**, with the falsification checks intact (selling does
not predict, buying beats undifferentiated activity).

It also has a hole its own pre-registration went looking for and found. **The median
excess is negative in every bucket** — S&P 500 −0.1%, S&P 400 −1.6%, S&P 600 −4.0%. Over
the S&P 600's 11 years the mean was positive in 8 and the median in only 4. The typical
company an insider bought underperformed SPY. The edge lives in a right tail.

E10 measured a **signal**. E11 asks whether a **portfolio** can harvest it. Those are
different questions and the second does not follow from the first:

- E10's statistic averages across 9,171 *signal rows*, so a month with 300 signals counts
  300 times and a month with 5 counts five times. A portfolio does not work that way.
- A right-tail mean is only capturable if you can hold *every* name in the tail's
  distribution, which is a statement about position count, capacity and cost — none of
  which E10 tested.
- E10 applied no cost beyond E06's assumption, and S&P 600 names are exactly where a
  cost assumption is least safe.

## The trap this must avoid

The convenient move is to search construction choices — rebalance frequency, holding
period, cluster threshold, weighting — until one clears. That is p-hacking with extra
steps, and it is the specific failure the box's rules name. So **the entire variant list
is fixed here, before computing, and it is short**:

| axis | values, fixed now |
|---|---|
| universe | S&P 600 (E10's PASS bucket); S&P 500 as a control, not a second chance |
| holding period | 12 months only |
| rebalance | monthly cohorts, overlapping, equal-weighted within a cohort |
| cluster filter | `>= 1` insider (E10's own definition) and `>= 3` insiders |
| cost | one stated round-trip, plus a breakeven cost solved for |

**That is 2 universes x 2 cluster thresholds = 4 variants, so `n_trials = 4`**, and that
number goes into the Deflated Sharpe deflation term rather than being quietly forgotten.
No other axis is tried. If none of the four clears, the answer is no.

## Construction, fixed now

- **Cohorts.** At each month end, open an equal-weighted cohort of every S&P 600 name with
  a qualifying open-market purchase filed that month. Hold 12 months. The strategy's
  monthly return is the mean across all active cohorts, so up to 12 overlap at once. This
  is the standard overlapping-portfolio construction and it stops a single crowded month
  from dominating.
- **A month with no signals is a month in cash**, earning zero excess — not a month
  dropped from the series. Dropping empty months is how a strategy silently acquires
  perfect timing.
- **Signal date is `filing_date`**, never `transaction_date`. Carried from E06/E10.
- **Only discretionary codes count** (`P` and `S`). Carried from E06/E10.
- **Benchmark is SPY over the identical months**, and the reported quantity is always
  excess. Never an absolute return.
- **2020 is reported in and out**, every time. E06's entire edge was that one year.
- **Per-year and per-cohort tables come before any pooled number.**

## Costs, stated before seeing the answer

E10 carried E06's cost assumption, which was set for large caps. S&P 600 names are not
large caps. E11 assumes **40 bps round-trip** (spread plus impact) as the base case, and
**additionally solves for the breakeven cost** at which the edge is exactly zero.

The breakeven number is the honest headline, because it can be compared against a real
spread rather than argued about. The fx_hermes post-mortem is the cautionary case: its
breakeven cost came out 2.5x smaller than the cost the strategy had assumed for itself.

## Capacity, defined before measuring

A retail position of **$10,000** and a cap of **1% of median 20-day dollar volume** on the
20 trading days before the signal date. For each signal, capacity is the ratio of the
position to that cap. Reported as the share of signals that a $10,000 position could not
fill, per bucket and per year.

$10,000 is chosen because it is the scale this box actually operates at. If the edge only
survives at a size below that, say so plainly rather than reporting a percentage.

## Pass criteria, fixed now

| | passes if |
|---|---|
| **P1** | The equal-weighted S&P 600 portfolio's annualised excess over SPY is **positive excluding 2020**, after the 40 bps cost |
| **P2** | The **median monthly** excess return is **above zero**. This is E10's failed P3 asked of a portfolio rather than a signal, and it is the question that decides whether the edge is livable |
| **P3** | The `>= 3` insider cluster filter **raises the median** relative to `>= 1`. If clustering only raises the mean, it is concentrating the same right tail, not finding a better signal |
| **P4** | Fewer than **10%** of signals are capacity-blocked at $10,000 / 1% of ADV |
| **P5** | The **breakeven cost exceeds 40 bps**, i.e. the edge is not smaller than a plausible small-cap round trip |
| **P6** | **Deflated Sharpe > 0** with `n_trials = 4`, and **PBO < 0.5**, reusing `copper_brain\copper_brain\validate.py` rather than a third copy of the math |

**P1 and P2 are both required for any positive claim.** An edge that passes P1 and fails
P2 is the E10 result restated, not progress — it would mean the portfolio's mean is
carried by a few cohorts and the median month is still a loss.

P6 is expected to be strict. A correct gate usually fails a first-pass strategy, and on
this box nothing has ever cleared it.

## Prior, stated before computing

I expect **P1 to pass narrowly and P2 to fail.** The reasoning: E10's mean averages over
signal rows, so crowded months dominate it, and crowded insider-buying months are
disproportionately market bottoms. Equal-weighting *months* rather than *signals* should
shrink the edge well below 6.1%. The negative median at the signal level is a
distributional fact that portfolio construction diversifies but does not reverse — a
basket of mostly-losers with a few large winners has a positive mean and a median month
near zero.

I expect **P3 to fail**: cluster filters concentrate conviction, which in a right-tail
distribution usually means a fatter tail and a *lower* median, not a higher one.

I expect **P4 to pass** at $10,000 — that size is small enough that S&P 600 liquidity is
rarely the binding constraint — and **P5 to be the real decider**, because a 6.1% annual
edge is large relative to 40 bps but the portfolio edge may not be.

Stating all of this now so a null cannot later be described as expected, and a pass cannot
later be described as predicted.

## Known limits, carried and new

- The S&P 600 is small-cap **within an index**. The microcap tail where the literature's
  effect is strongest is absent entirely, and E11 does not fix that.
- Form 4 bulk data starts 2016q1, so there is no pre-2016 regime and the only stress
  windows are 2020 and 2022.
- The 3y arm has fewer usable years than the 1y arm; per-year tables for it will be short.
- **Survivorship.** The bucket map is today's index membership. A company that left the
  S&P 600 after a collapse may be missing from the panel, which biases every one of these
  numbers upward. This is the same unfixed defect that gates the company_lab entry-rule
  studies, and E11 inherits it. It must appear in the results file, not only here.

## What a PASS would and would not establish

A PASS would say: this construction, on this universe, over 2016-2025, with these costs,
produced a positive excess a portfolio could actually have held. It would **not** establish
that the effect persists, that it survives in a live account, or that company_lab's own
ranking has any predictive power — E11 tests an insider signal, not the 100-point
framework. Nothing is promoted; `promoted` stays false regardless of outcome.

## Outputs

`journal/experiments/E11_results.json` / `.md`, implemented in
`clab/research/e11_investability.py`, reusing E10's `build_signals` and bucket map rather
than rebuilding either.
