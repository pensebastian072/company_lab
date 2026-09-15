# E54 — Financials Phase A: 15 industry objects

Ingested and verified 2026-09-06. **Every number below was read back from the store, not
taken from the report.** Advisory / SHADOW; `promoted` is false and nothing here touches
a company score.

## What landed

| check | result |
|---|---|
| industry objects | 39 -> **54** (+15, all `sector_id=financials`) |
| claims | 5,117 -> **5,192** (+75, exactly the 75 reported) |
| verify status, new claims | **75/75 VERIFIED_LOCAL**, 0 SELF_ATTESTED, 0 UNVERIFIABLE |
| corpus unverifiable rate | 4/5,192 = **0.077%**, unchanged (was 4/5,117) |

> **Correction recorded 2026-09-07:** this is the historical rate reported by E54.
> PDF extraction-state and numeric-quote guards later revised the corpus tally to
> 64/5,233 checked = 1.22%. See `verification_rate_correction_2026-09-07.md`.
> **Correction re-stated 2026-09-09.** This figure has now been quoted as 0.077%,
> 0.134%, 1.607%, 1.22% and 0.980% - every one of them true of a different corpus. The
> COUNT is the stable fact: **64 claims are UNVERIFIABLE**, from token overlap accepting a
> quote whose numbers are absent from the source, not from verifying against binary. The
> RATE moves with the denominator as coverage grows (6,531 claims as of 2026-09-09 =
> 0.980%). Quote the count and the as-of date, never a bare rate. Live figures are pinned
> in `CORPUS_SNAPSHOT_2026-09-09.json` (SHA-256 `FDA33CB1B32B0C3F4562C9799A66632765DEC43C7B749CEBB495C243FBDCA0A5`), on D: under external/reports.
| non-UNKNOWN field with no claim naming it | **none**, across all 15 |
| `regional_banking` / `life_insurance` / `pc_insurance` | row hashes **identical** before and after |

The three pre-existing objects were hashed before ingest and re-hashed after, because
`research_ingest --apply` rewrites all 53 industries and 11 sectors from disk, not just
the new ones. They came back byte-identical.

Claim counts and independence domains per object match the delivered table exactly. The
UNKNOWN inventory also matches: `mortgage_reits.structural_growth`, and all three
structural fields on `commercial_residential_mortgage_finance`, `multi_sector_holdings`
and `specialized_finance`.

## The taxonomy questions E54 was asked to answer

All three preregistered splits **survived contact with the research** — custody vs
long-only on deposit/NII/capital economics, alternatives vs long-only on
fee-related earnings and permanent capital, exchanges vs data/ratings on volume
versus subscription and issuance. Keep them.

Two buckets **did not hold together**, and the researcher returned UNKNOWN on all three
structural fields rather than invent a shared answer — the refusal the prompt asked for:

- `multi_sector_holdings` (BRK-B, JEF, VOYA) — proposed units: multi-industry
  conglomerate / investment banking + asset management / retirement + benefits.
- `specialized_finance` (CACC, EFC, HASI) — proposed units: subprime auto finance /
  mortgage-credit REIT / climate-infrastructure finance.
- `commercial_residential_mortgage_finance` also split: `private_mortgage_insurance`
  (ACT, ESNT, NMIH) and `commercial_mortgage_banking_servicing` (WD).

That is 10 companies across three buckets. Deciding the units is cheap now and expensive
after Phase B researches 170 companies against them.

## Two things in the store the report does not mention

**1. Every one of the 15 objects has exactly 5 claims.** Five is not a cap: across the
53 objects carrying object claims the histogram runs 4:9, 5:38, 6:3, 7:1, 9:1, 11:1.
Pre-existing objects range 4 to 11 claims; the new 15 have min 5, max 5, zero variance.

*(Corrected 2026-09-06: this first read "4 to 35". The 35-claim bucket is
`industry_id = None` - sector-level claims, which are not an object. The finding is
unchanged, the range was overstated.)* `diversified_banks`
(JPM, BAC, C, WFC) and `specialized_finance` (three companies that do not belong in one
bucket) drew the same evidence budget. Consistent with the 68-search underrun against a
200-280 budget: the run stopped at a per-object quota, not at exhaustion.

> **Recounted 2026-09-10 under B6 — searches are not sources.** The 75 object claims cite
> **35 distinct URLs**. Twenty-six of those URLs are cited more than once, accounting for
> **40 repeat citations**. So a "68 search" figure describes work done, not evidence
> breadth: the evidence base under the 15 objects is 35 documents, and slightly more than
> half of the claims rest on a re-read of a document another claim already used. Quote
> distinct sources when the question is how much evidence there is, and searches only when
> the question is how much budget was spent.

**2. E54 never uses the bottom of any scale.** Answered values only (UNKNOWN excluded),
new 15 against the 39 pre-existing objects, two-tailed Fisher exact:

| field | pattern | new 15 | pre-existing | p |
|---|---|---|---|---|
| `structural_growth` | answered MODERATE | **10/11** | 14/36 | **0.0044** |
| `structural_growth` | DECLINING or FLAT | 0/11 | 10/36 | 0.0885 |
| `replication_difficulty` | EXTREME | **0/12** | 12/37 | **0.0242** |
| `replication_difficulty` | answered MODERATE | 5/12 | 5/37 | 0.0502 |
| `substitution_risk` | SEVERE | 0/12 | 1/36 | 1.0000 |

Ten of the eleven answered `structural_growth` values are MODERATE; the eleventh
(`alternative_asset_management`) is HIGH. No FLAT, no DECLINING, no EXCEPTIONAL, no
EXTREME, no SEVERE anywhere in the set.

> **Corrected 2026-09-10 under B6 — E54 does use one scale endpoint.**
> `custody_banks.substitution_risk` is **LOW**, and LOW is the terminal value of that
> scale (`SEVERE, ELEVATED, MODERATE, LOW` — it reads worst-first, so LOW is the
> favourable end and `normalized()` returns 1.0 for it). Recounted from the store:
> **1 of the 35 answered values sits at a scale endpoint**, not zero.
>
> The table above tests only the ADVERSE endpoint of each scale — DECLINING/FLAT, EXTREME,
> SEVERE — so "never uses the bottom of any scale" is not the thing that was measured. It
> measured endpoint avoidance in one direction. The favourable endpoints (EXCEPTIONAL,
> and LOW on both risk scales) were not counted, and one of them is in use.
>
> The substantive worry survives intact and is arguably sharper: 34 of 35 answered values
> are interior, and zero of 12 `replication_difficulty` values are EXTREME across a set
> that includes `financial_exchanges` and `diversified_banks`. One favourable endpoint on
> one object is not a spread.

**The confound, and it is a real one.** Financials is genuinely a mature sector, so
central values may be correct. Two things bear on it and neither settles it:

- The five pre-existing objects that resolve to `financials` lean the same way —
  `life_insurance` MODERATE/MODERATE/MODERATE, `pc_insurance` MODERATE/MODERATE/LOW,
  `regional_banking` UNKNOWN/MODERATE/ELEVATED, `payments` MODERATE/HIGH/ELEVATED,
  `us_credit_scoring` UNKNOWN/HIGH/ELEVATED. But they came from the same pipeline, so
  they are corroboration, not an independent control, and n=5.
- Other sectors do spread: communication services {MODERATE 5, FLAT 3, HIGH 2,
  DECLINING 1}, energy {FLAT 4, MODERATE 2, HIGH 1, DECLINING 1}, information technology
  {HIGH 5}. Utilities, the other mature sector, also leans MODERATE (4 of 7).

So the comparison mixes a sector effect with a run effect and **cannot separate them at
this n.** The single least comfortable cell is `replication_difficulty`: zero EXTREME
across 12 objects that include `financial_exchanges` (CME, ICE — liquidity network
effects and open-interest lock-in) and `diversified_banks`, where 32.4% of pre-existing
objects earned EXTREME.

**This is not the abstention failure.** E54 answered 41 of 45 structural fields, and the
four UNKNOWNs are all argued refusals of incoherent buckets.

> **Recounted 2026-09-10 under B6 — the count above is wrong and is kept so the error is
> visible.** From the store, the 15 objects at version `2026-09-06` carry 45 structural
> field values of which **10 are UNKNOWN and 35 are answered**, not 41. The "four" counts
> BUCKETS, not fields: `mortgage_reits` (one field) plus the three incoherent buckets
> (three fields each) = 4 buckets, 10 fields. This file's own table already implies it —
> its denominators are 11 + 12 + 12 = 35 — and its UNKNOWN inventory above lists all ten.
> The finding is unchanged: the four refusals are still argued refusals, and the flat
> middle is still the shape worth registering. Only the headline count was overstated. It is the shape the E53 guard
was registered against: answering, but on the safe middle. Worth registering as a
prediction before Phase B rather than acting on now — a distribution this flat either
reflects the sector or reflects a researcher reaching for the middle value, and the
company phase will discriminate between those cheaply.

## Process note

The delivered report stated `Repository HEAD remains cfe83d8` and described the E54
handoff as "a concurrent untracked document [that] appeared during the run". Both were
stale: the handoff was committed at `437359f` before the run, and HEAD had moved to
`bb39300` and then `4bedf11` from the parallel session. The payload claims about `D:`
verified cleanly; the claims about repo state did not. Verify repo assertions locally.

## Not run, by design

No `clab.external.request`, no `finalize`, no `score --apply`, no roster, no company
research. E53's `journal/flags/external_research_request.json` was never opened. The only
`--apply` calls were `research_ingest` and `verify`.
