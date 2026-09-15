
# E05 — the four fixes from E03 (pre-registration)

Written 2026-08-11 before any of them was implemented. Each has a stated mechanism, a
stated pass criterion, and a stated way it could make things worse.

These will be tested on the **survivorship-free panel** (E04, 708 of the 716 companies
ever in the index since 2016), not on the panel that motivated them. That is the first
genuine holdout this project has had.

---

## F1 — Sector-relative scoring for margin and returns metrics

**Why.** E03 R1: pooled IC +0.013, within-sector IC −0.013. 95.6% of the ranking power
is sector selection, and 18.1% of score variance is sector alone. Mean score runs
Financials 62.6% down to Utilities 41.2%, because `rubric.py` bands an operating margin
of 25% as full marks — a threshold built for software and meaningless for a utility.

**Change.** For `fe_gross_margin`, `fe_operating_margin`, `fe_fcf_margin`, `fe_roic` and
`fe_roe`, score the metric's **percentile within its GICS sector at that date** instead
of against absolute bands. Absolute bands stay as the fallback when a sector has fewer
than 8 scored peers.

**Passes if** within-sector IC rises above zero AND the sector spread in mean score
(currently 21.4 points between the highest and lowest sector) at least halves.

**How it could make things worse.** It rewards the best utility as highly as the best
software company, so a portfolio built on it will hold more capital-intensive, low-growth
businesses. If absolute quality is what compounds, this is a downgrade. Reported either
way — the sector spread and the IC are both stated.

## F2 — Mid-cycle earnings for cyclical filers

**Why.** E03 R5 across 4,518 observations: cyclical IC is −0.059 at 1y and −0.038 at 3y
against +0.016 and +0.065 elsewhere, and the top score quintile underperformed the bottom
by 65.6 points over three years. TTM earnings peak exactly as the cycle turns, so the
score is highest at the top and lowest at the trough.

**Change.** For SIC groups 3600-3699, 3570-3579, 1300-1399, 2911, 3300-3399 and 3711,
compute the FE margin and growth inputs from a **7-year median** operating margin and a
7-year revenue CAGR rather than TTM. A new `CYCLICAL` sector profile carries the flag so
the scorecard states which basis was used.

**Passes if** cyclical IC at 3y turns positive AND the top-minus-bottom quintile spread
inside cyclicals stops being negative.

**How it could make things worse.** A structurally growing semiconductor company is
penalised for its own past: seven-year-median margins understate a business that has
genuinely re-rated. Watch NVDA and AVGO specifically — if their scores fall materially
while their fundamentals were genuinely improving, the fix is over-smoothing.

## F3 — Band hysteresis

**Why.** E03 R4: bands change in 27.2% of months and the median time in a band is 2
months. A label that flips every two months cannot be held through, and it means the
dashboard's answer depends on the week you look.

**Change.** A band only changes after **two consecutive** readings agree on the new
band. Degradation is NOT exempt — this is a usability rule, not a risk rule, and an
asymmetric version would quietly bias the ranking downward. Implemented on the stored
scorecard history, with the raw (unsmoothed) band retained beside it.

**Passes if** the band change rate falls below 12% per month AND the median months in a
band rises above 4, with no material change in IC (|delta| < 0.005). A change in IC would
mean the smoothing is doing something other than removing noise.

**How it could make things worse.** It delays a genuine deterioration by one month.
Quantified: the share of >30% drawdowns where the smoothed band was still the old one at
the last reading before the fall.

## F4 — Default the UI and expectations to 3 years

**Why.** E03 R3: IC is +0.013 at one year and +0.063 at three, positive in 84.5% of
months. The framework is built for multi-year compounding and every earlier test judged
it on one year.

**Change.** Presentation only — no scoring change. The dashboard and the workbook lead
with 3-year figures, and any future validation defaults to the 3-year horizon.

**Passes if** implemented without altering a single score. There is nothing to measure;
it is a correction to how the output is read.

---

## Order and independence

F1 and F2 both touch FE, so they are implemented and measured **separately**, in that
order, each against the survivorship-free panel, before any combined run. A combined
result that improved would otherwise be unattributable.

## Reporting rules

Unchanged: per-year before pooled, medians beside means, n everywhere, no claim on
n < 30, survivorship status stated, negative results reported as plainly as positive
ones. Nothing is promoted; `promoted` stays false regardless of outcome.

## Outputs

`journal/experiments/E05_results.json` / `.md`, one section per fix.
