# E37 results - the downgrades, and the comparison on common support

n = 1472 comparable companies  ·  score denominator /92 (fixed)  ·  registered at `journal/experiments/E37_downgrades_preregistration.md`

## Headline

| | raw | on common support |
|---|---:|---:|
| mean score delta | +8.79 | +4.245 |
| companies up | 1382 | 1188 |
| companies down | 60 | 196 |
| companies unchanged | 30 | 88 |

Common support = only the sub-tests **both lanes actually scored**. No sub-test can enter one numerator and not the other, so what is left is disagreement.

## Where the headline comes from

| part | mean points | in score units |
|---|---:|---:|
| judged: abstention filled (NULL -> SCORED) | +4.192 | +4.56 |
| judged: disagreement (scored in both) | +3.889 | +4.23 |
| judged: new abstention (SCORED -> NULL) | -0.024 | -0.03 |
| measured half (should be zero) | +0.014 | +0.02 |
| **total** | **+8.071** | **+8.79** |

The four parts are disjoint and sum to the ex-entry points delta. Score units are points/92 x 100 - the same scale the workbook ranks on.

## Registered criteria

**C1** - of 60 downgrades, **34** keep a drop of at least 3 points on common support (56.7%).

**C2** - measured-half movement in **221** of 1472 companies (15.0%), net +21 points. The measured half is supposed to be identical between the lanes.

Why it moved, over every measured transition: **279 vintage**, **31 cohort**. `cohort` = only peer/sector-derived inputs changed, so the *partial universe* moved the score and not one number about the company; `vintage` = a company number changed between the folds; `unexplained` = identical inputs, different points.

| measured sub-test | n moved | net points | kinds | why |
|---|---:|---:|---|---|
| `er_estimate_revisions` | 59 | -2 | disagree 58, lost 1 | vintage 59 |
| `va_pe_vs_own_history` | 46 | -1 | disagree 45, lost 1 | vintage 46 |
| `va_ev_ebitda_vs_peers` | 45 | +14 | disagree 41, lost 4 | cohort 10, vintage 35 |
| `va_peg` | 39 | +11 | disagree 30, fill 3, lost 6 | vintage 39 |
| `va_ev_sales_vs_peers` | 30 | +9 | disagree 22, lost 8 | cohort 6, vintage 24 |
| `va_reverse_dcf` | 25 | -4 | disagree 25 | vintage 25 |
| `fe_roic` | 11 | -3 | disagree 11 | cohort 10, vintage 1 |
| `va_p_fcf` | 9 | +5 | disagree 9 | vintage 9 |
| `fe_fcf_margin` | 8 | -6 | disagree 8 | vintage 8 |
| `va_fwd_pe` | 8 | +6 | disagree 8 | vintage 8 |
| `er_growth_vs_expectation` | 6 | -2 | disagree 6 | vintage 6 |
| `er_earnings_surprise` | 6 | +0 | fill 3, lost 3 | vintage 6 |

**C3** - `SCORED -> NULL`: **41** transitions over 50291 sub-tests the incumbent scored (0.08%), across 33 companies - **23** in the measured half and **18** in the judged half (14 companies).

**C4** - **5875** sub-test disagreements over 25 distinct keys.

| sub-test | component | n | mean delta | share down |
|---|---|---:|---:|---:|
| `bq_moat` | BQ | 1280 | +2.53 | 16% |
| `sg_revenue_growth_sustainable` | SG | 946 | +1.08 | 17% |
| `sg_multiple_independent_drivers` | SG | 901 | +0.91 | 5% |
| `sg_demand_drivers_3_5yr` | SG | 847 | -0.74 | 69% |
| `sg_secular_not_cyclical` | SG | 732 | +0.24 | 38% |
| `sg_capacity_backlog_contracts` | SG | 471 | +1.05 | 8% |
| `sg_tam_expanding` | SG | 382 | +1.51 | 1% |
| `er_estimate_revisions` | ER | 58 | -0.02 | 50% |
| `va_pe_vs_own_history` | VA | 45 | +0.0 | 49% |
| `va_ev_ebitda_vs_peers` | VA | 41 | +0.41 | 29% |
| `va_peg` | VA | 30 | +0.33 | 33% |
| `mg_buyback_discipline` | MG | 30 | +0.47 | 27% |
| `va_reverse_dcf` | VA | 25 | -0.16 | 48% |
| `va_ev_sales_vs_peers` | VA | 22 | +0.45 | 27% |
| `fe_roic` | FE | 11 | -0.27 | 64% |
| `va_p_fcf` | VA | 9 | +0.56 | 22% |
| `fe_fcf_margin` | FE | 8 | -0.75 | 88% |
| `va_fwd_pe` | VA | 8 | +0.75 | 12% |
| `er_growth_vs_expectation` | ER | 6 | -0.33 | 67% |
| `fe_operating_margin` | FE | 6 | -0.67 | 83% |

**C5** - mean common-support delta **+4.245** points (median +4.35).

## The downgrades

| ticker | score | common support | measured | judged disagree | judged lost | coverage |
|---|---:|---:|---:|---:|---:|---:|
| CACI | 68 -> 60 (-8) | -8.7 | +0 | -8 | +0 | +0.000 |
| KLAC | 74 -> 66 (-8) | -7.61 | -2 | -5 | +0 | +0.000 |
| PAYC | 85 -> 78 (-7) | -6.52 | +0 | -6 | +0 | +0.000 |
| NVT | 70 -> 64 (-6) | -5.43 | +0 | -5 | +0 | +0.000 |
| ULS | 79 -> 73 (-6) | -6.52 | +0 | -6 | +0 | +0.000 |
| ANET | 76 -> 71 (-5) | -5.43 | +0 | -5 | +0 | +0.000 |
| BDC | 65 -> 60 (-5) | -5.43 | +0 | -5 | +0 | +0.000 |
| GWRE | 72 -> 67 (-5) | -4.35 | -3 | -1 | +0 | +0.000 |
| QLYS | 76 -> 71 (-5) | -5.43 | +0 | -5 | +0 | +0.000 |
| SYY | 59 -> 54 (-5) | -4.35 | +0 | -4 | +0 | +0.000 |
| COHU | 47 -> 43 (-4) | -1.09 | +0 | -1 | -2 | -0.032 |
| FTNT | 71 -> 67 (-4) | -3.26 | +0 | -3 | +0 | +0.000 |
| NFLX | 74 -> 70 (-4) | -4.35 | -1 | -3 | +0 | +0.000 |
| VMI | 68 -> 64 (-4) | -4.35 | +0 | -4 | +0 | +0.000 |
| ALGM | 54 -> 51 (-3) | -3.26 | +0 | -3 | +0 | +0.000 |
| ATEN | 68 -> 65 (-3) | -3.26 | -3 | +0 | +0 | +0.000 |
| BMI | 68 -> 65 (-3) | -3.26 | +0 | -3 | +0 | +0.000 |
| EVTC | 61 -> 58 (-3) | -3.26 | +0 | -3 | +0 | +0.000 |
| JLL | 80 -> 77 (-3) | -3.26 | +0 | -3 | +0 | +0.000 |
| KBR | 64 -> 61 (-3) | -3.26 | -1 | -2 | +0 | +0.000 |
| LRCX | 71 -> 68 (-3) | -2.17 | +0 | -2 | +0 | +0.000 |
| META | 74 -> 71 (-3) | -6.52 | +0 | -6 | +0 | +0.032 |
| ORCL | 66 -> 63 (-3) | -3.26 | +0 | -3 | +0 | +0.000 |
| PANW | 53 -> 50 (-3) | -4.35 | +0 | -4 | +0 | +0.032 |
| TRIP | 58 -> 55 (-3) | -3.26 | +0 | -3 | +0 | +0.032 |
| AAPL | 72 -> 70 (-2) | -5.43 | +0 | -5 | +0 | +0.043 |
| AMT | 60 -> 58 (-2) | -2.17 | +1 | -3 | +0 | +0.000 |
| BILL | 62 -> 60 (-2) | -4.35 | +0 | -4 | +0 | +0.032 |
| BL | 70 -> 68 (-2) | -1.09 | +0 | -1 | +0 | +0.000 |
| CBOE | 76 -> 74 (-2) | -5.43 | +0 | -5 | +0 | +0.032 |
| CHWY | 68 -> 66 (-2) | -2.17 | +0 | -2 | +0 | +0.000 |
| CRM | 77 -> 75 (-2) | -2.17 | +0 | -2 | +0 | -0.032 |
| FLS | 57 -> 55 (-2) | -1.09 | +0 | -1 | +0 | +0.000 |
| HLNE | 68 -> 66 (-2) | -2.17 | +0 | -2 | +0 | +0.000 |
| NATL | 62 -> 60 (-2) | -2.17 | +0 | -2 | +0 | +0.000 |
| ONTO | 60 -> 58 (-2) | -2.17 | +1 | -3 | +0 | +0.000 |
| RJF | 52 -> 50 (-2) | -6.52 | +0 | -6 | +0 | +0.050 |
| SPGI | 75 -> 73 (-2) | -2.17 | +0 | -2 | +0 | +0.000 |
| ACIW | 71 -> 70 (-1) | -1.09 | -1 | +0 | +0 | +0.000 |
| AEIS | 66 -> 65 (-1) | -1.09 | -1 | +0 | +0 | +0.000 |
| BR | 75 -> 74 (-1) | -1.09 | +0 | -1 | +0 | +0.000 |
| BWXT | 54 -> 53 (-1) | -2.17 | -2 | -2 | +0 | +0.011 |
| COO | 55 -> 54 (-1) | -4.35 | -1 | -3 | +0 | +0.032 |
| ENVA | 71 -> 70 (-1) | -1.09 | +0 | -1 | +0 | +0.000 |
| HUBB | 63 -> 62 (-1) | -4.35 | +0 | -4 | +0 | +0.043 |
| INTU | 83 -> 82 (-1) | -2.17 | +0 | -2 | +0 | +0.032 |
| IRDM | 62 -> 61 (-1) | -1.09 | +0 | -1 | +0 | +0.000 |
| ITRI | 63 -> 62 (-1) | -1.09 | +0 | -1 | -4 | -0.011 |
| ITW | 55 -> 54 (-1) | -6.52 | +0 | -6 | +0 | +0.074 |
| KEYS | 72 -> 71 (-1) | -1.09 | +0 | -1 | +0 | +0.000 |
| LBRT | 38 -> 37 (-1) | -1.09 | +0 | -1 | +0 | +0.000 |
| LMT | 68 -> 67 (-1) | -4.35 | +0 | -4 | +0 | +0.043 |
| MIR | 65 -> 64 (-1) | -1.09 | +0 | -1 | +0 | +0.000 |
| NDAQ | 66 -> 65 (-1) | -1.09 | +0 | -1 | +0 | +0.000 |
| NOW | 68 -> 67 (-1) | -1.09 | +1 | -2 | +0 | +0.000 |
| NWSA | 51 -> 50 (-1) | -1.09 | +0 | -1 | -3 | -0.011 |
| PNC | 47 -> 46 (-1) | -5.43 | +0 | -5 | +0 | +0.051 |
| SCI | 54 -> 53 (-1) | -4.35 | +0 | -4 | +0 | +0.043 |
| SPG | 49 -> 48 (-1) | -4.35 | +0 | -4 | +0 | +0.043 |
| ZTS | 63 -> 62 (-1) | -1.09 | +0 | -1 | +0 | +0.000 |

Point columns are raw framework points (ex-entry); `common support` is in `score` units.

## Reading

**Half of E36's +8.9 is not coverage.** +4.56 of it is the candidate scoring where the incumbent abstained - the artefact E36 named - but +4.23 of it is the candidate awarding **more points on the very sub-tests both lanes answered**. That half survives common support, so it is not the schema making a missing key impossible. It is the candidate being more generous on the same evidence.

**It is one question, mostly.** `bq_moat` moves in 1280 companies at a mean of +2.53 points of a 15-point sub-test, and BQ is 15 of the framework's 94. A single question carries most of the disagreement half.

**The schema did not abolish abstention, it moved it.** The judged half still lost 18 scored sub-tests across 14 companies - not one dimension at a time, but a whole component failing to generate, which is why the worst downgrades are large and lopsided.

**Common support is a selected subset, and selected by the incumbent.** It conditions on qwen having scored the sub-test, and qwen abstained most where the evidence was thinnest. So the disagreement measured here lives on the *easier* items, and there is no reason to assume it is the same size on the ones the incumbent refused.

## What this does not establish

Which lane is *right*. There is no forward-return grader in this repo, so a disagreement is a disagreement and nothing more - a more generous scorer is not a better one. E36's confound is unrepaired: the candidate still ran schema-constrained at 2,500 tokens against an unconstrained 700, so its leniency could be either the model or the budget. **The qwen-structured control is still the only thing that separates them.** `promoted` stays false.
