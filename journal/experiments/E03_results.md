# E03 — the questions nobody asked

Run 2026-08-12T14:48:59.031366+00:00. Pre-registered: `journal/experiments/E03_questions_not_asked_preregistration.md`

Panel: 67889 month-ends, 675 companies, 2016-01-31 to 2026-08-31. Measured half only; survivorship applies throughout.


## R1 — quality bet, or sector bet?

- pooled IC **+0.043**
- within-sector IC **+0.018**
- IC retained after removing sector: **+42.0%**
- share of score variance explained by sector alone: **+16.0%**

**score largely disappears within sector - it is substantially a sector bet**


Mean score by sector (a tilt would show here):

| sector | mean score |
|---|---:|
| Information Technology | +63.0% |
| Financials | +62.8% |
| Health Care | +61.6% |
| Consumer Discretionary | +61.5% |
| Industrials | +59.4% |
| Communication Services | +57.8% |
|  | +57.2% |
| Materials | +55.5% |
| Energy | +55.0% |
| Consumer Staples | +54.0% |
| Real Estate | +49.3% |
| Utilities | +38.3% |

## R2 — does the trajectory beat the level?

- IC of the score LEVEL: **+0.035**
- IC of the 12-month CHANGE: **-0.018**

**the level carries at least as much as the trajectory**


| cell | n | mean 1y | median 1y |
|---|---:|---:|---:|
| high_level + improving | 16299 | +14.6% | +9.6% |
| high_level + deteriorating | 9910 | +18.8% | +13.4% |
| low_level + improving | 8203 | +16.9% | +9.3% |
| low_level + deteriorating | 17818 | +16.2% | +9.8% |

## R3 — is the horizon the problem?

| horizon | n | mean IC | share positive | top decile | bottom decile | spread |
|---|---:|---:|---:|---:|---:|---:|
| 1y | 60040 | +0.043 | 67.8% | +19.2% | +18.2% | +1.0% |
| 3y | 45588 | +0.081 | 92.3% | +62.5% | +76.6% | -14.1% |

**IC improves with horizon - earlier tests were too short**


## R4 — is it stable enough to act on?

- median month-to-month move in the score: **+2.4%** (p90 +8.1%)
- months where the score moved more than 10 points: 7.0%
- band changes per month: **21.8%**
- median months spent in a band before leaving: **3.0**

A band that changes every month or two cannot be traded on regardless of its IC. This is a usability number, not a pass/fail.


## R5 — the cyclical defect

4518 cyclical rows vs 63371 others.

| population | mean IC 1y | mean IC 3y |
|---|---:|---:|
| cyclical | -0.028 | +0.010 |
| other | +0.044 | +0.079 |

Cyclicals by score quintile, 3-year forward:

| quintile | n | mean 3y | median 3y |
|---|---:|---:|---:|
| 0 | 646 | +110.7% | +52.9% |
| 1 | 588 | +160.9% | +52.3% |
| 2 | 592 | +127.1% | +68.3% |
| 3 | 588 | +101.9% | +72.9% |
| 4 | 646 | +94.4% | +57.0% |

top minus bottom quintile: **-16.3%**

**confirmed: inside cyclicals a HIGH score preceded WORSE 3y outcomes**


## R6 — what it never owns


**bottom decile** (n=6850): median P/E -, median 3y revenue CAGR +0.2%, median operating margin +14.1%, negative FCF in 26.4% of rows
  sectors: Utilities 1515,  942, Real Estate 763, Industrials 558, Information Technology 536

**top decile** (n=6837): median P/E -, median 3y revenue CAGR +13.3%, median operating margin +21.4%, negative FCF in 1.2% of rows
  sectors: Information Technology 1302, Financials 1094,  960, Consumer Discretionary 882, Health Care 830

**115 companies were never once in the top 3 deciles** in ten years.

Examples: AAL, ABNB, ADP, AEE, AEP, AES, AIV, ANDV, ARG, AWK, BALL, BF-B, BG, BHF, BLK, BRK-B, CA, CAM, CCE, CCI, CHTR, CMS, CNP, CNX

Those names: median 1y return +6.4%, median operating margin +19.2%
sectors: Utilities 2541,  1505, Real Estate 1184, Industrials 590, Consumer Staples 515, Consumer Discretionary 427

This is the shape of the hole. Every ranking excludes something; the question is whether this exclusion is intentional.


## Limits that apply to every line above

- Measured half only - the LLM half cannot be backtested without hindsight.
- Universe is today's index members, so survivorship inflates every long result and makes the bottom decile 'low scores that survived'.
- 2016-2025 contains no prolonged bear market.
- ER, PEG, forward P/E and the reverse DCF are not reconstructible.
