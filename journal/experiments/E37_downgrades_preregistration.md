# E37 — the 46 downgrades, and what the comparison looks like on common support

Registered 2026-08-30, **before any of the numbers below were computed.** Follows E36
(`journal/experiments/E36_v2_lane_preregistration.md`, results in `E36_results.md`) and
is item 2 of `docs/TOMORROW.md`.

## Why

E36 measured the candidate lane against production and found the workbook reads better
almost everywhere: mean score **+8.9** over 1,045 comparable companies, 972 up, **46
down**, band-gate clearance 829 → 996. E36 already says out loud that this is largely an
**artefact of format**: the candidate ran schema-constrained, so it cannot abstain, and a
sub-test that stops abstaining enters the scoring denominator. A company can therefore
gain score without a single judgement changing.

The 46 downgrades are the part that arithmetic does not obviously explain, and two of them
reportedly *lost* coverage — which should be impossible for a lane that never abstains.

**This experiment does not ask which model is better.** There is no forward-return grader
in this repo (hard rule 1), and E36's confound is not repaired by looking harder at the
same data. It asks a narrower, answerable question:

> When the two lanes are restricted to the sub-tests **both of them actually scored**, how
> much of the movement survives — for the 46 downgrades, and for the whole comparable set?

## Population and freeze

* v1 = production `C:\Users\<your-user>\company_lab\data\scores.parquet` + `data\scorecards\`.
* v2 = the lane worktree `D:\company_lab_v2\...`, **snapshotted to scratch at registration
  time**. The fold loop is running, so the live v2 parquet grows while this runs; the
  snapshot is what gets analysed and its row count is reported.
* Comparable set = tickers present in both. n is reported, not assumed to be 1,045.

## Method

For every comparable company, decompose Δ`score` into three parts:

1. **Measured half** — Δ earned and Δ available over FE, BS, VA, ER, EN. Both lanes read
   the same EDGAR/yfinance cache, so this **should be zero**. Anything non-zero is data
   vintage, and it contaminates E36's headline as well as this one.
2. **Judged half, per sub-test transition** — for each SG/BQ/MG sub-test:
   `NULL→SCORED` (abstention filled), `SCORED→NULL` (new abstention), `SCORED→SCORED`
   with Δearned ≠ 0 (**disagreement — the residue**), `NULL→NULL`, and status changes that
   are neither (`not_applicable`, `data_quality_fail`).
3. **Common support** — recompute each lane's score using **only the sub-tests scored in
   both lanes**, same rubric arithmetic (earned / available, normalised the same way).
   This is the format-free comparison: no sub-test can enter one lane's denominator and
   not the other's.

## Registered criteria and predictions

| # | criterion | prediction |
|---|---|---|
| **C1** | Of the 46, how many keep a drop of ≥ 3 points on common support? | **Fewer than half (< 23).** Most downgrades are the denominator: the candidate answered a previously-abstained sub-test *low*, which drags the percentage down exactly as answering high lifts it. |
| **C2** | How many comparable companies show **any** measured-half movement? | **> 0, and I expect it to be small (< 5%).** The two lanes folded on different days against a shared cache; if this is large, E36's +8.9 is partly not the model at all and must be re-stated. |
| **C3** | `SCORED→NULL` transitions across all comparable companies | **> 0 but rare (< 1% of scored sub-tests).** A schema-constrained lane should not abstain; the two coverage-losing companies say it happens anyway. If it is zero, the coverage loss came from the measured half and C2 is the real story. |
| **C4** | Is the `SCORED→SCORED` disagreement concentrated in particular sub-test keys? | **Yes — concentrated in the narrative SG/BQ keys** (`sg_tam_expanding`, `bq_moat_*`), not spread evenly. |
| **C5** | Mean Δscore over the whole comparable set **on common support** | **Within ±2 points of zero.** This is the number E36's +8.9 becomes once format is removed, and it is the point of the whole exercise. |

## What each outcome would mean

* **C1 low + C5 near zero** — the v2 book's improvement is coverage, full stop, and the 46
  downgrades are the same arithmetic running the other way. Nothing about model quality is
  established either direction, and the qwen-structured control (item 1) remains the only
  thing that could settle it.
* **C1 high** — the downgrades survive format. That is a real disagreement between the two
  judged halves, and it localises where a control run should look first. It still is not
  evidence that either lane is *right*: without a grader, "which one is correct" is
  unanswerable here.
* **C2 large** — E36's headline is partly data vintage and both its numbers get an
  erratum. This is the outcome that would cost the most to be wrong about, which is why it
  is registered rather than assumed away.

## Out of scope, deliberately

* Any claim that one lane predicts returns better. There is no grader (hard rule 1).
* Any promotion. `promoted` stays false.
* Re-opening the abstention tail (E29 refused it in writing).

---

## Amendment 1 — the denominator I predicted does not exist (before any result was read)

Filed 2026-08-30, **after reading `clab/scoring/composite.py` and `clab/scoring/types.py`,
before computing a single number.**

C1's prediction was reasoned from a denominator effect: "the candidate answered a
previously-abstained sub-test *low*, which drags the percentage down". **That mechanism
cannot occur in this repo.** `score` is `selection_score`:

```
score = round(100 * (points_earned - EN_earned) / (TOTAL_POINTS - EN_max))   # /92, FIXED
```

The denominator is a constant. `NO_DATA` contributes nothing to the numerator and nothing
to the denominator (`earned_points` sums `SCORED` only). So filling an abstention with any
score ≥ 0 **can only raise or hold `score`; it can never lower it.**

Therefore every one of the 46 downgrades must be a genuine loss of earned points, from one
of exactly three places:

1. a sub-test **scored in both lanes**, lower in v2 — real judgement disagreement;
2. a sub-test `SCORED → NULL` — the candidate abstaining where the incumbent did not,
   which the schema was supposed to make impossible;
3. the **measured half** moving between the two folds — not the model at all.

**The original C1 prediction is left on the record as written and is already falsified as
reasoning.** It was wrong about the arithmetic, not about the data, and that is the more
embarrassing of the two.

**Revised C1** — of the 46, how many keep a drop of ≥ 3 points on common support:
**most of them, > 30.** With the denominator gone as an explanation, common support
subtracts only the abstention-filling, which by the argument above contributes nothing
negative. The residual question becomes *how the drop splits across the three sources
above*, and (2) and (3) are the ones that would be defects rather than disagreements.

**C5 is unchanged and now matters more.** The +8.9 cannot be a denominator artefact
either: it is real earned points, gained because the candidate scores where the incumbent
abstained. "Coverage explains it" is still true in the sense that *the abstention filling*
explains it — but the points are genuinely added to the numerator, and the common-support
mean is what says whether the two lanes agree where they both spoke. Prediction stays:
**within ±2 of zero.**
