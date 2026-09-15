# Codex E76 - Health Care Phase A re-research

Phase A only. All eleven Health Care objects are retired after B4's field-specific
semantic audit. This prompt rebuilds the layer needed before any Health Care Phase B
request can exist.

The counts below were reproduced from the configured DuckDB store and live
`scores.parquet` on 2026-09-10 at store SHA-256
`c6322b46bc6feef6f47c204b3210c818899162c5af9260538cd6c087205a3bc6`.
The fenced prompt is self-contained and is intended for a fresh research session.

## Prompt

`````
# COMPANY LAB - E76 PHASE A: HEALTH CARE RE-RESEARCH

Work in:

  repository: C:\Users\<your-user>\company_lab
  research tree: D:\company_lab_data\external

Phase A only. Re-research the retired Health Care industry objects. Do not research
companies, create a company roster, run `clab.external.request`, run
`clab.external.finalize`, touch
`journal\flags\external_research_request.json`, score anything, or export a workbook.

Everything remains advisory / SHADOW. `promoted` is false everywhere and no code path
may set it true.

## WHY ALL ELEVEN OBJECTS WERE RETIRED

E57 created eleven objects and 66 claims. All 66 quotes were found literally in their
sources, across 31 URLs and five independence domains. A later B4 audit read every passage
against its assigned field and found:

  direct support for the complete field claim      11 / 66
  relevant context only                            30 / 66
  materially different field or economic unit      25 / 66

The builder had mechanically assigned each of 33 evidence windows to two fixed fields.
Fifty-five of 66 claims therefore failed direct field support even though all 66 were
`VERIFIED_LOCAL`. The entire version was retired because no defensible corrected object
set could be assembled by deleting a few isolated claims.

At the 2026-09-10 starting snapshot:

  live Health Care book                  163 companies / 11 research units
  active Health Care units                 0
  retired E57 units                       11, all version 2026-09-07
  retained E57 claims                     66, all VERIFIED_LOCAL
  retained E57 source URLs                31
  retained E57 independence domains        5
  corpus claims                         7,223 total
                                         7,099 VERIFIED_LOCAL
                                            65 UNVERIFIABLE
                                            59 SELF_ATTESTED
  industry rows ever stored              109 total / 74 active / 35 SUPERSEDED

Do not run the historical E57 builder or recreate any fixed field-to-source index. The old
payloads and claims are audit evidence and search leads only. Do not copy their conclusions
or inherit a categorical because its quote verified literally.

## THE ELEVEN STARTING UNITS

Eleven is a starting taxonomy count, not a quota. Recompute membership from the live book
before research. These lists contain all 163 Health Care companies exactly once.

  biotechnology                                      29
    ABBV ADMA AMGN ARWR BIIB BMRN CYTK EXEL FTRE GILD HALO HRMY INCY KRYS LGND
    MRNA NBIX PTGX RCUS REGN RGEN ROIV SRPT TGTX UTHR VCEL VIR VRTX XNCR

  clinical_laboratories                               4
    DGX LH NEO VCYT

  health_care_distributors                            4
    CAH COR HSIC MCK

  health_care_equipment                              34
    ABT AHCO AORT BAX BDX BRKR BSX CNMD DXCM ENOV EW GEHC GKOS GMED IART IDXX
    INSP ISRG ITGR LIVN LMAT MDT PEN PODD RMD RVTY STAA STE SYK TFX TMDX TNDM
    UFPT ZBH

  health_care_facilities                             10
    ACHC ASTH EHC ENSG HCA NHC OPCH THC UHS USPH

  health_care_services                               14
    ADUS AMN BTSG CHE CON CRVL DVA HIMS LFST MD PGNY PRVA RDNT SHC

  health_care_supplies                               12
    ALGN BLFS COO HAE ICUI LNTH MMSI NEOG NVST QDEL WST XRAY

  health_care_technology                              8
    CERT DOCS HSTM OMCL SDGR SOLV VEEV WAY

  life_sciences_tools_services                       13
    A AVTR AZTA BIO CRL DHR ILMN IQV MEDP MTD TECH TMO WAT

  managed_health_care                                 9
    ALHC CI CNC CVS ELV HQY HUM MOH UNH

  pharmaceuticals                                    26
    ACAD ALKS AMPH AMRX ANIP BMY COLL CORT ELAN INDV INVA JAZZ JNJ LLY LQDA MRK
    OGN PAHC PBH PCRX PFE PRGO PTCT SUPN VTRS ZTS

## THE 11 DIRECT-SUPPORT PASSAGES ARE SEEDS, NOT ANSWERS

B4 found direct support only for these field-object pairs:

  structural_growth
    clinical_laboratories
    health_care_equipment
    health_care_facilities
    health_care_supplies

  substitution_risk
    biotechnology

  regulatory_trajectory
    health_care_equipment
    health_care_facilities
    health_care_supplies
    managed_health_care

  market_structure
    health_care_services
    managed_health_care

No E57 passage directly supported `replication_difficulty` or `key_metrics`. Start those
two fields clean for every object. For the eleven seed pairs, read the original passage
again and decide whether it supports the new claim's field, industry scope, direction,
period and magnitude. "Direct" in B4 meant direct support for the stored claim, not proof
that the categorical generalized to the whole industry.

The exact negative baseline is also binding:

- structural_growth: 4 direct, 5 context, 2 unsupported;
- replication_difficulty: 0 direct, 2 context, 9 unsupported;
- substitution_risk: 1 direct, 4 context, 6 unsupported;
- regulatory_trajectory: 4 direct, 5 context, 2 unsupported;
- market_structure: 2 direct, 6 context, 3 unsupported;
- key_metrics: 0 direct, 8 context, 3 unsupported.

Do not preserve a value merely because it existed in E57.

## TAXONOMY CHECKPOINT FIRST

The old `health_care_services` unit mixes renal care, imaging, home and hospice care,
staffing, behavioral health, physician enablement, digital consumer care, fertility
benefits, occupational health, workers-compensation cost management and sterilization.
A single growth, replication or substitution mechanism may not exist.

Before writing any new object:

1. Recompute all 163 memberships through `clab.external.taxonomy.industry_id`.
2. Read all eleven retired rows through the explicit audit path and inspect the frozen
   payloads without treating them as current.
3. Test each starting unit for shared customers, economics, cycle, regulatory regime and
   comparable operating metrics.
4. Test these known boundary problems explicitly:
   - CHE must be evaluated at the VITAS segment if it remains in Health Care; Roto-Rooter
     cannot define the object.
   - HQY is an HSA custodian and must not inherit managed-care underwriting economics.
   - SDGR's customer-facing software activity belongs with Health Care technology only if
     that scope is supported.
   - `health_care_services` requires a defensible split or a documented reason for
     keeping the inherited bucket.
5. Write
   `D:\company_lab_data\external\reports\E76_health_care_taxonomy_checkpoint.md`
   with every keep/split decision, economic reason and exact ticker map.
6. If evidence justifies a split, edit only Health Care overrides in
   `clab/external/taxonomy.py`, add focused tests, and recompute the roster. Preserve
   concurrent sector overrides. A singleton is allowed only for a real industry with
   private or foreign peers.

If a split cannot be defended, keep the unit and flag it. Do not invent a partition to
improve answer rate.

## OBJECT AND LIFECYCLE CONTRACT

Every rebuilt object is a new version:

  industry_id, sector_id="health_care", version="2026-09-10", status="SHADOW"
  structural_growth
  market_structure
  key_participants
  moat_mechanism
  replication_difficulty
  technology_trajectory
  regulatory_trajectory
  substitution_risk
  key_metrics
  refresh_class
  next_refresh_due
  claims
  last_updated

Do not alter or delete the stored `2026-09-07` rows. They must remain `SUPERSEDED` with
their B4 reason and original timestamp. New versioned rows are the only valid replacements.

Enforced vocabularies:

  structural_growth        DECLINING | FLAT | MODERATE | HIGH | EXCEPTIONAL | UNKNOWN
  replication_difficulty   LOW | MODERATE | HIGH | EXTREME | UNKNOWN
  substitution_risk        SEVERE | ELEVATED | MODERATE | LOW | UNKNOWN
  refresh_class            STRUCTURAL | QUARTERLY | EVENT_DRIVEN

Free-text caps:

  market_structure 1500 chars   moat_mechanism 1000
  technology_trajectory 1000    regulatory_trajectory 1000

Each claim must provide:

  claim_id            unique and matching ^c_[0-9a-f]{12}$
  field               the one field this claim supports
  text                required
  quote               verbatim, <= 300 characters, literally present in excerpt
  excerpt             the passage actually read
  source_url          exact source
  source_date         exact date
  source_type         SEC_FILING | EARNINGS_CALL | INVESTOR_PRESENTATION | REGULATOR |
                      TRADE_PUBLICATION | PRIMARY_DATA | COMPANY_IR | NEWS | OTHER
  independence_domain COMPANY_IR | COMPETITOR_FILING | CUSTOMER | SUPPLIER | REGULATOR |
                      TRADE_PRESS | PRIMARY_DATA | ACADEMIC
  stance              SUPPORTS | CONTRADICTS | CONTEXT
  fact_or_inference   FACT | INFERENCE

Set `stance` and `fact_or_inference` explicitly. Never send `verify_status`; the local
verifier owns it.

## COMPLETENESS GATE AND UNKNOWN LEDGER

A future `batch_health.enforce()` call retires an object answering zero of the three
structural fields. One- or two-field objects remain active but below the 3-of-3 ship bar.

The gate does not make assertion safer. Every non-UNKNOWN categorical needs a passage that
directly supports its field, scope and direction with `stance: SUPPORTS`. Every UNKNOWN
needs a report entry naming:

- the exact document, filing item, statistic, regulator or body searched;
- where it was searched and what came back;
- whether evidence was genuinely absent or work stopped short;
- why the passages did not establish the field for the object.

A unit not researched is better left unbuilt than shipped empty. Do not force a
categorical to avoid retirement.

## ONE FIELD, ONE SEMANTIC RECEIPT

- One claim backs one field.
- Never reuse an identical quote/excerpt window across fields.
- The same URL may back multiple fields only through different passages establishing
  different facts.
- A company description is not a replication-difficulty receipt.
- A proposed rule, trial endpoint or reimbursement model is not an implemented or realized
  industry outcome.
- A product, parent or segment fact cannot support another economic unit without an
  explicit scope argument.
- Compare metrics only for the same period, definition and basis.
- Record proposed, approved, implemented and realized events separately.

Audit all retained claims twice and report separate denominators:

1. literal quote containment;
2. semantic field support, including unit, scope, period, outcome status and comparability.

The second audit must read every passage. Keyword overlap is not semantic review.

## DEPTH AND SOURCE DIVERSITY

Depth follows evidence, not a quota. Aim for at least eight field-specific claims and three
genuinely independent organizations per object, but never pad.

The E57 lesson is that diversity is necessary and not sufficient: five domains and 31 URLs
did not prevent an 83.3% semantic-assignment failure. Do not optimize domain counts. Use
different evidence types only when they genuinely support the field, and report
concentration when they do not.

Paste `research_ingest.evidence_profile()` per object: claim count, distinct URLs, hosts
and domains; domains resting on one claim; host/domain conflicts; and stance distribution.
Also report FACT / INFERENCE counts.

One organization has one independence domain. A company, its IR site and its filing are
not independent organizations.

## METRICS TO START WITH, NOT ANSWERS TO COPY

  biotechnology
    pipeline stage, probability-adjusted assets, trial catalysts, cash runway, platform
    reuse, patent/exclusivity, licensing economics and modality/manufacturing constraints

  clinical_laboratories
    test volume, revenue per requisition, payer mix, reimbursement, esoteric-test mix,
    patient service centers, lab utilization and turnaround time

  health_care_distributors
    pharmaceutical or supply volume, gross profit rather than gross revenue, working
    capital, inventory turns, customer concentration, generic inflation and service mix

  health_care_equipment
    procedure volumes, installed base, consumables and service attach, utilization,
    replacement cycle, approvals, clinical evidence and surgeon training

  health_care_facilities
    admissions, occupancy, acuity, revenue per admission, labor cost, payer mix, same-store
    volume, bed capacity and reimbursement

  health_care_services
    define the operating unit before choosing metrics; dialysis treatments, imaging scans,
    home-health census, staffing hours, fertility cycles and physician lives are not
    comparable

  health_care_supplies
    procedure volume, recurring consumables, channel inventory, utilization, price-cost,
    manufacturing yields, approvals and product concentration

  health_care_technology
    recurring revenue, retention, bookings, lives or providers served, implementation
    backlog, take rate, interoperability and regulated-software exposure

  life_sciences_tools_services
    instrument placements, consumables pull-through, biopharma funding, order growth,
    book-to-bill, backlog, utilization and China exposure

  managed_health_care
    membership by product, premium yield, medical cost ratio, risk adjustment, Stars,
    utilization, reimbursement rates and capital requirements

  pharmaceuticals
    prescription volume, net price, patent/exclusivity, pipeline stage, indication mix,
    payer access, manufacturing capacity and loss-of-exclusivity exposure

Name real private and foreign peers. Do not infer market leadership from parent-company
revenue size.

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

For this Phase A run there is no company request and no pass A/B reconciliation. Do not
open or use a conclusions file. The canonical `competitive_position_trend` section is a
company-field carve-out and not a field on these objects.

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

## BUILD, DRY-RUN, AND STOP

Write current artifacts under:

  D:\company_lab_data\external\research\industries\<industry_id>\industry_state.json
  D:\company_lab_data\external\research\industries\<industry_id>\industry_brief.md

Update to a new version:

  D:\company_lab_data\external\research\sectors\health_care\sector_state.json
  D:\company_lab_data\external\research\sectors\health_care\sector_brief.md

Write:

  D:\company_lab_data\external\reports\E76_health_care_taxonomy_checkpoint.md
  D:\company_lab_data\external\reports\E76_health_care_phase_a.md

Before replacing each on-disk E57 artifact, record its prior version and SHA-256 in the
report. The immutable historical rows remain in DuckDB; do not mutate them.

Run only:

  cd C:\Users\<your-user>\company_lab
  $env:PYTHONPATH="C:\Users\<your-user>\company_lab"
  .venv\Scripts\python.exe -m clab.external.research_ingest

Do not pass `--apply`. Do not run `verify --apply`. Do not run
`batch_health.enforce()`. Stop after the dry run and return the artifacts for independent
Chat A review.

Record the store SHA-256 before and after dry run. It must remain unchanged.

The report must include:

1. Starting and final ticker maps, conserving all 163 names exactly once.
2. Every keep/split decision and its economic reason.
3. Prior E57 artifact hashes and every new version.
4. Per-object evidence profiles, stance distributions and fact/inference distributions.
5. Answered structural fields and the complete UNKNOWN ledger.
6. Exact disposition of all eleven B4 direct-support seed pairs.
7. Literal-containment and semantic-support audits as separate tables.
8. Duplicate quote/excerpt windows across fields; expected zero.
9. Search, network fetch and cache-hit counts separately.
10. Claim-depth distribution and whether it clusters around a quota.
11. Dry-run output and before/after store hashes.
12. A replacement-readiness map from every retired ID to its replacement ID or split IDs.
13. An explicit statement that no apply, verification apply, company research, request,
    score, rank or promotion occurred.

Budget 350-550 searches for the taxonomy checkpoint plus eleven starting units. Stop and
report before materially exceeding 650. Partial, receipted work is preferable to guessed
completion.

## WHAT YOU MUST NOT CLAIM

This ranking is not validated. Its top decile ran a -7.6% median three-year excess return
against SPY on a survivorship-free holdout, only 45.3% beat SPY, and 95.6% of ranking power
came from sector selection. Rebuilding Health Care restores a blocked research layer. It
does not establish predictive power. `promoted` remains false.
`````

## Return procedure for Chat A

The researcher returns dry-run artifacts only. Before any apply, Chat A must independently
review every taxonomy decision, every non-UNKNOWN categorical receipt, every UNKNOWN reason,
all eleven B4 seed dispositions, the semantic audit, source-domain labels, prior-artifact
hashes, and the unchanged store hash.

If accepted, Chat A performs ingest, local verification, exact store readback and the
completeness gate separately. The eleven `2026-09-07` rows remain `SUPERSEDED`; accepted
replacements arrive as version `2026-09-10`.
