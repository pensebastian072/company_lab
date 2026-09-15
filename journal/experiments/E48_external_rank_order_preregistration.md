# E48 - does external research change within-sector order?

Pre-registration written 2026-09-04 before computing any Energy rank deltas or
opening an Energy before/after comparison.

## Questions

1. Does V3 change the within-Energy ordering because it learned something about the
   companies, or does it mainly add evidence coverage to the ordering already present?
2. Should `sector_neutral_score` use the economically coherent research taxonomy
   (`industry_id`) rather than the raw GICS `sub_industry`?

Neither question is a return test. Nothing here validates the ranking, changes a
promotion state, or authorizes portfolio use.

## Frozen Energy universe

Primary universe: every Energy company with a depth-3 external record available by
2026-09-04, joined to the same `scores.parquet` snapshot used by E46. Select the latest
eligible external record per ticker without using any later record. The expected count
is 71. If the join does not produce 71 unique companies, the complete-sector primary
test is BLOCKED; report the missing names and run the 52-name E46 cohort only as a
diagnostic, clearly labelled incomplete.

Ties are broken alphabetically. Missing inputs are not imputed.

## Three fixed orderings

Use the criterion decomposition already implemented in `clab.external.gates`.

- `A_local`: framework_band + financial_engine + survivability + framework_coverage,
  rescaled to 0-100. This is the measured/local ordering.
- `B_evidence`: A plus external_coverage + external_confidence + research_depth +
  core_fields_known, rescaled over their combined maximum. This measures how much the
  evidence process alone reorders names.
- `C_full`: the shipped conviction score, including moat_trajectory and all existing
  flag penalties. This is the substantive V3 ordering.

Do not change criterion weights, flag penalties, coverage floors, or UNKNOWN handling.

## Metrics and decision rule

For A-to-B and B-to-C report Spearman rho, Kendall tau, median and 90th-percentile
absolute rank movement, top-decile overlap, and every move of at least five places.

Call a transition `ORDER_CHANGING` if either:

- Spearman rho is below 0.90; or
- median absolute movement is at least 5% of the universe and top-decile overlap is
  below 80%.

Otherwise call it `ORDER_PRESERVING`. The headline answer is:

- B order-changing but C order-preserving: V3 mainly adds evidence availability.
- C order-changing: V3 changes order through substantive company conclusions.
- neither order-changing: V3 documents rather than changes the existing order.

Report flag-driven and moat-trajectory-driven moves separately so missing evidence is
not mistaken for a negative company finding.

## Prior

I expect A-to-B to move more names than B-to-C because depth and citation coverage vary
more than strongly evidenced moat trajectories. I expect the full ordering to remain
broadly similar (Spearman at least 0.85) with a small tail of five-plus-place moves from
competitive deterioration or peer-relative risks. This prior is not a pass criterion.

## Neutral peer basis

The semantic decision is pre-registered now: `industry_id` is the preferred peer key
because it is the unit the external research establishes as economically coherent.
GICS `sub_industry` remains descriptive metadata, not the first-choice neutralization
basis.

The deterministic fallback hierarchy is:

1. `industry_id` when the monthly cross-section has at least 4 members;
2. GICS `sub_industry` when it has at least 5 members;
3. sector otherwise.

This deliberately lets CEG, NRG, TLN and VST form the competitive-generation peer set,
while preventing the two-name renewable bucket and one-name AES bucket from becoming
mechanical 0th/100th percentiles. Report old and new peer keys, peer counts and
percentiles for every ticker-level taxonomy override. Do not claim improved selection
without a separate forward-return study under the quant research gate.

## Outputs

Write results to `journal/experiments/E48_external_rank_order_results.json` and `.md`.
`promoted` remains false regardless of the result.
