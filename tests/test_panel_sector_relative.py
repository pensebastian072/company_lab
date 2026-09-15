"""F1 in the research panel: the sector-relative FE path must actually fire.

A small probe can never exercise this - the fallback needs fewer than
SECTOR_RELATIVE_MIN_PEERS peers and a 12-symbol probe always has fewer. These tests
build a synthetic cross-section so the relative branch is reached, and pin the two ways
it could silently hand out points it should not:

  * a sub-test the real scorer marked NOT_APPLICABLE must stay unavailable;
  * the percentile denominator must exclude filers the metric was not scored for.
"""
from __future__ import annotations

import pandas as pd

from clab.research import panel
from clab.scoring import rubric

FE_KEYS = "fe_gross_margin,fe_operating_margin,fe_fcf_margin,fe_roic,fe_roe"
SECTOR_MAX = sum(mx for _m, mx in panel._SECTOR_SUBTEST_MAX.values())
REST_MAX = rubric.COMPONENTS["FE"][1] - SECTOR_MAX


def _row(ticker, sector, *, gm, om, fcf, roic, roe, scored=FE_KEYS):
    return {"ticker": ticker, "cik": "0000000001", "date": pd.Timestamp("2020-06-30"),
            "sector": sector, "sub_industry": sector, "profile": "STANDARD",
            "price": 100.0, "gross_margin": gm, "operating_margin": om,
            "fcf_margin": fcf, "roic": roic, "roe": roe,
            "fe_rest": 5, "fe_rest_avail": REST_MAX,
            "fe_sector_abs": 3, "fe_sector_avail": SECTOR_MAX,
            "fe_sector_scored": scored}


def _cross_section(n=20, sector="Tech"):
    """n peers with margins fanned out across the whole range."""
    rows = []
    for i in range(n):
        f = i / (n - 1)
        rows.append(_row(f"T{i:02d}", sector, gm=0.10 + 0.50 * f, om=0.02 + 0.30 * f,
                         fcf=0.01 + 0.25 * f, roic=0.03 + 0.30 * f, roe=0.05 + 0.35 * f))
    return pd.DataFrame(rows)


def test_relative_branch_fires_with_enough_peers():
    df = _cross_section(20)
    dists = panel._sector_distributions(df)
    assert len(dists["Tech"]["gross_margin"]) == 20

    best = df.iloc[-1]
    worst = df.iloc[0]
    e_best, a_best, basis = panel._fe_sector_relative(best, dists)
    e_worst, a_worst, basis_w = panel._fe_sector_relative(worst, dists)

    assert basis == basis_w == "sector_relative"
    assert a_best == a_worst == SECTOR_MAX
    assert e_best == SECTOR_MAX, "top of every metric in its sector should max the block"
    assert e_worst == 0, "bottom of every metric should earn nothing"


def test_falls_back_to_absolute_below_min_peers():
    df = _cross_section(rubric.SECTOR_RELATIVE_MIN_PEERS - 1)
    dists = panel._sector_distributions(df)
    earned, avail, basis = panel._fe_sector_relative(df.iloc[-1], dists)
    assert basis == "absolute"
    assert (earned, avail) == (3, SECTOR_MAX)   # the stored absolute-basis points


def test_not_applicable_subtest_stays_unavailable():
    """A bank with no gross-profit line must not be handed the gross-margin points."""
    df = _cross_section(20, sector="Financials")
    bank = _row("BANK", "Financials", gm=None, om=0.30, fcf=0.20, roic=0.25, roe=0.30,
                scored="fe_operating_margin,fe_fcf_margin,fe_roic,fe_roe")
    df = pd.concat([df, pd.DataFrame([bank])], ignore_index=True)
    dists = panel._sector_distributions(df)

    earned, avail, basis = panel._fe_sector_relative(df.iloc[-1], dists)
    gm_max = panel._SECTOR_SUBTEST_MAX["fe_gross_margin"][1]
    assert basis == "sector_relative"
    assert avail == SECTOR_MAX - gm_max, "gross margin must not become available"
    assert earned <= avail


def test_denominator_excludes_unscored_filers():
    """Peers the metric was not scored for must not enter the percentile denominator."""
    df = _cross_section(20)
    ghosts = pd.DataFrame([
        _row(f"G{i}", "Tech", gm=0.95, om=0.9, fcf=0.9, roic=0.9, roe=0.9,
             scored="fe_roe")                      # gross margin NOT scored for these
        for i in range(10)])
    dists = panel._sector_distributions(pd.concat([df, ghosts], ignore_index=True))
    assert len(dists["Tech"]["gross_margin"]) == 20, "ghost filers leaked in"
    assert len(dists["Tech"]["roe"]) == 30, "roe was scored for the ghosts"


def test_score_panel_absolute_is_unchanged_by_the_split():
    """fe_rest + fe_sector_abs must reconstruct the original FE exactly."""
    df = _cross_section(20)
    df["fe"] = df.fe_rest + df.fe_sector_abs
    df["fe_avail"] = df.fe_rest_avail + df.fe_sector_avail
    assert (df.fe == 8).all()
    assert (df.fe_avail == REST_MAX + SECTOR_MAX).all()
    assert df.fe_avail.iloc[0] == rubric.COMPONENTS["FE"][1]
