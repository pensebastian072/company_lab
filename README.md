# company_lab

A ranking system for the S&P 500 built on **business quality, structural growth,
management, balance sheet, valuation, expectations and entry price** — 94 points,
one scorecard per company, re-scored as new filings land.

Not a trading system. It ranks companies to read, on a horizon of years.

```
python -m clab.runner.probe --n 10       # time it before you run it
python -m clab.runner.batch --tier sp500 --skip-qual
python -m clab.ui.app                    # http://127.0.0.1:8100
```

## What it scores

| | Component | Points | Where the number comes from |
|---|---|---:|---|
| SG | Structural Growth | 20 | LLM over 10-K business/risk/MD&A + the quant fact sheet |
| BQ | Business Quality & Moat | 15 | LLM across 11 moat dimensions |
| FE | Financial Engine | 18 | EDGAR: growth, margins, ROIC/ROE, margin expansion |
| MG | Management & Capital Allocation | 9 | **fully measured**: guidance hit-rate, downturn survival, capex/R&D/buybacks/M&A |
| BS | Balance Sheet & Survivability | 10 | EDGAR + a downturn stress test |
| VA | Valuation | 15 | multiples vs own history and peers, PEG, reverse DCF |
| ER | Expectations vs Reality | 5 | surprise history, estimate revisions |
| EN | Entry Opportunity | 2 | EMAs, drawdown, support, valuation trough |

Most of the framework is **measured** (FE + MG + BS + VA + ER + EN = 59 points,
every one traceable to a filed XBRL tag or a market quote) and the rest is
**judgement** (SG + BQ = 35 points, scored by a local LLM). The dashboard shows
both numbers side by side and marks every LLM-sourced point, because they are not
the same kind of number.

## What the experiments actually found

This is the part worth reading. The system is complete on all 500 companies, and
a series of pre-registered studies has been run against it. Most came back
negative, and the negatives are the reason the repo is interesting.

**On the ranking itself:**

- **Three pre-registered studies say the entry rule does not work.** It has never
  been validated out of sample, and every flag file says `promoted: false`.
- **The score is substantially a sector bet.** Once that was measured, the
  cross-sector headline was replaced with a sector-neutral score.
- **It works at a 3-year horizon, not a 1-year one** — a finding about the
  horizon, not a result to trade on.
- An applicability map was proposed, measured, and **refused as empty**. It is
  recorded as refused rather than quietly dropped.

**On the measured half — the part everyone assumes is fine:**

A per-sector audit found **four data bugs in the measured half**, all silent:

- one balance-sheet dilution component was dead in **all eleven sectors**;
- revenue was a *fragment* of the true figure for roughly 1 company in 22 — one
  health insurer was ranked on $6.18bn of a true $137.2bn;
- plus two smaller tag-selection faults.

Fixing all four moved the sector medians by about **one point**. That is the
useful result: the cross-sector gap was neither the rubric nor the data. Every
real defect found in this project was in the measured half and silent, which is
why a range / null-rate / unit sweep over every field now runs before any score
is interpreted.

**On the LLM half:**

- Swapping the judgement model produced a **different book**, not a better one —
  only 37% of bands agreed, and 29 of the top 50 survived the swap.
- A controlled A/B settled that the difference was **~92% the model and ~9% the
  output format**, refuting all five registered predictions that said otherwise.
- The newer model **cited text that is not in the filing 9.7% of the time**,
  against 0.5% for the incumbent. A more *willing* scorer, not a proven better
  one. A citation gate costs coverage to fix.
- A parse bug in our own JSON extraction had been killing components and
  inflating a "broken" list. It was found and fixed — and the "different book"
  verdict survived the re-run anyway.

## What it will not do

- Claim it predicts returns. It has never been tested against forward returns.
- Score a gap as a zero. Missing data is `—`, and a company scored on less than
  80% of the applicable framework gets no band at all.
- Round a model's opinion into false precision. Sub-test scores are integers, and
  an out-of-range LLM score is rejected rather than clamped.
- Talk to a broker.

## Outputs

- `http://127.0.0.1:8100` — sortable, filterable, searchable table of the whole
  index; tap a row for the breakdown, or open `/c/<TICKER>` for the full
  scorecard with every sub-test, threshold and source tag.
- `data/exports/scores_<date>.csv` — one flat row per company.
- `data/exports/company_lab_<date>.xlsx` — 7 sheets: Rank, Components, Subtests
  (the full audit trail), Thesis, Valuation, Stress, Meta.

## Data

SEC EDGAR XBRL `companyfacts` (free, keyless, authoritative) and yfinance. Both
are cached to disk and replayed free; a same-day re-run costs no network.

**The generated result sets are not in this repository.** The experiment
`.parquet` panels are large and regenerable — the code, the experiment writeups
and the analysis JSON are all here, so the results above can be reproduced from a
clean run. Judgement scores additionally require a local Ollama model.

## Scope

Research only. It ranks companies for reading. It is not investment advice, it
emits no signals, and it is wired to nothing that acts. See
[`DISCLAIMER.md`](DISCLAIMER.md).

MIT licensed.
