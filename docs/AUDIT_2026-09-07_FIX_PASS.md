# Fix pass — 2026-09-07 audit

Source report: `D:\company_lab_data\external\reports\FULL_HISTORY_BACKCHECK_2026-09-07.md`.

**Read this section before touching anything.** Six of the audit's claims were verified
independently against the code and the store before this document was written. The rest
were **not**. This repo's rule for an outside critique is to check it claim by claim and
neither defer nor defend — so the items below are split by verification status, and the
unverified ones are *investigations*, not fixes. Do not "fix" a finding nobody has
reproduced; that is how a correct number gets replaced by a wrong one.

**A1 was wrong when first committed and is corrected in place below.** I escalated the
audit's single bad citation into a class of 154, on the basis that 24 cached sources hold
raw PDF bytes. `verify.py` extracts PDF text on read and always did. The underlying
finding survives in a different form - token overlap is number-blind - and it touches 57
claims, not 154. The original claim is kept beside the correction rather than deleted.

## PROVENANCE WARNING - read before trusting the current tree

`clab/external/verify.py`, `clab/external/store.py`, `tests/test_external_verify.py` and
three journals are **modified and uncommitted**, and **neither session wrote them.**
`penas-00` believes they are mine; they are not. Someone or something applied a
numeric-quote guard, PDF extraction-state handling and correction notes to production
modules, and then `clab.external.verify --apply` was run against the LIVE store with that
unreviewed code in place. The store moved: 5,291 claims are now 5,148 VERIFIED_LOCAL / 85
UNVERIFIABLE / 58 SELF_ATTESTED.

The changes look correct and the new tally reproduces. That is not the same as knowing who
made them. **Before committing any of it: read the full diff, and treat the numbers in
those three journals as unverified** - they already disagree with the live store, saying
0.134% where the store says 1.607%.

Everything here is advisory / SHADOW. No fix in this document promotes anything, and
several deliberately do not change a headline verdict.

---

## A. CONFIRMED — reproduced independently, fix these

### A1. Token overlap is number-blind — a quote can verify with every figure wrong

**CORRECTED 2026-09-07, after this document was first committed. My original A1 was
wrong and is retained below so the error is visible rather than edited away.**

**What I first wrote:** that 154 claims were VERIFIED_LOCAL against un-extracted PDF
binary, because the cached bytes for 24 sources begin `%PDF-`.

**Why it was wrong:** the cache is *supposed* to hold raw PDF bytes. `verify.py` extracts
text on READ — `extract_text()` detects `%PDF-` by magic number and routes through
`_pdf_to_text()` — and that code was present at HEAD, before any of today's edits. I
inspected the cache without inspecting its consumer, concluded the verifier scored
binary, and did not check. That is the same "assert the inputs" failure it was accusing
the verifier of, pointed the other way. `penas-00` decompressed all 24 and got real prose
from 22, stopword ratios 0.231–0.317; the remaining 2 extract to zero characters and
`MIN_PAGE_CHARS` already caught them.

**The real defect, which does reproduce.** The E56 ICI claim (`c_520000000002`) is not a
substring of its source. It passed at overlap **0.818** on TOKEN OVERLAP ALONE, and token
overlap is **number-blind**: the prose matches while every figure differs. For a financial
citation that is exactly the wrong thing to be insensitive to.

Scoped across the corpus before the fix:

```
VERIFIED_LOCAL claims carrying a quote                    5,111
verbatim substrings of their source                       3,867
resting on token overlap alone                            1,244
of those, a quoted NUMBER absent from the source             57
```

**57, not 154, and nothing to do with PDF handling.**

**Status: fixed in the tree** by a numeric-subset guard
(`_numeric_tokens(quote).issubset(...)`) — see the provenance warning at the top of this
document about who wrote it. Live tally after the re-verify:

```
VERIFIED_LOCAL  5,148  97.297%
UNVERIFIABLE       85   1.607%   (quote_not_found 83, pdf_not_extracted 2)
SELF_ATTESTED      58   1.096%
```

**Remaining work:**
1. Correction notes in `E54_results.md`, `E56_registered.md` and `E56_results.md`
   currently say **0.134%**, which is stale — the honest figure is **1.607%**. Fix them,
   and state the cause as *token overlap accepting a quote whose numbers are absent*, NOT
   as verifying against binary. A note claiming the latter would itself be unreproducible.
2. Do not describe the 57 as fabrications. Several are formatting artifacts — "P. 753."
   from a table of contents, "026" from a split "2026", a differently formatted
   "$1.167 Trillion". UNVERIFIABLE means "we fetched and could not confirm", which is
   exactly true of all of them and is all that should be claimed.
3. Keep the audit correction as written: **"the quote is unsupported by what we fetched"**,
   never "the true figure is $47.6T". The audit's own replacement figures are absent from
   the fetched bytes too.

### A2. A retired newest industry version exposes an older one

Reproduced: two versions of one industry, retire the newest, and `store.industry()`
returns the **older** row. A retired unit comes back to life.

**Fix:** if the newest version is SUPERSEDED, the object is retired — return `None`
(unless `include_superseded=True`). Do not fall back down the version list. Test both.

### A3. Version `.9` / `.10` sort wrong on tied timestamps — in the EXPORT paths

`store.industry()` is **correct** (it parses the revision as an int). The two export
readers are not: both order in SQL by `last_updated DESC, version DESC`, a string sort, so
on a tied timestamp `2026-09-03.10` loses to `2026-09-03.9`. Reproduced in both.

- `clab/export/xlsx_export.py::_active_industry_rows`
- `clab/export/xlsx_external.py::active_industries`

**Fix:** order in Python on the same parsed key `store.industry()` uses, or add a parsed
sort column. One shared helper, not three implementations — this is the "ONE derivation,
ONE filter" rule.

### A4. E01 counts unavailable returns as losses

`clab/research/entry_study.py:365` — `(sig[f"ret_{h}"] > 0).mean()`. `NaN > 0` is `False`,
so missing horizons sit in the denominator as losses. Line 366 does the same for the
random control.

**Fix:** drop missing before the comparison, and report the observed-sample `n` beside
every hit rate so a shrinking denominator is visible.

**Do not overstate the correction.** The 5-year rate moves 40.1% → ~93.4% *among trades
that had a 5-year return*, and that **does not** overturn E01's failed mean-return gates
or authorise anything. Write the corrected number beside the original with both `n`s.

### A5. E13's "reproduction" predicate does not test reproduction

`clab/research/e13_topn_portfolio.py:255` — `raw["top_minus_bottom_pp"] < -10`, commented
"reproduces E05's -14.1". Any spread below −10 passes, so the v2 runs at **−25.52** and
**−33.93** are marked PASS.

**Fix:** either require numerical reproduction within a stated tolerance of −14.1, or
rename the criterion to what it actually tests (a directional check) and re-state the P4
verdicts in both v2 results files. Renaming is acceptable; silently keeping "reproduced"
is not.

### A6. E05's addendum contradicts its own table

The text says no `confirm` satisfies all three criteria and then discusses only 2 and 3.
Its `confirm=4` row: change rate **5.9%** (<12% ✓), median **11.0** months (>4 ✓), ΔIC
**+0.0022** (|·|<0.005 ✓). All three pass.

**Fix:** correct the sentence. Keep the decision. `confirm=4` was post-hoc, so it still
cannot be selected, and `confirm=2` stays shipped — but the *reason* given ("the criteria
are mutually incompatible") is false and must not be repeated.

---

## B. NOT VERIFIED — investigate before changing anything

Each needs a reproduction first. Report what you find; only then fix.

- **B1. E53 `competitive_position` is a revenue-size quartile, not a researched
  comparison.** Check how the field was actually derived for the 59. If true this is
  serious: a measured proxy wearing a researched field's name.
- **B2. E53 reconciliation marked all 59 `external_better` mechanically.** A field that is
  constant across every company is the symptom `e30_sector_audit` exists to catch.
- **B3. E53 moat-trajectory / value-capture evidence quality** — irrelevant evidence,
  pending rate requests treated as realized, UNKNOWNs ignoring relevant evidence.
  Sample-based, so quantify the rate rather than citing examples.

  **CLOSED.** Reproduced 2026-09-08 (`AUDIT_2026-09-08_B3_E53_EVIDENCE_REPRODUCTION.md`),
  remediated the same day by retiring the whole E53 arm
  (`B3_B4_REMEDIATION_DECISION_2026-09-08.md`); the store carries
  `status=SUPERSEDED` on all 59 rows. The rate it asked for was quantified 2026-09-10 in
  `B3_RATE_AND_CROSS_VERSION_2026-09-10.md`: of 48 answered pairs, **16 pending-as-realized,
  7 non-probative excerpts, 1 contradicted by its own passage, 23 relevant but unproven in
  magnitude, 1 clean** — so 50% assert a direction their evidence does not support — and
  **11 of 11 UNKNOWNs are unearned abstentions**, two with relevant evidence inside the
  attached excerpt. The same pass found the identical-receipt defect **live in E46 energy
  (12 answered pairs, not retired)**, which no one had checked for outside E53.
- **B4. E57 citations assigned to fields mechanically** — literal quotes that do not
  semantically support the field. Note A1 may explain part of this; check overlap.
- **B5. E56 was not an independent replication** — the task had already seen E54's
  distributions. If true, say so in `E56_results.md` and in `E58_registered.md`, because
  P3's whole value was that it ran in a separate session. **This one changes an
  interpretation we have already written down.**
- **B6. Overstated or stale totals** — answered-field counts, search counts, endpoint
  coverage, E57 test count. Recount from the store and correct in place with a dated note.
- **B7 - REPRODUCED 2026-09-09.** Full record:
  `journal/experiments/AUDIT_2026-09-09_B7_B8_REPRODUCTION.md`.

  Still open and confirmed: **H02 P/E availability** (dates a TTM window by
  `window[-1].filed` instead of `max(filed)`), **H08 E11/E13 reweighting** (missing
  returns dropped, mean taken over survivors).

  **Both addressed 2026-09-10.** H02 is measured and registered, not applied
  (`B7A_REGISTERED_2026-09-10.md`): 7,798 of 81,716 PIT TTM windows dated a median
  **+203 days** too early, **none** ever too late, across 1,509 of 1,561 companies - and
  the prescribed one-liner is **wrong for the live engine**, which builds `view="current"`
  where `filed` is a restatement date. H08 is measured and fixed
  (`B7F_DROP_ACCOUNTING_2026-09-10.md`): **243,171 name-months asked, zero dropped** - the
  reweighting has never fired, because the universe is survivors, and none of the 91
  delisted names has a price column at all, so **fixing survivorship without the counter
  would silently cancel itself at the portfolio step**. Fix is disclosure only; no computed
  value moves.

  **H04, the −35% rule, is RETIRED AS AN ACCEPTED LIMITATION on the user's decision
  2026-09-09.** This is NOT the H03 case. H03 was not a defect; H04 **is** one and is
  being accepted rather than fixed. What is accepted: `entry_study.forward_return`
  returns `None` when a trade window contains a single-day move past −35%, so a
  genuine one-day collapse takes the whole trade with it. Dropping windows that contain
  crashes removes losses, which **biases measured entry-study returns upward by an
  unmeasured amount**. The direction is known, the magnitude is not. Anyone quoting an
  entry-study return must carry this caveat; it is not a clean number. Reopening needs a
  measurement of how many dropped windows are genuine crashes versus corporate actions.
  Not reached: **H05 stock vs SPY samples**. Disclosed rather than hidden: **H07 index
  membership**, which `battery.py:545` already states in the study's own output.

  **H03, the EMA "extra period of delay", is CLOSED AND DELETED from this backlog on the
  user's decision 2026-09-09.** It is not a defect. The `shift(1)` is deliberate leak
  prevention with a comment saying so, and removing it would let the current week's own
  close into a signal evaluated inside that week. An item whose "fix" is a regression does
  not belong on a fix list - leaving it there only invites someone to action it later.
- **B8. E02 results file is a later rerun while its addendum discusses the original.**
  Pair the versions or label them.

  **DONE 2026-09-10** - both files labelled in place; record in
  `B8_E02_PAIRING_2026-09-10.md`. It was more than a labelling defect: **Q1 changes
  verdict between the runs** (3 of 10 years / IC +0.013 / FAIL in the addendum, 6 of 10 /
  +0.043 / `passes: true` in the results), and **the newer run's panel was never saved** -
  `E02_panel.parquet` is the addendum's 57,610 / 495, so a rebuild from the panel on disk
  silently reproduces the older run. Which run is canonical is left open as a decision.

---

## C. Rules for this pass

1. **Verify, then fix.** Anything in section B gets a reproduction in the journal before a
   line of production code moves.
2. **Corrections go BESIDE the original number, dated, never over it.** A results file is
   a record of what was believed when. `E01`, `E05`, `E13` all keep their original figures
   with a correction note.
3. **No verdict changes.** A4 does not rescue E01. A6 does not select `confirm=4`. A1 does
   not invalidate the research, only our confidence in its verification.
4. **Assert the inputs.** A1 existed because nobody checked that a "verified" source was
   text. When a check returns clean, confirm it can return dirty.
5. **Advisory / SHADOW throughout.** `promoted` stays false.
6. Run the full suite after each item. Commit per item, not one large commit.

## D. Suggested order

A1 first — it is the only one that changes what we believe about the evidence base, and
the re-verify wants to run before more batches land. Then A2/A3 (small, same area, one
shared helper). Then A4/A5/A6 (documentation corrections, no behaviour change). Then
section B, in the order B1, B2, B5, B6, then the historical ones.
