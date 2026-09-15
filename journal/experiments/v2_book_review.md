# The v2 book beside production

v1 1501 companies · v2 **1472** · comparable 1472 · in v2 only 0 · in v1 only 29. **Descriptive only** - no criterion, nothing promoted, and neither book has ever been graded against forward returns.

## Shape of the two books

| | n | mean | p25 | median | p75 | max |
|---|---:|---:|---:|---:|---:|---:|
| score v1 | 1472 | 49.52 | 39.75 | 49.0 | 60.0 | 87.0 |
| score v2 | 1472 | 58.32 | 50.0 | 59.0 | 67.0 | 87.0 |
| coverage v1 | 1472 | 0.87 | 0.82 | 0.9 | 0.95 | 1.0 |
| coverage v2 | 1472 | 0.96 | 0.94 | 0.98 | 1.0 | 1.0 |

Coverage gate 0.8: **1184 → 1414** of 1472.

| band | v1 | v2 |
|---|---:|---:|
| EXCEPTIONAL | 0 | 0 |
| HIGH_CONVICTION | 12 | 30 |
| INVESTABLE | 97 | 248 |
| WATCHLIST | 265 | 416 |
| WEAK | 325 | 416 |
| REJECT | 485 | 304 |
| INSUFFICIENT_DATA | 288 | 58 |

## Is it the same ranking?

* Spearman on `score`: **0.922**
* Spearman on `sector_neutral_score` (the cross-sector headline): **0.848**
* Same band: **535** of 1472 (**36%**)
* Top 50 by `sector_neutral_score`: **28 of 50 shared**
  * entered: BKR, CW, DIS, FORM, FSLR, GEN, GMED, HQY, IT, JAZZ, MWA, MYRG, OSIS, PCTY, PEP, PRI, PTC, SANM, STX, TER, TOST, TPR
  * left: ANET, AON, CHWY, DELL, HSTM, KEYS, KLAC, KNSL, META, NFLX, PAYC, PSN, QLYS, RAMP, RL, RMD, SEIC, STRL, TEL, TT, ULS, ZWS

## By sector, most improved first

| sector | n | median score v1 → v2 | banded v1 → v2 | median coverage v1 → v2 |
|---|---:|---:|---:|---:|
| Energy | 70 | 41.0 → 53.5 | 57% → 79% | 0.819 → 0.947 |
| Real Estate | 102 | 35.0 → 47.0 | 43% → 94% | 0.793 → 0.957 |
| Consumer Staples | 74 | 49.5 → 60.0 | 92% → 100% | 0.915 → 0.989 |
| Communication Services | 47 | 51.0 → 61.0 | 79% → 83% | 0.883 → 0.957 |
| Financials | 255 | 48.0 → 58.0 | 78% → 99% | 0.864 → 0.978 |
| Consumer Discretionary | 184 | 49.0 → 58.0 | 85% → 98% | 0.904 → 0.979 |
| Utilities | 59 | 39.0 → 48.0 | 83% → 97% | 0.887 → 0.978 |
| Health Care | 163 | 54.0 → 62.0 | 82% → 98% | 0.915 → 0.979 |
| Materials | 75 | 49.0 → 57.0 | 77% → 97% | 0.904 → 0.968 |
| Industrials | 257 | 54.0 → 61.0 | 88% → 96% | 0.925 → 0.989 |
| Information Technology | 186 | 60.5 → 65.0 | 95% → 98% | 0.936 → 0.989 |

## Broken in the v2 book

A judged component with **zero available points** in v2 where v1 had some: the component generated nothing usable. Not a low score - an absent one.

| component | companies |
|---|---:|
| SG | 0 |
| BQ | 0 |
| MG | 0 |

## Top 25 of the v2 book

| # | ticker | sector | score v1 → v2 | sector-neutral v1 → v2 | band v2 |
|---:|---|---|---:|---:|---|
| 1 | PTC | Information Technology | 84.0 → 87 | 97.5 → 100.0 | HIGH_CONVICTION |
| 2 | NVDA | Information Technology | 85.0 → 86 | 100.0 → 100.0 | HIGH_CONVICTION |
| 3 | FSLR | Information Technology | 82.0 → 84 | 96.9 → 100.0 | HIGH_CONVICTION |
| 4 | VRT | Industrials | 82.0 → 83 | 100.0 → 100.0 | HIGH_CONVICTION |
| 5 | EXEL | Health Care | 83.0 → 87 | 100.0 → 100.0 | HIGH_CONVICTION |
| 6 | APP | Communication Services | 83.0 → 84 | 100.0 → 100.0 | HIGH_CONVICTION |
| 7 | PCTY | Industrials | 80.0 → 87 | 90.0 → 100.0 | HIGH_CONVICTION |
| 8 | MORN | Financials | 78.0 → 80 | 100.0 → 100.0 | HIGH_CONVICTION |
| 9 | JLL | Real Estate | 80.0 → 77 | 100.0 → 100.0 | INVESTABLE |
| 10 | PYPL | Financials | 78.0 → 79 | 100.0 → 100.0 | INVESTABLE |
| 11 | EXLS | Industrials | 77.0 → 82 | 100.0 → 100.0 | HIGH_CONVICTION |
| 12 | APH | Information Technology | 78.0 → 82 | 100.0 → 100.0 | HIGH_CONVICTION |
| 13 | FSS | Industrials | 75.0 → 76 | 100.0 → 100.0 | INVESTABLE |
| 14 | LRN | Consumer Discretionary | 73.0 → 80 | 100.0 → 100.0 | INVESTABLE |
| 15 | GMED | Health Care | 73.0 → 84 | 91.2 → 100.0 | HIGH_CONVICTION |
| 16 | EXPE | Consumer Discretionary | 74.0 → 78 | 100.0 → 100.0 | INVESTABLE |
| 17 | GEN | Information Technology | 74.0 → 79 | 85.7 → 100.0 | HIGH_CONVICTION |
| 18 | AIZ | Financials | 74.0 → 76 | 100.0 → 100.0 | WATCHLIST |
| 19 | TOST | Financials | 73.0 → 80 | 89.5 → 100.0 | HIGH_CONVICTION |
| 20 | PGNY | Health Care | 72.0 → 77 | 100.0 → 100.0 | INVESTABLE |
| 21 | CW | Industrials | 72.0 → 77 | 96.3 → 100.0 | INVESTABLE |
| 22 | BMY | Health Care | 72.0 → 74 | 100.0 → 100.0 | INVESTABLE |
| 23 | STX | Information Technology | 73.0 → 78 | 90.9 → 100.0 | INVESTABLE |
| 24 | SCHW | Financials | 72.0 → 74 | 100.0 → 100.0 | INVESTABLE |
| 25 | TPR | Consumer Discretionary | 72.0 → 79 | 92.3 → 100.0 | HIGH_CONVICTION |

## What this is not

Evidence that either book works. A higher score is a higher score; **no company here has been checked against what it did next.** `promoted` is false.
