# E06 results — does following insiders beat holding the index?

as_of 2026-08-13T15:29:37.286145+00:00  ·  source: SEC Form 4 (DERA bulk insider datasets)

733,121 Form 4 non-derivative transactions, 667 symbols, 2016-01-04 → 2026-03-31. 667 of 675 panel symbols have at least one filing.

Only **34.2%** of transactions are discretionary (codes P/S). Open-market purchases: **19,363**; sales: 231,108. The rest are option exercises, tax withholding, awards and gifts — mechanical, not conviction.

Codes: {'S': 231108, 'A': 150957, 'F': 147432, 'M': 134010, 'G': 20904, 'P': 19363, 'J': 10822, 'D': 9377, 'C': 7189, 'X': 708, 'I': 564, 'L': 327}


## The signals, as excess over SPY

| signal | horizon | n | dates | mean excess ON | median ON | mean OFF | edge (mean) |
|---|---|---:|---:|---:|---:|---:|---:|
| S1_open_market_buying | 1y | 8,191 | 108 | 2.7% | -2.4% | 1.0% | 1.7% |
| S1_open_market_buying | 3y | 6,347 | 84 | 16.8% | -12.8% | 7.1% | 9.7% |
| S2_ceo_cfo_buying | 1y | 2,224 | 108 | 2.4% | -4.0% | 1.2% | 1.3% |
| S2_ceo_cfo_buying | 3y | 1,721 | 84 | 46.8% | -17.6% | 7.0% | 39.8% |
| S3_cluster_buying | 1y | 915 | 108 | 2.1% | -1.6% | 1.2% | 0.9% |
| S3_cluster_buying | 3y | 730 | 84 | 24.7% | -12.2% | 8.2% | 16.4% |
| S4_buy_sell_ratio | 1y | 1,965 | 108 | 0.7% | -3.4% | 1.2% | -0.6% |
| S4_buy_sell_ratio | 3y | 1,518 | 84 | 8.4% | -21.6% | 8.5% | -0.1% |
| S5_holdings_change | 1y | 27,155 | 103 | 1.2% | -4.0% | 1.2% | -0.0% |
| S5_holdings_change | 3y | 19,955 | 79 | 10.4% | -14.6% | 6.9% | 3.5% |
| S6_selling | 1y | 41,626 | 108 | 1.7% | -3.1% | 0.1% | 1.5% |
| S6_selling | 3y | 31,589 | 84 | 8.8% | -12.4% | 7.8% | 1.0% |
| X_any_activity | 1y | 44,645 | 108 | 1.6% | -3.1% | -0.1% | 1.7% |
| X_any_activity | 3y | 33,849 | 84 | 9.3% | -12.5% | 6.0% | 3.3% |

## Pre-registered pass criteria

- `S1_mean_excess_positive`: **PASS**
- `S1_positive_in_6_plus_years`: **PASS**
- `S1_enough_date_clusters`: **PASS**
- `S2_beats_S1_at_1y`: **FAIL**
- `S3_beats_S1_at_1y`: **FAIL**
- `S6_does_NOT_predict`: **FAIL**

S1 was positive in 6 of the years present.


**Overall: FAIL**


### Four things that must be read with the table above

**0. The entire edge is one year.** 2020 alone returned 19.9% mean excess. Drop that single year and S1's pooled mean falls from 2.7% to **-0.0%**, against -0.0% for names with no insider buying — an edge of **-0.0%**, with a median of -3.5%. The mean was negative in 4 of 10 years and the median was negative in 7.

> 2020 was the COVID crash. Insiders bought the March bottom, and so did anything else bought in March 2020. Attributing that to insider information rather than to buying a market bottom is the whole question, and one year cannot answer it.

**1. The mean is positive and the MEDIAN is negative** at both horizons (1y: True, 3y: True). The typical name an insider bought UNDERPERFORMED SPY; the positive mean is carried by a right tail. This is the same shape as E05's top decile, and it is why the pre-registration asked for medians beside means.

**2. The falsification check fired.** The pre-registration said selling should NOT predict, and that a positive result there is evidence the construction is wrong rather than a discovery. Selling's 1y mean excess is 1.7% against 2.7% for buying, and undifferentiated insider ACTIVITY gets 1.6% — buying beats mere activity by only 1.1%.

> Buying predicts materially better than undifferentiated activity.

**3. S2 and S3 are horizon-dependent, and the pre-registration did not fix a horizon for them.** At 1y, S2 beats S1: False, S3 beats S1: False. At 3y, S2: True, S3: True. The checks above are scored at 1y because that is what the code fixed before the results were seen. Switching to the 3y reading because it is more flattering would be exactly the after-the-fact choice this project refuses to make — it is reported, not adopted.


**Cost.** At 5.0 bps per side, S1's mean edge nets to 1.6% at 1y and 9.6% at 3y. Cost is not what decides this one.


## S1 per year — before any pooled claim

| year | n | mean excess 1y | median |
|---|---:|---:|---:|
| 2016 | 367 | -0.8% | -3.5% |
| 2017 | 930 | -2.2% | -6.2% |
| 2018 | 1,104 | 1.2% | 0.9% |
| 2019 | 971 | -5.4% | -11.3% |
| 2020 | 1,113 | 19.9% | 8.4% |
| 2021 | 754 | 8.0% | 3.4% |
| 2022 | 913 | 1.8% | -1.3% |
| 2023 | 852 | 0.7% | -5.6% |
| 2024 | 683 | -5.1% | -5.9% |
| 2025 | 504 | 3.0% | -6.8% |
| 2026 | 0 | n/a | n/a |

**Reading S6.** The pre-registration says selling should NOT predict, because executives sell for liquidity and diversification. A positive S6 is a red flag for the construction, not a discovery.


Nothing here is promoted. `promoted` stays false.
