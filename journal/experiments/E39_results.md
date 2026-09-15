# E39 results - the moat dimensions with a score and no reason

2185 unjustified dimension scores over 10178 scored (21.5%), affecting 395 companies. Registered at `journal/experiments/E39_unjustified_dimensions_preregistration.md`. **Nothing is rescored here.**

## P1 - do unjustified dimensions score differently?

| | mean 0-5 |
|---|---:|
| with a rationale | 2.607 |
| with none | 1.712 |
| **gap** | **-0.895** |
| gap within the same company (340 companies) | **-1.536** |

## P2 / P4 - what dropping them would do

* **271** companies fall below the 6-of-11 floor and lose `bq_moat` entirely.
* Of the rest: **89 up, 1 down, 14 unchanged**, mean `bq_moat` delta **+1.346** of 15 (median +1.0).
* **249** companies change band (raw, before hysteresis): REJECT -> INSUFFICIENT_DATA x111, WEAK -> INSUFFICIENT_DATA x67, WATCHLIST -> INSUFFICIENT_DATA x41, WATCHLIST -> WEAK x9, REJECT -> WEAK x6, WEAK -> REJECT x4, INVESTABLE -> INSUFFICIENT_DATA x4, WEAK -> WATCHLIST x3

## Most affected dimensions

| dimension | unjustified scores |
|---|---:|
| `switching_costs` | 332 |
| `technological_advantage` | 275 |
| `customer_relationships` | 213 |
| `data_advantages` | 194 |
| `brand` | 193 |
| `intellectual_property` | 187 |
| `regulatory_barriers` | 181 |
| `manufacturing_complexity` | 176 |
| `distribution` | 167 |
| `network_effects` | 151 |
| `economies_of_scale` | 116 |

## Reading

**Silence is a low score.** A dimension with no rationale scores 1.536 lower than a justified one **in the same company**, on a 0-5 scale - a bigger gap than the between-company one, so it is not that unexplained dimensions cluster in badly-read filings. The model scored low and did not say why.

**And that is exactly why enforcement is not a cheap win.** 271 of 395 affected companies fall below the 6-of-11 floor - **their moat score exists only because unexplained dimensions make up the quorum.** Dropping them does not tighten the ranking, it deletes moat scoring for 271 companies and pushes 223 of them out of banding entirely. The registered prediction for this was **< 60**, and it is wrong by a factor of four.

**The companies that survive get *better*, not worse** - mean `bq_moat` +1.346 of 15, 89 up against 1 down - because removing a silent low score raises a mean. Requiring a reason is not a rigour dial: it is an abstention dial at one end and a generosity dial at the other.

**So the defect is worth fixing at the source, not at the scorer.** A regenerated or repaired dimension that comes back with a reason keeps the quorum; withholding on the current payloads throws the company out. That points at the E15/E17 repair path, not at a rubric change.

## What this does not decide

Whether to enforce it. Requiring a rationale is a framework change, it is discontinuous at a date in the middle of the snapshot series the forward-return grader needs (hard rule 9), and it would delete moat scoring for the companies above the floor only by luck. That call is the user's, and it should be made against these numbers rather than against the word 'rigour'.
