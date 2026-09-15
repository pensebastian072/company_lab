# E13 results — top-N portfolio of the measured half

as_of 2026-08-17T15:26:35.683659+00:00  ·  pre-registered at `journal/experiments/E13_topn_portfolio_preregistration.md`

**the MEASURED HALF (FE+BS+VA+EN) only - panel.py excludes all 50 LLM points plus ER, PEG, forward P/E and the reverse DCF.**

Panel `journal\experiments\E14_panel_v2.parquet` — 178,388 rows, 131,037 after the 80% coverage filter, 1449 symbols. 12-month hold, 40 bps round trip, n_trials=3.

| variant | months | in mkt | ann. net | ann. net ex-2020 | median month | share + | sign p | breakeven |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| top20 | 120 | 120 | -0.5% | -0.9% | -0.0% | 49.2% | 0.93 | -13 bps |
| top40 | 120 | 120 | 0.1% | 0.2% | 0.2% | 51.7% | 0.78 | 49 bps |
| top80 | 120 | 120 | 0.4% | 0.3% | 0.2% | 54.2% | 0.41 | 77 bps |

## Distribution, not two moments

| variant | p05 | p25 | median | p75 | p95 |
|---|---:|---:|---:|---:|---:|
| top20 | -5.5% | -1.8% | -0.0% | 1.9% | 5.4% |
| top40 | -4.9% | -2.2% | 0.2% | 1.8% | 5.2% |
| top80 | -4.5% | -1.6% | 0.2% | 1.6% | 5.0% |

## Gate (copper_brain validate.py, imported not re-ported)

- top20: monthly Sharpe -0.014424097568217536, DSR -1.0101 (threshold 1.645), PBO 0.4484, passes=False
- top40: monthly Sharpe 0.002634249059328125, DSR -0.8241 (threshold 1.645), PBO 0.4802, passes=False
- top80: monthly Sharpe 0.011163334397325492, DSR -0.731 (threshold 1.645), PBO 0.4405, passes=False

## P4 — what E05's -14.1% actually was

E05 reported a mean IC at 3y of +0.0805 beside a top-bottom decile spread of -14.1%, and nothing explained how both could be true. Two things were folded into that number.

| decile spread, top − bottom | 1y | 3y |
|---|---:|---:|
| absolute, no coverage filter | -5.41pp | -25.52pp |
| absolute, ≥80% coverage | -0.11pp | 4.14pp |
| excess over SPY, ≥80% coverage | -0.26pp | 3.83pp |

**1. It is an ABSOLUTE-return spread, not excess over SPY.**

**2. It is computed with no coverage filter, and the bottom decile is contaminated by companies that score low because they are UNMEASURABLE, not because they are bad.** Bottom-decile 3y absolute return is 79.73% unfiltered against 50.92% once the coverage the rubric already requires for a band is applied. Those names are small, young and high-beta, and a decade-long bull market pays them handsomely in absolute terms.

So the score is **not** inverted. E05's headline was a data-coverage artefact crossed with beta. That is also a direct warning about `composite_normalized`: missing data is not random, and companies are being ranked on how measurable they are.

## Pre-registered criteria

- `P1_top20_positive_ex2020_after_cost`: **FAIL**
- `P2_median_month_above_zero`: **FAIL**
- `P3_size_gradient_runs_the_right_way`: **FAIL**
- `P4_E05_contradiction_reproduced_and_explained`: **PASS**
- `P5_deflated_sharpe_and_pbo`: **FAIL**

**Registered verdict: FAIL** (P1 and P2 both required) · **Status: SHADOW**

P4 passes only if the diagnostic REPRODUCES E05's -14.1% and the sign flips under both corrections. Reproduction is what makes it an explanation rather than a story that happens to fit.

**Correction — 2026-09-07:** the predicate did not test numerical reproduction. It
tested whether the unfiltered 3-year spread was below -10pp and the coverage-filtered
spread was positive. Restated honestly as
`P4_E05_negative_unfiltered_and_coverage_flip`, this run is **PASS** (-25.52pp to
+4.14pp). It did not reproduce -14.1pp. The registered overall verdict remains FAIL and
the status remains SHADOW.

Nothing is promoted. `promoted` stays false.
