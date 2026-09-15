# B7f - the reweighting that has never fired, and the fix that stops it mattering later

Run 2026-09-10. Advisory / SHADOW; `promoted` is false. **No return number changes**, and
that is provable rather than asserted - see the regression test below.

## The defect, as confirmed

`clab/research/e11_investability.py::cohort_series` averages a cohort's monthly return over
whichever holdings have a return that month:

```python
present = [t for t in names if t in rets.columns]
r = rets.iloc[i][present].dropna()
contrib.append(float(r.mean()))
```

Two silent losses, not one. A name missing from `rets.columns` never had a price series;
a name present but `NaN` did not trade that month. Either way it leaves the cohort, the
survivors are implicitly reweighted, and nothing recorded how many left. `n_names` counted
who stayed, never who was asked.

E13 consumes the same function (`e13_topn_portfolio.py:203`), which is why the audit named
both.

## Measured: it has never fired

Ran the real construction across all four E11 variants, on the real signals and the real
monthly returns.

| variant | name-months asked | held | dropped |
|---|---:|---:|---:|
| `sp600_insiders_ge_1` | 120,408 | 120,408 | **0** |
| `sp600_insiders_ge_3` | 21,553 | 21,553 | **0** |
| `sp500_insiders_ge_1` | 91,260 | 91,260 | **0** |
| `sp500_insiders_ge_3` | 9,950 | 9,950 | **0** |
| **total** | **243,171** | **243,171** | **0** |

Zero missing columns, zero NaN returns, worst month 0.0%. **No reported E11 or E13 number
is a survivor average.** The confirmed code path is real and has never executed.

That is worth stating plainly because the audit confirmed the mechanism and stopped. A
mechanism that cannot fire on the data in hand is a latent defect, not a live one, and
calling it live would have been the same error as the three prescriptions that did not
survive measurement.

## Why it has never fired, and when it will

Because the universe is survivors. E11 draws its names from `E10_returns_panel.parquet` -
1,497 tickers, today's index members - and every one of them has a complete price series
by construction. Nothing can go missing when the universe is defined as the names that
did not go missing.

**This is B7e's documented survivorship limitation producing a clean bill of health for
B7f.** The two defects are not independent, and the interaction runs the dangerous way:

`E04_panel_nosurv.parquet` carries **91 tickers that E11's universe does not** - ABMD, ADS,
AGN, AIV, ALXN, ATVI, BBBY, CA, CELG and the rest of the acquired and delisted. Checked
directly: **not one of those 91 has a cached price column at all.** `monthly_returns`
returns zero columns for them.

So if the survivorship fix were applied to the universe and B7f were left as it was, every
delisted name added at the universe step would be **silently deleted again at the portfolio
step**, and the "survivorship-free" study would quietly report survivor-only returns. The
fix would cancel itself, the numbers would barely move, and the natural reading would be
that survivorship never mattered here.

**Order matters: B7f has to be counted before survivorship is fixed, not after.** That is
the whole value of this item, and it is not what the original finding was about.

## What was changed

Counting only. `cohort_series` now records, per month:

- `n_asked` - holdings requested across active cohorts
- `n_dropped_no_price` - no price column (a universe problem)
- `n_dropped_nan_return` - column present, return missing (a data problem)

kept separate, because pooling them hides which one is growing. Each E11 variant's output
gained a `holdings` block carrying the same totals and a `dropped_share`, so a reweighted
return can no longer be read without its denominator.

**Returns are untouched**, and `test_counting_the_drops_does_not_move_the_returns` asserts
the arithmetic directly rather than trusting the diff.

The test that covered this before was named
`test_a_name_with_no_price_does_not_silently_shrink_the_cohort` - and it only asserted the
surviving return. The cohort really did shrink two names to one, the mean really was
reweighted, and nothing in the output said so. **The test's name described the fix that had
not been written.** It now asserts the count, and two more cover the NaN case and the
no-op guarantee.

## The review caught the hole in my own argument

`quant-reviewer` returned PASS with no blockers, and verified the no-op two ways - by
reading the branch predicates, and by running the pre-change function against the new one
over 300 randomised trials (0 mismatches on `ret`, `n_names`, `n_cohorts`, `in_market`).

It also found that the counters **could not see the loss this document is about.**
`if j is None or not names: continue` runs *before* `n_asked` is touched, so a cohort whose
signal date is absent from the price index contributes nothing to any counter and vanishes
silently. That is precisely the survivorship channel argued above: a delisted name has no
cached prices, so `monthly_returns` creates no column **and possibly no month**. The
name-level disclosure would have read perfectly clean while whole cohorts disappeared - the
same failure the fix exists to prevent, one level up.

Fixed: `n_cohorts_unresolvable_date` per month, surfaced as `cohorts_unresolvable_date` in
each variant's `holdings` block.

Three tests were also weaker than their names. `test_counting_the_drops_does_not_move_the_returns`
exercised **only the zero-drop path**, which is not the path the change touched, and nothing
pinned the partition invariant `asked == held + no_price + nan_return` - the property that
makes the counts trustworthy, and one a future edit could break silently by moving the
`n_nan_return` increment below the `r.empty` guard. Both now asserted, along with the
unresolvable-date channel.

This item adds **6 tests** to `tests/test_e11_investability.py`, 10 to 16. The full
suite is green at **1,338** — that total also carries tests Chat A added to
`test_external_taxonomy.py` in the same working tree today, so it is not this
change's delta.

**Known and left alone:** E13 and E14 call the same `cohort_series` and get the columns but
surface no `holdings` block, so the disclosure is E11-only today. End-of-sample truncation
(cohorts opened in the last `HOLD_MONTHS`) is still not disclosed either. Both are
recorded here rather than fixed, because neither is on the survivorship path this item
exists to protect.

## This unblocks B7a

`B7A_REGISTERED_2026-09-10.md` said to batch B7a's 50-minute panel rebuild with B7f,
because both were expected to invalidate the panel. **B7f does not.** It changes no
computed value, so it needs no re-run and B7a can be run on its own schedule.

## What this does and does not establish

It establishes that the reweighting has never occurred in 243,171 name-months, that the
reason is survivorship rather than correctness, that a survivorship fix applied alone would
have been silently cancelled at the portfolio step, and that the loss is now counted.

It establishes nothing about whether E11's or E13's returns are right. They rest on a
survivor universe, which `battery.py:545` already discloses and which this does not
repair. `promoted` stays false.
