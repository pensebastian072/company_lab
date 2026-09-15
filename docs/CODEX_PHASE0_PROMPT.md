# Codex Phase 0 — sector and industry intelligence build

Paste the fenced block below into Codex. It is self-contained.

## Why Phase 0 exists separately

The company lane needs `journal/flags/external_research_request.json`, which is built by
`clab/external/request.py` (V3 P1, not yet written). The sector and industry layer needs
none of that, is the expensive half, and is what makes the company lane cheap afterwards
— a fact about US credit scoring researched once is referenced by FICO, EFX and TRU
rather than researched three times.

So Phase 0 runs first and runs alone.

## The 15 seed research units are not a guess

They are `set(taxonomy.INDUSTRY_OVERRIDES.values()) | set(taxonomy.SUBINDUSTRY_ALIASES.values())`,
measured against the live book. Member counts as of 2026-09-01 (1,500 companies):

| industry_id | n | members |
|---|---:|---|
| `us_credit_scoring` | 3 | EFX, FICO, TRU |
| `ai_accelerators` | 2 | AMD, NVDA |
| `dram_hbm` | 1 | MU |
| `semiconductor_equipment` | 21 | AMAT, LRCX, KLAC, ENTG, ... |
| `datacenter_power_cooling` | 2 | ETN, VRT |
| `datacenter_reits` | 2 | DLR, EQIX |
| `cloud_infrastructure` | 2 | MSFT, ORCL |
| `cybersecurity` | 4 | CRWD, FTNT, OKTA, PANW |
| `payments` | 19 | V, MA, PYPL, FIS, GPN, ... |
| `upstream_oil_gas` | 25 | COP, EOG, DVN, APA, ... |
| `midstream` | 10 | KMI, OKE, TRGP, WMB, ... |
| `refining` | 9 | VLO, MPC, PSX, DINO, ... |
| `regional_banking` | 89 | (the largest unit in the book) |
| `pc_insurance` | 25 | CB, ALL, PGR, ACGL, ... |
| `life_insurance` | 12 | MET, AFL, PFG, GL, ... |

Note the shape: `regional_banking` (89), `pc_insurance` (25) and `upstream_oil_gas` (25)
are where shared research actually saves money. `dram_hbm` (1) and `ai_accelerators` (2)
save nothing on duplication and are on the list because a pooled "Semiconductors" brief
would be true of neither.

Two ids from the original plan sketch are deliberately absent. `EUV_lithography` is
covered by `semiconductor_equipment`, whose id ASML joins at P4 without a rename.
`LNG_US` has no members — Cheniere is not in the S&P 500/400/600 universe — and an
industry object nothing references is waste.

## Prompt

````
# COMPANY LAB — CODEX EXTERNAL INTELLIGENCE, PHASE 0: SECTOR + INDUSTRY BUILD

You are the external research arm of Company Lab, a quantamental system covering 1,500
US public companies. Two halves already exist and are DONE:

  MEASURED half — EDGAR XBRL + market data: growth, margins, ROIC, balance sheet,
  valuation, expectations, capital allocation. 59 of the framework's 94 points.

  FILING half — a local LLM on the user's GPU has already read all ~1,472 10-Ks and
  extracted business model, products, strategy, management claims, stated moat,
  customers, backlog, disclosed risks, named competitors. 35 points.

DO NOT REDO EITHER. Re-reading a 10-K to learn what a company says about itself is
wasted budget. Your only question is:

  "What would a well-informed sector specialist know about this company that cannot be
   learned reliably from the company's own filing?"

Phase 0 is SECTOR AND INDUSTRY ONLY. No per-company records yet — the company lane
needs a request file that does not exist yet. Build the reusable knowledge layer first.

## WORKING DIRECTORY

  D:\company_lab_data\external\research\
      sectors\<sector_id>\sector_state.json
      sectors\<sector_id>\sector_brief.md
      industries\<industry_id>\industry_state.json
      industries\<industry_id>\industry_brief.md

That tree already exists. Everything bulk goes on D: — C: on this box is a failing
drive with logged bad sectors, so do not write research output there.

You may READ C:\Users\<your-user>\company_lab (in particular clab/external/schema.py, which
is the authoritative vocabulary list, and clab/external/taxonomy.py, which owns the
industry ids). Write nothing there.

## HARD RULES

1. You never produce a score, rank, rating or point total. Company Lab computes every
   number, locally, from the categoricals and claims you return. If you are about to
   output a number that is not a directly observed quantity with a source, stop.
2. You never apply a gate. No HIGH_CONVICTION, no buy/sell, no price target.
3. Every claim carries a verifiable citation: source_url, source_date, a VERBATIM quote
   (<=300 chars, copied exactly, never paraphrased), and the ~1500-char excerpt you
   actually read around it. A later local pass re-fetches a sample of your URLs and
   checks the quote against what comes back. A quote that is not present in its own
   excerpt is discarded and counted against you, and the rate is reported.
4. UNKNOWN is a valid, expected answer, and it is NOT the bottom of the scale. If you
   did not find evidence, write UNKNOWN. Never a negative, never a hedge, never a
   plausible-sounding guess. The system treats UNKNOWN and NEGATIVE completely
   differently — UNKNOWN scores as NO_DATA, not as zero. Guessing corrupts the
   measurement in a way that is invisible downstream.
5. Never invent a number. Market share, growth rates, capacity, bookings and backlog
   appear only with a source that states them. No modelling, no estimation.
6. Confidence counts DISTINCT INDEPENDENCE DOMAINS, not claim counts. Ten trade-press
   rewrites of one press release is ONE domain. A company's own IR page can never, on
   its own, verify a claim that company made in its filing — that is the same source
   twice.
7. Budget is metered. Cached research is free and must be reused. Report your spend.
8. Advisory only. Every artifact carries "status": "SHADOW".

## DELIVERABLE A — 15 SHARED INDUSTRY OBJECTS

Build these FIRST. They are the reusable asset, and they are what stops the same
industry fact being researched twenty times.

  us_credit_scoring        ai_accelerators          dram_hbm
  semiconductor_equipment  datacenter_power_cooling datacenter_reits
  cloud_infrastructure     cybersecurity            payments
  upstream_oil_gas         midstream                refining
  regional_banking         pc_insurance             life_insurance

Use these ids EXACTLY. They are the keys company records join on
(clab/external/taxonomy.py). A renamed id is an orphaned object.

Each industry_state.json:

{
  "industry_id": "us_credit_scoring",
  "sector_id": "financials",
  "version": "2026-09-01",
  "status": "SHADOW",
  "structural_growth": "DECLINING | FLAT | MODERATE | HIGH | EXCEPTIONAL | UNKNOWN",
  "market_structure": "<=1500 chars — who competes, concentration, barriers",
  "key_participants": ["..."],
  "moat_mechanism": "<=1000 chars — what actually makes replication hard here, if anything",
  "replication_difficulty": "LOW | MODERATE | HIGH | EXTREME | UNKNOWN",
  "technology_trajectory": "<=1000 chars",
  "regulatory_trajectory": "<=1000 chars",
  "substitution_risk": "LOW | MODERATE | ELEVATED | SEVERE | UNKNOWN",
  "key_metrics": ["..."],
  "refresh_class": "STRUCTURAL | QUARTERLY | EVENT_DRIVEN",
  "next_refresh_due": "YYYY-MM-DD",
  "claims": [ ...claim objects, schema below... ],
  "last_updated": "<ISO UTC>"
}

REFRESH CLASSES — set these honestly, they control all future spend:
  STRUCTURAL    365d or on a major event. Moat mechanism, industry structure.
  QUARTERLY     90d. Bookings, backlog, market share, competitor results.
  EVENT_DRIVEN  on trigger. Regulation, litigation, new technology, M&A, customer loss.

## DELIVERABLE B — 11 SECTOR BRIEFS

sector_id: information_technology, health_care, financials, consumer_discretionary,
communication_services, industrials, consumer_staples, energy, utilities, real_estate,
materials

Each sector_state.json:

{
  "sector_id": "energy",
  "version": "2026-09-01",
  "status": "SHADOW",
  "major_industries": ["upstream_oil_gas", "midstream", "refining"],
  "market_structure": "<=1500 chars",
  "capital_cycle": "UNDERINVESTMENT | BALANCED | OVERINVESTMENT | UNKNOWN",
  "structural_tailwinds": ["..."],
  "structural_headwinds": ["..."],
  "current_winners": [{"ticker": "...", "why": "...", "claim_ids": ["c_..."]}],
  "current_losers":  [{"ticker": "...", "why": "...", "claim_ids": ["c_..."]}],
  "emerging_disruptions": ["..."],
  "regulatory_environment": "<=1000 chars",
  "metrics_that_matter": ["production growth", "lifting cost", "breakeven",
                          "realized pricing", "capex discipline"],
  "what_changed": "<=1200 chars since the previous version; on first build write FIRST_BUILD",
  "claims": [ ... ],
  "last_updated": "<ISO UTC>"
}

`major_industries` must reference real industry_ids, so the sector brief and the
industry objects form one graph rather than two prose documents.

`metrics_that_matter` is not decoration — it is the instruction for how companies in
this sector get judged later. Do not judge every industry identically:

  Semiconductors      utilization, node leadership, wafer capacity, memory pricing,
                      HBM demand, capex, customer concentration, product cycles
  Semi equipment      tool backlog, WFE share, service/installed-base revenue,
                      replacement cycle
  SaaS                ARR, NRR, RPO, seat growth, pricing, churn, CAC payback,
                      operating leverage
  Banks               NIM, deposits and deposit costs, credit losses, CET1, loan growth
  Insurance           combined ratio, reserve development, float, pricing cycle
  Energy              production growth, reserves, lifting cost, breakeven, realized
                      pricing, capex discipline
  Industrials         backlog, bookings, book-to-bill, capacity, orders
  Utilities           rate base growth, allowed ROE, regulatory environment, load growth
  REITs               same-store NOI, occupancy, lease spreads, cap rates, debt maturity
  Biotech             pipeline phase, trial readouts, patent cliff, payer coverage

UPDATE, NEVER RECREATE. A refresh answers one question: what has materially changed
since the previous version? Unchanged sections carry forward with their ORIGINAL
source_date intact. Restamping an old finding with today's date is a fabrication.

## CLAIM SCHEMA — every claim, everywhere

{
  "claim_id": "c_<12 hex>",
  "field": "<which field above this supports>",
  "text": "<the finding, one sentence>",
  "source_url": "https://...",
  "source_title": "...",
  "source_date": "YYYY-MM-DD",
  "source_type": "SEC_FILING | EARNINGS_CALL | INVESTOR_PRESENTATION | REGULATOR |
                  TRADE_PUBLICATION | PRIMARY_DATA | COMPANY_IR | NEWS | OTHER",
  "independence_domain": "COMPANY_IR | COMPETITOR_FILING | CUSTOMER | SUPPLIER |
                          REGULATOR | TRADE_PRESS | PRIMARY_DATA | ACADEMIC",
  "quote": "<verbatim, <=300 chars, copied exactly from the source>",
  "excerpt": "<~1500 chars of surrounding text as you actually read it>",
  "stance": "SUPPORTS | CONTRADICTS | CONTEXT",
  "fact_or_inference": "FACT | INFERENCE"
}

These vocabularies are CLOSED and are enforced mechanically by
clab/external/schema.py. A value outside them is rejected, never coerced.

## THREE CALIBRATION CASES — get these right and the rest follows

us_credit_scoring — THE DETERIORATING MOAT. Historical economics are exceptional and
the filing says so. Investigate competing scoring models, FHFA and mortgage-market
policy, bi-merge vs tri-merge, lender adoption, pricing decisions, government scrutiny,
viable alternatives. The object must be able to support: historical moat exceptional,
CURRENT moat strong, TRAJECTORY weakening, regulatory risk elevated, substitution risk
increasing. A correct record here disagrees with its own financial history. Note that
GICS scatters this industry across two sectors — FICO is Information Technology,
EFX and TRU are Industrials — which is exactly why it is one shared object.

semiconductor_equipment — THE CONFIRMED MOAT. External evidence must be able to raise
confidence WITHOUT adding points. Research EUV alternatives, technological complexity,
supplier ecosystem, accumulated R&D, patents, engineering requirements, replication time
and cost, customer dependence, installed base. The right answer is
replication_difficulty EXTREME supported by many DISTINCT independence domains, not by
many restatements of one.

datacenter_power_cooling — CAPTURE vs INDUSTRY. "Datacenter demand is growing" and
"company X is capturing disproportionate growth" are different claims needing different
evidence. Only bookings, backlog, capacity additions, order growth, named customer wins,
and growth RELATIVE TO NAMED COMPETITORS establish capture. Industry growth alone gives
structural_growth HIGH and says nothing about any single company. This unit is VRT and
ETN only; the wider GICS bucket also holds lighting, pool equipment and defense
electronics, and is not this industry.

## WHAT YOU MUST NOT CLAIM

The ranking this feeds is NOT validated. Its own top decile had a -7.6% median 3-year
excess return over SPY on a survivorship-free holdout, only 45.3% beat SPY, and 95.6%
of its ranking power is sector selection. `promoted` is false and stays false. Your
research improves what is MEASURED; it is not evidence the ranking works. Never write a
recommendation, a price target, or any claim about future returns.

## ORDER OF WORK

1. Build us_credit_scoring, semiconductor_equipment and datacenter_power_cooling FIRST
   and stop. Those are the three calibration cases; they get checked before you spend
   anything on the other twelve.
2. Then the remaining 12 industry objects.
3. Then the 11 sector briefs, referencing the industry objects by id.
4. Write D:\company_lab_data\external\research\PHASE0_SUMMARY.md: objects built, claim
   counts, DISTINCT independence domains per object, what you could NOT establish (the
   UNKNOWNs, listed explicitly), and your spend.

The UNKNOWN list in that summary is a deliverable, not an apology. It is what tells us
where the external layer has nothing to say, which is a different and more useful thing
than a confident guess.
````

## What happens to this output

`clab/external/store.py` ingests `industry_state.json` and `sector_state.json` into the
`industry_intelligence` and `sector_brief` tables, keyed `(id, version)` so a refresh
never overwrites the version a comparison was made against. Claims land in
`external_claim` with a locally-assigned `verify_status` — `VERIFIED_LOCAL`,
`SELF_ATTESTED` or `UNVERIFIABLE`. Codex does not set that field, and a claim that
arrives with one has it overwritten.
