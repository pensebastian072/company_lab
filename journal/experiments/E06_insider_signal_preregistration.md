# E06 — is insider buying a signal, and does it beat just holding the index?

Pre-registration written 2026-08-11, **before any insider data was analysed**. The
user's question, in their words: does insider activity work "as a signal and how much
that comes out and how it should be followed" versus "regular S&P 500 holding".

So the benchmark is **excess return over SPY**, not absolute return. Absolute numbers
over 2016-2026 flatter everything.

## Data

`insider_trades` from the LSE vault: 11,317,197 rows, **2003-12 → 2026-08** — deeper than
the existing panel. Fields that matter: `reporting_name`, `reporting_cik`, `company_cik`,
`type_of_owner`, `transaction_type`, `acquisition_or_disposition`,
`securities_transacted`, `securities_owned`, `filing_date`, `transaction_date`,
`form_type`.

### Three data disciplines fixed now, before any result exists

1. **Signal date is `filing_date`, never `transaction_date`.** A Form 4 is filed up to
   two business days after the trade, and in the sample the gap reaches **20 months**
   (AAPL: transaction 2024-01-02, filing 2025-08-12). Using the transaction date would
   let the study act on information nobody had. This is the single easiest way to
   manufacture a fake edge here.
2. **Congressional rows are excluded.** The dataset mixes Form 4 filings with
   senate/house disclosures and the `trade_type` query parameter is silently ignored, so
   filtering is client-side (`lse.insider_trades(corporate_only=True)`).
3. **Mechanical transactions are separated from discretionary ones.** Of 782 AAPL
   corporate rows, every one is `M-Exempt` (option exercise) or `F-InKind` (tax
   withholding). Counting those as conviction would be nonsense. Open-market
   `P-Purchase` and `S-Sale` are the discretionary set.

## Prior, stated before looking

The published literature (Lakonishok & Lee and successors) finds insider **buying**
carries modest predictive power and insider **selling** carries almost none, because
executives sell for liquidity and diversification while they buy for only one reason.
I expect: weak-positive on open-market buying, nothing on selling, and most of the raw
row volume to be mechanical noise. **If selling looks predictive, suspect the
construction before believing it.**

## Signals to test (fixed now, no additions later)

| # | signal | construction |
|---|---|---|
| S1 | open-market buying | any `P-Purchase` by an officer or director in the trailing 90 days, by filing date |
| S2 | conviction buying | S1 restricted to CEO/CFO (`type_of_owner` contains "Chief Executive"/"Chief Financial") |
| S3 | cluster buying | ≥3 distinct insiders buying in the trailing 90 days |
| S4 | buy/sell ratio | dollar value of purchases ÷ dispositions, trailing 180 days |
| S5 | holdings change | change in `securities_owned` for officers, trailing 12 months |
| S6 | selling | any `S-Sale` — tested to confirm it does **not** predict, not to harvest |

## Method

- Monthly grid, joined to the existing point-in-time panel so scores and insider signals
  sit on the same dates.
- Forward returns at **1y and 3y**, and the primary statistic is **excess over SPY**
  from the same date.
- Clustered by **date**, not row: a cross-section on one date is one observation
  (stock_xsect_lab rule 5). No verdict below 40 date-clusters.
- Median beside every mean. Per-year table before any pooled number.
- Trades whose window straddles an implausible price print are dropped (E01 defect).

## Pass criteria

| | passes if |
|---|---|
| S1 | mean excess over SPY > 0 at 1y **and** positive in ≥6 of the years present |
| S2 | S2 excess > S1 excess (conviction should beat generic) |
| S3 | S3 excess > S1 excess (clusters should beat singletons) |
| S6 | **fails to predict** — a positive result here is a red flag for the construction |

**And the question the user actually asked:** does a portfolio formed on the best of
these beat simply holding SPY, after a 5 bps-per-side cost as a fraction of price? That
is reported as a single number with its per-year breakdown.

## The second question: should it feed the score?

If and only if S1/S2/S3 clear, the candidate use is the **Management component**, which
currently has the LLM *guess* at "meaningful ownership". `securities_owned` measures it
directly. Any such change gets its own pre-registration and is tested on the
survivorship-free panel — the E05 fixes are still awaiting that test and this must not
jump the queue.

## Known limits, stated now

- LSE coverage is **current listings only**: ATVI, CELG and AET return nothing. So this
  study inherits the survivorship bias that E04 just removed from the panel. It will be
  stated on every line, and the honest version needs a delisted-inclusive insider source
  that does not currently exist here.
- 5,000 rows per request against 11.3M rows total: bulk pulls need `/export` (5/hour) or
  per-symbol pagination. Cost is bytes, and the cap is 50 GB/month, so this is a
  throughput problem rather than a budget one.
- Nothing here is promoted. `promoted` stays false.

## Outputs

`journal/experiments/E06_results.json` / `.md`, plus `E06_insider_panel.parquet`.
