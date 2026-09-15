# Codex E59 - Financials Phase B, batch 1 of 4

Company research over the 169 Financials companies that Phase A unblocked, in four
stratified batches. This is batch 1: **43 companies**, depth 3, citations required.

> **Operational correction recorded 2026-09-08:** request
> `0f796aae25b60d4865e5` was frozen and then burned after semantic review found that ERIE
> had been ranked against WTW under a wrong `insurance_brokers` assignment. The accepted
> rerun is request `3ff6f3aa0f3608c2f126`, sample
> `E59-financials-phaseb-b1-rerun`. The original remains in the store for audit.

ALRM is deliberately not in any batch. It is Alarm.com, home-security software, carried
into Financials by an error in the book's sector data; the sector field is what is wrong.

## Why four batches

`batch_health.compare()` measures a batch's fill rate against earlier batches on the same
industries. One 169-company delivery is a single research_version with no comparison, and
it was exactly this comparison that eventually caught the eight-batch abstention collapse.
The batches are stratified so each carries a mix of industries.

## Afterwards

```powershell
.venv\Scripts\python.exe -m clab.external.finalize --apply
.venv\Scripts\python.exe -m clab.external.verify --apply
.venv\Scripts\python.exe -m clab.external.batch_health --version <research_version>
```

Then check the store rather than the report, and read `batch_health` before accepting the
batch. E58 arm B is evaluated on this run's `research_version` and its thresholds are
already registered - do not read it off batch 1 alone.

## Prompt

`````
# COMPANY LAB - E59 PHASE B, FINANCIALS BATCH 1 OF 4

Company research. The request file is frozen and is the authority on what to research:

  journal\flags\external_research_request.json
  request_id  3ff6f3aa0f3608c2f126
  43 companies, depth 3, citations REQUIRED

Do not add a company, drop one, or substitute one. The finalizer refuses anything whose
ticker is not on that roster.

## THE ROSTER, by industry

  regional_banking                         12  ABCB BANF CFFN DCOM FHN FULT HTH NWBI RF STBA VLY ZION
  asset_management_custody_banks            4  APAM CRBG SEIC VRTS
  consumer_finance                          4  BFH ECPG NAVI WRLD
  investment_banking_brokerage              4  GS JEF PIPR SF
  mortgage_reits                            2  ABR RITM
  alternative_asset_management              2  APO KKR
  financial_exchanges                       2  CBOE MKTX
  life_insurance                            2  CNO PRU
  insurance_brokers                         2  ERIE WTW
  multi_line_insurance                      2  GNW LNC
  multi_industry_conglomerate               1  BRK-B
  pc_insurance                              1  CB
  retirement_benefits                       1  EQH
  financial_data_ratings                    1  MCO
  diversified_banks                         1  PNC
  reinsurance                               1  RNR
  custody_banks                             1  STT

Every one of these industries already has an industry object in the store. Read the
object for a company's industry BEFORE researching the company - it is the shared context
the company is judged against, and `key_participants` on it is the comparison set for
`competitive_position` and `competitive_position_trend`.

## WHY THIS IS FOUR BATCHES AND NOT ONE

169 companies remain in Financials. They are split into four stratified batches so that
every batch carries a mix of industries rather than one batch being all banks, and so
`clab/external/batch_health.py` can compare batch against batch on the same industries.
A single 169-company delivery would be one research_version with nothing to compare it to.
This is batch 1 of 4. Do not research companies from the other batches.

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

## COMPETITIVE_POSITION_TREND SHOULD MOSTLY WORK HERE

The carve-out above says to name the metric first and abstain where peers do not file a
shared one. Financials is the good case, not the hard one:

  banks           net interest margin, efficiency ratio, deposit beta, CET1
  insurers        combined ratio, reserve development
  asset managers  net flows as a percentage of beginning AUM, fee rate
  exchanges       revenue capture per contract, volumes by asset class

These are filed on a comparable basis by every peer in the bucket, over the same periods.
Where a shared metric exists, rank-order on it and answer. Regulated utilities returned
0 of 59 on this field TWICE and that was correct there; it is not the expected outcome
here.

## THE FOUR FIELDS THAT CARRY 45 OF THE 100 EXTERNAL POINTS

  moat_trajectory  competitive_position  competitive_position_trend
  company_specific_capture

All four need a comparison against NAMED peers. They are the first thing that goes when
abstaining feels safer than asserting, and they went 92% -> 0% filled across eight batches
once. Name the peers, name the metric, then answer.

## STANDING RULES

1. No score, rank, rating, price target or gate. We compute every number.
2. Every claim: source_url, source_date, VERBATIM quote <=300 chars, ~1500-char excerpt
   you actually read. The quote must appear in the excerpt.
3. UNKNOWN scores as NO_DATA, never zero.
4. Never invent a number.
5. One organisation gets ONE independence_domain. A regulator and the firm it regulates
   are different domains; a firm and its own IR page are not.
6. A company's own IR is the weakest source available.
7. Advisory only. "status": "SHADOW". Nothing is promoted.

## BUDGET

43 companies at depth 3. They share a regulatory and macro literature heavily - rates,
credit cycle, Basel endgame, CFPB, PMIERs - so cache aggressively across the batch.
Budget 300-400 searches. Stop and report if you go materially over.

## REPORT

1. Companies delivered, claims and independence domains each.
2. Fill rate on the four rank-order fields above, per industry.
3. Every UNKNOWN on those four, with the metric you looked for and whether it was absent
   or you stopped short.
4. Where an industry object was wrong or missing something you needed.
5. Searches, cache hits, sources.

## WHAT YOU MUST NOT CLAIM

This ranking is NOT validated: top decile ran a -7.6% median 3-year excess return against
SPY on a survivorship-free holdout, only 45.3% beat SPY, and 95.6% of its ranking power
is sector selection. `promoted` is false and stays false.
`````
