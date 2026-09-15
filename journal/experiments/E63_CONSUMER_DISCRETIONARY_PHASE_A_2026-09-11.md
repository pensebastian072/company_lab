# E63 — Consumer Discretionary Phase A, first five objects

Worked 2026-09-11, Claude lane, Codex out of tokens. Master plan `339e490`, Phase 3: build
the experts for the five sectors that have none. Consumer Discretionary is the largest of
them — **28 units, 193 companies, zero objects** before this.

Artifacts only. The store was not written; the workbook is unchanged. Advisory / SHADOW.

## What exists now

```
objects built                5 of 28          covering 48 of 193 companies
at >=2 of 3 (Phase B eligible) 4               covering 45 companies
claims                         9               all VERIFIED_LOCAL, all exact containment
```

| unit | n | growth | substitution |
|---|---:|---|---|
| `restaurants` | 17 | MODERATE — food services +4.2% YTD, $711.8bn | ELEVATED — MCD names convenience and grocery stores as competitors |
| `automotive_retail` | 14 | FLAT — NAICS 441 +1.8% YTD, $987.4bn | MODERATE — AZO: customers "pay others to repair… or may purchase new vehicles" |
| `apparel_retail` | 10 | MODERATE — clothing stores +5.8% YTD, $179.2bn | ELEVATED — the unit contains its own substitute (off-price vs full-price) |
| `home_furnishings` | 4 | DECLINING — furniture stores **−1.7%** YTD | ELEVATED — MHK: laminate/wood/LVT/vinyl substitute for each other, plus imports |
| `home_improvement_retail` | 3 | MODERATE — building materials +4.6% YTD | — (no substitution evidence found; stays 1 of 3) |

One Census release — the Advance Monthly Retail Trade Survey — carried the growth quantity
for all five, the way the wholesale release did for three Industrials units. Reading the
sector's own table is cheaper per unit than researching units one at a time, and it puts
every unit on the same basis.

## A skeleton carries only what is factual without research

Each object was created with: its id, sector, version, `status: SHADOW`, the member list
from the book, a `key_metrics` list of the quantities that industry actually reports, and a
refresh class. **Every ordinal started UNKNOWN and moved only when a verified claim arrived.**

Free-text fields — `market_structure`, `moat_mechanism`, `technology_trajectory`,
`regulatory_trajectory` — were left **absent**. The validator does not require them, and
E79's objects filled them with process prose: its `moat_mechanism` read "The cited evidence
is tested for capital, certification, installed-base, network or qualification…", which
describes our own method rather than the industry. An empty field is honest; that is not.

## Two readings that are about the UNIT, not the companies

- **`automotive_retail` is two businesses NAICS 441 puts in one box.** AutoZone's substitute
  — a customer who "may purchase new vehicles" instead of repairing — is simultaneously
  *demand* for the franchised dealers in the same unit. One member's substitution is another
  member's sale. Recorded on the claim as a caveat about the unit's construction, because a
  future reader will otherwise take MODERATE as a uniform statement about fourteen companies.
- **`apparel_retail` contains both sides of its own substitution.** TJX and Ross sell the
  same branded goods cheaper than the full-price chains beside them in the unit. The claim is
  labelled INFERENCE: TJX's filing establishes the off-price model's scale, and the
  substitution direction is my reading of what that means for GAP, ANF, AEO and URBN.

## The quote is lifted, never transcribed

For the table rows the script takes the characters following the row label and cuts the
quote to end **after the two figures that carry the claim** — the year-to-date total and its
percent change. The first attempt used a fixed character count and truncated `76,887` to
`76,88`, leaving a quote that could not support its own value. It verified as present on the
page and was still wrong, which is the exact shape of the problem the verification audit
found: a quote can be findable and still not say what the claim needs.

Every one of the nine claims passes exact character containment, not the overlap fallback.

## Limitation on all five growth readings, stated once

Retail sales are **nominal**. Part of every positive figure is price, not volume, and the
release does not deflate. `home_furnishings` is the only one where the direction is safe
from that objection — a nominal decline means a real decline that is worse.

## What remains in this sector

23 units, 145 companies, no object. Largest: `hotels_resorts_cruise_lines` 17,
`automotive_parts_equipment` 16, `homebuilding` 15, `apparel_accessories_luxury_goods` 13,
`casinos_gaming` 10, `leisure_products` 9, `education_services` 9.

The next cheap sources, by unit: Census New Residential Construction for `homebuilding`;
CLIA passenger counts for the cruise half of `hotels_resorts_cruise_lines` and STR RevPAR
via trade press for the hotel half; state gaming-commission revenue reports for
`casinos_gaming`. `automotive_parts_equipment` is the awkward one — it holds parts
*manufacturers*, so the retail parts line in MARTS is the wrong scope for it.

---

# Part 2, 2026-09-12 — eight more objects, two more Phase-B eligible

```
                              part 1   now
objects built in this sector      5      13  of 28
companies with an object         48     145  of 193
companies eligible (>=2 of 3)    45      71
claims                            9      13   all exact containment
```

Claim sources: PRIMARY_DATA 6, COMPETITOR_FILING 5, TRADE_PRESS 2.

| unit | n | growth | substitution |
|---|---:|---|---|
| `homebuilding` | 15 | DECLINING — single-family starts 808,000 SAAR; total starts **13.5% below July 2025** | ELEVATED — LEN competes with "resales of existing homes and with the rental housing market" |
| `casinos_gaming` | 10 | HIGH — AGA: 2025 GGR +9.2% to $78.72bn, **sixth consecutive record year** | ELEVATED — see below |

Skeletons also created, still at 0 of 3: `hotels_resorts_cruise_lines` 17,
`automotive_parts_equipment` 16, `apparel_accessories_luxury_goods` 13, `leisure_products` 9,
`education_services` 9, `specialty_stores` 7.

## The best single piece of evidence in this sector so far

AGA, on the casino substitution:

> In three states, New Jersey, Pennsylvania and Michigan, iGaming revenue has now surpassed
> commercial brick-and- mortar revenue for the year.

A substitution that has already **completed** in three states, with the magnitudes in the
same report — iGaming +27.6% to $10.74bn against traditional casino gaming +2.3% to
$50.94bn. Recorded with the twist that matters for this unit: the incumbents own much of
the substitute, so share moves channel before it moves operator.

## `hotels_resorts_cruise_lines` — growth REFUSED on scope, and it is a taxonomy question

CLIA publishes exactly the right kind of number — 37.2 million ocean-going cruisers in 2025,
each year a new record — and it describes **3 of this unit's 17 members**. The unit holds
online travel agencies (BKNG, EXPE, ABNB, SABR), hotel brands (MAR, HLT, H, WH, CHH),
timeshare (HGV, TNL, VAC), cruise lines (CCL, RCL, NCLH) and a ski operator (MTN). No single
growth quantity honestly describes that set, and forcing CLIA onto it would be the scope
violation this plan exists to prevent.

So the field stays UNKNOWN and the real finding is recorded instead: **this unit should
probably be four.** Under the standing rule, a split needs one ordinal-supporting claim in
hand per resulting unit before it happens — CLIA would serve the cruise unit, STR RevPAR the
hotel unit, and the OTA and timeshare units need their own sources. That is a decision for
the user, not a unilateral taxonomy edit.

## `automotive_parts_equipment` — not yet, and why

Aptiv's filing offers "we expect long-term growth of global vehicle sales and production",
which is a forward expectation rather than a measured quantity, and a driver sentence about
consumer credit. The industry's real volume series is North American light-vehicle
production, and the available figure (15.08 million units forecast for 2026, revised up 0.4%)
comes from S&P Global Mobility — a commercial forecaster, not a trade body, regulator or
statistical agency. Under the standard this plan set, that is not a qualifying source for
`structural_growth`, so the unit stays UNKNOWN rather than taking it. NADA publishes light-
vehicle SAAR as a trade body and is the next thing to try, with the caveat that sales are not
builds.
