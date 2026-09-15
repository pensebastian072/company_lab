"""Take a frontier model's moat scores and let in only what the filing actually says.

`clab.research.external_batches` hands out ten companies at a time; the answers come back
as one JSON object. This ingests them under the same discipline the local repair pass
obeys, with one deliberate difference:

    the local repair verifies a quote against the eight-chunk evidence PACK.
    an external answer is verified against the WHOLE FILING TEXT on disk.

That is not a loosening - it is the correct check for a reader that had the whole 10-K.
A quote the pack never contained can still be real, and a quote the FILING never contained
is fabricated no matter how plausible it reads. Anything that fails is stored and shown,
and scores nothing.

Provenance is explicit: these points are labelled with the model that produced them, so a
score from a frontier model is never silently mixed with one from `qwen2.5:7b`. E07
measured that different models fabricate at very different rates; the workbook has to be
able to tell them apart.

    python -m clab.runner.ingest_external --file journal/external/batch_001_reply.json
    python -m clab.runner.ingest_external --file reply.json --model gemini-3-pro --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone

from .. import config
from ..net import atomic_write_json, log_stamp, read_json, utc_now_iso
from ..scoring import rubric
from ..scoring.repair_merge import REPAIRS_KEY
from ..sources import edgar_filings
from . import engine

REPORT = config.JOURNAL_DIR / "external" / "ingested.jsonl"
VALID_DIMENSIONS = {k for k, _lbl in rubric.BQ_DIMENSIONS}
#: quotes shorter than this verify against anything
MIN_QUOTE_CHARS = 25


def log(msg: str) -> None:
    print(f"[{log_stamp()}] {msg}", flush=True)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def _extract(blob: str) -> dict | None:
    """Tolerate a reply wrapped in prose or code fences; refuse to guess beyond that."""
    blob = blob.strip()
    if blob.startswith("```"):
        blob = re.sub(r"^```[a-zA-Z]*\n", "", blob)
        blob = re.sub(r"\n```\s*$", "", blob)
    try:
        return json.loads(blob)
    except ValueError:
        pass
    start, end = blob.find("{"), blob.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(blob[start:end + 1])
        except ValueError:
            return None
    return None


def verify_against_filing(quote: str, filing_text: str) -> dict:
    """Is this sentence in the company's own 10-K?"""
    if not quote or len(quote.strip()) < MIN_QUOTE_CHARS:
        return {"has_quote": bool(quote), "verified": False,
                "why": f"quote shorter than {MIN_QUOTE_CHARS} characters"}
    if not filing_text:
        return {"has_quote": True, "verified": False, "why": "no filing text on disk"}
    return {"has_quote": True, "verified": _norm(quote)[:600] in _norm(filing_text),
            "why": ""}


def payload_path(cik: str, component: str = "BQ"):
    hits = sorted(config.QUAL_DIR.glob(f"{cik}_{component}_*.json"))
    return hits[-1] if hits else None


def ciks_by_ticker() -> dict[str, str]:
    import pandas as pd
    df = pd.read_parquet(config.SCORES_PARQUET)
    return {str(t).upper(): str(c).zfill(10)
            for t, c in zip(df["ticker"], df["cik"]) if t}


def ingest(reply: dict, *, model: str, run_id: str, dry_run: bool = False) -> dict:
    lookup = ciks_by_ticker()
    stats = {"companies": 0, "offered": 0, "verified": 0, "unverified": 0,
             "not_applicable": 0, "rejected_range": 0, "unknown_ticker": [],
             "no_filing": [], "by_company": {}}
    for entry in reply.get("companies") or []:
        ticker = str(entry.get("ticker") or "").upper().strip()
        cik = lookup.get(ticker)
        if not cik:
            stats["unknown_ticker"].append(ticker)
            continue
        path = payload_path(cik)
        if path is None:
            stats["no_filing"].append(ticker)
            continue
        text, _fmeta = edgar_filings.filing_text(cik)
        if not text:
            stats["no_filing"].append(ticker)
            continue

        payload = read_json(path)
        if not isinstance(payload, dict):
            stats["no_filing"].append(ticker)
            continue
        existing = payload.get("dimensions") or {}
        repairs = dict(payload.get(REPAIRS_KEY) or {})
        kept, dropped, na = [], [], []
        for key, rec in (entry.get("dimensions") or {}).items():
            if key not in VALID_DIMENSIONS or not isinstance(rec, dict):
                continue
            stats["offered"] += 1
            # never overwrite what our own model scored - the same rule the local repair
            # obeys, for the same reason: a collision means a stale payload, not a
            # judgement to arbitrate
            prior = existing.get(key)
            if isinstance(prior, dict) and prior.get("score") is not None:
                continue
            if rec.get("not_applicable"):
                na.append(key)
                stats["not_applicable"] += 1
                repairs[key] = {
                    "score": None, "not_applicable": True,
                    "rationale": str(rec.get("rationale") or "")[:300],
                    "quote": None, "gate": "not_applicable", "source": model,
                    "origin": "external", "run_id": run_id,
                    "generated_at": utc_now_iso(),
                }
                continue
            raw = rec.get("score")
            score = None
            if isinstance(raw, bool):
                score = None
            elif isinstance(raw, (int, float)) and float(raw).is_integer():
                v = int(raw)
                score = v if 0 <= v <= rubric.BQ_DIMENSION_MAX else None
                if score is None:
                    stats["rejected_range"] += 1
            quote = rec.get("evidence") if isinstance(rec.get("evidence"), str) else None
            check = verify_against_filing(quote or "", text)
            gate = "strict" if (score is not None and check["verified"]) else (
                "unverified" if check["has_quote"] else "no_quote")
            if gate == "strict":
                kept.append(key)
                stats["verified"] += 1
            elif score is not None:
                dropped.append(key)
                stats["unverified"] += 1
            repairs[key] = {
                "score": score,
                "rationale": str(rec.get("rationale") or "")[:300],
                "quote": (quote or "")[:600] or None,
                "gate": gate,
                "verified_against": "filing_text",
                "source": model,
                "origin": "external",
                "run_id": run_id,
                "generated_at": utc_now_iso(),
            }
        stats["companies"] += 1
        stats["by_company"][ticker] = {"kept": sorted(kept), "dropped": sorted(dropped),
                                       "not_applicable": sorted(na)}
        if not dry_run and (kept or dropped or na):
            payload[REPAIRS_KEY] = repairs
            payload["repaired_at"] = utc_now_iso()
            atomic_write_json(path, payload)
            visible = (engine.load_qual(cik) or {}).get("BQ") or {}
            if not set(kept).issubset(set(visible.get(REPAIRS_KEY) or {})):
                raise RuntimeError(
                    f"{ticker}: written to {path.name} but not visible through "
                    f"engine.load_qual - the scorer reads a different payload")
        log(f"  {ticker:<6} kept {len(kept):>2}  dropped {len(dropped):>2}  "
            f"n/a {len(na):>2}")
    return stats


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", required=True, help="the model's JSON reply")
    ap.add_argument("--model", default="gemini",
                    help="what produced it; stored as provenance on every point")
    ap.add_argument("--dry-run", action="store_true",
                    help="verify and report, write nothing")
    args = ap.parse_args(argv)

    blob = open(args.file, encoding="utf-8").read()
    reply = _extract(blob)
    if not isinstance(reply, dict):
        log(f"could not parse JSON from {args.file}")
        return 2

    run_id = datetime.now(timezone.utc).strftime("external_%Y%m%dT%H%M%SZ")
    stats = ingest(reply, model=args.model, run_id=run_id, dry_run=args.dry_run)
    stats["run_id"] = run_id
    stats["model"] = args.model
    stats["file"] = args.file
    stats["dry_run"] = args.dry_run
    if not args.dry_run:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        with REPORT.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(stats) + "\n")
    print(json.dumps({k: v for k, v in stats.items() if k != "by_company"}, indent=2))
    log(f"{stats['verified']} of {stats['offered']} offered scores had a quote that is "
        f"in the filing; {stats['unverified']} did not and score nothing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
