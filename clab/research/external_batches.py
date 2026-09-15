"""Hand the companies our own model could not read to a bigger model, ten at a time.

423 companies score few or no moat dimensions, and 154 of them sit at three or fewer.
Every one has a 10-K on file; the local `qwen2.5:7b` simply declines - it is asked to
quote from an eight-chunk retrieval window and will not answer without a quotable basis.
A frontier model with the whole filing in front of it is not subject to that constraint.

This writes paste-ready batches: the companies, what is missing for each, and a prompt
that pins the output to the same schema, the same 0-5 integers, and the same rule that a
score without a verbatim quote is worthless.

    python -m clab.research.external_batches --batches 5
    python -m clab.research.external_batches --batch-size 10 --max-dimensions 3

The answers come back through `clab.runner.ingest_external`, which verifies every quote
against the FILING TEXT on disk before it is allowed near a score.
"""
from __future__ import annotations

import argparse
import json

from .. import config
from ..net import log_stamp
from ..runner import engine
from ..scoring import rubric
from ..scoring.repair_merge import merged_items

OUT_DIR = config.JOURNAL_DIR / "external"
DIM_LABELS = dict(rubric.BQ_DIMENSIONS)


def log(msg: str) -> None:
    print(f"[{log_stamp()}] {msg}", flush=True)


def _missing(cik: str) -> list[str]:
    payload = (engine.load_qual(cik) or {}).get("BQ") or {}
    dims = merged_items(payload, "dimensions")
    return [k for k, _lbl in rubric.BQ_DIMENSIONS
            if not isinstance(dims.get(k), dict) or dims[k].get("score") is None]


def candidates(max_dimensions: int) -> list[dict]:
    """Companies with at most `max_dimensions` moat dimensions scored, worst first."""
    import pandas as pd
    df = pd.read_parquet(config.SCORES_PARQUET)
    df = df[df["ticker"].notna()].copy()
    df["cik"] = df["cik"].astype(str).str.zfill(10)
    rows = []
    for _i, r in df.iterrows():
        missing = _missing(r["cik"])
        scored = len(rubric.BQ_DIMENSIONS) - len(missing)
        if scored > max_dimensions:
            continue
        rows.append({
            "ticker": r["ticker"], "cik": r["cik"], "name": r.get("name") or "",
            "sector": r.get("sector") or "", "sub_industry": r.get("sub_industry") or "",
            "coverage": round(float(r.get("coverage") or 0), 3),
            "dimensions_scored": scored, "missing": missing,
        })
    rows.sort(key=lambda x: (x["dimensions_scored"], -x["coverage"]))
    return rows


PROMPT = """You are scoring the competitive moat of {n} US-listed companies from their
most recent SEC 10-K annual report.

For EACH company below, score ONLY the dimensions listed for it. Rules, all of which
matter more than completeness:

1. Every score is an INTEGER from 0 to 5. 0 = a commodity business that a well-funded
   competitor could replicate; 5 = displacing it would be exceptionally difficult.
2. "evidence" MUST be a VERBATIM quote copied from that company's own 10-K - not from a
   press release, not from your general knowledge, not paraphrased. Copy the words
   exactly, 10-40 words.
3. If the 10-K does not support a dimension, return "score": null. A null is a correct
   answer. An invented quote is not, and every quote is checked against the filing text
   before the score is used - a quote that is not found there is DISCARDED along with its
   score.
4. If a dimension does not apply to the business at all - manufacturing complexity for a
   REIT, network effects for a utility - return "score": null and set
   "not_applicable": true. That is different from "the filing does not say".
5. "rationale" is one sentence in your own words, under 200 characters.

Respond with ONE JSON object and nothing else. No markdown fences, no commentary:

{{"companies": [
  {{"ticker": "XYZ",
    "dimensions": {{
      "economies_of_scale": {{"score": 3, "not_applicable": false,
        "rationale": "...", "evidence": "verbatim quote from the 10-K"}}
    }}
  }}
]}}

THE COMPANIES
{companies}
"""


def render_batch(rows: list[dict], index: int) -> str:
    lines = []
    for r in rows:
        dims = "\n".join(f"      - {k}: {DIM_LABELS[k]}" for k in r["missing"])
        lines.append(
            f"  {r['ticker']} - {r['name']}\n"
            f"    CIK {r['cik']} | {r['sector']} / {r['sub_industry']}\n"
            f"    score these dimensions:\n{dims}")
    body = PROMPT.format(n=len(rows), companies="\n\n".join(lines))
    header = (f"# External review batch {index:03d}\n\n"
              f"{len(rows)} companies our local model could not read. Paste everything "
              f"below the line into Gemini, then save its JSON reply as\n"
              f"`journal/external/batch_{index:03d}_reply.json` and run:\n\n"
              f"    .venv\\Scripts\\python.exe -m clab.runner.ingest_external "
              f"--file journal/external/batch_{index:03d}_reply.json\n\n"
              f"Every quote is checked against the filing text on disk before it can "
              f"touch a score.\n\n---\n\n")
    return header + body


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--batch-size", type=int, default=10)
    ap.add_argument("--batches", type=int, default=5,
                    help="how many batch files to write this run")
    ap.add_argument("--max-dimensions", type=int, default=3,
                    help="only companies with at most this many dimensions scored")
    args = ap.parse_args(argv)

    rows = candidates(args.max_dimensions)
    log(f"{len(rows)} companies with <= {args.max_dimensions} dimensions scored")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for i in range(args.batches):
        chunk = rows[i * args.batch_size:(i + 1) * args.batch_size]
        if not chunk:
            break
        path = OUT_DIR / f"batch_{i + 1:03d}.md"
        path.write_text(render_batch(chunk, i + 1), encoding="utf-8")
        written.append(path)
        log(f"  {path.name}: {', '.join(c['ticker'] for c in chunk)}")
    index = OUT_DIR / "index.json"
    index.write_text(json.dumps(
        {"total_candidates": len(rows), "batch_size": args.batch_size,
         "batches_written": [p.name for p in written],
         "companies": rows}, indent=2), encoding="utf-8")
    log(f"index: {index}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
