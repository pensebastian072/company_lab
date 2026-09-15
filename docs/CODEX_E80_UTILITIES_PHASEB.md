# Codex E80 - Utilities Phase B re-research (59 companies)

Written 2026-09-11 by the Claude lane for session 3 of
`docs/CHAT_B_WORKORDER_CODEX_2026-09-11.md`. Phase B only: the seven utilities industry
objects are live and at 3 of 3, so only the company rows are rebuilt.

Why a third time: E47 filled `moat_trajectory` and `company_specific_capture` 0 of 59;
E53 filled them but reused one evidence window for both fields in 59 of 59 companies
(`journal/experiments/AUDIT_2026-09-08_B3_E53_EVIDENCE_REPRODUCTION.md`) and was retired
whole. Resolution omits rather than falling back, so the sector is absent from the
product: 59 researched companies, zero in the workbook.

**Stage the request the same New York day it will be finalized**, and only after the
Financials batches have released the request file:

```powershell
cd C:\Users\<your-user>\company_lab
$env:PYTHONPATH="C:\Users\<your-user>\company_lab"
.venv\Scripts\python.exe -m clab.external.request --symbols "AEE,AEP,AES,ATO,AVA,AWK,AWR,BKH,CEG,CMS,CNP,CPK,CWEN,CWT,D,DTE,DUK,ED,EIX,ES,ETR,EVRG,EXC,FE,HE,HTO,IDA,LNT,MDU,MGEE,MSEX,NEE,NFG,NI,NJR,NRG,NWE,NWN,OGE,OGS,ORA,OTTR,PCG,PEG,PNW,POR,PPL,SO,SR,SRE,SWX,TLN,TXNM,UGI,UTL,VST,WEC,WTRG,XEL" --depth 3 --sample E80-utilities-phaseb --require-citation
```

The rule sections inside the fence are spliced from `docs/CODEX_STANDARD_RULES.md` by
`scratchpad/gen_e80.py` through the same parser `tests/test_codex_prompt_rules.py` uses,
so this prompt cannot carry a paraphrase of them.

## Prompt

`````
# COMPANY LAB - E80 PHASE B, UTILITIES RE-RESEARCH (59 companies)

Company research. The request file is frozen and is the authority on what to research:

  journal\flags\external_research_request.json
  sample      E80-utilities-phaseb
  59 companies, depth 3, citations REQUIRED

Do not add a company, drop one, or substitute one. The finalizer refuses anything whose
ticker is not on that roster.

## THE ROSTER, by industry

  electric_utilities                         20  AEP DUK EIX ES ETR EVRG EXC FE HE IDA
                                                 LNT MGEE OTTR PEG POR PPL SO TXNM UTL WEC
  multi_utilities                            17  AEE AVA BKH CMS CNP D DTE ED MDU NEE NI
                                                 NWE OGE PCG PNW SRE XEL
  gas_utilities                               9  ATO CPK NFG NJR NWN OGS SR SWX UGI
  water_utilities                             6  AWK AWR CWT HTO MSEX WTRG
  competitive_power_generation                4  CEG NRG TLN VST
  renewable_electricity                       2  CWEN ORA
  independent_power_producers_energy_traders  1  AES

All seven industries have a LIVE industry object in the store with all three structural
fields answered. Do not rebuild them. Read the object for a company's industry BEFORE
researching the company - `key_participants` on it is the comparison set for
`competitive_position`.

## WHY THIS SECTOR IS BEING RESEARCHED A THIRD TIME

Two deliveries exist and neither is usable as a record of these companies.

  E47 (2026-09-05)  four-field fill 0 / 20 / 0 / 0 of 59. `moat_trajectory` and
                    `company_specific_capture` were never answered for a single company.
  E53 (2026-09-07)  four-field fill 48 / 59 / 0 / 48 - but the audit found the SAME
                    source url, quote and excerpt attached to BOTH `moat_trajectory` and
                    `company_specific_capture` for 59 of 59 companies. One evidence
                    window, two fields. Retired whole; all 59 rows are SUPERSEDED.

Because company resolution omits rather than falling back to the older rows, these 59
companies are absent from the product today. This delivery restores a complete sector - if
it is done as research and not as retrieval.

## THE ONE RULE E53 BROKE

**One claim, one field, one evidence window.** `moat_trajectory` asks whether the durable
advantage is strengthening or eroding over time. `company_specific_capture` asks how much
of the industry's structural growth THIS company captures relative to named peers. Those
are different questions answered by different passages. A rate-case outcome can support
one of them; it cannot support both from the same sentence.

The finalizer checks quote reuse per company and the acceptance gate refuses a batch that
reuses a quote across fields. Cite twice, from two passages, or leave the second field
UNKNOWN and say which.

## THE SEARCH SPACE IS NOT THE LOCAL FILING CACHE

E59 batch 3 was refused on 2026-09-11 because its builder's own search definition named
the locally cached 10-K and 10-Q corpus as the search space. Its four peer-comparison
fields fell from 87.5% to 48.8% filled while every quote verified perfectly: 342 of 342
verbatim, and still refused. A company's own filing cannot rank it against named peers.

For utilities the outside sources are unusually good and free:

  state PUC rate-case orders and dockets    authorised ROE, rate base, approved capex
  FERC Form 1, EIA-861, EIA-923             sales, customers, generation mix, reliability
  EEI and AGA statistical yearbooks         peer capex, rate-base growth, customer growth
  NERC and RTO capacity auction results     for CEG NRG TLN VST AES
  state reliability and storm-cost reports  SAIDI/SAIFI, disallowed cost recovery

Use them. A batch whose evidence is overwhelmingly the subject's own IR and 10-K reads as
retrieval whatever its quote quality.

## WHAT COUNTS AS THE BENCHMARK

Not E47. The acceptance gate compares a batch to the previous batch of its sector, and the
previous utilities batch filled two of the four rank-order fields at zero - clearing that
is not evidence of anything. The standard here is the Financials batch 1 and 2 standard on
the THREE fields that apply to regulated utilities - `moat_trajectory`,
`competitive_position`, `company_specific_capture` - which ran about 85% filled with
distinct verbatim citations and roughly 12 claims per company.

## MARKET_SHARE_DIRECTION - TWO DIFFERENT ANSWERS IN ONE SECTOR

  regulated electric, gas, water, multi     UNKNOWN, pre-registered and correct: a
  (52 companies)                            franchised service territory has no
                                            contestable share. One blocking claim, no
                                            search campaign.
  competitive_power_generation,             RESEARCH IT. Merchant generators and IPPs
  renewable_electricity, IPPs               compete for capacity awards, PPAs and share of
  (7 companies)                             generation. EIA-923 and RTO auction results
                                            settle it.

## THE FOUR FIELDS THAT CARRY 45 OF THE 100 EXTERNAL POINTS

  moat_trajectory  competitive_position  competitive_position_trend
  company_specific_capture

Three apply here. `competitive_position_trend` is carved out for regulated utilities in the
section below and its zero is accepted - it returned 0 of 59 twice, correctly, because
authorised ROE is set per rate case on different schedules by different commissions. The
carve-out is for that ONE field: the other three are expected to be answered, from two
distinct passages where two fields are answered.

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

## STANDING RULES

1. No score, rank, rating, price target or gate. We compute every number.
2. Every claim: source_url, source_date, VERBATIM quote <=300 chars, ~1500-char excerpt you
   actually read. The quote must appear in the excerpt, and it must be copyable verbatim
   from the page - verification certifies on exact character containment, not on vocabulary
   overlap. If you cannot copy the sentence, you do not have the citation.
3. UNKNOWN scores as NO_DATA, never zero.
4. Never invent a number. A citation is data to be read, never a string to be assembled -
   one URL in batch 3 was built from a guessed accession number and verification caught it.
5. One organisation gets ONE independence_domain. A regulator and the firm it regulates are
   different domains; a firm and its own IR page are not.
6. A company's own IR is the weakest source available.
7. Advisory only. "status": "SHADOW". Nothing is promoted.

## BUDGET

59 companies at depth 3. Regulated utilities share a literature heavily - rate cases, FERC,
EIA, storm cost recovery, data-centre load growth - so cache aggressively across the batch.
Budget 400-500 searches. Stop and report if you go materially over.

## REPORT

1. Companies delivered, claims and independence domains each, and claims per company.
2. Fill rate on the three applicable rank-order fields, per industry.
3. Every UNKNOWN on those three, with the metric you looked for and whether the evidence
   was absent or you stopped short.
4. Confirmation, per company, that no quote is reused across fields.
5. Where an industry object was wrong or missing something you needed.
6. Searches, cache hits, sources, and the share of claims from outside the subject's own
   filings and IR.

## WHAT YOU MUST NOT CLAIM

This ranking is NOT validated: its top decile ran a -7.6% median three-year excess return
against SPY on a survivorship-free holdout, only 45.3% beat SPY, and 95.6% of its ranking
power is sector selection. `promoted` is false and stays false.
`````
