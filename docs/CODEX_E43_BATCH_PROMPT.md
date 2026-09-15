# Codex E43 — the first real batch (40 companies)

Everything the pilot learned, applied. Request `1358af92f8227af46c5d` is built and
staged.

## What changed since the pilot, and why it matters to you

| change | why |
|---|---|
| Citation rule is ON | Arm 2 proved it: 10 of 36 evidenced -> 32 of 32, no relabelling |
| **Claims are wanted behind a researched UNKNOWN too** | The rule as written only demanded them for non-UNKNOWN fields, so you stopped writing the Eaton/Schneider claims that proved capture had been *investigated*. That lost `UNVERIFIED_CORE_THESIS` on VRT and the conviction gate then blessed the one company whose capture was unproven. |
| Conviction is a SCORE, not pass/fail | Every company is ranked. A flag costs points; it does not eject anyone. |
| `cheapness_quality` no longer scores | You told us twice it had no citable source. Valuation is already 15 measured points. It is still stored and still feeds VALUE_TRAP_RISK. |

## The batch is not arbitrary

40 companies drawn from the **226 covered by a built Phase 0 industry object**, so those
15 objects are reused instead of re-researched. 32 chosen by priority, **8 drawn at
random**, stratified by sector and market-cap tercile, disjoint from the priority arm.

The control arm is the point. Without it "priority surfaced N contradictions" is
unreadable — it could be N more than chance or fewer. You are not told which arm a
company is in, and you must not try to work it out.

FICO is in the batch again despite being researched two days ago: it carries four
contradiction flags, and priority weighs unresolved contradictions above freshness.
Treat it as a fresh look, not a confirmation.

## Cost expectation, stated honestly

Arm 2 cost 2 searches because the corpus was already cached from arm 1 and Phase 0.
**That is not the cost of this batch.** These are cold companies. Arm 1's rate — about
29 searches for 3 companies — is what sizes it: budget roughly **300-400 searches**.
If it runs materially over that, stop and report rather than pushing through.

## Prompt

````
# COMPANY LAB — E43, FIRST FULL BATCH: 40 COMPANIES

Request: C:\Users\<your-user>\company_lab\journal\flags\external_research_request.json
request_id 1358af92f8227af46c5d. Echo it back verbatim. The roster is frozen; a ticker
you add is rejected by name.

Phase 0 is in the catalog: 15 industry objects, 11 sector briefs, 109 claims, 90
verified by local re-fetch. Every company in this batch belongs to one of those 15
industry objects. READ THE OBJECT FIRST. Do not re-derive industry-level facts per
company - `industry_structural_growth` comes FROM the industry object.

  D:\company_lab_data\external\research\industries\<industry_id>\industry_state.json
  D:\company_lab_data\external\research\sectors\<sector_id>\sector_state.json

Each object also lists what Phase 0 could NOT establish. Those are your starting
hypotheses, already priced.

## THE ONE QUESTION THIS SYSTEM EXISTS TO ANSWER

Three companies can look identical in the accounts:

  a moat that is STRONG
  a moat that is STRENGTHENING
  a moat that still reads strong in the financials but is DETERIORATING underneath

Only the third is dangerous, and the financial history cannot tell them apart because it
is a record of what already happened. Separating them is the entire job. FICO scored a
conviction of 41.7 and ranked last in the pilot on exactly this basis, while its
historical economics remained exceptional.

So for every company, `moat_trajectory` is the field to get right, and it is the one
most likely to disagree with the numbers in front of you.

## THE CITATION RULE, AND ITS EXTENSION

EVERY non-UNKNOWN categorical needs at least one claim whose `field` names it, or return
UNKNOWN. The finalizer demotes uncited assertions to UNKNOWN automatically and lists
them; a demoted field scores NO_DATA and contributes nothing.

NEW, AND IMPORTANT: **when you research a field and CANNOT establish it, cite the claims
that blocked you.** Leave the field UNKNOWN and attach the evidence that prevented a
conclusion.

In the pilot you did this for Vertiv without being asked - you cited Eaton's and
Schneider's own growth specifically to block the inference that Vertiv's growth was
share capture, and the claim text said so. Then the citation rule was added, it only
demanded claims for non-UNKNOWN fields, and you stopped. The system lost the ability to
tell "we looked hard and could not establish this" from "nobody looked", and the
conviction gate then gave its top label to the one company whose capture was unproven.

Both are UNKNOWN. They are not the same finding, and only the claims behind them make
the difference visible. An UNKNOWN with blocking claims is a RESULT. An UNKNOWN with
nothing behind it is a gap.

## HOW TO CITE

`field` on a claim is one of the categorical names below. One claim backs one field.

The same SOURCE may back several fields - cite it once per field, each with its own
claim_id and its own quote from the part of the document that supports THAT field.
Never reuse a quote across fields; if the quote does not support the field, neither
does the claim.

A `CONTRADICTS` claim is a full citizen. It can back UNKNOWN, back a LOW reading, or
block an optimistic one. Your best pilot claims were of this kind.

  current_moat_strength        NONE | WEAK | MODERATE | STRONG | EXCEPTIONAL | UNKNOWN
  moat_trajectory              DETERIORATING | WEAKENING | STABLE | STRENGTHENING | UNKNOWN
  competitive_position         LAGGARD | CHALLENGER | STRONG_NUMBER_TWO | LEADER | DOMINANT | UNKNOWN
  competitive_position_trend   DETERIORATING | STABLE | IMPROVING | UNKNOWN
  industry_structural_growth   DECLINING | FLAT | MODERATE | HIGH | EXCEPTIONAL | UNKNOWN
  company_specific_capture     NONE | LOW | MODERATE | HIGH | UNKNOWN
  demand_visibility            NONE | LOW | MODERATE | HIGH | UNKNOWN
  market_share_direction       LOSING | FLAT | GAINING | UNKNOWN
  pricing_power                NONE | LOW | MODERATE | HIGH | UNKNOWN
  technology_risk              SEVERE | ELEVATED | MODERATE | LOW | UNKNOWN
  disruption_risk              SEVERE | ELEVATED | MODERATE | LOW | UNKNOWN
  regulatory_risk              SEVERE | ELEVATED | MODERATE | LOW | UNKNOWN
  cheapness_quality            STRUCTURAL | TEMPORARY | CYCLICAL | NOT_CHEAP | UNKNOWN

`cheapness_quality` NO LONGER SCORES. You told us twice it had no source-backed
classification, and you were right - valuation is already 15 measured points computed
from multiples, peers and a reverse DCF. Answer it only if a source actually supports
it; UNKNOWN is expected and costs nothing.

## THE TWO-PASS RULE

PASS A - BLIND. The request carries identity, the measured metrics and VERBATIM 10-K
evidence. It does NOT carry what the local model concluded, and that file will not be
given to you until pass A is written for all 40.

PASS B - RECONCILIATION. Then ask for
`journal\flags\external_research_conclusions.json` and add `pass_b.reconciliation`
per disagreement, citing claim_ids. Do not rewrite pass A.

Three companies in the roster carry NO filing evidence at all (CASH, FNB, MCY) - the
local model found no verifiable quote for them. Say so in your report; that is a gap in
our half, not yours.

## SELF-CHECK BEFORE REPORTING

  cd C:\Users\<your-user>\company_lab
  $env:PYTHONPATH="C:\Users\<your-user>\company_lab"
  .venv\Scripts\python.exe -m clab.external.finalize D:\company_lab_data\external\payloads\1358af92f8227af46c5d.json

Read-only without --apply. It prints accepted, rejected with reasons, unanswered, the
per-company backing table and every field it demoted. Fix what it flags before
reporting.

## WHAT THE FINALIZER REFUSES

Each is a passing test, not a wish:

  request_id, spec_fingerprint or a non-today request  -> WHOLE payload refused
  a ticker outside the frozen roster                   -> that company rejected
  external_score, rating, rank, price_target, recommendation, high_conviction,
    at top level or hidden inside pass_a               -> that company rejected
  a categorical outside its vocabulary                 -> that company rejected
  research_depth outside 0-4, or a bool                -> that company rejected
  a text field over its cap                            -> that company rejected
  a missing pass_a                                     -> that company rejected
  a quote absent from its own excerpt                  -> that company rejected
  a duplicate claim_id within one company              -> that company rejected
  verify_status supplied in a claim                    -> discarded, never read

We then FETCH YOUR URLS OURSELVES. 90 of Phase 0's 109 claims and 32 of 32 pilot claims
were verified that way, and the unverifiable rate is reported.

## BUDGET

Arm 2 of the pilot cost 2 searches because the corpus was already cached. THESE ARE COLD
COMPANIES. Arm 1's rate - roughly 29 searches for 3 - is what sizes this: expect
300-400 searches. If you run materially over that, STOP and report rather than pushing
through. Cached sources are free and must be reused; several of these companies share an
industry and will share sources.

## RULES THAT DID NOT CHANGE

1. You never produce a score, rank, rating or point total. We compute every number.
2. You never apply a gate.
3. Every claim: source_url, source_date, VERBATIM quote <=300 chars, ~1500-char excerpt
   you actually read. The quote must appear in the excerpt.
4. UNKNOWN is NOT the bottom of any scale. It scores as NO_DATA, never zero.
5. Never invent a number.
6. One organisation gets ONE independence_domain for the whole record. A domain resting
   on a single claim is not independence.
7. A unit member's own IR is the weakest source available - use it for facts only that
   company can state, never to support a structural conclusion about its industry.
8. Advisory only. "status": "SHADOW". Nothing here is promoted.

## OUTPUT

D:\company_lab_data\external\payloads\1358af92f8227af46c5d.json, same shape as the
pilot: request_id, spec_fingerprint, completed_at, cost, and `companies[]` each with
`pass_a`, `pass_b.reconciliation`, `claims[]`, `refresh_class`,
`next_suggested_refresh`.

## REPORT AT THE END

1. Per company: fields backed, fields left UNKNOWN, and for each UNKNOWN whether it is
   a RESULT (blocking claims attached) or a GAP (nothing found).
2. Claims, distinct sources, distinct independence domains.
3. Searches and cache hits against the 300-400 expectation.
4. Every conclusion you believe but could not evidence. That list was the most useful
   thing in the pilot.
5. Any company where `moat_trajectory` disagreed with the measured financial history,
   and what the evidence was. That is the finding this system exists to produce.

## WHAT YOU MUST NOT CLAIM

This ranking is NOT validated: top decile ran a -7.6% median 3-year excess return
against SPY on a survivorship-free holdout, only 45.3% beat SPY, and 95.6% of its
ranking power is sector selection. `promoted` is false and stays false. No
recommendations, no price targets, no claims about future returns.
````

## Afterwards

```powershell
.venv\Scripts\python.exe -m clab.external.finalize D:\company_lab_data\external\payloads\1358af92f8227af46c5d.json --apply
.venv\Scripts\python.exe -m clab.external.verify --apply
.venv\Scripts\python.exe -m clab.external.score --version "2026-09-02+E43-batch1" --apply
.venv\Scripts\python.exe -m clab.export.xlsx_external --version "2026-09-02+E43-batch1"
.venv\Scripts\python.exe -m clab.research.e42_compare --a "2026-09-02+E42-cited" --b "2026-09-02+E43-batch1"
```

Then the question the control arm exists to answer: **did the priority arm surface more
contradiction flags per company than the random arm?**
