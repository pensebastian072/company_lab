# E43 - the first full batch, and a funnel test that cannot be answered

> **Dated note, 2026-09-09 — scoring generation.** The external scores in this file
> were computed BEFORE the 2026-09-09 re-score. `score_all --apply` was run that day
> across all 13 research versions, applying two instrument changes that post-dated
> this study: the A1 UNVERIFIABLE doctrine
> (`A1_UNVERIFIABLE_SCORING_DECISION_2026-09-08.md`) and the FDIC-computed
> `market_share_direction`. For this arm that moved **9** stored scores.
> Largest moves: MA 38.2->28.0, EQT 55.0->46.0, XYZ 66.5->58.9, JKHY 41.8->34.3, CINF 67.0->60.3, MU 68.9->63.9 ....
> The pre-re-score values are frozen at
> `D:/company_lab_data/external/reports/prescore_snapshot_2026-09-09.json`
> (sha256 `a8189d864f7981508c26ab136050a1b28ed10ab9f4d0a80106f2f14a4e920272`).
> Numbers in this file are NOT restated; see `SCORE_STALENESS_2026-09-09.md`.


40 companies, request `1358af92f8227af46c5d`, research version `2026-09-02+E43-batch1`.
32 priority + 8 control, drawn from the 226 companies covered by a built Phase 0
industry object.

## The delivery

| | |
|---|---|
| accepted / rejected | 40 / 0 |
| non-UNKNOWN fields | 377, **all 377 citation-backed** |
| demoted by the citation rule | 0 |
| claims | 420 from 63 sources, 5 independence domains |
| verification (this batch) | 382 VERIFIED_LOCAL, 36 SELF_ATTESTED, 2 UNVERIFIABLE |
| corpus after the batch | 517 VERIFIED_LOCAL, 54 SELF_ATTESTED, 4 UNVERIFIABLE; **unverifiable rate 0.77%** over 521 checked |
| searches | 302, inside the 300-400 estimate |
| pass B reconciliations | 55 |
| below the 0.80 coverage floor | 13 companies |

The citation rule needed no enforcement: zero demotions across 377 fields. The
extension asking for **claims behind a researched UNKNOWN** worked - `FICO` carries
`UNVERIFIED_CORE_THESIS` again, which arm 2 of E42 had lost.

## THE FUNNEL RESULT: not answerable, and that is not the same as failed

Reported headline:

```
priority   23 flags / 32 companies = 0.719 per company
control     9 flags /  8 companies = 1.125 per company
difference  +0.406 in the CONTROL's favour
```

Read alone that says the priority engine is worse than chance. It does not say that,
because the two arms were not comparable.

**Contradiction flags are almost entirely an INDUSTRY property:**

```
us_credit_scoring        3.00 flags/company
regional_banking         2.00
semiconductor_equipment  2.00
dram_hbm                 2.00
refining                 2.00
payments                 0.31
pc_insurance             0.12
life_insurance, datacenter_reits, upstream_oil_gas,
  datacenter_power_cooling                    0.00
```

And the arms landed in almost disjoint industries. Priority put **21 of its 32 picks
into payments and pc_insurance**, the two lowest-flag industries in the pool; the free
random control landed in semis, refining and credit scoring.

Predicting each arm's flag rate from its industry mix alone:

```
priority   observed 0.719   expected from industry mix 0.719
control    observed 1.125   expected from industry mix 1.125
```

**Exact, to three decimals.** Neither arm explained anything beyond where it landed.

The only stratum containing both arms is `us_credit_scoring`, where priority scored
3.00 (n=2) and control scored 3.00 (n=1) - identical, on n=3.

So the honest verdict is that **E43 did not test the priority engine.** It measured
industry composition twice. Writing this up as "priority failed" would be the pooled
number this repo keeps getting caught by - the options-desk n=369 that was 41 date
clusters, and E03's headline that only survived being re-cut per fold.

## Root cause, and it is mine

`priority.py` stratified the control draw on **sector** and market-cap tercile. Flags
vary on **industry**. Sector was the wrong stratum, and a free random draw within it
could not keep the arms comparable.

Fixed: the control is now drawn **matched to the priority arm's own industry mix**, so
the comparison is within-stratum by construction. `matched=False` reproduces the E43
design for anyone who wants to replay it. A test asserts the control can never land in
an industry the priority arm did not pick.

This does not rescue E43's numbers. The next batch tests the question for the first
time.

## What the batch did establish

**The ranking works as a ranking.** 1 VERIFIED_HIGH, 22 SUPPORTED, 9 QUALIFIED, 6 WATCH,
2 UNSUPPORTED. Nobody is excluded and the spread is readable.

**FICO ranks 39 of 40 at 29.7**, carrying `REGULATORY_IMPAIRMENT`,
`TECHNOLOGY_DISRUPTION`, `COMPETITIVE_POSITION_DETERIORATING` and
`UNVERIFIED_CORE_THESIS`, on a `STRONG` current moat with a `WEAKENING` trajectory and
+17.6% three-year revenue CAGR. That is the entire thesis of the layer in one row: a
moat that still reads strong in the accounts while deteriorating underneath.

**Four more companies show the same shape** - positive three-year revenue growth with
current evidence of a weakening moat:

| | 3y CAGR | what the current evidence says |
|---|---|---|
| PYPL | +6.3% | checkout competition, near-flat active accounts, margin contraction |
| FISV | +4.2% | Q2 merchant and financial-solutions revenue declined |
| JKHY | +7.0% | quarterly operating income and EPS contracted despite revenue growth |
| KNSL | +24.7% | gross written premiums declined despite excellent underwriting |

None of these is visible in a three-year CAGR. All four rank between 20 and 33.

## What it did not establish

**No company received an externally sourced cheapness classification.** Every
`cheapness_quality` came back UNKNOWN across 40 companies, on top of 2 of 3 in the
pilot. That is now measured on n=43 and it retires the question: the field is not
answerable from external research, and removing it from the score was right. It should
come out of the prompt entirely.

**`market_share_direction` is a RESULT, not a gap, for 34 of 40 companies** - the
researcher looked, cited what blocked it, and could not establish direction. That is the
single most common unresolved field in the layer, and it is the one that would most
change `company_specific_capture` if a peer-normalised share series existed.

**13 companies sit below the 0.80 external coverage floor** and receive no external
score: AX, CASH, CUBI, EEFT, EFX, FIS, KNSL, MA, MCY, PAYO, PBF, PLMR, SEZL. CUBI is the
extreme at 0.16 coverage and conviction 14.8.

CASH, FNB and MCY had no local filing evidence at all, as flagged before the run. That
remains a gap in our half.

## Status

Nothing promoted. `promoted` is false. This says nothing about future returns.
