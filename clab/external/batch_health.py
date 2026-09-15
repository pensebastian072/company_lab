"""Is this batch answering LESS than the ones before it?

## Why this exists

Every metric reported per batch for eight batches was a QUALITY metric: rejections,
demotions, UNKNOWN gaps, the unverifiable rate. All of them were perfect or near-perfect
throughout. None of them was a COVERAGE metric, so **a batch that answered nothing,
perfectly, scored perfectly.**

Meanwhile the four rank-order fields - `moat_trajectory`, `competitive_position`,
`competitive_position_trend`, `company_specific_capture`, worth 45 of the 100 external
points - went 92%, 83%, 87%, 49%, 65%, 30%, 8%, 0% filled across those same eight
batches. It took eight batches and a failed sector-heterogeneity study to notice, because
nothing in the pipeline was watching.

This module watches. It is the cheap, permanent version of the query that eventually
found it.

## The confound it has to survive

Fill rate is not comparable across sectors on its own. `market_share_direction` SHOULD be
0% in a batch of regulated utilities - `applicability.py` says the question is meaningless
there - and reading that as decay would fire an alarm on correct behaviour.

Two defences:

* fields nominated NOT_APPLICABLE for a company's industry are excluded from that
  company's denominator, exactly as `score.py` excludes them from `applicable`;
* the headline number is the WITHIN-INDUSTRY comparison, over industries that appear in
  both the batch and its baseline. That holds the peer set, the industry object and the
  companies' comparability fixed, and it is the comparison that showed
  `upstream_oil_gas` running 92% at E43, 38% at E44 and 5% at E46.

The pooled figure is reported beside it, marked as confounded by sector mix.

## What it does NOT do

It does not diagnose. A drop can be honest - a sector where a field genuinely cannot be
established - or it can be the process degrading. This module says "look", not "you are
wrong". The distinction is what E50 exists to settle.
"""
from __future__ import annotations

import argparse

from . import applicability as AP
from .industry_versions import version_key as _version_key
from .schema import COMPANY_ORDINALS, UNKNOWN
from .. import config

#: The fields whose collapse this was built to catch. They are the four that need a
#: comparison against named peers, they carry 45 of the 100 external points, and they are
#: the first thing a researcher drops when abstaining is cheaper than asserting.
RANK_ORDER_FIELDS = (
    "moat_trajectory",
    "competitive_position",
    "competitive_position_trend",
    "company_specific_capture",
)

#: A within-industry fill rate this far below the baseline is reported as a REGRESSION.
#: Not a hard gate - the module refuses to fail a build on it, because a real sector can
#: honestly answer less. It is a prompt to look.
REGRESSION_DROP = 0.20

#: Below this many companies shared with the baseline, an industry is not compared.
MIN_SHARED = 3


def _fill(rows: list[dict], fields: tuple[str, ...]) -> tuple[int, int]:
    """(answered, applicable) over these rows, excluding NOT_APPLICABLE nominations."""
    answered = applicable = 0
    for r in rows:
        for f in fields:
            v = r.get(f)
            if AP.is_not_applicable(r.get("industry_id"), f, v):
                continue
            applicable += 1
            if v and str(v).strip().upper() != UNKNOWN:
                answered += 1
    return answered, applicable


def _rate(rows, fields):
    a, n = _fill(rows, fields)
    return (a / n) if n else None, n


def compare(version: str, *, store=None,
            fields: tuple[str, ...] = RANK_ORDER_FIELDS,
            include_superseded_baseline: bool = False) -> dict:
    """This batch against the latest eligible company row strictly before it.

    The named batch is an explicit audit read and remains available even when retired.
    The operational baseline excludes SUPERSEDED arms by default: a rejected batch is
    evidence of what happened, not a valid ruler for judging the next batch.
    """
    from .store import ExternalStore
    st = store or ExternalStore(config.EXTERNAL_DB)
    records = st.company_records(include_superseded=True)
    versions = sorted({r["research_version"] for r in records
                       if r.get("research_version")})
    batch = st.companies(version)
    if not batch:
        return {"version": version, "error": "no such research_version",
                "known": versions}
    base = st.latest_companies(
        before_version=version,
        include_superseded=include_superseded_baseline,
    )

    b_rate, b_n = _rate(batch, fields)
    p_rate, p_n = _rate(base, fields)

    # Within-industry: the confound-free number. Only industries present in both.
    by_ind_b, by_ind_p = {}, {}
    for r in batch:
        by_ind_b.setdefault(r["industry_id"], []).append(r)
    for r in base:
        by_ind_p.setdefault(r["industry_id"], []).append(r)

    shared = []
    for ind in sorted(set(by_ind_b) & set(by_ind_p)):
        if len(by_ind_b[ind]) < MIN_SHARED or len(by_ind_p[ind]) < MIN_SHARED:
            continue
        br, _ = _rate(by_ind_b[ind], fields)
        pr, _ = _rate(by_ind_p[ind], fields)
        if br is None or pr is None:
            continue
        shared.append({"industry_id": ind, "batch": round(br, 3), "baseline": round(pr, 3),
                       "delta": round(br - pr, 3), "n_batch": len(by_ind_b[ind]),
                       "n_baseline": len(by_ind_p[ind])})

    within = None
    if shared:
        within = round(sum(s["delta"] for s in shared) / len(shared), 3)

    regressions = [s for s in shared if s["delta"] <= -REGRESSION_DROP]
    verdict = "NO_BASELINE" if not base else (
        "REGRESSION" if (within is not None and within <= -REGRESSION_DROP)
        or (within is None and p_rate is not None and b_rate is not None
            and b_rate - p_rate <= -REGRESSION_DROP)
        else "OK")

    return {
        "version": version,
        "fields": list(fields),
        "n_companies": len(batch),
        "batch_fill": None if b_rate is None else round(b_rate, 3),
        "baseline_fill": None if p_rate is None else round(p_rate, 3),
        "pooled_delta": None if (b_rate is None or p_rate is None)
        else round(b_rate - p_rate, 3),
        "within_industry_delta": within,
        "shared_industries": shared,
        "regressions": regressions,
        "verdict": verdict,
        "note": ("pooled_delta is confounded by sector mix; within_industry_delta holds "
                 "the peer set and industry object fixed and is the number to read; "
                 "SUPERSEDED company arms are excluded from the baseline unless "
                 "include_superseded_baseline=True"),
    }


def history(*, store=None, fields: tuple[str, ...] = RANK_ORDER_FIELDS,
            include_superseded: bool = False) -> list[dict]:
    """Fill rate by arm; retired arms appear only when explicitly requested."""
    from .store import ExternalStore
    st = store or ExternalStore(config.EXTERNAL_DB)
    rows = st.company_records(include_superseded=include_superseded)
    by_v: dict[str, list[dict]] = {}
    for r in rows:
        if r["research_version"]:
            by_v.setdefault(r["research_version"], []).append(r)
    out = []
    for v in sorted(by_v):
        rate, n = _rate(by_v[v], fields)
        allr, _ = _rate(by_v[v], tuple(COMPANY_ORDINALS))
        out.append({"research_version": v, "n": len(by_v[v]),
                    "rank_order_fill": None if rate is None else round(rate, 3),
                    "all_field_fill": None if allr is None else round(allr, 3)})
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Is this batch answering less than the ones before it?")
    ap.add_argument("--version", default=None, help="research_version to check")
    ap.add_argument("--history", action="store_true", help="fill rate for every batch")
    args = ap.parse_args(argv)

    if args.history or not args.version:
        print(f"{'research_version':<32}{'n':>5}{'rank-order':>12}{'all 12':>9}")
        for h in history():
            ro = "-" if h["rank_order_fill"] is None else f"{100*h['rank_order_fill']:.0f}%"
            af = "-" if h["all_field_fill"] is None else f"{100*h['all_field_fill']:.0f}%"
            print(f"{h['research_version']:<32}{h['n']:>5}{ro:>12}{af:>9}")
        print("\nrank-order = moat_trajectory, competitive_position,")
        print("             competitive_position_trend, company_specific_capture")
        print("             (45 of the 100 external points)")
        if not args.version:
            return 0

    res = compare(args.version)
    if res.get("error"):
        print(f"{args.version}: {res['error']}")
        return 2
    print(f"\n{res['version']}  n={res['n_companies']}  verdict {res['verdict']}")
    print(f"  batch fill    {res['batch_fill']}")
    print(f"  baseline fill {res['baseline_fill']}   pooled delta {res['pooled_delta']}"
          "  (confounded by sector mix)")
    print(f"  WITHIN-INDUSTRY delta {res['within_industry_delta']}  <- read this one")
    for s in res["shared_industries"]:
        mark = "  REGRESSION" if s in res["regressions"] else ""
        print(f"    {s['industry_id']:<30}{s['baseline']:>6} -> {s['batch']:<6}"
              f"{s['delta']:>+7}{mark}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# ---------------------------------------------------------------------------
# Industry OBJECTS. Added after E54, which passed every check above and still
# carried two patterns nothing was watching for.
# ---------------------------------------------------------------------------

#: E54 built 15 Financials objects and every single one drew EXACTLY 5 claims, in a
#: corpus where objects range from 4 to 35. `diversified_banks` (JPM, BAC, C, WFC) and a
#: three-company bucket that did not describe one business got the same evidence budget.
#: Zero variance in depth is a QUOTA being satisfied, not evidence being exhausted, and
#: no quality metric can see it - every one of those claims verified.
#:
#: And none of the 15 used the end of any scale: 10 of 11 answered structural_growth
#: values were MODERATE (Fisher p=0.0044 against the rest of the corpus) and 0 of 12
#: replication_difficulty values were EXTREME where 32.4% of prior objects earned it.
#: That is not the abstention failure `compare()` catches - E54 ANSWERED 41 of 45 fields.
#: It is the mirror image: answering, on the safe middle.
#:
#: Both are reported, neither is judged. A mature sector can honestly sit in the middle,
#: and this module cannot tell that from a researcher reaching for it.


def object_health(*, store=None, sector_id: str | None = None,
                  include_superseded: bool = False) -> dict:
    """Evidence depth and value spread across industry objects.

    With `sector_id`, that sector's objects are compared against every other sector's.
    Without it, the whole corpus is described and no comparison is made.

    Reads the ACTIVE corpus: one row per industry, latest version, superseded objects
    excluded. `include_superseded=True` returns all historical evidence instead.
    """
    from .store import ExternalStore
    from .schema import INDUSTRY_ORDINALS, _ORDINALS
    st = store or ExternalStore(config.EXTERNAL_DB)
    cols = ["industry_id", "sector_id", "version", "status", *INDUSTRY_ORDINALS]
    with st.connect() as con:
        rows = [dict(zip(cols, r)) for r in con.execute(
            f"SELECT {', '.join(cols)} FROM industry_intelligence").fetchall()]
        depth = dict(con.execute(
            "SELECT industry_id, count(*) FROM external_claim "
            "WHERE ticker IS NULL OR ticker = '' GROUP BY 1").fetchall())

    # THE ACTIVE CORPUS is one row per industry: the LATEST version, and only if the
    # object has not been superseded. Two defects made this necessary and both were live.
    #
    # Every stored VERSION was counted, so `coal_consumable_fuels` appeared twice - and
    # the extra row was the superseded 2026-09-02 cut whose structural_growth is UNKNOWN
    # against the current DECLINING. A phantom all-UNKNOWN object was sitting in the
    # baseline of a study about how often objects answer UNKNOWN.
    #
    # And E56 re-cut three Financials buckets whose objects returned UNKNOWN on all three
    # fields. Left in, they inflate n_objects and enter claim-depth statistics with 15
    # claims between them.
    #
    # Retired operationally, retained evidentially: nothing is deleted, the rows and their
    # verified claims stay for audit, and `include_superseded=True` reports them.
    if include_superseded:
        # ALL historical evidence means every row, including an older version whose
        # industry has since been re-cut. Running the latest-version dedupe first made
        # the flag a lie: coal_consumable_fuels 2026-09-02 stayed dropped whatever the
        # caller asked for, so "all historical" returned 53 objects and not 54.
        objs = rows
    else:
        latest: dict[str, dict] = {}
        for r in rows:
            cur = latest.get(r["industry_id"])
            if cur is None or _version_key(r["version"]) > _version_key(cur["version"]):
                latest[r["industry_id"]] = r
        objs = [o for o in latest.values()
                if str(o.get("status") or "").upper() != "SUPERSEDED"]

    def described(rows: list[dict], label: str) -> dict:
        d = sorted(depth.get(o["industry_id"], 0) for o in rows)
        out = {"label": label, "n_objects": len(rows), "claims": {
            "min": d[0] if d else None, "max": d[-1] if d else None,
            "distinct_counts": len(set(d)),
            "uniform": len(set(d)) == 1 and len(d) > 1}, "fields": {}}
        for f in INDUSTRY_ORDINALS:
            scale = _ORDINALS[f]
            vals = [o[f] for o in rows
                    if o[f] and str(o[f]).strip().upper() != UNKNOWN]
            if not vals:
                out["fields"][f] = {"answered": 0}
                continue
            counts: dict[str, int] = {}
            for v in vals:
                counts[v] = counts.get(v, 0) + 1
            ends = sum(counts.get(e, 0) for e in (scale[0], scale[-1]))
            top = max(counts.values())
            out["fields"][f] = {
                "answered": len(vals),
                "distribution": dict(sorted(counts.items(), key=lambda kv: -kv[1])),
                "modal_share": round(top / len(vals), 3),
                "endpoint_share": round(ends / len(vals), 3),
            }
        return out

    if sector_id is None:
        return {"sector_id": None, "subject": described(objs, "corpus"),
                "baseline": None}
    subject = [o for o in objs if o["sector_id"] == sector_id]
    baseline = [o for o in objs if o["sector_id"] != sector_id]
    return {"sector_id": sector_id,
            "subject": described(subject, sector_id),
            "baseline": described(baseline, "every other sector")}


# ---------------------------------------------------------------------------
# THE COMPLETENESS GATE: an object that says nothing does not get to exist.
# ---------------------------------------------------------------------------

#: Every structural field must be answered. Not most - all three.
#:
#: E61 is why this exists and it is the worked example. Its 25 Industrials objects passed
#: every quality check there was: 138 of 138 claims VERIFIED_LOCAL, no non-UNKNOWN field
#: without a claim naming it, lifecycle guards intact. And **20 of 25 answered NOTHING** -
#: 5 structural fields answered out of 75, with `replication_difficulty` UNKNOWN on every
#: single object. 259 companies, the largest sector in the book, were about to be judged
#: against objects that assert nothing.
#:
#: That is the E54 abstention collapse one layer up: perfect quality metrics over an empty
#: answer. `compare()` catches it on the company side and nothing watched the object side.
#:
#: Measured on the live corpus the day this was written: 49 of 80 objects already pass
#: 3-of-3. Communication Services 11/11, Utilities 7/7, IT 5/5, Energy 7/8, Financials
#: 18/22. **Industrials passes 0 of 26.** The bar is not new or harsh - it is what every
#: other sector already clears, and E61 is the outlier.
REQUIRED_ANSWERED_FIELDS = 3          # len(schema.INDUSTRY_ORDINALS)

#: But the AUTO-RETIRE bar is lower, and the difference is load-bearing.
#:
#: An object answering ZERO fields concluded nothing and is deleted. An object answering
#: one or two abstained on the rest, and this repo's own standard rules say a reasoned
#: UNKNOWN is a RESULT, not a gap - E53 proved it, where `market_share_direction` was
#: correctly 0 of 59 because a regulated utility has no contestable market share.
#:
#: A strict 3-of-3 auto-retire cannot tell "abstained wholesale" from "abstained on one
#: field for a good reason", and on 2026-09-09 it deleted both: 20 empty Industrials
#: objects AND 11 working ones, including `regional_banking` at 2 of 3, which blocked a
#: staged 42-company batch. Deleting an honest refusal is the abstention error wearing a
#: quality check's clothes.
#:
#: So: zero answers is deleted automatically. Below three, the object survives and the
#: RESEARCHER owes a written reason per UNKNOWN field - a rule the prompt enforces,
#: because only the researcher knows which of the two cases it is.
RETIRE_BELOW_ANSWERED = 1


def completeness(*, store=None, sector_id: str | None = None,
                 required: int | None = None) -> dict:
    """Which ACTIVE objects answer all their structural fields, and which do not.

    UNKNOWN is NO_DATA, never a value, so an UNKNOWN field is an unanswered field. This
    counts what an object SAYS, not how well-sourced what it says happens to be - an
    object can be perfectly evidenced and still be useless because it concluded nothing.
    """
    from .store import ExternalStore
    from .schema import INDUSTRY_ORDINALS as FIELDS

    required = REQUIRED_ANSWERED_FIELDS if required is None else required
    st = store or ExternalStore(config.EXTERNAL_DB)
    cols = ["industry_id", "sector_id", *FIELDS]
    with st.connect() as con:
        rows = [dict(zip(cols, r)) for r in con.execute(
            f"SELECT {', '.join(cols)} FROM industry_intelligence "
            "WHERE status IS NULL OR upper(status) != 'SUPERSEDED'").fetchall()]
    if sector_id:
        rows = [r for r in rows if r["sector_id"] == sector_id]

    passed, failed = [], []
    for r in rows:
        n = sum(1 for f in FIELDS
                if r[f] and str(r[f]).strip().upper() != UNKNOWN)
        rec = {"industry_id": r["industry_id"], "sector_id": r["sector_id"],
               "answered": n, "of": len(FIELDS),
               "values": {f: r[f] for f in FIELDS}}
        (passed if n >= required else failed).append(rec)

    by_sector: dict[str, dict] = {}
    for rec in passed + failed:
        d = by_sector.setdefault(rec["sector_id"], {"pass": 0, "fail": 0})
        d["pass" if rec["answered"] >= required else "fail"] += 1

    return {"required": required, "n_objects": len(rows),
            "n_pass": len(passed), "n_fail": len(failed),
            "by_sector": by_sector,
            "passed": sorted(passed, key=lambda r: r["industry_id"]),
            "failed": sorted(failed, key=lambda r: (r["answered"], r["industry_id"]))}


def enforce(*, store=None, sector_id: str | None = None, required: int | None = None,
            apply: bool = False, reason: str | None = None) -> dict:
    """Retire every object that fails the gate. Retained evidentially, not erased.

    Failing objects are marked SUPERSEDED with `superseded_by` left EMPTY, because there
    is no replacement - the unit needs re-researching. `latest_companies()`-style
    resolution then omits rather than falling back, so the companies show as having no
    current industry object instead of being quietly judged against an empty one.

    `apply=False` reports what would happen and changes nothing.
    """
    from .store import ExternalStore
    from .lifecycle import supersede_industry_versions

    st = store or ExternalStore(config.EXTERNAL_DB)
    res = completeness(store=st, sector_id=sector_id, required=required)
    # Auto-retire only what concluded NOTHING. Objects at 1 or 2 of 3 survive and are
    # reported as `below_ship_bar` for the researcher to justify, not deleted here.
    ids = [r["industry_id"] for r in res["failed"] if r["answered"] < RETIRE_BELOW_ANSWERED]
    partial = [r["industry_id"] for r in res["failed"]
               if r["answered"] >= RETIRE_BELOW_ANSWERED]
    why = reason or (
        "Completeness gate: ZERO of %d structural fields answered. An object that "
        "concludes nothing gives the companies resolving to it nothing to be judged "
        "against. Retained for audit; the unit needs re-researching."
        % REQUIRED_ANSWERED_FIELDS)

    out = {"would_retire": ids, "n": len(ids), "applied": False, "reason": why,
           "below_ship_bar": partial, "n_below_ship_bar": len(partial)}
    if apply and ids:
        with st.connect() as con:
            for iid in ids:
                con.execute(
                    "UPDATE industry_intelligence SET status = 'SUPERSEDED', "
                    "superseded_reason = ?, superseded_at = now() "
                    "WHERE industry_id = ? AND (status IS NULL OR "
                    "upper(status) != 'SUPERSEDED')", [why, iid])
        out["applied"] = True
    return out


#: A field that takes ONE value across an entire batch is the E30 symptom: `bs_dilution`
#: earned nothing in all eleven sectors because one derivation ran unfiltered, and the
#: constancy was the only visible trace. It repeats here in two shapes and neither of the
#: existing gauges sees either:
#:
#:   ALL-UNKNOWN      `market_share_direction` came back UNKNOWN for 85 of 85 Financials
#:                    companies across two batches while `marketshare.py` - a module built
#:                    to compute that exact field from the FDIC Summary of Deposits - had
#:                    no production caller. E43 answered it 1 of 40. Both batches were
#:                    reported OK, correctly: `compare()` watches the four rank-order
#:                    fields and this is not one of them.
#:   ONE VALUE        E53's mechanical `external_better` got through the same way.
#:
#: An all-UNKNOWN field can be entirely correct - E53's utilities have no contestable
#: market share and E47 returned 0 of 59 on purpose - so this REPORTS and never fails.
#: What it removes is the ability to not notice.
CONSTANT_MIN_ROWS = 8


def constant_fields(version: str, *, store=None, min_rows: int | None = None) -> dict:
    """Fields that take a single value across one batch, UNKNOWN included.

    Returns the constant fields split into `all_unknown` (the batch answered nothing) and
    `single_value` (the batch answered the same thing every time), because those two ask
    different questions of a reviewer: the first is "was this answerable at all", the
    second is "is this a finding or a stuck derivation".
    """
    from .store import ExternalStore
    from . import schema as S

    st = store or ExternalStore(config.EXTERNAL_DB)
    rows = st.companies(version)
    min_rows = CONSTANT_MIN_ROWS if min_rows is None else min_rows
    out = {"version": version, "n_rows": len(rows), "min_rows": min_rows,
           "all_unknown": [], "single_value": [], "checked": 0}
    if len(rows) < min_rows:
        out["skipped"] = f"{len(rows)} rows < {min_rows}"
        return out

    for f in S.COMPANY_ORDINALS:
        # NOT_APPLICABLE nominations are excluded the same way _fill() excludes them: a
        # field an industry cannot answer by construction is not a constant, it is out of
        # scope. Without this the check would flag every applicability rule as a defect.
        vals = [r.get(f) for r in rows
                if not AP.is_not_applicable(r.get("industry_id"), f, r.get(f))]
        vals = [(str(v).strip().upper() if v else UNKNOWN) for v in vals]
        if len(vals) < min_rows:
            continue
        out["checked"] += 1
        distinct = set(vals)
        if len(distinct) != 1:
            continue
        only = distinct.pop()
        rec = {"field": f, "value": only, "n": len(vals)}
        out["all_unknown" if only == UNKNOWN else "single_value"].append(rec)
    return out
