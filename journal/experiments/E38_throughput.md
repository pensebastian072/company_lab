# E38 P5 — throughput. Registered prediction REFUTED.

Settled 2026-09-01, while the lane was still generating. P5 is a throughput criterion and
touches no scores, so settling it early costs P1–P4 nothing: they stay sealed until the
lane reaches 1,471.

## What was registered

> **P5** — Throughput, s/company, measured on the first 25. **Prediction: slower than the
> v2 lane's 42.9 s/company** — qwen2.5:7b is 4.7 GB against 1.7 GB on a 6 GB card, and
> 2,500 tokens is more decoding than the 700 v1 paid for. Recorded so the next run is
> sized on arithmetic rather than optimism.

## Measured

First 25 companies of the control run, 2026-08-30 12:19:47 → 12:41:11:

| | s/company |
|---|---|
| median | **40.3** |
| mean | 40.4 |
| min / max | 34.1 / 48.6 |
| v2 lane (comparator) | 42.9 |

**REFUTED.** qwen2.5:7b at 2,500 tokens is not slower than LFM2.5-2.6B at 2,500 tokens —
it is marginally **faster**, by ~2.6 s/company (~6%), despite being **2.8× the weights**.
The whole-run GPU median over 1,127 companies is 40.9 s, so the first-25 figure was not a
warm-cache artifact.

**What this does not establish.** It does not say qwen decodes faster per token. Time per
company is prompt + decode + the EDGAR fetch, and the two lanes emit different numbers of
tokens into the same schema — a model that abstains less writes more. E37 already showed
LFM2.5 fills abstentions the incumbent leaves empty, which costs decode time. So the
honest reading is that **the model-size intuition behind P5 was simply the wrong variable**,
and output length is the one that matters. Nothing here measures tokens/s; that would need
`eval_count` and `eval_duration` off the ollama responses, which the payloads do not keep.

## The CPU excursion, recorded so it never contaminates a timing claim

Six companies — GNL, PANW, AHR, DXC, ENS, FCF — were scored on **2026-09-01 08:38–09:41
with ollama on CPU**, after GPU discovery blew its 90 s per-backend watchdog during the
morning boot storm (see the repo `CLAUDE.md`). Their payloads are valid: same model, same
quantization, same schema, same token budget. Only the timings are from a different
machine state, so they are excluded from every figure above and reported separately:

| device state | n | median s/company |
|---|---|---|
| GPU | 1,127 | 40.9 |
| CPU | 6 | 661.6 |
| **ratio** | | **16.2×** |

16.2×, not the 13× quoted from the first four samples on the day.

## For sizing the next run

**~41 s/company on this box, GPU, at 2,500 tokens** — 1,471 companies ≈ **16.7 h of
generation**, before any crash. The lane log holds 1,133 timed entries against ~1,110
unique companies: restarts re-score whatever was mid-flight, so **the log is not a company
count**. Use the payload cache for that.
