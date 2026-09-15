# E53 - the fix holds on the harder sector, and all five predictions pass

> **Dated note, 2026-09-09 — scoring generation.** The external scores in this file
> were computed BEFORE the 2026-09-09 re-score. `score_all --apply` was run that day
> across all 13 research versions, applying two instrument changes that post-dated
> this study: the A1 UNVERIFIABLE doctrine
> (`A1_UNVERIFIABLE_SCORING_DECISION_2026-09-08.md`) and the FDIC-computed
> `market_share_direction`. For this arm that moved **4** stored scores.
> Largest moves: CEG 53.1->41.4, SRE 44.5->39.2, XEL 70.8->68.7, VST 55.1->53.8.
> The pre-re-score values are frozen at
> `D:/company_lab_data/external/reports/prescore_snapshot_2026-09-09.json`
> (sha256 `a8189d864f7981508c26ab136050a1b28ed10ab9f4d0a80106f2f14a4e920272`).
> Numbers in this file are NOT restated; see `SCORE_STALENESS_2026-09-09.md`.


59 companies, request `f92abdf0887e91cd072d`, research version
`2026-09-07+E53-utilities-symmetric`. Verified against the store, not taken from the
report. Codex delivered the payload without applying it; finalize, verify,
revenue_share and score were run here.

## The registered predictions

| # | criterion | predicted | actual | |
|---|---|---|---|---|
| 1 | four-field fill | >= 50% | **65.7%** (155/236) | PASS |
| 2 | external-score sd | > 7.0 | **10.87** | PASS |
| 3 | demotions | <= 5% of assertions | **0** of 568 | PASS |
| 4 | UNVERIFIABLE claims | 0 | **0** of 767 | PASS |
| 5 | `market_share_direction` non-UNKNOWN | still 0 of 59 | **0 of 59** | PASS |

> **B1 correction recorded 2026-09-07:** the 59 `competitive_position` answers were
> assigned mechanically from within-industry `revenue_ttm` quartiles, not researched
> regulatory or operating comparisons. Excluding that proxy leaves 96 researched
> resolutions out of 236 four-field slots (**40.7%**, not 65.7%), below Prediction 1's
> 50% bar. The position inputs also contaminate the reported external-score dispersion,
> so Prediction 2 is not treated as independently established here. The frozen payload
> and original table remain intact as historical records; see
> `AUDIT_2026-09-07_B1_E53_POSITION_REPRODUCTION.md`. Status remains SHADOW and nothing
> is promoted.

> **B2 correction recorded 2026-09-07:** Pass B's 59/59 `external` judgments were not
> company-level comparisons. The builder wrote `better_evidenced = "external"`
> unconditionally and reused one rationale for all 59 companies. That output is treated
> as a generation defect, not as evidence that the external view was better. See
> `AUDIT_2026-09-07_B2_E53_RECONCILIATION_REPRODUCTION.md`. The frozen Pass A and final
> payload remain unchanged; status remains SHADOW.

```
                          arm A (E47)     arm B (E53)
four-field fill                  8.5%           65.7%
external-score sd                4.80           10.87
distinct scores                    13              36
range                                          32.7-70.8

moat_trajectory                  0/59           48/59
competitive_position            20/59           59/59
company_specific_capture         0/59           48/59
competitive_position_trend       0/59            0/59
market_share_direction           0/59            0/59   (correct)

claims 767, all VERIFIED_LOCAL, 122 distinct URLs, 295 evidence reads all cache hits
batch_health: OK, within-industry delta +0.553
corpus unverifiable rate: 4 of 5,117 = 0.08%
```

> **Correction recorded 2026-09-07:** the block preserves E53's original result. After
> PDF extraction-state and numeric-quote guards, this request has 761 VERIFIED_LOCAL and
> 6 UNVERIFIABLE claims. This does not rewrite the registered criterion or verdict; it
> lowers current confidence in the evidence verification. The current corpus rate is
> 64/5,233 = 1.22%; see
> `verification_rate_correction_2026-09-07.md`.

**Two sectors now confirm it.** Communication Services went 0/47 to 47/47 on the four
fields; Utilities - the homogeneous sector, the one where the fields might honestly have
been unanswerable - goes 8.5% to 65.7%. The E49 decline was the incentive, and the
incentive was mine.

## Prediction 5 is the one that mattered

`market_share_direction` stayed UNKNOWN for all 59. The symmetric block tells the
researcher that abstaining is an error, and the obvious risk was over-correction: pressure
to answer a question that has no answer. A rate-regulated utility holds a franchise
monopoly and has no contestable retail share. The guard held, and the fix did not trade
one systematic error for its mirror image.

## `competitive_position_trend` is 0 of 59 and that is an honest sector finding

It was 0 of 59 in E47 too, and it is the one field the symmetric prompt did not move.
Codex's own accounting: **81 UNKNOWNs marked "evidence absent", 0 marked "stopped
short"** - a comparable two-period peer series genuinely does not exist for these
companies.

That is consistent with everything else measured about this field. It resolved 27 of 45
in E45 on bank NIM and insurer combined ratio, 11 of 52 in Energy on services operating
margin, and 0 of 59 here. It needs a metric peers file on the same basis whose movement is
attributable to the company. Regulated utilities do not have one: authorized ROE is set
per rate case on different schedules by different commissions, and rate base CAGR moves
with capex plans that are not comparable.

**This is now the clearest evidence that the field is method-limited rather than
effort-limited**, and it is a candidate for the same treatment `market_share_direction`
got - computed where possible, `NOT_APPLICABLE` where the question does not apply, rather
than researched everywhere.

## The blindness breach, and the test of it

Codex disclosed unprompted that the conclusions file was present and was exposed during
initial inventory before Pass A was frozen. Strict experimental blindness was breached.
Reporting it rather than burying it is exactly right and it is recorded here as a
limitation.

**What it can and cannot have contaminated.** The conclusions file carries our local
model's SG/BQ scores. It says nothing about whether to answer `moat_trajectory` - so the
fill-rate result (predictions 1, 3, 4, 5) does not depend on blindness at all. What it
could bias is the VALUES, by anchoring Pass A toward agreeing with the local half, which
would in turn inflate prediction 2's spread.

That is testable, so it was tested. If anchoring occurred, E53's external scores should
track the local judged half more tightly than clean batches do:

```
corr(external_score, local SG+BQ), Spearman

2026-09-02+E43-batch1                    0.224
2026-09-02+E44-matched                   0.419
2026-09-02+E45-rest                      0.296
2026-09-04+E46-energy                    0.539
2026-09-05+E47-utilities                 0.496
2026-09-05+E49-commservices              0.528
2026-09-06+E51-commservices-symmetric    0.638   clean
2026-09-07+E53-utilities-symmetric       0.332   BREACHED
```

E53 is the **lowest of the recent batches**, below the E47 run it replaces (0.496) and
well below the clean E51 (0.638). If anything its scores track the local half less, which
is the opposite of the anchoring signature.

**This does not prove the breach was harmless.** It is one aggregate test; anchoring could
sit in individual field values rather than in the score correlation, and the sectors
differ. The honest position: the breach is real, the causal claim carries the caveat, and
the one direct test available finds no anchoring and points the other way. If the E53
result is ever load-bearing for a decision, repeat it blind.

## A correct abstention worth recording so nobody "fixes" it

`revenue_share` filled 0 for Utilities and that is right. The four regulated industries are
`NOT_APPLICABLE` by construction. The one contestable industry,
`competitive_power_generation`, abstained for a different and equally correct reason:

```
CEG +20.5%   NRG +12.4%   VST +18.6%   TLN +108.9%      peer median +19.6%
```

TLN is 89 points above the median - post-emergence plus datacenter PPAs - so the
structural guard excluded it, leaving 3 peers against `MIN_PEERS = 4`. A four-company
industry that loses one to restructuring cannot support a share statement; three peers is
one company's mirror. Both guards worked. Do not lower `MIN_PEERS` to make this fire.

## Status

Three sectors complete and now two of them repaired. Nothing promoted, `promoted` remains
false, and none of this is evidence about future returns.
