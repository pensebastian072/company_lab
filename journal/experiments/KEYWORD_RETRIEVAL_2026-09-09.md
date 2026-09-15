# The unanimous-MODERATE fields, adjudicated in full — and the rerun never re-retrieved them

Recorded 2026-09-09 by Chat A. Raised by `batch_health.constant_fields`, hypothesised by
Chat B from a 12-quote sample, adjudicated here over every claim in both fields.

Status: SHADOW / advisory. `promoted` is false. **Nothing here is registered as a finding**
— see the last section on why, which is Chat B's call and stands.

## What was being explained

`constant_fields` flagged two fields that take a single value across a whole batch:

```
pricing_power     MODERATE for 47 of 47 comm-services companies, E49 AND E51
technology_risk   MODERATE for 59 of 59 utilities,               E47 AND E53
```

Chat B ruled out two hypotheses with evidence: the vocabularies are live corpus-wide
(`pricing_power` runs MODERATE 172 / LOW 105 / HIGH 17 / UNKNOWN 17), and the evidence is
per-company rather than one claim reused (47 distinct URLs, 47 distinct quotes). Their
12-quote sample then suggested keyword retrieval on the token "pricing", and they said
explicitly that a full adjudication was owed before anyone registered it.

## First, a structural fact that changes the question

**The symmetric reruns did not re-retrieve either field.**

```
pricing_power     E49 vs E51:  47 of 47 quotes byte-identical
technology_risk   E47 vs E53:  59 of 59 quotes byte-identical
```

So "the unanimity survived the symmetric-prompt fix" — the framing both sessions were
working from, mine included — is wrong. These fields were never re-run. The symmetric
prompt restored the four rank-order fields; the evidence behind these two was carried
across unchanged. A rerun that reuses the identical quote is not a second observation, and
the two batches must not be counted as two.

That halves the real denominator: 47 companies and 59 companies, not 94 claims and 118.

## `pricing_power`, all 47 adjudicated

Rule used, stated before the counts: does the passage let you rank **this company's ability
to set or defend its prices** against peers? Three outcomes — SUPPORTS, WRONG SENSE (the
token "pricing" carrying a different economic meaning), and ON TOPIC BUT NOT PROBATIVE
(genuinely about the company's prices, establishes no level).

| | n | of 47 |
|---|---:|---:|
| SUPPORTS the field | **6** | 13% |
| WRONG SENSE | **26** | 55% |
| on topic, not probative | 15 | 32% |

The 26 wrong-sense claims break down as:

```
11   valuation models        Black-Scholes "option-pricing model" (9), fair-value
                             "pricing models" for bonds and Level I/II inputs (2)
 4   tax                     IRS transfer pricing (META, GOOGL), GILTI, enacted rate changes
 3   debt                    repricing amendments to a credit agreement (CNK, IRDM) and to
                             a merger agreement (TMUS)
 3   FX translation          average exchange rates for revenue and expenses; no "pricing"
                             in the passage at all (APP, NFLX, PSKY)
 5   other                   supplier price increases (LUMN), principal-vs-agent pricing
                             risk (OMC), purchase-obligation pricing provisions (TTWO),
                             a share-buyback "Pricing Committee" (TDS), and a passage about
                             discount rates and FCC proceedings with no pricing at all (T)
```

**The decisive detail is not the 55%. It is the six that do support the field.** They point
in opposite directions and every one of them was labelled MODERATE:

```
FOXA  "our ability to secure industry leading affiliate rate and advertising price
       increases"                                                        -> strong pricing power
RDDT  "increase in global ARPU ... driven by an increase in pricing"     -> strong
PINS  "downward pressure on the pricing of our advertisements"           -> weak
WLY   "pricing pressures and revenue share concessions"                  -> weak
```

A label that is the same for the company raising prices and the company under pricing
pressure is not reading its own evidence. That is what settles it: not the modal value, not
the token, but two pairs of quotes that contradict each other landing on one answer.

## `technology_risk`, all 59 adjudicated — same unanimity, different mechanism

I expected Chat B's pricing pattern to repeat. It does not, and the difference matters.

| | n | of 59 |
|---|---:|---:|
| characterises a risk (magnitude still absent) | 10 | 17% |
| **governance boilerplate — a program description** | **45** | **76%** |
| wrong sense | 4 | 7% |

Forty-five of the fifty-nine are Item 1C Cybersecurity prose: which committee receives
updates, how often the board is briefed, that employees take quarterly training, that a
third party runs penetration tests, that the company carries cyber insurance. **Every US
utility files that section and it says the same thing in all of them.** There is no
discriminating content to read, so a per-company label built on it cannot vary — which is
exactly the observed 59 of 59.

The four wrong-sense ones are worth naming because they are unambiguous: ES retrieved an
**executive biography** ("EVP-Human Resources and Information Technology"), PCG an asset
-retirement-obligation assumption list, PNW an EPA rule on "technology-based pollution
limits" for coal plants, PPL a regulatory model requiring cybersecurity outcomes.

So the two fields fail for two different reasons: `pricing_power` retrieves the **wrong
economic sense of a token**, `technology_risk` retrieves the **right topic from a section
with no per-company information in it**. Both produce unanimity. A fix aimed only at
keyword sense would leave the utilities case untouched.

## Limits of this adjudication, stated plainly

- **One adjudicator, no second reader.** I classified all 106 quotes myself. The
  SUPPORTS / not-probative boundary is a judgement call: CCOI ("more control over our
  service, quality and pricing") and SHEN ("not subject to rate regulation") are the two I
  moved into SUPPORTS on a lenient reading. Strict reading gives 4 of 47, lenient 6 of 47.
  The WRONG SENSE count does not move under either reading — a Black-Scholes option-pricing
  model is not pricing power on any reading.
- It covers two fields in two sectors. It says nothing about the other ten company
  ordinals, and nothing about whether the same pattern holds in Financials or Energy.
- It is a read of the stored quote, not of the source document. A quote can be
  unrepresentative of a passage that would have supported the field.

## Why this is NOT being registered as a finding

Chat B's judgement, and it is right: this lands inside **E58 arm B's** registered territory.
Arm B predicts endpoint avoidance in Financials company ordinals against a non-Financials
baseline, with thresholds fixed in `clab/research/e58_endpoints.py` before any of this was
visible. Writing this up as a finding now would be measuring a pattern on the batches that
revealed it.

What the adjudication changes is what arm B's result will *mean*, and that limitation
belongs in E58 before batch 4 lands rather than as a reinterpretation afterwards: if
company-field evidence is retrieved by keyword, then modal and endpoint statistics over
those fields measure **retrieval**, not judgement. "Financials clusters on the middle" and
"the retriever found a token and the label defaulted to the middle" are indistinguishable
in the numbers arm B computes.

This is B4 — E57's mechanical field assignment — reappearing in company claims rather than
industry objects. B4 remains unreproduced in the audit backlog; this is not a reproduction
of it, it is a second instance in a different table.

---

## APPLIED 2026-09-09 — the affected values are blanked, re-research deferred to after E75

User decision: blank now, re-research later, and **the re-research is parked until after
E75** rather than competing with the coverage campaign for Codex.

**What was blanked and why all of it.** Every affected row, not only the ones whose quote
was wrong-sense:

```
pricing_power     47 comm-services companies x E49 and E51   =  94 rows
technology_risk   59 utilities            x E47 and E53      = 118 rows
                                                      total   212 rows
```

The narrower option — blank only the 26 wrong-sense and 45 boilerplate rows, keep the rest
— was rejected on the evidence above: the six `pricing_power` quotes that DO support the
field point in **opposite directions and all carry the same MODERATE label**. Where the
label does not follow the evidence even when the evidence is good, no value from that pass
is trustworthy, so keeping the "good" subset would keep exactly the rows whose labels are
demonstrably wrong.

**The claims were kept, not deleted.** They are real, verified quotes that were assigned to
the wrong field; erasing them destroys the audit trail for the re-research. All 212
claim_ids are recorded as contested in
`D:/company_lab_data/external/reports/keyword_retrieval_blanking_2026-09-09.json`
(sha256 `5403110058ae10c891a49e5db495ef6d34d2094d07b75a460068400419c25929`), which also
freezes every pre-blanking value and score.

**Measured effect, read back from the store:**

| | |
|---|---|
| rows blanked | 212, verified 47/47, 47/47, 59/59, 59/59 |
| scores moved | 212 |
| mean / range | **−3.03**, −3.4 to −2.6 |
| **scores LOST under the 0.80 coverage floor** | **0** |
| scored records after | 523 of 523 |

Nobody fell out of scoring. The drop is uniform because the two fields carry a fixed number
of points, and it is the honest direction: these companies were being credited for a label
that was not reading its evidence.

### Deferred to after E75 — re-research those two fields

`pricing_power` for the 47 comm-services companies and `technology_risk` for the 59
utilities need genuine research, not a relabel. It is deferred deliberately: it costs Codex
budget that the coverage campaign has first call on through E75, and the fields now read
UNKNOWN, which is honest in the meantime.

Two things must be true of that re-research when it happens, and both come from this
adjudication:

1. **It must actually re-retrieve.** The symmetric reruns did not — E51 and E53 reused the
   identical quotes — so "we re-ran it" is not evidence that anything was looked at again.
   Compare quote hashes against the frozen receipt before accepting the result.
2. **A keyword-sense fix alone will not do it.** `pricing_power` failed on the wrong sense
   of a token; `technology_risk` failed on the right topic retrieved from a section
   (Item 1C Cybersecurity) that every utility files and that contains no per-company
   information. The second one needs a different source, not a better matcher.

### A protocol correction this pass earned

The write died **half-applied** — 134 of 212 rows blanked — when the other session held the
DuckDB file, and the failure surfaced as
`IO Error: ... being used by another process` rather than as a wait.
`CHAT_A_B_PROTOCOL.md` rule 3 says "The DuckDB store is safe concurrently; the working tree
is not". That is true of *reads and of writes to different tables*, and it is **not** true
of a long write loop while the other session holds the file: DuckDB takes a
single-writer lock on the file, so a concurrent write fails mid-loop and leaves a partial
state that neither session can see from its own output.

Any bulk write to the store must therefore be idempotent and retry the lock, which is how
this one was completed. The edit to the protocol document is left **uncommitted** for Chat B
under rule 2, since that file is jointly held.
