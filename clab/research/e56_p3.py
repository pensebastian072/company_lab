"""E56 P3: does the middle-clustering repeat in a separate session?

Written BEFORE the five re-cut objects were researched, which is the only condition under
which its thresholds mean anything. E54 built 15 Financials objects in one session and 10
of the 11 answered `structural_growth` values came back MODERATE (Fisher p=0.0044 against
the rest of the corpus), with no object using the end of any scale. That is either a fact
about Financials - a mature sector honestly sits in the middle - or a fact about one
research session. The five E56 objects are Financials objects built in a DIFFERENT
session, so they discriminate.

P3 as registered: the clustering repeats, modal share >= 0.8 on `structural_growth`.

## The hole this module closes, found by writing the evaluator before the data

`modal_share` is computed over ANSWERED values only, because UNKNOWN is NO_DATA and never
a value. But four of these five objects have one or two members and one of them (BRK-B)
is explicitly invited to return UNKNOWN if a shared answer would be fiction. If only one
object answers, its modal share is 1.0 and P3 "confirms" on a sample of one.

So a minimum is registered here rather than discovered later: **fewer than 3 of the 5
answering `structural_growth` makes P3 INDETERMINATE**, not CONFIRMED and not REFUTED.
n=3 is itself thin and the verdict says so - this suggests, it does not settle.

Nothing in this module scores, ranks or promotes anything.
"""
from __future__ import annotations

import argparse

from ..external.schema import UNKNOWN

#: The five objects the E56 re-cut created. P3 is about these and nothing else.
E56_OBJECTS = (
    "private_mortgage_insurance",
    "retirement_benefits",
    "climate_infrastructure_finance",
    "commercial_mortgage_banking_servicing",
    "multi_industry_conglomerate",
)

#: Registered threshold: at or above this modal share, the clustering repeated.
MODAL_THRESHOLD = 0.80

#: Below this many ANSWERED values the question cannot be asked of the data.
MIN_ANSWERED = 3

FIELD = "structural_growth"


def evaluate(*, store=None) -> dict:
    """CONFIRMED / REFUTED / INDETERMINATE, with the counts behind it."""
    from ..external.store import ExternalStore
    from .. import config

    st = store or ExternalStore(config.EXTERNAL_DB)
    values: dict[str, str | None] = {}
    for iid in E56_OBJECTS:
        row = st.industry(iid)
        values[iid] = (row or {}).get(FIELD)

    missing = [i for i, v in values.items() if v is None]
    answered = {i: v for i, v in values.items()
                if v and str(v).strip().upper() != UNKNOWN}
    unknown = [i for i, v in values.items()
               if v and str(v).strip().upper() == UNKNOWN]

    counts: dict[str, int] = {}
    for v in answered.values():
        counts[v] = counts.get(v, 0) + 1
    modal_share = (max(counts.values()) / len(answered)) if answered else None
    modal_value = max(counts, key=counts.get) if counts else None

    if missing:
        verdict = "INCOMPLETE"
        reading = (f"{len(missing)} of the five objects are not in the store yet: "
                   f"{', '.join(sorted(missing))}. Ingest before evaluating.")
    elif len(answered) < MIN_ANSWERED:
        verdict = "INDETERMINATE"
        reading = (f"only {len(answered)} of 5 answered {FIELD}; the registration "
                   f"requires {MIN_ANSWERED}. A modal share over one or two objects "
                   "is not evidence either way.")
    elif modal_share >= MODAL_THRESHOLD:
        verdict = "CONFIRMED"
        reading = (f"the clustering repeated in a separate session: {modal_share:.0%} "
                   f"of {len(answered)} answered values are {modal_value}. Consistent "
                   "with a researcher tendency toward the middle rather than a fact "
                   "about Financials - but n is small and E54's confound (a genuinely "
                   "mature sector) is not excluded by this alone.")
    else:
        verdict = "REFUTED"
        reading = (f"the five spread: modal share {modal_share:.0%} of "
                   f"{len(answered)} answered, below the registered "
                   f"{MODAL_THRESHOLD:.0%}. E54's clustering does not reproduce in a "
                   "separate session, which points at a one-run artifact rather than a "
                   "property of the sector.")

    return {
        "prediction": "P3",
        "field": FIELD,
        "verdict": verdict,
        "reading": reading,
        "n_objects": len(E56_OBJECTS),
        "n_answered": len(answered),
        "n_unknown": len(unknown),
        "n_missing": len(missing),
        "modal_share": None if modal_share is None else round(modal_share, 3),
        "modal_value": modal_value,
        "distribution": dict(sorted(counts.items(), key=lambda kv: -kv[1])),
        "values": values,
        "threshold": MODAL_THRESHOLD,
        "min_answered": MIN_ANSWERED,
    }


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    res = evaluate()
    print(f"E56 P3 [{FIELD}]: {res['verdict']}")
    print(f"  answered {res['n_answered']}/5   UNKNOWN {res['n_unknown']}   "
          f"missing {res['n_missing']}")
    if res["modal_share"] is not None:
        print(f"  modal {res['modal_value']} at {res['modal_share']:.0%} "
              f"(registered threshold {MODAL_THRESHOLD:.0%})")
    print(f"  distribution {res['distribution']}")
    for iid, v in res["values"].items():
        print(f"    {iid:<40} {v}")
    print()
    print(f"  {res['reading']}")
    return 0


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(main())
