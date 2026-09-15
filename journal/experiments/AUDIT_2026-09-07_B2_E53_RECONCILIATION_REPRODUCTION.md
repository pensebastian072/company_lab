# B2 reproduction — E53 reconciliation selected external mechanically

Reproduced 2026-09-07 before changing any E53 interpretation.

## Inputs

- Builder: `D:\company_lab_data\external\e53_utilities_builder.py`, SHA-256
  `81f4e29a207520ece0e21852e6d0f738c56f894fd87e3b9f194175da3f462508`.
- Final payload: `f92abdf0887e91cd072d.json`, SHA-256
  `79e8bdcdc0a664775d11d5f161325907ce2d6af4a3510867732ce96d819a8845`.
- No conclusions file was opened.

## Reproduction

The builder's `reconcile()` loop creates exactly one reconciliation row per company.
The row always has:

- `field = "bq_killer_answer"`;
- `better_evidenced = "external"` as a literal, with no comparison predicate; and
- the same `why` paragraph for every company.

The final payload independently confirms the generated shape: 59 companies, 59
reconciliation rows, 59 `better_evidenced=external`, one field value, and one distinct
`why` string.

## Finding

**CONFIRMED.** E53 did not adjudicate which side was better evidenced company by
company. It declared the external side better mechanically. The 59/59 outcome is not
evidence that the external work improved the local conclusion and must not be used as a
reconciliation result. The frozen Pass A and final payload remain historical artifacts;
a valid rerun would need an explicit per-company comparison that permits local,
external, tie, and insufficient-evidence outcomes.

Status remains advisory / SHADOW. Nothing was promoted or rewritten by this
reproduction.
