# Codex Phase 0 — continuation after the calibration checkpoint

The three calibration objects were checked against `clab/external/schema.py` and are in
the catalog. Calibration reads correctly:

| unit | result | verdict |
|---|---|---|
| `us_credit_scoring` | moat weakening, substitution ELEVATED, structural growth UNKNOWN | correct — the record disagrees with its own financial history, which is the FICO test |
| `semiconductor_equipment` | replication EXTREME, growth HIGH, substitution LOW | correct — a confirmed moat |
| `datacenter_power_cooling` | growth HIGH, **relative share vs Schneider UNKNOWN** | correct — industry growth established, company capture explicitly not |

Two things the delivery report could not have caught, found by running our own checks:

1. **The schema did not enforce what the prompt claimed it enforced.** Our bug, fixed —
   `structural_growth`, `replication_difficulty` and `substitution_risk` are now real
   closed vocabularies in `schema.py`.
2. **The independence-domain label is a lever.** Confidence counts distinct domains, so
   relabelling two claims makes the same evidence report as more independent, and
   nothing about the object looks wrong. Measured on the delivery:

```
us_credit_scoring         6 claims /  4 urls / 2 domains   honest and thin
semiconductor_equipment   7 claims /  7 urls / 5 domains   4 of the 5 rest on ONE claim
datacenter_power_cooling  6 claims /  5 urls / 4 domains   3 rest on one claim, AND
                          www.se.com is filed as both COMPETITOR_FILING and SUPPLIER
```

All 19 claims are stored `SELF_ATTESTED`, not verified. Codex re-fetching Codex's own
URLs is not verification; nothing reaches `VERIFIED_LOCAL` until `verify.py` fetches
from this side.

## Measured cost, for sizing the rest

3 industry objects cost 21 retrieval batches / 27 searches / 56 open-find operations.
Straight-line: the remaining 12 industries land near 110 searches, and the 11 sector
briefs are a similar or slightly larger unit of work. Budget roughly 200-250 more
searches for the whole of Phase 0.

## Prompt

````
# COMPANY LAB — CODEX PHASE 0, CONTINUATION

Calibration approved. The three objects you built are validated and ingested. Build the
remaining 12 industry objects, then the 11 sector briefs, then the summary.

Everything you write still goes under this one root and nowhere else:

  D:\company_lab_data\external\research\

## FIRST — three corrections to carry into everything that follows

### 1. ONE ORGANISATION GETS ONE DOMAIN, FOR THE WHOLE OBJECT

In datacenter_power_cooling you filed www.se.com (Schneider Electric) as
COMPETITOR_FILING on one claim and SUPPLIER on another. Schneider is a competitor in
that industry. Filing it two ways turns one organisation into two apparent independent
sources, and because confidence counts DISTINCT DOMAINS, that inflates it.

Rule: decide what relationship an organisation has to THIS industry, once, and use that
domain for every claim sourced from it. If an organisation genuinely occupies two roles,
pick the one that matters for the claim being made and say so in the claim text.

Fix that object: re-file both www.se.com claims as COMPETITOR_FILING and re-emit
datacenter_power_cooling.

### 2. A DOMAIN SUPPORTED BY ONE CLAIM IS NOT INDEPENDENCE

semiconductor_equipment reported 5 domains, 4 of them resting on a single claim each.
That is one source per domain, not five independent lines of evidence.

Do NOT go hunting for one claim per domain to raise the count. Three domains with two
or three claims each is stronger than six with one each, and it will be scored that way.
Add a domain when the evidence is genuinely there and leave it out when it is not.

### 3. A UNIT MEMBER'S OWN IR IS THE WEAKEST SOURCE YOU CAN CITE

Half of datacenter_power_cooling's claims were Vertiv and Eaton investor material -
the companies inside the unit, describing themselves. That is the same category of
evidence as the 10-K half we already have, and it is what this whole layer exists to go
beyond. Use it for facts only a company can state (its own backlog, its own orders), and
never as the support for a structural conclusion about the industry.

## SELF-CHECK BEFORE YOU DECLARE ANY BATCH DONE

Run this. It validates against the real schema, not your own:

  cd C:\Users\<your-user>\company_lab
  $env:PYTHONPATH="C:\Users\<your-user>\company_lab"
  .venv\Scripts\python.exe -m clab.external.research_ingest

Read-only, writes nothing. Exit code 0 means every object on disk is valid. It prints,
per object: claims, distinct urls, distinct hosts, distinct domains, claims-per-url,
inference count, any domain resting on a single claim, and any host filed under two
domains. Fix what it flags before reporting.

## DELIVERABLE A — the remaining 12 industry objects

  ai_accelerators          dram_hbm                 datacenter_reits
  cloud_infrastructure     cybersecurity            payments
  upstream_oil_gas         midstream                refining
  regional_banking         pc_insurance             life_insurance

Use these ids EXACTLY - they are the join keys. Member counts in the book:
regional_banking 89, pc_insurance 25, upstream_oil_gas 25, payments 19,
life_insurance 12, midstream 10, refining 9, cybersecurity 4, and 2 each for
ai_accelerators, datacenter_reits, cloud_infrastructure; dram_hbm 1.

Spend in proportion. regional_banking covers 89 companies and deserves real depth.
dram_hbm covers one and exists only because a pooled "Semiconductors" brief would be
true of neither it nor ai_accelerators.

Same industry_state.json shape as before. The closed vocabularies, now genuinely
enforced:

  structural_growth       DECLINING | FLAT | MODERATE | HIGH | EXCEPTIONAL | UNKNOWN
  replication_difficulty  LOW | MODERATE | HIGH | EXTREME | UNKNOWN
  substitution_risk       SEVERE | ELEVATED | MODERATE | LOW | UNKNOWN
  refresh_class           STRUCTURAL | QUARTERLY | EVENT_DRIVEN

Claim vocabularies unchanged:

  stance               SUPPORTS | CONTRADICTS | CONTEXT
  fact_or_inference    FACT | INFERENCE
  source_type          SEC_FILING | EARNINGS_CALL | INVESTOR_PRESENTATION | REGULATOR |
                       TRADE_PUBLICATION | PRIMARY_DATA | COMPANY_IR | NEWS | OTHER
  independence_domain  COMPANY_IR | COMPETITOR_FILING | CUSTOMER | SUPPLIER |
                       REGULATOR | TRADE_PRESS | PRIMARY_DATA | ACADEMIC

## DELIVERABLE B — 11 sector briefs

sector_id: information_technology, health_care, financials, consumer_discretionary,
communication_services, industrials, consumer_staples, energy, utilities, real_estate,
materials

  D:\company_lab_data\external\research\sectors\<sector_id>\sector_state.json
  D:\company_lab_data\external\research\sectors\<sector_id>\sector_brief.md

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
  "metrics_that_matter": ["..."],
  "what_changed": "FIRST_BUILD",
  "claims": [ ... ],
  "last_updated": "<ISO UTC>"
}

major_industries must reference real industry_ids you built, so the sectors and the
industries form one graph rather than two prose documents.

A winner or loser needs a claim_id. "Company X is gaining share" with no citation is
the single easiest thing to write and the least useful thing in the file - leave the
lists short and sourced, or empty.

metrics_that_matter is the instruction for how companies in that sector get judged
later. Semis: utilization, node leadership, wafer capacity, memory pricing, HBM demand,
capex, customer concentration. SaaS: ARR, NRR, RPO, seat growth, churn, CAC payback.
Banks: NIM, deposits and deposit costs, credit losses, CET1, loan growth. Insurance:
combined ratio, reserve development, float, pricing cycle. Energy: production growth,
reserves, lifting cost, breakeven, realized pricing, capex discipline. Industrials:
backlog, bookings, book-to-bill, capacity, orders. Utilities: rate base growth, allowed
ROE, regulatory environment, load growth. REITs: same-store NOI, occupancy, lease
spreads, cap rates, debt maturity. Biotech: pipeline phase, trial readouts, patent
cliff, payer coverage.

## THE RULES THAT DID NOT CHANGE

1. You never produce a score, rank, rating or point total.
2. You never apply a gate.
3. Every claim: source_url, source_date, a VERBATIM quote <=300 chars, and the
   ~1500-char excerpt you actually read around it. The quote must appear in the excerpt.
4. UNKNOWN is valid and expected, and is NOT the bottom of the scale. It scores as
   NO_DATA, never as zero. Never a hedge, never a plausible guess. UNKNOWN is what you
   returned for relative share in datacenter_power_cooling and it was the right answer.
5. Never invent a number.
6. Confidence counts DISTINCT INDEPENDENCE DOMAINS - see corrections 1 and 2.
7. Cached research is free and must be reused. Report your spend.
8. Advisory only. "status": "SHADOW" on every artifact.

## ORDER OF WORK

1. Re-emit datacenter_power_cooling with the www.se.com domain conflict fixed.
2. The 12 industry objects, self-check after every four.
3. The 11 sector briefs, self-check after every four.
4. D:\company_lab_data\external\research\PHASE0_SUMMARY.md - objects built, claim
   counts, distinct domains per object, the UNKNOWNs listed explicitly, and your spend.

Report at the end, not at each step.

## WHAT YOU MUST NOT CLAIM

This ranking is NOT validated. Its own top decile ran a -7.6% median 3-year excess
return against SPY on a survivorship-free holdout, only 45.3% beat SPY, and 95.6% of
its ranking power is sector selection. `promoted` is false and stays false. Your
research improves what is measured; it is not evidence the ranking works. No
recommendations, no price targets, no claims about future returns.
````
