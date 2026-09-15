"""Which external fields a given industry cannot answer BY CONSTRUCTION.

## Why this exists, and why it is dangerous

E47 finished Utilities at 59 of 59 and `market_share_direction` came back UNKNOWN for
every one of them. That is the correct research answer - a rate-regulated utility holds a
legal franchise monopoly over retail load in its service territory, so there is no share
to gain or lose - but `score.py` computes `strict = earned / applicable` and counted those
5 points in `applicable` for all 59. The companies were charged for failing to answer a
question that has no answer.

So this module distinguishes two things the vocabulary currently collapses:

    UNKNOWN         we looked and could not establish it      -> stays in `applicable`
    NOT_APPLICABLE  the question is meaningless here          -> leaves `applicable`

## The direction of the risk

**Removing a field from `applicable` RAISES the score and RAISES coverage.** It is the
only edit in this layer that flatters a company for an absence, and E29 measured exactly
this failure mode in the measured half: nominating a judged sub-test converted every
model abstention into `NOT_APPLICABLE`, dropped it out of the coverage denominator, and
lifted companies over the 0.80 band gate - "a large, self-flattering effect from a
one-line edit".

The measured half's defence is `resolve_status`: a TWO-condition rule needing profile
nomination AND a genuinely absent value. This module copies it exactly.

    1. the INDUSTRY is nominated here, in code, with a written definitional argument; and
    2. the company's own value is UNKNOWN or absent.

Condition 1 is per-INDUSTRY and never per-company, so no single company can excuse itself
and every nomination is a visible claim about an industry's structure. Condition 2 means
a company that DID answer the question keeps its points - if a nominated field comes back
with a real value, the nomination is wrong and the score says so rather than hiding it.

## The bar for adding an entry

E31 set it and refused 35 of 40 candidates: a written definitional argument that the
quantity is *meaningless*, not merely *unmeasured*. The two are easy to confuse and the
difference is the whole point of this file.

The clearest illustration is already here. `market_share_direction` resolved for **0 of
71** Energy companies and **0 of 59** Utilities companies - identical emptiness. Only
Utilities is nominated. An E&P competes for acreage, rigs and barrels and can genuinely
gain or lose share; nobody publishes the series, so its UNKNOWN is a measurement gap and
it keeps costing the points. A regulated utility has no share to move. Same field, same
zero, different reasons, different treatment.

**Do not add an entry because a field came back empty.** That is the E29 mistake with a
new name. Add one only with an argument you would defend to someone who wants the score
to go down.
"""
from __future__ import annotations

from .schema import UNKNOWN

#: The four rate-regulated utility industries. A retail electric, gas or water utility
#: operates under a state-granted franchise: it is obliged to serve every customer in its
#: territory and no competitor may serve them. Retail share is fixed at 100% by law.
_REGULATED_FRANCHISE = (
    "electric_utilities",
    "multi_utilities",
    "gas_utilities",
    "water_utilities",
)

#: industry_id -> the fields that industry cannot answer by construction.
#:
#: Deliberately tiny. Every entry needs a WHY below and a test pinning it.
INAPPLICABLE: dict[str, frozenset[str]] = {
    ind: frozenset({"market_share_direction"}) for ind in _REGULATED_FRANCHISE
}

#: (industry_id, field) -> the definitional argument. Required for every entry above;
#: a test asserts the two structures agree, so an entry cannot be added without one.
WHY: dict[tuple[str, str], str] = {
    (ind, "market_share_direction"): (
        "A rate-regulated utility holds a state-granted franchise monopoly over retail "
        "service in its territory: it must serve every customer there and no competitor "
        "may. Retail share is 100% by law and cannot move, so LOSING / FLAT / GAINING "
        "describe nothing. Load and customer growth are real and are captured by "
        "demand_visibility. This is NOT the Energy case, where share is contestable and "
        "merely unpublished."
    )
    for ind in _REGULATED_FRANCHISE
}

#: WHAT A NOMINATION DOES *NOT* COVER.
#:
#: Nominating `market_share_direction` says one specific thing is meaningless: whether
#: CONTESTABLE share moved. It does NOT say the company has no measurable position in its
#: product market. "Who is the biggest player in regulated water, and who is growing or
#: shrinking" is answerable, and it discriminates - AWK holds 39.9% of listed water
#: revenue against 1.6% at the bottom of the bucket, and gas utilities' growth against
#: their peer median spans -9.9% to +35.2%.
#:
#: An earlier draft collapsed the two and refused to compute anything for a nominated
#: industry, which threw that away for 54 of 59 utilities. `revenue_share.py` now computes
#: peer position for EVERY industry and fills the categorical only where share is
#: contestable. If a future nomination is added, check the same distinction: the question
#: being retired is "did share move between competitors", never "how big is this company
#: and is it growing".

#: Industries deliberately NOT nominated, with the reason, so the next reader does not
#: have to re-derive why the obvious-looking neighbours were left out.
CONSIDERED_AND_REFUSED: dict[tuple[str, str], str] = {
    ("upstream_oil_gas", "market_share_direction"): (
        "0 of 71 Energy companies resolved it, which looks identical to Utilities and is "
        "not. Producers compete for acreage, rigs and crews and their share genuinely "
        "moves; EIA and state regulators publish production by operator, so this is an "
        "unbuilt ingest, not a meaningless question. It must keep costing the points."
    ),
    ("electric_utilities", "competitive_position_trend"): (
        "Tempting because it resolved for 0 of 59, but competitive_position itself "
        "resolved for 20 of them on scale and service quality, so the vocabulary IS "
        "meaningful here. An unmeasured trend of a meaningful quantity is UNKNOWN."
    ),
    ("electric_utilities", "company_specific_capture"): (
        "A regulated utility does not compete for its territory's load growth, which "
        "argues for nomination - but it does choose whether to earn on the capex that "
        "serves that growth, and that is what capture means for it. Arguable both ways, "
        "so refused under the E31 bar: an entry needs an argument, not a balance."
    ),
}


def inapplicable_fields(industry_id: str | None) -> frozenset[str]:
    """The fields nominated for this industry. Empty for an unknown or absent id."""
    if not industry_id:
        return frozenset()
    return INAPPLICABLE.get(str(industry_id), frozenset())


def is_not_applicable(industry_id: str | None, field: str, value) -> bool:
    """The two-condition rule: the INDUSTRY is nominated AND the company gave no value.

    A nominated field that comes back with a real answer is still scored. That is not a
    leniency - it is how a wrong nomination stays visible instead of silently deleting a
    finding that contradicts it.
    """
    if field not in inapplicable_fields(industry_id):
        return False
    return value is None or str(value).strip().upper() == UNKNOWN
