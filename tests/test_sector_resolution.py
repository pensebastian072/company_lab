"""The sector column must only ever hold one of the eleven GICS names.

Falling back to the raw SIC DESCRIPTION put values like "Services-Prepackaged Software",
"State Commercial Banks" and "Biological Products, (No Diagnostic Substances)" in the
sector column - 208 rows across 113 pseudo-sectors, so the Sectors sheet fragmented into
124 groups instead of 11.

That is not cosmetic. The Sectors sheet exists to show E03 R1's finding that the ranking
is substantially a sector bet, and F1 scores five margin metrics as a percentile WITHIN
sector against a minimum peer count - a company alone in "Laboratory Analytical
Instruments" has no peers and silently falls back to absolute bands.
"""
from __future__ import annotations

import pytest

from clab.research.sector_fill import sector_from_sic

GICS = {
    "Information Technology", "Health Care", "Financials", "Consumer Discretionary",
    "Communication Services", "Industrials", "Consumer Staples", "Energy",
    "Utilities", "Real Estate", "Materials",
}

#: the SIC codes behind the pseudo-sectors actually seen in the scores table
OBSERVED = {
    "6798": ("Real Estate Investment Trusts", "Real Estate"),
    "2834": ("Pharmaceutical Preparations", "Health Care"),
    "7372": ("Services-Prepackaged Software", "Information Technology"),
    "3674": ("Semiconductors & Related Devices", "Information Technology"),
    "6022": ("State Commercial Banks", "Financials"),
    "6021": ("National Commercial Banks", "Financials"),
    "2836": ("Biological Products", "Health Care"),
    "6311": ("Life Insurance", "Financials"),
    "1311": ("Crude Petroleum & Natural Gas", "Energy"),
    "6282": ("Investment Advice", "Financials"),
    "5500": ("Retail-Auto Dealers", "Consumer Discretionary"),
    "6211": ("Security Brokers & Dealers", "Financials"),
    "3841": ("Surgical & Medical Instruments", "Health Care"),
    "3826": ("Laboratory Analytical Instruments", "Health Care"),
    "5812": ("Retail-Eating Places", "Consumer Discretionary"),
}


@pytest.mark.parametrize("sic,pair", OBSERVED.items(), ids=list(OBSERVED))
def test_observed_pseudo_sectors_map_to_a_real_gics_sector(sic, pair):
    _desc, want = pair
    got = sector_from_sic(sic)
    assert got == want, f"SIC {sic} ({_desc}) -> {got}, expected {want}"
    assert got in GICS


def test_engine_prefers_the_index_sector_over_sic():
    """A GICS sector from the index page is authoritative; SIC is only the fallback."""
    sector = "Industrials"
    assert (sector or sector_from_sic("7372")) == "Industrials"


def test_engine_falls_back_to_a_gics_name_not_a_description():
    sector = ""
    resolved = sector or sector_from_sic("7372") or ""
    assert resolved == "Information Technology"
    assert resolved in GICS


def test_unmappable_sic_yields_empty_not_a_description():
    """Better an empty sector than a one-company pseudo-sector."""
    sector = ""
    resolved = sector or sector_from_sic("9999") or ""
    assert resolved == ""


def test_engine_uses_sector_fill_rather_than_the_description():
    """Guards the specific regression: engine.py must not put sic_desc in `sector`."""
    import inspect

    from clab.runner import engine

    src = inspect.getsource(engine)
    assert "sector_from_sic" in src
    assert "sector=sector or (sic_desc or \"\")" not in src, (
        "the raw SIC description is back in the sector column")
