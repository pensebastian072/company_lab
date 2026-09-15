# Codex E57 — Health Care Phase A

Phase A only: 11 industry objects. No company research, no request file, no roster.

**Parallelisable.** Nothing here touches `journal/flags/external_research_request.json`,
and nothing runs `clab.external.request` or `clab.external.finalize`. Phase A writes
industry objects, keyed by `industry_id` and ingested by `clab.external.research_ingest`.

Health Care: 163 companies, **none researched**, 11 objects — the best
objects-per-company ratio on the board at 14.8.

## The taxonomy was fixed before staging, for the third sector running

`health_care_services` held 22 companies and was incoherent: CVS and Cigna beside
dialysis clinics, an imaging chain, a staffing agency, and a company that owns both
hospice care and Roto-Rooter. Three splits, committed in `65daa50`:

- **CVS, CI, ALHC → `managed_health_care`.** They are insurers. Cigna and Alignment
  underwrite medical risk; CVS owns Aetna. MLR, membership mix, Medicare Advantage star
  ratings, risk adjustment and PBM rebate economics are questions a care-delivery object
  cannot ask.
- **LH, DGX, NEO, VCYT → `clinical_laboratories`.** Test volume, reimbursement per test,
  payer mix, PAMA rate cuts.
- **SDGR → `health_care_technology`.** Drug-discovery software, not services.

The 14 left in `health_care_services` are a genuine diversified care-delivery bucket.
Deliberately not split further — E56 measured that trade rather than assuming it, and
Codex is asked to judge it rather than told the answer.

## Afterwards

```powershell
.venv\Scripts\python.exe -m clab.external.research_ingest --apply
.venv\Scripts\python.exe -m clab.external.verify --apply
```

Then verify against the store, not the report: 11 objects present, claim counts and
domains each, corpus unverifiable rate still 0.08%. Note `external_claim.industry_id` is
populated on COMPANY claims too, so counting by that column mixes object and company
claims — filter by `request_id`.

> **Dated correction (2026-09-07):** 0.08% is the historical prompt input. After PDF
> extraction-state and numeric-quote verification fixes, the corpus rate is 64/5,233 =
> 1.22%. Two Health Care sector claims are `UNVERIFIABLE` because their FDA PDF did not
> extract. See `journal/experiments/verification_rate_correction_2026-09-07.md`.

## Prompt

`````
# COMPANY LAB — E57 PHASE A: HEALTH CARE INDUSTRY OBJECTS

Phase A only. Build industry objects. NO company research, NO request file, NO roster.
Do not touch journal\flags\external_research_request.json.

Health Care: 163 companies, none researched, 11 industry objects to build. Read an
existing object as the template and the sector brief first, updating rather than
recreating it:

  D:\company_lab_data\external\research\industries\regional_banking\industry_state.json
  D:\company_lab_data\external\research\sectors\health_care\sector_state.json

## BUILD THESE ELEVEN

  health_care_equipment          34  ABT AHCO AORT BAX BDX BRKR BSX CNMD DXCM ENOV EW
                                     GEHC GKOS GMED IART IDXX INSP ISRG ITGR LIVN LMAT
                                     MDT PEN PODD RMD RVTY STAA STE SYK TFX TMDX TNDM
                                     UFPT ZBH
  biotechnology                  29  ABBV ADMA AMGN ARWR BIIB BMRN CYTK EXEL FTRE GILD
                                     HALO HRMY INCY KRYS LGND MRNA NBIX PTGX RCUS REGN
                                     RGEN ROIV SRPT TGTX UTHR VCEL VIR VRTX XNCR
  pharmaceuticals                26  ACAD ALKS AMPH AMRX ANIP BMY COLL CORT ELAN INDV
                                     INVA JAZZ JNJ LLY LQDA MRK OGN PAHC PBH PCRX PFE
                                     PRGO PTCT SUPN VTRS ZTS
  health_care_services           14  ADUS AMN BTSG CHE CON CRVL DVA HIMS LFST MD PGNY
                                     PRVA RDNT SHC
  life_sciences_tools_services   13  A AVTR AZTA BIO CRL DHR ILMN IQV MEDP MTD TECH TMO
                                     WAT
  health_care_supplies           12  ALGN BLFS COO HAE ICUI LNTH MMSI NEOG NVST QDEL WST
                                     XRAY
  health_care_facilities         10  ACHC ASTH EHC ENSG HCA NHC OPCH THC UHS USPH
  managed_health_care             9  ALHC CI CNC CVS ELV HQY HUM MOH UNH
  health_care_technology          8  CERT DOCS HSTM OMCL SDGR SOLV VEEV WAY
  clinical_laboratories           4  DGX LH NEO VCYT
  health_care_distributors        4  CAH COR HSIC MCK

## THREE OF THESE ARE SPLITS WE MADE — HONOUR THEM

GICS filed all three inside "Health Care Services". We separated them because the
research questions do not overlap:

  managed_health_care gains CVS, CI and ALHC
      They underwrite medical risk - Cigna and Alignment directly, CVS through Aetna.
      Medical loss ratio, membership and mix, Medicare Advantage star ratings and rate
      notices, risk adjustment, PBM rebate economics and pharmacy reform. HQY is the odd
      member: a health-savings-account custodian, closer to a specialty financial than an
      insurer. Say so if the object cannot describe it.

  clinical_laboratories - LH, DGX, NEO, VCYT
      Test volume, reimbursement per test, payer and self-pay mix, PAMA rate cuts, lab
      consolidation, esoteric versus routine testing.

  health_care_technology gains SDGR
      Schrodinger sells computational drug-discovery software plus a co-development
      pipeline. Subscriptions, compute and pipeline economics, not care delivery.

## ONE BUCKET IS DELIBERATELY MIXED — JUDGE IT, DO NOT ASSUME

`health_care_services` is what remains: dialysis (DVA), imaging (RDNT), home health
(ADUS), behavioural (LFST), staffing (AMN), sterilisation (SHC), fertility benefits
(PGNY), physician enablement (PRVA), telehealth (HIMS), and CHE, which owns hospice care
and a plumbing business.

We did NOT split it further, and the reason is measured rather than assumed. E56 re-cut
three Financials buckets that had each returned UNKNOWN on all three industry fields; the
rule that came out is that a one-company object which can be answered beats a bucket that
cannot - but only when the bucket genuinely cannot.

So judge it. If a shared `structural_growth`, `replication_difficulty` and
`substitution_risk` would be fiction, return UNKNOWN on them, say so plainly in
`market_structure`, and name the units you would use instead. That refusal produced the
uranium/coal split in Energy and the Financials re-cut, and both were right.

## VOCABULARIES, enforced by clab/external/schema.py

  structural_growth        DECLINING | FLAT | MODERATE | HIGH | EXCEPTIONAL | UNKNOWN
  replication_difficulty   LOW | MODERATE | HIGH | EXTREME | UNKNOWN
  substitution_risk        SEVERE | ELEVATED | MODERATE | LOW | UNKNOWN
  refresh_class            STRUCTURAL | QUARTERLY | EVENT_DRIVEN

## METRICS THAT MATTER, to seed key_metrics

  health_care_equipment        procedure volumes, installed base and consumables pull-
                               through, hospital capex cycles, FDA clearance pathway,
                               reimbursement codes, GPO contracting, recalls
  biotechnology                pipeline phase and readout calendar, patent cliff and LOE
                               dates, orphan and exclusivity status, payer coverage,
                               IRA Medicare price negotiation exposure, cash runway
  pharmaceuticals              LOE exposure, generic and biosimilar entry, gross-to-net
                               erosion, IRA negotiation lists, DTC and formulary access,
                               emerging-market mix
  health_care_services         judge per company; this bucket may not be one thing
  life_sciences_tools_services pharma and biotech R&D budgets, academic and government
                               funding, China exposure, instrument versus consumables
                               mix, bioprocessing destocking, CRO backlog and
                               cancellations
  health_care_supplies         utilisation, raw-material and freight cost, GPO pricing,
                               private-label competition, dental and elective sensitivity
  health_care_facilities       admissions and acuity mix, payer mix, labour cost and
                               contract nursing, Medicaid supplemental payments and state
                               directed-payment programmes, bad debt
  managed_health_care          medical loss ratio, membership by line, MA star ratings
                               and rate notices, risk adjustment, PBM rebate economics,
                               Medicaid redeterminations
  health_care_technology       ARR and net revenue retention, EHR integration, provider
                               IT budgets, information-blocking and interoperability
                               rules
  clinical_laboratories        test volume, reimbursement per test, payer mix, PAMA,
                               esoteric mix, lab consolidation
  health_care_distributors     generic deflation, brand mix, opioid settlement payments,
                               fee-for-service contracts, specialty distribution growth

`key_participants` matters - it is the comparison set the company phase uses for
`competitive_position_trend`. Name real competitors including private and foreign ones the
book does not hold: Roche, Novartis, Novo Nordisk, Sanofi, AstraZeneca, Siemens
Healthineers, Philips, Kaiser, the Blues plans, Sonic Healthcare, and the private hospital
and dialysis operators.

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

## STANDING RULES

1. No score, rank, rating, price target or gate. We compute every number.
2. Every claim: source_url, source_date, VERBATIM quote <=300 chars, ~1500-char excerpt
   you actually read. The quote must appear in the excerpt. Corpus unverifiable rate is
   0.08% and should stay there.
3. UNKNOWN scores as NO_DATA, never zero.
4. Never invent a number.
5. One organisation gets ONE independence_domain. A regulator and the company it
   regulates are different domains; a company and its own IR page are not. CMS, the FDA
   and a payer are three separate domains.
6. A company's own IR is the weakest source available.
7. Advisory only. "status": "SHADOW". Nothing is promoted.

## BUDGET

11 objects. Utilities' 7 were budgeted at 80-120 searches and Financials' 15 at 200-280.
These share a regulatory literature heavily - CMS reimbursement, the IRA, FDA pathways -
so budget 150-220. Stop and report if you go materially over.

## REPORT

1. The 11 objects: claims and independence domains each.
2. Every UNKNOWN, with what blocked it and whether the evidence was absent or you
   stopped short.
3. Explicitly: did `health_care_services` hold together as one thing? If not, what units
   would you use, and which companies go where?
4. Whether the three splits we made - insurers, reference labs, SDGR - look right from
   the research side. If any is wrong we want to know before 163 companies are researched
   against them.
5. Whether `managed_health_care` can describe HQY, or whether an HSA custodian does not
   belong in an insurer object.
6. Searches, cache hits, sources.

## WHAT YOU MUST NOT CLAIM

This ranking is NOT validated: top decile ran a -7.6% median 3-year excess return against
SPY on a survivorship-free holdout, only 45.3% beat SPY, and 95.6% of its ranking power is
sector selection. `promoted` is false and stays false.
`````
