# Chat B — next prompt, 2026-09-09

You own `clab/export/`, the request flag, company batches, and the E56/E58 registrations.
You do not own `clab/external/` core. Protocol: `docs/CHAT_A_B_PROTOCOL.md`.

Batch 2 is accepted (`f1469ea`), verified against the store: 42/42, 541/541
`VERIFIED_LOCAL`, four-field fill 0.875. Financials is **172 of 257 researched, 85
remaining**.

---

## 1. Request batch 3 — roster verified against the store

All 42 still valid: none previously researched, every one resolves to an **active** object
after the gate work. ALRM remains the only blocked Financials company, on the book's
sector-data error.

```powershell
cd C:\Users\<your-user>\company_lab
$env:PYTHONPATH="C:\Users\<your-user>\company_lab"
.venv\Scripts\python.exe -m clab.external.request --symbols "AGO,AIG,ALLY,AMG,AON,AUB,BBT,BGC,BLK,BNY,BX,C,CFR,COF,COIN,DFIN,EFC,EGBN,ESNT,EZPW,FITB,HAFC,HASI,HLNE,HOOD,IBOC,KMPR,MC,MET,MRSH,MSCI,MTG,PNFP,RJF,RLI,SBSI,SLM,TRMK,TROW,USB,VIRT,WAFD" --depth 3 --sample E59-financials-phaseb-b3 --require-citation
```

17 industries, `regional_banking` the largest at 11. Announce before taking the request
file. Write the prompt from the batch-2 template and **add it to `CURRENT` in
`tests/test_codex_prompt_rules.py`** — E65 went red for exactly this omission.

---

## 2. THE FINDING — do not spend batch 3's budget on `market_share_direction`

Batch 2 returned it UNKNOWN for **42 of 42**, classified evidence-absent. Batch 1 returned
it UNKNOWN for **43 of 43**. That is **0 of 85** across both Financials Phase B batches.

Measured across every research version:

| batch | `market_share_direction` answered |
|---|---|
| E46 energy | 41/52 — **79%** |
| E49 / E51 comm services | 23/47 — **49%** |
| E44 matched | 16/40 — 40% |
| E45 rest | 13/45 — 29% |
| E47 utilities | 0/59 — **0%, registered and argued** |
| **E59 b1 + b2 Financials** | **0/85 — 0%, not argued** |

The field is **not** dead: 632 claims across the corpus cite it, and Energy answers it four
times out of five. E47's zero was correct and pre-registered — a regulated utility has no
contestable share. **Financials has no such argument.** Banks have measurable deposit
share; insurers have measurable premium share.

### And the fix already exists, unwired

`clab/external/marketshare.py` opens with:

> *"Compute `market_share_direction` from primary data instead of asking for it… It is not
> unanswerable. It is unanswerable *by reading documents*, which is what a web researcher
> does… For the largest group — regional banks — that disclosure is the FDIC Summary of
> Deposits."*

It computes deposit share from free, public, branch-level FDIC data, with acquisition
exclusion, a shared-market minimum and a coverage floor. It is written and it is tested.

**Its only importer is `tests/test_marketshare.py`. No production code calls it.**

So a module built to solve this exact problem, for this exact sector, was never connected —
and 85 Financials companies were asked for it by web research instead, and all 85 said
UNKNOWN. This is the same shape as `next_refresh_due`, which was written by two modules and
read by none until E74.

### What to do about it

- **Batch 3's prompt should tell Codex not to spend searches on
  `market_share_direction` for banks.** It is a computed field, not a researched one, and
  85 honest UNKNOWNs have already paid for that lesson.
- **Wiring `marketshare` is Chat A's** — it is `clab/external/`. Raise it; do not build it
  in your lane.
- If batch 3 returns 0/42 again without the prompt change, that is **127 consecutive
  companies** on one field and it should be registered as a finding rather than noticed a
  fourth time.

`batch_health` reported OK on both batches because it watches the four rank-order fields,
and `market_share_direction` is not one of them. That is not a bug in `batch_health` — it
is the gap between "the batch answered its scored fields" and "the batch answered."

---

## 3. Then

- **Batch 4** finishes Financials.
- **E58 arm B** is evaluable only after batch 4 — it needs the complete `research_version`
  scope, not three of four.
- **B6**, the recount of overstated totals, citing `CORPUS_SNAPSHOT_2026-09-09.json` rather
  than a bare rate.

## Non-negotiables

- Verify against the store, not the report.
- Advisory / SHADOW. `promoted` is false and no code path sets it true.
- Every count carries its corpus state.
- A field constant across an entire batch is the E30 symptom — check it every time, even
  when `batch_health` says OK.
- Rule 4 — an uncommitted change in a shared path is unowned until someone claims it.
