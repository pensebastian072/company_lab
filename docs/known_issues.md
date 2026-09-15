# Known issues — measured, not yet fixed

Things that are wrong, quantified, and deliberately left alone for now with the reason
stated. Anything in here should either get fixed or get an explicit decision not to.

---

## 1. Every LLM prompt exceeds the context window by ~25%

**Measured 2026-08-14.** `QUAL_NUM_CTX` is **8,192**. Real BQ prompts, sampled over six
companies:

| company | pack chars | prompt tokens (approx) |
|---|---:|---:|
| SWKS | 40,928 | ~10,904 |
| AFL | 37,500 | ~10,047 |
| AIG | 39,105 | ~10,448 |
| ABT | 38,090 | ~10,195 |
| AMD | 37,342 | ~10,008 |
| APD | 36,056 | ~9,686 |

Every one overflows. The theoretical worst case is far worse: `MAX_CHUNKS_TOTAL = 160`
at `MAX_CHUNK_CHARS = 1600` is 256,000 characters, roughly **64,000 tokens against an
8,192-token window**.

`clab/qual/ollama.py` sets `num_ctx` explicitly precisely because the default silently
truncates, and the module docstring records that the truncation takes the **front** of
the prompt — which is where the instructions and the JSON schema live.

**Why it is not fixed yet.** It was first suspected as the cause of the 215 companies
whose BQ scored zero. It is not: an A/B on 12 below-floor companies, full pack against a
pack trimmed to fit the window, gave **7.8 vs 8.0 mean dimensions and 12/12 reaching the
6-dimension floor in both arms**. So overflow is real but its measured effect on output
quality is small, and the actual cause of those 215 was a degraded Ollama server.

**Why it is not free to fix.** The cache key is `sha1(evidence pack + prompt + model)`.
Changing the pack size changes every hash and invalidates all ~807 cached companies —
about 9 hours of GPU at the measured 40 s/company. That is the expensive gotcha already
recorded in `CLAUDE.md`, which cost ~2 hours once for a one-space formatting change.

**What a fix should look like.** A token budget inside `evidence.build_pack` targeting
~6,000 tokens of evidence, so the prompt lands near 7,000 against the 8,192 window, and
the schema moved to the END of the prompt so front-truncation cannot eat it. Worth
pairing with the E07 model bake-off, since a model with a larger window changes the
arithmetic — and both invalidate the cache, so they should be paid for once.

---

## 2. BQ abstains for a quarter of companies, by design

`rubric` A2 requires **≥ 6 of 11 moat dimensions** scored before BQ awards any of its 15
points. Across 808 cached payloads the distribution of scored dimensions was:

```
 1 dim:   9     5 dims: 112     9 dims: 126
 2 dims: 11     6 dims: 117    10 dims:  20
 3 dims: 41     7 dims: 105    11 dims:  86
 4 dims: 42     8 dims: 139
```

**215 companies (27%) fell below the floor** and scored BQ 0/15. The floor itself is
sound — scoring a moat on two dimensions would be worse than abstaining, and hard rule 2
says absent data is `NO_DATA`, never 0. Most of those 215 were an artifact of the
degraded-server window and are being re-generated.

**Watch after the re-generation.** If a stable population still lands below the floor,
the question is whether specific dimensions (`network_effects`, `economies_of_scale`)
are ones a 7B model simply cannot assess from a 10-K, in which case the honest fix is to
drop them from the denominator rather than to lower the floor. **Lowering the floor to
make more companies score would be exactly the threshold-tuning this project forbids.**

---

## 3. The daily qual batch depends on a healthy Ollama

Fixed defensively in `run_clab.ps1` (restart if `/api/tags` is silent, plus a generation
timing probe with a 45 s threshold), but the underlying instability is not understood:
the server passed its availability check and then ran 7-20x slow for hours. If it recurs
with the health check in place, capture `ollama ps` and `nvidia-smi` at the time — the
open question is whether another model is being loaded and evicting `qwen2.5:7b` into
CPU offload.
