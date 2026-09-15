# E48 external rank-order result

Pre-registered before the Energy deltas were computed. This is a rank-behavior diagnostic, not a return test.

Primary Energy universe: **71 of 71**. Status: **COMPLETE_PRIMARY**.

Headline: **EVIDENCE_AVAILABILITY_ORDER_CHANGE**.

| transition | Spearman | Kendall | median move | p90 move | top-decile overlap | result |
|---|---:|---:|---:|---:|---:|---|
| A_local to B_evidence | 0.7889 | 0.6451 | 7.0 | 22 | 87.5% | ORDER_CHANGING |
| B_evidence to C_full | 0.9173 | 0.7956 | 3.0 | 14 | 62.5% | ORDER_PRESERVING |
| B_evidence to C_moat_no_flags | 0.9844 | 0.9412 | 0.0 | 7 | 87.5% | ORDER_PRESERVING |
| C_moat_no_flags to C_full | 0.9380 | 0.8366 | 2.0 | 12 | 75.0% | ORDER_PRESERVING |

## Evidence-driven moves

| ticker | from | to | places up |
|---|---:|---:|---:|
| VNOM | 71 | 39 | +32 |
| WHD | 61 | 29 | +32 |
| AESI | 58 | 28 | +30 |
| BKR | 2 | 30 | -28 |
| SLB | 10 | 35 | -25 |
| LBRT | 45 | 21 | +24 |
| LEU | 46 | 22 | +24 |
| DVN | 20 | 42 | -22 |
| HAL | 15 | 37 | -22 |
| PARR | 11 | 32 | -21 |
| RES | 23 | 43 | -20 |
| WMB | 47 | 27 | +20 |
| CRC | 28 | 46 | -18 |
| HLX | 34 | 16 | +18 |
| MTDR | 31 | 49 | -18 |
| MUR | 32 | 50 | -18 |
| NOV | 33 | 15 | +18 |
| RRC | 18 | 36 | -18 |
| AR | 30 | 47 | -17 |
| AROC | 35 | 18 | +17 |
| CVI | 42 | 26 | +16 |
| SEI | 37 | 52 | -15 |
| WFRD | 24 | 38 | -14 |
| CNR | 41 | 54 | -13 |
| KNTK | 38 | 25 | +13 |
| REX | 40 | 53 | -13 |
| DINO | 29 | 19 | +10 |
| VAL | 70 | 60 | +10 |
| CVX | 43 | 34 | +9 |
| TRGP | 26 | 17 | +9 |
| OVV | 49 | 57 | -8 |
| PBF | 22 | 14 | +8 |
| COP | 52 | 45 | +7 |
| GPOR | 55 | 62 | -7 |
| NOG | 48 | 55 | -7 |
| VTOL | 54 | 61 | -7 |
| WKC | 51 | 58 | -7 |
| BTU | 57 | 63 | -6 |
| EOG | 62 | 56 | +6 |
| KGS | 17 | 11 | +6 |
| PTEN | 50 | 44 | +6 |
| XOM | 25 | 31 | -6 |
| CHRD | 59 | 64 | -5 |
| CRK | 60 | 65 | -5 |
| FANG | 64 | 59 | +5 |
| PR | 53 | 48 | +5 |
| PSX | 56 | 51 | +5 |

## Moat-trajectory moves

| ticker | from | to | places up |
|---|---:|---:|---:|
| HLX | 16 | 27 | -11 |
| NOV | 15 | 26 | -11 |
| LBRT | 21 | 31 | -10 |
| DINO | 19 | 28 | -9 |
| OKE | 20 | 29 | -9 |
| AESI | 28 | 35 | -7 |
| PARR | 32 | 25 | +7 |
| XOM | 31 | 24 | +7 |
| LEU | 22 | 16 | +6 |
| WHD | 29 | 23 | +6 |
| AM | 23 | 18 | +5 |
| AROC | 18 | 13 | +5 |
| CVI | 26 | 21 | +5 |
| KNTK | 25 | 20 | +5 |
| OXY | 24 | 19 | +5 |
| WMB | 27 | 22 | +5 |

## Flag-driven moves

| ticker | from | to | places up |
|---|---:|---:|---:|
| MPC | 11 | 36 | -25 |
| RES | 43 | 65 | -22 |
| SEI | 52 | 71 | -19 |
| PARR | 25 | 40 | -15 |
| PBF | 15 | 30 | -15 |
| SLB | 36 | 50 | -14 |
| CVI | 21 | 33 | -12 |
| KMI | 30 | 18 | +12 |
| OKE | 29 | 41 | -12 |
| VLO | 12 | 24 | -12 |
| BKR | 33 | 22 | +11 |
| CVX | 32 | 21 | +11 |
| OII | 3 | 14 | -11 |
| INVX | 2 | 10 | -8 |
| VNOM | 37 | 29 | +8 |
| HAL | 38 | 31 | +7 |
| KNTK | 20 | 13 | +7 |
| WHD | 23 | 16 | +7 |
| XOM | 24 | 17 | +7 |
| AROC | 13 | 8 | +5 |
| INSW | 14 | 9 | +5 |
| KGS | 10 | 15 | -5 |
| LEU | 16 | 11 | +5 |
| TRGP | 17 | 12 | +5 |
| WFRD | 39 | 34 | +5 |

## Neutral peer basis

Decision: **use `industry_id` when n >= 4, then GICS `sub_industry` when n >= 5, then sector**.
This is not yet implemented in production. It changes the economic comparison set but does not establish better forward returns.

In Utilities, 56 of 59 companies change peer key under that hierarchy.
The full ticker-level old/new mapping is in the JSON result.

## Guardrail

`promoted` remains false. No portfolio or predictive claim follows from this diagnostic.
