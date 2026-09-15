# E56 — Financials Phase A2: the five re-cut objects, and P3

Ingested and verified 2026-09-07. Every number read back from the store, not taken from a
report. Advisory / SHADOW; `promoted` is false and nothing here touches a company score.

## What landed

| check | result |
|---|---|
| objects | all 5 present, `sector_id = financials` |
| claims | 5,192 → **5,225** (+33), all **VERIFIED_LOCAL** |
| corpus unverifiable rate | 4/5,225 = **0.077%**, unchanged |

> **Correction recorded 2026-09-07:** this is the historical rate reported by E56.
> PDF extraction-state and numeric-quote guards later revised the corpus tally to
> 64/5,233 checked = 1.22%. See `verification_rate_correction_2026-09-07.md`.
> **Correction re-stated 2026-09-09.** This figure has now been quoted as 0.077%,
> 0.134%, 1.607%, 1.22% and 0.980% - every one of them true of a different corpus. The
> COUNT is the stable fact: **64 claims are UNVERIFIABLE**, from token overlap accepting a
> quote whose numbers are absent from the source, not from verifying against binary. The
> RATE moves with the denominator as coverage grows (6,531 claims as of 2026-09-09 =
> 0.980%). Quote the count and the as-of date, never a bare rate. Live figures are pinned
> in `CORPUS_SNAPSHOT_2026-09-09.json` (SHA-256 `FDA33CB1B32B0C3F4562C9799A66632765DEC43C7B749CEBB495C243FBDCA0A5`), on D: under external/reports.
| non-UNKNOWN field with no claim naming it | **none** |
| `regional_banking` / `diversified_banks` / `consumer_finance` | row hashes **identical** before and after |
| SUPERSEDED rows after re-ingest | still **4** — the lifecycle survived a full re-ingest |

| object | claims | domains | SG / RD / SR |
|---|---:|---|---|
| `private_mortgage_insurance` | 8 | COMPETITOR_FILING, REGULATOR | MODERATE / HIGH / ELEVATED |
| `retirement_benefits` | 7 | COMPETITOR_FILING, PRIMARY_DATA, REGULATOR, TRADE_PRESS | MODERATE / HIGH / MODERATE |
| `commercial_mortgage_banking_servicing` | 7 | COMPETITOR_FILING, REGULATOR, TRADE_PRESS | MODERATE / HIGH / MODERATE |
| `climate_infrastructure_finance` | 6 | COMPETITOR_FILING, PRIMARY_DATA, REGULATOR | HIGH / HIGH / MODERATE |
| `multi_industry_conglomerate` | 5 | COMPETITOR_FILING | **UNKNOWN** / HIGH / **UNKNOWN** |

`multi_industry_conglomerate` refused two of three fields, which is the answer the prompt
asked for if a conglomerate is a portfolio rather than an industry. It is also the only
single-domain object of the five.

**Depth varied — 8, 7, 6, 7, 5 — against E54's uniform 5 on every one of fifteen.** This
does **not** test P1: the E56 prompt told the researcher not to aim for a fixed count, and
`E56_registered.md` declared that intervention in advance for exactly this reason. P1 is
measured on Phase B, whose prompt carries no such instruction.

## P3 — REFUTED as registered, and the threshold was stricter than intended

```
E56 P3 [structural_growth]: REFUTED
  answered 4/5   UNKNOWN 1   modal MODERATE at 75% (registered threshold 80%)
  distribution {'MODERATE': 3, 'HIGH': 1}
```

E54 ran modal **0.93** on `structural_growth`; the five re-cut objects, built in a
separate session, ran **0.75**. Below the registered 0.80, so the prediction is refuted
and E54's clustering does not reproduce.

> **B5 provenance correction recorded 2026-09-07:** “separate session” did not mean
> independent context. E54 and E56 ran as turns in the same Codex task, and the retained
> task history exposed E54's modal/endpoint distributions and P3's purpose before the
> E56 research turn. The 0.75 calculation remains REFUTED against the frozen threshold,
> but it cannot discriminate a sector effect from a researcher/run effect. See
> `AUDIT_2026-09-07_B5_E56_INDEPENDENCE_REPRODUCTION.md`.

**But the realized n changed what 0.80 meant, and this has to be said with the verdict.**
0.80 was chosen against an expected five objects, where it reads "four of five agree."
One object returned UNKNOWN, so the denominator was four, and at n=4 the reachable modal
shares are 0.25, 0.50, 0.75 and 1.00. **Nothing between 0.75 and 1.00 exists, so the only
confirming outcome was unanimity.** The verdict stands as registered — the threshold was
fixed before the data and is not being moved now — but a reader should know that "REFUTED"
here means "not unanimous", not "clearly spread".

The `MIN_ANSWERED = 3` floor added in the 2026-09-07 amendment did its job: 4 answered
clears it, so the result is decidable rather than INDETERMINATE.

**Lesson worth keeping: a threshold on a proportion must be checked against the modal
shares the realized n can actually produce.** A denominator that moves by one turns a
"most of them" test into a unanimity test without anyone editing the number.

## What did reproduce, and it was not the registered prediction

Endpoint use — how often an object lands on either end of a scale:

| field | E56 five | E54 eleven | rest of active corpus |
|---|---|---|---|
| `structural_growth` (DECLINING / EXCEPTIONAL) | **0/4** | 0/10 | 2/47 = 4.3% |
| `replication_difficulty` (LOW / EXTREME) | **0/5** | 0/11 | 12/49 = 24.5% |
| `substitution_risk` (SEVERE / LOW) | **0/4** | 0/11 | 11/48 = 22.9% |

**Zero of thirteen answered values across a separate session.** And
`replication_difficulty` came back HIGH for all five — modal 1.00, a *tighter* cluster
than E54 managed on any field.

> **B5 correction:** the 0/13 count is retained, but “across a separate session” is not
> evidence of independence for the same provenance reason above. Treat it as exploratory
> same-context output until tested in a genuinely separate task/sector.

So the "middle-reach" is two behaviours, not one, and they came apart:

- **Modal clustering on `structural_growth` did not reproduce** (0.93 → 0.75). Registered,
  tested, refuted.
- **Endpoint avoidance reproduced completely** (0/13, against 4–25% elsewhere), and one
  field clustered harder than anything in E54.

**This second finding is exploratory and is not evidence yet.** It was not the registered
prediction, the fields were not pre-specified, and pooling three fields over five objects
pools values that share the same objects. Testing it on the data that suggested it is the
p-hacking the registration exists to prevent. It needs its own pre-registration, against
Phase B or a non-Financials sector, before it means anything.

The confound E56 was built to break is also **not** broken by this. Financials may still
simply be a sector without extremes — the pre-existing Financials objects do use `LOW`
occasionally, but no object in either new batch has used any scale end.

## Verdicts

| prediction | status |
|---|---|
| **P3** — clustering repeats, modal ≥ 0.80 on `structural_growth` | **REFUTED** (0.75, n=4, only unanimity would have confirmed) |
| **P1** — depth stays uniform | **not tested here.** Depth varied 5–8, but the prompt intervened on depth by design. Phase B. |
| **P2** — middle-reach carries into company fields | **not tested.** Phase B. |

## Process

The evaluator was written and committed (`c0b5a3f`) **before** ingest, and returned
INCOMPLETE at that point — the receipt that its thresholds were fixed while the answer was
unknown. Writing it first is also what surfaced the `MIN_ANSWERED` hole, which would
otherwise have let a single answered object "confirm" P3 at a modal share of 1.0.

Nothing else ran: no request, no roster, no finalizer, no scoring, no company research.
