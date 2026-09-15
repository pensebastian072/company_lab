# E58 — endpoint avoidance, arm A result

Evaluated 2026-09-08 from the live store. Advisory / SHADOW; nothing here scores,
ranks, promotes, or changes a company record.

## Arm A — REFUTED at the registered boundary

The registered field was `replication_difficulty` on the eleven Health Care industry
objects. Ten answered it and one, `health_care_services`, returned `UNKNOWN`, so the
registered answered-value denominator is ten.

| measure | result |
|---|---:|
| Health Care endpoints | **1/10 = 0.10** |
| registered confirmation threshold | **below 0.10** |
| rest of active corpus | **12/54 = 0.222** |
| minimum answered objects | **10 observed; 6 required** |
| verdict | **REFUTED** |

The result lands exactly on the exclusive boundary: confirmation required a share
strictly below 0.10, while 1/10 is 0.10. The threshold was registered before E57 and is
not moved after seeing the data.

The one endpoint is `biotechnology = EXTREME`. Every other answered Health Care object
used `HIGH` or `MODERATE`; `health_care_services` is excluded from the rate because
`UNKNOWN` is NO_DATA, never a scale value.

## The result is one object wide

This verdict turns on a single object and that thinness is part of the result, not a
footnote. Had biotechnology come back `HIGH`, Health Care would have used zero endpoints
in ten answered values, 0/10, and arm A would have been **CONFIRMED**. At the realized
denominator the only possible shares below 0.10 are zero, so the registered rule became
a unanimity test: one endpoint refutes it.

The registered reading therefore stands narrowly: endpoint avoidance did not follow the
researcher unchanged from Financials into Health Care, which points back toward the
Financials industry-object result being sector-specific rather than a general researcher
tendency. It does not establish that Financials genuinely has no extremes, and it does
not show that endpoint use or avoidance is an error.

## Arm B — not tested

Arm B requires Financials Phase B companies sharing that run's own
`research_version`. The 87 pre-Phase-B Financials companies are an old-regime prior, not
the answer, and batch 1 alone is balanced rather than representative. No arm B verdict is
reported here.

## Reproduction receipt

The checked-in evaluator returned:

```text
E58 arm A [replication_difficulty in health_care]: REFUTED
  subject 0.1 n=10   rest 0.222 n=54   threshold 0.1
```

All 12 boundary tests in `tests/test_e58_endpoints.py` passed on 2026-09-08. The store
read showed the eleven Health Care values as one `EXTREME`, eight `HIGH`, one `MODERATE`,
and one `UNKNOWN`.
