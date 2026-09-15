# B7a - registered: the P/E availability fix, and its measured blast radius

Registered 2026-09-10, **before** any code change or re-run. Advisory / SHADOW;
`promoted` is false. Nothing in `clab/` has been edited by this document.

## Why this is registered rather than edited

The 2026-09-09 reproduction confirmed B7a and stopped there, deliberately:

> The fix is `max(f.filed for f in window)`. It is a one-line change with a real blast
> radius - every historical P/E point moves - so it belongs in a registered re-run, not a
> drive-by edit. **Not fixed here.**

It named the blast radius without measuring it. That measurement is below, and it changes
what the re-run should be.

## The defect

`clab/fundamentals/pe_history.py::_ttm_eps_by_date` dates each four-quarter TTM window by
`known = window[-1].filed` - the filing date of the **last quarter in the window**, not the
latest filing date across all four. When an earlier constituent was first disclosed or
revised later than the last quarter's filing, the TTM sum is dated to a day on which it was
not yet computable.

## Measured, over the whole EDGAR cache

1,606 cached companyfacts blobs, 1,561 usable (45 carry fewer than four consecutive
quarters of diluted EPS), 1.1 minutes to sweep. The question asked of each TTM window: does
`max(f.filed for f in window)` differ from `window[-1].filed`, and by how many days.

| | `view="as_first_filed"` (the PIT panel) | `view="current"` (live scoring) |
|---|---:|---:|
| TTM windows built | 81,716 | 81,546 |
| windows dated too early | **7,798 = 9.5%** | **17,774 = 21.8%** |
| median shift | **+203 days** | +203 days |
| p90 shift | +300 days | +297 days |
| max shift | +678 days | +1,028 days |
| windows that move EARLIER | **0** | **0** |
| companies with at least one | **1,509 / 1,561** | 1,542 / 1,561 |

Three things in that table matter more than the headline rate.

**The error is one-directional.** Not a single window of 81,716 moves earlier. Every
mis-dating makes data look available sooner than it was, which is the signature of
look-ahead rather than of noise.

**The median shift is 203 days**, not a few days. That is more than two quarters. A P/E
point used at a month-end was, in the median affected case, not computable until roughly
seven months later.

**It is nearly universal across companies.** 1,509 of 1,561 companies carry at least one
mis-dated window, so this is not a handful of serial restaters that could be excluded.

## The two views are not the same defect, and the audit conflated them

`clab/research/panel.py:203` builds P/E history with `view="as_first_filed"`; the live
scoring engine at `clab/runner/engine.py:158` uses the default `view="current"`.

- Under **`as_first_filed`**, every `filed` is a first-disclosure date, so
  `max(f.filed for f in window)` is exactly the availability date. The fix is correct as
  written, and the 9.5% is genuine look-ahead in the panel that E02 / E03 / E05 / E08 rank
  on.
- Under **`current`**, every `filed` is the date of the *latest restatement* of that
  quarter. `max(filed)` there is not an availability date at all - it is "when the last
  restatement of any constituent appeared", which would push a live P/E point up to 1,028
  days into the future for no availability reason.

**So the one-line fix is right for one caller and wrong for the other.** Applying
`max(f.filed for f in window)` unconditionally would fix the research panel and corrupt the
live scoring series. The registered change must therefore be view-aware, not the literal
one-liner the reproduction proposed.

This is the third time in four days that an audit item's stated fix has been wrong in a way
only a measurement exposed: A1's class of 154, B7b's "extra delay" that was deliberate leak
prevention, and now this. **The finding reproduced; the prescription did not.**

## The registered change

```python
# in _ttm_eps_by_date, replace:
known = window[-1].filed
# with the latest first-disclosure across the window, which is only meaningful
# when the facts themselves are first-filed:
known = max((f.filed for f in window if f.filed), default=None) \
        if view == "as_first_filed" else window[-1].filed
```

Exact form to be settled in implementation; the registered commitment is that **the PIT
path takes the max and the current-view path is left alone**, and that the choice is keyed
on the view rather than applied blind.

## Pre-registered predictions

Written before the re-run. Each is falsifiable and none is a hedge.

1. **P1.** The rebuilt PIT panel loses P/E coverage at early month-ends. Predicted:
   `pe_pctile_own` non-null count falls by **2-6%** of panel rows. Refuted below 1% or
   above 10%.
2. **P2.** E02's Q1 mean monthly IC **falls**, because removing look-ahead removes
   information that was not available. Predicted direction: down. Magnitude not predicted.
3. **P3.** The direction in P2 holds in a **majority of individual years**, not just in the
   pooled number. A pooled move with fewer than 6 of 10 years agreeing is a sample-skew
   result and will be reported as such.
4. **P4.** E05's top-decile three-year excess return does **not** improve past zero. The
   -7.6% median is not an artifact of this defect. Refuted if it turns positive.
5. **P5.** The live book is **unchanged**. The scoring engine uses `view="current"`, which
   this change does not touch, so `data\scores.parquet` must be byte-identical after the
   change. **Any movement in the live book means the fix leaked into the wrong caller** and
   is a bug, not a result.

P5 is the one that matters operationally: it is the regression test, stated in advance.

## Cost and order

```powershell
# panel rebuild is the expensive half; study re-runs are cheap
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_studies.ps1
```

About **50 minutes** for the panel, then E02 / E03 / E05 / E08 and the workbook refresh.
Deterministic - no LLM, no network beyond the caches on D:. The box crashes daily and this
exceeds an hour end to end, so it belongs in a repeat-triggered Scheduled Task with
checkpoints rather than a foreground process tree.

**Batch it.** This invalidates the panel, and so does B7f (E11/E13 reweighting over
survivors). Two panel-invalidating changes should pay the 50 minutes once, not twice. B7f
must therefore be decided before this runs, not after.

> **Superseded the same day.** B7f was measured and fixed
> (`B7F_DROP_ACCOUNTING_2026-09-10.md`) and it turns out **not** to invalidate the panel:
> the reweighting has never fired in 243,171 name-months, so the fix is pure disclosure and
> moves no computed value. There is nothing left to batch with. **B7a can run alone**, and
> the only remaining prerequisite is scheduling the 50 minutes somewhere the box's daily
> crash cannot take it.

## What this does and does not establish

It establishes the size and direction of the defect - 9.5% of PIT TTM windows dated a
median 203 days early, never late, across 1,509 of 1,561 companies - and that the proposed
one-line fix is correct for the research panel and wrong for the live engine.

It establishes nothing about what the corrected panel will show. No study has been re-run,
no verdict moves, and the predictions above are predictions. E05's top decile still ran
-7.6% median three-year excess against SPY and E03 still puts 95.6% of ranking power in
sector selection.
