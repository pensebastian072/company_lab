# When a Codex run comes back — receive, verify, record, queue the next

Both A and B are running in Codex. This is what to do with what they return, and what the
next run is. Written as a checklist because the failure mode is skipping a step that looks
redundant.

**The one rule above the others: verify against the STORE, never the report.** Reports have
been wrong twice here, and both times they were otherwise accurate — the errors were in the
half nobody spot-checked. A delivered report is a claim about the store, not the store.

`<rid>` = request_id. `<rv>` = research_version.

---

## CHAT B — Financials Phase B batch 1 returns

### 1. Receive

```powershell
cd C:\Users\<your-user>\company_lab
$env:PYTHONPATH="C:\Users\<your-user>\company_lab"
.venv\Scripts\python.exe -m clab.external.finalize D:\company_lab_data\external\payloads\<rid>.json --apply
.venv\Scripts\python.exe -m clab.external.verify --apply
.venv\Scripts\python.exe -m clab.external.batch_health --version <rv>
```

`batch_health` is not optional and is read BEFORE accepting the batch. It exists because
eight batches passed every quality metric while the four rank-order fields fell 92% → 0%,
and nothing was watching the coverage side.

### 2. Check the store, not the report

- Company count matches the frozen roster exactly — 43, no additions, no substitutions.
  The finalizer refuses off-roster tickers; confirm it had nothing to refuse.
- Verify tally, and the corpus rate against **1.607%** (not 0.077%, which is the stale
  pre-fix figure still sitting in three journals).
- Fill rate on `moat_trajectory`, `competitive_position`, `competitive_position_trend`,
  `company_specific_capture` — **per industry**, not pooled. These carry 45 of the 100
  external points.
- Every non-UNKNOWN categorical has a claim naming that field.
- `competitive_position_trend` should mostly be ANSWERED here. Financials is the good case
  — banks file NIM and efficiency ratio, insurers combined ratio, managers net flows. A
  utilities-style 0-of-N would be a finding, not a pass.
- **Watch for a field constant across every company.** That is the E30 symptom and it is
  exactly how E53's mechanical `external_better` got through.

### 3. Record

Write `journal/experiments/E59_results.md`. Include what the batch does NOT establish.

**E58 arm B is NOT read off batch 1.** A partial batch is balanced, not representative. It
waits for the full `research_version` across all four batches.

Also still owed and unwritten: **E58 arm A**, REFUTED at exactly the registered boundary
(1 of 10 answered Health Care objects used a scale end, 0.10 against "below 0.10"). Say
that the verdict turns on one object — had biotechnology come back HIGH it would be 0/10
and CONFIRMED.

### 4. Queue the next run

Batch 2 of 4. The stratification already exists; build the request, write the prompt from
the batch-1 template, hand over.

```powershell
.venv\Scripts\python.exe -m clab.external.request --symbols "<batch 2>" --depth 3 `
  --sample E59-financials-phaseb-b2 --require-citation
```

**Announce before taking the request file.** One path, one owner, and it was clobbered once
by a stray `--symbols`.

---

## CHAT A — a Phase A object run returns

### 1. Receive

```powershell
.venv\Scripts\python.exe -m clab.external.research_ingest --apply
.venv\Scripts\python.exe -m clab.external.verify --apply
```

`research_ingest --apply` rewrites **every** industry and sector object from disk, not just
the new ones. So hash the pre-existing rows before and after and prove they did not move —
that check has already caught nothing twice, which is the point of it being cheap.

### 2. Check the store, not the report

- Every expected object present, correct `sector_id`, and **none of the ids is a typo** — a
  misspelled `industry_id` creates an orphan object that no company resolves to, and it
  looks like success.
- Claim counts and independence domains per object.
- Corpus unverifiable rate still ~1.607%.
- Every non-UNKNOWN structural field has a claim naming it.
- SUPERSEDED rows still SUPERSEDED after the re-ingest.
- **`external_claim.industry_id` is populated on COMPANY claims too**, so filter object
  claims on a null ticker or the counts overstate the object's evidence.

### 3. Record, then queue

E57's Health Care write-up is still owed. Then Industrials Phase A (E61) — 25 objects, the
largest object build remaining.

**Phase A must land and verify before that sector's Phase B is requested.** A company
researched against a wrong object has to be re-researched; E56 cost five objects instead of
170 companies precisely because the re-cut happened first.

---

## Both, every time

- **Rule 4.** An uncommitted change in a shared path is unowned until someone claims it.
  Do not run it against live data, do not commit it — ask. Codex edited `verify.py` and
  Chat A ran it against the live store assuming it was Chat B's.
- **Codex writes payloads; the local finalizer applies the gates.** If a returned run has
  edited gate code, that is a boundary crossing to report, whatever the code quality.
- Corrections go **beside** the original number, dated, never over it.
- A registered threshold does not move after the data lands. If the realized n made it
  stricter than intended — as it did for P3 and again for E58 arm A — report that with the
  verdict.
- Advisory / SHADOW. `promoted` is false and no code path sets it true.
- Run the full suite before committing. Commit per item.

## Known-stale, do not propagate

Three journals — `E54_results.md`, `E56_registered.md`, `E56_results.md` — carry a
corrected verification rate of **0.134%**. The store says **1.607%**. Codex wrote those
notes, so under Rule 4 they are unowned and wait for the user. Do not quote 0.134% or
0.077% in anything new.
