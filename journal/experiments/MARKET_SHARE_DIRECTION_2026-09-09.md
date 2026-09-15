# `market_share_direction` — a field answered by a module nobody called

Recorded 2026-09-09. Raised by Chat B, measured independently by both sessions, wired and
applied by Chat A. Every number below was read from the store.

Status: SHADOW / advisory. `promoted` is false and nothing here changes that.

## Unified finding and decision

**This is one field-boundary finding, not four separate alerts.** The four observations
form one causal chain: document research did not produce bank share direction; a local
primary-data computation did; that computation was absent from the normal pipeline; and
its one-off use changed only one side of a matched experiment.

| Observation | Frozen measurement | What it establishes |
|---|---:|---|
| Financials Phase B web-research output | **0/85** answered across the accepted 43- and 42-company batches | The document-research route did not produce this quantity in the population where a registry exists. |
| E43 web-research output | **1/40** answered | The failure predates E59 and is not a one-batch accident. |
| Answered bank rows in E44 and E45 | **29/29 computed**, 0 researched | The apparent bank fill came entirely from the FDIC method, not partial researcher success. |
| E44 matched control versus E43 | **16/40** E44 rows received the computation; **0/40** E43 rows did | Applying a derived method to one arm only contaminates the control comparison. |

Decision recorded 2026-09-10, after the four measurements above and after the wiring was
implemented:

1. For regional banks, `market_share_direction` is a locally derived primary-data field
   where the FDIC guards resolve it. A web researcher is not asked to recreate the ratio.
   A missing, ambiguous or guard-rejected match remains `UNKNOWN`.
2. A computed value never overwrites a researched value. Agreement remains visible and a
   disagreement is a contradiction to investigate, not a reason to choose silently.
3. Computed claims are first-class evidence only through the explicit
   `fdic_sod:` / `revenue_share:` request prefixes. They may pass the research-arm filter,
   but no other arm's research claims may do so.
4. Every comparison arm must receive the same computed pass at the same method and data
   snapshot. If that symmetry is absent, the computed field is excluded from the causal
   comparison and the contamination is stated. E43 versus E44 is therefore not evidence
   of a treatment effect on `market_share_direction`.
5. This decision is about measurement provenance, not predictive usefulness. The field
   stays SHADOW and no score or ranking is promoted by making its derivation reproducible.

The four observations are jointly necessary. The two near-zero research rates alone could
be an abstention defect; the 29 computed answers show the viable method; the E44 asymmetry
shows why merely having that method is unsafe without orchestration.

## Frozen version-level receipt

| research version | answered | of | FDIC-computed | researched |
|---|---:|---:|---:|---:|
| `2026-09-02+E43-batch1` | 1 | 40 | 0 | 1 |
| `2026-09-02+E44-matched` | 16 | 40 | **16** | **0** |
| `2026-09-02+E45-rest` | 13 | 45 | **13** | **0** |
| `2026-09-04+E46-energy` | 41 | 52 | 0 | 41 |
| `2026-09-05+E47-utilities` | 0 | 59 | 0 | 0 |
| `2026-09-05+E49-commservices` | 23 | 47 | 0 | 23 |
| `2026-09-06+E51-commservices-symmetric` | 23 | 47 | 0 | 23 |
| `2026-09-08+E59-financials-phaseb-b1` | 0 | 43 | 0 | 0 |
| `2026-09-08+E59-financials-phaseb-b1-rerun` | 0 | 43 | 0 | 0 |
| `2026-09-09+E59-financials-phaseb-b2` | 0 | 42 | 0 | 0 |

E47's 0 of 59 is correct and was pre-registered: a rate-regulated utility has no
contestable market share. Financials has no equivalent argument — banks file deposit
share, insurers premium share — so its zeros are not that.

The operational chain behind the decision:

1. **The module existed and was never called by the pipeline.**
   `clab/external/marketshare.py` computes
   this field from the FDIC Summary of Deposits, with an acquisition guard, a shared-market
   minimum and a deposit-coverage floor. Its only importer in the repo is its own test
   file. Its docstring says the field "is not unanswerable, it is unanswerable BY READING
   DOCUMENTS, which is what a web researcher does" — and the corpus now proves that
   specifically: 0 of 85 Financials companies plus 39 of 40 in E43.
2. **It fired exactly once, by hand.** The 29 FDIC claims in the store were created
   2026-09-02 16:52 as a one-off. Every answered bank row in E44 and E45 is that one-off.
   The 40% and 29% rates are not partial research success; they are the computation and
   nothing else.
3. **That one-off silently changed a control arm.** `2026-09-02+E44-matched` is a matched
   control for `2026-09-02+E43-batch1`. It received the FDIC pass on 16 of its 40
   companies, **after it had been scored** (records scored 15:32, claims created 16:52),
   and E43 never received one. The two arms therefore differ by more than the variable
   under test, and any comparison drawn between them needs that stated before it is cited
   again. The scores only caught up in the 2026-09-09 re-score, which is where the
   +5.0/+2.5 on ten of those banks came from — see `SCORE_STALENESS_2026-09-09.md`.

Corpus-wide the researched answers lean on the weakest source the standing rules
recognise: of the 632 claims citing this field, 511 are `COMPANY_IR`, 116 `PRIMARY_DATA`
and 5 `COMPETITOR_FILING`. The computed ones are the primary data.

## Wired, applied, and what it actually bought

Ran `marketshare.compute` over the 89 `regional_banking` names in the book, FDIC SOD 2023
against 2024, then `apply_to` on the three Financials versions.

```
resolved              55 of 89   (26 GAINING, 13 LOSING, 16 FLAT)
unmatched by name     26
matched but refused    8   acquisition guard, or deposits coverage under the 60% floor
```

| research version | filled | conflicts | already agreed |
|---|---:|---:|---:|
| `2026-09-08+E59-financials-phaseb-b1` | 7 | 0 | 0 |
| `2026-09-08+E59-financials-phaseb-b1-rerun` | 7 | 0 | 0 |
| `2026-09-09+E59-financials-phaseb-b2` | 6 | 0 | 0 |
| `2026-09-02+E44-matched` | 0 | 0 | 16 |
| `2026-09-02+E45-rest` | 0 | 0 | 13 |

**Zero conflicts, and the 29 rows from the September one-off re-derived to the identical
direction two weeks later.** That is the reproducibility check on the module that nobody
had run, and it is what makes the wiring low-risk rather than merely tested.

Twenty rows filled — 13 unique companies, since b1 and b1-rerun are the same roster. After
re-scoring: seven moved +5.0 (GAINING), four +2.5 (FLAT), six +0.0 (LOSING earns no points
but the field becomes SCORED and coverage rises, 0.85 → 0.90 on RF).

**The ceiling is name matching, not economics.** Only 13 of the 35 already-researched
regional banks resolve. The 26 unmatched include ZION, CFG, WBS, VLY, FNB, ONB, ASB, SSB,
CBU and CFR — none small or obscure; FDIC files them under a holding-company name the
exact matcher does not reach. Improving that matcher is worth more than any prompt change
for this field. It is deliberately NOT folded into this change, because folding it in
would hide it.

## The wiring bug underneath, found while verifying the fill

The fill worked. It worked for the wrong reason, and checking why exposed a second defect.

`score_all` filters a company's claims to its own research arm — a real rule, protecting a
real failure (FICO's cited arm has 11 claims and an early draft scored it on 14). But a
COMPUTED claim is filed under `fdic_sod:<version>` or `revenue_share:<version>`, which
never equals a company's `request_id`, **so the scorer discarded every computed claim in
the corpus**: 87 `revenue_share` claims across 64 tickers and 42 `fdic_sod` claims across
42. The field was written onto the record and then refused backing.

It did no damage, and only by luck: in all 20 filled rows the researcher HAD cited
`market_share_direction` while returning UNKNOWN for it, and that citation did the
backing. The first company researched without a claim on the field would have been scored
wrong with nothing in the output saying so — a silent default covering a wiring error,
which is the class this repo has been bitten by five times.

Fixed in `score.py`: `_is_computed_claim` admits derived claims past the arm filter,
`_is_arm_claim` keeps the contamination rule, and the docstring records that a computed
pass must be run across EVERY live arm or it becomes an uncontrolled variable — which is
exactly what happened to E44.

Effect of admitting them, measured across all 13 versions:

```
records whose score moved                     136
delta distribution        +1.1 (47), +1.2 (37), +1.3 (52)
fields that became SCORED                       0
```

All of it is `evidence_quality`: one more claim and one more independence domain
(`PRIMARY_DATA`). **No company gained a categorical point**, because the computed claims
were always redundant as backing. Applied; the store now holds these values.

> **Correction, same day.** An earlier pass of this investigation reported "no
> `revenue_share` claims exist at all". That was a wrong `LIKE 'revshare%'` prefix against
> a request_id of `revenue_share:`. There are 87, across 64 tickers, and they were subject
> to the same invisibility. The corrected figure is used above.

## The gauge that would have caught it at batch 1

`batch_health.constant_fields(version)` — any company ordinal taking a single value across
a batch, all-UNKNOWN and single-answer reported separately, NOT_APPLICABLE nominations
excluded, strict (one dissenting row clears it, so E43's 1-of-40 does not trip it and
`compare()` stays the tool for near-constant fields).

`batch_health` reported OK on both Financials batches and was right to: `compare()` watches
the four rank-order fields and this is not one of them. The gap was between "the batch
answered its scored fields" and "the batch answered".

Over the live corpus it reproduces the known history rather than crying wolf — E49 four
all-UNKNOWN fields against E51's zero after the symmetric fix, E47 three against E53's
one, and that one is the pre-registered `competitive_position_trend`.

## An observation it surfaced, deliberately NOT written up as a finding

`pricing_power` is MODERATE for all 47 comm-services companies in **both** E49 and E51, and
`technology_risk` is MODERATE for all 59 utilities in **both** E47 and E53 — unanimity that
survived the symmetric-prompt fix.

Chat B checked it and the stuck-answer hypothesis fails twice: the vocabularies are live
corpus-wide (`pricing_power` runs MODERATE 172 / LOW 105 / HIGH 17 / UNKNOWN 17), and the
evidence is per-company rather than one claim reused (E49's `pricing_power`: 94 claims, 47
distinct URLs, 47 distinct quotes). That is unanimous convergence on the modal value with
separate evidence each time — the middle-clustering pattern **E58 arm B is registered to
test**. Writing it up now would be measuring the pattern on the batches that revealed it,
so it stays an observation and does not enter arm B's baseline. Arm B is evaluated on
Phase B's own `research_version` after batch 4, as registered.

The one cheap check that would separate convergence from 47 ways of not answering is a
read of the 47 quote texts, not a count of them. Not done here.

## What this does not establish

The FDIC computation says which direction a bank's deposit share moved between two annual
surveys in the markets it was present in both years. It does not say the bank is winning,
does not cover any non-bank Financials industry, and carries no claim that this ranking
predicts returns. E05's top decile ran −7.6% median three-year excess against SPY and E03
put 95.6% of ranking power in sector selection.

---

## Second pass, same day — the matcher was matching the wrong banks

Chat B diagnosed the name-matching ceiling and found something worse inside it. Verified
here against the 2024 survey before changing anything.

**`_norm` strips so many words that distinct institutions collide, and the index resolved
the collision by row order.** `holding_index` used `setdefault`, so whichever holding
company the file listed first claimed the key. Measured: **209 of 2,991 normalised keys
are claimed by more than one holding company.**

```
CFG   Citizens Financial Group  -> CITIZENS HOLDING COMPANY      $1.2bn   (true: $180.3bn)
FNB   FNB Corporation           -> FNB FINANCIAL SERVICES, INC.  $0.2bn
CHCO  City Holding Company      -> CITY BANCSHARES, INC.         $0.4bn
```

Those are the exact failures the prefix rule was removed for, happening on the **exact**
match. `match_company`'s docstring claimed exactness prevented them; it did not. What
prevented them was `_plausible_scale`. **The scale guard is load-bearing, not
belt-and-braces** — relax `SCALE_MIN` and CFG ships a deposit trend computed from a small
Mississippi bank, with a real FDIC URL on it.

Three changes, in the order they were tried:

1. **NAMEFULL as a second exact key.** The book holds the BANK's common name; NAMEHCR is
   the holding company's legal name. "Frost Bank" cannot normalise into "CULLEN/FROST
   BANKERS, INC." — a different name, not a formatting difference — but FDIC's NAMEFULL
   for that institution literally is "Frost Bank". Exact-on-normalised like the first key,
   so it loosens nothing. Wins CFR, WBS, VLY, ONB, ASB and others.
2. **Refusing every ambiguous key** — tried, and **rejected as too blunt**. It took the 89
   regional banks from 74 matched to 63, because most collisions are one large bank
   against a small one and the scale guard already tells them apart. CBSH, HOMB, INDB,
   NWBI and HOPE were correct matches thrown away to stop CFG being a wrong one.
3. **Resolving ambiguity by SIZE instead.** Exactly one candidate of a plausible scale
   wins; zero or several is UNKNOWN, with the count in the reason. Deposits against market
   cap is independent of the name, which is what a tie-break has to be. CFG now resolves
   to CITIZENS FINANCIAL GROUP, INC. out of **12** candidates.

Also closed: **an empty normalised key must never match.** "The Bancorp, Inc." strips to
the empty string — every token is a corporate-form stopword — and it had matched a $7.2bn
book against a $2.7bn market cap by luck. TBBK is now honestly UNKNOWN.

```
regional banks with a computed direction    55 -> 66 of 89
resolved via the scale tie-break            11
```

### The store was reconciled, not just improved

`NWBI` had been filled FLAT earlier the same day. The fixed matcher refuses it — "northwest"
is claimed by NORTHWEST BANCSHARES INC ($12.4bn) and NORTHWEST FINANCIAL CORP. ($2.5bn) and
**both are of a plausible scale against a $2.2bn market cap**, so size cannot separate them
and neither can an exact name. The stored value rested on a resolution the matcher now
rejects, so it was reverted to UNKNOWN and its claim deleted. A refusal we can defend beats
a fill we cannot.

Then the improved matcher was applied and everything re-scored:

| research version | newly filled | already agreed |
|---|---|---:|
| `2026-09-08+E59-financials-phaseb-b1` | CFFN, VLY | 6 |
| `2026-09-08+E59-financials-phaseb-b1-rerun` | CFFN, VLY | 6 |
| `2026-09-09+E59-financials-phaseb-b2` | ASB, BANR, CFG, TMP, WABC | 6 |

`market_share_direction` now reads answered on **27 of the 128 E59 rows** — 19 unique
companies, up from 13, one of them reverted, and 46 FDIC claims in the store.

**Still unmatched and correctly so:** ZION is structural — Zions collapsed its holding
company in 2018, so there may be no NAMEHCR row at all. FNB and CHCO stay refused. SSB is a
single space ("South State Bank" against FDIC's "SOUTHSTATE") and was deliberately left
alone: one company is not worth a wider door.
