# Next session — after 2026-08-31 09:40 (box came back from the electrical fault)

**Tree clean. `promoted` is false. Nothing here is graded against forward returns.**

---

## State right now

| what | state |
|---|---|
| **v2 book** | **FINISHED and repaired — 1,472 of 1,472, 0 failed, 0 parse failures in 4,416 payloads.** Frozen at `D:\company_lab_v2\data\exports\company_lab_v2_FINAL_1472.xlsx` + `scores_v2_FINAL_1472.csv` |
| **the five dead components** | **regenerated** (KGS/R/PLMR SG, AIZ/NWSA BQ), folded, book re-frozen |
| **E37 + book review** | **re-run on the repaired book.** See `journal/experiments/parse_bug_reread.md`; pre-fix results kept as `prebugfix_*` |
| **E38 control lane** | **running**, resumed 09:32 at 906. ~43 s/company, 562 left, ETA ~6.7 h |
| production | untouched, 1,501 rows |
| ollama | running — **it does not survive a reboot, start it first** |

### The freeze caught one thing mid-flight

The snapshot copy at `D:\company_lab_data\e37_snapshot_full\v2_scorecards` was
interrupted at **278 of 1,473 files**. It was re-copied whole before E37 was re-run, and
the snapshot parquet was md5-verified identical to the live one. **If the box dies during
a `cp -r` again, check the file count, not the exit code** — the shell never returned one.

### The fault also zeroed one control payload — handled

`MAC` MG in the control cache was written as **1,771 bytes of NUL** at 08:23 and is
quarantined at `D:\company_lab_data\qual_corrupt_backup\`. With the file gone the resume
stopped counting MAC done: **it is first in batch 1 of the 21:42 restart**, so no extra
pass is needed. Nothing else on either lane is corrupt; the full sweep is in
`journal/experiments/cache_audit_20260831.md`.

### The box crashed five times today and the lane is now a Scheduled Task

Unexpected shutdowns at **01:08, 08:03, 11:07, 19:32, 21:44**; boots at 07:20, 08:25,
15:51, 19:32, 22:08. The lane died at 11:16 with the 11:07 crash and **the box stayed
down until 15:51**, then ran unattended without it. An earlier note here blamed a
detached-`ollama` mistake for those ten hours — that was wrong, and the repo `CLAUDE.md`
now says so.

A shell-launched lane cannot survive this box. It is registered as
**`E38ControlLaneResume`** (`scripts/resume_control_lane.ps1`): at-logon plus a
30-minute repeat, `IgnoreNew`, restarts `ollama` detached, waits on `GET /api/tags`
rather than the process, resumes from cache, and **disables itself at 1,471**. Restarted
22:36 at 1,046 companies — **425 left, roughly 6.5 h of scoring** spread across however
many crashes intervene.

### C: is asking for a full chkdsk

Every one of those crashes logged NTFS event 98, *"Volume C: needs to be taken offline
to perform a Full Chkdsk"*, and `volmgr` 46, *"Crash dump initialization failed"* — so
there is no memory dump to read either. C: is the 49,423-hour spinner that holds every
repo and venv. **This is a hardware decision for the user, not something to work around.**

### If the lane is still running

It resumes by itself: `bash scripts/run_control_lane.sh` auto-skips what exists.
Check with `ls D:\company_lab_data\qual_qwen_struct | wc -l` divided by 3.

---

## What the re-read settled

**The "dead judged components" were entirely ours.** The book review's broken list is now
empty: SG 3 -> 0, BQ 2 -> 0. E37's `SCORED -> NULL` on the judged half was **37 -> 18** —
nineteen of them were `extract_json` deleting a valid answer. The 18 that remain are the
candidate genuinely abstaining.

**E37's headline is unaffected.** Raw +8.74 -> +8.79, common support +4.251 -> +4.245,
`bq_moat` +2.53 on 1,280 companies. About half the lift is the schema filling abstentions,
about half is the same evidence scored higher.

**The book is still a different book.** Coverage gate 1,410 -> 1,414, `INSUFFICIENT_DATA`
62 -> 58, and band agreement went **down** (541 -> 535). 28 of the top 50 survive.

---

## Open, in the order I would take them

1. **Let `E38ControlLaneResume` finish the control lane** (MAC is back in it; the task
   disables itself), then re-run E38 at full n. Its interim reading (875 companies) was format ~3% / model ~92%; that needs
   restating at 1,471. The whole-cache fill numbers are already stark: under the same
   structured regime LFM2.5 completes BQ on 99.8% of companies, qwen on **8.4%**.
2. **Regenerate the ten probe-scored companies** (AAPL, CAT, HD, JNJ, JPM, LIN, NEE, PG,
   UNP, XOM), ~3 min of GPU. They entered the v2 book from the 08-29 06:52 throughput
   probe, and `structured` / `num_predict` are not in the cache key, so the payloads
   cannot say which regime produced them. Their signature matches the lane exactly; this
   converts that from consistent to proven.
3. **E39's decision** — repair path vs leave it. Needs the user. 271 companies' moat
   scores exist only because unexplained dimensions make the 6-of-11 quorum, and the fix
   must not be "require a reason" at the scorer.
4. **Per-dimension evidence on BQ.** E41 is a floor because only SG verifies per sub-test.
   Needs `_scored_item(..., with_evidence=True)` on BQ in `prompts.schema_for`, `parse_bq`
   verifying per dimension, **and a full re-run** — the prompt change moves `prompt_sha1`,
   so the whole lane regenerates. Same size as the run that just finished.
5. **Cyclicals — F2 mid-cycle earnings.** Largest known scoring defect (carried).

## Carried

* **E29's applicability map stays refused.** Measured, empty, do not reopen on a null rate.
* **`sector_neutral_score` is the cross-sector headline**, not `score`.
* **E40/E41 are untouched by the parse fix** — they read payloads, not the folded book.
  LFM2.5 cites text absent from the filing 9.7% of the time against qwen's 0.5%; E41's
  citation gate takes coverage 1,184 -> 1,321, costs 16 companies, drops 264 answers.
* Payloads written before 2026-08-30 ~20:00 do not carry `structured` / `num_predict`.


### Unverified when we stopped (2026-08-31 22:50, lane at 1061/1471)

`E38ControlLaneResume` was left **running** on purpose — it is built to finish overnight
and disable itself. Two things were never confirmed:

- **That `IgnoreNew` really suppresses the 30-minute repeat** rather than starting a second
  lane. The 22:37 fire returned `0x800704E0`, which is probably the ignored-duplicate path
  but was not checked. First thing to look at: `grep -c "starting lane"` in
  `D:\company_lab_v2\journaluns\control_resume_*.ps.log` should be **1** per boot, and
  there should be one `bash.exe` and one `ollama.exe`.
- **Whether the lane survived the night at all.** Check the payload count against 1,471 and
  the task's `State` — if it disabled itself, it finished.

Then: re-run E38 at full n.

**Box, before anything else runs long:** `company_lab` is still on C:, which is asking for
an offline `CHKDSK /F` and logged 36 `disk` Event-7 bad blocks in 14 days. Ten repos already
moved to `D:epos` behind junctions via `perf_probe\migration\migrate_to_D.ps1`. Right
order is **lane finishes -> migrate company_lab -> chkdsk**, not the other way round.
