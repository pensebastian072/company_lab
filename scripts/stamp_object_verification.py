"""Stamp each industry object's claims with how its own citation actually matched.

## The gap this closes

Measured 2026-09-12: all **712** claims in the 208 object files carry the same twelve keys,
and none of them is `verify_status` or `match_mode`. **An object file cannot tell you whether
its own citations hold.** The DuckDB store records verification per claim and the corpus-wide
restate earlier today demoted what needed demoting there — but the object files are the Phase A
artifacts, they are what `e79b_merge` reads and writes, and they had never been stamped.

The cost of that is concrete. `retirement_benefits` still carries:

> Total US retirement assets were $49.1 trillion as of December 31, 2025, up 2.1 percent from
> September and up 11.2 percent for the year.

against an ICI page that now says $47.6T and −2.5%. That exact claim is the cautionary example
written into `verify.match_quote`'s own docstring, and it was still sitting in the live artifact
with nothing on it to say so, because there was no field to say it in.

## What it writes

Three keys per quoted claim, from `verify.match_quote` — the repo's matcher, not a stricter
one of this script's own:

    match_mode      exact | no_whitespace | overlap_only | numeric_mismatch | absent
    overlap         the token overlap, for the non-certifying modes
    verify_status   VERIFIED_LOCAL   when the mode is one of the two CERTIFYING modes
                    UNVERIFIABLE     when it is not - the quote is not on the page
                    SELF_ATTESTED    when the page could not be fetched or read at all

The third distinction is the one that matters: **our failure to reach a page is not the
claim's fault**, and recording it as UNVERIFIABLE would blame the batch for our network. That
is the same rule `acceptance.check_containment` follows when it counts unreachable pages
outside the rate entirely.

Ordinals are NOT touched. A claim whose citation no longer holds does not silently un-answer
its field — that is a judgement about the industry, and this script only records the state of
the evidence. What it does is make the next audit free and the next reader honest.

Run `scripts/audit_objects.py --fetch` for the corpus rate; run this to put the answer in the
artifacts. Backs up the whole tree before the first write, like everything else here.
"""
from __future__ import annotations

import collections
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, r"C:\Users\<your-user>\company_lab")

from clab.external import research_ingest as RI
from clab.external import verify as V

ROOT = Path(r"D:\company_lab_data\external\research\industries")


def main(apply: bool = False) -> int:
    pages: dict[str, V.Fetched] = {}
    modes = collections.Counter()
    statuses = collections.Counter()
    changed: list[tuple[str, int]] = []
    invalid: list[tuple[str, object]] = []

    objects = sorted(ROOT.glob("*/industry_state.json"))
    if apply:
        backup = ROOT.parent / f"industries_backup_{datetime.now():%Y%m%d-%H%M}"
        if not backup.exists():
            shutil.copytree(ROOT, backup)
            print(f"backup -> {backup}\n")

    for p in objects:
        obj = json.loads(p.read_text(encoding="utf-8"))
        n = 0
        for c in obj.get("claims") or []:
            quote, url = c.get("quote"), c.get("source_url")
            if not (quote and url):
                continue
            if url not in pages:
                pages[url] = V.fetch(url)
            page = pages[url]
            if (not page.ok or page.unverifiable_reason
                    or len(page.text) < V.MIN_PAGE_CHARS):
                status, mode, overlap = "SELF_ATTESTED", "unreachable", None
            else:
                m = V.match_quote(quote, page.text)
                mode, overlap = m.mode, m.overlap
                status = ("VERIFIED_LOCAL" if mode in V.CERTIFYING_MATCH_MODES
                          else "UNVERIFIABLE")
            modes[mode] += 1
            statuses[status] += 1
            if (c.get("verify_status"), c.get("match_mode")) != (status, mode):
                n += 1
            c["verify_status"], c["match_mode"], c["overlap"] = status, mode, overlap
        if not n:
            continue
        chk = RI.validate_industry(obj)
        bad = chk.get("reasons") or chk.get("claim_reasons")
        if bad:
            invalid.append((p.parent.name, bad))
            continue
        changed.append((p.parent.name, n))
        if apply:
            p.write_text(json.dumps(obj, indent=1), encoding="utf-8")

    total = sum(modes.values())
    certified = sum(v for k, v in modes.items() if k in V.CERTIFYING_MATCH_MODES)
    checkable = total - modes.get("unreachable", 0)
    print(f"{'APPLIED' if apply else 'DRY RUN'}  "
          f"objects touched {len(changed)} of {len(objects)}, claims stamped {total}")
    print(f"  match modes : {dict(modes)}")
    print(f"  statuses    : {dict(statuses)}")
    if checkable:
        print(f"  certified   : {certified}/{checkable} = {certified / checkable:.1%} "
              f"(unreachable {modes.get('unreachable', 0)} excluded, as the gate does)")
    if invalid:
        print(f"\n  NOT WRITTEN, schema invalid after stamping: {len(invalid)}")
        for iid, bad in invalid:
            print(f"    {iid:40} {bad}")
    print("\nDRY RUN - nothing written" if not apply else "\nstamped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(apply="--apply" in sys.argv[1:]))
