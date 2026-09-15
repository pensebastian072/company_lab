# B4 reproduction - E57 citation assignment and semantic support

Date: 2026-09-08

Status: SHADOW / advisory

Promoted: false

Source under test: the eleven Health Care Phase A objects stored at research version
`2026-09-07`, together with `e57_healthcare_phase_a_builder.py` and its saved evidence
receipt.

## Verdict

**B4 is reproduced.** Local quote containment succeeded for all 66 claims, but that
check did not establish that the quoted passage supported the field to which it was
attached. The builder mechanically assigns one evidence window to each fixed pair of
fields. Under a strict field-specific reading, 11 of 66 passages directly support the
full field claim, 30 provide relevant context without establishing it, and 25 concern a
materially different fact.

This is a citation-assignment and semantic-sufficiency defect. It is not a fabrication
finding: many sources are authoritative and topic-relevant, and all locally verified
quotes may still be literal matches. No object value, claim status, frozen report or
store row is changed by this reproduction.

## Mechanical assignment reproduced

The builder's `FIELD_SOURCE_INDEX` maps the same source index to two fields:

| Evidence window | Assigned fields |
|---:|---|
| 0 | `structural_growth`, `replication_difficulty` |
| 1 | `substitution_risk`, `regulatory_trajectory` |
| 2 | `market_structure`, `key_metrics` |

Across eleven objects this produces 33 evidence windows and 66 claims. Every window is
therefore reused once, regardless of whether its passage contains evidence for both
assigned fields. This establishes the mechanical-reuse allegation independently of any
individual semantic judgment.

## Denominator and rubric

The audit read the claim text, quote and excerpt for all six stored fields on all eleven
objects. Each claim was classified from the attached passage itself:

- **Direct:** the passage contains field-specific evidence for the full claim. This does
  not by itself prove that the categorical magnitude generalizes to the whole industry.
- **Context only:** the passage is relevant to the subject or industry but does not
  establish the complete field claim or categorical.
- **Unsupported:** the passage is about a materially different fact or economic unit.

| Field | Direct | Context only | Unsupported | Total |
|---|---:|---:|---:|---:|
| `structural_growth` | 4 | 5 | 2 | 11 |
| `replication_difficulty` | 0 | 2 | 9 | 11 |
| `substitution_risk` | 1 | 4 | 6 | 11 |
| `regulatory_trajectory` | 4 | 5 | 2 | 11 |
| `market_structure` | 2 | 6 | 3 | 11 |
| `key_metrics` | 0 | 8 | 3 | 11 |
| **Total** | **11 (16.7%)** | **30 (45.5%)** | **25 (37.9%)** | **66** |

Thus 55 of 66 attached passages (83.3%) do not directly support the complete field
claim under this rubric. Context-only evidence is not treated as false or fabricated;
it is simply insufficient for the delivered field conclusion.

## Exact direct-support receipt

- `structural_growth` (4): `clinical_laboratories`, `health_care_equipment`,
  `health_care_facilities`, `health_care_supplies`.
- `replication_difficulty` (0): none.
- `substitution_risk` (1): `biotechnology`.
- `regulatory_trajectory` (4): `health_care_equipment`, `health_care_facilities`,
  `health_care_supplies`, `managed_health_care`.
- `market_structure` (2): `health_care_services`, `managed_health_care`.
- `key_metrics` (0): none.

## Exact unsupported receipt

- `structural_growth` (2): `health_care_distributors`, `managed_health_care`.
- `replication_difficulty` (9): `biotechnology`, `clinical_laboratories`,
  `health_care_distributors`, `health_care_facilities`, `health_care_services`,
  `health_care_supplies`, `health_care_technology`,
  `life_sciences_tools_services`, `managed_health_care`.
- `substitution_risk` (6): `clinical_laboratories`, `health_care_distributors`,
  `health_care_equipment`, `health_care_facilities`, `health_care_supplies`,
  `life_sciences_tools_services`.
- `regulatory_trajectory` (2): `health_care_services`, `health_care_technology`.
- `market_structure` (3): `clinical_laboratories`, `health_care_distributors`,
  `health_care_technology`.
- `key_metrics` (3): `clinical_laboratories`, `health_care_distributors`,
  `health_care_technology`.

All other field-object pairs are context only.

## Clear unit and field mismatches

- The clinical-laboratories market-structure and key-metrics claims use an FDA
  pharmaceutical quality-control laboratory inspection passage, not evidence about the
  economics or metrics of clinical diagnostic laboratories.
- The health-care-distributors market-structure and key-metrics claims use a Medicare
  Advantage Star Ratings passage about health plans, not distributors.
- The distributors' first paired passage discusses LIFO and settlement expenses rather
  than prescription volume, logistics density or replication barriers.
- The managed-care growth and replication claims rely on HSA custodian and privacy
  evidence even though the E57 report itself concludes that HQY does not belong in the
  managed-care unit.
- The health-care-technology market-structure and key-metrics claims use an FDA passage
  about the device lifecycle for AI-enabled products, not evidence for the software
  market structure or recurring-revenue metrics asserted by the claims.

## Required correction for a future rerun

Each field needs its own evidence receipt selected after the field-specific claim is
defined. Quote containment, source authority, industry proximity and semantic support
must be reported as separate checks. Parent, segment and industry scope must match the
categorical being asserted; otherwise the field remains UNKNOWN with its abstention
reason preserved. The frozen E57 objects remain an auditable historical result and are
not eligible for Phase B on the strength of the original 66-of-66 containment result.
