# E57 - Health Care Phase A results

Recorded 2026-09-08 from a live-store read of the Phase A objects created on
2026-09-07.

Status: SHADOW / advisory

Promoted: false

E57 completed the Health Care industry-object construction pass. It did not research,
score, rank, select or promote any company, and it did not create a Phase B request.

## Store receipt

The live store contains all eleven E57 industry objects at version `2026-09-07` and all
66 attached claims. Each object has six claims spanning three independence domains; all
66 claims are stored as `VERIFIED_LOCAL`. The claims cite 31 distinct URLs.

| Industry object | Companies in Phase A map | Structural growth | Replication difficulty | Substitution risk |
|---|---:|---|---|---|
| `health_care_equipment` | 34 | HIGH | HIGH | LOW |
| `biotechnology` | 29 | HIGH | EXTREME | MODERATE |
| `pharmaceuticals` | 26 | MODERATE | HIGH | ELEVATED |
| `health_care_services` | 14 | UNKNOWN | UNKNOWN | UNKNOWN |
| `life_sciences_tools_services` | 13 | MODERATE | HIGH | MODERATE |
| `health_care_supplies` | 12 | MODERATE | MODERATE | MODERATE |
| `health_care_facilities` | 10 | MODERATE | HIGH | MODERATE |
| `managed_health_care` | 9 | MODERATE | HIGH | MODERATE |
| `health_care_technology` | 8 | HIGH | HIGH | MODERATE |
| `clinical_laboratories` | 4 | MODERATE | HIGH | MODERATE |
| `health_care_distributors` | 4 | MODERATE | HIGH | MODERATE |

The table is a receipt of stored Phase A output, not a fresh endorsement of every
categorical. B4 below changes how its evidence quality must be read.

## Evidence guarantee - dated correction

The original E57 report correctly recorded that the local verifier found every quote in
its fetched page: 66 of 66 claims passed literal containment. It then allowed that result
to read like an evidence-quality guarantee. The independent B4 reproduction on
2026-09-08 shows that the stronger interpretation is not supported:

| Attached-passage support | Claims | Rate |
|---|---:|---:|
| Direct support for the full field claim | 11 | 16.7% |
| Relevant context only | 30 | 45.5% |
| Materially different fact or unit | 25 | 37.9% |

The builder assigned three evidence windows to fixed pairs of fields, so every passage
was reused once. Consequently, 55 of 66 passages (83.3%) did not directly establish the
complete field claim under the strict B4 rubric. This does not mean that those sources
or literal quotes were fabricated. It means `VERIFIED_LOCAL` confirms quote containment,
not semantic field support, scope comparability or the categorical magnitude.

The exact field-object receipt and rubric are registered in
`AUDIT_2026-09-08_B4_E57_CITATION_REPRODUCTION.md`. The stored objects remain unchanged so
the original result stays auditable. A future use must repair or independently challenge
the evidence instead of inheriting 66-of-66 as semantic validation.

The original report also gave the then-current corpus statistic as 4 unverifiable claims
out of 5,231 checked (0.08%). A live read on 2026-09-08, after A1 and later corpus work,
shows 64 out of 6,335 checked (1.01%). This is a dated corpus-state correction, not an E57
failure rate; `A1_UNVERIFIABLE_SCORING_DECISION_2026-09-08.md` records the doctrine and
historical transition.

## UNKNOWN and taxonomy results

`health_care_services` deliberately remains UNKNOWN on all three scale fields. The unit
mixes renal care, diagnostic imaging, home and hospice care, staffing, behavioral health,
physician enablement, digital consumer care, fertility benefits, occupational health,
workers-compensation cost management and sterilization services. Their growth,
replication and substitution mechanisms are not comparable.
The abstention is `evidence absent` for a coherent combined categorical, not a claim that
no relevant passage exists and not a license to force a midpoint.

The Phase A taxonomy findings remain useful even though the categorical evidence needs
repair:

- Split `health_care_services` into the economically comparable operating units listed
  above before company research.
- Treat CHE at the VITAS segment rather than allowing Roto-Rooter to define a Health Care
  object.
- HQY is an HSA custodian and should not inherit managed-care economics.
- SDGR belongs with Health Care technology on its customer-facing software activity.

These are proposed taxonomy boundaries. They do not themselves populate company fields.

## E58 arm A result on the E57 objects

E58 arm A used `replication_difficulty` on the E57 objects to test endpoint avoidance.
Ten objects answered and `health_care_services` was UNKNOWN. One answered value used a
scale end: `biotechnology = EXTREME`.

| Measure | Result |
|---|---:|
| Endpoint share | **1/10 = 0.10** |
| Registered confirmation rule | **below 0.10** |
| Verdict | **REFUTED** |

The threshold remains where it was registered. The verdict turns on one object: had
biotechnology been HIGH, the result would have been 0/10 and CONFIRMED. At this
denominator the rule is effectively unanimity, so the narrowness is part of the finding.
E58's complete arm-A receipt is in `E58_results.md`; arm B is separate and is not inferred
from E57.

## Disposition

E57 remains a completed Phase A construction artifact in SHADOW. It supplies a taxonomy
map and an auditable set of provisional industry states, but B4 prevents the 66-of-66
containment result from being used as proof that those states are semantically validated.
Any Health Care Phase B handoff must preserve UNKNOWN, keep parent and segment units
explicit, and either repair or independently challenge inherited field evidence.
