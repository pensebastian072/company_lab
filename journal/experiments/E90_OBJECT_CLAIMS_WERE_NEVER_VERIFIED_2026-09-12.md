# E90 — the object files are a second population, and nobody had verified them

2026-09-12, continuing E82–E89 in the same session. SHADOW throughout; no ordinal was changed.

## The gap

The corpus-wide restate run at the start of this session verified **the store**: 7,141 claims
re-settled, 97.9% exact containment, three demotions written back. The object files on
`D:\company_lab_data\external\research\industries` are a **different population** — they are the
Phase A artifacts, what `e79b_merge` reads and writes and what a human opens to see an industry's
evidence — and they had never been verified at all.

Measured: all **712** claims in the 208 object files carried the same twelve keys, and **not one
was `verify_status` or `match_mode`.** There was no field in which to record whether a citation
held, so nothing recorded it.

The cost was sitting in plain sight. `retirement_benefits` carried:

> Total US retirement assets were $49.1 trillion as of December 31, 2025, up 2.1 percent from
> September and up 11.2 percent for the year.

against an ICI page that now says **$47.6T and −2.5%**. That claim is the cautionary example
written into `verify.match_quote`'s own docstring — *"the ICI page scored 0.8182 while saying
$47.6T/-2.5% where the quote said $49.1T/+11.2%"* — and its overlap now stamps at exactly
**0.8182**. The repo documented the failure and the artifact kept the claim, because the two were
never connected.

## What the object files actually look like

`scripts/stamp_object_verification.py`, using `verify.match_quote` — the repo's matcher, not a
stricter one of its own:

```text
objects stamped            175 of 208      (the other 33 have no quoted claims yet)
claims stamped             712

match modes
  exact                    573
  no_whitespace             97   <- certifying: quotes lifted out of HTML tables
  overlap_only              25   <- not on the page in sequence
  numeric_mismatch           4   <- the numbers disagree with the page
  absent                     2   <- the text is not there at all
  unreachable               11   <- our failure to fetch, not the claim's fault

verify_status
  VERIFIED_LOCAL           670
  UNVERIFIABLE              31
  SELF_ATTESTED             11

certified                  670 / 701 = 95.6%   (unreachable excluded, as the gate does)
```

**Contrast with the store: 97.9% there, 95.6% here.** Different populations, and the object files
are the weaker half — they also sit only 0.6 points above `MIN_CONTAINMENT_RATE`, a floor
deliberately placed in the gap between a 99.3–100% cluster and an 89.2–91.5% one.

Three design choices in the stamp, each stated because each could have been made lazily:

- an unreachable page records **SELF_ATTESTED**, never UNVERIFIABLE — our network is not the
  batch's fault, the same rule `acceptance.check_containment` follows when it counts unreachable
  pages outside the rate;
- **ordinals are not touched.** A stale citation does not silently un-answer a field. That is a
  judgement about the industry; this script records only the state of the evidence;
- each object is re-validated after stamping and skipped if it would not survive. None did fail.

## The number that matters: 11 ordinals with no surviving evidence

The 31 UNVERIFIABLE claims are not 31 broken conclusions — most sit beside a good claim on the
same field. The actionable figure is how many **answered ordinals have no certifying claim left**:

```text
answered ordinal fields with at least one VERIFIED_LOCAL claim      336
answered ordinal fields whose ONLY evidence fails containment        11   (9 units, 53 companies)

 10 cos  mortgage_reits                 substitution_risk      = ELEVATED    overlap_only
 10 cos  mortgage_reits                 replication_difficulty = MODERATE    overlap_only
  8 cos  electronic_components          structural_growth      = MODERATE    overlap_only
  7 cos  diversified_banks              replication_difficulty = HIGH        overlap_only
  5 cos  alternative_asset_management    replication_difficulty = HIGH        numeric_mismatch
  4 cos  reinsurance                    replication_difficulty = HIGH        overlap_only
  3 cos  custody_banks                  replication_difficulty = HIGH        overlap_only
  2 cos  retirement_benefits            structural_growth      = MODERATE    numeric_mismatch + overlap_only
  2 cos  ai_accelerators                substitution_risk      = MODERATE    unreachable  <- ours, not theirs
  1 cos  dram_hbm                       structural_growth      = HIGH        absent
  1 cos  climate_infrastructure_finance  replication_difficulty = HIGH        overlap_only
```

So **10 genuinely unsupported ordinals** plus one we simply could not check. 3.2% of answered
fields. `dram_hbm`'s `structural_growth = HIGH` is the worst of them: the quote is **absent** from
the page, not merely out of sequence.

`mortgage_reits` deserves a note — both its ordinals rest on one `overlap_only` claim each, and it
is one of the two Real Estate units that had an object before this session. It has been sitting at
2 of 3 and counted as Phase-B eligible on evidence that does not contain its own quotes.

**Nothing was retracted here.** `overlap_only` has two causes that this test cannot separate — a
page that moved since it was cited, and a citation that was never right — and `relocate.py` exists
to settle exactly that against the live web, including following the links a cited page publishes.
That is the next job on these 11, and it is the same shape as the job that settled the 146
unlocatable claims at the start of the session.

## The generalisable part

**A verification that writes to one store does not verify the artifacts.** The restate was correct
and complete for what it covered, and it left a parallel population untouched for months because
that population had no field to record the answer in. The fix was not a better matcher — it was
giving the artifact somewhere to be honest.

Worth checking the same way: anything in this repo that holds evidence in two places. The
scorecards and `scores.parquet` are one such pair; the v1 and v2 qual payload caches are another.
