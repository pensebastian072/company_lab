"""E43 — does the candidate POOL decide the answer, upstream of either model?

E42 asked which model reads better and found each one dead on different fields. E43 asks
the question underneath it, which turns out to matter more: **are the candidate sentences
evidence for the field at all?**

`candidates()` selects by regex. Three of the patterns select text that cannot support
their field:

  current_moat_strength  matches bare `patent|proprietary|trade secret`, which in a 10-K
                         live overwhelmingly in LITIGATION and risk sections
  regulatory_risk        matches "subject to extensive regulation", the exact boilerplate
                         `prompt_for` tells the model to ignore
  competitive_position   matches ONLY self-assertions of leadership, so the pool cannot
                         contain evidence that a company is anything but a leader

The last one is the useful one, because a pool that can only say one thing makes a
misattribution **checkable without ground truth**: if every sentence offered asserts
leadership, a claim of LAGGARD is contradicted by its own citation.

    .venv\\Scripts\\python.exe -m clab.research.e43_pool_decides
"""
from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

from .. import config

QWEN_DIR = Path(r"D:\company_lab_data\external\phase_b_local")
LFM_DIR = Path(r"D:\company_lab_data\external\phase_b_lfm25")
OUT = config.JOURNAL_DIR / "experiments" / "E43_results.json"

#: The filer asserting its OWN leadership. Deliberately narrower than the pool pattern:
#: "products from leading suppliers" and "acquired Traverse Systems, an industry-leading
#: ..." are leadership claims about OTHER companies and are evidence of nothing about the
#: filer, so they are counted separately rather than scored as contradictions.
SELF_LEADER = re.compile(
    r"\b(?:we are|we're|the company is|we remain|we have been)\s+"
    r"(?:the\s+|a\s+|one of\s+(?:the\s+)?)?"
    r"(?:world'?s\s+|nation'?s\s+|global\s+|leading\s+|largest\s+|premier\s+|top\s+|"
    r"market[- ]leading\s+|number one\s+|second[- ]largest\s+)",
    re.I)
OTHER_LEADER = re.compile(
    r"\b(?:from|with|by|of)\s+(?:the\s+)?(?:world'?s\s+)?leading\b|"
    r"\ban industry[- ]leading\b|\bleading (?:suppliers|vendors|customers|partners)\b",
    re.I)

#: Values that AGREE with a sentence in which the filer calls itself a leader.
CONSISTENT = {"DOMINANT", "LEADER", "STRONG_NUMBER_TWO"}
#: Values CONTRADICTED by such a sentence.
CONTRADICTED = {"CHALLENGER", "LAGGARD", "NICHE", "WEAK"}


def _rows(d: Path) -> list[dict]:
    out = []
    for f in d.glob("*.json"):
        if f.name.startswith("_status"):
            continue
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    return out


def _audit_competitive_position(rows: list[dict]) -> dict:
    """Contradiction rate on the one field where the pool makes truth checkable."""
    self_lead = other_lead = neither = 0
    contra = consistent = unscored = 0
    examples: list[dict] = []
    for r in rows:
        for c in r.get("claims") or []:
            if c["field"] != "competitive_position":
                continue
            q = c.get("quote") or ""
            v = str(c.get("value") or "").upper()
            if SELF_LEADER.search(q) and not OTHER_LEADER.search(q):
                self_lead += 1
                if v in CONTRADICTED:
                    contra += 1
                    if len(examples) < 8:
                        examples.append({"ticker": c["ticker"], "value": v,
                                         "quote": q[:200]})
                elif v in CONSISTENT:
                    consistent += 1
                else:
                    unscored += 1
            elif OTHER_LEADER.search(q):
                other_lead += 1
            else:
                neither += 1
    checkable = self_lead
    return {
        "claims_total": self_lead + other_lead + neither,
        "quote_asserts_OWN_leadership": self_lead,
        "quote_asserts_SOMEONE_ELSES_leadership": other_lead,
        "quote_asserts_no_leadership": neither,
        "of_checkable_consistent": consistent,
        "of_checkable_contradicted": contra,
        "of_checkable_unscored_value": unscored,
        "contradiction_rate": round(contra / checkable, 4) if checkable else None,
        "examples_contradicted": examples,
    }


def _pool_relevance(rows: list[dict]) -> dict:
    """How often a cited sentence sits in a risk/litigation frame rather than a factual one.

    A crude but honest proxy: `_is_hypothetical` already strips conditional sentences, so
    what is left is declarative. These markers catch the declarative-but-about-litigation
    case that the hypothetical filter does not - "we have faced patent claims" is a
    statement of fact and is still not evidence of a moat.
    """
    litig = re.compile(
        r"\b(?:lawsuit|litigation|claims? (?:relating|against|alleging)|infring|"
        r"defendant|settlement|court|patent claims|allegation)", re.I)
    out: dict[str, dict] = {}
    for field in ("current_moat_strength", "moat_trajectory", "regulatory_risk",
                  "competitive_position", "technology_risk", "pricing_power"):
        n = hit = 0
        for r in rows:
            for c in r.get("claims") or []:
                if c["field"] != field:
                    continue
                n += 1
                if litig.search(c.get("quote") or ""):
                    hit += 1
        out[field] = {"claims": n, "litigation_framed": hit,
                      "share": round(hit / n, 4) if n else None}
    return out


def compute() -> dict:
    res: dict = {}
    for name, d in (("qwen", QWEN_DIR), ("lfm", LFM_DIR)):
        rows = _rows(d)
        res[name] = {
            "n_rows": len(rows),
            "competitive_position": _audit_competitive_position(rows),
            "litigation_framed_quotes": _pool_relevance(rows),
        }
    return res


def main(argv: list[str]) -> int:
    res = compute()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    for arm in ("qwen", "lfm"):
        a = res[arm]
        cp = a["competitive_position"]
        print(f"\n=== {arm}  ({a['n_rows']} rows)")
        print(f"  competitive_position claims: {cp['claims_total']}")
        print(f"    quote asserts OWN leadership      : {cp['quote_asserts_OWN_leadership']}")
        print(f"    quote asserts SOMEONE ELSE'S      : {cp['quote_asserts_SOMEONE_ELSES_leadership']}")
        print(f"    quote asserts no leadership       : {cp['quote_asserts_no_leadership']}")
        print(f"    of the checkable ones: consistent={cp['of_checkable_consistent']} "
              f"CONTRADICTED={cp['of_checkable_contradicted']}")
        print(f"    CONTRADICTION RATE = {cp['contradiction_rate']}")
        print("  litigation-framed quotes by field:")
        for f, v in a["litigation_framed_quotes"].items():
            print(f"    {f:26} {v['litigation_framed']:4} of {v['claims']:4}  = {v['share']}")
    print(f"\nwritten to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
