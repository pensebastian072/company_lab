# E34 results - "did not repurchase" is a fact, and it is mostly a BAD one

Measured 2026-08-26 against `E34_buyback_absence_preregistration.md`. All four criteria
pass. **The prior was wrong on two of three numbers**, and the interesting one is wrong in
a way that changes what the rule means.

## The change

`mg_buyback_discipline` scored `no_data` — reason `"input unavailable"` — for a third of
the universe, while its sibling ten lines below (`mg_ma_track_record`) already scores **2**
for *"no acquisitions and no impairments in the trailing year"*. Two absences of the same
kind read in opposite directions inside one component.

Where there are no repurchases, the sub-test now reads the share count instead of
abstaining. A company with **no `dilution_yoy` either still abstains** — that is P2, and it
is what keeps this a measurement rather than a default.

## Criteria

Computed by classifying every company's stored inputs under all three code paths, so the
comparison is exact rather than a diff across two crawls:

| mode | scored normally | scored on absence | NO_DATA | **falsely labelled** |
|---|---:|---:|---:|---:|
| before E34 | 1,133 | 0 | **311** | 0 |
| E34 first draft | 1,133 | 288 | 23 | **147** |
| **E34 as shipped** | 1,133 | **141** | **170** | **0** |

| | result |
|---|---|
| **P1** sibling asymmetry is real | **PASS** - `mg_ma_track_record` scores its analogous absence, pinned by a test |
| **P2** nothing scored without a dilution series | **PASS** - 0 violations; 170 companies correctly still `NO_DATA` |
| **P3** not a gift - at least 15% at 0 or 1 | **PASS** - **83.0%** score 0 or 1 |
| **P4** within-sector Spearman above 0.98 | **PASS** - worst 0.9965 (Utilities); nine sectors above 0.999 |

## The prior, scored honestly

| prediction | outcome |
|---|---|
| 200-260 newly scored | **141** - wrong, and low |
| skewed toward 2 points; 20-35% at 0 or 1 | **badly wrong - 83.0% at 0 or 1**, and only 17.0% at 2 |
| fewer than 40 gaining a band | **right - 12** |

## What the 83% actually means

I predicted most non-repurchasers would score 2, because most S&P constituents are not
diluting. The opposite is true:

| points | companies | share |
|---|---:|---:|
| 0 - no repurchases while the share count grew above the tolerated band | **66** | 46.8% |
| 1 - no repurchases, dilution inside the band (ordinary SBC) | 51 | 36.2% |
| 2 - no repurchases and the count flat or shrinking | 24 | 17.0% |

**A company that does not repurchase is usually a company that is diluting.** So this is
not a coverage lever dressed as a rule - it assigns a *low* score to five companies in six
it touches, and P3 passes by a factor of five rather than scraping over its bar. Had the
distribution come back the way I predicted, P3 would have been close and the honest
conclusion might have been that the absence carries no information.

Coverage rises by about **+0.021** for the 141 (2 points of ~94 applicable), and **12**
companies cross the 0.80 band gate: HWKN, WSBC, HE, BLFS, BXP, PI, AAT, VICI, NABL, SN,
WS, NWE. Note that seven of those twelve earned **0 or 1** on the very sub-test that banded
them - they are banded because more of the framework is now answered, not because they
scored well.

## The first draft would have shipped 147 false statements

The branch was originally `elif dil is not None`, which fires whenever the *normal* path
declines — and that path also declines when repurchases **exist** but free cash flow is
zero, negative or undefined. That is every bank, and every company with negative FCF.

The result: **JPM labelled "no repurchases" while holding $31,670,000,000 of them.** Also
Boeing ($2.65bn), ADP ($2.08bn) and Aflac ($3.79bn) — 147 companies in total carrying a
note that was simply untrue.

**And my own check said zero.** The query filtered on `s.get("note")`; the field is
`threshold_note`. It read `None` for every row, the substring never matched, and the check
reported clean. That is the same failure class as everything else in this pass — NaN
passing `is not None`, `getattr(fact, "value")` returning `None`, a parquet NaN surviving
an `is not None` split. **A verification that reads the wrong field does not fail loudly;
it passes quietly**, and it is more dangerous than no check at all because it retires the
suspicion.

The branch is now guarded on `buybacks is None` explicitly, so those 147 fall back to
`NO_DATA` — honest, because they *did* repurchase and we simply cannot express it as a
share of cash flow. `tests/test_buyback_absence.py` pins that case by name.

## What this does not establish

Nothing here tests whether any of it predicts anything. There is no forward-return grader
— it needs ~50 weekly snapshots and the `as_first_filed` view, and **5** exist. This
changes what 141 companies are scored on with no way to check whether the new scores are
better, only whether they are more internally consistent. `promoted` stays false.

**It changes the framework**, so the snapshot series is discontinuous at this date for
those 141 — unlike E33, which corrected arithmetic and display and left the framework
identical.

`mg_reinvestment_quality` was deliberately out of scope and stays `NO_DATA` where capex is
absent. Its argument is different and has not been made.
