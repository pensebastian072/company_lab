# Workload with Codex live — 2026-09-09

Codex is back. **There is one Codex session and both chats need it**, so the order below
is a queue, not two parallel tracks. Everything marked LOCAL runs while Codex is busy.

State verified against the store: 6,531 claims (6,409 VERIFIED_LOCAL, 64 UNVERIFIABLE,
58 SELF_ATTESTED), 80 active industry objects, **269 companies with current research =
17.93% coverage**. Batch 2 is staged and unhanded. Tree clean at `e104f65`.

---

## THE QUEUE — who gets Codex, in order

| # | who | what | why this order |
|---|---|---|---|
| 1 | **Chat B** | Financials batch 2, already staged | It is the only thing that has been sitting idle waiting for Codex. Nothing else is blocked on it. |
| 2 | **Chat A** | IT Phase A, 10 objects | The prompt does not exist yet. Chat A writes it while Codex runs batch 2. |
| 3 | **Chat B** | Financials batch 3 | Only after batch 2 is finalized, verified and accepted. |

**Never two Phase B campaigns at once — one request file, one owner.** Chat A's Phase A
work needs no request file, so 1 and 2 do not collide; they queue only on Codex itself.

---

# CHAT B — hand batch 2 over now

Staged and verified: request `b1d3275420b64cdb92f3`, 42 companies, depth 3, citations
required, roster matches the prompt exactly, none previously researched.

```powershell
cd C:\Users\<your-user>\company_lab
$env:PYTHONPATH="C:\Users\<your-user>\company_lab"
Get-Content docs\CODEX_E59_FINANCIALS_PHASEB_B2.md      # hand this to Codex
```

## When it returns

```powershell
.venv\Scripts\python.exe -m clab.external.finalize D:\company_lab_data\external\payloads\<rid>.json --apply
.venv\Scripts\python.exe -m clab.external.verify --apply
.venv\Scripts\python.exe -m clab.external.batch_health --version <rv>
```

**Read `batch_health` BEFORE accepting the batch, not after.** Batch 1 was burned on an
ERIE/WTW peer-evidence defect that a report would not have surfaced.

Then check the store rather than the report:

- roster matched exactly — 42, nothing added, nothing substituted
- per-industry fill on the four rank-order fields, **not pooled** — they carry 45 of the
  100 external points
- every non-UNKNOWN categorical has a claim naming that field
- **a field constant across every company** is the E30 symptom and is how E53's mechanical
  `external_better` got through
- `competitive_position_trend` should mostly ANSWER here — banks file NIM, insurers
  combined ratio, managers net flows. A utilities-style 0-of-N would be a finding.

## While Codex is busy — LOCAL

**B6, the recount of overstated totals.** Answered-field counts, search counts, endpoint
coverage. Several are Chat B's own and at least two are known stale. Correct them in place
with a dated note, and **cite the corpus state** —
`CORPUS_SNAPSHOT_2026-09-09.json` on D: is the pinned reference, because the unverifiable
figure alone has been quoted as 0.077%, 0.134%, 1.607%, 1.22% and 0.980%, every one true
of a different corpus.

## Do NOT yet

**E58 arm B needs all four Financials batches.** Two of four is not the version scope, and
a partial batch is balanced rather than representative.

---

# CHAT A — write the IT prompt while Codex runs batch 2

Full brief: `docs/CHAT_A_PROMPT_2026-09-09b.md`. Two items, both startable now.

## 1. LOCAL — write up E61

`journal/experiments/E61_results.md` does not exist. E61 shipped on a decision and the
decision has no record. Use the **store's** numbers, not the receipt's — they differ:

| receipt | store |
|---|---|
| 163 claims | **145** |
| one independence domain | **three** (COMPETITOR_FILING 140, COMPANY_IR 3, REGULATOR 2) |
| 19 of 25 under eight claims | **24 of 26** |

## 2. Write the IT Phase A prompt, then hand it over when Codex frees up

```
information_technology   190 companies   10 objects needed
  application_software, communications_equipment, electronic_components,
  electronic_equipment_instruments, electronic_manufacturing_services,
  internet_services_infrastructure, ...
```

Five IT objects already exist and must not be rebuilt. Chosen over Consumer Discretionary
(27 objects) because it is the cheapest test of whether the single-domain pattern repeats
under a prompt that explicitly demands diversity.

The prompt must carry the three rules the last three Phase A rounds earned: **depth
follows the evidence** (a quota produced a defect twice), **context is not support** (E57
lost 30 of 66 claims to it, all verifying literally), and **source diversity is part of
the deliverable** (E61 is why this is a rule).

---

## The open question neither chat should answer alone

**E61 shipped with three independence domains. Health Care was retired with five.**

On evidence diversity those two decisions point in opposite directions, and E76 will
re-research Health Care against whichever standard is current. Deciding which one is the
real bar belongs to the user, and it belongs before E76 rather than after — otherwise the
re-research is measured against a standard nobody chose.

## Non-negotiables, both chats

- **Verify against the store, not the report.** Four reported numbers have been corrected
  this way, the most recent being E61's own receipt.
- Advisory / SHADOW. `promoted` is false and no code path sets it true.
- **Every count carries its corpus state.**
- A default that covers a wiring error must be loud; when a check returns zero, confirm it
  can return non-zero.
- **Rule 4** — an uncommitted change in a shared path is unowned until someone claims it.
- Corrections go beside the original number, dated, never over it.
- Closing a real defect and closing a non-defect look identical in a changelog. Say which
  — H03 was deleted as a non-defect, H04 retired as an accepted one.
