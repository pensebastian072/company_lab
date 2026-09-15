# E31 - a metric that is UNDEFINED is not a metric that is MISSING

Pre-registration written 2026-08-25, **before any profile, rubric or denominator is
changed**. Raised by E30's per-sector audit, which flagged 42 (sub-test x sector) cells
where a profile says a metric does not describe a filer and the scorecard scores it
anyway.

## What is already measured, before this is registered

`SectorProfile.resolve_status` grants `NOT_APPLICABLE` only when the profile nominates the
sub-test **AND** the value is genuinely absent. The second condition is deliberate and
load-bearing - UNH is nominally a FINANCIAL filer but files a full ordinary income
statement, so its margins are scored rather than suppressed, and suppressing them on the
SIC code alone would throw away real measured signal on a $450bn-revenue company.

The consequence, measured over 1,501 scorecards on 2026-08-25: a suppression whose reason
is **"meaningless"** rather than **"missing"** almost never fires, because the ratio is
nearly always computable from the filing.

| sub-test | profile | the profile's stated reason | nominated companies SCORED |
|---|---|---|---:|
| `bs_interest_coverage` | FINANCIAL | "interest expense is cost of goods, not a solvency burden" | **93.8%** |
| `va_ev_sales_vs_peers` | FINANCIAL | "EV is not defined for a bank" | **93.0%** |
| `fe_roic` | FINANCIAL | "ROE carries the returns weight" | **91.4%** |
| `bs_net_debt_ebitda` | FINANCIAL | "deposits are funding, not leverage in the covenant sense" | **82.8%** |
| `va_reverse_dcf` | FINANCIAL | undefined | 75.5% |

The FINANCIAL profile's note says these "are not defined". Between three-quarters and
94% of banks carry a score for them. **The profile is documentation that mostly does not
run**, and a scorecard presenting an EV/Sales percentile for a bank is presenting a
measured, meaningless number as evidence, with a `provenance.source` of `edgar` behind it.

## The question

Should a profile be able to say **"this quantity does not exist for this filer"** -
suppressing regardless of whether arithmetic can produce a number - as distinct from
today's **"this line is often missing here, and when it is, do not penalise"**?

## Why this is not E29 again

E29 refused every candidate for a per-sector applicability map six hours earlier, and the
refusal must not be quietly reversed. The distinction is the **kind of argument**, and it
is the whole of this registration:

* **E29's candidates were justified by a NULL RATE.** "The model abstains on this
  dimension for 81% of Real Estate" is a statistic about a language model and an evidence
  pack. It cannot tell inapplicability from a retrieval failure, which is why Rule C
  exists and why every candidate was refused.
* **E31's candidates are justified by an ACCOUNTING FACT.** Enterprise value is
  market capitalisation plus net debt. For a bank, deposits are funding and cash is
  inventory, so the quantity EV is *defined* to measure does not exist. That is not a
  statistic and no amount of better retrieval changes it.

The second argument is much stronger, which is exactly why it gets the same discipline
rather than less. **A stronger argument that is never written down is how a rubric drifts.**

## The change, if the criteria below are met

Add a second, stronger nomination kind to `SectorProfile`, sitting beside the existing
one rather than replacing it:

| | condition to suppress | for |
|---|---|---|
| `not_applicable` (today) | nominated **AND** value absent | a line that is often missing but meaningful when present - gross margin for UNH |
| `undefined` (new) | nominated, **regardless of the value** | a quantity that does not exist for the filer type - EV for a bank |

Nothing else moves. `composite_strict` still sums earned points, `coverage` still divides
available by applicable, the 0.80 band gate stands, and the existing `not_applicable` set
is **untouched** - no sub-test is promoted from one kind to the other without clearing P1
and P2 below.

## The bar for an entry, fixed now

| | passes if |
|---|---|
| **P1** | **A written definitional argument** naming the quantity and why it does not exist for that filer type, in accounting terms, in the map document. Not a null rate, not a score distribution, not a point total. This is E12's P3 in its proper setting and it is **required for any change at all**. |
| **P2** | **No counter-example in the universe.** If ANY company carrying that profile has a filed, plausible value for the sub-test that a domain reader would call meaningful, the entry is refused and stays `not_applicable`. The UNH precedent is the test: one real exception kills the hard suppression, because `not_applicable` already handles the mixed case correctly. |
| **P3** | **The sub-test must not be the profile's substitute.** A profile that redirects a measurement elsewhere (`returns_metric="roe"` for FINANCIAL) may suppress the redirected-from metric only if the substitute is actually scored for that sector. Suppressing ROIC while ROE is also unavailable removes the returns question entirely rather than answering it differently. |

## Required reporting after any change

Because the direction of the effect is **ambiguous and not obviously favourable**, and
saying so in advance is the point:

1. **Coverage moves per sector**, and how many companies cross the 0.80 band gate in each
   direction. `NOT_APPLICABLE` leaves both the numerator and the coverage denominator, so
   a bank that was *earning* points on a meaningless `fe_roic` loses them, while its
   applicable total falls too. Some banks will score higher and some lower.
2. **Band changes, per sector, both directions.** A count of companies that gain a band
   is not the finding; the net and the direction are.
3. **Within-sector Spearman of `composite_strict` before vs after** - E12's P4 duty.
4. **The refused entries with their counter-examples**, in the same document as the
   admitted ones.

## Prior, stated before computing

I expect **4 to 7 entries, all on FINANCIAL / INSURANCE / MORTGAGE_REIT**, and I expect
`va_ev_ebitda_vs_peers`, `va_ev_sales_vs_peers` and `va_reverse_dcf` to be the clearest
passes, because EV and a discounted free-cash-flow are definitionally absent for a
deposit-funded balance sheet.

I expect **`fe_roic` to FAIL P3**: the FINANCIAL profile redirects returns to ROE, and
whether `fe_roe` is actually scored for those same banks has not been checked. If it is
not, suppressing ROIC deletes the returns question for a quarter of the universe.

I expect **REIT entries to be thin**. `fe_margin_expansion` is nominated for REIT and
scores for 84% of them, but a REIT's operating margin is computable and meaningful, so I
expect it to fail P2 - the same reasoning that ruled `fe_margin_expansion` for Utilities
out of E29 on the record this morning.

And I expect the **net effect on median score to be small and mixed**, because points
leave the numerator and the denominator together. If median Financials score moves by
more than 3 points in either direction, that is a finding about the framework and not
about banks, and it must be written up as one.

## What this experiment cannot establish

**Nothing here tests whether any of it predicts anything.** There is no forward-return
grader - it needs ~50 weekly snapshots and the `as_first_filed` view, and 5 exist. This
change alters what is *asked* of several hundred companies with **no way to check whether
the resulting scores are better**, only whether they are more internally honest. Any
write-up must say that in those words. `promoted` stays false.

**And it resets comparability.** Unlike E30's three fixes - which corrected inputs and
left the framework identical - this changes the framework, so the snapshot series is
discontinuous at the change date. Against a grader that needs ~50 weekly snapshots and
has 5, that cost is real and is the main argument for doing nothing.

## Outputs

* `journal/experiments/E31_results.json` / `.md`
* `journal/experiments/E31_undefined_map.md` - admitted and refused entries together, one
  written definitional argument per admitted entry, one counter-example per refusal.
