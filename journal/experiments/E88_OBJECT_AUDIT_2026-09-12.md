# E88 — running the Phase A gate over every object for the first time

2026-09-12, continuing E82–E87 in the same session. Read-only audit plus one reversible
cleanup. SHADOW throughout.

`acceptance.main` only ever had a `--payload` mode, which is Phase B. The Phase A half —
`accept_objects` — had never been run over the whole corpus, so the rules it enforces were
checked batch by batch as each landed and **never totalled**. `scripts/audit_objects.py` totals
them.

## What it found

```text
objects on disk                 233   ->  208 after the cleanup below
verdicts                        98 PASS · 77 FAIL · 41 SKIP · 20 WARN
exit code                       1

ordinals answered, objects per level
  before cleanup   0/3 -> 61   1/3 -> 49   2/3 -> 51   3/3 -> 72
  after cleanup    0/3 -> 36   1/3 -> 49   2/3 -> 51   3/3 -> 72
```

Three findings, in descending order of how much they matter.

## 1. Rule 3 is failing for 57 units and 207 companies, and 49 of them are Industrials

The plan's rule 3 — *at least one non-issuer source* — is the corpus's largest systematic gap,
and it had never been counted:

```text
objects with claims but NOT ONE from a regulator, trade body, agency or academic
  Industrials              49 units   145 companies
  Consumer Discretionary    3 units    30 companies
  Real Estate               2 units    15 companies
  Financials                2 units     7 companies
  Consumer Staples          1 unit     10 companies
  TOTAL                    57 units   207 companies
```

This is not a surprise so much as an unpaid bill: E79's write-up already noted that its 64
Industrials objects were **100% `sec.gov`**, and E81 added claims from the same place. What the
audit adds is the size of it, and the fact that **some of these objects are at 3 of 3** —
`flow_filtration_equipment` (9 companies) and `financial_data_ratings` (6) would both ship as
finished experts while failing rule 3 outright. An object evidenced only by its own members'
filings has no outside view of the industry it claims to describe, whatever its ordinal count.

The twelve largest are a concrete work list:

```text
 25  engineered_motion_components    Industrials             2/3
 17  hotels_resorts_cruise_lines     Consumer Discretionary  1/3
 10  household_products              Consumer Staples        2/3
  9  leisure_products                Consumer Discretionary  1/3
  9  hotel_resort_reits              Real Estate             1/3
  9  flow_filtration_equipment       Industrials             3/3   <- ships as an expert
  6  real_estate_services            Real Estate             1/3
  6  off_highway_equipment           Industrials             2/3
  6  government_mission_services     Industrials             2/3
  6  financial_data_ratings          Financials              3/3   <- ships as an expert
  5  payroll_hcm                     Industrials             2/3
  5  industrial_controls_sensors      Industrials             1/3
```

### The promising lead, tried the same session, and refused

Census M3 publishes per-industry shipment rows for machinery, electrical equipment, fabricated
metals and primary metals, each with levels beside their percent change, so they pass E87's
arithmetic-attribution test:

```text
Machinery (NAICS 333), shipments year to date
  2026 $293,372m   2025 $266,963m   +9.9% nominal   (293,372/266,963-1 = +9.89%, checks)
  less CPI +3.4%                    = ~+6.5% real   -> HIGH
```

The obvious move was to write that onto `engineered_motion_components` — 25 companies, the
largest rule-3 failure in the corpus, and at 2 of 3 with growth missing, so one claim would have
fixed rule 3 AND finished the object. **It was not written**, because the unit's own members
contradict it:

```text
NAICS 333 machinery shipments        +6.5% real
engineered_motion_components members  +2.3% real (1-year)   -1.3% real (3-year)
```

A five-to-eight point gap in the same direction as the coarser aggregate means the unit is a
**slow slice of a fast sector** — bearings and power transmission inside a NAICS code that also
holds turbines, HVAC and the machinery going into data centres and power generation. Writing HIGH
there would have described NAICS 333, not this unit.

This is E87's aerospace finding run in reverse and it completes the pair. There, the agency
figure was *lower* than the members' revenue and the agency was right, because the members do
things the series excludes. Here the agency figure is *higher* and the members are right, because
the series includes things the members do not do. **The lesson is the same either way: when an
agency series and the members' own revenue disagree by several points, the series is not scoped
to the unit — and which one is wrong depends on the direction of the gap, so both comparisons are
worth making before either number is used.**

So M3 does not discharge the rule-3 debt wholesale. The 49 Industrials units need sources scoped
to them, which is the same per-unit research grind as the ordinals, and spraying one coarse
number across twenty units to tick rule 3 would be padding of exactly the kind E85's chemicals
refusal avoided.

## 2. Twenty-five objects on disk belonged to no company

233 objects, 208 units with members, **25 orphans**. All of them answer 0 of 3, so they were 25
of the 61 objects the gate's `structural_ordinals` check was failing — which made the corpus
read worse than it is and hid the 36 live objects that genuinely conclude nothing.

They are the **pre-E79 coarse Industrials units**. E79 split `building_products` into
`building_fixtures_access` and others, `industrial_machinery_supplies_components` into
`engineered_motion_components` and `flow_filtration_equipment`, and so on; the finer objects
were written and the coarse ones were left behind. Their `key_participants` lists still name
tickers, but every one of those tickers now resolves through `taxonomy.industry_id` to a
different unit, so nothing reads them.

`scripts/archive_orphan_objects.py` **moves** them to `industries_orphaned_<stamp>/` — never
deletes. Several carry real evidence (`research_consulting_services` 9 claims,
`diversified_support_services` 9) that a later pass may want to re-point at whichever finer unit
inherited those members. The orphan set is **recomputed from the book at run time**, not typed
from a list, and the script refuses to move anything a company resolves to; that derivation is
the whole safety property.

After the move: 208 objects on disk, 208 units with members, and **no unit without an object**.

## 3. `split_unit_evidence` has a false-positive mode during build-out, and I am not fixing it

The check flags 8 objects — all REIT skeletons written today: `diversified_reits`,
`health_care_reits`, `industrial_reits`, `other_specialized_reits`, `real_estate_development`,
`self_storage_reits`, `telecom_tower_reits`, `timber_reits`. Its rule (rule 6) is that a **new**
unit in a sector that already has objects must carry an ordinal claim, because otherwise the
completeness gate retires the empty pieces and strands their companies.

These are not new units. They are pre-existing taxonomy units getting their **first object**.
The check cannot tell the two apart because its `known` set is the industry_ids in the DuckDB
store, and a unit that has never been researched has never been in the store — so during a
build-out every first object in a populated sector looks like an unevidenced split.

**I considered changing `known` to the taxonomy's unit list and decided against it.** A real
split is normally performed by editing `INDUSTRY_OVERRIDES`, which puts the new unit in the
taxonomy *with members* — so that "fix" would stop the check catching the exact case it was
written for. The correct test is whether the unit's members previously resolved somewhere else,
which needs a stored prior mapping; only 311 of 1,500 companies have one, so it cannot be relied
on yet.

So the check stays strict and the false positive is documented instead. Nothing slips through in
the meantime: all 8 are independently failed by `structural_ordinals` for answering nothing,
which is their real defect.

This is the same shape as the E47 correction earlier today, run in the opposite direction — there
the criterion was wrong and the gate was right; here the gate is over-firing and I still left it
alone, because the alternative weakened it against the case it exists for. A gate is worth having
only if it is not adjusted to suit whoever is currently being measured.

## The `--fetch` run, done the same session

```text
exact_containment[objects]   668 / 699 = 95.6% found on their own page
                             floor is 95%  ->  WARN, not FAIL
                             11 citations unreachable, not counted either way
```

**31 object-level citations are not on the page they cite**, and the corpus sits **0.6 points
above the floor** that `MIN_CONTAINMENT_RATE` sets. That floor was chosen in E-something-earlier
because the ingested batches were bimodal — ten at 99.3–100% and three at 89.2–91.5% — so 95.6%
is in the gap between the clusters, which is not a comfortable place to be.

Note the contrast with the claim-level figure from the restate earlier today: **97.9% over the
store, 95.6% over these files.** They are different populations — the store holds the company
lane's claims as well, and these object files hold some claims that never went through an
ingest — so the object files are the weaker half and had never been measured.

The per-claim list is the actionable output and is being generated; it is a `relocate.py`-shaped
job, the same one that settled the 146 unlocatable claims at the start of the session.


---

## Addendum, same session — one of the 57 closed, and why the other 56 are slow

`waste_environmental_services` (4 companies) now carries a non-issuer source and reaches 2 of 3.
EPA: *"Together, almost 94 million tons of MSW were recycled and composted, equivalent to a 32.1
percent recycling and composting rate."* The substitute for disposal is diversion, a third of the
waste stream by volume, policy-driven rather than price-driven. ELEVATED rather than SEVERE
because diversion has plateaued and the incumbents own much of the recycling infrastructure —
share moves channel before it moves operator, the fourth instance of that pattern this session.

**Vintage is stated on the claim and is unusually bad: the EPA series is current through calendar
year 2018.** It is cited for the magnitude of diversion, which is structural and slow, not as a
current reading. No comparable EPA series has been published since, which is itself part of why
this unit had no non-issuer source.

### The blocked-host finding

Three of the four physical-volume series that would have closed the transport units **cannot be
cited at all**:

```text
BTS Freight Transportation Services Index   HTTP 403, even with FETCH_HEADERS
AAR rail traffic                            HTTP 404 at the documented path
USACE Waterborne Commerce Statistics        HTTP 403
```

This is the eCFR lesson generalising. A citation has to survive `e79b_merge`'s **bare re-fetch**,
so a host that refuses anonymous requests is not a source this corpus can use, however good its
data. `rail_transportation`, `freight_forwarding_brokerage` and `marine_transportation` stay at 1
of 3 for that reason and not for want of a published quantity.

### And the rule that closes off the easy fix for the rest

Most of the remaining 56 are service units whose only national series is **employment** — BLS
publishes monthly employment for temporary help services, linen and uniform supply, pest control
and so on. The plan's rule 4 bars it explicitly: *"never company revenue, employment or a
sentiment index."* That rule is right — headcount tracks productivity and wage rates as much as
industry volume — and it means the obvious bulk fix is closed by design.

```text
after this addendum
  companies eligible        1,199 of 1,500
  rule-3 failures              56 units / 203 companies
  ordinals   0/3 -> 36   1/3 -> 48   2/3 -> 52   3/3 -> 72
```

So the rule-3 debt is genuinely a per-unit research problem: 56 units, mostly 1–5 companies each,
each needing a named non-issuer source that publishes something other than employment or revenue
and that serves pages to an anonymous client.
