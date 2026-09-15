"""SIC to sector mapping, and the re-score path that uses it.

The mapping decides which peers a company is ranked against, so a wrong range silently
moves a company into the wrong distribution and F1's result becomes meaningless rather
than wrong-looking. The boundary codes below are the ones the ranges actually turn on.
"""
from __future__ import annotations

import pandas as pd
import pytest

from clab.research import panel
from clab.research import sector_fill as sf


@pytest.mark.parametrize("sic,want", [
    ("7372", "Information Technology"),      # prepackaged software
    ("7370", "Information Technology"),      # lower edge of the software block
    ("7379", "Information Technology"),      # upper edge
    ("7380", "Industrials"),                 # one past it
    ("3674", "Information Technology"),      # semiconductors
    ("3679", "Information Technology"),
    ("3690", "Industrials"),
    ("6798", "Real Estate"),                 # REIT - a single-code range
    ("6799", "Financials"),                  # immediately after the REIT code
    ("6500", "Real Estate"),
    ("6499", "Financials"),
    ("4911", "Utilities"),
    ("4899", "Communication Services"),      # one below the utilities block
    ("2834", "Health Care"),                 # pharma
    ("2840", "Materials"),                   # one past the drug block
    ("2911", "Energy"),                      # petroleum refining
    ("1311", "Energy"),
    ("3711", "Consumer Discretionary"),      # motor vehicles
    ("3721", "Industrials"),                 # aircraft
    ("5912", "Consumer Staples"),            # drug stores, a single-code carve-out
    ("5913", "Consumer Discretionary"),
    ("5411", "Consumer Staples"),            # grocery
    ("8731", "Health Care"),                 # commercial research
    ("3826", "Health Care"),                 # lab instruments
    ("3825", "Information Technology"),      # one below
])
def test_sic_boundaries(sic, want):
    assert sf.sector_from_sic(sic) == want


@pytest.mark.parametrize("bad", [None, "", "   ", "0000", "abc", "9999", 0, float("nan")])
def test_unmappable_sic_returns_none_not_a_guess(bad):
    assert sf.sector_from_sic(bad) is None


def test_ranges_do_not_overlap():
    """An overlap would make the result depend on table order rather than on the code."""
    spans = sorted((lo, hi) for lo, hi, _s in sf.SIC_RANGES)
    for (lo1, hi1), (lo2, hi2) in zip(spans, spans[1:]):
        assert hi1 < lo2, f"ranges {lo1}-{hi1} and {lo2}-{hi2} overlap"


def test_leading_zero_sic_is_parsed():
    assert sf.sector_from_sic("0100") == "Consumer Staples"


def _panel():
    return pd.DataFrame([
        {"ticker": "AAA", "cik": "1", "date": pd.Timestamp("2020-01-31"),
         "sector": "Information Technology"},
        {"ticker": "BBB", "cik": "2", "date": pd.Timestamp("2020-01-31"),
         "sector": ""},          # a removed constituent: no GICS sector
        {"ticker": "CCC", "cik": "3", "date": pd.Timestamp("2020-01-31"),
         "sector": None},
    ])


def test_fill_keeps_gics_and_only_fills_the_gaps(monkeypatch):
    monkeypatch.setattr(sf, "sic_map",
                        lambda ciks: {"AAA": "3674", "BBB": "4911", "CCC": "6022"})
    q = sf.fill(_panel())
    assert list(q["sector_filled"]) == ["Information Technology", "Utilities",
                                        "Financials"]
    assert list(q["sector_basis"]) == ["gics", "sic", "sic"]
    # sector_sic is the CONSISTENT definition: SIC for everyone, including AAA
    assert list(q["sector_sic"]) == ["Information Technology", "Utilities", "Financials"]
    # `sector` itself must be untouched (pandas stores the None as NaN)
    assert q["sector"].iloc[0] == "Information Technology"
    assert q["sector"].iloc[1] == ""
    assert pd.isna(q["sector"].iloc[2])


def test_unresolvable_sic_is_labelled_not_silently_grouped(monkeypatch):
    monkeypatch.setattr(sf, "sic_map", lambda ciks: {"AAA": "3674"})
    q = sf.fill(_panel())
    assert q.loc[q.ticker == "BBB", "sector_filled"].iloc[0] == sf.UNKNOWN
    rep = sf.report(q)
    assert rep["symbols_still_unclassified"] == 2
    assert rep["rows_without_gics_sector"] == 2


def test_report_measures_sic_gics_disagreement(monkeypatch):
    monkeypatch.setattr(sf, "sic_map",
                        lambda ciks: {"AAA": "4911", "BBB": "4911", "CCC": "6022"})
    rep = sf.report(sf.fill(_panel()))
    dis = rep["disagreement_where_both_known"]
    assert dis["n_symbols"] == 1        # only AAA has both
    assert dis["agreement_rate"] == 0.0  # GICS says IT, SIC says Utilities
    assert "Information Technology -> Utilities" in dis["top_mismatches"]


# ---------------------------------------------------------------- re-score path
def _scored(n=20, sector="Tech", other="Utils"):
    """Two sectors with DIFFERENT margin levels - the software/utility case F1 exists for.

    Identical distributions would make the sector column irrelevant by construction and
    the test below would prove nothing.
    """
    rows = []
    offsets = {sector: 0.30, other: 0.0}
    for i in range(n):
        f = i / (n - 1)
        for sec in (sector, other):
            o = offsets[sec]
            rows.append({
                "ticker": f"{sec}{i:02d}", "cik": "1",
                "date": pd.Timestamp("2020-06-30"), "sector": sec,
                "gross_margin": 0.10 + o + 0.5 * f,
                "operating_margin": 0.02 + o + 0.3 * f,
                "fcf_margin": 0.01 + o + 0.25 * f, "roic": 0.03 + o + 0.3 * f,
                "roe": 0.05 + o + 0.35 * f,
                "fe_rest": 5, "fe_rest_avail": 12,
                "fe_sector_abs": 3, "fe_sector_avail": 6,
                "fe_sector_scored": ("fe_gross_margin,fe_operating_margin,"
                                     "fe_fcf_margin,fe_roic,fe_roe"),
                "bs": 5, "bs_avail": 10, "va": 6, "va_avail": 12,
                "en": 1, "en_avail": 2})
    return pd.DataFrame(rows)


def test_apply_sector_relative_rebuilds_fe_and_the_composite():
    df = _scored()
    out = panel.apply_sector_relative(df, "sector")
    assert set(out.fe_basis) == {"sector_relative"}
    assert (out.fe >= out.fe_rest).all(), "FE cannot fall below its non-sector half"
    sector_max = sum(mx for _m, mx in panel._SECTOR_SUBTEST_MAX.values())
    assert (out.fe <= out.fe_rest + sector_max).all(), "FE exceeded the sector block max"
    assert (out.measured_earned == out.fe + out.bs + out.va + out.en).all()
    assert (out.measured_avail == out.fe_avail + out.bs_avail + out.va_avail
            + out.en_avail).all()
    assert (out.measured_pct == out.measured_earned / out.measured_avail).all()


def test_changing_the_sector_column_changes_the_ranking():
    """The whole point: which column is used must actually matter."""
    df = _scored()
    df["sector_one"] = "ALL"          # everyone in one sector
    by_sector = panel.apply_sector_relative(df, "sector")
    by_one = panel.apply_sector_relative(df, "sector_one")
    assert not by_sector.fe.equals(by_one.fe), (
        "collapsing two sectors into one did not change any score")


def test_apply_sector_relative_refuses_an_incomplete_panel():
    df = _scored().drop(columns=["fe_sector_scored"])
    with pytest.raises(ValueError, match="missing columns"):
        panel.apply_sector_relative(df, "sector")


def test_score_panel_refuses_when_the_f1_columns_are_absent():
    """This exact wiring bug shipped once: fe_sector_scored was computed but never copied
    onto the panel row, so every sector distribution filtered to zero peers and all 67,889
    rows scored on the absolute basis while the run reported success."""
    df = _scored().drop(columns=["fe_sector_scored"])
    with pytest.raises(ValueError, match="fe_sector_scored"):
        panel.score_panel(df, sector_relative=True)


def test_score_panel_refuses_an_unknown_sector_column():
    with pytest.raises(ValueError, match="sector column"):
        panel.score_panel(_scored(), sector_relative=True, sector_col="nope")


def test_total_fallback_is_an_error_not_a_silent_absolute_panel():
    """Too few peers everywhere means F1 did nothing; that must not look like a result."""
    thin = _scored(n=3)          # 3 peers per sector, below SECTOR_RELATIVE_MIN_PEERS
    with pytest.raises(ValueError, match="ZERO sector-relative rows"):
        panel.apply_sector_relative(thin, "sector")
