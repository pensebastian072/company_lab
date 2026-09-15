# E11 results — is E10's insider edge investable?

as_of 2026-08-16T19:35:11.753293+00:00  ·  pre-registered at `journal/experiments/E11_insider_investability_preregistration.md`

Overlapping equal-weighted cohorts, 12-month hold, 40 bps round trip, n_trials=4. Months with no active cohort are held in cash at zero excess, never dropped.

## Variants (all four registered before computing)

| variant | signals | months | in mkt | ann. net | ann. net ex-2020 | median month | share + | breakeven |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| sp600_insiders_ge_1 | 10,389 | 120 | 120 | 4.9% | 4.5% | 0.1% | 50.8% | 529 bps |
| sp600_insiders_ge_3 | 1,844 | 120 | 120 | 7.7% | 7.5% | 0.3% | 55.0% | 810 bps |
| sp500_insiders_ge_1 | 7,879 | 120 | 120 | 3.2% | 3.1% | 0.2% | 55.0% | 355 bps |
| sp500_insiders_ge_3 | 862 | 120 | 120 | 4.6% | 5.0% | 0.0% | 50.0% | 498 bps |

## The distribution, not two moments

| variant | p05 | p25 | median | p75 | p95 |
|---|---:|---:|---:|---:|---:|
| sp600_insiders_ge_1 | -5.0% | -2.2% | 0.1% | 2.5% | 6.9% |
| sp600_insiders_ge_3 | -6.1% | -2.3% | 0.3% | 4.0% | 8.5% |
| sp500_insiders_ge_1 | -2.5% | -0.8% | 0.2% | 1.5% | 3.3% |
| sp500_insiders_ge_3 | -4.4% | -1.6% | 0.0% | 2.5% | 5.5% |

## Capacity

A $10,000 position capped at 1% of median 20-day dollar volume.

| variant | signals checked | blocked | share |
|---|---:|---:|---:|
| sp600_insiders_ge_1 | 10,300 | 243 | 2.4% |
| sp600_insiders_ge_3 | 1,815 | 45 | 2.5% |
| sp500_insiders_ge_1 | 7,822 | 0 | 0.0% |
| sp500_insiders_ge_3 | 857 | 0 | 0.0% |

## Gate (copper_brain validate.py, imported not re-ported)

- sp600_insiders_ge_1: monthly Sharpe 0.10235723760161075, DSR ratio 0.0735 (threshold 1.645), PBO 0.0516, passes=False
- sp600_insiders_ge_3: monthly Sharpe 0.12729290549596659, DSR ratio 0.3519 (threshold 1.645), PBO 0.0516, passes=False
- sp500_insiders_ge_1: monthly Sharpe 0.13124642320775673, DSR ratio 0.3582 (threshold 1.645), PBO 0.0397, passes=False
- sp500_insiders_ge_3: monthly Sharpe 0.11836854665368436, DSR ratio 0.2725 (threshold 1.645), PBO 0.0476, passes=False

## Pre-registered criteria

- `P1_positive_excess_ex2020_after_cost`: **PASS**
- `P2_median_monthly_excess_above_zero`: **PASS**
- `P3_cluster_filter_raises_the_median`: **PASS**
- `P4_capacity_under_10pct_blocked`: **PASS**
- `P5_breakeven_cost_above_40bps`: **PASS**
- `P6_deflated_sharpe_and_pbo`: **FAIL**

**Registered verdict: PASS**  (P1 and P2 both required) · **Status: SHADOW**

> PASS on the registered economic criteria, FAIL on the overfit gate. The median month clears zero by 0.12% on 61 positive months out of 120 (sign test p=0.93) - a coin flip. Deflated Sharpe is 0.0735 against a 1.645 threshold. Stays SHADOW.

### The median clears zero, and that is almost all it does

A post-hoc sign test, reported because P2 can be passed by a hair and reporting the pass alone would be true and misleading:

| variant | months | positive | sign-test p |
|---|---:|---:|---:|
| sp600_insiders_ge_1 | 120 | 61 | 0.93 |
| sp600_insiders_ge_3 | 120 | 66 | 0.32 |
| sp500_insiders_ge_1 | 120 | 66 | 0.32 |
| sp500_insiders_ge_3 | 120 | 60 | 1.00 |

Not a pre-registered criterion, and it does not change the registered verdict. It is here so the verdict cannot be read as stronger than it is.

### Survivorship, stated in the results and not only in the plan

The bucket map is TODAY's index membership. A company that fell out of the S&P 600 after a collapse is absent from the panel, which biases every number here upward. E11 does not fix that and cannot; it is the same unfixed defect that gates the entry-rule studies.

Nothing is promoted. `promoted` stays false.