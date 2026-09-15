# B3 - the rate, and the check nobody ran on the other twelve versions

Run 2026-09-10. Advisory / SHADOW; `promoted` is false. No research value was changed, no
arm was retired, and no verdict moves. Corpus state for every count:
`CORPUS_SNAPSHOT_2026-09-10.json` (7,223 claims, 311 companies with current research, 74
live industry objects).

## B3 is CLOSED, and three documents still list it as open

`ROADMAP_TO_E75.md` and `AUDIT_2026-09-07_FIX_PASS.md` both carry B3 as an open,
unreproduced item. It is neither. It was reproduced in
`AUDIT_2026-09-08_B3_E53_EVIDENCE_REPRODUCTION.md` and remediated the same day by
`B3_B4_REMEDIATION_DECISION_2026-09-08.md`, which retired the whole E53 arm.

The store agrees, and says so in its own words. All 59 E53 rows carry
`status = SUPERSEDED` with `superseded_at = 2026-09-08 19:36:54 -04:00` and:

> B3 semantic-evidence failure: identical receipt reused for `moat_trajectory` and
> `company_specific_capture` on 59/59 companies; pending a field-specific rerun.

**This is the same failure class B6 just recounted**, one level up: a backlog that is
itself stale, listing work as undone after it was done. Strike B3 from both documents.

## The 59/59 claim reproduces exactly

Checked independently against the store rather than taken from the decision doc. For
request `f92abdf0887e91cd072d`, for every one of the 59 tickers, the set of
`excerpt_sha1` behind `moat_trajectory` is **identical** to the set behind
`company_specific_capture`. Fifty-nine of 59, zero exceptions, including all 11
companies that returned UNKNOWN on both.

E53 delivered `moat_trajectory` as STABLE 22, STRENGTHENING 14, WEAKENING 10,
DETERIORATING 2, UNKNOWN 11; and `company_specific_capture` as MODERATE 27, LOW 11,
HIGH 10, UNKNOWN 11. The two fields agree about whether evidence exists in all 59 cases,
which is what one shared receipt forces them to do.

## The rate B3 asked for

B3's instruction was *"sample-based, so quantify the rate rather than citing examples."*
The reproduction and the decision both quantified one cut - 11 of 48 answered pairs
contained a realized outcome relevant to at least one field. The other 37 were never
classified. Below is every one of the 59, under a single rubric.

**What this classifies, and what it does not.** These are the 2026-09-07 register's
assessments of the attached evidence, classified consistently - not a fresh read of 59
filings. The register author read all 59 excerpts; this pass reads the register. A second
opinion on a judgement is not an independent measurement of the filing, and the rubric
inherits whatever that reading got wrong.

### Answered pairs, n = 48

| class | n | rate | what it means |
|---|---:|---:|---|
| **P** pending treated as realized | 16 | **33.3%** | evidence is a request, proposal, ALJ recommendation, stipulation or settlement awaiting an order; the delivered value asserts an outcome |
| **M** relevant, magnitude or scope unproven | 23 | 47.9% | real on-point evidence; the fault is whole-company magnitude, parent vs subsidiary scope, or a level read as a time trend |
| **I** excerpt does not bear on the question | 7 | 14.6% | dividends, accounting estimates, debt-instrument terms, purchase-price allocation, generic risk factors |
| **X** direction contradicted by its own excerpt | 1 | 2.1% | MSEX: the same passage describing the claimed loss also describes approved rate increases |
| clean - relevant, no deficiency recorded | 1 | 2.1% | WEC |

So **24 of 48 answered pairs (50%) rest on evidence that does not support the asserted
direction at all** (P + I + X), and only one of 48 drew no criticism. Within the 23 M
cases, roughly 11 contain an actual realized outcome, which is where the decision doc's
"11 of 48" comes from - the two counts are measuring different bars and are consistent.
The useful gap is the other 13: relevant evidence that is not a realized outcome.

### UNKNOWN pairs, n = 11

**Eleven of 11 are unjustified abstentions on the register's reading.** In every case the
blocking excerpt fails to establish that the evidence is absent - it establishes only that
the attached passage was not about the question. Two are stronger than that: **SR** and
**CWT** had relevant evidence *inside the attached excerpt itself* (an ARM filing cap that
bars recovery of historical earnings deficiencies; implemented initial settlement rates)
and returned evidence-absent anyway.

Set against E53's own accounting - **81 UNKNOWNs marked "evidence absent", 0 marked
"stopped short"** - that self-report is unsupported for all 11 of these pairs. The
abstention error leaves no trace, which is exactly why it needs a register and not a
self-assessment.

**Both error directions are present at once.** Half the assertions are unsupported and
every abstention is unearned. Blanket-converting the answered fields to UNKNOWN would have
converted the first error into the second, which is what the original register warned
against and why retiring the arm whole was the right call.

## The finding: the check was never run on any other version

The B3 decision retired E53 for reusing one receipt across two fields. Nobody then asked
whether any other delivery does the same thing. Run across all thirteen research versions
- for each company, is the `excerpt_sha1` set behind `moat_trajectory` identical to the
set behind `company_specific_capture`:

| research version | companies | same receipt | rate |
|---|---:|---:|---:|
| `2026-09-04+E46-energy` | 52 | 52 | **100%** |
| `2026-09-05+E47-utilities` | 59 | 59 | **100%** |
| `2026-09-07+E53-utilities-symmetric` | 59 | 59 | **100%** (retired) |
| `2026-09-08+E59-financials-phaseb-b1-rerun` | 43 | 9 | 21% |
| `2026-09-08+E59-financials-phaseb-b1` | 43 | 7 | 16% |
| `2026-09-09+E59-financials-phaseb-b2` | 42 | 5 | 12% |
| `2026-09-02+E45-rest` | 45 | 4 | 9% |
| E42 / E43 / E44 / E49 / E51 and the 2026-09-02 pilot | 178 | 0 | 0% |

It is a **builder artifact, not a researcher behaviour**: three versions sit at exactly
100% and everything else sits between 0% and 21%. The three are the deliveries built by
`e46_phase_b_builder.py`, `e47_utilities_builder.py` and `e53_utilities_builder.py`. A
researcher who sometimes reuses a passage produces 12%; a builder that assigns one
evidence window to a fixed pair of fields produces 100%.

This is the same mechanism B4 found in E57, where "the builder assigned three evidence
windows to fixed pairs of fields, so every passage was reused once." B3 and B4 were
treated as two findings in two sectors. They are one defect in a family of builders.

### What is actually exposed

Not as much as 100% suggests, and the honest number is small:

| version | status | answered pairs | live exposure |
|---|---|---:|---|
| E53 utilities | retired 2026-09-08 | 48 | none - superseded |
| E47 utilities | current arm for utilities | **0** | none - answers 0 of 59 on both fields |
| **E46 energy** | **live, not retired** | **12** | **12 companies** |

E46 answers `moat_trajectory` on 16 of 52 and `company_specific_capture` on 12 of 52; the
rest are UNKNOWN. Twelve companies have both fields answered, and all twelve answer both
from the same receipt. So the live consequence of this defect today is **twelve companies
carrying two of the four rank-order fields off a single shared passage** - not 52, and not
the 170 the 100% rows might suggest.

Worth noting where E47 landed: retiring E53 fell utilities back to an arm that answers
zero of 59 on both fields, so **utilities currently contribute no `moat_trajectory` or
`company_specific_capture` evidence at all**, and all 59 utility tickers now hold only
retired arms. That is the conservative outcome the decision intended, and it is also why
utilities appear in no live sector count.

## Recommendation, not an action

**Do not retire E46 on this.** Twelve companies is not 59, the arm is live, and retiring
it would drop energy's two fields to zero the way utilities already did - trading a
measurement problem for a coverage hole without measuring which is worse. What E46 needs
is the same thing E53 was told to get: a field-specific rerun with separate receipts, and
that is a Codex cost, not a local one.

What can be done locally and should be: **an ingest-time check that flags a delivery where
one receipt answers two different fields above some rate.** At 100% it is a builder bug and
at 12% it is a researcher reusing a good passage, so the flag belongs near the top of that
range and must be a loud line in the report, never a block - the same rule E78 set for the
zero-SUPPORTS gate. That check is `clab/external/` and therefore Chat A's to write.

## What this does and does not establish

It establishes that B3 was closed two days ago and is still listed as open; that the 59/59
receipt reuse reproduces from the store; that half the answered pairs asserted a direction
their evidence does not support while every abstention was unearned; and that the same
defect is live in E46 for twelve companies and was never looked for.

It establishes nothing about whether any delivered categorical is *right*. A shared receipt
makes a value unevidenced, not false. E05's top decile still ran -7.6% median three-year
excess against SPY, E03 still puts 95.6% of ranking power in sector selection, and
`promoted` is still false.
