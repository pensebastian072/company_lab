# MG label correction - MG is measured, and was being reported as judgement

Made 2026-09-01 as V3 P0, before any external-intelligence code was written.
Not an experiment: no hypothesis, no sampling, no verdict. A defect report with a
measured blast radius.

## The defect

`rubric.LLM_COMPONENTS` was `("SG", "BQ", "MG")`. It had been correct once. It stopped
being correct at E25 and nothing followed it:

- **E25** removed the five model-scored CEO attributes from `MG_CEO_ATTRIBUTES`. Both
  survivors carry source `"data"`.
- **E26** cut the CEO block 8 points -> 2, and the component 15 -> 9.

The consequences on disk today, all verified before the change:

- `clab/scoring/mg.py::_LLM_ATTRS` is an **empty tuple** - the comprehension that fills
  it selects `src == "llm"` and no attribute has that source any more.
- Every MG sub-test resolves `source=edgar` (checked on `0000001800_ABT.json`).
- `ComponentScore.is_llm` is `False` for MG.
- **Every LFM2.5 (v2 lane) MG payload carries `ceo = {}`.** The schema generated from
  the rubric has no keys left to ask for. The only thing the model still contributes to
  MG is a display-only `ceo_summary` string used as the block's rationale.
- **The v1 lane is different and it matters.** `D:\company_lab_data\qual` predates E25
  and its MG payloads still carry the five removed attributes - `founder_led`, `tenure`,
  `ownership`, `execution_history`, `industry_expertise` - with real 0-2 scores in them
  (e.g. `0000001750_MG_3a6b1bb2b197a874.json` has `execution_history: 2`). Those scores
  are **inert**: `_ceo_block` reads an attribute only when its source is `"llm"`, and
  none is. But they are still sitting on disk. If a rubric edit ever re-marks one of
  those attributes as `"llm"`, months-old model opinions would silently come back to
  life across the whole v1 book, presented as current. `tests/test_mg_is_measured.py::
  test_stale_ceo_scores_in_old_payloads_are_inert` proves the inertness rather than
  assuming the payloads are clean, because they are not.

So MG's 9 points are measured, and were being counted as model judgement: included in
`qual_only_50`, excluded from `quant_only_50` / `quant_normalized` / `quant_band` /
`quant_coverage`.

The docstrings said `"9.4 of MG's 15 points are measured and 5.6 are model judgement"` -
stale by two experiments and a component resize. `README.md` was worse: it still carried
the pre-E25/E26 100-point table (FE 15, MG 15, EN 5) and the "50 measured / 50 judged"
symmetry that E25 had already broken.

## The fix

One name was doing two jobs. Split into three:

| constant | members | points | meaning |
|---|---|---:|---|
| `JUDGED_COMPONENTS` | SG, BQ | 35 | what the score treats as model judgement |
| `MEASURED_COMPONENTS` | FE, MG, BS, VA, ER, EN | 59 | what the score treats as measured |
| `GENERATED_COMPONENTS` | SG, BQ, MG | - | what the qual pipeline generates a payload for |

MG is in `GENERATED_COMPONENTS` and not in `JUDGED_COMPONENTS` **on purpose**. Dropping
it from the generation list would have silently deleted the `ceo_summary` rationale from
every scorecard - a quiet data loss dressed as a cleanup.

`clab/research/e37_downgrades.py` is **pinned** to `("FE","BS","VA","ER","EN")`, the
definition it actually ran under. Pointing a settled study at the corrected constant
would change numbers already written to `E37_results.json`.

## Blast radius - measured over all 1,501 scorecards

Per-company detail: `journal/experiments/mg_label_correction.parquet`.

| column | before | after |
|---|---|---|
| `quant_only_50` mean | 24.45 / 50 | **29.38 / 59** (+4.93) |
| `quant_normalized` mean | 54.08 | **55.18** (+1.10; range -9.6 to +11.4) |
| `quant_coverage` mean | 0.9335 | **0.9277** |
| `qual_only_50` mean | 21.97 / 44 | **17.04 / 35** |

**`quant_band` changed for 297 of 1,501 companies (19.8%).**

| band | before | after |
|---|---:|---:|
| EXCEPTIONAL | 4 | 2 |
| HIGH_CONVICTION | 55 | 45 |
| INVESTABLE | 174 | 198 |
| WATCHLIST | 305 | 310 |
| WEAK | 322 | 318 |
| REJECT | 512 | 452 |
| INSUFFICIENT_DATA | 129 | 176 |

Largest transitions: WEAK->WATCHLIST 62, REJECT->WEAK 60, WATCHLIST->INVESTABLE 36,
WATCHLIST->WEAK 31, REJECT->INSUFFICIENT_DATA 22.

Two of those movements are worth reading carefully:

1. `quant_coverage` **fell** and `INSUFFICIENT_DATA` **grew 129 -> 176**. Adding MG to
   the measured half exposed MG's own `NO_DATA` points, which the old split hid by
   counting them against the judged half instead. The measured half is not more complete
   than it was; it is more honestly described. 47 companies were being given a
   measured-half band they had not earned the data for.
2. The direction is not uniform - `quant_normalized` moves both ways (-9.6 to +11.4),
   because a company with a strong MG gains and a company with a weak or absent MG loses.
   This is not a rescale.

## What this does NOT change

- **The headline score.** `composite_strict`, `score` / `selection_score`, `band`,
  `coverage`, `sector_neutral_score` and every ranking are untouched. MG's 9 points were
  always in the total; only the measured/judged attribution was wrong.
- **The frozen v2 book.** `D:\company_lab_frozen\v2_lfm25_20260901\` is not backfilled.
  Snapshots cannot be backfilled - it records what was computed on 2026-08-31, wrong
  attribution included.
- **`journal/snapshots/*.parquet`.** Same rule.

## One thing to watch

`clab/research/e40_informative.py` reads `quant_only_50` straight out of
`data/scores.parquet` and correlates moat scores against it. E40's written results were
produced against the 50-point definition. **A re-run of E40 after the next crawl will
use the 59-point definition and will not reproduce `E40_results.json`.** That is a
different measurement, not a contradiction of the old one. If E40 is ever re-run, say
which definition it used.

## Verification

`tests/test_mg_is_measured.py`, plus three pre-existing pins that caught this change
and were updated deliberately: `test_label_drift.py` (94/35/59), `test_composite.py`
(the measured half now includes MG, and its coverage assertion is derived rather than a
literal - that line had already drifted once), `test_export_and_ui.py` (`is_llm` no
longer marks MG in the UI payload).

827 tests pass.
