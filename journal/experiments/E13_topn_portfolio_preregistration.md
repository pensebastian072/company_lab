# E13 — does a top-N portfolio of this score beat the index?

Pre-registration written 2026-08-16, **before any portfolio return was computed**. The
panel and the portfolio machinery were read only far enough to confirm which columns and
helpers exist.

## Why this exists, and why it comes first

A review proposed four v2 changes: fix the XBRL normalization, add company archetypes,
sector-neutralize the ranking, then backtest. The order was inverted deliberately. Four
changes landing together are unattributable, and this repo already learned that the
expensive way — F1 and F2 are kept apart in E05 for exactly this reason. E13 is the
**baseline**: the number every later phase has to beat.

It also exists to resolve a contradiction sitting in E05 that nothing has explained:

| E05, 3-year horizon | |
|---|---:|
| mean IC | **+0.0805** |
| top−bottom decile | **-14.1%** |

A positive rank correlation with an inverted decile spread is not a detail. It means the
score orders companies weakly in the right direction while its *extremes* are backwards,
and every "top 10" list this system publishes lives in exactly that extreme. If E13 cannot
reproduce and explain it, no later phase is trustworthy.

## What is actually being graded — stated before the result

**This grades the MEASURED HALF, not the published composite.** `panel.py:19-21` excludes
the entire LLM half (SG/BQ/MG, 50 of 100 points) and also ER, PEG, forward P/E and the
reverse DCF, because none of them can be reconstructed point-in-time without hindsight. So
E13 tests **FE + BS + VA + EN**, surfaced as `measured_pct`.

Testing the published composite needs ~50 weekly snapshots. Four exist. The weekly cadence
is healthy (verified: `CompanyLabSnapshot`, weekly Saturday trigger, last result 0), so
that path opens around mid-2027 and not before. **Any claim E13 makes is a claim about the
measured half only**, and the results file must say so in those words.

## Construction, fixed now

Reuses the existing machinery rather than rebuilding it:

- **Point-in-time scores** — `clab/research/panel.py`. `payload_asof:69` filters
  companyfacts to `filed <= asof`; `build_symbol_history:159` uses the `as_first_filed`
  restatement view; `removed_constituents:486` keeps delisted names present for the months
  they were members. Grading on restated data would be look-ahead bias.
- **Portfolio construction** — `clab/research/e11_investability.py:cohort_series:112`.
  Overlapping equal-weighted monthly cohorts; a month with no cohort is **cash at zero
  excess, never a dropped month**.
- **Benchmark** — `battery.attach_benchmark:36` (SPY at the same month-ends).
- **Gate** — `e11._gate:48`, importing `copper_brain/validate.evaluate_gate` (PBO +
  Deflated Sharpe). Not re-ported.

The only new code is `top_n_by_date(panel, n, score_col)` producing
`{month_end: [tickers]}`.

Fixed parameters: **12-month hold**, **40 bps round trip**, **coverage ≥ 0.80** (below
which the rubric awards no band, so it must not award a portfolio slot either), monthly
cohorts, equal weight within a cohort.

## The variant list, fixed now

| axis | values |
|---|---|
| N | 20, 40, 80 |
| ranking column | `measured_pct` |

**3 variants, so `n_trials = 3`** for the Deflated Sharpe deflation. That number is
registered here so it cannot be quietly discovered later. Sector-neutral ranking is *not*
in this run — it does not exist yet, and adding it later is a new pre-registration with its
own `n_trials`, not an extra column here.

A long-only top-N is the only construction tested. No short leg, no weighting scheme
search, no rebalance-frequency search. If the answer is no, it is no.

## Pass criteria, fixed now

| | passes if |
|---|---|
| **P1** | top-20 annualised excess over SPY is **positive after 40 bps**, excluding 2020 |
| **P2** | the **median month** is above zero — the E10/E11 lesson, that a positive mean with a negative median is a right-tail result a holder does not experience |
| **P3** | the **size gradient runs the right way**: top-20 ≥ top-40 ≥ top-80. If a broader portfolio does better, the score is not concentrating anything and any apparent edge is a market-beta or size artefact |
| **P4** | **the E05 contradiction is reproduced and explained** — either the top-N result agrees in sign with the -14.1% decile spread, or the disagreement is traced to a specific construction difference and named |
| **P5** | Deflated Sharpe > 0 (threshold 1.645) and PBO < 0.5, `n_trials = 3` |

**P4 is required regardless of outcome.** P1 and P2 together are required for any positive
claim. P5 is expected to fail; on this box nothing has ever cleared it, and a correct gate
usually fails a first-pass strategy.

## Prior, stated before computing

I expect **P1 to fail or land near zero, and P3 to fail outright.** The reasoning: E05
already measured a -14.1% top−bottom decile spread at 3y, and a top-N portfolio is a
sharper version of the top decile. If the extreme of the ranking is where the score is
worst, concentrating into 20 names should be *worse* than 80, not better.

I expect the E05 contradiction (P4) to resolve as a **horizon and weighting artefact**:
E05's IC is a monthly cross-sectional rank correlation pooled across all names, while the
decile spread is driven by the tails, and the two can disagree when the relationship is
non-monotonic — good scores mildly better, the very best actively worse. If that is what
it is, it is the single most important fact about this system and it argues against the
whole "top 10 list" framing rather than for a weight change.

Stating this now so a null is not later called expected, and a pass is not later called
predicted.

## Known limits

- **675 symbols, not 1,496.** The score panel covers the original universe; rebuilding it
  for the full universe is a multi-hour crawl. Whether to pay that is a decision, not an
  oversight, and the results file must carry the figure.
- Survivorship is handled inside the panel but the *index membership* map is today's, so
  the same caveat E11 carried applies here.
- No transaction-cost model beyond a flat 40 bps; no turnover accounting at name level.
- 2016-2025 contains one crash (2020) and one drawdown (2022) and no prolonged bear market.

## Outputs

`journal/experiments/E13_results.json` / `.md`, implemented in
`clab/research/e13_topn_portfolio.py`. Per-year and per-N tables before any pooled number.
Nothing is promoted; `promoted` stays false regardless of outcome.
