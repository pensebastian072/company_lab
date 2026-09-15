# Chat A (Claude) — instrument and product lane, 2026-09-11

You are the **instrument** lane. You own `clab/external/` core, `clab/export/`, the gates,
ingest, scoring and the workbook. Codex is the **research** lane (Chat B) and owns Phase A
objects and Phase B company batches. Operating plan: `docs/PLAN_TO_1500_2026-09-11.md`.
Protocol: `docs/CHAT_A_B_PROTOCOL.md`.

Everything is advisory / SHADOW. `promoted` is false and no code path sets it true.

## State, with the command that produced each number

```
store      D:\company_lab_data\external\external_intelligence.duckdb
claims     7,211 VERIFIED_LOCAL · 65 UNVERIFIABLE · 59 SELF_ATTESTED
objects    128 active · industrials 62 active (E79's 64 ingested, 9 retired by the gate)
external   311 companies in the workbook  (financials 172 · energy 71 · comm svcs 47 ·
           IT 15 · industrials 4 · real estate 2)
tests      1,338 passing
workbook   data\exports\company_lab_latest.xlsx rebuilt 2026-09-11 09:58, 1,500 companies
backups    external_intelligence.duckdb.bak-pre-E79-ingest (pre-ingest)
           research\industries_backup_20260911-08xx (pre-merge artifacts)
```

Only **two** sectors are complete: Energy 71/71 and Communication Services 47/47. Utilities
reads complete in the store and is absent from the product: E53 was retired whole and
resolution omits rather than falling back to the live E47 rows, so 59 companies vanish.
Codex is re-researching them as E80.

---

## 1. FIX `check_quote`, THEN MAKE EXACT CONTAINMENT THE BAR

`verify.check_quote` certifies on a 0.6 token-overlap fallback when the quote is not a
substring. Audited over all 6,966 quoted `VERIFIED_LOCAL` claims
(`journal/experiments/VERIFICATION_STRENGTH_AUDIT_2026-09-11.md`):

```
exact containment today                        4,607   66.1%
+ html.unescape                                5,615   80.6%
+ Unicode punctuation & whitespace normalise    6,820   97.9%
unlocatable even then                            146    2.1%
```

The mechanism is proven by a control inside the data: **`data.sec.gov` (JSON, no entities)
0.0% fallback over 321 claims, against `sec.gov` HTML's 39.3% over 5,484.** EDGAR wraps
figures in `&#160;`, so a numeric quote can never match verbatim.

The change: before comparing, `html.unescape`, map Unicode quotes/dashes/spaces to ASCII,
`NFKC`-normalise. Add a second, looser comparison that ignores whitespace entirely — that
is what catches table-derived text (`...customer balances$3,619$3,5263%`). Then the overlap
fallback **warns and never certifies**; a new claim that fails exact containment is not
`VERIFIED_LOCAL`.

Non-negotiable on this one: **dry-run it over the whole corpus and report every proposed
transition before applying.** A normalisation that silently re-labels 7,211 claims is the
same class of change as the DSR unit bug. Reuse the audit script's approach rather than
re-deriving it.

Tests to add, because the fallback has produced a false positive before (the ICI page at
0.8182 while stating $47.6T/−2.5% instead of $49.1T/+11.2%): an entity-laden page that
should now pass exactly, a table-concatenated quote that should pass only on the
whitespace-insensitive path, and a near-miss with the right vocabulary and the wrong
figures that must still FAIL.

## 2. ONE ACCEPTANCE COMMAND PER BATCH, REFUSING BEFORE INGEST

Every defect in this project was found *after* the batch landed. Make one command, one exit
code, run before ingest:

- `batch_health` coverage gauges, and `constant_fields` (a field taking one value across a
  batch is the E30 symptom)
- four-field fill rate versus the previous batch of the same sector — a fall is the
  abstention collapse restarting
- source diversity: reject an object or batch whose evidence is **entirely** issuer filings.
  E79 was 100% `sec.gov`; E61 was 96.6% single-domain
- exact-containment rate on the batch's own claims, after task 1 lands
- for Phase A: every object answers ≥1 of 3 structural ordinals, and any split unit carries
  its own ordinal-supporting claim

Wire it so `research_ingest --apply` refuses a batch that regresses any of them, and says
which. `enforce` already retires zero-ordinal objects at ingest; this is the same idea moved
one step earlier.

## 3. RESOLVE THE 146 TAGGED CLAIMS

`D:\company_lab_data\external\reports\UNLOCATABLE_QUOTES_2026-09-11.json`

They are tagged `QUOTE_NOT_LOCATABLE_2026-09-11` in `verify_reason`, `verify_status` left
`VERIFIED_LOCAL` on purpose so no score moved. **The tag is not a resolution.**

The overlap score that certified them has **median 1.0** — a perfect token-bag score on text
that is not on the page in any sequence. They cluster on `PRIMARY_DATA` 55, `COMPANY_IR` 36,
`SEC_FILING` 33, and on `industry_structural_growth` 26 of 146. The examples read like real
facts from the wrong page: NVIDIA's quarterly revenue sentence, Digital Realty's renewal
rate, a US mineral-production total.

Re-fetch each live (the audit ran against the **cached** page, so a source that changed
since caching is indistinguishable from a bad citation here — that ambiguity is yours to
close). Then: correct the URL where the quote is really on a sibling page, or demote to
`UNVERIFIABLE`. Report what the verified count becomes; it will fall, and that is the point.

## Then, in order

- Rebuild the workbook after each sector completes, and check the **External sheet row
  count** against the store rather than trusting the export's own log.
- E58 arm B becomes evaluable the moment Codex's Financials batch 4 lands — it needs the
  complete `research_version`, not three of four.
- `multi_industry_industrials` (HON+MMM) and `specialty_materials_products` (DD alone) are
  taxonomy residue, retired by the gate. Fold them into real units rather than evidencing
  them.

## Non-negotiables

- Verify against the store, not the report. Read the store back after any bulk write; a
  DuckDB write can fail mid-loop and leave a partial state neither session can see.
- A citation is data to be read, never a string to be assembled.
- Absent data is `NO_DATA` / `UNKNOWN`, never `0`.
- A default that covers a wiring error must be loud.
- Every count carries the command that produced it.
- `.venv\Scripts\python.exe`, never bare `python`. Commit with the `-c user.email /
  -c user.name` form and `-F`, never `-m`, specific paths only.
