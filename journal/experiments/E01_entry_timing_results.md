# E01 - does the EN entry rule improve timing?

Run 2026-08-10T15:36:53.065324+00:00. Pre-registered: `journal/experiments/E01_entry_timing_preregistration.md`

Watchlist: top 100 by composite. Signal: EN >= 4, 60-day cooldown. Cost 5.0 bps/side.

**958 clustered signals**, 19800 random-date controls.


## Per-year, 1-year holding period (this table comes first on purpose)

| year | n | signal mean | random mean | edge (mean) | signal med | random med | edge (med) |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2017 | 30 | +21.2% | +29.8% | -8.6% | +7.8% | +26.2% | -18.5% |
| 2018 | 99 | +16.7% | +19.5% | -2.8% | +18.1% | +17.9% | +0.2% |
| 2019 | 120 | +16.2% | +22.4% | -6.2% | +13.0% | +16.3% | -3.4% |
| 2020 | 135 | +52.6% | +46.2% | +6.4% | +46.6% | +40.8% | +5.8% |
| 2021 | 76 | +1.5% | -4.9% | +6.4% | +1.3% | -5.9% | +7.2% |
| 2022 | 170 | +20.0% | +19.3% | +0.7% | +17.6% | +10.9% | +6.7% |
| 2023 | 143 | +33.5% | +48.5% | -15.1% | +26.9% | +30.0% | -3.2% |
| 2024 | 104 | +11.0% | +32.4% | -21.4% | +9.1% | +14.3% | -5.2% |
| 2025 | 74 | +6.2% | +444.4% | -438.2% | -2.4% | +13.7% | -16.1% |

Years with a positive edge: **3/9** on the mean, **4/9** on the median.

The median matters here: a few 10x recoveries dominate any mean over this window. The pre-registered test named the mean, so that is what the verdict uses - the median is reported alongside, not instead.


## Pooled

| horizon | n | signal | random | edge | vs SPY | signal hit | random hit |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1y | 951 | +22.3% | +56.9% | -34.6% | +4.1% | +73.3% | +74.3% |
| 3y | 702 | +85.8% | +103.7% | -17.9% | +29.9% | +65.0% | +66.7% |
| 5y | 411 | +166.0% | +174.2% | -8.2% | +70.5% | +40.1% | +48.8% |

### Correction — 2026-09-07

The original hit-rate columns above divided wins by every generated row, so unavailable
forward returns counted as losses. The corrected signal rates among observed returns are
**73.82% (702/951)** at 1 year, **88.75% (623/702)** at 3 years, and **93.43%
(384/411)** at 5 years. The historical random-control rows and their observed-horizon
counts were not saved; only the 19,800 generated-row total and the biased aggregate
rates remain, so no corrected historical random rate or observed `n` can be recovered
without a rerun. Future results record separate signal and random observed `n`s beside
every hit rate.

This denominator correction does not change the mean returns, the failed H1/H2 gates,
or the SHADOW verdict.

## $10,000 per signal

| horizon | trades | staked | profit | per trade | random per trade |
|---|---:|---:|---:|---:|---:|
| 1y | 951 | $9,510,000 | $2,123,368 | $2,233 | $5,690 |
| 3y | 702 | $7,020,000 | $6,021,027 | $8,577 | $10,368 |
| 5y | 411 | $4,110,000 | $6,821,887 | $16,598 | $17,422 |

## By EN score, and confluence

| EN | n | mean 1y |
|---|---:|---:|
| 4 | 237 | +21.0% |
| 5 | 714 | +22.8% |

Confluence: n=951 mean +22.3% vs no-confluence n=0 mean -


## Pre-registered hypotheses

- FAIL  H1_beats_random_1y
- FAIL  H2_positive_in_6_of_9_years
- PASS  H3_confluence_beats_partial
- PASS  H4_beats_spy_1y_and_3y

**Verdict: entry rule does NOT clear its pre-registered tests - it should stay a 5-of-100 tiebreaker, not a gate**


## What this cannot tell you

- Watchlist chosen with today's knowledge - survivorship and selection bias are present by construction.
- No LLM score used; SG/BQ/MG excluded entirely.
- Delisted and removed constituents absent from the price store.

Skipped 1 names: V (no P/E series)
