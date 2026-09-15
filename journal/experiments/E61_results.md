# E61 - Industrials Phase A results

Recorded 2026-09-09 from the live store and the current Phase A payloads, after ingest,
local verification and exact readback.

Status: SHADOW / advisory

Promoted: false

E61 added 25 Industrials industry objects covering 259 companies. Together with the
protected `datacenter_power_cooling` object already in the active Industrials research
tree, the sector now has 26 active objects and 145 current-object claims. No company
research, request, score, rank, selection or promotion was performed.

## What shipped into SHADOW

| Measure | Live result |
|---|---:|
| E61 objects | 25 |
| E61 mapped companies | 259 |
| E61 claims | 138 |
| E61 claims `VERIFIED_LOCAL` | 138 |
| Active Industrials objects, including protected prior work | 26 |
| Current-object claims across those 26 | 145 |
| Current-object claims `VERIFIED_LOCAL` | 142 |
| Current-object claims `SELF_ATTESTED` | 3 |
| Objects below the eight-claim aspiration | 24 of 26 |

The 138 E61 claims are all `VERIFIED_LOCAL`. The three residual `SELF_ATTESTED` claims
belong to the protected pre-E61 `datacenter_power_cooling` object, not to the new E61
slice. The five E61 claims used to support non-`UNKNOWN` categorical fields are also all
`VERIFIED_LOCAL`; the other 70 categorical cells stay `UNKNOWN` with their reason recorded
as either evidence absent at the inherited bucket level or work stopped short.

The store SHA-256 after verification was
`7f3f8e972e3a0c0d20b3e2ac2630844071312c2acd22593db18e18d7e6592fd9`. A metadata-only
correction removed `NO_STORE_APPLY` from the already-applied sector label; after the
idempotent re-ingest the final store SHA-256 was
`b3320b43f05d9167aec6801f63ae4d43ec0a83ddd774fccc7109cf965fbb4410`. Claim statuses did
not move in that re-ingest.

## Evidence depth and diversity - accepted with eyes open

This is the thinnest Phase A accepted into the SHADOW corpus so far. It was accepted
knowingly, not because it cleared the original evidence-depth aspiration:

- 24 of 26 active objects have fewer than eight claims.
- 140 of 145 current-object claims use `COMPETITOR_FILING`; the remaining five comprise
  three `COMPANY_IR` and two `REGULATOR` claims.
- The 25 new E61 objects themselves use one independence domain. Independent issuers
  provide organization diversity, but they do not provide source-type diversity.
- The builder retained 138 of 225 candidate windows after explicit field- and scope-level
  rejections. Its automated field-keyword screen is not independent semantic proof.

The contrast with E57 Health Care belongs in the same record. Health Care had five
independence domains and 31 distinct URLs, yet its independent B4 review found that 55 of
66 verified passages did not directly establish their assigned full field claims, so all
11 objects were retired. Industrials has only three domains across its active tree and is
being kept. The decisions point in opposite directions on evidence diversity alone because
diversity was not the sole acceptance rule: literal verification, direct field support,
explicit abstention and disclosed depth were considered separately. Keeping E61 is not a
finding that its source diversity is adequate.

`VERIFIED_LOCAL` means the stored quote was found in the fetched source. It does not prove
that a passage establishes the assigned field, that an industry bucket is coherent, or
that a categorical magnitude is correct. The E61 report therefore preserves every manual
rejection and does not promote its automated selector into a semantic guarantee.

## Taxonomy and abstention disposition

No taxonomy edit was made. Broad inherited buckets that could not be split completely
from the available evidence remain intact and are flagged for review. Heterogeneous units
such as `diversified_support_services`, `environmental_facilities_services` and
`industrial_conglomerates` retain `UNKNOWN` categoricals rather than inheriting a forced
common direction.

The two protected roster units were not rebuilt: `datacenter_power_cooling` and
`us_credit_scoring` remain at version `2026-09-01`. `us_credit_scoring` remains a
Financials-sector research object even though its two companies are part of the frozen
Industrials roster map.

## Lifecycle and interpretation

The whole-tree ingest did not resurrect retired research. All 11 Health Care objects at
version `2026-09-07`, the 59-row E53 Utilities company arm and the 43-row burned E59
Financials arm remain `SUPERSEDED`.

E61 increases research coverage for the largest sector in the book. It does not establish
predictive power, validate a ranking, or authorize promotion. Any Phase B use must carry
the thin-evidence and single-domain limitations forward rather than treating presence in
the store as an endorsement.
