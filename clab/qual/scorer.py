"""The offline LLM batch: evidence -> prompt -> parse -> cache.

Modelled on hq-trading-system/analytics/llm_macro_analyst.py's
context -> prompt -> parse -> write loop, including the JSON extraction that
survives prose and the except-everything fail-safe.

Cache key = sha1(evidence pack + prompt template + model name), so:
  - an unchanged company is never re-scored and costs zero GPU;
  - a new filing, refreshed fundamentals, an edited prompt or a model swap all
    change the key and force a fresh score with no manual invalidation.

Rejection rules, all deliberate:
  - a non-integer score is rejected, not rounded;
  - an out-of-range score is rejected, NOT clamped - clamping would launder a
    hallucinated 9/4 into a top score;
  - `null` is the model's sanctioned "I don't know" and becomes NO_DATA;
  - a quote that does not overlap the supplied pack is kept but tagged
    `evidence_unverified`, which the UI renders as a warning chip.

Usage:
  python -m clab.qual.scorer --symbols AAPL,MSFT --probe
  python -m clab.qual.scorer --limit 20 --max-minutes 240
  python -m clab.qual.scorer --status
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time

from .. import config
from ..net import (atomic_write_json, log_stamp, read_json, sha1_text,
                   trust_windows_certs, utc_now_iso)
from ..runner import batch as batch_mod
from ..runner import engine
from ..scoring import rubric
from . import evidence as ev_mod
from . import ollama, prompts

MIN_EVIDENCE_OVERLAP = 0.60


def log(msg: str) -> None:
    # Local time with its offset - see net.log_stamp. Stored `as_of` fields stay UTC.
    print(f"[{log_stamp()}] {msg}", flush=True)


# ------------------------------------------------------------------ parsing
_DROPPED_PREFIX = "__clab_dropped_"


def _strip_bareword_keys(blob: str) -> str:
    """Rename unquoted keys to a unique sentinel so the object parses.

    Observed on UNP: the model emitted {"score": 4, null: "Significant regulatory
    hurdles..."} - a bare null where the key should be. Renaming rather than
    deleting works wherever the pair sits (first key, last key, only key) and
    leaves no dangling commas; `_drop_sentinels` removes the values afterwards.

    The score in that object is unambiguous, so it is kept. We never guess what
    the intended key was.
    """
    counter = [0]

    def repl(m: re.Match) -> str:
        counter[0] += 1
        return f'{m.group(1)}"{_DROPPED_PREFIX}{counter[0]}":'

    return re.sub(r"([{,]\s*)(?:null|true|false|undefined|None|NaN)\s*:", repl, blob)


def _drop_sentinels(obj):
    """Recursively remove the placeholder keys left by _strip_bareword_keys."""
    if isinstance(obj, dict):
        return {k: _drop_sentinels(v) for k, v in obj.items()
                if not (isinstance(k, str) and k.startswith(_DROPPED_PREFIX))}
    if isinstance(obj, list):
        return [_drop_sentinels(v) for v in obj]
    return obj


#: A double quote only ENDS a JSON string when the next non-space character is a
#: structural one. Anything else means the model copied a filing quote containing
#: quotation marks - measured on ITW ('Customer-back Innovation ("CBI")'), UPS
#: ('Logistics ("Frigo-Trans")') and others. Those interior quotes get escaped
#: rather than the whole company being thrown away.
_STRING_VALUE = re.compile(
    r'(:\s*)"((?:[^"\\]|\\.|"(?!\s*[,}\]]))*)"(?=\s*[,}\]])', re.S)


def _escape_inner_quotes(blob: str) -> str:
    def repl(m: re.Match) -> str:
        body = m.group(2)
        # escape only quotes that are not already escaped
        fixed = re.sub(r'(?<!\\)"', r'\\"', body)
        return f'{m.group(1)}"{fixed}"'

    return _STRING_VALUE.sub(repl, blob)


def _close_truncated(blob: str) -> str:
    """Close a response cut off by the token limit.

    Measured on DIS: the reply ended mid-object with the string still open. The
    sub-tests already completed are worth keeping; the truncated one simply
    becomes NO_DATA downstream, which is the honest outcome.
    """
    s = blob
    # drop a dangling unterminated string and whatever key introduced it
    if s.count('"') % 2 == 1:
        cut = s.rfind('"')
        s = s[:cut]
        comma = max(s.rfind(","), s.rfind("{"))
        if comma > 0:
            s = s[:comma]
    s = s.rstrip().rstrip(",")
    opens = s.count("{") - s.count("}")
    if opens > 0:
        s += "}" * opens
    brackets = s.count("[") - s.count("]")
    if brackets > 0:
        s += "]" * brackets
    return s


def _strip_stray_parens(blob: str) -> str:
    """Remove a stray ')' emitted straight after a closing brace or bracket.

    Measured on PYPL: the model wrote `...36 % ** **"}),` - a spurious paren
    between two sub-test objects. Only parens adjacent to structural tokens are
    touched, so parentheses inside quoted text are left alone.
    """
    return re.sub(r"([}\]])\s*\)+", r"\1", blob)


def _merge_sibling_objects(blob: str) -> dict | None:
    """Merge `{...},{...},{...}` emitted instead of one object.

    Observed on QCOM: the model closed the object after the first sub-test and
    started a new one for each subsequent sub-test. Wrapping the sequence in a
    list and merging is exactly what it meant.

    The separator varies: QCOM used a comma, SYY used only a newline. A `}` sitting
    directly before a `{` is never valid JSON anyway, so inserting the missing
    comma can only help.
    """
    normalized = re.sub(r"\}(\s*)\{", r"},\1{", blob)
    try:
        parsed = json.loads(f"[{normalized}]")
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, list) or not all(isinstance(x, dict) for x in parsed):
        return None
    merged: dict = {}
    for part in parsed:
        for k, v in part.items():
            # a repeated key means nested payloads (e.g. "dimensions"): merge those too
            if isinstance(v, dict) and isinstance(merged.get(k), dict):
                merged[k].update(v)
            else:
                merged.setdefault(k, v)
    return merged or None


def extract_json(raw: str) -> dict | None:
    """Survive prose, code fences, trailing chatter and two measured model quirks.

    Repairs are conservative: they only recover structure the model clearly
    intended. Nothing here invents a score, and a score that cannot be read as an
    in-range integer is still rejected downstream.
    """
    if not raw:
        return None
    # REPAIRS RUN ONLY WHEN THERE IS SOMETHING TO REPAIR. A clean response is returned
    # untouched, before any of the salvage below can damage it.
    #
    # This is not tidiness. The unpaired-`</think>` branch below rewrites `^.*?</think>`
    # to a space, and a schema-constrained model that writes the literal characters
    # `</think>` INSIDE a rationale - mid-quote, in the middle of otherwise valid JSON -
    # had everything before that point deleted. Measured 2026-08-31: all five parse
    # failures in the v2 lane were this, and they cost five whole judged components
    # (KGS, R, PLMR SG; AIZ, NWSA BQ). A repair for a format quirk destroyed answers that
    # `json.loads` accepted as they stood.
    try:
        clean = json.loads(raw.strip())
        if isinstance(clean, dict):
            return _drop_sentinels(clean)
    except (json.JSONDecodeError, ValueError):
        pass
    # Reasoning models (qwen3 and friends) emit a <think> block before the answer, and
    # it routinely contains braces - "maybe {\"score\": 3}?" - so the greedy match below
    # would start INSIDE the reasoning and swallow it. Strip it first. This is the same
    # category as the code fences and trailing chatter this function already survives,
    # and it is applied to every model equally so no E07 arm is rescued or penalised by
    # its output format rather than its judgement.
    raw = re.sub(r"<think>.*?</think>", " ", raw, flags=re.S | re.I)
    # An UNPAIRED closing tag: the model reasons in plain prose and then emits `</think>`
    # before the answer, with no opening tag anywhere. Measured on
    # LFM2.5-2.6B-Finance 2026-08-26, whose very first smoke test returned
    # `The user wants me to...</think>{"ok": true}`. Neither branch around this one fires
    # on that shape, so the prose stayed in front of the JSON - and since the greedy
    # `\{.*\}` below starts at the FIRST brace, any brace inside the reasoning (the
    # docstring above notes they are routine) would swallow the whole thing and read as a
    # parse failure. Applied to every model equally, so no arm is rescued or penalised by
    # its output format rather than its judgement.
    #
    # ...but it is TRIED, not applied: the stripped text is preferred and the ORIGINAL is
    # kept as a fallback. A `</think>` written inside a rationale looks identical to one
    # written in front of the answer, and there is no reliable way to tell them apart by
    # position - the reasoning legitimately contains braces, so "before the first brace"
    # is not a test. Parsing both and taking whichever works is.
    candidates = [raw]
    if "</think>" in raw.lower() and not re.search(r"<think>", raw, re.I):
        candidates.insert(0, re.sub(r"^.*?</think>", " ", raw, flags=re.S | re.I))
    for candidate in candidates:
        out = _extract_json_one(candidate)
        if out is not None:
            return out
    return None


def _extract_json_one(raw: str) -> dict | None:
    """One extraction attempt over one candidate string - the salvage ladder itself."""
    # An unterminated block means the whole response was reasoning; there is no answer.
    if re.search(r"<think>", raw, re.I):
        raw = re.sub(r"<think>.*", " ", raw, flags=re.S | re.I)
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return None
    blob = m.group(0)

    tidy = blob.replace(",\n}", "\n}").replace(",}", "}").replace(",]", "]")
    quoted = _escape_inner_quotes(blob)
    attempts = [
        blob,
        tidy,
        _strip_bareword_keys(blob),
        _strip_bareword_keys(tidy),
        quoted,
        _strip_bareword_keys(quoted),
        _strip_stray_parens(quoted),
        _strip_stray_parens(_strip_bareword_keys(quoted)),
        _close_truncated(blob),
        _close_truncated(quoted),
        _close_truncated(_strip_stray_parens(_strip_bareword_keys(quoted))),
    ]
    for attempt in attempts:
        try:
            out = json.loads(attempt)
            if isinstance(out, dict):
                return _drop_sentinels(out)
        except json.JSONDecodeError:
            continue

    for attempt in (blob, _strip_bareword_keys(blob)):
        merged = _merge_sibling_objects(attempt)
        if merged:
            return _drop_sentinels(merged)
    return None


def _clean_int(value, max_points: int):
    """(score, rejected_value). Rejects rather than coercing."""
    if value is None:
        return None, None
    if isinstance(value, bool):
        return None, value
    if isinstance(value, int):
        return (value, None) if 0 <= value <= max_points else (None, value)
    if isinstance(value, str):
        s = value.strip()
        if re.fullmatch(r"-?\d+", s):
            n = int(s)
            return (n, None) if 0 <= n <= max_points else (None, n)
        return None, value
    return None, value        # floats are rejected, never rounded


def _token_overlap(quote: str, pack: str) -> float:
    q = {w for w in re.findall(r"[a-z0-9]{4,}", (quote or "").lower())}
    if not q:
        return 0.0
    p = set(re.findall(r"[a-z0-9]{4,}", pack.lower()))
    return len(q & p) / len(q)


def _verify_evidence(quote: str | None, pack: str) -> tuple[str | None, bool]:
    """Cheap containment check - the concrete defence against fabricated citations."""
    if not quote or not isinstance(quote, str):
        return None, False
    quote = quote.strip()[:600]
    if not quote:
        return None, False
    return quote, _token_overlap(quote, pack) < MIN_EVIDENCE_OVERLAP


def parse_sg(raw: str, pack: str) -> dict:
    data = extract_json(raw)
    out = {"scores": {}, "parse_ok": data is not None}
    if not data:
        return out
    for key, _label, mx in rubric.SG_SUBTESTS:
        rec = data.get(key)
        if not isinstance(rec, dict):
            continue
        score, rejected = _clean_int(rec.get("score"), mx)
        quote, unverified = _verify_evidence(rec.get("evidence"), pack)
        out["scores"][key] = {
            "score": score,
            "rationale": str(rec.get("rationale") or "")[:300],
            "evidence": quote,
            "evidence_unverified": unverified,
            "rejected_value": rejected,
        }
    return out


def parse_bq(raw: str, pack: str) -> dict:
    data = extract_json(raw)
    out = {"dimensions": {}, "parse_ok": data is not None}
    if not data:
        return out
    dims = data.get("dimensions")
    if not isinstance(dims, dict):
        dims = data          # tolerate a flat object
    for key, _label in rubric.BQ_DIMENSIONS:
        rec = dims.get(key)
        if not isinstance(rec, dict):
            if isinstance(rec, (int, str)):
                rec = {"score": rec}
            else:
                continue
        score, rejected = _clean_int(rec.get("score"), rubric.BQ_DIMENSION_MAX)
        out["dimensions"][key] = {
            "score": score,
            "rationale": str(rec.get("rationale") or "")[:300],
            "rejected_value": rejected,
        }
    quote, unverified = _verify_evidence(data.get("evidence"), pack)
    out["killer_answer"] = str(data.get("killer_answer") or "")[:600]
    out["summary"] = str(data.get("summary") or "")[:300]
    out["evidence"] = quote
    out["evidence_unverified"] = unverified
    return out


def parse_mg(raw: str, pack: str) -> dict:
    data = extract_json(raw)
    out = {"ceo": {}, "parse_ok": data is not None}
    if not data:
        return out
    ceo = data.get("ceo")
    if not isinstance(ceo, dict):
        ceo = data
    for key, _label, source in rubric.MG_CEO_ATTRIBUTES:
        if source != "llm":
            continue          # measured attributes are never taken from the model
        rec = ceo.get(key)
        if not isinstance(rec, dict):
            if isinstance(rec, (int, str)):
                rec = {"score": rec}
            else:
                continue
        score, rejected = _clean_int(rec.get("score"), rubric.MG_CEO_ATTRIBUTE_MAX)
        out["ceo"][key] = {
            "score": score,
            "rationale": str(rec.get("rationale") or "")[:300],
            "rejected_value": rejected,
        }
    quote, unverified = _verify_evidence(data.get("evidence"), pack)
    out["ceo_summary"] = str(data.get("ceo_summary") or "")[:300]
    out["evidence"] = quote
    out["evidence_unverified"] = unverified
    return out


PARSERS = {"SG": parse_sg, "BQ": parse_bq, "MG": parse_mg}


# ------------------------------------------------------------------ cache
#: the three judgement components. A company is "done" only when all three are cached;
#: two out of three still leaves a hole in the 50-point half.
QUAL_COMPONENTS = ("SG", "BQ", "MG")

#: tickers touched by the most recent batch, so the fold-in re-scores exactly those
BATCH_MANIFEST = config.JOURNAL_DIR / "runs" / "qual_last_batch.txt"


def ciks_with_all_components() -> set[str]:
    """CIKs that already have every judgement component on disk.

    Read from the cache filenames (`{cik}_{component}_{sha}.json`) rather than by
    rebuilding evidence packs, so it costs no GPU and no EDGAR requests.
    """
    if not config.QUAL_DIR.exists():
        return set()
    seen: dict[str, set[str]] = {}
    for p in config.QUAL_DIR.glob("*.json"):
        parts = p.stem.split("_")
        if len(parts) >= 2:
            seen.setdefault(parts[0], set()).add(parts[1])
    return {cik for cik, comps in seen.items()
            if all(c in comps for c in QUAL_COMPONENTS)}


def load_universe_multi(tier: str) -> list[dict]:
    """Universe rows for one tier, or every tier when `tier == "all"`.

    The daily batch has to reach the S&P 400 and 600 - they are the ~1,000 companies
    without a judgement half - and a single-tier load would silently keep re-visiting
    the 500 that are already done.
    """
    if tier != "all":
        return batch_mod.load_universe(tier)
    rows: list[dict] = []
    seen: set[str] = set()
    for t in ("sp500", "sp400", "sp600"):
        try:
            for r in batch_mod.load_universe(t):
                if r["cik"] not in seen:
                    seen.add(r["cik"])
                    rows.append(r)
        except Exception as exc:  # noqa: BLE001 - one bad index page must not stop the rest
            log(f"  WARN could not load {t}: {type(exc).__name__}: {exc}")
    return rows


def cache_path(cik: str, component: str, evidence_sha1: str):
    return config.QUAL_DIR / f"{cik}_{component}_{evidence_sha1[:16]}.json"


def prompt_sha1(component: str) -> str:
    """Hash of the template itself, so editing a prompt invalidates its cache."""
    return sha1_text(prompts.prompt_for(component, "<EVIDENCE>"))[:16]


def cache_key(component: str, pack_sha1: str) -> str:
    """Legacy key: a hash of the RENDERED pack. Kept only for migration.

    This self-invalidated every day. The pack embeds price, market cap and P/E, and
    the yfinance cache is date-partitioned, so at UTC midnight every key changed and
    a resume re-scored the entire universe. Measured the hard way.
    """
    return sha1_text(f"{pack_sha1}|{prompt_sha1(component)}|{config.QUAL_MODEL}")


def stable_key(component: str, *, cik: str, accn: str | None,
               data_through: str | None) -> str:
    """The real cache key: semantic identity, not rendered text.

    A company's qualitative score should be re-generated when, and only when,
    something it depends on actually changes:

      accn          the filing the evidence was drawn from - changes on a new 10-K
      data_through  the newest reported period - changes on new fundamentals
      prompt        the rubric itself - an edited rubric SHOULD re-score everything
      model         a different model is a different opinion

    Deliberately NOT in the key: today's price, market cap, multiples, retrieval
    ordering, or any wording or whitespace in the pack. Those change daily or
    cosmetically and have nothing to do with whether the moat changed.
    """
    parts = [str(cik), component, accn or "no-accn", data_through or "no-period",
             prompt_sha1(component), config.QUAL_MODEL]
    return sha1_text("|".join(parts))


def cached(cik: str, component: str, pack_sha1: str) -> dict | None:
    key = cache_key(component, pack_sha1)
    return read_json(cache_path(cik, component, key))


# ------------------------------------------------------------------ one company
def _cheap_identity(ctx) -> tuple[str | None, str | None]:
    """(filing accn, data_through) without building the evidence pack.

    The stable key needs only these two, and both are available from artifacts
    already on disk - the submissions feed and the metric bundle. Deriving them
    cheaply is what lets a resume skip a finished company in well under a second
    instead of re-reading its 10-K and re-embedding 160 chunks.
    """
    from ..sources import edgar_filings

    try:
        row = edgar_filings.latest_annual(ctx.cik)
        accn = str(row.get("accessionNumber")) if row else None
    except Exception:  # noqa: BLE001
        accn = None
    return accn, ctx.metrics.raw("data_through")


def score_company(ctx, *, force: bool = False, use_embeddings: bool = True) -> dict:
    """Score SG, BQ and MG for one company. Never raises."""
    result = {"ticker": ctx.ticker, "cik": ctx.cik, "components": {},
              "cache_hits": 0, "generated": 0, "elapsed_s": {}, "errors": {}}

    # Fast path: if every component is already cached, never touch the filing or
    # the embedder. On a resume this is the difference between ~0.5 s and ~13 s
    # per finished company - about 80 minutes across the S&P 500.
    if not force:
        accn, data_through = _cheap_identity(ctx)
        keys = {c: stable_key(c, cik=ctx.cik, accn=accn, data_through=data_through)
                for c in rubric.GENERATED_COMPONENTS}
        if all(cache_path(ctx.cik, c, k).exists() for c, k in keys.items()):
            result["components"] = {c: "cache" for c in rubric.GENERATED_COMPONENTS}
            result["cache_hits"] = len(rubric.GENERATED_COMPONENTS)
            result["fast_path"] = True
            result["accn"] = accn
            result["data_through"] = data_through
            return result

    try:
        pack = ev_mod.build_pack(ctx, use_embeddings=use_embeddings)
    except Exception as exc:  # noqa: BLE001
        result["errors"]["evidence"] = f"{type(exc).__name__}: {exc}"
        return result
    result["evidence_meta"] = pack["meta"]

    accn = ((pack.get("meta") or {}).get("filing") or {}).get("accn")
    data_through = ctx.metrics.raw("data_through")
    result["accn"] = accn
    result["data_through"] = data_through

    for component in rubric.GENERATED_COMPONENTS:
        body = pack["components"][component]
        pack_sha = pack["sha1"][component]
        key = stable_key(component, cik=ctx.cik, accn=accn, data_through=data_through)
        path = cache_path(ctx.cik, component, key)

        if not force:
            hit = read_json(path)
            if isinstance(hit, dict):
                result["components"][component] = "cache"
                result["cache_hits"] += 1
                continue

        t0 = time.perf_counter()
        try:
            # `fmt` constrains generation to the rubric-generated schema when the lane
            # asks for it. Off by default, so the production lane is bit-identical to
            # what it was before this existed. Neither this flag nor the token budget is
            # part of the cache key (`stable_key` is pack + prompt + MODEL), so changing
            # either one mid-run silently mixes two generation regimes into one dataset -
            # settle them before a run starts, and wipe the lane's QUAL_DIR if they must
            # change after.
            raw = ollama.chat(prompts.prompt_for(component, body), system=prompts.SYSTEM,
                              fmt=(prompts.schema_for(component)
                                   if config.QUAL_STRUCTURED else None))
        except ollama.OllamaUnavailable as exc:
            # total fail-safe: no score at all, never a neutral midpoint
            result["errors"][component] = str(exc)
            result["components"][component] = "unavailable"
            continue
        except Exception as exc:  # noqa: BLE001
            result["errors"][component] = f"{type(exc).__name__}: {exc}"
            result["components"][component] = "error"
            continue
        elapsed = time.perf_counter() - t0
        result["elapsed_s"][component] = round(elapsed, 1)

        parsed = PARSERS[component](raw, body)
        payload = {
            **parsed,
            "ticker": ctx.ticker,
            "cik": ctx.cik,
            "component": component,
            "model": config.QUAL_MODEL,
            "prompt_sha1": prompt_sha1(component),
            "evidence_sha1": pack_sha,
            "cache_key": key,
            "key_scheme": "stable_v2",
            "filing_accn": accn,
            "data_through": data_through,
            "generated_at": utc_now_iso(),
            "elapsed_s": round(elapsed, 1),
            "evidence_meta": pack["meta"],
            "raw_response_chars": len(raw),
            # The GENERATION REGIME, recorded because neither of these is in the cache
            # key and a payload could not otherwise say which one produced it. E38 hit
            # exactly that wall: its whole claim is "same model, different format", and
            # the only way to check the format was actually on was to re-read the env
            # plumbing - the 253 payloads themselves could not answer it. A run that
            # cannot describe its own regime cannot be compared to another one.
            "structured": bool(config.QUAL_STRUCTURED),
            "num_predict": int(config.QUAL_NUM_PREDICT),
        }
        if not parsed.get("parse_ok"):
            payload["raw_response"] = raw[:4000]     # keep it for diagnosis
        try:
            atomic_write_json(path, payload)
        except Exception as exc:  # noqa: BLE001
            result["errors"][component] = f"cache write failed: {exc}"
        result["components"][component] = "generated" if parsed.get("parse_ok") \
            else "parse_failed"
        result["generated"] += 1
    return result


# ------------------------------------------------------------------ the batch
def run(*, tier: str = config.DEFAULT_TIER, symbols: list[str] | None = None,
        limit: int | None = None, force: bool = False, max_minutes: float = 0.0,
        probe: bool = False, use_embeddings: bool = True,
        wait_for_gpu: bool = False, only_missing: bool = False) -> dict:
    trust_windows_certs()
    ok, why = ollama.available()
    if not ok:
        log(f"ollama is not usable: {why}")
        log("  SG/BQ/MG stay NO_DATA for every company, the full band stays "
            "withheld, and the measured /50 is unaffected.")
        log(f"  start it with: \"{_ollama_exe()}\" serve")
        return {"ok": False, "reason": why}
    log(why)

    rows = load_universe_multi(tier)
    by = {r["ticker"]: r for r in rows}
    if symbols:
        wanted = [s.strip().upper().replace(".", "-") for s in symbols]
        missing = [s for s in wanted if s not in by]
        if missing and tier != "all":
            # An explicit --symbols list is a statement about WHICH companies to score,
            # so silently dropping the ones outside the default tier is wrong: asking
            # for 215 companies and scoring 93 of them looked like a completed run.
            # Widen to every tier before giving up on them.
            log(f"  {len(missing)} of {len(wanted)} symbols are not in tier {tier!r}; "
                f"searching all tiers")
            rows = load_universe_multi("all")
            by = {r["ticker"]: r for r in rows}
            missing = [s for s in wanted if s not in by]
        if missing:
            log(f"  WARNING: {len(missing)} symbols are in no universe and will NOT be "
                f"scored: {', '.join(missing[:15])}"
                + (" ..." if len(missing) > 15 else ""))
        todo = [by[s] for s in wanted if s in by]
    else:
        todo = batch_mod.order_universe(rows, "marketcap")
    if only_missing and not symbols:
        # Without this, `--limit 100` spends the whole budget on the largest companies,
        # which are exactly the ones already cached: the run costs no GPU, scores nobody
        # new, and reports success. That is what a daily 100-a-day job would have done
        # every single day.
        done = ciks_with_all_components()
        before = len(todo)
        todo = [r for r in todo if str(r["cik"]) not in done]
        log(f"  --only-missing: {before - len(todo)} of {before} already have all three "
            f"components cached; {len(todo)} left to score")
    if limit:
        todo = todo[:limit]
    if probe:
        todo = todo[:max(len(todo) and 3, 3)][:3]

    log(f"qual batch: {len(todo)} companies, model {config.QUAL_MODEL}")
    # The tickers this batch touched, for the fold-in step. `batch --tier X` skips
    # companies the manifest already marks done, so a plain re-run does NOT pick up
    # freshly cached judgement scores - they sit in the cache, invisible. Passing
    # --symbols bypasses resume, so the caller needs to know exactly who to re-score.
    try:
        BATCH_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        BATCH_MANIFEST.write_text(",".join(r["ticker"] for r in todo),
                                  encoding="utf-8")
    except Exception:  # noqa: BLE001 - a bookkeeping file must not fail the batch
        pass
    deadline = time.monotonic() + max_minutes * 60 if max_minutes else None

    with ollama.gpu_lease(wait=wait_for_gpu, max_wait_minutes=30) as held:
        if not held:
            holder = ollama.lease_holder() or {}
            log(f"GPU lease held by pid {holder.get('pid')} until "
                f"{holder.get('expires_at')} - not starting")
            return {"ok": False, "reason": "gpu lease held elsewhere"}

        as_of = utc_now_iso()
        stats = {"n": 0, "cache": 0, "generated": 0, "failed": 0, "times": []}
        for i, r in enumerate(todo, 1):
            if deadline and time.monotonic() > deadline:
                log(f"wall-clock limit reached after {i - 1} companies - resumable, "
                    f"just run it again")
                break
            ollama.renew_lease()
            try:
                # No with_qual flag any more: the cache is always read. Harmless here -
                # the evidence pack never consults ctx.qual, so loading a company's
                # previous judgement scores cannot leak into the prompt or the pack hash.
                ctx, _meta = engine.build_context(
                    r["ticker"], r["cik"], as_of=as_of, name=r.get("name", ""),
                    sector=r.get("sector", ""), sub_industry=r.get("sub_industry", ""))
            except Exception as exc:  # noqa: BLE001 - per-company isolation
                stats["failed"] += 1
                log(f"  {r['ticker']:6s} context failed: {type(exc).__name__}: {exc}")
                continue

            res = score_company(ctx, force=force, use_embeddings=use_embeddings)
            stats["n"] += 1
            stats["cache"] += res["cache_hits"]
            stats["generated"] += res["generated"]
            total = sum(res["elapsed_s"].values())
            if total:
                stats["times"].append(total)
            state = ",".join(f"{k}={v}" for k, v in res["components"].items())
            if res.get("fast_path"):
                # No pack was built, so there are no sections to report. Say that
                # rather than printing sections=none, which is the signal used to
                # detect filers whose 10-K has no Item 1/1A/7 to slice.
                detail = "cached (pack not rebuilt)"
            else:
                ev = res.get("evidence_meta") or {}
                detail = f"sections={','.join(ev.get('sections_found') or []) or 'none'}"
            log(f"  {i}/{len(todo)} {r['ticker']:6s} {total:6.1f}s  {state}  {detail}"
                + (f"  ERR {res['errors']}" if res["errors"] else ""))

        if stats["times"]:
            med = statistics.median(stats["times"])
            log(f"median {med:.0f}s per company -> {med * len(rows) / 3600:.1f} h "
                f"for {len(rows)} companies")
            stats["median_seconds"] = round(med, 1)
            stats["projected_hours_full_universe"] = round(med * len(rows) / 3600, 2)

    log(f"done: {stats['n']} companies, {stats['generated']} generated, "
        f"{stats['cache']} from cache, {stats['failed']} failed")
    log("re-run `clab.runner.batch` (without --skip-qual) to fold these into the scores")
    return {"ok": True, **stats}


def _ollama_exe() -> str:
    import os
    from pathlib import Path

    for cand in (Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Ollama/ollama.exe",
                 Path(r"C:\Program Files\Ollama\ollama.exe")):
        if cand.exists():
            return str(cand)
    return "ollama"


def reparse(*, dry_run: bool = False) -> dict:
    """Re-parse cached payloads that failed to parse, using the current parser.

    Free: every parse failure stores its raw_response, so a parser improvement can
    recover the company with no GPU time and no re-fetch. This is the reason the
    raw response is kept at all.
    """
    out = {"examined": 0, "recovered": 0, "still_failed": 0, "tickers": []}
    if not config.QUAL_DIR.exists():
        return out
    for path in sorted(config.QUAL_DIR.glob("*.json")):
        d = read_json(path)
        if not isinstance(d, dict) or d.get("parse_ok"):
            continue
        raw = d.get("raw_response")
        if not raw:
            continue
        out["examined"] += 1
        component = d.get("component")
        parser = PARSERS.get(component)
        if parser is None:
            continue
        # The evidence pack is not stored verbatim, so evidence quotes cannot be
        # re-verified here; mark them unverified rather than silently trusting them.
        parsed = parser(raw, "")
        if not parsed.get("parse_ok"):
            out["still_failed"] += 1
            continue
        merged = {**d, **parsed, "reparsed_at": utc_now_iso(),
                  "reparse_note": ("recovered from the stored raw response by a later "
                                   "parser; evidence quotes could not be re-verified "
                                   "against the original pack")}
        merged.pop("raw_response", None)
        for block in ("scores", "dimensions", "ceo"):
            body = merged.get(block)
            if isinstance(body, dict):
                for rec in body.values():
                    if isinstance(rec, dict) and rec.get("evidence"):
                        rec["evidence_unverified"] = True
        out["recovered"] += 1
        out["tickers"].append(f"{d.get('ticker')}/{component}")
        if not dry_run:
            try:
                atomic_write_json(path, merged)
            except Exception as exc:  # noqa: BLE001
                log(f"  could not rewrite {path.name}: {exc}")
    return out


def migrate_cache(*, dry_run: bool = False) -> dict:
    """Re-key legacy payloads onto the stable scheme, offline.

    The old key hashed the rendered pack, which embedded the day's price, so the
    whole cache invalidated at UTC midnight. Everything the stable key needs is
    already inside each payload (cik, component, filing accn) or in the scorecard
    on disk (data_through), so no pack rebuild, no network and no GPU are required.
    """
    out = {"examined": 0, "migrated": 0, "already_stable": 0, "unmappable": 0,
           "details": []}
    if not config.QUAL_DIR.exists():
        return out

    # cik -> data_through, from the scorecards written by the quant crawl
    through: dict[str, str] = {}
    for p in config.SCORECARD_DIR.glob("*.json"):
        d = read_json(p)
        if isinstance(d, dict) and d.get("cik"):
            through[str(d["cik"])] = d.get("data_through")

    for path in sorted(config.QUAL_DIR.glob("*.json")):
        d = read_json(path)
        if not isinstance(d, dict) or not d.get("component"):
            continue
        out["examined"] += 1
        if d.get("key_scheme") == "stable_v2":
            out["already_stable"] += 1
            continue
        cik = str(d.get("cik") or "")
        component = d["component"]
        accn = ((d.get("evidence_meta") or {}).get("filing") or {}).get("accn")
        dt = d.get("data_through") or through.get(cik)
        if not cik or not accn:
            out["unmappable"] += 1
            out["details"].append(f"{d.get('ticker')}/{component}: no cik or accn")
            continue
        key = stable_key(component, cik=cik, accn=accn, data_through=dt)
        new_path = cache_path(cik, component, key)
        d.update({"key_scheme": "stable_v2", "cache_key": key,
                  "filing_accn": accn, "data_through": dt,
                  "migrated_at": utc_now_iso(),
                  "legacy_cache_key": d.get("cache_key")})
        if dry_run:
            out["migrated"] += 1
            continue
        try:
            atomic_write_json(new_path, d)
            if new_path.resolve() != path.resolve():
                path.unlink(missing_ok=True)
            out["migrated"] += 1
        except Exception as exc:  # noqa: BLE001
            out["unmappable"] += 1
            out["details"].append(f"{d.get('ticker')}/{component}: {exc}")
    return out


def status() -> dict:
    hits = list(config.QUAL_DIR.glob("*.json")) if config.QUAL_DIR.exists() else []
    per: dict[str, int] = {}
    ciks: set[str] = set()
    for p in hits:
        parts = p.stem.split("_")
        if len(parts) >= 2:
            per[parts[1]] = per.get(parts[1], 0) + 1
            ciks.add(parts[0])
    ok, why = ollama.available()
    return {"cached_payloads": len(hits), "per_component": per,
            "companies_with_any": len(ciks), "ollama": why, "ollama_ok": ok,
            "model": config.QUAL_MODEL, "dir": str(config.QUAL_DIR),
            "gpu_lease": ollama.lease_holder()}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tier", default=config.DEFAULT_TIER,
                    choices=(*config.UNIVERSE_TIERS, "all"),
                    help="'all' spans sp500+sp400+sp600, deduped by CIK")
    ap.add_argument("--only-missing", action="store_true",
                    help="skip companies that already have all three components cached "
                         "- without it, --limit is spent on the largest names, which "
                         "are the ones already done")
    ap.add_argument("--symbols")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--force", action="store_true", help="ignore the qual cache")
    ap.add_argument("--max-minutes", type=float, default=0.0,
                    help="stop after N minutes (resumable)")
    ap.add_argument("--probe", action="store_true", help="3 companies, then report timing")
    ap.add_argument("--no-embeddings", action="store_true",
                    help="keyword retrieval only (faster, lower quality)")
    ap.add_argument("--wait-for-gpu", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--reparse", action="store_true",
                    help="re-parse cached parse failures with the current parser (no GPU)")
    ap.add_argument("--migrate-cache", action="store_true",
                    help="re-key legacy payloads onto the stable scheme (no GPU)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    if args.status:
        print(json.dumps(status(), indent=2, default=str))
        return 0
    if args.reparse:
        print(json.dumps(reparse(dry_run=args.dry_run), indent=2, default=str))
        return 0
    if args.migrate_cache:
        print(json.dumps(migrate_cache(dry_run=args.dry_run), indent=2, default=str))
        return 0

    res = run(tier=args.tier,
              symbols=[s for s in (args.symbols or "").split(",") if s.strip()] or None,
              limit=args.limit, force=args.force, max_minutes=args.max_minutes,
              probe=args.probe, use_embeddings=not args.no_embeddings,
              wait_for_gpu=args.wait_for_gpu, only_missing=args.only_missing)
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
