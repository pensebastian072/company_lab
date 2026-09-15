# E84 — the three-year window was supposed to add coverage; it took coverage away instead

2026-09-12, immediately after E83, same session. The plan was the obvious next step named at
the end of E83: give `industry_growth` a multi-year window so it could speak to the 13 units
the one-year window had to refuse. It does. The result is the opposite of what was expected,
and the opposite is the correct answer.

## Headline

```text
                                    E83 close   E84 close
objects at 3 of 3                          71          75
companies eligible for Phase B          1,141       1,099     <- DOWN 42
units filled from the revenue route          5           7
units RETRACTED                              0           3
```

**Eligibility went down, deliberately.** Three of the five units E83 filled that morning were
measuring the window, not the industry, and they were retracted the same day.

## What the second window actually showed

`revenue_ttm_3y_ago` is in the scorecards for 1,466 of 1,500 companies, so the 3-year window
cost nothing to compute. The deflator needed the CPI series rather than the news release
(which publishes only a 12-month change): BLS public API **v2**, August-to-August, giving
**+2.947% a year** over three years against **+3.397%** over one. (v1 returns only three years
of data and would have left the 3-year window effectively un-deflated — the error that turns a
shrinking industry into a growing one. The applier now cross-checks the series' 1-year figure
against the release's and refuses if they differ, so it can never cite a figure it did not
use.)

Then both windows were run over every unit with an unanswered `structural_growth`:

```text
unit                                  cos    1y real  1y band      3y real  3y band
regional_banking                       89      +4.3%  MODERATE       +6.5%  HIGH        DIFFER
engineered_motion_components           25      +2.3%  MODERATE       -1.3%  FLAT        DIFFER
electronic_equipment_instruments       17      +5.7%  MODERATE       +2.7%  MODERATE    same
civil_aerospace_platforms_components   15     +15.1%  EXCEPTIONAL  refused  -           3y refuses
health_care_services                   14     +11.5%  HIGH           +8.0%  HIGH        same
flow_filtration_equipment               9      +5.4%  MODERATE       +2.9%  MODERATE    same
government_mission_services             6      -1.0%  FLAT           +5.2%  MODERATE    DIFFER
building_fixtures_access                5      -0.3%  FLAT           -3.4%  DECLINING   DIFFER
industrial_controls_sensors             5      +3.4%  MODERATE       +0.3%  FLAT        DIFFER
auction_marketplaces                    4      +3.0%  MODERATE      +10.9%  HIGH        DIFFER
business_process_outsourcing            4      +3.2%  MODERATE       +7.6%  HIGH        DIFFER
commercial_vehicle_powertrain           4      -5.5%  DECLINING      -3.5%  DECLINING   same
internet_infrastructure_services        4      +4.4%  MODERATE       +4.0%  MODERATE    same
```

**The two windows disagree on 8 of the 13.** Not by a little: `government_mission_services`
goes FLAT to MODERATE, `auction_marketplaces` MODERATE to HIGH, `engineered_motion_components`
MODERATE to FLAT. `regional_banking` — the largest unit in the book at 89 companies — reads
MODERATE at one year and HIGH at three, which is the rate cycle turning up precisely where
E83 predicted it would.

## Then I ran it against E83's own five, which is the part that mattered

```text
unit                          written    1y               3y                verdict
hotels_resorts_cruise_lines   MODERATE   +4.2% MODERATE   +6.8% HIGH        UNSTABLE
automotive_parts_equipment    FLAT       -0.1% FLAT       -3.0% DECLINING   UNSTABLE
leisure_products              FLAT       -0.4% FLAT       -7.6% DECLINING   UNSTABLE
household_products            DECLINING  -3.5% DECLINING  -3.4% DECLINING   stable
food_distributors             FLAT       +1.1% FLAT       +0.4% FLAT        stable
```

Three of five. `leisure_products` is the worst of them — FLAT on one year, **−7.6% real a year
DECLINING** on three — and it is the unit I had argued hardest for, because E82 had already
refused it once for want of any published quantity. The one-year number let it through; a
second window says the one-year number was a trough comparison.

Retracted via `scripts/retract_unstable_growth.py`: field back to UNKNOWN, computed claim
removed, 42 companies out of eligibility. The script only ever removes a claim carrying this
module's own `COMPUTED, NOT PUBLISHED.` marker on a `bls.gov` URL, so it cannot touch
researched evidence and is idempotent.

## The rule that came out of it

`industry_growth.agreeing_growth` is now the only supported way to get an ordinal from this
route: **every window must pass every guard, and they must land in the same band.** Applied
to all 18 candidates it fills 5 and refuses 13.

The five it fills:

```text
electronic_equipment_instruments   16   +5.7% real   MODERATE    -> 3 of 3
health_care_services               14  +11.5% real   HIGH        -> 1 of 3
flow_filtration_equipment           9   +5.4% real   MODERATE    -> 3 of 3
commercial_vehicle_powertrain       4   -5.5% real   DECLINING   -> 3 of 3
internet_infrastructure_services    4   +4.4% real   MODERATE    -> 3 of 3
```

Four units went to **3 of 3** on a stricter test than the three that were retracted ever
passed. That is the trade: 42 companies of eligibility given up, 4 objects completed, and the
ones that remain survive a test the others failed.

**What the agreement test still cannot see, and why `--units` stays required.** Two windows of
the same wrong aggregate agree with each other perfectly. The test says nothing about whether
the members belong in one unit — `specialty_stores` and `tobacco` are refused by the
concentration and dispersion guards, not by this one, and a unit that is simply mis-grouped
would sail through. Scope is still a human judgement, so the applier still refuses to run
without an explicit list.

## What this says about the rest of the plan

This is a generalisable result and it is worth stating as one, because the same shape will
recur:

**Any ordinal computed from a single window of market data should be assumed unstable until a
second window is tried.** It cost nothing here — the second window was already in the
scorecards — and it overturned 60% of the morning's work. The cheapest version of this test
should run before anything computed is written, not after.

It also closes the question E83 left open. The 13 refused units are not waiting on a
multi-year window any more; the multi-year window exists and it refuses 11 of them for a
better reason than the one-year window refused them. What they are waiting on is a **published
industry quantity**, which is what the plan's rule 4 asked for in the first place. Rule 4 was
right, the exception is narrower than it looked, and the honest count of what the revenue route
can carry is **7 units, not 18**.

## Artifacts

- `clab/external/industry_growth.py` — `load_revenue(window_years)`, annualised growth,
  `agreeing_growth`; 20 tests.
- `scripts/apply_industry_growth.py` — per-window deflators from the BLS series, agreement
  gate, release-vs-series cross-check.
- `scripts/retract_unstable_growth.py` — marker-scoped, idempotent, backs up first.
