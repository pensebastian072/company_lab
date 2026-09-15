"""The External Quality Score, computed HERE from categoricals and cited evidence.

Codex never supplies a number. `finalize.py` refuses a payload that carries one. This
module is where every external number comes from, and it is built to the same rules the
94-point framework already runs on:

    a field with no evidence is NO_DATA, not a zero
    coverage is scored / applicable
    below EXTERNAL_MIN_COVERAGE there is NO score, not a flattering one

## A field scores only if a claim cites it, checked HERE

`finalize.py` can demote uncited fields when a request sets `require_citation`, but that
is a property of how a run was configured, not of the data. Arm 1 of E42 was finalized
without it and its records still hold 26 uncited assertions. So this module re-derives
backing from the claim table rather than trusting that the finalizer was strict:

    scored  = non-UNKNOWN AND at least one claim in the catalog cites that field
              AND that claim is not UNVERIFIABLE

An UNVERIFIABLE claim is one we fetched and could not find the quote in. It cannot back
a score. A SELF_ATTESTED claim - one whose source we could not reach - still backs the
field, because failing to fetch a page is our problem and not evidence of anything about
the company. That asymmetry is the same UNKNOWN-is-not-NEGATIVE rule the layer runs on.

## `cheapness_quality` is deliberately NOT scored

Measured on E42: it had no citable source for two of the three companies, and both said
so explicitly - "staged valuation suggests it is not cheap, but no source-backed
valuation classification is available".

That is not a research failure, it is the wrong question to ask this layer. Valuation is
already 15 measured points of the framework, computed from multiples, peers and a
reverse DCF. An external opinion about cheapness would be scoring bloat on top of a
component that already exists, which is exactly what V3 was told not to do.

It is kept as a stored field and as an input to VALUE_TRAP_RISK, where a STRUCTURAL
reading beside a cheap measured valuation is a flag. It earns no points.

## The dimensions

    Competitive Position   20   competitive_position 12 + trend 8
    Moat Strength          15   current_moat_strength 10 + pricing_power 5
    Moat Trajectory        15   moat_trajectory
    Structural Demand      15   industry_structural_growth 10 + demand_visibility 5
    Company Capture        15   company_specific_capture 10 + market_share_direction 5
    Risk Resilience        10   technology_risk + disruption_risk + regulatory_risk
    Evidence Quality       10   computed from the evidence, not from a categorical
                          ----
                          100

Twelve of the thirteen company categoricals carry points; `cheapness_quality` is the
thirteenth and carries none.
"""
from __future__ import annotations

import argparse
import collections
from datetime import date, datetime, timezone

from .. import config
from . import applicability as AP
from . import schema as S

#: (dimension, {field: points}). Evidence Quality has no fields - it is measured.
DIMENSIONS: dict[str, dict[str, int]] = {
    "competitive_position": {"competitive_position": 12,
                             "competitive_position_trend": 8},
    "moat_strength": {"current_moat_strength": 10, "pricing_power": 5},
    "moat_trajectory": {"moat_trajectory": 15},
    "structural_demand": {"industry_structural_growth": 10, "demand_visibility": 5},
    "company_capture": {"company_specific_capture": 10, "market_share_direction": 5},
    "risk_resilience": {"technology_risk": 4, "disruption_risk": 3,
                        "regulatory_risk": 3},
}
EVIDENCE_QUALITY_POINTS = 10
TOTAL_POINTS = sum(sum(d.values()) for d in DIMENSIONS.values()) + EVIDENCE_QUALITY_POINTS

#: The categoricals that carry points. Everything in COMPANY_ORDINALS except the one
#: field this module deliberately does not score.
SCORED_FIELDS: tuple[str, ...] = tuple(
    f for d in DIMENSIONS.values() for f in d)
UNSCORED_FIELDS: tuple[str, ...] = tuple(
    f for f in S.COMPANY_ORDINALS if f not in SCORED_FIELDS)

#: Evidence Quality sub-weights, out of EVIDENCE_QUALITY_POINTS.
_EQ_DOMAINS = 5       # distinct independence domains, saturating at this many
_EQ_DOMAIN_TARGET = 4
_EQ_VERIFIED = 3      # share of backing claims that we fetched and matched
_EQ_FRESHNESS = 2     # share of backing claims newer than FRESH_DAYS
FRESH_DAYS = 550

#: Claims older than this contribute nothing to freshness but still back their field.
#: A structural fact about an industry does not expire; a bookings number does. The
#: refresh_class on the industry object is where that distinction lives, not here.


def _backing(claims: list[dict]) -> dict[str, list[dict]]:
    """field -> claims that cite it and are not UNVERIFIABLE."""
    out: dict[str, list[dict]] = collections.defaultdict(list)
    for c in claims:
        if c.get("verify_status") == "UNVERIFIABLE":
            continue
        f = c.get("field")
        if f:
            out[f].append(c)
    return out


def _age_days(stamp, today: date) -> int | None:
    if stamp is None:
        return None
    try:
        d = stamp if isinstance(stamp, date) and not isinstance(stamp, datetime) \
            else datetime.fromisoformat(str(stamp)[:10]).date()
    except (ValueError, TypeError):
        return None
    return (today - d).days


def evidence_quality(claims: list[dict], *, today: date | None = None) -> tuple[float, dict]:
    """Points out of EVIDENCE_QUALITY_POINTS, plus the parts, from the backing claims.

    Counts DISTINCT INDEPENDENCE DOMAINS rather than claims. Ten trade-press rewrites of
    one press release is one domain. Measured on E42 arm 2: COMPANY_IR grew from 5 of 14
    claims to 11 of 32 when citations were demanded, because a rule that wants a source
    pushes a researcher toward the most citable one, which is the company itself.
    Counting domains is what stops that from reading as more evidence.
    """
    today = today or datetime.now(timezone.utc).date()
    usable = [c for c in claims if c.get("verify_status") != "UNVERIFIABLE"]
    if not usable:
        return 0.0, {"claims": 0, "domains": 0, "verified_share": None,
                     "fresh_share": None}

    domains = {c.get("independence_domain") for c in usable if c.get("independence_domain")}
    dom_pts = _EQ_DOMAINS * min(len(domains), _EQ_DOMAIN_TARGET) / _EQ_DOMAIN_TARGET

    verified = sum(1 for c in usable if c.get("verify_status") == "VERIFIED_LOCAL")
    ver_share = verified / len(usable)
    ver_pts = _EQ_VERIFIED * ver_share

    ages = [_age_days(c.get("source_date"), today) for c in usable]
    dated = [a for a in ages if a is not None]
    fresh_share = (sum(1 for a in dated if a <= FRESH_DAYS) / len(dated)) if dated else None
    fresh_pts = _EQ_FRESHNESS * fresh_share if fresh_share is not None else 0.0

    return round(dom_pts + ver_pts + fresh_pts, 3), {
        "claims": len(usable), "domains": len(domains),
        "verified_share": round(ver_share, 3),
        "fresh_share": None if fresh_share is None else round(fresh_share, 3),
    }


def score_company(record: dict, claims: list[dict], *,
                  today: date | None = None) -> dict:
    """External score, coverage and per-dimension detail for one company record.

    `record` is a `company_external` row; `claims` are that company's rows from
    `external_claim`. Nothing here reads a number supplied by the researcher.
    """
    backed = _backing(claims)
    dims: dict[str, dict] = {}
    earned = available = applicable = 0.0
    scored_fields: list[str] = []
    unbacked: list[str] = []
    not_applicable: list[str] = []

    for dim, fields in DIMENSIONS.items():
        d_earned = d_available = 0.0
        detail = {}
        for field, pts in fields.items():
            value = record.get(field)
            # NOT_APPLICABLE leaves the denominator; UNKNOWN stays in it. Two-condition,
            # per-INDUSTRY, argued in applicability.py - it is the only edit here that
            # flatters a company for an absence, so it never keys on emptiness alone.
            if AP.is_not_applicable(record.get("industry_id"), field, value):
                detail[field] = {"value": value, "points": None,
                                 "status": "NOT_APPLICABLE", "max": pts}
                not_applicable.append(field)
                continue
            applicable += pts
            norm = S.normalized(field, value)
            has_claim = bool(backed.get(field))
            if norm is None or not has_claim:
                detail[field] = {"value": value, "points": None,
                                 "status": "NO_DATA" if norm is None else "UNBACKED"}
                if norm is not None and not has_claim:
                    unbacked.append(field)
                continue
            got = norm * pts
            d_earned += got
            d_available += pts
            detail[field] = {"value": value, "points": round(got, 3),
                             "max": pts, "status": "SCORED",
                             "claims": len(backed[field])}
            scored_fields.append(field)
        dims[dim] = {"earned": round(d_earned, 3), "available": d_available,
                     "max": sum(fields.values()),
                     "applicable": sum(
                         p for f, p in fields.items()
                         if not AP.is_not_applicable(record.get("industry_id"), f,
                                                     record.get(f))),
                     "fields": detail}
        earned += d_earned
        available += d_available

    # Evidence Quality is always applicable - it measures the evidence we have, and an
    # absence of evidence is a real 0 rather than NO_DATA.
    eq_pts, eq_detail = evidence_quality(
        [c for f in SCORED_FIELDS for c in backed.get(f, [])], today=today)
    applicable += EVIDENCE_QUALITY_POINTS
    available += EVIDENCE_QUALITY_POINTS
    earned += eq_pts
    dims["evidence_quality"] = {"earned": eq_pts, "available": EVIDENCE_QUALITY_POINTS,
                                "max": EVIDENCE_QUALITY_POINTS, "fields": eq_detail}

    coverage = available / applicable if applicable else 0.0
    enough = coverage >= config.EXTERNAL_MIN_COVERAGE

    # STRICT is the headline, exactly as composite_strict is for the framework: points
    # earned out of the points that APPLY, so a dimension nobody could evidence costs
    # the company those points.
    #
    # Normalizing over `available` instead was tried and reverted. It gave VRT the
    # HIGHEST score of the three (81.4) while its entire company_capture dimension had
    # zero available points - both fields UNKNOWN - because excluding a dimension from
    # the denominator is indistinguishable from acing it. VRT's whole finding is
    # "industry growing, capture unproven", and the arithmetic was paying it for the
    # second half. Strict puts the three back in the order the evidence supports:
    # NVDA 76.2, VRT 69.2, FICO 44.1.
    strict = round(100.0 * earned / applicable, 1) if applicable else None
    normalized = round(100.0 * earned / available, 1) if available else None

    return {
        "ticker": record.get("ticker"),
        "research_version": record.get("research_version"),
        "external_score": strict,
        # The extrapolated form. The framework's rule is that it is "never shown without
        # its coverage figure" - NOT that it is withheld. An earlier draft blanked it
        # below the floor, and reporting that as "38 of 40 got no external score" made a
        # property sound like a gate. This is a RANKING: every company is ranked, always,
        # and coverage travels beside the number as a column so a reader can discount it.
        "external_normalized": normalized,
        "insufficient_coverage": not enough,
        "coverage": round(coverage, 4),
        "points_earned": round(earned, 3),
        "points_available": round(available, 3),
        "points_applicable": round(applicable, 3),
        "scored_fields": sorted(set(scored_fields)),
        "unbacked_fields": sorted(set(unbacked)),
        # Fields excluded from `applicable` by applicability.py. Always reported, never
        # silent: this list is the only thing standing between a defensible structural
        # exclusion and the E29 self-flattering coverage lift.
        "not_applicable_fields": sorted(set(not_applicable)),
        "insufficient": not enough,
        "dimensions": dims,
        "evidence": eq_detail,
    }


def confidence(record: dict, claims: list[dict], *, coverage: float | None = None,
               today: date | None = None) -> tuple[float | None, dict]:
    """0-1, and it NEVER multiplies the score.

    Its only mechanical jobs are gating whether a reconciliation rule may fire and
    appearing as a column. Multiplying a score by a confidence blends two different
    things into one number that can no longer be read as either.

    COVERAGE IS A TERM, and it has to be. Without it this returned **1.0 for arm 1's
    FICO** - four claims, four domains, all verified, all fresh - against 0.945 for the
    same company in arm 2 with eleven claims. Arm 1 had evidenced 38% of the picture and
    arm 2 had evidenced 80%, and the more complete record scored LOWER. A confidence
    that measures only the quality of what was cited, and not how much was cited, is
    maximised by researching one field impeccably and ignoring the rest.
    """
    usable = [c for c in claims if c.get("verify_status") != "UNVERIFIABLE"]
    if not usable:
        return None, {"reason": "no usable claims"}

    today = today or datetime.now(timezone.utc).date()
    domains = {c.get("independence_domain") for c in usable if c.get("independence_domain")}
    verified = sum(1 for c in usable if c.get("verify_status") == "VERIFIED_LOCAL")
    unverifiable = sum(1 for c in claims if c.get("verify_status") == "UNVERIFIABLE")
    depth = record.get("research_depth") or 0
    ages = [_age_days(c.get("source_date"), today) for c in usable]
    dated = [a for a in ages if a is not None]
    fresh = (sum(1 for a in dated if a <= FRESH_DAYS) / len(dated)) if dated else 0.0

    parts = {
        "domains": min(len(domains), _EQ_DOMAIN_TARGET) / _EQ_DOMAIN_TARGET,
        "verified": verified / len(usable),
        "coverage": float(coverage) if coverage is not None else 0.0,
        "depth": min(depth, 3) / 3,
        "freshness": fresh,
    }
    value = (0.30 * parts["domains"] + 0.30 * parts["verified"]
             + 0.25 * parts["coverage"]
             + 0.075 * parts["depth"] + 0.075 * parts["freshness"])

    # An unverifiable claim is one we fetched but could not confirm from the retrieved
    # bytes. That includes genuine quote/source mismatches and extraction or formatting
    # artifacts; it is not a fabrication label. It caps confidence because the stored
    # claim cannot currently be checked, rather than merely nudging it.
    if unverifiable:
        value = min(value, 0.5)
        parts["unverifiable_cap"] = True

    return round(value, 3), parts


#: A claim we DERIVED is not another arm's research, and the arm filter below must not
#: hide it. `marketshare.apply_to` writes its FDIC Summary of Deposits claim under
#: `fdic_sod:<research_version>`, which never equals a company's own request_id, so the
#: scorer discarded it - the field was written onto the record and then refused points for
#: having no backing claim.
#:
#: Measured 2026-09-09 when the FDIC pass was wired: 0 records actually lost a point,
#: because in all 20 filled rows the researcher HAD cited `market_share_direction` while
#: returning UNKNOWN for it, and that citation did the backing. So this was a silent
#: default covering a wiring error, exactly the class this repo keeps being bitten by -
#: masked by luck rather than by design, and the first company researched without a claim
#: on that field would have been scored wrong with nothing in the output saying so.
COMPUTED_REQUEST_PREFIXES: tuple[str, ...] = ("fdic_sod:", "revenue_share:")


def _is_computed_claim(claim: dict) -> bool:
    """True for a claim this repo derived from a dataset it holds, not from research."""
    rid = str(claim.get("request_id") or "")
    return rid.startswith(COMPUTED_REQUEST_PREFIXES)


def _is_arm_claim(claim: dict, record: dict) -> bool:
    """True when the claim belongs to the same research arm as the record.

    The arm filter exists because claims are keyed by claim_id, not by research version,
    so `claims_for(ticker)` returns EVERY arm's evidence: FICO's cited arm has 11 claims
    and an early draft scored it on 14, borrowing three findings from an arm run under a
    different rule. Two arms exist to be compared and contaminating one destroys that.

    A COMPUTED claim is different in kind - deterministic, public, identical whichever arm
    asks - so it is admitted separately. But that only holds if the computed pass is run
    across EVERY live arm: `2026-09-02+E44-matched` received an FDIC pass that
    `2026-09-02+E43-batch1` never got, on 16 of its 40 companies and after it was scored,
    and a matched control arm that differs from its treatment arm by an extra method is no
    longer a control. Run a computed pass on all arms, or record the asymmetry.
    """
    return not record.get("request_id") or claim.get("request_id") == record["request_id"]


def score_all(*, research_version: str, store=None, apply: bool = False,
              today: date | None = None) -> list[dict]:
    from .store import ExternalStore

    store = store or ExternalStore()
    rows = store.companies(research_version)
    out = []
    for rec in rows:
        # Claims are keyed by claim_id, not by research version, so claims_for(ticker)
        # returns EVERY arm's evidence for that company. Scoring one arm on another's
        # claims is not a rounding error: FICO's cited arm has 11 claims and the first
        # draft scored it on 14, borrowing three findings from an arm that was run under
        # a different rule. Two arms exist to be compared; contaminating one with the
        # other destroys the comparison.
        claims = [c for c in store.claims_for(rec["ticker"])
                  if _is_arm_claim(c, rec) or _is_computed_claim(c)]
        res = score_company(rec, claims, today=today)
        conf, conf_parts = confidence(rec, claims, coverage=res["coverage"],
                                      today=today)
        res["external_confidence"] = conf
        res["confidence_parts"] = conf_parts
        if apply:
            store.upsert_company({
                **{k: rec[k] for k in rec},
                "external_score": res["external_score"],
                "external_confidence": conf,
                "distinct_domains": res["evidence"].get("domains", 0),
                "claims_total": len(claims),
                "claims_verified": sum(
                    1 for c in claims if c.get("verify_status") == "VERIFIED_LOCAL"),
                "claims_self_attested": sum(
                    1 for c in claims if c.get("verify_status") == "SELF_ATTESTED"),
                "claims_unverifiable": sum(
                    1 for c in claims if c.get("verify_status") == "UNVERIFIABLE"),
            })
        out.append(res)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Compute the external quality score")
    ap.add_argument("--version", required=True, help="research_version to score")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)

    results = score_all(research_version=args.version, apply=args.apply)
    if not results:
        print(f"no company records at research_version {args.version!r}")
        return 1

    print(f"framework: {TOTAL_POINTS} points over {len(DIMENSIONS)} dimensions "
          f"+ evidence quality")
    print(f"not scored on purpose: {list(UNSCORED_FIELDS)}")
    print(f"coverage floor: {config.EXTERNAL_MIN_COVERAGE}\n")
    for r in results:
        norm = ("withheld" if r["external_normalized"] is None
                else f"{r['external_normalized']:.1f}")
        print(f"{r['ticker']:<6} score {r['external_score']:>5.1f}  "
              f"normalized {norm:>8}  coverage {r['coverage']:.3f}  "
              f"conf {r['external_confidence']}")
        print(f"       earned {r['points_earned']:.1f} / available "
              f"{r['points_available']:.0f} / applicable {r['points_applicable']:.0f}"
              f"   {'INSUFFICIENT_DATA' if r['insufficient'] else ''}")
        for dim, d in r["dimensions"].items():
            if dim == "evidence_quality":
                print(f"       {dim:<22} {d['earned']:>5.1f} / {d['max']:<3} {d['fields']}")
            else:
                avail = f"{d['available']:.0f}/{d['max']}"
                print(f"       {dim:<22} {d['earned']:>5.1f} / {d['max']:<3} "
                      f"(available {avail})")
        if r["unbacked_fields"]:
            print(f"       asserted but uncited, not scored: {r['unbacked_fields']}")
    if not args.apply:
        print("\nDRY RUN - nothing written. Re-run with --apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
