# E03 addendum — what I found when I asked my own questions

Written after seeing results. Pre-registration unedited.

## The big one: the score is substantially a sector bet (R1)

| | mean IC vs 1y return |
|---|---:|
| pooled | **+0.013** |
| within sector (both score and return demeaned by sector) | **−0.013** |

**95.6% of the pooled IC disappears once sector is removed**, and 18.1% of the score's
variance is explained by sector alone. Mean score by sector:

| Financials | InfoTech | Cons Disc | Health | Comm | Indust | Materials | Staples | Energy | REITs | Utilities |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 62.6% | 62.4% | 61.5% | 61.4% | 59.9% | 59.9% | 56.0% | 55.1% | 53.4% | 50.6% | **41.2%** |

A utility is 21 points behind a bank before anything about the business is considered.
That is not a judgement about utilities — it is the arithmetic of scoring an 8%
operating margin against a threshold table built for software. **What little ranking
power the score has comes from choosing sectors, not companies.**

This is the most fixable thing found in three studies. The absolute thresholds in
`rubric.py` (operating margin ≥25% = full marks, ROIC ≥20% = full marks) are
sector-blind. Scoring those metrics as a **percentile within sector** would make the
score answer "is this a good utility" rather than "is this a software company".

## R3 is the most encouraging result in the whole programme

| horizon | mean IC | months positive |
|---|---:|---:|
| 1 year | +0.013 | 55.6% |
| **3 years** | **+0.063** | **84.5%** |

At a three-year horizon the score ranks companies correctly in **84.5% of months**.
Every earlier test used one year and was measuring the wrong thing — the framework is
built for multi-year compounding and it needs to be judged that way.

One honest wrinkle: the 3-year *decile spread* is −22.8% even though the rank IC is
+0.063. Both are true. The rank correlation is positive while the mean spread is
negative because the bottom decile contains the 10x recoveries (CVNA and friends),
which move a mean and not a rank. **The score orders the middle of the distribution
correctly and gets run over by the tails.** That is worth knowing precisely.

## R5 confirms the cyclical defect rigorously

| population | IC 1y | IC 3y |
|---|---:|---:|
| cyclical (semis, hardware, energy, metals, autos) | **−0.059** | **−0.038** |
| everything else | +0.016 | +0.065 |

Cyclicals by score quintile, 3-year forward: bottom quintile +158.9%, top quintile
+93.3%. **Top minus bottom = −65.6%.** Inside cyclicals a high score reliably preceded
*worse* outcomes, which is exactly the LITE/WDC/STX/MU pattern from E02 measured across
4,518 observations rather than five anecdotes.

TTM earnings are the wrong denominator for a cyclical, and the framework currently has
no idea it is looking at one.

## R4 is a usability problem nobody had raised

- median month-to-month move in the score: 2.6 points, p90 10.0
- **band changes in 27.2% of months**
- **median time in a band before leaving: 2 months**

A company's label changes every two months. That is unusable for a multi-year holding
framework and it undermines the dashboard: the answer you get depends on the week you
look. Needs hysteresis — the same two-consecutive-readings rule already designed for
the thesis tri-state.

## R2 — trajectory does not beat level, but the 2x2 is revealing

Change IC −0.016 vs level +0.002, so no case for a momentum-of-fundamentals dimension.
But:

| cell | n | mean 1y |
|---|---:|---:|
| low level + improving | 7,445 | **+21.5%** |
| high level + deteriorating | 8,038 | +18.5% |
| low level + deteriorating | 14,644 | +18.3% |
| high level + improving | 14,849 | **+16.0%** |

The *worst* cell is high-and-improving; the best is low-and-improving. Read with the
survivorship caveat this is mostly "beaten-down survivors recovered", but it is one
more piece of evidence pointing the same way as E02's U-shape.

## R6 — the shape of the hole

**31 companies were never once in the top 3 deciles in ten years**: AEE, AEP, BALL,
BLK, CCI, CMS, CNP, CRWD, D, DOC, DUK, ED, EQR, ES, GE, IFF, IRM, KKR, KR, LNT, MDLZ,
MRVL, PCG, PEG and more — 1,815 of those rows are Utilities, then Real Estate and
Staples.

The framework is internally consistent about what it likes:

| | top decile | bottom decile |
|---|---:|---:|
| median 3y revenue CAGR | +12.8% | +0.3% |
| median operating margin | +21.5% | +6.4% |
| negative FCF | 0.9% of rows | 34.9% of rows |

So it *is* finding growing, high-margin, cash-generative businesses. It just did not
turn that into return prediction within sector over this window.

## What I recommend changing, in priority order

1. **Sector-relative scoring for margin and returns metrics** (R1). Score operating
   margin, gross margin, FCF margin, ROIC and ROE as percentiles within GICS sector
   instead of against absolute bands. Biggest available improvement; makes the score
   about companies rather than sectors. Pre-register and test on the panel first.
2. **Mid-cycle earnings for cyclical filers** (R5, and E02). Use a 7-year median
   margin and revenue CAGR for semis, hardware, energy, metals and autos.
3. **Band hysteresis** (R4). Require two consecutive readings to change band. Cheap,
   and it fixes a real usability defect.
4. **Report 3-year expectations, not 1-year** (R3). The framework works better at the
   horizon it was designed for; the UI and any future validation should default to 3y.

None of these are applied. Each needs its own pre-registration and a test on the panel
before it touches the live scorer — the EN reweighting already went in on two studies'
evidence and even that was in-sample.

## In-sample check on the reweighting — read the caveat, it matters

Rebuilding the panel under the new weights (FE 18, EN 2) and re-running E02:

| | old (FE 15, EN 5) | new (FE 18, EN 2) |
|---|---:|---:|
| IC 1y | +0.0134 | **+0.0229** |
| months positive, 1y | 55.6% | 59.3% |
| top decile beat bottom | 3/10 years | **6/10 years** |
| IC 3y | +0.0627 | **+0.0841** |
| months positive, 3y | 84.5% | 84.5% |

Every number improved, and the 1-year test now reaches the 6-of-10 threshold that E02's
H2 asked for.

**This is not evidence the change generalises, and the H2 threshold must not be
treated as passed.** The weights were chosen using this data, so re-scoring the same
data with them is close to arithmetic: removing a component whose IC was −0.033 and
adding weight to one at +0.025 raises the composite's IC almost by construction. What
this confirms is that the change was implemented as intended and did what the
mechanism predicts. Whether it helps out of sample is unknown and will stay unknown
until the survivorship-free panel exists and can serve as a genuine holdout.

Recorded so nobody later reads +0.0229 as a validated result.

## The constraint that limits all four

Every number here comes from today's index members, so the bottom decile is
"low-scoring companies that survived". Fixing that needs `D:\ohlcv_1m` (411 monthly
files back to 1992, delisted tickers retained) and `stock_xsect_lab`'s point-in-time
universe. Until then the sector finding (R1) and the cyclical finding (R5) are the two
results I would trust most, because neither depends on the level of returns — both are
about *relative* ordering inside groups that are equally affected by the bias.
