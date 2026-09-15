# E13 results — top-N portfolio of the measured half

as_of 2026-08-17T03:04:53.659776+00:00  ·  pre-registered at `journal/experiments/E13_topn_portfolio_preregistration.md`

**the MEASURED HALF (FE+BS+VA+EN) only - panel.py excludes all 50 LLM points plus ER, PEG, forward P/E and the reverse DCF.**

Panel `C:\Users\<your-user>\company_lab\journal\experiments\E05_panel_abs.parquet` — 67,889 rows, 52,448 after the 80% coverage filter, 600 symbols. 12-month hold, 40 bps round trip, n_trials=3.

| variant | months | in mkt | ann. net | ann. net ex-2020 | median month | share + | sign p | breakeven |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| top20 | 120 | 120 | 1.3% | 0.3% | 0.2% | 52.5% | 0.65 | 170 bps |
| top40 | 120 | 120 | 2.1% | 1.4% | 0.2% | 55.8% | 0.24 | 252 bps |
| top80 | 120 | 120 | 2.9% | 2.1% | 0.4% | 58.3% | 0.08 | 329 bps |

## Distribution, not two moments

| variant | p05 | p25 | median | p75 | p95 |
|---|---:|---:|---:|---:|---:|
| top20 | -3.8% | -1.2% | 0.2% | 1.8% | 3.6% |
| top40 | -3.5% | -1.3% | 0.2% | 1.6% | 3.2% |
| top80 | -3.1% | -1.0% | 0.4% | 1.4% | 3.2% |

## Gate (copper_brain validate.py, imported not re-ported)

- top20: monthly Sharpe 0.04260065447399611, DSR -0.391 (threshold 1.645), PBO 0.3968, passes=False
- top40: monthly Sharpe 0.08010843755647255, DSR 0.0169 (threshold 1.645), PBO 0.2619, passes=False
- top80: monthly Sharpe 0.12633292125572645, DSR 0.5073 (threshold 1.645), PBO 0.0873, passes=False

## P4 — what E05's -14.1% actually was

E05 reported a mean IC at 3y of +0.0805 beside a top-bottom decile spread of -14.1%, and nothing explained how both could be true. Two things were folded into that number.

| decile spread, top − bottom | 1y | 3y |
|---|---:|---:|
| absolute, no coverage filter | 0.96pp | -14.13pp |
| absolute, ≥80% coverage | 6.27pp | 18.47pp |
| excess over SPY, ≥80% coverage | 6.00pp | 17.02pp |

**1. It is an ABSOLUTE-return spread, not excess over SPY.**

**2. It is computed with no coverage filter, and the bottom decile is contaminated by companies that score low because they are UNMEASURABLE, not because they are bad.** Bottom-decile 3y absolute return is 76.63% unfiltered against 45.28% once the coverage the rubric already requires for a band is applied. Those names are small, young and high-beta, and a decade-long bull market pays them handsomely in absolute terms.

So the score is **not** inverted. E05's headline was a data-coverage artefact crossed with beta. That is also a direct warning about `composite_normalized`: missing data is not random, and companies are being ranked on how measurable they are.

## Pre-registered criteria

- `P1_top20_positive_ex2020_after_cost`: **PASS**
- `P2_median_month_above_zero`: **PASS**
- `P3_size_gradient_runs_the_right_way`: **FAIL**
- `P4_E05_contradiction_reproduced_and_explained`: **PASS**
- `P5_deflated_sharpe_and_pbo`: **FAIL**

**Registered verdict: PASS** (P1 and P2 both required) · **Status: SHADOW**

P4 is a written explanation, not a computed boolean — it is never auto-passed.

Nothing is promoted. `promoted` stays false.