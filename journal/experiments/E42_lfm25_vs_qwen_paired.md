# E42 — Is LFM2.5's higher fill better evidence, or just more willing?

**Registered 2026-09-13, BEFORE the instrument was run.** Approved by the user
("do as you wish") after being asked whether to spend part of the run scoring the
comparison rather than only counting companies.

## A structural correction that narrows the question

I told the user earlier today that "the E41 citation gate is what would settle it,"
citing E40's finding that LFM2.5 cites text which is not in the filing **9.7%** of the
time against qwen's 0.5%. **That does not transfer to this harness, and the reason is
structural.**

In the Phase B lane the model never writes a quote. `prompt_for` numbers the candidate
sentences and instructs "Cite ONE sentence by its number. Never write the sentence out";
`parse_judgement` returns an *index*; `claim_for` is called with `pool[idx]`. The quote
is therefore a verbatim slice of the filing **by construction**, and a fabricated citation
is not merely discouraged here — it is impossible. E40's 9.7% was measured on the
free-text qual scorer, which is a different instrument.

So the failure mode available to a model in THIS lane is not fabrication. It is
**misattribution**: choosing an index whose sentence does not support the value it
returned, or answering at all where the sentences support nothing. That is what E42 has
to measure.

## Design

The two books are a genuinely controlled pair, which is unusual and worth using:

- **Candidate pools are model-independent.** `candidates()` is a regex sweep over the
  filing text plus the `_is_hypothetical` exclusion and the 60–300 character window. No
  model touches it. Both books therefore saw **identical** numbered sentence lists.
- **Prompts are identical**, built by the same `prompt_for`.
- **Inherited fields are identical** — `market_share_direction` from `revenue_share`,
  `industry_structural_growth` from the industry object. These are NOT model output and
  are excluded from every comparison below.
- **Only the model differs**: `qwen2.5:7b` (`phase_b_local`) against
  `LFM2.5-2.6B-Finance-Q4_K_M` (`phase_b_lfm25`).

One variable per arm, which is the thing that went wrong with the original "+8.9 mean"
LFM2.5 result (model *and* schema *and* token budget moved together). Here only the model
moves.

Pairing is on companies present in **both** books. At registration that is 246 companies
and it grows as the lane advances, so every number below must be reported with its `n`
and re-run at the end. **A partial sample is balanced, not representative** — the qwen
book covers the front of the S&P book, so the overlap is biased toward larger companies
and nothing here may be read as "the book".

## Registered predictions

Written down before the instrument ran, so a wrong one costs something.

- **P1 — LFM2.5 answers more fields per company than qwen, paired.**
  Expected TRUE (the 6-company probe said 9.2/12 against 8.52/12). This one is nearly
  free; it is registered so the rest cannot be read as the whole result.
- **P2 — LFM2.5's mean per-field normalised entropy is >= qwen's.**
  **This is the actual test.** Fill that all lands on one value is not information: a
  model answering SEVERE for every company has perfect fill and zero discriminating
  power, which is exactly the `acceptance.constant_fields` failure. If P2 fails, the
  extra fill is willingness, not evidence.
- **P3 — LFM2.5 is not more concentrated on candidate index 0 than qwen.**
  A model that mostly returns the first sentence offered is not reading the list, it is
  agreeing with the extractor. Measured as the share of claims citing index 0.
- **P4 — where both models answer, mean per-field Cohen's kappa > 0.**
  Two readings of the same sentences should agree above chance. Near-zero kappa with high
  fill on both sides would mean at least one of them is not reading.
- **P5 — LFM2.5's abstention rate rises with a thinner candidate pool, at least as
  steeply as qwen's.** A model that reads should abstain more when offered one weak
  sentence than when offered six. A flat slope is the signature of a model answering from
  priors rather than from the page.

## What this cannot establish

There is **no ground truth here and none is being invented.** Every metric above is either
a property of the answer distribution or an agreement measure. None of them can say which
model is *right* about a company, and no result from E42 may be written up as one model
being more accurate than the other. What E42 can settle is narrower and still worth
having: whether LFM2.5's extra fill carries information, and whether either model is
answering without reading.

The contamination argument in `CLAUDE.md` applies to both arms and is not differenced
away by pairing — both models' pretraining overlaps the filings. A null here is not
evidence of no difference.

## Results — n = 246 paired companies, 2026-09-13

**Four of the five registered predictions failed, and the one that passed did so at a
level too weak to mean anything.** Full numbers in `E42_results.json`.

| | prediction | result | |
|---|---|---|---|
| P1 | LFM answers more fields | **6.94 → 7.85 of 10**, +0.90; LFM won 158, tied 80, lost 8 | **CONFIRMED** |
| P2 | LFM entropy >= qwen | **0.553 vs 0.582**, −0.030 | **REFUTED** |
| P3 | LFM not more index-0 | **36.3% vs 29.8%** | **REFUTED** |
| P4 | mean kappa > 0 | **0.039** over 10 fields | passed, uninformative |
| P5 | LFM abstention slope >= qwen's | **0.060 vs 0.278** | **REFUTED** |

### The answer to the question that was asked

**LFM2.5's extra fill is willingness, not information.** P5 is the decisive one. Offered a
thin candidate pool of one or two sentences, qwen withholds **35.7%** of the time and LFM
**7.7%**; on a thick pool of five or more they converge to 7.8% and 1.7%. qwen's
abstention tracks the evidence it was given (slope 0.278); LFM's barely moves (0.060).
That flat slope is the signature the registration named in advance: a model answering from
priors rather than from the page. It answers +0.90 more fields per company and the extra
answers carry **less** spread, not more.

### The per-field picture contradicts any single headline

Pooling these ten fields would hide the actual result, which is that **each model has
collapsed fields and the sets barely overlap**:

```
                        qwen modal        LFM modal
current_moat_strength   STRONG  86.5%     MODERATE 99.6%   <- LFM dead
moat_trajectory         STABLE  59.8%     STABLE   94.0%   <- LFM dead
regulatory_risk         ELEVATED 84.5%    MODERATE 95.4%   <- LFM dead
competitive_position    LEADER  94.8%     CHALLENGER 53.8% <- qwen dead
technology_risk         MODERATE 71.7%    (spread) 49.6%   <- LFM better
competitive_position_trend  83.3%         (spread) 54.8%   <- LFM better
```

LFM is genuinely useless on `current_moat_strength`, where it answered MODERATE for 242
of 243.

**CORRECTED 2026-09-13 by E43 — the claim that LFM is "the better scorer on
`competitive_position`" was WRONG and is withdrawn.** It was read off the spread alone:
qwen answered LEADER for 109 of the 115 companies it answered at all, LFM spread across
four values, and spread looked like discrimination. E43 checked what each model was
CITING when it said those things. The `competitive_position` pool can only contain
self-assertions of leadership, because that is all its regex matches — so a claim of
LAGGARD is contradicted by its own quote. **LFM contradicts its own citation 53.9% of the
time (63 of 117 checkable claims); qwen does so 0 of 66 times.** LFM answers LAGGARD while
citing "We are a leading global provider of security products."

So qwen's collapse to LEADER is a **pool** defect — it is the correct reading of a pool
that can only say one thing — while LFM's spread is a **reading** defect on top of the
pool defect. The lesson is the one this repo keeps relearning: **spread is not
discrimination, and a distribution statistic cannot tell you whether a model read the
page.** Every entropy number above is subject to the same caveat.

### Why kappa is near zero, which is not what it first looks like

0.039 looks like two models reading at random. It is mostly not. The disagreement is
**systematic level offset**: on moat strength qwen says STRONG where LFM says MODERATE; on
regulatory risk qwen says ELEVATED where LFM says MODERATE. They are reading the same
sentences onto **differently calibrated scales**, one notch apart. That is a different
defect from random disagreement and it has a different fix — and it means the two books
must never be pooled or compared on levels, which is precisely why they were given
separate directories.

P4 as registered (`kappa > 0`) was a **badly chosen prediction**: almost any pair of
non-random scorers clears it. It is recorded as passed and it establishes nothing.

### A gate that does not catch any of this

`acceptance._constant_fields_in_rows` fires only when a field has **exactly one** distinct
value. LFM's `current_moat_strength` is MODERATE 242 / NONE 1 — **two** distinct values,
so it **passes the gate at 99.6% constant**. One dissenting row in 243 defeats the check.
The gate is a degenerate-case guard, not a discrimination check, and a field carrying no
information passes it comfortably. Changing it would change what passes for every existing
book, so it is written up here as a finding rather than silently altered.

### What this does not establish

No ground truth was used and none was invented, as registered. Nothing here says which
model is **right** about any company. The 246 paired companies are the **front of the S&P
book** — larger companies, richer filings — so this is a balanced sample, not a
representative one, and it must be re-run at the end of the lane. Contamination applies to
both arms and is not differenced away by pairing.
