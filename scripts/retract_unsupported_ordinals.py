"""Set an ordinal back to UNKNOWN when its evidence does not exist on its cited source.

## The rule this enforces

Master plan, rule 2: *every non-UNKNOWN field backed by a claim passing exact containment on its
cited page.* E90 stamped every object claim with how it actually matched and found **11 answered
ordinals whose only support fails containment**. That is a rule-2 violation by definition, but it
was not acted on immediately, because `overlap_only` has three possible causes and only one of them
is the claim's fault:

1. an IR index page was cited instead of the specific release it links to;
2. the figure came from a PDF or a deck while the cached page is the HTML landing page;
3. the quote was never on that source.

`scripts/relocate_object_claims.py` ran all 11 against the LIVE web through
`relocate.resolve_claims`, which re-fetches the cited url, then follows the links the cited page
itself publishes, and for SEC urls expands the whole accession. Every page came back readable and
every claim came back **`still_absent`** — including three SEC accessions whose 124, 21 and 112
documents were each searched.

So causes 1 and 2 are excluded for these 11. The pages are live, they were read, and the quotes are
not on them or anywhere they link to. Under rule 2 the fields are not supported.

## What it changes, and what it deliberately does not

It sets the FIELD to UNKNOWN. **It does not delete the claim.** The claim stays, stamped
UNVERIFIABLE with its match mode and overlap, because it is the record of what was asserted and
deleting it would erase the evidence that the retraction was warranted. A later pass that finds the
real source can re-point it and re-answer the field.

Cost, measured before running: **10 companies of Phase B eligibility** (only `mortgage_reits` falls
below 2 of 3) and **eight objects from 3 of 3 to 2 of 3**. That is the correct direction. An object
at 3 of 3 on a quote that is not on its page is worse than an object at 2 of 3, because the first
one ships.

A field is only touched when EVERY claim on it is non-certifying. A field with one bad claim and one
good one keeps its answer and keeps the bad claim's stamp.
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, r"C:\Users\<your-user>\company_lab")

from clab.external import research_ingest as RI
from clab.external.schema import INDUSTRY_ORDINALS

ROOT = Path(r"D:\company_lab_data\external\research\industries")


def main(apply: bool = False) -> int:
    if apply:
        backup = ROOT.parent / f"industries_backup_{datetime.now():%Y%m%d-%H%M}"
        if not backup.exists():
            shutil.copytree(ROOT, backup)
            print(f"backup -> {backup}\n")

    retracted, skipped = [], []
    for p in sorted(ROOT.glob("*/industry_state.json")):
        obj = json.loads(p.read_text(encoding="utf-8"))
        claims = obj.get("claims") or []
        hits = []
        for f in INDUSTRY_ORDINALS:
            was = str(obj.get(f) or "UNKNOWN").upper()
            if was == "UNKNOWN":
                continue
            support = [c for c in claims if c.get("field") == f]
            if not support:
                continue                      # no claim at all is a different defect
            if any(c.get("verify_status") == "VERIFIED_LOCAL" for c in support):
                continue
            # EVERY claim must have been TESTED and FAILED. A SELF_ATTESTED claim means the
            # page could not be fetched or read, which is our failure and not evidence of
            # absence - retracting on it would blame the researcher for our network. The
            # first dry run caught `ai_accelerators` exactly this way: its only claim is
            # `unreachable`, and it must keep its answer until the page can be read.
            if not all(c.get("verify_status") == "UNVERIFIABLE" for c in support):
                skipped.append((p.parent.name, f,
                                "not all support was testable - "
                                + ", ".join(sorted({str(c.get("verify_status"))
                                                    for c in support})))) 
                continue
            # Only act where a LIVE relocation has already been tried and failed; a claim
            # still carrying no match_mode has not been tested and must not be retracted
            # on an absence of information.
            if not all(c.get("match_mode") for c in support):
                skipped.append((p.parent.name, f, "never tested - run the stamp first"))
                continue
            hits.append((f, was, [str(c.get("match_mode")) for c in support]))
        if not hits:
            continue
        for f, _was, _modes in hits:
            obj[f] = "UNKNOWN"
        chk = RI.validate_industry(obj)
        bad = chk.get("reasons") or chk.get("claim_reasons")
        answered = [f for f in INDUSTRY_ORDINALS
                    if str(obj.get(f) or "UNKNOWN").upper() != "UNKNOWN"]
        if bad:
            skipped.append((p.parent.name, "-", f"invalid after retraction: {bad}"))
            continue
        retracted.append((p.parent.name, hits, len(answered)))
        if apply:
            p.write_text(json.dumps(obj, indent=1), encoding="utf-8")

    print(f"{'APPLIED' if apply else 'DRY RUN'}  objects {len(retracted)}, "
          f"fields {sum(len(h) for _, h, _ in retracted)}")
    for iid, hits, now in sorted(retracted):
        for f, was, modes in hits:
            print(f"  {iid:34} {f:24} {was:12} -> UNKNOWN   ({', '.join(modes)})")
        print(f"  {'':34} object now at {now}/3")
    for iid, f, why in skipped:
        print(f"  SKIP {iid:34} {f:24} {why}")
    print("\nDRY RUN - nothing written" if not apply else "\nretracted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(apply="--apply" in sys.argv[1:]))
