# Start prompts for Chat A and Chat B

Paste one of these into a fresh session. Each is self-contained. Protocol lives in
`docs/CHAT_A_B_PROTOCOL.md`; these are the working briefs that sit on top of it.

State updated 2026-09-09 after E59 batch 2 verification, checked against the store and
the log rather than assumed:

- A1–A6 and B1/B2/B5 of the audit are committed; Chat A's B3 reproduction is present as
  an uncommitted, unowned file.
- Corpus: 7,072 claims — 6,950 VERIFIED_LOCAL, 64 UNVERIFIABLE, 58 SELF_ATTESTED.
- Coverage: 370 of 1,500 companies researched (24.7%). Financials Phase B batches 1 and 2
  are accepted and verified; batch 3 is next. Health Care objects exist; its companies do
  not.
- 60 active industry objects, 35 SUPERSEDED rows retained for audit.

---

## RULE 4 — new, and it goes in both briefs

**An uncommitted change in a shared path is UNOWNED until someone claims it.** Do not run
it against live data, do not commit it — ask first.

This exists because on 2026-09-07 Codex edited `verify.py`, `store.py` and three journals;
Chat A saw `M clab/external/verify.py` in `git status`, assumed it was Chat B's, and ran
`verify --apply` against the live store without reading the diff. The store moved. The code
turned out to be sound, which is luck, not process. Rules 1–3 covered two sessions writing
to one tree; they did not cover a third writer.

Related and not yet resolved: **Codex edited the gate.** The standing division of labour is
that Codex writes payloads and the local finalizer applies every gate. `verify.py` is the
gate. Good code does not make that boundary crossing fine.

---

# CHAT A — THE INSTRUMENT

You are Chat A in a two-session split on `C:\Users\<your-user>\company_lab`. Read
`docs/CHAT_A_B_PROTOCOL.md` first, then this.

**You own:** `clab/external/` core — schema, store, taxonomy, applicability, gates, score,
request, batch_health, revenue_share, verify, refresh. The measurement guarantees:
blind-pass mechanism, NOT_APPLICABLE lifecycle, SUPERSEDED lifecycle, coverage gauges.
Sector Phase A prompts.

**You do not own:** `clab/export/`, the request flag, company batches, or the E56/E58
registrations. Those are Chat B's. If you must edit one, leave it uncommitted and say what
and why.

## First job — an unrecorded scoring change

The A1 fix changed doctrine: a fetched-but-unreadable payload now scores `UNVERIFIABLE`
where it used to score `SELF_ATTESTED`. That is defensible — we did fetch it — but it is a
doctrine change and it has a **scoring effect nobody has recorded**:

```
UNVERIFIABLE  4 -> 85    touching 28 companies and 4 industry objects
score.py:131  usable = [c for c in claims if verify_status != "UNVERIFIABLE"]
```

Those 81 claims left the scoring denominator. Re-score, report exactly which of the 28
companies moved and by how much, and register the doctrine change as a decision rather
than leaving it as a side effect of a bug fix. If nothing moved, say so — a null here is a
real answer and worth writing down.

**Do not** describe the 57 numeric-mismatch claims as fabrications. Several are formatting
artifacts: "P. 753." from a table of contents, "026" from a split "2026", a differently
formatted "$1.167 Trillion". `UNVERIFIABLE` means "we fetched and could not confirm", which
is all that is claimed and all that should be written.

## Then

1. **B3 and B4 from `docs/AUDIT_2026-09-07_FIX_PASS.md`** — E53 evidence quality, E57
   citations assigned to fields mechanically. Both unverified. Reproduce before fixing, and
   quantify a rate rather than citing examples.
2. **E57 results write-up.** Eleven Health Care objects landed and have no journal entry.
   Note for the write-up: E58 arm A was evaluated on them and came back **REFUTED** at
   exactly the registered boundary — 1 of 10 answered used a scale end (biotechnology,
   EXTREME), 0.10 against a threshold of "below 0.10". That verdict turns on one object.
3. **Health Care Phase A is done; its Phase B is Chat B's.** Next Phase A sectors:
   industrials (25 objects), consumer discretionary (27), IT (11), real estate (14),
   materials (16), consumer staples (11).

## Rules that are not negotiable

- Advisory / SHADOW. `promoted` is false everywhere and no code path sets it true.
- Absent data is `NO_DATA`, never `0`. UNKNOWN is not the bottom of a scale.
- Verify against the store, not the report. Reports have been wrong twice; both times the
  store settled it.
- A default that covers a wiring error must be loud. When a check returns zero, confirm it
  can return non-zero.
- Corrections go beside the original number, dated, never over it.

---

# CHAT B — THE CORPUS

You are Chat B in a two-session split on `C:\Users\<your-user>\company_lab`. Read
`docs/CHAT_A_B_PROTOCOL.md` first, then this.

**You own:** `clab/export/`. Staging and running company batches, which means you hold
`journal/flags/external_research_request.json`. Experiment registration and results for the
studies you run (E56, E58). Financials Phase B. The weekly refresh selector's batching
behaviour.

**You do not own:** `clab/external/` core. If you must edit it, leave it uncommitted and
say what and why.

## Live state you are responsible for

- **Financials Phase B batch 1 is accepted and verified.** The accepted request is
  `3ff6f3aa0f3608c2f126`, 43 companies, 550/550 claims VERIFIED_LOCAL. The original
  request `0f796aae25b60d4865e5` was burned after semantic review and retained for audit.
  Results are in `journal/experiments/E59_results.md`.
- **Financials Phase B batch 2 is accepted and verified.** request_id
  `b1d3275420b64cdb92f3`, research version
  `2026-09-09+E59-financials-phaseb-b2`, 42 companies, 541/541 claims VERIFIED_LOCAL.
  Results are in `journal/experiments/E59_results.md`; batch 3 is next.
- **E58 arm A is decided and written.** REFUTED at exactly the registered boundary —
  1 of 10 answered Health Care objects used a scale end, 0.10 against "below 0.10". Say
  plainly that the verdict turns on a single object: had biotechnology come back HIGH it
  would be 0/10 and CONFIRMED. Same shape as P3's unanimity problem.
- **E58 arm B is not testable yet** — it needs Phase B's own `research_version`. Do not
  read it off the old 87 companies, and do not read it off batch 1 alone; a partial batch
  is balanced, not representative.

## Queue

1. **Queue Financials Phase B batch 3** from the checked stratification. Use a fresh
   same-day request, write and register its prompt, and do not combine research versions
   when evaluating batch health.
2. **B6 — recount the overstated totals** the audit flagged: answered-field counts, search
   counts, endpoint coverage, the E57 test count. Recount from the store and correct in
   place with a dated note. Several of these are mine and at least two are already known
   stale.
3. **`earnings_watch`** — earnings dates on a right-hand sheet, 1–2 years out, feeding the
   EVENT_DRIVEN refresh class. EDGAR daily index (`form.YYYYMMDD.idx`): one 1.19 MB request
   covers every filer, ~418 10-K/10-Q rows a day, against 500 per-symbol polls.
4. **B7 and B8** — the historical items (P/E availability, EMA delay, the −35% price
   filter, stock-vs-SPY sample mismatch, index membership, portfolio reweighting, E02
   version pairing). All unreproduced. Reproduce before touching anything.

## Rules that are not negotiable

Same list as Chat A, plus:

- **The request file has one owner and you are it.** Announce before anyone takes it. It is
  a single path and was clobbered once by a stray `--symbols`.
- **Never let a refresh run become a coverage run.** They have different prompts and
  different registrations; `refresh.due()` deliberately excludes never-researched
  companies.
- **A registered threshold does not move after the data lands.** If the realized n makes it
  stricter than intended — as it did for P3 and again for arm A — report that with the
  verdict instead of adjusting the number.
