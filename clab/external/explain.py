"""Why this company scored what it scored, in a sentence a person can argue with.

A ranking that cannot say why is a black box, and a black box asking to be trusted with
capital allocation is worse than no ranking at all. Every company in the book gets a
score and a rank; this module makes every one of them explain itself.

## What it is not

It is not an LLM summary. Every clause below is generated from the same numbers that
produced the score, so the explanation cannot drift from the arithmetic and cannot
flatter it. If the text says "moat trajectory weakening cost it", `moat_trajectory` is
in the record and the dimension is in the score.

## The order it says things in

Strongest contributor, then weakest, then what actively counted against it, then what
could not be established and what would settle that. That order is deliberate: a reader
scanning forty rows wants the reason it is high or low FIRST, and the caveats after.

## Coverage is a caveat, never a silence

An earlier draft withheld the extrapolated score below the coverage floor and the
result was reported as "38 of 40 got no external score", which turned a property into a
gate. Every company is ranked. Thin evidence is SAID, in the explanation and in a
column beside the number, and the reader discounts it.
"""
from __future__ import annotations

from . import schema as S

#: How a dimension is named to a human.
DIMENSION_LABELS: dict[str, str] = {
    "competitive_position": "competitive position",
    "moat_strength": "moat strength",
    "moat_trajectory": "moat trajectory",
    "structural_demand": "structural demand",
    "company_capture": "company capture",
    "risk_resilience": "risk resilience",
    "evidence_quality": "evidence quality",
}

#: What would settle each field, by industry family. From Codex's own E44 report, which
#: named the specific disclosure for all 40 companies rather than shrugging.
WOULD_SETTLE: dict[str, dict[str, str]] = {
    "market_share_direction": {
        "regional_banking": "consecutive FDIC Summary of Deposits institution-by-market "
                            "tables on identical geographies",
        "pc_insurance": "NAIC direct-written-premium by line and state for this company "
                        "and named competitors across two periods",
        "life_insurance": "LIMRA or NAIC product-level premium and policy-count series "
                          "against named peers",
        "refining": "EIA throughput and capacity by named operator and region, adjusted "
                    "for closures and turnarounds",
        "midstream": "named-competitor basin throughput or contracted capacity on "
                     "identical asset boundaries",
        "upstream_oil_gas": "EIA or state-regulator production series for this company "
                            "and named basin peers",
        "payments": "named-competitor processed volume or transaction count plus the "
                    "same-rail denominator",
        "semiconductor_equipment": "SEMI or customer procurement share in this "
                                   "company's exact process subcategories",
        "ai_accelerators": "named-competitor datacenter-accelerator revenue or shipments "
                           "plus a same-scope total-market series",
        "cloud_infrastructure": "consecutive independent infrastructure-cloud share "
                                "series across the named providers",
        "cybersecurity": "independent named-vendor ARR or billings share in the same "
                         "security category",
        "us_credit_scoring": "GSE delivery share by score model across two periods",
    },
    "competitive_position_trend": {
        "*": "competitor-relative movement; current filings describe a company's own "
             "performance far better than its position against named peers",
    },
    "company_specific_capture": {
        "*": "a peer-normalised growth or share series, not absolute growth",
    },
}


def _settles(field: str, industry_id: str | None) -> str | None:
    table = WOULD_SETTLE.get(field)
    if not table:
        return None
    return table.get(industry_id or "") or table.get("*")


def _dimension_ranking(scored: dict) -> list[tuple[str, float, float, float]]:
    """(dimension, earned, available, fraction) sorted best fraction first.

    Ranked on the fraction EARNED OF WHAT WAS AVAILABLE, not of the maximum. A
    dimension nobody could evidence is not a weakness of the company, and calling it one
    would let thin research masquerade as a bad business.
    """
    out = []
    for dim, d in (scored.get("dimensions") or {}).items():
        avail = d.get("available") or 0
        if avail <= 0:
            continue
        out.append((dim, d.get("earned") or 0.0, avail, (d.get("earned") or 0.0) / avail))
    return sorted(out, key=lambda x: -x[3])


def explain(record: dict, scored: dict, gate: dict, flags_detail: list[dict],
            local: dict | None = None) -> str:
    """One paragraph saying why this company sits where it sits."""
    local = local or {}
    parts: list[str] = []
    ticker = record.get("ticker") or ""

    band = gate.get("conviction_band")
    score = gate.get("conviction_score")
    rank = gate.get("conviction_rank")
    n = gate.get("conviction_rank_n")
    head = f"{ticker} ranks {rank} of {n} on conviction {score} ({band})" \
        if rank else f"{ticker} scores {score} ({band})"
    ext = scored.get("external_score")
    if ext is not None:
        head += f", external quality {ext}/100"
    parts.append(head + ".")

    # --- what carried it, and what did not
    dims = _dimension_ranking(scored)
    if dims:
        best = dims[0]
        parts.append(f"Strongest: {DIMENSION_LABELS.get(best[0], best[0])} at "
                     f"{best[1]:.1f} of {best[2]:.0f} available.")
        if len(dims) > 1 and dims[-1][3] < 0.6:
            worst = dims[-1]
            parts.append(f"Weakest: {DIMENSION_LABELS.get(worst[0], worst[0])} at "
                         f"{worst[1]:.1f} of {worst[2]:.0f}.")

    # --- the moat sentence, which is the one this whole layer exists for
    moat = record.get("current_moat_strength")
    traj = record.get("moat_trajectory")
    cagr = local.get("revenue_cagr_3y")
    if traj in ("WEAKENING", "DETERIORATING"):
        sent = f"Moat reads {str(moat).lower()} today but {traj.lower()}"
        if isinstance(cagr, (int, float)) and cagr == cagr and cagr > 0.05:
            sent += (f" - and the accounts do not show it, with a "
                     f"{cagr:.1%} three-year revenue CAGR")
        parts.append(sent + ".")
    elif traj in ("STRENGTHENING", "STABLE") and moat not in (None, S.UNKNOWN):
        parts.append(f"Moat {str(moat).lower()} and {traj.lower()}.")

    # --- what actively cost it points
    pens = [p for p in (gate.get("penalties") or []) if p.get("points")]
    if pens:
        by_flag = {f["flag"]: f.get("reason", "") for f in flags_detail}
        bits = []
        for p in sorted(pens, key=lambda x: -x["points"]):
            reason = by_flag.get(p["flag"], "")
            bits.append(f"{p['flag']} (-{p['points']}"
                        + (f"; {reason.split(',')[0]}" if reason else "") + ")")
        parts.append("Cost points: " + "; ".join(bits) + ".")
    elif gate.get("penalties"):
        # reported but scoring zero - VALUE_TRAP_RISK, whose measured ancestor inverted
        names = ", ".join(p["flag"] for p in gate["penalties"])
        parts.append(f"Flagged but not scored: {names} (unvalidated - E08's measured "
                     f"version failed and inverted).")

    # --- what could not be established, and what would settle it
    unknown = [f for f in S.COMPANY_ORDINALS
               if record.get(f) in (None, S.UNKNOWN)]
    if unknown:
        ind = record.get("industry_id")
        named = []
        for f in unknown[:3]:
            fix = _settles(f, ind)
            named.append(f"{f}" + (f" (would need {fix})" if fix else ""))
        more = f" and {len(unknown) - 3} more" if len(unknown) > 3 else ""
        parts.append("Unestablished: " + "; ".join(named) + more + ".")

    cov = scored.get("coverage")
    if isinstance(cov, (int, float)):
        note = (" - thin, discount accordingly" if scored.get("insufficient_coverage")
                else "")
        parts.append(f"Evidence covers {cov:.0%} of the questions asked{note}.")

    return " ".join(parts)


def why_short(gate: dict, flags: list[str]) -> str:
    """A one-clause version for a narrow column: the single biggest reason."""
    pens = [p for p in (gate.get("penalties") or []) if p.get("points")]
    if pens:
        worst = max(pens, key=lambda p: p["points"])
        return f"{worst['flag']} (-{worst['points']})"
    short = gate.get("shortfalls") or []
    if short:
        return short[0]
    return "no shortfall; scored on evidence"
