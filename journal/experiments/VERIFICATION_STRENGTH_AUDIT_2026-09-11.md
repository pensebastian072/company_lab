# What `VERIFIED_LOCAL` actually means — audited over all 6,966 quoted claims

Measured 2026-09-11 from the live store and the local source cache (1,195 cached pages, all
6,966 claims re-readable, none missing). Nothing was written: no claim was re-labelled, no
score recomputed, no object touched. Store hash unchanged,
`c6322b46bc6feef6f47c204b3210c818899162c5af9260538cd6c087205a3bc6`.

Found while doing E79B: two of my own claims verified at overlap 1.0 without being verbatim
on the page, which should not have been possible. It generalises.

## The headline

```
VERIFIED_LOCAL claims carrying a quote and a url      6,966
EXACT character containment TODAY                     4,607   66.1%
  + decode HTML entities                              5,615   80.6%
  + normalise Unicode punctuation and whitespace       6,820   97.9%
cannot be located on the cited page AT ALL               146    2.1%
```

**One in three `VERIFIED_LOCAL` claims is not verbatim-confirmed today.** It passes on
`check_quote`'s token-overlap fallback at `MIN_EVIDENCE_OVERLAP = 0.6`. The corpus is
mostly sound — 97.9% of quotes ARE on their page once encoding is handled — but the label
currently certifies less than it is read to certify.

The mechanism is proven by a control inside the data: `data.sec.gov`, which serves JSON and
therefore no HTML entities, has a **0.0% fallback rate over 321 claims**, against
`sec.gov` HTML's **39.3% over 5,484**. Same filer, same facts, different encoding.

| host | fallback / checked | rate |
|---|---|---|
| sec.gov | 2,156 / 5,484 | 39.3% |
| data.sec.gov | 0 / 321 | **0.0%** |
| content.naic.org | 32 / 80 | 40.0% |
| limra.com | 13 / 24 | 54.2% |
| fdic.gov | 40 / 162 | 24.7% |
| eia.gov | 19 / 241 | 7.9% |

## The fix, with its measured yield

In `verify.check_quote`, before matching: `html.unescape`, map Unicode quotes/dashes/spaces
to ASCII, `NFKC`-normalise, then compare. A second, looser comparison ignoring whitespace
entirely catches table-derived text (`...customer balances$3,619$3,5263%`).

```
entity decode alone          +983 claims   66.1% -> 80.6%
+ punctuation/whitespace    +1,205 claims  80.6% -> 97.9%
```

That nearly retires the overlap fallback, which matters because the fallback is the path
`verify.py`'s own comment records as having produced a false match (the ICI page at 0.8182
while stating $47.6T/-2.5% instead of $49.1T/+11.2%).

`verify.py` is Chat A's file. This is the measurement, not the edit.

## The 146 that cannot be found at all — and what passed them

`D:\company_lab_data\external\reports\UNLOCATABLE_QUOTES_2026-09-11.json`

**The overlap score that certified them has median 1.0, min 0.6667, max 1.0.** A perfect
token-bag score on text that is not on the page in any sequence. That is the fallback's
failure mode stated precisely: it compares vocabulary, not language.

```
by source_type   PRIMARY_DATA 55 · COMPANY_IR 36 · SEC_FILING 33 · REGULATOR 12 · OTHER 5 · TRADE_PUBLICATION 5
by host          sec.gov 32 · content.naic.org 23 · eia.gov 19 · limra.com 13 · IR hosts (gcs-web.com) 20+
by field         industry_structural_growth 26 · regulatory_risk 17 · technology_risk 16 ·
                 company_specific_capture 11 · moat_trajectory 10 · disruption_risk 10
                 115 company claims, 144 industry claims
```

The examples read like real facts from the wrong page — NVIDIA's quarterly revenue sentence,
Digital Realty's renewal-rate figure, a US mineral-production total. The likely causes are an
IR index page cited instead of the specific release, a figure taken from a PDF or deck while
the cached page is HTML, or invention. **The audit cannot distinguish those three, and that
distinction is the whole question**, so each of the 146 needs re-fetching against its real
source or demoting to `UNVERIFIABLE`.

Honest consequence: until that is done, the corpus's verified count is **up to 146 claims
lower than stated**, and the affected fields are named above.

Note which field leads that list: `industry_structural_growth`, 26 of 146. The field this
session had considered dropping for being hard to answer also carries the largest share of
evidence that cannot be located. Those are two different problems with one field and they
should not be conflated — one is availability, the other is citation discipline.

## What this does and does not establish

It establishes that `VERIFIED_LOCAL` today means "the page shares this quote's vocabulary"
for about a third of the corpus, that 97.9% of quotes are genuinely present once encoding is
normalised, and that 146 are not present at all on the page they cite.

It does **not** establish that those 146 are fabricated; three candidate causes remain open
and one of them is benign. It also does not re-verify anything against a FRESH fetch — every
check here ran against the cached page, so a source that changed since caching would read as
a mismatch here and is not distinguished either. A re-fetch of the 146 settles both.
