# Codex handoff — company_lab, 2026-08-12

Written by the Claude Code session that built everything below. Claude Code tokens ran out
and its shell tool was blocked by an upstream outage at the end, so **some work is on disk
but was never executed**. That is flagged explicitly — do not assume anything here is
verified unless it says so.

**Read `CLAUDE.md` first.** It holds the hard rules and the hard-won gotchas. This file is
only "where things stand and what to do next".

---

## 0. Ground rules for this repo, in one place

1. **Advisory / SHADOW only.** `promoted` is `false` in every flag file and no code path
   sets it true. This ranking has never been validated out of sample.
2. **Absent data is `NO_DATA`, never `0`.** A company with no interest-expense tag is not a
   company with terrible coverage.
3. **Below 80% coverage a company gets NO band** — `INSUFFICIENT_DATA`, not a flattering
   label.
4. **Sub-test scores are integers.** An out-of-range LLM score is *rejected, never clamped*.
5. **The dashboard binds `127.0.0.1` only.** Port 8100. A test asserts `0.0.0.0` never
   appears in `clab/ui/app.py`.
6. **Bulk data lives on D:** — C: is the slow SATA spinner.
7. **No order placement, no broker code, ever, in this repo.**
8. **Probe before a long run.** A crawl over 50 companies refuses to start without a probe
   report younger than 7 days (`--i-know` overrides).

Environment specifics that will bite you:

```powershell
cd C:\Users\<your-user>\company_lab
$env:PYTHONPATH = "C:\Users\<your-user>\company_lab"
.venv\Scripts\python.exe -m pytest -q          # 1,329 tests, offline
```

- Bare `python` is the Store stub (exit 49). Always `.venv\Scripts\python.exe`.
- git has no global identity:
  `git -c user.email='YOUR_GITHUB_NOREPLY_EMAIL' -c user.name='YOUR_GITHUB_USERNAME' commit -F <file>`
- Norton transiently locks `.git/objects` → **retry `git add` in a loop** (it usually
  succeeds on try 2-4).
- `git commit -m` with escaped quotes fails here (exit 129). **Always use `-F messagefile`.**
- Write message files with
  `[IO.File]::WriteAllText($p,$t,(New-Object Text.UTF8Encoding($false)))` —
  `Out-File -Encoding utf8` adds a BOM that ends up in the commit subject forever.
- Keep `.ps1` files **ASCII only** (PowerShell 5.1 mangles the rest).

---

## 1. State of the build

Live: 500 S&P 500 companies scored, dashboard on `127.0.0.1:8100`, 11-sheet workbook, three
scheduled tasks (`CompanyLabCrawl` Sat 03:00, `CompanyLabSnapshot` Sat 12:00,
`CompanyLabWatchdog`). 1,329 tests green (85 files, 0 skipped; recounted 2026-09-10 under B6). Last commit `59b048c`.

> The figure here read "329 tests green". Recounted 2026-09-10: the suite collects and
> passes **1,329** across 85 files with nothing skipped. The repo's own pytest cache holds
> **1,395** node ids — 66 of them stale identifiers for tests that no longer exist — so a
> count taken from `.pytest_cache/v/cache/nodeids` overstates the suite by 5%. Count from a
> run, never from the cache.

**The primary weekly artifact is `data\exports\company_lab_latest.xlsx`** — a stable name
refreshed by every crawl beside a dated archive. Sheets, in reading order: Rank, Changes,
Sectors, Findings, Entry, Components, Subtests, Thesis, Valuation, Stress, Meta. Changes /
Sectors / Findings sit directly behind Rank deliberately: 500 confident-looking scores with
no measured predictive power beside them is misleading by omission.

### What the research actually concluded — read this before "improving" anything

| study | finding |
|---|---|
| E01 | Entry timing (20/72 EMAs + own-history P/E percentile) **failed three independent times**. |
| E02 | 22 of the 25 biggest winners **could not have been seen** from fundamentals at the start of the move. |
| E03 | The score is **substantially a sector bet** (95.6% of ranking power vanished within sector). Horizon should be **3 years, not 1**. Cyclical scores are **inverted** (TTM earnings peak as the cycle turns). |
| E04 | Survivorship bias was **hiding real skill** — adding back removed constituents nearly doubled the IC. |
| **E05** | **F1 FAIL, F3 FAIL.** And the headline: the top decile's **median** 3-year excess over SPY is **−7.6%**, with only **45.3%** of picks beating SPY. The positive mean (+11.9%) is a few huge winners. **On this evidence, holding the index beats the typical top-decile pick.** |

E05 detail is in `journal/experiments/E05_results.md` and `E05_addendum.md`. The addendum
also records that **no value of `BAND_CONFIRM_READINGS` satisfies all three F3 criteria at
once** — the churn bar and the IC-stability bar contradict each other. F3 ships at
`confirm=2` on usability grounds and is recorded as a FAIL, not reinterpreted into a pass.

**Do not re-tune a threshold to convert a FAIL into a PASS.** Pre-register the change
first. The user's own stated rule: sign-flipping a discovered effect to harvest it is
p-hacking.

---

## 2. UNVERIFIED work on disk — start here

Three files were written and **never executed** because the shell tool was blocked:

| file | status |
|---|---|
| `clab/research/e08_value_trap.py` | never run, never imported |
| `scripts/run_studies.ps1` | never run |
| `clab/export/refresh.py` | never run, never imported |

They are also **uncommitted**. First job:

```powershell
cd C:\Users\<your-user>\company_lab
$env:PYTHONPATH = "C:\Users\<your-user>\company_lab"

.venv\Scripts\python.exe -c "from clab.research import e08_value_trap; from clab.export import refresh; print('imports ok')"
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m clab.research.e08_value_trap
.venv\Scripts\python.exe -m clab.export.refresh
```

Expect to shake out a bug or two. Known risk points in `e08_value_trap.py`:

- `build()` does a self-merge on `(ticker, ym)` to get the 36-month lag. It uses
  `drop_duplicates(["ticker","ym"])`; if the panel ever has two rows for one ticker-month
  the lag silently picks one. Assert one row per `(ticker, date)` if it looks wrong.
- `p.apply(_quadrant, axis=1)` over 67,889 rows is the slowest part. If it drags, vectorise
  it — the logic is two sign tests.
- `h4_independent_of_score()` residualises per date and will divide by a zero-variance rank
  on dates with very few names; it guards with `len(g) < 10` but check the output for NaNs.
- `render()` prints raw `mean_ic` floats for H4 without percent formatting. Cosmetic.

`clab/export/refresh.py` exits **3** when Excel holds `company_lab_latest.xlsx` open — the
data is fresh, it just went to a `_PENDING` sibling. That is a warning, not a failure, and
`run_studies.ps1` already treats it as one. **This happens most weeks; do not "fix" it by
deleting the user's open file.**

Then commit:

```powershell
$m = "journal\runs\_msg.txt"
[IO.File]::WriteAllText((Join-Path $PWD $m), "E08 value-trap study + unattended study runner`n", (New-Object Text.UTF8Encoding($false)))
for ($i=1; $i -le 8; $i++) { git add -A clab tests scripts journal HANDOFF.md CODEX_HANDOFF.md 2>$null; if ($?) { break }; Start-Sleep -Milliseconds 1500 }
git -c user.email='YOUR_GITHUB_NOREPLY_EMAIL' -c user.name='YOUR_GITHUB_USERNAME' commit -F $m
```

---

## 3. E08 — the user's own hypothesis, and the most promising lead

**This came from the user reading the workbook, and it is the best explanation anyone has
for E05's central failure.** Preserve their framing; it is the reason the study exists.

Their objection: FICO ranked ~18th, alongside PayPal and a large defense name. Their
diagnosis, in their words — a deep discount is usually deep **for a reason**, and the reason
is normally a **decaying moat or gone growth**. FICO's revenue rises "only because they're
raising prices, but their moat is being broken right now". PayPal is cheap because "the use
case for it as a company for growth isn't really there". NVDA is expensive because the
growth is real and the moat holds.

Mechanism: **VA awards points for cheapness and nothing tests whether the cheapness is
deserved.** That is a value trap, and it would produce exactly E05's result.

The measurable is **moat DIRECTION, not level** — a static moat score cannot capture this:

- `share` = a company's `revenue_ttm` ÷ summed `revenue_ttm` of its sub-industry peers, per
  filing vintage, where the sub-industry has ≥5 peers.
- `d_share_3y` = the 36-month change, matched on the **calendar**, not on row position.

Crossed with the margin trend it separates the user's cases:

| margin | share | reading |
|---|---|---|
| up | **up** | winning — moat intact (NVDA) |
| **up** | **down** | **harvesting — the FICO case** |
| down | down | losing |
| down | up | buying share |

Pre-registered in `journal/experiments/E08_value_trap_preregistration.md`. **H3 is the
decisive test:** does excluding declining-share names lift the top decile's **median**
excess over SPY above zero? Median, not mean — E05's whole lesson is that this
distribution's mean is carried by a few enormous winners.

**Limit that must appear on every line of any result:** the peer group is **S&P 500 members
only**, so this is share of large-cap *listed* peers, not true market share. Private,
foreign and small-cap competitors are invisible; a company losing real ground to a private
entrant reads as flat here.

**If H3 passes**, the follow-up needs its **own** pre-registration. The candidates:
a BQ sub-test scored from *measured* share direction instead of the LLM's static moat
judgement, plus a **value-trap veto** withholding a top band from a cheap company with
deteriorating share. Do not wire either without pre-registering.

**If H3 fails**, say so as plainly as a success. The value-trap story then is not the
explanation, and that is a real result.

---

## 4. Ordered task list

### P1 — verify and commit section 2. Nothing else matters until the tests pass.

### P2 — run E08 and report it honestly
Then refresh the workbook so the Findings sheet picks it up:
`.venv\Scripts\python.exe -m clab.export.refresh`. Add E08's verdict to
`_sheet_findings()` in `clab/export/xlsx_export.py` the same way E05's rows are built.

### P3 — E06, insider buying (pre-registered, data source ready)
`journal/experiments/E06_insider_signal_preregistration.md`. Second independent input to the
same moat question, so measure it **separately** from E08 or neither is attributable.

Three disciplines already locked, each of which is a way to fake an edge:
1. Signal date is **`filing_date`, never `transaction_date`** — the observed gap reaches 20
   months.
2. **Congressional rows excluded** — the dataset mixes Form 4 with senate/house
   disclosures and the `trade_type` query param is *silently ignored*, so filter
   client-side (`lse.insider_trades(corporate_only=True)` already does).
3. **Mechanical vs discretionary separated** — all 782 AAPL corporate rows are `M-Exempt`
   or `F-InKind`. Only `P-Purchase`/`S-Sale` are decisions.

Primary statistic is **excess over SPY**. S6 (selling) is tested to confirm it does *not*
predict — **if selling looks predictive, the construction is wrong.**

LSE client is `clab/sources/lse.py`; key in `secrets/lse.json` (gitignored, never log it,
and it was pasted in chat so it should be rotated). Measured limits in
`docs/lse_data_source.md`: closes are **not dividend-adjusted** (never mix into the yfinance
series), **volume is unusable** (4.4% of consolidated for NVDA), and coverage is **current
listings only** — so E06 reintroduces the survivorship bias E04 removed. State that on
every line.

### P4 — E07, the LLM bake-off (pre-registered, not started)
`journal/experiments/E07_llm_swap_preregistration.md`. The user upgraded the box to **32 GB
RAM** and offered to swap the qual model.

**The binding constraint is VRAM, not RAM:** RTX 3050, **6 GB total, ~5.0 GB free**;
`qwen2.5:7b` already uses ~4.7 GB. A 14B q4 (~9 GB) runs its overflow at CPU speed. What
the RAM does buy: CPU offload without touching the pagefile on the slow C: spinner, a bigger
`num_ctx`, and running the crawl and qual batch together.

**A swap re-scores all 500 companies** — `scorer.py` keys the cache on
`sha1(pack | prompt | QUAL_MODEL)`. ~11 h for a model that fits, far worse for one that
offloads. Hence: probe on 15 companies first. Build `clab/qual/bakeoff.py`.

Graded on **self-consistency first** (same company, 3 runs, score spread — a model that
scores one company SG 4/20 then 11/20 is unusable however good its prose), then parse
validity, `evidence_unverified` rate, throughput. **Cannot be graded on returns** — the qual
half has never been validated against them.

Ollama needs a kill-and-restart plus ~70 s before it answers:

```powershell
Get-Process ollama* | Stop-Process -Force
$env:OLLAMA_MODELS = "D:\ollama\models"
Start-Process "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" serve -WindowStyle Hidden
```

### P5 — F2, mid-cycle earnings for cyclicals
Deliberately unimplemented so F1 and F2 stay attributable. Spec in
`E05_four_fixes_preregistration.md`: 7-year median margin and 7-year revenue CAGR instead of
TTM, for SIC 3600-3699, 3570-3579, 1300-1399, 2911, 3300-3399, 3711. Watch NVDA and AVGO —
if their scores fall materially while fundamentals genuinely improved, the fix over-smooths.

### P6 — LSE tracks B and C
B: `financial_reports` vs EDGAR on AAPL/JPM/XOM/NKE/COST (the five that broke naive
parsing). EDGAR is as-first-filed with the exact tag per number, so the bar is high; the
likely genuine gap is **non-US filers**, which have no companyfacts at all.

C: options flow. **Load the `paper-options-desk` and `paper-trading-guardrails` skills before
touching `options_desk`** — it has its own hard rules and a **paid CBOE archive that must not
be re-paid**. LSE options history is only 7 months against LiveVol's 18 years, so it is a
candidate *current* source, not a historical one. The number that matters is **half-spread
agreement** on overlapping dates.

### P7 — universe expansion to the next 500 / 1000
`config.UNIVERSE_TIERS` already has the `xsect` tier and the engine takes one CIK at a time,
so it is a config change plus a longer crawl. ~2.2 s/company quant, ~78 s/company LLM.
**Do not expand before P2/P3 land** — expanding a ranking that loses to SPY just produces
more of it.

---

## 5. Measured numbers — do not re-derive

| | |
|---|---|
| Quant crawl | 2.2 s/company, ~18 min for 500 |
| LLM half | 78 s/company, ~11 h for 500; cached resume 2.6 s/company |
| Panel build | ~50 min for 705 symbols (survivorship-free), 67,889 rows |
| Ollama batch embed | 0.013 s/chunk vs 2.19 s on the legacy endpoint — **160x** |
| Workbook build | ~50 s for 500 companies with all sheets |

---

## 6. Traps that have already cost time

All in `CLAUDE.md` in full. The ones most likely to bite a new session:

- **A graceful fallback hides a wiring bug.** `fe_sector_scored` was computed and never
  copied onto the panel row; every sector distribution filtered to zero peers, the "too few
  peers → absolute basis" fallback swallowed all 67,889 rows, and the run printed
  `fe_basis: {'absolute': 67889}` and **exited 0**. F1 was almost recorded as having no
  effect when it had never run. Both entry points now raise. **Thin data is a fallback; an
  absent column is a bug.**
- **A rubric constant nobody renders is not an implemented fix.** F4 was declared
  (`DEFAULT_HORIZON`, `HORIZON_LABEL`, `HORIZON_NOTE`) and referenced nowhere; F3's
  `smooth_bands` was called only by research code while the live scorer shipped the raw
  band. Both are wired now, with tests asserting they are actually rendered.
- **A retired XBRL tag must not supply the recent series** (NVDA revenue ended 2020, giving
  a "TTM revenue" of $10.9B against ~$200B).
- **`frame` is lossy** — classify by duration, never by `frame`.
- **`company_tickers.json` can point at a shell registrant** (XOM).
- **`auto_adjust=False` makes splits read as crashes** — bit 26 of 500 symbols.
- **The qual cache keys on the rendered pack**, so a cosmetic formatting edit invalidates all
  500 companies. Cost ~2 h of GPU once.
- **`ws.append([])` moves openpyxl's write cursor but not `max_row`** — read `max_row` back
  *after* appending a header, never predict it.

---

## 7. What to tell the user

They care about one question: **should this be followed, or should they just hold the
index?** Today's honest answer is **hold the index** — top-decile median 3-year excess
−7.6%, 45.3% beating SPY. E08 is the most promising route to changing that answer, and it is
their own hypothesis.

Report failures as failures. Give medians beside means — a mean alone would have made E05
look like a +11.9% edge. Nothing is promoted; `promoted` stays false.
