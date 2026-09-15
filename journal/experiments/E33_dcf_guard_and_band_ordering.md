# E33 - three correctness fixes: the DCF's margin of safety, a band ordering bug, label drift

2026-08-25/26. **No registration**: none of these changes a weight, a threshold or a
denominator. Two are display, one is a band-state ordering bug. Scores are untouched.

Prompted by an outside review of the workbook plus a direct request to check the DCF and
the margin of safety. The review found one of the three defects; measuring it found two
more, and the biggest was the one nobody had looked for.

---

## A. The margin of safety inverted its sign on a negative fair value

`margin_of_safety = (fair - price) / fair`, guarded by `if fv` — which catches `fv == 0`
and **nothing else**. With a negative fair value the numerator and denominator go negative
together and the result comes out **positive**.

| | fair value | reported margin of safety |
|---|---:|---:|
| HR | **-$0.008** | **+251,695%** |
| VST | -$0.76 | +17,846% |
| BLDR | $0.023 | -307,711% |

117 companies carried an absolute margin of safety above 500%. **And the DCF sheet sorts
on that column descending**, so a model saying the equity is worthless ranked as the
cheapest company in the workbook.

**Fix.** The margin of safety is emitted only when the fair value is finite, **strictly
positive**, and the DCF is not flagged implausible. `implausible` is now computed before
the return dict so the guard can read it.

## B. Every flagged DCF carried a flag with no explanation

`dcf_reason` was `None` for all 125 implausible companies — the workbook showed a $1,400
fair value on a $370 stock with nothing saying which check it failed. Each now carries a
written reason naming the ratio, and the sheet's banner says that a **blank** margin of
safety means refused-or-flagged, not expensive.

## C. NaN leaked past the refusal test — 520 companies

`_sheet_dcf` split its rows with `r.get("dcf_fair_value") is not None`. The rows come from
parquet, which turns every `None` into **NaN**, and `NaN is not None` — so all 1,501
companies were treated as "valued", the 520 refusals were sorted among them, and the sort
key was NaN for each. The sheet's own docstring promises refusals listed underneath with
their reason; that had not been happening. Now uses the existing `_finite` helper, the
same guard added to `xlsx_export` earlier the same day for the identical bug class.

### What A-C did

| | before | after |
|---|---:|---:|
| margin of safety present while fair value ≤ 0 **or** implausible | **125** | **0** |
| flagged implausible with no written reason | **125** | **0** |
| abs(margin of safety) > 500% | 117 | 35 |
| refusals mis-sorted as valued | 520 | 0 |

The surviving 35 are legitimate: within the plausible band a fair value of 0.1×–0.17× the
price gives a margin of safety of −5 to −9, which is the model saying *very overvalued*
and is exactly what it should say. RAMP (+49.2%), PCTY (+82.7%) and INTU (+75.3%) are
unchanged apart from a day of price movement.

**The refusals themselves were correct and stay**: 269 "FCF is not a valuation input"
(banks and insurers), 197 "trailing FCF zero or negative", 53 "no usable growth rate". A
DCF that produced a number for all 1,500 would be worth less than one that refuses 520 and
says why.

---

## D. The band hysteresis had an ordering bug worth 13 companies

`advance_band` checks E27's same-day no-op **before** the coverage-gate exemption sitting
directly beneath it — and that exemption's own comment says it *"has to be exempt to work
at all here"*. The no-op returns `current`, so it short-circuited the exemption entirely.

A company whose coverage crossed 0.80 on a day it was re-scored stayed
`INSUFFICIENT_DATA` until the next calendar day. **BMY** — coverage 0.894, score 72,
`band_raw` **INVESTABLE** — was displayed as unrankable, with OXY, GT, ESS, BURL, TXT,
EHC, CXW, UDR, KSS, LGIH, MAA and VICI.

**Fix.** The coverage-gate exemption runs first. Crossing the gate is a data-availability
change, not the score wobbling across a threshold, and it is symmetric in both directions
so it cannot bias the ranking upward. E27's property is intact: ordinary score wobble
still cannot advance a band twice in one day.

All 13 now band. **Companies at coverage ≥ 0.80 still showing INSUFFICIENT_DATA: 13 → 0.**

---

## E. Labels drifted from the framework, and one was wrong twice over

The framework went 100 → 94 at E26 and the text did not follow. `rubric.points_in()` now
derives every user-facing total, and `tests/test_label_drift.py` fails the build if a
literal returns.

The review caught *"Qualitative half — 50 of 100 points"*. Measuring found three more, and
the company page's **"Excluding Entry /95"** was wrong twice: ex-entry is the total minus
EN, and EN itself had dropped from 5 points to 2, so the correct figure is **92**.

---

## The measurement is confounded, and here is the honest split

The before/after straddles a calendar day — the crawl ran on 2026-08-26 — so E27's
hysteresis confirmed every pending transition at once. Reporting 100 band changes as this
work's effect would be false:

| band changes | 100 |
|---|---:|
| hysteresis confirming a pending transition (**the day rolling over**) | **85** |
| coverage-gate crossings this fix unblocked | **13** |
| score crossing a threshold on new prices | 2 |

`composite_strict` moved for **255** companies, and **none of it is attributable here**:
this work changes no score. The DCF is advisory and feeds nothing (E20), the labels are
text, and the band fix touches band state only. That movement is one day of market data.

`INSUFFICIENT_DATA` went **314 → 287**. Thirteen of those 27 are this fix; the rest is the
day rolling over.

Within-sector Spearman of `composite_strict` runs 0.940 (Communication Services) to 0.999
— also the day, not the change.

## What this does not establish

Nothing here tests whether any of it predicts anything. There is no forward-return grader;
it needs ~50 weekly snapshots and the `as_first_filed` view, and **5** exist. `promoted`
stays false. The framework is identical, so the snapshot series stays comparable.
