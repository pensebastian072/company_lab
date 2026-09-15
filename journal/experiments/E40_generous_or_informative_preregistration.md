# E40 — generous, or informative? What can be told apart WITHOUT a grader

Registered 2026-08-30, before any of it was computed. Follows E38, which established that
the candidate's lower abstention and higher scores are **the model** (format 13%, model
92% on `bq_moat`) rather than the schema.

## The question the user asked, stated honestly

> "compare both and see what we learn from both, or just v2 with the model is just better
> no matter what"

**"Better" cannot be established here.** Better means the score predicts something, and
this repo has no forward-return grader — hard rule 1, and the reason `promoted` has never
been true. E38 measured that LFM2.5 answers more questions and awards more points. Both of
those are equally consistent with *seeing more in the filing* and with *being less willing
to say "the filing does not support this"*.

What CAN be told apart without ground truth is whether the extra answers **carry
information**. Three properties do that, and all three are computable from payloads
already on disk, with no GPU:

1. **Discrimination.** A dimension where nearly every company gets the same number is a
   weight with no information in it — E30's finding about the measured half, and the
   market-state workbook's 6-of-12-constant-layers failure. If the candidate answers
   everything by handing out the same score, its coverage is decoration.
2. **The fills specifically.** The dimensions the incumbent abstained on and the candidate
   answered are the ones in question. If those cluster on a single value while the
   both-answered ones spread, the fill is a default, not a judgement.
3. **Evidence that verifies.** SG carries a per-sub-test quote and the parser checks
   containment against the pack (`evidence_unverified`). A model that answers more by
   citing text that is not in the filing is fabricating, and that is measurable.

## Registered predictions

| # | criterion | prediction |
|---|---|---|
| **D1** | Modal share per BQ dimension (share of companies on the most common score), candidate vs incumbent, same companies | **Candidate HIGHER by ≥ 10pp on most dimensions.** Answering everything usually means answering it the same way. |
| **D2** | Score dispersion (stdev) per BQ dimension | **Candidate LOWER.** Same reasoning as D1, on the other statistic. |
| **D3** | Distribution of the **fill** dimensions (incumbent null → candidate scored) vs dimensions both scored | **Fills are more concentrated** — modal share at least 15pp higher than the both-scored ones. This is the sharpest test of whether coverage bought anything. |
| **D4** | SG `evidence_unverified` rate, candidate vs incumbent | **Candidate HIGHER.** It answers where the pack is thin, so its quotes should verify less often. |
| **D5** | Does either lane's judged half separate companies at all? Spearman(judged score, measured /50) per lane | **Both weakly positive and similar (0.1–0.4), with no meaningful gap.** The halves measure different things; a large gap either way would be the surprise. |

## What each outcome licenses

* **D1/D2/D3 confirmed** — the candidate's extra coverage is largely a constant, the v2
  book's +8.74 is partly a uniform lift, and "better" is not supported. The honest use of
  the v2 lane is then as a *coverage* fix whose scores need a grader before anyone ranks
  on them.
* **D1/D2/D3 refused** — the candidate answers more AND spreads its answers, which is the
  first positive thing anyone could say about it here. Still not "better", but it would
  make a grader worth building rather than optional.
* **D4 high** — a fabrication rate, and it would be disqualifying on its own.

## Out of scope

Any claim that either lane predicts returns. Any promotion. `promoted` stays false.
