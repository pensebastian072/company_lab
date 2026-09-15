# E91 — ten ordinals retracted: the quotes are not on their sources, and now we know

2026-09-12, closing the chain that began with E90's stamp. SHADOW throughout.

```text
                                      E90 close   E91 close
objects at 3 of 3                            72          64
companies whose unit has >=1 ordinal      1,361       1,354
companies eligible for Phase B            1,202       1,192
answered ordinals with no evidence            11           1   (and that one is OUR fault)
```

**Eligibility went down again, deliberately, for the second time today.**

## The test that made it actionable

E90 found 11 answered ordinals whose only support failed containment. That is a rule-2 violation
by definition — *every non-UNKNOWN field backed by a claim passing exact containment on its cited
page* — but it was not acted on immediately, because `overlap_only` has three causes and only one
is the claim's fault. `relocate.py`'s own docstring lists them:

1. an IR index page was cited instead of the specific release it links to;
2. the figure came from a PDF or a deck while the cached page is the HTML landing page;
3. the quote was never on that source.

`scripts/relocate_object_claims.py` ran all 11 through `relocate.resolve_claims` against the
**live** web. That function re-fetches the cited url, and if the quote is not there it reads the
links the cited page itself publishes and tries the closest ones on the same host — and for SEC
urls it expands the entire accession.

```text
10 distinct urls, every one fetched and READABLE ("ok")
  + 124 documents in one SEC accession, read from one complete-submission fetch
  +  21 documents in another
  + 112 documents in a third

outcomes: {'still_absent': 11}
```

**Eleven for eleven.** Causes 1 and 2 are excluded: the pages are live, they were read, the links
they publish were followed, and three full SEC accessions were searched document by document. The
quotes are not there.

## What was retracted

```text
alternative_asset_management      replication_difficulty  HIGH      -> UNKNOWN  numeric_mismatch
climate_infrastructure_finance    replication_difficulty  HIGH      -> UNKNOWN  overlap_only
custody_banks                     replication_difficulty  HIGH      -> UNKNOWN  overlap_only
diversified_banks                 replication_difficulty  HIGH      -> UNKNOWN  overlap_only
dram_hbm                          structural_growth       HIGH      -> UNKNOWN  absent
electronic_components             structural_growth       MODERATE  -> UNKNOWN  overlap_only
mortgage_reits                    replication_difficulty  MODERATE  -> UNKNOWN  overlap_only
mortgage_reits                    substitution_risk       ELEVATED  -> UNKNOWN  overlap_only
reinsurance                       replication_difficulty  HIGH      -> UNKNOWN  overlap_only
retirement_benefits               structural_growth       MODERATE  -> UNKNOWN  numeric_mismatch + overlap_only
```

Nine objects, ten fields. Eight fell from 3 of 3 to 2 of 3; `mortgage_reits` fell from 2 of 3 to
**0 of 3**, because both of its ordinals rested on a single `overlap_only` claim each — and it had
been counted as Phase-B eligible on that the whole time.

`dram_hbm` is the starkest: `structural_growth = HIGH` on a quote **absent** from its page, not
merely out of sequence. `retirement_benefits` is the one the repo already knew about — its ICI
claim is the cautionary example inside `verify.match_quote`'s docstring, and its overlap stamps at
exactly the 0.8182 that docstring quotes.

**The claims were not deleted.** Each stays in its object, stamped UNVERIFIABLE with its match mode
and overlap. The claim is the record of what was asserted; deleting it would erase the evidence
that the retraction was warranted, and a later pass that finds the real source can re-point it and
re-answer the field.

## My own script caught my own overreach, on its first run

The first dry run wanted to retract an eleventh field: `ai_accelerators`' `substitution_risk`,
whose only claim is `unreachable` — we could not read the page at all. Retracting on that would
blame the researcher for our network, which is the opposite of the rule applied everywhere else
today and the rule `acceptance.check_containment` already follows when it counts unreachable pages
outside the rate entirely.

The condition now requires every supporting claim to be **tested and failed** (`UNVERIFIABLE`),
never merely untestable (`SELF_ATTESTED`), and it skips with the reason printed. So the remaining
count of unsupported ordinals is **1, and it is ours to fix by reading the page, not theirs**.

That is the second time today a guard written in the session caught the session's own work on its
first run — the first was `agreeing_growth` retracting three ordinals written that morning. Worth
noticing as a pattern rather than a coincidence: **the guards that fire on their author are the
ones worth keeping**, and both would have passed silently if they had been written to confirm what
had already been done.

## What this chain cost and what it bought

```text
E83  wrote 5 computed ordinals                             +57 companies eligible
E84  retracted 3 of them on window instability             -42
E90  stamped every object claim with its real match state     0   (measurement only)
E91  retracted 10 ordinals whose quotes are not on source  -10
```

Net from the computed route and the verification chain together: **+5 companies**, and a corpus
that now states its own evidential state in the artifact rather than in a separate store. The
honest summary of today's eligibility number is that it moved 1,026 → 1,192 on research, and that
**52 of those companies were removed again by this session's own checks.**

## Left open, deliberately

- `ai_accelerators` substitution_risk — one unreadable page. Read it, then decide.
- The 25 `overlap_only` claims that were NOT the sole support for a field still sit beside good
  claims, stamped UNVERIFIABLE. They did not go through relocation because the field did not
  depend on them. They should, eventually: a bad citation beside a good one is still a bad
  citation, and `--all` on `relocate_object_claims.py` is the switch for it.
- Whether `mortgage_reits` at 0 of 3 should now be retired by the lifecycle gate is a separate
  decision and was not taken here.
