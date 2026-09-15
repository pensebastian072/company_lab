# E01 addendum — what the negative result actually means

Written after seeing the results. The pre-registration is unedited; this is the
interpretation, kept separate on purpose.

## The headline

The EN entry rule **failed** its pre-registered tests.

| Hypothesis | Result |
|---|---|
| H1 signal beats random entries at 1y | **FAIL** — signal +22.3% vs random +56.9% |
| H2 positive edge in 6 of 9 years | **FAIL** — 3/9 on the mean, 4/9 on the median |
| H3 confluence beats partial | PASS, but see below — this one is uninformative |
| H4 beats SPY at 1y and 3y | PASS — +4.1% and +29.9% |

Hit rates are effectively identical: **73.3% for signals, 74.3% for random entries.**
Waiting for a good entry did not improve the odds of being up a year later.

**Correction — 2026-09-07:** those rates used all generated rows as the denominator,
including unavailable forward returns as losses. The corrected 1-year signal rate is
**73.82% (702/951 observed)**. The random-control observed `n` was not saved, so its
historical corrected rate cannot be recovered from the aggregate; the “effectively
identical” hit-rate comparison is withdrawn. E01 still fails H1 and H2 on its registered
mean-return tests, so the decision remains unchanged.

## Why H3's "pass" should be ignored

At the pre-registered threshold of EN >= 4, **every single signal also had
confluence** (n_no_confluence = 0), so the comparison it was meant to make does not
exist. What remains is EN 5 (+22.8%) versus EN 4 (+21.0%) on n=714 and n=237 — a
1.8-point gap that is noise. H3 was not really tested. Do not cite it.

## The mechanism, which is the useful finding

The 2025 row looks broken and is not: the random-entry mean is **+444%** because
**MU returned up to +1029% from a 2025 entry** (mean +541% across 2025 entry dates)
on the memory/AI supercycle. VRT +374%, DELL +316%, ANET +163% behave similarly.

**The entry rule never fired on MU.** Its P/E sat around the 52nd percentile of its
own range and price stayed above every 20/72 EMA — so on the rule's own logic it was
never "an unusually attractive price". Meanwhile buying it on essentially any random
day of 2025 produced a multiple.

That is the whole result in one example, and it points the opposite way from the
hope that motivated the change:

> A compressed multiple is a good entry in a business whose earnings are *stable*.
> In a business that is **re-rating upward** — earnings inflecting, multiple
> expanding — waiting for the multiple to compress means never buying it at all.

The names this framework is best at finding are high-growth compounders. Those are
exactly the names where "wait for a cheap multiple" is most likely to keep you out.

## What this does not say

- It does **not** say the ranking picks bad companies. Company selection was held
  constant by construction; only timing was tested.
- It does **not** say entry timing never matters. It says that over 2016-2025, inside
  a watchlist of companies that turned out well, in a market that mostly rose,
  waiting for a discount cost more than it saved. A different window - one containing
  a prolonged bear market - could easily reverse it.
- The watchlist is survivorship-selected (today's top 100). Names that collapsed are
  absent, which if anything *flatters* the buy-anytime baseline. The honest reading is
  that the comparison favours the baseline for a reason that is itself a bias.

## What I would change, and what I would not

**Keep EN at 5 of 100 points.** The result says it is not a reliable timing edge, so
it should stay a tiebreaker between two companies you already want - which is exactly
how the framework already weights it, and exactly how the user described using it.
Nothing needs to change in the scoring.

**Do not turn EN into a gate** (do not filter the ranking to EN >= 4). On this
evidence that would have systematically excluded the biggest winners.

**Worth testing next, pre-registered separately:**

1. Split the test by whether earnings are *accelerating* at the entry date. The
   hypothesis worth checking is that a compressed multiple is a good entry only when
   growth is stable, and a bad one when growth is inflecting. That is a real,
   falsifiable claim and this data can answer it.
2. Test the EMA pillar alone against the P/E pillar alone at a lower threshold, where
   non-confluence cases actually exist, so H3 can be tested for real.
3. Re-run on a window containing 2000-2002 and 2008. The price store only reaches
   ~2016, so this needs the `D:\ohlcv_1m` archive that `stock_xsect_lab` already
   indexes back to 1992.

## Data defect found and fixed during this study

The price store was built with `auto_adjust=False`, so unadjusted splits read as
single-day crashes: 26 of 500 symbols affected (KDP -82% on its spinoff, GL -53%,
DXCM -41%, FISV -44%). That corrupted the EMAs feeding live EN scores, the price
basis of the P/E series, and every return in the first run of this study.

Fixed at the root (`auto_adjust=True`), all 501 series re-downloaded, all 500
companies re-scored, and a `price_quality` / `audit_store` guard added so it cannot
recur silently. Spinoffs and mergers still survive adjustment (KDP -87%, GEN -52%),
so any trade whose window straddles an implausible print is now dropped rather than
believed — while genuine crashes (the 2020 oil collapse, DXCM's guidance miss) stay
in the sample where they belong.
