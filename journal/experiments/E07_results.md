# E07 results — the model bake-off

as_of 2026-08-28T22:34:48.165560+00:00  ·  pre-registered at `journal/experiments/E07_llm_swap_preregistration.md`

3 companies, 1 repeats per prompt, incumbent `qwen2.5:7b`. The evidence pack is built ONCE per company and reused across every arm, so M1 measures the model and not retrieval noise.

## M1-M5

| model | M1 mean spread | M1 unstable | M2 parse fail | M3 unverified | M4 null rate | M5 s/gen | projected 1500 |
|---|---:|---:|---:|---:|---:|---:|---:|
| hf.co/mradermacher/LFM2.5-2.6B-Finance-GGUF:Q4_K_M | n/a | n/a | 77.8% | 0.0% | 0.0% | 13.14 | 16.42 h |

## E12's question: does a better model abstain less?

If the four watched dimensions stop being abstained on, then a quarter of the universe sits under the BQ floor because of the MODEL and **no rubric change is warranted at all** (E12 P1).

| model | network_effects | manufacturing_complexity | data_advantages | economies_of_scale | mean |
|---|---:|---:|---:|---:|---:|

## Registered verdicts

- `hf.co/mradermacher/LFM2.5-2.6B-Finance-GGUF:Q4_K_M`: **INCOMPLETE - not measured: M1_no_worse_consistency, M2_no_worse_parse_rate, M3_no_higher_unverified**
  - `M1_no_worse_consistency`: NOT MEASURED
  - `M2_no_worse_parse_rate`: NOT MEASURED
  - `M3_no_higher_unverified`: NOT MEASURED
  - `M5_under_24h_rescore`: PASS

Nothing is adopted by this harness. A verdict of CANDIDATE means the registered criteria hold on a 15-company sample, not that the model is better - the qual half has never been validated against forward returns, so 'better' is not measurable here.

Nothing is promoted. `promoted` stays false.