# The acceptance gate refuses every batch, good or bad — one accessor, wrong level

Found 2026-09-11 by the Claude lane, by running the new gate against a batch whose verdict
was already known. `clab/external/acceptance.py` is Chat A's, uncommitted at the time of
writing; **nothing in it was edited here.** This is the measurement.

## Two cases, same false verdict

```
E59 batch 3   9e243401d2fb0d1e380e.json   42 companies   REFUSED - constant_fields
E47 utilities f92abdf0887e91cd072d.json   59 companies   REFUSED - constant_fields
```

The second was researched, accepted and ingested weeks ago. Both are refused with the same
sentence:

> rank-order field(s) all-UNKNOWN across the whole batch: competitive_position (42 rows),
> competitive_position_trend (42 rows), moat_trajectory (42 rows),
> company_specific_capture (42 rows)

That is false for both. Batch 3 answers `competitive_position` **35 of 42**,
`moat_trajectory` 26, `competitive_position_trend` 16, `company_specific_capture` 5 — which
is exactly the measurement this lane used to reject it for a *different* reason. A gate that
refuses everything is no better than one that refuses nothing, and worse in practice, because
the next person learns to pass `--no-fetch` and skim past it.

## Root cause, one line

`acceptance.py::_payload_rows`:

```python
cats = c.get("categoricals") or c          # payload nests them under "pass_a"
```

A Codex payload's company record carries `ticker`, `research_depth`, **`pass_a`**, `claims`,
`refresh_class`, `next_suggested_refresh`, `pass_b`. There is no `categoricals` key and no
top-level ordinal, so the `or c` fallback silently yields a record with every ordinal absent,
which reads as UNKNOWN.

`finalize.py` is where the two shapes diverge, and it is worth stating precisely because the
fix should follow it rather than guess:

```
finalize.py:147   pass_a = row.get("pass_a") or {}
finalize.py:151   cats = {k: v for k, v in pass_a.items() if k in ALLOWED_CATEGORICALS}
finalize.py:193   "categoricals": cats,          <- the NORMALISED shape, after finalize
```

So `categoricals` is the post-finalizer shape and `pass_a` is the wire shape. The gate runs
**before** ingest on the wire shape, and reads the post-ingest key.

The same omission breaks sector detection: the payload record has no `sector_id`, so
`sectors.most_common(1)` is empty, `sector_id` is None, and the four-field check degrades to
`SKIP: no previous ? batch to compare against` — the one check written specifically to catch
batch 3's regression never ran.

## Fix

```python
cats = c.get("categoricals") or c.get("pass_a") or c
```

and resolve the sector per row through `taxonomy.resolve(ticker, ...)` or from the frozen
request's roster, since the payload does not carry it.

**The rule underneath it, which is the part worth keeping:** an acceptance check must read a
payload through the *same accessor the finalizer uses*, or it grades a different object than
the one that lands. Two readers of one wire format is the `LLM_COMPONENTS` failure in a new
place — one name, two meanings, and nothing checking that they agree.

Suggested test, since the gate's own test suite passed while this was live: assert that
`_payload_rows` on a real payload recovers a KNOWN non-zero fill — batch 3's
`competitive_position` 35 of 42 is a good fixture precisely because that batch is otherwise
bad. A test that only ever feeds the gate synthetic rows in the post-finalizer shape cannot
see this class of bug.

## Status of the verdict on batch 3

Unchanged and independent of this. Batch 3 is refused for the collapse measured in
`E59_B3_REJECTION_2026-09-11.md` — four-field fill 87.5% → 48.8%, `pricing_power` 100% → 33%,
against a b2 whose 247 claims on those fields all pass exact containment. The gate happening
to refuse it for a bogus reason is a coincidence, not a confirmation.

---

# Fixed 2026-09-12 — and the corrected gate finds a real defect in E47

`_payload_rows` now reads through `_ROW_FIELD_HOLDERS = ("categoricals", "pass_a")`,
merged rather than picked, and resolves `sector_id` / `industry_id` per row through
`taxonomy.resolve` off the book when the payload omits them (it always does — ids are
assigned on the way in). Six tests added, all in the **wire** shape, since the existing
twenty-four were written in the post-finalizer shape and that is precisely why they could
not see this.

`categoricals` is first, not `pass_a` as a one-line fix would give: where a row carries
both, `categoricals` is the filtered shape `finalize.py:193` writes and the store holds,
so it is the object that lands and therefore the object to grade.

## What the corrected gate says

```
E59 batch 3   9e243401d2fb0d1e380e   REFUSED - four_field_fill
              financials 75.9% -> 48.8%, within-industry delta -0.341 (refuses at -0.20)
              constant_fields now PASSES: no field constant across 42 rows
E47 utilities f92abdf0887e91cd072d   REFUSED - constant_fields
              competitive_position_trend all-UNKNOWN across 59 rows
              four_field_fill: 65.7%, SKIP (no previous utilities batch to compare)
```

Batch 3 is now refused **by the check written for it**, on the regression
`E59_B3_REJECTION_2026-09-11.md` measured independently, at the delta that document
reports. The coincidental refusal is gone.

## The correction this document needs

This entry said the all-UNKNOWN sentence was "false for both". It was false for batch 3 on
all four fields, and false for E47 on three of four. **On E47's
`competitive_position_trend` it was true, and remains true after the fix:**

```
E47 f92abdf0, 59 utilities, from the payload itself
  moat_trajectory             STABLE 22 · STRENGTHENING 14 · WEAKENING 10 · UNKNOWN 11
  competitive_position        LAGGARD 17 · STRONG_NUMBER_TWO 15 · LEADER 14 · CHALLENGER 13
                              UNKNOWN 0  <- 59 of 59 answered
  competitive_position_trend  UNKNOWN 59  <- 0 of 59 answered
  company_specific_capture    MODERATE 27 · HIGH 10 · LOW 11 · UNKNOWN 11
```

A batch that places every one of 59 companies on the competitive ladder and then declines,
59 times out of 59, to say which way they are moving, is not a sector answering honestly.
`competitive_position` at 100% is what rules out the "utilities are genuinely
unknowable" reading — the same researcher, on the same companies, in the same batch,
answered the harder field and left the easier one empty. This is the E43–E46 abstention
pattern in a single field, and nothing had named it.

**So the Master Plan's Phase 0 criterion is wrong.** It reads:

> must ACCEPT E47 `f92abdf0…` and REFUSE E59-b3 `9e243401…` on `four_field_fill`

The second half is now met exactly. The first half cannot be met without weakening
`constant_fields` to let a dead rank-order field through, which is the one thing that check
exists to stop. The criterion was written from the belief that E47 was clean, not from a
measurement of E47. It is the criterion that is wrong, and the gate is left as it is.

This costs nothing operationally: E47 was never the plan for Utilities. Utilities has **0
of 59** companies live in the store today, and Phase 1 already routes it through E80
Utilities Phase B (`docs/CODEX_E80_UTILITIES_PHASEB.md`) rather than E47. What changes is
that restoring Utilities by replaying E47 is now known to import a field that is dead in
all 59 rows, and the gate will say so before it lands rather than after.

## Corpus state at the same moment, for the record

```
external_claim          7,335
  match_mode     exact 6,402 · no_whitespace 589 · overlap_only 134
                 numeric_mismatch 9 · absent 4 · NULL 197
  verify_status  VERIFIED_LOCAL 7,124 · UNVERIFIABLE 149 · SELF_ATTESTED 62
```

`match_mode` was NULL on all 7,335 at plan approval, so the restate pass ran and the 146
unlocatable claims were settled — they are the 147 `overlap_only` / `numeric_mismatch` /
`absent` rows, every one demoted to UNVERIFIABLE rather than left certified. Of the 197
still NULL, **133 carry no quote at all** (computed claims from `revenue_share` and
`fdic_sod` — nothing to contain, correctly NULL) and **64 carry a quote and were never
tested**, all from batches dated 2026-09-01, -02, -07 and -09. None of this session's
claims are among them.
