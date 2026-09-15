# Codex E45 — the rest of the covered pool

Request `71245bc7adbc298fd13e` built and staged. 45 companies, none previously
researched. 36 priority + 9 matched control.

## What changed since E44, and it affects your work directly

**`market_share_direction` is now COMPUTED for regional banks — do not research it.**

You reported for all 40 E44 companies exactly what would settle it, and for 19 regional
banks the answer was consecutive FDIC Summary of Deposits institution-by-market tables.
That is now built: `clab/external/marketshare.py` pulls the full SOD, matches the
holding company on an exact normalised name plus a deposit-to-market-cap scale guard,
compares only markets held in **both** years, excludes any market where deposits jumped
more than 40% as an acquisition rather than capture, and abstains below 3 shared markets
or 60% deposit coverage.

55 of 89 regional banks resolve. It filled 16 of E44's 19 banks.

**So for the 20 regional banks in this batch, leave `market_share_direction` UNKNOWN and
say "computed from FDIC SOD" as the blocking reason.** Spend the search budget on the
fields the FDIC cannot answer. If you *do* find a document that establishes direction,
report it — a disagreement between your reading and our computation is a contradiction
worth surfacing, and our number never overwrites yours.

Nothing else changed. `cheapness_quality` is still retired. The citation rule and the
blocking-claims rule are unchanged, and E44 hit them perfectly: zero demotions across
327 fields and all 153 UNKNOWNs carrying blocking claims, G = 0.

## The field that is now the binding constraint

`competitive_position_trend` came back UNKNOWN for **all 40** companies in E44, and your
own note said why: *"current filings describe company performance much better than
competitor-relative movement."*

That single field is what keeps 38 of 40 companies below the coverage floor. It is worth
more of your attention in this batch than anything else. Two angles that were not tried:

- **Rank-order rather than share.** You do not need a share series to say a company's
  position is improving; you need the same metric for named competitors over the same
  two periods. For banks: NIM, deposit growth, efficiency ratio. For insurers: combined
  ratio, premium growth. Those are in everyone's filings.
- **The industry object already holds competitor lists.** `key_participants` is
  populated for all 15 objects. Use it as the comparison set rather than searching for
  one.

If it stays UNKNOWN, say precisely what blocked it. If it becomes answerable this way,
that is the most valuable finding available in this batch.

## Prompt

````
# COMPANY LAB — E45: 45 COMPANIES, THE REST OF THE COVERED POOL

Request: C:\Users\<your-user>\company_lab\journal\flags\external_research_request.json
request_id 71245bc7adbc298fd13e. Echo it verbatim. The roster is frozen.

Every company belongs to one of the 15 Phase 0 industry objects. Read the object and
the sector brief FIRST. `industry_structural_growth` comes FROM the industry object -
do not re-derive it per company.

  D:\company_lab_data\external\research\industries\<industry_id>\industry_state.json
  D:\company_lab_data\external\research\sectors\<sector_id>\sector_state.json

Mix: 20 regional banks, 5 P&C insurers, 5 payments, 5 midstream, 4 semiconductor
equipment, 3 life insurance, 1 refining, 1 cybersecurity, 1 cloud infrastructure.

## THE QUESTION THIS SYSTEM EXISTS TO ANSWER

Three companies can look identical in the accounts:

  a moat that is STRONG
  a moat that is STRENGTHENING
  a moat that still reads strong in the financials but is DETERIORATING underneath

Only the third is dangerous, and the financial history cannot separate them because it
is a record of what already happened.

Eight found so far: FICO (+17.6% 3y CAGR, lender choice ending its exclusive GSE
position), PYPL, FISV, JKHY, KNSL, ALL (46% ROE with Protection Plans income down
11.7%), OKE (27.0% CAGR with crude shipments declining), TFIN (24.6% operating margin
with NIM down 28bp). None of that is visible in a CAGR.

For a bank the shape is a growing loan book with deposit costs eroding the spread. For
an insurer it is premium growth with reserve quality decaying. `moat_trajectory` is the
field most likely to disagree with the numbers in front of you.

## DO NOT RESEARCH market_share_direction FOR REGIONAL BANKS

It is now COMPUTED from the FDIC Summary of Deposits - your own recommendation from
E44, built. Consecutive years, identical geographies, acquisition-sized jumps excluded,
abstaining below 3 shared markets or 60% deposit coverage. 55 of 89 regional banks
resolve.

For the 20 banks here, leave the field UNKNOWN and give the blocking reason as
"computed from FDIC Summary of Deposits". Spend the budget elsewhere.

If you nonetheless find a document that genuinely establishes direction, report it. Our
computed number NEVER overwrites a researched one - a disagreement is a contradiction we
want to see, not something to bury.

For the other industries, keep naming what WOULD settle it, exactly as in E44. That list
is what built the FDIC ingest, and NAIC direct-written-premium is the obvious next one.

## THE FIELD THAT NOW MATTERS MOST

`competitive_position_trend` was UNKNOWN for ALL 40 companies in E44. Your own note said
why: current filings describe a company's own performance far better than its position
against named peers. That single field is what keeps most companies below the evidence
floor.

Two angles not tried yet:

  RANK-ORDER, NOT SHARE. You do not need a market-share series to say a position is
  improving - you need the SAME METRIC for NAMED COMPETITORS over the SAME TWO PERIODS.
  Banks: NIM, deposit growth, efficiency ratio. Insurers: combined ratio, premium
  growth, reserve development. Semis equipment: service revenue, tool backlog. All of
  it is in everyone's filings.

  THE COMPETITOR LIST ALREADY EXISTS. `key_participants` is populated in all 15
  industry objects. Use it as the comparison set instead of searching for one.

If it stays UNKNOWN, say precisely what blocked it. If this makes it answerable, that is
the most valuable thing you can produce in this batch.

## THE RULES, UNCHANGED

Every non-UNKNOWN categorical needs a claim whose `field` names it, or return UNKNOWN.
E44 needed ZERO demotions across 327 fields - hold that.

When you research a field and CANNOT establish it, cite the claims that BLOCKED you. An
UNKNOWN with blocking claims is a RESULT; an UNKNOWN with nothing behind it is a GAP.
E44 returned 153 UNKNOWNs and every one was a result. Hold that too.

The twelve fields:

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

`cheapness_quality` is RETIRED. Do not answer it, do not search for it.

ONE NOTE ON THE RISK FIELDS. In E44, REGULATORY_IMPAIRMENT fired for 39 of 40 companies
and inside regional_banking both risk flags fired for 19 of 19 - two distinct flag-sets
across nineteen banks. "Banking is regulated" is an industry constant, not a finding
about a bank. Those flags are now PEER-RELATIVE: a company must be worse than its
industry peers for one to fire. So answer the risk fields RELATIVE TO THIS COMPANY'S
INDUSTRY, not on an absolute scale. A bank with ordinary banking regulation is
MODERATE, not ELEVATED.

## TWO PASSES

PASS A - BLIND. Identity, measured metrics, verbatim 10-K evidence. Five companies carry
no filing evidence (CVBF, EWBC, GPN, NBTB, WU) - a gap in our half, not yours.

PASS B - then ask for journal\flags\external_research_conclusions.json and add
`pass_b.reconciliation` per disagreement, citing claim_ids. Do not rewrite pass A.

## SELF-CHECK BEFORE REPORTING

  cd C:\Users\<your-user>\company_lab
  $env:PYTHONPATH="C:\Users\<your-user>\company_lab"
  .venv\Scripts\python.exe -m clab.external.finalize D:\company_lab_data\external\payloads\71245bc7adbc298fd13e.json

Read-only without --apply. Fix what it flags.

## STANDING RULES

1. No score, rank, rating, price target or gate. We compute every number.
2. Every claim: source_url, source_date, VERBATIM quote <=300 chars, ~1500-char excerpt
   you actually read. The quote must appear in the excerpt. We fetch your URLs
   ourselves; the corpus unverifiable rate is 0.40% and should stay there.
3. UNKNOWN is NOT the bottom of any scale. It scores as NO_DATA, never zero.
4. Never invent a number.
5. One organisation gets ONE independence_domain for the whole record.
6. A company's own IR is the weakest source available.
7. Advisory only. "status": "SHADOW". Nothing is promoted.

## BUDGET

E44 cost 295 searches for 40 companies. This is 45, but 20 of them are banks whose
market-share field you are NOT researching, and they share an industry object and
sources. Budget 280-350. Stop and report if you go materially over.

## REPORT AT THE END

1. Per company: fields backed, fields UNKNOWN, each marked R (blocking claims) or G.
2. `competitive_position_trend`: did the rank-order approach work for ANY company? For
   which, and on what metric? This is the headline of the batch.
3. Every non-bank `market_share_direction` UNKNOWN: the specific disclosure that would
   settle it.
4. Claims, sources, independence domains, searches, cache hits.
5. Every company where moat_trajectory disagreed with the financial history.
6. Every conclusion you believe but could not evidence.

## WHAT YOU MUST NOT CLAIM

This ranking is NOT validated: top decile ran a -7.6% median 3-year excess return
against SPY on a survivorship-free holdout, only 45.3% beat SPY, and 95.6% of its
ranking power is sector selection. `promoted` is false and stays false.
````

## Afterwards

```powershell
.venv\Scripts\python.exe -m clab.external.finalize D:\company_lab_data\external\payloads\71245bc7adbc298fd13e.json --apply
.venv\Scripts\python.exe -m clab.external.verify --apply
.venv\Scripts\python.exe -m clab.external.marketshare --apply-to "2026-09-02+E45-rest"
.venv\Scripts\python.exe -m clab.external.score --version "2026-09-02+E45-rest" --apply
.venv\Scripts\python.exe -m clab.export.xlsx_external --version "2026-09-02+E45-rest"
```

Close Excel first or the exporter writes `_PENDING.xlsx`.

After E45 the covered pool is 127 of 226 researched, and the funnel comparison has 17
control companies across E44 and E45 rather than 8 — the first sample large enough for
the priority-versus-chance question to mean something.
