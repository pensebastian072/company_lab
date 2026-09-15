# E59 - Financials Phase B batch 1 result

> **Dated note, 2026-09-09 — scoring generation.** The external scores in this file
> were computed BEFORE the 2026-09-09 re-score. `score_all --apply` was run that day
> across all 13 research versions, applying two instrument changes that post-dated
> this study: the A1 UNVERIFIABLE doctrine
> (`A1_UNVERIFIABLE_SCORING_DECISION_2026-09-08.md`) and the FDIC-computed
> `market_share_direction`. For this arm that moved **0** stored scores and filled **128** that had none.
> The pre-re-score values are frozen at
> `D:/company_lab_data/external/reports/prescore_snapshot_2026-09-09.json`
> (sha256 `a8189d864f7981508c26ab136050a1b28ed10ab9f4d0a80106f2f14a4e920272`).
> Numbers in this file are NOT restated; see `SCORE_STALENESS_2026-09-09.md`.
>
> **Second dated note, same day — the FDIC fill.** `marketshare.py` was wired after this
> file was written. It filled `market_share_direction` for 13 companies across the three
> E59 versions (7 in b1, the same 7 in b1-rerun, 6 in b2), zero conflicts, and those rows
> were re-scored: seven +5.0, four +2.5, six +0.0. Every other Financials company still
> reads UNKNOWN on that field, and the ceiling is FDIC name matching rather than economics.
> See `MARKET_SHARE_DIRECTION_2026-09-09.md`.


Recorded 2026-09-08. Advisory / SHADOW. `promoted` remains false.

## Delivery and correction

The accepted batch is request `3ff6f3aa0f3608c2f126`, sample
`E59-financials-phaseb-b1-rerun`, research version
`2026-09-08+E59-financials-phaseb-b1-rerun`. It contains exactly the frozen 43-company
roster: no company was added, omitted, or substituted.

Request `0f796aae25b60d4865e5` was burned after its frozen blind pass. A semantic audit found
that the frozen taxonomy placed ERIE in `insurance_brokers`; the first pass therefore
ranked ERIE and WTW as peers even though Erie Indemnity/P&C insurance is not comparable
with WTW's brokerage business. That version remains in the append-only store for audit,
but it is not the accepted batch. The corrected request used the same roster and a new
sample/version; its blind pass was independently frozen before conclusions were released.

## Frozen pass and receipt

- Frozen blind payload: `3ff6f3aa0f3608c2f126.pass_a.json`
- Frozen sha256: `d24c933c703ccf1d2a97245a8be6649feb1bb733531564047a016ae64df76e06`
- Search/reads: 258; cache hits: 258
- Distinct cited URLs: 89
- Claims: 550
- Independence-domain claim counts: COMPANY_IR 473, COMPETITOR_FILING 39,
  REGULATOR 26, TRADE_PRESS 11, PRIMARY_DATA 1
- Quote-in-excerpt containment failures: 0

After release, five reused industry-object citations needed literal-verification repairs
in the final payload: four asset-management structural-growth claims were changed to the
exact locally rendered SEC text, and EQH's retirement structural-growth citation was
changed to a locally verified LIMRA claim. The frozen Pass A file was not edited; its hash
still matched after reconciliation.

## Store-first verification

The finalizer accepted 43 companies and rejected 0. All 426 non-UNKNOWN categorical
values had a claim naming the field. It stored 550 claims. `verify --apply` then left the
accepted request at 550/550 `VERIFIED_LOCAL`.

Whole-corpus claim status after the run:

| status | claims |
|---|---:|
| VERIFIED_LOCAL | 6,271 |
| UNVERIFIABLE | 64 |
| SELF_ATTESTED | 58 |

The checked-claim UNVERIFIABLE rate is 64 / 6,335 = 1.010%. SELF_ATTESTED claims are
reported separately rather than folded into that denominator.

## Batch health

`batch_health` returned `OK` for 43 companies.

| measure | result |
|---|---:|
| batch fill | 0.820 |
| baseline fill | 0.529 |
| pooled delta | +0.291 |
| within-industry delta | +0.074 |

The pooled comparison is confounded by sector mix. The within-industry result is the one
to read: the shared regional-banking bucket improved from 0.683 to 0.979 (+0.296), while
three already-full shared buckets remained at 1.000.

## Four-field fill by industry

| industry | n | trajectory | position | position trend | capture |
|---|---:|---:|---:|---:|---:|
| alternative_asset_management | 2 | 2/2 | 2/2 | 2/2 | 2/2 |
| asset_management_custody_banks | 4 | 4/4 | 4/4 | 4/4 | 4/4 |
| consumer_finance | 4 | 4/4 | 4/4 | 4/4 | 4/4 |
| custody_banks | 1 | 0/1 | 1/1 | 0/1 | 0/1 |
| diversified_banks | 1 | 0/1 | 1/1 | 0/1 | 0/1 |
| financial_data_ratings | 1 | 0/1 | 1/1 | 0/1 | 0/1 |
| financial_exchanges | 2 | 2/2 | 2/2 | 2/2 | 2/2 |
| insurance_brokers | 2 | 0/2 | 1/2 | 0/2 | 0/2 |
| investment_banking_brokerage | 4 | 4/4 | 4/4 | 4/4 | 4/4 |
| life_insurance | 2 | 2/2 | 2/2 | 2/2 | 2/2 |
| mortgage_reits | 2 | 2/2 | 2/2 | 2/2 | 0/2 |
| multi_industry_conglomerate | 1 | 0/1 | 1/1 | 0/1 | 0/1 |
| multi_line_insurance | 2 | 2/2 | 2/2 | 2/2 | 2/2 |
| pc_insurance | 1 | 0/1 | 1/1 | 0/1 | 0/1 |
| regional_banking | 12 | 12/12 | 12/12 | 12/12 | 11/12 |
| reinsurance | 1 | 0/1 | 1/1 | 0/1 | 0/1 |
| retirement_benefits | 1 | 0/1 | 1/1 | 0/1 | 0/1 |

Across all 12 categorical fields, 426 of 516 cells were answered.

## UNKNOWN audit

All four-field UNKNOWNs were recorded as **evidence absent**, not stopped short. The
metric attempted for trajectory and position trend was annual net-income change. The
metric attempted for position and capture was peer-relative revenue growth / operating
scale.

- `company_specific_capture`: ABR, BRK-B, CB, EQH, ERIE, HTH, MCO, PNC, RITM, RNR, STT,
  WTW.
- `moat_trajectory` and `competitive_position_trend`: BRK-B, CB, EQH, ERIE, MCO, PNC,
  RNR, STT, WTW.
- `competitive_position`: ERIE only.

ERIE was left UNKNOWN on all four rank-order fields. WTW retained a supported
`competitive_position=LEADER`, while its trajectory, trend, and capture were left UNKNOWN
because the frozen bucket did not supply a valid peer. This is an industry-object defect,
not evidence that either company is average or weak.

`market_share_direction` is UNKNOWN for all 43 companies, the only field constant across
the batch. No same-market numerator and denominator were available for two comparable
periods. This means evidence absent; it does not mean flat share, and it is a finding rather
than a pass.

## What this does not establish

This is one balanced, partial batch. It does not test E56 P1/P2, does not test E58 arm B,
does not validate the ranking, and does not support promotion. E58 arm B waits for the
complete Financials Phase B population under its own research version or a registered
cross-batch version set. No threshold moves after seeing this batch.

---

# Batch 2 result

Recorded 2026-09-09. Advisory / SHADOW. `promoted` remains false.

## Delivery and frozen receipt

The accepted batch is request `b1d3275420b64cdb92f3`, sample
`E59-financials-phaseb-b2`, research version
`2026-09-09+E59-financials-phaseb-b2`. The September 8 request was rebuilt unchanged on
September 9 to satisfy the same-New-York-day gate. The request ID, fingerprint, roster,
depth, and sample remained the same; only the receipt time moved.

- Frozen blind payload: `b1d3275420b64cdb92f3.pass_a.json`
- Frozen sha256: `fb17272e283275179c85b4fe99965cca8447d83c6f1c02efe41b06d9f03d238c`
- Exact roster: 42/42, no additions, omissions, substitutions, or duplicates
- Search/reads: 252; cache hits: 252
- Distinct cited URLs: 92
- Claims: 541
- Quote-in-excerpt containment failures: 0
- Non-UNKNOWN categoricals: 428/428 claim-backed

Conclusions were absent during Pass A. After the blind file was frozen, release recorded
its exact SHA-256. Six reused industry-object citations were repaired in the final payload
only: five asset-management structural-growth claims used the exact locally rendered SEC
text, and VOYA used the locally verified LIMRA retirement claim. The frozen Pass A file
was not edited and its embedded/final hashes matched.

## Store-first verification and corpus state

The finalizer accepted 42 companies, rejected 0, and stored 541 claims. `verify --apply`
left the accepted request at 541/541 `VERIFIED_LOCAL`.

Corpus state immediately after that verification receipt:

| status | claims |
|---|---:|
| VERIFIED_LOCAL | 6,950 |
| UNVERIFIABLE | 64 |
| SELF_ATTESTED | 58 |
| total | 7,072 |

The checked-claim UNVERIFIABLE rate at this state is 64 / 7,014 = 0.913%.
SELF_ATTESTED claims are reported separately rather than folded into that denominator.

## Batch health before acceptance

`batch_health --version 2026-09-09+E59-financials-phaseb-b2` returned `OK` for 42
companies before the batch was accepted.

| measure | result |
|---|---:|
| batch fill | 0.875 |
| baseline fill | 0.680 |
| pooled delta | +0.195 |
| within-industry delta | +0.068 |

The pooled delta is confounded by sector mix. On shared industries, regional banking
improved from 0.683 to 0.955 (+0.272); asset management/custody, consumer finance, and
investment banking/brokerage remained at 1.000.

## Four-field fill by industry

| industry | n | trajectory | position | position trend | capture |
|---|---:|---:|---:|---:|---:|
| alternative_asset_management | 1 | 0/1 | 1/1 | 0/1 | 0/1 |
| asset_management_custody_banks | 5 | 5/5 | 5/5 | 5/5 | 5/5 |
| consumer_finance | 3 | 3/3 | 3/3 | 3/3 | 3/3 |
| diversified_banks | 2 | 2/2 | 2/2 | 2/2 | 0/2 |
| financial_data_ratings | 1 | 0/1 | 1/1 | 0/1 | 0/1 |
| financial_exchanges | 2 | 2/2 | 2/2 | 2/2 | 2/2 |
| insurance_brokers | 2 | 2/2 | 2/2 | 2/2 | 0/2 |
| investment_banking_brokerage | 4 | 4/4 | 4/4 | 4/4 | 4/4 |
| life_insurance | 2 | 2/2 | 2/2 | 2/2 | 2/2 |
| mortgage_reits | 2 | 2/2 | 2/2 | 2/2 | 2/2 |
| multi_line_insurance | 2 | 2/2 | 2/2 | 2/2 | 2/2 |
| pc_insurance | 1 | 0/1 | 1/1 | 0/1 | 0/1 |
| private_mortgage_insurance | 1 | 0/1 | 1/1 | 0/1 | 0/1 |
| regional_banking | 11 | 11/11 | 11/11 | 11/11 | 9/11 |
| reinsurance | 2 | 2/2 | 2/2 | 2/2 | 2/2 |
| retirement_benefits | 1 | 0/1 | 1/1 | 0/1 | 0/1 |

## UNKNOWN and constant-field audit

All four-field UNKNOWNs were recorded as **evidence absent**, not stopped short.

- `moat_trajectory` and `competitive_position_trend`: ACT, ARES, EIG, MORN, VOYA.
- `company_specific_capture`: ACT, AJG, ARES, BAC, BANR, EIG, GSHD, MORN, OFG, TFC,
  VOYA.
- `competitive_position`: none.

`market_share_direction` is UNKNOWN for all 42 companies and is the only field constant
across the batch. No same-market company numerator and total-market denominator were
available for two comparable periods. This is evidence absent, not flat share, and was
treated as a finding rather than a pass.

No company-to-industry assignment defect was found in the frozen roster. In particular,
ACT resolves to the re-cut `private_mortgage_insurance` object and VOYA resolves to
`retirement_benefits`.

## What batch 2 does not establish

Two balanced batches are still a partial campaign. This result does not test E56 P1/P2,
does not test E58 arm B, does not validate the ranking, and does not support promotion.
E58 arm B remains unopened until the full Financials Phase B version scope exists.
