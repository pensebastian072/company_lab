# E17 results - the quote gates the score (2026-08-18)

ADVISORY / SHADOW. A verified quote means the sentence is in the filing, not
that the score is right. No forward-return grader exists. `promoted` stays false.

Repair call ran on 52 companies (49 under-floor).

| criterion | measured | bar | verdict |
|---|---|---|---|
| R1 floor clearance, STRICT gate | 21 of 59 (35.6%) | >= 35% | PASS |
| R3 controls losing a dimension | 0 | 0 | PASS |
| R4 economies_of_scale, STRICT gate | 22.4% | >= 50% | FAIL |

Floor clearance by gate: no gate **22**, production 0.60 **22**, strict substring **21** of 59 (base call alone cleared 10).

## R2 - what survives verification (no bar; this is a description)

| gate | dimensions kept | of proposed |
|---|---:|---:|
| has_quote | 33 | 45.2% |
| production | 33 | 45.2% |
| tight | 33 | 45.2% |
| strict | 29 | 39.7% |

Median token overlap of a proposed quote: **1.0**. Scores offered with no quote at all: 40.

| dimension | proposed | production 0.60 | tight 0.90 | strict substring |
|---|---:|---:|---:|---:|
| network_effects | 2 | 1 | 1 | 1 |
| manufacturing_complexity | 9 | 4 | 4 | 4 |
| data_advantages | 24 | 16 | 16 | 13 |
| economies_of_scale | 38 | 12 | 12 | 11 |
