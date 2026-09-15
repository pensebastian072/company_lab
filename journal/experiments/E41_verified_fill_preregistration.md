# E41 — the verified-fill hybrid: how much coverage survives a citation check?

Registered 2026-08-30, before computing any of it. Follows E40.

## Why

E40 leaves a specific proposal on the table rather than a verdict. Production abstains
honestly and cites accurately (SG evidence failing containment **0.6%**) but leaves a
third of the book unbanded. The candidate fills those gaps with genuinely varied
judgements — D3 refused my prediction that they would be a default — but **9.9% of its SG
citations fail containment, 13% on the fills specifically**, against qwen's 0.6%.

The obvious move is not a model swap. It is: **keep production's judged half, and accept a
candidate answer only where the candidate's own quote verifies against the filing.**

This experiment measures what that would buy, in coverage and in bands, **without
rebuilding anything.**

## Method, and its hard limit

Arithmetic over payloads plus production's scorecards — no fold, no fourth workbook, no
GPU. For each company: take production's judged sub-tests, add the candidate's **only**
where production abstained **and** `evidence_unverified` is false, then recompute
available points and coverage against the same denominators the rubric uses.

**The limit, stated up front: this can only be done for SG.** `parse_sg` verifies a quote
**per sub-test**; `parse_bq` and `parse_mg` read evidence **once at the top level**, so
there is no per-dimension citation to check on the component where most of the abstention
actually lives (BQ null 38.6%). Extending the gate to BQ needs a schema with per-dimension
evidence and a full re-run — a GPU job, not an analysis. **So E41 measures a floor, not
the ceiling**, and the headline must say so.

## Registered predictions

| # | criterion | prediction |
|---|---|---|
| **H1** | Share of candidate SG fills whose evidence verifies | **~87%**, straight from E40's 13% unverified on fills. Recorded so the arithmetic is checked against the thing it came from. |
| **H2** | Companies clearing the 0.80 band gate: v1 → hybrid → full v2 | **1,184 → ~1,250 → 1,410.** SG is 20 of 94 points and BQ is the bigger abstention block, so a SG-only gate cannot buy most of the v2 lift. |
| **H3** | Mean judged-half available points added per company by verified SG fills | **+2 to +4 of 20.** |
| **H4** | How much of the *rejected* fill volume is concentrated in a few sub-tests | **Yes — over half in two sub-tests.** If the unverifiable answers cluster, they can be excluded by rule rather than per-quote. |

## What each outcome licenses

* **H2 near 1,250** — the honest conclusion is that a citation-gated hybrid fixes a small
  part of the coverage problem, and the real prize needs per-dimension evidence on BQ.
  That becomes the next GPU job with a known cost, rather than a vague "re-run it".
* **H2 near 1,410** — SG was carrying more of the coverage gap than assumed, and the
  hybrid is most of the v2 book without the fabrication risk.
* **H1 far from 87%** — the two measurements disagree and one of them is wrong; find out
  which before anything is built on either.

## Out of scope

Any claim that the hybrid predicts returns. It cannot; there is still no grader.
`promoted` stays false. Nothing is rescored and no production artifact is touched.
