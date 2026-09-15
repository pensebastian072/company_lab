"""The repair's guarantees, and the two defects it found on the way.

This module only ever recomputes ATTRIBUTION. Everything else on a scorecard must come
back byte-identical, and the run must abort rather than write a partial repair - which
is what caught the two pre-E26 scorecards that were still sitting in the book.
"""
from __future__ import annotations

import json

import pytest

from clab.runner import repair_attribution as RA
from clab.scoring import rubric


def _subtest(key, max_points, earned=None, status="scored"):
    return {"key": key, "label": key, "max_points": max_points,
            "earned": earned, "status": status}


def _card(**over):
    """A minimal but complete card on the CURRENT framework."""
    comps = {}
    for code, mx in rubric.COMPONENTS.items():
        comps[code] = {
            "code": code, "label": rubric.COMPONENTS[code][0],
            "max_points": rubric.COMPONENTS[code][1],
            "subtests": [_subtest(f"{code.lower()}_a", rubric.COMPONENTS[code][1],
                                  earned=1)],
        }
    card = {"ticker": "TEST", "cik": "0000000001", "components": comps}
    card.update(over)
    return card


# --------------------------------------------------------- framework detection
def test_framework_total_reads_the_card_not_the_current_rubric():
    card = _card()
    assert RA.framework_total(card) == rubric.TOTAL_POINTS
    assert RA.is_current_framework(card)
    card["components"]["MG"]["max_points"] = 15          # the pre-E26 shape
    assert RA.framework_total(card) == rubric.TOTAL_POINTS + 6
    assert not RA.is_current_framework(card)


def test_a_card_from_an_older_framework_is_skipped_not_repaired(tmp_path, monkeypatch):
    """Its coverage denominator is 100 while today's is 94, so rewriting only its
    attribution would leave two scales side by side and hide the real problem: it was
    never rescored. EQR and AVB were both in this state."""
    monkeypatch.setattr(RA.config, "SCORECARD_DIR", tmp_path)
    monkeypatch.setattr(RA.config, "SCORES_PARQUET", tmp_path / "none.parquet")
    old = _card(ticker="OLD")
    old["components"]["MG"]["max_points"] = 15
    old["components"]["MG"]["subtests"] = [_subtest("mg_a", 15, earned=3)]
    (tmp_path / "0000000001_OLD.json").write_text(json.dumps(old), encoding="utf-8")

    res = RA.repair_scorecards(apply=True)
    assert [s["ticker"] for s in res["skipped"]] == ["OLD"]
    assert res["changed"] == 0
    # and it is left exactly as found
    assert json.loads((tmp_path / "0000000001_OLD.json").read_text())["components"] \
        ["MG"]["max_points"] == 15


# ------------------------------------------------------------- the guardrail
def test_headline_drift_aborts_rather_than_writing_a_partial_repair():
    card = _card()
    card["composite_strict"] = 999          # a value the components cannot produce
    with pytest.raises(RA.HeadlineDrift):
        fixed, check = RA.recompute(card)
        RA._verify_headline(card, check)


def test_a_missing_headline_field_is_not_treated_as_drift():
    """An older card may simply lack a field. Absent is not different."""
    card = _card()
    fixed, check = RA.recompute(card)
    RA._verify_headline(card, check)        # no headline keys stored at all


# ---------------------------------------------------------------- the repair
def test_mg_moves_from_the_judged_half_to_the_measured_half():
    card = _card()
    card["quant_only_50"] = 0
    card["qual_only_50"] = 0
    fixed, _ = RA.recompute(card)
    # every component earned 1 point in the fixture
    assert fixed["quant_only_50"] == len(rubric.MEASURED_COMPONENTS)
    assert fixed["qual_only_50"] == len(rubric.JUDGED_COMPONENTS)


def test_repair_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(RA.config, "SCORECARD_DIR", tmp_path)
    monkeypatch.setattr(RA.config, "SCORES_PARQUET", tmp_path / "none.parquet")
    card = _card()
    card.update({"quant_only_50": 0, "qual_only_50": 0, "quant_band": "WRONG"})
    (tmp_path / "0000000001_TEST.json").write_text(json.dumps(card), encoding="utf-8")

    first = RA.repair_scorecards(apply=True)
    assert first["changed"] == 1
    second = RA.repair_scorecards(apply=True)
    assert second["changed"] == 0


def test_a_data_quality_fail_subtest_is_not_promoted_to_scored(tmp_path, monkeypatch):
    """SubTest.__post_init__ forces status=SCORED whenever earned is not None, which is
    right for a live scorer and wrong when replaying a stored row. A DATA_QUALITY_FAIL
    row carrying a value must stay withheld, or the repair hands back points the
    original run deliberately refused."""
    d = _subtest("fe_a", 4, earned=4, status="data_quality_fail")
    st = RA._subtest_from(d)
    assert st.status.value == "data_quality_fail"
    assert st.earned == 4
    # ...and therefore it contributes nothing
    from clab.scoring.types import ComponentScore
    comp = ComponentScore(code="FE", label="FE", max_points=18, subtests=[st])
    assert comp.earned_points == 0
    assert comp.available_points == 0


# ----------------------------------------------------------------- the ghosts
def test_two_cards_on_one_cik_are_a_ghost_and_the_newest_current_one_wins(
        tmp_path, monkeypatch):
    """CIK 0000906107 held both EQR (2026-08-17, 100pt) and VMRK (2026-08-29, 94pt)
    after a ticker change, so the book carried the same company twice."""
    monkeypatch.setattr(RA.config, "SCORECARD_DIR", tmp_path)
    old = _card(ticker="EQR", cik="0000906107", as_of="2026-08-17T00:00:00")
    old["components"]["MG"]["max_points"] = 15
    new = _card(ticker="VMRK", cik="0000906107", as_of="2026-08-29T00:00:00")
    (tmp_path / "0000906107_EQR.json").write_text(json.dumps(old), encoding="utf-8")
    (tmp_path / "0000906107_VMRK.json").write_text(json.dumps(new), encoding="utf-8")

    ghosts = RA.find_ghosts()
    assert len(ghosts) == 1
    assert ghosts[0]["keep"]["ticker"] == "VMRK"
    assert [c["ticker"] for c in ghosts[0]["drop"]] == ["EQR"]


def test_an_ex_constituent_with_one_card_is_not_a_ghost(tmp_path, monkeypatch):
    """AVB left the index with no rename. Dropping ex-constituents is exactly the
    survivorship bias E05 exists to measure."""
    monkeypatch.setattr(RA.config, "SCORECARD_DIR", tmp_path)
    (tmp_path / "0000915912_AVB.json").write_text(
        json.dumps(_card(ticker="AVB", cik="0000915912")), encoding="utf-8")
    assert RA.find_ghosts() == []


def test_ghosts_are_quarantined_not_deleted(tmp_path, monkeypatch):
    monkeypatch.setattr(RA.config, "SCORECARD_DIR", tmp_path)
    monkeypatch.setattr(RA.config, "SCORES_PARQUET", tmp_path / "none.parquet")
    old = _card(ticker="EQR", cik="0000906107", as_of="2026-08-17T00:00:00")
    old["components"]["MG"]["max_points"] = 15
    (tmp_path / "0000906107_EQR.json").write_text(json.dumps(old), encoding="utf-8")
    (tmp_path / "0000906107_VMRK.json").write_text(
        json.dumps(_card(ticker="VMRK", cik="0000906107", as_of="2026-08-29T00:00:00")),
        encoding="utf-8")

    RA.prune_ghosts(apply=True)
    assert not (tmp_path / "0000906107_EQR.json").exists()
    assert (tmp_path / "ghosts" / "0000906107_EQR.json").exists()
    assert (tmp_path / "0000906107_VMRK.json").exists()


# -------------------------------------------------- against the live book
def test_the_live_book_has_no_duplicate_ciks():
    """The invariant the ghost broke. 1,501 rows over 1,500 CIKs until 2026-09-01."""
    pd = pytest.importorskip("pandas")
    from clab import config
    if not config.SCORES_PARQUET.exists():
        pytest.skip("no book on disk")
    df = pd.read_parquet(config.SCORES_PARQUET)
    dupes = df[df.duplicated("cik", keep=False)]
    assert dupes.empty, f"duplicate CIKs: {dupes[['ticker', 'cik']].to_dict('records')}"


def test_the_live_book_is_all_on_one_framework():
    """Two scorecards sat on the 100-point framework for a fortnight because their
    companies left the index and stopped being crawled."""
    from clab import config
    if not config.SCORECARD_DIR.exists():
        pytest.skip("no scorecards on disk")
    bad = []
    for p in sorted(config.SCORECARD_DIR.glob("*.json")):
        card = json.loads(p.read_text(encoding="utf-8"))
        if not RA.is_current_framework(card):
            bad.append((card.get("ticker"), RA.framework_total(card)))
    assert bad == [], f"cards on an older framework, needing a rescore: {bad}"
