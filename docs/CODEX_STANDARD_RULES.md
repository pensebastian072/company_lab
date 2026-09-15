# The standard rules block — one copy, quoted by every Codex prompt

Every external-research prompt reuses this verbatim. It exists because the rules drifted
once, invisibly, over eight batches, and the drift cost 45 of the 100 external points.

## What went wrong, so it is not reintroduced

From E44 onward every prompt carried some version of:

> "An UNKNOWN with blocking claims is a RESULT; one with nothing behind it is a GAP."
> "E44 needed ZERO demotions across 327 fields - hold that."
> "Five batches running with zero demotions - hold it."
> "Zero gaps across five batches - hold that too."

Read as an incentive rather than as a standard, that is **asymmetric**. An UNKNOWN with a
blocking claim scored as a success in the batch report. An assertion whose citation did
not name the field was a *demotion* — reported as a failure. Abstention was free;
assertion carried the only risk anyone was counting. And the next prompt congratulated the
streak, which closed the loop.

Measured across eight batches, the four fields needing a comparison against named peers —
`moat_trajectory`, `competitive_position`, `competitive_position_trend`,
`company_specific_capture` — went **92%, 83%, 87%, 49%, 65%, 30%, 8%, 0%** filled. Holding
the industry fixed, `upstream_oil_gas` ran 92% at E43, 38% at E44 and 5% at E46.

**Two rules follow and they are not negotiable in a future prompt:**

1. **Never quote a streak back at the researcher.** No "N batches with zero demotions,
   hold that". Past performance on a metric belongs in our report, not in their
   instructions.
2. **State both errors symmetrically, always.** The block below does this. Do not
   reintroduce a sentence that names only one of them.

`clab/external/batch_health.py` now measures the coverage side after every batch and will
say REGRESSION if this starts again.

---

## THE BLOCK — copy verbatim into every prompt

```
## THE TWO ERRORS COST THE SAME

There are two ways to be wrong here and they are equally bad.

  ASSERTING what you cannot evidence.   A categorical with no claim naming that field is
                                        removed by the finalizer. It corrupts the score
                                        and it wastes the search that produced it.

  ABSTAINING when you could have        An UNKNOWN on a field that the evidence would
  established it.                       have supported is a silent loss. It costs the
                                        company real points - the score divides by what
                                        APPLIES, not by what you answered - and unlike a
                                        bad assertion nothing in the pipeline catches it.

Neither is the safe choice. UNKNOWN is not a way to avoid being wrong; it is a different
way to be wrong, and it is the one that leaves no trace.

For every field you leave UNKNOWN, say in the report which you were closer to: was the
evidence genuinely absent, or did you stop short? An honest "I stopped short" is more
useful to us than a confident blocking claim, and it costs you nothing.

## WHAT UNKNOWN MEANS

UNKNOWN means the evidence to establish this field does not exist or could not be
reached. It does NOT mean:

  - the answer is uncertain          -> give the answer your evidence supports
  - the answer is mid-range          -> MODERATE and STABLE are real values, use them
  - peers are hard to compare        -> say so AND give your best-evidenced reading
  - the field feels risky to answer  -> that is the abstention error, see above

UNKNOWN scores as NO_DATA and never as zero, so it does not drag a company down relative
to its peers. That is exactly why it is tempting and exactly why it must be earned.

## CITATIONS ARE REQUIRED, AND THEY ARE NOT A REASON TO ABSTAIN

Every non-UNKNOWN categorical needs a claim whose `field` names it. That rule exists to
stop unbacked assertion, NOT to discourage answering. If you can evidence a field, cite
it and answer it. If the citation requirement is what is stopping you from answering a
field you believe you could establish, say so explicitly in the report - that is a
finding about our process and we want it.

## A QUOTE IS A QUOTATION, NOT A SUMMARY OF THE PAGE

`quote` must appear on the page at `source_url` **verbatim** - the same characters in the
same order. We re-fetch every page here and test exactly that. Encoding is not your
problem: we decode HTML entities, fold Unicode quotes, dashes and spaces to ASCII,
NFKC-normalise, and we run a second comparison that ignores whitespace entirely, so text
copied out of a table still matches. Case does not matter either.

What does NOT match is a sentence you re-worded, a figure you re-typed in a different
format, or a fact from the right organisation on the wrong page.

Measured on 2026-09-11 over all 6,966 quoted claims in the corpus: 97.9% are verbatim on
their page once encoding is handled, and **146 are not on their cited page in any
sequence**. Every one of those 146 scored above the old vocabulary-overlap threshold, with
a MEDIAN score of 1.0 - a perfect match on the words, on text that is not there. We
re-fetched all 146 live on the same day: 7 were the wrong document of the right SEC
filing, 3 we could not reach, and **136 were not on the page, not on any page it links
to, and not anywhere in the same filing.**

So the rule, stated as both errors:

* **Assertion error** - pasting a sentence that is nearly what the page says. It will be
  stored UNVERIFIABLE and the field it backs will earn nothing. Copy, do not paraphrase.
* **Abstention error** - dropping a field because you could not copy a clean sentence.
  A quote may be a fragment. Copy the clause that carries the figure and nothing else;
  a short exact fragment beats a long approximate one.

If the fact is in a PDF, a slide or a table you cannot copy from cleanly, cite the page
you actually read and say so in the report. A citation is data we read, never a string
either of us assembles.

## THE BLIND PASS - DO NOT OPEN A CONCLUSIONS FILE, ASK FOR IT

`journal\flags\external_research_conclusions.json` holds what our local model concluded
(SG and BQ). It is withheld during pass A on purpose, and it is now withheld
MECHANICALLY - it is not written to disk until we release it.

  1. Write pass A from the request and your own research only.
  2. FREEZE it: write `<request_id>.pass_a.json` and tell us it is frozen.
  3. We release the conclusions and record your frozen pass A's sha256.
  4. Then write pass B reconciliation. Never edit pass A afterwards - the hash will not
     match and we will see it.

If a conclusions file is present before step 3, it is stale from an earlier request.
**Do not read it. Say it is there.** You are not being asked to resist temptation; if
you can see it, that is our bug and we want to know.

## COMPETITIVE_POSITION_TREND - ATTEMPT IT ONLY WHERE A SHARED METRIC EXISTS

Do not spend searches forcing this one. Measured across four sectors:

  works    banks (NIM), insurers (combined ratio), oilfield services (operating margin)
           - 27 of 45 in E45, 11 of 52 in Energy
  fails    regulated utilities - 0 of 59, TWICE, and correctly: authorised ROE is set per
           rate case on different schedules by different commissions, and rate-base CAGR
           moves with capex plans that are not comparable

The rule: name the metric FIRST. If the peers in this industry file a shared metric on a
comparable basis over the same two periods, rank-order on it and answer. If they do not,
return UNKNOWN with "no comparable two-period peer metric" and move on - one blocking
claim, not a search campaign.

We built a computed version to replace this and REFUSED it: 36% agreement against your
researched values where chance alone predicts 34.3%, Cohen's kappa 0.026, and it got the
sign wrong as often as right. So there is no fallback. Where you do not establish it, it
stays empty, and that is accepted.

**This carve-out is for THIS FIELD ONLY.** It is not licence to abstain elsewhere, and
the two-errors rule above still governs the other eleven. A carve-out that spreads is how
the last collapse happened.

## KEY_METRICS AND STRUCTURAL_GROWTH - NAME THE FACT, NOT A PROXY FOR IT

Measured by reading all 136 stored quotes of the last Phase A round: no claim sat in the
wrong economic unit, and six of eight fields were strong throughout. Two were not, and
they failed the same way - a quote that is ABOUT the field stood in for a quote that
ESTABLISHES it.

  key_metrics         ~4 of 15 were risk-factor prose. "We depend on highly complex
                      manufacturing processes that require strategic materials,
                      components, and products from limited sources of supply" names a
                      dependency, not a metric. A metric is a named quantity this
                      industry reports and an analyst tracks: book-to-bill, remaining
                      performance obligations, product backlog, component lead times.

  structural_growth   ~5 of 15 rested on an indirect proxy - a benchmark participation
                      count ("17,457 performance results from 23 submitting
                      organizations"), a sentiment index reading of 93.1, a BLS
                      EMPLOYMENT projection standing in for industry growth. A direct
                      reading looks like "WFE projected to increase 6.2% to $110.8
                      billion", or "approximately 15.7 GWdc of PV panels in H1 2025, up
                      126% y/y".

The test for both: does the quote state the quantity, or does it state something
CORRELATED with the quantity? Employment in an industry is not that industry's growth
rate. A sentiment index is not a volume. A count of benchmark submissions is not a market
size. A proxy can be the best evidence available and still not be the fact.

THIS IS NOT A LICENCE TO ABSTAIN, and saying so is the point of putting it here. The two
errors still cost the same. Stopping at a proxy when the direct figure was findable is the
assertion error. Dropping the field because the first source you found was a proxy is the
abstention error, and it is the worse of the two because nothing downstream catches it.

So the instruction is to SEARCH for the direct quantity - a trade association's shipment
or volume series, a regulator's published statistic, a sized market in a filing - and to
answer on it. Where no direct figure exists, you may answer on the best proxy you have,
but then NAME IT AS A PROXY in the claim's own words and say in the report what direct
quantity you looked for and could not find. A proxy declared as a proxy is usable
evidence. A proxy filed as the fact is not.
```
