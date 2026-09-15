# E04 addendum — what changed when the dead companies came back

Written 2026-08-11 after building the survivorship-free panel.

## The hole, measured

| | |
|---|---:|
| In the S&P 500 today | 503 |
| Ever a member since 2016 | **716** |
| Removed | **213 (29.7% of the window)** |

Nearly a third of the companies in the E01/E02/E03 window were absent from those
studies. Recovery: prices for **213/213** (`D:\ohlcv_1m` retains delisted tickers),
validated CIKs for **205/213**, and **161** of those cleared the panel's own
minimum-history bar, giving 644 symbols against 483 before.

## The comparison — identical weights, only the universe differs

Both panels were built with weights v2 (FE 18, EN 2) and before F1 was active, so this
isolates survivorship and nothing else.

| | biased (483 syms) | survivorship-free (644 syms) |
|---|---:|---:|
| IC 1y | +0.0229 | **+0.0419** |
| months positive, 1y | 59% | **67%** |
| IC 3y | +0.0841 | **+0.0900** |
| months positive, 3y | 85% | 86% |
| bottom decile mean 1y | **+22.2%** | +19.5% |
| top decile mean 1y | +20.7% | +19.7% |
| FE component IC | +0.030 | **+0.050** |
| BS component IC | **−0.012** | **+0.001** |
| VA component IC | +0.013 | +0.004 |
| EN component IC | −0.030 | **−0.046** |
| bands monotone | False | False |

## Four things this settles

**1. The bias was HIDING the score's skill, not manufacturing it.** IC at one year
nearly doubled and went from positive in 59% of months to 67%. That is the reverse of
the usual survivorship story, and the mechanism is straightforward: the companies that
got removed were disproportionately low-scoring *and* did badly, so excluding them
deleted exactly the observations where the score was right. Every earlier IC figure in
this project understated the measured half.

**2. The U-shape was a survivorship artifact, as called.** The E02/E03 addendum said the
bottom decile out-earning the top "should not be believed". With the dead companies
restored the bottom decile falls from +22.2% to +19.5% and no longer beats the top
(+19.7%). It is now flat rather than inverted — the beaten-down-survivor effect was
doing the work.

**3. Balance Sheet is rehabilitated, not vindicated.** BS went from −0.012 to +0.001,
exactly as predicted when its IC was called "untested rather than disproven" — every
company it would have saved you from was missing by construction. It is now neutral. It
is still not positive, so the honest reading is that BS earns its place as a
ruin-avoidance check and not as a return predictor.

**4. Entry got WORSE, for the third independent time.** EN's IC fell from −0.030 to
−0.046. E01 (signal entries underperformed random entries), E02/E03 (most negative IC of
the four components), and now the survivorship-free panel all point the same way. The cut
from 5 points to 2 was justified; a case for cutting it to zero is now stronger, and the
only thing still arguing against is that this window contains no prolonged bear market.

## What did NOT change

Band ordering is still non-monotone. That finding survives the fix and is therefore
about the framework, not about the sample — the bands as drawn do not order returns.

## Caveats that remain

- 44 of the 205 resolvable removed names did not clear the panel's minimum-history bar,
  and 8 were never resolvable (Aetna, C.R. Bard and others predate usable XBRL). So this
  is a 90%-complete universe, not a complete one.
- 9,699 of 63,185 rows come from the **unadjusted** archive. Split artifacts are handled
  by dropping any return window straddling an implausible print, but that is a blunt
  instrument and it drops real data along with fake.
- Still no prolonged bear market in the window.
- The LLM half is still absent from every historical test and always will be.

## Next

F1 (sector-relative margins) and F3 (band hysteresis) are implemented but **not yet
tested** — that needs a panel rebuild with F1 active, which is then a genuine holdout
because F1 was designed on the biased panel. F2 (mid-cycle earnings for cyclicals) is
still unimplemented, deliberately, so it stays attributable separately from F1.
