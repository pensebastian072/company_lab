# company_lab — build plan and resume pointer

Built 2026-08-08. This file is the authority on what is done and what is next.

## Done

**P0 — skeleton and the honesty gate.** `config.py` (path/port owner, C:/D: split),
`net.py` (one atomic write, TLS trust for the intercepting proxy, rate limiter,
retry with transient/permanent classification), `sources/base.py` (Source ABC that
never raises), `scoring/types.py` (integer-only sub-tests, NO_DATA distinct from a
scored zero), `scoring/rubric.py` (every threshold and every A1-A10 resolution),
`scoring/composite.py` (strict vs normalized, the 80% coverage band gate).

**P1 — data spine.** `edgar_tickers` (10,398-ticker CIK map), `edgar_facts`
(companyfacts + submissions + reorganization following), `universe` (Wikipedia
S&P 500 by header signature, with an immutable point-in-time membership snapshot),
`normalize` (restatement dedupe, duration classification, YTD de-cumulation, TTM),
`tags` (fallback chains that merge across a switched taxonomy), `metrics` (the full
bundle), `profile` (sector profiles, evidence-driven NOT_APPLICABLE).
Validated against AAPL, MSFT, NVDA, JPM, XOM, COST, UNH, LIN, NKE, BRK-B — every
headline number reconciles with reality.

**P1 exit gate — probe.** `runner/probe.py`. Measured 2026-08-08: **3.6 s/company,
~30 min for 500, ~0.1 GB on D:**. A crawl over 50 companies is refused without a
probe report younger than 7 days.

**P2 — first useful output.** All eight components (`fe bs stress va reverse_dcf
er en` measured; `sg bq mg` reading the LLM cache), `runner/engine.py`,
`runner/batch.py` (10 at a time, manifest-checkpointed, resumable, per-symbol
isolation, market-cap ordering), CSV + 11-sheet XLSX export, the dashboard on
`127.0.0.1:8100` with a virtualized 500-row table and per-company scorecard pages,
`snapshot.py`, `watchdog.py`, the scheduler triplet, login autostart, and 154
offline tests.

Full S&P 500 quant crawl run 2026-08-08.

## Next, in order

**P4 — `clab/qual/` (the LLM half).** The single biggest gap: without it SG/BQ/MG
are `NO_DATA` for every company, so no company can earn a full-framework band.
Constraints already decided:
- `qual/ollama.py` — port `research_rag/rag/common.py::_post/chat`; `num_ctx` set
  explicitly (the default silently truncates the front of a long prompt, which
  here would drop the 10-K evidence); `keep_alive: "10m"` so the model loads once
  per batch, worth ~20-30 s per company; an advisory GPU lease file with a 30-min
  TTL, because the 6 GB card is shared and a killed process must not deadlock it.
- `qual/evidence.py` — a bounded, cited pack: identity, the already-computed quant
  fact sheet, retrieved 10-K Item 1 / 1A / 7 chunks (reuse `research_rag`'s
  `chunk_text` + `nomic-embed-text`, but into **its own** sqlite store — mixing
  500 10-Ks into the papers corpus would wreck its retrieval), recent headlines,
  estimate context, capital-allocation history.
- `qual/prompts.py` — three prompts (SG, BQ, MG), not one: a 7B model degrades
  badly across 6+11+2 sub-tests at once. Closed-vocabulary JSON, integer-only,
  `"score": null` as the explicit "I don't know" channel.
- `qual/scorer.py` — `re.search(r"\{.*\}", s, re.S)` to survive prose and code
  fences; reject non-integer and out-of-range scores rather than clamping; require
  the quoted evidence to overlap the supplied pack or tag `evidence_unverified`;
  cache on `sha1(evidence + prompt template + model name)` so an unchanged company
  is never re-scored and a prompt edit invalidates automatically.
- **Measure real per-company GPU time on 10 symbols before scheduling anything.**
  The projection is 90-200 s/company, i.e. overnight runs across several days —
  roughly 20x the entire quant crawl. Do not plan around "one run does everything".

**P5 — thesis and tri-state status.** `thesis/schema.py`, `thesis/status.py`. The
falsifiers must be machine-checkable `(metric, direction, threshold,
window_quarters)` tuples validated against a whitelist, not prose alone.
**Price is not an input to the status** — enforce it by the function signature and
by a named test that doubles and halves every price field and asserts the status is
byte-identical. Hysteresis: a status only improves after two consecutive
computations agree; degradation is immediate.

**P5b — earnings trigger.** `runner/earnings_watch.py` over the EDGAR daily index.
Verified: `form.YYYYMMDD.idx` is one 1.19 MB request covering every filer on the
planet (418 10-K/10-Q rows in a single day) versus 500 per-symbol polls, and
past-day index files are immutable so re-scans are free.

**P6 — validation, deliberately deferred.** A `research_ledger` grader for
forward-return IC by score decile, on the `as_first_filed` restatement view, once
roughly 50 weekly snapshots exist (~12 months). Grading on restated numbers is
look-ahead bias and would invalidate the exercise. Until then: ADVISORY/SHADOW,
`promoted: false`, and the banner says so on every page.

## Follow-ups created by the first live run

**Key the qual cache on semantic content, not the rendered pack string.** Today
`cache_key = sha1(rendered pack + prompt template + model)`, so a cosmetic edit to
`evidence.py`'s string assembly invalidates all 500 companies. That happened on
2026-08-08: adding an empty `{where}` interpolation to the excerpt header changed
every pack by one space and forced a full regeneration, costing about two hours of
GPU. Fix: hash a canonical structure - the fact-sheet metric values, the ordered
list of chosen chunk texts, the component, the prompt template and the model - so
that headers, whitespace and wording changes are free while a genuine change to the
evidence still invalidates. Do this between runs, never during one.

**Prompt-template changes have the same blast radius** and that is correct: an
edited rubric SHOULD re-score everything. Just know it costs a full night.

**Consider fetching Exhibit 13 for incorporate-by-reference filers.** The
whole-document fallback keeps Morgan Stanley and Citigroup from reaching the model
empty-handed, but their actual business narrative lives in a separate exhibit the
submissions feed's `primaryDocument` does not point at. Walking the filing index
for the largest text exhibit would give those filers real Item 1 prose.

## Known limitations worth writing down

- Coverage is ~50% for every company until the LLM half runs, so every
  full-framework band reads `INSUFFICIENT_DATA` by design. The measured /50 and
  `quant_band` carry the system meanwhile.
- Own-history valuation percentiles need accumulated snapshots; peer medians need
  >= 5 scored companies in a sub-industry. Both abstain rather than guess.
- Energy and financial filers legitimately score on fewer applicable points. The
  scorecard states how many.
- ROIC uses the current debt and cash balance against an averaged equity balance;
  a fully averaged invested-capital series would be marginally better and is not
  worth the extra instant-series bookkeeping today. Documented in
  `metrics.py::build_metrics`.
- The `xsect` down-cap tier is plumbed (config + universe loader) but never run.
