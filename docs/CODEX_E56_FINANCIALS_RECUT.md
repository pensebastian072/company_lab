# Codex E56 - Financials Phase A2: the five re-cut objects

Phase A only: 5 industry objects. No company research, no request file, no roster.

E54 built 15 Financials objects. Three came back with `structural_growth`,
`replication_difficulty` AND `substitution_risk` all UNKNOWN - each argued, none a gap -
because the buckets did not describe one business. That refusal is what this run acts on:
the ten companies have been re-cut, six into objects that already exist, and five new
units need objects before the company phase can run.

Do NOT rebuild `multi_sector_holdings`, `specialized_finance` or
`commercial_residential_mortgage_finance`. They have zero members now and are superseded.

`journal/experiments/E56_registered.md` carries a registered prediction about THIS run's
output, which is why the prompt below says nothing about what the answers should look
like. Do not put it in front of the researcher.

## Afterwards

```powershell
.venv\Scripts\python.exe -m clab.external.research_ingest --apply
.venv\Scripts\python.exe -m clab.external.verify --apply
```

`research_ingest --apply` rewrites every industry and sector object from disk, not just
the new ones, so hash the pre-existing rows before and after to prove they did not move.
Then check the store rather than the report: 5 objects present, claim counts and domains
per object, and the corpus unverifiable rate still at 0.077%. Note that
`external_claim.industry_id` is populated on COMPANY claims too, so filter object claims
on a null ticker.

> **Dated correction (2026-09-07):** 0.077% is the historical prompt input. After PDF
> extraction-state and numeric-quote verification fixes, the corpus rate is 64/5,233 =
> 1.22%. See `journal/experiments/verification_rate_correction_2026-09-07.md`.

## Prompt

`````
# COMPANY LAB - E56 PHASE A2: THE FIVE RE-CUT FINANCIALS OBJECTS

Phase A only. Build industry objects. NO company research, NO request file, NO roster.
Do not run `clab.external.request`, `clab.external.finalize` or `clab.external.score`,
and do not touch `journal\flags\external_research_request.json`.

## BUILD THESE FIVE

  private_mortgage_insurance             3  ACT ESNT NMIH
  retirement_benefits                    2  EQH VOYA
  climate_infrastructure_finance         1  HASI
  commercial_mortgage_banking_servicing  1  WD
  multi_industry_conglomerate            1  BRK-B

Read an existing object as a template first:

  D:\company_lab_data\external\research\industries\regional_banking\industry_state.json
  D:\company_lab_data\external\research\sectors\financials\sector_state.json  (update, do not recreate)

## WHY THESE EXIST - YOUR OWN E54 FINDING IS THE REASON

You researched `multi_sector_holdings`, `specialized_finance` and
`commercial_residential_mortgage_finance` as single objects and returned UNKNOWN on all
three structural fields for each, arguing that no shared answer was true of the members.
That was correct and it was acted on. The ten companies have been re-cut:

  BRK-B  -> multi_industry_conglomerate      VOYA, EQH -> retirement_benefits
  HASI   -> climate_infrastructure_finance   WD        -> commercial_mortgage_banking_servicing
  ACT, ESNT, NMIH -> private_mortgage_insurance

  JEF, LAZ -> investment_banking_brokerage   CACC -> consumer_finance   EFC -> mortgage_reits
  (those three objects already exist and are NOT rebuilt - the companies simply join them)

## FOUR OF THE FIVE HAVE ONE OR TWO MEMBERS. THAT IS NOT A PROBLEM

An industry object describes an INDUSTRY, not the companies from our book that sit in it.
`key_participants` is where the real comparison set goes, and for these units most of it
is private, mutual or foreign and will never appear in an S&P 500 book:

  private_mortgage_insurance      MGIC, Radian, Arch MI, and the FHA/USDA/VA channel that
                                  competes with private MI outright
  retirement_benefits             Fidelity, Empower, TIAA, Principal, Corebridge,
                                  Nationwide, MassMutual
  climate_infrastructure_finance  Brookfield, Copenhagen Infrastructure, KKR and BlackRock
                                  infrastructure funds, tax-equity desks at the big banks
  commercial_mortgage_banking     Berkadia, Newmark, CBRE Capital Markets, Greystone, and
                                  the GSE lender networks themselves
  multi_industry_conglomerate     Danaher, Honeywell, Loews, Markel, and the Japanese
                                  trading houses

A one-company unit is fully researchable. If a field is UNKNOWN here it must be because
the evidence is absent, not because our book holds one name.

## METRICS THAT MATTER, to seed key_metrics

  private_mortgage_insurance      insurance-in-force, new insurance written, persistency,
                                  PMIERs available assets vs required, cure and default
                                  rates, credit mix, GSE pricing changes (LLPAs), and the
                                  FHA premium as the substitution boundary
  retirement_benefits             net flows by channel, general vs separate account
                                  balances, spread income and crediting rates, surrender
                                  and lapse behaviour, fee rate on advice and asset
                                  management, RILA and annuity sales, reinsurance of
                                  legacy blocks
  climate_infrastructure_finance  portfolio yield vs cost of capital, managed assets, the
                                  spread and its direction, contracted vs merchant
                                  exposure, counterparty credit, tax-equity and ITC/PTC
                                  policy risk, the refinancing wall
  commercial_mortgage_banking     origination volume by channel, the servicing book (UPB)
                                  and its runoff, MSR valuation and escrow earnings,
                                  gain-on-sale margin, GSE caps and delegated lender
                                  status, credit risk retained
  multi_industry_conglomerate     the parts, and how they are financed. Underwriting
                                  float and its cost, book value per share, retained
                                  earnings vs distributions, capital redeployment and the
                                  hurdle rate, succession, and whether the parts share
                                  anything beyond a balance sheet

## ON BRK-B SPECIFICALLY

It was in an incoherent bucket and now has its own. That does not automatically make it
coherent - a conglomerate may still be a portfolio rather than an industry. If a shared
answer would be fiction, UNKNOWN with a blocking claim is the correct return, exactly as
before. Say which it is.

## EVIDENCE DEPTH FOLLOWS THE EVIDENCE

Do not aim for a fixed number of claims per object. These five differ a great deal in how
much public literature exists - PMIERs and GSE pricing are heavily documented, a
climate-infrastructure lender much less so. Some objects should end up thinner than
others and that is the honest outcome; a uniform count across five different literatures
would tell us you stopped at a quota.

## VOCABULARIES, enforced by clab/external/schema.py

  structural_growth        DECLINING | FLAT | MODERATE | HIGH | EXCEPTIONAL | UNKNOWN
  replication_difficulty   LOW | MODERATE | HIGH | EXTREME | UNKNOWN
  substitution_risk        SEVERE | ELEVATED | MODERATE | LOW | UNKNOWN
  refresh_class            STRUCTURAL | QUARTERLY | EVENT_DRIVEN

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

5 objects, four of them small units with a thin book presence but a real trade
literature. Budget 60-100 searches. Stop and report if you go materially over.

## REPORT

1. The 5 objects: claims and independence domains each.
2. Every UNKNOWN, with what blocked it and whether the evidence was absent or you
   stopped short.
3. Whether `multi_industry_conglomerate` is a real research unit or a portfolio.
4. Whether any of the five should instead have joined an existing object - you have now
   seen these companies twice and are better placed than we are to say.
5. Searches, cache hits, sources.

## WHAT YOU MUST NOT CLAIM

This ranking is NOT validated: top decile ran a -7.6% median 3-year excess return against
SPY on a survivorship-free holdout, only 45.3% beat SPY, and 95.6% of its ranking power
is sector selection. `promoted` is false and stays false.
`````
