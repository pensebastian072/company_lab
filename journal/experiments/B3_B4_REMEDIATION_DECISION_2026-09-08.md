# B3 and B4 remediation decision

Date: 2026-09-08

Status: SHADOW / instrument decision

Promoted: false

This decision follows the independent reproductions in
`AUDIT_2026-09-08_B3_E53_EVIDENCE_REPRODUCTION.md` and
`AUDIT_2026-09-08_B4_E57_CITATION_REPRODUCTION.md`. It does not reinterpret quote
containment as semantic validity and does not overwrite either frozen result.

## Decision summary

| Finding | Operational decision | Evidential treatment |
|---|---|---|
| B3, E53 Utilities company arm | Retire the entire research version | Keep all 59 rows and 767 claims; explicit version remains queryable |
| B4, E57 Health Care objects | Retire all eleven version `2026-09-07` objects | Keep all objects, briefs and 66 claims; explicit versions remain queryable |

No affected claim is changed to `UNVERIFIABLE`. That status means the source was fetched
but its stored quote could not be confirmed. B3 and B4 concern semantic field support,
scope and outcome status, so overloading the quote-verification status would erase the
distinction registered by A1.

## B3 - retire E53 as one research arm

Target:

- research version `2026-09-07+E53-utilities-symmetric`
- request `f92abdf0887e91cd072d`
- 59 company rows and 59 distinct tickers
- 767 claims: 761 VERIFIED_LOCAL and 6 UNVERIFIABLE

B3 found the identical source URL, quote and excerpt reused for
`moat_trajectory` and `company_specific_capture` on 59 of 59 companies. Of 48 answered
pairs, only 11 contained a realized outcome relevant to at least one of the two fields;
that did not validate both delivered categoricals.

The arm is retired whole rather than rewriting the two fields to UNKNOWN in place.
Rewriting would destroy the frozen output, while selectively borrowing the remaining
fields into a new implicit arm would create mixed provenance that has never passed the
finalizer as a unit.

The current operational accessor therefore falls each ticker back to the prior accepted
Utilities version, `2026-09-05+E47-utilities`. That version has 59 rows and answers zero
of 59 `moat_trajectory` fields and zero of 59 `company_specific_capture` fields. This is
a conservative fallback, not a new endorsement of E47. A future Utilities rerun must use
separate field-specific receipts, distinguish proposed from approved and realized, and
produce a new version before it becomes current.

## B4 - retire the E57 object set

Targets: all eleven Health Care industry objects at version `2026-09-07`:

- `biotechnology`
- `clinical_laboratories`
- `health_care_distributors`
- `health_care_equipment`
- `health_care_facilities`
- `health_care_services`
- `health_care_supplies`
- `health_care_technology`
- `life_sciences_tools_services`
- `managed_health_care`
- `pharmaceuticals`

The 66 claims remain VERIFIED_LOCAL for literal containment. The B4 field audit found 11
direct-support passages, 30 context-only passages and 25 unsupported field or unit
assignments. Fifty-five of 66 therefore did not directly establish the complete field
claim under the registered rubric.

All eleven objects are retired because the mechanical pairing is object-wide and there
is no defensible field-level object assembled from the frozen run. No older Health Care
object version exists, so an active lookup returns no object until a corrected Phase A
version is built. **Health Care Phase B is blocked during that interval.** The filesystem
artifacts remain as frozen evidence and must not be re-ingested as though they were the
corrected version.

The request builder now enforces that block: every requested company must resolve to an
active industry object. A missing or SUPERSEDED object stops roster construction before
a Phase B request is written.

E58 arm A remains a valid audit of what the frozen E57 run produced: REFUTED at 1/10
against the exclusive threshold below 0.10. It is not a validation of the retired object
evidence and it does not transfer to a future corrected version. The threshold is not
moved.

## Live application receipt

Both commands were dry-run first. Each dry-run resolved the exact target denominator,
reported no missing rows and left the store SHA-256 unchanged at
`304baf51f19197fd019b3931eb48dc4612400c290f1dee8de7008bf2d9fde400`.

### B3 transition

| Receipt | Value |
|---|---|
| Store SHA-256 before | `304baf51f19197fd019b3931eb48dc4612400c290f1dee8de7008bf2d9fde400` |
| Store SHA-256 after | `953c41200ab6822ff992b591ce23d51d143af21f99cfbb338d5cdd3d065f5a9a` |
| Company rows changed | 59 |
| Explicit E53 read | 59 rows, all `SUPERSEDED` |
| Operational Utilities fallback | 59 rows at `2026-09-05+E47-utilities` |
| Retained E53 claims | 761 VERIFIED_LOCAL; 6 UNVERIFIABLE |

### B4 transition

| Receipt | Value |
|---|---|
| Store SHA-256 before | `953c41200ab6822ff992b591ce23d51d143af21f99cfbb338d5cdd3d065f5a9a` |
| Store SHA-256 after | `f5d1e273332856058bc506be09465239ff8e623b7f49ffaa34ccb120b184f33a` |
| Industry rows changed | 11 |
| Explicit E57 read | 11 objects, all `SUPERSEDED` |
| Active Health Care object lookups | 0 |
| Retained E57 claims | 66 VERIFIED_LOCAL |

Post-transition readback found 328 latest operational company rows over 328 distinct
tickers and zero SUPERSEDED rows in that selection. `batch_health.history()` excludes both
E53 and the burned E59 batch by default. The object corpus now contains 55 active objects;
audit-inclusive history contains all 70 rows. Corpus claim status is unchanged at 6,271
VERIFIED_LOCAL, 64 UNVERIFIABLE and 58 SELF_ATTESTED.

## Conditions for return to the active corpus

B3 returns only through a new company research version finalized and locally verified
under a prompt that requires separate evidence for trajectory and capture.

B4 returns only through a new Phase A version where:

1. every claim backs one named field;
2. identical quote/excerpt windows are not reused across fields;
3. literal containment and semantic field support are reported separately;
4. parent, segment and industry scope match the asserted categorical;
5. proposed, approved, implemented and realized facts are distinguished; and
6. every UNKNOWN records evidence absent or stopped short.

The E61 Industrials prompt already carries these rules. A corrected Health Care prompt
must do the same before its objects are ingested.

## Live pre-application corpus state

Immediately before these retirements:

| Measure | Value |
|---|---:|
| Store SHA-256 | `304baf51f19197fd019b3931eb48dc4612400c290f1dee8de7008bf2d9fde400` |
| Latest active company rows | 328 |
| Distinct latest active tickers | 328 |
| Active industry objects | 66 |
| Corpus VERIFIED_LOCAL claims | 6,271 |
| Corpus UNVERIFIABLE claims | 64 |
| Corpus SELF_ATTESTED claims | 58 |

Lifecycle changes only active selection. Claim counts, scores stored inside the frozen
rows, payloads and research files are not edited. Static exported/parquet artifacts are
not rebuilt by this decision.
