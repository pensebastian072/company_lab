# Re-reading E37 and the book review after the parse bug was fixed

**2026-08-31, after the reboot.** Both studies were re-run against a v2 book whose five
parse-destroyed components had been regenerated. Nothing about the model, the prompt, the
filings or the cache key changed between the two runs; only `extract_json` did. The
pre-fix results are kept verbatim beside them as `prebugfix_*.json` / `prebugfix_*.md`.

## The five components

| ticker | component | before | after |
|---|---|---|---|
| KGS | SG | dead | 6 sub-tests |
| R | SG | dead | 6 |
| PLMR | SG | dead | 6 |
| AIZ | BQ | dead | 11 dimensions |
| NWSA | BQ | dead | 11 |

All 4,416 v2 payloads now parse; zero parse failures in the cache.

## What changed, and what did not

### The book review's "broken in the v2 book" list is now empty

| component | dead in v2, before | after |
|---|---:|---:|
| SG | 3 | **0** |
| BQ | 2 | **0** |
| MG | 0 | 0 |

Every component the review called broken was our parser deleting a valid answer. The v2
model never declined to produce one.

### E37's SCORED -> NULL count was inflated by half on the judged side

| | before | after |
|---|---:|---:|
| total | 66 | **41** |
| judged | 37 | **18** |
| measured | 29 | 23 |
| share of scored sub-tests | 0.131% | **0.082%** |

Nineteen of the 37 judged losses were ours. The remaining 18 are the candidate genuinely
abstaining, still led by `sg_secular_not_cyclical` (12) and `va_ev_sales_vs_peers` (8).
The measured-half movement (29 -> 23) is fold noise, not the parser: the measured half
moves with the folded cohort and always has.

### Everything E37 was actually about is unchanged

| | before | after |
|---|---:|---:|
| raw mean delta | +8.74 | +8.79 |
| common-support mean | +4.251 | +4.245 |
| judged fill | +4.190 | +4.192 |
| judged disagreement | +3.879 | +3.889 |
| `bq_moat` n / mean delta | 1279 / +2.53 | 1280 / +2.53 |
| downgrades kept on common support | 33 of 62 | 34 of 60 |

The decomposition, the disagreement concentration and the `bq_moat` result do not depend
on the bug. **E37's headline stands: about half the lift is the schema filling
abstentions and about half is the same evidence scored higher.**

### The book moved slightly, in the direction you would expect

| | before | after |
|---|---:|---:|
| clearing the 0.80 coverage gate | 1,410 | **1,414** |
| `INSUFFICIENT_DATA` | 62 | **58** |
| HIGH_CONVICTION | 27 | 30 |
| Spearman on `score` | 0.918 | 0.922 |
| Spearman on `sector_neutral_score` | 0.845 | 0.848 |
| bands agreeing with v1 | 541 | 535 |
| top-50 survivors | 29 | **28** |

Five companies gaining a judged component moved four of them over the coverage gate. It
does not rescue the headline finding: **the v2 book is still a different book** — 535 of
1,472 keep their band (36%), and 28 of the top 50 survive.

## What this does not touch

E40 and E41 were computed on payloads, not on the folded book, and the parse bug never
reached them. The citation-containment gap (LFM2.5 9.7% vs qwen 0.5%) and E41's costing
(1,184 -> 1,321, 16 companies, 264 unverifiable answers dropped) stand as written.
