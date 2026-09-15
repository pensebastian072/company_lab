# Codex E46 - Energy, complete

## STATE AS OF 2026-09-04

**Phase A is DONE and verified.** Five objects, not four: Codex built the four planned,
found `coal_consumable_fuels` incoherent because GICS had filed Centrus beside Peabody,
and split `uranium_enrichment` out. That refusal was correct and it is the reason the
taxonomy now carries a `LEU` override.

In the catalog, checked against the store:

```
coal_consumable_fuels  2026-09-02    structural_growth UNKNOWN     (superseded)
coal_consumable_fuels  2026-09-02.1  structural_growth DECLINING   BTU CNR
uranium_enrichment     2026-09-02    structural_growth HIGH        LEU
17 claims, 2 independence domains each, ALL VERIFIED_LOCAL, zero unverifiable
```

**Phase B has NOT run.** No payload exists at
`D:\company_lab_data\external\payloads\9e32692a515262b68bfd.json`. Codex correctly
stopped rather than spend the 52-company budget against the obsolete request
`91d9655d996160278823`, which still bound LEU to coal. That request is dead; every
reference below now points at `9e32692a515262b68bfd`.

Phase B is the outstanding work.


New approach: **one sector at a time, 100% of it.** No sampling, no priority arm, no
control arm. Every company in the sector gets researched so the sector ranking is a
ranking of the whole sector rather than of whoever got picked.

Energy is first because it is the cheapest complete sector on the board: 71 companies,
**19 already researched**, 3 of its 7 industry objects already built covering 44 of them.
Four new objects and 52 companies finishes it.

## What this changes

**The control arm is retired for this work, and it should be said plainly.** It existed
to answer "does priority beat chance at finding contradictions" — a question about how to
ration a scarce budget. A complete sector does not ration. After three batches and 85
companies the answer was inconclusive anyway: the arm effect was +0.016 flags per
company against an industry-mix expectation, and the only adequately powered stratum
(regional banking, 31 vs 8) went the wrong way. Complete sectors make the question moot
rather than answering it, and that is an honest trade.

The priority engine still has a job — deciding what to *refresh* — but it is no longer
being tested here.

## Two phases

| phase | work |
|---|---|
| A | 4 new industry objects: `integrated_oil_gas`, `oil_gas_equipment_services`, `oil_gas_drilling`, `coal_consumable_fuels` |
| B | 52 companies, request `9e32692a515262b68bfd` |

Phase A first. The 52 companies in phase B all belong to one of the seven Energy
industry objects, and three of those objects (`upstream_oil_gas`, `midstream`,
`refining`) already exist from Phase 0.

## Prompt

````
# COMPANY LAB — E46: THE ENERGY SECTOR, COMPLETE

New approach. One sector at a time, all of it. No sampling and no control arm - every
company in Energy gets researched, so the sector ranking ranks the sector rather than a
sample of it.

Energy: 71 companies. 19 are already researched and in the catalog. This is the other
52, plus the 4 industry objects they need.

## PHASE A - FOUR NEW INDUSTRY OBJECTS

Same shape and same rules as the Phase 0 objects already on disk. Read one of those
first as the template:

  D:\company_lab_data\external\research\industries\upstream_oil_gas\industry_state.json

Build:

  integrated_oil_gas            2 companies (XOM, CVX) - and this object matters far
                                beyond its member count, because it is the reference
                                point every other Energy industry is judged against
  oil_gas_equipment_services   18 companies - the largest Energy industry in the book
                                and the one with no object at all
  oil_gas_drilling              4 companies
  coal_consumable_fuels         3 companies - note this includes LEU (Centrus, enriched
                                uranium), which is NOT thermal coal. If the industry is
                                too heterogeneous to describe as one thing, SAY SO in
                                market_structure rather than averaging it away.

Vocabularies for an industry object, enforced by clab/external/schema.py:

  structural_growth        DECLINING | FLAT | MODERATE | HIGH | EXCEPTIONAL | UNKNOWN
  replication_difficulty   LOW | MODERATE | HIGH | EXTREME | UNKNOWN
  substitution_risk        SEVERE | ELEVATED | MODERATE | LOW | UNKNOWN
  refresh_class            STRUCTURAL | QUARTERLY | EVENT_DRIVEN

`key_participants` matters more than usual now: it is the comparison set phase B uses
for `competitive_position_trend`, and that field is what unlocked coverage in E45. Name
real competitors, including private and foreign ones the book does not contain -
Schlumberger's peers include private pressure-pumpers, and integrated oil's peers
include Shell, BP and TotalEnergies.

Metrics that matter, to seed `key_metrics`:

  oil_gas_equipment_services   international vs North America revenue mix, rig-count
                               sensitivity, service pricing, backlog, offshore vs
                               onshore exposure, technology/digital revenue
  oil_gas_drilling             dayrates, utilization, contract backlog and duration,
                               rig class (jackup, deepwater, land), newbuild overhang
  integrated_oil_gas           upstream breakeven, downstream capture, chemicals,
                               reserve replacement, capex discipline, buyback capacity
  coal_consumable_fuels        realized price vs benchmark, contracted volume, export
                               exposure, mine life, and for LEU: enrichment capacity,
                               SWU contracts, HALEU

Then STOP and report before phase B.

## PHASE B - 52 COMPANIES

Request: C:\Users\<your-user>\company_lab\journal\flags\external_research_request.json
request_id 9e32692a515262b68bfd. Echo it verbatim. The roster is frozen.

## THE ID DOES NOT EXPIRE. THE TIMESTAMP DOES.

Take as many days as this needs. `generated_at` is NOT part of the content hash - the id
is sha256 over roster + depth + spec + schema + sample only. Rebuilding the identical
roster reproduces `9e32692a515262b68bfd` exactly; only the timestamp moves. Verified.

So: echo `9e32692a515262b68bfd` whatever day you finish. Do not invent a new id, do not
wait for a new request, and do not truncate the batch to beat a clock. The finalizer's
same-day guard is satisfied locally by restaging the request the day your payload lands,
which changes nothing you can see.

One useful consequence: if a rebuild ever produced a DIFFERENT id, that would mean the
underlying book had changed under the roster. Id stability is the drift check.

CORRECTION, recorded rather than quietly edited: an earlier revision of this file
claimed the roster was ordered by industry. It never was. `request.py:147` sorts
the roster by ticker unconditionally, so the file is ALPHABETICAL and always has
been. Every row carries its own `industry_id`; group by that and work the groups in
this order, so a run interrupted by this box crashing leaves whole industries
finished rather than a scatter:

  oil_gas_equipment_services   18  AESI AROC BKR FTI HAL HLX INVX KGS LBRT NOV OII
                                   RES SEI SLB TDW VTOL WFRD WHD
  upstream_oil_gas             20  APA AR CHRD CNX COP CRC CRGY CRK DVN EOG FANG
                                   GPOR MGY MTDR MUR NOG OVV PR SM TALO
  coal_consumable_fuels         2  BTU CNR
  integrated_oil_gas            2  CVX XOM
  oil_gas_drilling              4  HP NE PTEN VAL
  midstream                     2  KMI VNOM
  uranium_enrichment            1  LEU
  refining                      3  PSX REX WKC

Note coal is TWO companies, not three, and LEU is its own industry. That is the taxonomy
correction you made, now frozen into the roster.

## THE QUESTION THIS SYSTEM EXISTS TO ANSWER

Three companies can look identical in the accounts:

  a moat that is STRONG
  a moat that is STRENGTHENING
  a moat that still reads strong in the financials but is DETERIORATING underneath

Only the third is dangerous, and the financial history cannot separate them because it
is a record of what already happened. Eleven companies have shown that shape so far,
including three from Energy - OKE at +27.0% three-year revenue CAGR with crude shipments
declining, and DINO.

Energy has its own version and it is the hardest case in the book: **a commodity
business's accounts are a record of the commodity price, not of the company.** A
producer's revenue tripling tells you what oil did, not whether the company got better.
Separate them. The company-level questions are breakeven, reserve life, lifting cost,
capital discipline through the cycle, and acreage quality - none of which move with the
price.

## THE RULES, UNCHANGED

Every non-UNKNOWN categorical needs a claim whose `field` names it, or return UNKNOWN.
E44 and E45 both hit zero demotions - hold that.

When you research a field and CANNOT establish it, cite the claims that BLOCKED you. An
UNKNOWN with blocking claims is a RESULT; one with nothing behind it is a GAP. E44 and
E45 returned 268 UNKNOWNs between them and every single one was a result. Hold that too.

`competitive_position_trend` - USE THE E45 METHOD. Rank-order against named peers on a
shared metric over the same two periods, not a market-share series. It resolved for 27
of 45 companies in E45 after being UNKNOWN for all 40 in E44, and it is what moved
companies over the evidence floor. For Energy the shared metrics are:

  upstream        breakeven, reserve replacement ratio, lifting cost per boe,
                  production growth per share
  equipment/svcs  revenue growth by geography, margin, backlog, book-to-bill
  drilling        dayrate, utilization, backlog duration
  refining        capture rate, crack realization, turnaround days
  midstream       throughput, contracted capacity, distribution coverage
  integrated      downstream capture, reserve replacement, breakeven

`market_share_direction` - for Energy there is no FDIC equivalent. Name what would
settle it, per company, as in E44 and E45. For upstream and drilling the EIA and state
regulators publish production and rig data by operator, which may be closer to reachable
than it looks.

RISK FIELDS ARE PEER-RELATIVE. A company must be worse than its INDUSTRY PEERS for a
risk flag to fire. "Oil and gas is a regulated, cyclical, carbon-exposed industry" is an
industry constant, not a finding about a company. An ordinary E&P carries MODERATE
regulatory risk, not ELEVATED. In E44 the absolute reading produced
REGULATORY_IMPAIRMENT on 39 of 40 companies and two distinct flag-sets across nineteen
banks, which is no information at all.

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

## TWO PASSES

PASS A - BLIND. Identity, measured metrics, verbatim 10-K evidence. Seven companies
carry no filing evidence (AR, CHRD, GPOR, LBRT, MTDR, PSX, PTEN) - a gap in our half.

PASS B - then ask for journal\flags\external_research_conclusions.json and add
`pass_b.reconciliation` per disagreement, citing claim_ids. Do not rewrite pass A.

## SELF-CHECK

  cd C:\Users\<your-user>\company_lab
  $env:PYTHONPATH="C:\Users\<your-user>\company_lab"
  .venv\Scripts\python.exe -m clab.external.finalize D:\company_lab_data\external\payloads\9e32692a515262b68bfd.json

Read-only without --apply. Fix what it flags before reporting.

## STANDING RULES

1. No score, rank, rating, price target or gate. We compute every number.
2. Every claim: source_url, source_date, VERBATIM quote <=300 chars, ~1500-char excerpt
   you actually read. The quote must appear in the excerpt. We fetch your URLs
   ourselves; the corpus unverifiable rate is 0.26% and should stay there.
3. UNKNOWN is NOT the bottom of any scale. It scores as NO_DATA, never zero.
4. Never invent a number.
5. One organisation gets ONE independence_domain for the whole record.
6. A company's own IR is the weakest source available.
7. Advisory only. "status": "SHADOW". Nothing is promoted.

## BUDGET

E45 cost 315 searches for 45 companies. This is 52 plus 4 industry objects, but the
companies cluster hard - 18 in equipment and services, 20 in upstream - and share
sources heavily. Budget 350-450 including phase A. Stop and report if you go materially
over.

## REPORT

Phase A: the 4 objects, claims and domains each, and every UNKNOWN with what blocked it.

Phase B:
1. Per company: fields backed, fields UNKNOWN, each marked R or G.
2. `competitive_position_trend`: which companies resolved and on what metric.
3. Every company where moat_trajectory disagrees with the financial history - and for
   Energy, say explicitly whether the accounts are moving with the COMMODITY or with
   the COMPANY.
4. Claims, sources, independence domains, searches, cache hits.
5. Every conclusion you believe but could not evidence.

## WHAT YOU MUST NOT CLAIM

This ranking is NOT validated: top decile ran a -7.6% median 3-year excess return
against SPY on a survivorship-free holdout, only 45.3% beat SPY, and 95.6% of its
ranking power is sector selection. `promoted` is false and stays false.
````

## Afterwards

```powershell
.venv\Scripts\python.exe -m clab.external.research_ingest --apply
.venv\Scripts\python.exe -m clab.external.finalize D:\company_lab_data\external\payloads\9e32692a515262b68bfd.json --apply
.venv\Scripts\python.exe -m clab.external.verify --apply
.venv\Scripts\python.exe -m clab.external.score --version "2026-09-02+E46-energy" --apply
.venv\Scripts\python.exe -m clab.export.xlsx_external --version "2026-09-02+E46-energy"
```

Close Excel first or the exporter writes `_PENDING.xlsx`.

That completes Energy: 71 of 71, and the `BySector` sheet becomes a ranking of the whole
sector rather than of a sample.

## The order after Energy

By cost to complete, cheapest first:

| sector | companies | objects needed | already done |
|---|---:|---:|---:|
| **energy** | 71 | 4 | 19 |
| communication_services | 47 | 10 | 0 |
| utilities | 59 | 6 | 0 |
| consumer_staples | 75 | 11 | 0 |
| materials | 77 | 16 | 0 |
| real_estate | 105 | 15 | 2 |
| financials | 257 | 15 | 87 |
| health_care | 163 | 10 | 0 |
| information_technology | 190 | 11 | 15 |
| consumer_discretionary | 193 | 28 | 0 |
| industrials | 263 | 25 | 4 |

Utilities is the natural second — 59 companies over only 6 industries, the most
concentrated sector in the book. Financials is 87 companies deep already but needs 15
more objects to finish, so it is a mid-project target rather than a next one.
