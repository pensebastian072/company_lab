# E07 Amendment 2 — adding `LFM2.5-2.6B-Finance`, 2026-08-26

Written **before the arm is run** and after the model was pulled and smoke-tested.
Recorded as an amendment rather than an edit to the candidate list, for the same reason
Amendment 1 was: a model added after seeing results is exactly what a pre-registration
exists to make visible.

## Why it was added, stated plainly

**The user asked for it**, after I argued against it. That disagreement is the reason to
measure rather than continue arguing, and both halves of it belong on the record.

My objection, from the model card: this is an **autonomous-agent hobby experiment** —
QLoRA'd overnight on a GTX 1080, driven by a single prompt that asked for a model able to
*"determine actions on markets"* and *"aggressively make assumptions about future results
or possibilities."* That is close to the opposite of the disposition this pipeline needs,
which is strict schema compliance and a **calibrated `null`**. E07's own finding is that
every model which abstains less also fabricates more; a model tuned for market confidence
should sit at the bad end of that trade.

The counter-argument, which is also real: it is **1.56 GB against a ~5.0 GB budget**, so
unlike every candidate in Amendment 1 it fits with roughly 3.4 GB spare. E07's conclusion
was *"the boundary is the whole result"* — every eligible arm so far has been at the edge
of VRAM. This is the first candidate with genuine headroom, which is the one structural
reason to expect a surprise.

## Scope change: 100 companies, not 15

The registered harness runs 15. The user asked for 100, which is a **strict improvement in
power** for M1 (self-consistency) and for the E12 per-dimension abstention read, and it
does not change any criterion. Recorded because it makes this arm's numbers not directly
comparable to the 15-company arms on sampling error alone — the incumbent's figures are
re-read on the same 100 where a comparison is made.

## A parser fix landed FIRST, and it is not neutral to admit that

The very first smoke test returned:

```
The user wants me to return a specific JSON format...</think>{"ok": true}
```

An **unpaired closing `</think>`** — reasoning in plain prose, then a closing tag with no
opening tag anywhere. Neither existing strip branch fires on that shape, and
`extract_json` matches greedily from the first `{`, so any brace inside the reasoning
(the function's own docstring notes they are routine, and a scoring prompt invites them)
would swallow the answer and register as a **parse failure**.

`scorer.py` now strips a leading unpaired `</think>`, pinned by three tests. This is the
same act as commit `861db47` ("Strip reasoning blocks before JSON extraction, **before**
E07 runs on qwen3") and it follows the same rule: **applied to every model equally, so no
arm is rescued or penalised by its output format rather than its judgement.**

**Stated honestly: this fix helps the new candidate specifically**, because it is the only
model observed to emit that shape. Without it, M2 would have measured a format quirk and
called it bad judgement — which is not a result. The incumbent's M2 is unaffected (0.0%
before and after), so the comparison is not tilted, but the fix is not neutral in origin
and pretending otherwise would be the kind of quiet thumb on the scale this file exists to
prevent.

## Criteria — unchanged

The registered bar from E07 stands exactly as written. A candidate replaces `qwen2.5:7b`
only if **all** of:

1. **M1 self-consistency no worse** than the incumbent (mean across-run spread).
2. **M2 mechanical validity no worse** — parse-failure rate at or below the incumbent's.
3. **M3 `evidence_unverified` rate no higher.**
4. **M5 total re-score cost under 24 h**, or M1 won decisively enough to justify more.

M4 (`null` discipline) and M6 (agreement with the incumbent) are **reported, not gated**.
E12's per-dimension abstention is reported on top, and it is the number this arm exists to
move: the incumbent sits at **78.3%** mean null on the watched BQ dimensions against
llama3.1's **33.9%**.

## Prior, stated before the run

I expect it to **fail on M2 or M3**, most likely M3. Specifically:

* **M2 parse failures above the incumbent's 0.0%** even after the `</think>` fix — a 2.6B
  model holding an 11-key JSON schema is the thin end of what works, and qwen3:8b already
  failed here at 56.8%.
* **M4 null rate well below the incumbent's 42.7%**, because the tune rewards answering.
  If that arrives *with* a low M3, it is the best possible outcome and I am wrong in the
  interesting direction.
* **M3 unverified evidence above 0.28%**, which is where "aggressively make assumptions"
  should show up, and which is a hard criterion.
* **M5 comfortably under 24 h** — at 1.56 GB it should be the fastest arm ever run here,
  and throughput is the one thing I expect it to win outright.

If it clears M1–M4, the honest conclusion is that a small domain fine-tune beat a general
model twice its size, my read of the model card was wrong, and it earns a full 1,501
company re-score. **`promoted` stays false regardless**, and the judged half remains
LLM-generated with no human review.

## Outputs

`journal/experiments/E07_raw/hf_co_mradermacher_LFM2_5_2_6B_Finance_GGUF_Q4_K_M.summary.json`
and a written verdict beside this file.
