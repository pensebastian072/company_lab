"""Computing market share instead of asking for it, and the guard that makes it safe.

The whole risk of this module is a wrong match: one institution's deposit trend attached
to another company's record, carrying a real FDIC URL that makes it look impeccably
sourced. Most of what is pinned here is that guard.
"""
from __future__ import annotations

import pytest

from clab.external import marketshare as MS
from clab.external.schema import UNKNOWN


def _rows(spec):
    """spec maps (holding company, market) to deposits."""
    return [{"NAMEHCR": h, "MSABR": m, "DEPSUMBR": v, "STNAMEBR": "X", "CNTYNAMB": "Y"}
            for (h, m), v in spec.items()]


def _two_years(a_spec, b_spec):
    return MS.market_shares(_rows(a_spec)), MS.market_shares(_rows(b_spec))


# ------------------------------------------------------------------ matching
def test_matching_is_exact_and_a_prefix_is_not_enough():
    """The first draft allowed a strict prefix of exactly one holding name, and it
    matched FNB - F.N.B. Corporation, roughly 47 billion of deposits - to FNB FINANCIAL
    SERVICES, INC. VLY, Valley National Bancorp, matched VALLEY BANK SHARES, INC.
    Each returned a confident direction computed from the wrong bank's branches."""
    idx = MS.holding_index(_rows({("FNB FINANCIAL SERVICES, INC.", "1"): 100}))
    assert MS.match_company("FNB Financial Services", idx) is not None
    assert MS.match_company("F.N.B. Corporation", idx) is None


def test_matching_ignores_corporate_furniture():
    idx = MS.holding_index(_rows({("M&T BANK CORPORATION", "1"): 100}))
    assert MS.match_company("M&T Bank Corp", idx) == "M&T BANK CORPORATION"


def test_an_unmatched_company_is_unknown_not_a_guess():
    idx = MS.holding_index(_rows({("SOME OTHER BANK", "1"): 100}))
    assert MS.match_company("Nothing Like It", idx) is None


# ------------------------------------------------------------- the scale guard
def test_a_hundredfold_size_mismatch_is_rejected():
    """A second, independent line of defence: even an exact name match can land on the
    wrong institution."""
    ok, why = MS._plausible_scale(deposits=5_000, market_cap=50_000_000_000)
    assert not ok and "too small" in why


def test_a_plausible_bank_passes_the_scale_guard():
    ok, _ = MS._plausible_scale(deposits=50_000_000, market_cap=10_000_000_000)
    assert ok


def test_no_market_cap_does_not_block_the_check():
    ok, why = MS._plausible_scale(deposits=1_000, market_cap=None)
    assert ok and "no market cap" in why


# ------------------------------------------------------- the four disciplines
def test_only_markets_held_in_BOTH_years_are_compared():
    """Otherwise a bank exiting a weak market would read as gaining."""
    a, b = _two_years(
        {("ME", "1"): 100, ("ME", "2"): 100, ("RIVAL", "1"): 900, ("RIVAL", "2"): 900},
        {("ME", "1"): 100, ("RIVAL", "1"): 900})
    res = MS.direction_for("ME", a, b)
    assert res["markets"] <= 1
    assert res["direction"] == UNKNOWN


def test_an_acquisition_sized_jump_is_excluded_not_counted_as_capture():
    """A bank that buys another bank gains share without competing better for a single
    dollar. Reading that as capture would be actively wrong."""
    a_spec = {("ME", str(i)): 100 for i in range(5)}
    b_spec = {("ME", str(i)): 100 for i in range(5)}
    b_spec[("ME", "0")] = 1000
    for i in range(5):
        a_spec[("RIVAL", str(i))] = 900
        b_spec[("RIVAL", str(i))] = 900
    a, b = _two_years(a_spec, b_spec)
    res = MS.direction_for("ME", a, b)
    assert res["excluded"] >= 1


def test_too_few_shared_markets_abstains():
    a, b = _two_years({("ME", "1"): 100, ("RIVAL", "1"): 900},
                      {("ME", "1"): 200, ("RIVAL", "1"): 900})
    res = MS.direction_for("ME", a, b)
    assert res["direction"] == UNKNOWN
    assert "minimum" in res["reason"]


def test_a_real_share_gain_reads_as_gaining():
    a_spec, b_spec = {}, {}
    for i in range(6):
        a_spec[("ME", str(i))] = 100
        b_spec[("ME", str(i))] = 130
        a_spec[("RIVAL", str(i))] = 900
        b_spec[("RIVAL", str(i))] = 870
    a, b = _two_years(a_spec, b_spec)
    res = MS.direction_for("ME", a, b)
    assert res["direction"] == "GAINING"
    assert res["share_change_pp"] > 0


def test_a_real_share_loss_reads_as_losing():
    a_spec, b_spec = {}, {}
    for i in range(6):
        a_spec[("ME", str(i))] = 130
        b_spec[("ME", str(i))] = 100
        a_spec[("RIVAL", str(i))] = 870
        b_spec[("RIVAL", str(i))] = 900
    a, b = _two_years(a_spec, b_spec)
    assert MS.direction_for("ME", a, b)["direction"] == "LOSING"


# ------------------------------------------------------------------- claims
def test_the_claim_says_it_is_DEPOSIT_share_and_names_the_holding_company():
    """This settles deposit share, which for a regional bank is most of the franchise
    and for a diversified one is not. A reader must be able to see what it matched."""
    c = MS.claim_for("MTB", "M&T BANK CORPORATION",
                     {"direction": "LOSING", "reason": "x"}, 2023, 2024)
    assert "deposit market share" in c["text"]
    assert "M&T BANK CORPORATION" in c["text"]
    assert c["independence_domain"] == "PRIMARY_DATA"
    assert c["quote"] is None


def test_a_computed_claim_is_not_run_through_quote_verification(tmp_path):
    """It has no quote to check. Running it through check_quote would score it
    UNVERIFIABLE and turn our own arithmetic into a fabrication signal."""
    from clab.external import verify as V
    from clab.external.schema import Claim
    from clab.external.store import ExternalStore
    store = ExternalStore(tmp_path / "t.duckdb")
    store.insert_claims([Claim(
        claim_id="c_000000000001", field="market_share_direction", text="computed",
        source_url="https://banks.data.fdic.gov/api/sod", quote=None,
        verify_status="VERIFIED_LOCAL", overlap=1.0, ticker="MTB")], request_id="fdic")
    res = V.verify_all(store=store, apply=True)
    assert res["tally"].get("UNVERIFIABLE", 0) == 0
    assert store.verify_rates() == {"VERIFIED_LOCAL": 1}


def test_a_computed_direction_never_overwrites_a_researched_one(tmp_path):
    """A computed number does not overrule a researched conclusion - a disagreement is
    a contradiction worth surfacing, not something to silently overwrite."""
    from clab.external.store import ExternalStore
    store = ExternalStore(tmp_path / "t.duckdb")
    store.upsert_company({"ticker": "MTB", "research_version": "v1",
                          "market_share_direction": "GAINING"})
    out = MS.apply_to("v1", {"MTB": {
        "direction": "LOSING",
        "claim": MS.claim_for("MTB", "M&T BANK CORPORATION",
                              {"direction": "LOSING", "reason": "x"}, 2023, 2024)}},
        store=store)
    assert out["filled"] == []
    assert out["conflicts"] and out["conflicts"][0]["researched"] == "GAINING"
    assert store.company("MTB", "v1")["market_share_direction"] == "GAINING"


def test_a_computed_direction_fills_an_unknown(tmp_path):
    from clab.external.store import ExternalStore
    store = ExternalStore(tmp_path / "t.duckdb")
    store.upsert_company({"ticker": "MTB", "research_version": "v1",
                          "market_share_direction": UNKNOWN})
    out = MS.apply_to("v1", {"MTB": {
        "direction": "LOSING",
        "claim": MS.claim_for("MTB", "M&T BANK CORPORATION",
                              {"direction": "LOSING", "reason": "x"}, 2023, 2024)}},
        store=store)
    assert out["filled"] == ["MTB"]
    assert store.company("MTB", "v1")["market_share_direction"] == "LOSING"


def test_the_live_fdic_pull_is_cached_not_refetched():
    """A free primary source stays free only if it is not re-pulled every run."""
    if not MS._cache_path(2024).exists():
        pytest.skip("no FDIC cache on disk")
    rows = MS.fetch_year(2024)
    assert len(rows) > 50_000
    assert {"NAMEHCR", "DEPSUMBR", "MSABR"} <= set(rows[0])


# ------------------------------------------- ambiguity is resolved by SIZE, never by order
def test_an_ambiguous_key_is_resolved_by_scale_and_not_by_row_order():
    """209 of the 2,991 normalised keys in the 2024 survey are claimed by more than one
    holding company, because _norm strips "financial", "group", "holding" and more:
    "citizens financial group" and "citizens holding company" both become "citizens".
    setdefault kept whichever the file listed first, so CFG - roughly $180bn of deposits -
    resolved to CITIZENS HOLDING COMPANY, a small Mississippi bank, and only the scale
    guard stopped it reaching the store."""
    rows = _rows({("CITIZENS HOLDING COMPANY", "1"): 1_200_000,
                  ("CITIZENS FINANCIAL GROUP, INC.", "2"): 180_000_000})
    col = MS.collision_index(rows)
    assert col["citizens"] == ["CITIZENS FINANCIAL GROUP, INC.", "CITIZENS HOLDING COMPANY"]
    # the unambiguous index refuses it outright; compute() then resolves by size
    assert MS.match_company("Citizens Financial Group", MS.holding_index(rows)) is None


def test_a_name_that_normalises_to_nothing_never_matches():
    """"The Bancorp, Inc." strips to the empty string - every token is a corporate-form
    stopword - so it carries no distinguishing content and must not match anything."""
    assert MS._norm("The Bancorp, Inc.") == ""
    rows = _rows({("BANCORP, INC., THE", "1"): 7_200_000,
                  ("BANCORP FINANCIAL, INC.", "2"): 1_300_000})
    assert MS.match_company("The Bancorp, Inc.", MS.holding_index(rows)) is None
    assert "" not in MS.collision_index(rows)


def test_namefull_is_a_second_exact_key():
    """The book holds the BANK's common name; NAMEHCR is the holding company's legal name.
    "Frost Bank" cannot normalise into "CULLEN/FROST BANKERS, INC." - a different name, not
    a formatting difference - but FDIC's NAMEFULL for that institution IS "Frost Bank"."""
    rows = _rows({("CULLEN/FROST BANKERS, INC.", "1"): 40_000_000})
    for r in rows:
        r["NAMEFULL"] = "Frost Bank"
    idx = MS.holding_index(rows)
    assert MS.match_company("Frost Bank", idx) == "CULLEN/FROST BANKERS, INC."
