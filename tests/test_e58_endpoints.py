"""E58's verdict boundaries, pinned before either arm has data.

E56's endpoint finding was exploratory. This is the instrument that tests it somewhere
else, so its thresholds are fixed here, on synthetic values, while both E57 and Phase B
are still unrun. Every boundary that could be nudged afterwards to produce a nicer answer
is asserted.
"""
from __future__ import annotations

import pytest

from clab.external.schema import UNKNOWN, _ORDINALS
from clab.research import e58_endpoints as E58


class _IndustryStore:
    def __init__(self, rows):
        self._rows = rows

    def connect(self):
        rows = self._rows

        class _Con:
            def __enter__(self_):
                return self_

            def __exit__(self_, *a):
                return False

            def execute(self_, sql, params=None):
                self_._out = rows
                return self_

            def fetchall(self_):
                return self_._out

        return _Con()


def _obj(iid, sector, rd, *, status=None):
    """(industry_id, sector_id, status, structural_growth, replication_difficulty,
    substitution_risk) - the SELECT order arm_a builds."""
    return (iid, sector, status, "MODERATE", rd, "MODERATE")


# --------------------------------------------------------------- arm A


def test_arm_a_confirmed_when_another_sector_also_avoids_the_ends():
    rows = [_obj(f"h{i}", "health_care", "HIGH") for i in range(8)]
    rows += [_obj(f"o{i}", "energy", "EXTREME") for i in range(10)]
    r = E58.arm_a("health_care", store=_IndustryStore(rows))
    assert r["verdict"] == "CONFIRMED"
    assert r["subject_share"] == 0.0
    assert "not a fact about Financials" in r["reading"]


def test_arm_a_refuted_when_another_sector_uses_the_ends():
    rows = [_obj(f"h{i}", "health_care", "EXTREME") for i in range(4)]
    rows += [_obj(f"h{i}b", "health_care", "HIGH") for i in range(4)]
    rows += [_obj(f"o{i}", "energy", "HIGH") for i in range(10)]
    r = E58.arm_a("health_care", store=_IndustryStore(rows))
    assert r["subject_share"] == 0.5
    assert r["verdict"] == "REFUTED"
    assert "did NOT follow the researcher" in r["reading"]


def test_arm_a_is_indeterminate_below_the_registered_minimum():
    rows = [_obj(f"h{i}", "health_care", "HIGH") for i in range(3)]
    rows += [_obj(f"o{i}", "energy", "EXTREME") for i in range(10)]
    r = E58.arm_a("health_care", store=_IndustryStore(rows))
    assert r["subject_n"] == 3 < E58.ARM_A_MIN_ANSWERED
    assert r["verdict"] == "INDETERMINATE"


def test_arm_a_ignores_unknown_and_superseded():
    """UNKNOWN is NO_DATA, and a retired object is not part of the active corpus. If
    either leaked in, a refusal would read as an answer."""
    rows = [_obj(f"h{i}", "health_care", "HIGH") for i in range(6)]
    rows += [_obj("h_unknown", "health_care", UNKNOWN)]
    rows += [_obj("h_dead", "health_care", "EXTREME", status="SUPERSEDED")]
    rows += [_obj(f"o{i}", "energy", "EXTREME") for i in range(10)]
    r = E58.arm_a("health_care", store=_IndustryStore(rows))
    assert r["subject_n"] == 6
    assert r["subject_share"] == 0.0


def test_arm_a_threshold_boundary_is_exclusive():
    """Registered as 'below 0.10'. 1 of 10 is exactly 0.10 and must NOT confirm."""
    rows = [_obj("h0", "health_care", "EXTREME")]
    rows += [_obj(f"h{i}", "health_care", "HIGH") for i in range(1, 10)]
    rows += [_obj(f"o{i}", "energy", "HIGH") for i in range(10)]
    r = E58.arm_a("health_care", store=_IndustryStore(rows))
    assert r["subject_share"] == E58.ARM_A_THRESHOLD
    assert r["verdict"] == "REFUTED"


# --------------------------------------------------------------- arm B


def test_arm_b_never_compares_a_three_point_scale():
    """On a 3-value scale two of the three values are endpoints, so the measure is not
    comparable to a 4- or 5-value one. Pooling them was the flaw in P2 as first written."""
    short = [f for f in E58.COMPANY_ORDINALS if len(_ORDINALS[f]) < E58.MIN_SCALE]
    assert short, "expected at least one 3-point company scale"
    assert E58.MIN_SCALE == 4


def test_arm_b_margin_and_majority_rule_are_what_was_registered():
    assert E58.ARM_B_MARGIN == 0.15
    assert E58.ARM_B_MIN_PER_SIDE == 20


def test_arm_a_constants_are_what_was_registered():
    assert E58.ARM_A_FIELD == "replication_difficulty"
    assert E58.ARM_A_THRESHOLD == 0.10
    assert E58.ARM_A_MIN_ANSWERED == 6


def test_endpoints_are_both_ends_of_the_scale_not_just_the_top():
    """`substitution_risk` runs SEVERE..LOW, so its endpoints are SEVERE and LOW. Taking
    only the last value would have measured half the behaviour."""
    assert E58._endpoints("substitution_risk") == ("SEVERE", "LOW")
    assert E58._endpoints("replication_difficulty") == ("LOW", "EXTREME")
    assert E58._endpoints("structural_growth") == ("DECLINING", "EXCEPTIONAL")


def test_share_excludes_unknown_from_the_denominator():
    share, n = E58._share(["HIGH", "EXTREME", UNKNOWN, None], "replication_difficulty")
    assert n == 2
    assert share == 0.5


@pytest.mark.parametrize("field", ["replication_difficulty", "substitution_risk"])
def test_a_field_of_all_middles_scores_zero_not_none(field):
    share, n = E58._share(["MODERATE", "MODERATE"], field)
    assert n == 2 and share == 0.0


def test_arm_b_counts_companies_not_rows():
    """A company with several research arms must count ONCE by default.

    Live store 2026-09-08 had 481 company_external rows over 328 tickers, and arm B read
    financials as n=173 for 130 companies - pooling a KNOWN-DEFECTIVE burned batch with
    the accepted one. Pooling arms is exactly what this experiment exists to avoid.
    """
    import inspect
    src = inspect.getsource(E58.arm_b)
    assert "_dedupe" in src and "research_version" in src
    assert "SUPERSEDED" in src


def test_arm_b_version_scope_constrains_the_SUBJECT_not_the_baseline():
    """E58 registers arm B on "Phase B's own research_version". The scope names the
    SUBJECT. Applying it to the baseline too empties the comparison group, which comes
    back INDETERMINATE and reads like a thin sample rather than the error it is - that is
    exactly what the first version of this fix did.
    """
    import inspect
    src = inspect.getsource(E58.arm_b)
    assert "does not restrict the" in src
    assert "subject_rows" in src
    # and the baseline is deduped independently of the subject scope
    assert "rest = _dedupe(" in src


def test_arm_b_takes_a_SET_of_versions_because_phase_b_spans_several():
    """Financials Phase B is four batches. An instrument that accepts one version cannot
    express the registered scope at all."""
    import inspect
    sig = inspect.signature(E58.arm_b)
    assert "research_versions" in sig.parameters
    assert "research_version" in sig.parameters


def test_arm_b_excludes_a_superseded_arm_and_counts_a_company_once():
    """E59 batch 1 was burned and replaced by its rerun. Counting both would weight 43
    companies twice AND include research we rejected.

    Measured 2026-09-09: the unscoped default gave Financials technology_risk 0.048 on
    n=167; the registered E59 scope gives 0.000 on n=85. Both are correct about their own
    sample and only one of them is arm B.
    """
    import inspect
    src = inspect.getsource(E58.arm_b)
    assert "SUPERSEDED" in src
    assert "_dedupe" in src
