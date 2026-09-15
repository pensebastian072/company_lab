# E52 - what the conviction score actually weighs, and a v2 that is NOT shipped

Written 2026-09-05, acting on E48's finding that the evidence terms reorder the conviction
score more than every substantive conclusion combined.

## E48's result was a design choice written down, not an emergent property

Unpacking `external_confidence` into its own internals (0.30 domains + 0.30 verified +
0.25 coverage + 0.075 depth + 0.075 freshness) and reallocating v1's 100 points:

```
how much we know (coverage)   31.0
how hard we looked (depth)     8.9
evidence quality               8.1
what we concluded             12.0
local measured half           40.0

(coverage + depth) : substance = 3.3 : 1
```

**Coverage is counted three times.** As `external_coverage` (12), again as
`core_fields_known` (16, a weighted subset of the same denominator), and again inside
`external_confidence` (0.25 x 12 = 3). Depth is counted twice: `research_depth` (8) and
0.075 x 12 = 0.9 inside confidence.

**And the deeper defect: `core_fields_known` scores whether a field is ANSWERED, not what
it SAYS.** `external.get(f) not in (None, UNKNOWN)` is the whole test. A company with
`company_specific_capture = NONE` and one with `HIGH` score identically on its 8 points;
`current_moat_strength` of WEAK and of EXCEPTIONAL score identically on its 4.

Only `moat_trajectory` reads its own value. So **of the 60 external points, 12 read a
conclusion and 48 read the existence of one.** That is precisely why E48 found
B_evidence -> C_full order-preserving: C adds only `moat_trajectory` and the flags,
because B already contained everything else.

## v2, built and measured

`gates.CRITERIA_WEIGHTS_V2` counts each thing once and reads the conclusions:

```
framework_band        15     evidence_quality      10   domains+verified+freshness only,
financial_engine      10                                no coverage, no depth
survivability          8     research_depth         6
framework_coverage     7     core_fields_value     32   what capture/moat/trajectory SAY
                             competitive_position  12   a second conclusion actually read
```

`external_coverage` is dropped as a separate criterion - `core_fields_value` covers the
fields that matter, weighted, and covers them better. UNKNOWN scores 0.4 on every value
scale, the middle and never the floor, preserving the package-wide rule that an
unanswered field is not a bad answer.

## CORRECTION 2026-09-06 - the table below was measured wrong, twice

**Every v1 number in the next section is wrong and understates v1.** Codex found it while
re-running the post-E51 comparison and it is confirmed: `gates.criteria()` reads
`scored["coverage"]` and `scored["external_confidence"]`, and the harness passed a `scored`
dict holding only `claims_total` and `claims_verified` - the keys **v2** reads. `_scale`
returns 0.0 for a missing value, so `external_coverage` (12) and `external_confidence` (12)
were silently zeroed: **24 of v1's 100 points, in a comparison against v2.**

The second attempt fixed only half of it. `company_external` has **no `coverage` column** -
coverage comes from `score.score_company(...)["coverage"]` - so passing `r.get("coverage")`
handed v1 `None` again.

Corrected, with both versions receiving the same evidence:

```
                          v1       v2
pooled sd              16.18 -> 10.62      v1 discriminates MORE, not less

communication_services 10.78 -> 13.06   better
information_technology  7.81 -> 13.02   better
utilities               3.62 ->  4.38   better
energy                 15.70 ->  9.11   WORSE
financials              7.56 ->  6.80   WORSE

sectors improved: 3 of 5
```

The registered ship rule needed >= 4 sectors AND pooled sd not lower. It fails on both.
**v2 does not ship** - which was the decision before, but the reasoning inverts. The
published claim was "v2 is not clearly better". The truth is that **v1 is clearly better
and the measurement had been handicapping it.**

The bug is the class this repo already has a rule for: a default that covers a WIRING
error must be loud. `gates.REQUIRED_SCORED_KEYS` now raises on a `scored` dict missing
v1's inputs, and two tests pin it - one asserting the raise, one asserting that no
`coverage` column exists to read it from.

## The measurement, over all 289 researched companies (WRONG - see the correction above)

```
        mean     sd    min    max
v1      40.4  12.84   20.8   72.9
v2      54.7   9.63   37.2   96.3

Spearman(v1, v2) = 0.827   median |rank move| 26 of 289   90th pct 77

within-sector sd            v1        v2
  utilities            n=59  2.29 ->  4.38     better
  information_tech     n=18  8.21 -> 13.02     better
  financials           n=87  6.20 ->  6.80     marginal
  communication_svcs   n=47  8.10 ->  6.18     WORSE
  energy               n=71 12.20 ->  9.11     WORSE
```

## The honest verdict: v2 is not clearly better, and it is NOT shipped

It fixes two defects that are real and independently demonstrable - the triple-counted
coverage and the unread conclusions. But its measured effect on the thing E48 complained
about is **mixed**: overall spread FALLS (12.84 to 9.63), it helps the two sectors where
coverage was low and hurts the two where coverage was high, and it moves the median
company 26 places out of 289 with a 90th percentile of 77. PYPL moves 199 places.

A change that large, on a score nobody has validated, needs to beat v1 on something
before it ships. Right now it does not.

## And the measurement is confounded, which is the reason to wait

`core_fields_value` is 32 of v2's 100 points and it reads
`company_specific_capture`, `current_moat_strength` and `moat_trajectory`. **Three of
those four fields are 0% filled in Utilities and Communication Services** because of the
E49 abstention defect - 106 of the 289 companies here.

So every one of those companies gets `UNKNOWN_VALUE = 0.4` on most of the 32 points, which
flattens exactly the sectors v2 was meant to help, and inflates the sectors where the
fields survived. **Measuring v2 today measures the E49 defect, not the design.**

## Decision

**Hold.** v1 stays wired into `evaluate()`. v2 exists, is tested, and is not called.

Re-run this comparison after E51 reports. If the symmetric prompt restores the four
fields, v2 gets a fair test for the first time; if it does not, v2's core premise -
that there are conclusions worth reading - is itself in question and the answer is not
a reweighting.

Registered in advance so the re-run cannot be read selectively: **v2 ships only if, on
post-E51 data, it raises within-sector sd in at least 4 of 5 sectors and does not lower
the pooled sd.** Anything less and the two double-counts get fixed in v1 instead, which
is the smaller change and does not need this argument.

## Out of scope

Predicts nothing about returns. No promotion state changes. `promoted` stays false.

## Post-E51 result - 2026-09-05

E51 restored all four target fields for all 47 Communication Services companies without
a single demotion or unverifiable claim. Replacing E49 with E51 keeps this comparison at
n=289.

The registered measurement now improves within-sector standard deviation in 4 of 5
sectors: Communication Services 10.78 -> 13.06, Financials 6.20 -> 6.80, Information
Technology 8.21 -> 13.02, and Utilities 2.29 -> 4.38. Energy falls 12.20 -> 9.11.
Pooled standard deviation falls 12.91 -> 10.62. The registered rule therefore fails and
v2 does not ship.

The rerun found that the original table's v1 numbers reproduce only when v1 receives an
empty scored-evidence object while v2 receives stored claim totals. That silently zeroes
v1's external-coverage and external-confidence criteria. An apples-to-apples audit using
the same scored evidence for both versions is less favorable to v2: it improves 3 of 5
sectors and pooled standard deviation falls 16.04 -> 10.62. The no-ship decision is
unchanged. Full evidence and both tables are in `E51_results.md`.


---

## CLOSED 2026-09-06 - both remedies built, measured, refused

Re-run on the fully repaired book: E51 supersedes E49 and E53 supersedes E47, so the
three fields `core_fields_value` depends on are populated instead of empty. 285 companies,
latest research version each, both arms receiving the same evidence (the asymmetry that
wrecked the first two attempts is now caught by `gates.REQUIRED_SCORED_KEYS`).

### v2 - read the conclusions rather than their presence

```
pooled sd    v1 13.37  ->  v2 10.39

communication_services  n=47   10.78 -> 13.06   better
information_technology  n=15    7.09 -> 12.38   better
utilities               n=59    9.91 ->  8.95   WORSE
financials              n=87    7.56 ->  6.80   WORSE
energy                  n=71   15.70 ->  9.11   WORSE

sectors improved 2/5        registered rule needed >= 4 AND pooled not lower
```

**DO NOT SHIP**, and by a wider margin than on the broken book.

The instructive part is Utilities. On the broken book v2 looked *better* there
(2.29 -> 4.38); with the fields actually filled it is *worse* (9.91 -> 8.95). v2's apparent
advantage came precisely from the fields being empty - v1 was being dragged down by
coverage terms that had nothing to score. That is the confound the hold was called for,
and it inverted exactly as predicted.

### v1b - the registered fallback: count coverage once

Identical weights; the `external_confidence` criterion reads a coverage-free, depth-free
quality measure, so coverage is counted once instead of three times and depth once instead
of twice.

```
pooled sd    v1 13.37  ->  v1b 13.38
Spearman(v1, v1b) 0.9983      median |rank move| 1 of 285

communication_services  10.78 -> 10.78      energy      15.70 -> 15.70
utilities                9.91 ->  9.91      financials   7.56 ->  7.36
information_technology   7.09 ->  7.85
```

Three sectors identical to two decimals. **DO NOT SHIP** - not because it harms anything
but because it changes nothing, and a scoring change that moves the live book is not worth
making for no measured gain.

**The triple count is real in the weights and nearly inert in effect.** The coverage
component of `external_confidence` is 0.25 x 12 = 3 points, confidence is saturated for
most companies, and what it does vary with is correlated with `external_coverage` anyway.
The earlier write-up made a great deal of "counted three times"; the honest correction is
that the arithmetic was right and the consequence is negligible.

### What the whole thread settles

E48's finding stands as a description: the evidence terms do reorder more than the
conclusions, and 48 of the 60 external points read the existence of a conclusion rather
than its content. Both available remedies were then built and measured, and **neither
improves the instrument.** The conviction score stays exactly as it is.

That is a real answer, not a failure to decide. It also relocates the question: the
weighting is not the binding constraint, so if the conviction score is to get better, the
next place to look is what it is made of rather than how those parts are weighed. Nothing
here is evidence about returns; `promoted` stays false.
