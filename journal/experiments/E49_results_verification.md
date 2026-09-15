# E49 verification - the negative result is real, and it is not about the sector

> **Dated note, 2026-09-09 — scoring generation.** The external scores in this file
> were computed BEFORE the 2026-09-09 re-score. `score_all --apply` was run that day
> across all 13 research versions, applying two instrument changes that post-dated
> this study: the A1 UNVERIFIABLE doctrine
> (`A1_UNVERIFIABLE_SCORING_DECISION_2026-09-08.md`) and the FDIC-computed
> `market_share_direction`. For this arm that moved **5** stored scores.
> Largest moves: NYT 30.8->23.3, PPLI 31.0->27.7, PINS 35.8->33.8, ROKU 35.8->33.8, TTD 34.8->32.8.
> The pre-re-score values are frozen at
> `D:/company_lab_data/external/reports/prescore_snapshot_2026-09-09.json`
> (sha256 `a8189d864f7981508c26ab136050a1b28ed10ab9f4d0a80106f2f14a4e920272`).
> Numbers in this file are NOT restated; see `SCORE_STALENESS_2026-09-09.md`.


Verified against the store 2026-09-05. Codex's delivery reproduces exactly: 47 of 47
accepted, 0 rejected, 0 demotions, **564 of 564 claims VERIFIED_LOCAL**, 11 industry
objects with 55 claims. Revenue-share filled 23 companies (6 GAINING, 11 FLAT, 6 LOSING).

E49's registered predictions: **1 of 5 passed.**

```
#  criterion                        predicted    actual     verdict
1  external-score sd                > 8.0        2.90       FAIL
2  distinct scores                  > 40% of n   38.3%      FAIL
3  largest tied group               < 25% of n   13%        PASS
4  fields resolving for 0 of n      <= 1         4          FAIL
5  technology_risk distinct values  >= 3         2          FAIL
```

Under the registered rule that is unambiguous: `sd_opmargin` does not determine sector
order, and prediction 5's failure says stop before buying another sector. Both hold. But
the reason is not the one the study was looking for.

## sd_opmargin failed in the most informative possible direction

Communication services was the **highest** sector in the book on measured-half dispersion
(`sd_score` 15.3) and returned the **lowest** external dispersion yet measured - 2.90,
below Utilities' 4.80. The screen did not merely fail to predict; it pointed the wrong
way. Drop it.

## Two hypotheses of mine, both measured, both refuted

**"The external layer is a sector bet, like the measured half."** Wrong, and by a wide
margin. Variance decomposition over all 289 researched companies:

```
explained by sector    29.1%   (6 sectors)
explained by industry  36.9%   (20 industries)
company-level, within industry   63.1%
```

E03 measured 95.6% of the MEASURED half's ranking power as sector selection. The external
half is nothing like that. Whatever is wrong, it is not that.

**"Buckets holding non-comparable peers kill the rank-order fields."** It was a good
story - `interactive_media_services` holds GOOGL beside YELP, and rank-ordering ARPU
across those is meaningless. Measured as within-industry dispersion of log market cap
against the fill rate of the four rank-order fields, over 20 industries with n >= 4:
**Spearman 0.066.** No relationship. `us_credit_scoring` has the tightest size dispersion
in the book (0.17) and fills 85%; `oil_gas_drilling` is nearly as tight (0.22) and fills
25%; `payments` is dispersed (1.67) and fills 80%.

## What it actually is: the process decayed, monotonically, across eight batches

```
research_version                n    4-field fill   all-12 fill
2026-09-02  (pilot)              3        92%           92%
2026-09-02+E42-cited             3        83%           86%
2026-09-02+E43-batch1           40        87%           79%
2026-09-02+E44-matched          40        49%           71%
2026-09-02+E45-rest             45        65%           79%
2026-09-04+E46-energy           52        30%           75%
2026-09-05+E47-utilities        59         8%           61%
2026-09-05+E49-commservices     47         0%           62%
```

The four fields are `moat_trajectory`, `competitive_position`,
`competitive_position_trend` and `company_specific_capture` - **45 of the 100 external
points.** They went from 92% filled to 0% filled.

Eight sectors do not independently become homogeneous in chronological order.

**The confound-free test is the same industry across batches**, where the peer set, the
industry object and the companies' comparability are all held fixed:

```
upstream_oil_gas    E43  n=3   92%      pc_insurance   E43  n=8   91%
                    E44  n=2   38%                     E44  n=6   50%
                    E46  n=20   5%                     E45  n=5   70%

regional_banking    E43  n=5   75%      payments       E43  n=13  85%
                    E44  n=19  47%                     E44  n=1   50%
                    E45  n=20  69%                     E45  n=5   75%
```

`upstream_oil_gas` is the clearest: 92% to 5% within one industry. The industry did not
change. The process did.

## The most likely cause is something I built

From E44 onward every prompt I wrote carried some version of:

> "An UNKNOWN with blocking claims is a RESULT; one with nothing behind it is a GAP."
> "E44 needed ZERO demotions across 327 fields - hold that."
> "Five batches running with zero demotions - hold it."
> "Zero gaps across five batches - hold that too."

That is an **asymmetric incentive and I reinforced it every single batch.** An UNKNOWN
carrying a blocking claim is scored as a success in my own reporting. A non-UNKNOWN whose
citation does not name the field is a *demotion* - reported as a failure. Abstaining is
free and cheap; asserting risks the one number I kept congratulating.

The break starts at E44, which is where the citation rule went from measured
(`E42_citation_rule_result.md`) to enforced-and-praised, and it never recovers.

**This is a hypothesis, not a finding.** Batch order is confounded with everything else
that changed over those eight batches, and observational data over 8 points cannot
separate them. It needs an experiment, which is E50.

## What this does and does not establish

Establishes: the decline is real, monotonic, survives holding the industry fixed, and is
not explained by sector heterogeneity, peer comparability, or sector-versus-company
variance. 45 of 100 external points are currently dead in the two most recent sectors.

Does not establish: what caused it. Four candidate mechanisms are entangled - the
abstention incentive, the citation rule's enforcement, the complete-sector switch at E46,
and the removal of researched fields (market share at E49). One variable per arm, or the
answer will be another story that measures well and is wrong.

Does not establish anything about returns. `promoted` stays false.

## Consequences now

1. **Do not buy a fourth sector until E50 reports.** E49's own registered outcome map
   said this on prediction 5's failure, and the decay finding says it louder.
2. **`sd_opmargin` is dropped as a screen**, per the registered rule. It was right once
   and pointed the wrong way when tested.
3. **The two finished sectors keep their evidence and lose their ranking claim.**
   Utilities and communication services have impeccable claim sets - 708 and 564, all
   VERIFIED_LOCAL - and external scores that separate almost nobody. The evidence is worth
   keeping; the within-sector order is not worth reading.
