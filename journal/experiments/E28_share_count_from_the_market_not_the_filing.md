# E28 - the share count comes from the market, and disagreement is reported

Registered 2026-08-24, before the fix. Found because the user looked at MCD in the
workbook and said it was wrong. It was.

## What was wrong

`MCD` files `WeightedAverageNumberOfDilutedSharesOutstanding` as **714.525** - millions of
shares - while nearly every other filer reports raw units. The forward DCF divided a
$170.5bn equity value by 715 and produced a fair value of **$238,644,091 per share**.

Audited across the universe by cross-checking the filed count against `market_cap /
price`, an independent estimate from a different source:

| disagreement | companies | cause |
|---|---:|---|
| ~1,000,000x | 1 | filed in millions (MCD) |
| ~1,000x | 6 | filed in thousands (BRK-B, CYTK, HUBG, RGEN, NPK, NTNX) |
| 2x - 10x | 19 | stock splits inside the TTM window (NFLX 10:1), multi-class structures |
| count too HIGH (<0.5x) | 4 | HON, DD, AMCR, LXP |
| sane (0.5-2x) | **1,409** | |

**Nineteen of the thirty produced a fair value, and only ten were flagged implausible.**
The other nine - KLAC $631, NFLX $561, CRWD $290, CWEN $89, WMG $98, POWL $835, KNTK $47,
HON $37, AMCR $15 - sit in the sheet looking like ordinary numbers while being wrong by
2-10x. The >10x implausibility gate cannot catch an error of 3x, which is exactly the size
a split produces.

## The change

**`market_cap / price` becomes the share count for per-share valuation**, with the filed
count as cross-check rather than input.

The reasoning is not only that it is more robust. It is more **correct for the purpose**:
a fair value per share needs the shares outstanding TODAY, and `diluted_shares_ttm` is a
trailing four-quarter AVERAGE - so for any company that split, issued or bought back
meaningfully during the year, the filed number is the wrong quantity even when its units
are right.

Both come from the same yfinance snapshot and are contemporaneous, so their ratio is a
current count.

Rules, fixed here:

* `shares = market_cap / price` when both are present and positive.
* Fall back to `diluted_shares_ttm` when they are not, and record which was used in
  `dcf_shares_basis`.
* When the two disagree by more than **2x**, the row carries `dcf_shares_disputed = true`
  and the disagreement ratio, so a reader can see it rather than infer it. The fair value
  is still produced - from the market-derived count - because refusing would drop 30
  companies for a problem the fix has already solved.
* When NEITHER is available, no fair value, as now.

## Pass criteria

| | passes if |
|---|---|
| **S1** | MCD's fair value lands in a plausible range for a company whose price is $270 - specifically inside 0.1x to 10x price - rather than $238m. |
| **S2** | The count of companies whose filed and market-derived share counts disagree by >2x is **reported** on every affected row, and is not zero simply because the check was removed. |
| **S3** | The 1,409 companies whose counts already agree see their fair value move by **less than 1%**. A fix that quietly re-values the healthy 98% is not a fix. |
| **S4** | No company gains a fair value it did not have, except through the share count itself. |

## Prediction

S1 and S3 pass. S2 reports ~30. The interesting one is the nine unflagged names: NFLX and
KLAC should move by roughly their disagreement ratio, which will look like a large change
and is a correction, not a re-rating.

## What this does not fix

The filed share count is still wrong for those thirty companies everywhere ELSE it is
used - `dilution_yoy` reads it, and so does anything per-share downstream. This
registration covers the DCF only; the wider audit is a separate piece of work and is
noted rather than silently bundled in.
