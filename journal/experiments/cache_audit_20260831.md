# Cache audit after the power fault — 2026-08-31

Read-only sweep of every payload in both lanes while the control lane held the GPU.
Three things it was looking for: corruption from the unclean shutdown, components that
are *partly* dead (the book review only counts a component when it is entirely empty),
and whether every payload in the v2 book was produced under the same regime.

## 1. The power fault corrupted exactly one file

`qual_qwen_struct\0000912242_MG_47475644105b6a07.json` — **MAC (Macerich), MG,
1,771 bytes of NUL**, timestamped 08:23, the instant the box went down. NTFS sized the
file and never flushed its contents.

Scanned every payload and scorecard on both lanes for the same signature:

| directory | files | NUL-corrupt |
|---|---:|---:|
| `qual_qwen_struct` | 2,811 | **1** |
| `qual_lfm25` | 4,416 | 0 |
| `company_lab_v2\data\scorecards` | 1,473 | 0 |
| `e37_snapshot_full\v2_scorecards` | 1,473 | 0 |

Quarantined to `D:\company_lab_data\qual_corrupt_backup\`, not deleted. **MAC's other two
components are intact, so the resume logic counts it done and will skip it** — the control
lane needs one more pass after it finishes to pick MAC back up.

## 2. Partial deadness in the v2 book is negligible, and real

Nothing is missing or fully empty. What is partial:

* **BQ**: 3 of 1,472 — IFF 10/11 (`data_advantages`), NTNX 10/11 (`regulatory_barriers`),
  NABL 9/11 (both).
* **SG**: 15 of 1,472 below 6, of which **14 have all six keys with a null score** — the
  model abstaining — and **one, NWSA, emitted only three of the six keys at all**.

`MG` looks empty in a naive sweep and is not: **both `MG_CEO_ATTRIBUTES` are `data`-sourced
since E26**, so `parse_mg` fills `ceo` only from `llm`-sourced attributes and there are
none. MG contributes `ceo_summary` and evidence. `ceo: {}` is the designed state.

## 3. The willingness gap, measured on the whole cache rather than a sample

Both lanes, same structured regime, same prompts:

| lane | BQ mean filled | BQ complete | SG mean filled | SG complete |
|---|---:|---:|---:|---:|
| v2 / LFM2.5 (1,472) | **11.00 / 11** | 1,469 (99.8%) | 5.99 / 6 | 1,457 (99.0%) |
| control / qwen (940 so far) | 6.64 / 11 | 79 (**8.4%**) | 4.61 / 6 | 161 (17.1%) |

This is E38's finding at cache scale and it is not subtle: under the candidate's exact
format, qwen still leaves a third of BQ unanswered and completes 8.4% of companies against
the candidate's 99.8%. It says nothing about which set of answers is *right* — E40's
containment gap (9.7% vs 0.5%) is the reason not to read this as quality.

## 4. Provenance: ten companies in the v2 book did not come from the lane

AAPL, CAT, HD, JNJ, JPM, LIN, NEE, PG, UNP, XOM were scored by the **06:52 throughput probe
on 2026-08-29**, and the lane reused them from cache. `structured` and `num_predict` are
**not in the cache key** — the scorer's own comment says so, which is why the fields were
added to the payload on 08-30 — so **these ten cannot prove which regime produced them.**

Their observable signature is identical to the lane's:

| component | probe median chars | lane median chars | probe mean filled | lane mean filled | prompt_sha1 |
|---|---:|---:|---:|---:|---|
| SG | 1,980 | 2,146 | 6.00 | 5.98 | same |
| BQ | 2,288 | 2,422 | 11.00 | 11.00 | same |
| MG | 322 | 342 | — | — | same |

Consistent, not proven. **Regenerating those ten costs about three minutes of GPU and
settles it**; queued behind the control lane.
