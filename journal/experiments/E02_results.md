# E02 — what the measured half catches, misses, and when

> **B8 pairing note, added 2026-09-10.** `E02_addendum.md` does **not** interpret this
> run. It was written 2026-08-10, two days earlier, against a 495-company / 57,610-row
> panel; this file is the 2026-08-12 run over 675 companies and 67,889 month-ends, and the
> two disagree on Q1 (3 of 10 years and IC +0.013 there, 6 of 10 and +0.043 here — recorded
> as `passes: true` in `E02_results.json`). **This run's panel is not on disk**:
> `E02_panel.parquet` is the addendum's 57,610 / 495. Full record and the open question of
> which run is canonical: `B8_E02_PAIRING_2026-09-10.md`.

Run 2026-08-12T14:48:38.779881+00:00. Pre-registered: `journal/experiments/E02_measured_half_battery_preregistration.md`

Panel: **67889 month-ends** across **675 companies**, 2016-01-31 to 2026-08-31. Median available points **38 of 45** (ER, PEG, forward P/E and reverse DCF are not reconstructible; the LLM half is excluded entirely).


## Q1 — does the measured score rank forward returns?

Absolute returns flatter everything in a rising market, so the excess-over-SPY columns are the ones that answer 'did this beat just owning the index'.

| year | n | SPY | top decile | bottom decile | top − bottom | top vs SPY | mean IC |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2016 | 3928 | +20.7% | +29.0% | +15.2% | +13.8% | +9.6% | +0.090 |
| 2017 | 6866 | +13.3% | +21.2% | +18.2% | +3.0% | +7.8% | +0.095 |
| 2018 | 6783 | +9.5% | +11.1% | +16.6% | -5.4% | +1.7% | -0.004 |
| 2019 | 6705 | +11.4% | +12.5% | +10.8% | +1.7% | +1.2% | +0.103 |
| 2020 | 6688 | +36.0% | +47.3% | +49.4% | -2.1% | +11.3% | +0.073 |
| 2021 | 6591 | -2.5% | -7.7% | +4.6% | -12.3% | -5.3% | -0.065 |
| 2022 | 6461 | +8.2% | +13.1% | +2.9% | +10.2% | +4.8% | +0.064 |
| 2023 | 6361 | +27.8% | +31.2% | +22.8% | +8.4% | +3.4% | +0.086 |
| 2024 | 6209 | +16.4% | +19.3% | +18.3% | +0.9% | +2.9% | +0.006 |
| 2025 | 3448 | +22.0% | +18.4% | +24.6% | -6.2% | -3.6% | -0.067 |

Top decile beat bottom in **6/10** years. Mean monthly IC **+0.043**, positive in +67.8% of months.

**PASS — measured score ranks forward returns**


Against the index: mean monthly IC vs **excess** return **+0.039**, positive in 65.7% of months.


| decile | n | mean 1y | median 1y | hit | vs SPY | mean score |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 6056 | +18.2% | +10.6% | 65.4% | +2.8% | +24.9% |
| 1 | 6002 | +16.0% | +9.4% | 62.6% | +0.4% | +38.7% |
| 2 | 5982 | +16.0% | +9.8% | 63.5% | +0.4% | +46.3% |
| 3 | 6003 | +17.2% | +10.9% | 64.8% | +1.7% | +52.0% |
| 4 | 6007 | +15.6% | +11.5% | 66.1% | +0.1% | +57.0% |
| 5 | 5975 | +15.3% | +10.6% | 65.3% | -0.3% | +61.6% |
| 6 | 5986 | +15.7% | +11.4% | 65.7% | +0.2% | +66.0% |
| 7 | 5999 | +16.0% | +11.6% | 66.3% | +0.5% | +71.0% |
| 8 | 5985 | +18.4% | +13.7% | 69.0% | +2.8% | +76.6% |
| 9 | 6045 | +19.2% | +13.8% | 66.0% | +3.4% | +85.7% |

## Q2 — detection timing on the biggest realised winners

Universe mean score +57.9%; the winners averaged +51.7% at the start of their move, and 7 of 25 were above the universe mean.

Share that ever crossed 70% of available points BEFORE the move: **56.0%**; 60%: **64.0%**.


**What we got wrong, split by whether it was knowable at the time:**

- **caught**: 4 of 25 — score already >=70% of available points before the move
- **should_have_seen**: 6 of 25 — fundamentals were already strong (FE >= 10/15) but valuation or entry held the score down - the framework saw the quality and refused the price
- **couldnt_have_seen**: 15 of 25 — fundamentals were not yet strong at the start; the earnings arrived after the move, so no fundamentals-based score could have known


| ticker | move start | 3y return | score at start | 12m before | max before | crossed 70% first at | EN | FE | VA | verdict |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|---|
| CVNA | 2022-12-31 | +9410.0% | +38.5% | +50.0% | +50.0% | never | 0 | 3 | 0 | couldnt_have_seen |
| ENPH | 2018-01-31 | +8655.8% | +19.0% | +29.4% | +56.0% | never | 1 | 0 | 1 | couldnt_have_seen |
| APP | 2022-12-31 | +5910.5% | +50.0% | +10.0% | +50.0% | never | 0 | 12 | 1 | should_have_seen |
| PLTR | 2022-12-31 | +2729.8% | +61.1% | +43.3% | +61.1% | never | 1 | 10 | 8 | should_have_seen |
| SMCI | 2021-02-28 | +2554.3% | +56.2% | +66.7% | +80.6% | 2016-11-30 | 0 | 6 | 3 | couldnt_have_seen |
| VRT | 2023-04-30 | +2193.4% | +56.2% | +37.5% | +56.2% | never | 2 | 9 | 4 | couldnt_have_seen |
| LITE | 2023-04-30 | +1961.2% | +48.8% | +87.8% | +94.6% | 2018-05-31 | 0 | 7 | 7 | couldnt_have_seen |
| TSLA | 2019-05-31 | +1947.5% | +50.0% | +53.8% | +53.8% | never | 0 | 10 | 0 | should_have_seen |
| WDC | 2023-06-30 | +1828.1% | +41.5% | +82.9% | +85.4% | 2022-02-28 | 1 | 5 | 3 | couldnt_have_seen |
| TTD | 2017-11-30 | +1664.1% | +54.5% | +20.0% | +54.5% | never | 0 | 7 | 1 | couldnt_have_seen |
| STX | 2023-05-31 | +1427.2% | +31.7% | +75.6% | +80.5% | 2018-11-30 | 1 | 6 | 2 | couldnt_have_seen |
| NVDA | 2022-09-30 | +1426.1% | +70.7% | +87.8% | +100.0% | 2016-08-31 | 1 | 10 | 9 | caught |
| MU | 2023-06-30 | +1423.0% | +56.1% | +68.3% | +95.1% | 2017-10-31 | 1 | 9 | 3 | couldnt_have_seen |
| HOOD | 2022-12-31 | +1336.9% | +17.4% | +10.0% | +45.5% | never | 0 | 2 | 0 | couldnt_have_seen |
| FIX | 2023-04-30 | +1230.8% | +73.7% | +71.1% | +89.5% | 2016-08-31 | 0 | 13 | 6 | caught |
| MRNA | 2019-07-31 | +1132.8% | +21.7% | +21.7% | +26.1% | never | 0 | 2 | 0 | couldnt_have_seen |
| CIEN | 2023-04-30 | +1083.1% | +43.8% | +70.7% | +91.9% | 2016-12-31 | 1 | 3 | 1 | couldnt_have_seen |
| ETSY | 2018-01-31 | +1020.1% | +61.1% | +42.9% | +61.1% | never | 1 | 14 | 5 | should_have_seen |
| TRGP | 2020-03-31 | +1016.8% | +50.0% | +53.8% | +53.8% | never | 1 | 6 | 3 | couldnt_have_seen |
| COHR | 2023-05-31 | +919.9% | +63.2% | +86.8% | +89.5% | 2016-08-31 | 1 | 11 | 5 | should_have_seen |
| VST | 2022-09-30 | +899.3% | +50.0% | +70.0% | +82.5% | 2020-04-30 | 1 | 4 | 9 | couldnt_have_seen |
| RCL | 2022-06-30 | +856.2% | +53.7% | +48.8% | +73.2% | 2017-12-31 | 0 | 13 | 5 | should_have_seen |
| GNRC | 2018-10-31 | +853.1% | +86.8% | +60.5% | +86.8% | 2018-01-31 | 2 | 16 | 8 | caught |
| DELL | 2023-05-31 | +828.3% | +43.9% | +67.5% | +78.0% | 2021-07-31 | 1 | 6 | 5 | couldnt_have_seen |
| SEDG | 2018-10-31 | +815.9% | +92.7% | +68.3% | +95.1% | 2016-05-31 | 1 | 18 | 10 | caught |

## Q3 — what it flagged that went badly

Top-decile rows: 6045. Of those, 842 lost more than 20% over the next year — a rate of 13.9% against a universe base rate of 12.5% (WORSE than the base rate).


| ticker | date | 1y | score | FE | BS | VA | EN |
|---|---|---:|---:|---:|---:|---:|---:|
| NKTR | 2018-08-31 | -74.6% | +80.6% | 14 | 8 | 7 | 0 |
| META | 2021-10-31 | -71.3% | +100.0% | 18 | 9 | 8 | 2 |
| NKTR | 2018-09-30 | -69.9% | +83.3% | 14 | 8 | 7 | 1 |
| TSLA | 2021-12-31 | -69.4% | +89.5% | 18 | 8 | 7 | 1 |
| ALGN | 2021-10-31 | -69.0% | +88.6% | 18 | 7 | 5 | 1 |
| ALGN | 2021-09-30 | -69.0% | +88.6% | 18 | 7 | 5 | 1 |
| ALGN | 2021-11-30 | -67.9% | +91.4% | 18 | 7 | 6 | 1 |
| ALGN | 2021-12-31 | -67.8% | +88.6% | 18 | 7 | 5 | 1 |
| IT | 2025-06-30 | -67.0% | +84.2% | 13 | 9 | 8 | 2 |
| ALGN | 2021-08-31 | -65.7% | +85.7% | 18 | 7 | 5 | 0 |
| SMCI | 2024-03-31 | -65.4% | +80.5% | 15 | 9 | 9 | 0 |
| JWN | 2019-03-31 | -64.6% | +83.8% | 10 | 8 | 11 | 2 |

By sector:  204, Information Technology 153, Consumer Discretionary 100, Health Care 97, Financials 93, Industrials 49, Energy 46, Communication Services 46

## Q4 — which component carries the signal

| component | months | mean IC | median IC | share positive |
|---|---:|---:|---:|---:|
| fe | 115 | +0.052 | +0.077 | 69.6% |
| bs | 115 | -0.000 | -0.005 | 44.3% |
| va | 115 | +0.010 | +0.013 | 57.4% |
| en | 115 | -0.051 | -0.050 | 28.7% |
| measured_pct | 115 | +0.043 | +0.051 | 67.8% |

## Q5 — do the bands order returns?

| band | n | mean 1y | median 1y | hit |
|---|---:|---:|---:|---:|
| EXCEPTIONAL | 1419 | +14.9% | +8.9% | 59.3% |
| HIGH_CONVICTION | 5220 | +19.5% | +13.3% | 66.4% |
| INVESTABLE | 9873 | +16.7% | +12.2% | 66.9% |
| WATCHLIST | 13036 | +15.8% | +11.5% | 66.2% |
| WEAK | 12289 | +17.2% | +12.1% | 66.4% |
| REJECT | 18203 | +16.6% | +9.8% | 63.8% |

Monotone across bands with n>=30 (EXCEPTIONAL, HIGH_CONVICTION, INVESTABLE, WATCHLIST, WEAK, REJECT): **False** — FAIL


## Q6 — does the score fall before price?

3918 events where the next year lost more than 30%. The score was already falling beforehand in **38.0%** of them.

A score that falls before price would be genuinely useful. A share near 0.5 means the score carries no early warning.


## What none of this can tell you

- The LLM half (SG/BQ/MG, 50 points) is excluded - it cannot be backtested without hindsight.
- ER, PEG, forward P/E and the reverse DCF are not reconstructible, so the score is out of ~37 of 45 available points.
- Universe is today's index members: delisted and removed constituents are absent, which flatters every long result.
- 2016-2025 was mostly a rising market; value-ish measured factors underperformed over it.
