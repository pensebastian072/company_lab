# E20 results - forward DCF (2026-08-24)

ADVISORY / SHADOW. A fair value is four assumptions in a trench coat - the
growth rate, where it fades, the terminal rate and the discount rate. Nothing
here is validated against forward returns and `promoted` stays false.

| criterion | measured | bar | verdict |
|---|---|---|---|
| V1 forward/reverse identity | worst growth error 1.95e-07 over 1027 companies | < 1e-3 | PASS |
| V2 coverage | 1027 of 1501 valued | >= 1,000 | PASS |
| V3 bear < base < bull | True | all | PASS |

Median margin of safety **0.0109**; 50% of valued companies screen cheap. 135 fair values are flagged implausible (>10x or <0.1x price) and are excluded from the sector table below.

## Where the growth rate came from

| basis | companies |
|---|---:|
| fcf_cagr_5y | 630 |
| revenue_cagr_3y_proxy | 230 |
| fcf_cagr_3y | 119 |
| sub_industry_median | 48 |

## Why the rest got no fair value

| reason | companies |
|---|---:|
| free cash flow is not a valuation input for this business | 275 |
| trailing free cash flow is zero or negative | 194 |
| no usable growth rate | 5 |

## V4 - margin of safety by sector, reported not scored

If the median company in a sector looks 50% cheap, the model is wrong before
the market is.

| sector | n | median margin of safety |
|---|---:|---:|
| Energy | 44 | 49.6% |
| Consumer Staples | 70 | 25.1% |
| Health Care | 118 | 18.4% |
| Consumer Discretionary | 144 | -1.7% |
| Real Estate | 59 | -5.5% |
| Communication Services | 35 | -13.3% |
| Industrials | 211 | -25.1% |
| Information Technology | 160 | -27.1% |
| Utilities | 5 | -32.0% |
| Materials | 46 | -54.3% |
