"""Deterministic flags where the three sources of truth disagree.

Computed HERE, never returned by Codex, because a flag is a conclusion and conclusions
are ours. Each rule reads three inputs: what the numbers show (the measured half), what
the company says (the judged half), and what the world says (the external record).

## Two rules that shape every flag below

**A flag needs VERIFIED evidence, not an assertion.** A flag that fires on an uncited
categorical is E39 wearing a warning label. Every rule that reads an external field also
requires at least one claim citing that field which we fetched and matched ourselves.

**UNKNOWN never fires a negative flag, but "we looked and could not establish it" is
not UNKNOWN-with-nothing-behind-it.** VRT is the case: the local model scored SG 19/20,
and external research at depth 3 cited Eaton's and Schneider's own growth specifically
to block the inference that Vertiv's growth is share capture. The capture field is
honestly UNKNOWN, and there are CONTRADICTS claims sitting behind that UNKNOWN. That
earns `UNVERIFIED_CORE_THESIS` - a flag and a confidence cap - and it does NOT earn a
points deduction, because failing to confirm a thesis is not the same as refuting it.
"""
from __future__ import annotations

from . import schema as S

#: A measured valuation at or above this (of VA's 15) reads as "cheap" for VALUE_TRAP.
VA_CHEAP_POINTS = 11
#: Judged-half thresholds at which a local conclusion is strong enough to contradict.
SG_HIGH = 16
BQ_HIGH = 11
#: 3-year revenue CAGR below this is weak growth for GROWTH_CONTRADICTION.
WEAK_CAGR = 0.05
#: Share of a company's claims that may be UNVERIFIABLE before it is a fabrication risk.
FABRICATION_RATE = 0.10
#: Peers needed before a risk level can be called worse-than-industry. Below this the
#: comparison is unmeasurable, and an unmeasurable comparison is not a passed one.
MIN_PEERS_FOR_RISK = 4


def _verified(claims: list[dict], field: str) -> list[dict]:
    return [c for c in claims
            if c.get("field") == field and c.get("verify_status") == "VERIFIED_LOCAL"]


def _domains(claims: list[dict]) -> int:
    return len({c.get("independence_domain") for c in claims
                if c.get("independence_domain")})


def _contradicting(claims: list[dict], field: str) -> list[dict]:
    return [c for c in _verified(claims, field) if c.get("stance") == "CONTRADICTS"]


def _worse_than_peers(field: str, value: str,
                      peers: list[dict] | None) -> tuple[bool, str]:
    """Is this company's risk strictly worse than its industry peers' typical level?

    Returns (fires, human detail). With fewer than MIN_PEERS peers the answer is NO -
    an unmeasurable comparison is not a passed comparison, the same rule the framework
    applies to peer multiples.
    """
    if not peers or len(peers) < MIN_PEERS_FOR_RISK:
        return False, f"no peer context ({len(peers or [])} peers < {MIN_PEERS_FOR_RISK})"
    levels = [p.get(field) for p in peers if p.get(field) not in (None, S.UNKNOWN)]
    if len(levels) < MIN_PEERS_FOR_RISK:
        return False, f"only {len(levels)} peers carry {field}"
    # The scales run worst-first, so a LOWER ordinal is a WORSE risk.
    mine = S.ordinal(field, value)
    peer_ords = sorted(o for o in (S.ordinal(field, x) for x in levels) if o is not None)
    if mine is None or not peer_ords:
        return False, "unscoreable"
    median = peer_ords[len(peer_ords) // 2]
    if mine < median:
        return True, (f"worse than the industry median ({value} vs "
                      f"{S.VOCABULARIES[field][median]} across {len(peer_ords)} peers)")
    return False, (f"at or better than the industry median across "
                   f"{len(peer_ords)} peers")


def evaluate(local: dict, external: dict, claims: list[dict],
             peers: list[dict] | None = None) -> list[dict]:
    """Flags for one company.

    `local` is a scores.parquet row (sg, bq, va, revenue_cagr_3y, stress_verdict...),
    `external` a company_external row, `claims` that company's claims for this arm.
    Returns a list of {flag, reason, claim_ids} - never bare strings, because a flag a
    reader cannot audit is a rumour.
    """
    out: list[dict] = []

    def fire(flag: str, reason: str, cited: list[dict] | None = None) -> None:
        out.append({"flag": flag, "reason": reason,
                    "claim_ids": sorted(c["claim_id"] for c in (cited or []))})

    sg, bq, va = local.get("sg"), local.get("bq"), local.get("va")
    cagr = local.get("revenue_cagr_3y")

    # ---------------------------------------------------------------- growth
    # The judged half is confident about growth, the measured half is not, and external
    # research found nothing forward-looking to reconcile them.
    if sg is not None and sg >= SG_HIGH and cagr is not None and cagr < WEAK_CAGR:
        forward = (_verified(claims, "demand_visibility")
                   + _verified(claims, "company_specific_capture"))
        if not forward:
            fire("GROWTH_CONTRADICTION",
                 f"SG {sg} with 3y revenue CAGR {cagr:.1%} and no external demand or "
                 f"capture evidence to explain the gap")

    # ------------------------------------------------------------------ moat
    moat = external.get("current_moat_strength")
    if bq is not None and bq >= BQ_HIGH and moat in ("WEAK", "MODERATE"):
        cited = _verified(claims, "current_moat_strength")
        if cited:
            fire("MOAT_CONTRADICTION",
                 f"BQ {bq}/15 against an externally evidenced {moat} moat", cited)

    traj = external.get("moat_trajectory")
    if traj in ("WEAKENING", "DETERIORATING"):
        cited = _verified(claims, "moat_trajectory")
        if cited and _domains(cited) >= 1:
            fire("COMPETITIVE_POSITION_DETERIORATING",
                 f"moat trajectory {traj} on {len(cited)} verified claim(s) across "
                 f"{_domains(cited)} domain(s)", cited)

    # ------------------------------------------------------------------ risk
    #
    # PEER-RELATIVE, not absolute. E44 measured why: on an absolute threshold
    # REGULATORY_IMPAIRMENT fired for 39 of 40 companies and, inside regional_banking,
    # both risk flags fired for 19 of 19 - two distinct flag-sets across nineteen banks.
    # "Banking is regulated" is an industry constant, not a finding about a bank, and a
    # sub-test constant across every company is precisely the symptom E30 exists to
    # catch. On the absolute rule, 67 of E44's 74 flags were these two.
    #
    # A risk flag now requires the company to be WORSE THAN ITS INDUSTRY PEERS. With no
    # peer context supplied the flag cannot fire at all - silence is correct, because
    # without peers there is no way to tell a company signal from an industry constant.
    for field, flag in (("regulatory_risk", "REGULATORY_IMPAIRMENT"),
                        ("disruption_risk", "TECHNOLOGY_DISRUPTION"),
                        ("technology_risk", "TECHNOLOGY_DISRUPTION")):
        value = external.get(field)
        if value not in ("ELEVATED", "SEVERE"):
            continue
        cited = _verified(claims, field)
        if not cited or any(f["flag"] == flag for f in out):
            continue
        worse, detail = _worse_than_peers(field, value, peers)
        if worse:
            fire(flag, f"{field} {value} with verified evidence, {detail}", cited)

    # ------------------------------------------------------------ value trap
    #
    # E08 tested the value-trap hypothesis on MEASURED inputs alone and it failed AND
    # INVERTED. This is a different hypothesis - it adds externally evidenced moat
    # deterioration - so it is a new test and not a rescue of E08, and it ships
    # pre-registered with E08's inversion printed beside it. It is a FLAG, never a
    # points deduction.
    if (va is not None and va >= VA_CHEAP_POINTS
            and traj in ("WEAKENING", "DETERIORATING")
            and external.get("cheapness_quality") == "STRUCTURAL"):
        cited = _verified(claims, "moat_trajectory") + _verified(claims,
                                                                "cheapness_quality")
        if cited:
            fire("VALUE_TRAP_RISK",
                 f"VA {va}/15 (cheap) with moat trajectory {traj} and cheapness read "
                 f"as STRUCTURAL. NOTE: E08 tested this on measured inputs alone and "
                 f"it failed and inverted; this variant is unvalidated.", cited)

    # ------------------------------------------------- unverified core thesis
    #
    # The distinction that keeps UNKNOWN honest. A field left UNKNOWN with nothing
    # behind it means nobody looked, and earns no flag. A field left UNKNOWN with
    # CONTRADICTS claims behind it means somebody looked and could not establish it -
    # which is worth saying out loud when the judged half is confident about the same
    # thing.
    if (external.get("research_depth") or 0) >= 2:
        for field, judged, threshold in (("company_specific_capture", sg, SG_HIGH),
                                         ("market_share_direction", sg, SG_HIGH),
                                         ("current_moat_strength", bq, BQ_HIGH)):
            if external.get(field) != S.UNKNOWN or judged is None or judged < threshold:
                continue
            blocking = _contradicting(claims, field)
            if blocking:
                fire("UNVERIFIED_CORE_THESIS",
                     f"{field} could not be established at research depth "
                     f"{external.get('research_depth')} despite {len(blocking)} "
                     f"contradicting claim(s), while the judged half scored "
                     f"{judged}", blocking)
                break

    # ------------------------------------------------------------- fabrication
    if claims:
        bad = [c for c in claims if c.get("verify_status") == "UNVERIFIABLE"]
        if len(bad) / len(claims) > FABRICATION_RATE:
            fire("EVIDENCE_FABRICATION_RISK",
                 f"{len(bad)} of {len(claims)} claims were fetched and their quote was "
                 f"not found in the source", bad)

    # --------------------------------------------------------- balance sheet
    # NOT reimplemented. stress_verdict is already a measured column produced by
    # clab/scoring/stress.py, and a second derivation of one quantity is how
    # dilution_yoy came to read +32.5% across the whole universe.
    if local.get("stress_verdict") == "FAIL":
        fire("BALANCE_SHEET_STRESS", "measured stress test verdict is FAIL")

    return out


def flags_for(local: dict, external: dict, claims: list[dict],
              peers: list[dict] | None = None) -> list[str]:
    """Just the flag names, deduped and ordered as schema.FLAGS declares them."""
    got = {f["flag"] for f in evaluate(local, external, claims, peers=peers)}
    return [f for f in S.FLAGS if f in got]
