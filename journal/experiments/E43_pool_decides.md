# E43 — The candidate pool decides the answer, and it makes misattribution checkable

**Run 2026-09-13, n = 371 qwen rows / 645 LFM rows.** Instrument:
`clab/research/e43_pool_decides.py`. Raw numbers in `E43_results.json`.

E42 asked which model reads better. E43 asks the question underneath it — **are the
candidate sentences evidence for the field at all?** — and the answer changes E42's
conclusion on one field and puts a hard number on the failure mode E42 could only name.

## The headline

**LFM2.5 contradicts its own citation 53.9% of the time. qwen does so 0.0% of the time.**

| | checkable claims | consistent | **contradicted** | rate |
|---|---|---|---|---|
| qwen2.5:7b | 66 | 66 | **0** | **0.0%** |
| LFM2.5-2.6B | 117 | 54 | **63** | **53.9%** |

A contradiction looks like this — LFM's answer, then the sentence it cited as the reason:

```
LAGGARD    <- "We are a leading global provider of security products and solutions
               operating in two segments: Allegion Americas and Allegion International."
LAGGARD    <- "We are one of the largest vehicle technology suppliers and our customers
               include the 25 largest automotive OEMs in the world."
CHALLENGER <- "The Hi-Crush Transaction expanded the Company's position as a leading
               provider of proppant and proppant logistics in the Permian Basin."
```

## Why this is checkable without ground truth

`competitive_position`'s pattern is

```
(we are (?:the|a|one of) (?:the )?(?:largest|leading|number one|second largest|top)
 |market leader|leading (?:producer|provider|manufacturer|supplier))
```

Every sentence it can select is an **assertion of leadership**. The pool therefore cannot
contain evidence that a company is a laggard. That is a defect — but it is a defect that
makes one thing knowable: if the only sentence offered says the filer leads its market,
then answering LAGGARD is wrong **on the model's own stated evidence**, with no outside
label required.

Claims are split three ways before any rate is computed, because two of the three are not
checkable:

- the quote asserts the **filer's own** leadership — checkable (qwen 66, LFM 117)
- the quote asserts **someone else's** ("products from *leading suppliers*", "acquired
  Traverse Systems, an *industry-leading* firm") — evidence of nothing about the filer,
  excluded (qwen 12, LFM 23)
- the quote asserts no leadership at all — excluded (qwen 96, LFM 128)

The classifier was checked against known-positive and known-negative sentences in both
directions before the rate was trusted, per the E34 rule: **when a check returns zero,
confirm it can return non-zero at all.** qwen's 0.0% is a real zero, not a broken query —
the same classifier returns 63 on the other arm.

## What it does and does not establish

**Does:** on the one field where the pool makes truth checkable, LFM2.5 misreads its own
evidence more than half the time and qwen never does. This is the misattribution failure
mode E42 registered as the only one available in this harness — the model cannot fabricate
a quote, so the way it can be wrong is to cite a sentence that does not support its answer.
It is consistent with E42's P3 (LFM picks the first candidate more often) and P5 (LFM
barely abstains when the evidence is thin).

**Does not:** generalise to the other nine fields. This is **one field**, chosen precisely
because its pool bias makes it checkable, which is the opposite of a representative sample.
53.9% is not "LFM is wrong half the time"; it is "LFM is wrong half the time *here*".

## A hypothesis that the data did NOT support

The first reading of the dead `current_moat_strength` field was that its pool is full of
litigation text — the pattern matches bare `patent|proprietary|trade secret`, and the
eyeballed examples were patent-claim and foreign-law sentences. **Measured, that is only
6.1% of LFM's claims for the field and 2.5% of qwen's.** The litigation framing is real
but small, and it is not why the field is dead. Recorded here because it was the stated
hypothesis before the count, and n=3 eyeballed examples produced a wrong one — the same
n=1 trap this repo has hit before.

`current_moat_strength` at MODERATE 242 of 243 remains unexplained and is open.

## Open, not acted on

1. **The pool patterns are a correctness-core change.** `CLAUDE.md` requires an A/B over
   cached filings before any such edit, and rewriting them invalidates every row already
   scored. At 645 of 1,500 that decision belongs to the user, batched once, not taken
   mid-lane.
2. **A contradiction check could be a deterministic gate rather than a study.** The
   classifier here is cheap and runs at ingest; a claim whose citation contradicts its
   value could be dropped or flagged without any model in the loop. That would help every
   book, including the 311 Codex rows.
3. **Extend the checkable-pool trick.** `competitive_position` is checkable by accident.
   Other fields could be made checkable on purpose by pairing a one-sided pool with the
   values it rules out.
