# E81 — the Industrials growth top-up, done in the Claude lane while Codex is down

Worked 2026-09-11 evening. Decision 1 of the approved master plan: lift the largest
Industrials units off 1 of 3 so their companies can be researched against an object that
concludes something. Artifacts only — the store is untouched and the workbook unchanged.

Advisory / SHADOW. `promoted` is false.

## Result

```
                                        before   after
objects answering structural_growth          1       9
Industrials objects at >=2 of 3              8      16
companies whose object is at >=2 of 3       43     107
claims added                                        11   all VERIFIED_LOCAL, all exact containment
```

Every one of the 11 was re-checked for **exact character containment** on its cited page,
not just `VERIFIED_LOCAL` — the overlap fallback certified none of them.

| unit | n | growth | source |
|---|---:|---|---|
| `construction_engineering` | 20 | DECLINING | Census C30: YTD $1,244.6bn vs $1,289.7bn, −3.5%; July −3.8% y/y |
| `building_materials_envelope` | 15 | DECLINING | FGIA (E79B) |
| `defense_mission_systems` | 13 | HIGH | FY2027 topline: $1.5tn requested, +42% |
| `passenger_airlines` | 8 | FLAT | IATA North America: RPK +1.5%, ASK +1.0% |
| `industrial_distribution` | 6 | MODERATE | Census MWTS NAICS 4238: +12.1% y/y |
| `water_infrastructure_analytics` | 5 | MODERATE | AWWA: $2.1–2.4tn need, 2026–2050 |
| `building_climate_controls` | 5 | DECLINING | AHRI via ACHR News: unit shipments −20% in 2025 |
| `construction_electrical_distribution` | 4 | HIGH | Census MWTS NAICS 4236: +30.8% y/y |
| `building_products_distribution` | 3 | FLAT | Census MWTS NAICS 4233: +3.9% y/y nominal |
| `agricultural_farm_machinery` | 4 | DECLINING | AEM (E79B) |

**DECLINING 4 · FLAT 2 · MODERATE 2 · HIGH 2.** A top-up that returned HIGH everywhere
would be the thing to distrust.

## Scope discipline — two numbers deliberately refused

The easy wrong answer was available in both cases, in the same document as the right one.

- **`industrial_distribution`.** The Census wholesale release leads with total merchant
  wholesaler sales of **$801.3bn, +13.0% y/y**. That is all wholesale trade, not this
  industry. The scope-correct line is NAICS **4238, machinery, equipment and supplies** —
  the census category these companies *are* — at +12.1%. Using the headline would have been
  a scope violation dressed as a bigger sample.
- **`passenger_airlines`.** IATA's headline is **5.2 billion passengers, +4.4%** globally.
  Every member of this unit is a US carrier, and IATA's own regional table puts North
  America at **+1.5% RPK** — a third of the global rate. The unit gets the regional number.

## Four values deliberately held down

Each of these could have been graded a notch higher and the reason it was not is recorded
with the claim:

- `industrial_distribution` MODERATE not HIGH — one month's y/y change, nominal dollars.
- `defense_mission_systems` HIGH not EXCEPTIONAL — a budget *request*, $350bn of it one-off
  reconciliation money, and primes recognise programme revenue over years.
- `water_infrastructure_analytics` MODERATE not HIGH — a **need** is a demand ceiling, and
  the same AWWA report documents the funding gap between need and actual utility spend.
- `building_products_distribution` FLAT not MODERATE — +3.9% nominal is roughly the price
  level, and it sits beside construction spending being down 3.5% in the same sector.

## Quoting a table row, on purpose

Four of the eleven quotes are table rows, e.g.

```
4236 ..Electrical 111,485 111,385 85,210 0.1 -1.2 30.8
```

The figures exist only in tables in these releases. A number retyped out of a table into
prose is no longer a quotation, and the verification audit found exactly that pattern among
the corpus's unlocatable quotes — narrative sentences assembled from table cells. So the row
is quoted verbatim and the claim text says what the columns are. This is also why the
whitespace-insensitive match mode matters: table text extracts with collapsed spacing.

## Sources that failed, so the next pass does not re-try them blind

- **faa.gov returns HTTP 403** to the repo fetcher, as `bts.gov` did. The FAA Aerospace
  Forecast is the natural source for `civil_aerospace_platforms_components` (15 companies)
  and it cannot be cited from here. AIA Facts & Figures is the next thing to try.
- **ahrinet.org serves its shipment figures through a script** — the page extracts 4.3KB
  with no numbers in it. AHRI's data was citable only through the trade press reporting it.
- **AEM publishes ag tractor and combine units publicly but not construction equipment
  shipments**, which leaves `off_highway_equipment` (6) without a free industry quantity;
  AEM's "construction output" figure is its customers' activity, not equipment demand.

## What remains

```
39 objects still at 1 of 3, holding 124 companies
largest: engineered_motion_components 25 · civil_aerospace_platforms_components 15 ·
         flow_filtration_equipment 9 (growth established as unobtainable, E79B) ·
         off_highway_equipment 6 · industrial_controls_sensors 5
2 objects at 0 of 3: cash_logistics and equipment_rental, the deliberate singletons, which
         by decision must name their foreign peers before they are rebuilt
```

`engineered_motion_components` is now the single biggest hole in the sector at 25 companies
after the folds, and it is the hardest: diversified machinery has no trade body publishing a
unit-scope quantity. Census M3 machinery shipments are the candidate, at the cost of a scope
argument about how much of that series this unit represents.

## Method, unchanged from E79B because it worked

A search finds the candidate; **the quote is taken from the text the verifier itself
extracts**, never from a search summary; the field judgement is made by hand; the merge
re-fetches and re-verifies rather than trusting the staging file, and cuts each excerpt from
the fetched page so an excerpt cannot be a frame around a quote that is not there.
`scripts/e79b_merge.py` now takes `--stage`, so every pass goes through that one merge
instead of growing a second one.

Staging record: `D:\company_lab_data\external\reports\E81_industrials_growth_claims.json`.
Artifact backup before the writes: `research\industries_backup_20260911-2113`.

---

# Part 2, same evening — ten more claims, eight more units

Codex is out of tokens, so this lane did the research as well as the instrument. All
artifacts; the store was not written by this work.

## Where Industrials stands now

```
                                       session start   now
objects at >=2 of 3 (Phase B eligible)       8          23
companies whose object is eligible          43         159
objects below 2 of 3                        49          34
companies blocked by a thin object         188          74
E81 claims                                   0          21   all exact containment
```

Claim mix, which is the check that this was evidence and not filling: `structural_growth`
11, `substitution_risk` 8, `replication_difficulty` 2. Values DECLINING 3, FLAT 4,
MODERATE 8, HIGH 2, ELEVATED 4. Sources PRIMARY_DATA 5, TRADE_PRESS 5, REGULATOR 1,
COMPETITOR_FILING 10 — so half the evidence is non-issuer, against E79's 0%.

## The eight units this part cleared

| unit | n | field | value | evidence |
|---|---:|---|---|---|
| `engineered_motion_components` | 25 | replication | MODERATE | ITW: "10,400 unexpired foreign patents covering articles, methods and machines" |
| `off_highway_equipment` | 6 | substitution | MODERATE | CAT: customers "extend preventative maintenance and delay overhauls"; TEX appraises used-equipment secondary values |
| `building_fixtures_access` | 5 | substitution | MODERATE | MAS: "significant competition from private label products and digitally native brands" |
| `commercial_vehicle_powertrain` | 4 | substitution | ELEVATED | PCAR already "producing battery-electric Kenworth, Peterbilt and DAF trucks"; CMI on markets adopting electrification |
| `rail_equipment_leasing` | 4 | substitution | MODERATE | GATX: "availability and relative cost of alternative modes of transportation" |
| `business_process_outsourcing` | 4 | replication | MODERATE | CNXC: "We operate globally in 74 countries across six continents" |
| `agricultural_farm_machinery` | 4 | substitution | ELEVATED | DE: used equipment's "value, age, and level" drives new sales; CNH says the same |
| *(part 1)* | | | | Census, AHRI, ATA, IATA, AWWA, FY27 topline |

`engineered_motion_components` is the one that matters most: 25 companies, the largest
Industrials unit after the folds, and it moved on a single patent count.

Five of the eight rest on **two members saying the same thing independently** — CAT and TEX,
PCAR and CMI, DE and CNH, MAS and ALLE, GATX and TRN. That is the test for a unit-level
reading, and it is why these are not one issuer's risk factor generalised.

## `civil_aerospace_platforms_components` — 15 companies, still UNKNOWN, and the record of why

The largest remaining hole, attempted and refused rather than filled:

- **faa.gov returns HTTP 403** to the fetcher, exactly as bts.gov does. The FAA Aerospace
  Forecast is the obvious source and cannot be cited from this box.
- **AIA's 2026 Facts & Figures gives a LEVEL, not a direction** — "$988.6 billion in total
  sales" — and its prior-year release says only "nearly $1 trillion in economic activity",
  so the two cannot be differenced into a growth rate. It also spans defense and space,
  which is the wrong scope for the civil unit.
- **Trade pages carrying the 2025 Boeing/Airbus delivery totals do not carry them in
  fetchable text** — two attempts, neither page yields the figures to the extractor.
- Substitution was also attempted, with PMA/used-serviceable-material vocabulary across
  TDG, HWM and GE: the filings return their own MRO businesses, not a substitute for them.

So the unit keeps `replication_difficulty: EXTREME` alone. The next thing to try is the
FAA forecast through a mirror, or AIA's underlying Facts & Figures PDF rather than its press
release.

## Remaining, honestly

34 objects below 2 of 3, holding 74 companies, and they are now nearly all small:
`civil_aerospace` 15 is more than a fifth of the remainder by itself, then
`industrial_controls_sensors` 5, `waste_environmental_services` 4, and a long tail of
3-company and 1-company units. Two objects sit at 0 of 3 by decision — `cash_logistics`
and `equipment_rental`, the deliberate singletons, which must name their foreign peers
before they are rebuilt.

The cheap wins are done. What is left needs either a source this box cannot reach or a
unit whose filings do not discuss a substitute, and the honest answer for several of them
is that they stay at 1 of 3 until a different source appears.
