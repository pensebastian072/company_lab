# E82 — Phase 3: three Consumer Discretionary units finished, and Consumer Staples off zero

2026-09-12, Claude lane, single session. Master plan `MASTER_PLAN_TO_1500_2026-09-11.md`,
Phase 3 ("build missing experts"). Everything here is SHADOW; no score moved, no company
was re-ranked, and `promoted` is false as always.

## What moved

```
                                     before   after
objects in the corpus                   160     171
objects at 3 of 3                        69      71
companies whose unit has an object     1,202   1,277
companies eligible for Phase B (>=2/3) 1,026   1,084

Consumer Discretionary   objects 14/28   at 3/3  1 -> 3   eligible  71 -> 93
Consumer Staples         objects  0/11   at 3/3  0        eligible   0 -> 36
claims this session                                       21, all exact containment
```

Claim sources: PRIMARY_DATA 9, COMPETITOR_FILING 11, REGULATOR 1. Every object touched
carries at least one non-issuer source, which is the plan's rule 3.

## education_services (9) — 3 of 3, and the only unit here with a regulator behind it

- **structural_growth FLAT.** National Student Clearinghouse, spring 2026: 18.6m students,
  **+1.0%**; undergraduate 15.5m (+1.3%), graduate 3.1m (-0.1%). The Clearinghouse covers
  97% of Title IV degree-granting enrolment, so this is the industry's unit count, not a
  member's revenue.
- **replication_difficulty HIGH.** 34 CFR 600.4 makes accreditation or preaccreditation a
  condition of being an eligible institution at all, with state authorisation required
  separately. An unaccredited entrant is not a cheaper competitor; it is a business whose
  customers cannot use federal aid to buy from it. Grand Canyon Education states the same
  three-part gate in its own 10-K.
- **substitution_risk ELEVATED.** UTI: *"We compete with local community colleges for
  students seeking programs that are similar to ours, mainly due to local accessibility,
  low tuition rates and in certain cases free tuition."* Laureate goes further — public
  institutions *"can offer substantially lower tuition prices or other advantages that we
  cannot match."* And the Clearinghouse sizes it: **community colleges +3.1% against +1.0%
  for postsecondary enrolment as a whole**. The subsidised substitute is taking the growth.

**Scope, stated on the claim itself:** the enrolment number describes postsecondary
education — LOPE, STRA, PRDO, LAUR, UTI and Graham's Kaplan, six of nine members. It does
not describe Stride's K-12 programs or Duolingo's consumer app. Six of nine is why this was
recorded rather than refused; CLIA's three of seventeen last session was not.

## apparel_accessories_luxury_goods (13) — 3 of 3

- **structural_growth FLAT.** Census clothing and clothing accessories stores **+5.0%**
  year over year in July 2026, +5.2% for May–July. Against CPI apparel **+3.6%** over twelve
  months that is roughly **1.4% of real growth**, which is why this is FLAT and not MODERATE.
  The nominal number alone would have read as a healthy industry.
- **replication_difficulty LOW**, on a member's own words. PVH: *"We also face increased
  competition from digitally native brands; digital retailing is characterized by low
  barriers to entry."* This unit contracts out its manufacturing, so the only thing hard to
  replicate is a brand — and a brand is precisely what a digitally native entrant sets out
  to build without the cost base. A list of thirteen famous names looks like a moat from
  outside and does not read as one from inside.
- **substitution_risk ELEVATED.** VF: *"VF competes directly with the private label brands
  of its wholesale customers."* PVH names the identical mechanism. The substitute is stocked
  by the unit's own distribution, and the shelf position is in the customer's gift.

## Consumer Staples, from nothing to eleven objects

Eleven skeletons written (the sector had **zero**), then three units researched. The
research rests on a single observation: **one Census table publishes food and beverage
stores, general merchandise stores and nonstore retailers side by side, same month, same
basis.** The substitution claims below are therefore not an analyst asserting a channel is
losing share — they are two rows of one agency release read against each other.

```
Census Table 2, Advance Monthly Retail Trade Survey, July 2026 (CB26-131)
  445 Food & beverage stores          +0.9% y/y     +1.4% May-Jul
  452 General merchandise stores      +3.7% y/y     +3.7% May-Jul
  454 Nonstore retailers              +7.7% y/y    +10.4% May-Jul
BLS CPI, August 2026
  Food at home                        +2.2% over twelve months
```

- **packaged_foods_meats (22) — 2 of 3.** `structural_growth` **DECLINING**: the channel
  moved fewer units than a year ago while charging more for them (+0.9% of dollars on +2.2%
  of price). Two members put their own numbers on it — Conagra *"Organic volume decreased by
  2.2%"*, General Mills *"a $1,009 million decrease due to lower volume, partially offset by
  a $506 million increase attributable to product rate and mix."* Dollars defended with
  price while units leave. `substitution_risk` **ELEVATED**: private label, named
  independently by Campbell's, Conagra, General Mills, Kraft Heinz and Tyson — five of
  twenty-two. Tyson states the mechanism plainly: *"These customers also may use shelf space
  currently used for our products for their own private label products."* The substitute
  does not have to win a customer; it only has to be given the space.
- **food_retail (7) — 2 of 3.** `structural_growth` **FLAT** (the dollars are this unit's
  revenue and they are up, just under inflation). `substitution_risk` **ELEVATED** on the
  **four-times spread** between general merchandise +3.7% and food and beverage +0.9%.
- **consumer_staples_merchandise_retail (7) — 2 of 3.** `structural_growth` **MODERATE**
  (+3.7% nominal against goods prices up well under a point). `substitution_risk`
  **ELEVATED**: this unit is the substitute taking grocery's share, and the same table names
  the channel taking its own — nonstore +7.7% to +10.4%. The members are building that
  substitute themselves, so as with casinos and iGaming, **share moves channel before it
  moves operator.**

## The refusal: leisure_products (9) stays at 1 of 3

`substitution_risk` **ELEVATED** was recordable and is unit-wide — Brunswick names the
substitute as *"other forms of recreational, religious, cultural, or community activities"*
and Polaris says its products *"compete with many other recreational, utility, and work
products for the discretionary spending of our customers."* Every member sells a
discretionary leisure durable, so that claim covers all nine.

Neither of the other two ordinals could be answered honestly.

**No published quantity describes this unit.** The Toy Association publishes Circana's US
toy sales (+6% to $30.3bn in 2025) and it covers Hasbro and Mattel — two of nine. NMMA
covers Brunswick. RVIA covers Thor. Each trade body measures a fragment, and the fragments
do not add up to the unit. The one series that would have covered it — BEA's PCE line
"recreational goods and vehicles", whose scope is almost exactly this unit — appears in the
release **only as a chart**, and the PDF extraction yields sixteen numbers against eleven
category labels with no way to attribute one to another. Using it would have meant guessing
which number was which, so it was not used. `structural_growth` stays UNKNOWN.

**The barrier to entry points in two directions inside one unit**, which is itself a
finding. Polaris sells through *"approximately 2,400 independent dealers in North America"*
and Thor through its own independent dealer networks — a distribution barrier that takes
decades to build. Acushnet, in the same unit, says: *"The markets for golf equipment, wear
and gear are highly competitive and there may be low barriers to entry in many of our
markets."* Averaging those to MODERATE would be a number describing no company in the unit.
`replication_difficulty` stays UNKNOWN and the contradiction is recorded here rather than
resolved by arithmetic.

**This unit should probably be three or four** — marine and powersports and RV behind dealer
networks; toys; golf and fitness and drinkware. Under the standing rule a split needs one
ordinal-supporting claim in hand per resulting piece first, and that is the user's call, not
a unilateral taxonomy edit. It is the second such finding in two sessions, after
`hotels_resorts_cruise_lines`.

**And it is the one object built today that would FAIL the acceptance gate.** Both its
claims are `COMPETITOR_FILING`, so it has no non-issuer evidence at all — the plan's rule 3
and the gate's `source_diversity` check. That is left standing rather than patched: the
Toy Association's +6% could have been dropped in to satisfy the rule, and it would have been
the same three-of-seventeen scope violation the growth field was refused for, wearing a
different field's name. An object that fails a rule for a stated reason is more useful than
one that passes it by importing evidence about two of its nine members.

## Two instrument notes

**`scripts/create_industry_objects.py` takes `--sector`.** It had "consumer_discretionary"
hardcoded as the stored `sector_id`. Eleven Consumer Staples objects written through it
would each have carried the wrong sector. It now derives the id through `taxonomy.sector_id`
from the GICS name, refuses a name that is not one of the eleven, and builds only units that
actually have members in the sector being built — so a stale name in `UNITS` cannot create
an object under the wrong sector.

**The eCFR cannot be cited.** `ecfr.gov` returns a 1,100-character shell to a bare fetch and
the full section only to a browser-ish user agent, so a claim cited to it verifies at
staging and then fails `e79b_merge`'s re-fetch — which is the merge working correctly, since
a citation that only one client can read is not a citation. The regulator claim is cited to
the GPO's own CFR XML at govinfo.gov, which serves full text to anyone. **Rule for the next
pass: a source that needs `FETCH_HEADERS` to render cannot be a citation.**

## Corpus verification

- 21 claims staged, **21 exact containment**, 0 skipped at merge after the govinfo fix.
- Full restate over the corpus, applied: **7,141 rows written, 7,141 verified by reading the
  store back**; exact containment **97.9%** (6,402 exact + 589 whitespace-only of 7,141
  tested). Three claims moved SELF_ATTESTED → UNVERIFIABLE, all three `regulatory_risk` on
  `content.naic.org`; nothing was promoted in the other direction.
- 61 quoted claims remain untested for lack of a usable cached page (34 under the minimum
  page length, 25 with no cached page, 2 PDFs that would not extract). None are from this
  session.
