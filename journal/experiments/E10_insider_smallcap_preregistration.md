# E10 — does insider buying work where the literature says it should: small caps?

Pre-registration written 2026-08-15, **before the small-cap Form 4 panel was analysed**.

## Why this is a new question and not a re-run

E06 asked whether following insiders beats holding the index and answered **no**: across
675 large caps, S1's entire edge was 2020 (+19.9% mean excess, contributing 0.199 of the
0.210 sum of yearly means). Strip that year and the edge was −0.0% with a median of
−3.5%.

But E06's population was the S&P 500 plus the companies that left it — the most analysed
companies in the world. The insider-trading literature's mechanism is **information
asymmetry**, and asymmetry is smallest exactly there. Lakonishok & Lee and successors
report the effect concentrated in **small firms**, where analyst coverage is thin.

The universe now holds **1,497 companies** (S&P 500 + 400 + 600), so roughly 1,000 mid
and small caps that E06 never saw. That is a different population, not a second look at
the same one.

**This is the honest version of the "maybe we have to filter the differences in the
insider trading" idea** — the filter being tested is company size, fixed in advance,
rather than a search across cuts until one works.

## The trap this must avoid

E06 already produced one apparent edge that was a single year. Slicing a null result by
size until a subgroup looks positive is the same mistake with more steps. So:

1. **Size is the ONLY new dimension.** Three buckets, fixed now: S&P 500, S&P 400, S&P
   600. No market-cap thresholds tuned after the fact, no sector cuts, no interaction
   terms.
2. **The 2020 test is mandatory.** Every result is reported with and without 2020. An
   edge that disappears without one year is not an edge, and E06 established that this
   dataset has exactly that failure mode.
3. **The falsification check carries over.** S6 (selling) must not predict, and
   undifferentiated insider ACTIVITY must not predict as well as buying does. In E06
   both fired: selling returned +1.7% against buying's +2.7%, and mere activity +1.6%.
   If that repeats in small caps, the construction is measuring attention, not
   information.

## Disciplines, unchanged from E06

- Signal date is **`filing_date`**, never `transaction_date`.
- Only **discretionary** codes count: `P` and `S`. Option exercises (M), tax withholding
  (F), awards (A) and gifts (G) are not decisions — they were 66% of all transactions.
- Primary statistic is **excess over SPY**, never absolute return.
- Clustered by **date**; no verdict below 40 date clusters.
- **Median beside every mean**, per-year table before any pooled number.
- Source is SEC Form 4 via the DERA bulk datasets, so there are no congressional rows
  and no vendor duplication.

## Prior, stated before looking

I expect the small-cap edge to be **larger than large-cap but still not survive the 2020
test**, because the mechanism that produced E06's result — insiders buying a market
bottom along with everyone else — applies to small caps more strongly, not less. I also
expect far fewer open-market purchases per company than the raw count suggests once
mechanical codes are stripped.

Stating that now so a null is not later described as expected and a positive is not
later described as predicted.

## Pass criteria, fixed now

| | passes if |
|---|---|
| **P1** | S1 mean excess over SPY at 1y is positive in the S&P 600 bucket **excluding 2020** |
| **P2** | the S&P 600 edge exceeds the S&P 500 edge, i.e. the size gradient runs the way the literature says |
| **P3** | S1's **median** excess is above zero in at least one bucket — E06's means were carried by a right tail, and a strategy is lived through at the median |
| **P4** | S6 does **not** predict, and buying beats undifferentiated activity by more than 1 percentage point |

**P1 and P4 are both required for any positive claim.** P2 and P3 are reported either
way.

If P1 fails, the answer to "should insider activity feed the score" is no across the
whole market-cap range, and E06's conclusion stands with a much wider base.

## Known limits

- The S&P 600 is *small cap within an index* — it excludes microcaps and anything
  unlisted, so this is not the smallest, least-covered tail where the effect should be
  strongest.
- Form 4 bulk data begins 2016q1, so there is no pre-2016 window and no second market
  regime beyond 2020 and 2022.
- 3-year forward returns exist only for signal dates up to ~2023, so the 3y arm has
  fewer years than the 1y arm and its per-year table will be short.

## Outputs

`journal/experiments/E10_results.json` / `.md`. Nothing is promoted; `promoted` stays
false regardless of outcome.
