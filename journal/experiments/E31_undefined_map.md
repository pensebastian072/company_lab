# E31 - the undefined map: FIVE entries, all on one profile

Written 2026-08-25 against `E31_undefined_vs_missing_preregistration.md`. Every entry
carries a written definitional argument (P1); every refusal carries a named
counter-example (P2).

## Result

Of **40 (profile, sub-test) candidates** scoring for at least half their nominated
companies, **5 were admitted** - all on `MORTGAGE_REIT` - and **35 were refused**, almost
every one of them on P2.

## The admitted entries: MORTGAGE_REIT, 9 companies

The only homogeneous bucket in `profile.py`. All nine members are GICS "Mortgage REITs" -
ABR, ADAM, ARR, BXMT, FBRT, NLY, PMT, RITM, STWD - so there is no company in it for which
a domain reader would call these metrics meaningful. (The measurement below was taken on
eight of them; ADAM was mid-repair from the `--symbols` bug described at the end of this
document and reads score 25 / coverage 0.627 on the final crawl.) That is the entire reason it survived
and FINANCIAL did not.

| sub-test | the quantity, and why it does not exist here |
|---|---|
| `va_ev_ebitda_vs_peers` | Enterprise value is market capitalisation **plus net debt**, on the theory that an acquirer assumes the debt to obtain the operations. A mortgage REIT **is** a levered bond portfolio: the debt is the strategy, not a claim against the business, and the cash is posted collateral. There is no "operations net of financing" to value. P/B and dividend yield are the multiples used here. |
| `va_ev_sales_vs_peers` | Same numerator problem, and the denominator is worse: "sales" for this filer is interest income, so EV/Sales is a financing structure divided by a financing spread. |
| `bs_net_debt_ebitda` | EBITDA is earnings **before interest**. Interest is this filer's cost of revenue, so there is no pre-interest earnings figure to compute, and "net debt" is its funding book rather than a leverage burden. Both halves of the ratio are undefined. |
| `bs_interest_coverage` | Coverage is a **fixed-charge** test: can operating earnings clear the financing bill? Repo interest is the cost of goods sold here. The ratio asks whether revenue covers itself. |
| `fe_roic` | ROIC is NOPAT over invested capital, `debt + equity - cash`. Invested capital so defined is the portfolio, not capital employed. **P3 is satisfied**: the profile already redirects returns to ROE, and `fe_roe` is scored for **100%** of these filers. |

## The refusals, with their counter-examples

### FINANCIAL - every candidate refused, and this is the finding of the experiment

Seven candidates were argued and all seven fail P2 on the same evidence: **the FINANCIAL
profile is not a profile of banks.** 63 of its 192 members are not banks at all.

| sub-industry inside FINANCIAL | n |
|---|---:|
| Regional Banks | 89 |
| **Asset Management & Custody Banks** | **24** |
| **Transaction & Payment Processing Services** | **19** |
| Consumer Finance | 14 |
| Investment Banking & Brokerage | 14 |
| **Financial Exchanges & Data** | **13** |
| Diversified Banks | 7 |
| **Application Software** | **2** |

The named counter-examples, each one sufficient on its own to refuse every FINANCIAL
entry:

* **Visa** and **Mastercard** (Transaction & Payment Processing). Gross margin, FCF
  margin, EV/EBITDA and ROIC are not merely defined for them, they are the **primary**
  metrics. Neither company takes a deposit.
* **CME, ICE, S&P Global, MSCI** (Financial Exchanges & Data). EV/EBITDA is the standard
  multiple for an exchange.
* **BlackRock, Blackstone, KKR, T. Rowe Price** (Asset Management). Fee businesses with
  real debt and meaningful enterprise value.
* **Dolby** (87.6% gross margin, 29.0% FCF margin) and **Alarm.com** (65.8%, 17.7%) -
  Application Software companies carrying the FINANCIAL profile outright. Dolby's stored
  GICS sector is even *Information Technology*; only the profile is wrong.

A hard suppression on FINANCIAL would have deleted Dolby's 87.6% gross margin and Visa's
ROIC as "not defined for a bank". **The two-part `resolve_status` test has been silently
protecting the framework from a coarse classification**, which is a more useful sentence
than E30's "the profile is documentation that mostly does not run".

### INSURANCE - every candidate refused

73 members, and at least two groups break every entry:

* **8 Insurance Brokers** (AJG, MMC, BRO, WTW and peers). A broker is a fee business.
  **EV/EBITDA is its standard valuation multiple** and net debt / EBITDA is its standard
  leverage measure. Both are exactly what the EV and leverage entries would suppress.
* **5 Managed Health Care + 3 Health Care Services** - Humana and peers. Operating
  companies with real revenue, real margins and meaningful ROIC. This is the UNH
  precedent, which the original profile note already cites, appearing again.
* `bs_interest_coverage` fails on its own merits too: an insurer's interest expense is on
  **debt**, not on float, so coverage is a meaningful and standard test for it - unlike a
  bank, where deposit interest is cost of revenue.

### REIT - every candidate refused

* `fe_margin_expansion` scores for **86.7%** of REITs. A REIT's operating margin is
  computable and meaningful, and a margin that is not expanding is a **true low score**,
  not a question with no referent. **E29 ruled this exact sub-test out for Utilities on
  the record this morning**; refusing it here is the same rule applied consistently.
* `va_p_fcf`, `va_reverse_dcf`, `fe_fcf_margin`, `fe_fcf_growth`: a REIT's FCF is
  *distorted* by acquisition capex, not undefined, and net-lease REITs with no development
  pipeline have perfectly meaningful FCF. Distorted is not undefined. FFO/AFFO is the
  right measure and **is not implemented** - that gap is honest NO_DATA, not a case for
  suppression.
* `mg_reinvestment_quality`, `mg_buyback_discipline`: a REIT's acquisitions **are** its
  reinvestment, and REITs do buy back stock.

### UTILITY - refused

`fe_fcf_margin` scores for 92.6% of utilities. Rate-base capex is mandated, so FCF is
structurally thin - and that is a **true fact about the business**, exactly the kind E29
ruled out. Suppressing it would flatter the sector by declining to measure what makes it
what it is.

### BIOTECH - refused

`va_peg`, `va_p_fcf`, `va_reverse_dcf` are undefined for a **pre-revenue** filer and
perfectly defined for an early-commercial one, and the profile holds both. That mixture is
precisely what the soft `not_applicable` rule handles correctly today.

## The prior, scored honestly

| prediction | outcome |
|---|---|
| 4-7 entries | **5 - right on count** |
| all on FINANCIAL / INSURANCE / MORTGAGE_REIT | **wrong on distribution** - FINANCIAL and INSURANCE were refused outright; every admitted entry is MORTGAGE_REIT |
| EV and reverse-DCF entries the clearest passes | half right - they pass for MORTGAGE_REIT, fail P2 everywhere else |
| `fe_roic` **fails P3** | **WRONG** - `fe_roe` is scored for 100% of FINANCIAL and 98.5% of INSURANCE filers, so P3 is satisfied. Recorded before the map was written. |
| REIT entries thin | right - zero |
| net effect on median score small and mixed | small, and **not** mixed - see below |

## What it did

Measured over the mortgage REITs, before vs after:

| | score | coverage | band |
|---|---|---|---|
| NLY | 24 -> 18 | 0.500 -> 0.443 | INSUFFICIENT_DATA (no change) |
| RITM | 33 -> 30 | 0.797 -> 0.776 | INSUFFICIENT_DATA (no change) |
| STWD | 30 -> 29 | 0.818 -> 0.802 | REJECT (no change) |
| ABR | 20 -> 18 | 0.580 -> 0.547 | INSUFFICIENT_DATA (no change) |
| ARR, BXMT, FBRT, PMT | -0 to -2 | -0.01 to -0.03 | no change |

**Zero band changes.** Scores and coverage both fall, consistently, and the direction is
arithmetic rather than a judgement: these companies were *earning* points on the
suppressed metrics, so removing them takes points out of the numerator, and because
coverage was below 1.0 removing an available point from both sides lowers the ratio.

The registration said the direction was ambiguous. It is not ambiguous - it is
consistently slightly negative - and that is the correct outcome. A mortgage REIT that
was scoring on a meaningless ROIC now scores on less, and its coverage honestly says the
framework can measure less of it than it previously claimed.

## The four required reports, measured over the full 1,501 after a tier re-score

1. **Coverage per sector: unchanged to four decimals in all eleven.** Median coverage
   moved 0.0000 in every sector, and **no company crossed the 0.80 band gate in either
   direction**.
2. **Band changes: NONE.** Not one company in the universe changed band.
3. **Within-sector Spearman of `composite_strict`, before vs after** - E12's P4 duty.
   Real Estate 0.998451, Financials 0.999909, Materials 0.999618, Information Technology
   and Utilities 1.000000, every other sector above 0.9998. **This reweights; it does not
   reorder.**
4. **Refusals with counter-examples**: above.

**26 of 1,501 companies changed `composite_strict` at all**, and only 8 of those are
E31's - the mortgage REITs measured in that pass, every one down. The other 18 are +/-1 point on STANDARD,
FINANCIAL and REIT filers, which is run-to-run boundary noise and not this change.

Worth noting for anyone reading the sector column: the eight mortgage REITs are split
across **two GICS sectors** - ABR, NLY, RITM and STWD sit in Financials while ADAM, FBRT
and PMT sit in Real Estate - so a profile is not a sector and the workbook's sector
aggregates will never isolate them.

## Found while measuring this, and it is worse than the experiment

**`--symbols` silently rewrote the profile of every company outside the default tier.**
`batch.py` built its lookup from one tier and handed anything missing a bare CIK row with
an **empty `sub_industry`** - and sub-industry is the only thing separating a mortgage
REIT from an equity REIT. Re-scoring the nine mortgage REITs by name reclassified all nine
as equity REITs and moved NLY's coverage 0.500 -> 0.446.

`--symbols` is the documented way to re-score one company, so **the same company scored
two different ways depending on how the crawl was invoked**. It now searches every tier
first, and the remaining no-tier case logs a WARN saying what it costs instead of a
neutral note. This is the graceful-degradation failure class the repo rules already name,
in a new place.

## What this does not establish

Nothing here tests whether any of it predicts anything. There is no forward-return grader;
it needs ~50 weekly snapshots and the `as_first_filed` view, and 5 exist. This changed what
is asked of 8 companies with no way to check whether the resulting scores are better, only
whether they are more internally honest. `promoted` stays false.

**And it changes the framework**, so the snapshot series is discontinuous at this date for
those 8 companies - unlike E30's four fixes, which corrected inputs and left the framework
identical.
