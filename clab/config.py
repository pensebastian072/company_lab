"""THE path/port owner for company_lab.

Convention copied from options_desk/desk/config.py: BASE_DIR, one named
constant per artifact, cross-repo paths, UI_HOST/UI_PORT, mkdir loop at the
bottom.

Import-safe and side-effect-free apart from mkdir: no network, no cert
injection, no logging config. `clab.net.trust_windows_certs()` is called
explicitly by each entrypoint instead.

Drive split (C: is the slow SATA spinner on this box, D: is the NVMe):
  D:  bulk raw feeds - EDGAR companyfacts (~2 GB), yfinance json, prices,
      10-K text, LLM outputs. Regenerable, never committed.
  C:  journal/ + data/scorecards + data/scores.parquet - small, human-read,
      read by the UI on every request.
"""
from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------- roots
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_ROOT = Path(os.environ.get("CLAB_DATA_ROOT", r"D:\company_lab_data"))

# ---------------------------------------------------------------- C: side
DATA_DIR = BASE_DIR / "data"
SCORECARD_DIR = DATA_DIR / "scorecards"            # <CIK>_<TICKER>.json
SCORECARD_HISTORY_DIR = SCORECARD_DIR / "history"  # <CIK>_<as_of>.json
THESIS_DIR = DATA_DIR / "thesis"                   # <CIK>.json
EXPORT_DIR = DATA_DIR / "exports"                  # scores_YYYY-MM-DD.csv/.xlsx
# Stable names refreshed by every crawl, beside the dated archive. These are what a human
# opens weekly, so a desktop shortcut or a pinned Excel window keeps working.
LATEST_XLSX = EXPORT_DIR / "company_lab_latest.xlsx"
LATEST_CSV = EXPORT_DIR / "scores_latest.csv"
SCORES_PARQUET = DATA_DIR / "scores.parquet"       # the one table the UI reads

JOURNAL_DIR = BASE_DIR / "journal"
FLAGS_DIR = JOURNAL_DIR / "flags"
RUNS_DIR = JOURNAL_DIR / "runs"                    # <task>_<yyyyMMdd>.log
MANIFEST_DIR = JOURNAL_DIR / "manifest"
SNAPSHOT_DIR = JOURNAL_DIR / "snapshots"           # point-in-time, for the P6 grader
PROBE_DIR = JOURNAL_DIR / "probes"

STATE_FLAG = FLAGS_DIR / "company_lab_state.json"
FRESHNESS_FILE = FLAGS_DIR / "freshness.json"
CRAWL_MANIFEST = MANIFEST_DIR / "crawl_manifest.json"
QUAL_MANIFEST = MANIFEST_DIR / "qual_manifest.json"
EARNINGS_QUEUE = MANIFEST_DIR / "earnings_queue.json"
THESIS_HISTORY = JOURNAL_DIR / "thesis_history.jsonl"

# ---------------------------------------------------------------- D: side
EDGAR_DIR = DATA_ROOT / "edgar"
EDGAR_FACTS_DIR = EDGAR_DIR / "facts"              # CIK##########.json.gz
EDGAR_INDEX_DIR = EDGAR_DIR / "index"              # form.YYYYMMDD.idx.gz
EDGAR_SUBMISSIONS_DIR = EDGAR_DIR / "submissions"  # CIK##########.json.gz
EDGAR_FILINGS_DIR = EDGAR_DIR / "filings"          # <CIK>/<accn>.txt.gz (10-K text)
EDGAR_TICKERS_FILE = EDGAR_DIR / "company_tickers.json.gz"
YF_DIR = DATA_ROOT / "yf"                          # <SYM>/<endpoint>_<date>_<hash>.json.gz
PRICES_DIR = DATA_ROOT / "prices"                  # <SYM>.parquet
#: <CIK>_<component>_<sha1>.json. Overridable on its own, and NOT merely for tidiness:
#: `runner.fold_qual` asks `QUAL_DIR.glob(f"{cik}_{component}_*.json")`, which matches
#: EVERY model's payload for that CIK. Cache keys already carry the model
#: (`qual.scorer.cache_key`) so nothing is ever overwritten, but the fold's staleness
#: question is model-blind - so a second lane running a different model needs its own
#: directory, not just its own key.
QUAL_DIR = Path(os.environ.get("CLAB_QUAL_DIR", str(DATA_ROOT / "qual")))
UNIVERSE_DIR = DATA_ROOT / "universe"
CA_BUNDLE = DATA_ROOT / "_windows_ca_bundle.pem"
GPU_LEASE = DATA_ROOT / ".gpu_lease.json"
#: Serialises the DATA write path (scorecards, scores.parquet, the state flag). The GPU
#: lease does not cover it: batch and fold_qual never touch the GPU, so two of them can
#: and did run at once on 2026-08-16 and stomped each other's atomic renames.
WRITE_LEASE = FLAGS_DIR / ".write_lease.json"
WRITE_LEASE_TTL_MINUTES = 180      # a full crawl is ~30 min; a qual fold over 1,500 less
WRITE_LEASE_WAIT_MINUTES = 90      # queue behind a running batch rather than corrupt it

UNIVERSE_MEMBERS = UNIVERSE_DIR / "members.parquet"   # (as_of, ticker, cik, ...)
UNIVERSE_CHANGES = UNIVERSE_DIR / "changes.parquet"   # (date, added, removed)

# ---------------------------------------------------------------- network
# SEC requires a declared User-Agent with a contact address; it 403s without one.
SEC_USER_AGENT = os.environ.get(
    "CLAB_SEC_USER_AGENT", "company_lab/0.1 (research-contact@example.com)"
)
SEC_RPS = float(os.environ.get("CLAB_SEC_RPS", "6.0"))  # SEC allows 10/s; leave headroom
HTTP_TIMEOUT = float(os.environ.get("CLAB_HTTP_TIMEOUT", "30"))

EDGAR_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
EDGAR_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
EDGAR_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
EDGAR_DAILY_INDEX_URL = (
    "https://www.sec.gov/Archives/edgar/daily-index/{year}/QTR{qtr}/form.{ymd}.idx"
)
WIKI_SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

# ---------------------------------------------------------------- universe
UNIVERSE_TIERS = ("sp500", "sp400", "sp600", "xsect")
DEFAULT_TIER = "sp500"
WIKI_TIER_URLS = {
    "sp500": WIKI_SP500_URL,
    "sp400": "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies",
    "sp600": "https://en.wikipedia.org/wiki/List_of_S%26P_600_companies",
}
XSECT_UNIVERSE = Path(
    os.environ.get("XSECT_DATA_ROOT", r"D:\stock_xsect_data")
) / "universe.parquet"

# ---------------------------------------------------------------- crawl
BATCH_SIZE = int(os.environ.get("CLAB_BATCH_SIZE", "10"))   # user-specified
PROBE_MAX_AGE_DAYS = 7      # a >50-symbol crawl needs a probe report newer than this
PROBE_GATE_SYMBOLS = 50     # crawls larger than this are probe-gated
TICKERS_TTL_DAYS = 7
UNIVERSE_TTL_DAYS = 7
YF_TTL_HOURS = 20           # one trading day
FACTS_TTL_HOURS = 24        # fallback when accn revalidation is unavailable
SOURCE_STALE_DAYS = 4
STATE_STALE_HOURS = 48      # watchdog threshold

RETRY_TRANSIENT_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = (2, 8, 30)

# ---------------------------------------------------------------- qual (LLM)
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
#: Layers to offload to the GPU, or None to let ollama decide (the normal case).
#: Set to 0 to force a genuinely CPU-only generation. This exists because
#: CUDA_VISIBLE_DEVICES does NOT reliably keep ollama off the card on this box:
#: a second server started 2026-09-13 with CUDA_VISIBLE_DEVICES=-1 reported
#: size_vram=1.79GB and was competing with the GPU lane for a 6 GB card. The
#: per-request `num_gpu` option is the only setting that actually holds.
QUAL_NUM_GPU = (int(os.environ["CLAB_NUM_GPU"])
                if os.environ.get("CLAB_NUM_GPU", "").strip() != "" else None)
#: Inference threads, or None for ollama's default (every core). A CPU lane running beside
#: a GPU lane must NOT take all 8 cores: measured 2026-09-13, an uncapped CPU probe pushed
#: the GPU lane from 67.4 to 102.8 s/company, because the GPU lane still needs CPU for
#: tokenisation, sampling and the D: reads.
QUAL_NUM_THREAD = (int(os.environ["CLAB_NUM_THREAD"])
                   if os.environ.get("CLAB_NUM_THREAD", "").strip() != "" else None)
QUAL_MODEL = os.environ.get("CLAB_QUAL_MODEL", "qwen2.5:7b")
EMBED_MODEL = os.environ.get("CLAB_EMBED_MODEL", "nomic-embed-text")
QUAL_NUM_CTX = 8192         # set explicitly: the default silently truncates long prompts
QUAL_TEMPERATURE = 0.1
QUAL_SEED = 1337
#: Token budget per generation. 700 is enough for a model that answers directly, and it
#: was tuned to one that does. A model which reasons in prose FIRST is truncated before it
#: reaches its JSON, and the harness then reads a parse failure and calls it bad
#: judgement. Measured 2026-08-28: LFM2.5-2.6B-Finance emitted 3,417 characters of
#: reasoning and scored a 77.8% "parse failure" rate that was entirely this.
#: Overridable so a lane can raise it for EVERY arm at once - never for one.
QUAL_NUM_PREDICT = int(os.environ.get("CLAB_QUAL_NUM_PREDICT", "700"))
#: Constrain generation to the rubric-generated JSON schema (`qual.prompts.schema_for`).
#: Makes a parse failure, a missing key and a prose preamble structurally impossible.
#: `null` stays a legal score type, so honest abstention is never forced into a number.
QUAL_STRUCTURED = os.environ.get("CLAB_QUAL_STRUCTURED", "") == "1"
QUAL_KEEP_ALIVE = "10m"     # load the model once per batch, not once per symbol
GPU_LEASE_TTL_MINUTES = 30  # a killed process must not deadlock the GPU forever

# ------------------------------------------------- external intelligence (V3)
#: The third source of truth: competitive, sector, regulatory and technological
#: evidence a filing cannot supply, researched by a Codex department and ingested
#: here. It NEVER adds points to the 94 - it validates, contradicts, and bounds
#: confidence. See the V3 plan and clab/external/.
#:
#: Bulk lives on D: like every other cache. C: is the failing spinner.
EXTERNAL_ROOT = DATA_ROOT / "external"
EXTERNAL_DB = EXTERNAL_ROOT / "external_intelligence.duckdb"
EXTERNAL_RESEARCH_DIR = EXTERNAL_ROOT / "research"     # sectors/ industries/ companies/
EXTERNAL_PAYLOAD_DIR = EXTERNAL_ROOT / "payloads"      # <request_id>.json from Codex

#: The request/state pair. Same contract the options desk uses with Codex:
#: <x>_request.json carries a content-hashed request_id and a FROZEN roster,
#: <x>_state.json is the finalized summary. Codex does not apply the gates.
EXTERNAL_REQUEST = FLAGS_DIR / "external_research_request.json"
EXTERNAL_STATE = FLAGS_DIR / "external_intelligence_state.json"
#: The pass-B half of the two-pass rule, released only AFTER pass A is written.
#: Split into its own file on purpose: telling a researcher "do not look at this field
#: yet" inside one payload is an honour system, and anchoring is exactly what the blind
#: pass exists to measure. Two files makes it enforceable.
EXTERNAL_CONCLUSIONS = FLAGS_DIR / "external_research_conclusions.json"
EXTERNAL_HISTORY_DIR = JOURNAL_DIR / "external"        # <YYYY-MM>.jsonl, append-only

#: A record older than this is UNKNOWN, never stale-negative. Absence of research is
#: not bearish - that distinction is load-bearing and is tested.
EXTERNAL_STALE_DAYS = 120

# ---------------------------------------------------------------- weekly refresh
#: How many COMPANIES the weekend refresh will queue in one run. This is the one
#: number to change when the throughput should change - 115 is roughly a quarterly
#: cadence over a 1,500-company book (1500 / 13 weeks). Raise it to 200 or 500 and
#: nothing else needs editing; the selector just takes more off the same due list.
#: Set CLAB_REFRESH_BUDGET in the environment to override without editing code.
REFRESH_WEEKLY_BUDGET = int(os.environ.get("CLAB_REFRESH_BUDGET", "115"))

#: Companies are batched for Codex at this size. Batches are what `batch_health`
#: compares against each other, so this is not just a convenience.
REFRESH_BATCH_SIZE = int(os.environ.get("CLAB_REFRESH_BATCH", "43"))

#: Cadence per refresh_class, in days, when an object or company carries no explicit
#: `next_refresh_due`. STRUCTURAL facts do not move weekly - re-researching them on a
#: weekly clock spends searches to rewrite unchanged text, and re-judging on unchanged
#: evidence manufactures rank churn that is not signal.
REFRESH_DAYS = {
    "STRUCTURAL": 365,
    "QUARTERLY": 91,
    "EVENT_DRIVEN": 30,
}
#: Used when a record names no class at all.
REFRESH_DAYS_DEFAULT = 91

#: The funnel. Configurable because the right numbers are not known yet; hard-coding
#: them would freeze a guess into the architecture.
EXTERNAL_TRIAGE_N = int(os.environ.get("CLAB_EXT_TRIAGE_N", "400"))
EXTERNAL_RESEARCH_N = int(os.environ.get("CLAB_EXT_RESEARCH_N", "150"))
EXTERNAL_DEEP_N = int(os.environ.get("CLAB_EXT_DEEP_N", "50"))

#: Fraction of every batch drawn at random instead of by priority. Without a control
#: arm, researching only high-scorers is circular - a high score can never be
#: falsified because it is never challenged. This makes "does priority find more
#: contradictions than chance?" a measurable question.
EXTERNAL_CONTROL_FRACTION = float(os.environ.get("CLAB_EXT_CONTROL_FRACTION", "0.20"))

#: Fraction of SELF_ATTESTED claims re-fetched locally each run, purely to MEASURE the
#: self-attested lane's true error rate. E40 measured the local model citing text
#: absent from the filing 9.7% of the time; a web agent's surface is larger.
EXTERNAL_AUDIT_FRACTION = float(os.environ.get("CLAB_EXT_AUDIT_FRACTION", "0.10"))

#: Reconciliation caps. External evidence may move SG/BQ only through a written rule,
#: only on a verified citation, and never past these. Both the pre- and
#: post-reconciliation score are stored so the change is always reversible.
EXTERNAL_MAX_DELTA_SG = 2
EXTERNAL_MAX_DELTA_BQ = 2
EXTERNAL_MAX_DELTA_TOTAL = 3

#: Preconditions before ANY reconciliation rule may fire.
EXTERNAL_MIN_DEPTH_FOR_ADJUST = 2
EXTERNAL_MIN_CONFIDENCE_FOR_ADJUST = 0.60

#: Mirrors rubric.MIN_COVERAGE_FOR_BAND: below this, no external score at all.
EXTERNAL_MIN_COVERAGE = 0.80

# ---------------------------------------------------------------- UI
UI_HOST = "127.0.0.1"       # loopback ONLY. Never 0.0.0.0, never tunnelled.
UI_PORT = int(os.environ.get("CLAB_UI_PORT", "8100"))
# box port registry: HQ console 8099, options desk 8078, copper 8077,
# hq webhook 8090 (retired), company_lab 8100.
UI_STATE_TTL_SECONDS = 25.0
UI_SCORECARD_LRU = 128

ADVISORY_BANNER = (
    "ADVISORY / SHADOW - not validated against forward returns. "
    "The judged half (Structural Growth, Business Quality) is LLM-generated without "
    "human review. Management & Capital Allocation is measured, not judged - see "
    "journal/experiments/mg_label_correction.md."
)

for _d in (
    DATA_DIR, SCORECARD_DIR, SCORECARD_HISTORY_DIR, THESIS_DIR, EXPORT_DIR,
    JOURNAL_DIR, FLAGS_DIR, RUNS_DIR, MANIFEST_DIR, SNAPSHOT_DIR, PROBE_DIR,
    EXTERNAL_HISTORY_DIR,
):
    _d.mkdir(parents=True, exist_ok=True)


def ensure_data_root() -> bool:
    """Create the D: tree. Returns False if D: is unavailable (external drive).

    Callers that need bulk storage should check this and fail loudly rather
    than silently writing 2 GB onto the C: spinner.
    """
    try:
        for d in (
            EDGAR_FACTS_DIR, EDGAR_INDEX_DIR, EDGAR_SUBMISSIONS_DIR,
            EDGAR_FILINGS_DIR, YF_DIR, PRICES_DIR, QUAL_DIR, UNIVERSE_DIR,
            EXTERNAL_ROOT, EXTERNAL_RESEARCH_DIR, EXTERNAL_PAYLOAD_DIR,
        ):
            d.mkdir(parents=True, exist_ok=True)
        return True
    except OSError:
        return False
