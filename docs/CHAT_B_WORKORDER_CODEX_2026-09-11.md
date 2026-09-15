# Chat B (Codex) — research lane work order, 2026-09-11

You are the **research** lane. You produce industry objects and company research. You do not
apply gates, score, rank, export, or write the DuckDB store — Claude's lane does that, and
the finalizer applies every gate locally. Operating plan:
`docs/PLAN_TO_1500_2026-09-11.md`.

Everything is advisory / SHADOW. `promoted` is false everywhere and no code path may set it
true.

Three sessions, in this order. Each is self-contained; do not start the next until the
previous is accepted.

---

## SESSION 1 — E59 Financials, batch 3 (42 companies)

The prompt is written: **`docs/CODEX_E59_FINANCIALS_PHASEB_B3.md`**. Read it and follow it.

The request is staged as `9e243401d2fb0d1e380e`, sample `E59-financials-phaseb-b3`, but the
finalizer compares the request's date in **New York** against today in New York and refuses
anything else. It has already killed two stagings. So **re-stage it the same NY day you will
finalize it**, with the identical roster — `request_id` hashes roster+depth+spec+sample and
not the timestamp, so the same command rebuilds the same id:

```powershell
cd C:\Users\<your-user>\company_lab
$env:PYTHONPATH="C:\Users\<your-user>\company_lab"
.venv\Scripts\python.exe -m clab.external.request --symbols "AGO,AIG,ALLY,AMG,AON,AUB,BBT,BGC,BLK,BNY,BX,C,CFR,COF,COIN,DFIN,EFC,EGBN,ESNT,EZPW,FITB,HAFC,HASI,HLNE,HOOD,IBOC,KMPR,MC,MET,MRSH,MSCI,MTG,PNFP,RJF,RLI,SBSI,SLM,TRMK,TROW,USB,VIRT,WAFD" --depth 3 --sample E59-financials-phaseb-b3 --require-citation
```

**Do not spend searches on `market_share_direction` for banks.** It returned UNKNOWN for
0 of 85 across batches 1 and 2, because it is not answerable by reading documents. It is now
**computed** from the FDIC Summary of Deposits. Asking for it again buys nothing.

## SESSION 2 — E59 Financials, batch 4 (43 companies, finishes the sector)

Build it from the batch-3 template, same rules. This session matters twice over: it takes
Financials to 257/257, and it is the only thing that makes **E58 arm B** evaluable, because
arm B needs the complete `research_version` rather than three of four.

Add the new prompt file to `CURRENT` in `tests/test_codex_prompt_rules.py`. E65 went red for
exactly that omission, and the test also checks that the three core sections of
`docs/CODEX_STANDARD_RULES.md` are quoted **verbatim** — a paraphrase is how the last drift
started.

## SESSION 3 — E80 Utilities, Phase B re-research (59 companies)

Utilities is the sector that looks finished and is absent from the product. The industry
objects are fine — **7 of 7 active, all three structural fields answered** — so this is
Phase B only. Do not rebuild the objects.

What happened: `2026-09-07+E53-utilities-symmetric` was retired whole under B3 for evidence
quality, all 59 rows `SUPERSEDED`. The older `2026-09-05+E47-utilities` rows are still live,
but company resolution **omits rather than falling back**, so all 59 companies drop out of
the workbook. Re-researching them restores a complete sector.

E53's defect was evidence that did not support its assigned field — read
`journal/experiments/AUDIT_2026-09-08_B3_E53_EVIDENCE_REPRODUCTION.md` before starting, and
note that the same defect was later found **live in E46 energy for 12 companies**, so it is a
method failure and not a one-batch accident.

One sector-specific carve-out that is already settled and must not be re-litigated:
`competitive_position_trend` is **0 of 59 for regulated utilities, twice, and correctly** —
authorised ROE is set per rate case by different commissions on different schedules. Return
UNKNOWN with one blocking claim and move on. The carve-out is for that field only.

---

## FOUR RULES THAT ARE NEW, AND EACH ONE COST A RE-RUN

1. **Every industry object needs at least one NON-ISSUER source** — REGULATOR, TRADE_PRESS,
   ACADEMIC or PRIMARY_DATA. An object evidenced only by its own members' filings is rejected
   at ingest. E79 came back 100% `sec.gov` across 72 claims; E61 was 96.6% single-domain.
2. **Never split a taxonomy unit without evidence already in hand for each resulting unit.**
   E79 split 20 units into 64, 26 of them singletons, and 36 concluded nothing — so the gate
   deleted them and stranded 131 companies. Splitting and then failing to evidence is
   strictly worse than not splitting.
3. **`structural_growth` comes from a body that publishes the quantity, or it stays UNKNOWN.**
   A trade association's shipment series, a regulator's statistic, a sized market in a
   filing. Never company revenue, never employment, never a sentiment index. Two worked
   examples: FGIA publishes prime-window demand −5% and residential skylights −9% in unit
   shipments for 2025; AEM publishes US ag tractors −14.8% and combines −4.3%. A proxy you
   decide to use anyway must be **named as a proxy in the claim's own words**.
4. **A quote must be copyable verbatim from the page you cite.** Verification is being
   tightened so that exact containment, not vocabulary overlap, is what certifies a claim.
   146 existing claims cite a page that does not contain their quote at all, and the overlap
   score that passed them has a median of 1.0. If you cannot copy the sentence, you do not
   have the citation.

## Standing rules

- **Two errors cost the same.** Asserting what you cannot evidence corrupts the score;
  abstaining where the evidence would have supported an answer is a silent loss that nothing
  catches. UNKNOWN is not the safe choice, it is the other way to be wrong.
- Absent data is `NO_DATA` / `UNKNOWN`, never `0`.
- One claim, one field. Never reuse an identical quote across fields. A company description
  is not a replication-difficulty receipt; a segment metric is not an industry metric without
  a scope argument.
- Stage a request the same New York day it will be finalized.
- Report what you did **not** establish and which of the two errors you were closer to —
  "I stopped short" is more useful to us than a confident blocking claim.
- Never claim this ranking works. Its top decile ran a **−7.6% median three-year excess
  against SPY** on a survivorship-free holdout, only 45.3% beat SPY, and **95.6% of ranking
  power was sector selection**. Coverage buys a more honest instrument, nothing more.

---

# ADDENDUM 2026-09-11 — batch 3 was REJECTED, and session 1 repeats

Full adjudication: `journal/experiments/E59_B3_REJECTION_2026-09-11.md`. Nothing was applied;
the request slice still holds 0 rows and its manifest is `pending`.

Your quality half was perfect and independently reproduced: 342/342 quotes verbatim,
326/326 fields claim-backed, both SHA-256s exact. **Keep all of that.** The reject is coverage.

```
four-field fill      b1 85.5%   b2 87.5%   b3 48.8%
company_specific_capture   33/43 · 31/42 · 5/42
competitive_position_trend 36/43 · 37/42 · 16/42
pricing_power              43/43 · 42/42 · 14/42
```

I tested whether b3 was simply stricter than b2 and it was not: all **247** of b2's claims on
those five fields pass exact containment under the same bar. b2 answered 87.5% with evidence
that clears your own standard, so the drop is lost information.

The cause is in your builder, line 702: `"search_definition": "latest locally cached SEC 10-K
and 10-Q per issuer..."`. 321 of 342 claims are `sec.gov` and 297 of 342 are `COMPANY_IR`.
The four fields that collapsed are the four that require ranking a company against **named
peers**, and a company's own 10-K cannot establish that. This is the second time a session
ran as local retrieval — E79 was the first, same signature.

## Two rules added, both now acceptance conditions

5. **The local filing cache is a starting point, never the search space.** A peer-comparison
   field needs a second issuer's disclosure, a regulator series, or trade coverage. If you
   cannot reach outside the cache for a field, return UNKNOWN and say so — but do not let the
   cache define what was searched.
6. **Claim volume per company is an acceptance number.** b1 ran 550 claims over 43 companies
   and b2 541 over 42 - about 12.8 each. b3 ran **342 over 42, or 8.1**, a 37% fall, and that
   is the measurable shape of a search that stopped early.

   **Correction to the first version of this rule, which said evidence concentration was a
   reject on its own.** It is not, and it would have wrongly rejected b1, b2, E46 and E47:
   measured, `COMPANY_IR` runs 85-92% across every ingested batch here, and b3's 86.8% is
   normal. Concentration is reported, not refused. Volume and per-field fill are the numbers
   that discriminate.

## Session 1, repeated

Same roster and command as above, with one change already made on this side: **MTG now
resolves to `private_mortgage_insurance`**, not `reinsurance`. The book files MGIC under GICS
"Reinsurance" and the override map had ACT, ESNT and NMIH but not MTG — the largest of the
four was missing from its own peer group, which is why your batch judged it on treaty pricing,
retrocession cost and ILS capacity. Re-stage, and MTG comes through correctly; no quarantine
needed.
