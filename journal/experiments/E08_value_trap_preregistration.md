# E08 — is the discount deserved? Moat DIRECTION as a value-trap filter

Pre-registration written 2026-08-12, **before any of these statistics were computed**.

## Where this came from

The user read the workbook and objected to the top of the ranking: FICO around 18th, plus
PayPal and a large defense name. Their diagnosis, in their words: a deep discount is usually
deep *for a reason*, and the reason is normally **decaying growth prospects or a moat being
broken**. FICO's revenue growth "is only because they're raising prices, but their moat is
being broken right now". PayPal is cheap because "the use case for it as a company for
growth isn't really there". Against that, NVIDIA is expensive because the growth is real and
the moat holds.

This is a specific, testable mechanism for the finding E05 just produced — **the top
decile's median 3-year excess over SPY is −7.6% and only 45.3% of its picks beat SPY.** The
measured half awards VA points for cheapness and has no test of whether the cheapness is
deserved. If the user is right, the top decile is contaminated by value traps and screening
them out should repair it.

## The insight, made into a measurable

A static moat score cannot capture this; **direction** is the whole point. Two series,
both computable from the point-in-time panel already on disk, with no new data and no LLM:

- **`share`** = a company's `revenue_ttm` divided by the summed `revenue_ttm` of its
  sub-industry peers on that date, using the as-first-filed vintage.
- **`d_share_3y`** = change in that share over 36 months.

Combined with the margin series, this separates the user's cases:

| pattern | margin trend | share trend | reading |
|---|---|---|---|
| winning | up or flat | **up** | moat intact, growth real |
| **harvesting** | **up** | **down** | the FICO case: raising prices into a shrinking position |
| losing | down | down | moat gone |
| buying share | down | up | competing on price |

**Honest limit, stated before any result:** the peer group is S&P 500 members only, so this
is *share of large-cap listed peers*, not true market share — private, foreign and
small-cap competitors are invisible. A company can lose real share to a private entrant with
this metric flat. It is a proxy for direction, and every result must say so.

## Hypotheses, fixed now

| # | hypothesis |
|---|---|
| H1 | Within the top decile of `measured_pct`, names with **declining** 3-year share have worse forward excess over SPY than names with rising share. |
| H2 | The "harvesting" quadrant (margin up, share down) is the worst of the four, and worse than the plain "losing" quadrant — because the market rewards the visible margin while the position erodes. |
| H3 | Excluding declining-share names from the top decile **raises its median excess over SPY above zero**. This is the one that matters: it is the difference between a ranking that beats the index and one that does not. |
| H4 | `d_share_3y` carries forward-return information **independently of** the existing score — i.e. it survives controlling for `measured_pct`. Otherwise it is a slower way to say something the score already says. |

## Pass criteria

- H1 passes if the rising-share group's mean AND median excess both exceed the
  declining-share group's, at 1y and 3y, with ≥40 date clusters.
- **H3 is the decisive one.** It passes only if the filtered top decile's **median** 3-year
  excess over SPY is **above zero**. A mean improvement alone does not count: the whole
  lesson of E05 is that this distribution's mean is carried by a few winners.
- H4 passes if `d_share_3y` keeps a positive mean IC against excess returns after the score
  is partialled out.

If H3 fails, the value-trap story is **not** the explanation for the top decile's
underperformance, and that gets reported as plainly as a success would.

## Prior, stated before looking

The user's reasoning is sound and the mechanism is real in the literature (value traps,
and the fact that cheapness unadjusted for quality is a weak factor). But I expect the
*proxy* to be noisy: sub-industry buckets in the S&P 500 are often 5-15 names, so share is
lumpy, and a large acquisition moves it for reasons unrelated to competitive position. I
expect H1 to be directionally right and **H3 to be a close call**, because the top decile's
median is 7.6 points below SPY and that is a large gap to close with one filter.

## Method

- Monthly grid, the same 67,889-row survivorship-free panel as E05 (675 symbols).
- Share computed only where the sub-industry has **≥5 peers** with revenue on that date;
  otherwise `NO_DATA`, never a zero.
- Excess over SPY is the primary statistic, never absolute return.
- Clustered by date. Medians beside every mean. Per-year table before any pooled number.
- Acquisitions are not adjusted for. Instead, share changes above a stated threshold are
  reported separately so a merger-driven jump cannot masquerade as competitive advance.

## If it works

Then and only then does a scoring change get pre-registered separately. The candidate is a
**BQ sub-test scored from measured share direction** rather than the LLM's static moat
judgement, plus a hard **value-trap veto** that withholds a top band from a cheap company
with deteriorating share. Insider buying (E06, pre-registered) is a second candidate input
to the same question and is measured separately so the two stay attributable.

Nothing here is promoted. `promoted` stays false regardless of outcome.
