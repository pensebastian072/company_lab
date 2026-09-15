# Chat A / Chat B — the two-session protocol

Two Claude sessions work this repo in parallel. This is the standing convention: who owns
what, what must never be touched by two people at once, and what to paste into a fresh
session of either.

Written 2026-09-07 by A, after a day in which both sessions edited the same files in both
directions without losing work — but only because each one asked first. Every rule here is
something that was earned, not designed.

---

## Identity

| | role | holds |
|---|---|---|
| **Chat A** | **the INSTRUMENT** | `clab/external/` core — how a thing is measured, and the guarantees around it |
| **Chat B** | **the CORPUS** | `clab/export/`, staging and running company batches, buying sectors |

The split is not by file, it is by **what the work is for.** A makes the ruler honest. B
uses it and grows the book. Where they meet, the rules below decide.

---

## The three rules

### 1. The request file has exactly ONE owner, and you announce before taking it

`journal/flags/external_research_request.json` is a **single path**. Staging a request
overwrites whatever is there, and `finalize.py` requires the request to carry today's New
York date, so a clobbered request silently destroys another session's in-flight job.

It has been clobbered once already, by a stray `--symbols "CEG"` left at the end of a
command.

**B holds it by default**, because B stages company batches. Before taking it, ask; before
handing it back, say so. The correct form is the one B used:

> "About to overwrite the request file for Financials Phase B — confirm you are not using
> it. It currently holds `<id>`, which is complete and committed. If you have anything
> mid-flight that reads it, say so now and I will wait."

Phase A work needs **no** request file. Industry objects are keyed by `industry_id` and
ingested by `research_ingest`, so a Phase A lane never contends for it.

### 2. Commit only your own paths

If you must edit a file the other session holds — and you will — make the edit, **leave it
uncommitted**, and say exactly what you changed and why. The other session commits it with
their work, or overwrites you.

This ran in both directions in one day and cost nothing:

- B's `test_export_active_corpus.py` went red because of a `store.industry()` change B had
  asked A to make. A fixed the one line, left it uncommitted, explained it. B kept it.
- A's `E56_registered.md` carried a stale number after A's own dedupe fix. B corrected it
  and said so.

`git add <specific paths>` — never `git add -A` while the other session is live.

### 3. The DuckDB store is safe concurrently; the working tree is not

`ExternalStore` opens a connection per call and never holds one. The two sessions write
different tables — A writes `industry_intelligence` and instrument columns, B writes
`company_external` and reads for export. No coordination needed.

The **working tree** is the shared mutable thing, not the database.

> **Correction, 2026-09-09 (Chat A, left uncommitted under rule 2 — this file is jointly
> held).** That is true of reads, and of writes to different tables that do not overlap in
> time. It is **not** true of a long write loop. DuckDB takes a single-writer lock on the
> file, so a bulk write while the other session holds it fails **mid-loop** with
> `IO Error: ... being used by another process` and leaves a **partially applied** state
> that neither session can see from its own output. It happened that day: 134 of 212 row
> updates landed before the error, and only a re-read of the store revealed it.
>
> So: any bulk write to the store must be **idempotent and retry the lock**, and must be
> verified by reading the store back afterwards rather than trusting its own exit.

---

## Ownership, concretely

**A — the instrument**

```
clab/external/schema.py          closed vocabularies, UNKNOWN semantics
clab/external/store.py           the catalog, migrations, lifecycle columns
clab/external/applicability.py   NOT_APPLICABLE nominations (two-condition rule)
clab/external/gates.py           conviction scoring
clab/external/score.py           external quality score, coverage
clab/external/request.py         the frozen-request contract + blind-pass mechanism
clab/external/batch_health.py    coverage gauges, active-corpus definition
clab/external/revenue_share.py   computed market-share direction
docs/CODEX_STANDARD_RULES.md     the canonical rules block
tests/ for all of the above
```

**B — the corpus**

```
clab/export/                     the workbook, active_industries()
journal/flags/external_research_request.json     (default holder)
staging + finalizing company batches
experiment registration and results for B's own studies
```

**Genuinely ambiguous, pending B's ruling:** `clab/external/taxonomy.py`. It is the
instrument by the split above, but every sector's Phase A prep lands in it, which is
corpus work. Both sessions have edited it the same day for different sectors and never
actually conflicted — only sequenced. A's proposal is **whoever preps a sector edits that
sector's overrides and the other stays out of them**, since the override map partitions
naturally by sector.

---

## What a fresh session of either needs to know

### The layer, in one paragraph

Company Lab scores 1,500 companies on a 94-point framework. The **external layer**
(`clab/external/`) adds a third source of truth: competitive, sector and regulatory
evidence researched by Codex, verified locally, and scored here. Codex never produces a
number — it returns categoricals and cited claims, and the finalizer applies every gate.
Everything is SHADOW; `promoted` is false everywhere and no code path sets it true.

### The failure that shaped everything

Across eight batches the four rank-order fields — `moat_trajectory`,
`competitive_position`, `competitive_position_trend`, `company_specific_capture`, **45 of
the 100 external points** — fell from 92% filled to 0%, while every quality metric stayed
perfect.

Cause: the prompts rewarded abstention. They told Codex a well-blocked UNKNOWN was a
success and an uncited assertion was a failure, and congratulated the streak each batch.

Fix: `docs/CODEX_STANDARD_RULES.md` — one canonical block, both errors stated
symmetrically, **never quote a streak back at the researcher**. Measured: Communication
Services went 0/47 → 47/47, Utilities 8.5% → 65.7%, both with zero demotions.

Gauge: `clab/external/batch_health.py` would have caught it at batch four. Run it after
every company batch.

### Rules that are not negotiable

- **Advisory / SHADOW always.** The ranking is unvalidated: E05 measured its top decile at
  **−7.6% median 3-year excess over SPY** on a survivorship-free holdout, and E03 measured
  **95.6% of its ranking power as sector selection**. Never write a claim that it works.
- **Absent data is `NO_DATA`, never `0`.** UNKNOWN is not the bottom of a scale.
- **Verify against the store, not the report.** Reports have been wrong twice — both times
  while otherwise accurate.
- **A default that covers a wiring error must be loud.** This repo has been bitten by
  graceful degradation five times now, most recently `gates.criteria()` silently scoring 0
  for missing evidence inputs, which corrupted an A/B twice before anyone noticed.
- Bulk data on `D:` (C: is a failing spinner). `.venv\Scripts\python.exe`, never bare
  `python`. Commit with the `-c user.email/-c user.name` form and `-F`, never `-m`.

### Current state — 2026-09-07

```
sector                    done  total  objects left   ext sd
communication_services      47     47        0        13.85
energy                      71     71        0        13.22
utilities                   59     59        0        10.87
financials                  87    257        1         9.56
information_technology      15    190       11         9.38
health_care                  0    163        0            -
real_estate                  2    105       14            -
industrials                  4    263       25         8.39
consumer_discretionary       0    193       27            -
consumer_staples             0     75       11            -
materials                    0     77       16            -

285 of 1,500 companies researched     66 active industry objects
claims: 5,227 VERIFIED_LOCAL, 60 SELF_ATTESTED, 4 UNVERIFIABLE (0.08%)
```

> **Dated correction (2026-09-07):** this snapshot predates PDF extraction-state and
> numeric-quote guards. The corrected corpus tally is 5,169 VERIFIED_LOCAL, 58
> SELF_ATTESTED, 64 UNVERIFIABLE (64/5,233 checked = 1.22%). See
> `journal/experiments/verification_rate_correction_2026-09-07.md`.

Three sectors complete and all three discriminating. Health Care has all 11 objects built
and **zero companies researched** — Phase B there is the largest unstarted lane.

---

## Working the two chats

The user drives both. Each session reports what it did and what it needs; the user pastes
between them when a decision belongs to the other side. Sessions also message each other
directly, and should — a peer message costs a round trip and has twice caught a defect the
other session had already committed.

**When a session finishes a piece of work, its report should say:** what landed, what it
verified against the store, what it left uncommitted in the other's files, and what the
other session is now unblocked or blocked on. That last one is the part that makes the
parallelism worth its overhead.

**Do not** ask the peer to do something your own permissions refused. That is laundering,
and it routes back to the user instead.
