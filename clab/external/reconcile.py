"""The only path by which external evidence may move a point.

Everything else in this package validates, contradicts or scores. This module is the
single place where the 94-point framework changes because of something the world said,
and it is deliberately the most constrained code here.

## The four properties that make it allowable at all

**Rule-based.** Five written rules, no model in the loop, no judgement call at runtime.
A reader can predict every adjustment from the record.

**Evidence-gated.** Every rule requires claims we FETCHED AND MATCHED ourselves.
A SELF_ATTESTED claim backs a score but may not move one - the bar to change the
incumbent's answer is higher than the bar to record our own.

**Capped.** `|dSG| <= 2`, `|dBQ| <= 2`, `|dSG| + |dBQ| <= 3` out of 35 judged points.
External research can tilt the judged half; it cannot rewrite it.

**Reversible.** Every firing writes a ledger row with before, after, rule and claim ids,
so the pre-reconciliation book is always recomputable and the V2-vs-V3 comparison stays
honest.

## What deliberately does NOT move a point

**Absence.** `research_depth == 0` moves nothing, and neither does UNKNOWN. Absence of
external research is not bearish - it is the difference between "we looked and found
trouble" and "we have not looked", and collapsing the two would let an unresearched
company be punished for our budget.

**A thesis we could not confirm.** VRT is the case: SG 19/20 from the judged half, and
external research at depth 3 that cited competitors' own growth specifically to block
the inference that Vertiv's growth is share capture. That earns R5 - a flag and a
confidence cap - and NOT a deduction. Failing to confirm a thesis is not refuting it,
and a system that deducts for the difference will quietly punish every company whose
industry has no public share data.

**A company with no external score.** A record below `EXTERNAL_MIN_COVERAGE` has too
little of the picture evidenced to have earned an opinion about someone else's. E42
arm 1 cleared the confidence threshold at 0.845 on 38% coverage, which is exactly the
combination this precondition exists to refuse.
"""
from __future__ import annotations

from .. import config

#: A rule may only cite claims we fetched and matched.
REQUIRED_STATUS = "VERIFIED_LOCAL"


def _cited(claims: list[dict], field: str, stance: str | None = None) -> list[dict]:
    out = [c for c in claims if c.get("field") == field
           and c.get("verify_status") == REQUIRED_STATUS]
    if stance:
        out = [c for c in out if c.get("stance") == stance]
    return out


def _domains(claims: list[dict]) -> int:
    return len({c.get("independence_domain") for c in claims
                if c.get("independence_domain")})


def preconditions(external: dict, scored: dict) -> list[str]:
    """Reasons this company may not be reconciled at all. Empty means it may."""
    blocked = []
    depth = external.get("research_depth") or 0
    if depth < config.EXTERNAL_MIN_DEPTH_FOR_ADJUST:
        blocked.append(f"research_depth {depth} < "
                       f"{config.EXTERNAL_MIN_DEPTH_FOR_ADJUST}")
    conf = scored.get("external_confidence")
    if conf is None or conf < config.EXTERNAL_MIN_CONFIDENCE_FOR_ADJUST:
        blocked.append(f"confidence {conf} < "
                       f"{config.EXTERNAL_MIN_CONFIDENCE_FOR_ADJUST}")
    cov = scored.get("coverage")
    if cov is None or cov < config.EXTERNAL_MIN_COVERAGE:
        blocked.append(f"coverage {cov} < {config.EXTERNAL_MIN_COVERAGE}; a record with "
                       f"no external score has not earned an opinion about the judged "
                       f"half")
    return blocked


def _rules(local: dict, external: dict, claims: list[dict]) -> list[dict]:
    sg, bq = local.get("sg"), local.get("bq")
    cagr = local.get("revenue_cagr_3y")
    capture = external.get("company_specific_capture")
    traj = external.get("moat_trajectory")
    out: list[dict] = []

    # R1 - the judged half is confident about growth, external evidence says the company
    # is not the one capturing it. Requires an actual LOW/NONE reading, never UNKNOWN.
    if sg is not None and sg >= 16 and capture in ("LOW", "NONE"):
        cited = _cited(claims, "company_specific_capture", "CONTRADICTS") \
            + _cited(claims, "market_share_direction", "CONTRADICTS")
        if len(cited) >= 2 and _domains(cited) >= 2:
            out.append({"rule_id": "R1_SG_CAPTURE_UNCONFIRMED", "component": "SG",
                        "delta": -2, "claims": cited,
                        "why": f"SG {sg} with externally evidenced capture {capture}"})

    # R2 - external evidence confirms capture the judged half under-credited, and the
    # measured growth agrees. All three must line up.
    if sg is not None and sg < 20 and capture == "HIGH":
        cited = _cited(claims, "company_specific_capture") \
            + _cited(claims, "market_share_direction")
        if len(cited) >= 2 and cagr is not None and cagr >= 0.10:
            out.append({"rule_id": "R2_SG_CAPTURE_CONFIRMED", "component": "SG",
                        "delta": +1, "claims": cited,
                        "why": f"capture HIGH on {len(cited)} verified claims with "
                               f"3y CAGR {cagr:.1%}"})

    # R3 - the FICO shape. A high judged moat against evidenced deterioration.
    if bq is not None and bq >= 11 and traj in ("WEAKENING", "DETERIORATING"):
        cited = _cited(claims, "moat_trajectory")
        if len(cited) >= 2 and _domains(cited) >= 2:
            out.append({"rule_id": "R3_MOAT_TRAJECTORY_WEAKENING", "component": "BQ",
                        "delta": -2, "claims": cited,
                        "why": f"BQ {bq}/15 against evidenced trajectory {traj}"})

    # R4 - the ASML shape: external evidence CONFIRMS a moat rather than adding to it.
    # Deliberately the hardest rule to fire - three claims across three domains - and
    # deliberately worth only +1. Confirmation should mostly raise confidence, not score.
    if bq is not None and bq >= 10 and traj in ("STRENGTHENING", "STABLE"):
        cited = _cited(claims, "moat_trajectory") + _cited(claims,
                                                           "current_moat_strength")
        if len(cited) >= 3 and _domains(cited) >= 3:
            out.append({"rule_id": "R4_MOAT_CONFIRMED_EXTERNAL", "component": "BQ",
                        "delta": +1, "claims": cited,
                        "why": f"trajectory {traj} on {len(cited)} verified claims "
                               f"across {_domains(cited)} domains"})
    return out


def reconcile(local: dict, external: dict, claims: list[dict], scored: dict) -> dict:
    """What external evidence does to this company's SG and BQ. Never mutates input."""
    blocked = preconditions(external, scored)
    sg, bq = local.get("sg"), local.get("bq")
    result = {
        "ticker": external.get("ticker"),
        "blocked": blocked,
        "applied": [],
        "sg_before": sg, "bq_before": bq,
        "sg_after": sg, "bq_after": bq,
        "delta_sg": 0, "delta_bq": 0,
        "capped": False,
    }
    if blocked:
        return result

    fired = _rules(local, external, claims)
    d_sg = d_bq = 0
    applied = []
    for rule in fired:
        delta = rule["delta"]
        comp = rule["component"]
        # Per-component cap, then the joint cap. A rule that would breach a cap is
        # recorded as capped rather than silently trimmed to a different number.
        if comp == "SG":
            if abs(d_sg + delta) > config.EXTERNAL_MAX_DELTA_SG:
                result["capped"] = True
                continue
            if abs(d_sg + delta) + abs(d_bq) > config.EXTERNAL_MAX_DELTA_TOTAL:
                result["capped"] = True
                continue
            d_sg += delta
        else:
            if abs(d_bq + delta) > config.EXTERNAL_MAX_DELTA_BQ:
                result["capped"] = True
                continue
            if abs(d_sg) + abs(d_bq + delta) > config.EXTERNAL_MAX_DELTA_TOTAL:
                result["capped"] = True
                continue
            d_bq += delta
        applied.append(rule)

    # A component cannot go below zero or above its maximum. Clamping here is not the
    # same as clamping a model's score - the rule's delta is ours and bounded; this only
    # stops arithmetic running off the end of a component.
    sg_after = None if sg is None else max(0, min(20, sg + d_sg))
    bq_after = None if bq is None else max(0, min(15, bq + d_bq))
    result.update({
        "applied": [{"rule_id": r["rule_id"], "component": r["component"],
                     "delta": r["delta"], "why": r["why"],
                     "claim_ids": sorted(c["claim_id"] for c in r["claims"])}
                    for r in applied],
        "sg_after": sg_after, "bq_after": bq_after,
        "delta_sg": 0 if sg is None else sg_after - sg,
        "delta_bq": 0 if bq is None else bq_after - bq,
    })
    return result


def ledger_rows(result: dict, request_id: str | None = None) -> list[dict]:
    """Ledger rows for `store.log_reconciliation`. Reversibility lives here: before,
    after, delta, rule and the claims that justified it."""
    rows = []
    for r in result["applied"]:
        comp = r["component"]
        before = result[f"{comp.lower()}_before"]
        after = result[f"{comp.lower()}_after"]
        rows.append({"ticker": result["ticker"], "component": comp, "subtest": None,
                     "before_points": before, "after_points": after,
                     "delta": r["delta"], "rule_id": r["rule_id"],
                     "claim_ids": r["claim_ids"], "request_id": request_id})
    return rows
