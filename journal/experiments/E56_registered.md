# E56 — registered before Phase B: the middle-clustering question

Registered 2026-09-06, **before** any Financials company research runs. Nothing here is
acted on now. Advisory / SHADOW throughout.

## What was observed

E54 built 15 Financials industry objects. Every quality metric was clean — 75/75 claims
VERIFIED_LOCAL, corpus unverifiable rate steady at 0.077%, no unbacked categorical — and
it answered 41 of 45 structural fields, so this is **not** the abstention failure that
`batch_health.compare()` was built to catch.

> **Correction recorded 2026-09-07:** 0.077% is preserved as the registered input, not
> a current verified rate. The corrected corpus figure is 64/5,233 = 1.22%; see
> `verification_rate_correction_2026-09-07.md`. The registration is not rewritten.
> **Correction re-stated 2026-09-09.** This figure has now been quoted as 0.077%,
> 0.134%, 1.607%, 1.22% and 0.980% - every one of them true of a different corpus. The
> COUNT is the stable fact: **64 claims are UNVERIFIABLE**, from token overlap accepting a
> quote whose numbers are absent from the source, not from verifying against binary. The
> RATE moves with the denominator as coverage grows (6,531 claims as of 2026-09-09 =
> 0.980%). Quote the count and the as-of date, never a bare rate. Live figures are pinned
> in `CORPUS_SNAPSHOT_2026-09-09.json` (SHA-256 `FDA33CB1B32B0C3F4562C9799A66632765DEC43C7B749CEBB495C243FBDCA0A5`), on D: under external/reports.

Two patterns showed up in the store instead:

1. **Uniform evidence depth.** All 15 objects drew exactly 5 claims. Across the 53
   objects carrying object claims the counts run 4:9, 5:38, 6:3, 7:1, 9:1, 11:1 — so 5 is
   not a cap. `diversified_banks` and a three-company bucket that did not describe one
   business got identical budgets. Consistent with the 68-search underrun against a
   200–280 allowance.
2. **The end of the scale is never used.** Answered values only, two-tailed Fisher against
   the 39 pre-existing objects: `structural_growth` MODERATE 10/11 vs 14/36 (p=0.0044);
   `replication_difficulty` EXTREME 0/12 vs 12/37 (p=0.0242). At sector level, across all
   20 Financials objects, `object_health()` reads modal share **0.93** on
   `structural_growth` against **0.36** for every other sector, and endpoint share
   **0.00** against **0.38** on `replication_difficulty`.

## The confound this exists to settle

Financials is genuinely a mature sector, so central values may simply be right. The five
Financials objects built by earlier runs lean the same way, and Utilities does too — but
those came from this pipeline, so they corroborate rather than control, and n=5. **The
sector effect and the run effect cannot be separated on what we have.**

## Registered predictions

Measured with `clab.external.batch_health` — `object_health()` for objects,
`compare()` for companies. Each states what refutes it.

**P1 — depth stays uniform.** Across Phase B's 170 Financials companies, claims per
company will have ≤ 3 distinct counts, indicating a per-company quota rather than
evidence-driven depth. *Refuted if* depth varies as widely as the object corpus does
(≥ 6 distinct counts).

**P2 — the middle-reach carries into company fields.** Financials company ordinals will
show an endpoint share at least 0.15 below the non-Financials baseline. *Refuted if* the
gap is under 0.15, which would confine the pattern to industry-level questions.

**P3 — the discriminator.** The five objects built by the E56 re-cut
(`private_mortgage_insurance`, `retirement_benefits`, `climate_infrastructure_finance`,
`commercial_mortgage_banking_servicing`, `multi_industry_conglomerate`) are Financials
objects researched in a **separate session**. If the clustering is a property of the
sector, they will repeat it — modal share ≥ 0.8 on `structural_growth`. *Refuted if* they
spread, which would make E54's pattern a run artifact rather than a fact about Financials.

P3 is the one that carries information, and it is why the re-cut runs **before** Phase B.
It is n=5, so it can suggest and not settle.

### Amendment, 2026-09-07 — before the five objects were researched

Writing the evaluator (`clab/research/e56_p3.py`) before the data exposed a hole in P3 as
first registered. `modal_share` is computed over ANSWERED values only, because UNKNOWN is
NO_DATA and never a value. But four of these five objects have one or two members, and
the prompt explicitly invites `multi_industry_conglomerate` to return UNKNOWN if a shared
answer would be fiction. **If only one object answered, its modal share would be 1.0 and
P3 would "confirm" on a sample of one.**

So a floor is registered now rather than discovered afterwards: **fewer than 3 of the 5
answering `structural_growth` makes P3 INDETERMINATE** — not CONFIRMED, not REFUTED.
`MIN_ANSWERED = 3`, `MODAL_THRESHOLD = 0.80`, both constants in the module, every verdict
boundary pinned by `tests/test_e56_p3.py`. n=3 is still thin and the verdict text says so.

The evaluator was run before the research and returns INCOMPLETE, which is the receipt
that its thresholds were fixed while the answer was unknown.

## What each outcome means

| P3 | P2 | reading |
|---|---|---|
| repeats | gap ≥ 0.15 | a researcher tendency toward the middle, across sessions and levels. Fix the prompt, not the taxonomy. |
| repeats | gap < 0.15 | Financials really is middling at industry level; company fields are unaffected. Leave it. |
| spreads | gap ≥ 0.15 | E54's objects were a one-run artifact and the company phase has its own problem. Two separate fixes. |
| spreads | gap < 0.15 | no finding. E54 was noise at n=15 and the confound wins. |

## What the E56 prompt does and does not say

Declared here so it is not discovered later as a hidden intervention.

**It says nothing about the value distribution.** No mention of MODERATE, of the middle
of a scale, of E54's clustering, or of what a good spread would look like. Telling the
researcher it clustered last time would guarantee a spread and destroy P3 - the same
mistake in the opposite direction as quoting a streak back, which standard rule 1 already
forbids. The only guidance on values is the standard block, which is symmetric by
construction.

**It does tell the researcher not to aim for a fixed claim count** (`EVIDENCE DEPTH
FOLLOWS THE EVIDENCE`), naming the five literatures as genuinely different in size. That
is an intervention on depth, so **P3 is a clean test of the value distribution and is NOT
a clean test of depth uniformity.** If these five come back with varying depth, the
prompt is a sufficient explanation and no conclusion about E54's quota follows. P1
measures depth on Phase B, whose prompt does not carry that instruction.

## Rules this run is held to

- **No action on the E54 distribution before these are measured.** Sign-flipping a
  discovered effect to harvest it is p-hacking; this is registered instead.
- Per-fold / per-sector tables, never a pooled number that a sector mix could manufacture.
- A partial Phase B batch is balanced, not representative — do not read P1 or P2 off the
  first batch.
- `object_health()` reports and does not judge. A REGRESSION verdict is a prompt to look.

---

## PRE-RUN AMENDMENT - 2026-09-06, before any E56 payload exists

Two deterministic defects in the instrument that would read P3, both found in the live
store and both fixed before the result lands. Recorded as an amendment rather than folded
in silently, because changing how a measurement is taken after seeing its subject is how a
prediction gets fitted to its answer.

**1. `object_health()` counted every stored VERSION, not every object.**

`industry_intelligence` held 54 rows over 53 distinct `industry_id`s, so
`coal_consumable_fuels` was counted twice - and the extra row is the superseded
2026-09-02 cut whose `structural_growth` is `UNKNOWN` against the current `DECLINING`. A
phantom all-UNKNOWN object was sitting in the baseline of a study about how often objects
answer UNKNOWN. The active corpus is now one row per industry, latest version.

**2. The three re-cut buckets were still in the active corpus.**

`multi_sector_holdings`, `specialized_finance` and
`commercial_residential_mortgage_finance` returned UNKNOWN on all three industry fields,
which is exactly why E56 re-cut them. Left in they inflate `n_objects` and enter
claim-depth statistics with 15 claims between them. Their all-UNKNOWN values do not move
modal or endpoint shares - those are computed over answered values only - but they are not
analytically inert.

### Lifecycle: retired operationally, retained evidentially

Nothing is deleted. Four new columns on `industry_intelligence` - `status`,
`superseded_by`, `superseded_reason`, `superseded_at` - carry the mapping and a dated
reason, and the state files, briefs, rows and verified claims all stay for audit.

```
multi_sector_holdings         -> multi_industry_conglomerate (BRK-B),
                                 investment_banking_brokerage (JEF),
                                 retirement_benefits (VOYA)
specialized_finance           -> consumer_finance (CACC), mortgage_reits (EFC),
                                 climate_infrastructure_finance (HASI)
commercial_residential_
  mortgage_finance            -> private_mortgage_insurance (ACT, ESNT, NMIH),
                                 commercial_mortgage_banking_servicing (WD)
coal_consumable_fuels
  version 2026-09-02          -> coal_consumable_fuels 2026-09-02.1
```

`object_health()` reads the ACTIVE corpus by default and
`object_health(include_superseded=True)` returns all historical evidence, so verification
can report both.

### Effect on the baseline P3 will be read against

```
active corpus     n_objects 50      claim depth 4-11    (one row per live industry)
all historical    n_objects 54      claim depth 4-11    (every stored ROW)
```

*(Corrected: this first read 53 for all historical. Now that `include_superseded=True`
skips the latest-version dedupe entirely, it returns 54 ROWS - the 53 distinct objects
plus the second `coal_consumable_fuels` version. 50 / 53 / 54 are three different true
numbers: live industries, distinct industries ever, and stored rows. Row counts and
object counts have now diverged twice, so state which one a figure is.)*

Claim depth is unchanged - the three superseded objects sat inside the existing range, so
this does not move the depth statistic. It removes three all-UNKNOWN objects and one
phantom duplicate from the object count.

**The modal and endpoint shares are identical active versus historical, and that is a
coincidence, not a property.** It holds only because every object retired so far happened
to be all-UNKNOWN, so none of them ever entered the answered denominator. A future re-cut
that retires an object which DID answer will move the shares. Do not read "identical"
here as a guarantee that retirement cannot affect the distribution P3 is judged on. **P3 is evaluated against the 50-object active
corpus.**

### What this does NOT change

The five re-cut objects do not exist yet; E56's Codex run has not been handed over at the
time of writing. No prediction is altered, no threshold is moved, and the amendment is
dated before any payload. `promoted` stays false.
