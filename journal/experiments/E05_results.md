# E05 results — the four fixes, measured on the survivorship-free panel

as_of 2026-08-12T14:49:58.593648+00:00

Panel: 67,889 rows, 675 symbols, 2016-01-31 → 2026-08-31, median available 38 points.
**Survivorship-free** — companies removed from the index are present until the month they left.

Every fix was designed on the BIASED panel, so this is a genuine holdout. Criteria were fixed in the pre-registration before this run.


### The sector variable had to be repaired first

The GICS sector comes from the Wikipedia CURRENT-members table, so it is **missing for 182 of 675 companies** — 15.9% of rows, which is exactly the set the survivorship fix added. Left alone they form one pseudo-sector mixing utilities with software, and F1 is a *sector* fix, so that would have measured it against a fake variable.

SIC (from the cached EDGAR submissions, no new requests) resolves 99.8% of them, leaving 1 unclassified. But SIC and GICS agree on only **78.2%** of the 491 companies where both exist, so the F1 verdict is reported under all three definitions below.

Largest GICS → SIC disagreements: Consumer Discretionary -> Industrials (14), Industrials -> Information Technology (11), Financials -> Industrials (10), Information Technology -> Industrials (7), Consumer Staples -> Materials (7).


## F1 — sector-relative margins and returns

**FAIL** — within_sector_ic_positive=yes, sector_spread_halved=no

Did the change bind at all? 97.2% of rows scored on the sector-relative basis; FE moved on 78.6% of rows, mean |ΔFE| 1.86 points, mean Δmeasured% -0.0484.

| | absolute | sector-relative |
|---|---:|---:|
| pooled IC 1y | 0.0426 | 0.0438 |
| **within-sector IC 1y** | 0.0170 | 0.0233 |
| IC 3y | 0.0805 | 0.0774 |
| top−bottom decile 3y | -0.1413 | -0.0941 |
| score variance from sector | 0.1726 | 0.1212 |
| **sector spread in mean score** | 24.1 pts | 19.2 pts |

Criterion: within-sector IC > 0 and sector spread < 10.7 pts (half of 21.4).

- absolute: highest Information Technology 62.6%, Financials 62.0%, Health Care 61.2% | lowest Consumer Staples 53.4%, Real Estate 48.3%, Utilities 38.5%
- sector-relative: highest Unclassified 57.4%, Financials 57.0%, Information Technology 56.6% | lowest Consumer Staples 48.3%, Real Estate 45.9%, Utilities 38.2%

### F1 under each sector definition

| definition | rows | symbols | within-sector IC (abs → rel) | sector spread pts (abs → rel) | passes |
|---|---:|---:|---:|---:|:--:|
| gics_only | 57,115 | 493 | 0.0014 → 0.0063 | 24.7 → 19.4 | FAIL |
| sic_filled | 67,889 | 675 | 0.0170 → 0.0233 | 24.1 → 19.2 | FAIL |
| sic_for_everyone | 67,889 | 675 | 0.0188 → 0.0249 | 26.4 → 27.7 | FAIL |

gics_only silently drops every removed constituent and so reintroduces the survivorship bias E04 removed; it is here as a comparison, not as the headline.

**The verdict does NOT depend on which sector definition is used.**


## F3 — band hysteresis

**FAIL** — change_rate_under_12pct=no, median_months_over_4=yes, ic_materially_unchanged=yes

| | raw | smoothed |
|---|---:|---:|
| band change rate / month | 21.8% | 12.8% |
| median months in a band | 3.0 | 5.0 |
| band IC 1y | 0.0448 | 0.0484 |
| band IC 3y | 0.0829 | 0.0846 |

ΔIC 1y 0.0036, ΔIC 3y 0.0017 (criterion |ΔIC 1y| < 0.005).

Delay cost — observations whose next 12 months returned <= -30%. This is a HORIZON RETURN, not a peak-to-trough drawdown. n=3,977; the smoothed band differed on 17.1% of them and was **more flattering** on 7.8%.


## F4 — default to three years

F4 changes no score, so it cannot fail on data. The horizon numbers here are new: they are the first computed on a survivorship-free panel.

| horizon | mean IC | share of months positive | top−bottom decile | n |
|---|---:|---:|---:|---:|
| 1y | 0.0426 | 67.8% | 1.0% | 60,040 |
| 3y | 0.0805 | 92.3% | -14.1% | 45,588 |

Excess over SPY — the comparison actually asked for:

| horizon | mean IC vs excess | top decile mean excess | median | n dates |
|---|---:|---:|---:|---:|
| 1y | 0.0391 | 3.4% | -1.2% | 108 |
| 3y | 0.0778 | 11.9% | -7.6% | 84 |

## F2

Not implemented, deliberately: F1 and F2 both touch FE and a combined result would be unattributable. Still open.


Nothing here is promoted. `promoted` stays false.
