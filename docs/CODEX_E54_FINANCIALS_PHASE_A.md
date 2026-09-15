# Codex E54 — Financials Phase A

Phase A only: 15 industry objects. No company research, no request file, no roster.

**Runs in parallel with E53 (Utilities).** E53 owns
`journal/flags/external_research_request.json`. Nothing in E54 touches it, and nothing in
E54 runs `clab.external.request` or `clab.external.finalize`. Phase A writes industry
objects, which are keyed by `industry_id` and ingested by `clab.external.research_ingest`.

Financials: 257 companies, 87 researched, 170 remaining. 15 objects unblock all 170.
Three objects already exist — `regional_banking`, `life_insurance`, `pc_insurance` — and
must NOT be rebuilt.

Session handoff for whoever supervises this: `docs/HANDOFF_E54_FINANCIALS_PHASE_A.md`.

## Afterwards

```powershell
.venv\Scripts\python.exe -m clab.external.research_ingest --apply
.venv\Scripts\python.exe -m clab.external.verify --apply
```

Then verify against the store rather than the report: 15 objects present, claim counts and
domains per object, and the corpus unverifiable rate still at 0.09%.

> **Dated correction (2026-09-07):** 0.09% is the historical prompt input. After PDF
> extraction-state and numeric-quote verification fixes, the corpus rate is 64/5,233 =
> 1.22%. See `journal/experiments/verification_rate_correction_2026-09-07.md`.

Note `external_claim.industry_id` is populated on COMPANY claims too, so counting by that
column mixes object and company claims — filter by `request_id`.

## Prompt

`````
# COMPANY LAB — E54 PHASE A: FINANCIALS INDUSTRY OBJECTS

Phase A only. Build industry objects. NO company research, NO request file, NO roster.
This runs in parallel with E53 (Utilities) — do not touch
journal\flags\external_research_request.json, which belongs to that job.

Financials is the largest sector in the book: 257 companies, 87 already researched, 170
remaining. Three of its objects exist already (regional_banking, life_insurance,
pc_insurance) — READ those as templates and do not rebuild them.

  D:\company_lab_data\external\research\industries\regional_banking\industry_state.json
  D:\company_lab_data\external\research\sectors\financials\sector_state.json  (update, don't recreate)

## BUILD THESE FIFTEEN

  asset_management_custody_banks  17  AAMI AMG AMP APAM BEN BLK CNS CRBG FHI HLNE IVZ
                                      SEIC STEP TROW VCTR VRTS WT
  consumer_finance                14  ALLY AXP BFH COF DAVE ECPG ENVA EZPW FCFS NAVI
                                      PRG SLM SYF WRLD
  investment_banking_brokerage    14  BGC EVR GS HLI HOOD IBKR MC MS PIPR PJT RJF SCHW
                                      SF SNEX
  insurance_brokers                8  (the 8 in the book)
  multi_line_insurance             8
  diversified_banks                7  BAC C JPM PNC TFC USB WFC
  financial_exchanges              7  CBOE CME COIN ICE MKTX NDAQ VIRT
  financial_data_ratings           6  DFIN FDS MCO MORN MSCI SPGI
  alternative_asset_management     5  APO ARES BX CG KKR
  mortgage_reits                   5
  reinsurance                      5
  commercial_residential_mortgage_finance  4  ACT ESNT NMIH WD
  custody_banks                    3  BNY NTRS STT
  multi_sector_holdings            3  BRK-B JEF VOYA
  specialized_finance              3  CACC EFC HASI

Skip `application_software`, `diversified_capital_markets` and
`diversified_financial_services` — one company each, and the first is a data error on our
side (ALRM is Alarm.com, home security software, miscarried into Financials).

## THREE OF THESE ARE SPLITS WE MADE — HONOUR THEM

GICS combines each of the following. We separated them because the research questions do
not overlap:

  custody_banks vs asset_management_custody_banks
      BNY, NTRS and STT take deposits, run a securities portfolio, and answer to the Fed:
      net interest income, deposit betas, CET1, assets under custody, fee waivers.
      BlackRock and T. Rowe answer to the SEC: AUM, net flows, fee rate, passive share.

  alternative_asset_management vs asset_management_custody_banks
      Fee-related earnings, carried interest, permanent capital, dry powder, realisations,
      and increasingly an insurance balance sheet — APO and KKR are substantially
      insurers attached to an origination engine. A long-only manager lives or dies on
      net flows against passive.

  financial_exchanges vs financial_data_ratings
      Volumes, capture rate per contract, open interest, clearing, market-data fees on one
      side. Subscriptions, retention, price increases and debt-issuance volumes on the
      other. SPGI and MCO move with the credit cycle, not with trading volume.

## ONE BUCKET IS KNOWINGLY INCOHERENT — SAY SO

`multi_sector_holdings` is BRK-B, JEF and VOYA: a conglomerate, an investment bank and a
retirement insurer. We kept it as one object because splitting makes three singletons,
which is the worse trade. Its `market_structure` must state plainly that the bucket does
not describe one business, and its structural_growth / replication_difficulty /
substitution_risk should be UNKNOWN if a shared answer would be fiction. That refusal is
what produced the uranium/coal split in Energy and it was the right call.

`specialized_finance` (CACC subprime auto, HASI climate infrastructure, EFC mortgage
credit) may be the same case. Judge it and say which.

## VOCABULARIES, enforced by clab/external/schema.py

  structural_growth        DECLINING | FLAT | MODERATE | HIGH | EXCEPTIONAL | UNKNOWN
  replication_difficulty   LOW | MODERATE | HIGH | EXTREME | UNKNOWN
  substitution_risk        SEVERE | ELEVATED | MODERATE | LOW | UNKNOWN
  refresh_class            STRUCTURAL | QUARTERLY | EVENT_DRIVEN

## METRICS THAT MATTER, to seed key_metrics

  diversified_banks            NIM, deposit beta and mix, CET1 and the stress-capital
                               buffer, loan growth by book, charge-offs and reserve
                               build, fee income mix, efficiency ratio
  custody_banks                assets under custody and administration, net interest
                               income, deposit betas, fee waivers, securities-lending
                               revenue, CET1
  asset_management_custody_banks  AUM, NET FLOWS (not AUM growth — markets do that), fee
                               rate compression, passive share, product mix, seed capital
  alternative_asset_management fee-related earnings, FRE margin, carried interest and
                               accrued carry, permanent capital share, dry powder,
                               realisations, insurance float where present
  investment_banking_brokerage advisory and underwriting backlog, trading VaR and
                               revenue, client cash sweep rates, DARTs and payment for
                               order flow, compensation ratio
  consumer_finance             receivables growth, net charge-offs, reserve rate, funding
                               mix and cost, late-fee and CFPB rule exposure, prime vs
                               subprime mix
  financial_exchanges          volumes by asset class, revenue capture per contract, open
                               interest, clearing and collateral income, market-data fees
  financial_data_ratings       subscription retention and net revenue retention, price
                               increases, debt-issuance volumes for the ratings half,
                               index AUM-linked fees, AI substitution of research
  insurance_brokers            organic growth, retention, fiduciary investment income,
                               contingent commissions, M&A roll-up economics
  multi_line_insurance         combined ratio by segment, reserve development, statutory
                               capital, catastrophe exposure
  reinsurance                  renewal pricing and the cycle, retrocession cost, cat load,
                               reserve development, alternative capital / ILS competition
  mortgage_reits               book value per share, net interest spread, leverage,
                               hedging, prepayment speeds, agency vs credit mix
  commercial_residential_mortgage_finance  insurance-in-force, persistency, PMIERs
                               capital, cure rates, GSE pricing changes
  specialized_finance          judge per company; say if the bucket is incoherent

`key_participants` matters — it is the comparison set the company phase uses for
`competitive_position_trend`. Name real competitors including private and foreign ones the
book does not hold: Vanguard, Fidelity, Capital Group, Nomura, Barclays, Swiss Re, the
mutual insurers, and the private-credit shops.

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
   you actually read. The quote must appear in the excerpt. Corpus unverifiable rate is
   0.09% and should stay there.
3. UNKNOWN scores as NO_DATA, never zero.
4. Never invent a number.
5. One organisation gets ONE independence_domain. A regulator and the firm it regulates
   are different domains; a firm and its own IR page are not.
6. A company's own IR is the weakest source available.
7. Advisory only. "status": "SHADOW". Nothing is promoted.

## BUDGET

15 objects. Utilities' 7 were budgeted at 80-120 searches. Budget 200-280 for these 15 —
they share a regulatory and macro literature (rates, credit cycle, Basel endgame, CFPB)
heavily. Stop and report if you go materially over.

## REPORT

1. The 15 objects: claims and independence domains each.
2. Every UNKNOWN, with what blocked it and whether evidence was absent or you stopped
   short.
3. Explicitly: did `multi_sector_holdings` and `specialized_finance` hold together as one
   thing? If not, say what the right units would be.
4. Whether the three splits we made (custody, alts, exchanges vs data) look right from
   the research side — if any of them is wrong, we want to know before 170 companies are
   researched against them.
5. Searches, cache hits, sources.

## WHAT YOU MUST NOT CLAIM

This ranking is NOT validated: top decile ran a -7.6% median 3-year excess return against
SPY on a survivorship-free holdout, only 45.3% beat SPY, and 95.6% of its ranking power is
sector selection. `promoted` is false and stays false.
`````
