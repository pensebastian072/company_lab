# E12 Amendment 1 - P2 as written does not decide anything

Written 2026-08-18, **before any rubric, prompt, threshold or denominator is changed**,
and before P1 can be evaluated (the E07 winner is not known yet - the `mistral:7b` arm is
still running). Amends `E12_bq_denominator_preregistration.md`; that document stands
except where this one replaces P2.

## Why an amendment was needed

The original P2 reads:

> For each of the four worst dimensions, abstention is **concentrated by sector** - the
> gap between the highest and lowest sector null rate exceeds **40 percentage points**.

That criterion could not be computed from the artifact `bq_abstention` wrote: it stored
each sector's **worst four** dimensions, and the minimum of a spread is exactly the entry
a worst-four view drops. The measurement now emits the full 11 x sector matrix and a P2
table. **No rubric code moved to get this** - it is a reporting change to a research
script, pinned by `tests/test_bq_abstention_p2.py`.

With the criterion finally computable, on the incumbent `qwen2.5:7b` cache
(1,498 companies, 2026-08-18, sectors with n >= 30):

| dimension | spread | lowest sector | highest sector | sectors >= 75% null |
|---|---:|---|---|---:|
| intellectual_property | 80.5pp | Information Technology 2.1% | Real Estate 82.5% | 1/11 |
| technological_advantage | 70.3pp | Information Technology 2.6% | Real Estate 72.8% | 0/11 |
| regulatory_barriers | 59.5pp | Utilities 0.0% | Information Technology 59.5% | 0/11 |
| **network_effects** | 54.8pp | Communication Services 43.5% | Utilities 98.3% | **10/11** |
| distribution | 52.4pp | Consumer Staples 0.0% | Real Estate 52.4% | 0/11 |
| **manufacturing_complexity** | 52.0pp | Materials 46.3% | Utilities 98.3% | **5/11** |
| **economies_of_scale** | 50.0pp | Consumer Staples 31.5% | Real Estate 81.6% | **2/11** |
| switching_costs | 48.0pp | Information Technology 1.5% | Real Estate 49.5% | 0/11 |
| **data_advantages** | 43.1pp | Communication Services 50.0% | Real Estate 93.1% | **7/11** |
| brand | 39.1pp | Consumer Staples 0.0% | Energy 39.1% | 0/11 |
| customer_relationships | 30.5pp | Consumer Staples 1.4% | Energy 31.9% | 0/11 |

**Nine of eleven dimensions clear the 40pp bar, including every dimension the model
answers most of the time.** `intellectual_property` has the largest spread in the whole
table and is 26.5% null overall - nobody thinks IP is an inapplicable question. A bar
that licenses dropping the dimensions that work is not a test of applicability; it is a
test of whether Real Estate and Utilities differ from Information Technology, which they
do on every dimension at once.

The original registration already knew this. It called `network_effects` a FAIL "40.0% to
94.4% is a 54pt spread, **but the floor is 75%+ in 9 of 11 sectors**". That qualifier is
doing the actual work and it was never written into the criterion. This amendment writes
it in.

## The trap, named before choosing

The table above is already computed. **Any threshold picked now is picked knowing which
dimensions it passes**, which is the same failure mode this project refuses everywhere
else. Two protections:

1. The choice below must be justified by **mechanism** - what the number means about the
   evidence pack - and must be stated as a rule that would have been written the same way
   before the table existed.
2. The July prior is on the record and is scored honestly against whichever rule is
   chosen: it predicted `manufacturing_complexity` and `data_advantages` PASS,
   `network_effects` FAIL.

## The three candidate rules, and what each licenses

**A. Spread only (the literal original).** Passes 9 of 11 dimensions. Rejected: it would
license dropping `intellectual_property` and `technological_advantage`, and it cannot
tell "inapplicable in two sectors" from "unanswerable in ten".

**B. Spread AND a high-floor cap** - spread > 40pp and the dimension is >= 75% null in no
more than N sectors. Encodes the qualifier the registration used in prose. Sensitive to N
in a way that is hard to argue from mechanism.

**C. Spread AND an answerable-somewhere floor** - spread > 40pp **and** the dimension's
null rate in its *best* sector is at or under 40%. The mechanism is direct: if the model
can answer the question for the businesses that plainly have the thing, then silence
elsewhere is evidence about the business. If the model cannot answer it anywhere - if
even the best sector is majority-null - then the pack cannot support the question and
dropping the dimension launders a retrieval failure into a scoring rule (H2, not H1).

Under C, on the incumbent cache: `network_effects` (best sector 43.5%) FAILS,
`data_advantages` (50.0%) FAILS, `manufacturing_complexity` (46.3%) FAILS, and
`economies_of_scale` (31.5%) PASSES. **That contradicts two thirds of the July prior**,
and it means the honest outcome is *one* candidate dimension for a sector-applicability
denominator, not four - with `network_effects`, `manufacturing_complexity` and
`data_advantages` all routed to the evidence-retrieval fix instead.

**Recommendation: C**, with the 40% floor stated as "the model answers it for a majority
of companies in at least one sector". P3 is unchanged and still binding: a named written
business reason is required on top, per sector, and no dimension is dropped globally.

## Open, and blocking

* **P1 cannot be evaluated yet.** It is defined on the E07 winner's cache. On the
  incumbent, 463 of 1,498 (30.9%) are under the floor - P1's bar is 10%.
* **The E07 winner may not exist.** Three arms reported; the fourth (`mistral:7b`) is
  running. A direct probe on 2026-08-18 measured mistral at 77.6 / 64.9 / 28.6 s for one
  SG / BQ / MG generation (~57 s mean), which puts a 1,498-company re-score at **~71 h
  against the incumbent's 17.0 h** - it fails E07's throughput criterion M5 by roughly
  4x before its abstention or fabrication rate is read at all.
* If no candidate wins E07, P1 is evaluated on the incumbent and fails, and E12 proceeds
  on the rule chosen above.

## Unchanged from the original registration

P3 (named business reason, required for any change at all), P4 (report within-sector rank
correlation after any denominator change), the floor stays at 6 of the *applicable*
dimensions, and the limit that matters most: **nothing here tests whether BQ predicts
anything.** There is no forward-return grader. A denominator change alters the composite
of hundreds of companies with no way to check whether the new scores are better, only
whether they are more internally consistent. `promoted` stays false regardless.
