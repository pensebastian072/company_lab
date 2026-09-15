# E10 results — insider buying by company size

as_of 2026-08-15T00:49:12.892516+00:00  ·  SEC Form 4 (DERA bulk insider datasets)

1497 companies, 1,335,563 Form 4 transactions, 38,461 open-market purchases. Buckets: {'sp400': 398, 'sp500': 500, 'sp600': 599}

E06 answered this for large caps: no, and its entire edge was 2020. The question here is whether the literature's small-firm result shows up where information asymmetry is actually larger.


## S1 open-market buying, excess over SPY

| bucket | horizon | n | dates | mean ON | median ON | mean OFF | edge |
|---|---|---:|---:|---:|---:|---:|---:|
| sp500 | 1y | 7,101 | 108 | 5.3% | -0.1% | 2.9% | 2.4% |
| sp500 | 3y | 5,576 | 84 | 18.5% | -5.1% | 11.5% | 7.0% |
| sp400 | 1y | 5,538 | 108 | 6.8% | -1.6% | 2.5% | 4.2% |
| sp400 | 3y | 4,284 | 84 | 13.9% | -12.7% | 6.1% | 7.8% |
| sp600 | 1y | 9,171 | 108 | 6.9% | -4.0% | -0.9% | 7.8% |
| sp600 | 3y | 6,792 | 84 | 10.7% | -25.4% | -5.1% | 15.8% |

## The same thing with 2020 removed

E06's whole edge was that single year. An edge that needs it is not an edge.

| bucket | horizon | mean ON | mean OFF | edge |
|---|---|---:|---:|---:|
| sp500 | 1y | 3.1% | 2.3% | 0.8% |
| sp500 | 3y | 14.9% | 10.9% | 4.0% |
| sp400 | 1y | 0.0% | 0.2% | -0.1% |
| sp400 | 3y | 4.1% | 1.8% | 2.3% |
| sp600 | 1y | 2.1% | -4.0% | 6.1% |
| sp600 | 3y | 8.3% | -8.9% | 17.3% |

## Falsification checks

| bucket | selling mean 1y | any-activity mean 1y | buying mean 1y |
|---|---:|---:|---:|
| sp500 | 3.2% | 3.3% | 5.3% |
| sp400 | 1.8% | 2.7% | 6.8% |
| sp600 | -2.5% | -0.7% | 6.9% |

Selling should NOT predict, and buying should beat undifferentiated activity. In E06 both failed, which is the signature of an attention confound rather than information.


## Pre-registered criteria

- `P1_smallcap_positive_excluding_2020`: **PASS**
- `P2_size_gradient_runs_the_right_way`: **PASS**
- `P3_median_above_zero_somewhere`: **FAIL**
- `P4a_selling_does_not_predict`: **PASS**
- `P4b_buying_beats_mere_activity`: **PASS**
- `enough_date_clusters`: **PASS**

**Overall: PASS**


### Read this before acting on the PASS

**The mean is positive and the MEDIAN is negative in every bucket** (sp500 -0.1%, sp400 -1.6%, sp600 -4.0%). The typical company an insider bought still UNDERPERFORMED SPY; the edge lives in a right tail. Across the S&P 600's 11 years the mean was positive in 8 but the median in only 4.

That is the same shape as E05's top decile and E06's large-cap result, and it is why the pre-registration asked for medians beside means. A positive mean edge with a negative median is a statement about a minority of large winners, not about what a holder of these names experiences.

It is also **not a tested strategy**: no costs beyond the E06 assumption, no position sizing, no capacity check on small-cap liquidity, and the S&P 600 is small-cap WITHIN an index - the microcap tail where the literature's effect is strongest is absent entirely.


## S&P 600 per year

| year | n | mean excess 1y | median |
|---|---:|---:|---:|
| 2016 | 309 | 8.0% | 4.6% |
| 2017 | 803 | 9.7% | -4.1% |
| 2018 | 1,064 | 3.9% | -7.1% |
| 2019 | 948 | -9.5% | -17.8% |
| 2020 | 1,330 | 34.6% | 17.8% |
| 2021 | 853 | 8.3% | 0.7% |
| 2022 | 1,099 | 1.0% | -6.8% |
| 2023 | 1,120 | 1.3% | -7.8% |
| 2024 | 967 | -6.4% | -13.3% |
| 2025 | 678 | 11.7% | 2.9% |
| 2026 | 0 | n/a | n/a |

Nothing is promoted. `promoted` stays false.
