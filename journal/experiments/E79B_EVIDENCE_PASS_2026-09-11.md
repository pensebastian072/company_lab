# E79B — the evidence half, done by hand against the gate

Worked 2026-09-11, 07:43 to 08:07 NY. Status: **STAGED, NOT APPLIED.** The store is
untouched and still hashes `c6322b46bc6feef6f47c204b3210c818899162c5af9260538cd6c087205a3bc6`.
Advisory / SHADOW throughout; `promoted` is false and no code path sets it true.

The ask was "run the passes so we can get 100 or over 90% on the coverages". The headline
of this file is that **90% is not reachable on `structural_growth` from free verifiable
sources, and the number that was actually hurting is a different one.**

---

## Why a coverage target is the wrong instrument here, measured rather than argued

E79 shipped 64 objects of which **36 answer zero of three structural ordinals**, so on
apply `batch_health.enforce()` retires 36 and **131 of 236 Industrials companies are left
with no active industry object** — blocked for E62 exactly as Health Care is blocked. The
E79 report counted 19, because it counted zero-*claim* objects rather than zero-*answered*
ones. 17 objects carry claims that back no ordinal.

So the binding deficit is not "8 fields at 90%". It is **every unit off zero**, which
needs ONE ordinal per unit, not three.

## Pass 1 — clear the zeros from the local filing corpus

Method, and the split matters: a script retrieves candidate sentences from the cached
EDGAR corpus, and **the field judgement is made by hand afterwards**. Nothing auto-assigns
a field. That division is the whole point — E79's defect was mechanical assignment, and
44 of its 72 claim texts are one template (`"X provides a field-specific Y receipt for
Z"`).

Extractor: `scratchpad/e79b_candidates.py` (retrieval only, writes nothing).

| unit | field | value | evidence |
|---|---|---|---|
| `background_screening` | `substitution_risk` | MODERATE | FA: customers may "take such programs in-house" |
| `background_screening` | `replication_difficulty` | HIGH | FA: "over 1 billion US criminal, education, and work history records" |
| `government_program_administration` | `substitution_risk` | ELEVATED | MMS: "Our primary competitors are government insourced operations." |
| `insurance_data_analytics` | `substitution_risk` | MODERATE | VRSK: competes against "the in-house technology departments of life insurers" |
| `insurance_data_analytics` | `replication_difficulty` | HIGH | VRSK: subscriptions and long-term agreements "represented over 80% of our revenues in 2025" |
| `flow_filtration_equipment` | `substitution_risk` | ELEVATED | **ATMU and DCI independently** name "alternatives to diesel engines, such as electrification" |
| `flow_filtration_equipment` | `replication_difficulty` | MODERATE | ATMU: "approximately 1,200 worldwide active or pending patents" |
| `engineered_motion_components` | `substitution_risk` | ELEVATED | CRS: "customers may substitute alternate materials" |

The filtration one is the strongest of the set and for a structural reason: **two of the
nine members name the same substitute in their own filings**, so the direction rests on
two issuers rather than one, which is what makes it a unit-level reading.

Two deliberate restraints recorded: `flow_filtration_equipment.replication_difficulty` is
MODERATE and not HIGH, because a 1,200-patent portfolio establishes that the field is
patented, not that a position is exclusive; and the
`engineered_motion_components` claim carries a written caveat that the unit spans
composites, specialty alloys, bearings and fluid handling, so a single substitution reading
sits on a heterogeneous membership.

## Pass 2 — growth, where a body actually publishes the quantity

| unit | value | source | what it states |
|---|---|---|---|
| `building_materials_envelope` | DECLINING | FGIA 2026 market studies, 2026-05-15 | prime windows −5% in 2025; residential skylights **−9% in unit shipments** |
| `agricultural_farm_machinery` | DECLINING | AEM, 2026-01-15 | US ag tractors −14.8%, combines −4.3%, Dec 2025 y/y |

Both are direct industry quantities from the industry's own reporting bodies — not company
revenue, not employment, not a sentiment index. The skylight figure is in units, so the
direction is not a price effect.

### Where growth is NOT obtainable, and why that is a finding

- `flow_filtration_equipment` — no free industry-scope quantity exists. Three paid vendors
  give the **same year's market size as $10.87bn, $11.3bn and $11.6bn**. Citing any of them
  would be a proxy filed as a fact, and unverifiable besides. Census "Machinery shipments
  up 2.3 percent to $41.6 billion" is a scope violation, not this industry.
- `passenger_airlines` — BTS publishes exactly the right quantity (84.1 million systemwide
  passengers, October 2025, +1.6% y/y) but **bts.gov returns HTTP 403 to both WebFetch and
  `clab.net.http_get`**, so a BTS claim can only ever be `SELF_ATTESTED`. The FAA
  enplanement tables are the route to try next.

Probe hit rate on growth: **2 of 4 industries**, and the four were chosen as *likely* to
have publishing bodies, so 50% is the optimistic read, not the pessimistic one. n=4 — a
rate, not a verdict.

## Pass 3 — coverage as measured

```
claims staged                    12      ALL VERIFIED_LOCAL at overlap 1.0
units moved off zero              6
zero-ordinal units          36 -> 30
companies stranded         131 -> 100
units at 3 of 3 (ship bar)        0      none yet; the growth field is the blocker
```

Every claim was verified the same way the pipeline will: fetch the cited URL with
`clab.net.http_get`, extract, and run `verify.check_quote`. 12 of 12 at overlap 1.0.

### One error made and caught, recorded because the catch is the point

I wrote the Donaldson citation by **constructing** an accession number
(`0000029644-25-000049`) instead of reading it from the submissions cache. The real one is
`0000029644-25-000098`. Verification caught it — a fabricated URL cannot return a page
containing the quote. The corrected claim then verified at 1.0, which is itself the proof
the correction was right. The lesson is the repo's existing one in a new place: **a
citation is data to be read, never a string to be assembled**, and the claim carries a
`_url_corrected` field saying so.

## Rate, and what remains

24 minutes of wall clock produced 12 verified claims across 8 units (6 off zero). Roughly
**2 minutes per claim including dead ends**, and the dead ends cost the same as the wins.

Remaining: **30 units at zero, 100 companies stranded.** At the measured rate that is
perhaps 2 hours of further work for the zeros alone, and it should be done in batches with
a checkpoint after each, because this box crashes daily.

Resumable state:

```
queue   D:\company_lab_data\external\reports\E79B_pass1_queue.json      36 units, largest first
claims  D:\company_lab_data\external\reports\E79B_pass1_claims.json     12 staged + verify status
probe   D:\company_lab_data\external\reports\E79B_evidence_probe_2026-09-11.json
```

Units that defeated the generic patterns and need targeted vocabulary next:
`cash_logistics` (cashless payments), `equipment_rental` (own-versus-rent, rental
penetration), `construction_engineering` (surety bonding, prequalification).

## What this does and does not establish

It establishes that a web- and filing-sourced Phase A pass produces claims that clear local
verification at 1.0, and that the zero-ordinal problem is fixable unit by unit without
padding. It does **not** establish that 90% field coverage is reachable — on current
evidence it is not, for `structural_growth`, and the honest ceiling is closer to half the
units. Nothing here is applied, nothing is scored, and no object has been promoted.

---

# Continuation, same day: batches 2 through 6

Worked on without stopping between batches. Everything below is additional to the 12 claims
above. Store still untouched: `c6322b46...`.

## Result

```
                              before E79B     after
claims on the 64 E79 objects         72        112
objects answering ZERO ordinals       36          9
companies stranded on apply          131         18
objects at 1 of 3                     28         47
objects at 2 of 3                      0          8
objects at 3 of 3 (ship bar)           0          0
```

**40 claims, every one `VERIFIED_LOCAL` at overlap 1.0 AND exact-containment verified** — a
stricter bar than the pipeline's, because `check_quote` also passes on its token-overlap
fallback and none of these rest on that.

Value distribution, which is the check that this was not a padding exercise:

```
MODERATE 17 | ELEVATED 13 | HIGH 5 | DECLINING 3 | LOW 2
substitution_risk 19 | replication_difficulty 18 | structural_growth 3
```

Two **LOW** barrier readings were recorded deliberately. `building_products_distribution` is
LOW because Builders FirstSource describes its own industry as highly fragmented across five
classes of competitor; `freight_forwarding_brokerage` is LOW because Expeditors is
non-asset-based, and a business owning no ships or trucks has no capital barrier protecting
it either. A LOW with evidence is worth the same as a HIGH.

The strongest findings are the ones where two members said the same thing independently:

| unit | substitute or barrier named by | reading |
|---|---|---|
| `flow_filtration_equipment` | Atmus **and** Donaldson: electrification of equipment | ELEVATED |
| `payroll_hcm` | ADP **and** Insperity: the customer's own HR function | ELEVATED |
| `government_mission_services` | Amentum **and** Booz Allen: government insourcing | ELEVATED |
| `waste_environmental_services` | WM **and** Republic: permitted airspace is regulator-issued | HIGH |
| `construction_engineering` | Quanta **and** Primoris: surety bonding, pre-qualified lists | MODERATE |
| `ride_hailing_platforms` | Uber, with the magnitude: personal vehicle ownership holds "the majority of passenger miles" | ELEVATED |

## The 9 that remain at zero, and why each one does

These are honest UNKNOWNs, not unfinished ones. Their filings were searched with
unit-specific vocabulary and did not yield a passage that establishes an ordinal.

| unit | n | why it resisted |
|---|---:|---|
| `industrial_tools_fabrication` | 6 | hand/power tools and welding consumables: no member states a substitute or barrier in quotable terms |
| `automation_precision_equipment` | 4 | the only substitution language found was input-material sourcing, which is the wrong scope |
| `multi_industry_industrials` | 2 | **HON + MMM is not an industry.** Honeywell's own filing says no segment depends on any single patent group. A taxonomy residue: fold it, do not evidence it |
| `cash_logistics` | 1 | Brink's filing never discusses declining cash usage, the actual substitute |
| `equipment_rental` | 1 | no own-versus-rent or rental-penetration language in United Rentals' 10-K |
| `investor_communications_processing` | 1 | Broadridge's regulatory mandate is the barrier but is never stated as one |
| `lighting_controls` | 1 | Acuity lists competitive factors without naming a substitute or a barrier |
| `road_tolling_enforcement` | 1 | Verra Mobility describes what it sells, not what could replace it |
| `specialty_materials_products` | 1 | **DD alone.** Patent language is boilerplate. This is the singleton flagged earlier as the prompt's forbidden "isolate a hard company" case; folding beats evidencing |

Five of the nine are one-company units, which is the taxonomy finding arriving from the other
direction: **a split that leaves a single company in a unit also leaves a single filing to
evidence it from.**

## An instrument defect for Chat A, found by using it

`verify._extract_fetched` does **not decode HTML entities.** EDGAR HTML filings wrap figures
in `&#160;`, so "represented over&#160;80%&#160;of our revenues" can never match a verbatim
quote. The claim still returns `VERIFIED_LOCAL` — via the token-overlap fallback, the same
path `verify.py`'s own comment warns about after the ICI false match. Two of my claims
verified that way before I noticed, and both had to be re-quoted from the page.

The consequence is general, not mine: **any numeric quote taken from an EDGAR HTML filing is
likely resting on the fallback rather than on exact containment.** A decode pass before
matching would move a large share of the corpus from fallback to exact. Worth measuring
across the 7,099 existing `VERIFIED_LOCAL` claims before that number is read as "verbatim".

## Still true, and still the honest ceiling

`structural_growth` remains answered for only 3 of 64 objects, and that is what blocks the
ship bar — 0 objects reach 3 of 3. Nothing here changes the earlier finding: free, fetchable,
industry-scope growth quantities exist for perhaps half the units, and for several they do
not exist at all. Applying E79B makes the object set **survivable**, not complete.
