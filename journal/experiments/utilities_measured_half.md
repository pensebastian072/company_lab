# The measured half in Utilities - shifted, not flattened

Measured 2026-09-04 while planning E47, over the 59 Utilities companies in
`data/scores.parquet`. Not a pre-registered study; a range/level sweep of the kind the
E30 audit should have been run everywhere.

## The level

```
band mix        REJECT 47   INSUFFICIENT_DATA 10   WEAK 2   above WEAK: 0
top score       VST 59      book max 87      book median 49   utilities median 39

component      max   utils med   book med   utils as % of max   book as % of max
VA              15         3.0        8.0                20%                53%
BS              10         3.0        6.0                30%                60%
FE              18         6.0        7.0                33%                39%
MG               9         4.0        5.0                44%                56%
ER               5         2.0        3.0                40%                60%
BQ              15         6.0        6.0                40%                40%
SG              20        11.0       10.0                55%                50%
```

Not one utility scores above WEAK. The sector is rejected wholesale, and the two
components doing it are VA and BS - the two whose readings are structurally determined
for a rate-regulated business. Rate base is debt-financed against an allowed return, so
5-6x net debt / EBITDA is the design, not a warning. Utilities trade on dividend yield
and rate-base growth, not on the earnings and FCF multiples VA tests.

SG is the one component where utilities beat the book (11.0 vs 10.0). The judged half
likes them; the measured half does not.

## The thing that would have been a defect, and is not

The obvious next claim is that VA is dead inside the sector - the E30 symptom, where
`bs_dilution` was constant across all 11 sectors and therefore carried no information.
Tested, and it is false:

```
comp  max distinct     sd   iqr  mode share
SG     20       16   3.02   3.0         20%
BQ     15       10   2.65   4.5         20%
FE     18       13   2.74   3.5         20%
MG      9        7   1.36   3.0         29%
BS     10        9   1.73   2.0         25%
VA     15       10   2.08   2.0         31%
ER      5        6   1.23   1.0         34%
EN      2        3   0.53   0.0         71%
```

VA takes 10 of 15 possible values across 59 companies, sd 2.08, and its most common
value covers only 31% of them. It separates utilities from each other perfectly well.
It separates them at a lower level than it separates the rest of the book.

**Shifted is not flattened, and the two want opposite responses.** A flat component is a
measurement bug to fix. A shifted one is the framework reporting something true about
the sector, and the response is to compare within the sector - which
`sector_neutral_score` already does.

EN is the one component that is close to flat here (mode share 71%, sd 0.53), but EN is
2 points of 94 and is near-binary book-wide, so that is not a Utilities finding.

## What this does and does not establish

It establishes that a cross-sector ranking will place essentially no utility in its top
band, and that this is driven by VA and BS reading the regulated capital structure
rather than by any judgement about the companies. It is a restatement of E03 - 95.6% of
ranking power is sector selection - localised to the sector where the effect is largest.

It establishes nothing about returns. It does not show utilities are mispriced, cheap,
or worth owning. It does not show the framework is wrong: a framework calibrated on
unregulated businesses reporting that regulated ones look different is the framework
working.

It is the reason Utilities is a good second sector for the external layer. Where the
measured half has the least to say about level, external evidence is carrying more of
the weight - and that also makes it the sector where a bad external record would do the
most damage.
