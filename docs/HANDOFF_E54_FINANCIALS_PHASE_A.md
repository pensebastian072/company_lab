# Handoff — E54 Financials Phase A (parallel session)

For a second Claude Code session running E54 **while E53 runs in this one.** Read this
whole file before touching anything; the collision risk in §2 is the one that can destroy
another job's work.

Repo: `C:\Users\<your-user>\company_lab`. Head at handoff: `cfe83d8`, **1138 tests pass**,
working tree clean.

---

## 1. What E54 is

Build the **15 missing Financials industry objects.** That is the whole job. No company
research, no scoring, no export.

Financials is the largest sector in the book — 257 companies, 87 already researched, 170
remaining — and it is the highest-leverage target left: 15 objects unblock 170 companies.
Three of its objects already exist (`regional_banking`, `life_insurance`, `pc_insurance`)
and must **not** be rebuilt.

The Codex prompt is written and ready: **`docs/CODEX_E54_FINANCIALS_PHASE_A.md`** is where
it should live; if it is not on disk yet, it was pasted into chat in the session that
created this handoff — recover it from there or rebuild it from §4 below.

---

## 2. THE COLLISION RISK — READ THIS FIRST

**`journal/flags/external_research_request.json` is a single path and E53 owns it.**

It currently holds `f92abdf0887e91cd072d` — the 59-company Utilities re-run. Codex is
reading that file. If you run `clab.external.request` for any reason, it **overwrites that
file** and destroys the other job.

This has already happened once in this project: a stray `--symbols "CEG"` left in a command
clobbered a live 59-company request. Do not repeat it.

**E54 needs no request file at all.** Phase A writes industry objects, which are keyed by
`industry_id` and ingested by `clab.external.research_ingest`. There is no roster, no
frozen request, no finalizer, no `request_id`.

So:

```
DO NOT run  clab.external.request           (any flags, any reason)
DO NOT run  clab.external.finalize
DO NOT touch journal/flags/external_research_request.json
DO NOT run  clab.external.score --apply     (E53 will rescore utilities when it lands)
```

Both jobs write to the same DuckDB (`D:\company_lab_data\external\external_intelligence.duckdb`)
but to **different tables** — E54 writes `industry_intelligence` and `external_claim`
rows tagged with an `industry_id`; E53 writes `company_external`. The store opens a
connection per call and never holds one, so concurrent writes are safe.

---

## 3. Taxonomy decisions already made — do not undo them

Committed in `cfe83d8` with tests pinning each. If Codex's report argues one is wrong,
**bring it back rather than acting on it** — these were made on business logic and the
research may legitimately overturn them, but that is a decision, not a cleanup.

| split | why |
|---|---|
| `custody_banks` (BNY, NTRS, STT) out of `asset_management_custody_banks` | They are banks: deposits, securities portfolio, NII, deposit betas, CET1, assets under custody, and the Fed. An asset manager is AUM / net flows / fee rate and the SEC. |
| `alternative_asset_management` (APO, ARES, BX, CG, KKR) out of the same bucket | Fee-related earnings, carried interest, permanent capital, and increasingly an insurance balance sheet. APO and KKR are substantially insurers attached to an origination engine. |
| `financial_exchanges` vs `financial_data_ratings` | Volumes / capture rate / open interest / clearing on one side; subscriptions, retention and debt-issuance volumes on the other. SPGI and MCO move with the credit cycle, not trading volume. |

**Knowingly left incoherent:** `multi_sector_holdings` (BRK-B, JEF, VOYA) — a
conglomerate, an investment bank and a retirement insurer. Splitting makes three
singletons, which is the worse trade. Codex is told its `market_structure` must say the
bucket does not describe one business, and that UNKNOWN is correct if a shared answer
would be fiction. `specialized_finance` (CACC, HASI, EFC) may be the same case and Codex
is asked to judge it.

**Excluded from scope:** `application_software` (1 co), `diversified_capital_markets` (1),
`diversified_financial_services` (1). The first is a data error on our side — ALRM is
Alarm.com, home security software, miscarried into Financials in the book's sector data.
Worth fixing eventually; not part of E54.

---

## 4. The 15 objects

```
asset_management_custody_banks  17   AAMI AMG AMP APAM BEN BLK CNS CRBG FHI HLNE IVZ
                                     SEIC STEP TROW VCTR VRTS WT
consumer_finance                14   ALLY AXP BFH COF DAVE ECPG ENVA EZPW FCFS NAVI
                                     PRG SLM SYF WRLD
investment_banking_brokerage    14   BGC EVR GS HLI HOOD IBKR MC MS PIPR PJT RJF SCHW
                                     SF SNEX
insurance_brokers                8
multi_line_insurance             8
diversified_banks                7   BAC C JPM PNC TFC USB WFC
financial_exchanges              7   CBOE CME COIN ICE MKTX NDAQ VIRT
financial_data_ratings           6   DFIN FDS MCO MORN MSCI SPGI
alternative_asset_management     5   APO ARES BX CG KKR
mortgage_reits                   5
reinsurance                      5
commercial_residential_mortgage_finance  4   ACT ESNT NMIH WD
custody_banks                    3   BNY NTRS STT
multi_sector_holdings            3   BRK-B JEF VOYA
specialized_finance              3   CACC EFC HASI
```

Regenerate this list at any time with:

```powershell
cd C:\Users\<your-user>\company_lab
$env:PYTHONPATH="C:\Users\<your-user>\company_lab"
.venv\Scripts\python.exe -c @'
import pandas as pd
from clab.external.store import ExternalStore
from clab.external.taxonomy import resolve
from clab import config
bk = pd.read_parquet("data/scores.parquet")
bk["sid"] = [resolve(r.ticker,r.sector,r.sub_industry)["sector_id"] for r in bk.itertuples()]
bk["iid"] = [resolve(r.ticker,r.sector,r.sub_industry)["industry_id"] for r in bk.itertuples()]
with ExternalStore(config.EXTERNAL_DB).connect() as c:
    have = {r[0] for r in c.execute("select distinct industry_id from industry_intelligence").fetchall()}
    done = {r[0] for r in c.execute("select distinct ticker from company_external").fetchall()}
f = bk[(bk.sid=="financials") & (~bk.ticker.isin(done))]
for iid, g in sorted(f.groupby("iid"), key=lambda kv:-len(kv[1])):
    print(f"{iid:<42}{len(g):>4}{'' if iid in have else '   NEEDS OBJECT'}")
'@
```

---

## 5. When Codex returns — the verification discipline

**Verify against the store. Do not take the report.** This project has caught real errors
in reports twice, and the reports were otherwise accurate both times.

```powershell
cd C:\Users\<your-user>\company_lab
$env:PYTHONPATH="C:\Users\<your-user>\company_lab"

# 1. ingest the objects  (this is the ONLY --apply E54 runs)
.venv\Scripts\python.exe -m clab.external.research_ingest --apply

# 2. verify the claims that came with them
.venv\Scripts\python.exe -m clab.external.verify --apply
```

Then check, in Python, that the store agrees with the report:

- **15 objects present** in `industry_intelligence`, with the expected `industry_id`s
- **claim counts and independence domains** per object
- **`verify_status` tally** — the corpus unverifiable rate is **0.09% (4 of 4,286)** and
  must not move materially

  **Dated correction (2026-09-07):** this is the historical handoff value. The current
  corrected corpus rate is 64/5,233 = 1.22%; see
  `journal/experiments/verification_rate_correction_2026-09-07.md`.
- every non-UNKNOWN `structural_growth` / `replication_difficulty` / `substitution_risk`
  has a claim naming that field

A useful gotcha, already paid for: `external_claim.industry_id` is populated on **company**
claims as well as object claims, so counting claims by `industry_id` mixes the two and
overstates an object's evidence. Filter by `request_id` or by the object's own claim ids.

---

## 6. What to bring back to the main session

1. Whether the **three splits in §3 survived contact with the research.** This is the
   highest-value item — Codex researching the industries is better placed than we were to
   say whether custody / alts / exchanges-vs-data are the right units, and it is far
   cheaper to hear now than after 170 companies are researched against them.
2. Whether `multi_sector_holdings` and `specialized_finance` held together as one thing.
3. Any object where a shared `structural_growth` would have been fiction and UNKNOWN was
   returned instead — that refusal is what produced the uranium/coal split in Energy and
   it is a feature.
4. Claim counts, domains, searches, and the corpus unverifiable rate after ingest.

---

## 7. Standing invariants — these are not negotiable

From the repo's own `CLAUDE.md` and the project's hard rules:

- **Advisory / SHADOW always.** `promoted` is `false` everywhere and no code path sets it
  true. This ranking has never been tested against forward returns: E05 measured its top
  decile at **-7.6% median 3-year excess over SPY** on a survivorship-free holdout, and
  E03 measured **95.6% of its ranking power as sector selection**. Never write a claim
  that it works.
- **Absent data is `NO_DATA`, never `0`.** UNKNOWN is not the bottom of a scale.
- **Bulk data lives on `D:`.** `C:` is a failing SATA spinner — 49,423 power-on hours,
  bad-block events, and the box takes unclean shutdowns. Anything long-running belongs in
  a Scheduled Task, not a shell.
- **Python is `.venv\Scripts\python.exe`.** Bare `python` is the Store stub and exits 49.
- **Commit with** `git -c user.email='YOUR_GITHUB_NOREPLY_EMAIL' -c user.name='YOUR_GITHUB_USERNAME'`,
  and retry `add`/`commit` on a `.git/objects` lock. Use `-F`, never `-m` with escaped
  quotes.
- **A default that covers a WIRING error must be loud.** This repo has been bitten
  repeatedly by graceful degradation hiding a bug — most recently
  `gates.criteria()` silently scoring 0 for missing evidence inputs, which corrupted an
  A/B twice. If a check returns zero, confirm it *can* return non-zero.

---

## 8. Context you may need but should not have to re-derive

The layer had an eight-batch failure that was only just diagnosed and fixed:

- The four rank-order fields (`moat_trajectory`, `competitive_position`,
  `competitive_position_trend`, `company_specific_capture` — **45 of the 100 external
  points**) fell **92% → 0% filled** across eight batches while every quality metric
  stayed perfect.
- Cause: the prompts rewarded abstention. They told Codex a well-blocked UNKNOWN was a
  success and an uncited assertion was a failure, and congratulated the streak each batch.
- Fix: `docs/CODEX_STANDARD_RULES.md` — one canonical block, both errors stated
  symmetrically, never quote a streak back at the researcher. **Every prompt must quote
  it.** The E54 prompt already does.
- E51 measured the fix: Communication Services went **0/47 → 47/47** on those four fields,
  external-score sd 2.90 → 13.85, zero demotions.
- `clab/external/batch_health.py` is the permanent gauge that would have caught it at
  batch four. It does not apply to Phase A (no companies), but run it after any company
  batch.

E53, running in the other session, is the same fix applied to Utilities — the harder,
more homogeneous sector — with a registered guard that `market_share_direction` must stay
**0 of 59**, because a regulated utility has no contestable share and over-correcting into
answering it would trade one systematic error for its mirror image.
