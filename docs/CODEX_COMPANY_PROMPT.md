# Codex company lane — the pilot

Held back until `clab/external/request.py` existed, so the JSON below is dumped from the
real builder rather than hand-authored. A prose contract that the code then has to match
is how this repo has drifted before.

## Build the request first

```powershell
cd C:\Users\<your-user>\company_lab
$env:PYTHONPATH="C:\Users\<your-user>\company_lab"
.venv\Scripts\python.exe -m clab.external.request --symbols FICO,VRT,NVDA --sample E42-pilot
```

Writes two files:

| file | when |
|---|---|
| `journal\flags\external_research_request.json` | hand over **now** |
| `journal\flags\external_research_conclusions.json` | hand over **only after pass A is written** |

**The request expires the same NY day it was built.** `finalize.py` refuses a payload
whose frozen request is not from today — an age window said yes to a 21.6-hour-old
signal on the options desk and it published against the previous session. Rebuild before
finalizing if the day has turned.

## Why two files

Telling a researcher "this field is in the payload, don't read it until pass B" is an
honour system, and anchoring on the incumbent's answer is exactly what the blind pass
exists to measure. So the local model's SG/BQ scores, its per-sub-test rationales and its
BQ killer answer live in a separate file. The blind request carries only identity, the
measured metrics, and **verbatim 10-K evidence** — what the company said, not what the
model concluded about it. Evidence flagged `evidence_unverified` is stripped, so E40's
9.7% hallucinated-citation rate cannot launder into the external layer.

## Finalize afterwards

```powershell
.venv\Scripts\python.exe -m clab.external.finalize D:\company_lab_data\external\payloads\<request_id>.json
.venv\Scripts\python.exe -m clab.external.finalize D:\company_lab_data\external\payloads\<request_id>.json --apply
.venv\Scripts\python.exe -m clab.external.verify --apply
```

## Prompt

````
# COMPANY LAB — CODEX COMPANY LANE (PILOT: 3 COMPANIES)

Phase 0 is done and in the catalog: 15 industry objects, 11 sector briefs, 109 claims,
90 of them verified by local re-fetch. Read from it. Do not rebuild it.

This is the company lane, run on three companies before forty. Every gap found here is
found cheaply.

## WHAT YOU RECEIVE

C:\Users\<your-user>\company_lab\journal\flags\external_research_request.json

{
  "request_id": "812721fe9a0d87fd6b72",
  "spec_fingerprint": "a770ff332c2a037f",
  "roster_sha1": "e5305a3b419c16398a612d50b51540aedf10d37e",
  "generated_at": "2026-09-02T13:37:54+00:00",
  "status": "READY",
  "read_only": true,
  "depth": 3,
  "external_schema_version": "1.0.0",
  "pass": "A",
  "steps": [ ... the only work this request authorises ... ],
  "roster": [
    {
      "ticker": "VRT", "cik": "0001674101", "name": "Vertiv",
      "sector": "Industrials", "sub_industry": "Electrical Components & Equipment",
      "sector_id": "industrials", "industry_id": "datacenter_power_cooling",
      "subindustry_id": "electrical_components_equipment",
      "data_through": "2026-06-30",
      "measured": { "revenue_ttm": 11479600000.0, "revenue_cagr_3y": 0.2156,
                    "gross_margin": 0.3804, "operating_margin": 0.1894,
                    "fcf_margin": 0.2552, "roic": 0.4359, ... },
      "filing_evidence": {
        "SG": ["[sg_tam_expanding] particularly driven by AI and high-performance
                computing workloads."]
      }
    }
  ]
}

THE ROSTER IS FROZEN. Research only these tickers. A ticker you add is rejected by
name. `request_id` must be echoed back verbatim.

`filing_evidence` is VERBATIM 10-K text. It is what the company said about itself, and
the 10-K has already been read - do not read it again.

## THE TWO-PASS RULE

PASS A — BLIND. Using only the roster, the sector brief, the industry object and your
own research, write the competitive picture. You have NOT been told what the local
model concluded, and that file will not be given to you until pass A is written. This
is what makes anchoring measurable rather than assumed.

PASS B — RECONCILIATION. Ask for
`journal\flags\external_research_conclusions.json`. It carries the local model's SG and
BQ points, its per-sub-test rationales and its BQ killer answer. DO NOT REWRITE PASS A.
Add a `pass_b.reconciliation` list stating, per disagreement: what the model concluded,
what you found, which is better evidenced, and why. Each entry cites its own claim_ids.

## READ PHASE 0 BEFORE SEARCHING

  D:\company_lab_data\external\research\industries\<industry_id>\industry_state.json
  D:\company_lab_data\external\research\sectors\<sector_id>\sector_state.json

The roster tells you which. Your three companies map to `us_credit_scoring`,
`ai_accelerators` and `datacenter_power_cooling`. All three objects exist and carry
their own claims. `industry_structural_growth` comes FROM the industry object; do not
re-derive it per company.

Each of those objects also lists what Phase 0 could NOT establish. Those are your
starting hypotheses, already priced. For datacenter_power_cooling: like-for-like share
versus Schneider, vendor-normalized backlog and book-to-bill, named hyperscale wins,
service attach rates, liquid-cooling revenue by vendor.

## THE THREE COMPANIES ARE CALIBRATION CASES

FICO — THE DETERIORATING MOAT. Historical economics are exceptional and the filing says
so. The right record disagrees with its own financial history: moat STRONG, trajectory
WEAKENING, regulatory_risk ELEVATED, cheapness_quality STRUCTURAL. If FICO comes back
uniformly excellent, the lane has failed its main test.

NVDA — LEADER OR LOSING RELATIVE ADVANTAGE. "AI is growing therefore NVDA is good" is
not an answer. Determine whether it is MAINTAINING or LOSING relative advantage:
custom silicon at hyperscalers, AMD, networking, inference versus training, customer
concentration, supply. `company_specific_capture` needs evidence about NVDA, not about
AI.

VRT — CAPTURE VERSUS INDUSTRY. Datacenter demand growing and Vertiv capturing
disproportionate growth are different claims needing different evidence. Only bookings,
backlog, capacity additions, order growth, named customer wins and growth RELATIVE TO
NAMED COMPETITORS establish capture. Industry growth alone gives
industry_structural_growth HIGH and says nothing about VRT. Phase 0 already returned
UNKNOWN on relative share here; UNKNOWN again is an acceptable answer.

## OUTPUT

Write D:\company_lab_data\external\payloads\<request_id>.json

{
  "request_id": "<echoed verbatim>",
  "spec_fingerprint": "<echoed verbatim>",
  "completed_at": "<ISO UTC>",
  "external_schema_version": "1.0.0",
  "cost": { "tokens": 0, "searches": 0, "cache_hits": 0 },
  "companies": [
    {
      "ticker": "FICO",
      "research_depth": 3,
      "pass_a": {
        "current_moat_strength": "STRONG",
        "moat_trajectory": "WEAKENING",
        "competitive_position": "LEADER",
        "competitive_position_trend": "DETERIORATING",
        "industry_structural_growth": "MODERATE",
        "company_specific_capture": "MODERATE",
        "demand_visibility": "HIGH",
        "market_share_direction": "LOSING",
        "pricing_power": "HIGH",
        "technology_risk": "MODERATE",
        "disruption_risk": "ELEVATED",
        "regulatory_risk": "ELEVATED",
        "cheapness_quality": "STRUCTURAL",
        "why_is_it_cheap": "<=400 chars",
        "bull_case": "<=800 chars",
        "bear_case": "<=800 chars",
        "major_thesis_risk": "<=300 chars",
        "thesis_break_condition": "<=300 chars, an OBSERVABLE event",
        "key_monitoring_variables": ["...", "..."]
      },
      "pass_b": {
        "reconciliation": [
          {"field": "bq", "local_value": 10, "external_view": "WEAKENING",
           "better_evidenced": "external", "why": "<=400 chars",
           "claim_ids": ["c_..."]}
        ]
      },
      "claims": [ ...same claim schema as Phase 0... ],
      "refresh_class": "EVENT_DRIVEN",
      "next_suggested_refresh": "2026-12-01"
    }
  ]
}

CLOSED VOCABULARIES (enforced by clab/external/schema.py — genuinely, this time):

  current_moat_strength        NONE | WEAK | MODERATE | STRONG | EXCEPTIONAL | UNKNOWN
  moat_trajectory              DETERIORATING | WEAKENING | STABLE | STRENGTHENING | UNKNOWN
  competitive_position         LAGGARD | CHALLENGER | STRONG_NUMBER_TWO | LEADER | DOMINANT | UNKNOWN
  competitive_position_trend   DETERIORATING | STABLE | IMPROVING | UNKNOWN
  industry_structural_growth   DECLINING | FLAT | MODERATE | HIGH | EXCEPTIONAL | UNKNOWN
  company_specific_capture     NONE | LOW | MODERATE | HIGH | UNKNOWN
  demand_visibility            NONE | LOW | MODERATE | HIGH | UNKNOWN
  market_share_direction       LOSING | FLAT | GAINING | UNKNOWN
  pricing_power                NONE | LOW | MODERATE | HIGH | UNKNOWN
  technology_risk              SEVERE | ELEVATED | MODERATE | LOW | UNKNOWN
  disruption_risk              SEVERE | ELEVATED | MODERATE | LOW | UNKNOWN
  regulatory_risk              SEVERE | ELEVATED | MODERATE | LOW | UNKNOWN
  cheapness_quality            STRUCTURAL | TEMPORARY | CYCLICAL | NOT_CHEAP | UNKNOWN

Claim vocabularies are unchanged from Phase 0.

## WHAT THE FINALIZER WILL REFUSE

Tested, not aspirational. Each of these is a passing test in
tests/test_external_finalize.py:

  - a request_id that does not match           -> the WHOLE payload is refused
  - a frozen request that is not from today    -> the WHOLE payload is refused
  - a spec_fingerprint that does not match     -> the WHOLE payload is refused
  - a ticker outside the frozen roster         -> that company rejected, rest survives
  - external_score, rating, rank, price_target,
    recommendation, high_conviction, anywhere  -> that company rejected
  - a categorical outside its vocabulary       -> that company rejected
  - research_depth outside 0-4, or a bool      -> that company rejected
  - a text field over its cap                  -> that company rejected
  - a missing pass_a                           -> that company rejected
  - a quote absent from its own excerpt        -> that company rejected
  - a duplicate claim_id within one company    -> that company rejected
  - verify_status supplied in a claim          -> discarded, never read

A roster ticker you do not answer is reported as `unanswered`. Nothing is silently
dropped: a payload that half-arrives must say which half and why, or the next run
cannot tell a research gap from a parsing accident.

## RULES THAT DID NOT CHANGE

1. You never produce a score, rank, rating or point total. We compute every number.
2. You never apply a gate.
3. Every claim: source_url, source_date, VERBATIM quote <=300 chars, and the ~1500-char
   excerpt you actually read. The quote must appear in the excerpt. We then FETCH YOUR
   URLS OURSELVES - 90 of Phase 0's 109 claims were verified that way and the rate is
   reported.
4. UNKNOWN is valid and expected and is NOT the bottom of the scale. It scores as
   NO_DATA, never zero.
5. Never invent a number.
6. Confidence counts DISTINCT INDEPENDENCE DOMAINS. One organisation gets one domain
   for the whole record. A domain resting on a single claim is not independence.
7. Cached research is free and must be reused. Report your spend.
8. Advisory only. Nothing here is promoted.

## WHAT YOU MUST NOT CLAIM

This ranking is NOT validated: top decile ran a -7.6% median 3-year excess return
against SPY on a survivorship-free holdout, only 45.3% beat SPY, and 95.6% of its
ranking power is sector selection. `promoted` is false and stays false. No
recommendations, no price targets, no claims about future returns.

## ORDER OF WORK

1. Read the three industry objects and the two sector briefs.
2. Write pass A for all three companies, blind. Stop.
3. Ask for the conclusions file. Write pass B.
4. Write the payload. Report your spend and every UNKNOWN you are leaving.
````
