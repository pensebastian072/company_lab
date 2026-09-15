# E15 - can BQ abstention be bought back with retrieval instead of a rubric change?

Pre-registered 2026-08-18, **before any retrieval, prompt or rubric code is changed**.
E12 asks whether the BQ denominator is wrong. E15 asks the question that must be answered
first, because E12's own H2 says a denominator fix would otherwise "launder a retrieval
failure into a scoring rule".

## The mechanism this tests

BQ asks for **11 moat dimensions**. The pack it gets is **8 chunks of 1,600 chars**
retrieved by **one embedding query for the whole component**. Measured on the incumbent
cache 2026-08-18 (1,498 companies, `E12_abstention_2026-08-18.json`):

* retrieval is working: `embedding` method for 1,489 of 1,498, median 109 chunks
  embedded, `business` / `mdna` / `risk_factors` all found;
* and the packs of the abstainers are **indistinguishable** from the packs of the
  companies that answer - same sections, same chunk counts, same method
  (under floor: 110 median chunks; at or above floor: 108).

So the pack pipeline is not broken. What is untested is whether **eight chunks chosen by
one query can carry eleven questions**. `network_effects` is 83.5% null overall,
`data_advantages` 73.9%, `manufacturing_complexity` 73.1%, `economies_of_scale` 61.4%,
while `customer_relationships` is 7.5% null off the same eight chunks.

## Why this is worth GPU time

70% of the coverage that the low-coverage half of the universe is missing is the
judgement half abstaining, not the measured half failing. Of 19,755 available points lost
across the 570 companies under 0.8 coverage: **BQ 6,330, MG 4,256, SG 3,324**, against
FE 2,016 / VA 2,441 / BS 1,249 / ER 86 / EN 53. And 422 of those 570 have **zero** BQ
availability. Coverage does not move without this.

## Design

Two arms over the same companies, same model (`qwen2.5:7b`), same seed, same fact sheet.

* **A - control.** The current single-call BQ pack, regenerated, not read from cache.
* **B - split BQ.** The 7 dimensions that answer stay in call 1 unchanged. The 4 weak
  dimensions (`network_effects`, `manufacturing_complexity`, `data_advantages`,
  `economies_of_scale`) move to a second call whose pack is retrieved by **one embedding
  query per dimension**, 2 chunks each, from the same chunk pool.

Two calls rather than one bigger pack because `QUAL_NUM_CTX` is 8,192 and a BQ prompt is
already ~12.5k chars (~3.1k tokens); adding 12 chunks would push it to ~7.8k tokens and
risk truncating the schema at the front - the exact failure the E12 registration warned
about.

**Sample: 30 companies** - 20 drawn from the under-floor set stratified across Real
Estate, Energy, Utilities, Financials and Information Technology, plus **10 controls that
already clear the floor**, to catch a change that buys coverage by breaking what works.

## Pass criteria, fixed now

| | passes if |
|---|---|
| **P1** | On the 20 under-floor companies, median dimensions scored rises by **>= 1.5** in arm B vs arm A. |
| **P2** | **Fabrication does not rise.** The unverified-quote rate in arm B is **<= 1.0%** (the incumbent's M3 is 0.28%; llama3.1's 1.67% was disqualifying). A B that answers more by inventing quotes FAILS regardless of P1. |
| **P3** | On the 10 controls, no dimension that was scored in arm A becomes null in arm B for more than **1 of 10** companies. |
| **P4** | Added cost **<= 25 s per company** on this box, so a full 1,498-company regeneration stays inside one overnight window. |

All four must pass for the change to reach production. P1 alone is not enough; P2 is the
one that decides it, for the same reason E07 came down to M3.

## Prediction, stated before running

**Partial pass.** `manufacturing_complexity` and `economies_of_scale` improve materially -
10-Ks discuss plants, scale and cost structure in quotable terms. `network_effects` stays
mostly null even with a targeted query, because the language is not in the filing to
retrieve; that is a genuine absence and belongs to E12's applicability question, not here.
`data_advantages` I expect in between.

If that is what happens, the honest outcome is **retrieval fixes two dimensions and E12
still has to decide one or two**, which is a smaller and better-posed rubric question than
the four-dimension one it is holding now.

## What this cannot establish

Nothing about whether BQ predicts anything. There is no forward-return grader. More
dimensions scored means more companies clear the floor and get a band; it does **not**
mean the bands are better. `promoted` stays false. Any write-up says so.

## Outputs

`journal/experiments/E15_results.json` / `.md`, per-dimension and per-sector, never a
single pooled number.
