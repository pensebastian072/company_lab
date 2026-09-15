# E30 - does every sub-test do any work, in every sector?

Started 2026-08-25 at the user's request: a pure review-and-improve pass over every
metric in every sector. Instrument is `clab/research/e30_sector_audit.py`; raw output
`E30_results.json`.

**What this pass can and cannot deliver.** It can prove that every sub-test is computed
correctly, applies to the sector it is scoring, and actually separates one company from
another there. It **cannot** show that any of it predicts anything - there is no
forward-return grader and there are 5 of the ~50 weekly snapshots it needs. "100%
correct" here means internally sound, not validated. `promoted` stays false.

## The instrument

473 (sub-test x sector) cells over 1,501 companies and 11 sectors at n >= 30. Four
questions a coverage figure cannot answer:

1. **Is it answered?** scored / no_data / not_applicable / data_quality_fail.
2. **Does it DISCRIMINATE?** A sub-test where 98% of a sector earns the same number
   separates nobody, yet still moves the composite and still sits in the coverage
   denominator looking like evidence. This is the market-state workbook's failure -
   6 of 12 layers constant, so a "12-layer tally" was a 6-layer tally plus an offset.
3. **Is a suppression DEAD?** - nominated, never fires.
4. **Is a suppression MISSING?** - NO_DATA for a whole sector, not nominated.

Two of my own flags were wrong on the first run and were fixed before anything was read:
`DEAD_NA_NOMINATION` used the whole sector as the denominator when only some companies
carry the nominating profile (Energy holds two FINANCIAL filers), which flagged 83 cells
where the rule was firing exactly as designed; and E19's synthetic `*_unassessed` weights
are not questions and cannot be suppressed. 137 flags became 79.

---

## FIXED 1 - `bs_dilution` earned nothing in all eleven sectors

**Symptom.** Mean earned share 0.00-0.04 in every sector; in Energy all 71 companies
scored 0 and the sub-test had exactly **one** distinct value. A whole point of the
framework, constant across the entire universe.

**Cause.** `diluted_shares_ttm` goes through `ttm_share_count`, which is E28's filter for
a poisoned row - AAPL's FY 10-K files a quarter-duration `diluted_shares` of
**-47,029,000**, a *change* in shares wearing a count's clothes. `diluted_shares_ttm_prior`
did not: it kept a hand-rolled `sum(facts[-4:]) / 4.0`. Two code paths for one quantity
and only one of them filtered, so the prior window came out ~25% light.

**Consequence.** Median `dilution_yoy` was **+32.5%** across 1,469 companies - almost
exactly 4/3 - so every company read as issuing a third of its shares a year. AAPL, MSFT,
KO, JPM and NVDA are all shrinking their share counts and all scored zero.

| | before | after |
|---|---:|---:|
| median `dilution_yoy` | +32.5% | -0.9% |
| AAPL | +31.3% | **-2.2%** |
| JPM | +29.6% | **-3.5%** |
| share earning the point | 3.1% | **78.7%** |

**Fix.** One derivation, one filter, every window. Pinned by
`tests/test_dilution_prior_window.py`, which keeps the old expression in the test so the
defect cannot come back unrecognised.

---

## FIXED 2 - revenue was a FRAGMENT for 1 company in 22, and 1 in 6 of Real Estate

The larger finding, and it was reached by asking why Real Estate's margins were failing
their plausibility bounds so often.

**Symptom.** Impossible figures. EQR (Equity Residential) `revenue_ttm` **$216,000**
against a real ~$2.9bn, an operating margin of **5,373** and an FCF margin of 7,232.
Healthpeak with operating income four times larger than revenue. A screen for
"operating income > 1.5x revenue, or market cap > 100x revenue" found **17.0% of Real
Estate and 16.0% of Financials**, against 0.0% for Industrials, Materials, Consumer
Staples and Consumer Discretionary.

**Two separate causes, both one guard short of correct.**

**(a) Chain order preferred a fragment.** `tags.resolve` merges the chain and lets the
earliest position win every period it covers, because chain order encodes semantic
preference. For a REIT that is backwards: ASC 842 lease income is not ASC 606 contract
revenue, so `RevenueFromContractWithCustomerIncludingAssessedTax` is structurally a minor
line for the whole sector. EQR files it at **$384,000** - management fees - beside
`Revenues` of **$2,699,485,000**. The fragment won.

**(b) The bank substitute never ran.** `interest_income_operating + noninterest_income`
existed, was correct, and was gated on `len(revenue) == 0`. FITB files no `Revenues`, but
it does file $617m of contract revenue (card and deposit fees), so the chain came back
non-empty and the substitute never fired. FITB's real revenue is $11.35bn of interest and
dividend income plus $3.49bn of non-interest income.

**The fix, by mechanism rather than by tuning.** Every revenue tag in one filing is either
the consolidated total or a component of it, and **a component cannot exceed its own
total**. So a fresh tag that dominates on the periods the two actually share is the
consolidated line, and chain order yields to it. The same sentence fixes both: *an empty
series is a fallback; a series dwarfed by a more consolidated measurement of the same
thing is a bug.* Freshness is still decided first, so the NVDA retired-tag rule is
untouched.

**Validated before committing.** A/B over a 220-company random sample: **10 changed
(4.5%) and every single one increased.** Zero decreases is what the mechanism predicts -
the change can only ever move toward the consolidated line - and it is the evidence that
this is a repair rather than a re-tuning.

| company | sector | before | after | |
|---|---|---:|---:|---:|
| Essex Property Trust | Real Estate | $9.3m | $1.93bn | **x207** |
| Phillips Edison | Real Estate | $14.2m | $751m | x53 |
| **Humana** | Health Care | **$6.18bn** | **$137.2bn** | x22 |
| Ally Financial | Financials | $1.23bn | $8.68bn | x7.1 |
| Healthpeak | Real Estate | $723m | $2.95bn | x4.1 |
| SBA Communications | Real Estate | $894m | $2.87bn | x3.2 |
| United Rentals | Industrials | $6.95bn | $16.4bn | x2.4 |

**This is not a REIT-and-bank story.** Humana was ranked on a revenue number 22x too
small, and United Rentals is a plain STANDARD-profile industrial. Every margin, growth
rate, revenue multiple and reverse DCF for these companies was computed on the wrong
denominator.

It also looked, at this point in the session, as though it might reframe E29 - which
closed six hours earlier having found the rubric was not the problem. E29 never asked
whether the NUMBERS were right, and for one REIT in six they were not. **The re-score
below shows that guess was wrong too**, and it is recorded here rather than quietly
dropped.

---

## OPEN 1 - the profiles say a metric is meaningless and the scorecard scores it anyway

42 cells, and the biggest unresolved question in the framework.

`SectorProfile.resolve_status` grants NOT_APPLICABLE only when the profile nominates the
sub-test **AND** the value is genuinely absent. That two-part test is deliberate and
load-bearing: UNH is nominally a FINANCIAL filer but files a full income statement, so its
margins are scored rather than suppressed.

But it means a suppression whose reason is **"meaningless"** rather than **"missing"**
almost never fires, because the ratio is nearly always computable:

| sub-test | sector | profile says | scored anyway |
|---|---|---|---:|
| `fe_roic` | Financials | not defined for a bank | **91.4%** |
| `va_ev_sales_vs_peers` | Financials | EV is not defined for a bank | **93.0%** |
| `bs_interest_coverage` | Financials | interest is cost of goods, not a solvency burden | **93.8%** |
| `fe_margin_expansion` | Real Estate | no gross margin line | **84.0%** |
| `bs_net_debt_ebitda` | Financials | deposits are funding, not leverage | **82.8%** |
| `va_reverse_dcf` | Financials | undefined | 75.5% |

The FINANCIAL profile's note says these "are not defined". 93% of banks carry a score for
them. The profile is documentation that mostly does not run, and a scorecard that presents
an EV/Sales percentile for a bank is presenting a measured, meaningless number as
evidence.

**This needs its own registration and it is NOT done here.** It is a rubric change, it
moves points out of both the numerator and the coverage denominator, and its direction on
the composite is ambiguous rather than obviously favourable. Note the contrast with E29:
that refused to add suppressions justified by a **null rate**; this one would add them
justified by an **accounting fact** - EV genuinely is not defined for a bank. Those are
different arguments and the second is much stronger, which is exactly why it needs the
same discipline rather than less.

## OPEN 2 - sub-tests that separate nobody inside one sector

Real, and much smaller than they looked once `bs_dilution` was removed from the list.

| sub-test | sector | shape |
|---|---|---|
| `bs_cash_vs_opex` | Utilities | 96% score ZERO - a regulated utility runs on revolvers, not cash |
| `bs_current_ratio` | Materials | 96% score MAX |
| `bs_maturity_wall` | Communication Services | 95% score MAX |

Each is one point. A constant sub-test is not necessarily wrong - it can be a true
statement about a sector - but it contributes weight without information, and per-sector
thresholds are a rubric change. Deferred, with the same reasoning E29 used.

## FIXED 3 - a lessor's rent is not contract revenue, so the chain never saw it

EQR's `Revenues` **and** its contract-revenue tag both stop at **2020-03-31**, while
`OperatingLeaseLeaseIncome` runs to 2026-06-30. ASC 842 lease income appears under no
member of the revenue chain, so the company was scored on six-year-old revenue and its
growth rates described 2020. Measured over 251 filings, **2.0% carry a revenue series
stranded more than 400 days behind their own net income and cash flow.**

A `lease_income` chain was added and deliberately kept OUT of `revenue`: for an ordinary
filer lease income is a small line (FITB files $85m against $14.9bn) and merging it in
would let a component fill a gap and pass as a total.

**The A/B killed two drafts before anything was committed**, and the second one matters:

1. dominance + freshness replaced a $7.56bn series with a $2.99bn one on **no shared
   period at all**, and turned another company's revenue into `None`.
2. With overlap and TTM guards added, **Iron Mountain still broke**: its storage rent runs
   **1.72x** its contract-revenue tag over their shared periods, so dominance swapped the
   total for a half.
3. Final rule: **dominance is not used here at all.** "A component cannot exceed its
   total" holds INSIDE the revenue chain, where every member is a candidate total. Lease
   income is not a candidate total - for a filer with both it is one half of the business.
   The only trigger is the stranded case, and the series must still overlap the incumbent,
   agree with it there (0.67x-1.5x), and yield a usable TTM.

Final A/B: **0 changes** across 260 filings, EQR fixed ($216,000 -> $3,129,217,000,
period end 2020-03-31 -> 2026-06-30), Iron Mountain preserved at $7,562,471,000.

---

## FIXED 4 - a stranded income-statement line, withheld while its derivation sat unused

The same shape as FIXED 3, one line down. A filer that stops tagging `GrossProfit` or
`OperatingIncomeLoss` leaves a **full-length** series stranded years in the past. It
passes the existing length test (which was written for COST's 4-row partial disclosure),
then pairs a 2020 numerator with 2026 revenue - and `RATIO_PERIOD_MAX_GAP_DAYS` correctly
refuses the ratio. So the point was **withheld while `revenue - cogs`, or the EBIT
reconstruction, sat there current and usable**.

Measured over 235 filings: `GrossProfit` stale by more than 400 days against revenue for
**6.4%** of filers (absent for 52.8%), `OperatingIncomeLoss` for **4.7%** (absent for
17.0%). One sampled filer's operating-income series ends **2010-12-31**.

Both derivations already existed and were gated on ABSENCE (`len(...) == 0`) or on
LENGTH. They now also fire on the stranded case, through the same guard the lessor fix
needed: the replacement must reach further **and** agree with the incumbent where the two
overlap, or it is measuring something else.

A/B over 240 filings: **8 quality failures resolved, 0 newly failing**, and the recovered
numbers check against reality rather than merely existing - BMY 70.2% gross / 27.7%
operating, Nucor 15.5% / 11.8%, H&R Block 23.7% operating, Hartford 18.0%.

---

## The re-score: what the four fixes actually did

Full re-score of sp500 + sp400 + sp600 (1,500 of 1,501; the `xsect` tier refused itself
on an unrelated CIK-dedupe guard, correctly).

| check | before | after |
|---|---:|---:|
| `bs_dilution` earning its point | 3.1% | **78.7%** |
| median `dilution_yoy` | +32.5% | **-0.6%** |
| Real Estate with operating income > 1.5x revenue | 17.0% | **2.8%** |
| Financials, same | 16.0% | **1.2%** |
| `data_quality_fail` sub-tests | 502 | **307** |
| audit cells flagged | 79 | **67** |
| `CONSTANT_ZERO` cells | 12 | **1** |

### And now the part that matters more: it did NOT close the sector gap

| sector | median score | median coverage |
|---|---:|---:|
| Information Technology | 59 -> 61 | 0.936 -> 0.936 |
| Industrials | 53 -> 54 | 0.925 -> 0.925 |
| Financials | 47 -> 48 | 0.855 -> **0.861** |
| **Real Estate** | **33 -> 34** | 0.778 -> **0.793** |
| Utilities | 38 -> 39 | 0.887 -> 0.887 |
| Energy | 40 -> 41 | 0.808 -> **0.830** |
| universe | 48 -> 49 | |

(coverage after all four fixes; the score column was already final after the first three)

**17 of 1,501 bands changed.** The largest individual moves are small banks and REITs at
+6 to +10 points - NBTB 43 -> 53, CUBI 40 -> 50, CTRE 28 -> 36, AMT 54 -> 61.

I expected more, and said so in the session before measuring: the working guess was that
Real Estate's low scores were substantially a data defect. **They are not.** The bugs were
severe *per company* - EQR's revenue was wrong by four orders of magnitude, Humana's by
22x - but they were concentrated in a minority of names, and the sector's median moved one
point. The IT-to-Real-Estate spread is 27 points after the fixes against 26 before.

That is a real negative result and it **strengthens E29 rather than weakening it**. The
cross-sector gap is not the rubric asking the wrong questions (E29), and it is not broken
inputs either (E30). It is a property of what these businesses look like through this
framework - which is exactly why the cross-sector headline is now `sector_neutral_score`
and not `score`.

Real Estate's median coverage is **0.793** after all four fixes - up from 0.778, moving
toward the 0.80 band gate and still under it, so most REITs still carry no band. Energy
moved most on coverage, 0.808 -> 0.830. That is the honest state.

## OPEN 3 - data-quality failures, re-measured

**502 -> 400 after the revenue fixes -> 307 after FIXED 4**, a 39% fall overall. This is
the cleanest independent check that the repairs worked: the guards were firing correctly
on bad inputs and went quiet once the inputs were right.

The residue, and it is honest: **218 of the remaining 307 are the stale-pairing guard on
`fe_gross_margin` and `fe_operating_margin`** in cases FIXED 4 could not rescue - the
filer's `cogs` is stale too, or the derivation disagrees with the stranded series where
they overlap, or there is no `pretax_income` to reconstruct EBIT from. Those sub-tests are
**withheld rather than wrong**, which is the safe failure: they leave both the numerator
and the coverage denominator, so nobody is penalised for them. The rest is 84
`out_of_bounds` and 25 `derivations_disagree`, both of which are guards catching real
filing problems rather than defects in this code.

---

## What changed and what did not

Four bugs fixed, all in the measured half, all data-correctness rather than rubric:
scores move because the inputs were wrong, not because a weight was retuned. **No
threshold, weight, band or denominator changed**, so the framework is the same framework
and the snapshot series stays comparable in structure - though the affected companies'
levels do move, and that is the point.

Three findings are left open on purpose. Each is a rubric change, and this project's rule
is that those get registered before they get made.

And the headline result of the whole pass is a negative one, which is the point of running
it: **the data was wrong in places and fixing it did not change the answer.** The
cross-sector spread survived E29 (the rubric is not asking the wrong questions) and it
survived E30 (the inputs were not what was driving it). Two plausible explanations tested
and refused is worth more than one accepted without testing.
