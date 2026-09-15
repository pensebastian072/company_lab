"""The contract: closed vocabularies, record shapes, and the checks over them.

Everything in this package validates against this module, and so does the prompt handed
to Codex (docs/CODEX_EXTERNAL_PROMPT.md). If a vocabulary changes here it must change
there in the same commit, or the finalizer will start rejecting valid research.

Two rules are encoded rather than documented, because both have already cost this repo
a book:

1. UNKNOWN is a member of every ordinal vocabulary and is NOT the bottom of it.
   `ordinal()` returns None for UNKNOWN, never 0. Absence of evidence scoring as
   evidence of absence is how a system quietly turns "we did not look" into "it is
   bad".
2. Every categorical is closed. An out-of-vocabulary value is REJECTED, never coerced
   and never clamped - the same rule the rubric applies to out-of-range LLM scores.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

#: Bumped whenever a vocabulary or a required field changes. Recorded on every row and
#: echoed by Codex, so a payload built against an older contract is visible rather than
#: silently mis-parsed.
EXTERNAL_SCHEMA_VERSION = "1.0.0"

UNKNOWN = "UNKNOWN"

# --------------------------------------------------------------- vocabularies
#: Ordinal vocabularies, worst -> best. UNKNOWN is appended to every one of them and is
#: deliberately outside the ordering.
_ORDINALS: dict[str, tuple[str, ...]] = {
    "current_moat_strength": ("NONE", "WEAK", "MODERATE", "STRONG", "EXCEPTIONAL"),
    "competitive_position": ("LAGGARD", "CHALLENGER", "STRONG_NUMBER_TWO", "LEADER",
                             "DOMINANT"),
    "competitive_position_trend": ("DETERIORATING", "STABLE", "IMPROVING"),
    "moat_trajectory": ("DETERIORATING", "WEAKENING", "STABLE", "STRENGTHENING"),
    "industry_structural_growth": ("DECLINING", "FLAT", "MODERATE", "HIGH",
                                   "EXCEPTIONAL"),
    "company_specific_capture": ("NONE", "LOW", "MODERATE", "HIGH"),
    "demand_visibility": ("NONE", "LOW", "MODERATE", "HIGH"),
    "market_share_direction": ("LOSING", "FLAT", "GAINING"),
    "pricing_power": ("NONE", "LOW", "MODERATE", "HIGH"),
    # Risk scales are written best-FIRST like every other scale here, so `ordinal()`
    # is monotone across the whole module. `normalized()` inverts them by name via
    # INVERTED_FIELDS rather than by reversing a tuple a later reader would misread.
    "technology_risk": ("SEVERE", "ELEVATED", "MODERATE", "LOW"),
    "disruption_risk": ("SEVERE", "ELEVATED", "MODERATE", "LOW"),
    "regulatory_risk": ("SEVERE", "ELEVATED", "MODERATE", "LOW"),
    "cheapness_quality": ("STRUCTURAL", "TEMPORARY", "CYCLICAL", "NOT_CHEAP"),

    # ---- fields that live on an INDUSTRY object rather than a company record ----
    # Added 2026-09-02 after the first Codex delivery. The Phase 0 prompt told the
    # researcher these vocabularies were "CLOSED and enforced mechanically by
    # clab/external/schema.py" and they were not in this file at all, so all three
    # industry objects came back with `unknown field` from validate_categoricals. The
    # research was fine; the promise was false. Same class as the MG constant going
    # stale: a contract stated in prose that the code does not actually hold.
    #
    # `structural_growth` is the SAME SCALE as `industry_structural_growth` under the
    # name the industry object uses. Defined from the same tuple rather than retyped,
    # so the two cannot drift into disagreeing about what MODERATE means.
    "structural_growth": ("DECLINING", "FLAT", "MODERATE", "HIGH", "EXCEPTIONAL"),
    # Harder to replicate is BETTER for the incumbent, so best-last like every other
    # scale here.
    "replication_difficulty": ("LOW", "MODERATE", "HIGH", "EXTREME"),
    # A risk, so it reads worst-first to match technology_risk / disruption_risk /
    # regulatory_risk, and normalized() returns 1.0 for LOW.
    "substitution_risk": ("SEVERE", "ELEVATED", "MODERATE", "LOW"),
}

#: Sector-object vocabularies. NOMINAL, not ordinal, and that is the point:
#: underinvestment and overinvestment are opposite ends of a cycle, not a good/bad
#: axis. Underinvestment is good for incumbent pricing and bad for volume growth;
#: overinvestment is the reverse. Giving it an ordinal scale would let score.py add it
#: to a quality dimension as though more were better, which is false in both
#: directions. Added 2026-09-02 with the sector validator - it was another vocabulary
#: the Phase 0 prompt named and this file did not carry.
_NOMINALS_SECTOR: dict[str, tuple[str, ...]] = {
    "capital_cycle": ("UNDERINVESTMENT", "BALANCED", "OVERINVESTMENT", UNKNOWN),
}

#: Industry-object fields that mirror a company-record field under a different name.
#: Kept explicit so a reader can see the two names are one scale.
FIELD_SYNONYMS: dict[str, str] = {
    "structural_growth": "industry_structural_growth",
}

#: Vocabularies with no ordering. Membership is checked; no arithmetic is done on them.
_NOMINALS: dict[str, tuple[str, ...]] = {
    "stance": ("SUPPORTS", "CONTRADICTS", "CONTEXT"),
    "fact_or_inference": ("FACT", "INFERENCE"),
    "source_type": ("SEC_FILING", "EARNINGS_CALL", "INVESTOR_PRESENTATION", "REGULATOR",
                    "TRADE_PUBLICATION", "PRIMARY_DATA", "COMPANY_IR", "NEWS", "OTHER"),
    "independence_domain": ("COMPANY_IR", "COMPETITOR_FILING", "CUSTOMER", "SUPPLIER",
                            "REGULATOR", "TRADE_PRESS", "PRIMARY_DATA", "ACADEMIC"),
    "refresh_class": ("STRUCTURAL", "QUARTERLY", "EVENT_DRIVEN"),
    "verify_status": ("VERIFIED_LOCAL", "SELF_ATTESTED", "UNVERIFIABLE"),
}

#: Every categorical field Codex may return, mapped to its legal values (UNKNOWN added
#: to the ordinals, which are the only ones a researcher may legitimately abstain on).
VOCABULARIES: dict[str, tuple[str, ...]] = {
    **{k: v + (UNKNOWN,) for k, v in _ORDINALS.items()},
    **_NOMINALS,
    **_NOMINALS_SECTOR,
}

#: Every ordinal field, company and industry alike. Use one of the two sets below
#: instead wherever the answer depends on WHICH KIND of object is being scored.
ORDINAL_FIELDS: tuple[str, ...] = tuple(_ORDINALS)

#: Ordinals that live on an INDUSTRY object. Added 2026-09-02 with the Phase 0 ingest.
INDUSTRY_ORDINALS: tuple[str, ...] = (
    "structural_growth", "replication_difficulty", "substitution_risk")

#: Ordinals RETIRED from the company record: still a legal vocabulary so historical
#: rows parse and the field can still be supplied, but out of the scored set and out of
#: the coverage denominator.
#:
#: `cheapness_quality` was retired 2026-09-02 on measurement, not opinion. Across every
#: record ever stored - E42 both arms and the 40-company E43 batch - it came back
#: UNKNOWN in 42 of 46, and exactly ONE claim in the entire corpus cites it (FICO's
#: STRUCTURAL, backed by CFPB pricing scrutiny). Under the citation rule that is 1 of 43
#: answered.
#:
#: It is not a research failure. Valuation is already 15 measured points of the
#: framework, computed from multiples, peers and a reverse DCF, and there is rarely a
#: public document that says "this company is structurally cheap". Keeping it in the
#: denominator charged every company for a question that cannot be answered - it capped
#: external coverage at 12/13 = 0.923 and pushed companies under the 0.80 floor for
#: nothing. It survives as a stored field and as an input to VALUE_TRAP_RISK.
RETIRED_ORDINALS: tuple[str, ...] = ("cheapness_quality",)

#: Ordinals that live on a COMPANY record and are scored - the 12 a researcher answers.
#:
#: This split exists because ORDINAL_FIELDS silently grew from 13 to 16 when the
#: industry vocabularies were added, and anything using it as a company denominator
#: would have computed coverage over 16 fields a company never carries. A company with
#: all 13 answered would have read 0.813 instead of 1.000, and one with 11 answered
#: would have read 0.688 and failed the 0.80 gate it actually clears. Caught before
#: score.py was written; the same shape as the MG constant going stale under a name
#: that used to be right.
COMPANY_ORDINALS: tuple[str, ...] = tuple(
    f for f in _ORDINALS
    if f not in INDUSTRY_ORDINALS and f not in RETIRED_ORDINALS)

#: Everything a company record may legally CARRY, retired fields included. finalize.py
#: accepts these; only COMPANY_ORDINALS are scored and counted.
COMPANY_ORDINALS_ALL: tuple[str, ...] = tuple(
    f for f in _ORDINALS if f not in INDUSTRY_ORDINALS)

#: Fields whose vocabulary reads worst-first for a human but whose SCALE already runs
#: best-first here. Kept as an explicit set so the intent survives a later edit to the
#: tuples above: these are the ones where a HIGH label is BAD for the company.
INVERTED_FIELDS: frozenset[str] = frozenset()

#: Free-text fields, with the caps the prompt states. Enforced, not suggested: an agent
#: that returns a 40 kB bear case has written an essay instead of a finding, and the
#: workbook would be unreadable.
TEXT_LIMITS: dict[str, int] = {
    "why_is_it_cheap": 400,
    "bull_case": 800,
    "bear_case": 800,
    "major_thesis_risk": 300,
    "thesis_break_condition": 300,
}

#: Research depth. 0 is cache-reuse, not "no research" - a company nobody has ever
#: looked at has NO record at all, which is a different state and must stay different.
DEPTH_LABELS: dict[int, str] = {
    0: "cache_reuse", 1: "lightweight", 2: "normal", 3: "deep", 4: "forensic",
}
MIN_DEPTH, MAX_DEPTH = 0, 4

#: Contradiction flags. Deterministic and computed locally in contradiction.py - Codex
#: never raises one, because a flag is a conclusion and conclusions are ours.
FLAGS: tuple[str, ...] = (
    "GROWTH_CONTRADICTION",
    "MOAT_CONTRADICTION",
    "VALUE_TRAP_RISK",
    "REGULATORY_IMPAIRMENT",
    "TECHNOLOGY_DISRUPTION",
    "COMPETITIVE_POSITION_DETERIORATING",
    "UNVERIFIED_CORE_THESIS",
    "EVIDENCE_FABRICATION_RISK",
    #: Computed from the MEASURED `stress_verdict` column rather than from external
    #: research - contradiction.py does not re-derive it. It was missing from this
    #: tuple at first, and because `flags_for` filters to this order the flag was
    #: computed and then silently discarded. Reusing an existing derivation is a reason
    #: not to reimplement a flag, never a reason not to surface it.
    "BALANCE_SHEET_STRESS",
)

#: The 11 GICS sectors as directory-safe ids.
SECTOR_IDS: tuple[str, ...] = (
    "information_technology", "health_care", "financials", "consumer_discretionary",
    "communication_services", "industrials", "consumer_staples", "energy", "utilities",
    "real_estate", "materials",
)


# --------------------------------------------------------------- helpers
def is_valid(field_name: str, value: Any) -> bool:
    """Membership test. An unknown FIELD is a programming error, so it raises; an
    unknown VALUE is bad input, so it returns False and the caller rejects the row."""
    try:
        vocab = VOCABULARIES[field_name]
    except KeyError as exc:
        raise KeyError(f"no vocabulary for field {field_name!r}") from exc
    return isinstance(value, str) and value in vocab


def ordinal(field_name: str, value: Any) -> int | None:
    """Position of `value` in its ordinal vocabulary, or None.

    None for UNKNOWN, None for a value outside the vocabulary, None for a nominal
    field. Callers must treat None as NO_DATA and must never substitute 0 - that
    substitution is the single most damaging bug available in this layer, because it
    silently converts every unresearched company into a maximally bad one.
    """
    scale = _ORDINALS.get(field_name)
    if scale is None or not isinstance(value, str) or value not in scale:
        return None
    return scale.index(value)


def ordinal_max(field_name: str) -> int | None:
    """Top index of an ordinal scale, for normalising `ordinal()` to 0-1."""
    scale = _ORDINALS.get(field_name)
    return None if scale is None else len(scale) - 1


def normalized(field_name: str, value: Any) -> float | None:
    """`ordinal()` mapped to 0.0-1.0 where 1.0 always means "good for the company".

    None stays None. Every ordinal scale in this module is already written best-last,
    including the risk scales (SEVERE ... LOW), so no inversion is needed today;
    INVERTED_FIELDS remains the hook if a future scale is written the other way.
    """
    idx = ordinal(field_name, value)
    top = ordinal_max(field_name)
    if idx is None or not top:
        return None
    frac = idx / top
    return 1.0 - frac if field_name in INVERTED_FIELDS else frac


# --------------------------------------------------------------- records
@dataclass(frozen=True)
class Claim:
    """One sourced finding. The unit of evidence, and the unit of verification.

    `excerpt` is the surrounding text the researcher says it read. `quote` must appear
    within it. That check is cheap and catches quote fabrication; it does NOT catch
    excerpt fabrication, which is why `verify.py` re-fetches a sample of source_urls
    and why the audited rate is reported beside every score rather than assumed away.
    """
    claim_id: str
    field: str
    text: str
    source_url: str | None = None
    source_title: str | None = None
    source_date: str | None = None
    source_type: str | None = None
    independence_domain: str | None = None
    quote: str | None = None
    excerpt: str | None = None
    # NULL is a real value here and means "the researcher did not label it". These
    # defaulted to CONTEXT and INFERENCE until E78 measured what a silent default does
    # to a field nobody sets: two whole runs read as context-only evidence when they had
    # simply never used the label. Do not restore a default.
    stance: str | None = None
    fact_or_inference: str | None = None
    # Assigned locally by verify.py. NEVER accepted from the payload: a researcher
    # marking its own work verified is not verification.
    verify_status: str = "UNVERIFIABLE"
    overlap: float | None = None
    ticker: str | None = None
    industry_id: str | None = None


@dataclass
class CompanyExternal:
    """The finalized per-company record. Every number on it is computed locally."""
    ticker: str
    cik: str | None = None
    sector_id: str | None = None
    industry_id: str | None = None
    subindustry_id: str | None = None
    research_depth: int = 0
    categoricals: dict[str, str] = field(default_factory=dict)
    texts: dict[str, str] = field(default_factory=dict)
    claims: list[Claim] = field(default_factory=list)
    external_score: float | None = None
    external_confidence: float | None = None
    distinct_domains: int = 0
    flags: list[str] = field(default_factory=list)
    request_id: str | None = None


def validate_categoricals(values: dict[str, Any]) -> list[str]:
    """Return a list of human-readable rejection reasons; empty means clean.

    Returns reasons rather than raising because a single bad field must cost one
    company, not the whole payload - and because every rejection is written into the
    manifest with its reason. Nothing is silently dropped.
    """
    reasons: list[str] = []
    for name, value in values.items():
        if name not in VOCABULARIES:
            reasons.append(f"unknown field {name!r}")
            continue
        if not is_valid(name, value):
            reasons.append(
                f"{name}={value!r} not in vocabulary "
                f"({', '.join(VOCABULARIES[name])})")
    return reasons


def validate_texts(values: dict[str, Any]) -> list[str]:
    """Length caps on the free-text fields."""
    reasons: list[str] = []
    for name, limit in TEXT_LIMITS.items():
        v = values.get(name)
        if v is None:
            continue
        if not isinstance(v, str):
            reasons.append(f"{name} is {type(v).__name__}, expected str")
        elif len(v) > limit:
            reasons.append(f"{name} is {len(v)} chars, cap is {limit}")
    return reasons


def validate_depth(depth: Any) -> list[str]:
    """`isinstance(True, int)` is True in Python, so bool is rejected explicitly - the
    same NaN/bool class of silent-degradation bug the rubric already guards against."""
    if isinstance(depth, bool) or not isinstance(depth, int):
        return [f"research_depth is {depth!r}, expected int {MIN_DEPTH}-{MAX_DEPTH}"]
    if not MIN_DEPTH <= depth <= MAX_DEPTH:
        return [f"research_depth {depth} outside {MIN_DEPTH}-{MAX_DEPTH}"]
    return []
