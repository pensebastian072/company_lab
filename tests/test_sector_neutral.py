"""Sector-neutral percentiles.

E05's F1 is the cautionary case behind every test here: it moved the sector spread and
still FAILED its criterion, because moving a spread is not the same as ranking better.
These tests pin the mechanics and the abstentions, never a claim of improvement.
"""
from __future__ import annotations

import pytest

from clab.scoring import sector_neutral as sn


def _rows(*specs):
    return [{"ticker": t, "sector": sec, "sub_industry": sub, "composite_strict": v}
            for t, sec, sub, v in specs]


def _peers(sector, sub, n, start=50):
    return [(f"{sub[:2]}{i}", sector, sub, start + i) for i in range(n)]


def test_the_best_in_its_sub_industry_scores_100():
    rows = _rows(*_peers("IT", "Semiconductors", 6))
    sn.neutralize(rows)
    top = max(rows, key=lambda r: r["composite_strict"])
    assert top["sub_industry_percentile"] == 1.0
    assert top["sector_neutral_score"] == 100.0
    assert top["sector_neutral_basis"] == "sub_industry"


def test_a_low_raw_score_can_outrank_a_high_one_across_sectors():
    """The whole point: 68 in Energy against 78 in software."""
    rows = _rows(*_peers("Energy", "Oil & Gas", 6, start=30),
                 *_peers("IT", "Software", 6, start=70))
    rows.append({"ticker": "ENERGY_STAR", "sector": "Energy",
                 "sub_industry": "Oil & Gas", "composite_strict": 68})
    rows.append({"ticker": "SOFT_LAGGARD", "sector": "IT",
                 "sub_industry": "Software", "composite_strict": 71})
    sn.neutralize(rows)
    e = next(r for r in rows if r["ticker"] == "ENERGY_STAR")
    s = next(r for r in rows if r["ticker"] == "SOFT_LAGGARD")
    assert e["composite_strict"] < s["composite_strict"]
    assert e["sector_neutral_score"] > s["sector_neutral_score"]


def test_sub_industry_beats_sector_when_both_are_available():
    """Semiconductors and enterprise software must not share expectations."""
    rows = _rows(*_peers("IT", "Semiconductors", 6, start=80),
                 *_peers("IT", "Software", 6, start=40))
    sn.neutralize(rows)
    assert all(r["sector_neutral_basis"] == "sub_industry" for r in rows)
    # a mid semiconductor is mid among semis, not top of all IT
    semi = sorted((r for r in rows if r["sub_industry"] == "Semiconductors"),
                  key=lambda r: r["composite_strict"])[2]
    assert semi["sector_neutral_score"] < 100.0


def test_a_thin_sub_industry_falls_back_to_sector_and_says_so():
    rows = _rows(*_peers("IT", "Software", 6),
                 ("LONE", "IT", "Quantum Widgets", 90))
    sn.neutralize(rows)
    lone = next(r for r in rows if r["ticker"] == "LONE")
    assert lone["sub_industry_percentile"] is None
    assert lone["sector_neutral_basis"] == "sector"
    assert lone["sector_neutral_n"] == 7


def test_too_few_peers_anywhere_means_ABSTAIN_not_a_guess():
    """A made-up percentile is worse than none - the same call va.py already makes."""
    rows = _rows(("A", "Tiny", "Tiny", 90), ("B", "Tiny", "Tiny", 10))
    sn.neutralize(rows)
    assert all(r["sector_neutral_score"] is None for r in rows)
    assert all(r["sector_neutral_basis"] == "none" for r in rows)


def test_an_unscored_company_is_left_alone():
    rows = _rows(*_peers("IT", "Software", 6))
    rows.append({"ticker": "NOSCORE", "sector": "IT", "sub_industry": "Software",
                 "composite_strict": None})
    sn.neutralize(rows)
    n = next(r for r in rows if r["ticker"] == "NOSCORE")
    assert n["sector_neutral_score"] is None
    assert n["raw_score"] is None


def test_raw_score_is_preserved_untouched():
    """composite_strict stays the headline; this is additive, never a replacement."""
    rows = _rows(*_peers("IT", "Software", 6))
    before = [r["composite_strict"] for r in rows]
    sn.neutralize(rows)
    assert [r["composite_strict"] for r in rows] == before
    assert [r["raw_score"] for r in rows] == before


def test_the_peer_count_is_recorded_so_6_is_not_mistaken_for_60():
    rows = _rows(*_peers("IT", "Software", 6))
    sn.neutralize(rows)
    assert all(r["sector_neutral_n"] == 6 for r in rows)


# ------------------------------------------------------------------ the report
def test_the_spread_report_refuses_to_claim_improvement():
    rows = _rows(*_peers("IT", "Software", 6, start=70),
                 *_peers("Utilities", "Electric", 6, start=30))
    sn.neutralize(rows)
    rep = sn.spread_report(rows)
    assert rep["spread_raw"] > rep["spread_neutral"]
    assert "BY CONSTRUCTION" in rep["note"]
    assert "not evidence" in rep["note"]


def test_the_report_counts_which_basis_was_used():
    rows = _rows(*_peers("IT", "Software", 6), ("LONE", "IT", "Odd", 90))
    sn.neutralize(rows)
    rep = sn.spread_report(rows)
    assert rep["by_basis"]["sub_industry"] == 6
    assert rep["by_basis"]["sector"] == 1
