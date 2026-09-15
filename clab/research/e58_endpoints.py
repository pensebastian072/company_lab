"""E58: does the researcher avoid the ends of a scale, or does Financials just sit mid?

E56 found that across two separate research sessions, sixteen Financials INDUSTRY objects
used a scale endpoint exactly **zero** times in 24 answered values, against 4-25% in the
rest of the corpus. That was exploratory - it was not the registered prediction, and
testing it on the data that suggested it is the p-hacking the registration exists to
prevent. This module is the instrument for testing it somewhere else.

## Two arms, and they answer different questions

**Arm A - E57 Health Care industry objects.** Same researcher, same object type, DIFFERENT
sector. If the avoidance is a researcher tendency it appears here too; if it is a fact
about Financials, Health Care uses endpoints at the corpus rate. This is the cleaner
separation and it is nearly free, because E57 is being built anyway.

**Arm B - Phase B Financials companies.** Same sector, DIFFERENT field family and a much
larger n. This is P2 from `E56_registered.md`, made concrete.

## Why the company arm is measured per field and never pooled

Measured 2026-09-07 on the 395 company rows already in the store, the endpoint rate varies
enormously BY FIELD, and the direction is not consistent:

    demand_visibility      financials  2.6%   non-financials  53.2%
    disruption_risk        financials 16.3%   non-financials   2.6%
    moat_trajectory        financials 36.0%   non-financials  35.5%

A pooled endpoint share over these is a statement about which fields happened to be
answered, not about the researcher. So the company arm reports a per-field table and
counts fields, and a pooled figure is never the headline. Fields whose scale has fewer
than four values are excluded: on a 3-point scale two of the three values ARE endpoints,
so the measure is not comparable.

Nothing here scores, ranks or promotes anything.
"""
from __future__ import annotations

import argparse

from ..external.schema import (COMPANY_ORDINALS, INDUSTRY_ORDINALS, _ORDINALS,
                               UNKNOWN)

#: Arm A's primary field. `replication_difficulty` carries the highest endpoint rate in
#: the rest of the corpus (24.5%), so it has the most power to detect avoidance, and it
#: is the field where the E56 five clustered hardest (HIGH for all five).
ARM_A_FIELD = "replication_difficulty"

#: Arm A: below this endpoint share, the avoidance reproduced in a different sector.
ARM_A_THRESHOLD = 0.10

#: Arm A needs at least this many answered objects to say anything.
ARM_A_MIN_ANSWERED = 6

#: Arm B: a field counts as AVOIDED when the subject's endpoint share is this far below
#: the comparison group's on the SAME field.
ARM_B_MARGIN = 0.15

#: Arm B: a field needs this many answered values on both sides to be compared at all.
ARM_B_MIN_PER_SIDE = 20

#: Scales shorter than this are not comparable - two of three values are endpoints.
MIN_SCALE = 4


def _endpoints(field: str) -> tuple[str, str]:
    scale = _ORDINALS[field]
    return scale[0], scale[-1]


def _share(values: list[str], field: str):
    """(endpoint share, n) over ANSWERED values. UNKNOWN is NO_DATA, never a value."""
    ends = _endpoints(field)
    v = [x for x in values if x and str(x).strip().upper() != UNKNOWN]
    if not v:
        return None, 0
    return sum(x in ends for x in v) / len(v), len(v)


def arm_a(sector_id: str = "health_care", *, store=None) -> dict:
    """Industry objects in another sector: does the avoidance follow the researcher?"""
    from ..external.store import ExternalStore
    from .. import config

    st = store or ExternalStore(config.EXTERNAL_DB)
    with st.connect() as con:
        rows = con.execute(
            "SELECT industry_id, sector_id, status, "
            f"{', '.join(INDUSTRY_ORDINALS)} FROM industry_intelligence").fetchall()
    cols = ["industry_id", "sector_id", "status", *INDUSTRY_ORDINALS]
    objs = [dict(zip(cols, r)) for r in rows]
    objs = [o for o in objs if str(o.get("status") or "").upper() != "SUPERSEDED"]

    subject = [o[ARM_A_FIELD] for o in objs if o["sector_id"] == sector_id]
    rest = [o[ARM_A_FIELD] for o in objs if o["sector_id"] != sector_id]
    s_share, s_n = _share(subject, ARM_A_FIELD)
    r_share, r_n = _share(rest, ARM_A_FIELD)

    if s_n < ARM_A_MIN_ANSWERED:
        verdict, reading = "INDETERMINATE", (
            f"only {s_n} {sector_id} objects answered {ARM_A_FIELD}; "
            f"{ARM_A_MIN_ANSWERED} registered as the minimum.")
    elif s_share < ARM_A_THRESHOLD:
        verdict, reading = "CONFIRMED", (
            f"{sector_id} objects avoid the ends too ({s_share:.0%} of {s_n}, against "
            f"{r_share:.0%} elsewhere). The avoidance follows the RESEARCHER across "
            "sectors, so it is not a fact about Financials. It is still not shown to be "
            "an error - a scale end may genuinely be rare - only that the sector "
            "explanation is dead.")
    else:
        verdict, reading = "REFUTED", (
            f"{sector_id} objects use the ends at {s_share:.0%} of {s_n}, at or above "
            f"the registered {ARM_A_THRESHOLD:.0%} (rest of corpus {r_share:.0%}). The "
            "avoidance did NOT follow the researcher into another sector, which points "
            "back at Financials being genuinely without extremes.")

    return {"arm": "A", "field": ARM_A_FIELD, "sector_id": sector_id,
            "verdict": verdict, "reading": reading,
            "subject_share": None if s_share is None else round(s_share, 3),
            "subject_n": s_n,
            "rest_share": None if r_share is None else round(r_share, 3),
            "rest_n": r_n, "threshold": ARM_A_THRESHOLD}


def arm_b(sector_id: str = "financials", *, store=None, research_version=None,
          research_versions=None) -> dict:
    """Company fields, PER FIELD. Never pooled - see the module docstring.

    SUBJECT SCOPE, and getting this wrong silently answers a different question.
    E58 registers arm B as "evaluated on Phase B's own research_version". Phase B spans
    SEVERAL versions - Financials is four batches - so `research_versions` takes the set.
    `research_version` remains for a single arm.

    Passing NEITHER uses every company with current research in the sector, which
    INCLUDES pre-Phase-B arms. That is a different subject set and it is not what was
    registered: measured 2026-09-09, the default gave Financials technology_risk 0.048 on
    n=167 while the registered E59 scope gives 0.000 on n=128. Both numbers are correct
    about their own sample and only one of them is arm B.

    A SUPERSEDED arm is never in the subject. E59 batch 1 was burned and replaced by its
    rerun; counting both would weight 43 companies twice and include research we rejected.
    """
    import pandas as pd
    from ..external.store import ExternalStore
    from ..external.taxonomy import resolve
    from .. import config

    st = store or ExternalStore(config.EXTERNAL_DB)
    bk = pd.read_parquet(config.SCORES_PARQUET)
    sect = {r.ticker: resolve(r.ticker, r.sector, r.sub_industry)["sector_id"]
            for r in bk.itertuples()}

    cols = ["ticker", "research_version", "last_research_date", "status",
            *COMPANY_ORDINALS]
    with st.connect() as con:
        rows = [dict(zip(cols, r)) for r in con.execute(
            f"SELECT {', '.join(cols)} FROM company_external").fetchall()]
    wanted = set(research_versions or ())
    if research_version:
        wanted.add(research_version)

    def _dedupe(rs):
        """Latest SURVIVING row per ticker. A rejected arm is never counted, and a
        company with two arms in scope is counted once."""
        keep: dict[str, tuple] = {}
        for r in rs:
            if str(r.get("status") or "").upper() == "SUPERSEDED":
                continue
            k = (str(r.get("last_research_date") or ""),
                 str(r.get("research_version") or ""))
            cur = keep.get(r["ticker"])
            if cur is None or k > cur[0]:
                keep[r["ticker"]] = (k, r)
        return [r for _k, r in keep.values()]
    # THE REGISTERED SCOPE NAMES THE SUBJECT'S research_version. It does not restrict the
    # baseline - the comparison group is the rest of the corpus as it currently stands.
    # Applying the version filter to BOTH sides empties the baseline, and the result then
    # returns INDETERMINATE, which reads like a thin sample rather than the error it is.
    # The first draft of this scoping did exactly that.
    subject_rows = [r for r in rows if sect.get(r["ticker"]) == sector_id]
    if wanted:
        subject_rows = [r for r in subject_rows if r["research_version"] in wanted]
    subject = _dedupe(subject_rows)
    rest = _dedupe([r for r in rows if sect.get(r["ticker"])
                    and sect.get(r["ticker"]) != sector_id])

    fields, avoided, compared = [], 0, 0
    for f in COMPANY_ORDINALS:
        if len(_ORDINALS[f]) < MIN_SCALE:
            continue
        s_share, s_n = _share([r[f] for r in subject], f)
        r_share, r_n = _share([r[f] for r in rest], f)
        row = {"field": f, "subject_share": s_share, "subject_n": s_n,
               "rest_share": r_share, "rest_n": r_n, "comparable": False,
               "avoided": False}
        if (s_n >= ARM_B_MIN_PER_SIDE and r_n >= ARM_B_MIN_PER_SIDE
                and s_share is not None and r_share is not None):
            row["comparable"] = True
            row["delta"] = round(s_share - r_share, 3)
            row["avoided"] = (r_share - s_share) >= ARM_B_MARGIN
            compared += 1
            avoided += bool(row["avoided"])
        for k in ("subject_share", "rest_share"):
            if row[k] is not None:
                row[k] = round(row[k], 3)
        fields.append(row)

    if compared == 0:
        verdict, reading = "INDETERMINATE", (
            "no field had enough answered values on both sides to compare.")
    elif avoided > compared / 2:
        verdict, reading = "CONFIRMED", (
            f"{sector_id} sits at least {ARM_B_MARGIN:.0%} below the comparison group on "
            f"{avoided} of {compared} comparable fields - a majority. The middle-reach "
            "carries into company fields.")
    else:
        verdict, reading = "REFUTED", (
            f"{sector_id} is materially lower on only {avoided} of {compared} comparable "
            "fields, not a majority. Endpoint use at company level is field-specific, "
            "not a blanket avoidance.")

    return {"arm": "B", "sector_id": sector_id, "verdict": verdict, "reading": reading,
            "n_subject": len(subject), "n_rest": len(rest),
            "fields_compared": compared, "fields_avoided": avoided,
            "margin": ARM_B_MARGIN, "per_field": fields}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--arm", choices=["A", "B", "both"], default="both")
    ap.add_argument("--sector")
    ap.add_argument("--research-version")
    a = ap.parse_args(argv)

    if a.arm in ("A", "both"):
        r = arm_a(a.sector or "health_care")
        print(f"E58 arm A [{r['field']} in {r['sector_id']}]: {r['verdict']}")
        print(f"  subject {r['subject_share']} n={r['subject_n']}   "
              f"rest {r['rest_share']} n={r['rest_n']}   "
              f"threshold {r['threshold']}")
        print(f"  {r['reading']}\n")
    if a.arm in ("B", "both"):
        r = arm_b(a.sector or "financials", research_version=a.research_version)
        print(f"E58 arm B [company fields, {r['sector_id']}]: {r['verdict']}")
        print(f"  n {r['n_subject']} vs {r['n_rest']}   "
              f"avoided {r['fields_avoided']}/{r['fields_compared']} comparable fields")
        print("  %-28s %10s %10s %8s" % ("field", "subject", "rest", "avoided"))
        for f in r["per_field"]:
            if not f["comparable"]:
                continue
            print("  %-28s %6s n=%-4d %6s n=%-4d %6s" % (
                f["field"], f["subject_share"], f["subject_n"],
                f["rest_share"], f["rest_n"], "YES" if f["avoided"] else ""))
        print(f"  {r['reading']}")
    return 0


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(main())
