# A1 UNVERIFIABLE scoring doctrine - decision and measured effect

Decision date: 2026-09-08

Measurement as-of date: 2026-09-07

Status: SHADOW / advisory

Promoted: false

## Decision

Keep the A1 doctrine change and name it explicitly:

- `UNVERIFIABLE` means the source was fetched, but the stored quote could not be
  confirmed from the retrieved bytes. This includes quote/source mismatches, failed
  extraction and formatting artifacts. It is not a fabrication label.
- An `UNVERIFIABLE` claim cannot back a scored field and does not enter the usable
  evidence denominator. Its presence caps external confidence at 0.5.
- `SELF_ATTESTED` is reserved for a source that could not be fetched. It may still back a
  score so that network access does not become a company penalty.
- This changes the measurement instrument. It is not merely an implementation detail of
  the A1 numeric and extraction guards.

No score, field, verdict or promotion flag was written to the live store for this
measurement.

## Frozen receipt and reconstruction

The historical A1 receipt is reconstructed from:

- `D:\company_lab_data\external\reports\audit_a1_numeric_demotions.json`
  (SHA-256 `70AA09CBF9C7CC64B59422260ECD0C860218611F6DD93AFF80EB09A98578ED29`):
  79 claims that cleared the old fuzzy-overlap rule but failed the numeric-subset guard.
- Health Care sector claims `c_7a8b9c0d1e05` and `c_7a8b9c0d1e06`: two fetched FDA PDF
  claims whose payload could not be extracted.

Only `verify_status` changes between the two arms. The same stored company records,
claims, scoring code and 2026-09-07 clock are used in both:

| status | before A1 | after A1 |
|---|---:|---:|
| VERIFIED_LOCAL | 5,227 | 5,148 |
| SELF_ATTESTED | 60 | 58 |
| UNVERIFIABLE | 4 | 85 |

The 81-claim transition is therefore 79 `VERIFIED_LOCAL -> UNVERIFIABLE` numeric-guard
claims plus 2 `SELF_ATTESTED -> UNVERIFIABLE` extraction failures.

## Correction to the handoff counts

The saved receipt touches **27 unique company tickers**, not 28. The prior 28 is exactly
what results when the null ticker on object claims is retained as a distinct set member.
It also touches **three industry objects** (`alternative_asset_management`, `reinsurance`,
`retirement_benefits`) and **one sector object** (`health_care`), not four industry
objects. The sector claims have a null `industry_id` by design.

The 27 tickers produce 39 versioned score rows because several were researched in both an
original sector batch and a symmetric rerun. Twenty-six tickers have at least one changed
external score. WKC is the only ticker whose external score is unchanged in every
affected version. CEG is unchanged in E47 but moves in E53.

## Measured scoring effect

Across the 39 versioned rows, 37 external scores moved and 2 did not. Every non-null
movement was non-positive. The mean change was -5.85 points, the median was -3.4, and the
range was -22.8 to 0.0. The largest movement was CMS in the E53 symmetric Utilities run,
58.9 -> 36.1 (-22.8).

The two null score movements are still real effects: WKC in E46 and CEG in E47 kept the
same external score because the demoted claims did not remove their last backing claim
for a scored field, but both confidence readings were capped at 0.5.

| research version | ticker | claims | score before | score after | delta | coverage before -> after | confidence before -> after | scored fields lost |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `2026-09-02` | VRT | 1 | 28.1 | 28.0 | -0.1 | 0.3000 -> 0.3000 | 0.690 -> 0.500 | none |
| `2026-09-02+E43-batch1` | AX | 1 | 53.8 | 43.8 | -10.0 | 0.7600 -> 0.6600 | 0.790 -> 0.500 | company_specific_capture |
| `2026-09-02+E43-batch1` | CINF | 1 | 67.0 | 60.3 | -6.7 | 0.9500 -> 0.8500 | 0.837 -> 0.500 | company_specific_capture |
| `2026-09-02+E43-batch1` | EQT | 2 | 55.0 | 46.0 | -9.0 | 0.8000 -> 0.6700 | 0.800 -> 0.500 | competitive_position_trend, demand_visibility |
| `2026-09-02+E43-batch1` | KLIC | 1 | 55.7 | 52.4 | -3.3 | 0.9500 -> 0.9000 | 0.906 -> 0.500 | pricing_power |
| `2026-09-02+E43-batch1` | KNSL | 1 | 34.8 | 29.8 | -5.0 | 0.6800 -> 0.5300 | 0.770 -> 0.500 | moat_trajectory |
| `2026-09-02+E43-batch1` | MA | 1 | 38.2 | 28.0 | -10.2 | 0.6000 -> 0.4500 | 0.643 -> 0.500 | moat_trajectory |
| `2026-09-02+E43-batch1` | MU | 1 | 68.9 | 63.9 | -5.0 | 0.8200 -> 0.7700 | 0.500 -> 0.500 | pricing_power |
| `2026-09-02+E44-matched` | OXY | 1 | 47.5 | 44.2 | -3.3 | 0.6700 -> 0.6200 | 0.767 -> 0.500 | demand_visibility |
| `2026-09-04+E46-energy` | CNR | 4 | 26.7 | 17.2 | -9.5 | 0.5000 -> 0.3700 | 0.725 -> 0.500 | current_moat_strength, disruption_risk |
| `2026-09-04+E46-energy` | LBRT | 3 | 35.4 | 30.4 | -5.0 | 0.8800 -> 0.6300 | 0.895 -> 0.500 | company_specific_capture, moat_trajectory |
| `2026-09-04+E46-energy` | PR | 1 | 35.5 | 33.8 | -1.7 | 0.6700 -> 0.6200 | 0.767 -> 0.500 | demand_visibility |
| `2026-09-04+E46-energy` | WKC | 3 | 25.0 | 25.0 | 0.0 | 0.5500 -> 0.5500 | 0.737 -> 0.500 | none |
| `2026-09-05+E47-utilities` | CEG | 3 | 43.2 | 43.2 | 0.0 | 0.6200 -> 0.6200 | 0.755 -> 0.500 | none |
| `2026-09-05+E47-utilities` | CMS | 4 | 36.8 | 31.6 | -5.2 | 0.5263 -> 0.4737 | 0.732 -> 0.500 | demand_visibility |
| `2026-09-05+E47-utilities` | PPL | 1 | 36.8 | 34.7 | -2.1 | 0.5263 -> 0.4947 | 0.732 -> 0.500 | regulatory_risk |
| `2026-09-05+E47-utilities` | SRE | 1 | 43.2 | 37.9 | -5.3 | 0.6526 -> 0.6000 | 0.763 -> 0.500 | demand_visibility |
| `2026-09-05+E47-utilities` | WEC | 1 | 43.2 | 41.1 | -2.1 | 0.6526 -> 0.6211 | 0.763 -> 0.500 | regulatory_risk |
| `2026-09-05+E47-utilities` | XEL | 1 | 43.2 | 41.1 | -2.1 | 0.6526 -> 0.6211 | 0.763 -> 0.500 | regulatory_risk |
| `2026-09-05+E49-commservices` | NYT | 3 | 30.8 | 23.3 | -7.5 | 0.5000 -> 0.4000 | 0.725 -> 0.500 | current_moat_strength |
| `2026-09-05+E49-commservices` | PINS | 5 | 35.8 | 26.3 | -9.5 | 0.5500 -> 0.3700 | 0.737 -> 0.500 | current_moat_strength, disruption_risk, market_share_direction |
| `2026-09-05+E49-commservices` | PPLI | 1 | 31.0 | 27.7 | -3.3 | 0.5000 -> 0.4500 | 0.725 -> 0.500 | demand_visibility |
| `2026-09-05+E49-commservices` | ROKU | 2 | 35.8 | 33.8 | -2.0 | 0.5500 -> 0.5200 | 0.737 -> 0.500 | disruption_risk |
| `2026-09-05+E49-commservices` | TTD | 2 | 34.8 | 32.8 | -2.0 | 0.5000 -> 0.4700 | 0.725 -> 0.500 | disruption_risk |
| `2026-09-05+E49-commservices` | WBD | 1 | 27.3 | 24.0 | -3.3 | 0.5500 -> 0.5000 | 0.737 -> 0.500 | demand_visibility |
| `2026-09-06+E51-commservices-symmetric` | NYT | 3 | 74.1 | 57.6 | -16.5 | 0.9500 -> 0.7300 | 0.912 -> 0.500 | competitive_position, current_moat_strength |
| `2026-09-06+E51-commservices-symmetric` | PINS | 5 | 69.7 | 50.6 | -19.1 | 1.0000 -> 0.6000 | 0.925 -> 0.500 | company_specific_capture, competitive_position, current_moat_strength, disruption_risk, market_share_direction |
| `2026-09-06+E51-commservices-symmetric` | PPLI | 1 | 43.6 | 40.2 | -3.4 | 0.9500 -> 0.9000 | 0.912 -> 0.500 | demand_visibility |
| `2026-09-06+E51-commservices-symmetric` | ROKU | 2 | 79.1 | 67.1 | -12.0 | 1.0000 -> 0.8700 | 0.925 -> 0.500 | company_specific_capture, disruption_risk |
| `2026-09-06+E51-commservices-symmetric` | TTD | 2 | 78.1 | 66.1 | -12.0 | 0.9500 -> 0.8200 | 0.912 -> 0.500 | company_specific_capture, disruption_risk |
| `2026-09-06+E51-commservices-symmetric` | WBD | 1 | 45.9 | 42.6 | -3.3 | 1.0000 -> 0.9500 | 0.925 -> 0.500 | demand_visibility |
| `2026-09-07+E53-utilities-symmetric` | BKH | 1 | 35.5 | 34.2 | -1.3 | 0.6526 -> 0.6526 | 0.838 -> 0.500 | none |
| `2026-09-07+E53-utilities-symmetric` | CEG | 3 | 53.1 | 41.4 | -11.7 | 0.8700 -> 0.6200 | 0.892 -> 0.500 | company_specific_capture, moat_trajectory |
| `2026-09-07+E53-utilities-symmetric` | CMS | 4 | 58.9 | 36.1 | -22.8 | 0.9158 -> 0.6000 | 0.904 -> 0.500 | company_specific_capture, demand_visibility, moat_trajectory |
| `2026-09-07+E53-utilities-symmetric` | PPL | 1 | 41.3 | 39.2 | -2.1 | 0.6526 -> 0.6211 | 0.838 -> 0.500 | regulatory_risk |
| `2026-09-07+E53-utilities-symmetric` | SRE | 1 | 44.5 | 39.2 | -5.3 | 0.6526 -> 0.6000 | 0.838 -> 0.500 | demand_visibility |
| `2026-09-07+E53-utilities-symmetric` | VST | 1 | 55.1 | 53.8 | -1.3 | 0.8700 -> 0.8700 | 0.892 -> 0.500 | none |
| `2026-09-07+E53-utilities-symmetric` | WEC | 1 | 53.2 | 51.1 | -2.1 | 0.9158 -> 0.8842 | 0.904 -> 0.500 | regulatory_risk |
| `2026-09-07+E53-utilities-symmetric` | XEL | 1 | 70.8 | 68.7 | -2.1 | 0.9158 -> 0.8842 | 0.904 -> 0.500 | regulatory_risk |

## Later live-store state - dated, not substituted

At measurement time on 2026-09-08, the live store stood at 5,169 `VERIFIED_LOCAL`, 58
`SELF_ATTESTED` and 64 `UNVERIFIABLE`. The saved full replay at
`D:\company_lab_data\external\reports\audit_a1_full_dryrun.json` (SHA-256
`C653D1212FC43CE0458C299AF64B620A147AA15436282A4408B917BD36CC1E5E`) matches that
later state. It does not overwrite the historical 4 -> 85 decision measurement above.

The live drift is itself a reason to bind decisions to claim IDs and a dated status map,
not to reconstruct old scoring effects from whichever statuses happen to be current.
