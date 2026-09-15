# Chat A — next prompt, 2026-09-09

You are Chat A in a two-session split on `C:\Users\<your-user>\company_lab`. Read
`docs/CHAT_A_B_PROTOCOL.md` first. You own `clab/external/` core, the measurement
guarantees, and sector Phase A prompts. You do not own `clab/export/`, the request flag,
company batches, or the E56/E58 registrations.

## What moved while you were away — verified against the store, not reported

**E61 is INGESTED and verified.** Chat B ran it after the user's decision to ship. The
re-ingest was a no-op on everything else, which is the useful part of the receipt:
pre-existing objects hashed before and after, **zero changed, zero added, zero removed**,
and the 11 SUPERSEDED Health Care objects **stayed superseded through a full re-ingest**,
so the resurrection guard holds.

Industrials is now **26 active objects**, 142 of 145 claims VERIFIED_LOCAL, and no
non-UNKNOWN field lacks a claim naming it.

**Two deviations from your E61 receipt.** Neither is serious, both are worth knowing
because the receipt is what a future reader will trust:

| your receipt | the store |
|---|---|
| 163 retained claims | **145** |
| one independence domain | **three** — COMPETITOR_FILING 140, COMPANY_IR 3, REGULATOR 2 |
| 19 of 25 objects under eight claims | **24 of 26** |

The single-domain concern stands substantially — 140 of 145 is one domain — but the
receipt overstated it as absolute, and understated the thin-evidence count.

**Other state:** the E53 fallback is gone (a retired newest arm now follows
`superseded_by` or omits, so 59 utilities correctly show as having no current research and
coverage is honestly **17.93%**, not 21.9%). E74 is complete — `earnings_watch` plus
event-driven jumps, verified through the scheduled path. Corpus: 6,531 claims, 64
UNVERIFIABLE, pinned in `CORPUS_SNAPSHOT_2026-09-09.json` on D:.

---

## 1. Write the E61 results — it has no journal entry

`journal/experiments/E61_results.md` does not exist. E61 shipped on a decision, and a
decision with no record is indistinguishable later from nobody having noticed.

Record what it shipped **with**, using the store's numbers rather than the receipt's:
26 objects, 145 claims, 140 of them a single independence domain, 24 of 26 objects under
eight claims, 3 claims still SELF_ATTESTED. **259 companies will be researched against
these**, which is the largest sector in the book. State plainly that this is the thinnest
Phase A shipped so far, and that it was shipped knowingly.

Useful comparison for the write-up: the Health Care batch you retired for B4 had **five**
independence domains and 31 distinct URLs, and was still judged unfit. Industrials has
three domains and is being kept. Those two decisions need to sit in the record together,
because on evidence diversity alone they point in opposite directions.

## 2. Next Phase A — Information Technology, 10 objects

Recommended over Consumer Discretionary (27 objects) for one reason: it is the **cheapest
test of whether the single-domain pattern repeats** when the prompt explicitly asks for
diversity. If IT comes back with three domains again under a prompt that demands better,
that is a fact about the researcher and not about Industrials, and it is worth knowing
before 193 Consumer Discretionary companies depend on it.

```
information_technology   190 companies   10 objects needed
  application_software, communications_equipment, electronic_components,
  electronic_equipment_instruments, electronic_manufacturing_services,
  internet_services_infrastructure, ...
```

Five IT objects already exist and must not be rebuilt.

**The prompt must carry the three rules the last three Phase A rounds earned:**

- **Evidence depth follows the evidence.** A uniform claim count across objects with very
  different literatures is a quota, and a quota has now produced a defect twice — E54's
  uniform 5, and E57's one-claim-per-field, which is what retired Health Care.
- **Context is not support.** A passage relevant to an industry that does not establish
  the specific field does not back that field. E57 lost 30 of 66 claims to exactly this,
  and every one of them verified literally.
- **Source diversity is part of the deliverable.** Say what a single-domain object costs
  and ask for the count explicitly in the report. E61 is the reason this is now a rule.

## 3. Still yours, unchanged

**E76 — Health Care re-research, at the END of the coverage run.** Keep the 11
direct-support claims as seeds: 4 in `structural_growth`, 4 in `regulatory_trajectory`,
2 in `market_structure`, 1 in `substitution_risk`. `replication_difficulty` and
`key_metrics` have none and start clean.

Note for that write-up when it comes: **`replication_difficulty` had zero direct support
in any of the 11 objects, and that is the field E58 arm A was measured on.** Arm A stays
REFUTED; that is a second reason it cannot carry weight, alongside the verdict turning on
a single object.

## 4. The rule the retirements earned, now with a worked example

Three retirements used `superseded_by = None`, and E53's fallback silently served 59
utilities their pre-fix arm at 8.5% fill against 65.7%. **A retirement with no replacement
must state what it costs before it lands.**

There is now a precedent for how to close things, and it distinguishes two cases the
record must not blur:

- **H03 was DELETED — it was never a defect.** The EMA `shift(1)` is deliberate leak
  prevention; "fixing" it would have leaked the current period's close into a signal
  evaluated inside that period.
- **H04 was RETIRED AS ACCEPTED — it is a real defect nobody is fixing.** Entry-study
  returns are biased upward by an unmeasured amount, and every future quote of one carries
  that caveat.

Closing a real defect and closing a non-defect look identical in a changelog. Say which.

## Non-negotiables

- Advisory / SHADOW. `promoted` is false everywhere and no code path sets it true.
- Absent data is `NO_DATA`, never `0`. UNKNOWN is not the bottom of a scale.
- **Verify against the store, not the report.** Both sessions have now caught real defects
  in the other's reported work this way, and the E61 receipt above is the fourth instance.
- A default that covers a wiring error must be loud. When a check returns zero, confirm it
  can return non-zero — E74's zero event jumps was correct, and the first explanation for
  it was wrong.
- **Every count carries its corpus state.** The unverifiable figure has been quoted as
  0.077%, 0.134%, 1.607%, 1.22% and 0.980%, all true of different corpora. The count is
  the stable fact.
- Rule 4: an uncommitted change in a shared path is unowned until someone claims it.
- Corrections go beside the original number, dated, never over it.
