# E78 — results: all three predictions REFUTED, and the field they rest on is unusable

Run 2026-09-09 by Chat A, against the live store, immediately after
`journal/experiments/E78_registered.md` was written. Read from `industry_intelligence` and
`external_claim`, not from any report.

Status: SHADOW / advisory. `promoted` is false. Nothing here changes a score, and the
ingest check this experiment was meant to justify **is not being built**.

Corpus state: 95 industry objects ever stored, **60 active**, 35 superseded (20 of them
retired by today's completeness pass). 508 industry-object claims.

## Verdict

| | registered | measured | |
|---|---|---|---|
| **P1** | zero-SUPPORTS objects answer >= 1 fewer field, outside Industrials | 2.85 vs 2.90 mean, median **3 vs 3** | **REFUTED** |
| **P2** | zero active objects at 3-of-3 with no SUPPORTS claim | **11** | **REFUTED** |
| **P3** | separation survives conditioning on `claims >= 4` | identical to P1, n unchanged | **REFUTED** |

The proposed "reject an object with no SUPPORTS claim at ingest" check would have rejected
**eleven Financials objects that answer all three structural fields** — `diversified_banks`,
`reinsurance`, `financial_exchanges`, `insurance_brokers`, `consumer_finance`,
`custody_banks`, `asset_management_custody_banks`, `alternative_asset_management`,
`investment_banking_brokerage`, `multi_line_insurance`, `financial_data_ratings`. Five
claims each, one or two independence domains each, every structural field answered.

The confound the registration named did all the work. Pooled over all 95 objects the
relation looks overwhelming — median answered 0 for zero-SUPPORTS against 3 for the rest —
and it is entirely the 20 retired Industrials objects being bad at both things at once.
Remove them and it vanishes.

## What is actually wrong, and it is worse than the thing being tested

`stance` on industry-object claims is **a per-run labelling habit, not a property of the
evidence.**

| sector | SUPPORTS | CONTEXT | CONTRADICTS |
|---|---:|---:|---:|
| health_care | 63 | 0 | 3 |
| communication_services | 44 | 11 | 0 |
| information_technology | 22 | 4 | 0 |
| utilities | 28 | 7 | 0 |
| energy | 28 | 23 | 4 |
| real_estate | 5 | 0 | 0 |
| **financials** | **29** | **103** | 0 |
| **industrials** | **11** | **134** | 0 |

`fact_or_inference` is worse:

| sector | FACT | INFERENCE |
|---|---:|---:|
| industrials | 139 | 6 |
| information_technology | 23 | 3 |
| real_estate | 5 | 0 |
| energy | 31 | 24 |
| financials | 36 | 96 |
| health_care | 0 | 66 |
| **communication_services** | **0** | **55** |
| **utilities** | **0** | **35** |

A field that is ~100% one value in one sector and ~100% the other value in the next is not
measuring the claim. It is measuring who wrote that run. Three of eight sectors filed
**zero** FACT claims (communication_services, utilities, health_care); real_estate filed
zero INFERENCE; five of eight filed zero CONTRADICTS.

This is the **E30 symptom** — a field constant across every row — one layer down, in the
claim table, where nothing was looking for it. It is also the mechanism behind the silent
default noted while writing the E65 prompt: `research_ingest.to_claim` fills `stance` with
CONTEXT and `fact_or_inference` with INFERENCE when the payload omits them, so a run that
never set them is indistinguishable from a run that judged every claim to be context.

Contrast the **company** claim table, where the prompt asks for stance per field
explicitly: 4,818 SUPPORTS, 1,501 CONTRADICTS, 210 CONTEXT. That distribution varies. The
industry-object one does not.

## The correction this forces to a number already in circulation

The E65 IT prompt, written earlier today, told Codex that **"277 of 508 industry-object
claims are stance CONTEXT — more than half of the evidence attached to industry objects
supports nothing."**

The arithmetic is right and the reading is wrong. 237 of those 277 CONTEXT claims are the
Financials and Industrials runs, which appear never to have used SUPPORTS as a live
category at all. The number measures labelling, not evidence.

Corrected in `docs/CODEX_E65_IT_PHASE_A.md` before handover, with the original figure kept
beside the correction. The demand that Codex set `stance` and `fact_or_inference`
explicitly **survives and is now better motivated**: we cannot currently measure support
from the label, and the only way that changes is if the next run populates it deliberately.

## Second finding, not registered, reported as unregistered

16 of the 25 Financials objects carry **exactly 5 claims** (distribution: 4,4,4, then 5
sixteen times, then 6,6,6,7,7,8). That is the E54 uniform-quota shape, in a sector that
passed every other check — and the 11 P2 false positives are all drawn from that group of
5-claim objects. It was found while investigating P2 and is not a pre-registered result.

## What this does not establish

- Sector, prompt version, run and builder are **one-to-one** here — each sector's objects
  come from a single dated run. Nothing in this design separates "Financials is different"
  from "the Financials prompt was different" from "that run's builder labelled differently".
- It says nothing about whether the underlying passages support their fields. E57 is the
  standing reminder that literal verification and semantic support are different questions;
  this experiment touches neither.
- n=60 active objects, 7 sectors, one researcher. A refutation here is a refutation about
  this corpus.

## Consequences

1. **The zero-SUPPORTS ingest gate is not built.** 11 false positives on the corpus we
   have. If any warning ships it is a loud line in the ingest report, never a block.
2. **`stance` and `fact_or_inference` are not evidence-quality metrics today** and must not
   be quoted as one — including by me, in a prompt, three hours ago.
3. E65's report requirement stands: the SUPPORTS/CONTRADICTS/CONTEXT split per object is
   still worth collecting, because after an explicit-stance run it becomes measurable for
   the first time. Until then it is a baseline, not a finding.
4. The Financials uniform-5 needs its own look under B6, alongside the other overstated
   counts.

   > **Looked at 2026-09-10 under B6.** The uniform-5 was real for E54's delivery and is
   > no longer true of the live corpus: live `financials` objects now run 4:3, 5:13, 6:2,
   > 7:2, 8:1, 15:1, against 4:6, 5:23, 6:2, 7:4, 8:4, 9:4, 10:4, 11:2, 16:1 elsewhere.
   > The E56 re-cut and later work broke the zero-variance shape, so the original finding
   > stands as a fact about that ONE delivery and must not be quoted as a live property
   > of Financials. Full recount: `B6_RECOUNT_2026-09-10.md`.
