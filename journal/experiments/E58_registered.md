# E58 — registered: is the endpoint avoidance the researcher, or is it Financials?

Registered 2026-09-07, **before** E57 Health Care runs and **before** Phase B runs.
Instrument: `clab/research/e58_endpoints.py`, thresholds pinned by
`tests/test_e58_endpoints.py`. Advisory / SHADOW; nothing here scores or promotes.

## The finding this tests

E56 refuted P3 — the modal clustering on `structural_growth` did not reproduce (0.93 →
0.75). But something else did, exactly:

| field | E56 five | E54 eleven | rest of active corpus |
|---|---|---|---|
| `structural_growth` | 0/4 | 0/10 | 4.3% |
| `replication_difficulty` | 0/5 | 0/11 | 24.5% |
| `substitution_risk` | 0/4 | 0/11 | 22.9% |

**Zero endpoint use in 24 answered values across two separate sessions.** That was
exploratory — not the registered prediction, fields not pre-specified — so it cannot be
tested on the data that produced it. E58 tests it elsewhere.

> **B5 provenance correction recorded 2026-09-07:** E54 and E56 were separate turns in
> the same Codex task, with E54's distributions retained in context before E56. The 0/24
> count is real, but “two separate sessions” does not supply independent replication.
> Arm A remains a preregistered attempt to test the exploratory pattern in another
> sector; its rationale no longer claims that E56 independently reproduced E54. See
> `AUDIT_2026-09-07_B5_E56_INDEPENDENCE_REPRODUCTION.md`.

## Arm A — E57 Health Care industry objects (the clean separation)

Same researcher, same object type, **different sector**. Eleven objects, none built yet.

- **Field:** `replication_difficulty`. Highest endpoint rate in the rest of the corpus, so
  the most power, and the field where the E56 five clustered hardest (HIGH for all five).
- **Pre-run baseline, measured today:** rest of active corpus **22.2%** endpoint use on
  this field, n=54. Health Care contributes **0** of that — it has no objects yet.
- **CONFIRMED** if Health Care endpoint share is **below 0.10**. The avoidance follows the
  researcher across sectors, so "Financials is a mature sector" is dead as an explanation.
- **REFUTED** at **0.10 or above** — the boundary is exclusive, and 1 of 10 lands exactly
  on it and refutes. The avoidance did not follow the researcher, pointing back at
  Financials genuinely lacking extremes.
- **INDETERMINATE** below 6 answered objects.

### Disclosure on Arm A's prompt, checked before E57 ran

`docs/CODEX_E57_HEALTHCARE_PHASE_A.md` was checked for endpoint language before being
handed over. The only mentions of `EXTREME` or `SEVERE` are the vocabulary block every
prompt carries — the legal values listed, with nothing about how often to use them or
where on a scale to sit. The canonical rules block says nothing about it either. **Arm A
is not nudged on endpoint choice.**

One thing does move, and it is the DENOMINATOR rather than the rate. E57 explicitly
invites UNKNOWN on all three industry fields for `health_care_services` if a shared answer
would be fiction, and cites the uranium/coal and Financials refusals as precedent. That
primes toward refusal in general, not toward any particular value. Endpoint share is
computed over ANSWERED values, so it cannot shift the rate — but it can take the answered
count from 11 to 10. The registered floor is 6, so the arm stays decidable.

The instruction stays in the prompt. It is the E56 rule applied honestly, and suppressing
a legitimate refusal to protect a statistic would be the wrong trade — that is the
abstention error in reverse.

Confirmation here still would **not** show the avoidance is an error. A scale end may
genuinely be rare across every industry anyone has looked at. It would only kill the
sector explanation.

## Arm B — Phase B Financials companies (P2 from E56, made concrete)

Same sector, **different field family**, much larger n. Evaluated on Phase B's own
`research_version`.

- **Per field, never pooled.** A field counts as AVOIDED when Financials sits at least
  **0.15** below the comparison group on the *same* field. CONFIRMED if a majority of
  comparable fields are avoided.
- Fields with fewer than four scale values are excluded — on a 3-point scale two of the
  three values are endpoints. Both sides need 20 answered values to be compared.

### Why P2 changed shape, and the pre-run number

P2 was first registered as a **pooled** endpoint share "at least 0.15 below the
non-Financials baseline". Measuring the existing 395 company rows before Phase B showed
that is not a usable statistic — the rate varies by field and **the direction is not
consistent**:

```
E58 arm B on the EXISTING 87 Financials companies (old prompts, E43/E44/E45):
  REFUTED - lower on 1 of 9 comparable fields

  current_moat_strength        0.0%  vs   1.3%
  moat_trajectory             36.0%  vs  35.5%
  industry_structural_growth   0.0%  vs   3.3%
  company_specific_capture    21.7%  vs  30.6%
  demand_visibility            2.6%  vs  53.2%   <- the only avoided field
  pricing_power                5.3%  vs   3.3%
  technology_risk              9.8%  vs   2.6%   <- HIGHER
  disruption_risk             16.3%  vs   2.6%   <- HIGHER
  regulatory_risk              0.0%  vs   2.3%
```

A pooled figure over those would have been dominated by `demand_visibility` alone. So the
rule is per-field with a majority test, and this table is recorded **now** so that the
Phase B result cannot be compared against a baseline chosen after the fact.

**This old-regime read is not Arm B's answer.** Those 87 companies were researched under
the pre-E51 prompts, before the symmetric two-errors block existed. Phase B re-tests under
the current prompt. But it is a strong prior, and it is the single most useful thing found
while registering: **at company level, Financials does not blanket-avoid endpoints, and on
three fields it uses them more than everyone else.** If the industry-level zero is real, it
is specific to industry objects, not a property of how this researcher answers anything.

---

## LIMITATION recorded 2026-09-09, BEFORE batch 4 - arm B may be measuring retrieval

Written before the data that decides arm B exists, so it is a limitation and not a
reinterpretation. **No threshold moves.** `ARM_B_MARGIN` stays 0.15, `ARM_B_MIN_PER_SIDE`
stays 20, the majority rule stands.

### What was found

Chat A adjudicated all 106 company claims behind two unanimous fields; Chat B read a
sample independently first. Both land in the same place.

**`pricing_power`, all 47 comm-services companies, every one MODERATE:** genuinely
SUPPORTS 6 (13%), WRONG SENSE 26 (55%), on-topic but not probative 15 (32%). The 26 are 11
valuation models (Black-Scholes "option-pricing model" nine times), 4 tax, 3 debt
repricing, 3 FX-translation passages containing no "pricing" at all, and TDS, where the
passage is about a share-buyback *Pricing Committee*.

**The six that DO support the field are the argument, not the 55%** - they point in
opposite directions and all six are labelled MODERATE:

```
FOXA  "industry leading affiliate rate and advertising price increases"  -> strong
RDDT  "ARPU ... driven by an increase in pricing"                        -> strong
PINS  "downward pressure on the pricing of our advertisements"           -> weak
WLY   "pricing pressures and revenue share concessions"                  -> weak
```

A label identical for the company raising prices and the company under pricing pressure is
not reading its evidence. That argument does not depend on any classification boundary.

**`technology_risk`, all 59 utilities, every one MODERATE - same symptom, DIFFERENT
mechanism:** characterises-a-risk 10 (17%), **governance boilerplate 45 (76%)**, wrong
sense 4 (7%). The 45 are Item 1C Cybersecurity prose - which committee is briefed, how
often, training, penetration tests, insurance. Every US utility files that section and it
says the same thing in all of them. It is the right topic from a section carrying no
per-company information, so a label built on it **cannot** vary.

A fix aimed at keyword SENSE would leave the utilities case untouched. **Two failures, one
symptom.**

### And the reruns never re-retrieved these fields

Verified by hashing the stored quotes: E51's `pricing_power` claims are **byte-identical**
to E49's - same SHA-1 over the ordered set, zero rows differing - and E53's
`technology_risk` claims are byte-identical to E47's. The symmetric prompt restored the
four rank-order fields; these two were carried across unchanged.

**Both sessions had been quoting doubled denominators, 94 and 118. The real figures are 47
and 59.** A rerun that reuses the identical quote is not a second observation.

### What this means for arm B

1. **Arm B's numbers may measure RETRIEVAL, not judgement.** "Financials clusters on the
   middle" and "the retriever found a token and the label defaulted to the middle" are
   indistinguishable in an endpoint or modal share.
2. **Any arm comparison involving E51 or E53 on a field outside the rank-order four is
   comparing a batch against itself.**
3. A CONFIRMED arm B is weaker evidence than when it was registered, because a plausible
   non-judgement mechanism produces the same signature. A REFUTED arm B is unaffected -
   retrieval artefacts push toward clustering, not away from it.


### Second bias, larger than the first, found by Chat A 2026-09-09

The blanking moved BOTH baselines, not only `pricing_power`, and the bigger move lands on
the field where the comparison is most extreme:

```
non-Financials baseline endpoint share, before blanking -> now
  pricing_power     3.704% -> 4.930%   (n 378 -> 284)
  technology_risk   4.113% -> 5.904%   (n 389 -> 271)
```

`technology_risk` moves more in both absolute and relative terms, and **Financials
`technology_risk` endpoint share is 0.000% on n=85 under the registered scope** - the
maximal-avoidance reading. So the baseline that rose is being compared against a subject
sitting at exactly zero. Same direction as the `pricing_power` caveat, on the field where
it matters most.

For contrast, `pricing_power` Financials is 7.1% against a 4.9% baseline - endpoint
SEEKING, not avoidance, and consistent with the REFUTED preview.

Both belong here, not just the one Chat B first recorded.
### Limits of the adjudication itself

One adjudicator, no second reader. The SUPPORTS boundary is a judgement call: a strict
reading gives 4 of 47 rather than 6, though the wrong-sense count does not move. Two
fields, two sectors. It reads the STORED QUOTE, not the source document. Chat B's
independent sample of 12 agreed on direction but was regex-classified and is not an
adjudication.

Full record: `journal/experiments/KEYWORD_RETRIEVAL_2026-09-09.md` (Chat A, `2f93876`).

## What the two arms mean together

| Arm A (Health Care objects) | Arm B (Phase B companies) | reading |
|---|---|---|
| CONFIRMED | CONFIRMED | a researcher tendency, across sectors and field families. Fix the prompt. |
| CONFIRMED | REFUTED | specific to INDUSTRY objects — the small-n shared questions, not company judgement. |
| REFUTED | CONFIRMED | not a general tendency; something about Financials companies. |
| REFUTED | REFUTED | E56's zero was small-n noise. 24 values is not many, and this is the outcome the existing company data already points at. |

## Rules

- Arm A is evaluated when E57 lands, Arm B when Phase B lands. Neither threshold moves.
- The evaluator was run before both and returns INDETERMINATE for Arm A — the receipt.
- Per-field tables, never a pooled headline.
- A partial Phase B batch is balanced, not representative. Do not read Arm B off the
  first batch.
