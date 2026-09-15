# E13 results — top-N portfolio of the measured half

as_of 2026-08-17T15:26:00.289116+00:00  ·  pre-registered at `journal/experiments/E13_topn_portfolio_preregistration.md`

**the MEASURED HALF (FE+BS+VA+EN) only - panel.py excludes all 50 LLM points plus ER, PEG, forward P/E and the reverse DCF.**

Panel `journal\experiments\E14_panel_v2.parquet` — 178,388 rows, 59,917 after the 80% coverage filter, 619 symbols. 12-month hold, 40 bps round trip, n_trials=3.

| variant | months | in mkt | ann. net | ann. net ex-2020 | median month | share + | sign p | breakeven |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| top20 | 120 | 120 | 1.1% | 0.2% | 0.1% | 52.5% | 0.65 | 147 bps |
| top40 | 120 | 120 | 2.3% | 1.4% | 0.2% | 55.8% | 0.24 | 267 bps |
| top80 | 120 | 120 | 2.6% | 1.7% | 0.4% | 55.0% | 0.32 | 301 bps |

## Distribution, not two moments

| variant | p05 | p25 | median | p75 | p95 |
|---|---:|---:|---:|---:|---:|
| top20 | -4.2% | -1.6% | 0.1% | 1.8% | 4.1% |
| top40 | -3.6% | -1.4% | 0.2% | 1.6% | 3.7% |
| top80 | -3.1% | -1.2% | 0.4% | 1.4% | 3.4% |

## Gate (copper_brain validate.py, imported not re-ported)

- top20: monthly Sharpe 0.03340518235406451, DSR -0.4891 (threshold 1.645), PBO 0.3968, passes=False
- top40: monthly Sharpe 0.08130462713679591, DSR 0.0347 (threshold 1.645), PBO 0.2143, passes=False
- top80: monthly Sharpe 0.10697287936241663, DSR 0.3104 (threshold 1.645), PBO 0.1151, passes=False

## P4 — what E05's -14.1% actually was

E05 reported a mean IC at 3y of +0.0805 beside a top-bottom decile spread of -14.1%, and nothing explained how both could be true. Two things were folded into that number.

| decile spread, top − bottom | 1y | 3y |
|---|---:|---:|
| absolute, no coverage filter | 0.64pp | -33.93pp |
| absolute, ≥80% coverage | 8.05pp | 19.73pp |
| excess over SPY, ≥80% coverage | 7.80pp | 19.20pp |

**1. It is an ABSOLUTE-return spread, not excess over SPY.**

**2. It is computed with no coverage filter, and the bottom decile is contaminated by companies that score low because they are UNMEASURABLE, not because they are bad.** Bottom-decile 3y absolute return is 97.02% unfiltered against 45.12% once the coverage the rubric already requires for a band is applied. Those names are small, young and high-beta, and a decade-long bull market pays them handsomely in absolute terms.

So the score is **not** inverted. E05's headline was a data-coverage artefact crossed with beta. That is also a direct warning about `composite_normalized`: missing data is not random, and companies are being ranked on how measurable they are.

## Pre-registered criteria

- `P1_top20_positive_ex2020_after_cost`: **PASS**
- `P2_median_month_above_zero`: **PASS**
- `P3_size_gradient_runs_the_right_way`: **FAIL**
- `P4_E05_contradiction_reproduced_and_explained`: **PASS**
- `P5_deflated_sharpe_and_pbo`: **FAIL**

**Registered verdict: PASS** (P1 and P2 both required) · **Status: SHADOW**

P4 passes only if the diagnostic REPRODUCES E05's -14.1% and the sign flips under both corrections. Reproduction is what makes it an explanation rather than a story that happens to fit.

**Correction — 2026-09-07:** the predicate did not test numerical reproduction. It
tested whether the unfiltered 3-year spread was below -10pp and the coverage-filtered
spread was positive. Restated honestly as
`P4_E05_negative_unfiltered_and_coverage_flip`, this run is **PASS** (-33.93pp to
+19.73pp). It did not reproduce -14.1pp. The registered overall verdict remains PASS and
the status remains SHADOW.

Nothing is promoted. `promoted` stays false.
