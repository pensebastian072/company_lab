# E02 — what does the measured half catch, what does it miss, and when? (pre-registration)

Written **2026-08-10, before the panel engine existed and before any result was
computed.** Unedited once run; interpretation goes in an addendum.

## The programme

Build a **point-in-time score panel** — the measured half of the framework recomputed
monthly for the S&P 500 over ~10 years using only information published at that date —
and use it to answer a fixed list of questions about what the scoring does and does
not detect.

## What is in the historical score, and what cannot be

| Component | Points | In the panel? | Why |
|---|---:|---|---|
| FE Financial Engine | 15 | **yes** | EDGAR, `as_first_filed` view |
| BS Balance Sheet | 10 | **yes** | EDGAR, `as_first_filed` |
| VA Valuation | 15 | **partly** | own-history P/E and peer medians reconstructible; reverse DCF needs a historical beta and risk-free, so it is dropped and VA is scored out of its available points |
| EN Entry | 5 | **yes** | price and filed EPS only |
| ER Expectations | 5 | **no** | needs historical consensus estimates; yfinance serves only current. Excluded, not approximated |
| SG / BQ / MG | 50 | **no** | the LLM read current filings and its training data postdates the window. Any historical use is circular |

So the panel score is **`measured45` = FE + BS + VA + EN**, reported as a percentage
of the points actually available at that date. Every result is a statement about that
45-point subset, never about the 100-point framework.

## Point-in-time discipline (the whole basis of the study)

- Fundamentals use `normalize.dedupe(view="as_first_filed")` — the value as first
  reported, never a later restatement.
- A quarter enters the panel only from its **filing date**. Fundamentals change only
  on filing dates, so metrics are computed at each filing date and held forward.
- P/E percentile ranks against the trailing 5 years **up to t**, expanding window.
- Weekly and monthly EMAs use completed bars only.
- Peer medians at t are computed across companies **that had a score at t**, never
  across the final universe.
- Universe: the 500 names currently in the index. Delisted and removed constituents
  are absent — a survivorship bias that is stated everywhere and cannot be fixed
  without the `D:\ohlcv_1m` archive.

## Pre-registered questions and pass criteria

**Q1 — Does the measured score rank forward returns at all?**
Sort into deciles by `measured45` each month; measure mean and median forward 1y/3y
return per decile, and Spearman IC per month.
*Passes* if mean IC > 0 with the top decile beating the bottom in **at least 6 of 9**
years. I expect this to fail or be weak: value-ish measured factors underperformed
over 2016-2025.

**Q2 — Detection timing on the realised winners.** THE question.
Take the 25 largest realised 3-year returns in the window. For each, plot
`measured45` in the 24 months before the move began, and record:
- the score 12 months before the move,
- the highest score reached before the move,
- whether it ever crossed 70% of available points before the move,
- and when the score peaked relative to the move.
*Reported, not pass/fail* — the deliverable is a table showing, per winner, whether the
framework was flagging it early, late, or never.

**Q3 — What did it flag that went badly?**
Names scoring in the top decile whose forward 1y return was worse than −20%. Grouped
by which component carried their score, to see whether one component is systematically
misleading.

**Q4 — Which component carries any signal there is?**
Per-component Spearman IC against forward 1y return, so credit or blame is attributed
rather than pooled.

**Q5 — Do the framework's own bands order returns?**
Mean forward return by band. *Passes* if the ordering is monotone in the expected
direction across the top four bands.

**Q6 — Does the score detect deterioration before price?**
For names whose price fell >30% in a year, was `measured45` already falling in the
preceding 6 months? Reported as the share where the score led the drawdown.

## Reporting rules

- Per-year tables before any pooled number.
- n stated everywhere; no claim on n < 30.
- Median beside every mean — a few 10x recoveries dominate means in this window.
- Trades whose window straddles an implausible price print are dropped (E01 defect).
- A negative or null result is the expected outcome for Q1 and Q5 and will be
  reported as plainly as a positive one.
- **Nothing here promotes anything.** No gate is cleared, no flag file is written,
  `promoted` stays false.

## Outputs

- `journal/experiments/E02_panel.parquet` — the point-in-time score panel itself,
  reusable for every later question
- `journal/experiments/E02_results.json` / `.md`
