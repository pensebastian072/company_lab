# E14 — does sector-neutral ranking pick better companies, or just more diversified ones?

Pre-registration written 2026-08-17, **before any sector-neutral portfolio return was
computed**, while the v2 panel was still being built.

## Why this is a separate study and not an extra column on E13

E13 registered **3 variants** (N ∈ 20/40/80 on `measured_pct`) and `n_trials = 3` fed the
Deflated Sharpe deflation. Adding a second ranking column doubles the search and would
make E13's own gate number wrong retroactively. So this is its own registration with its
own `n_trials = 6` (2 rankings × 3 sizes), and E13's published result stands unmodified.

## What Phase 3 actually did, and what it did not

Sector-neutral scoring replaced a cross-sector comparison with a within-peer-group
percentile. Measured on the live table: sector spread in mean score fell **23.4 → 5.2
points**, Real Estate rising 31.3 → 54.3 and Energy 36.0 → 54.1.

**That proves nothing.** A percentile transform removes sector spread *by construction* —
it is the definition of a percentile, not a discovery. `sector_neutral.spread_report`
says so in its own output. E05's F1 is the standing warning: it moved the spread
24.1 → 19.2, improved within-sector IC 0.0170 → 0.0233, and **failed** its criterion.

## The confound this study exists to catch

E13's clearest finding was that **concentration hurts monotonically**: top20 1.3%,
top40 2.1%, top80 2.9% annualised net, with the Deflated Sharpe going −0.391 → 0.017 →
0.507 as the portfolio widened.

A sector-neutral top-20 is, mechanically, **spread across more sectors** than a raw
top-20, because the raw ranking piles into whichever sectors score high (Information
Technology 54.7 against Real Estate 31.3). So if sector-neutral top-20 beats raw top-20,
**the obvious explanation is diversification, not better selection** — the same effect
that makes top80 beat top20.

Any improvement that is really diversification is not a reason to change the ranking; it
is a reason to hold more names, which E13 already established and which needs no new
scoring machinery at all.

So the design carries an explicit control: **report the number of distinct sectors and
the largest single-sector weight in every portfolio, every month.** If neutral top-20
spans 11 sectors and raw top-20 spans 3, that is the finding, and P3 below is the test
that separates them.

## Construction, fixed now

Identical to E13 in every respect except the ranking column — same
`e11.cohort_series`, same 12-month hold, same 40 bps, same ≥80% coverage proxy, same
`battery.attach_benchmark`, same `copper_brain` gate. Anything that differs would make
the comparison meaningless.

Ranking columns:

| | |
|---|---|
| `measured_pct` | the control, exactly as E13 ran it |
| `measured_pct_sector_neutral` | within-sub-industry percentile of `measured_pct`, computed **per month** across that month's cross-section, falling back to sector below 5 peers |

The percentile must be computed **within each month**, never once over the pooled panel —
pooling would let a 2016 company's rank be set by 2026 peers, which is look-ahead.

## Pass criteria, fixed now

| | passes if |
|---|---|
| **P1** | sector-neutral top-20 annualised excess, net of cost and excluding 2020, is **positive** |
| **P2** | sector-neutral top-20 **beats raw top-20** on annualised net excess |
| **P3** | **the improvement survives the diversification control** — sector-neutral top-20 beats raw top-**80**. If it does not, any gain over raw top-20 is explained by spreading across sectors, which E13 already showed is worth doing on its own |
| **P4** | the **median month** is above zero, and the sign test on positive months is reported beside it |
| **P5** | Deflated Sharpe > 0 (threshold 1.645) and PBO < 0.5 at `n_trials = 6` |

**P2 AND P3 are both required for any claim that sector-neutralisation improves
selection.** P2 alone is the diversification result wearing a better hat.

## Prior, stated before computing

I expect **P2 to pass and P3 to fail.** Reasoning: E13 established that widening the
portfolio improves every measure, and sector-neutral top-20 is a wider portfolio in
sector terms. I expect the gain over raw top-20 to be real and to disappear entirely
against raw top-80.

I expect **P5 to fail** at `n_trials = 6` — the deflation is harsher than E13's 3, and
E13's best variant (top80) reached only 0.507 against a 1.645 threshold.

If that is how it lands, the honest conclusion is that **sector-neutral scoring is a
better way to PRESENT the score — a Real Estate company at the 90th percentile of REITs
is a more useful statement than 31.3 out of 100 — without being a better way to rank
for a portfolio.** Those are different claims and only the first would be supported.

Stating this now so a null cannot later be called expected and a pass cannot later be
called predicted.

## Known limits

- Same as E13: this grades the **measured half** (FE+BS+VA+EN); `panel.py` excludes all
  50 LLM points plus ER, PEG, forward P/E and the reverse DCF.
- The v2 panel is rebuilt with the Phase 1 data-quality layer and Phase 2 archetypes, so
  E14 is **not** comparable to E13's numbers line for line. E13 must be re-run on the
  same panel to give the control — and it is, as the `measured_pct` arm here.
- Sub-industry membership is today's, not point-in-time, so a company reclassified since
  2016 is ranked against the wrong peers in early months.

## Outputs

`journal/experiments/E14_results.json` / `.md`, implemented in
`clab/research/e14_sector_neutral_portfolio.py`. Per-year and per-N tables before any
pooled number. Nothing is promoted; `promoted` stays false regardless of outcome.
