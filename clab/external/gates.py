"""Conviction as a SCORE, not a bouncer.

The first version of this module answered one boolean: does the company clear
HIGH_CONVICTION_VERIFIED? Run over the E42 pilot it returned False, False, False. That
is not a useful answer from a ranking system. Every company stays in the ranking; the
question is never "are you allowed in", it is "how do you score on these factors".

So each condition is a scored criterion, not a veto, and each flag carries a severity
that costs points rather than slamming a door. A company with a weakening moat and a
regulatory problem does not vanish - it ranks below one without them, by an amount a
reader can see and argue with.

    conviction_score = criteria earned (0-100)  -  flag penalties, floored at 0

`HIGH_CONVICTION_VERIFIED` survives as the top BAND of that continuum plus a short list
of genuine disqualifiers, which is a much narrower claim than the old gate made.

## Why VALUE_TRAP_RISK costs zero points

E08 tested the value-trap hypothesis on measured inputs and it **failed and inverted** -
the apparently-cheap deteriorating companies did better, not worse. The external variant
adds evidenced moat deterioration, so it is a different hypothesis, but it is an
UNTESTED one. Deducting points for an unvalidated flag whose measured ancestor pointed
the other way would be acting on a belief this repo has already measured as wrong.

It is reported, ranked and shown. It scores nothing until its own pre-registered test
passes. That is the quant-research-gate rule applied to a flag instead of a model.
"""
from __future__ import annotations

from .. import config
from ..scoring import rubric
from . import schema as S

FE_FLOOR = 13
CONFIDENCE_FLOOR = 0.70
DEPTH_FLOOR = 3

#: Fields whose UNKNOWN at deep research depth is itself informative, and what each is
#: worth inside `core_fields_known`.
#:
#: NOT equal thirds. `company_specific_capture` is the question this entire layer was
#: built to answer - the VRT case exists because "the datacenter industry is growing"
#: and "Vertiv is capturing that growth" are different claims needing different
#: evidence. Weighting it as one of three made VRT rank FIRST at VERIFIED_HIGH with
#: capture unestablished, which is the exact confusion the case tests for.
CORE_FIELD_WEIGHTS: dict[str, float] = {
    "company_specific_capture": 0.5,
    "current_moat_strength": 0.25,
    "moat_trajectory": 0.25,
}
CORE_FIELDS = tuple(CORE_FIELD_WEIGHTS)

PASSING_BANDS = ("HIGH_CONVICTION", "EXCEPTIONAL")

#: The criteria and their weights, summing to 100. Each returns 0..max, and most are
#: CONTINUOUS rather than binary so that a near-miss ranks above a distant one.
CRITERIA_WEIGHTS: dict[str, int] = {
    "framework_band": 15,
    "financial_engine": 10,
    "survivability": 8,
    "framework_coverage": 7,
    "external_coverage": 12,
    "external_confidence": 12,
    "research_depth": 8,
    "moat_trajectory": 12,
    "core_fields_known": 16,
}
CRITERIA_TOTAL = sum(CRITERIA_WEIGHTS.values())

# --------------------------------------------------------------- conviction v2
#: E48 measured that the evidence terms reorder the conviction score more than every
#: substantive conclusion combined. Unpacking the weights shows that was a design choice
#: written down, not an emergent property, and that it rests on two double-counts and one
#: deeper defect.
#:
#: Effective allocation of v1's 100 points, after expanding `external_confidence` into its
#: own internals (0.30 domains + 0.30 verified + 0.25 coverage + 0.075 depth + 0.075
#: freshness):
#:
#:     how much we know (coverage)   31.0   <- counted THREE times
#:     how hard we looked (depth)     8.9   <- counted twice
#:     evidence quality               8.1
#:     what we concluded             12.0
#:     local measured half           40.0
#:
#: Coverage appears as `external_coverage` (12), again as `core_fields_known` (16, a
#: weighted subset of the same denominator), and again inside `external_confidence`
#: (0.25 x 12 = 3). Depth appears as `research_depth` (8) and inside confidence (0.9).
#:
#: The deeper defect is that `core_fields_known` scores whether a field is answered and
#: NOT what it says: `company_specific_capture` of NONE and of HIGH score identically on
#: its 8 points. Only `moat_trajectory` reads its own value. So of the 60 external points,
#: 12 read a conclusion and 48 read the existence of one.
#:
#: v2 counts each thing once and reads the conclusions:
#:   * `external_coverage` is dropped as a separate criterion - `core_fields_value` covers
#:     the fields that matter, weighted, and covers them better;
#:   * `evidence_quality` replaces `external_confidence` and excludes coverage and depth,
#:     so nothing is counted twice;
#:   * `core_fields_value` scores the VALUES of capture, moat strength and trajectory;
#:   * `competitive_position` joins as a second read conclusion.
#:
#: NOT SHIPPED. `evaluate()` still uses v1. See E52 - the four fields v2 leans on are
#: currently 0% filled in two sectors, so switching now would measure the E49 defect
#: rather than the design. The switch waits on E51.
CRITERIA_WEIGHTS_V2: dict[str, int] = {
    "framework_band": 15,
    "financial_engine": 10,
    "survivability": 8,
    "framework_coverage": 7,
    "evidence_quality": 10,      # domains + verified + freshness, NO coverage, NO depth
    "research_depth": 6,
    "core_fields_value": 32,     # what capture / moat strength / trajectory SAY
    "competitive_position": 12,  # a second conclusion actually read
}

#: What each core field's VALUE is worth inside `core_fields_value`, and what each value
#: scores. UNKNOWN sits at the middle, never at the bottom: an unanswered field must not
#: read as a bad answer, which is the rule the whole package runs on.
CORE_FIELD_VALUE_WEIGHTS: dict[str, float] = {
    "company_specific_capture": 0.40,
    "current_moat_strength": 0.30,
    "moat_trajectory": 0.30,
}

CORE_FIELD_VALUE_SCALES: dict[str, dict[str, float]] = {
    "company_specific_capture": {"HIGH": 1.0, "MODERATE": 0.7, "LOW": 0.3, "NONE": 0.0},
    "current_moat_strength": {"EXCEPTIONAL": 1.0, "STRONG": 0.8, "MODERATE": 0.5,
                              "WEAK": 0.2, "NONE": 0.0},
    "moat_trajectory": {"STRENGTHENING": 1.0, "STABLE": 0.8, "WEAKENING": 0.15,
                        "DETERIORATING": 0.0},
}

COMPETITIVE_POSITION_SCALE: dict[str, float] = {
    "DOMINANT": 1.0, "LEADER": 0.85, "STRONG_NUMBER_TWO": 0.6,
    "CHALLENGER": 0.35, "LAGGARD": 0.0,
}

#: What an UNKNOWN scores on a value scale. The middle, not the floor. A company nobody
#: could evidence is not a company with a bad answer, and v1's own rule that UNKNOWN never
#: lowers a score elsewhere in the package is preserved here.
UNKNOWN_VALUE = 0.4


#: Points deducted per flag. A severity, not a veto.
#:
#: EVIDENCE_FABRICATION_RISK is the heaviest because it is the only flag that impeaches
#: the evidence itself rather than the company - if a quote is not in its own source,
#: nothing else in the record can be relied upon either.
FLAG_PENALTY: dict[str, int] = {
    "EVIDENCE_FABRICATION_RISK": 25,
    "BALANCE_SHEET_STRESS": 15,
    "UNVERIFIED_CORE_THESIS": 12,
    "REGULATORY_IMPAIRMENT": 10,
    "TECHNOLOGY_DISRUPTION": 10,
    "MOAT_CONTRADICTION": 10,
    "GROWTH_CONTRADICTION": 10,
    "COMPETITIVE_POSITION_DETERIORATING": 8,
    # Zero on purpose. See the module docstring.
    "VALUE_TRAP_RISK": 0,
}

#: Bands over the conviction score. Named so they cannot be confused with the
#: framework's own bands, which answer a different question.
CONVICTION_BANDS: tuple[tuple[int, str], ...] = (
    (85, "VERIFIED_HIGH"),
    (70, "SUPPORTED"),
    (55, "QUALIFIED"),
    (35, "WATCH"),
    (0, "UNSUPPORTED"),
)

#: Conditions that keep the VERIFIED_HIGH LABEL off a company however well it scores.
#: They do not touch the score or the rank - the company keeps its position and its
#: points, and only the top label is withheld.
#:
#: Deliberately short. A disqualifier is a claim that no amount of other evidence can
#: compensate for, and only two flags qualify: one that impeaches the evidence itself,
#: and one that says the balance sheet may not survive.
HARD_DISQUALIFIERS = ("EVIDENCE_FABRICATION_RISK", "BALANCE_SHEET_STRESS")

#: ...and one condition that is not a flag: at DEEP research depth, an unestablished
#: company capture. "We looked hard and still cannot say whether this company captures
#: its market" and "verified high conviction" cannot both be true. It costs the label,
#: not the ranking.
CAPTURE_FIELD = "company_specific_capture"


def _band_for(score: float) -> str:
    for floor, name in CONVICTION_BANDS:
        if score >= floor:
            return name
    return CONVICTION_BANDS[-1][1]


def _scale(value, lo: float, hi: float) -> float:
    """Linear 0..1 between lo and hi, clamped. A near-miss must outrank a far miss."""
    if value is None:
        return 0.0
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    if v != v:                                   # NaN is not a measurement
        return 0.0
    if hi <= lo:
        return 1.0 if v >= hi else 0.0
    return max(0.0, min(1.0, (v - lo) / (hi - lo)))


#: Keys `criteria()` needs out of `scored`. A caller that omits one used to get a silent
#: zero from `_scale(None, ...)`, which is 24 of v1's 100 points vanishing without a word.
#:
#: That is exactly how E52's first two A/B runs were wrong: the harness passed a `scored`
#: dict holding `claims_total`/`claims_verified` (which v2 reads) and neither `coverage`
#: nor `external_confidence` (which v1 reads). v1 was measured at pooled sd 12.84 when its
#: real figure is 16.18, and the comparison was published handicapping the incumbent. The
#: second attempt fixed only half of it, because `company_external` has no `coverage`
#: column - it has to come from `score.score_company()`.
#:
#: The repo rule this violates is already written down: a default that covers a WIRING
#: error must be loud. Thin data is a fallback; an absent input is a bug.
REQUIRED_SCORED_KEYS = ("coverage", "external_confidence")


def criteria(local: dict, external: dict, scored: dict) -> dict[str, dict]:
    """Each criterion's earned points, its max, and a human note.

    Raises if `scored` is missing an evidence input rather than scoring it as zero.
    """
    missing = [k for k in REQUIRED_SCORED_KEYS if k not in scored]
    if missing:
        raise KeyError(
            f"criteria() needs {missing} in `scored` and they are absent. Omitting them "
            f"silently zeroes {sum(CRITERIA_WEIGHTS[c] for c in ('external_coverage', 'external_confidence'))}"
            f" of 100 points. `coverage` comes from score.score_company(...)['coverage'], "
            f"not from a company_external column - there is no such column.")
    out: dict[str, dict] = {}

    def put(key, frac, note):
        mx = CRITERIA_WEIGHTS[key]
        out[key] = {"earned": round(mx * max(0.0, min(1.0, frac)), 2), "max": mx,
                    "note": note}

    band = local.get("band")
    band_frac = {"EXCEPTIONAL": 1.0, "HIGH_CONVICTION": 0.85, "INVESTABLE": 0.6,
                 "WATCHLIST": 0.35, "WEAK": 0.15}.get(band, 0.0)
    put("framework_band", band_frac, f"band {band}")

    fe = local.get("fe")
    put("financial_engine", _scale(fe, 6, rubric.COMPONENTS["FE"][1]),
        f"FE {fe}/{rubric.COMPONENTS['FE'][1]} (floor {FE_FLOOR})")

    stress = local.get("stress_verdict")
    stress_frac = {"SURVIVES_COMFORTABLY": 1.0, "SURVIVES": 0.8, "STRESSED": 0.45,
                   "FAIL": 0.0}.get(stress, 0.5)
    put("survivability", stress_frac, f"stress {stress}")

    put("framework_coverage",
        _scale(local.get("coverage"), rubric.MIN_COVERAGE_FOR_BAND - 0.2,
               rubric.MIN_COVERAGE_FOR_BAND),
        f"framework coverage {local.get('coverage')}")

    put("external_coverage",
        _scale(scored.get("coverage"), config.EXTERNAL_MIN_COVERAGE - 0.3,
               config.EXTERNAL_MIN_COVERAGE),
        f"external coverage {scored.get('coverage')}")

    put("external_confidence",
        _scale(scored.get("external_confidence"), CONFIDENCE_FLOOR - 0.3,
               CONFIDENCE_FLOOR),
        f"confidence {scored.get('external_confidence')}")

    depth = external.get("research_depth") or 0
    put("research_depth", _scale(depth, 0, DEPTH_FLOOR), f"depth {depth}")

    traj = external.get("moat_trajectory")
    traj_frac = {"STRENGTHENING": 1.0, "STABLE": 0.8, S.UNKNOWN: 0.4,
                 "WEAKENING": 0.15, "DETERIORATING": 0.0}.get(traj, 0.4)
    put("moat_trajectory", traj_frac, f"trajectory {traj}")

    # Knowing is the thing conviction is made of. UNKNOWN still never lowers a SCORE
    # anywhere else in this package - it lowers this, which is a different quantity.
    # At shallow depth nobody claimed to have looked, so the silence says nothing and
    # the criterion is not charged for it.
    if depth < DEPTH_FLOOR:
        put("core_fields_known", 0.5,
            f"depth {depth} below {DEPTH_FLOOR}; core fields not chargeable")
    else:
        known = [f for f in CORE_FIELDS if external.get(f) not in (None, S.UNKNOWN)]
        frac = sum(CORE_FIELD_WEIGHTS[f] for f in known)
        put("core_fields_known", frac,
            f"{len(known)}/{len(CORE_FIELDS)} core fields established at depth {depth}"
            + ("" if len(known) == len(CORE_FIELDS)
               else f" (UNKNOWN: {[f for f in CORE_FIELDS if f not in known]})"))
    return out


def evaluate(local: dict, external: dict, scored: dict,
             flags: list[str]) -> dict:
    """Graded conviction for one company. Nobody is excluded from the ranking."""
    parts = criteria(local, external, scored)
    earned = sum(p["earned"] for p in parts.values())

    penalties = [{"flag": f, "points": FLAG_PENALTY.get(f, 0)}
                 for f in flags if f in FLAG_PENALTY]
    penalty = sum(p["points"] for p in penalties)
    score = max(0.0, round(earned - penalty, 2))
    band = _band_for(score)

    disqualified = [f for f in HARD_DISQUALIFIERS if f in flags]
    if ((external.get("research_depth") or 0) >= DEPTH_FLOOR
            and external.get(CAPTURE_FIELD) in (None, S.UNKNOWN)):
        disqualified.append(
            f"{CAPTURE_FIELD} unestablished at depth "
            f"{external.get('research_depth')}")
    verified_high = band == "VERIFIED_HIGH" and not disqualified

    # Kept so a reader can still see the individual shortfalls, but they no longer
    # decide anything on their own.
    shortfalls = [p["note"] for k, p in parts.items() if p["earned"] < p["max"] * 0.6]

    return {
        "ticker": local.get("ticker") or external.get("ticker"),
        "conviction_score": score,
        "conviction_band": band,
        "criteria_earned": round(earned, 2),
        "flag_penalty": penalty,
        "penalties": penalties,
        "criteria": parts,
        "shortfalls": shortfalls,
        "disqualified_by": disqualified,
        "high_conviction_verified": verified_high,
    }


def rank(rows: list[dict]) -> list[dict]:
    """Rank companies by conviction score, highest first, with ties broken by the
    unpenalised criteria so a flag never reorders two otherwise-identical companies
    arbitrarily."""
    ordered = sorted(rows, key=lambda r: (-r["conviction_score"],
                                          -r["criteria_earned"],
                                          str(r.get("ticker") or "")))
    for i, r in enumerate(ordered, 1):
        r["conviction_rank"] = i
        r["conviction_rank_n"] = len(ordered)
    return ordered


# ------------------------------------------------------------------ conviction v2
def criteria_v2(local: dict, external: dict, scored: dict) -> dict:
    """v2 criteria. Each thing counted once; the core conclusions read for their VALUE.

    Not wired into `evaluate()`. Built so the change can be measured against v1 before
    anything is switched - see E52.
    """
    out: dict[str, dict] = {}

    def put(key, frac, why):
        frac = max(0.0, min(1.0, float(frac)))
        out[key] = {"fraction": round(frac, 4),
                    "points": round(frac * CRITERIA_WEIGHTS_V2[key], 2),
                    "max": CRITERIA_WEIGHTS_V2[key], "why": why}

    # --- local half, unchanged from v1 in weight and meaning
    band = local.get("band")
    put("framework_band", 1.0 if band in PASSING_BANDS else
        (0.6 if band == "GOOD" else (0.3 if band == "WEAK" else 0.0)), f"band {band}")
    fe = local.get("fe")
    put("financial_engine", _scale(fe or 0, 8, 15), f"fe {fe}")
    put("survivability", 0.0 if local.get("stress_verdict") == "FAIL" else 1.0,
        f"stress {local.get('stress_verdict')}")
    put("framework_coverage", _scale(local.get("coverage") or 0, 0.5, 0.9),
        f"coverage {local.get('coverage')}")

    # --- evidence QUALITY only: no coverage, no depth, so nothing is counted twice
    claims = scored.get("claims_total") or 0
    verified = scored.get("claims_verified") or 0
    domains = external.get("distinct_domains") or 0
    q_ver = (verified / claims) if claims else 0.0
    q_dom = min(domains, 4) / 4
    put("evidence_quality", 0.5 * q_ver + 0.5 * q_dom,
        f"{verified}/{claims} verified, {domains} domains")

    depth = external.get("research_depth") or 0
    put("research_depth", _scale(depth, 0, DEPTH_FLOOR), f"depth {depth}")

    # --- the conclusions, read for what they SAY
    total = 0.0
    detail = []
    for field, w in CORE_FIELD_VALUE_WEIGHTS.items():
        v = external.get(field)
        scale = CORE_FIELD_VALUE_SCALES[field]
        frac = UNKNOWN_VALUE if v in (None, S.UNKNOWN) else scale.get(str(v), UNKNOWN_VALUE)
        total += w * frac
        detail.append(f"{field}={v}")
    put("core_fields_value", total, "; ".join(detail))

    pos = external.get("competitive_position")
    put("competitive_position",
        UNKNOWN_VALUE if pos in (None, S.UNKNOWN)
        else COMPETITIVE_POSITION_SCALE.get(str(pos), UNKNOWN_VALUE),
        f"position {pos}")
    return out


def conviction_v2(local: dict, external: dict, scored: dict,
                  flags: list[str] | None = None) -> dict:
    """v2 conviction score, same flag penalties and same bands as v1."""
    crit = criteria_v2(local, external, scored)
    earned = sum(c["points"] for c in crit.values())
    penalty = sum(FLAG_PENALTY.get(f, 0) for f in (flags or []))
    score = max(0.0, min(100.0, earned - penalty))
    return {"conviction_v2": round(score, 1), "band_v2": _band_for(score),
            "earned": round(earned, 2), "penalty": penalty, "criteria": crit}
