# E22 - the judgement half has never been tested. Two years of history, and what that can and cannot answer.

Pre-registered 2026-08-20, before any historical pack is built.

## Why this exists

`clab/research/panel.py` excludes the entire LLM half by construction - its docstring
says so in as many words. So E02, E05, E13 and E14 all tested **FE + BS + VA + EN only**.

**The 50 judgement points that make up half of `composite_strict` have never appeared in
any backtest.** Every "this ranking does not work" result on the Findings sheet is a
statement about the measured half. The judgement half is untested, which is a different
thing from disproven, and it is the half the whole LLM pipeline exists to produce.

## Scope, set by the user: the last two annual filings

Not ten years. Two scoring dates per company - the 10-K filed about two years ago and the
one filed about a year ago - plus the live cache as a third, present-day reading.

**What that buys, stated before the work rather than after:**

* A 2-year and a 1-year forward-return observation, from **two** cross-sections.
* Two cross-sections are not two independent samples. Every company in a given month
  shares the market's move, so the effective sample for a return test is closer to **n=2
  than n=1,000**. A Deflated Sharpe or PBO figure computed on this would be theatre, and
  this study will not compute one.
* E03 R3 already established that this score's information ratio is **far higher at three
  years than at one**. A two-year window therefore tests the horizon the project already
  knows is the weak one.

So the return test here is a **first look, explicitly underpowered**, and it is not the
primary output.

## The primary question two years CAN answer: is the judgement half stable?

A score that swings on a business that did not change is unusable whatever its returns
do - and unlike the return test, this needs no market data and has real statistical power,
because every company contributes an independent year-over-year pair.

| | measured |
|---|---|
| **R1 Stability** | Spearman of each judgement component's score at t-2 against t-1, across companies. Reported per component (SG, BQ, MG), never pooled. |
| **R2 Churn** | Share of companies whose BQ dimension count moves by more than 2, and whose SG total moves by more than 4 points, between consecutive annual filings. |
| **R3 Agreement** | Rank correlation between the judgement half and the measured half at the same date. Near 1.0 means the LLM is re-deriving the financials and adds nothing; near 0 means it is measuring something else, for better or worse. |
| **R4 Direction** | For the two dates that have forward returns, the IC of the judgement half and of the measured half, reported **per date, side by side, never pooled**, with the number of companies behind each. |

**Pass criteria are set for R1 and R3 only**, because those are the ones this design can
actually decide:

* **R1** - a component whose year-over-year Spearman is **below 0.5** is reported as
  unreliable, and its use in the composite becomes a live question for a follow-up
  registration. It does not get quietly dropped on this result alone.
* **R3** - if the judgement half correlates with the measured half above **0.8**, the LLM
  is largely restating the numbers and the 50 points are buying far less than they cost.

R2 and R4 are reported with no bar. Setting a bar on an underpowered return test is how a
project talks itself into a result.

## Method

* **Sample: 400 companies**, stratified across the eleven sectors and across measured-half
  score deciles, so the test is not run only on names the measured half already likes.
  Seeded and recorded.
* Three readings each: the 10-K current at t-2, the one at t-1, and the live cache.
  Roughly 800 historical packs to build and score.
* **Reuse, do not rewrite**: `panel.py`'s `as_first_filed` MetricBundle for the fact sheet
  at each date, `edgar_filings.filing_text` (extended to accept an accession rather than
  always taking the newest), `evidence.chunk_pool` / `build_pack`, and the production
  `sg` / `bq` / `mg` scorers.
* **Probe first.** Ten company-years timed end to end before any long run is launched -
  the estimate is ~70 s each (~20 s pack, ~50 s for three generations) plus an EDGAR fetch
  per historical filing, so 800 packs is roughly **16 hours**. If the probe says
  materially more, the sample shrinks rather than the run stretching.
* Checkpointed per company-year and resumable. This box has lost power three times this
  week.

## Prediction, stated before running

**R1: SG and MG come back reasonably stable (Spearman 0.6-0.8); BQ comes back the least
stable of the three**, because its dimension count is sensitive to which chunks retrieval
happens to surface, and E15-E18 showed how much that moves.

**R3: correlation with the measured half is LOW - under 0.4.** The LLM is reading
narrative sections, not the financial statements, so if this comes back high the packs are
leaking the fact sheet rather than the business description.

**R4: no detectable direction either way at one year**, consistent with E03 R3, and the
result should be read as "this design cannot see it" rather than "there is nothing there".

## What this cannot establish

It cannot establish that the judgement half predicts returns. Two cross-sections cannot
carry that claim, and the honest ceiling on this study is: *is the judgement half stable,
and is it saying anything the numbers do not already say?* `promoted` stays false either
way.
