# Chat A / Chat B continuation prompts — 2026-09-09

Paste one into the relevant session. Protocol: `docs/CHAT_A_B_PROTOCOL.md`. Roadmap:
`docs/ROADMAP_TO_E75.md`. These supersede the 2026-09-08 briefs.

## State, verified against the store rather than reported

```
claims                6,393
industry objects         70 total - 55 ACTIVE, 15 SUPERSEDED
  superseded            11 health_care (B4), 3 financials, 1 energy
companies researched    328 of 1,500 (21.9%)
```

Active objects by sector: financials 22, communication_services 11, energy 8,
utilities 7, information_technology 5, industrials 1, real_estate 1.
**Health Care has zero active objects.**

## Decision taken 2026-09-09 — Health Care goes to the END

The 11 Health Care objects were retired for B4 (mechanical cross-field receipt reuse).
The evidence is real — all 66 claims are still `VERIFIED_LOCAL` across 31 URLs and 5
independence domains — but the field assignment is a quota: exactly **11 claims per field
across 6 fields**, one per object per field. `replication_difficulty` has **zero direct
support in all 11 objects** and 9 of 11 assignments are about a different economic unit.

**Health Care re-research is E76, scheduled at the END of the coverage run, not now.**

**Consequence, stated rather than buried: the book is no longer complete at E75.** 163
Health Care companies — 11% of the book — stay unresearched through E75, and their Phase B
follows the re-research. Exit criterion 1 is met at **E77**, not E75. Everything else in
the roadmap still lands at E75.

---

# CHAT A — THE INSTRUMENT

You own `clab/external/` core, the measurement guarantees, and sector Phase A prompts. You
do not own `clab/export/`, the request flag, company batches, or the E56/E58 registrations.

## 1. Decide E61 before ingesting it

E61 built 25 Industrials objects and passed `research_ingest` dry-run with zero skips. It
is **not in the store**, and that is the right moment to decide it.

The receipt says plainly: `Independence-domain counts: {'COMPETITOR_FILING': 163}`,
`Distinct source hosts: 1`. **Every retained claim is an SEC filing.** Also **19 of 25
objects carry fewer than eight claims** and four rest on fewer than three organizations.

`research_ingest` already flags single-domain objects one at a time; this is an entire
sector at once, and 259 companies — the largest sector in the book — will be researched
against it. Compare with the retired Health Care batch, which had 5 independence domains
and was still retired for evidence quality.

Either ship it with the limitation recorded in the E61 results, or send it back for source
diversity. **Do not ingest without deciding, and write the decision down either way.**

## 2. Then Phase A for the next sector

Consumer Discretionary (27 objects, most of any sector) or Information Technology (11
objects, smallest remaining). IT is the cheaper way to test whether the E61 single-domain
pattern repeats under a prompt that asks for diversity.

Whichever you build, the prompt must carry the anti-quota rules the last two Phase A rounds
earned:

- **Evidence depth follows the evidence.** A uniform claim count across objects with very
  different literatures is a quota, and it has now produced a defect twice — E54's uniform
  5, and E57's one-claim-per-field.
- **Context is not support.** A passage that is relevant to an industry but does not
  establish the specific field does not back that field. E57 lost 30 of 66 claims to
  exactly this, and they all verified literally.
- **Source diversity is part of the deliverable.** Say what a single-domain object costs.

## 3. E76 — Health Care re-research, at the END of coverage

Yours, scheduled last. Keep the **11 direct-support claims as seeds** so the work is not
repeated: 4 in `structural_growth`, 4 in `regulatory_trajectory`, 2 in `market_structure`,
1 in `substitution_risk`. `replication_difficulty` and `key_metrics` have none and start
clean.

## 4. A rule the last three retirements earned

E53 utilities, E59 batch 1 and E57 health care were all retired with
**`superseded_by = None`**. E53's fallback silently regressed 59 companies from 65.7% to
8.5% fill on the four rank-order fields. Health Care fails safe only because there is no
older arm to fall back to.

**A retirement with no replacement must state what it costs before it lands.** All three
may be right calls; all three were made as bug fixes and measured afterwards by the other
session.

---

# CHAT B — THE CORPUS

You own `clab/export/`, the request flag, company batches, and the E56/E58 registrations.
You do not own `clab/external/` core.

## 1. Hand Financials Phase B batch 2 to Codex

Staged and verified: request `b1d3275420b64cdb92f3`, 42 companies, depth 3, citations
required, prompt roster matches the request exactly, none previously researched. Prompt at
`docs/CODEX_E59_FINANCIALS_PHASEB_B2.md`.

On return:

```powershell
cd C:\Users\<your-user>\company_lab
$env:PYTHONPATH="C:\Users\<your-user>\company_lab"
.venv\Scripts\python.exe -m clab.external.finalize D:\company_lab_data\external\payloads\<rid>.json --apply
.venv\Scripts\python.exe -m clab.external.verify --apply
.venv\Scripts\python.exe -m clab.external.batch_health --version <rv>
```

`batch_health` is read **before** accepting, not after. Batch 1 was burned on a peer defect
a report would not have surfaced. Check the store: roster matched exactly, per-industry
fill on the four rank-order fields, every non-UNKNOWN categorical backed by a claim naming
that field, and watch for a field constant across every company — the E30 symptom.

## 2. Batches 3 and 4, then E58 arm B

The stratification exists. **Arm B is evaluated only when all four Financials batches are
in** — not on two of four, not on the old 87.

When you do write it up, record that **arm A's field, `replication_difficulty`, had zero
direct support in the Health Care batch it was measured on.** Arm A stays REFUTED; that is
a second reason it cannot carry weight, alongside the verdict turning on one object.

## 3. Then B6, earnings_watch, B7/B8

B6 is the recount of overstated totals — answered-field counts, search counts, endpoint
coverage. Several are yours and at least two are known stale.

---

## Both sessions

- **Rule 4.** An uncommitted change in a shared path is unowned until someone claims it.
  Do not run it against live data, do not commit it — ask.
- **Every count carries its corpus state.** The UNVERIFIABLE company count has been quoted
  as 28, 27 and 24; the verification rate as 0.077%, 0.134% and 1.607%. All true at
  different moments. Chat A's A1 doc does this correctly — pinned to a receipt with a
  SHA-256 and the tally beside it.
- Verify against the store, not the report. Both sessions have now caught real defects in
  the other's reported work by doing this.
- Advisory / SHADOW. `promoted` is false and no code path sets it true.
