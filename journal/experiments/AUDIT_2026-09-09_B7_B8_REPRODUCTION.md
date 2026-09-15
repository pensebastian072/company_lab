# B7 / B8 reproduction — the historical audit items

Reproduced 2026-09-09 against the source and the files, before any fix. Nothing in this
document changes a result, a label or a verdict. Two of the seven claims **do not
reproduce**, and one reproduces with a correction to how it was described.

Source: `docs/AUDIT_2026-09-07_FIX_PASS.md` section B, items B7 and B8.

| item | claim | verdict |
|---|---|---|
| B7a | P/E history does not enforce availability of every TTM constituent | **CONFIRMED** |
| B7b | Completed-period EMA adds an extra period of delay | **REFUTED** |
| B7c | The −35% filter removes genuine crashes, not only bad prints | **CONFIRMED - RETIRED as accepted 2026-09-09** |
| B7d | Stock and SPY returns averaged over different valid samples | **NOT REPRODUCED** |
| B7e | The panel does not enforce index membership per company-month | **DISCLOSED, not hidden** |
| B7f | E11/E13 silently drop missing returns and reweight | **CONFIRMED** |
| B8 | E02's results file is a later rerun than its addendum discusses | **CONFIRMED** |

---

## B7a — CONFIRMED

`clab/fundamentals/pe_history.py::_ttm_eps_by_date` dates each TTM window with
`known = window[-1].filed` — the filing date of the **last** quarter in the window, not
the maximum filed date across all four. A quarter that was revised, or first disclosed
late, is therefore backdated to an earlier quarter's filing date, and the TTM EPS appears
knowable before every constituent was public.

The fix is `max(f.filed for f in window)`. It is a one-line change with a real blast
radius — every historical P/E point moves — so it belongs in a registered re-run, not a
drive-by edit. **Not fixed here.**

> **Blast radius measured 2026-09-10, and the prescription above is half wrong.** Swept the
> whole EDGAR cache: 1,561 usable blobs, 81,716 TTM windows under `view="as_first_filed"`.
> **7,798 (9.5%) are dated too early, median +203 days, p90 +300, max +678, and not one of
> the 81,716 moves earlier** — one-directional, the signature of look-ahead. 1,509 of 1,561
> companies carry at least one.
>
> But `max(f.filed for f in window)` is only the availability date **under
> `as_first_filed`**, which is what `panel.py:203` builds. The live engine
> (`engine.py:158`) uses `view="current"`, where `filed` is the latest RESTATEMENT date —
> there `max(filed)` would push a P/E point up to **1,028 days** into the future for no
> availability reason. Applied unconditionally the fix repairs the research panel and
> corrupts the live series, so the change must be view-aware.
>
> Registered with predictions in `B7A_REGISTERED_2026-09-10.md`; still not fixed here.

## B7b — REFUTED

The audit called this an extra period of delay. It is deliberate leak prevention, and the
code says so in a comment written before the audit existed:

```python
# shift(1): at any day inside a period, only PREVIOUS completed periods
# are known. Without this the current week's own close leaks in.
aligned = e.shift(1).reindex(e.index.union(close.index)).ffill()
```

Removing the shift would let the current week's own close into a signal evaluated inside
that week. **The behaviour is correct and must not be "fixed".**

## B7c — CONFIRMED, but not as described

The audit said the filter *removes daily drops*. It does not remove price rows. There are
two separate mechanisms and only one drops anything:

- `clab/sources/yf_prices.py::price_quality` **flags and does not repair** —
  "Real crashes do happen (PCG's bankruptcy, the 2020 oil collapse), so this FLAGS for
  inspection rather than silently repairing." No defect here.
- `clab/research/entry_study.py::forward_return` returns `None` when the trade window
  contains a suspect day. **The trade is dropped.**

The real finding is in the second, and it is sharper than the audit's version. The code
comment claims the rule "keeps genuine crashes in the sample where they belong" — that is
true only for crashes shallower than −35% in a single day. A genuine one-day collapse past
the threshold takes the whole trade window with it, and **dropping windows that contain
crashes removes losses, biasing measured returns upward.**

That is the same family as A4, where missing forward returns were counted as losses: both
are a silent change to which trades are in the denominator.

**RETIRED 2026-09-09 as an ACCEPTED LIMITATION, on the user's decision.** The defect is
real and is not being fixed. Two things follow and both are binding:

- **Entry-study returns are biased upward by an unmeasured amount.** The direction is
  known; the magnitude is not, because nobody has counted how many dropped windows are
  genuine crashes versus corporate actions. Any entry-study return quoted from here on
  carries that caveat.
- **This is not the H03 case.** H03 was closed because it was never a defect. H04 is
  closed while still being one. Retiring a real defect is a decision about priorities,
  not a finding about the code, and the record has to say which it is.

## B7d — NOT REPRODUCED

Ran out of scope before locating where stock and benchmark returns are averaged over
different valid samples. **No claim is made either way.** It stays open.

## B7e — DISCLOSED, not hidden

`clab/research/battery.py:545` states the limitation in the study's own output:
"Universe is today's index members: delisted and removed constituents are …". The audit
presented this as an unenforced guarantee; it is a documented survivorship limitation that
the study already reports. It remains a real limitation on what the panel establishes, and
it is not a hidden defect.

## B7f — CONFIRMED

`clab/research/e11_investability.py:135`:

```python
r = rets.iloc[i][present].dropna()
contrib.append(float(r.mean()))
```

A holding with a missing return leaves the cohort and the remaining names are implicitly
reweighted, because the mean is taken over survivors. Nothing records how many were
dropped. **Not fixed here** — the fix is to report the dropped count beside every cohort
return so a shrinking denominator is visible, which is the A4 remedy applied to portfolios.

> **Measured and fixed 2026-09-10** (`B7F_DROP_ACCOUNTING_2026-09-10.md`). Across all four
> E11 variants on the real signals: **243,171 name-months asked, 243,171 held, ZERO
> dropped.** The mechanism is real and **has never fired**, so no reported E11 or E13
> number is a survivor average.
>
> It has never fired because the universe IS survivors - E11 draws from
> `E10_returns_panel.parquet`, today's 1,497 index members, all with complete price
> series. **B7e's survivorship limitation is what gives B7f a clean bill of health**, and
> the interaction runs the dangerous way: none of the 91 delisted tickers in
> `E04_panel_nosurv.parquet` has a cached price column at all, so fixing survivorship
> without this counter would silently delete every restored name again at the portfolio
> step and report survivor returns from a "survivorship-free" panel. **Count first, then
> fix survivorship.**
>
> Fixed as disclosure only: per-month `n_asked`, `n_dropped_no_price` and
> `n_dropped_nan_return`, plus a `holdings` block per variant. No computed value moves,
> which is asserted by test rather than argued. Suite 1,329 -> 1,332.

## B8 — CONFIRMED

File timestamps settle it:

```
E02_addendum.md    2026-08-10 18:31
E02_results.md     2026-08-12 10:48
E02_results.json   2026-08-12 10:48
```

The results are **two days newer** than the addendum that interprets them, so the addendum
discusses an earlier run. The pairing is broken. The fix is to label which run each file
describes; the numbers themselves are not in question.

---

## What this changes

Nothing yet, on purpose. Four items are confirmed and all four need a registered change
rather than an edit — B7a moves every historical P/E point, B7c needs a measurement before
a rule, B7f changes reported portfolio returns, and B8 is a labelling decision about which
run is canonical.

> **Revised 2026-09-10.** Two of the four are settled and one premise was wrong. **B7f
> does NOT change reported portfolio returns** - it has never fired, and the fix is pure
> disclosure. **B8 was more than labelling**: Q1 changes verdict between the two runs, and
> the newer run's panel was never saved (`B8_E02_PAIRING_2026-09-10.md`). B7a is measured
> and registered but deliberately not applied. B7c still needs its measurement.

Two claims were wrong, and that is worth as much as the confirmations. **B7b would have
been a real regression if "fixed"** — it would have leaked the current period's close into
a signal evaluated inside that period. This is the second time in three days that acting on
an unreproduced audit item would have made the code worse; the first was my own A1
escalation.
