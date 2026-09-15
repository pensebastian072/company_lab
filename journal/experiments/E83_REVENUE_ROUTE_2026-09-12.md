# E83 — `structural_growth` from the members' own revenue, and the 13 units I refused to write it to

2026-09-12, same session as E82. Authorised by the user: *"just use their revenues since they
are similar companies."* SHADOW throughout; no score moved.

## What it bought

```
companies eligible for Phase B (>=2 of 3)     1,084 -> 1,141
Consumer Discretionary  eligible                 93 ->  135
Consumer Staples        eligible                 36 ->   51

units filled from the revenue route                5   (57 companies)
  hotels_resorts_cruise_lines   17   +7.6% nominal  +4.2% real  MODERATE
  automotive_parts_equipment    16   +3.3%          -0.1%       FLAT
  household_products            10   -0.1%          -3.5%       DECLINING
  leisure_products               9   +3.0%          -0.4%       FLAT
  food_distributors              5   +4.5%          +1.1%       FLAT
substitution_risk claims staged    7, all exact containment
```

Deflator: CPI-U all items **+3.4%** over the twelve months to August 2026, quoted from the
BLS release and cited on every computed claim, because it is the half of the arithmetic that
comes from outside and it is the half that decides the sign.

## The instrument, and why the user's premise is the test

`clab/external/industry_growth.py`, 12 tests. "Since they are **similar** companies" is the
load-bearing half of the instruction and it is checkable rather than assumed. Each guard is
one way that premise fails, and each was set from a unit where it actually failed:

| guard | bar | what it caught on 2026-09-12 |
|---|---|---|
| `MIN_PEERS` | 4 | `brewers` (2), `distillers_vintners` (2), `tobacco` (3) |
| `MAX_TOP_SHARE` | 0.50 | `tobacco` — PM is 62%, so the aggregate reads **+4.9%** while the median member reads **−0.6%** |
| `MAX_AGG_MEDIAN_GAP` | 0.05 | `specialty_stores` — aggregate **+18.4%** against a **+3.8%** median member |
| `STRUCTURAL_MOVE` | 0.40 | `agricultural_products_services` — BG excluded, leaving 3, under the peer floor |

Tobacco is the clearest case for the concentration bar: the unit's real story is declining
volume defended with price, and the aggregate says the opposite, because the aggregate is
Philip Morris.

## It was validated first, and the validation is thinner than it looks

Three units already carry a `structural_growth` from a Census channel series, so the module
was run against them **before** being applied anywhere:

```text
unit                                 agency route   revenue route   bands
packaged_foods_meats                 -1.3% real     -1.7% real      DECLINING vs FLAT
food_retail                          -1.3% real     -1.6% real      FLAT      vs FLAT
consumer_staples_merchandise_retail  +3.0% real     REFUSED          WMT is 60% of it
```

**Two comparable, not three** — the concentration guard refuses the third, which is the guard
working. On the two that compare, the quantities agree within **0.4 points** and the bands
agree on one of two. The packaged-foods disagreement is entirely the −2% cut: both routes say
real growth is negative and they differ by less than either one's uncertainty. So the
measurement is calibrated and **the band edge is not** — a unit landing within half a point of
a cut could read either way. Two comparisons, one quarter, one year. A sanity check, not a
validation.

`packaged_foods_meats` keeps DECLINING. A computed value never overwrites a researched one.

## The 13 units I did NOT write it to, which is the real finding

A dry run over the whole corpus passed every guard on **18** units. Five were applied. The
other 13 were not, and the reason is a limitation no guard in the module can see:

```text
regional_banking                      n=79   +7.7% nominal -> MODERATE
civil_aerospace_platforms_components  n=14  +18.5%         -> EXCEPTIONAL
health_care_services                  n=14  +14.9%         -> HIGH
electronic_equipment_instruments      n=16   +9.1%         -> MODERATE
engineered_motion_components          n=25   +5.7%         -> MODERATE
flow_filtration_equipment              n=9   +8.8%         -> MODERATE
... and 7 more at 4-6 members
```

**A one-year nominal window reads a cycle as a structure.** Seventy-nine regional banks up
7.7% together is a rate cycle. Civil aerospace up 18.5% is a delivery recovery. The guards
test whether the members *resemble each other*, and in a cyclical industry they resemble each
other perfectly — all up, together, for a reason that has nothing to do with structural
growth. Concentration and dispersion cannot separate the two.

Eleven of those 13 would have gone straight to **3 of 3** and `regional_banking` is the
largest unit in the book, so this was the cheapest large coverage gain available today and it
was the wrong one to take. `scripts/apply_industry_growth.py` now **refuses to run without an
explicit `--units` list** and says why. The 13 stay UNKNOWN until either a published quantity
turns up or the module learns a multi-year window.

That multi-year window is the obvious next piece of work: the book holds `revenue_cagr_3y`,
so a 3-year aggregate is reachable, and it would let the instrument speak to exactly the
units it currently must refuse.

## What the computed claim is, exactly

`research_ingest.validate_claim` requires every industry claim to carry a quote and an
excerpt containing it, and that guard was **not** relaxed — an industry object's claims are
citations. A revenue aggregate has no page to quote. So the ordinal is written from the
computation while the claim attached to it cites the CPI release, and the claim's text carries
the aggregate, the member count, the top member's share, the median member and the
nominal-to-real arithmetic, so it is auditable without re-running anything.

**This is the weakest ordinal in the corpus.** Every other non-UNKNOWN field is backed by a
quote on a page that says it; this one is backed by a quote for the price level and a
computation for the quantity. Two deliberate labelling choices follow:

- `independence_domain` is **`COMPETITOR_FILING`**, not `PRIMARY_DATA`. The quantity is built
  from the members' own filings, and calling it independent would let a unit satisfy the
  plan's non-issuer rule with evidence about itself. `leisure_products` therefore still fails
  rule 3, correctly.
- `fact_or_inference` is **`INFERENCE`**.

### And that makes all five of these units fail rule 3, not just `leisure_products`

Measured after writing: every one of the five carries **zero** non-issuer claims.

```text
hotels_resorts_cruise_lines   3 claims   COMPETITOR_FILING 3                  non-issuer 0
automotive_parts_equipment    3 claims   COMPETITOR_FILING 3                  non-issuer 0
household_products            3 claims   COMPETITOR_FILING 3                  non-issuer 0
leisure_products              3 claims   COMPETITOR_FILING 3                  non-issuer 0
food_distributors             2 claims   COMPETITOR_FILING 2                  non-issuer 0
                        -> fixed later in this session, now 3 claims with PRIMARY_DATA 1
```

This is the labelling choice above working as intended, and it has a consequence worth stating
rather than discovering later: **the 57 companies these units cover are now at ≥2 of 3, but an
object-level acceptance run would REFUSE all five on `source_diversity`.** So part of today's
eligibility gain is provisional. It is not illusory — the ordinals are real and the claims are
exact — but each unit needs one non-issuer claim before its object passes the gate.

The cheapest fix per unit, for the next pass, with the scope problem named in each case:

| unit | candidate non-issuer source | the catch |
|---|---|---|
| `food_distributors` | **DONE, same session** — Census MARTS 722 food services & drinking places, +5.0% y/y | clean: restaurant sales ARE this unit's demand |
| `automotive_parts_equipment` | Census MARTS **4413 auto parts, accessories & tire stores** | aftermarket channel only — covers DORM, SMP, XPEL, not the Tier 1s |
| `hotels_resorts_cruise_lines` | Census Quarterly Services Survey, NAICS 721 accommodation | covers hotels and timeshare, not OTAs or cruise |
| `household_products` | Census MARTS 446 health & personal care stores | mostly pharmacy dollars; a real scope stretch |
| `leisure_products` | none found | refused deliberately, see E82 |

`food_distributors` was the only one of the five where a clean unit-wide non-issuer quantity
was already in hand, so it was done in this session: Census food services and drinking places
+5.0% y/y, recorded as CONTEXT on `substitution_risk`. Restaurants are this unit's customers,
so it is the closest published quantity to the unit that does not come from its members' own
filings, and the spread is the interesting part - the customer base grew 5.0% while the
distributors' combined revenue grew 4.5%, a small gap running the wrong way for a
distributor. **Four units still carry no non-issuer evidence**, covering 52 companies.

## The substitution claims, and the shape they share

Seven claims, all exact containment, and all four units turned out to have the same structure:
**the substitute is the customer, or something the customer can reach without leaving the
transaction.**

- `automotive_parts_equipment` — Aptiv: *"If our OEM customers successfully in-source products
  currently manufactured by us…"*; Visteon says it almost verbatim; BorgWarner from the other
  side: *"Our competitors include vertically integrated units of our major OEM customers"*,
  and names where it is happening now — Chinese OEMs *"increasingly insourcing certain
  components once sourced from Tier 1 suppliers."*
- `household_products` — Church & Dwight does not list private label as a risk, it reports it:
  *"In 2025, some of our largest customers launched private label brands that compete with our
  products."* Colgate, Clorox, Kimberly-Clark and Energizer name it too — five of ten members.
  Same mechanism as packaged foods, and this unit's revenue is already shrinking in real terms.
- `food_distributors` — Sysco: customers may buy *"directly from wholesale or retail outlets,
  including club, cash and carry and grocery stores, online retailers, or negotiate prices
  directly with our suppliers."* The last is disintermediation by the unit's own supplier. US
  Foods operates over 90 cash-and-carry depots itself.
- `hotels_resorts_cruise_lines` — Royal Caribbean lists its competition as *"resorts
  (including all-inclusive resorts), hotels, internet-based alternative lodging sites, theme
  parks, sports, nature and sightseeing destinations"* — which is the rest of this unit plus
  every other thing a holiday could be. Airbnb **is a member**, so the alternative-lodging
  substitute sits inside the unit, and Hyatt runs a short-term rental platform of its own.

That last pattern now has three instances in two sessions — casinos owning iGaming, staples
retailers owning their own e-commerce, hotels owning short-term rentals. **Share moves format
before it moves operator**, and a unit whose members own their own substitute will show the
transition in mix long before it shows in revenue. Worth a registered test rather than three
anecdotes: it predicts that measured substitution should show up in segment mix disclosures
and not in unit-level revenue growth, which is checkable against what the corpus already holds.

## Both taxonomy splits declined

Recorded in the master plan. `hotels_resorts_cruise_lines` and `leisure_products` stay whole:
the per-piece claims the standing rule requires do not exist, a split re-keys every peer set
`revenue_share` is computed against, and both units turned out answerable without one — 17
and 9 companies reached eligibility with the taxonomy untouched. The findings stay on the
record for a later pass.
