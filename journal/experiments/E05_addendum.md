# E05 addendum — what the holdout actually said

Written 2026-08-12, after `E05_results.md`. Three things need saying that the graded
pass/fail table does not carry on its own.

---

## 1. The most important number is not F1 or F3

The user's question has always been: should this be followed *instead of* holding the
index? The holdout answers it, and the answer is no.

| top decile, excess over SPY | 1 year | 3 years |
|---|---:|---:|
| mean | **+3.4%** | **+11.9%** |
| **median** | **−1.2%** | **−7.6%** |
| share of picks beating SPY | 48.4% | 45.3% |
| n | 5,938 | 4,497 |

**The typical top-decile pick loses to SPY at both horizons**, and fewer than half beat it.
The positive *average* is produced by a small number of very large winners. A mean without
its median would have read as a +11.9% edge; it is not one.

The bottom decile is worse behaved still: its mean 3-year excess is **+27.1%** — higher
than the top decile's — on a median of **−18.9%** and only 36.0% beating SPY. That is the
signature of a few violent recoveries (the CVNA pattern E02 already found) inside a mostly
bad group.

So the ranking is **not** monotonic at the extremes even though its rank correlation is
positive (IC +0.081 at 3y, positive in 92.3% of months). The middle of the ranking is
ordered roughly correctly; the tails are not. Any use of this framework that concentrates
on the top decile is relying on the part of the distribution that behaves worst.

This is now stated in `rubric.HORIZON_NOTE`, so the dashboard and the workbook carry it,
and on the workbook's Findings sheet.

## 2. F1 improved things and still failed, and the failure is the honest reading

Pre-registered criterion: within-sector IC above zero **and** the sector spread at least
halved.

| | absolute | sector-relative | required |
|---|---:|---:|---|
| within-sector IC 1y | 0.0170 | **0.0233** | > 0 ✓ |
| sector spread | 24.1 pts | **19.2 pts** | < 10.7 ✗ |
| score variance from sector | 0.173 | 0.121 | — |
| IC 3y | 0.0805 | 0.0774 | — |

It bound properly — 97.2% of rows scored on the sector-relative basis, FE moved on 78.6% of
rows — so this is a real measurement of the fix, not of a no-op. Sector-relative scoring cut
the spread by 20%, not the 50% required. **Sector remains the dominant axis of the score.**
Note also that IC at 3 years got slightly *worse* (0.0805 → 0.0774), so the fix is not
free.

The verdict held under all three sector definitions (`gics_only`, `sic_filled`,
`sic_for_everyone`), which is the useful robustness result: the conclusion is about the
framework, not about the SIC-to-GICS mapping — even though SIC and GICS agree on only 78.2%
of the 491 companies where both exist.

One discrepancy to record: the pre-registration fixed the baseline spread at **21.4 points**
from the biased panel, but the same statistic on the survivorship-free panel is **24.1
points**. The criterion was graded against the pre-registered 10.7 threshold as written.
Grading against half of the holdout's own baseline (12.05) does not change the outcome.

## 3. F3 shipped setting fails; the post-hoc sensitivity contains a pass

F3 at the shipped `BAND_CONFIRM_READINGS = 2`: change rate 21.8% → **12.8%** (needed
< 12%), median months in a band 3 → **5** (needed > 4) ✓, ΔIC 1y **+0.0036** (needed
|Δ| < 0.005) ✓. **Two of three: FAIL.**

Post-hoc sensitivity — **explicitly not pre-registered**, recorded so the choice is
visible rather than tuned in silence:

| confirm | change rate | median months | band IC 1y | ΔIC vs raw | smoothed band was more flattering before a >30% fall |
|---:|---:|---:|---:|---:|---:|
| 1 (raw) | 21.8% | 3.0 | 0.0448 | — | 0.0% |
| **2 (shipped)** | **12.8%** | **5.0** | 0.0484 | +0.0036 | 7.8% |
| 3 | 9.3% | 7.0 | 0.0504 | +0.0056 | 12.8% |
| 4 | 5.9% | 11.0 | 0.0469 | +0.0022 | 15.3% |

~~**No value of `confirm` satisfies all three criteria at once.**~~ `confirm=2` misses the
change-rate bar by 0.8pp; `confirm=3` clears it but then breaches the IC-stability bar
(+0.0056 > 0.005) and nearly doubles the delay harm. The two criteria pull against each
other, which is a defect in the pre-registration rather than in the fix.

**Correction — 2026-09-07:** that sentence is false. The table's post-hoc `confirm=4`
row satisfies all three thresholds: 5.9% change rate (<12%), 11.0 median months (>4),
and +0.0022 ΔIC (absolute value <0.005). This does not turn the registered `confirm=2`
test into a pass and does not authorise selecting `confirm=4` after seeing the result.
The shipped setting and decision remain unchanged.

Two things worth being precise about:

- The ΔIC is **positive** — smoothing slightly *improves* ranking power. The criterion
  existed to detect smoothing doing something other than removing noise, and it is doing
  something else: lagging the label adds a little signal. That is still a criterion breach
  as written, and it is not reinterpreted here into a pass.
- The cost is real and rises with `confirm`: at `confirm=2`, on 3,977 observations that
  went on to lose ≥30% over the next year, the smoothed band was still the more flattering
  one **7.8%** of the time. At `confirm=3` that becomes 12.8%.

**Decision taken:** `confirm=2` is wired into the live scorer anyway, on the grounds it was
built for — usability. Raw bands changed for **79 of 500 companies in two days** on live
data, and a label that unstable cannot be held through a multi-year thesis. But it is
recorded as a **FAIL against its own criteria**, not as a pass, and `band_raw` is stored
beside the shown band on every scorecard so any smoothed label can be traced to the number
that produced it. Choosing `confirm=3` because it clears the churn bar, after seeing that
it does, would be exactly the sign-flipping-a-discovered-effect problem this journal exists
to prevent. If a different `confirm` is wanted, it needs a fresh pre-registration with
a selection rule fixed before its results are observed.

## 4. What was fixed to make this measurable at all

Both of these would have produced a plausible, publishable, wrong number.

- **F4 was never implemented.** `DEFAULT_HORIZON` / `HORIZON_LABEL` / `HORIZON_NOTE` were
  declared in the rubric and referenced by nothing. The fix whose criterion is "implemented
  without altering a score" had not been implemented.
- **F1 never ran on the first crawl.** `fe_sector_scored` was computed and never copied
  onto the panel row, so every sector distribution filtered to zero peers, the "too few
  peers → absolute basis" fallback swallowed all 67,889 rows, and the run printed
  `fe_basis: {'absolute': 67889}` and exited 0. F1 would have been recorded as having no
  effect when it had simply not executed. Both entry points now raise rather than fall back
  silently.
- **The sector variable was missing for exactly the companies the survivorship fix added**
  — 182 of 675, 15.9% of rows, all in one pseudo-sector mixing utilities with software.
  Filled from SIC out of the already-cached submissions.

Nothing is promoted. `promoted` stays false.
