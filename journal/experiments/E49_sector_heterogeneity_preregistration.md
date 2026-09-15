# E49 - can we predict, before spending, whether a sector's external layer will rank it?

Registered 2026-09-05, before researching any third sector and before computing any
external result for one.

## Why

Two sectors are complete and they came out opposite ways:

```
            external score    distinct   sd      verdict
energy      22.5 - 78.0        47/71    12.98    ranked the sector
utilities   28.5 - 44.0        13/59     4.80    22 companies tied, did not rank it
```

Both cost the same discipline and roughly the same budget - 634 and 708 claims, 208 and
266 searches, zero rejections and zero unverifiable claims in each. Utilities returned
impeccable evidence and a ranking that cannot separate its own sector, for a structural
reason: in a population where every member faces the same regulator and the same
technology, peer-relative fields honestly return the same value for everybody.

The sector-by-sector plan assumed a complete sector buys a rankable sector. Energy bought
one; Utilities did not. **If that is predictable in advance it changes the running order,
and if it is not, that is worth knowing before eight more sectors are bought.**

## The hard limit, stated first

**n = 2.** Nothing below is a fitted model or a validated rule. It is one pre-registered
proxy, one prediction and one threshold, written down before the third sector is bought
so the third result can refute it. Two points cannot distinguish a real predictor from a
coincidence, and a third cannot either - it can only fail to support one.

## The proxy

`sd_opmargin` - the within-sector standard deviation of `operating_margin` over the live
book. It measures whether a sector's companies run economically different businesses,
which is the property peer-relative fields need in order to have anything to say.

Measured today over 1,500 companies:

```
sector                   n  inds  hhi   sd_score  sd_opmargin  med_score
financials             257    19  0.159    12.8      0.243        48
real_estate            105    16  0.092    12.3      0.235        35
energy                  71     8  0.229    11.0      0.199        41   <- ranked
materials               77    16  0.137    11.5      0.193        48
health_care            163    10  0.138    12.8      0.188        54
communication_services  47    10  0.134    15.3      0.179        51
information_technology 190    17  0.102    12.7      0.152        62
consumer_discretionary 193    28  0.056    12.0      0.113        49
consumer_staples        75    11  0.106    10.3      0.106        49
industrials            263    27  0.074    12.5      0.094        54
utilities               59     7  0.238     7.7      0.077        39   <- did not
```

Utilities is **last on `sd_opmargin` at 0.077, and last by a wide margin** - the next
lowest is industrials at 0.094 and the median sector is 0.152. Energy sits at 0.199.

**Two rival explanations are rejected here, in advance, because both looked obvious and
neither survives the data.**

*Industry fragmentation does not separate them.* Utilities `hhi` 0.238, Energy 0.229 -
effectively identical, and both are the two MOST concentrated sectors in the book. "Few
industries means homogeneous companies" is wrong, and it was the intuition behind the
original cheapest-sector ordering.

*Score LEVEL does not separate them either.* Utilities median 39 and real_estate median
35 are the two lowest in the book, but real_estate's `sd_score` is 12.3 against utilities'
7.7. A sector can be scored low and still be dispersed. **Flatness predicts the failure;
lowness does not.** Confusing the two is what the E47 plan did.

## The prediction

The third sector is **communication_services**: 47 companies over 10 industry objects,
none researched. It is the cheapest sector on the board by company count and the highest
in the book on `sd_score` (15.3), while sitting mid-table on `sd_opmargin` (0.179).

Registered predictions, all to be evaluated on the completed sector:

| # | criterion | prediction |
|---|---|---|
| 1 | external-score sd | **> 8.0** (utilities 4.80, energy 12.98) |
| 2 | distinct external scores | **> 40% of n** (utilities 22%, energy 66%) |
| 3 | largest tied group | **< 25% of n** (utilities 37%, energy 18%) |
| 4 | fields resolving for 0 of n | **at most 1** (utilities 4, energy 1) |
| 5 | `technology_risk` distinct values | **>= 3** (utilities 1, energy 4) |

Prediction 5 is the sharpest and the most falsifiable: communication services spans
Alphabet and Meta beside rural telephone companies and broadcast television. If a single
`technology_risk` value covers that population the field is broken rather than the sector
being homogeneous, and that is a different and more serious finding.

## What each outcome licenses

- **All five hold.** `sd_opmargin` is not refuted as a screen. It is still not validated -
  n = 3 - but the running order may be set by it, and consumer_staples (0.106) and
  industrials (0.094) move to the back of the queue behind materials and health_care.
- **Predictions 1-3 fail with 4 and 5 holding.** The sector is heterogeneous and the
  layer still cannot rank it. That points at the scoring dimensions rather than the
  sector, and the next question is whether `external_score` can rank anything.
- **Prediction 5 fails.** Stop and fix the risk fields before buying another sector.
  A constant `technology_risk` across Alphabet and a rural telco is a measurement defect,
  not a fact about the world.
- **Everything holds but `sd_opmargin` did not order the sectors.** Then the screen is a
  coincidence that survived one test, and it should be dropped rather than kept because
  it was right once.

## Taxonomy to settle BEFORE staging, not after

E46 and E47 both established that the taxonomy must be fixed before the research is
bought, because a bucket Codex correctly refuses to describe costs its members their
industry fields. Two candidates are already visible in communication services and are
recorded here rather than fixed, since the sector is not confirmed:

**PINS is filed as `interactive_home_entertainment`** - the video-game bucket, beside
Take-Two. Pinterest is an ad-supported social platform whose peers are META and RDDT,
both of which sit in `interactive_media_services`. This is the CEG-and-VST case exactly:
GICS has put a company in a bucket whose research questions do not apply to it. Moving it
also leaves TTWO alone, which is the AES situation and would need the same explicit
decision.

**`advertising` holds APP at a 77.4% operating margin beside OMC at 2.2%** - a mobile
ad-tech platform and a traditional agency holding company, 35x apart on the metric.
Whether that is one research unit or two should be decided before the object is built,
not discovered in the report.

Note the tension with prediction 1: both fixes would REDUCE within-bucket dispersion by
making the buckets more coherent, while the registered predictions are about
dispersion of the SECTOR's scores. They are different quantities and splitting a bucket
does not mechanically move the sector's sd. Recording that here so the two are not
conflated after the fact.

## Out of scope

This predicts nothing about returns. It is a question about whether a measurement
instrument discriminates, not about whether what it measures is worth anything. The
ranking remains unvalidated - E05's top decile ran a -7.6% median 3-year excess return
against SPY on a survivorship-free holdout and 95.6% of its power is sector selection.
`promoted` stays false, status stays SHADOW, and no result here changes either.
