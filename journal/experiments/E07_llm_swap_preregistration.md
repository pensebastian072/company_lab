# E07 — should the qual model be replaced? (pre-registration)

Written 2026-08-12 after the box went to **32 GB of system RAM**, before any candidate was
downloaded or benchmarked. The user's offer: "switch out the LLM we use for the scoring for
a better LLM… you can choose which one gets them all to work."

## The constraint the RAM upgrade does NOT lift

Measured on the box today:

| | |
|---|---|
| system RAM | **31.9 GB** total, 16.8 GB free |
| GPU | RTX 3050, **6.0 GB VRAM**, 5.0 GB free (883 MiB already in use) |
| current model | `qwen2.5:7b`, ~4.7 GB — fits in VRAM with ~0.3 GB headroom |

**The binding constraint on model quality is VRAM, not RAM.** A model that does not fit in
~5.0 GB spills layers to CPU, and generation then runs at CPU speed for the offloaded
fraction. 32 GB of RAM does not make a 14B model fast; it makes it *possible*.

What the extra RAM genuinely buys, and these matter:

1. **CPU offload without paging.** C: is the slow SATA spinner (see `box-disk-topology`), so
   before the upgrade a partially-offloaded model risked touching the pagefile, which is
   catastrophic rather than merely slow.
2. **A larger `num_ctx`.** The KV cache can live in RAM. `evidence.py` currently caps the
   pack at 160 chunks partly for context reasons; a bigger window could carry more 10-K
   evidence per call.
3. **Running the quant crawl and the qual batch concurrently** without thrashing.

## What a swap actually costs

`scorer.py:346` keys the qual cache on `sha1(pack | prompt | QUAL_MODEL)`. **Changing the
model invalidates all 500 companies.** At the measured 78 s/company that is ~11 h of GPU for
a model that stays in VRAM, and proportionally worse for one that offloads. This is exactly
the case the box rule covers: *probe before committing to a long run*. A 6.5 h run has
already been wasted here for want of five minutes of arithmetic.

So no model is adopted without the probe below passing first.

## The grading problem, stated honestly

**The qual half has never been validated against forward returns**, so "better" cannot be
claimed on returns — not for the current model and not for a replacement. Anything that
claims otherwise is inventing a result. What *is* measurable today, on a 15-company sample:

| # | metric | why it decides the question |
|---|---|---|
| M1 | **self-consistency** — same company, same pack, 3 runs, spread in each component score | A model that scores one company SG 4/20 then 11/20 is unusable regardless of how clever it sounds. This is the single most important number. |
| M2 | **mechanical validity** — parse failures, non-integer scores, out-of-range scores rejected | Current baseline: 6 parse failures in ~1,100 generations, all recovered offline. Out-of-range is *rejected, never clamped* (hard rule 4). |
| M3 | **evidence groundedness** — share of sub-tests tagged `evidence_unverified` | The scorer already requires quoted evidence to overlap the supplied pack. A model that quotes things not in the pack is hallucinating citations. |
| M4 | **`null` discipline** — share of scores returned as explicit `null` | `"score": null` is the "I don't know" channel. A model that never abstains is overconfident; one that always abstains is useless. |
| M5 | **throughput and VRAM** — s/company, GPU vs CPU layer split, peak VRAM | Sets the real cost of the 500-company re-score. |
| M6 | **agreement with `qwen2.5:7b`** — per-component correlation and mean shift | Not a quality measure. It measures whether scores are COMPARABLE across the switch: a large mean shift means every stored score and every band moves for reasons unrelated to any company. |

## Candidates

Chosen so the set spans the VRAM boundary rather than clustering on one side. Sizes are
expectations to be **measured** by the probe, not quoted facts.

| candidate | expected fit | why it is in the set |
|---|---|---|
| `qwen2.5:7b` | fits (~4.7 GB) | the incumbent, and the control arm |
| `qwen3:8b` | marginal (~5.2 GB) | a materially newer generation at nearly the same size — the most likely free win |
| `llama3.1:8b` | fits tight (~4.9 GB) | different family, so a failure mode specific to Qwen would show |
| `qwen2.5:14b-instruct-q4_K_M` | **offloads** (~9 GB) | tests whether 32 GB makes a genuinely larger model tolerable, and what it costs |

If a candidate cannot be pulled or will not load, that is recorded as a result, not
retried around.

## Pass criteria, fixed now

A candidate replaces `qwen2.5:7b` only if **all** of:

1. **M1 self-consistency is no worse** than the incumbent's, measured as the mean
   across-run spread per component. A model that is less consistent is rejected however
   good its prose.
2. **M2 mechanical validity is no worse** — parse-failure rate at or below the incumbent's.
3. **M3 `evidence_unverified` rate is no higher.**
4. **M5 total re-score cost is under 24 h**, or the candidate wins M1 decisively enough to
   justify more. Stated explicitly either way.

M4 and M6 are **reported, not gated** — there is no defensible threshold for them without
forward-return validation, and inventing one would be false precision.

## How it could make things worse

- A larger model that offloads could take the qual batch from ~11 h to 40 h+, which means
  the earnings-triggered re-run (`P5b`) becomes impractical and the weekly workbook goes
  stale between runs. Throughput is a correctness property here, not a nicety.
- Switching resets every stored qual score at once, so the Changes sheet will show a
  wholesale shift. It must carry the same warning the weights v2 reweighting now triggers,
  or a model swap will read as 500 companies changing quality on the same day.
- A newer model with better prose but the same 7B judgement may simply *sound* more
  authoritative while being no better grounded — which is worse than the incumbent, because
  the output is read by a human who cannot check 500 companies.

## Not in scope

- **`options_desk` has no LLM to swap.** Verified 2026-08-12: no reference to ollama, qwen
  or any model in the repo. That is deliberate — box hard rule 3, *no model or LLM on the
  trade hot path*. A "similar thing" there would mean **introducing** an LLM to a trading
  repo, which needs its own approval and would sit off the hot path behind a flag file, not
  a model swap.
- `fx_hermes_trader`'s Hermes supervisor is still a placeholder (`.env.example`: "NOT used
  in Milestone 1"), so there is nothing to replace there either.
- The three judgement components keep their current prompts. Changing model *and* prompt
  together would make the result unattributable — the same reason F1 and F2 are kept apart.

## Outputs

`journal/experiments/E07_results.json` / `.md`, and the probe harness at
`clab/qual/bakeoff.py`. Nothing is promoted. `promoted` stays false regardless of outcome,
and the qual half remains LLM-generated without human review.

---

# AMENDMENT 1 — adding `mistral:7b`, 2026-08-17

Written **after** three arms had reported and **before** `mistral:7b` was pulled or run.
Recording it as an amendment rather than editing the candidate list silently, because a
model added after seeing results is exactly what a pre-registration exists to make
visible.

## Why this is a principled addition and not cherry-picking

The original candidate set was chosen on 2026-08-12 to "span the VRAM boundary rather
than cluster on one side". Running it discovered that **the boundary is the whole
result**: on this 6 GB card, every candidate that does not fit is disqualified on
throughput alone.

| | fits 6 GB | 1500-company re-score | verdict |
|---|---|---:|---|
| `qwen2.5:7b` (4.7 GB) | yes | 17.0 h | incumbent, passes M5 |
| `llama3.1:8b` (4.9 GB, offloads at 8192 ctx) | marginal | 53.4 h | fails M5 |
| `qwen3:8b` (5.2 GB) | no | 154.0 h | fails M2 and M5 |
| `qwen2.5:14b-q4_K_M` (9.0 GB) | no | ~234 h | fails M5 |

So exactly ONE candidate was ever eligible, and it was the incumbent. A bake-off with a
single eligible arm has not tested the question the user asked. `mistral:7b` is ~4.1 GB
and is the main remaining instruction-tuned model that fits **with headroom** — it is
added because it satisfies the eligibility criterion the study itself discovered, not
because it might win.

`gemma4:latest` (9.6 GB) remains excluded on the same rule that admits Mistral: it does
not fit. Being already installed is not a reason.

## What changes, and what does not

- `n_trials` for any downstream deflation rises from 4 to **5**. Recorded here so it is
  not discovered later.
- **M1-M5 and the pass criteria are unchanged.** No threshold moves to accommodate the
  new arm.
- The evidence pack, prompts and repeat count are unchanged, so the arm is directly
  comparable to the three already run.

## The result this amendment expects to be measured against

Stated before pulling the model. The three completed arms show a **consistent trade**:

| | E12 watched abstention | M3 unverified evidence |
|---|---:|---:|
| `qwen2.5:7b` | 78.3% | **0.28%** |
| `llama3.1:8b` | 33.9% | **1.67%** |

Every model that abstains less also cites material that is **not in the pack** — 6x more
often for llama3.1. That is not a model knowing more; it is a model guessing more.

So the prediction is that `mistral:7b` will land on the same curve: lower abstention than
the incumbent, higher `evidence_unverified`, and **M3 will decide it**. If Mistral breaks
the curve — lower abstention AND M3 no worse than 0.28% — that is a genuine finding and
the first evidence that qwen2.5's abstention is a fixable model limitation rather than an
honest reading of what a 10-K contains.

Stated now so a null cannot later be called expected, and so that "Mistral wins" cannot
be claimed without M3 being checked first.
