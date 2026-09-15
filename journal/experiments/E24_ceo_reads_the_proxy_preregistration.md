# E24 - ask the CEO questions of the document that answers them

Pre-registered 2026-08-22, before the evidence-pack change. **This supersedes E23**, which
removed the five model-scored CEO attributes. E23's code change is reverted here; its
registration and its measurements stay on the record as what the alternative looked like.

## Why the reversal

E22 measured MG's year-over-year stability at Spearman **0.29** against a bar of 0.5, and
the obvious reading was "management quality is unmeasurable, cut it". The diagnosis says
otherwise. Three of the five attributes are **proxy-statement facts**, and the evidence
pack is built from the 10-K:

| attribute | scored across ~200 companies | where it actually lives |
|---|---:|---|
| industry_expertise | 177 | 10-K, business description |
| execution_history | 67 | 10-K, MD&A |
| tenure | 14 | **DEF 14A** |
| ownership | 10 | **DEF 14A** |
| founder_led | 9 | **DEF 14A** |

A 10-K does not say who founded the company, how long the CEO has served, or what they
own. The model was answering from nothing, and 0.29 is the stability of one or two noisy
items - not evidence about management quality.

The proxies are on the submissions feed already: **23 for AAPL, 24 for FDX, 6 for JPM**,
reachable with the machinery E22 built for historical 10-Ks.

## The change

1. **Restore** `MG_CEO_ATTRIBUTES` to its seven entries and `MG_MIN_ATTRIBUTES_SCORED` to
   4. E23 is reverted in code.
2. **`edgar_filings.proxy_text(cik, as_of=None)`** - the DEF 14A current at a date, cached
   and sliced the same way 10-K text is.
3. **MG's evidence pack, and only MG's**, gains proxy excerpts. A separate proxy pool
   rather than proxy chunks added to the shared pool: adding them to the shared pool would
   make them compete for SG's and BQ's eight retrieval slots and invalidate all three
   components' caches. This way **only MG's pack hash changes**, so only MG regenerates.
4. The repair queries for `founder_led` / `tenure` / `ownership` come back, aimed at proxy
   language ("has served as our chief executive officer since", "beneficial ownership").

## Cost, measured before committing

* **MG regeneration: ~1,498 companies x ~16 s = 6.7 h** of GPU, because the pack hash
  changes for every company. SG and BQ are untouched and do not re-run.
* **E22 re-measure: 200 companies x 2 readings x MG only = ~1.8 h.** The historical
  readings need the proxy that was current at each as-of date, which `proxy_text(as_of=)`
  supplies the same way the historical 10-K does.
* A probe of 3-5 companies runs first and reports proxy size, section hit rate and time
  per company. If the probe shows proxies failing to slice, the build stops there rather
  than committing seven hours to a pack that carries boilerplate.

## Pass criteria, fixed now

| | passes if |
|---|---|
| **P1 - attributes answered** | The three proxy attributes are scored for **>= 60%** of companies, against 5-7% today. This is the direct test of the diagnosis. |
| **P2 - stability** | MG's year-over-year Spearman rises above the **0.5** bar E22 set. This is the criterion that decides whether MG stays in the framework. |
| **P3 - no fabrication** | Unverified-quote rate on the CEO block stays at or under the incumbent's **0.28%** (E07's M3). A model handed a document it can quote from must not start inventing. |
| **P4 - SG and BQ unmoved** | Their pack hashes are unchanged and their cached scores are byte-identical. If they move, the "separate pool" claim is false and the change costs 20 hours instead of 7. |

P1 and P4 are checked on the probe, before the long run. P2 needs the re-measure.

## Prediction, stated before running

**P1 passes comfortably** - `tenure` and `founder_led` are stated plainly in the director
biographies, and `ownership` in the beneficial-ownership table. **P2 passes but not by
much: 0.5-0.65.** Tenure and founder status barely change year to year, which should lift
stability mechanically, but `execution_history` and `industry_expertise` remain judgement
calls on narrative text and will keep moving.

**If P1 passes and P2 still fails**, the honest conclusion is that MG's instability is not
about the source document, and E23's cut becomes the right answer after all - reinstated
by a third registration, not by silence.

## What this cannot establish

Nothing about returns. A stable score is not a predictive one, and E13 still has the
measured-half top-20 at -0.5% annualised net against SPY. `promoted` stays false.

## State note

E23's partial re-score touched 782 of 1,500 scorecards before it was stopped, so the
table is mid-migration until E24's re-score completes. That is a known transient, not a
finding.
