# E50 - did I train the researcher to abstain?

Registered 2026-09-05, before running any arm and before re-researching any company.

## The observation this is testing

Across eight batches the four rank-order fields - `moat_trajectory`,
`competitive_position`, `competitive_position_trend`, `company_specific_capture`, worth
**45 of the 100 external points** - fell from 92% filled to 0% filled, monotonically. It
survives holding the industry fixed: `upstream_oil_gas` ran 92% at E43, 38% at E44 and 5%
at E46, with the same industry object and the same peer set.

It is not sector heterogeneity (measured, refuted), not peer comparability (measured,
Spearman 0.066), and not a sector-versus-company variance problem (63.1% of external-score
variance is company-level within industry).

## The hypothesis, and why it is uncomfortable

**I built an asymmetric incentive into the prompts and reinforced it every batch.**

From E44 onward each prompt carried some version of:

> "An UNKNOWN with blocking claims is a RESULT; one with nothing behind it is a GAP."
> "E44 needed ZERO demotions across 327 fields - hold that."
> "Five batches running with zero demotions - hold it."
> "Zero gaps across five batches - hold that too."

An UNKNOWN with a blocking claim is scored a success by my own reporting. A non-UNKNOWN
whose citation does not name the field is a *demotion*, reported as a failure. So
abstention is free and assertion is risky, and I congratulated the streak in the next
prompt every time - which is a reinforcement loop, not a standard.

If this is right, the layer's decline is a measurement artifact I manufactured, and the
two most recent sectors are not homogeneous - they are under-answered.

## Method - one variable, four arms is too many

**One variable per arm.** The four candidate mechanisms entangled in batch order are the
abstention incentive, the citation rule's enforcement, the complete-sector switch at E46,
and the removal of researched fields at E49. This tests **only the first**.

Universe: the **11 `interactive_media_services` companies** already researched in E49 -
CARG, GOOGL, GTM, META, MTCH, PINS, PPLI, QNST, RDDT, TRIP, YELP. They filled 0 of 4 on
every one of the four fields, so the floor is unambiguous and any movement is signal.

Two arms over the identical roster, identical request spec, identical citation rule
(`require_citation` stays ON), identical vocabularies, identical two-pass rule:

| arm | prompt |
|---|---|
| **A control** | the E49 prompt verbatim, re-run |
| **B** | the E49 prompt with **only** the abstention-praise removed |

Arm B deletes these and nothing else:
- every sentence congratulating a prior batch's zero demotions or zero gaps
- "An UNKNOWN with blocking claims is a RESULT; one with nothing behind it is a GAP"

and replaces them with a symmetric statement:

> Both errors cost the same. An UNKNOWN you could have established is as wrong as an
> assertion you could not evidence. Report which you were closer to on each field you
> left UNKNOWN.

The citation requirement itself is UNCHANGED in both arms. This is not a test of whether
citations should be enforced - E42 settled that they should. It is a test of whether
praising the abstention streak changed behaviour.

Arm A must be re-run rather than reusing the E49 record, so both arms face the same model
on the same day. Reusing the stored result would confound the arm with elapsed time.

## Registered predictions

| # | criterion | prediction |
|---|---|---|
| 1 | arm B 4-field fill | **>= 25%** (E49 delivered 0%) |
| 2 | arm A 4-field fill | **<= 10%**, reproducing E49's floor |
| 3 | B minus A on 4-field fill | **>= 20 points** |
| 4 | demotions in arm B | **<= 2 of 44 assertions** - removing the praise must not cost citation discipline |
| 5 | UNVERIFIABLE claims in arm B | **0**, as in every batch since E42 |

## What each outcome licenses

- **1, 3 and 4 hold.** The abstention incentive is real and the decline is substantially
  mine. Rewrite every prompt to state the two errors symmetrically, stop quoting streaks
  back at the researcher, and **re-run Utilities and Communication Services** before
  either sector's ranking is read.
- **B does not beat A.** The prompts are not the cause. The next arm tests the
  complete-sector switch, which is the other change that lands at E46 where the steepest
  drop begins.
- **4 fails - B fills the fields but demotions rise.** The praise was load-bearing and
  the honest trade is stated, not hidden: we bought discipline with coverage. Then the
  question becomes which of the two the layer needs, and that is a decision, not a
  measurement.
- **A itself fills well above 10%.** Then E49's 0% was not stable and something varies
  run to run. Everything above is suspended until that is understood, because an
  unstable instrument cannot measure a sector.

## Cost

22 company-records over 11 companies, two arms. E49 cost 564 claims for 47 companies, so
roughly 130 claims and 60-80 searches. Cheap against the alternative, which is buying an
eighth sector on an instrument that has lost 45 of its 100 points.

## Out of scope

Predicts nothing about returns. Does not change any promotion state. The ranking remains
unvalidated - E05's top decile ran a -7.6% median 3-year excess against SPY on a
survivorship-free holdout and 95.6% of the measured half's power is sector selection.
`promoted` stays false, status stays SHADOW.

**No fourth sector is bought until this reports.**
