# E42 - the citation rule, measured

Two arms over the same three companies (FICO, VRT, NVDA), same roster, same two-pass
structure. Arm 2 adds one enforced rule: every non-UNKNOWN categorical needs a claim
whose `field` names it, or the finalizer demotes it to UNKNOWN.

| | arm 1 `812721fe9a0d87fd6b72` | arm 2 `d2b5f81d5335a87baedf` |
|---|---|---|
| rule | none | `require_citation: true` |
| claims | 14 | **32** |
| distinct sources | 14 | 20 (9 new) |
| distinct quotes | 14 | **32, zero reuse** |
| claims per source | 1.00 | **1.60** |
| independence domains | 4 | **6** |
| verified locally | 13 of 14 | **32 of 32** |
| searches | 29 | **2** (+20 cache hits) |

## The headline

Evidenced coverage, over the 13 company categoricals, against the 0.80 gate:

```
              arm 1 asserted    arm 1 EVIDENCED    arm 2 (all evidenced)
FICO             12/13  0.923      4/13  0.308        11/13  0.846  SCORES
NVDA             13/13  1.000      4/13  0.308        11/13  0.846  SCORES
VRT              11/13  0.846      2/13  0.154        10/13  0.769  no score
```

**Arm 1's coverage was not real.** It read 0.92 / 1.00 / 0.85 and would have produced
external scores for all three companies, but 26 of its 36 asserted fields had no
citation. Replayed through the rule its true evidenced coverage is **0.31 / 0.31 /
0.15**, and none of the three would score at all.

Arm 2's numbers are lower and they are all backed by a quote that we fetched and
matched ourselves. Two of three companies now clear the gate honestly. VRT misses at
0.769, one field short - which is the correct answer for a company whose capture and
share direction genuinely could not be established.

## The rule was not gamed

The obvious failure mode was relabelling: attach an existing quote to a new field name
and satisfy the rule without doing any research. It did not happen.

```
32 claims, 32 distinct quotes, 0 reused
```

Spot-checking the fields that arm 1 asserted with nothing behind them, the arm 2 claims
are specific and on-point:

- FICO `competitive_position_trend` cites named lenders - Rocket, United Wholesale,
  AmeriSave - moving originations to VantageScore. CONTRADICTS.
- FICO `pricing_power` cites "B2B revenue increased 49%, primarily attributable to a
  higher mortgage origination scores unit price."
- NVDA `technology_risk` cites AMD's own filing: Instinct data-centre revenue +107%.
- NVDA `disruption_risk` cites Google's Ironwood scaling to 9,216-chip pods.
- VRT `competitive_position_trend` cites +410bps adjusted operating margin, and the
  claim text says in as many words that this does not prove share gains.

## What the 2 searches do and do not mean

Arm 2 cost 2 searches against arm 1's 29, and it is tempting to read that as "the
citation rule is free". It is not what happened.

11 of arm 2's 20 sources were already in the cache from arm 1 and Phase 0. The corpus
had been paid for. What arm 2 shows is that **the binding constraint in arm 1 was
extraction depth, not search budget** - the documents were already there and only one
finding per document was being taken out of them. Under the rule that went to 1.6.

So the cost of the rule on COLD companies is still unmeasured. A 40-company run pays
arm-1-style search costs to build the corpus first, and then gets arm-2-style density
on top of it for very little extra. That is a good shape, but the first number is the
one that sizes the job.

## What got weaker

`COMPANY_IR` went from 5 of 14 claims to **11 of 32** - the weakest independence domain
grew fastest. That is expected when a field like `pricing_power` is easiest to evidence
from a company's own margin commentary, and it is exactly why confidence counts distinct
domains rather than claims. Worth watching: a rule that demands citations will always
push a researcher toward the most citable source, which is the company itself.

## The unevidenced list is the useful output

Six conclusions Codex believes and could not evidence, reported rather than asserted:

- FICO probably still captures substantial mortgage-scoring economics, but price-led
  growth does not establish unit or share capture.
- NVIDIA appears to maintain relative advantage, but no comparable share series exists
  that includes custom hyperscaler silicon.
- NVIDIA and Vertiv both look expensive on the staged valuation, but no source-backed
  valuation classification is available.
- Vertiv likely has positive company-specific capture, but competitor disclosures are
  not comparable.
- Vertiv may be gaining share on selected AI projects, but named wins do not establish
  portfolio-wide share direction.

Three of these are the same shape: **valuation classification has no citable source.**
`cheapness_quality` is asked of a researcher who has the multiples in front of it and
no external document that says "this is structurally cheap". FICO managed it by citing
regulatory pricing scrutiny; NVDA and VRT could not. That is a design question for
`score.py`, not a research failure.

## The calibration cases survived the rule

FICO `moat_trajectory: WEAKENING`. NVDA `STABLE` with scaling alternatives named.
VRT's industry and demand evidence was NOT converted into unsupported company capture.
All three held under a rule that removed two thirds of arm 1's assertions.

## A bug found while measuring this

`ORDINAL_FIELDS` silently grew from 13 to 16 when the industry vocabularies were added
at the Phase 0 ingest. Anything using it as a company coverage denominator would have
divided by 16. A company with all 13 answered would have read **0.813 instead of
1.000**, and one with 11 answered would have read 0.688 and failed a gate it actually
clears at 0.846.

Split into `COMPANY_ORDINALS` (13) and `INDUSTRY_ORDINALS` (3). `finalize.py` now
accepts only the company set, so an industry field cannot be stored in a company row.
Caught before `score.py` was written; the same shape as the MG constant going stale
under a name that used to be right.

## Provenance

Arm 1 is stored under research version `2026-09-02` because it was finalized before the
run label became part of the version; arm 2 is `2026-09-02+E42-cited`. The two arms did
not collide and arm 1 was **not** relabelled or replayed. Renaming it would be tidying
a stored research record for cosmetic consistency, which is the thing this layer
refuses to do everywhere else.

Catalog after both arms: 155 claims, 135 VERIFIED_LOCAL, 18 SELF_ATTESTED (unreachable
sources), 2 UNVERIFIABLE. Corpus unverifiable rate 1.5% over 137 checked.
