# E86 — Real Estate, a fourth guard, and the revenue route running out

2026-09-12, continuing E82–E85 in the same session. SHADOW throughout.

```text
                                      E85 close   E86 close
units with an object                                  208 of 208
objects at 3 of 3                                          72
companies whose unit has an object        1,353       1,500
companies whose unit has >=1 ordinal      1,357       1,361
companies eligible for Phase B (>=2/3)    1,123       1,150
claims                                                      6, all exact containment
```

**A counting correction while measuring this.** The per-sector tables in E82–E85 summed unit
counts sector by sector and reported **214 units**; the true figure is **208**, because six
units have members in two GICS sectors and were counted twice:

```text
application_software       Financials + Information Technology      n=37
mortgage_reits             Financials + Real Estate                 n=10
technology_distributors    Industrials + Information Technology      n=8
agricultural_farm_machinery Industrials + Materials                  n=5
publishing                 Communication Services + Consumer Disc.   n=4
us_credit_scoring          Industrials + Information Technology       n=3
```

The same double count inflated "objects at 3 of 3" from 72 to 75. Company counts were never
affected — a company appears once. Taxonomy is doing the right thing here: `industry_id` is
assigned from sub-industry and overrides, not from the sector, so a consumer-credit complex
scattered across two GICS sectors still lands in one research unit, which is the whole argument
in `taxonomy.py`'s docstring. **Count units globally, not by summing sectors.**

**Every company in the book now sits in a unit that has an object.** 28 skeletons written this
round (14 Real Estate, 14 the Consumer Discretionary tail), which closes the "NONE" column that
has been open since the plan was approved.

Eligibility did not move, and the reason is the point of this entry.

## The fourth guard: growth that arrived with new shares

Real Estate broke the revenue route, and it broke it in a way the existing three guards could
not see. `retail_reits` passed every one of them and read **HIGH, +6.2% real**. Retail property
has not grown 6% a year in real terms. So I measured where the revenue came from:

```text
unit                    revenue 3y   shares 3y   revenue/share 3y
retail_reits                +11.5%      +4.9%              +6.2%
industrial_reits             +9.8%      +4.3%              +5.3%
health_care_reits           +16.6%      +6.1%             +10.0%
diversified_reits            +5.0%      +6.7%              -1.6%
hotel_resort_reits           +4.5%      +0.0%              +4.4%
real_estate_services        +10.0%      +0.1%              +9.9%
```

A REIT grows revenue by issuing equity and buying buildings, and **the buildings come from
private owners outside the listed set** — so the listed aggregate grows while the property
sector does not. It is `revenue_share.py`'s "share of the listed set, not of the market"
problem arriving somewhere it moves the headline. Roughly 43% of retail REITs' growth and 37%
of health care REITs' came with issuance. `diversified_reits` is the clearest case of all: it
issued shares **faster than it grew revenue**, so revenue per share actually fell 1.6% a year
while the aggregate grew 5.0%.

None of the three existing guards can catch this. The members resemble each other, nobody is
over-concentrated, and both windows agree — **because every member is doing the same thing.**

`MAX_SHARE_GROWTH = 0.02` refuses a unit whose aggregate diluted share count grew faster than
2% a year, and reports the split so the refusal can be read. Missing share counts refuse rather
than skip the guard, because graceful degradation would disable it for exactly the units whose
filings are most awkward. A buyback is deliberately one-sided: shrinking the share count does
not make revenue growth more real, so it fails to block rather than earning anything.

Two Real Estate units survive: `hotel_resort_reits` FLAT (+0.8% real) and
`real_estate_services` HIGH (+9.8% real), both with share counts flat. Both are at 1 of 3.
`real_estate_services` is flagged as cyclical on its own claim — commercial brokerage revenue
turned in 2023, and two windows that both begin after a trough will agree with each other.

## Real Estate substitution, from two agencies

Four claims, four units, 43 companies, one ordinal each. What makes them worth having is that
each substitute is **measured by a government agency** rather than asserted.

- **`office_reits` — SEVERE, the first in this corpus.** BLS American Time Use Survey: *"In
  2025, 35 percent of employed people did some or all of their work at home on days they
  worked, and 70 percent did some or all of their work at their workplace."* A home is not a
  cheaper office — it is an office the tenant already pays for, and no landlord can price
  against it. The two figures overlap, which is the hybrid pattern, and that is what makes it
  structural here: a tenant needing three days a week renews for **less space** rather than not
  renewing, so the loss arrives as a permanent cut in square feet per employee rather than as a
  vacancy. This is the one unit all week where the substitute removed demand instead of capping
  price.
- **`retail_reits` — ELEVATED.** Census nonstore retailers +7.7% y/y and +10.4% over May–July
  against general merchandise +3.7% and food and beverage +0.9%, all from one table on one
  basis. ELEVATED rather than SEVERE for a reason specific to these nineteen: most own
  grocery-anchored and net-lease assets, and the tenant categories that survive e-commerce best
  are what they are leased to. The substitution is measured; its incidence across the unit is
  not, and nothing here measures it.
- **`multi_family_residential_reits` and `single_family_residential_reits` — MODERATE.** Census
  HVS: the homeownership rate of **65.0%** was *"virtually the same"* as a year earlier, and
  rental vacancy at 7.3% *"not statistically different"* from 7.0%. A substitute that is large,
  permanent and currently **static**: two thirds of households own rather than rent, so the
  substitute is most of the market, but on the agency's own significance tests it is not taking
  share, and what would move it is mortgage rates rather than anything either industry does.
  Not LOW, because the option to buy caps what a landlord can charge; not ELEVATED, because the
  measurement says it is not moving.

## The revenue route is finished, and this is the number that says so

With all four guards and the two-window agreement test, I re-ran the route over **every** unit
in the corpus whose `structural_growth` is still UNKNOWN:

```text
PASSES      1 unit, 4 companies   (distributors, FLAT +1.5% real)
REFUSALS  123 units
            84  under the 4-peer floor
            13  one member over 50% of the unit's revenue
            11  growth bought, not earned
             9  the windows disagree
             5  aggregate not describing the median member
             1  share counts missing
```

**One pass in 124.** The exception the user authorised on 2026-09-12 has now carried 8 units
in total and is done — not because it was switched off, but because the guards that make it
honest refuse almost everything left. 84 of the 123 refusals are simply units with fewer than
four members, which no amount of method fixes.

So the remaining path to eligibility is what rule 4 asked for in the first place: a **published
industry quantity, per unit**. There are **53 units holding 234 companies sitting at exactly 1
of 3** — one ordinal each from Phase B eligibility — and they are now the whole job:

```text
 23  specialty_chemicals          ANSWERED this session - see the TSCA addendum below
 19  retail_reits                 has substitution needs growth or replication
 17  hotels_resorts_cruise_lines  has substitution needs growth or replication
 16  automotive_parts_equipment   has substitution needs growth or replication
 15  civil_aerospace              has replication  needs growth or substitution
 14  health_care_services         has growth       needs substitution or replication
 11  office_reits                 has substitution needs growth or replication
  ... 46 more units at 1 of 3
```

That is a research list, not an instrument problem, and it is the honest end state of four
experiments' worth of automation: the measurement machinery is built, validated, and has
extracted everything it can. What is left has to be read off published sources one unit at a
time.

## Debt still on the books

- **Rule 3** — the revenue-route units carry no non-issuer source (`food_distributors` was
  fixed; four remain).
- **Rule 5** — single-member units must name private or foreign peers: `copper`, `silver`,
  `paper_products`, `tires_rubber`, `motorcycle_manufacturers`, `housewares_specialties`,
  `real_estate_development`, `agricultural_farm_machinery`.
- Both would fail an object-level acceptance run. Neither is hidden.


## TSCA addendum: the two chemicals units reached 2 of 3

`specialty_chemicals` (23 companies) was the largest unit in the corpus at 1 of 3, and the
ordinal it was missing turned out to be regulatory rather than commercial. 40 CFR 720.22, from
the GPO's own CFR XML:

> Any person who intends to manufacture a new chemical substance in the United States for
> commercial purposes must submit a notice unless the substance is excluded under § 720.30.

`replication_difficulty` **MODERATE** for `specialty_chemicals` and `diversified_chemicals` —
**27 companies, both now eligible.** Three details make it more than boilerplate: the same
section extends the duty to **imports**, so a foreign entrant cannot route around it by
shipping the molecule in; and (a)(2) puts the duty on whoever specifies the substance and
controls the process rather than the toller who runs the reactor, so contract manufacturing does
not shed it either.

MODERATE and deliberately not HIGH. Thousands of premanufacture notices are filed and cleared,
so this is a cost and a delay — **the floor on entry, not the moat.** The barrier a practitioner
would name first is being designed into a customer's formulation and qualified there, and this
corpus has **no** evidence for that: the filings sweep returned nothing usable on qualification
or switching costs. The claim records the part that is evidenced and names the stronger part as
missing rather than assuming it.

`commodity_chemicals` was deliberately left out. Its members make existing substances, so a
premanufacture notice for a *new* chemical substance does not gate them, and applying the claim
there would have been a scope error of exactly the kind this week's refusals were about.