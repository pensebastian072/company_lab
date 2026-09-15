# E36 Amendment 1 — what counts as a rationale that carries no judgement

Written **2026-08-29 10:45**, after the criterion was applied to incumbent data for the
first time and before any of the 400 was analysed.

## The change

C2 originally read: a rationale is **degenerate** if it matches the pack's header form
**or is under 45 characters**.

It now reads: a rationale is **degenerate** if it matches the pack's header form
(`chrome`) **or is the literal word null / none / n-a / empty** (`empty`). A
short-but-real judgement is classified `terse` and is **reported separately, not counted
against either lane**.

## Why, stated plainly

The character threshold was doing most of the work, and it was measuring the wrong thing.
Run against the incumbent's cache it flagged, among others:

```
ABT  brand           score=3  "Established brand in healthcare equipment."      (41 chars)
ABT  distribution    score=3  "Wide distribution channels mentioned."           (37 chars)
AIR  brand           score=2  "Brand promise of 'Doing it Right. Nonstop.'"     (43 chars)
```

Those are **judgements**. Short ones, but a moat rating with a one-clause reason is not
the same failure as a page header pasted under a score of 4. Counting them together gave
qwen a 40.4% "degenerate" rate on the first sample, and roughly three quarters of that was
the threshold rather than the model.

What the same pass found that *is* a defect, and which the threshold was burying:

```
APD  manufacturing_complexity  score=5  rationale='null'
APD  brand                     score=4  rationale='null'
SWKS switching_costs           score=1  rationale=''
```

The literal string `null` beside a committed score of 5. That is a rationale that carries
no judgement in exactly the sense C2 was written to catch, and it belongs in the count.

Under the corrected definition the same sample reads **29.8% for the incumbent and 3.2%
for the candidate** on BQ.

## Which direction this cuts, and the disclosure that matters

**It cuts against my own registered prediction, and it was made after seeing data.** Both
facts have to sit next to each other.

Prediction 2 in the registration says the candidate's degenerate rate will be *materially
higher* than the incumbent's — that LFM2.5 answers everything by quoting chrome. The
corrected metric moves the incumbent's number **down** (40.4% → 29.8%) and still leaves it
roughly **nine times** the candidate's. So the amendment makes my own prediction look
*more* wrong, not less, which is the only reason it is defensible to make it mid-experiment.

Had it gone the other way — had the fix flattered the prediction — the honest move would
have been to keep the registered definition and report both.

## What is unchanged

* The sample, the seed and the run order.
* C1, C3 and C4 exactly as registered.
* C3 in particular: `evidence_unverified` stays excluded as a quality check, because a
  page header is verbatim pack text and verifies cleanly. A 0.0% unverified rate is not
  evidence of honesty here and will not be reported as if it were.
* Both lanes are measured by the identical function, `classify_rationale`, over the same
  companies.

## The incumbent finding this produced on its own

`rationale='null'` beside a real score is a **v1 data-quality defect**, not a v2 finding,
and it was invisible until a comparison forced someone to look at rationale text. How
widespread it is across the full 1,501 is not yet measured; it is reported in the results
with its own count rather than folded into a rate.
