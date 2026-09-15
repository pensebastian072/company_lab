"""E30 - does every sub-test do any work, in every sector?

A per-(sub-test x sector) audit of all 94 points, not just the judged half. It answers
four questions that a coverage figure cannot:

  1. **Is it answered?** status mix - scored / no_data / not_applicable / quality_fail.
  2. **Does it DISCRIMINATE?** A sub-test where 98% of a sector earns the same number is
     a weight with no information in it. It cannot separate two companies, but it still
     moves the composite and still sits in the coverage denominator looking like
     evidence. This is the failure mode the market-state workbook hit - 6 of 12 layers
     constant, so a "12-layer confluence tally" was really a 6-layer tally plus an
     offset.
  3. **Is a suppression DEAD?** A profile that nominates a sub-test for NOT_APPLICABLE
     which then scores for everyone is a rule that never fires - harmless, but it means
     the profile is not doing what its note claims.
  4. **Is a suppression MISSING?** A sub-test that is NO_DATA for nearly a whole sector
     and is NOT nominated is charging that sector for an absence.

Nothing here changes a score. It produces the list a human then argues about, the same
division of labour E29 used: the script narrows, the writing decides.

    python -m clab.research.e30_sector_audit
    python -m clab.research.e30_sector_audit --json journal/experiments/E30_results.json
    python -m clab.research.e30_sector_audit --component FE --sector "Real Estate"
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
from pathlib import Path

from .. import config
from ..net import read_json
from ..scoring import rubric

#: A sector smaller than this is not a sector for this purpose. Same floor E29 used.
MIN_SECTOR_N = 30

#: share of a sector's SCORED companies landing on one value, above which the sub-test
#: separates nobody. 0.95 is deliberately severe: at 0.90 a sub-test still splits one
#: company in ten, which is thin but real.
CONSTANT_SHARE = 0.95

#: a sub-test NO_DATA for at least this share of a sector, while the sector's profile
#: does NOT nominate it, is charging the sector for an absence.
MISSING_NA_SHARE = 0.85

#: a nomination that fires for fewer than this share of its OWN nominated companies is
#: not doing the work its profile note claims. Not a bug - `resolve_status` requires the
#: value to be absent, so a nomination that never fires means the number is always there.
DEAD_NA_SHARE = 0.02

#: the profile says the metric does not describe this filer; the number is computable
#: anyway, so it scores. Above this share of the nominated companies, the profile's note
#: and the scorecard disagree about what is being measured.
OVERRIDDEN_NA_SHARE = 0.50

STATUSES = ("scored", "no_data", "not_applicable", "data_quality_fail")


def _cards() -> list[dict]:
    out = []
    for p in sorted(config.SCORECARD_DIR.glob("*.json")):
        d = read_json(p)
        if isinstance(d, dict) and d.get("components"):
            out.append(d)
    return out


def _profiles_nominating(key: str) -> set[str]:
    from ..fundamentals.profile import PROFILES
    return {name for name, p in PROFILES.items() if p.na_candidate(key)}


def _nominates(profile_name: str, key: str) -> bool:
    from ..fundamentals.profile import PROFILES
    p = PROFILES.get(profile_name)
    return bool(p and p.na_candidate(key))


def _subtests(card: dict):
    for comp in rubric.COMPONENT_ORDER:
        c = (card.get("components") or {}).get(comp) or {}
        for s in (c.get("subtests") or []):
            key = str(s.get("key") or "")
            if key:
                yield comp, key, s


def audit(cards: list[dict]) -> dict:
    """One record per (sub-test, sector), with the flags that need a human."""
    acc: dict[tuple[str, str], dict] = {}
    sector_n: collections.Counter = collections.Counter()
    profiles: dict[str, collections.Counter] = {}
    for card in cards:
        sec = str(card.get("sector") or "").strip() or "?"
        sector_n[sec] += 1
        profiles.setdefault(sec, collections.Counter())[str(card.get("profile") or "?")] += 1
        for comp, key, s in _subtests(card):
            rec = acc.setdefault((key, sec), {
                "subtest": key, "component": comp, "sector": sec,
                "n": 0, "status": collections.Counter(), "earned": [],
                "max_points": int(s.get("max_points") or 0),
                # A nomination's denominator is the companies whose OWN profile nominates
                # the key, never the sector. Energy holds two FINANCIAL filers, so asking
                # "does any profile in this sector nominate bs_current_ratio?" flagged 83
                # cells where the rule was firing exactly as designed.
                "nom_n": 0, "nom_na": 0, "nom_scored": 0,
            })
            rec["n"] += 1
            status = str(s.get("status") or "?")
            rec["status"][status] += 1
            if _nominates(str(card.get("profile") or ""), key):
                rec["nom_n"] += 1
                rec["nom_na"] += status == "not_applicable"
                rec["nom_scored"] += status == "scored"
            # A sub-test whose max_points VARIES across companies is E19's proportional
            # weight (bq_moat), so the earned figure is only comparable as a share.
            mx = int(s.get("max_points") or 0)
            rec["max_points"] = max(rec["max_points"], mx)
            e = s.get("earned")
            if str(s.get("status")) == "scored" and isinstance(e, (int, float)) and mx:
                rec["earned"].append(e / mx)

    out = []
    for rec in acc.values():
        sec, key, n = rec["sector"], rec["subtest"], rec["n"]
        st = rec["status"]
        shares = {k: round(st[k] / n, 4) for k in STATUSES}
        vals = rec["earned"]
        nominated = _profiles_nominating(key)
        sector_profiles = set(profiles.get(sec, {}))
        top = collections.Counter(vals).most_common(1)
        rec2 = {
            "subtest": key, "component": rec["component"], "sector": sec,
            "n": n, "max_points": rec["max_points"],
            "scored": st["scored"], "no_data": st["no_data"],
            "not_applicable": st["not_applicable"],
            "data_quality_fail": st["data_quality_fail"],
            "share": shares,
            "mean_earned_share": round(statistics.fmean(vals), 4) if vals else None,
            "distinct_values": len(set(vals)),
            "modal_share_of_scored": round(top[0][1] / len(vals), 4) if vals else None,
            "modal_value_share_of_max": round(top[0][0], 4) if vals else None,
            "profiles_nominating": sorted(nominated),
            "sector_profiles": sorted(sector_profiles),
            "flags": [],
        }
        nom_n = rec["nom_n"]
        rec2["nominated_companies"] = nom_n
        rec2["nominated_suppressed_share"] = (
            round(rec["nom_na"] / nom_n, 4) if nom_n else None)
        rec2["nominated_scored_share"] = (
            round(rec["nom_scored"] / nom_n, 4) if nom_n else None)

        f = rec2["flags"]
        # E19's synthetic weights are not questions - `bq_moat_unassessed` is NO_DATA for
        # everyone by construction and can never be scored or suppressed.
        synthetic = key.endswith("_unassessed")
        if vals and rec2["modal_share_of_scored"] >= CONSTANT_SHARE:
            where = ("ZERO" if rec2["modal_value_share_of_max"] == 0
                     else "MAX" if rec2["modal_value_share_of_max"] == 1 else "ONE VALUE")
            f.append(f"CONSTANT_{where}")
        if (not synthetic and shares["no_data"] >= MISSING_NA_SHARE
                and not (nominated & sector_profiles)):
            f.append("MISSING_NA_NOMINATION")
        # A nomination that never fires means the number is always there. Measured over
        # the nominated companies only.
        if nom_n >= 5 and rec2["nominated_suppressed_share"] <= DEAD_NA_SHARE:
            f.append("DEAD_NA_NOMINATION")
        # The one the two-part test cannot see: the profile says the metric does not
        # describe this filer, the number is computable anyway, so it SCORES. The
        # scorecard then carries a measured, meaningless number as evidence.
        if nom_n >= 5 and rec2["nominated_scored_share"] >= OVERRIDDEN_NA_SHARE:
            f.append("NOMINATION_OVERRIDDEN")
        if shares["data_quality_fail"] > 0.02:
            f.append("QUALITY_FAIL")
        if not vals and n and not synthetic:
            f.append("NEVER_SCORED")
        out.append(rec2)

    out.sort(key=lambda r: (r["component"], r["subtest"], -r["n"]))
    return {
        "companies": len(cards),
        "min_sector_n": MIN_SECTOR_N,
        "sector_n": dict(sector_n.most_common()),
        "sector_profiles": {s: dict(c.most_common()) for s, c in sorted(profiles.items())},
        "thresholds": {"constant_share": CONSTANT_SHARE,
                       "missing_na_share": MISSING_NA_SHARE,
                       "dead_na_share": DEAD_NA_SHARE},
        "records": out,
    }


def big(r: dict) -> list[dict]:
    """Records for sectors large enough to draw a conclusion from."""
    ok = {s for s, n in r["sector_n"].items() if n >= r["min_sector_n"] and s != "?"}
    return [x for x in r["records"] if x["sector"] in ok]


def _report(r: dict, component: str | None, sector: str | None) -> None:
    rows = big(r)
    if component:
        rows = [x for x in rows if x["component"] == component.upper()]
    if sector:
        rows = [x for x in rows if x["sector"].lower() == sector.lower()]

    flagged = [x for x in rows if x["flags"]]
    print(f"{r['companies']} scorecards, "
          f"{len({x['sector'] for x in rows})} sectors at n >= {r['min_sector_n']}")
    print(f"{len(rows)} (sub-test x sector) cells, {len(flagged)} flagged")
    print()

    by_flag = collections.Counter(f for x in flagged for f in x["flags"])
    for k, v in by_flag.most_common():
        print(f"  {k:24s} {v:4d}")
    print()

    print(f"{'component':10s} {'sub-test':32s} {'sector':24s} {'n':>4s} "
          f"{'scored':>7s} {'ND':>6s} {'NA':>6s} {'mean':>6s} {'mode':>6s}  flags")
    for x in sorted(flagged, key=lambda y: (y["component"], y["subtest"], y["sector"])):
        mean = "-" if x["mean_earned_share"] is None else f"{x['mean_earned_share']:.2f}"
        mode = "-" if x["modal_share_of_scored"] is None else f"{x['modal_share_of_scored']:.2f}"
        print(f"{x['component']:10s} {x['subtest']:32s} {x['sector'][:24]:24s} "
              f"{x['n']:>4d} {x['share']['scored']:>7.2f} {x['share']['no_data']:>6.2f} "
              f"{x['share']['not_applicable']:>6.2f} {mean:>6s} {mode:>6s}  "
              + ",".join(x["flags"]))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="E30 per-sector sub-test audit")
    ap.add_argument("--json", type=Path, default=None)
    ap.add_argument("--component", default=None)
    ap.add_argument("--sector", default=None)
    a = ap.parse_args(argv)
    r = audit(_cards())
    _report(r, a.component, a.sector)
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps(r, indent=2), encoding="utf-8")
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
