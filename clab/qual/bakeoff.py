"""E07 - the model bake-off harness. Pre-registered; this file only executes the plan.

Read `journal/experiments/E07_llm_swap_preregistration.md` first. The candidates, the
metrics M1-M6 and the pass criteria are fixed there and are NOT restated or adjusted here.

Two properties make this safe to run against a live cache:

  * **It never writes to `config.QUAL_DIR`.** A candidate's scores go to a separate
    directory keyed by model. Poisoning the production cache with another model's
    judgement would be unrecoverable without a full re-score.
  * **The evidence pack is built ONCE per company and reused across every candidate and
    every repeat.** That is what makes M1 a measure of the model rather than of retrieval
    noise, and it is also why the pack must not be rebuilt between arms.

E12 adds one required output on top of the registered M4: the **per-dimension abstention
rate** for each candidate. `journal/experiments/E12_bq_denominator_preregistration.md`
turns on it - if a better model abstains less on `network_effects`,
`manufacturing_complexity`, `data_advantages` and `economies_of_scale`, then a quarter of
the universe falls under the 6-of-11 BQ floor because of the MODEL, and no rubric change
is warranted at all.

    python -m clab.qual.bakeoff --dry-run          # what it would do, no GPU
    python -m clab.qual.bakeoff --models qwen3:8b  # one candidate
    python -m clab.qual.bakeoff                    # the full registered set
"""
from __future__ import annotations

import argparse
import json
import statistics
import time

from .. import config
from ..net import log_stamp, utc_now_iso
from ..runner import engine
from ..scoring import rubric
from . import evidence as ev_mod
from . import ollama, prompts
from .scorer import (load_universe_multi, parse_bq, parse_mg, parse_sg)

#: registered in E07. The incumbent is the control arm and must stay first.
CANDIDATES = (
    "qwen2.5:7b",
    "qwen3:8b",
    "llama3.1:8b",
    "qwen2.5:14b-instruct-q4_K_M",
    # AMENDMENT 1, 2026-08-17: added after three arms reported, and recorded in the
    # pre-registration rather than slipped into this tuple. Running the original set
    # discovered that fitting in 6 GB IS the result - only the incumbent was ever
    # eligible on throughput - and mistral:7b (~4.1 GB) is the main remaining
    # instruction-tuned model that fits with headroom. Admitted because it meets the
    # eligibility rule the study itself found, not because it might win. gemma4 stays
    # excluded by that same rule: 9.6 GB does not fit.
    "mistral:7b",
)
SAMPLE_N = 15          # registered
REPEATS = 3            # registered: M1 needs 3 runs of the same pack

#: Generous, because a candidate that offloads to CPU is SLOW rather than broken and
#: must not be failed by the harness's patience. Measured 2026-08-16: the incumbent runs
#: 15.8 s/generation, llama3.1:8b 61 s, the 14B 187 s, and qwen3:8b exceeded 300 s
#: because it is a reasoning model and emits a long think block before answering.
GEN_TIMEOUT = 900.0
#: consecutive failures before an arm is abandoned rather than timing out 135 times
ABANDON_AFTER = 3
#: wall-clock budget per candidate, so one slow arm cannot eat the whole night
MAX_MINUTES_PER_MODEL = 150.0

#: the four dimensions E12 found abstained on more than half the time
E12_WATCH = ("network_effects", "manufacturing_complexity",
             "data_advantages", "economies_of_scale")

BAKEOFF_DIR = config.JOURNAL_DIR / "experiments" / "E07_raw"


def log(msg: str) -> None:
    print(f"[{log_stamp()}] {msg}", flush=True)


def _parse(component: str, raw: str, pack_body: str) -> dict:
    if component == "SG":
        return parse_sg(raw, pack_body)
    if component == "BQ":
        return parse_bq(raw, pack_body)
    return parse_mg(raw, pack_body)


def _scores_of(component: str, parsed: dict) -> dict:
    """{key: score-or-None} for whichever shape this component parses into."""
    if component == "SG":
        return {k: v.get("score") for k, v in (parsed.get("scores") or {}).items()}
    if component == "BQ":
        return {k: v.get("score") for k, v in (parsed.get("dimensions") or {}).items()}
    return {k: v.get("score") for k, v in (parsed.get("ceo") or {}).items()}


def _unverified(parsed: dict) -> tuple[int, int]:
    """(flagged, total) evidence quotes that did not overlap the pack."""
    flagged = total = 0
    for bucket in ("scores", "dimensions", "ceo"):
        for v in (parsed.get(bucket) or {}).values():
            if "evidence_unverified" in v:
                total += 1
                flagged += bool(v.get("evidence_unverified"))
    if "evidence_unverified" in parsed:
        total += 1
        flagged += bool(parsed.get("evidence_unverified"))
    return flagged, total


def _norm_model(name: str) -> str:
    """`qwen2.5` and `qwen2.5:latest` are the same model; `qwen2.5:7b` is not."""
    name = (name or "").strip()
    return name if ":" in name else f"{name}:latest"


def installed_models() -> list[str]:
    """Model names ollama already has locally. Never pulls anything.

    A candidate that is not here needs a multi-GB download, which is the user's call and
    not something a research harness should start on its own.
    """
    try:
        import urllib.request
        url = f"{config.OLLAMA_URL.rstrip('/')}/api/tags"
        with urllib.request.urlopen(url, timeout=10) as fh:
            payload = json.loads(fh.read().decode("utf-8"))
        return sorted(m.get("name", "") for m in (payload.get("models") or []))
    except Exception:                                  # noqa: BLE001
        return []


def sample(tier: str = "all", n: int = SAMPLE_N) -> list[dict]:
    """A fixed, reproducible sample: every Nth company by market cap.

    Deliberately spread across the size range rather than the top N, because the top N
    are mega-caps whose 10-Ks are the easiest text in the universe and would flatter
    every candidate equally.
    """
    from ..runner import batch as batch_mod

    rows = batch_mod.order_universe(load_universe_multi(tier), "marketcap")
    if not rows:
        return []
    step = max(1, len(rows) // n)
    return rows[::step][:n]


def checkpointed_models() -> dict:
    """Summaries already on disk from an earlier, interrupted run."""
    out = {}
    if not BAKEOFF_DIR.exists():
        return out
    for p in BAKEOFF_DIR.glob("*.summary.json"):
        try:
            out[p.name[:-len(".summary.json")]] = json.loads(
                p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
    return out


def run(models=CANDIDATES, *, n: int = SAMPLE_N, repeats: int = REPEATS,
        num_predict: int | None = None, structured: bool = False,
        components: tuple[str, ...] | None = None,
        tier: str = "all", dry_run: bool = False, resume: bool = False,
        wait_for_gpu: bool = False, max_wait_minutes: int = 120,
        timeout: float = GEN_TIMEOUT,
        max_minutes_per_model: float = MAX_MINUTES_PER_MODEL) -> dict:
    rows = sample(tier, n)
    n_gen = len(rows) * len(models) * repeats * len(rubric.GENERATED_COMPONENTS)
    log(f"bake-off sample: {len(rows)} companies, {len(models)} models, "
        f"{repeats} repeats = {n_gen} generations")
    if dry_run:
        log("  " + ", ".join(r["ticker"] for r in rows))
        installed = installed_models()
        # Match the FULL tag. Comparing on the family alone called
        # qwen2.5:14b-instruct-q4_K_M "installed" because qwen2.5:7b was present, which
        # would have sent the run straight into a pull it claimed it did not need.
        have = {_norm_model(i) for i in installed}
        missing = [m for m in models if _norm_model(m) not in have]
        for m in models:
            log(f"  {'INSTALLED' if _norm_model(m) in have else 'NEEDS PULL':<11} {m}")
        if missing:
            log(f"  {len(missing)} candidates must be pulled before this can run. That is "
                f"a multi-GB download each, and a decision for the user - the harness "
                f"never pulls on its own.")
        log("  dry run - nothing generated, no GPU used")
        return {"dry_run": True, "sample": [r["ticker"] for r in rows],
                "models": list(models), "installed": installed,
                "needs_pull": missing, "n_generations": n_gen}

    ok, why = ollama.available()
    if not ok:
        log(f"ollama is not usable: {why}")
        return {"ok": False, "reason": why}

    BAKEOFF_DIR.mkdir(parents=True, exist_ok=True)
    as_of = utc_now_iso()

    # ---- build every pack ONCE. This is the load-bearing decision of the harness.
    packs: dict[str, dict] = {}
    for r in rows:
        try:
            ctx, _ = engine.build_context(
                r["ticker"], r["cik"], as_of=as_of, name=r.get("name", ""),
                sector=r.get("sector", ""), sub_industry=r.get("sub_industry", ""))
            packs[r["ticker"]] = ev_mod.build_pack(ctx)
            log(f"  pack {r['ticker']}")
        except Exception as exc:                      # noqa: BLE001
            log(f"  pack {r['ticker']} FAILED: {type(exc).__name__}: {exc}")
    if not packs:
        return {"ok": False, "reason": "no evidence packs could be built"}

    out: dict = {
        "study": "E07_llm_swap",
        "as_of": as_of,
        "preregistration":
            "journal/experiments/E07_llm_swap_preregistration.md",
        "sample": sorted(packs),
        "repeats": repeats,
        "incumbent": CANDIDATES[0],
        "models": {},
    }

    # wait_for_gpu lets this be queued BEHIND a running qual batch: it blocks on the
    # advisory lease instead of racing the batch for VRAM, which on a 6 GB card means
    # both jobs thrash and neither finishes.
    if wait_for_gpu:
        holder = ollama.lease_holder() or {}
        if holder:
            log(f"waiting for the GPU lease (held by pid {holder.get('pid')} until "
                f"{holder.get('expires_at')}), up to {max_wait_minutes} min")
    with ollama.gpu_lease(wait=wait_for_gpu,
                          max_wait_minutes=max_wait_minutes) as held:
        if not held:
            holder = ollama.lease_holder() or {}
            log(f"GPU lease held by pid {holder.get('pid')} - not starting")
            return {"ok": False, "reason": "gpu lease held elsewhere"}

        done = checkpointed_models() if resume else {}
        for model in models:
            slug = model.replace(":", "_").replace("/", "_")
            if slug in done:
                log(f"=== {model} - already checkpointed, skipping ===")
                out["models"][model] = done[slug]
                continue
            log(f"=== {model} ===")
            m: dict = {"generations": 0, "parse_failures": 0, "elapsed_s": [],
                       "unverified_flagged": 0, "unverified_total": 0,
                       "scores": {}, "nulls": 0, "score_slots": 0,
                       "bq_null_by_dimension": {}, "bq_seen_by_dimension": {},
                       "load_error": None, "failures": 0,
                       "consecutive_failures": 0, "companies_done": 0,
                       "budget_exhausted": False, "companies_total": len(packs)}
            arm_deadline = (time.monotonic() + max_minutes_per_model * 60
                            if max_minutes_per_model else None)
            for ticker, pack in packs.items():
                # A bounded arm. Without it a slow candidate eats the whole night: at
                # the measured 187 s/generation the 14B alone is 7 h, and qwen3:8b did
                # not finish a single generation in 300 s. Partial coverage is reported
                # as partial - fewer companies, stated - never as a completed arm.
                if arm_deadline and time.monotonic() > arm_deadline:
                    m["budget_exhausted"] = True
                    log(f"  {model}: {max_minutes_per_model:.0f} min budget reached "
                        f"after {m['companies_done']} of {len(packs)} companies")
                    break
                for component in (components or rubric.GENERATED_COMPONENTS):
                    body = pack["components"][component]
                    for rep in range(repeats):
                        t0 = time.perf_counter()
                        try:
                            raw = ollama.chat(prompts.prompt_for(component, body),
                                              system=prompts.SYSTEM, model=model,
                                              num_predict=num_predict,
                                              timeout=timeout,
                                              fmt=(prompts.schema_for(component)
                                                   if structured else None))
                        except Exception as exc:      # noqa: BLE001
                            # A model that will not answer is a RESULT, not a retry.
                            # Abandon after ABANDON_AFTER consecutive failures rather
                            # than spending the whole arm timing out: qwen3:8b at the
                            # default 300 s would have burned ~11 h producing nothing.
                            m["consecutive_failures"] += 1
                            m["failures"] += 1
                            log(f"  {model} generation failed "
                                f"({m['consecutive_failures']}/{ABANDON_AFTER}): "
                                f"{type(exc).__name__}: {exc}")
                            if m["consecutive_failures"] >= ABANDON_AFTER:
                                m["load_error"] = (
                                    f"{type(exc).__name__}: {exc} "
                                    f"(abandoned after {ABANDON_AFTER} consecutive "
                                    f"failures at a {timeout:.0f}s timeout)")
                                break
                            continue
                        m["consecutive_failures"] = 0
                        m["elapsed_s"].append(time.perf_counter() - t0)
                        m["generations"] += 1

                        parsed = _parse(component, raw, body)
                        if not parsed.get("parse_ok"):
                            m["parse_failures"] += 1
                        f, t = _unverified(parsed)
                        m["unverified_flagged"] += f
                        m["unverified_total"] += t

                        s = _scores_of(component, parsed)
                        for k, v in s.items():
                            m["score_slots"] += 1
                            if v is None:
                                m["nulls"] += 1
                            m["scores"].setdefault(f"{ticker}|{component}|{k}",
                                                   []).append(v)
                            if component == "BQ":
                                m["bq_seen_by_dimension"][k] = \
                                    m["bq_seen_by_dimension"].get(k, 0) + 1
                                if v is None:
                                    m["bq_null_by_dimension"][k] = \
                                        m["bq_null_by_dimension"].get(k, 0) + 1
                    if m["load_error"]:
                        break
                if m["load_error"]:
                    break
                m["companies_done"] += 1
                # Per-company progress. Without this the log is silent between
                # "=== model ===" and "done, checkpointed" - on the 14B that was a
                # 2h41m gap with no way to tell a working arm from a wedged one, and
                # no way to answer "how much longer" except by guessing from another
                # model's pace.
                done, tot = m["companies_done"], len(packs)
                secs = sum(m["elapsed_s"])
                rate = secs / max(done, 1)
                log(f"  {model}: {done}/{tot} companies, "
                    f"{secs / 60:.0f} min elapsed, ~{rate * (tot - done) / 60:.0f} min left")
            out["models"][model] = _summarise(m)
            _slug = model.replace(":", "_").replace("/", "_")
            (BAKEOFF_DIR / f"{_slug}.json").write_text(
                json.dumps(m["scores"], indent=2), encoding="utf-8")
            # Checkpoint the SUMMARY too, per model. The 14B offloads to CPU and can take
            # hours on its own; a box that reboots mid-arm (this one does - see the WHEA
            # history) would otherwise throw away every completed model. --resume reads
            # these back and skips what is already done.
            (BAKEOFF_DIR / f"{_slug}.summary.json").write_text(
                json.dumps(out["models"][model], indent=2), encoding="utf-8")
            log(f"  {model} done, checkpointed")

    _compare(out)
    return out


def _summarise(m: dict) -> dict:
    """M1-M5 for one candidate, plus E12's per-dimension abstention."""
    spreads = []
    for _key, vals in m["scores"].items():
        got = [v for v in vals if v is not None]
        if len(got) >= 2:
            spreads.append(max(got) - min(got))
    times = m["elapsed_s"]
    n_gen = m["generations"] or 1
    return {
        "load_error": m["load_error"],
        "generations": m["generations"],
        # M1: the single most important number in the pre-registration
        "M1_mean_spread": (float(statistics.mean(spreads)) if spreads else None),
        "M1_max_spread": (max(spreads) if spreads else None),
        "M1_share_unstable": (float(sum(1 for s in spreads if s > 0) / len(spreads))
                              if spreads else None),
        # M2
        "M2_parse_failure_rate": m["parse_failures"] / n_gen,
        "M2_parse_failures": m["parse_failures"],
        # M3
        "M3_unverified_rate": (m["unverified_flagged"] / m["unverified_total"]
                               if m["unverified_total"] else None),
        # M4
        "M4_null_rate": (m["nulls"] / m["score_slots"] if m["score_slots"] else None),
        # M5
        "M5_median_s_per_generation": (float(statistics.median(times)) if times else None),
        "M5_projected_hours_for_1500": (
            float(statistics.median(times)) * 3 * 1500 / 3600 if times else None),
        # partial coverage is stated, never silently averaged over fewer companies
        "companies_done": m.get("companies_done"),
        "companies_total": m.get("companies_total"),
        "budget_exhausted": m.get("budget_exhausted", False),
        "failed_generations": m.get("failures", 0),
        # E12's required addition
        "E12_bq_null_by_dimension": {
            k: round(m["bq_null_by_dimension"].get(k, 0) / v, 3)
            for k, v in sorted(m["bq_seen_by_dimension"].items())
        },
        "E12_watched_mean_null": (
            statistics.mean([m["bq_null_by_dimension"].get(k, 0)
                             / m["bq_seen_by_dimension"][k]
                             for k in E12_WATCH if m["bq_seen_by_dimension"].get(k)])
            if any(m["bq_seen_by_dimension"].get(k) for k in E12_WATCH) else None),
    }


def _compare(out: dict) -> None:
    """The registered pass criteria. No candidate is adopted by this file."""
    inc = out["models"].get(out["incumbent"]) or {}
    for model, m in out["models"].items():
        if model == out["incumbent"]:
            continue
        if m.get("load_error"):
            m["verdict"] = "REJECTED - would not load (recorded as a result)"
            m["criteria"] = {}
            continue
        c = {
            "M1_no_worse_consistency": _le(m.get("M1_mean_spread"),
                                           inc.get("M1_mean_spread")),
            "M2_no_worse_parse_rate": _le(m.get("M2_parse_failure_rate"),
                                          inc.get("M2_parse_failure_rate")),
            "M3_no_higher_unverified": _le(m.get("M3_unverified_rate"),
                                           inc.get("M3_unverified_rate")),
            "M5_under_24h_rescore": (None
                                     if m.get("M5_projected_hours_for_1500") is None
                                     else m["M5_projected_hours_for_1500"] < 24),
        }
        m["criteria"] = c
        # None means NOT MEASURED, which is not the same as FAIL and must never be
        # rendered as one. A 1-repeat smoke run cannot produce a spread at all, so M1
        # came back None and every candidate was printed as failing consistency it had
        # never been tested for.
        if any(v is None for v in c.values()):
            unmeasured = [k for k, v in c.items() if v is None]
            m["verdict"] = f"INCOMPLETE - not measured: {', '.join(unmeasured)}"
        else:
            m["verdict"] = "CANDIDATE" if all(c.values()) else "REJECTED"
    out["promoted"] = False
    out["note"] = ("Nothing is adopted by this harness. A verdict of CANDIDATE means the "
                   "registered criteria hold on a 15-company sample, not that the model "
                   "is better - the qual half has never been validated against forward "
                   "returns, so 'better' is not measurable here.")


def _le(a, b):
    """<= comparison that returns None when either side was never measured.

    Returning False for an unmeasured metric turns "we did not test this" into "this
    failed", which is how a 1-repeat smoke run printed FAIL on M1 for every candidate.
    """
    if a is None or b is None:
        return None
    return a <= b


def render(res: dict) -> str:
    if res.get("dry_run"):
        return f"dry run: {len(res['sample'])} companies x {len(res['models'])} models"
    L = ["# E07 results — the model bake-off", "",
         f"as_of {res['as_of']}  ·  pre-registered at `{res['preregistration']}`", "",
         f"{len(res['sample'])} companies, {res['repeats']} repeats per prompt, "
         f"incumbent `{res['incumbent']}`. The evidence pack is built ONCE per company "
         f"and reused across every arm, so M1 measures the model and not retrieval noise.",
         "", "## M1-M5", "",
         "| model | M1 mean spread | M1 unstable | M2 parse fail | M3 unverified | "
         "M4 null rate | M5 s/gen | projected 1500 |",
         "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for model, m in res["models"].items():
        if m.get("load_error"):
            L.append(f"| {model} | — would not load: {m['load_error']} | | | | | | |")
            continue
        # .get throughout: --resume reads summaries written by an earlier version of
        # this harness, and a missing key must not crash the report.
        L.append(
            f"| {model} | {_n(m.get('M1_mean_spread'))} | "
            f"{_p(m.get('M1_share_unstable'))} | "
            f"{_p(m.get('M2_parse_failure_rate'))} | "
            f"{_p(m.get('M3_unverified_rate'))} | "
            f"{_p(m.get('M4_null_rate'))} | "
            f"{_n(m.get('M5_median_s_per_generation'))} | "
            f"{_n(m.get('M5_projected_hours_for_1500'))} h |")
    partial = [(k, m) for k, m in res["models"].items()
               if m.get("budget_exhausted")
               or (m.get("companies_done") is not None
                   and m.get("companies_total")
                   and m["companies_done"] < m["companies_total"])]
    if partial:
        L += ["", "**Partial arms** — these did not cover the full sample, so their "
                  "metrics rest on fewer companies and are not directly comparable "
                  "to a complete arm:", ""]
        for k, m in partial:
            L.append(f"- `{k}`: {m.get('companies_done')} of "
                     f"{m.get('companies_total')} companies"
                     + (" (wall-clock budget reached)" if m.get("budget_exhausted")
                        else "")
                     + (f", {m['failed_generations']} failed generations"
                        if m.get("failed_generations") else ""))
    L += ["", "## E12's question: does a better model abstain less?", "",
          "If the four watched dimensions stop being abstained on, then a quarter of the "
          "universe sits under the BQ floor because of the MODEL and **no rubric change "
          "is warranted at all** (E12 P1).", "",
          "| model | " + " | ".join(E12_WATCH) + " | mean |",
          "|---|" + "---:|" * (len(E12_WATCH) + 1)]
    for model, m in res["models"].items():
        d = m.get("E12_bq_null_by_dimension") or {}
        if not d:
            continue
        cells = " | ".join(_p(d.get(k)) for k in E12_WATCH)
        L.append(f"| {model} | {cells} | {_p(m.get('E12_watched_mean_null'))} |")
    L += ["", "## Registered verdicts", ""]
    for model, m in res["models"].items():
        if model == res["incumbent"]:
            L.append(f"- `{model}`: incumbent / control arm")
            continue
        L.append(f"- `{model}`: **{m.get('verdict')}**")
        for k, v in (m.get("criteria") or {}).items():
            state = "NOT MEASURED" if v is None else ("PASS" if v else "FAIL")
            L.append(f"  - `{k}`: {state}")
    L += ["", res.get("note", ""), "", "Nothing is promoted. `promoted` stays false."]
    return "\n".join(L)


def _n(v):
    return "n/a" if v is None else f"{v:.2f}"


def _p(v):
    return "n/a" if v is None else f"{v * 100:.1f}%"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", help="comma-separated override of the registered set")
    ap.add_argument("--n", type=int, default=SAMPLE_N)
    ap.add_argument("--repeats", type=int, default=REPEATS)
    ap.add_argument("--tier", default="all")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--resume", action="store_true",
                    help="skip models already checkpointed in E07_raw/")
    ap.add_argument("--wait-for-gpu", action="store_true",
                    help="queue behind a running qual batch instead of refusing")
    ap.add_argument("--max-wait-minutes", type=int, default=120)
    ap.add_argument("--num-predict", type=int, default=None,
                    help="token budget per generation. The registered default (700) "
                         "is enough for a model that answers directly; one that "
                         "reasons at length in prose is TRUNCATED before it reaches "
                         "its JSON, which measures format and calls it judgement. "
                         "Raised equally for every arm, so no candidate is rescued.")
    ap.add_argument("--structured", action="store_true",
                    help="constrain generation to the rubric-generated JSON schema "
                         "(prompts.schema_for). Makes a parse failure, a missing key "
                         "and a prose preamble structurally impossible. `null` stays "
                         "a legal score type, so abstention is never forced into a "
                         "number. Applied to every arm in the run.")
    ap.add_argument("--components", default=None,
                    help="comma-separated subset of SG,BQ,MG. MG scores NOTHING "
                         "since E25 moved both CEO attributes to measured, so it "
                         "asks the model for an empty object.")
    ap.add_argument("--timeout", type=float, default=GEN_TIMEOUT,
                    help="per-generation timeout; a slow model is not a broken one")
    ap.add_argument("--max-minutes-per-model", type=float,
                    default=MAX_MINUTES_PER_MODEL,
                    help="wall-clock budget per arm; 0 disables")
    args = ap.parse_args(argv)

    models = ([s.strip() for s in args.models.split(",") if s.strip()]
              if args.models else CANDIDATES)
    res = run(models, n=args.n, repeats=args.repeats, tier=args.tier,
              dry_run=args.dry_run, resume=args.resume,
              wait_for_gpu=args.wait_for_gpu,
              max_wait_minutes=args.max_wait_minutes, timeout=args.timeout,
              num_predict=args.num_predict, structured=args.structured,
              components=(tuple(c.strip().upper() for c in args.components.split(','))
                          if args.components else None),
              max_minutes_per_model=args.max_minutes_per_model)
    if res.get("dry_run") or not res.get("models"):
        print(render(res) if res.get("dry_run") else json.dumps(res, indent=2))
        return 0 if res.get("dry_run") else 1

    exp = config.JOURNAL_DIR / "experiments"
    (exp / "E07_results.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    md = render(res)
    (exp / "E07_results.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
