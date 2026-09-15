# Repair pass impact (2026-08-21)

ADVISORY / SHADOW. This measures what the repair did to COVERAGE and to the
ORDERING. It says nothing about accuracy - there is no forward-return grader.

80 of 1500 companies gained at least one quote-backed sub-test.

Median coverage 0.87 -> 0.87.

| threshold | companies gained | companies lost |
|---|---:|---:|
| coverage >= 0.80 | 0 | 3 |
| coverage >= 0.90 | 1 | 1 |

## E12 P4 - within-sector rank correlation of composite_strict

A repair that only fills gaps leaves the ordering inside a sector alone. A
correlation well below 1.0 means it reshuffled the sector, which is a bigger
change than 'more coverage' and must be described as one.

Computed over every company in the sector, not only the repaired ones: a
correlation among the repaired names alone cannot see one of them overtaking a
peer that was not repaired.

| sector | repaired | of peers | scores moved | Spearman |
|---|---:|---:|---:|---:|
| Consumer Discretionary | 16 | 193 | 3 | 0.9983 |
| Information Technology | 14 | 190 | 2 | 0.999 |
| Health Care | 13 | 163 | 2 | 0.9995 |
| Industrials | 9 | 263 | 1 | 0.9992 |
| Financials | 7 | 257 | 1 | 0.9995 |
| Real Estate | 7 | 105 | 1 | 0.9966 |
| Materials | 6 | 77 | 1 | 0.9948 |
| Consumer Staples | 4 | 75 | 2 | 0.9891 |
| Energy | 3 | 71 | 0 | 0.997 |
| Utilities | 1 | 59 | 0 | 0.9993 |

## Band changes

| change | companies |
|---|---:|
| WEAK -> INSUFFICIENT_DATA | 2 |
| REJECT -> INSUFFICIENT_DATA | 1 |
