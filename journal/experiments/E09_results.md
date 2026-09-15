# E09 — LSE `financial_reports` vs SEC EDGAR

as_of 2026-08-13T14:31:24.959667+00:00

EDGAR is the incumbent and the bar is high: as-first-filed, restatement-aware, back to ~2009, with the exact us-gaap tag on every number. LSE is adopted only if it beats that or fills a gap EDGAR genuinely leaves.


## Coverage and structure

| symbol | rows | earliest | latest | periods | restated periods | traceability |
|---|---:|---|---|---|---:|---|
| AAPL | 114 | 2018-09-29 | 2026-06-27 | FY,Q1,Q2,Q3,Q4 | 0 | **none** |
| JPM | 110 | 2017-12-31 | 2026-06-30 | FY,Q1,Q2,Q3,Q4 | 0 | **none** |
| XOM | 120 | 2017-12-31 | 2026-06-30 | FY,Q1,Q2,Q3,Q4 | 0 | **none** |
| NKE | 114 | 2018-05-31 | 2026-05-31 | FY,Q1,Q2,Q3,Q4 | 0 | **none** |
| COST | 108 | 2018-08-31 | 2026-05-10 | FY,Q1,Q2,Q3,Q4 | 0 | **none** |

## Do the numbers agree? (annual periods present in both)

| symbol | periods | revenue | operatingIncome | grossProfit | netIncome | freeCashFlow | operatingCashFlow |
|---|---:|---:|---:|---:|---:|---:|---:|
| AAPL | 8 | 100% (8) | 100% (8) | 100% (8) | 100% (8) | 100% (8) | 100% (8) |
| JPM | 9 | 0% (8) | — | — | 100% (9) | — | 89% (9) |
| XOM | 9 | 56% (9) | — | — | 78% (9) | 100% (9) | 100% (9) |
| NKE | 9 | 100% (9) | — | 100% (9) | 100% (9) | 100% (9) | 100% (9) |
| COST | 8 | 100% (8) | 100% (8) | 0% (1) | 100% (8) | 100% (8) | 100% (8) |

### Largest disagreements

- **JPM revenue 2018-12-31**: EDGAR 109,029,000,000 vs LSE 129,824,000,000 (16.0%)
- **JPM revenue 2019-12-31**: EDGAR 115,627,000,000 vs LSE 142,515,000,000 (18.9%)
- **JPM revenue 2020-12-31**: EDGAR 119,543,000,000 vs LSE 129,843,000,000 (7.9%)
- **JPM revenue 2021-12-31**: EDGAR 121,649,000,000 vs LSE 127,238,000,000 (4.4%)
- **JPM operatingCashFlow 2025-12-31**: EDGAR -147,782,000,000 vs LSE 100,867,000,000 (168.2%)
- **XOM revenue 2022-12-31**: EDGAR 413,680,000,000 vs LSE 398,675,000,000 (3.6%)
- **XOM revenue 2023-12-31**: EDGAR 344,582,000,000 vs LSE 334,697,000,000 (2.9%)
- **XOM revenue 2024-12-31**: EDGAR 349,585,000,000 vs LSE 339,247,000,000 (3.0%)
- **XOM revenue 2025-12-31**: EDGAR 332,238,000,000 vs LSE 323,905,000,000 (2.5%)
- **XOM netIncome 2021-12-31**: EDGAR 23,040,000,000 vs LSE 23,598,000,000 (2.4%)
- **XOM netIncome 2022-12-31**: EDGAR 55,740,000,000 vs LSE 57,577,000,000 (3.2%)
- **COST grossProfit 2019-09-01**: EDGAR 16,465,000,000 vs LSE 19,817,000,000 (16.9%)

**Verdict — EDGAR stays the source of record.**

- **Depth**: earliest period seen 2017-12-31, against EDGAR's ~2009. The catalogue advertises 2013; the filers probed start 2017-2018.
- **Point-in-time**: 0 restated periods retained across all five filers. **Every period appears exactly once**, so this is a latest-view source. It cannot support the `as_first_filed` discipline the panel depends on — and grading a model on restated numbers is look-ahead bias.
- **Traceability**: **none**. No accession, no URL, no us-gaap tag on any number, so a figure cannot be traced back to the filing it came from. EDGAR carries the tag and the accession on every fact.
- **Agreement**: exact on the clean filers (AAPL, NKE), but it diverges on JPM, XOM, COST — and those are the hard cases the set was chosen for. JPM revenue disagrees by 4-19% every year (a bank total-vs-net revenue definition), JPM 2025 operating cash flow has the **opposite sign** (EDGAR −147.8bn, LSE +100.9bn), and XOM revenue runs 2.5-3.6% apart every year (excise taxes in or out). None of these are errors exactly; they are a different chart of accounts, which is precisely why a source without a tag per number cannot be reconciled.

The one gap LSE could still fill is **non-US filers**, which have no companyfacts at all. That is worth revisiting only if the universe expands beyond US listings.
