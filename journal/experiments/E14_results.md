# E14 results — sector-neutral ranking vs raw

as_of 2026-08-17T16:49:47.147475+00:00  ·  pre-registered at `journal/experiments/E14_sector_neutral_preregistration.md`

Panel `C:\Users\<your-user>\company_lab\journal\experiments\E14_panel_v2.parquet` — 131,037 rows after coverage, 1449 symbols. Percentiles computed within each month, never pooled. n_trials=6.

| variant | ann. net | ex-2020 | median mo | share + | sign p | breakeven | sectors held | largest sector |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| raw_top20 | -0.5% | -0.9% | -0.0% | 49.2% | 0.93 | -13 bps | 7.15 | 33.3% |
| raw_top40 | 0.1% | 0.2% | 0.2% | 51.7% | 0.78 | 49 bps | 8.48 | 30.0% |
| raw_top80 | 0.4% | 0.3% | 0.2% | 54.2% | 0.41 | 77 bps | 9.62 | 27.8% |
| neutral_top20 | 2.2% | 1.2% | 0.1% | 51.7% | 0.78 | 261 bps | 8.07 | 23.5% |
| neutral_top40 | 1.3% | 1.1% | 0.2% | 55.0% | 0.32 | 169 bps | 9.66 | 21.5% |
| neutral_top80 | 1.2% | 1.1% | 0.1% | 51.7% | 0.78 | 156 bps | 10.95 | 20.2% |

## Gate

- raw_top20: DSR -1.4574, PBO 0.4484, passes=False
- raw_top40: DSR -1.2714, PBO 0.4802, passes=False
- raw_top80: DSR -1.1783, PBO 0.4405, passes=False
- neutral_top20: DSR -0.5073, PBO 0.1825, passes=False
- neutral_top40: DSR -0.8263, PBO 0.3135, passes=False
- neutral_top80: DSR -0.8464, PBO 0.3294, passes=False

## Pre-registered criteria

- `P1_neutral_top20_positive_ex2020`: **PASS**
- `P2_beats_raw_top20`: **PASS**
- `P3_survives_the_diversification_control`: **PASS**
- `P4_median_month_above_zero`: **PASS**
- `P5_deflated_sharpe_and_pbo`: **FAIL**

**Registered verdict: PASS** (P2 AND P3 both required) · **Status: SHADOW**

Nothing is promoted. `promoted` stays false.