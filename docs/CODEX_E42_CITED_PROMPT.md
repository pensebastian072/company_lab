# E42 arm 2 — the citation rule

Same three companies, same roster, one rule added. This measures whether the evidence
density the external layer needs is purchasable, before anything is spent on forty.

## Arm 1, measured

```
39 categoricals asserted   14 claims   0.39 claims per non-UNKNOWN assertion
only 10 of 36 non-UNKNOWN assertions had a claim naming that field
29 searches, 5 cache hits
```

Replaying arm 1's payload through the citation rule prices it exactly: **10 of 36
fields survive**. FICO keeps 4, NVDA 4, VRT 2. Everything else was asserted with
nothing behind it — `current_moat_strength: EXCEPTIONAL`, `moat_trajectory: STABLE`,
`competitive_position_trend: IMPROVING`.

## The bar

`EXTERNAL_MIN_COVERAGE` is 0.80, matching the framework's own band gate. With 13
ordinal fields per company that means **11 of 13 backed** before a company gets an
external score at all. Across three companies that is roughly **33 claims against arm
1's 14** — about 2.4x.

Whether that is buyable is the question. If it costs 3x the searches, forty companies
is a different budget conversation and it is better to have it now.

## Requests

| arm | request_id | rule |
|---|---|---|
| 1 (done) | `812721fe9a0d87fd6b72` | none |
| 2 (this) | `d2b5f81d5335a87baedf` | `require_citation: true` |

Distinct ids on purpose — a run label is part of `research_version`, so arm 2 cannot
overwrite the arm it is being compared against.

```powershell
cd C:\Users\<your-user>\company_lab
$env:PYTHONPATH="C:\Users\<your-user>\company_lab"
.venv\Scripts\python.exe -m clab.external.request --symbols FICO,VRT,NVDA --sample E42-cited --require-citation
```

Already built and staged. Rebuild only if the NY day has turned.

## Prompt

````
# COMPANY LAB — E42 ARM 2: THE CITATION RULE

Same three companies as the last run: FICO, VRT, NVDA. Same roster, same two-pass
structure, same vocabularies. ONE RULE IS ADDED, and it is enforced in code rather than
asked for.

Request: C:\Users\<your-user>\company_lab\journal\flags\external_research_request.json
request_id d2b5f81d5335a87baedf. Echo it back verbatim.

## THE RULE

EVERY non-UNKNOWN categorical must have at least one claim whose `field` names it.
Otherwise return UNKNOWN for that field.

The finalizer enforces this. Any non-UNKNOWN categorical with no claim citing it is
DEMOTED to UNKNOWN and listed in a `demoted` report. It is not a rejection - your cited
fields survive untouched - but a demoted field scores as NO_DATA and contributes
nothing, so an uncited assertion is simply wasted work.

Your last run asserted 39 categoricals against 14 claims. Only 10 of the 36 non-UNKNOWN
assertions had a claim naming that field. Under this rule that run would keep FICO 4
fields, NVDA 4, VRT 2, and all three would fall below the coverage floor and receive no
external score.

## WHAT THIS IS NOT ASKING FOR

It is NOT asking you to fill all 13 fields. UNKNOWN remains a correct, expected answer
and it is what you should return whenever the evidence is not there. Six well-cited
fields beat thirteen thinly cited ones, and manufacturing a claim to unlock a field is
the failure this rule exists to prevent - it would convert an honest UNKNOWN into a
fabricated citation, which is far worse than the gap.

The question being measured is simply: WHEN YOU TRY, how much of the picture can
actually be evidenced? Answer that honestly and the answer is useful either way.

## HOW TO CITE

`field` on a claim must be one of the categorical names. One claim backs one field.

The same SOURCE may back several fields - that is normal and correct. Cite it once per
field, each as its own claim with its own claim_id and its own quote taken from the part
of the document that actually supports THAT field. Do not reuse one quote across fields;
if the quote does not support the field, the claim does not either.

A claim may also back a field by CONTRADICTING a favourable reading. Your Eaton and
Schneider claims for Vertiv did this well - they cited competitors' own growth
specifically to block the inference that Vertiv's growth equals share gain, and the
claim text said so. `stance: CONTRADICTS` on a claim that names `market_share_direction`
is a fully valid way to back UNKNOWN or LOSING.

The 13 categorical fields:

  current_moat_strength        moat_trajectory
  competitive_position         competitive_position_trend
  industry_structural_growth   company_specific_capture
  demand_visibility            market_share_direction
  pricing_power                technology_risk
  disruption_risk              regulatory_risk
  cheapness_quality

`industry_structural_growth` may be backed by a claim already in the industry object
you read - re-cite it as your own claim with the same source and quote. That is reuse,
not duplication, and it is free.

## EVERYTHING ELSE IS UNCHANGED

- Two passes. Pass A blind, then ask for the conclusions file and write pass B. Do not
  rewrite pass A.
- Read the industry object and sector brief first. Your three map to
  us_credit_scoring, ai_accelerators, datacenter_power_cooling.
- Every claim: source_url, source_date, VERBATIM quote <=300 chars, ~1500-char excerpt.
  The quote must appear in the excerpt. We fetch your URLs ourselves afterwards.
- One organisation gets one independence_domain for the whole record.
- No score, no rank, no rating, no price target, no gate. We compute every number.
- UNKNOWN is NOT the bottom of the scale. It scores as NO_DATA, never zero.
- Never invent a number.
- Advisory only. Nothing here is promoted.

## THE CALIBRATION CASES STILL APPLY

FICO must still come back as a moat that disagrees with its own financial history.
VRT must still separate industry growth from company capture. NVDA must still answer
whether it is maintaining or losing relative advantage rather than "AI is growing".

Arm 1 got all three right. If the citation rule costs you those answers, that is a
finding worth reporting, not a failure to hide - say which conclusions you could reach
but not evidence.

## REPORT AT THE END

1. Per company: fields backed, fields left UNKNOWN, and for each UNKNOWN one line on
   what evidence would have settled it.
2. Claims written, distinct sources, distinct independence domains.
3. Searches and cache hits, against arm 1's 29 searches / 5 cache hits.
4. Any conclusion you believe is true but could not evidence. That list is the real
   output of this arm.

## WHAT YOU MUST NOT CLAIM

This ranking is NOT validated: top decile ran a -7.6% median 3-year excess return
against SPY on a survivorship-free holdout, only 45.3% beat SPY, and 95.6% of its
ranking power is sector selection. `promoted` is false and stays false.
````

## Afterwards

```powershell
.venv\Scripts\python.exe -m clab.external.finalize D:\company_lab_data\external\payloads\d2b5f81d5335a87baedf.json
.venv\Scripts\python.exe -m clab.external.finalize D:\company_lab_data\external\payloads\d2b5f81d5335a87baedf.json --apply
.venv\Scripts\python.exe -m clab.external.verify --apply
```

The finalizer prints the backing table and the demotion list for both arms, so the
comparison is a diff of two numbers rather than an impression.
