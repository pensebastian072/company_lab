# Codex E61 - Industrials Phase A

Phase A only. The current book has 263 Industrials companies in 27 research units. Four
companies already point to two existing research objects, leaving 259 companies in 25
unbuilt units for E61. No company research, request file or roster is part of this run.

The fenced prompt is self-contained. Paste it into a fresh research session.

## Prompt

`````
# COMPANY LAB - E61 PHASE A: INDUSTRIALS INDUSTRY OBJECTS

Work in:

  repository: C:\Users\<your-user>\company_lab
  research tree: D:\company_lab_data\external

Phase A only. Build and verify Industrials industry objects. Do not research companies,
create a company roster, run `clab.external.request`, run `clab.external.finalize`, or
touch `journal\flags\external_research_request.json`.

Everything remains advisory / SHADOW. `promoted` is false everywhere and no code path
may set it true.

## EXACT STARTING DENOMINATOR

The live book contains 263 Industrials companies in 27 research units. Two objects
already exist and must not be overwritten by E61:

  datacenter_power_cooling       ETN VRT
  us_credit_scoring              EFX TRU

`us_credit_scoring` is deliberately cross-sector and also covers FICO outside
Industrials. Do not put EFX or TRU back into `research_consulting_services` merely to make
the sector self-contained.

E61 starts with 259 companies in the following 25 unresolved units. Twenty-five is the
starting taxonomy count, not a target to preserve if research proves a unit incoherent.

## STARTING UNITS AND MEMBERS

  aerospace_defense                              27
    AIR ATI AVAV AXON BA BWXT CW GD GE HII HONA HWM HXL KRMN KTOS LHX LMT MOG-A
    NOC NPK PSN RTX SARO TDG TXT VSEC VVX

  agricultural_farm_machinery                     4
    AGCO CNH DE TTC

  air_freight_logistics                            6
    CHRW EXPD FDX GXO HUBG UPS

  building_products                               27
    AAON ALLE AOS APOG AWI BCC BLDR CARR FBIN FERG GFF JCI LII LPX MAS MBC NX OC
    ROCK RUN SSD TREX TT UFPI WMS WOR WTS

  cargo_ground_transportation                     14
    ARCB FDXF HTLD JBHT KNX LSTR MRTN ODFL R RXO SAIA SNDR WERN XPO

  commercial_printing                              2
    BRC DLX

  construction_engineering                        20
    ACA ACM AGX APG DY ECG EME FIX FLR GVA IESC J MTZ MYRG PRIM PWR ROAD STRL TPC
    TTEK

  construction_machinery_heavy_transportation_equipment 14
    ALG ALSN ASTE CAT CMI FSS GATX GBX OSK PCAR RUSHA TEX TRN WAB

  data_processing_outsourced_services              7
    BR CNXC EXLS G MBGL MMS VRRM

  diversified_support_services                    13
    AMTM CACI CPRT CTAS CXW KBR LDOS LQDT OPLN RBA SAIC UNF VSTS

  electrical_components_equipment                 14
    AME AYI EMR ENS HAYW MRCY NVT NXT POWL ROK RRX ST VICR WWD

  environmental_facilities_services                9
    ABM CLH CWST GEO HCSG ROL RSG VLTO WM

  heavy_electrical_equipment                        3
    AZZ GEV GNRC

  human_resource_employment_services               10
    ADP FA KFY MAN NSP PAYC PAYX PCTY RHI UPWK

  industrial_conglomerates                          5
    CSL CSW DD HON MMM

  industrial_machinery_supplies_components         44
    AIN ATMU CR CRS DCI DOV EPAC ESAB ESE FELE FLS FTV GGG GTES GWW HUBB IEX IR
    ITT ITW JBTM KAI KMT LECO MFP MIDD MLI MWA NDSN NPO OTIS PH PNR PRLB RBC SNA
    SPXC SWK SXI TKR TNC VMI XYL ZWS

  marine_transportation                             2
    KEX MATX

  office_services_supplies                          6
    HNI MLKN MSA PBI TILE WSC

  passenger_airlines                                8
    AAL ALGT ALK DAL JBLU LUV SKYW UAL

  passenger_ground_transportation                   3
    CAR LYFT UBER

  rail_transportation                               3
    CSX NSC UNP

  research_consulting_services                      6
    BAH EXPO FCN LZ ULS VRSK

  security_alarm_services                           1
    BCO

  technology_distributors                           1
    NSIT

  trading_companies_distributors                   10
    AIT CNM DNOW DXPE FAST MSM REZI URI WCC WSO

## TAXONOMY CHECKPOINT COMES BEFORE OBJECT CONSTRUCTION

E56 showed that an incoherent shared unit can return UNKNOWN on every industry field,
making a supposedly efficient bucket less useful than several narrow objects. E57 then
showed that a coherent-looking report can still attach evidence mechanically to the
wrong fields. Do not repeat either failure merely to finish exactly 25 objects.

Before writing any new `industry_state.json`:

1. Read the live book rows for all 259 names and recompute the membership through
   `clab.external.taxonomy.industry_id`; do not trust this prompt if the book has moved.
2. Read the existing `datacenter_power_cooling` and `us_credit_scoring` objects and the
   Industrials sector state. Preserve the two existing objects.
3. Test whether each starting unit has shared customers, economics, cycle, regulatory
   regime and metrics. Pay particular attention to these broad or mixed buckets:

   - `industrial_machinery_supplies_components` (44)
   - `aerospace_defense` (27)
   - `building_products` (27)
   - `diversified_support_services` (13)
   - `human_resource_employment_services` (10)
   - `environmental_facilities_services` (9)
   - `data_processing_outsourced_services` (7)
   - `industrial_conglomerates` (5)

4. Write `D:\company_lab_data\external\reports\E61_industrials_taxonomy_checkpoint.md`
   with every proposed keep/split decision, the economic reason, and exact ticker map.
5. If a split is necessary, edit only the Industrials entries in
   `clab/external/taxonomy.py`, add focused taxonomy tests, run them, and recompute the
   roster before research. A one-company object is allowed when it describes a real
   industry with private or foreign competitors. It is not allowed merely to isolate a
   difficult company.

If you cannot defend a taxonomy change from evidence, keep the starting unit and flag it
for review. Do not invent a split to improve answer rate.

## OBJECT CONTRACT

Use a current object as the schema template, but do not copy its conclusions. Each new
object must contain:

  industry_id, sector_id="industrials", version="2026-09-08", status="SHADOW"
  structural_growth
  market_structure
  key_participants
  moat_mechanism
  replication_difficulty
  technology_trajectory
  regulatory_trajectory
  substitution_risk
  key_metrics
  refresh_class
  next_refresh_due
  claims
  last_updated

Enforced vocabularies:

  structural_growth        DECLINING | FLAT | MODERATE | HIGH | EXCEPTIONAL | UNKNOWN
  replication_difficulty   LOW | MODERATE | HIGH | EXTREME | UNKNOWN
  substitution_risk        SEVERE | ELEVATED | MODERATE | LOW | UNKNOWN
  refresh_class            STRUCTURAL | QUARTERLY | EVENT_DRIVEN

The sector object is updated rather than recreated. Its `major_industries` must include
every active research unit used by an Industrials company after the taxonomy checkpoint,
including the two pre-existing objects where appropriate. Do not overwrite their industry
states.

## ONE FIELD, ONE SEMANTIC RECEIPT

Quote containment is necessary and not sufficient. E57 passed 66 of 66 literal quote
checks while a later field-by-field audit found that only 11 passages directly supported
the complete field claim. The builder had assigned each of three source windows to a
fixed pair of fields.

Do not create a `FIELD_SOURCE_INDEX` or any equivalent pairing shortcut.

- One claim backs one field.
- Never attach an identical quote/excerpt window to two fields.
- The same URL may be used twice only when two genuinely different passages establish
  two different facts; create separate claims and explain the distinction.
- For each non-UNKNOWN categorical, provide a claim whose passage directly supports that
  categorical's field, scope and direction.
- Support the material assertions in `market_structure`, `moat_mechanism`,
  `technology_trajectory`, `regulatory_trajectory` and `key_metrics` with field-specific
  receipts. A generic company description is not a replication-difficulty receipt; a
  regulatory proposal is not a realized outcome; a metric used by one segment is not an
  industry metric without a scope argument.
- Compare peer metrics only on the same period, definition and economic basis. If the
  bases differ, say so and do not rank them.
- Distinguish proposed, approved, implemented and realized events.

Aim for at least eight field-specific claims and three genuinely independent
organizations per object. If that cannot be reached, do not manufacture a domain or pad
with context. Return UNKNOWN where the evidence rule requires it and document the search
trail.

## METRICS TO START THE RESEARCH, NOT ANSWERS TO COPY

  aerospace_defense
    funded and unfunded backlog, book-to-bill, deliveries, program mix, fixed-price
    versus cost-plus exposure, aftermarket, defense budgets and program milestones

  agricultural_farm_machinery
    farm income, crop prices, large-ag retail demand, dealer inventory, production
    schedules, replacement age, precision-ag adoption and recurring revenue

  air_freight_logistics
    package or tonnage volume, yield, fuel surcharge, network density, international
    mix, contract logistics backlog, service level and capital intensity

  building_products
    housing starts, repair and remodel, nonresidential construction, backlog, price-cost,
    channel inventory, installed base, code exposure and distribution share

  cargo_ground_transportation
    tonnage or loads, yield per shipment or mile, operating ratio, contract versus spot,
    load-to-truck balance, fleet utilization, fuel surcharge and driver availability

  commercial_printing
    print and mail volume, postage exposure, recurring program revenue, digital mix,
    customer concentration and substitution by electronic communications

  construction_engineering
    awards, backlog, book-to-bill, funded infrastructure, project and customer mix,
    fixed-price exposure, change orders, cost overruns and working capital

  construction_machinery_heavy_transportation_equipment
    unit orders, dealer inventory, replacement cycle, rental utilization, production,
    parts and service mix, freight equipment orders and used-equipment prices

  data_processing_outsourced_services
    retention, bookings, backlog, transaction or seat volumes, revenue per employee,
    automation, offshore mix, client concentration and contract margins

  diversified_support_services
    name the operating unit first; do not force government IT, uniforms, auctions,
    corrections, food service and salvage economics onto one metric set

  electrical_components_equipment
    orders, backlog, book-to-bill, channel inventory, automation and electrification
    exposure, capacity, price-cost, service mix and end-market concentration

  environmental_facilities_services
    collection pricing, route density, landfill airspace, waste or remediation volume,
    facility labor, recurring contracts, PFAS and hazardous-waste regulation

  heavy_electrical_equipment
    grid and generation equipment orders, backlog, capacity, turbine deliveries,
    service agreements, warranty exposure and policy-supported demand

  human_resource_employment_services
    payroll clients, worksite employees, retention, float income, temporary-help volume,
    bill and pay rates, bookings, recruiter productivity and platform take rate

  industrial_conglomerates
    segment mix, organic growth, order and backlog mix, portfolio changes, corporate
    costs, capital allocation and whether a shared industry comparison is meaningful

  industrial_machinery_supplies_components
    define the machinery segment before choosing metrics; candidates include orders,
    backlog, aftermarket or consumables mix, installed base, price-cost, capacity,
    distributor inventory and end-market exposure

  marine_transportation
    charter rates, utilization, contract duration, vessel supply, Jones Act exposure,
    port volumes, fuel and dry-dock capex

  office_services_supplies
    unit or square-foot demand, commercial renovation, office occupancy, dealer channel,
    recurring supplies, price-cost and digital substitution

  passenger_airlines
    capacity, passenger unit revenue, unit cost ex fuel, load factor, loyalty economics,
    fleet and order book, labor contracts and net debt

  passenger_ground_transportation
    trips, bookings, gross bookings, take rate, active riders and drivers, utilization,
    fleet economics, insurance cost and local regulation

  rail_transportation
    carloads, revenue ton-miles, yield, operating ratio, velocity, dwell, service levels,
    labor, capex and regulatory requirements

  research_consulting_services
    organic growth, backlog, utilization, bill rates, headcount, retention, government or
    regulated-data exposure and contract mix; exclude EFX and TRU

  security_alarm_services
    cash-in-transit or security-service volumes, route density, recurring contracts,
    labor, insurance, customer concentration and electronic substitution

  technology_distributors
    billings, gross-versus-net revenue basis, gross margin, working capital, inventory,
    vendor concentration, cloud marketplace mix and channel consolidation

  trading_companies_distributors
    daily sales, backlog, price-cost, gross margin, working capital, inventory turns,
    branch density, supplier and customer concentration and rental utilization

`key_participants` is the comparison set for later company research. Name real private
and foreign competitors, not only companies in this book. Do not infer market leadership
from revenue size alone.

## THE TWO ERRORS COST THE SAME

There are two ways to be wrong here and they are equally bad.

  ASSERTING what you cannot evidence.   A categorical with no claim naming that field is
                                        removed by the finalizer. It corrupts the score
                                        and it wastes the search that produced it.

  ABSTAINING when you could have        An UNKNOWN on a field that the evidence would
  established it.                       have supported is a silent loss. It costs the
                                        company real points - the score divides by what
                                        APPLIES, not by what you answered - and unlike a
                                        bad assertion nothing in the pipeline catches it.

Neither is the safe choice. UNKNOWN is not a way to avoid being wrong; it is a different
way to be wrong, and it is the one that leaves no trace.

For every field you leave UNKNOWN, say in the report which you were closer to: was the
evidence genuinely absent, or did you stop short? An honest "I stopped short" is more
useful to us than a confident blocking claim, and it costs you nothing.

## WHAT UNKNOWN MEANS

UNKNOWN means the evidence to establish this field does not exist or could not be
reached. It does NOT mean:

  - the answer is uncertain          -> give the answer your evidence supports
  - the answer is mid-range          -> MODERATE and STABLE are real values, use them
  - peers are hard to compare        -> say so AND give your best-evidenced reading
  - the field feels risky to answer  -> that is the abstention error, see above

UNKNOWN scores as NO_DATA and never as zero, so it does not drag a company down relative
to its peers. That is exactly why it is tempting and exactly why it must be earned.

## CITATIONS ARE REQUIRED, AND THEY ARE NOT A REASON TO ABSTAIN

Every non-UNKNOWN categorical needs a claim whose `field` names it. That rule exists to
stop unbacked assertion, NOT to discourage answering. If you can evidence a field, cite
it and answer it. If the citation requirement is what is stopping you from answering a
field you believe you could establish, say so explicitly in the report - that is a
finding about our process and we want it.

## THE BLIND PASS - DO NOT OPEN A CONCLUSIONS FILE, ASK FOR IT

`journal\flags\external_research_conclusions.json` holds what our local model concluded
(SG and BQ). It is withheld during pass A on purpose, and it is now withheld
MECHANICALLY - it is not written to disk until we release it.

  1. Write pass A from the request and your own research only.
  2. FREEZE it: write `<request_id>.pass_a.json` and tell us it is frozen.
  3. We release the conclusions and record your frozen pass A's sha256.
  4. Then write pass B reconciliation. Never edit pass A afterwards - the hash will not
     match and we will see it.

If a conclusions file is present before step 3, it is stale from an earlier request.
**Do not read it. Say it is there.** You are not being asked to resist temptation; if
you can see it, that is our bug and we want to know.

For this Phase A object run there is no request and no pass A/B company reconciliation.
The rule still applies: do not open or use a conclusions file.

## COMPETITIVE_POSITION_TREND - ATTEMPT IT ONLY WHERE A SHARED METRIC EXISTS

Do not spend searches forcing this one. Measured across four sectors:

  works    banks (NIM), insurers (combined ratio), oilfield services (operating margin)
           - 27 of 45 in E45, 11 of 52 in Energy
  fails    regulated utilities - 0 of 59, TWICE, and correctly: authorised ROE is set per
           rate case on different schedules by different commissions, and rate-base CAGR
           moves with capex plans that are not comparable

The rule: name the metric FIRST. If the peers in this industry file a shared metric on a
comparable basis over the same two periods, rank-order on it and answer. If they do not,
return UNKNOWN with "no comparable two-period peer metric" and move on - one blocking
claim, not a search campaign.

We built a computed version to replace this and REFUSED it: 36% agreement against your
researched values where chance alone predicts 34.3%, Cohen's kappa 0.026, and it got the
sign wrong as often as right. So there is no fallback. Where you do not establish it, it
stays empty, and that is accepted.

**This carve-out is for THIS FIELD ONLY.** It is not licence to abstain elsewhere, and
the two-errors rule above still governs the other eleven. A carve-out that spreads is how
the last collapse happened.

## CLAIM AND SOURCE RULES

1. No score, rank, rating, price target or gate. Company Lab computes every number.
2. Every claim needs `source_url`, `source_date`, a verbatim quote no longer than 300
   characters, and an excerpt actually read. The quote must appear literally in the
   excerpt.
3. Use primary filings, regulators, official statistics, standards bodies and credible
   competitor disclosures where available. A company's IR is the weakest source.
4. One organization gets one `independence_domain`. A company, its IR site and its filing
   are not independent organizations.
5. Never invent a number, date, source, quote, competitor or search count.
6. UNKNOWN is NO_DATA, never zero.
7. Every object and the sector object have `status: "SHADOW"`.
8. Do not optimize for a verification rate. Report literal containment and semantic
   support separately, with exact denominators.

## BUILD, VALIDATE AND REPORT

Write new objects under:

  D:\company_lab_data\external\research\industries\<industry_id>\industry_state.json
  D:\company_lab_data\external\research\industries\<industry_id>\industry_brief.md

Update:

  D:\company_lab_data\external\research\sectors\industrials\sector_state.json
  D:\company_lab_data\external\research\sectors\industrials\sector_brief.md

Write the run report to:

  D:\company_lab_data\external\reports\E61_industrials_phase_a.md

Run `clab.external.research_ingest` in dry-run mode first. Do not apply to the DuckDB
store until every object and the sector object pass the local schema and the taxonomy
receipt matches the live book. After apply, run `clab.external.verify --apply`, then read
the store back by exact `industry_id` and version. When counting object claims, filter by
the Phase A request-id pattern; `external_claim.industry_id` is also populated on company
claims.

The report must include:

1. Starting roster and final roster, with exact counts and every taxonomy change.
2. Each object, member count, claim count, distinct URLs, hosts and genuine independence
   domains.
3. Every UNKNOWN, its search trail, and whether evidence was absent or work stopped short.
4. Literal quote-containment results and a separate field-specific semantic-support
   audit. Report the number of identical quote/excerpt windows reused across fields; the
   expected value is zero.
5. For every broad bucket named in the taxonomy checkpoint, the keep/split verdict and
   economic reason.
6. Searches, page fetches and cache hits as separate counts. Do not call a cache replay a
   search.
7. Exact store readback after ingestion and verification. Do not treat the generated
   report as store evidence.

Budget 350-550 searches for taxonomy plus the starting 25 units. Stop and report before
going materially over 600. A partial, clearly receipted result is preferable to invented
completion.

## WHAT YOU MUST NOT CLAIM

This ranking is not validated. Its top decile ran a -7.6% median three-year excess return
against SPY on a survivorship-free holdout, only 45.3% beat SPY, and 95.6% of ranking
power came from sector selection. Completing Industrials buys coverage and a more honest
research instrument. It does not establish predictive power. `promoted` remains false.
`````
