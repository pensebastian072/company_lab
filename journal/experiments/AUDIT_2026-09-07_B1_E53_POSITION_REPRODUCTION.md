# B1 reproduction — E53 competitive position was a revenue-size quartile

Reproduced 2026-09-07 before changing any E53 interpretation.

## Inputs

- Builder: `D:\company_lab_data\external\e53_utilities_builder.py`, SHA-256
  `81f4e29a207520ece0e21852e6d0f738c56f894fd87e3b9f194175da3f462508`.
- Frozen Pass A: `f92abdf0887e91cd072d.pass_a.json`, SHA-256
  `d10a9a46ab5c265a67f8d12d1a5236c8b8d0ebe2781592933e60978936fdb24d`.
- No conclusions file was opened.

## Reproduction

The derivation is direct and exclusive:

1. `position_labels()` groups the frozen roster by `industry_id`.
2. Within each group it sorts only `measured.revenue_ttm`, descending.
3. Rank quartiles become `LEADER`, `STRONG_NUMBER_TWO`, `CHALLENGER`, or `LAGGARD`.
4. `build_blind()` assigns that result directly to
   `pa["competitive_position"]` for every company.

The frozen payload contains 59/59 filled values: 14 LEADER, 15
STRONG_NUMBER_TWO, 13 CHALLENGER, and 17 LAGGARD. All 59 attached claim texts use the
same generated “franchise, network or fleet ... bounded scale” template; none changes
the derivation above.

## Finding

**CONFIRMED.** E53's 59 `competitive_position` values are within-industry revenue-size
quartiles. They are not a researched regulatory/operating peer comparison. The values
must remain in the frozen historical payload, but they cannot be counted as researched
four-field resolutions or relied on as competitive-position evidence. A corrective run
must research the field or return UNKNOWN; it must not translate revenue size into this
ordinal under the researched field's name.

Status remains advisory / SHADOW. No values were promoted or rewritten by this
reproduction.
