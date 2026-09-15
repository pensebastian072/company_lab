# E08 results — is the discount deserved?

as_of 2026-08-12T14:50:09.230064+00:00

Panel: 67,889 rows, 675 symbols. Share computable on 59.8% of rows (needs ≥5 sub-industry peers); 3-year share change on 37.8%.

**Limit, and it is not a small one:** the peer group is S&P 500 members only, so this is share of large-cap LISTED peers, not true market share. A company losing real ground to a private or foreign competitor can read as flat here.


## H3 — the decisive test: does the filter beat SPY?

**FAIL**

| top decile, 3y excess over SPY | n | mean | **median** | share > 0 |
|---|---:|---:|---:|---:|
| unfiltered | 4,590 | 12.1% | **-7.4%** | 45.3% |
| where share is known | 1,288 | -3.3% | **-24.0%** | 34.9% |
| **declining share excluded; NO_DATA retained** | 4,362 | 12.2% | **-7.1%** | 45.3% |
| rising share only (diagnostic) | 1,060 | -6.1% | **-24.7%** | 33.0% |
| rising share only, ex-mergers (diagnostic) | 1,006 | -5.5% | **-25.3%** | 32.9% |
| declining share (excluded) | 228 | 9.4% | **-16.7%** | 43.4% |

The filter drops 8.6% of the top decile. Criterion: median above zero.


## H1 — share direction inside the top decile

**FAIL** — {'1y': False, '3y': False}

| horizon | group | n | mean | median | share > 0 |
|---|---|---:|---:|---:|---:|
| 1y | rising share | 1,624 | 2.2% | -1.1% | 48.5% |
| 1y | declining share | 420 | 0.6% | 0.2% | 50.5% |
| 3y | rising share | 1,060 | -6.1% | -24.7% | 33.0% |
| 3y | declining share | 228 | 9.4% | -16.7% | 43.4% |

## H2 — the four quadrants (the FICO case is 'harvesting')

**FAIL** — {'harvesting_worse_than_winning': False, 'harvesting_worse_than_losing': False, 'harvesting_worse_than_buying_share': False}

| quadrant | n | 3y mean | 3y median | share > 0 |
|---|---:|---:|---:|---:|
| winning | 3,276 | -11.6% | -28.3% | 31.4% |
| buying_share | 3,386 | -16.4% | -31.2% | 26.8% |
| harvesting | 3,577 | -1.2% | -14.3% | 37.6% |
| losing | 2,334 | 4.1% | -18.4% | 33.9% |

## H4 — is it independent of the score?

**FAIL**

| horizon | raw IC | partial IC controlling for the score |
|---|---:|---:|
| 1y | -6.6% | -7.6% |
| 3y | -9.0% | -10.0% |

## Per year — top decile 3y median excess, rising vs declining share

| year | rising n | rising median | declining n | declining median |
|---|---:|---:|---:|---:|
| 2019 | 137 | -15.8% | 31 | 33.6% |
| 2020 | 254 | -7.9% | 63 | -28.1% |
| 2021 | 259 | -26.4% | 48 | 8.3% |
| 2022 | 258 | -41.4% | 58 | -26.8% |
| 2023 | 152 | -56.5% | 28 | -43.6% |
| 2024 | 0 | n/a | 0 | n/a |
| 2025 | 0 | n/a | 0 | n/a |
| 2026 | 0 | n/a | 0 | n/a |

Nothing here is promoted. `promoted` stays false. A scoring change requires its own pre-registration and only if H3 passed.
