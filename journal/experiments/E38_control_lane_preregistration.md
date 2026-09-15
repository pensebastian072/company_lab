# E38 — the qwen-structured control: is the leniency the model or the format?

Registered 2026-08-30, before any control payload exists. Follows E36 (`E36_results.md`)
and E37 (`E37_results.md`), and is item 1 of `docs/TOMORROW.md`.

## The hole this fills

E36 compared `qwen2.5:7b` (production) against `LFM2.5-2.6B-Finance` (the v2 lane) and
found the candidate's abstention gone. E36 named its own confound in writing: **every
production payload predates structured output** — unconstrained, 700 tokens — while the
candidate ran schema-constrained at 2,500. Two things changed at once.

E37 then showed the confound matters more than E36 assumed. Of the +8.9 mean score gain,
**+4.63 is abstention being filled and +4.34 is the candidate awarding more points on the
sub-tests both lanes answered** — a difference that survives common support and is
therefore not the schema making a missing key impossible. It is concentrated in one
question: `bq_moat`, 951 companies, mean **+2.55** of a 15-point sub-test.

Both of those numbers are currently attributed to nothing. The design has one cell
missing:

| | unconstrained, 700 tok | schema-constrained, 2,500 tok |
|---|---|---|
| **qwen2.5:7b** | v1 — production | **MISSING — this experiment** |
| **LFM2.5-2.6B-Finance** | never run | v2 — the lane |

Filling it splits the two effects apart:

* **(qwen-structured − qwen-v1) = the FORMAT effect.** Same model, same prompt, same
  filings; only the schema and the token budget change.
* **(LFM2.5 − qwen-structured) = the MODEL effect.** Same format, same budget; only the
  weights change.

Neither is a claim about which is *better*. There is still no forward-return grader
(hard rule 1), and `promoted` stays false.

## Design

* **Cache:** `D:\company_lab_data\qual_qwen_struct\`, its own `CLAB_QUAL_DIR`, so neither
  production nor the v2 lane is touched.
* **Knobs:** `CLAB_QUAL_MODEL=qwen2.5:7b`, `CLAB_QUAL_STRUCTURED=1`,
  `CLAB_QUAL_NUM_PREDICT=2500` — identical to the v2 lane in everything but the model.
* **Population:** the companies **both** existing lanes have already scored, so every
  comparison is three-way paired on the same filings.
* **Order:** stratified by 11 GICS sectors × 3 within-sector market-cap terciles and then
  shuffled under a recorded seed, drawn by `clab.research.e38_draw_control`. **Any prefix
  of the order is itself a stratified sample** — the E36 lesson, so a run the clock cuts
  off is a smaller sample and not a skewed one.
* **Minimum for reporting: 100 companies.** Below that the run is reported as incomplete
  and no criterion is called. The GPU is single-tenant and the v2 lane holds it until it
  finishes, so this starts after that and its size is whatever the clock allows.
* **No fold.** The comparison is payload-level, like E36's. Nothing is scored into a
  workbook, so there is no third scores.parquet to keep straight.

## Registered criteria and predictions

Written before a single control payload exists.

| # | criterion | prediction |
|---|---|---|
| **P1** | Null rate on E12's four watched moat dimensions for qwen-structured (v1 was 83.6 / 73.6 / 74.2 / 59.1%) | **Below 15% on all four.** Most of the abstention was the format: a required key cannot be omitted, and 2,500 tokens do not run out mid-object. |
| **P2** | `bq_moat` mean delta, qwen-structured minus qwen-v1, on companies both scored | **≥ +1.0 points** of 15. If the schema and the budget make *qwen* more generous too, leniency is a property of the format and not of LFM2.5. |
| **P3** | Mean common-support score delta, LFM2.5 minus qwen-structured | **Between 0 and +3**, i.e. strictly smaller than the +4.34 measured against v1. My belief is that most, not all, of the leniency is format. |
| **P4** | Degenerate-rationale rate for qwen-structured (v1 BQ: 22.7%, almost all the literal string `null`) | **Below 5%, but not zero.** The schema types `rationale` as a string, which makes `rationale: null` unrepresentable — but nothing stops a model writing the four characters `null` into a string field. |
| **P5** | Throughput, s/company, measured on the first 25 | **Slower than the v2 lane's 42.9 s/company** — qwen2.5:7b is 4.7 GB against 1.7 GB on a 6 GB card, and 2,500 tokens is more decoding than the 700 v1 paid for. Recorded so the next run is sized on arithmetic rather than optimism. |

## What each outcome means

* **P2 large and P3 near zero** — the whole E36 result is format. "LFM2.5 abstains less"
  becomes "structured output abstains less", the candidate model has shown nothing, and
  the cheap fix for production is a schema on the incumbent, not a new model.
* **P2 small and P3 near +4.34** — the leniency is the model. That is a real difference
  between the two, and it still does not say which is right, because a scorer that awards
  more points is only better if the points are earned, and nothing here measures that.
* **P1 still high** — the abstention was never the format; it is the retrieval pack, and
  E12/E29's tail is a different problem than either model.

## Out of scope

* Which lane predicts returns. No grader exists.
* Any promotion, any change to production scoring, any edit to the v1 cache.
* Re-opening E29's applicability map on a null rate.
