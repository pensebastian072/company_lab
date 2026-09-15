"""Run the acceptance gate over EVERY industry object on disk, and say what it refuses.

`acceptance.main` only has a `--payload` mode, which is Phase B. The Phase A half -
`accept_objects` - has never been run over the whole corpus, so the rules it enforces have
been checked object by object as each batch landed and never totalled. This totals them.

Read-only. It writes nothing, ingests nothing, and does not fetch by default: with
`fetch=False` the containment check SKIPs rather than passing, which is the honest reading of
a check that did not run. What it does exercise is the set of rules that need no network:

    structural_ordinals   does the object conclude anything (0 of 3 is a FAIL)
    split_unit_evidence   a NEW unit in a populated sector must carry an ordinal claim
    source_diversity      the plan's rule 3 - at least one non-issuer source

Add `--fetch` to test every citation as well; that is ~200 objects' worth of sources and is
not the default for that reason.
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\<your-user>\company_lab")

from clab.external import acceptance as A
from clab.external import research_ingest as RI
from clab.external import schema as S

ROOT = Path(r"D:\company_lab_data\external\research\industries")


def main(fetch: bool = False) -> int:
    results = []
    for p in sorted(ROOT.glob("*/industry_state.json")):
        obj = json.loads(p.read_text(encoding="utf-8"))
        res = RI.validate_industry(obj)
        results.append({"industry_id": obj.get("industry_id") or p.parent.name,
                        "ok": res.get("ok"), "reasons": res.get("reasons") or [],
                        "claim_reasons": res.get("claim_reasons") or {},
                        "evidence": res.get("evidence"), "_obj": obj})
    print(f"objects on disk: {len(results)}\n")

    invalid = {r["industry_id"]: (r["reasons"], r["claim_reasons"])
               for r in results if not r["ok"]}
    if invalid:
        print(f"SCHEMA INVALID: {len(invalid)} object(s)")
        for iid, (reasons, claim_reasons) in sorted(invalid.items()):
            print(f"  {iid:40} {reasons or ''} {list(claim_reasons)[:3] or ''}")
        print()

    report = A.Report(f"phase A: {len(results)} objects on disk")
    A.check_objects(report, results, fetch=fetch)
    for c in report.checks:
        print(f"[{c.verdict}] {c.name}")
        for line in str(c.detail).split(". "):
            if line.strip():
                print(f"        {line.strip()}")
    print(f"\nexit code would be: {report.exit_code}")

    # The ordinal distribution, which no single check reports but which is the number the
    # plan is actually steered by.
    dist = collections.Counter()
    for r in results:
        obj = r["_obj"]
        dist[len([f for f in S.INDUSTRY_ORDINALS
                  if str(obj.get(f) or "UNKNOWN").upper() != "UNKNOWN"])] += 1
    print("\nordinals answered, objects per level: "
          + ", ".join(f"{k}/3 -> {dist[k]}" for k in sorted(dist)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(fetch="--fetch" in sys.argv[1:]))
