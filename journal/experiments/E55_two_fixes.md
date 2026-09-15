# E55 - two fixes from E53: one shipped, one refused

Written 2026-09-06, acting on the two open items E53 left.

## Fix 1 - the blind pass is now enforced by mechanism (SHIPPED)

Codex disclosed on E53 that the conclusions file was open during initial inventory,
before pass A was frozen. It reported this unprompted and it was right to.

**That is a defect in `request.py`, not a protocol failure by the researcher.** Until now
`write()` wrote BOTH files at stage time, so our local model's SG/BQ sat on disk at a
documented path for the entire duration of the blind pass. The module docstring even
argued that splitting the payload into two files "makes the split enforceable". It does
not. It moves the honour system; it does not remove it. **A blind anyone can lift by
opening a file is not a blind.**

What changed:

- `write()` no longer writes `external_research_conclusions.json`. It stashes the
  conclusions under `EXTERNAL_ROOT/withheld/<request_id>.conclusions.json` on D:, and
  **deletes any stale release** so a previous request's answers cannot stand in for this
  one's.
- `release_conclusions(request_id, pass_a_path)` writes the real file, and only once a
  **frozen pass A exists on disk**. It raises otherwise.
- The released file records **`pass_a_sha256`**, taken at reveal time. That is what turns
  "reconciliation did not alter pass A" from something reported into something checkable:
  compare the hash against the pass A inside the final payload, and a pass A rewritten
  after the reveal no longer matches.

CLI: `python -m clab.external.request --release <request_id> --pass-a <frozen pass_a.json>`.
Six tests pin it, including that staging deletes a stale release and that the recorded
hash stops matching once pass A is edited.

**E53's own result is not re-run on the strength of this.** The breach was tested rather
than assumed: E53's external scores correlate with the local judged half at Spearman
**0.332**, the lowest of the recent batches, against the clean E51's 0.638. That is the
opposite of the anchoring signature. The mechanism exists so the question does not arise
again, not because E53 is believed to be contaminated.

## Fix 2 - a computed `competitive_position_trend` was built, validated, and REFUSED

`competitive_position_trend` has resolved 27/45 in E45, 11/52 in Energy, and **0/59 in
Utilities twice**, with Codex reporting 81 UNKNOWNs as "evidence absent" and **zero** as
"stopped short". It looked method-limited rather than effort-limited, and
`market_share_direction` had already been fixed by computing it instead of researching it.
So the obvious move was to compute this one too.

The data supports it: `operating_income_ttm` / `revenue_ttm` and their `_prior` twins
exist for **1,437 companies**, giving a two-period operating margin, and a within-industry
rank change over those two periods is exactly the E45 rank-order method. It computes for
**1,329 companies** - against 100 that have ever been researched.

**It does not work.** Validated against the 100 companies where Codex researched the field:

```
exact agreement                36 / 100 = 36%
expected by chance             34.3%      (from the two base-rate distributions)
Cohen's kappa                  0.026

confusion, researched -> computed
   STABLE        -> STABLE          20        DETERIORATING -> DETERIORATING   9
   DETERIORATING -> STABLE          16        IMPROVING     -> DETERIORATING   8
   IMPROVING     -> STABLE          15        DETERIORATING -> IMPROVING       8
   STABLE        -> IMPROVING       11        IMPROVING     -> IMPROVING       7
                                              STABLE        -> DETERIORATING   6
```

Agreement beyond chance is essentially nil, and on the directional cases it gets the sign
wrong as often as right - DETERIORATING read as IMPROVING eight times, and IMPROVING read
as DETERIORATING eight times.

**Why it fails, and it is the interesting part.** The E45 method worked because the METRIC
was chosen per industry: bank NIM, insurer combined ratio, oilfield-services operating
margin. One metric applied blindly to every industry is not that method wearing a
different hat - it is a different and much worse method. A one-year operating-margin rank
change mostly measures cycle and mix.

`market_share_direction` was computable because share is a ratio with a defensible
universal definition and a property - a common price shock cancels - that holds in every
industry. Competitive position has no such universal metric, which is precisely why a
researcher has to pick one per industry, and precisely why it stays UNKNOWN where peers
do not share one.

**So `competitive_position_trend` stays researched.** Nothing ships. The prototype is not
kept; the validation is the deliverable.

## What this settles about the field

The 0/59 in Utilities is **not a defect to fix**. It is the honest answer: regulated
utilities have no metric their peers file on a comparable basis, because authorised ROE is
set per rate case on different schedules by different commissions and rate-base CAGR moves
with capex plans that are not comparable.

It is also **not** a case for `NOT_APPLICABLE`. `applicability.py` already refused that
nomination on the grounds that `competitive_position` itself was meaningful for these
companies - it resolved for 20 of 59 in E47, and **59 of 59 in E53**. The vocabulary
applies; the trend is unmeasured. UNKNOWN is the correct value and the E31 bar holds:
meaningless, not merely unmeasured, is what earns a nomination.

## Out of scope

Neither fix predicts anything about returns. `promoted` stays false, status stays SHADOW.
