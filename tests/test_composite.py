"""Composite assembly, coverage gate, bands, and the weight reconciliation.

The single most dangerous thing this system could do is label a company
"High Conviction" on 60% of the framework. test_band_gate_* pins that shut.
"""
from __future__ import annotations

import random

import pytest

from clab.scoring import composite, rubric
from clab.scoring.types import ComponentScore, Status, no_data, not_applicable, scored


def mx_of(code: str) -> int:
    """Component maximum from the rubric.

    Tests derive every maximum from the rubric rather than hardcoding it, so a
    deliberate reweighting (FE 15->18, EN 5->2 on 2026-08-10) changes one place
    instead of breaking a dozen assertions.
    """
    return rubric.COMPONENTS[code][1]


def comp(code: str, earned: int, *, no_data_points: int = 0, na_points: int = 0):
    """A component with `earned` points scored, plus optional unavailable points."""
    label, mx = rubric.COMPONENTS[code]
    sts = []
    scored_max = mx - no_data_points - na_points
    if scored_max > 0:
        sts.append(scored(f"{code.lower()}_a", "scored part", scored_max,
                          min(earned, scored_max)))
    if no_data_points:
        sts.append(no_data(f"{code.lower()}_nd", "missing part", no_data_points, "absent"))
    if na_points:
        sts.append(not_applicable(f"{code.lower()}_na", "n/a part", na_points, "n/a"))
    c = ComponentScore(code=code, label=label, max_points=mx, subtests=sts)
    c.check_points()
    return c


def card(components: dict, **kw) -> composite.Scorecard:
    return composite.build_scorecard(
        ticker="TEST", cik="0000000001", name="Test Co", as_of="2026-08-08T00:00:00+00:00",
        components=components, **kw)


def full_house(points_per_component: dict) -> dict:
    return {code: comp(code, pts) for code, pts in points_per_component.items()}


# ------------------------------------------------------------------ weights
def test_weights_sum_to_one():
    total = sum(mx / rubric.TOTAL_POINTS for _l, mx in rubric.COMPONENTS.values())
    assert total == pytest.approx(1.0)


def test_component_maxima_sum_to_100():
    assert sum(mx for _l, mx in rubric.COMPONENTS.values()) == rubric.TOTAL_POINTS


def test_weighted_form_equals_raw_point_sum_over_random_vectors():
    """The framework states weights on normalized sub-scores; the code sums raw
    points. They are arithmetically identical and this pins them together forever."""
    rng = random.Random(1337)
    for _ in range(10000):
        pts = {code: rng.randint(0, mx) for code, (_l, mx) in rubric.COMPONENTS.items()}
        comps = full_house(pts)
        # E26 took the framework to 94 points, so the weighted form scales by
        # TOTAL_POINTS. The identity being pinned is that weights-on-normalised-subscores
        # and raw-point-sum are the same arithmetic, whatever the total happens to be.
        weighted = composite.weighted_composite01(comps) * rubric.TOTAL_POINTS
        raw = sum(pts.values())
        assert weighted == pytest.approx(raw, abs=1e-9)


# ------------------------------------------------------------------ coverage
def test_no_data_reduces_available_not_earned():
    scored_max = mx_of("FE") - 5
    c = card({"FE": comp("FE", scored_max, no_data_points=5)})
    assert c.points_earned == scored_max
    assert c.points_available == scored_max   # the 5 missing points were never available
    assert c.components["FE"].no_data_points == 5


def test_not_applicable_leaves_coverage_intact():
    """A bank is not penalised for having no gross-margin line: NOT_APPLICABLE
    comes out of the coverage denominator as well as the numerator."""
    all_scored = {code: comp(code, mx) for code, (_l, mx) in rubric.COMPONENTS.items()}
    c1 = card(all_scored)
    assert c1.coverage == pytest.approx(1.0)

    with_na = dict(all_scored)
    with_na["FE"] = comp("FE", mx_of("FE") - 5, na_points=5)
    c2 = card(with_na)
    assert c2.not_applicable_points == 5
    assert c2.applicable_points == rubric.TOTAL_POINTS - 5
    assert c2.coverage == pytest.approx(1.0)     # still fully covered
    assert c2.points_earned == rubric.TOTAL_POINTS - 5


def test_coverage_counts_only_applicable_points():
    c = card({code: comp(code, 0, no_data_points=mx)
              for code, (_l, mx) in rubric.COMPONENTS.items()})
    assert c.points_available == 0
    assert c.coverage == 0.0


# ------------------------------------------------------------------ band gate
def test_band_gate_refuses_to_label_thin_coverage():
    """90 points earned but only 60% of the framework scored -> no band."""
    full = ("SG", "BQ", "FE", "MG", "BS")
    empty = ("VA", "ER", "EN")
    comps = {k: comp(k, mx_of(k)) for k in full}
    comps.update({k: comp(k, 0, no_data_points=mx_of(k)) for k in empty})
    c = card(comps)
    expected = sum(mx_of(k) for k in full)
    assert c.points_earned == expected
    assert c.coverage == pytest.approx(expected / rubric.TOTAL_POINTS)
    assert c.band == rubric.INSUFFICIENT_BAND


@pytest.mark.parametrize("points,expected", [
    (100, "EXCEPTIONAL"), (90, "EXCEPTIONAL"), (89, "HIGH_CONVICTION"),
    (80, "HIGH_CONVICTION"), (79, "INVESTABLE"), (70, "INVESTABLE"),
    (69, "WATCHLIST"), (60, "WATCHLIST"), (59, "WEAK"), (50, "WEAK"),
    (49, "REJECT"), (0, "REJECT"),
])
def test_band_boundaries(points, expected):
    assert rubric.band_for(points, 1.0) == expected


def test_band_for_respects_coverage_at_every_score():
    for pts in (0, 50, 75, 95):
        assert rubric.band_for(pts, 0.79) == rubric.INSUFFICIENT_BAND
        assert rubric.band_for(pts, 0.80) != rubric.INSUFFICIENT_BAND


# ------------------------------------------------------------------ strict vs normalized
def test_strict_never_extrapolates_normalized_does():
    scored_max = mx_of("FE") - 5
    c = card({"FE": comp("FE", scored_max, no_data_points=5)})
    assert c.composite_strict == scored_max               # flat: missing costs points
    assert c.composite_normalized == pytest.approx(100.0)  # extrapolated


def test_normalized_is_none_when_nothing_available():
    c = card({"FE": comp("FE", 0, no_data_points=mx_of("FE"))})
    assert c.composite_normalized is None


# ------------------------------------------------------------------ halves
def test_the_halves_are_no_longer_50_50_and_the_code_says_so():
    """E25 removed MG's five model-scored CEO attributes and E26 shrank the block to the
    two measured ones it still asks, so the framework is 94 points, not 100, and the
    judged share is smaller than the measured one.

    Pinned as a FACT rather than deleted: "half the score is an LLM" was true for months,
    is quoted in the workbook and the docs, and anything still asserting it should fail
    here rather than mislead a reader.
    """
    quant = sum(rubric.COMPONENTS[c][1] for c in rubric.MEASURED_COMPONENTS)
    judged = sum(rubric.COMPONENTS[c][1] for c in rubric.JUDGED_COMPONENTS)
    assert quant + judged == rubric.TOTAL_POINTS == 94
    assert judged < quant           # 44 judged against 50 measured
    # MG's own split: 2 measured CEO points, 7 judged capital-allocation points
    assert rubric.MG_CEO_POINTS == 2
    assert rubric.MG_CEO_POINTS + rubric.MG_CAPALLOC_POINTS == rubric.COMPONENTS["MG"][1]


def test_quant_half_is_unaffected_by_a_cold_llm_cache():
    """The behaviour that makes the system useful on day one."""
    comps = {k: comp(k, 0, no_data_points=mx_of(k)) for k in rubric.JUDGED_COMPONENTS}
    # MG belongs here: it is fully measured (V3 P0 corrected the list it was missing
    # from). A cold LLM cache must not cost MG a single point.
    comps.update({"FE": comp("FE", mx_of("FE")), "MG": comp("MG", mx_of("MG")),
                  "BS": comp("BS", mx_of("BS")),
                  "VA": comp("VA", 8), "ER": comp("ER", 4),
                  "EN": comp("EN", min(3, mx_of("EN")))})
    c = card(comps)
    expected_quant = (mx_of("FE") + mx_of("MG") + mx_of("BS") + 8 + 4
                      + min(3, mx_of("EN")))
    assert c.quant_only_50 == expected_quant   # the name predates E26
    assert c.quant_coverage == pytest.approx(1.0)
    assert c.qual_available is False
    # The measured half is the larger one. Derived, not a literal: this line already
    # drifted once (it said 50 when the measured half became 59 at the V3 P0 MG fix).
    assert c.coverage == pytest.approx(rubric.MEASURED_POINTS / rubric.TOTAL_POINTS)
    assert c.band == rubric.INSUFFICIENT_BAND        # full band withheld, correctly
    assert c.quant_normalized is not None
    assert c.quant_band != rubric.INSUFFICIENT_BAND   # measured half still labelled


def test_composite_ex_entry_removes_only_entry():
    comps = {"FE": comp("FE", mx_of("FE")), "EN": comp("EN", mx_of("EN"))}
    c = card(comps)
    assert c.composite_strict == mx_of("FE") + mx_of("EN")
    assert c.composite_ex_entry == mx_of("FE")


# ------------------------------------------------------------------ validation
def test_build_scorecard_rejects_wrong_component_maximum():
    bad = ComponentScore(code="FE", label="Financial Engine", max_points=99,
                         subtests=[scored("x", "x", 99, 1)])
    with pytest.raises(ValueError, match="max_points"):
        card({"FE": bad})


def test_check_points_rejects_subtests_that_do_not_sum():
    c = ComponentScore(code="BS", label="Balance Sheet", max_points=10,
                       subtests=[scored("a", "a", 3, 1)])
    with pytest.raises(ValueError, match="sum to 3"):
        c.check_points()


def test_unknown_component_code_rejected():
    label, mx = "x", 5
    bad = ComponentScore(code="ZZ", label=label, max_points=mx,
                         subtests=[scored("z", "z", mx, 1)])
    with pytest.raises(ValueError, match="unknown component"):
        card({"ZZ": bad})


def test_empty_component_is_all_no_data():
    c = composite.empty_component("VA", "stage skipped")
    assert c.earned_points == 0
    assert c.available_points == 0
    assert c.subtests[0].status == Status.NO_DATA


def test_scorecard_serializes_and_flattens():
    scored_max = mx_of("FE") - 3
    c = card({"FE": comp("FE", scored_max, no_data_points=3)},
             metrics={"roic": 0.2, "stress_verdict": "SURVIVES"})
    d = c.to_dict()
    assert d["composite_strict"] == scored_max
    assert d["components"]["FE"]["no_data_points"] == 3
    assert "ADVISORY" in d["advisory"] or "ADVISORY" in d["advisory"].upper()
    row = c.table_row()
    assert row["fe"] == scored_max and row["fe_max"] == mx_of("FE")
    assert row["roic"] == 0.2


# ------------------------------------------------------------------ E21
def test_the_band_ignores_entry_timing():
    """E01 failed three times, yet EN's 2 points were ordering the top of the book.

    The band now reads `selection_score` - the ex-entry sum rescaled to the same
    100-point basis - so two companies identical apart from entry timing must land in the
    same band, and `composite_strict` must still report the full eight-component sum.
    """
    from clab.scoring import composite, rubric
    from clab.scoring.types import ComponentScore, Status, SubTest

    def card(en_points):
        comps = {}
        for code, (_label, mx) in rubric.COMPONENTS.items():
            earned = en_points if code == "EN" else int(round(mx * 0.78))
            comps[code] = ComponentScore(
                code=code, label=code, max_points=mx,
                subtests=[SubTest(key=f"{code}_x", label=code, max_points=mx,
                                  earned=earned, status=Status.SCORED)])
        return composite.Scorecard(ticker="T", cik="1", components=comps)

    with_entry, without = card(2), card(0)
    assert with_entry.composite_strict == without.composite_strict + 2
    assert with_entry.selection_score == without.selection_score
    assert with_entry.band == without.band


def test_selection_score_keeps_the_100_point_basis():
    """A raw /98 sum against thresholds calibrated for /100 would downgrade every
    company holding entry points - a recalibration disguised as a removal."""
    from clab.scoring import composite, rubric
    from clab.scoring.types import ComponentScore, Status, SubTest

    comps = {}
    for code, (_label, mx) in rubric.COMPONENTS.items():
        comps[code] = ComponentScore(
            code=code, label=code, max_points=mx,
            subtests=[SubTest(key=f"{code}_x", label=code, max_points=mx,
                              earned=mx, status=Status.SCORED)])
    perfect = composite.Scorecard(ticker="T", cik="1", components=comps)
    assert perfect.composite_strict == rubric.TOTAL_POINTS      # 94 after E26
    # ...but the BAND score is normalised to 100 regardless, because rubric.BANDS is
    # calibrated in 0-100 points. Scaling it by the framework total instead would have
    # made every band harder to reach the moment E26 shortened the scale.
    assert perfect.selection_score == 100


def test_a_row_carries_the_age_of_its_scorecard(tmp_path, monkeypatch):
    """A company that leaves the index keeps its scorecard and stops being re-scored.

    E04 established that dropping removed constituents is what manufactures survivorship
    bias, so they stay - but AVB and EQR sat in the table at 3.5 days old, looking exactly
    like the 1,498 rows written that night. The age travels with the row.
    """
    import json
    import os
    import time

    from clab import config as clab_config
    from clab.runner import batch

    monkeypatch.setattr(clab_config, "SCORECARD_DIR", tmp_path)
    card = {"ticker": "OLD", "cik": "1", "components": {}, "metrics": {}}
    p = tmp_path / "0000000001_OLD.json"
    p.write_text(json.dumps(card), encoding="utf-8")
    old = time.time() - 3.5 * 86400
    os.utime(p, (old, old))

    rows = batch.collect_scorecard_rows()
    assert len(rows) == 1
    assert 3.4 < rows[0]["scorecard_age_days"] < 3.6
