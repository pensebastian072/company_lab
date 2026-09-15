"""E38's draw - the pairing filter, which is the only thing this module has to get right.

The control lane exists to make a three-way paired comparison possible, and a pair that
is not a pair silently becomes an unpaired difference: a company the v2 lane scored only
half of would put a MISSING component into what the write-up calls the model effect. So
the properties pinned here are membership ones.

The stratification itself is E36's and is deliberately not re-implemented - the reuse is
the point, and a second copy would be a second chance to get the terciles wrong.
"""
from __future__ import annotations

import json

from clab.research import e38_draw_control as e38


def _payload(tmp_path, cik, component, ticker):
    path = tmp_path / f"{cik}_{component}_{cik}{component}.json"
    path.write_text(json.dumps({"ticker": ticker, "cik": cik}), encoding="utf-8")
    return path


def test_two_of_three_components_is_not_a_scored_company(tmp_path):
    """A company caught mid-flight when the box went off has SG and BQ and no MG. It is
    not comparable, and counting it would compare a partial judged half."""
    _payload(tmp_path, "0000000001", "SG", "AAA")
    _payload(tmp_path, "0000000001", "BQ", "AAA")
    assert e38.v2_complete_tickers(str(tmp_path)) == set()

    _payload(tmp_path, "0000000001", "MG", "AAA")
    assert e38.v2_complete_tickers(str(tmp_path)) == {"AAA"}


def test_a_company_with_no_sg_payload_is_not_counted(tmp_path):
    """Ticker is read off the SG payload, so three files without one resolve to no
    company at all rather than to a guess from the filename."""
    _payload(tmp_path, "0000000002", "BQ", "BBB")
    _payload(tmp_path, "0000000002", "MG", "BBB")
    _payload(tmp_path, "0000000002", "ER", "BBB")
    assert e38.v2_complete_tickers(str(tmp_path)) == set()


def test_unreadable_payload_is_skipped_not_fatal(tmp_path):
    """A truncated write from a killed lane must not take the whole draw down with it."""
    _payload(tmp_path, "0000000003", "SG", "CCC")
    _payload(tmp_path, "0000000003", "BQ", "CCC")
    _payload(tmp_path, "0000000003", "MG", "CCC")
    bad = tmp_path / "0000000004_SG_x.json"
    bad.write_text('{"ticker": "DDD"', encoding="utf-8")   # truncated on purpose
    (tmp_path / "0000000004_BQ_x.json").write_text("{}", encoding="utf-8")
    (tmp_path / "0000000004_MG_x.json").write_text("{}", encoding="utf-8")
    assert e38.v2_complete_tickers(str(tmp_path)) == {"CCC"}


def test_components_required_is_three():
    """SG + BQ + MG. If the framework ever grows a fourth judged component this constant
    is the thing that must move, and a test is where that gets noticed."""
    assert e38.COMPONENTS_REQUIRED == 3
