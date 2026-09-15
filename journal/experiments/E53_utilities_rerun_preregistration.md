# E53 - does the symmetric prompt hold on a harder sector?

Registered 2026-09-06, before the re-run is handed to Codex and before any result is seen.

## Why this is not just cleanup

E51 restored all four rank-order fields for all 47 Communication Services companies -
0/47 to 47/47, external-score sd 2.90 to 13.85, zero demotions, zero unverifiable claims.
That is one sector, and Communication Services is a heterogeneous one: GOOGL, NFLX, TMUS
and a rural telco have obviously different competitive positions and the evidence is
public.

**Utilities is the harder case and the better test.** Its companies genuinely are alike -
same regulator, same technology, same product - which is why E47's peer-relative risk
fields honestly returned MODERATE for nearly all 59. If the symmetric prompt works here
too, the E49 decline was the incentive. If the fields stay empty here while they filled in
Communication Services, then part of what looked like a prompt defect was real sector
homogeneity, and the two causes are separable for the first time.

Either result is worth the 59 companies.

## The arms

| arm | what it is | status |
|---|---|---|
| **A** | `2026-09-05+E47-utilities`, 59 companies | frozen |
| **B** | same 59, request `f92abdf0887e91cd072d`, symmetric rules block | to run |

Arm A's measured baseline:

```
rank-order fill              8.5%      all-12 fill  66.0%
external-score sd            4.80

moat_trajectory              0/59      competitive_position_trend   0/59
competitive_position        20/59      company_specific_capture     0/59
market_share_direction       0/59      <- NOT_APPLICABLE by construction
```

Identical roster, depth, `require_citation`, vocabularies and two-pass rule. The 7
Utilities industry objects already exist and are NOT rebuilt. The only change is
`docs/CODEX_STANDARD_RULES.md` in place of the abstention-praise language.

## Registered predictions

| # | criterion | prediction |
|---|---|---|
| 1 | arm B rank-order fill | **>= 50%** (arm A: 8.5%; E51 reached 100% on an easier sector) |
| 2 | arm B external-score sd | **> 7.0** (arm A: 4.80) |
| 3 | demotions in arm B | **<= 5% of assertions** |
| 4 | UNVERIFIABLE claims | **0** |
| 5 | `market_share_direction` non-UNKNOWN | **still 0 of 59** |

**Prediction 5 is the guard and it is the reason this is registered rather than just
run.** Telling a researcher that abstention is an error creates a real risk in the
opposite direction: pressure to answer a field that is structurally meaningless. A
regulated utility has no contestable retail share, `applicability.py` says so with a
written definitional argument, and the finalizer must not start receiving GAINING/LOSING
for franchise monopolies. If prediction 5 fails, the symmetric block is over-corrected and
needs an explicit carve-out for NOT_APPLICABLE fields before it is used anywhere else.

Prediction 1 is deliberately set below E51's 100%. Utilities is more homogeneous and some
of these fields may honestly be harder here; demanding a repeat of 100% would make an
honest partial result look like a failure.

## What each outcome licenses

- **All five hold.** The E49 decline was the incentive, confirmed on two sectors of
  different character. Resume buying sectors with `batch_health` watching, and re-run
  E52's v1-versus-v2 comparison on a fully repaired book.
- **1 and 2 fail, 3 to 5 hold.** The prompt was not the whole story and Utilities is
  genuinely homogeneous. That is a real finding about the sector rather than the process,
  and it means some sectors cannot support this layer - which changes what is worth
  buying, not how it is bought.
- **5 fails.** Stop. The symmetric block is over-corrected, and a fix that trades one
  systematic error for its mirror image is not a fix. Carve out NOT_APPLICABLE fields and
  re-run before it touches another sector.
- **3 fails.** Coverage bought with citation discipline. Report both numbers as a trade,
  never as a win, and put the choice to the user.

## Cost

59 companies, no new industry objects, and `market_share_direction`, company size and
growth-versus-peers all removed from research. E47 cost 266 searches with the objects to
build. Budget 250-350.

## Out of scope

Predicts nothing about returns. No promotion state changes. The ranking remains
unvalidated - E05's top decile ran a -7.6% median 3-year excess against SPY on a
survivorship-free holdout, and 95.6% of the measured half's power is sector selection.
`promoted` stays false, status stays SHADOW.
