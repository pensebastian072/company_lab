# London Strategic Edge vault — what it is and what it may be used for

Assessed 2026-08-11 by probing the live API. Key in `secrets/lse.json` (gitignored).
Client: `clab/sources/lse.py`. Everything below was measured, not read off a brochure.

## Access

| | |
|---|---|
| HTTP | `https://api.londonstrategicedge.com/vault` — FastAPI, 16 endpoints, OpenAPI at `/openapi.json`, Swagger at `/docs` |
| WebSocket | `wss://data-ws.londonstrategicedge.com` — live prices, 24 h replay |
| Auth | `x-api-key` header. The base path 404s, which makes it look dead; hit a real endpoint |
| Quota | **50 GB/month**, 16 GB/week, 200 calls/min, **5,000 rows/request**, 2 concurrent, 5 exports/hour, unlimited history depth |
| Used so far | 0.4 MB (0.0008%) |

Endpoints: `/candles /series /catalog /meta /reference /ref/{dataset} /options/chain
/options/flow /options/candles /mbo/contracts /mbo/events /export /export/{id}
/export/{id}/download /usage /health`.

## Dataset inventory

| dataset | rows | span |
|---|---:|---|
| options_flow_1m | 194,392,181 | 2026-01 → 2026-08 |
| options_flow | 119,097,451 | 2026-06 → 2026-08 |
| **insider_trades** | **11,317,197** | **2003-12 → 2026-08** |
| options_chain | 1,173,618 | 2026-06 → 2026-08 |
| dividends | 918,950 | 1970 → 2027 |
| bond_yields | 708,808 | 1990 → 2026 |
| financial_reports | 204,861 | 2013 → 2026 |
| economic_calendar | 137,229 | 2015 → 2026-11 |
| stock_splits | 46,015 | 1970 → 2026 |
| cot | 34,006 | 2015 → 2026 |
| stock_fundamentals / company_profiles | 8,304 each | current snapshot |

Candle classes: stocks, etf, index, futures, fx, crypto, commodity. Timeframes 1s → 1mo.

## Measured limitations — these decide what it may be used for

**1. Closes are split-adjusted but NOT dividend-adjusted.** Against the
dividend-adjusted yfinance store the offset is consistently positive and scales with
yield: NVDA +0.34%, AAPL +0.92%, MSFT +1.68% (median over 10 sessions, max |diff| 2.28%).
Usable standalone. **Never mix into a yfinance series** — a systematic ~1% bias that
correlates with dividend yield is exactly the kind of thing that reads as alpha.

**2. Volume is a partial feed and is unusable.** Ratio to consolidated volume:
AAPL 0.65, MSFT 0.70, **NVDA 0.044**. Same failure mode as Alpaca's IEX feed. Do not
compute dollar volume, liquidity screens or volume z-scores from it.

**3. Current listings only — it does NOT help survivorship.** ATVI, CELG and AET return
zero candles and zero splits. `D:\ohlcv_1m` remains the only delisted price source here.

**4. Candle history starts ~2015-2016**, shallower than the 10-year yfinance store.

**5. `trade_type` is silently ignored as a query parameter** on `/ref/insider_trades`,
and that dataset **mixes Form 4 corporate filings with congressional (senate/house)
disclosures**. Filtering must happen client-side; `lse.insider_trades()` does it.
Counting a senator's purchase as company-insider buying would be a real error.

**6. The advertised insider history does not exist. Measured 2026-08-13.** The catalogue
says `insider_trades` holds 11,317,197 rows spanning 2003-12 → 2026-08. What is actually
reachable, probed over 15 large caps, is **2025-09-02 → 2026-02-12** — five months — and
the feed is **~6 months stale**. AAPL returns zero rows for every year 2015-2023. A
no-symbol query for 2020-06 returns zero, so it is not a per-symbol quirk. FICO returns
nothing at all. Across all 15 symbols there are **4 open-market `P-Purchase` rows**.
This makes the insider study (E06) impossible on this source — no forward-return window
exists — and the honest alternative is SEC Form 4 straight from EDGAR, which is free,
complete back to 2003 and has no row cap. See `journal/experiments/E06_insider_signal_STATUS.md`.

**7. The feed re-ingests the same filing many times, so rows must be deduplicated.**
On AAPL, 4,980 corporate rows collapse to **27 real transactions**; one transaction
appeared **320 times** under 160 distinct `created_at` values, with only `id` and
`created_at` varying. `lse.insider_trades()` now dedupes on
`INSIDER_IDENTITY_FIELDS` by default. Without it a count-based signal is inflated ~160x
and "cluster buying (≥3 insiders)" fires on almost everything — a fabricated signal that
would have looked convincing.

**8. Only `start`/`end` paginate, and they filter the TRANSACTION date.** `offset`,
`page`, `from`/`to`, `date_from`/`date_to`, `year` and `sort` are all silently ignored.
With a hard 5,000-row cap and no paging, history can only be walked in date windows.

## Where it is genuinely worth using

**insider_trades is the prize for company_lab.** 11.3M rows back to 2003 with
`reporting_name`, `reporting_cik`, `company_cik`, `type_of_owner`
("director, officer: Chief Executive Officer"), `securities_transacted`,
`securities_owned`, `transaction_type`, `form_type` and the SEC URL. The Management
component currently has the LLM *guess* at "meaningful ownership" and "execution
history"; `securities_owned` measures the first directly.

One caveat found immediately: of 782 AAPL corporate rows, all are `M-Exempt` (option
exercises, 669) and `F-InKind` (tax withholding, 113) — mechanical, not discretionary.
Open-market `P-Purchase` rows are the real conviction signal and are rare. So the usable
constructions are **holdings level and change in holdings**, plus open-market purchases
where they exist — not raw transaction counts.

**Relevant to other repos on this box, not to company_lab:**

- `options_chain` + `options_flow` (194M rows, 1-minute) — `options_desk` currently pays
  metered CBOE LiveVol points. This is worth a serious look as a parallel or cheaper
  source, subject to the same never-pay-twice caching rule.
- `cot` (2015+) — `qlib_lab` already writes a COT flag; this is a cross-check.
- `bond_yields`, `sovereign_yields`, `credit_indices`, `economic_calendar` —
  `macro_gpu_lab` and the HQ macro brain.
- The WebSocket — no use for company_lab, which is a multi-year tool whose dashboard
  reads published artifacts. Relevant to `options_desk` / `hq-trading-system`.

## Rules for using it here

1. Key stays in `secrets/lse.json`, gitignored, never logged. It was pasted in chat, so
   rotate when convenient.
2. Every response is cached to `D:\company_lab_data\lse\` and replayed free. Quota is by
   bytes and generous, but the box rule stands: never pay for a request twice.
3. Never mix LSE closes into the yfinance series (limitation 1).
4. Never use LSE volume (limitation 2).
5. Filter `insider_trades` to corporate rows client-side (limitation 5).
6. Nothing from this source is promoted or feeds a trade. Advisory only, like everything
   else here.
