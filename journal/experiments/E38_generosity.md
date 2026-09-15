# E38 - generosity: the model or the format?

Control lane at **1471 companies** (past the registered 100 minimum). Measured on BQ moat dimensions read from the payloads; the control lane is never folded, and `bq_moat` is where E37 localised the disagreement.

| comparison | paired | both scored | mean `bq_moat` /15 | Δ points | Δ per shared dimension /5 |
|---|---:|---:|---:|---:|---:|
| qwen-v1 → **qwen-structured** | 1470 | 929 | 7.6 → 7.7 | **+0.1** | +0.002 |
| qwen-structured → **LFM2.5** | 1471 | 1015 | 7.6 → 8.6 | **+1.003** | +0.598 |
| qwen-v1 → **LFM2.5** | 1471 | 1020 | 7.52 → 8.6 | **+1.085** | +0.609 |

`bq_moat` is compared only where **both** lanes clear the 6-of-11 quorum - otherwise the number measures coverage, not generosity. The last column is the mean 0-5 gap over the dimensions both lanes scored, which no amount of answering-more-questions can move.

## Attribution

Of the **+1.085** points E36 measured between production and the v2 lane:

* the **format** (schema + 2,500 tokens) accounts for **9%**
* the **model** accounts for **92%**

## What this does not establish

That the more generous scorer is the better one. There is no forward-return grader in this repo, so a higher moat score is a higher moat score. `promoted` stays false.
