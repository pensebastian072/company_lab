"""E44 — A/B the V1 and V2 candidate patterns before letting V2 rescore the book.

`CLAUDE.md`: "A/B any change to the correctness core before committing it." The retrieval
patterns decide what evidence every model ever sees, so they are the correctness core of
this lane, and E43 showed what a bad one costs — a pool that can only assert leadership
produced a 53.9% self-contradiction rate in one arm and a 94.8% modal collapse in the
other.

Two parts:

  STATIC (free, no model) — over cached filings, compare V1 and V2 on pool availability and
  on TWO-SIDEDNESS: can the pool surface evidence for opposite ends of the field's own
  scale, or only one? One-sidedness is the defect E43 named, so it is measured directly
  rather than inferred.

  PAIRED (needs the model) — the existing lane rows were scored under V1. Re-scoring the
  same companies with the same model under V2 isolates the pattern set as the only
  variable, so no V1 arm has to be re-run.

    .venv\\Scripts\\python.exe -m clab.research.e44_pattern_ab --static 300
    .venv\\Scripts\\python.exe -m clab.research.e44_pattern_ab --compare <v2_dir>
"""
from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

from .. import config
from ..external import local_phase_b as PB
from ..external import schema as S

LFM_DIR = Path(r"D:\company_lab_data\external\phase_b_lfm25")
OUT = config.JOURNAL_DIR / "experiments" / "E44_results.json"

#: Per field, sentence markers for the two ENDS of its scale. A pool containing only one
#: side cannot argue the other, whatever the model does with it.
POLES: dict[str, tuple[str, str]] = {
    "current_moat_strength": (
        r"barriers? to entry|switching costs?|economies of scale|installed base",
        r"commoditi|compete (?:primarily |largely )?on (?:the basis of )?price|expire"),
    "competitive_position": (
        r"we are (?:the|a|one of)|market leader|we rank",
        r"our competitors (?:are|have)|of our competitors|smaller (?:participant|player)"),
    "competitive_position_trend": (
        r"gain\w* (?:market )?share|grew faster|outpaced|share gains?",
        r"los\w* (?:market )?share|slow(?:ly|er) than|underperformed|declined"),
    "moat_trajectory": (
        r"strengthen|expanded our|widened|invest in our brand",
        r"erosion|eroded|commoditi|narrowed|weakened|expire"),
    "company_specific_capture": (
        r"achieved|realized|realised|delivered|margin expansion|operating leverage",
        r"compression|contraction|declined|inflation"),
    "demand_visibility": (
        r"backlog|order book|take-or-pay|long[- ]term (?:contracts?|agreements?)|recurring",
        r"no (?:material )?backlog|short(?:er)? (?:order|lead)|book[- ]and[- ]ship|spot|seasonal"),
    "pricing_power": (
        r"pric\w* increases?|raise\w* (?:our )?prices|pass\w* (?:on|through)",
        r"pricing pressure|price competition|unable to pass|erosion|discount"),
    "technology_risk": (
        r"technological (?:change|advance|obsolescence)|new technolog|obsolete",
        r"long product life|mature technolog|stable technolog"),
    "disruption_risk": (
        r"disrupt|new entrants?|substitute|alternative",
        r"high barriers?|few new entrants|limited substitutes?"),
    "regulatory_risk": (
        r"consent decree|enforcement action|civil penalt|fined|approval",
        r"not subject to"),
}


def _static(n: int) -> dict:
    import pandas as pd
    book = pd.read_parquet(config.SCORES_PARQUET).to_dict("records")[:n]
    out: dict[str, dict] = {}
    stats = {v: collections.defaultdict(lambda: {"with_pool": 0, "both_poles": 0,
                                                 "one_pole": 0, "cands": 0})
             for v in ("v1", "v2")}
    read = 0
    for r in book:
        t = str(r["ticker"])
        filing = (PB.load_filing(t, r.get("cik"))
                  or PB.load_filing(t, r.get("cik"), form="10-Q"))
        if not filing:
            continue
        read += 1
        for tag, pats in (("v1", PB.FIELD_PATTERNS_V1), ("v2", PB.FIELD_PATTERNS)):
            pools = PB.candidates(filing.text, patterns=pats)
            for field, (hi, lo) in POLES.items():
                pool = pools.get(field) or []
                if not pool:
                    continue
                s = stats[tag][field]
                s["with_pool"] += 1
                s["cands"] += len(pool)
                joined = " ".join(pool)
                has_hi = bool(re.search(hi, joined, re.I))
                has_lo = bool(re.search(lo, joined, re.I))
                if has_hi and has_lo:
                    s["both_poles"] += 1
                elif has_hi or has_lo:
                    s["one_pole"] += 1
    for field in POLES:
        row = {}
        for tag in ("v1", "v2"):
            s = stats[tag][field]
            wp = s["with_pool"]
            row[tag] = {
                "companies_with_pool": wp,
                "mean_candidates": round(s["cands"] / wp, 2) if wp else None,
                "both_poles": s["both_poles"],
                "two_sided_share": round(s["both_poles"] / wp, 4) if wp else None,
            }
        out[field] = row
    return {"filings_read": read, "per_field": out}


def _load(d: Path) -> dict[str, dict]:
    o = {}
    for f in d.glob("*.json"):
        if f.name.startswith("_status"):
            continue
        try:
            o[f.stem] = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
    return o


def _compare(v2_dir: Path) -> dict:
    """Paired V1-vs-V2 on the same companies and the same model."""
    v1, v2 = _load(LFM_DIR), _load(v2_dir)
    both = sorted(set(v1) & set(v2))
    res: dict = {"n_paired": len(both)}
    if not both:
        res["error"] = "no overlap"
        return res
    per: dict[str, dict] = {}
    fields = [f for f in S.COMPANY_ORDINALS
              if f not in ("market_share_direction", "industry_structural_growth")]
    ansc = {"v1": 0, "v2": 0}
    for f in fields:
        e = {}
        for tag, src in (("v1", v1), ("v2", v2)):
            c = collections.Counter()
            for t in both:
                val = str((src[t].get("categoricals") or {}).get(f) or S.UNKNOWN).upper()
                if val != S.UNKNOWN:
                    c[val] += 1
            n = sum(c.values())
            ansc[tag] += n
            e[tag] = {"answered": n, "distinct": len(c),
                      "modal_share": round(max(c.values()) / n, 3) if n else None,
                      "spread": dict(c.most_common())}
        per[f] = e
    res["per_field"] = per
    res["answered_per_company"] = {k: round(v / len(both), 3) for k, v in ansc.items()}
    for tag, src in (("v1", v1), ("v2", v2)):
        contra = tot = 0
        for t in both:
            for c in src[t].get("claims") or []:
                if c["field"] != "competitive_position":
                    continue
                tot += 1
                if PB.contradicts(c["field"], c["value"], c.get("quote") or ""):
                    contra += 1
        res[f"{tag}_competitive_position_contradictions"] = {
            "claims": tot, "contradicted": contra,
            "rate": round(contra / tot, 4) if tot else None}
    modal = {tag: [e[tag]["modal_share"] for e in per.values() if e[tag]["modal_share"]]
             for tag in ("v1", "v2")}
    res["mean_modal_share"] = {k: round(sum(v) / len(v), 4) if v else None
                               for k, v in modal.items()}
    return res


def main(argv: list[str]) -> int:
    res = {}
    if "--static" in argv:
        res["static"] = _static(int(argv[argv.index("--static") + 1]))
        s = res["static"]
        print(f"STATIC over {s['filings_read']} cached filings\n")
        print(f"{'field':28} {'v1 pool':>8} {'v2 pool':>8} {'v1 2-sided':>11} {'v2 2-sided':>11}")
        for f, r in s["per_field"].items():
            print(f"{f:28} {r['v1']['companies_with_pool']:8} {r['v2']['companies_with_pool']:8} "
                  f"{str(r['v1']['two_sided_share']):>11} {str(r['v2']['two_sided_share']):>11}")
    if "--compare" in argv:
        res["compare"] = _compare(Path(argv[argv.index("--compare") + 1]))
        c = res["compare"]
        print(f"\nPAIRED on {c['n_paired']} companies, same model, patterns the only change")
        print("answered/company:", c["answered_per_company"])
        print("mean modal share:", c["mean_modal_share"], "(lower = more discriminating)")
        for tag in ("v1", "v2"):
            print(f"{tag} competitive_position contradictions:",
                  c[f"{tag}_competitive_position_contradictions"])
        print(f"\n{'field':28} {'v1 ans':>7} {'v2 ans':>7} {'v1 modal':>9} {'v2 modal':>9}")
        for f, e in c["per_field"].items():
            print(f"{f:28} {e['v1']['answered']:7} {e['v2']['answered']:7} "
                  f"{str(e['v1']['modal_share']):>9} {str(e['v2']['modal_share']):>9}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    prev = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    prev.update(res)
    OUT.write_text(json.dumps(prev, indent=1), encoding="utf-8")
    print(f"\nwritten to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
