# E01 — Does the EN entry rule improve timing? (pre-registration)

Written **2026-08-10, before any result was computed.** Nothing below may be edited
once the study has been run; corrections go in an addendum with a date.

## The question

Given a watchlist of companies already chosen on fundamentals, does buying when the
EN (Entry) rule fires beat buying the same company at an arbitrary time?

This is a question about **timing only**. It is not a test of whether the ranking
picks good companies.

## What this study cannot answer, stated up front

1. **The 100 names are chosen with today's knowledge.** They are the current top 100
   by `composite_strict`. Survivors of a decade are over-represented and companies
   that blew up are absent. So a positive result means "the entry rule improved
   timing *within a set of companies that turned out fine*", never "the system finds
   winners".
2. **No LLM input is used anywhere.** SG, BQ and MG are excluded entirely. The model
   read each company's current 10-K and its training data runs past the test window,
   so any historical use of those scores would be circular. EN uses only price and
   filed EPS.
3. **Delisted and removed constituents are absent** from the price store, so index
   turnover is not represented.

## Data and point-in-time discipline

- Prices: `D:\company_lab_data\prices\<SYM>.parquet`, ~10 years of daily closes.
- EPS: EDGAR `EarningsPerShareDiluted`, each quarter applied **from its filing
  date**, never its period end (`fundamentals/pe_history.py`). At date *t* the P/E
  uses only EPS the market had already seen.
- P/E percentile at *t*: rank of P/E(*t*) within the trailing 5 years up to *t*.
  Expanding-window, never the full-sample distribution.
- EMAs at *t*: 20 and 72 period on daily, and on **completed** weekly and monthly
  bars only — the current partial week/month is excluded so no future close leaks in.
- Test window: 2016-01-01 to 2025-08-10. The final 12 months are excluded from
  entry dates so every trade has at least a 1-year forward return.

## Signal definition (fixed now)

EN is recomputed historically with the production rubric
(`clab/scoring/en.py`, `rubric.EN_*`). A **signal** is EN >= 4 of 5.

- Signals are **clustered**: after a signal for a symbol, a 60-trading-day cooldown
  before that symbol can signal again. Consecutive qualifying days are one event,
  not sixty. (Box rule: cluster same-date/adjacent entries or n is fiction.)
- Secondary thresholds reported for context: EN >= 3 and EN == 5.

## Trade construction

- $10,000 at the close of the signal date, held for exactly 1, 3 and 5 years.
- Costs: 5 bps of notional per side, applied as a **fraction of price**, not an
  absolute amount. (Box lesson: absolute costs zeroed every win rate in fx_hermes.)
- No leverage, no stops, no pyramiding, no dividends on either side (so the
  comparison is like-for-like on price return).

## Benchmarks (both required)

1. **Random-date control, same company.** For each signal, 200 random entry dates
   drawn from that company's own eligible history, same holding period. This is the
   comparison that isolates timing: it holds company selection constant.
2. **SPY from the signal date**, same holding period.

## Pre-registered hypotheses and thresholds

| # | Hypothesis | Passes if |
|---|---|---|
| H1 | Signal entries beat random entries in the same names | mean signal return − mean random return > 0 at 1y, AND the signal mean sits above the 60th percentile of the random-draw distribution |
| H2 | The edge is not one lucky year | H1 holds in **at least 6 of the 9** calendar years, reported as a per-year table |
| H3 | Confluence (EN = 5) beats the EMA-only or P/E-only cases | EN 5 mean > EN 3–4 mean at 1y |
| H4 | Signal entries beat SPY | mean excess over SPY > 0 at 1y and 3y |

**Falsification is a real outcome.** If signal ≈ random, the honest conclusion is
that the entry rule does not add timing value within this watchlist, and it should
stay a 5-of-100 tiebreaker rather than a gate. I expect that to be a live
possibility: buying quality companies at almost any time has worked over this
window, which compresses the difference between good and bad timing.

## Reporting rules

- Per-year table before any pooled number.
- n (clustered events) stated everywhere; no result claimed on n < 30.
- Both benchmarks always shown together.
- Nothing here promotes anything. `promoted` stays false; this study does not feed
  the flag file or the dashboard.

## Outputs

- `journal/experiments/E01_entry_timing_results.json`
- `journal/experiments/E01_entry_timing_results.md`
