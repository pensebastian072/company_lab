# Codex E49 - Communication Services, complete

Third sector. 47 companies over 11 industry objects, none researched, no sector brief
gaps - the Phase 0 brief exists.

## What is different this time

**`market_share_direction` is now COMPUTED. Do not research it.**

It resolved for 4 of 183 companies across five batches of research and cost one blocking
claim per company to fail - 8.2% of E46's entire claim budget spent documenting a dead
end. `clab/external/revenue_share.py` now computes it from revenue share of the listed
peer set, and for this sector it resolves **23 of 47** (interactive media 9 of 11, movies
and entertainment 10 of 10, broadcasting 4 of 4).

Leave the field UNKNOWN and give the blocking reason as "computed from revenue share".
Spend the budget on the fields arithmetic cannot reach. If you find a document that
genuinely establishes direction, report it - our computed number never overwrites a
researched one and a disagreement is a contradiction we want to see.

**The taxonomy was fixed before staging, again.** Two moves:

- **PINS leaves the video-game bucket.** GICS files Pinterest under Interactive Home
  Entertainment beside Take-Two. It is an ad-supported social platform whose peers on
  DAU, ad load and ARPU are META and RDDT. It is now `interactive_media_services`.
  **TTWO is knowingly left alone** as a one-company object - it is a genuine games
  publisher and the book holds no other. Same decision as AES in Utilities.
- **`ad_tech` splits from `advertising`.** APP, TTD and DV sell software to advertisers
  and are researched on take rate, platform spend, supply-path economics and identity
  rules. OMC sells agency services. The 77.4%-versus-2.2% margin gap overstates it, since
  an agency books pass-through media spend as revenue, but they are not one unit. OMC and
  ZD stay in `advertising`.

## The roster

Request `d1233fa7352dca524421`, 47 companies, depth 3, `require_citation` on.
`journal/flags/external_research_request.json`.

The file is ALPHABETICAL - `request.py:147` sorts by ticker unconditionally. Every row
carries its own `industry_id`. Group by that and work the groups in this order, so a run
interrupted by this box crashing leaves whole industries finished:

```
interactive_media_services            11  CARG GOOGL GTM META MTCH PINS PPLI QNST RDDT TRIP YELP
movies_entertainment                  10  CNK DIS LYV MSGS NFLX PSKY ROKU SPHR TKO WMG
alternative_carriers                   4  CCOI IRDM LUMN UNIT
broadcasting                           4  FOXA NXST SIRI WBD
ad_tech                                3  APP DV TTD
cable_satellite                        3  CHTR CMCSA VSNT
integrated_telecommunication_services  3  T TDS VZ
publishing                             3  NWSA NYT WLY
wireless_telecommunication_services    3  ECHO SHEN TMUS
advertising                            2  OMC ZD
interactive_home_entertainment         1  TTWO
```

**One company carries no filing evidence: CHTR.** A gap in our half, not yours.

The id does not expire; the timestamp does. `generated_at` is not in the content hash, so
rebuilding this roster reproduces `d1233fa7352dca524421` exactly. Take as many days as the
work needs, echo that id whatever day you finish, and the same-day guard is satisfied
locally by restaging on the day the payload lands.

## What is deliberately NOT in this prompt

There is a pre-registered study attached to this sector -
`journal/experiments/E49_sector_heterogeneity_preregistration.md` - asking whether a
sector's heterogeneity can be screened before it is bought. **Its predictions are
deliberately withheld from you.** Telling a researcher what result is expected is how you
get that result. Answer each field on its evidence and let the study fall where it falls.

## Prompt

`````
# COMPANY LAB - E49: COMMUNICATION SERVICES, COMPLETE

Third sector at 100%. 47 companies over 11 industry objects, none researched.

Request: C:\Users\<your-user>\company_lab\journal\flags\external_research_request.json
request_id d1233fa7352dca524421. Echo it verbatim. The roster is frozen.

Two phases. PHASE A builds the 11 industry objects. STOP and report. PHASE B researches
the 47 companies against them.

Read the sector brief first and UPDATE it rather than recreating it:
  D:\company_lab_data\external\research\sectors\communication_services\sector_state.json
Template for an object:
  D:\company_lab_data\external\research\industries\upstream_oil_gas\industry_state.json

## PHASE A - ELEVEN OBJECTS

  interactive_media_services            11   CARG GOOGL GTM META MTCH PINS PPLI QNST
                                             RDDT TRIP YELP
  movies_entertainment                  10   CNK DIS LYV MSGS NFLX PSKY ROKU SPHR TKO WMG
  alternative_carriers                   4   CCOI IRDM LUMN UNIT
  broadcasting                           4   FOXA NXST SIRI WBD
  ad_tech                                3   APP DV TTD
  cable_satellite                        3   CHTR CMCSA VSNT
  integrated_telecommunication_services  3   T TDS VZ
  publishing                             3   NWSA NYT WLY
  wireless_telecommunication_services    3   ECHO SHEN TMUS
  advertising                            2   OMC ZD
  interactive_home_entertainment         1   TTWO - a knowing one-company object

Note that `interactive_media_services` and `movies_entertainment` are each large and each
holds companies of very different size. GOOGL and META beside CARG and YELP; NFLX and DIS
beside CNK and SPHR. If a bucket cannot be described as one thing, SAY SO in
market_structure rather than averaging it away - that refusal is what produced the
uranium/coal split in Energy and it was the right call.

Vocabularies, enforced by clab/external/schema.py:

  structural_growth        DECLINING | FLAT | MODERATE | HIGH | EXCEPTIONAL | UNKNOWN
  replication_difficulty   LOW | MODERATE | HIGH | EXTREME | UNKNOWN
  substitution_risk        SEVERE | ELEVATED | MODERATE | LOW | UNKNOWN
  refresh_class            STRUCTURAL | QUARTERLY | EVENT_DRIVEN

Metrics that matter, to seed key_metrics:

  interactive_media_services  DAU/MAU and the ratio, ARPU by geography, ad load, time
                              spent, take rate for marketplaces, AI-answer substitution
                              of search and referral traffic, app-store rules
  movies_entertainment        subscribers and churn, content spend and amortisation,
                              theatrical windows, licensing versus owned IP, live-event
                              attendance, sports rights cost and renewal dates
  ad_tech                     platform spend, take rate, supply-path economics, identity
                              and signal loss, measurement and verification rules,
                              retail-media competition
  broadcasting                retransmission fees, political advertising cyclicality,
                              affiliate agreements, cord-cutting rate, ATSC 3.0
  cable_satellite             broadband subscriber net adds, ARPU, fixed-wireless and
                              fibre overbuild, capex per home passed
  integrated / wireless telecom  postpaid phone net adds, churn, ARPU, spectrum
                              position and cost, fibre and FWA build economics, capex
                              intensity
  alternative_carriers        route and network assets, IRU and dark-fibre contracts,
                              datacenter interconnect demand, leverage and maturities
  publishing                  digital subscriber growth, ARPU, print decline rate,
                              AI licensing deals and litigation
  advertising                 organic revenue growth, client wins and losses, principal
                              versus agent media buying, headcount and utilisation

`key_participants` is the comparison set Phase B uses for competitive_position_trend.
Name real competitors including private and foreign ones the book does not hold - TikTok,
ByteDance, Amazon advertising, Apple, Comcast's Sky, private equity owners of local
broadcast.

STOP and report before Phase B.

## PHASE B - 47 COMPANIES

## DO NOT RESEARCH market_share_direction, OR COMPANY SIZE, OR GROWTH VERSUS PEERS

All three are COMPUTED here from revenue share of the listed peer set, for every industry:

  peer_revenue_share / peer_share_rank    who is the biggest player in this product
                                          market, and where each company ranks
  peer_growth_direction                   who is expanding and who is shrinking against
                                          the peer median
  market_share_direction                  whether CONTESTABLE share moved - filled only
                                          where share is contestable at all; it resolves
                                          for 23 of these 47

Leave `market_share_direction` UNKNOWN with the blocking reason "computed from revenue
share", and do not spend searches establishing how large a company is or how fast it grew
relative to its peers. We have both from filed revenue. Spend the budget on what
arithmetic cannot reach: WHY the position is what it is, whether it is defensible, and
what would change it.

If you nonetheless find a document that genuinely establishes contestable share
direction, report it - our number never overwrites a researched one and a disagreement is
a contradiction we want to see.

## THE QUESTION THIS SYSTEM EXISTS TO ANSWER

Three companies can look identical in the accounts:

  a moat that is STRONG
  a moat that is STRENGTHENING
  a moat that still reads strong in the financials but is DETERIORATING underneath

Only the third is dangerous, and the financial history cannot separate them because it is
a record of what already happened. Nineteen companies have shown that shape so far.

This sector's version: **an audience is not a moat, and the accounts cannot tell the
difference between a business that owns its distribution and one that rents it.** A
company whose traffic comes from search referral, an app store, or a platform's
recommendation algorithm reports the same revenue as one that owns the relationship,
right up until the referral stops. Ask where the audience actually comes from, who
controls that channel, and what it costs to keep.

## THE RULES, UNCHANGED

Every non-UNKNOWN categorical needs a claim whose `field` names it, or return UNKNOWN.
Five batches running with zero demotions - hold it.

When you research a field and CANNOT establish it, cite the claims that BLOCKED you. An
UNKNOWN with blocking claims is a RESULT; one with nothing behind it is a GAP. Zero gaps
across five batches - hold that too.

`competitive_position_trend` - rank-order against named peers on a shared metric over the
same two periods, not a share series. It resolved 27 of 45 in E45 on bank NIM and insurer
combined ratio, and 11 of 52 in Energy on services operating margin. It needs a metric
peers file on the same basis whose movement is attributable to the company. Candidates
here: ARPU, DAU growth, subscriber net adds, churn, retransmission revenue per subscriber,
organic revenue growth.

RISK FIELDS ARE PEER-RELATIVE. A company must be worse than its INDUSTRY PEERS for a risk
flag to fire. An industry-wide condition is not a finding about a company.

The twelve fields:

  current_moat_strength        NONE | WEAK | MODERATE | STRONG | EXCEPTIONAL | UNKNOWN
  moat_trajectory              DETERIORATING | WEAKENING | STABLE | STRENGTHENING | UNKNOWN
  competitive_position         LAGGARD | CHALLENGER | STRONG_NUMBER_TWO | LEADER | DOMINANT | UNKNOWN
  competitive_position_trend   DETERIORATING | STABLE | IMPROVING | UNKNOWN
  industry_structural_growth   DECLINING | FLAT | MODERATE | HIGH | EXCEPTIONAL | UNKNOWN
  company_specific_capture     NONE | LOW | MODERATE | HIGH | UNKNOWN
  demand_visibility            NONE | LOW | MODERATE | HIGH | UNKNOWN
  market_share_direction       COMPUTED - do not research
  pricing_power                NONE | LOW | MODERATE | HIGH | UNKNOWN
  technology_risk              SEVERE | ELEVATED | MODERATE | LOW | UNKNOWN
  disruption_risk              SEVERE | ELEVATED | MODERATE | LOW | UNKNOWN
  regulatory_risk              SEVERE | ELEVATED | MODERATE | LOW | UNKNOWN

`cheapness_quality` is RETIRED. Do not answer it, do not search for it.

## TWO PASSES

PASS A - BLIND. Identity, measured metrics, verbatim 10-K evidence. CHTR carries no
filing evidence - a gap in our half.

PASS B - then ask for journal\flags\external_research_conclusions.json and add
`pass_b.reconciliation` per disagreement, citing claim_ids. Do not rewrite pass A.

## SELF-CHECK

  cd C:\Users\<your-user>\company_lab
  $env:PYTHONPATH="C:\Users\<your-user>\company_lab"
  .venv\Scripts\python.exe -m clab.external.finalize D:\company_lab_data\external\payloads\d1233fa7352dca524421.json

Read-only without --apply. Fix what it flags before reporting.

## STANDING RULES

1. No score, rank, rating, price target or gate. We compute every number.
2. Every claim: source_url, source_date, VERBATIM quote <=300 chars, ~1500-char excerpt
   you actually read. The quote must appear in the excerpt. We fetch your URLs ourselves;
   the corpus unverifiable rate is 0.13% and should stay there.
3. UNKNOWN is NOT the bottom of any scale. It scores as NO_DATA, never zero.
4. Never invent a number.
5. One organisation gets ONE independence_domain for the whole record.
6. A company's own IR is the weakest source available.
7. Advisory only. "status": "SHADOW". Nothing is promoted.

## BUDGET

E47 cost 266 searches for 59 companies plus 7 objects. This is 47 plus 11 objects, with
market share removed from the research list. Budget 250-350. Stop and report if you go
materially over.

## REPORT

Phase A: the 11 objects, claims and domains each, every UNKNOWN with what blocked it, and
explicitly whether `interactive_media_services`, `movies_entertainment` and the TTWO
object held together as one thing.

Phase B:
1. Per company: fields backed, fields UNKNOWN, each marked R or G.
2. `competitive_position_trend`: which companies resolved and on what metric.
3. Every company where moat_trajectory disagrees with the financial history - and for
   this sector, say explicitly whether the audience is OWNED or RENTED.
4. Claims, sources, independence domains, searches, cache hits.
5. Every conclusion you believe but could not evidence.

## WHAT YOU MUST NOT CLAIM

This ranking is NOT validated: top decile ran a -7.6% median 3-year excess return against
SPY on a survivorship-free holdout, only 45.3% beat SPY, and 95.6% of its ranking power is
sector selection. `promoted` is false and stays false.
`````

## Afterwards

```powershell
.venv\Scripts\python.exe -m clab.external.research_ingest --apply
.venv\Scripts\python.exe -m clab.external.finalize D:\company_lab_data\external\payloads\d1233fa7352dca524421.json --apply
.venv\Scripts\python.exe -m clab.external.verify --apply
.venv\Scripts\python.exe -m clab.external.revenue_share --sector communication_services --apply-to "<version>"
.venv\Scripts\python.exe -m clab.external.score --version "<version>" --apply
.venv\Scripts\python.exe -m clab.export.xlsx_external --version "<version>"
```

Then evaluate E49's five registered predictions against the finished sector.
