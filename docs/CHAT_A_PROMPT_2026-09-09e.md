# Chat A — next prompt, 2026-09-09 (FDIC matcher)

You own `clab/external/` core. This is all in `marketshare.py`, which is yours — Chat B
diagnosed it read-only and did not edit it while you were wiring.

---

## 1. THE DEFECT — 25 book companies can silently match the wrong bank

`holding_index()` builds `normalised name -> NAMEHCR` with `setdefault`, so when two
institutions normalise to the same key, **the first branch row in the file wins,
arbitrarily.** Measured on SOD 2024:

```
distinct normalised NAMEHCR keys                     2,991
keys shared by MORE THAN ONE holding company           208
institutions sitting on a shared key                   611
BOOK COMPANIES landing on a colliding key               25
```

The worst keys:

| key | institutions | |
|---|---|---|
| `first` | **21** | FFBC, First Financial Bancorp, lands here |
| `peoples` | 13 | |
| `citizens` | 12 | CFG lands here |
| `fnb` | 9 | FNB lands here |
| `community` | 9 | |

Two confirmed today, both matching **exactly** onto the wrong institution:

- **CFG**, Citizens Financial Group, roughly $180bn of deposits → `CITIZENS HOLDING
  COMPANY`, a small Mississippi bank
- **FNB**, F.N.B. Corporation → `FNB FINANCIAL SERVICES, INC.`

`_norm` strips `financial`, `group`, `services`, `holdings`, `bancorp`, so genuinely
distinct institutions collapse onto one key. **This is the exact failure the docstring
says exact-matching was adopted to prevent, happening on the exact match.**

**So the docstring's central claim is wrong and should be corrected.** What actually stops
CFG and FNB is the SCALE GUARD, not the matcher. That makes `SCALE_MIN` load-bearing
rather than belt-and-braces: relax it and CFG ships a deposit trend computed from a
Mississippi bank, carrying a real FDIC URL that makes it look impeccably sourced.

### The fix

**Refuse a colliding key.** Build `key -> set(NAMEHCR)` and return `None` when the set has
more than one member. An ambiguous key is not a match; it is an unknown wearing a match's
clothes. That converts 25 silent wrong-match risks into honest UNKNOWNs and costs nothing,
because those were never right.

---

## 2. THE RECOVERY — `NAMEFULL` as a second exact key, 74 → 83 of 89

The book stores the **bank's** common name; `NAMEHCR` is the **holding company's** legal
name. "Frost Bank" can never normalise to "CULLEN/FROST BANKERS, INC." — that is a
different name, not a formatting difference. But FDIC carries `NAMEFULL`, and `NAMEFULL`
for that institution literally *is* "Frost Bank".

Match on `NAMEFULL` as a second exact key, then roll it up to its `NAMEHCR`. **Nothing is
loosened** — same exact-normalised comparison, and it refuses when a bank maps to more than
one holding company, so the prefix concession stays dead.

Measured over all 89 `regional_banking` names:

```
matched today, NAMEHCR exact       74
NEW via NAMEFULL exact              8      WBS VLY ONB ASB CFR + 3
NEW via space-insensitive           1      SSB - "South State" vs "SOUTHSTATE"
ambiguous, correctly refused        0
still unmatched                     6      CBU FBNC FBP HTH IBOC ZION

coverage 74 -> 83 of 89   (83% -> 93%)
```

Take `NAMEFULL`. The space-insensitive variant is one company and a slightly wider door —
your call.

**ZION is genuinely absent, not mismatched.** Zions collapsed its holding company in 2018,
so there may be no `NAMEHCR` row at all. UNKNOWN is the right answer there.

Note the two fixes pull in opposite directions and that is fine: collision-refusal removes
matches, `NAMEFULL` adds them. Report both deltas separately so neither hides the other.

---

## 3. Then, in your queue

- **`constant_fields` gauge** — you built it; reproducing the known history rather than
  crying wolf is the right acceptance test.
- **Wire `marketshare`**, with the fixes above and the reproducibility result stated:
  zero conflicts on 20 rows and 29 agrees re-deriving two weeks later is what makes this
  low-risk rather than merely tested.
- **Register the field finding as ONE thing**: 0 of 85 Financials + E43's 1 of 40 + 29 of
  29 bank answers ever recorded are computed rather than researched + the E44-matched
  control-arm contamination.
- **E76 Health Care** and **Industrials re-research** — both gate-enforced now, so a repeat
  of E61 retires itself.

## 4. On the `pricing_power` / `technology_risk` observation

Judged: **not stuck**, and **not yet a finding**. The vocabularies are live corpus-wide
(`pricing_power` MODERATE 172 / LOW 105 / HIGH 17), and the evidence is per-company — 47
distinct quotes over 47 URLs, not one claim reused. So it is not the E30 symptom.

It is unanimous convergence on the modal value, which is **E58 arm B's registered
territory**. Writing it up now would be measuring a pattern on the batches that revealed
it. Record it as an observation with both negative checks attached; arm B stays evaluated
on Phase B's own `research_version` after batch 4.

The one cheap check that would settle it: **read the 47 quotes.** Distinct quotes saying
different things and still landing on one label is convergence. 47 generic quotes is a
stuck answer wearing distinct citations. That is a read of text, not a count.

## Non-negotiables

- Verify against the store, not the report.
- Advisory / SHADOW. `promoted` is false and no code path sets it true.
- A default that covers a wiring error must be loud — `setdefault` on a colliding key is
  exactly that, and it has been silent since the module was written.
- Every count carries its corpus state.
