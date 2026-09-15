# E29 - the applicability map: asking a REIT only what a REIT has

Pre-registration written 2026-08-25, **before any profile, rubric, prompt or denominator
is changed**. This is the second half E19 deferred in writing ("A REIT should not be
*asked* about manufacturing complexity at all"), and it discharges E12's P3, which has
been open since 2026-08-16.

E19 made the floor a weight. That stopped the cliff deleting companies. It did not stop
the framework **asking questions that have no referent** and then counting the silence
against the company.

## What is already measured, before this is registered

Stated first so nothing below is presented as a prediction that was really a
retrodiction. All of it motivated this document.

**E12 Amendment 1 (2026-08-18) already fixed the rule and already ran it on the BQ moat
dimensions.** Rule C: a dimension may be marked inapplicable for a sector only if its
null rate **in its best sector is at or under 40%** - if the model can answer the
question for the businesses that plainly have the thing, then silence elsewhere is
evidence about the business; if even the best sector is majority-null, the pack cannot
support the question and dropping it launders a retrieval failure into a scoring rule.
Under Rule C, of the four worst dimensions only `economies_of_scale` (best sector 31.5%)
qualified; `network_effects` (43.5%), `manufacturing_complexity` (46.3%) and
`data_advantages` (50.0%) all FAILED and were routed to the retrieval fix instead. That
contradicted two thirds of the July prior, and it is on the record.

**The 2026-08-24 audit itemised where the points actually go.** Summed across the 104
Real Estate companies: `bq_moat` unassessed availability **793**, `sg_tam_expanding`
**344**, `sg_capacity_backlog_contracts` **207**, and a further **448** of scored
shortfall inside `bq_moat`. Utilities are smaller and the same shape on the judged half:
`bq_moat` unassessed **208**, `sg_tam_expanding` **188**.

**`NOT_APPLICABLE` already fires about 1,000 times and never for this reason.** Its
largest users are `fe_gross_margin` 334 and `bs_current_ratio` 293 - **accounting
absence**, a line the filing does not contain. Not one entry in any profile's suppression
set exists because the *business* has no such thing. That is the gap.

## The mechanism problem, which is the reason this needs its own registration

`SectorProfile.resolve_status` grants `NOT_APPLICABLE` only when the profile nominates
the sub-test **AND** the value is genuinely absent. On the measured half that is a real
two-part test and it is load-bearing: UNH is nominally a FINANCIAL filer but files a full
income statement, so its margins are scored rather than suppressed.

**On the judged half the second condition collapses.** For an LLM sub-test "the value is
absent" IS "the model abstained" - there is no independent fact to check nomination
against. So nominating a judged sub-test in a profile is a one-condition rule wearing a
two-condition rule's clothes, and it converts every abstention in that sector into
`NOT_APPLICABLE`, which leaves the coverage denominator, which raises coverage, which
lifts companies over the 0.80 band gate.

That is a large, self-flattering effect available from a one-line edit. It is the same
shape as lowering the BQ floor from 6 to 4, which E12 refused. Rule C is the only thing
standing between the two, so Rule C is imported here **unchanged** and applied per
sub-test rather than per moat dimension.

## What is a candidate, and what is explicitly not

A sub-test is a candidate **only if the referent does not exist for the business**. A
REIT has no order backlog. A REIT has no product TAM in the sense the question means.

A sub-test where the sector simply **scores badly** is never a candidate, however large
the point loss. The distinction is not stylistic:

* **Category error** - the question has no referent, the model abstains, the points
  become `NO_DATA`, and the company is charged for an absence that is not a defect.
* **True low score** - the question has a referent, the answer is computable, and it is
  low. Marking that inapplicable **deletes a real weakness and inflates the sector.**

**`fe_margin_expansion` for Utilities is the second kind and is ruled out here, on the
record, despite being 133 points of the loss the 2026-08-24 audit itemised.** A regulated
utility's margin is computable and its inability to expand it is the regulatory bargain -
a true economic fact about the business, not a question with no referent. Suppressing it
would make regulated utilities look better by declining to measure the thing that makes
them what they are. It is also already unreachable by accident: `fe_margin_expansion` is
nominated by the REIT, FINANCIAL, MORTGAGE_REIT and INSURANCE profiles and still scores
wherever the number exists, which is the two-part test doing its job.

So the candidate set is drawn **only from the judged half** (SG, BQ, MG), where
abstention is the observable, and every entry must pass the bar below.

## The rule, fixed now

For a (sector, sub-test) pair to enter the map, **all five** must hold. P1-P3 are E12's,
imported verbatim in substance; P4 and P5 are new and are the price of extending Rule C
beyond the moat dimensions.

| | passes if |
|---|---|
| **P1** | **Spread.** The sub-test's null rate across sectors with n >= 30 spans more than **40 percentage points** between its lowest and highest sector. |
| **P2** | **Answerable somewhere (Rule C).** Its null rate in its **best** sector is at or under **40%**. If the model cannot answer it for a majority of companies in any sector, the pack cannot support the question and this is a retrieval failure, not an applicability fact. |
| **P3** | **A named, written business reason** for that sector, in the map document, in prose, naming what the business does not have. No entry is admitted on a null rate alone. E12's P3, unchanged and still the binding one: **P3 is required for any change at all.** |
| **P4** | **The sector is near-total.** The sub-test's null rate in the nominated sector is at or above **85%**. A category error is close to universal within the sector; a 60%-null sector is a mixture and this instrument cannot separate its halves. |
| **P5** | **Not scored elsewhere in the same sector for the same reason.** If more than **15%** of the nominated sector's companies were SCORED on the sub-test, the referent demonstrably exists for that business model and the entry is refused. |

P4 and P5 are stated by mechanism and would have been written the same way before the
table existed: P4 says a category error is a property of the business model rather than
of the company, and P5 says a question the model answered for one in six of the sector's
companies plainly has a referent there. Both are one-sided - they can only shrink the
map, never grow it.

**The map is per (sector, sub-test). Nothing is dropped globally, and nothing is dropped
for a sector that fails any of the five.**

## Required reporting after the change

1. **Within-sector Spearman of `composite_strict`, before vs after, per sector** - E12's
   P4 duty. A change that reshuffles the ranking *inside* a sector is doing more than
   filling gaps and must be described as such.
2. **Counts**: companies gaining a band, per sector, and the median coverage move per
   sector. If Real Estate's median coverage crosses 0.80 on this change alone, that is
   the headline and it is reported as a **denominator** move, never as companies having
   become better understood.
3. **The refused entries, with their numbers**, in the same document as the admitted
   ones. A map that lists only what it dropped is not auditable.
4. **The scored-shortfall residue.** Of Real Estate's itemised loss, how much was
   category error (removed here) and how much was the model scoring the company low
   (untouched). The 448 points of scored shortfall inside `bq_moat` are **not** in scope
   and the write-up must say so.

## Prior, stated before computing

I expect the map to be **small - between 2 and 6 entries, concentrated in Real Estate**,
and I expect P2 to be the criterion that does most of the killing, exactly as it did on
the moat dimensions. Specifically:

* `sg_capacity_backlog_contracts` for Real Estate **passes**. A REIT has no backlog and
  the question is answered routinely for Industrials.
* `sg_tam_expanding` for Real Estate **fails P2**. "TAM" is a question the model is
  vague about everywhere, and I expect no sector under 40% null.
* No BQ entry is admitted beyond `economies_of_scale`, because BQ is one sub-test
  (`bq_moat`, 15 points) built from eleven dimensions - the map's unit and the rubric's
  unit do not line up, so an admitted dimension changes the **denominator inside
  bq_moat**, not a sub-test status.
* **Utilities gain little.** Their large losses are `bq_moat` and `sg_tam_expanding`, and
  I expect both to fail.
* Median coverage moves by **less than 0.03** overall, and Real Estate's stays **below
  0.80**.

Stated now so a small map is not later called a disappointing result, and so that "drop
the questions Real Estate does badly on", which is the convenient answer, has to beat a
written prediction that the honest map is nearly empty.

## What this experiment cannot establish

**Nothing here tests whether any of it predicts anything.** There is no forward-return
grader; it needs ~50 weekly snapshots and the `as_first_filed` view, and **5 exist**. A
denominator change alters the composite and possibly the band of hundreds of companies
with **no way to check whether the new scores are better** - only whether they are more
internally consistent. Any write-up must say that in those words. `promoted` stays false
regardless.

**And it resets comparability.** Every rubric change makes the snapshot series
discontinuous at the change date, which is a direct cost against the one clock that
matters. That cost is accepted here only because the alternative is continuing to charge
104 companies for not having a backlog.

## Outputs

* `clab/research/e29_applicability.py` - the measurement, emitting the full
  sub-test x sector null matrix and a P1-P5 table per candidate.
* `journal/experiments/E29_results.json` / `.md` - per-sector before any pooled number.
* `journal/experiments/E29_applicability_map.md` - the argued map, admitted and refused
  entries together, one written business reason per admitted entry.
