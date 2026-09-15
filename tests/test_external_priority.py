"""The priority engine, its control arm, the xsect tier and the workbook.

The control arm is the load-bearing part. Researching only the companies the ranking
already likes means a high score is never challenged, only confirmed, and the system
quietly becomes unable to be wrong.
"""
from __future__ import annotations

from datetime import date

import pytest

from clab import config
from clab.external import priority as P

TODAY = date(2026, 9, 2)


def _rows(n=60):
    sectors = ["Information Technology", "Financials", "Energy", "Health Care",
               "Industrials", "Utilities"]
    return [{"ticker": f"T{i:03d}", "sector": sectors[i % len(sectors)],
             "market_cap": 1e9 * (i + 1), "score": 40 + (i % 50),
             "va": i % 16, "sector_percentile": (i % 100) / 100.0}
            for i in range(n)]


# ------------------------------------------------------------------ inputs
def test_every_input_is_recorded_not_just_the_score():
    """A later reader must be able to recompute the decision rather than trust it."""
    inp = P.priority_inputs(_rows(1)[0], today=TODAY)
    assert set(inp) == set(P.WEIGHTS)
    assert all(0.0 <= v <= 1.0 for v in inp.values())


def test_the_weights_sum_to_one():
    assert abs(sum(P.WEIGHTS.values()) - 1.0) < 1e-9


def test_a_never_researched_company_is_maximally_stale():
    assert P.priority_inputs(_rows(1)[0], prior=None, today=TODAY)["staleness"] == 1.0


def test_staleness_decays_from_the_last_research_date():
    fresh = P.priority_inputs(_rows(1)[0],
                              prior={"last_research_date": "2026-09-01"}, today=TODAY)
    old = P.priority_inputs(_rows(1)[0],
                            prior={"last_research_date": "2025-01-01"}, today=TODAY)
    assert old["staleness"] > fresh["staleness"]


def test_a_company_at_a_band_edge_is_prioritised_over_one_deep_inside():
    """Research is most valuable where it can change the answer."""
    edge = P.priority_inputs({"ticker": "A", "score": 80}, today=TODAY)
    inside = P.priority_inputs({"ticker": "B", "score": 65}, today=TODAY)
    assert edge["conviction_proximity"] > inside["conviction_proximity"]


def test_nan_never_reaches_the_arithmetic():
    """NaN passes isinstance(v, float) and scrambles every comparison it touches."""
    inp = P.priority_inputs({"ticker": "A", "score": float("nan"),
                             "va": float("nan"), "market_cap": float("inf")},
                            today=TODAY)
    assert all(v == v for v in inp.values())
    assert 0.0 <= P.priority_score(inp) <= 1.0


def test_flags_raise_priority():
    a = P.priority_inputs(_rows(1)[0], flags=[], today=TODAY)
    b = P.priority_inputs(_rows(1)[0], flags=["MOAT_CONTRADICTION",
                                              "GROWTH_CONTRADICTION"], today=TODAY)
    assert P.priority_score(b) > P.priority_score(a)


# ------------------------------------------------------------ the control arm
def test_the_control_arm_is_the_configured_fraction():
    sel = P.select(_rows(), n=20, seed=1, today=TODAY)
    assert sel["n_control"] == round(20 * config.EXTERNAL_CONTROL_FRACTION)
    assert sel["n_priority"] + sel["n_control"] == 20


def test_the_two_arms_are_disjoint():
    """"Did priority beat chance" is only a fair question if they do not overlap."""
    sel = P.select(_rows(), n=20, seed=1, today=TODAY)
    a = {r["ticker"] for r in sel["priority"]}
    b = {r["ticker"] for r in sel["control"]}
    assert a & b == set()


def test_the_control_arm_is_not_the_priority_arm_by_another_name():
    """If the random draw reproduced the priority ordering it would measure nothing."""
    sel = P.select(_rows(200), n=40, seed=7, today=TODAY)
    top = [r["ticker"] for r in sorted(
        sel["priority"] + sel["control"], key=lambda r: -r["priority_score"])][:8]
    control = {r["ticker"] for r in sel["control"]}
    assert not control.issuperset(set(top))


def test_the_draw_is_reproducible_under_its_seed():
    a = P.select(_rows(), n=20, seed=99, today=TODAY)
    b = P.select(_rows(), n=20, seed=99, today=TODAY)
    c = P.select(_rows(), n=20, seed=100, today=TODAY)
    assert a["order"] == b["order"]
    assert a["order"] != c["order"]


def test_the_control_draw_is_stratified_across_sectors():
    sel = P.select(_rows(180), n=60, seed=3, today=TODAY)
    sectors = {r["ticker"][-1] for r in sel["control"]}
    assert len(sel["control"]) > 0
    assert len({t for t in sectors}) >= 1
    assert sel["strata"] > 1


def test_the_selection_records_everything_e36_records():
    """experiment, seed, requested, eligible_pool, strata, sector_counts, order."""
    sel = P.select(_rows(), n=10, seed=5, today=TODAY)
    for key in ("experiment", "seed", "requested", "eligible_pool", "strata",
                "sector_counts", "order", "control_fraction"):
        assert key in sel, key
    assert len(sel["order"]) == sel["n_priority"] + sel["n_control"]


def test_asking_for_more_than_the_pool_does_not_crash():
    sel = P.select(_rows(5), n=50, seed=1, today=TODAY)
    assert len(sel["order"]) <= 5 + 5


def test_an_empty_pool_is_not_a_crash():
    sel = P.select([], n=10, seed=1, today=TODAY)
    assert sel["order"] == []


def test_the_ledger_records_both_arms(tmp_path):
    from clab.external.store import ExternalStore
    store = ExternalStore(tmp_path / "t.duckdb")
    sel = P.select(_rows(), n=20, seed=1, today=TODAY)
    n = P.log(sel, store=store, run_date=TODAY)
    assert n == 20
    arms = store.priority_arms(TODAY)
    assert arms["priority"] == sel["n_priority"]
    assert arms["control"] == sel["n_control"]


# ------------------------------------------------------------- the xsect tier
def test_the_curated_xsect_list_carries_its_classification():
    """config.XSECT_UNIVERSE is a 44M-row bar file with no CIK and no sector. A company
    loaded from it arrives with an empty sub_industry, which is the only thing
    separating a mortgage REIT from an equity REIT."""
    from clab.sources import universe as uni
    if not uni.XSECT_MEMBERS_FILE.exists():
        pytest.skip("no curated xsect list")
    df = uni.fetch_universe("xsect", force=False)
    assert len(df) > 0
    for _, r in df.iterrows():
        assert r["cik"], f"{r['ticker']} has no CIK"
        assert r["gics_sector"], f"{r['ticker']} has no sector"
        assert r["gics_sub_industry"], f"{r['ticker']} has no sub-industry"


def test_asml_joins_the_existing_semiconductor_equipment_object():
    """Named for exactly this at Phase 0: the id ASML joins without a rename, so its
    research is not orphaned from the object already built."""
    from clab.sources import universe as uni
    from clab.external import taxonomy as T
    if not uni.XSECT_MEMBERS_FILE.exists():
        pytest.skip("no curated xsect list")
    df = uni.fetch_universe("xsect", force=False)
    asml = df[df["ticker"] == "ASML"]
    if asml.empty:
        pytest.skip("ASML not in the curated list")
    r = asml.iloc[0]
    ids = T.resolve("ASML", r["gics_sector"], r["gics_sub_industry"])
    assert ids["industry_id"] == "semiconductor_equipment"
    assert ids["sector_id"] == "information_technology"


# ----------------------------------------------------------------- workbook
def test_the_workbook_is_filterable_and_carries_its_caveats(tmp_path):
    from clab.export import xlsx_external as X
    openpyxl = pytest.importorskip("openpyxl")
    data = {"research_version": "test", "overview": [
        {"conviction_rank": 1, "ticker": "AAA", "conviction_score": 90.0,
         "conviction_band": "VERIFIED_HIGH", "sector": "Energy"}],
        "claims": [{"ticker": "AAA", "field": "moat_trajectory",
                    "verify_status": "VERIFIED_LOCAL"}],
        "industries": [{"industry_id": "refining", "sector_id": "energy"}]}
    out = tmp_path / "wb.xlsx"
    X.write(out, data)
    wb = openpyxl.load_workbook(out)
    assert {"Overview", "BySector", "Claims", "Industries", "Findings",
            "Meta"} <= set(wb.sheetnames)
    for name in ("Overview", "Claims", "Industries", "Meta"):
        assert wb[name].auto_filter.ref, f"{name} header is not filterable"
    findings = " ".join(str(c.value) for row in wb["Findings"].iter_rows()
                        for c in row if c.value)
    assert "-7.6%" in findings and "95.6%" in findings
    assert "E08" in findings and "INVERTED" in findings.upper()


# ------------------------------------------- the matched control (E43's finding)
def _ind_rows(n_per=10):
    """Companies across three industries with very different flag propensities."""
    out = []
    for ind, sub in (("payments", "Transaction & Payment Processing Services"),
                     ("regional_banking", "Regional Banks"),
                     ("refining", "Oil & Gas Refining & Marketing")):
        for i in range(n_per):
            out.append({"ticker": f"{ind[:3].upper()}{i:02d}",
                        "sector": "Financials", "sub_industry": sub,
                        "market_cap": 1e9 * (i + 1), "score": 50 + i,
                        "va": i % 16, "sector_percentile": i / n_per})
    return out


def test_the_stratum_is_industry_not_sector():
    """E43: flags are an industry property. us_credit_scoring averaged 3.00 per company,
    pc_insurance 0.12, and four industries 0.00. Stratifying on sector let the two arms
    land in disjoint industries and the whole comparison became unreadable."""
    a = P._stratum_key({"ticker": "FICO", "sub_industry": "Application Software",
                        "sector": "Information Technology"})
    b = P._stratum_key({"ticker": "ADBE", "sub_industry": "Application Software",
                        "sector": "Information Technology"})
    assert a == "us_credit_scoring"
    assert b == "application_software"
    assert a != b, "two companies in one SECTOR must be able to differ by stratum"


def test_the_matched_control_never_lands_in_an_industry_priority_did_not_pick():
    """The failure E43 measured: the arms ended up in almost disjoint industries and
    the observed difference was exactly what industry mix alone predicted."""
    rows = _ind_rows(12)
    sel = P.select(rows, n=20, seed=11, today=TODAY)
    assert sel["control_design"] == "matched_by_industry"
    by_t = {r["ticker"]: r for r in rows}
    pind = {P._stratum_key(by_t[r["ticker"]]) for r in sel["priority"]}
    cind = {P._stratum_key(by_t[r["ticker"]]) for r in sel["control"]}
    assert cind <= pind, f"control landed outside priority's industries: {cind - pind}"


def test_the_matched_control_is_still_disjoint_from_priority():
    rows = _ind_rows(12)
    sel = P.select(rows, n=20, seed=11, today=TODAY)
    assert ({r["ticker"] for r in sel["priority"]}
            & {r["ticker"] for r in sel["control"]}) == set()


def test_the_free_draw_is_still_available_to_reproduce_e43():
    rows = _ind_rows(12)
    sel = P.select(rows, n=20, seed=11, matched=False, today=TODAY)
    assert sel["control_design"] == "free_stratified"


def test_the_matched_draw_is_reproducible_under_its_seed():
    rows = _ind_rows(12)
    a = P.select(rows, n=20, seed=5, today=TODAY)
    b = P.select(rows, n=20, seed=5, today=TODAY)
    assert a["order"] == b["order"]
