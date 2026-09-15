# E65 stance adjudication — do the SUPPORTS labels hold up?

Adjudicated 2026-09-09 by Chat B, reading all 136 stored quotes for the 17 active
Information Technology objects. Advisory / SHADOW; nothing here scores or promotes.

**Why this was owed.** E65 self-reports 130 SUPPORTS and 6 CONTEXT, and stance became a
*required* field only that morning. A label is the researcher's claim about evidence, not
a measurement of it — Health Care labelled **63 SUPPORTS and 0 CONTEXT**, and B4 found only
**11 of 66** with direct field support. So the label count proves nothing on its own.

## Verdict: the labels substantially hold

**No claim was found in the wrong economic unit.** That is the failure that killed
`pricing_power` — debt repricing, IRS transfer pricing and FX translation retrieved for a
field about pricing *power*, 26 of 47 wrong-sense. Nothing of that kind appears here. Every
claim is at least in the right domain for its field.

Six of the eight fields are strong throughout:

| field | n | read |
|---|---|---|
| `market_structure` | 25 | "the cloud computing services market is characterised by a high level of concentration among a few major providers"; "ASML is the only firm that provides EUV equipment" |
| `moat_mechanism` | 10 | "customers often face technical, contractual, and financial obstacles when attempting to migrate from one cloud provider to another" |
| `replication_difficulty` | 16 | "there is only one CdTe company manufacturing at gigawatt scale"; "median lead time … at least one year"; "more than 2,000 ZEISS patents" |
| `substitution_risk` | 18 | "solar PV module prices fell by around 50%"; "platform providers increasingly incorporate native security … often at no additional cost, which may reduce demand" |
| `regulatory_trajectory` | 19 | HBM export controls under the FDP rule; BIS licensing posture; ICANN registry agreements |
| `technology_trajectory` | 18 | on-topic throughout |

**These are doing real work.** "ASML is the only firm that provides EUV equipment" and
"only one CdTe company manufacturing at gigawatt scale" establish their fields outright,
and both come from ACADEMIC and REGULATOR sources rather than the company's own filing.

## Two fields are weaker, and they should not be quoted as if they were not

**`key_metrics`, roughly 4 of 15 are risk-factor prose rather than metrics.**
`electronic_components` retrieved "We depend on highly complex manufacturing processes
that require strategic materials, components, and products from limited sources of
supply" — a risk-factor bullet. `bitcoin_mining` retrieved "If we cannot timely sell
bitcoin, adjust hedges, post collateral…" — liquidity risk. The good ones are unambiguous:
book-to-bill, remaining performance obligations, product backlog, component lead times.

**`structural_growth`, roughly 5 of 15 are indirect proxies.** `ai_accelerators` rests on
"MLPerf Inference v5.0 includes 17,457 performance results from 23 submitting
organizations" — a benchmark participation count, not a growth rate.
`electronic_components` rests on "the sentiment index stabilized at 93.1 in May". Two
objects use a BLS *employment* projection as a proxy for industry growth, which is
defensible but is not the industry's growth. Against that, the strong ones are direct:
"WFE … projected to increase 6.2% to $110.8 billion", "the United States manufactured
approximately 15.7 GWdc of PV panels in H1 2025, up 126% y/y".

## Rate

Roughly **9 or 10 of 136 claims (~7%)** are weaker than their SUPPORTS label implies, all
concentrated in those two fields. Compare:

```
E65 IT              ~7% weak,        0% wrong economic unit
pricing_power       55% wrong sense, 13% genuinely supporting
E57 Health Care     55 of 66 lacking direct field support (B4)
```

## Limits of this adjudication

One adjudicator, no second reader — the same limit Chat A recorded for theirs. It reads the
**stored quote**, not the source document, so a quote that is accurate but unrepresentative
of its source would pass. The boundary between "indirect proxy" and "does not support" is a
judgement call, and a stricter reading moves `structural_growth` from 5 weak to perhaps 7;
the **zero wrong-unit count does not move** under any reading, and that is the finding that
matters.

## What it means

The E65 prompt worked on both axes it was written to test. Source diversity went from
E61's 96.6% single-domain to a 52.9% top share over six domains, and the stance labels are
substantially honest rather than a new default. **A required field can still be filled
carelessly; this one was not.**

The remaining weakness is narrow and nameable: `key_metrics` and `structural_growth` accept
a proxy where the other six fields demand the fact. That is a prompt refinement for the
next Phase A, not a defect in this one.
