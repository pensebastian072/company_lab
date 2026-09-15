# Codex E44 — the funnel test, for real this time

Request `1d7df1eb255e193553a5` built and staged. 40 companies, none previously
researched.

## Why this batch exists

E43 asked whether the priority engine finds more contradictions than chance and could
not answer, because the two arms landed in almost disjoint industries. Flags turned out
to be an industry property — `us_credit_scoring` 3.00 per company, `payments` 0.31,
`pc_insurance` 0.12, four industries 0.00 — and each arm's observed flag rate equalled
what its industry mix alone predicted, **to three decimals**. Neither arm explained
anything.

Two design fixes, both mine to make:

1. **The control is now MATCHED to the priority arm's industry mix.** Control industries
   are a strict subset of priority's, so the comparison is within-stratum by
   construction.
2. **Previously researched companies are excluded from both arms.** Priority re-picks
   flagged companies by design — the first E44 draw pulled 12 of them, which would have
   loaded the priority arm with companies already known to carry flags and let it win
   circularly. Re-research is legitimate; it just cannot sit inside the arm being
   measured.

You are not told which arm any company is in, and must not try to work it out.

## What changed in the contract

**`cheapness_quality` is retired.** Across all 46 records ever stored it came back
UNKNOWN in 42, and exactly one claim in the whole corpus cites it. Under the citation
rule that is 1 of 43 answered. It is gone from the prompt — do not spend a search on it.
Valuation is already 15 measured points computed from multiples, peers and a reverse
DCF. **Twelve fields are asked and twelve are scored.**

**`market_share_direction` gets one extra instruction.** It came back as a *result*
(blocking claims attached, direction unestablished) for 34 of 40 companies in E43 — the
most common unresolved field in the layer, and the one that would most change
`company_specific_capture` if it could be settled. So when you leave it UNKNOWN, name
**which specific disclosure would have settled it**. That turns 34 dead ends into a
costed shopping list for data we might buy.

## Prompt

````
# COMPANY LAB — E44: 40 COMPANIES, MATCHED CONTROL

Request: C:\Users\<your-user>\company_lab\journal\flags\external_research_request.json
request_id 1d7df1eb255e193553a5. Echo it verbatim. The roster is frozen.

Every company belongs to one of the 15 Phase 0 industry objects. READ THE OBJECT AND
THE SECTOR BRIEF FIRST; do not re-derive industry facts per company.
`industry_structural_growth` comes FROM the industry object.

  D:\company_lab_data\external\research\industries\<industry_id>\industry_state.json
  D:\company_lab_data\external\research\sectors\<sector_id>\sector_state.json

This batch is heavily weighted to regional_banking (19 of 40), pc_insurance (6),
refining (4) and midstream (3). That concentration is deliberate - it is what the
priority engine chose from the fresh pool - and it means the industry objects will do a
lot of work. Use them.

## THE QUESTION THIS SYSTEM EXISTS TO ANSWER

Three companies can look identical in the accounts:

  a moat that is STRONG
  a moat that is STRENGTHENING
  a moat that still reads strong in the financials but is DETERIORATING underneath

Only the third is dangerous, and the financial history cannot separate them because it
is a record of what already happened.

E43 found five: FICO on +17.6% three-year revenue CAGR with lender choice ending its
exclusive GSE position; PYPL +6.3% with flat active accounts and margin contraction;
FISV +4.2% with declining merchant revenue; JKHY +7.0% with contracting operating
income; KNSL +24.7% with declining gross written premiums. None of that is visible in a
CAGR. Finding the same shape here is the highest-value thing you can do.

Banks and insurers have their own version of it: a bank can grow loans while deposit
costs erode the spread, and an insurer can grow premium while reserve quality decays.
`moat_trajectory` is the field most likely to disagree with the numbers in front of you.

## THE CITATION RULE

Every non-UNKNOWN categorical needs at least one claim whose `field` names it, or return
UNKNOWN. Uncited assertions are demoted automatically and listed. E43 needed zero
demotions across 377 fields - hold that standard.

AND when you research a field and CANNOT establish it, cite the claims that BLOCKED you.
Leave the field UNKNOWN and attach the evidence that prevented a conclusion. An UNKNOWN
with blocking claims is a RESULT; an UNKNOWN with nothing behind it is a GAP. Only the
claims make the difference visible, and the conviction gate reads it.

NEW FOR market_share_direction: it was a RESULT for 34 of 40 companies in E43 - looked
at, blocked, unestablished. It is the field that would most change
`company_specific_capture` if it could be settled. So whenever you leave it UNKNOWN,
add ONE LINE to your report naming the specific disclosure that would have settled it -
a named competitor's segment breakout, a regulator's market-share table, an industry
association series. Be concrete enough that someone could go and buy it.

## THE TWELVE FIELDS

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

`cheapness_quality` IS RETIRED. Do not answer it, do not search for it. Across 46
records it was UNKNOWN in 42 and exactly one claim in the corpus cites it. Valuation is
already 15 measured points of the framework.

## SECTOR-SPECIFIC EVIDENCE FOR THIS BATCH

  regional_banking   NIM, deposit costs and deposit beta, non-interest-bearing mix,
                     credit losses and reserve build, CET1, loan growth by category,
                     branch/deposit share in named markets (FDIC deposit-market-share
                     data is a real share series - use it)
  pc_insurance       combined ratio, reserve development, rate versus loss trend,
                     catastrophe load, premium growth versus the cycle
  life_insurance     product mix, persistency, spread compression, reserve conservatism
  refining           crack spreads, capture rate, turnaround schedule, regional
                     advantage, renewable-diesel conversion economics
  midstream          contracted capacity, take-or-pay share, recontracting risk,
                     basin exposure, project returns
  upstream_oil_gas   breakeven, reserve life, lifting cost, capex discipline

For banks and insurers the industry object already carries the structural picture -
your job is the COMPANY's position inside it.

## THE TWO-PASS RULE

PASS A - BLIND. Identity, measured metrics, verbatim 10-K evidence. It does NOT carry
what the local model concluded. Six companies carry no filing evidence at all (CVI,
HBAN, INDB, KEY, MTB, PRI) - that is a gap in our half, not yours; say so.

PASS B - then ask for journal\flags\external_research_conclusions.json and add
`pass_b.reconciliation` per disagreement, citing claim_ids. Do not rewrite pass A.

## SELF-CHECK BEFORE REPORTING

  cd C:\Users\<your-user>\company_lab
  $env:PYTHONPATH="C:\Users\<your-user>\company_lab"
  .venv\Scripts\python.exe -m clab.external.finalize D:\company_lab_data\external\payloads\1d7df1eb255e193553a5.json

Read-only without --apply. Fix what it flags before reporting.

## RULES THAT DID NOT CHANGE

1. No score, rank, rating, price target or gate. We compute every number.
2. Every claim: source_url, source_date, VERBATIM quote <=300 chars, ~1500-char excerpt
   you actually read. The quote must appear in the excerpt. We fetch your URLs
   ourselves - the corpus unverifiable rate is currently 0.77% and should stay there.
3. UNKNOWN is NOT the bottom of any scale. It scores as NO_DATA, never zero.
4. Never invent a number.
5. One organisation gets ONE independence_domain for the whole record.
6. A company's own IR is the weakest source - use it for facts only that company can
   state, never for a structural conclusion about its industry.
7. Advisory only. "status": "SHADOW". Nothing is promoted.

## BUDGET

E43 cost 302 searches for 40 cold companies. This batch is more concentrated - 19 of 40
are regional banks sharing one industry object and, in several cases, the same FDIC and
Fed sources - so expect FEWER searches and more cache hits. Budget 250-350. If you go
materially over, stop and report.

## REPORT AT THE END

1. Per company: fields backed, fields UNKNOWN, each UNKNOWN marked R (result, blocking
   claims attached) or G (gap, nothing found).
2. For EVERY market_share_direction left UNKNOWN: the specific disclosure that would
   have settled it.
3. Claims, distinct sources, distinct independence domains, searches, cache hits.
4. Every company where moat_trajectory disagreed with the measured financial history,
   and the evidence. This is the finding the system exists to produce.
5. Every conclusion you believe but could not evidence.

## WHAT YOU MUST NOT CLAIM

This ranking is NOT validated: top decile ran a -7.6% median 3-year excess return
against SPY on a survivorship-free holdout, only 45.3% beat SPY, and 95.6% of its
ranking power is sector selection. `promoted` is false and stays false.
````

## Afterwards

```powershell
.venv\Scripts\python.exe -m clab.external.finalize D:\company_lab_data\external\payloads\1d7df1eb255e193553a5.json --apply
.venv\Scripts\python.exe -m clab.external.verify --apply
.venv\Scripts\python.exe -m clab.external.score --version "2026-09-02+E44-matched" --apply
.venv\Scripts\python.exe -m clab.export.xlsx_external --version "2026-09-02+E44-matched"
```

Then, for the first time, the funnel question has an answer: **within matched
industries, did the priority arm surface more contradiction flags than the random one?**
