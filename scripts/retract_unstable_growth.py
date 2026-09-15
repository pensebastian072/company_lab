"""Remove a computed `structural_growth` whose band depends on the window that measured it.

Written 2026-09-12 to undo this module's own work from the same morning. Three of the five
units filled from the one-year revenue window read a different band at three years:

    hotels_resorts_cruise_lines   1y +4.2% MODERATE    3y +6.8% HIGH
    automotive_parts_equipment    1y -0.1% FLAT        3y -3.0% DECLINING
    leisure_products              1y -0.4% FLAT        3y -7.6% DECLINING

An ordinal that changes when the window changes is a property of the window. Those three
are retracted: the field goes back to UNKNOWN and the computed claim is removed, which drops
42 companies out of Phase B eligibility. That is the correct direction - they were never
eligible on evidence that survives its own stability test.

## What it will and will not touch

It removes ONLY a claim whose `source_url` is the CPI release AND whose `text` begins with
the "COMPUTED, NOT PUBLISHED." marker this module writes. A researched claim is never
removed, and a field whose current value did not come from a computed claim is never reset -
so running this twice, or running it over a unit that was later researched properly, does
nothing. The backup is taken before any write, as everywhere else in this tree.
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, r"C:\Users\<your-user>\company_lab")

from clab.external import research_ingest as RI

ROOT = Path(r"D:\company_lab_data\external\research\industries")
MARKER = "COMPUTED, NOT PUBLISHED."
CPI_HOST = "bls.gov"


def _is_computed_growth(c: dict) -> bool:
    return (c.get("field") == "structural_growth"
            and CPI_HOST in str(c.get("source_url") or "")
            and str(c.get("text") or "").startswith(MARKER))


def main(units: list[str], apply: bool = False) -> int:
    if apply:
        stamp = datetime.now().strftime("%Y%m%d-%H%M")
        backup = ROOT.parent / f"industries_backup_{stamp}"
        if not backup.exists():
            shutil.copytree(ROOT, backup)
            print(f"backup -> {backup}\n")

    for iid in units:
        p = ROOT / iid / "industry_state.json"
        if not p.exists():
            print(f"  MISSING {iid}")
            continue
        obj = json.loads(p.read_text(encoding="utf-8"))
        claims = obj.get("claims") or []
        drop = [c for c in claims if _is_computed_growth(c)]
        if not drop:
            print(f"  SKIP    {iid:36} no computed growth claim to remove "
                  f"(growth is {obj.get('structural_growth')})")
            continue
        obj["claims"] = [c for c in claims if not _is_computed_growth(c)]
        obj["structural_growth"] = "UNKNOWN"
        chk = RI.validate_industry(obj)
        bad = chk.get("reasons") or chk.get("claim_reasons")
        answered = [f for f in ("structural_growth", "replication_difficulty",
                                "substitution_risk")
                    if str(obj.get(f) or "UNKNOWN").upper() != "UNKNOWN"]
        print(f"  RETRACT {iid:36} -{len(drop)} claim(s), growth -> UNKNOWN, "
              f"ordinals {len(answered)}/3  {'OK' if not bad else bad}")
        if apply and not bad:
            p.write_text(json.dumps(obj, indent=1), encoding="utf-8")
    print("\nDRY RUN - nothing written" if not apply else "\nretracted")
    return 0


if __name__ == "__main__":
    _argv = sys.argv[1:]
    if "--units" not in _argv:
        raise SystemExit("--units <a,b,c> is required")
    raise SystemExit(main(_argv[_argv.index("--units") + 1].split(","),
                          apply="--apply" in _argv))
