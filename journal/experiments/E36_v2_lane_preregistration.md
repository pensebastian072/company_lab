# E36 — the v2 lane: what changes when only the model changes

Registered **2026-08-29 10:40**, with the 400-company run already in flight (it started
10:36) and the 10-company probe already read.

## What is honestly "pre" here, and what is not

This registration is **not** clean and saying otherwise would be the exact self-flattery
the file exists to prevent.

**Already seen before this was written** — the probe, n=10 (AAPL, JPM, XOM, JNJ, PG, HD,
NEE, LIN, UNP, CAT):

* 0 parse failures, 0 failed generations, median **25 s/company**;
* **0.0% abstention across all 55 BQ dimensions**, against the incumbent's 78.3% mean null
  on E12's four watched dimensions;
* 0.0% unverified evidence on SG;
* **5 of AAPL's 11 BQ rationales were the evidence pack's page header**
  (`Apple Inc. | 2025 Form 10-K | 2`) carrying a confident score of 4 — and **zero** such
  rationales in the other four companies inspected.

**Genuinely pre-registered**: everything below, fixed before any of the 400 was read. The
probe's ten are *excluded* from the analysis sample for that reason.

## The sample

`E36_sample.json`, drawn by `clab/research/e36_draw_sample.py` at seed **36** before the
run: **400 companies** from an eligible pool of 1,471, stratified across 11 GICS sectors ×
3 within-sector market-cap terciles, allocated proportionally, then **shuffled**, so that
any prefix of the run order is itself a balanced sample. The run will be stopped by the
clock, not by a criterion, and this is what stops the stopping point from being a
selection.

Eligibility: carries a v1 judged half to compare against, has a sector and a market cap,
and is findable in a universe file. That last filter is not pedantry — EQR sits in
`scores.parquet` and in no universe file, and the scorer refuses it.

## The question

E12 P1 asked whether a quarter of the universe sits under the BQ floor because of the
**rubric** or because of the **model**. The incumbent abstains on 78.3% of the four
watched moat dimensions. If a different model scores them, the rubric is exonerated.

**The trap this experiment exists to avoid:** "it abstained less" is only good news if the
scores it produced instead are *justified*. A model that answers everything by quoting the
page header has not solved the abstention problem, it has hidden it — and it would raise
coverage, push companies over the 0.80 band gate, and read as an improvement on every
summary statistic in the workbook.

## Criteria, fixed now

**C1 — abstention.** Per-dimension null rate, v2 vs v1, on the same 400. Reported per
dimension, never pooled: the whole E12 finding is that abstention is *structured*.

**C2 — citation quality, the deciding one.** A rationale is **degenerate** if it matches
the evidence pack's header form (`<name> | <form> | <page>`) or is under 45 characters.
Measured for BOTH lanes on the same companies.

* If v2's degenerate rate is **at or below** v1's, the abstention drop is real and E12 P1
  is answered: the model was the bottleneck.
* If v2's degenerate rate is **materially above** v1's, the abstention drop is an
  artefact, and the correct conclusion is that qwen's abstention was *honest* — the
  filings do not discuss those moats.

**C3 — verified evidence is NOT sufficient and will not be treated as such.** The
containment check passes any verbatim string from the pack, and a page header is verbatim.
**A 0.0% unverified rate is therefore not evidence of honesty in this experiment**, and
will be reported only alongside C2.

**C4 — coverage and banding.** How many of the 400 cross the 0.80 coverage gate that did
not before, and how many change band. Stated as an exposure, not a win.

## The prior, stated before the 400 are read

Carried from the E07 amendment and updated by the probe:

1. **Abstention will stay near 0%** across the sample. High confidence — it was 0/55.
2. **The degenerate-citation rate will be materially higher in v2 than v1.** This is the
   prediction that matters, and the probe's AAPL is one instance of it against four
   counter-instances, so it is genuinely uncertain. If I am wrong here, LFM2.5 is a better
   judge than a model three times its size and the abstention was the rubric's fault.
3. **Coverage will rise and companies will cross the band gate.** Mechanical, given (1).
   This is the outcome that would look like an improvement in the workbook while being
   the symptom of a problem, and it is why C2 outranks C4.

## What this cannot establish

Nothing here validates either model against forward returns; there is still no grader.
"Better" is not measurable in this repo today. E36 can only say which model abstains less
and whether it earned it.

`promoted` stays **false**. The v2 workbook is a measurement of how much of the judged
half is the model, not a second opinion to act on.
