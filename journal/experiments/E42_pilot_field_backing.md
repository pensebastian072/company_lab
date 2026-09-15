# E42 pilot - measured field backing, and a hypothesis that did NOT hold

Measured 2026-09-02 on the completed pilot payload `812721fe9a0d87fd6b72`
(FICO, VRT, NVDA; depth 3; 14 claims; 29 searches, 5 cache hits).

Not a registered experiment. A measurement over what came back, written down before
`score.py` is designed, because it decides what `score.py` is allowed to score.

## The calibration cases passed

| case | target behaviour | result |
|---|---|---|
| FICO | the record must disagree with its own financial history | **PASS** - moat STRONG, trajectory WEAKENING, position DETERIORATING, share LOSING, regulatory ELEVATED, cheapness STRUCTURAL |
| VRT | industry growth must not be read as company capture | **PASS** - structural growth HIGH, `company_specific_capture` UNKNOWN, `market_share_direction` UNKNOWN |
| NVDA | must not answer "AI is growing therefore NVDA is good" | **PASS** - moat EXCEPTIONAL but trajectory STABLE, share FLAT, with merchant and custom silicon named |

The claims behind them are good. VantageScore's own site cited as COMPETITOR_FILING
against FICO's share. Fannie Mae's selling guide as CUSTOMER. AMD's 10-Q against NVDA.
Google's TPU announcement as substitution evidence. Eaton AND Schneider both cited for
Vertiv **specifically to block** the inference that growth equals share gain - the claim
text says so in as many words.

All three reconciliations DISAGREE with the local model, each citing claim ids. VRT is
the sharpest: the local model scored SG **19/20**, and the external layer says the
industry is growing while VRT's capture is unestablished.

## The finding: most assertions carry no citation

39 categoricals asserted across 3 companies. 3 of them UNKNOWN. 14 claims.

```
claims per asserted non-UNKNOWN categorical: 0.39
non-UNKNOWN categoricals with a claim citing that field: 10 of 36 (28%)
```

Per company, the fields asserted with NO backing claim include:

```
FICO  current_moat_strength STRONG, competitive_position LEADER,
      cheapness_quality STRUCTURAL, disruption_risk ELEVATED
NVDA  current_moat_strength EXCEPTIONAL, moat_trajectory STABLE,
      market_share_direction FLAT, pricing_power HIGH
VRT   competitive_position_trend IMPROVING, current_moat_strength MODERATE,
      pricing_power MODERATE
```

This is the E39 shape in a new place. E39 found 271 companies whose moat scores existed
only because unexplained dimensions made the 6-of-11 quorum; here most external
categoricals exist without cited evidence.

## The hypothesis that did NOT hold

Before measuring, the expectation was that unbacked fields would lean **optimistic** -
that a researcher asserts a flattering value when it has nothing to cite. VRT looked
like the case for it: `competitive_position_trend: IMPROVING` has no claim, while
`market_share_direction: UNKNOWN` has two CONTRADICTS claims behind it.

Measured over all three companies, on the 0-1 favourability scale where 1.0 is good for
the company:

```
claim-BACKED   non-UNKNOWN fields   n=10   mean 0.683
UNBACKED       non-UNKNOWN fields   n=26   mean 0.660
```

**No gap.** If anything the backed fields read slightly more favourable. n is far too
small to conclude anything either way, and the honest statement is that unbacked fields
are not measurably more optimistic - not that they are equally trustworthy. They are
still unevidenced; they are simply not evidently biased.

Recording the refutation because the intuition is strong enough that someone will have
it again.

## What this decides for score.py

The main framework already answers this: points are earned only where a sub-test was
actually SCORED, coverage is `earned / available`, and below
`MIN_COVERAGE_FOR_BAND = 0.80` no band is issued at all.

The external score takes the same shape. A categorical with no claim citing its field
is NO_DATA, not a score, and external coverage is backed-fields / applicable-fields.
At 28% backing, all three pilot companies fall far below `EXTERNAL_MIN_COVERAGE` and
would receive **no external score**.

That is the correct outcome and it is also the measurement that matters: research
density needs to roughly triple before an external score means anything. It is a
concrete target, not a vague call for more depth.

## Verification

13 of 14 claims VERIFIED_LOCAL by local re-fetch. One VRT claim (Eaton press release)
stayed SELF_ATTESTED after a fetch timeout - the same host timed out during Phase 0.
Catalog: 103 VERIFIED_LOCAL, 18 SELF_ATTESTED, 2 UNVERIFIABLE across 123 claims.

`external_score` and `external_confidence` are NULL for all three, as designed.
