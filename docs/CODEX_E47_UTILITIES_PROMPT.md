# Codex E47 - Utilities, complete

Second sector under the complete-sector approach. 59 companies, **0 researched**, and
**every one of its industry objects still to build**. The sector brief already exists
from Phase 0.

Energy's ordering held up, so it is repeated: Phase A builds the industry objects, then
Phase B researches the companies against them.

## The taxonomy was fixed BEFORE staging this time

Energy taught this at a price. Codex correctly refused to describe `coal_consumable_fuels`
as one thing - Centrus enriches uranium, Peabody mines coal - and that refusal cost all
three member companies their `industry_structural_growth`, `replication_difficulty` and
`substitution_risk`. The fix was the taxonomy, and it came after the research.

Utilities has the same defect and it has been fixed up front. **CEG, VST, TLN and NRG
are now `competitive_power_generation`**, out of the regulated buckets:

- GICS files CEG and VST under Electric Utilities beside DUK, SO and PEG, and files TLN
  under Independent Power Producers. None of the four earns a regulated return.
- A rate-regulated utility is researched on rate base growth, allowed ROE, regulatory lag
  and the posture of its state commission. A competitive generator is researched on power
  prices, capacity auctions, PPA pricing, the hedge book and nuclear production credits.
  An object covering both is true of neither.
- The measured half corroborates it on the metric that most encodes *is this revenue
  guaranteed by a regulator*: net debt / EBITDA is **5.2-6.6x** across the regulated
  fleet (DUK 5.2, SO 5.3, EXC 5.6, PEG 5.9, NEE 6.4, D 6.6) and **2.9-3.6x** for CEG and
  VST. A merchant cash flow cannot carry rate-base leverage.
- TLN sitting in a different GICS bucket from CEG while running the same business - a
  nuclear fleet contracted to hyperscalers - is the FICO-split-across-sectors case
  exactly.

**AES is knowingly left alone** in `independent_power_producers_energy_traders`. It owns
AES Indiana and AES Ohio, which are rate-regulated, alongside international development.
A one-company object is a real cost and it is accepted rather than forcing AES into a
unit half its business does not belong to. Pinned by a test so nobody "fixes" it later.

Seven objects over 59 companies:

| industry_id | n | members |
|---|---:|---|
| `electric_utilities` | 20 | AEP DUK EIX ES ETR EVRG EXC FE HE IDA LNT MGEE OTTR PEG POR PPL SO TXNM UTL WEC |
| `multi_utilities` | 17 | AEE AVA BKH CMS CNP D DTE ED MDU NEE NI NWE OGE PCG PNW SRE XEL |
| `gas_utilities` | 9 | ATO CPK NFG NJR NWN OGS SR SWX UGI |
| `water_utilities` | 6 | AWK AWR CWT HTO MSEX WTRG |
| `competitive_power_generation` | 4 | CEG NRG TLN VST |
| `renewable_electricity` | 2 | CWEN ORA |
| `independent_power_producers_energy_traders` | 1 | AES |

## What the measured half says about this sector, and why it matters here

Utilities is the sector where our own measured half has the least to offer, and it is
worth being precise about how.

```
band mix        REJECT 47   INSUFFICIENT_DATA 10   WEAK 2   above WEAK: 0
top score       VST 59      book max 87      book median 49   utilities median 39

component      max   utils med   book med   utils as % of max
VA              15         3.0        8.0                20%
BS              10         3.0        6.0                30%
FE              18         6.0        7.0                33%
SG              20        11.0       10.0                55%   <- the only one we beat
```

Not one utility in the book scores above WEAK. VA runs at 20% of max against 53% for the
rest of the book, and BS at 30% against 60%.

**But the components are shifted, not dead.** The E30 discrimination test inside the
sector: VA takes 10 distinct values, sd 2.08, largest single value only 31% of companies.
It still separates companies; it separates them at a lower level. That distinction is the
whole point - a flat field would be a defect to fix, a shifted field is the framework
telling the truth about rate-base leverage and regulated returns.

So within-sector ranking works and `sector_neutral_score` already carries it. What the
external layer adds here is **evidence**, not a rescue.

## Two phases

| phase | work |
|---|---|
| A | 7 industry objects, all new |
| B | 59 companies, request `a9dcab461a277de4f72a` |

**Phase B is now staged.** Energy finalized on 2026-09-04 and freed the request file, so
both phases can be handed over together. `require_citation` is on, as it was for E45 and
E46.

The id does not expire; the timestamp does. `generated_at` is not in the content hash, so
rebuilding this roster reproduces `a9dcab461a277de4f72a` exactly - take as many days as
the work needs, echo that id whatever day you finish, and the same-day guard is satisfied
locally by restaging on the day the payload lands. A rebuild returning a DIFFERENT id
would mean the book had moved under the roster, which makes id stability the drift check.

## Prompt - PHASE A

`````
# COMPANY LAB - E47 PHASE A: SEVEN UTILITIES INDUSTRY OBJECTS

Utilities, complete, one sector at a time. 59 companies, none researched, all seven
industry objects still to build. The sector brief already exists - READ IT FIRST and
update it rather than recreating it:

  D:\company_lab_data\external\research\sectors\utilities\sector_state.json

Template for an object, from Phase 0:

  D:\company_lab_data\external\research\industries\upstream_oil_gas\industry_state.json

Build these seven:

  electric_utilities            20 companies - vertically integrated and T&D regulated
                                electrics
  multi_utilities               17 - combination gas and electric. Contains NEE, whose
                                FPL is a regulated utility and whose Energy Resources
                                arm is the largest US renewables developer. Say in
                                market_structure whether that mix makes the bucket
                                coherent
  gas_utilities                  9 - regulated local gas distribution
  water_utilities                6 - regulated water and wastewater
  competitive_power_generation   4 (CEG NRG TLN VST) - see below, this is the object
                                that matters most
  renewable_electricity          2 (CWEN ORA) - a yieldco and a geothermal developer.
                                If two companies cannot share an object, say so
  independent_power_producers_energy_traders   1 (AES) - a knowing one-company object

Vocabularies, enforced by clab/external/schema.py:

  structural_growth        DECLINING | FLAT | MODERATE | HIGH | EXCEPTIONAL | UNKNOWN
  replication_difficulty   LOW | MODERATE | HIGH | EXTREME | UNKNOWN
  substitution_risk        SEVERE | ELEVATED | MODERATE | LOW | UNKNOWN
  refresh_class            STRUCTURAL | QUARTERLY | EVENT_DRIVEN

## THE OBJECT THAT MATTERS MOST

`competitive_power_generation` is the reference point every other Utilities object is
judged against, the way integrated_oil_gas was for Energy - and it is the one place in
this sector where the business is not a regulated monopoly.

These four earn market-based returns. Research them on power prices by market (ERCOT,
PJM), capacity auction clearing prices and design changes, bilateral PPA pricing to
hyperscalers, hedge book duration, retail churn and gross margin, nuclear capacity
factors, and the 45U nuclear production tax credit floor.

Note the split inside it and describe it rather than averaging it: CEG and TLN are
generation-led nuclear fleets; VST and NRG pair generation with large competitive retail
books, which is why NRG operating margin is 6.2% against CEG 18.5%. That gap is retail
mix, not quality.

## DO NOT RE-RESEARCH THE DATACENTER LOAD STORY

`datacenter_power_cooling` already exists as an object (VRT, ETN) and carries the
equipment side of datacenter power demand. Utilities load growth is the SAME phenomenon
seen from the demand side.

READ that object and stay consistent with it. If your Utilities research CONTRADICTS what
it says, that is a finding worth reporting explicitly - do not quietly diverge.
Researching one industry fact twice is the most expensive mistake available here.

## METRICS THAT MATTER, TO SEED key_metrics

  electric_utilities / multi_utilities / gas_utilities / water_utilities
        rate base and its growth rate, authorized ROE, authorized equity ratio,
        regulatory lag, forward test years, rate case outcomes and pending filings,
        the commission posture, load growth, capex plan and how it is financed,
        FFO/debt against the rating agency threshold, and equity issuance as a share of
        the capex plan
  competitive_power_generation
        realized power price, capacity factor, capacity revenue, PPA pricing and tenor,
        hedge percentage by year, retail customer count and churn, 45U PTC floor,
        heat rate
  renewable_electricity
        PPA price and tenor, contracted vs merchant mix, cash available for distribution,
        development pipeline, ITC/PTC treatment, resource quality
  independent_power_producers (AES)
        the regulated / development split, country risk, asset recycling proceeds,
        parent-level leverage

`key_participants` matters as much as it did for Energy - it is the comparison set Phase
B uses for `competitive_position_trend`. For regulated utilities the meaningful
comparison set is peers **before the same or a comparable state commission**, not a
national peer list: a utility in a constructive jurisdiction and one in a hostile one are
not competing. Name the commission.

Then STOP and report before Phase B.

## STANDING RULES

1. No score, rank, rating, price target or gate. We compute every number.
2. Every claim: source_url, source_date, VERBATIM quote <=300 chars, ~1500-char excerpt
   you actually read. The quote must appear in the excerpt. We fetch your URLs ourselves;
   the corpus unverifiable rate is 0.25% and should stay there.
3. UNKNOWN is NOT the bottom of any scale. It scores as NO_DATA, never zero. An UNKNOWN
   with claims behind it is a RESULT; one with nothing behind it is a GAP.
4. Never invent a number.
5. One organisation gets ONE independence_domain for the whole record. A state
   commission and the utility it regulates are different domains; a utility and its own
   IR page are not.
6. Advisory only. "status": "SHADOW". Nothing is promoted.

## BUDGET

Seven objects, several of them sharing a regulatory literature. Budget 80-120 searches
for Phase A. Stop and report if you go materially over.

## REPORT

The 7 objects; claims and independence domains each; every UNKNOWN with what blocked it;
and explicitly, for `multi_utilities`, `renewable_electricity` and the AES object,
whether the bucket held together as one thing.

## WHAT YOU MUST NOT CLAIM

This ranking is NOT validated: top decile ran a -7.6% median 3-year excess return against
SPY on a survivorship-free holdout, only 45.3% beat SPY, and 95.6% of its ranking power
is sector selection. `promoted` is false and stays false.
`````

## Phase B - the shape of it, for when the request is issued

Not a prompt yet; the pieces that are already decided, so the day Energy lands this is a
staging command and a paste.

**The roster file is ALPHABETICAL**, not grouped - `request.py:147` sorts by ticker
unconditionally. Every row carries its own `industry_id`. Group by that and work the
groups in this order, so a crash leaves whole industries finished:
`competitive_power_generation` (4) -> `electric_utilities` (20) -> `multi_utilities` (17)
-> `gas_utilities` (9) -> `water_utilities` (6) -> `renewable_electricity` (2) ->
`independent_power_producers_energy_traders` (1).

**Five companies carry no filing evidence: AWR, CPK, NI, POR, SR.** An earlier revision of
this file said there was no gap; that was measured wrong - it checked whether a qual
payload EXISTS, which it does for all 59, not whether the payload carries extracted
quotes. Those five have none. It is a gap in our half, not Codex's.

**The utilities version of the accounts-are-not-the-company warning.** Energy's was that
a producer's revenue is a record of the oil price. The utilities version is sharper: a
regulated utility's revenue is a record of **its last rate case**. Revenue grew because a
commission allowed it to. The company-level questions are whether the capex plan is being
earned on with acceptable lag, whether equity issuance is diluting the rate-base growth,
whether the commission relationship is deteriorating, and whether load growth is real or
contracted-and-not-yet-built.

**`market_share_direction` is close to meaningless for a regulated monopoly** and must
not be forced. A utility does not contest share inside its franchise territory. Expect
UNKNOWN with the blocking reason stated, and put load and customer growth under
`demand_visibility` instead. For the four competitive generators share IS contestable -
state PUCs and ERCOT publish retail provider market share, and EIA-861 publishes retail
sales and customer counts by provider, which is the closest thing this sector has to the
FDIC Summary of Deposits.

**The one place a risk flag should fire.** Risk fields stay peer-relative - "utilities are
regulated" is a sector constant and carries no information. But wildfire liability is
genuinely peer-relative *within* utilities: HE and PCG are not ordinary utilities on this
axis. The peer-relative rule exists to stop 39-of-40 flagging, not to suppress a real
difference between members of the same industry.

**`competitive_position_trend`, E45 rank-order method.** Shared metrics: authorized ROE
and achieved-vs-authorized ROE against named peers; rate base CAGR; regulatory lag in
months; O&M per customer. For the competitive four: realized price per MWh, capacity
factor, hedge percentage.

**Budget estimate:** 59 companies, heavily clustered (20 + 17 in two objects sharing a
regulatory literature). 400-500 including Phase A.

## Afterwards (Phase A only)

```powershell
.venv\Scripts\python.exe -m clab.external.research_ingest --apply
```

## The order after Utilities

| sector | companies | objects needed | already done |
|---|---:|---:|---:|
| energy | 71 | 4 | in flight |
| **utilities** | **59** | **7** | **0** |
| communication_services | 47 | 10 | 0 |
| consumer_staples | 75 | 11 | 0 |
| materials | 77 | 16 | 0 |
| real_estate | 105 | 15 | 2 |
| financials | 257 | 15 | 87 |
| health_care | 163 | 10 | 0 |
| information_technology | 190 | 11 | 15 |
| consumer_discretionary | 193 | 28 | 0 |
| industrials | 263 | 25 | 4 |

Communication services is next on company count (47), but it needs 10 objects for those
47 - the worst objects-per-company ratio on the board. Financials is 87 deep already and
15 objects from finished, which makes it the cheapest *large* sector to complete and the
better third target.
