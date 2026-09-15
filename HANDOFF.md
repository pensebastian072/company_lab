# company_lab — handoff, 2026-08-11

Read `CLAUDE.md` for invariants, `PLAN.md` for the build plan. This file is only
"where things stood".

## 2026-09-12 — Phase A is effectively done; the remaining work is Phase B

One long unattended session, six experiments (E82–E87), seven commits. Operating document is
`docs/MASTER_PLAN_TO_1500_2026-09-11.md`, which was edited twice today (see below). Everything
SHADOW; `promoted` is false; no score moved and no company was re-ranked.

```text
                                       session start   session end
units with an object                        160 of 208    208 of 208
objects at 3 of 3                                    69            64
companies whose unit has an object                1,202         1,500
companies eligible for Phase B (>=2/3)            1,026         1,192
units still at exactly 1 of 3                                      48  (162 companies)
objects failing rule 3 (no non-issuer source)                      56  (203 companies)
answered ordinals with NO certifying evidence left                  1  (ai_accelerators, an
                                                                        unreadable page - ours to fix)
ordinals RETRACTED this session                                    13  (3 on window instability,
                                                                        10 whose quotes are not on
                                                                        their cited sources)
tests                                             1,387         1,413
```

**Read these first if you are picking this up:**

1. `journal/experiments/E84_WINDOW_STABILITY_2026-09-12.md` — the one that overturned its own
   morning's work. Three computed ordinals were **retracted** because a 3-year window put them
   in a different band than the 1-year window did. The rule that came out of it generalises:
   *any ordinal computed from a single window of market data is unstable until a second window
   is tried.*
2. `journal/experiments/E87_FRONTIER_2026-09-12.md` — Census M3 says civil aerospace grew +4.5%
   real where the members' own revenue implied +15.1%. A two-band error on the unit holding
   Boeing, RTX and GE. This is the best evidence in the corpus for why rule 4 wants a published
   quantity.
3. `journal/experiments/E90_OBJECT_CLAIMS_WERE_NEVER_VERIFIED_2026-09-12.md` — the object files
   are a SECOND population from the store and had never been verified, because they had no field
   to record the answer in. They are now stamped with `verify_status`/`match_mode`/`overlap`.
   11 answered ordinals have no certifying claim left; `mortgage_reits` has been counted as
   Phase-B eligible on two `overlap_only` claims.
4. `journal/experiments/ACCEPTANCE_GATE_FALSE_REJECT_2026-09-11.md` — the plan's Phase 0
   criterion "must ACCEPT E47" is **struck**. E47 answers `competitive_position` for 59 of 59
   companies and `competitive_position_trend` for 0 of 59.

**What is built and can be reused**

- `clab/external/industry_growth.py` (+26 tests) — `structural_growth` from the members' own
  revenue, under the user's authorised exception to rule 4. Five guards: ≥4 peers, no member
  over 50% of the aggregate, aggregate within 5 points of the median member, structural revenue
  moves excluded, and **share-count growth ≤2%/yr** (growth that arrived with new shares was
  bought, not earned — this is what REITs do). `agreeing_growth` is the only supported entry
  point: every window must pass and they must agree on the band.
- `scripts/apply_industry_growth.py` — **refuses to run without `--units`**, on purpose.
- `scripts/retract_unstable_growth.py` — marker-scoped, idempotent, backs up first.
- `scripts/create_industry_objects.py --sector "<GICS name>"` — skeletons for a whole sector.

**The revenue route is exhausted.** Re-run over every unanswered unit with all guards: **1 pass
in 124**. 84 of the refusals are units with fewer than four members. It carried 8 units total.

**RESTARTED CLEAN 2026-09-13 on the V2b patterns.** The book in
`D:\company_lab_data\external\phase_b_lfm25` is a FRESH 1,500-row run. The previous 700
rows are archived at `phase_b_lfm25_v1patterns` with their own `ARCHIVE.md` - read it
before touching them, and never merge the two.

Why the restart rather than finishing the 700: the retrieval patterns decide what evidence
any model ever sees, so a book with 700 rows on V1 pools and 800 on V2b would not be
internally comparable - the same error as mixing two models in one directory. Every row is
now stamped `"patterns": "v2b"`; the archived rows carry no such field, which is how you
tell them apart. **Cost of the restart: about 7 extra GPU-hours**, ~16 hours total from
scratch at ~93 companies/hour.

**What the A/B actually said, because it does not all point one way:**

- The **contradiction gate is a decisive win** - self-contradiction 33.3% -> 0.0% in
  production (E44, n=40 paired). It is also a REPAIR PASS, not a re-score: it reads
  `(field, value, quote)`, all already on disk, so `scripts/apply_contradiction_gate.py`
  fixed the archived book with no GPU at all (69 of 700 rows, idempotent).
- The **pattern rewrite is roughly NEUTRAL on outcome**. Mean modal share 0.784 -> 0.778,
  better on 3 fields and worse on 4. It fixes measured junk retrieval and raises
  two-sidedness (competitive_position 0.000 -> 0.234, pricing_power 0.036 -> 0.199 with
  recall UP), but it did not move discrimination at n=40. It was adopted for the junk
  removal and the consistency, not on a proven downstream gain - say so when reporting it.
- **`current_moat_strength` is DEAD under both pattern sets** - 1.0 modal share either
  way, MODERATE for 242 of 243. No pattern written here fixes it, and it should not be
  tuned further on this evidence. Same for `technology_risk` two-sidedness at 0.000.
- The first pattern draft was **refused by its own A/B** (moat_trajectory pool 300 -> 40)
  and discarded. That is what the A/B rule is for.

**TWO LANES RUN IN PARALLEL as of 2026-09-13** - the user offered the CPU ("If you need
to use my cpu to run more go for it"), and it is worth roughly +79%.

```text
GPU lane  CompanyLabPhaseBv2    scripts
esume_phase_b_v2.ps1   :11434   _status.json
CPU lane  CompanyLabPhaseBCpu   scripts
esume_phase_b_cpu.ps1  :11435   _status_cpu.json
both      24-company blocks, 30-minute repeat, IgnoreNew, same out dir, same model
stop both Disable-ScheduledTask -TaskName CompanyLabPhaseBv2,CompanyLabPhaseBCpu
```

Measured, paired on PTC/NVDA/INTU/FSLR rather than assumed:

| | s/company | companies/hour |
|---|---|---|
| GPU lane alone | 67.4 | 53 |
| CPU lane (while GPU lane ran) | 59.6 | 60 |
| GPU lane (while CPU lane ran) | **102.8** | 35 |
| **both together** | | **~95** |

So the second lane is **+79%, not +100%** - it takes cores the GPU lane needs for
tokenisation, sampling and the D: reads. `CLAB_NUM_THREAD=5` of 8 caps it for that reason.
~27.9 GPU-hours becomes **~15 hours wall**.

**The CPU lane is genuinely off the card.** `CUDA_VISIBLE_DEVICES=-1` does NOT hold ollama
off the GPU here - a server started that way reported `size_vram=1.79GB` and was competing
with the fast lane. Only the per-request `num_gpu` option works (`CLAB_NUM_GPU=0`), and
`run_phase_b_local.py --cpu` asserts `size_vram == 0` and refuses to run otherwise, so a
regression stops the lane instead of quietly stealing the card.

**The two lanes walk the book from opposite ends** (`--reverse` on the CPU lane) so they
never pick the same company at the same moment. Worst case where they meet is one company
researched twice, which costs time and corrupts nothing.

**Young registrants now fall back to the 10-Q.** ADIG and MFP were written as permanent
0/12 rows because neither has ever filed a 10-K - both are recent spin-offs whose newest
forms are 10-12B/A and one 10-Q. A file existing meant the resume counted them done
forever: the MAC failure in a new costume. `load_filing` now falls back to the 10-Q, the
row records which `form` backed it, and both were re-queued by deleting their files.
**A 10-Q is thinner evidence, not equivalent evidence** - it carries no business
description and usually no risk factors - so never pool the two forms without checking it.

**RUNNING 2026-09-13: the Phase B lane, now on LFM2.5 ONLY.** The user's instruction was
"dont use qwen use lfm 2.5" / "only use lfm2.5", so the lane restarted against
`hf.co/mradermacher/LFM2.5-2.6B-Finance-GGUF:Q4_K_M`.

```text
model     hf.co/mradermacher/LFM2.5-2.6B-Finance-GGUF:Q4_K_M
out dir   D:\company_lab_data\external\phase_b_lfm25        (NOT phase_b_local)
lane tag  phase_b_v2_lfm2.5-2.6b-finance
block     24 companies (~27 min) - NOT 55
check     type D:\company_lab_data\external\phase_b_lfm25\_status.json
log       journal
uns\phase_b_lfm25_<date>.log   (.err holds tracebacks)
stop      Disable-ScheduledTask -TaskName CompanyLabPhaseBv2
resume    Enable-ScheduledTask  -TaskName CompanyLabPhaseBv2
```

**It writes to its own directory on purpose.** The 317 files in `phase_b_local` were
scored by `qwen2.5:7b`. E38 settled that the gap between two scorers is ~92% MODEL and
only ~9% format, so one directory holding both would be a book whose rows are not
comparable to each other. Nothing was deleted - the qwen 317 are intact and are now a
paired control on the companies the LFM lane will also cover.

**LFM2.5 is SLOWER and fills MORE.** Probed on 6 companies 2026-09-13:

| | qwen2.5:7b | LFM2.5-2.6B-Finance |
|---|---|---|
| s/company | 30.6 | **67.4** |
| fields answered | 8.52 / 12 | **9.2 / 12** |
| claims/company | 6.94 | **7.7** |
| whole book | ~12.4 GPU-h | **~27.9 GPU-h** |

The smaller model being 2.2x slower is not a misconfiguration - it is fully on the card
(`size_vram` 1.90 GB of 1.90 GB) and it is generating more. That is consistent with E40's
finding that LFM2.5 is a **more willing** scorer, which is not the same as a better one:
E40 measured it citing text that is not in the filing **9.7%** of the time against qwen's
0.5%. The containment check in `research()` drops a claim whose quote fails, so the fill
figures above are post-containment - but a higher fill from a more willing model still
needs the E41 citation gate before it is read as better evidence.

Block size moved 55 -> 24 for the same reason: 55 x 67.4s = 62 min would overrun the
30-minute repeat window on every single block.

**PAUSED 2026-09-12 ~22:30 at the user's request ("stop after this one gonna turn off"). The task
is DISABLED, so nothing restarts on its own. 316 of 1,500 companies are saved. To pick up:**

```text
Enable-ScheduledTask -TaskName CompanyLabPhaseBv2     <- resumes the 30-minute cadence
Start-ScheduledTask  -TaskName CompanyLabPhaseBv2     <- optional, go immediately
```

Roughly **10.1 GPU-hours** of work remain at the measured 30.6 s/company. Nothing is lost by the
shutdown: each company's JSON is written the moment it finishes, so at worst the one company in
flight is redone.

**First job on resume, BEFORE ingesting anything** - decide which fields the v2 lane should stop
emitting. Measured across the 274 companies done at the time of pausing, five fields are >=75% a
single value:

```text
competitive_position        95% of 126 answered   LEADER 120   <- and 148 UNKNOWN
current_moat_strength       87% of 264            STRONG 230
disruption_risk             87% of 270            ELEVATED 235
regulatory_risk             85% of 266            ELEVATED 227
competitive_position_trend  83% of  35            IMPROVING 29
```

`competitive_position` is the worst and it was NOT the one expected. Its retrieval pattern looks
for "we are a leading ...", which is how every company describes itself, so the field measures
whether the filing contains a self-congratulatory sentence rather than the company's position -
and it carries 12 points. `current_moat_strength` (10 pts) has the same shape on "our brands /
patents / proprietary".

**Standing recommendation: drop `competitive_position` and `current_moat_strength` from the v2
lane** rather than let 22 points of near-constant signal inflate coverage against the 0.80 band
gate. The fields that genuinely discriminate are `moat_trajectory` (15 pts, STABLE 128 /
STRENGTHENING 46 / WEAKENING 40), `demand_visibility`, `company_specific_capture`,
`market_share_direction` (computed) and `industry_structural_growth` (inherited).

**Original note, still accurate:**

**The Phase B v2 lane.** Scheduled Task `CompanyLabPhaseBv2`, 30-minute
repeat, IgnoreNew, disables itself at 1,500. One 55-company block per run, ~28 min, ~30 s/company,
**~12.4 GPU-hours total**. Approved by the user 2026-09-12 as "phase b v2, to see" after being told
plainly it is not the standard of the existing 311 rows.

```text
check        type D:\company_lab_data\external\phase_b_local\_status.json
log          journal
uns\phase_b_v2_<date>.log   (+ .err for tracebacks)
stop         Disable-ScheduledTask -TaskName CompanyLabPhaseBv2   (or just shut down)
resume       Enable-ScheduledTask  -TaskName CompanyLabPhaseBv2
go now       Start-ScheduledTask   -TaskName CompanyLabPhaseBv2
```

Saving is per COMPANY: each writes its own JSON immediately and anything on disk is skipped, so a
kill mid-block loses at most the company in flight. Every output carries `lane="phase_b_v2"`.

**NOTHING IS INGESTED and nothing should be until two numbers are looked at.** The lane writes JSON
to D: only; the chain to the store is assemble -> `finalize` -> `acceptance` -> `research_ingest
--apply`. Before any of it:

1. **Four fields are near-constant** - current_moat_strength STRONG 35/40, disruption_risk ELEVATED
   36/40, regulatory_risk ELEVATED 35/40, technology_risk ELEVATED 31/40. That is 20 of 100 points
   adding COVERAGE without DISCRIMINATION, which is how a company crosses the 0.80 band gate on
   content-free fields. CLAUDE.md rule 3 exists to stop exactly that.
2. **One independence domain for every company** (the filing itself) against a mean of 2.76 on the
   existing rows, so Evidence Quality's domain component scores 1.25 of 5 structurally and forever.

So v2 is a first pass for companies that currently have NOTHING, not a replacement for the Codex
lane. Keep the two distinguishable.

**Resume here.** The frontier is 49 units at 1 of 3, and **41 of them hold five companies or
fewer** — a long thin tail of separate research problems. The concentrated value is:

- five REIT units (52 companies) + `hotels_resorts_cruise_lines` (17), all blocked on the same
  thing: a published quantity for a property or travel sector measuring **demand** not supply,
  covering the unit rather than one slice. **Do not reach for Census Construction Spending** —
  E87 explains why it inverts the field's meaning and why its "Office" line cannot be
  attributed.
- Phase B itself, which is barely started: **311 of 1,500 companies have a live research row.**
  That is now the critical path, not Phase A.

**Debt, recorded not hidden — and E88 measured it properly: it is 57 units and 207 companies,
not the four I first thought.** Run `PYTHONPATH=. .venv\Scripts\python.exe scripts/audit_objects.py`
for the current totals; 49 of the 57 are Industrials, from the E79/E81 sessions that were 100%
sec.gov, and two of them (`flow_filtration_equipment`, `financial_data_ratings`) sit at 3 of 3 and
would ship as finished experts while failing rule 3. Census M3 does NOT discharge this wholesale —
E88 records why the obvious attempt was refused. Originally-noted: four revenue-route units carry
no non-issuer source (rule 3);
eight single-member units owe their named private or foreign peers (rule 5). Both would fail an
object-level acceptance run. `journal/flags/external_research_request.json` is stale (NY-date
rule) and must be re-staged the day it is used.

**Two reusable lessons about sources**, because they cost hours today:

- A PDF table is citable when a row carries **levels next to their percent change** — the
  arithmetic then identifies the columns (Census M3, MARTS). It is not citable when the row is
  percentages only and the header did not survive extraction (Fed G.17), or when a chart's
  labels and values separate (BEA PCE). Form, not quality.
- A source that needs a browser user-agent to render **cannot be a citation**: it verifies at
  staging and fails the merge's bare re-fetch. eCFR is like this; use the GPO's CFR XML at
  govinfo.gov instead.

## Where it stands (updated 2026-08-15)

- **1,497 companies scored** — S&P 500 + 400 + 600. Median quant coverage 0.94.
- **The judgement half is rolling out at 100/day.** `CompanyLabQual` runs daily at
  12:15 and does the whole chain: score → fold into scorecards → refresh the workbook.
  Roughly 800 companies still to go. Until a company has it, its score is out of ~50
  rather than 100 and it **cannot rank near the top** — the Rank sheet says so in row 1.
- **The weekly artifact is `data\exports\company_lab_latest.xlsx`**, 11 sheets. Rank,
  then Changes / Sectors / Findings directly behind it, on purpose.
- **Sectors are two-level**: the 11 GICS names on top, sub-industries beneath ranked
  within each sector. The gap inside a sector is often larger than the gap between
  sectors — Financials averages 35 while Financial Exchanges & Data is 61 and Regional
  Banks 27.
- 1,329 tests green (85 files, 0 skipped; recounted 2026-09-10 under B6). *(This line read "505 tests green"; the figure was stale.)* Scheduled tasks: `CompanyLabCrawl` (Sat 03:00),
  `CompanyLabSnapshot` (Sat 12:00), `CompanyLabQual` (daily 12:15),
  `CompanyLabWatchdog`.
- Dashboard on <http://127.0.0.1:8100> (start with `scripts\ui_autostart.ps1`).
- **Open issues are in `docs/known_issues.md`** — read it before trusting the LLM half.

## What the studies concluded

| | finding |
|---|---|
| **E01** | The entry rule does **not** improve timing. Signal entries +22.3% vs random entries +56.9% at 1y; hit rates 73.3% vs 74.3%. Found and fixed a real data defect on the way: the price store was built with `auto_adjust=False`, so splits read as crashes (26 of 500 symbols). |
| **E02** | 22 of the 25 biggest winners **could not have been seen** — their fundamentals were weak at the start of the move (CVNA scored FE 2/15 while nearly bankrupt, then rose 94x). Only NVDA, FIX and GNRC were caught. Top decile had a *worse* disaster rate than the universe. |
| **E03** | **The score is substantially a sector bet** — 95.6% of ranking power vanishes within sector. **The horizon was wrong all along** — IC +0.013 at 1y vs **+0.063 at 3y**, positive in 84.5% of months. Cyclical defect confirmed across 4,518 observations (top quintile −65.6 pts vs bottom over 3y). Bands change in 27.2% of months — unusable for multi-year holding. |
| **E05** | F1 and F3 both **FAIL** on the survivorship-free holdout. And the headline: the top decile's **median** 3-year excess over SPY is **−7.6%**, with only 45.3% beating SPY. The positive mean is a few huge winners. On this evidence **holding the index beats the typical top-decile pick**. |
| **E06** | **Following insiders does NOT beat the index** over 675 large caps. The entire edge was 2020 (+19.9%, 0.199 of the 0.210 sum of yearly means); drop it and the edge is −0.0% with a median of −3.5%. The falsification check fired — selling predicted too, and undifferentiated activity nearly as well as buying, which is an attention confound. |
| **E08** | The user's value-trap hypothesis **fails, and inverts**. Excluding declining-share names moved the top decile's median from −7.4% to −7.1%. "Harvesting" (margin up, share down, the FICO pattern) was the second *best* quadrant. Selection dominates: the subset where share is computable has a median of −24.0%. |
| **E09** | LSE `financial_reports` **loses to EDGAR** on depth (2017 vs ~2009), point-in-time (zero restatements retained) and traceability (no tag or accession). Exact on clean filers, 4-19% apart on JPM, opposite sign on JPM 2025 operating cash flow. |
| **E10** | **The first PASS.** Small-cap insider buying, excluding 2020: S&P 600 buyers +2.1% vs non-buyers −4.0%, an edge of **+6.1%** at 1y and +17.3% at 3y, and the falsification checks pass where they failed for large caps. **But the median is negative in every bucket** (−4.0% in the S&P 600) — the edge is a right tail, not a typical outcome. |

## 2026-08-11: survivorship fixed, and it changed the answer

The hole was **29.7%** — 716 companies were in the index at some point since 2016
against 503 today. Recovered prices for 213/213 and validated CIKs for 205/213; 161
cleared the panel's history bar, giving 644 symbols.

**Adding the dead companies nearly doubled the measured score's 1-year IC** (+0.0229 →
+0.0419, positive months 59% → 67%). The bias was *hiding* skill, not creating it: the
removed names were disproportionately low-scoring and did badly, so excluding them
deleted the observations where the score was right.

Also settled: the U-shaped decile curve **was** a survivorship artifact (bottom decile
+22.2% → +19.5%, no longer beats the top); Balance Sheet went −0.012 → **+0.001**, so it
is rehabilitated but still not a return predictor; and Entry got **worse** (−0.030 →
−0.046), the third independent strike against it. Band non-monotonicity survived the
fix, so that one is about the framework rather than the sample.

Full write-up: `journal/experiments/E04_survivorship_addendum.md`.

Artifacts: `E04_panel_nosurv.parquet` (63,185 rows, 644 symbols),
`E04_survivorship_report.json`.

## 2026-08-12: the weekly Excel workbook

**Open one file, every week: `data\exports\company_lab_latest.xlsx`.** The crawl refreshes
that stable name (and `scores_latest.csv`) beside the dated archive, so a shortcut or a
pinned Excel window keeps working instead of pointing at last week's file. The Saturday
`CompanyLabCrawl` task at 03:00 rebuilds it; `CompanyLabSnapshot` at 12:00 records the
week's scores so the next build can diff against them.

Eleven sheets. Three are new and they sit **directly behind Rank**, deliberately — a
workbook showing 500 confident-looking scores with no measured predictive power beside
them is misleading by omission:

| sheet | what it answers |
|---|---|
| **Changes** | what moved since the previous weekly snapshot, band moves sorted first, plus names that arrived or left. States the real gap in days, so a 2-day comparison is never dressed up as a week. |
| **Sectors** | mean/median score per sector with a bar chart and the spread stated. This exists because E03 R1 measured that the ranking is substantially a *sector* bet: on live data IT averages 62.7 and Real Estate 39.6, a **23-point spread**, so comparing a bank with a utility on the headline score partly compares their sectors. |
| **Findings** | what the studies did and did not establish, failures included, and the E05 verdicts as soon as they exist. Reads "NOT YET MEASURED" rather than staying silent, because omission reads as passing. |

Snapshots cannot be backfilled, so the Changes sheet only becomes a true week-over-week
view once two weekly snapshots exist; until then it compares against the oldest file on
disk and says how old it is.

## 2026-08-12: run everything unattended

Claude Code tokens are nearly out, so the research half is set up to keep moving without an
interactive agent. Everything below is **deterministic — no LLM, no network beyond the
caches already on D:**.

```powershell
# rebuild the panel (~50 min) then re-run E02/E03/E05/E08 and refresh the workbook
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_studies.ps1

# study code changed but the panel did not - skips the 50-minute crawl
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_studies.ps1 -SkipPanel

# just rebuild the CSV + workbook from scores already on disk (fast)
.venv\Scripts\python.exe -m clab.export.refresh
```

`clab/export/refresh.py` is separate from `runner.batch` on purpose: rebuilding the OUTPUT
must not require re-crawling the INPUT, because the Findings sheet reads the study results
and re-crawling 500 companies to pick up a changed journal file would be absurd. It exits
**3** when Excel holds `company_lab_latest.xlsx` open — the data is fresh, it just went to a
`_PENDING` sibling. `run_studies.ps1` treats 3 as a warning, not a failure.

**The LLM half is the only part that needs Ollama**, and it already runs on its own
schedule. `E07_llm_swap_preregistration.md` has the model bake-off, still to run.

## 2026-08-12: E08 — the user's value-trap objection

The user read the workbook and objected to the top of the ranking: FICO around 18th, plus
PayPal and a big defense name. Their diagnosis: **a deep discount is usually deep for a
reason**, and the reason is normally a decaying moat or gone growth. FICO's revenue rises
"only because they're raising prices, but their moat is being broken". NVDA is expensive
because the growth is real.

This is a **concrete mechanism for E05's central finding** — the top decile's median 3-year
excess over SPY is −7.6%. VA awards points for cheapness and nothing tests whether the
cheapness is deserved.

It is measurable with no new data and no LLM. `clab/research/e08_value_trap.py` computes,
per filing vintage, a company's `revenue_ttm` as a share of its sub-industry peers' summed
revenue, and the 3-year change in it. Crossed with the margin trend it separates the cases
the user named:

| margin | share | reading |
|---|---|---|
| up | **up** | winning — moat intact |
| **up** | **down** | **harvesting — the FICO case** |
| down | down | losing |
| down | up | buying share |

Pre-registered in `E08_value_trap_preregistration.md`. **H3 is the decisive test:** does
excluding declining-share names lift the top decile's *median* excess over SPY above zero?
Median, not mean — E05's whole lesson is that this distribution's mean is carried by a few
huge winners.

**Limit to state on every line:** the peer group is S&P 500 members only, so this is share
of large-cap *listed* peers, not true market share. A company losing real ground to a
private or foreign competitor reads as flat.

If H3 passes, a scoring change gets its own pre-registration — the candidate being a BQ
sub-test scored from *measured* share direction instead of the LLM's static moat judgement,
plus a value-trap veto that withholds a top band from a cheap company with deteriorating
share. Insider buying (E06) is a second candidate input to the same question, measured
separately so the two stay attributable.

## Immediate next step

**Measure F1/F3/F4 on the survivorship-free panel.** They are implemented and unit-tested
but have never been measured on data, and because F1 was designed on the biased panel this
is a genuine holdout:

```powershell
# one crawl, two panels: absolute and sector-relative
.venv\Scripts\python.exe -m clab.research.panel --include-removed --both --out journal\experiments\E05_panel.parquet
.venv\Scripts\python.exe -m clab.research.e05_measure
```

F1 passes only if within-sector IC rises above zero AND the 21.4-point sector spread in
mean score at least halves. F2 (mid-cycle earnings for cyclicals) is still unimplemented,
deliberately, so it stays attributable separately from F1.

**The sector variable had to be repaired first.** GICS sector comes from the Wikipedia
*current*-members table, so all 161 removed constituents had none — 15.4% of panel rows —
and they were being percentile-ranked inside one pseudo-sector mixing utilities with
software. Since F1 *is* a sector fix, that would have measured it against a fake variable.
`clab/research/sector_fill.py` maps SIC from the already-cached EDGAR submissions (no new
requests) and resolves 99.8% of them, but **SIC and GICS agree on only 78.4%** of the 481
companies where both exist — so E05 reports F1 under `gics_only`, `sic_filled` and
`sic_for_everyone` and states whether the verdict depends on the choice.
`panel.apply_sector_relative()` re-scores just the F1 half of FE, so varying the definition
costs no second crawl.

**F4 was declared and never wired.** `rubric.DEFAULT_HORIZON` / `HORIZON_LABEL` /
`HORIZON_NOTE` existed and were referenced by nothing, so the one fix whose criterion is
"implemented without altering a score" was not implemented. Now rendered by the dashboard
and the workbook Meta sheet, with tests asserting it. Its note still quotes the *biased*
panel's IC figures — replace them with the holdout numbers once E05 reports.

## Older plan, still valid below this line

**1. Survivorship first — it gates everything else.**
`D:\ohlcv_1m` holds 411 monthly files, 1992-2026, and **retains delisted tickers**;
`stock_xsect_lab/src/universe.py` already builds a point-in-time eligibility universe
from it and `src/delisting.py` handles the removals. Rebuilding the panel on that basis
would:

- include the companies that scored badly and died — the only real test of BS, and
  probably reverses the U-shaped decile curve;
- reach back through 2008 and 2000-02, the only windows where the entry rule's premise
  can be tested;
- give a genuine holdout for the weights v2 change, which is currently only validated
  in-sample.

Every result in E01/E02/E03 carries an asterisk until this exists.

**2. Four fixes, each needing its own pre-registration** (none applied):

| # | fix | why |
|---|---|---|
| 1 | Score margin/ROIC as percentiles **within sector** | E03 R1: biggest available improvement; makes the score about companies not sectors |
| 2 | **Mid-cycle earnings** (7-yr median margin) for cyclical SIC groups | E03 R5 + E02: TTM is the wrong denominator for a cyclical |
| 3 | **Band hysteresis** — two consecutive readings to change band | E03 R4: 27.2% monthly flip rate is unusable |
| 4 | Default the UI and expectations to **3 years** | E03 R3: the framework works at the horizon it was designed for |

**3. Then expand the universe** — next 500, then 1000+. The `xsect` tier is already
plumbed in `config.UNIVERSE_TIERS` and the scoring engine takes one CIK at a time, so
expansion is a config change plus a longer crawl, not a refactor. Cost scales linearly:
~2.2 s/company for the quant half, ~78 s/company for the LLM half.

## Commands

```powershell
cd C:\Users\<your-user>\company_lab

# refresh the live scores (~18 min for 500)
.venv\Scripts\python.exe -m clab.runner.batch --tier sp500 --no-resume

# LLM half for anything new (resumes from cache; needs Ollama up)
.venv\Scripts\python.exe -m clab.qual.scorer --tier sp500

# the studies
.venv\Scripts\python.exe -m clab.research.panel            # ~55 min, 500 symbols
.venv\Scripts\python.exe -m clab.research.battery          # E02 questions
.venv\Scripts\python.exe -m clab.research.questions        # E03 questions
.venv\Scripts\python.exe -m clab.research.entry_study --top 100

.venv\Scripts\python.exe -m clab.ui.app                    # dashboard
.venv\Scripts\python.exe -m pytest -q                      # 1,329 tests, offline
```

Ollama must be running for the LLM half, and it needs a kill-and-restart plus ~70
seconds before it answers:

```powershell
Get-Process ollama* | Stop-Process -Force
$env:OLLAMA_MODELS = "D:\ollama\models"
Start-Process "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" serve -WindowStyle Hidden
```

## Measured numbers — do not re-derive

| | |
|---|---|
| Quant crawl | 2.2 s/company, ~18 min for 500 |
| LLM half | 78 s/company, ~11 h for 500; cached resume 2.6 s/company |
| Panel build | 6.2 s/company, ~55 min for 500 |
| Ollama batch embed | 0.013 s/chunk vs 2.19 s on the legacy endpoint — **160x** |
| Parse failures | 6 in ~1,100 generations, all recovered offline via `--reparse` |

## Traps already paid for (all in CLAUDE.md)

Retired XBRL tags, `frame` being lossy, YTD de-cumulation, restatement dedupe, shell
registrants (XOM), filers with no gross-profit line, `NOT_APPLICABLE` needing evidence
not just a SIC code, `auto_adjust=False` splits, the qual cache keyed on rendered text
(fixed — now semantic), and Norton locking `.git/objects` (retry loop handles it).

## Status

Nothing is promoted. `promoted` is false in every flag file. The ranking has never been
validated out of sample, and the weights v2 change is confirmed only in-sample.
