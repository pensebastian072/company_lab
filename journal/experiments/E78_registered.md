# E78 — registered: does a SUPPORTS claim predict an answered field, outside Industrials?

Registered 2026-09-09 by Chat A, **before the join was run.** Corpus state at registration:
60 active industry objects (49 pass 3-of-3, 11 below ship bar), 20 Industrials objects
retired earlier today, 508 industry-object claims ever filed (277 CONTEXT, 226 SUPPORTS,
5 CONTRADICTS).

Status: SHADOW / advisory. `promoted` is false and nothing here changes that.

## Where the question came from

Writing the E65 IT prompt turned up a one-sector regularity: of the 26 objects the
Industrials tree shipped, **20 have zero claims with `stance = 'SUPPORTS'`, and those are
exactly the 20 that answered 0 of 3 structural fields and were auto-retired.** 11 SUPPORTS
claims across 145.

The tempting conclusion is a cheap ingest check — reject an object that arrives with no
SUPPORTS claim, and E61 never reaches the store. Before writing that check the regularity
has to survive the obvious confound.

## The confound, named in the same breath as the finding

**Industrials is bad at both things at once.** It is the only sector that cleared 0 of 26 on
the completeness gate and it is the sector with 140 of 145 claims on one independence
domain. A pooled association over all objects would be manufactured by that single sector
even if SUPPORTS claims and answered fields are unrelated everywhere else.

So the pooled number is not the test. The test is what is left when Industrials is removed.

## Population and measurement

Unit of analysis: one industry object.

  ACTIVE      `industry_intelligence` rows where status IS NULL or != 'SUPERSEDED'  (n=60)
  RETIRED     the 20 auto-retired Industrials objects, reported SEPARATELY, never pooled
              into the primary test — they are the extreme cases and including them is
              how a tautology gets reported as a finding

Per object:

  answered    count of `structural_growth`, `replication_difficulty`, `substitution_risk`
              that are non-null and not UNKNOWN                                   (0..3)
  supports    claims with `ticker IS NULL` and `stance = 'SUPPORTS'`
  supports_ord  the subset of those whose `field` names one of the three ordinals
  claims      all claims with `ticker IS NULL`
  domains     distinct `independence_domain`

`supports` and `supports_ord` are kept apart on purpose. `supports_ord` is close to
tautological — the finalizer strips a categorical with no claim naming its field, so an
answered field nearly implies a claim on that field. **The proposed ingest check uses ANY
SUPPORTS claim, so ANY SUPPORTS is the primary predictor.** If only `supports_ord` carries
the relation, the check is measuring its own rule back at itself and buys nothing.

## Predictions, registered

**P1 (primary).** Among ACTIVE objects **excluding Industrials** (expected n=54), objects
with `supports = 0` answer fewer structural fields than objects with `supports >= 1`, by a
median difference of **at least 1 field**.

**P2 (operational, decisive for shipping the check).** Across ALL active objects, the
number of objects that answer **3 of 3** and have **zero** SUPPORTS claims is **0**.
Any such object is a false positive of the proposed gate: it concluded everything and would
have been rejected at ingest. One is enough to disqualify a hard block.

**P3.** The relation is not an artifact of depth alone — i.e. `supports = 0` still
separates answered-field counts after conditioning on objects with `claims >= 4`.

## What refutes what

- P1 fails → the regularity is Industrials' signature, not a corpus property. The E61
  diagnosis stands as a description of E61 and the ingest check does not generalize.
- P2 fails at any count > 0 → the check must not be a hard block. Fall back to a loud
  warning in the ingest report, which is what this repo's "a default that covers a wiring
  error must be loud" rule asks for anyway.
- P3 fails → what is being measured is thin evidence, not unsupported evidence, and the
  existing claim-count aspiration already covers it.

## What this cannot establish either way

n=60 objects across 7 sectors, built by one researcher under prompts that changed between
sectors. Sector, prompt version and builder are entangled and this design does not
separate them. A pass here says the check would not have fired on good objects in the
corpus we have; it does not say the check is right, and it says nothing about whether any
of this ranking predicts returns.
