"""Merge hand-judged E79B claims into the E79 Phase A artifacts.

Writes ONLY the on-disk research artifacts under
`D:\\company_lab_data\\external\\research\\industries`. It never touches the DuckDB store,
never scores, and never promotes - applying to the store stays a separate, explicit step.

Every claim is re-fetched and re-verified here rather than trusted from the staging file,
and the `excerpt` is cut from the FETCHED page around the quote, so an excerpt can never be
a hand-written frame around a quote that is not really there. A claim that fails
verification is skipped and reported, not downgraded quietly.

Originals are copied to `industries_backup_<stamp>` before the first write.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, r"C:\Users\<your-user>\company_lab")

from clab import net
from clab.external import research_ingest as RI
from clab.external import verify as V
from clab.external.schema import INDUSTRY_ORDINALS

ROOT = Path(r"D:\company_lab_data\external\research\industries")
#: Default staging file. Any pass hands in its own with `--stage <path>`, so every pass
#: goes through THIS merge - the excerpt-cut-from-the-fetched-page rule and the artifact
#: backup cannot be bypassed by writing a second merge script.
STAGE = Path(r"D:\company_lab_data\external\reports\E79B_pass1_claims.json")
EXCERPT_PAD = 420


def excerpt_for(quote: str, page: str) -> str | None:
    """A real window from the fetched page, containing the quote verbatim."""
    norm_p = re.sub(r"\s+", " ", page)
    norm_q = re.sub(r"\s+", " ", quote).strip()
    # Case-INSENSITIVE, because that is what verify.check_quote does. A case-sensitive
    # search here rejected two claims that had already verified at overlap 1.0, which
    # would have silently dropped real evidence.
    i = norm_p.lower().find(norm_q.lower())
    if i < 0:
        return None
    s, e = max(0, i - EXCERPT_PAD), min(len(norm_p), i + len(norm_q) + EXCERPT_PAD)
    return norm_p[s:e]


def main(apply: bool = False, stage: Path | None = None) -> int:
    stage = stage or STAGE
    doc = json.loads(stage.read_text(encoding="utf-8"))
    claims = [c for c in doc["claims"] if c.get("verify_status") == "VERIFIED_LOCAL"]
    pages: dict[str, str] = {}
    merged: dict[str, list[dict]] = {}
    skipped: list[tuple[str, str, str]] = []

    for c in claims:
        url = c["source_url"]
        if url not in pages:
            try:
                pages[url] = V._extract_fetched(net.http_get(url), url)[0]
            except Exception as exc:                      # loud, never silent
                pages[url] = ""
                print(f"FETCH FAIL {type(exc).__name__} {url}")
        ex = excerpt_for(c["quote"], pages[url]) if pages[url] else None
        if not ex:
            skipped.append((c["industry_id"], c["field"], "quote not found in fetched page"))
            continue
        cid = "c_" + hashlib.sha1(
            f"E79B|{c['industry_id']}|{c['field']}|{url}|{c['quote']}".encode()).hexdigest()[:12]
        merged.setdefault(c["industry_id"], []).append({
            "claim_id": cid, "field": c["field"], "text": c["text"],
            "source_url": url, "source_title": c["source_title"],
            "source_date": c["source_date"], "source_type": c["source_type"],
            "independence_domain": c["independence_domain"],
            "stance": c["stance"], "fact_or_inference": c["fact_or_inference"],
            "quote": c["quote"], "excerpt": ex,
            "_value": c["value"], "_pass": "E79B",
        })

    if apply:
        stamp = datetime.now().strftime("%Y%m%d-%H%M")
        backup = ROOT.parent / f"industries_backup_{stamp}"
        if not backup.exists():
            shutil.copytree(ROOT, backup)
            print(f"backup -> {backup}")

    report = []
    for iid, new in sorted(merged.items()):
        p = ROOT / iid / "industry_state.json"
        obj = json.loads(p.read_text(encoding="utf-8"))
        have = {c.get("claim_id") for c in (obj.get("claims") or [])}
        fresh = [c for c in new if c["claim_id"] not in have]
        for c in fresh:
            if c["field"] in INDUSTRY_ORDINALS:
                obj[c["field"]] = c["_value"]
        obj["claims"] = (obj.get("claims") or []) + [
            {k: v for k, v in c.items() if not k.startswith("_")} for c in fresh]
        answered = [f for f in INDUSTRY_ORDINALS
                    if str(obj.get(f) or "UNKNOWN").upper() != "UNKNOWN"]
        res = RI.validate_industry(obj)
        bad = res.get("reasons") or res.get("claim_reasons") or ([] if res.get("ok") else ["not ok"])
        report.append((iid, len(fresh), len(answered), bad))
        if apply and not bad:
            p.write_text(json.dumps(obj, indent=1), encoding="utf-8")

    print(f"\n{'APPLIED' if apply else 'DRY RUN'}  objects touched: {len(report)}")
    for iid, n, ans, bad in report:
        flag = "OK" if not bad else f"INVALID: {bad}"
        print(f"  {iid:40} +{n} claims  ordinals {ans}/3  {flag}")
    for s in skipped:
        print(f"  SKIPPED {s}")
    return 0


if __name__ == "__main__":
    _argv = sys.argv[1:]
    _stage = Path(_argv[_argv.index("--stage") + 1]) if "--stage" in _argv else None
    raise SystemExit(main(apply="--apply" in _argv, stage=_stage))
