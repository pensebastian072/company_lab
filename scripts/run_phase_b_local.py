"""Research companies for Phase B from the local filing cache and the local GPU.

Resumable by construction: every company's result is written to its own JSON file under
`D:\\company_lab_data\\external\\phase_b_local\\<ticker>.json` the moment it is finished, and a
company whose file exists is skipped. The box takes unclean shutdowns most days (five on
2026-08-31), so a lane that must survive more than an hour cannot hold its state in memory.

    --probe N        research N companies and STOP, printing throughput and spread
    --tickers A,B    research exactly these
    --unit <id>      research every company in one industry unit
    --limit N        stop after N companies this run
    --model          default qwen2.5:7b
    --cpu            run CPU-ONLY, for a second lane running beside the GPU lane. It
                     asserts size_vram == 0, the exact opposite of the normal assertion,
                     so a CPU lane can never quietly consume the card the fast lane needs.
    --reverse        take work from the END of the book. The CPU lane uses this so the two
                     lanes never race for the same company; they converge and the skip
                     check settles the overlap.
    --out <dir>      output directory; default is the qwen lane's dir. A DIFFERENT model
                     must be given a DIFFERENT dir - E38 settled that the gap between two
                     scorers is ~92% model, so one dir holding two models is a book whose
                     rows are not comparable to each other.

It asserts the GPU before doing anything, because ollama answers /api/tags normally while
running CPU-only and the difference is 660-702 s/company against ~50 s (CLAUDE.md). A
CPU-only run is refused rather than allowed to take 13x longer silently.

Writes NOTHING to the store or to the industry objects. The output is per-company JSON that a
later step assembles into a payload for `finalize` -> `acceptance` -> `research_ingest`.
"""
from __future__ import annotations

import collections
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, r"C:\Users\<your-user>\company_lab")

import pandas as pd

from clab import config
from clab.external import revenue_share as RS
from clab.qual import ollama as OL
from clab.external import local_phase_b as PB
from clab.external import schema as S
from clab.external import taxonomy as T

OUT = Path(r"D:\company_lab_data\external\phase_b_local")
STATUS = OUT / "_status.json"
OLLAMA = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen2.5:7b"

#: Lane label, stamped into every output file. This research is NOT the same standard as
#: the 311 rows the Codex lane produced - 8.1 of 12 fields against 9.6, 7.0 claims against
#: 17.7, and ONE independence domain against a mean of 2.76 - so the two must stay
#: distinguishable forever rather than merging into an undifferentiated corpus. Approved by
#: the user 2026-09-12 as "phase b v2, to see".
LANE = "phase_b_v2"
#: Retrieval-pattern regime, stamped into every row. "v1" is what scored the first 700
#: rows; "v2b" is E44's two-sided set - V1's recall plus a low end, minus the three
#: alternatives E43 measured to be junk.
PATTERNS_VERSION = "v2b"
#: Model tag appended to LANE. The 317 rows in `phase_b_local` were scored by qwen2.5:7b
#: and everything after 2026-09-13 by LFM2.5 at the user's instruction ("only use lfm2.5").
#: E38 settled that the gap between two scorers is ~92% MODEL and only ~9% format, so a
#: consumer that selected on lane alone would pool two books that are not comparable. The
#: per-file `model` field already records this; the lane label must not contradict it.
_MODEL_TAG = {"qwen2.5:7b": ""}
#: Companies per block. At the probed 30.6 s/company a block of 55 runs about 28 minutes,
#: inside the 30-minute repeat window, so a block finishes before its successor is due and
#: IgnoreNew never has to skip one.
DEFAULT_BLOCK = 55


def assert_gpu(model: str) -> None:
    """One real generate, then require size_vram > 0. Refuses a CPU-only run."""
    import urllib.request
    OL.chat("ok", model=model, num_predict=1, timeout=300)
    with urllib.request.urlopen(f"{OLLAMA}/api/ps", timeout=30) as resp:
        ps = json.loads(resp.read().decode("utf-8"))
    for m in ps.get("models", []):
        if m.get("name", "").startswith(model.split(":")[0]):
            vram, total = m.get("size_vram", 0), m.get("size", 1)
            if vram <= 0:
                raise SystemExit(
                    "ollama loaded the model on CPU ONLY (size_vram = 0). That is 13x "
                    "slower here - 660-702 s/company against ~50 s - and it answers "
                    "/api/tags normally the whole time. Kill ollama, start it again on a "
                    "quiet box, and re-run.")
            print(f"GPU ok: {model} {vram / 1e9:.2f} GB of {total / 1e9:.2f} GB on card "
                  f"({100 * vram / total:.0f}%)")
            return
    raise SystemExit(f"{model} is not in /api/ps after a generate - cannot confirm the GPU")


def assert_cpu(model: str) -> None:
    """One real generate, then require size_vram == 0. The mirror image of assert_gpu.

    A CPU lane exists to add throughput beside the GPU lane, so a CPU lane that quietly
    lands ON the card is worse than no CPU lane at all: it takes the compute the fast lane
    needs and returns less work for it. Measured 2026-09-13: a second ollama started with
    CUDA_VISIBLE_DEVICES=-1 reported size_vram=1.79GB and was doing exactly that. Only the
    per-request `num_gpu` option (config.QUAL_NUM_GPU) actually holds it off.
    """
    import urllib.request
    if config.QUAL_NUM_GPU != 0:
        raise SystemExit("--cpu requires CLAB_NUM_GPU=0 in the environment; "
                         f"config.QUAL_NUM_GPU is {config.QUAL_NUM_GPU!r}")
    OL.chat("ok", model=model, num_predict=1, timeout=900)
    ps = json.loads(urllib.request.urlopen(
        f"{config.OLLAMA_URL.rstrip('/')}/api/ps", timeout=30).read())
    for m in ps.get("models", []):
        if m.get("name", "").startswith(model.split(":")[0]):
            vram = m.get("size_vram") or 0
            if vram:
                raise SystemExit(
                    f"--cpu asked for a CPU-only lane but ollama put {vram / 1e9:.2f} GB "
                    f"of {model} on the GPU. That competes with the GPU lane for a 6 GB "
                    f"card and must not run.")
            print(f"CPU ok: {model} at {config.OLLAMA_URL}, size_vram = 0")
            return
    raise SystemExit(f"{model} is not in /api/ps after a generate - cannot confirm CPU")


def research(ticker: str, name: str, cik: str, model: str,
             inherited: dict[str, str]) -> PB.CompanyResult:
    res = PB.CompanyResult(ticker)
    res.filing = PB.load_filing(ticker, cik)
    if not res.filing:
        # A young registrant has no 10-K yet and is not an error. ADIG and MFP both came
        # back empty on 2026-09-13: each is a recent spin-off whose newest forms are
        # 10-12B/A and a single 10-Q. Writing them as permanent 0/12 rows would have been
        # the MAC failure again - a file exists, so the resume counts them done forever.
        #
        # The 10-Q is thinner evidence, not equivalent evidence, so the row records which
        # form backed it rather than letting a consumer assume a 10-K.
        res.filing = PB.load_filing(ticker, cik, form="10-Q")
        if res.filing:
            res.notes.append("no 10-K - researched from the 10-Q, which carries no "
                             "business description and usually no risk factors")
        else:
            res.notes.append("no cached 10-K and no cached 10-Q")
            return res
    cands = PB.candidates(res.filing.text)
    for field in S.COMPANY_ORDINALS:
        if field in inherited:
            # Inherited from the industry expert, or computed. Not a judgement call, and
            # deliberately carries no claim of its own: the claim lives on the industry
            # object, which is where the evidence is.
            res.categoricals[field] = inherited[field]
            continue
        pool = cands.get(field)
        if not pool:
            res.categoricals[field] = S.UNKNOWN
            res.abstained.append(f"{field}: no candidate sentence in the filing")
            continue
        raw = OL.chat(PB.prompt_for(ticker, name, field, pool), model=model,
                      num_predict=120, timeout=600,
                      fmt=PB.schema_for(field, len(pool)))
        value, idx, why = PB.parse_judgement(raw, field, len(pool))
        res.categoricals[field] = value
        if value == S.UNKNOWN or idx is None:
            res.abstained.append(f"{field}: {why}")
            continue
        quote = pool[idx]
        # Deterministic contradiction gate (E43). The model cites by index and so cannot
        # fabricate a quote; what it CAN do is cite a sentence that refutes its own
        # answer, which LFM2.5 did on 53.9% of its checkable competitive_position claims.
        # A refuted claim becomes an abstention, never a corrected answer - the sentence
        # shows the model misread, not what the right reading would have been.
        refuted = PB.contradicts(field, value, quote)
        if refuted:
            res.categoricals[field] = S.UNKNOWN
            res.abstained.append(f"{field}: {refuted}")
            res.notes.append(f"contradiction gate dropped {field}={value}")
            continue
        res.claims.append(PB.claim_for(ticker, field, value, quote, why, res.filing))
    bad = PB.verify_claims(res)
    if bad:
        res.notes.extend(bad)
        res.claims = []                     # never keep a claim whose quote did not check
        res.notes.append("ALL CLAIMS DROPPED - containment failed, which should be "
                         "impossible by construction; investigate before trusting this row")
    return res


def main(argv: list[str]) -> int:
    global OUT, STATUS
    model = argv[argv.index("--model") + 1] if "--model" in argv else DEFAULT_MODEL
    cpu = "--cpu" in argv
    reverse = "--reverse" in argv
    if "--out" in argv:
        OUT = Path(argv[argv.index("--out") + 1])
        STATUS = OUT / "_status.json"
    # The two lanes share an output directory on purpose - same model, same book - but they
    # must not share a status file, or each would overwrite the other's progress line and
    # neither would be readable.
    if cpu:
        STATUS = OUT / "_status_cpu.json"
    probe = int(argv[argv.index("--probe") + 1]) if "--probe" in argv else 0
    limit = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else 0
    block = int(argv[argv.index("--block") + 1]) if "--block" in argv else 0
    only = (argv[argv.index("--tickers") + 1].split(",")
            if "--tickers" in argv else None)
    unit = argv[argv.index("--unit") + 1] if "--unit" in argv else None

    OUT.mkdir(parents=True, exist_ok=True)
    if cpu:
        assert_cpu(model)
    else:
        assert_gpu(model)

    book = pd.read_parquet(config.SCORES_PARQUET)
    rows = book.to_dict("records")
    ind = {r["ticker"]: T.industry_id(r["ticker"], r.get("sub_industry")) for r in rows}

    # COMPUTED field: peer revenue share direction, which is what revenue_share.py was
    # built to answer and what it has answered for 1,251 of 1,500 companies. It fills
    # `market_share_direction` and NOTHING ELSE.
    #
    # It is NOT also used for `competitive_position_trend`, although the mapping
    # GAINING->IMPROVING reads naturally. Those two fields sit in DIFFERENT score
    # dimensions and carry 5 and 8 points separately (score.DIMENSIONS), so filling both
    # from one measurement would give one fact 13 points and make two dimensions the
    # framework treats as independent move together. That is the MG failure - one name
    # doing two jobs - in a new costume.
    share: dict[str, str] = {}
    try:
        for tk, r in RS.compute().items():
            d = str(r.get("direction") or "").upper()
            if d in ("GAINING", "FLAT", "LOSING"):
                share[tk] = d
        print(f"revenue_share: market_share_direction computed for {len(share)} companies")
    except Exception as exc:                       # loud, never silent
        print(f"revenue_share FAILED ({type(exc).__name__}: {exc}) - "
              f"market_share_direction will be UNKNOWN for every company this run")

    # Inherited field: the industry expert's own structural_growth, under the company
    # name for the same scale (schema.FIELD_SYNONYMS).
    growth: dict[str, str] = {}
    iroot = Path(r"D:\company_lab_data\external\research\industries")
    for iid in set(ind.values()):
        if not iid:
            continue
        p = iroot / iid / "industry_state.json"
        if not p.exists():
            continue
        v = str(json.loads(p.read_text(encoding="utf-8")).get("structural_growth")
                or S.UNKNOWN).upper()
        if v != S.UNKNOWN:
            growth[iid] = v

    todo = []
    for r in rows:
        t = str(r["ticker"])
        if only and t not in only:
            continue
        if unit and ind.get(t) != unit:
            continue
        if (OUT / f"{t}.json").exists():
            continue
        todo.append(r)
    # The CPU lane walks the book backwards so the two lanes start at opposite ends and
    # never pick the same company at the same moment. They meet in the middle, and from
    # there the "file already exists" skip settles it: worst case one company is done
    # twice, which costs time and corrupts nothing.
    if reverse:
        todo = todo[::-1]
    if probe:
        todo = todo[:probe]
    elif block:
        todo = todo[:block]
    elif limit:
        todo = todo[:limit]
    print(f"{len(todo)} company(ies) to research; {len(list(OUT.glob('*.json')))} already done\n")

    t0 = time.time()
    done = 0
    spread: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    claims_total = 0
    for r in todo:
        t = str(r["ticker"])
        iid = ind.get(t)
        inherited = {}
        if iid and iid in growth:
            inherited["industry_structural_growth"] = growth[iid]
        if t in share:
            inherited["market_share_direction"] = share[t]
        started = time.time()
        res = research(t, str(r.get("name") or t), r.get("cik"), model, inherited)
        answered = sum(1 for f in S.COMPANY_ORDINALS
                       if str(res.categoricals.get(f) or S.UNKNOWN).upper() != S.UNKNOWN)
        for f, v in res.categoricals.items():
            spread[f][v] += 1
        claims_total += len(res.claims)
        (OUT / f"{t}.json").write_text(json.dumps({
            "ticker": t, "industry_id": iid, "filed": res.filing.filed if res.filing else None,
            "source_url": res.filing.url if res.filing else None,
            "form": res.filing.form if res.filing else None,
            "categoricals": res.categoricals, "claims": res.claims,
            "abstained": res.abstained, "notes": res.notes, "model": model,
            # Which retrieval regime produced this row. The pools decide what evidence any
            # model ever sees, so a book mixing two of them is not internally comparable -
            # the same error as mixing two models in one directory. Stamped per row so a
            # consumer can never be left guessing, as it was for the first 700 rows.
            "patterns": PATTERNS_VERSION,
            "lane": _lane_for(model),
        }, indent=1), encoding="utf-8")
        done += 1
        # Checkpoint after EVERY company, not every block. The per-company file is the
        # real checkpoint - this one exists so a human can see progress without counting
        # 1,500 files, and so a killed block still reports where it got to.
        _write_status(done, len(todo), t, time.time() - t0)
        print(f"  {t:6} {answered:2}/12 answered, {len(res.claims):2} claims, "
              f"{time.time() - started:5.1f}s" + (f"  {res.notes}" if res.notes else ""))

    if not done:
        print("nothing to do")
        return 0
    el = time.time() - t0
    print(f"\n{done} companies in {el / 60:.1f} min = {el / done:.1f} s/company")
    print(f"claims: {claims_total} total, {claims_total / done:.1f} per company "
          f"(the 311 existing rows average 17.7)")
    remaining = 1500 - len([f for f in OUT.glob("*.json")
                            if not f.name.startswith("_status")])
    print(f"at this rate, {remaining} remaining companies = "
          f"{remaining * el / done / 3600:.1f} GPU-hours")
    print("\nVALUE SPREAD per field - a field with one value across the batch is the "
          "constant_fields failure the acceptance gate refuses:")
    for f in S.COMPANY_ORDINALS:
        c = spread.get(f)
        if c:
            print(f"  {f:28} {dict(c.most_common())}")
    return 0


def _write_status(done_this_run: int, block_size: int, last_ticker: str,
                  elapsed: float) -> None:
    """Progress a human can read without counting files.

    Written after every company. The authoritative checkpoint is still the per-company
    JSON - this file can be deleted without losing a single company's work - but a lane
    that only reports at the end of a block reports nothing at all when the box takes an
    unclean shutdown mid-block, which it does most days.
    """
    import datetime as _dt
    total_done = len(list(OUT.glob("*.json"))) - 1          # minus this status file
    STATUS.write_text(json.dumps({
        "lane": LANE,
        "updated": _dt.datetime.now().isoformat(timespec="seconds"),
        "companies_done_total": total_done,
        "companies_remaining": max(1500 - total_done, 0),
        "this_block": {"done": done_this_run, "of": block_size,
                       "last_ticker": last_ticker,
                       "seconds_per_company": round(elapsed / max(done_this_run, 1), 1)},
        "percent_complete": round(100 * total_done / 1500, 1),
    }, indent=1), encoding="utf-8")


def _lane_for(model: str) -> str:
    """LANE, suffixed with the model unless it is the original qwen lane."""
    if model in _MODEL_TAG:
        return LANE + _MODEL_TAG[model]
    short = model.split("/")[-1].split(":")[0].lower().replace("-gguf", "")
    return f"{LANE}_{short}"


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

