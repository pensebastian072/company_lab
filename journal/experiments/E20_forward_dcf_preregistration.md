# E20 - a forward DCF for every company that can carry one

Pre-registered 2026-08-19 for execution 2026-08-20, before any DCF code is written.
The user's framing: *"everything is the DCF model"* - a fair value per share to sit beside
the score, rather than a score with no anchor to price.

## What already exists, and must be reused

`clab/scoring/reverse_dcf.py` is 80% of this and it is **not** being rewritten:

* `wacc_for(beta, risk_free)` - CAPM, clamped to a floor and ceiling, every input stamped
  `assumed` when defaulted;
* `_growth_path(g, years)` - growth held flat to `DCF_FADE_START_YEAR`, then faded
  linearly to `DCF_TERMINAL_GROWTH`;
* `enterprise_value(fcf0, g, wacc, years)` - the 10-year PV plus terminal value, already
  guarding `wacc <= terminal growth`.

The reverse DCF asks *what growth does today's price require*. E20 asks the forward
question with the same machinery: **pick g from evidence, compute EV, subtract net debt,
divide by shares, compare to price.** The two must agree by construction - a company whose
forward fair value equals its price must have an implied growth equal to its assumed g,
and that is the first test written.

## Input availability, measured today on 1,500 companies

| input | present |
|---|---:|
| price | 1,500 |
| market cap | 1,461 |
| revenue CAGR 3y | 1,463 |
| net debt | 1,398 |
| trailing FCF | 1,396 |
| `analyst_growth_3y` | **0** |

* **1,242 companies have positive trailing FCF** (83%).
* **1,114 have everything a per-share DCF needs** - positive FCF, market cap, net debt and
  price. That is the honest denominator for this study, not 1,500.
* **154 have negative or zero FCF**, concentrated in Utilities (39), Industrials (24) and
  Health Care (18). A DCF started from a negative FCF is arithmetic, not valuation.
* `analyst_growth_3y` is **empty for all 1,500 and is mislabelled** - it holds yfinance's
  +5y estimate, and it holds nothing at all right now. It is NOT an input to E20.

## Design

**Growth `g`, in a fixed preference order, with the choice recorded per company:**

1. 5-year FCF CAGR, when the series has 5 clean annual points and the result is inside
   `[-10%, +25%]`;
2. else 3-year revenue CAGR haircut by the FCF-to-revenue trend;
3. else the sub-industry median of (1);
4. else **no DCF** - `NO_DATA`, never a default growth rate. A fabricated g is the single
   easiest way to make this whole exercise worthless.

**Fair value per share** = `(enterprise_value(fcf0, g, wacc) - net_debt) / diluted shares`.

**Every company gets a three-point strip, not a point estimate**: bear / base / bull from
`g - 5pp / g / g + 5pp`, plus the existing WACC +/-2% sensitivity. A single fair value
carries far more apparent authority than it deserves - the same reason the reverse DCF
already ships a sensitivity strip.

**Margin of safety** = `(fair_value - price) / fair_value`, reported as a number, and
**not** wired into the composite in this experiment. Scoring on it is a separate decision
and needs its own registration.

## Refusals, fixed now

* Negative or zero trailing FCF -> **no DCF**. Stated, not defaulted, not floored at zero.
* Financials (banks, insurers) -> **no FCF-based DCF**. Free cash flow is not meaningful
  when borrowing is the raw material; 254 Financials and the mortgage REITs are excluded
  and the reason is written on the row. A residual-income or dividend model is the right
  instrument for them and is out of scope here.
* `wacc <= terminal growth` -> refuse, do not clamp the terminal spread to make a number
  appear.
* A fair value more than **10x** or less than **0.1x** the current price is reported with
  a `implausible` flag rather than silently ranked.

## Pass criteria

| | passes if |
|---|---|
| **V1** | The forward DCF and the existing reverse DCF **reconcile**: feeding a company's own implied growth back through `enterprise_value` reproduces its enterprise value to within 1%. This is an arithmetic identity - a failure means one of the two is wrong. |
| **V2** | Coverage: a fair value is produced for **>= 1,000** companies, and every refusal carries a named reason from the list above. |
| **V3** | The bear-base-bull strip is **monotone** for every company, and the base case sits between them. |
| **V4** | Sanity, reported not scored: the distribution of margin-of-safety by sector. If the median company in the universe shows a +50% margin of safety, the model is wrong, not the market. |

## What this cannot establish

**Nothing about whether the DCF predicts returns.** It is a valuation anchor computed from
assumptions - a growth rate, a fade, a terminal growth, a discount rate - and changing any
one of them moves the answer materially. There is no forward-return grader, `promoted`
stays false, and a large margin of safety is a hypothesis, not a signal.

The honest use is the one the reverse DCF already serves: **a cross-check on the story**.
If the score says quality and the DCF says the price already assumes 20% growth forever,
that disagreement is the useful output.

## Prediction, stated before running

A fair value lands for **1,050-1,150** companies. The median margin of safety is
**negative** (the market is not systematically 30% wrong), with the widest positive tails
in Energy and Consumer Discretionary cyclicals where trailing FCF is at a cycle high - the
same trap E03 R5 already found in the score itself, arriving here through the same door.
