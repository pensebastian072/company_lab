# Chat A — next prompt, 2026-09-10

You own `clab/external/` core and the Phase A lane. Protocol: `docs/CHAT_A_B_PROTOCOL.md`.
Chat B holds the request file — it re-staged E59 batch 3 today (`1741e77`); do not touch
`journal/flags/external_research_request.json`.

Your queue as of `1ffa923` is verified complete. Every claim in your report was reproduced
independently against the store, not the report: store SHA-256 `c6322b46...` unchanged,
7,223 claims (7,099 / 65 / 59), Industrials 7 active / 20 superseded, Health Care 0 / 11,
370 tickers, no E76/E79 research applied, worktree clean, and the suite is exactly **1,329
tests, 0 failures** (dot count and exit 0 — this pytest config prints no summary line).

---

## 1. THE GAP — E79 and E76 do not carry the E65 refinement, and they are about to run

The E65 stance adjudication (`522806e`) ended with one nameable weakness:

> `key_metrics` and `structural_growth` accept a proxy where the other six fields demand
> the fact. That is a prompt refinement for the next Phase A, not a defect in this one.

Measured: **neither new prompt carries it.**

```
CODEX_E79_INDUSTRIALS_PHASE_A_RERESEARCH.md   key_metrics / structural_growth appear only
                                              in the field list and the vocabulary block.
                                              No evidence standard.
CODEX_E76_HEALTH_CARE_PHASE_A_RERESEARCH.md   states E57's HISTORY (key_metrics 0 direct /
                                              8 context / 3 unsupported) but not the RULE.
docs/CODEX_STANDARD_RULES.md                  no mention of either field.
```

The history is not the rule. E57 is told it failed; it is not told what a passing
`key_metrics` looks like. What E65 measured it returning instead:

- `key_metrics`, ~4 of 15 were risk-factor prose — "We depend on highly complex
  manufacturing processes that require strategic materials..." is a risk bullet, not a
  metric. The good ones are unambiguous: book-to-bill, remaining performance obligations,
  product backlog, component lead times.
- `structural_growth`, ~5 of 15 were indirect proxies — MLPerf submission counts, a
  sentiment index at 93.1, two objects using a BLS *employment* projection as industry
  growth. The strong ones are direct: "WFE projected to increase 6.2% to $110.8 billion".

Exposure if it ships unfixed: **27 Industrials objects + 11 Health Care objects, upstream
of 259 + 163 companies.** That is the E56 argument exactly — re-cutting three buckets
before 170 companies were researched against them is why that cost five objects instead of
170 companies.

**The call is yours and it is a real trade-off.** If Codex has not started, patch both
prompts. If it is mid-run, do not move the target — register that both runs predate the
refinement, and apply it to E63 instead. What is not acceptable is shipping them unpatched
without recording which you chose.

> **The branch is resolved, 2026-09-10 18:36.** Chat B's `8a545f4` records that Codex has
> **no token budget today**, which is why batch 3 stays staged and unhanded. Nothing is
> mid-run, so the trade-off above collapses: **patch both prompts now.** It costs a doc edit
> today and 38 objects over 422 companies if deferred.

Either way the rule belongs in `docs/CODEX_STANDARD_RULES.md`, which is yours, so the next
Phase A does not re-derive it. Both prompts are already registered in `CURRENT` in
`tests/test_codex_prompt_rules.py` — you did that; an edit keeps them there.

---

## 2. TWO NEGATIVE RESULTS — do not spend a pass reproducing these

Both measured today, 2026-09-10, from the live store and the tree.

**The external scores are current.** A dry recompute of every record with today's code,
against the same stored evidence:

```
company records            523
recompute IDENTICAL        523
stored NULL, would score     0
stored disagrees             0
would LOSE a score           0
```

`SCORE_STALENESS_2026-09-09.md`'s 128 blanks and 42 disagreements are **closed** by
`1e72f5c`, and they stayed closed through the blanking (`22e290c`) and the FDIC wiring
(`db7d5c2`), which both landed after that apply. Nothing to re-score.

**The `marketshare` defect class does not recur.** Of 41 public functions in
`clab/external/`, 12 have no caller anywhere outside their own module — and all 12 are
called *inside* it, as CLI `main` paths or local helpers:

```
finalize.apply_citation_rule / check_request / finalize_company
industry_versions.version_key      priority.draw_control      reconcile.preconditions
research_ingest.ingest_sectors / load_and_validate_sectors / validate_sector
revenue_share.load_revenue         schema.ordinal_max         taxonomy.subindustry_id
```

**No truly dead public function.** `marketshare` and `next_refresh_due` were the only two,
and both are now wired. The sweep found nothing — recorded as a negative result, not
written up as a finding.

---

## 3. THE ROADMAP IS STALE IN THREE PLACES

`docs/ROADMAP_TO_E75.md`, measured against the store:

- **Line 81 still lists "the unrecorded scoring change (Chat A, first)" as open.** Your own
  `SCORE_STALENESS_2026-09-09.md` said to remove it, and section 2 above confirms the
  follow-on apply also landed. Remove it.
- **E79 does not appear at all.** Industrials is still shown as E61 Phase A done / E62
  Phase B ready, with no sign that 20 of 27 objects are superseded.
- **The three stale journals item reads as open**, but `E54_results.md`,
  `E56_registered.md` and `E56_results.md` now each carry a dated correction block naming
  all four rates (0.134%, 1.607%, 1.22%, 0.980%) and which corpus each was true of. Either
  it is done, or the remaining part needs saying in one line.

---

## 4. THE NEXT PHASE A — and two of its object counts are wrong

Four sectors have no usable objects. Sizes from `taxonomy.industry_members` over
`scores.parquet` today, against the roadmap's numbers:

| sector | companies | units TODAY | roadmap says | singletons | unmapped | existing objects |
|---|---:|---:|---:|---:|---:|---|
| Consumer Discretionary | 193 | **28** | 27 | 4 | 0 | 0 |
| Real Estate | 105 | **16** | 14 | 1 | 0 | 1 (`datacenter_reits`, 2026-09-01, active) |
| Materials | 77 | 16 | 16 | 4 | 0 | 0 |
| Consumer Staples | 75 | 11 | 11 | 0 | 0 | 0 |

Two counts are understated, so a prompt written from the roadmap would under-build. Largest
units, which is where the E65 splitting lesson applies:

```
Consumer Discretionary   restaurants 17 | hotels_resorts_cruise_lines 17 |
                         automotive_parts_equipment 16 | homebuilding 15
Real Estate              retail_reits 19 | office_reits 11 | health_care_reits 11 |
                         industrial_reits 9
Materials                specialty_chemicals 23 | steel 9 | paper_plastic_packaging 8
Consumer Staples         packaged_foods_meats 22 | household_products 10 | soft_drinks 8
```

**Recommendation: E63 Consumer Discretionary.** 193 companies is the largest remaining
unblock, and 0 unmapped means no taxonomy prep is owed before the prompt can be written.

Two things to settle while writing it, not after:

- **The 4 singleton units.** A one-company unit is an industry object with one member, and
  the rule-1 gate deletes an object that concludes nothing. Decide up front whether a
  singleton gets an object, gets folded, or is left unbuilt — E65's lesson was that an
  empty object costs the search budget on the way to being deleted.
- **The sector brief.** All four of these sit on the **2026-09-01 baseline**, while every
  sector actually researched got a refreshed brief first (Financials 09-07, Industrials
  09-08, IT 09-09, Health Care 09-07). Is a 09-01 brief adequate Phase A input, or is a
  brief refresh part of E63? Nobody has ruled on this, and four sectors depend on the
  answer.

---

## 5. Blocked, and stays blocked

- **E58 arm B** — needs Phase B's complete `research_version`, so it waits on Chat B's
  batch 4. Three of four is not the registered scope.
- **E77** Health Care Phase B follows E76. **E62** Industrials Phase B follows E79.
- One Phase B campaign at a time: one request file, one owner, and B holds it.

## Non-negotiables

- Verify against the store, not the report.
- Advisory / SHADOW. `promoted` is false and no code path sets it true.
- Absent data is `NO_DATA` / `UNKNOWN`, never `0`.
- A default that covers a wiring error must be loud.
- Every count carries its corpus state.
- A field constant across a batch is the E30 symptom — `batch_health.constant_fields` now
  flags it; run it, and reproduce known history rather than crying wolf.
- Bulk data on `D:`. `.venv\Scripts\python.exe`, never bare `python`. Commit with the
  `-c user.email / -c user.name` form and `-F`, never `-m`, specific paths only.
