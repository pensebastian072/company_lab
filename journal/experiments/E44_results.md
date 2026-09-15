# E44 - the funnel test, and two flags that were measuring nothing

> **Dated note, 2026-09-09 — scoring generation.** The external scores in this file
> were computed BEFORE the 2026-09-09 re-score. `score_all --apply` was run that day
> across all 13 research versions, applying two instrument changes that post-dated
> this study: the A1 UNVERIFIABLE doctrine
> (`A1_UNVERIFIABLE_SCORING_DECISION_2026-09-08.md`) and the FDIC-computed
> `market_share_direction`. For this arm that moved **14** stored scores.
> Largest moves: BOH 45.5->50.5, COLB 33.8->38.8, FFIN 45.5->50.5, HBAN 45.5->50.5, NBHC 40.5->45.5, SFBS 42.2->47.2 ....
> The pre-re-score values are frozen at
> `D:/company_lab_data/external/reports/prescore_snapshot_2026-09-09.json`
> (sha256 `a8189d864f7981508c26ab136050a1b28ed10ab9f4d0a80106f2f14a4e920272`).
> Numbers in this file are NOT restated; see `SCORE_STALENESS_2026-09-09.md`.


40 fresh companies, matched control, request `1d7df1eb255e193553a5`, research version
`2026-09-02+E44-matched`.

## The delivery is the best yet

| | |
|---|---|
| accepted / rejected | 40 / 0 |
| non-UNKNOWN fields | 327, **all citation-backed**, zero demotions |
| UNKNOWN fields | 153, and **all 153 carry blocking claims. G = 0.** |
| claims | 480 from 82 sources, 5 independence domains |
| verification | 479 VERIFIED_LOCAL, 1 SELF_ATTESTED, **0 UNVERIFIABLE** |
| corpus unverifiable rate | **0.40%** over 1,000 checked |
| searches | 295 + 14 Phase 0 cache hits, inside the 250-350 estimate |

The blocking-claims instruction worked completely. Every single UNKNOWN is a RESULT -
looked at, blocked, evidence attached - and not one is a gap.

## THE FLAGS WERE MEASURING THE INDUSTRY, NOT THE COMPANY

Reported funnel result: priority 1.906 flags per company against control 1.625, a
+17.3% lift, "yes numerically but not decisively".

That is not what those flags were counting.

```
REGULATORY_IMPAIRMENT               39 of 40 companies   (98%)
TECHNOLOGY_DISRUPTION               28 of 40 companies   (70%)
UNVERIFIED_CORE_THESIS               4 of 40             (10%)
COMPETITIVE_POSITION_DETERIORATING   3 of 40             (8%)
```

Inside `regional_banking`, **both risk flags fired for 19 of 19 banks** and there were
**two distinct flag-sets across nineteen companies**. "Banking is regulated" is an
industry constant, not a finding about a bank. 67 of the 74 flags were these two.

This is E30's symptom exactly: *a sub-test constant across every company is the symptom
to look for* - the one that found `bs_dilution` dead in all eleven sectors.

**Fixed.** A risk flag now requires the company to be **worse than its industry peers**,
using the median of peers carrying that field, with at least 4 peers. Below that the
comparison is unmeasurable, and an unmeasurable comparison is not a passed one - the
same rule the framework applies to peer multiples. With no peer context a risk flag
cannot fire at all, because without peers there is no way to separate a company signal
from an industry constant.

## The funnel result, after the fix

```
priority   7 flags / 32 companies = 0.219 per company   any-flag 7/32 = 22%
control    0 flags /  8 companies = 0.000 per company   any-flag 0/8  =  0%
```

Both industry constants vanish. What survives is the whole of what the layer found:

| company | arm | industry | flag |
|---|---|---|---|
| ALL | priority | pc_insurance | COMPETITIVE_POSITION_DETERIORATING |
| OKE | priority | midstream | COMPETITIVE_POSITION_DETERIORATING |
| TFIN | priority | regional_banking | COMPETITIVE_POSITION_DETERIORATING |
| AMD | priority | ai_accelerators | UNVERIFIED_CORE_THESIS |
| FTNT | priority | cybersecurity | UNVERIFIED_CORE_THESIS |
| LRCX | priority | semiconductor_equipment | UNVERIFIED_CORE_THESIS |
| MPC | priority | refining | UNVERIFIED_CORE_THESIS |

**7-0 to priority.** And it must not be over-read:

```
under the null: 7 flagged of 40, control draws 8
  expected flagged in control : 1.40
  observed                    : 0
  P(control draws 0)          : 0.181
```

Drawing zero happens about one time in six by chance. **Directionally supportive of the
priority engine; nowhere near established.** The honest reading is that the question is
now *askable* - E43 could not even be interpreted - and needs a control arm several
times larger before it has an answer.

The three COMPETITIVE_POSITION_DETERIORATING companies are exactly the three the
research itself identified as weakening despite strong-looking accounts: ALL (8.7% 3y
CAGR, 46% ROE, Protection Plans income down 11.7%), OKE (27.0% CAGR, crude shipments
declining), TFIN (24.6% operating margin, NIM down 28bp). The layer found what it is
for.

## The binding constraint is now COVERAGE, not evidence

**Only 2 of 40 companies clear the 0.80 external coverage floor: AMD and MSFT.**

```
coverage distribution: 0.55 x2, 0.57 x1, 0.65 x18, 0.67 x1, 0.70 x8, 0.75 x7, 0.77 x1, 0.87 x2
median scored fields: 8 of 12
```

The arithmetic is forced. `market_share_direction` and `competitive_position_trend`
came back UNKNOWN for **all 40 companies**, which caps coverage at 10/12 = 0.833. One
further UNKNOWN - and `competitive_position` or `industry_structural_growth` is usually
next - takes a company to 9/12 = 0.75 and under the floor.

So 38 of 40 companies got flawless, fully cited, locally verified research and **no
external score**.

I am NOT lowering the floor. Retuning a gate so more things pass is the self-flattering
one-line edit this repo has caught itself making before, and E29 refused an
applicability map for exactly this shape of argument. The floor is doing its job: it is
telling us the evidence does not reach.

The real answer is in Codex's own report. For every one of the 40 it named the specific
disclosure that would settle `market_share_direction`:

- **regional banks (19)** - consecutive FDIC Summary of Deposits institution-by-market
  tables, identical geographies and acquisition adjustments
- **P&C insurers (6)** - NAIC direct-written-premium by line and state, company and
  named competitors, two periods
- **refiners (4)** - EIA throughput/capacity by operator and region
- **midstream (3)** - named-competitor basin throughput or contracted capacity
- **upstream (2)** - EIA/state-regulator production series

FDIC Summary of Deposits and NAIC are **free, public, and structured**. That is 25 of
the 40 companies in this batch, and it is the single highest-value next move in the
project: it converts the most common unresolved field in the layer from unanswerable
into computed, and it does it without a paid subscription.

`competitive_position_trend` is harder - Codex's note that "current filings describe
company performance much better than competitor-relative movement" is the real
constraint, and no purchase fixes it directly.

## Status

Nothing promoted. This says nothing about future returns.
