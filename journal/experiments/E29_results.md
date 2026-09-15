# E29 results - no rubric change

Measured 2026-08-25 over **1,501 scorecards** with
`python -m clab.research.e29_applicability`. Raw numbers in `E29_results.json`. The
argued map, with every refusal and its numbers, is `E29_applicability_map.md` - read that
one for the reasoning; this file is the summary and the audit trail.

## Verdict

**The applicability map is empty. No profile, rubric, denominator or prompt changed.
`promoted` is still false.**

Of **132** (sub-test, sector) pairs, **1** cleared P1+P2+P4+P5 and was refused on **P3**,
the named-written-business-reason test that E12 called binding.

## The judged-half null matrix, per sector (%)

Sectors with n >= 30. This is the full grid, never a worst-four view - E12's Amendment 1
exists because a spread cannot be computed from a table that drops its own minimum.

| sub-test | IT | Ind | Fin | CD | HC | RE | Mat | CS | Ene | Uti | Com |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bq_moat | 0.0 | 0.8 | 0.0 | 0.0 | 0.0 | 2.8 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| mg_balance_sheet_stewardship | 13.2 | 7.6 | 17.1 | 11.9 | 12.9 | 16.0 | 2.6 | 6.7 | 15.5 | 8.5 | 12.8 |
| mg_buyback_discipline | 12.6 | 15.2 | 28.8 | 15.0 | 25.2 | 0.0 | 24.7 | 8.0 | 32.4 | 0.0 | 25.5 |
| mg_ceo | 0.5 | 1.5 | 0.0 | 0.5 | 0.0 | 0.0 | 1.3 | 0.0 | 0.0 | 0.0 | 2.1 |
| mg_ma_track_record | 2.6 | 2.7 | 7.8 | 3.1 | 4.9 | 19.8 | 2.6 | 4.0 | 8.5 | 22.0 | 0.0 |
| mg_reinvestment_quality | 10.5 | 11.8 | 26.5 | 14.0 | 15.3 | 0.0 | 18.2 | 2.7 | 33.8 | 0.0 | 17.0 |
| **sg_capacity_backlog_contracts** | 38.9 | 38.4 | 78.6 | 66.8 | 50.9 | **65.1** | 63.6 | 84.0 | 39.4 | 28.8 | 80.9 |
| sg_demand_drivers_3_5yr | 0.0 | 0.4 | 0.4 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 2.1 |
| sg_multiple_independent_drivers | 1.1 | 4.6 | 8.6 | 7.8 | 4.3 | 7.5 | 16.9 | 4.0 | 11.3 | 6.8 | 8.5 |
| sg_revenue_growth_sustainable | 8.9 | 3.4 | 3.9 | 6.2 | 5.5 | 7.5 | 6.5 | 2.7 | 7.0 | 8.5 | 10.6 |
| sg_secular_not_cyclical | 2.1 | 1.9 | 0.8 | 0.5 | 0.0 | 4.7 | 1.3 | 1.3 | 0.0 | 1.7 | 4.3 |
| **sg_tam_expanding** | **22.1** | 64.6 | 79.8 | 69.4 | 78.5 | **81.1** | 79.2 | **85.3** | 74.6 | 79.7 | 53.2 |

Two rows carry the whole story. Nine of the twelve judged sub-tests are answered for
almost everyone in almost every sector.

**`bq_moat` reads ~0% null everywhere because E19 already fixed it**: the cliff became a
weight, so BQ is always "scored" on a reduced `max_points` and the unassessed remainder
is carried by the synthetic `bq_moat_unassessed`. The map's unit and the rubric's unit do
not line up for BQ - exactly as the registration predicted - so the moat dimensions are
governed by E12 Amendment 1's Rule C one level down, where only `economies_of_scale`
survived, and it is refused here on P3.

## The one machine pass

`sg_tam_expanding`, Consumer Staples: spread 63.2pp (P1 PASS), best sector Information
Technology 22.1% (P2 PASS), sector null 85.3% (P4 PASS), +82.6pp over the sector's own
2.7% median null rate on the rest of SG (P5 PASS).

**Refused on P3.** A packaged-foods company has a total addressable market. The 85.3% is
a mature business not writing about expansion that is not happening, and the honest score
for that is low rather than absent. P5's +82.6pp margin is the proof that this is not a
retrieval failure: Consumer Staples filings are 2.7% null across the rest of the
component. The model can read them fine. It is declining to claim something untrue.

## Loss itemisation, judged half

`category_error` = availability never assessed (NO_DATA plus E19's `*_unassessed`
weight). `scored_shortfall` = points the model assessed and did not award. **The map can
only ever move the first, and it moved none of it.**

| sector | category error | scored shortfall |
|---|---:|---:|
| Financials | 2,798 | 3,079 |
| Industrials | 1,775 | 3,488 |
| Real Estate | 1,527 | 1,275 |
| Consumer Discretionary | 1,515 | 2,926 |
| Health Care | 1,310 | 2,152 |
| Information Technology | 1,008 | 2,298 |
| Energy | 857 | 1,021 |
| Materials | 642 | 1,191 |
| Consumer Staples | 570 | 1,152 |
| Utilities | 512 | 739 |
| Communication Services | 358 | 655 |

Real Estate: `bq_moat_unassessed` 793, `sg_tam_expanding` 344,
`sg_capacity_backlog_contracts` 207, 183 elsewhere; plus **448 of scored shortfall inside
`bq_moat` that was never in scope**.

**Financials lose more to category error than Real Estate does**, and every sector's
scored shortfall exceeds its category error. The judged half's biggest problem is not
that the wrong questions are asked.

## Prior scored

Predicted 2-6 entries concentrated in Real Estate; delivered **zero**. The named
prediction (`sg_capacity_backlog_contracts` Real Estate PASSES) was **wrong** - 34.9% of
REITs were scored on it, because a long-term lease is contracted forward revenue.
`sg_tam_expanding` Real Estate was predicted to fail P2 and instead **passes P2 and fails
P4**: right verdict, wrong mechanism. Full table in `E29_applicability_map.md`.

## What this does not establish

Nothing here tests whether any of it predicts anything. There is no forward-return
grader; it needs ~50 weekly snapshots and the `as_first_filed` view, and **5 exist**. An
empty map means the scores did not move, so nothing was made better or worse - what
changed is that a plausible fix was checked and refused in writing.

## Follow-on, not started

`sg_tam_expanding` and `sg_capacity_backlog_contracts` are **askable** - the model answers
both routinely in at least one sector - so they belong to the evidence-and-prompt fix,
not to a denominator change. That path has a losing record (E15 failed 3 of 4, E17's R4
is still open and unrepaired) and nothing here should be read as a reason to expect it to
work.
