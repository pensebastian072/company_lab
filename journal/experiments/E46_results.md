# E46 - Energy is complete, and two fields declare themselves

> **Dated note, 2026-09-09 — scoring generation.** The external scores in this file
> were computed BEFORE the 2026-09-09 re-score. `score_all --apply` was run that day
> across all 13 research versions, applying two instrument changes that post-dated
> this study: the A1 UNVERIFIABLE doctrine
> (`A1_UNVERIFIABLE_SCORING_DECISION_2026-09-08.md`) and the FDIC-computed
> `market_share_direction`. For this arm that moved **2** stored scores.
> Largest moves: LBRT 35.4->30.4, PR 35.5->33.8.
> The pre-re-score values are frozen at
> `D:/company_lab_data/external/reports/prescore_snapshot_2026-09-09.json`
> (sha256 `a8189d864f7981508c26ab136050a1b28ed10ab9f4d0a80106f2f14a4e920272`).
> Numbers in this file are NOT restated; see `SCORE_STALENESS_2026-09-09.md`.


52 companies, request `9e32692a515262b68bfd`, research version `2026-09-04+E46-energy`.
The first sector finished at 100%.

## The delivery

| | |
|---|---|
| accepted / rejected | 52 / 0 |
| claims | 634 from 111 distinct sources |
| verification | **634 of 634 VERIFIED_LOCAL**, zero SELF_ATTESTED, zero UNVERIFIABLE |
| non-UNKNOWN fields | 426, all citation-backed, zero demotions |
| UNKNOWN | 198, all with blocking claims, **zero gaps** |
| searches | 208 + 4 cache hits |
| corpus unverifiable rate | **0.17%** (4 of 2,290), down from 0.25% |

Four batches now with zero rejections, zero demotions and zero UNKNOWN gaps. Verified
against the store, not taken from the report.

**Energy: 71 of 71.** External scores run 22.5 to 78.0, median 38.5. Top of the sector is
TPL at 78.0, then AROC 72.8, KGS 67.8, LEU 64.8.

## Phase A was right to refuse, and the refusal is now in the taxonomy

Codex built four industry objects, found `coal_consumable_fuels` incoherent because GICS
had filed Centrus beside Peabody, and returned UNKNOWN for all three industry fields
rather than average uranium enrichment together with thermal coal. That refusal cost
BTU, CNR and LEU their industry fields, and the fix was the taxonomy, not the research.

`LEU` now overrides to `uranium_enrichment` and the rebuilt objects carry real answers:

```
coal_consumable_fuels  2026-09-02.1  DECLINING / HIGH / ELEVATED    BTU CNR
uranium_enrichment     2026-09-02    HIGH / EXTREME / LOW           LEU
```

The lesson generalised: for E47 the Utilities taxonomy was fixed **before** staging.

## `market_share_direction` is not a researchable field

This is the batch's clearest result and it is a negative one.

```
Energy                     0 resolved of 71
corpus                    33 resolved of 183
  ...of which financials  29, and every one of those came from the FDIC
                            Summary of Deposits COMPUTATION, not from research
  researched resolutions   4 of 183 = 2.2%
```

Web research has resolved this field four times in one hundred and eighty-three
companies. Every other resolution in the corpus was computed locally from a free primary
registry.

And it is not free to fail. It cost **52 claims in this batch - one per company, 8.2% of
the entire claim budget** - spent entirely on documenting why the answer cannot be
obtained. Those are honest blocking claims and they are correctly marked `R`, but 198 of
them across four batches is a standing tax on every future sector.

**The response is not to delete the field.** It resolves fine when a registry publishes
the share. It is to stop *researching* it and only *compute* it:

| sector | registry | status |
|---|---|---|
| financials (banks) | FDIC Summary of Deposits | built, 55 of 89 resolve |
| utilities | EIA-861 retail sales and customers by provider | named in the E47 plan, not built |
| energy (upstream) | EIA and state regulator production by operator | not built |
| everything else | none known | keep as UNKNOWN, stop spending a claim on it |

## `competitive_position_trend` works only where peers share a filed metric

E45 broke this field open by switching from market-share series to rank-order against
named peers on a shared metric. It resolved 27 of 45 there. In Energy it resolved 11 of
52, and **all eleven were oilfield services**, rank-ordered on same-period fiscal-year
operating margin:

```
IMPROVING       AROC +836bps   INVX +613   KGS +448
STABLE          OII  +183      FTI  +172   TDW -224   WHD -242
DETERIORATING   NOV  -423      HLX  -434   LBRT -721  AESI -1178
```

Zero of the twenty upstream E&Ps resolved. The reason is structural and it is the Energy
warning turning around and biting the method: **an E&P's margin rank-order is a rank-order
on hedging, acreage quality and realised price, not on competitive position.** The
commodity contaminates the very metric the rank-order method depends on. Banks have NIM
and insurers have combined ratio because both are competitive outcomes; an upstream
producer has no equivalent.

So the method is not general. It is worth stating what it needs: a metric that peers file
on the same basis, over the same periods, whose movement is attributable to the company
rather than to a price all of them face.

## Coverage is uneven, and the biggest industry is the weakest

```
industry                        fields backed    rate
uranium_enrichment                   10/12        83%
oil_gas_equipment_services          168/216       78%
integrated_oil_gas                   18/24        75%
midstream                            88/120       73%
refining                             75/108       69%
oil_gas_drilling                     32/48        67%
upstream_oil_gas                    185/300       62%   <- 25 companies
coal_consumable_fuels                14/24        58%
```

Seven of the twelve fields are near-complete across the sector (moat strength, structural
growth, demand visibility all 100%; pricing power 93%; the three risk fields 96-99%).
The whole coverage deficit sits in five fields: market share (0%), position trend (21%),
competitive position (35%), capture (41%), moat trajectory (49%).

That shape matters for how the sector ranking should be read. It is well evidenced on
what an industry is and what a company's moat and risks look like today, and thin on
whether a company is winning against its peers.

## Moat trajectory against the financial history

Eight disagreements, and the commodity-versus-company split was reported explicitly as
asked:

- **accounts moving with the COMPANY**: AESI, FTI, HLX, LBRT, NOV, TDW, WHD - all services
- **accounts moving with the COMMODITY**: XOM

No upstream producer appears, which is not a finding about upstream: `moat_trajectory`
was UNKNOWN for most of them, so there was nothing to disagree with. Running total across
all batches is nineteen.

## The 17-versus-26 claim count

Not a discrepancy. `external_claim.industry_id` is populated on company claims as well as
industry-object claims, so counting by that column mixes the two - it now returns 53 for
coal plus uranium, against the 17 measured before Phase B ingested any company claims.
Codex's 26 counts distinct claim ids referenced by the five object files. Different sets,
both correct, and neither is the number to quote. Nothing to repair.

## Status

Energy complete. 179 of the covered pool researched. The control arm stays retired -
complete sectors do not ration, so the priority-versus-chance question is moot here
rather than answered, and E45's verdict stands: after 85 companies the priority engine
was not shown to beat chance.

Nothing promoted. `promoted` remains false. None of this is evidence about future returns.
