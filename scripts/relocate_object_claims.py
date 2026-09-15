"""Settle the object files' unverifiable citations against the LIVE web.

## Why this exists next to relocate.py rather than inside it

`clab/external/relocate.py` is store-oriented: `load_unlocatable` reads the DuckDB catalog and
`apply_resolutions` writes back to it. The claims E90 found are in the **object files**, and some
of them were never ingested, so they are not in the store to be loaded or written.

What is reused is the part that matters — `relocate.resolve_claims`, which holds the discipline:

* it re-fetches the CITED url live, because a page that changed after we cached it is
  indistinguishable from a bad citation when you only look at the cache;
* if the quote is not there, it reads the links the cited page itself publishes and tries the
  closest ones, on the cited page's own host;
* **it never assembles a URL.** Guessing `.../q2-2026-results` from a quote about the second
  quarter would manufacture a source, and a manufactured source that happens to contain the
  words is the worst possible outcome;
* unreachable means SELF_ATTESTED, not UNVERIFIABLE - our failure is not the claim's fault.

This script is the thin part: select the object claims worth settling, hand them over, and write
the outcome back into the artifacts.

## What it writes, and what it refuses to write

On a relocation it updates `source_url` to the page that actually carries the quote, and stamps
`verify_status` / `match_mode` / `overlap` from the match there. On a demotion it stamps
UNVERIFIABLE and leaves the url alone, because the citation as given is the record of what was
claimed.

**It never changes an ordinal.** A demoted claim can leave a field with no surviving evidence -
E90 counted 11 of those - and whether to withdraw the conclusion is a judgement about the
industry, not a consequence of a fetch. The script reports which fields are left stranded and
stops there.

`--all` settles every UNVERIFIABLE claim in the tree; the default is the narrower and more useful
set: only those that are the **sole** support for an answered ordinal.
"""
from __future__ import annotations

import collections
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, r"C:\Users\<your-user>\company_lab")

from clab.external import relocate as R
from clab.external import research_ingest as RI
from clab.external import verify as V
from clab.external.schema import INDUSTRY_ORDINALS

ROOT = Path(r"D:\company_lab_data\external\research\industries")


def _load(only_stranded: bool) -> tuple[list[dict], dict[str, tuple[Path, dict]]]:
    """Claims to settle, plus an index from claim_id back to its file and object."""
    claims: list[dict] = []
    index: dict[str, tuple[Path, dict]] = {}
    for p in sorted(ROOT.glob("*/industry_state.json")):
        obj = json.loads(p.read_text(encoding="utf-8"))
        all_claims = obj.get("claims") or []
        # Which answered ordinals have NO certifying claim left - the stranded set.
        stranded = set()
        for f in INDUSTRY_ORDINALS:
            if str(obj.get(f) or "UNKNOWN").upper() == "UNKNOWN":
                continue
            support = [c for c in all_claims if c.get("field") == f]
            if support and not any(c.get("verify_status") == "VERIFIED_LOCAL"
                                   for c in support):
                stranded.add(f)
        for c in all_claims:
            if c.get("verify_status") != "UNVERIFIABLE":
                continue
            if only_stranded and c.get("field") not in stranded:
                continue
            if not (c.get("quote") and c.get("source_url")):
                continue
            claims.append(c)
            index[c["claim_id"]] = (p, obj)
    return claims, index


def main(apply: bool = False, only_stranded: bool = True) -> int:
    claims, index = _load(only_stranded)
    if not claims:
        print("nothing to settle")
        return 0
    scope = "sole support for an answered ordinal" if only_stranded else "every UNVERIFIABLE"
    print(f"{len(claims)} claim(s) to settle ({scope}), "
          f"{len({c['source_url'] for c in claims})} distinct url(s)\n")

    resolutions = R.resolve_claims(claims)
    by_id = {r.claim_id: r for r in resolutions}
    outcomes = collections.Counter(r.outcome for r in resolutions)
    print(f"\noutcomes: {dict(outcomes)}")

    if apply:
        backup = ROOT.parent / f"industries_backup_{datetime.now():%Y%m%d-%H%M}"
        if not backup.exists():
            shutil.copytree(ROOT, backup)
            print(f"backup -> {backup}")

    touched: dict[Path, dict] = {}
    for c in claims:
        r = by_id.get(c["claim_id"])
        if not r:
            continue
        p, obj = index[c["claim_id"]]
        if r.url_now and r.url_now != r.url_was:
            c["source_url"] = r.url_now
            c["relocated_from"] = r.url_was
        c["verify_status"] = r.status
        if r.mode:
            c["match_mode"] = r.mode
        if r.overlap is not None:
            c["overlap"] = r.overlap
        touched[p] = obj

    print(f"\nper claim:")
    for c in claims:
        r = by_id.get(c["claim_id"])
        if not r:
            continue
        moved = f"  ->  {str(r.url_now)[:70]}" if r.url_now and r.url_now != r.url_was else ""
        print(f"  {c.get('field'):24} {r.outcome:16} {r.status:15} "
              f"{str(r.mode or '-'):16}{moved}")

    written = 0
    for p, obj in sorted(touched.items()):
        chk = RI.validate_industry(obj)
        bad = chk.get("reasons") or chk.get("claim_reasons")
        if bad:
            print(f"  NOT WRITTEN (invalid) {p.parent.name}: {bad}")
            continue
        if apply:
            p.write_text(json.dumps(obj, indent=1), encoding="utf-8")
        written += 1

    # Re-report the stranded set from the post-resolution state, so the caller learns
    # whether anything was actually rescued rather than just what was tried.
    still = []
    for p, obj in sorted(touched.items()):
        for f in INDUSTRY_ORDINALS:
            if str(obj.get(f) or "UNKNOWN").upper() == "UNKNOWN":
                continue
            support = [c for c in (obj.get("claims") or []) if c.get("field") == f]
            if support and not any(c.get("verify_status") == "VERIFIED_LOCAL"
                                   for c in support):
                still.append((p.parent.name, f, str(obj.get(f))))
    print(f"\nobjects {'written' if apply else 'would be written'}: {written}")
    print(f"answered ordinals STILL with no certifying evidence: {len(still)}")
    for iid, f, v in still:
        print(f"  {iid:34} {f:24} = {v}")
    print("\nDRY RUN - nothing written" if not apply else "\napplied")
    return 0


if __name__ == "__main__":
    _argv = sys.argv[1:]
    raise SystemExit(main(apply="--apply" in _argv, only_stranded="--all" not in _argv))
