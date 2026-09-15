# The external scores in the store are stale — three instrument changes, none applied

Measured 2026-09-09 by Chat A against the live store. Nothing was written: every number
below comes from a dry recompute.

Status: SHADOW / advisory. `promoted` is false.

Corpus state: 523 company records across 13 research versions, 7,076 claims
(6,950 VERIFIED_LOCAL, 64 UNVERIFIABLE, 62 SELF_ATTESTED), 60 active industry objects.

## First, the roadmap item is stale

`ROADMAP_TO_E75.md` lists "the unrecorded scoring change (Chat A, first)" as open. It is
not. `journal/experiments/A1_UNVERIFIABLE_SCORING_DECISION_2026-09-08.md` (commit
`d2dcbda`) registered the doctrine a day later, with a frozen receipt and a 39-row effect
table, and it also corrected the handoff's own counts — 27 tickers not 28, three industry
objects plus one sector object not four.

Reproduced here independently before reading that document, from the current store: the
per-record deltas match it exactly — NYT −16.5, CEG −11.7, MA −10.2, EQT −9.0, JKHY −7.5,
CINF −6.7, SRE −5.3. The registration stands. **Remove the item from the roadmap.**

## What is actually open

The decision document says, correctly and deliberately: *"No score, field, verdict or
promotion flag was written to the live store for this measurement."*

It never was afterwards either. `score_all --apply` has not been run since at least three
changes to the instrument, so `company_external.external_score` still holds pre-change
values. Recomputing every record with today's code, against the same stored evidence:

| | records |
|---|---:|
| company records in the store | 523 |
| carry a stored `external_score` | 395 |
| **stored NULL, would score today** | **128** |
| **stored score disagrees with a recompute** | **42** |
| stored score that would be LOST | 0 |

Nothing loses its score. The exposure is in the other direction — 128 companies are
carrying no external score at all, and 42 are carrying a number the current instrument
would not produce.

## The 42, attributed

Two separate causes, pulling opposite ways. Neither is drift; both are instrument changes
that were made and never applied.

**29 of 42 — the A1 doctrine.** Every one carries at least one UNVERIFIABLE claim.
Isolated by rescoring with UNVERIFIABLE treated as usable, same code and same clock: 32
records move, mean **−5.19** points, every movement non-positive. These are the same rows
the 2026-09-08 decision measured; the store simply still holds the "before" column.

**13 of 42 — the FDIC computed `market_share_direction`.** All are `2026-09-02+E44-matched`
banks, all with **zero** UNVERIFIABLE claims, all moving **up**: ten at +5.0 and three at
+2.5. Cause confirmed on BOH: its `market_share_direction` is backed by a computed
PRIMARY_DATA claim from the FDIC Summary of Deposits API, created 2026-09-02 **16:52**,
where the E44 records were scored at **15:32**. 29 banks now carry such a claim. The field
became scorable an hour after the arm was scored and nobody re-ran it.

That second one matters more than its size: **`2026-09-02+E44-matched` is a matched
control arm**, and a +5.0 on ten of its members changes an arm comparison, not just a
company's number.

## The decision this needs, and it is not mine

Re-scoring is one command and it is not reversible in practice — the previous values exist
only in the 2026-09-08 receipt and in this file.

Applying it rewrites the stored scores of `2026-09-02+E43-batch1`,
`2026-09-02+E44-matched`, `2026-09-05+E47-utilities`, `2026-09-05+E49-commservices`,
`2026-09-06+E51-commservices-symmetric` and `2026-09-07+E53-utilities-symmetric` — the arms
that registered experiments were read off. A study computed on the old numbers and a
workbook showing the new ones is the worse of the two states, so if it is applied, the
affected results files need a dated line saying which scoring generation they used.

The alternative — leave it — means the workbook keeps showing 42 scores the instrument
disowns and 128 blanks it could fill.

Recommendation: apply, then stamp the affected results files, because the blanks and the
A1 rows are both cases of the store contradicting a registered decision. But the arms
belong to studies, so the call is the user's.

## Two smaller things found on the way

**The doctrine and the code disagree on one path.** The registered doctrine says
UNVERIFIABLE covers "quote/source mismatches, **failed extraction** and formatting
artifacts". `verify.py` does not implement it that way: a PDF whose extraction throws or
returns implausible text becomes `pdf_not_extracted` → **UNVERIFIABLE**, while any page
that extracts to under `MIN_PAGE_CHARS` (400) becomes SELF_ATTESTED with the reason
"likely a JS shell or an unreadable PDF". Same physical failure — we fetched bytes and
could not read them — on opposite sides of the scoring line, and the module's own docstring
argues the SELF_ATTESTED side ("an empty page is a page we could not read"). Live footprint
is small and lopsided: **2 claims** on the UNVERIFIABLE side, **33** on the SELF_ATTESTED
side. Either the doctrine's "failed extraction" clause should be narrowed to quote
mismatch, or those 2 claims should move. Two claims, one line of code, but it is the kind
of unreconciled edge that becomes a false rate later.

**33 claims rest on a single URL.** All 33 of the `<400 chars` SELF_ATTESTED claims cite
one DOJ press release (`justice.gov/archives/opa/pr/justice-department-sues-visa-...`),
which serves an archive shell rather than a body. One unreachable page is currently
supporting 33 claims' worth of scoring. Not a defect in itself — it is a concentration
worth knowing about, and it belongs with B6's recount.

> **B6 recount, 2026-09-10.** That URL now carries **34 claims across 18 tickers**, so the
> concentration grew by one while it sat open. But it is not the corpus's largest by a
> wide margin, and looking only where the last finding pointed would have missed the real
> one: a **single FDIC quarterly-banking-profile speech supports 162 claims across 70
> tickers**, five times the DOJ page. Next are one EIA page at 88 claims / 42 tickers and
> the computed `computed://company_lab/revenue_share` source at 87 / 64.
>
> Corpus context, from `CORPUS_SNAPSHOT_2026-09-10.json`: 7,223 claims over **917 distinct
> URLs**, with the ten most-cited carrying 656 of them = **9.1%**. So the corpus is not
> broadly concentrated; it has a small number of very load-bearing pages, and both of the
> top two are single documents that a whole sector's structural claims rest on. Whether
> that is a defect depends on whether those pages are the right source for 70 companies at
> once — which is a question about scope comparability, not about verification, and is not
> answered here.

## What this does not establish

It compares stored numbers to recomputed ones. It says nothing about whether either is
right, whether the evidence semantically supports its fields, or whether this ranking
predicts anything. E05 measured the top decile at −7.6% median three-year excess and E03
put 95.6% of ranking power in sector selection; both still stand.

---

## APPLIED 2026-09-09 — what actually moved

The user chose "apply, then stamp the studies". Done, in this order:

1. The DuckDB store was copied to
   `D:/company_lab_data/external/backups_external_intelligence_pre_rescore_20260909.duckdb`.
2. Every stored score was frozen to
   `D:/company_lab_data/external/reports/prescore_snapshot_2026-09-09.json`
   (523 rows, sha256 `a8189d864f7981508c26ab136050a1b28ed10ab9f4d0a80106f2f14a4e920272`).
3. `score_all(apply=True)` ran across all 13 research versions, 523 records.
4. The result was read back FROM THE STORE and diffed against the frozen snapshot.

| | records |
|---|---:|
| scored before | 395 |
| **scored after** | **523** |
| filled (NULL -> score) | 128 |
| changed | 42 |
| unchanged | 353 |
| **lost a score** | **0** |

Score movement across the 42: mean **-2.55**, range **-16.5 to +5.0**. The two directions
are the two causes — A1 pulls down, the FDIC computed field pulls up.

Per arm, from the store:

| research version | changed | filled |
|---|---:|---:|
| `2026-09-02` | 1 | 0 |
| `2026-09-02+E43-batch1` | 9 | 0 |
| `2026-09-02+E44-matched` | 14 | 0 |
| `2026-09-04+E46-energy` | 2 | 0 |
| `2026-09-05+E47-utilities` | 2 | 0 |
| `2026-09-05+E49-commservices` | 5 | 0 |
| `2026-09-06+E51-commservices-symmetric` | 5 | 0 |
| `2026-09-07+E53-utilities-symmetric` | 4 | 0 |
| `2026-09-08+E59-financials-phaseb-b1` | 0 | 43 |
| `2026-09-08+E59-financials-phaseb-b1-rerun` | 0 | 43 |
| `2026-09-09+E59-financials-phaseb-b2` | 0 | 42 |

`2026-09-02+E44-matched` moved 14, not the 13 forecast above: OXY also carries an
UNVERIFIABLE claim, so it belongs to the A1 group rather than the FDIC group. The
attribution holds — 29 A1 + 13 FDIC = 42 — the arm totals just cut across it.

Eight results files carry a dated stamp naming the scoring generation and the largest
moves in their arm: E43, E44, E46, E49, E49_verification, E51, E53, E59. **No number in
any of those files was restated.** A study that was computed on the pre-re-score values is
still that study; the stamp says so and points here.
