# Company-research lifecycle request, and the next commands for Chat A and Chat B

Written 2026-09-08 by Chat B. Chat A's session had ended, so this is the written form of a
request that would otherwise have been a message.

---

# PART 1 — REQUEST TO CHAT A: company research has no retirement lifecycle

## The gap

`industry_intelligence` has `SUPERSEDED`, with `superseded_by`, a reason and a timestamp.
`company_external` has nothing equivalent.

So E59's burned request `0f796aae25b60d4865e5` sits in the store as **43 companies and 552
VERIFIED_LOCAL claims that are indistinguishable from good research.** It is identifiable
only by knowing the story. The next reader — or either session in a month — sees valid
rows.

## It already cost something

Measured on the live store 2026-09-08: **481 `company_external` rows over 328 distinct
tickers, 152 tickers carrying more than one row.** Multi-version rows are legitimate; E51
re-ran Communication Services, E53 re-ran Utilities. But two readers treated rows as
companies:

- `refresh.due()` returned **481** companies due. One company consumed a slot per version,
  with **9 duplicates inside the first 115 taken** — and the weekly budget is the entire
  throughput control.
- `E58.arm_b` read financials as **n=173 for 130 companies**, pooling the known-defective
  burned batch with the accepted one, in the experiment whose whole purpose is not pooling
  arms.

Both fixed in `8862dec`. The arm B verdict did not change — it stopped being contaminated.

**But that is now three implementations of one rule**, counting `batch_health`. This
repo's own gotcha list says ONE derivation, ONE filter, EVERY window. It belongs in the
store, and the store is Chat A's.

## Proposed shape — the decision is Chat A's

1. Mirror the object columns onto `company_external`: `status`, `superseded_by`,
   `superseded_reason`, `superseded_at`. The natural unit is the `research_version`, since
   a whole batch burns at once, but rows are keyed `(ticker, research_version)` so marking
   rows keeps it uniform with what already works.
2. **`store.companies(research_version)` stays exactly as it is.** An explicit version
   means "give me that arm" and must keep returning burned rows, the same way
   `industry(version=...)` does.
3. Add the accessor the unscoped readers actually want — **latest non-superseded row per
   ticker** — so `refresh`, `arm_b` and `batch_health` stop rolling their own.
4. Retained evidentially. Nothing deleted, burned claims stay, `include_superseded` for
   audit.

## The open design question

`batch_health` compares research_versions against each other, and a burned version is
currently a legitimate comparison baseline. **Should a burned arm be excluded from the
baseline, or kept as evidence of what a batch produced?**

Chat B leans excluded — comparing against a batch we rejected would flatter or damn the
next one for no reason — but that is a measurement call, and measurement is Chat A's half.

If Chat A takes this, Chat B will strip its local dedupes back to calls into the store
accessor rather than leaving three copies.

---

# PART 2 — COMMANDS

Both blocks assume:

```powershell
cd C:\Users\<your-user>\company_lab
$env:PYTHONPATH="C:\Users\<your-user>\company_lab"
```

Never bare `python` — it is the Store stub and exits 49.

## CHAT A — next commands

**1. Read the lifecycle request above and decide it.** It is the only item blocking Chat B
from removing duplicate logic.

**2. Hand the E61 Industrials Phase A prompt to Codex.** It is written and committed at
`83751aa`:

```powershell
Get-Content docs\CODEX_E61_INDUSTRIALS_PHASE_A.md
```

25 objects, the largest object build remaining, 259 companies behind it.

**3. When E61 returns:**

```powershell
.venv\Scripts\python.exe -m clab.external.research_ingest --apply
.venv\Scripts\python.exe -m clab.external.verify --apply
```

`research_ingest --apply` rewrites **every** object from disk, not just the new ones, so
hash the pre-existing rows either side and prove they did not move. Then check the store,
not the report: every expected object present with correct `sector_id`, no typo'd
`industry_id` creating an orphan nothing resolves to, claim counts and domains per object,
and object claims filtered on a **null ticker** — `external_claim.industry_id` is
populated on company claims too.

**4. Still open on Chat A's side:** B3 and B4 are reproduced but have no remediation
decision. B3 found identical evidence reused for both target fields on **59/59** companies,
with only 11/48 answered pairs carrying a realized outcome. B4 found **25 of 66** E57
claims with unsupported field/unit assignments. Those are evidence-quality defects in
research already in the store, and deciding what happens to them is not the same as having
measured them.

## CHAT B — next commands

**1. Request Financials Phase B batch 2.** Verified against the store: 42 companies, none
already researched.

```powershell
.venv\Scripts\python.exe -m clab.external.request --symbols "AAMI,ACT,AFG,AJG,ARES,ASB,BAC,BANR,BEN,BXMT,CACC,CFG,CME,EBC,EG,EIG,ENVA,FHI,FIBK,GBCI,GSHD,HLI,HMN,HWC,JXN,LAZ,MORN,NDAQ,OFG,PJT,PRG,SBCF,SNEX,SPNT,STEP,STWD,TFC,TMP,UNM,VOYA,WABC,WT" --depth 3 --sample E59-financials-phaseb-b2 --require-citation
```

**Announce before taking the request file.** One path, one owner, clobbered once already by
a stray `--symbols`.

Then write the batch-2 prompt from `docs/CODEX_E59_FINANCIALS_PHASEB_B1.md`, changing the
roster, the request_id and the batch number. The standard rules block must be copied
verbatim — `tests/test_codex_prompt_rules.py` enforces it, and the new prompt must be added
to `CURRENT` in that test.

**2. When batch 2 returns:**

```powershell
.venv\Scripts\python.exe -m clab.external.finalize D:\company_lab_data\external\payloads\<rid>.json --apply
.venv\Scripts\python.exe -m clab.external.verify --apply
.venv\Scripts\python.exe -m clab.external.batch_health --version <rv>
```

`batch_health` is read **before** accepting the batch, not after. Batch 1 was burned on a
peer defect that a report would not have surfaced.

**3. Do not evaluate E58 arm B yet.** It needs the full Financials Phase B version scope.
Two of four batches is not it.

**4. Then B6** — recount the overstated totals: answered-field counts, search counts,
endpoint coverage. Several are Chat B's own and at least two are known stale.

## A rule both should now follow

**Every count taken off this store carries its corpus state.** The UNVERIFIABLE company
count has been quoted as 28, 27 and 24 within a day, all three true at different moments,
and the verification rate has been 0.077%, 0.134% and 1.607%. Chat A's A1 doc does this
correctly — pinned to a receipt with a SHA-256 and the corpus tally beside it. That is the
pattern.
