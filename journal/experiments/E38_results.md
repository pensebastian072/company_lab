# E38 — the qwen-structured control. All five registered predictions were wrong.

Settled 2026-09-01 at the full registered n. Control lane **1,471 / 1,471**, 0 failed,
cache audited clean (0 unflushed, 0 unparseable, 0 silently incomplete). Registered at
`E38_control_lane_preregistration.md`; arms written by `e36_compare` and
`e38_generosity`.

## The answer

**The leniency E36 found is the MODEL, not the format.** That is the opposite of the
belief the experiment was registered on.

| | abstention (BQ null) | degenerate rationale | `bq_moat` Δ /15 |
|---|---:|---:|---:|
| qwen-v1 → **qwen-structured** (FORMAT) | 38.7% → 40.0% | 21.7% → 19.7% | **+0.1** |
| qwen-structured → **LFM2.5** (MODEL) | 40.0% → 0.0% | 19.7% → 0.1% | **+1.003** |
| qwen-v1 → LFM2.5 (what E36 saw) | 38.7% → 0.0% | 21.7% → 0.1% | +1.085 |

**Of the gap E36 measured, the format is 9% and the model is 92%.** Giving the incumbent
the candidate's schema and its 2,500-token budget moved essentially nothing: SG
abstention 22.9% → 22.8%, BQ abstention 38.7% → **40.0%** — slightly *worse* — and
+0.1 of 15 on `bq_moat`.

## The registered criteria

| # | prediction | measured | verdict |
|---|---|---|---|
| **P1** | qwen-structured null rate **below 15%** on E12's four watched dimensions | 87.6 / 74.3 / 79.6 / 61.8% | **REFUTED** |
| **P2** | `bq_moat` delta, structured − v1, **≥ +1.0** of 15 | **+0.1** | **REFUTED** |
| **P3** | LFM2.5 − qwen-structured **between 0 and +3**, i.e. smaller than E37's +4.34 | +1.003 of 15 | **see below** |
| **P4** | qwen-structured degenerate rate **below 5%, not zero** | **19.7%** | **REFUTED** |
| **P5** | slower than the v2 lane's 42.9 s/company | 40.3 s median | **REFUTED** (`E38_throughput.md`) |

**P1 did not merely miss — it moved the wrong way.** Under the schema the incumbent
abstained *more* on three of the four dimensions (network_effects 83.4 → 87.6,
data_advantages 73.6 → 79.6, manufacturing_complexity 72.8 → 74.3). The registered
reasoning was that "a required key cannot be omitted, and 2,500 tokens do not run out
mid-object". Both are true, and both are irrelevant: **a required key can be filled with
`score: null`.** The schema compels a key, never a judgement.

**P4 is the same mistake.** The prediction reasoned that typing `rationale` as a string
makes `rationale: null` unrepresentable. It does — and the incumbent wrote the pack's own
header line instead, keeping a 19.7% degenerate rate against a predicted <5%.

**P3 cannot be settled as written, and that is a defect in the registration, not a
result.** E37's +4.34 is a composite over a *folded* book, and this experiment forbids
folding the control lane ("no fold… there is no third `scores.parquet`"). The registration
asked for a statistic in units it had already ruled out producing. The nearest measurable
equivalent is `bq_moat`, where E37 localised the disagreement: **+1.003 of 15**, inside
the predicted 0-to-+3 band. So the band holds, but it is not a like-for-like test of
"smaller than +4.34" and must not be quoted as one. **The belief underneath P3 — "most,
not all, of the leniency is format" — is refuted outright: it is 92% model.**

## What this does and does not establish

It establishes that the E36 result survives its own confound, and belongs to the model.
Two things changed at once; only one of them mattered, and it was not the one the
incumbent could be given for free.

It establishes nothing about which lane is **right**. There is still no forward-return
grader in this repo, so a scorer that awards more points is only better if the points are
earned. E40 already found LFM2.5 cites text absent from the filing **9.7%** of the time
against qwen's 0.5% — a more *willing* scorer, not a proven better one. `promoted` stays
false.

**The cheap fix is dead.** "Put a schema on the incumbent" was the outcome that would have
avoided adopting a new model, and it buys 9% of the gap. Anyone wanting E36's behaviour
has to take the model, and with it E40's citation problem.

## MG is absent from both arms, correctly

Every structured MG payload carries `ceo: {}` — all 1,471 control and all 1,472 v2. This
is **not** a bug. E26 cut `MG_CEO_ATTRIBUTES` to two attributes, both sourced `"data"`,
so `schema_for("MG")` generates no LLM keys and `parse_mg` writes none. The stale side is
production, whose MG payloads still carry five pre-E26 dimensions. MG therefore has no
LLM-judged content to compare and is reported `n/a` throughout.

SG and BQ were checked against the current rubric before any of the above was read:
**4 payloads out of ~4,400 across all three lanes** differ in key-set, so the comparison
is not measuring a rubric change.
