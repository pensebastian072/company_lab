# E15 verdict: the split FAILS, one dimension was genuinely a retrieval failure

Run 2026-08-18 on 30 companies (20 under-floor stratified across Real Estate, Energy,
Utilities, Financials and Information Technology; 10 controls already clearing the
floor). Raw records in `journal/experiments/E15_raw/`, table in `E15_results.md`.

## Result against the bars fixed in advance

| | measured | bar | |
|---|---|---|---|
| P1 median dimensions scored | 4.5 -> **4.0** | >= +1.5 | **FAIL** |
| P2 unverified quote rate, arm B | **3.33%** (arm A: 0.00%) | <= 1.0% | **FAIL** |
| P3 controls losing a dimension | **7 of 10** | <= 1 | **FAIL** |
| P4 added seconds per company | 2.2 | <= 25 | PASS |

**Arm B is dead.** Splitting BQ into a 7-dimension call and a 4-dimension call makes the
7 dimensions that already worked *worse*: 7 of 10 control companies lost a dimension they
had scored in the single 11-dimension call, and the median under-floor company ended with
fewer dimensions than before. A smaller prompt did not help the model concentrate; it
removed the context in which the easy dimensions were being answered.

## What did replicate, and it is one dimension

| dimension | scored in A | scored in B | of 20 |
|---|---:|---:|---:|
| network_effects | 0 | 1 | 20 |
| manufacturing_complexity | 3 | 4 | 20 |
| data_advantages | 0 | 1 | 20 |
| **economies_of_scale** | **2** | **18** | 20 |

`economies_of_scale` went from 2 of 20 to **18 of 20** on a dimension-specific query. That
is a retrieval failure, cleanly demonstrated: the evidence was in the filing, the single
BQ query never surfaced it, and the model answered as soon as it did.

The other three did not move. **The prediction registered before the run was half right**:
`network_effects` staying null was predicted; `manufacturing_complexity` recovering was
predicted and did **not** happen. Those three are E12's applicability question, not a
retrieval problem.

## The exploratory arm, stated as exploratory

Arm C - keep the production 11-dimension call and *add* the targeted weak-dimension call,
taking any dimension either one scored - was computed after the fact from the same raw
records. It **cannot lose a dimension by construction**, so it is not comparable to B on
this table:

* under-floor median dimensions 4.5 -> **5.0**;
* companies clearing the 6-dimension floor **3 -> 9 of 20**;
* controls: every one held or gained (`6,6,6,7,8,8,9,9,9,11` -> `7,7,7,8,8,9,9,9,9,11`).

That is a real coverage move and it is also exactly the shape of result that must not be
adopted off an unregistered arm. Hence E16.

## The caveat that matters more than the gain

The floor exists so that a moat verdict cannot rest on two or three dimensions. A repair
pass that recovers **one** dimension pushes companies to exactly 6 with the sixth being
`economies_of_scale` almost every time. That is a floor cleared on a technicality unless
the recovered dimension is genuinely informative. **E16 must report which dimensions make
up the 6 for every company it newly clears**, and if the answer is "the same six
everywhere", that is a finding against the repair, not for it.

## Fabrication: 2 events, and the direction is the E07 pattern

The P2 failure rests on **2 flagged quotes out of 60 slots** - GRBK (`data_advantages`)
and PBF - both in the targeted call, against 0 of 30 in arm A. n is far too small to put
a rate on, and E15 could only attribute per *company*, not per *call*, because it summed
the two calls' counters. But the direction is the one E07 already established: every
configuration that abstains less cites material that is not in the pack. E16 fixes the
attribution so the targeted call carries its own number.

---

# E16 - a targeted repair pass, registered

Pre-registered 2026-08-18 after E15 and before any code that could ship. Production BQ is
unchanged: the 11-dimension call runs as it does today. **Only when its result lands under
the 6-dimension floor** does a second, dimension-targeted call run over the same chunk
pool, and any dimension it scores that the first call left null is merged in.

The conditional is deliberate and is the reason this is cheap: 463 of 1,498 companies are
under the floor, so the repair pass is ~2.5 h of GPU rather than ~8 h, and a company that
already answers is never touched.

## Sample

**60 under-floor companies**, drawn seeded and stratified in proportion to where the
under-floor population actually lives (Real Estate 76.2% of 105, Energy 53.6% of 69,
Utilities 39.0% of 59, Financials 37.0% of 254, plus IT, Industrials, Consumer
Discretionary, Health Care), and **20 controls** that already clear the floor.

## Pass criteria, fixed now

| | passes if |
|---|---|
| **Q1** | Floor clearance among the under-floor sample rises to **>= 35%** (E15's exploratory arm reached 45% on n=20; 35% is the bar that survives that estimate being optimistic). |
| **Q2** | The **targeted call's own** unverified-quote rate is **<= 1.0%**, measured separately from the production call. This is the criterion that kills the change if it fails, exactly as M3 decided E07. |
| **Q3** | **No control loses a dimension.** Guaranteed by construction, so a failure here is a wiring bug and must be treated as one, not as a result. |
| **Q4** | `economies_of_scale` recovery replicates at **>= 60%** of the under-floor sample (E15: 90% on n=20). |
| **Q5** | **Rank integrity is reported, not passed.** Within-sector Spearman of `composite_strict` before vs after, over the affected companies, plus the dimension composition of every newly cleared company. A repair that reshuffles a sector's ranking is doing more than filling gaps and must be described in those words. |

Q1, Q2, Q3 and Q4 must all pass for this to reach production. Q5 is a reporting duty with
no bar - its point is that the write-up cannot omit it.

## Prediction, stated before running

Q1 and Q4 replicate. Q2 is the live risk and I put it near even. If Q2 fails, the honest
outcome is that **BQ coverage cannot be bought at all without a human review step**, and
E12's denominator question becomes the only remaining lever - a worse position than today,
but a true one.

## What this cannot establish

Nothing about whether BQ predicts anything. There is no forward-return grader. More
companies clearing the floor means more companies get a band; it does not mean the bands
are right. `promoted` stays false. Any write-up says so in those words.
