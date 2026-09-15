# B3 reproduction - E53 trajectory and capture evidence quality

Date: 2026-09-08

Status: SHADOW / advisory

Promoted: false

Source under test: frozen payload `f92abdf0887e91cd072d`, research version
`2026-09-07+E53-utilities-symmetric`.

## Verdict

**B3 is reproduced.** The failure is a decision-process defect, not merely a few weak
examples. The payload mechanically reuses one evidence window for two different fields,
frequently treats an unresolved regulatory or operating event as a realized outcome, and
labels UNKNOWN as `evidence absent` without recording an exhaustion trail.

No company value or frozen Pass A artifact is changed by this reproduction. Relevance is
not the same as sufficiency, and an unsupported answer does not authorize filling an
UNKNOWN.

## Denominator and rubric

The audit read the two stored claims and their supplied excerpt for every company:
`moat_trajectory` and `company_specific_capture`, 118 field claims across 59 companies.
The two fields use the identical source URL, quote and excerpt for **59/59 companies**.

The 48 answered pairs were classified by what the attached passage itself establishes:

- **Realized outcome:** contains an observed order, earned/allowed return, booked
  impairment/refund, or implemented recovery mechanism directly relevant to at least one
  target field. This does not endorse both categorical labels or their magnitudes.
- **Unresolved substituted for realized:** the central support is a request, proposal,
  recommendation, allegation, expectation, investigation or conditional future benefit.
- **Relevant context only:** the passage bears on financing, demand, regulation or
  operations but does not establish a realized directional or capture outcome.
- **Unrelated:** the passage does not answer either target field.

| Attached-passage result | Companies | Rate among 48 answered pairs |
|---|---:|---:|
| Realized outcome relevant to at least one field | 11 | 22.9% |
| Unresolved event substituted for realized outcome | 19 | 39.6% |
| Relevant context only | 16 | 33.3% |
| Unrelated to both target fields | 2 | 4.2% |

The strict pass rate cannot be read as 22.9%: that row says only that at least one
realized, relevant fact is present. It does not prove both delivered labels. A
field-by-field relabeling requires new research and is outside this reproduction.

## Exact classification receipt

### Realized outcome relevant to at least one field - 11

`D`, `ES`, `ETR`, `HE`, `NEE`, `NWN`, `OGS`, `OTTR`, `SWX`, `TXNM`, `WEC`.

These include such facts as earned versus allowed returns, final orders, booked refunds,
rate-base reductions and implemented recovery. Parent scope and magnitude still need
calibration before either exact categorical is retained.

### Unresolved event substituted for realized outcome - 19

`AEE`, `AEP`, `AWK`, `AWR`, `CMS`, `CNP`, `DTE`, `DUK`, `FE`, `HTO`, `MGEE`, `NFG`,
`NI`, `NRG`, `PCG`, `PNW`, `POR`, `UGI`, `XEL`.

Examples of the repeated error class are a settlement in principle awaiting an order,
requested incentives conditional on approval, complaints seeking a remedy, management's
expected benefits, and a recommendation still requiring commission action. These facts
can be relevant risks or watch items; they are not realized capture outcomes.

### Relevant context only - 16

`ATO`, `CEG`, `CPK`, `ED`, `EXC`, `IDA`, `LNT`, `MDU`, `MSEX`, `NWE`, `ORA`, `PEG`,
`SO`, `UTL`, `VST`, `WTRG`.

The common gaps are direction over time, parent/subsidiary scope, financing and lag, and
the difference between pass-through revenue or contract tenor and earned economic
capture.

### Unrelated to both target fields - 2

`CWEN` cites acquisition fair-value methodology. `EIX` cites supplemental cash-flow,
accrued-capex and related-party insurance material. Neither passage establishes moat
trajectory or company-specific capture.

## The 11 UNKNOWN pairs

All 11 UNKNOWN pairs say `evidence absent`, but **0/11** records name the searched sources,
the attempted comparison, or an exhaustion criterion. Each records one attached excerpt;
that is not evidence that the requested evidence was absent from the available record.

| Attached-passage result | Companies | Rate among 11 UNKNOWN pairs |
|---|---:|---:|
| Direct recovery evidence ignored | 2 | 18.2% |
| Topic-adjacent evidence requiring more work | 4 | 36.4% |
| Passage does not answer the targets | 5 | 45.5% |
| Documented evidence-exhaustion trail | 0 | 0.0% |

- Direct recovery evidence ignored: `CWT`, `SR`. CWT records an implemented initial
  settlement phase with final approval pending; SR records annual adjustment rights, a
  cap and restrictions on deficiency recovery.
- Topic-adjacent evidence requiring more work: `AES`, `AVA`, `NJR`, `SRE`.
- Non-answering passage: `BKH`, `EVRG`, `OGE`, `PPL`, `TLN`.

The result does not say the eleven fields should be filled. It says the delivered record
does not support the stronger procedural claim that evidence was absent.

## Required correction for a future rerun

Future Utilities research must keep separate evidence receipts for trajectory and
capture, distinguish proposed from approved and approved from earned, state the
parent/subsidiary denominator, and record the actual search/exhaustion trail for every
`evidence absent` result. The frozen E53 payload remains an auditable historical result.
