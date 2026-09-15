# FROZEN — company_lab v2, the LFM2.5 book

> **Copy of `D:\company_lab_frozen\v2_lfm25_20260901\FROZEN.md`**, kept in the repo so
> the frozen set is findable from here. The set itself is 345 MB across 9,613 read-only
> files and lives on D: because C: is the failing spinner. Verify it with
> `sha256sum -c MANIFEST.sha256 --quiet` from that directory.

Frozen **2026-09-01**. This directory is read-only and is the reference copy of the v2
run. Nothing here is regenerated; if you need to change something, copy it out first.

## What this is

The 1,472-company book scored by **LFM2.5-2.6B-Finance (Q4_K_M)** instead of the
incumbent `qwen2.5:7b`. It is a **different book, not a better-scored version of the
incumbent's** — only ~37% of bands agree and 29 of the top 50 survive, so a company's
position here is not comparable to its position in the v1 workbook.

| | |
|---|---|
| companies | 1,472 (0 failed) |
| scoring model | `hf.co/mradermacher/LFM2.5-2.6B-Finance-GGUF:Q4_K_M` |
| median coverage | 0.9787 |
| `data_through` | 2026-08-02 |
| book generated | 2026-08-31T12:22:54Z |
| framework | 94 points |

## Contents

```
book/company_lab_v2_FINAL_1472.xlsx   the workbook, 12 sheets
scores.parquet                        the scores the workbook was built from
scorecards/                           5,193 files - per-company detail
qual_lfm25/                           4,416 LLM payloads - the expensive half
MANIFEST.sha256                       9,611 files hashed
```

Verify at any time from this directory:

```
sha256sum -c MANIFEST.sha256 --quiet
```

## Scoring breakdown as frozen

| component | max | mean | % of max | coverage | half |
|---|---:|---:|---:|---:|---|
| SG Structural Growth | 20 | 16.87 | 84.4% | 0.998 | judged |
| BQ Business Quality & Moat | 15 | 8.25 | 55.0% | 1.000 | judged |
| MG Management & Capital Alloc | 9 | 4.94 | 54.9% | 0.901 | measured |
| FE Financial Engine | 18 | 7.58 | 42.1% | 0.934 | measured |
| BS Balance Sheet & Survivability | 10 | 5.74 | 57.4% | 0.922 | measured |
| VA Valuation | 15 | 7.43 | 49.5% | 0.915 | measured |
| ER Expectations vs Reality | 5 | 2.83 | 56.7% | 0.987 | measured |
| EN Entry Opportunity | 2 | 0.88 | 44.0% | 0.969 | measured |
| **total** | **94** | **54.52** | **58.0%** | | |

Judged half **71.8%** of max, measured half **49.8%**.

## Read this before building on it

1. **The Rank sheet is NOT sorted.** It is in ascending CIK order. Sort on
   `composite_strict` descending, or the top of the sheet means nothing.
2. **`ticker` is a `=HYPERLINK(...)` formula with no cached value.** Excel renders it;
   `pandas.read_excel` returns `None` for all 1,472 rows. Read tickers from
   `scores.parquet`, or parse the formula string with `openpyxl(data_only=False)`.
3. **This book is not validated.** `validated_against_forward_returns: NO`,
   `promoted` is false. There is no forward-return grader in the repo. E05 measured the
   *incumbent* ranking's top decile **losing to SPY** on a survivorship-free holdout, and
   nothing has re-tested that for this book.
4. **The model is more willing, not proven better** (E38, `journal/experiments/`).
   Of the gap against the incumbent, **92% is the model and 9% the format**. But E40
   measured this model citing text absent from the filing **9.7%** of the time against
   qwen's **0.5%**.
5. **SG is the component to distrust first.** It averages **84.4% of max at 99.8%
   coverage** — eight perfect 20/20s in the top fifteen. A 20-point component almost
   nobody loses points on separates almost nobody; that is E32's "weight without
   information" test, and SG is now the biggest candidate for it in the book.
6. **The sector bet did not go away.** Median runs Information Technology 61 to Real
   Estate 44, and Utilities produced **0 investable names out of 59**. Compare across
   sectors with `sector_neutral_score`, never `score`.
