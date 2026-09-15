# Chat B — next prompt, 2026-09-10 (Codex is out of tokens)

You own `clab/export/`, the request flag, company batches, and the E56/E58 registrations.
You do not own `clab/external/` core. Protocol: `docs/CHAT_A_B_PROTOCOL.md`.

**Chat A is live and committing.** Three commits landed on top of Chat B's during this
session (`544f14c`, `9a07f9d`, `1ffa923`). `git add <specific paths>` only — never
`git add -A`.

State verified against the store, not a report, and pinned at
`external/reports/CORPUS_SNAPSHOT_2026-09-10.json`:

| | |
|---|---:|
| claims | 7,223 — 7,099 `VERIFIED_LOCAL`, 65 `UNVERIFIABLE`, 59 `SELF_ATTESTED` |
| unverifiable rate (checked claims) | 0.907% |
| companies with current research | 311 of 1,500 = **20.73%** |
| company rows / tickers any arm | 523 / 370 (59 tickers hold only retired arms) |
| industry objects | 109 total, **74 live** |
| Financials | **172 of 257 researched**, 85 remaining (42 staged as b3, 42 in b4, ALRM blocked) |

Regenerate any of that with `scripts\corpus_snapshot.py` rather than quoting a bare rate.
That script is new today and exists because the unverifiable figure alone has been quoted
as 0.077%, 0.134%, 1.607%, 1.22% and 0.980% — every one true of a different corpus.

---

## 1. Batch 3 is staged, valid today, and NOT handed over

Request `9e243401d2fb0d1e380e`, sample `E59-financials-phaseb-b3`, 42 companies, depth 3,
citations required. It was staged 2026-09-09 20:18 **New York**, which is not a New York
date the finalizer accepts, so it was rebuilt today (`1741e77`). The rebuild returned the
**same** `request_id`, `spec_fingerprint` and `roster_sha1` — the id hashes
roster+depth+spec+sample and not the timestamp — so the roster is byte-identical and not
merely the same list of tickers.

Prompt, unchanged and date-free: `docs\CODEX_E59_FINANCIALS_PHASEB_B3.md`.

**Codex has no token budget, so do not hand it over on a budget that cannot finish today.**

### The gate that has now killed two batches out of three

`finalize.check_request` compares the request's `generated_at`, converted to New York,
against today in New York. Not an age window — the DATE.

- b2 was staged 09-08 and had to be rebuilt on 09-09.
- b3 was staged at 00:18Z on 09-10, which is 20:18 on 09-09 in New York, and was dead
  before Codex opened it.

The part that is not obvious: **a request staged in the evening dies at New York midnight
while the batch is still running.** Staging is not the deadline; `finalize --apply` is.

So the rule for handing this over:

1. Stage in the **morning** New York, not the evening.
2. Hand over only when Codex can both research and return the payload the same NY day.
3. If it slips, re-stage — one command, same id, `store.begin` is idempotent on
   `request_id`, and nothing in the store has to be unwound. The b3 manifest row sat at
   `pending` with 0 returned and zero rows in `company_external` the whole time.

### When it does return

```powershell
cd C:\Users\<your-user>\company_lab
$env:PYTHONPATH="C:\Users\<your-user>\company_lab"
.venv\Scripts\python.exe -m clab.external.finalize D:\company_lab_data\external\payloads\9e243401d2fb0d1e380e.json --apply
.venv\Scripts\python.exe -m clab.external.verify --apply
.venv\Scripts\python.exe -m clab.external.batch_health --version 2026-09-1X+E59-financials-phaseb-b3
```

Read `batch_health` **before** accepting, then check the store rather than the report:
roster matched exactly at 42, per-industry fill on the four rank-order fields and not
pooled, every non-UNKNOWN categorical backed by a claim naming that field, and a field
constant across the whole batch treated as the E30 symptom.

`market_share_direction` will be UNKNOWN for the 11 regional banks **by instruction** —
the b3 prompt tells Codex not to spend searches on it. That is the intended outcome of
0-of-85 across b1 and b2, not a new failure. `competitive_position_trend` should mostly
ANSWER here; a utilities-style 0-of-42 would be a finding.

---

## 2. Batch 4 — roster computed, DO NOT stage yet

Financials closes at 42 more. Computed today from the book minus everything with current
research, minus b3, minus ALRM, and it lands exactly on 42 with 257 − 172 − 42 − 42 = 1
left over, which is ALRM:

```
AIZ AMP AMSF AXP BANC BHF BKU BRO CG CHCO CNS DAVE EVR FCF FCFS FDS FLG HOPE IBKR ICE
IVZ JPM L LKFN MS NLY NMIH NTRS PFG PRK RGA RYAN SCHW SFNC SPGI SYF TRST TRV VCTR WAL
WD WFC
```

All 42 resolve to a live industry object (checked with `store.industry()`, which is
`superseded_at IS NULL` — **do not filter on the `status` column, it is NULL on all 109
rows** and a `status='active'` filter silently returns zero). Seventeen industries, same
shape as b3: `regional_banking` 11, then asset management / consumer finance / investment
banking at 4 each. One new one against b3 — `commercial_mortgage_banking_servicing` (WD).

**One request file, one owner.** b3 holds it. Staging b4 overwrites b3 and destroys it.
Announce before taking it, in the form rule 1 gives.

---

## 3. LOCAL, while Codex is dark

1. **B6 — the recount of overstated totals.** Answered-field counts, search counts,
   endpoint coverage. Several are Chat B's own and at least two are known stale. Correct
   them in place with a dated note and cite `CORPUS_SNAPSHOT_2026-09-10.json`. The
   09-09 snapshot it was told to cite is itself now stale: the corpus moved 6,531 → 7,223
   claims and 269 → 311 companies while it was the pinned reference.
2. **Write up the b3 re-stage** in `journal/experiments/E59_results.md` when b3 lands,
   including the receipt-time rebuild, the way b2's entry records it.
3. **Not yours:** wiring `clab/external/marketshare.py` is Chat A's lane. Chat A registered
   the computed-field finding at `1ffa923`
   (`journal/experiments/MARKET_SHARE_DIRECTION_2026-09-09.md`). Raise it, do not build it.

## Do NOT yet

**E58 arm B needs all four Financials batches.** Three of four is not the version scope,
and a partial batch is balanced rather than representative. No threshold moves on a
partial population.

## Non-negotiables

- Verify against the store, not the report.
- Advisory / SHADOW. `promoted` is false and no code path sets it true.
- Every count carries its corpus state.
- A field constant across an entire batch is the E30 symptom — check it every time, even
  when `batch_health` says OK.
- Bulk writes to the store must be idempotent, retry the lock, and be verified by reading
  the store back. DuckDB is single-writer and a failed loop leaves a partial state that
  the failing session cannot see from its own output.
