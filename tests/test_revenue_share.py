"""Market-share direction from revenue share, and the guards that make it honest.

The field resolved for 4 of 183 companies by research and cost one blocking claim per
company to fail. This computes it instead. Most of what is pinned here is the reasons it
is allowed to abstain, plus the one property that makes it work for commodities at all:
share is a ratio, so a price move common to every peer cancels.
"""
from __future__ import annotations

from clab.external import revenue_share as RS
from clab.external.schema import UNKNOWN


def _rev(**kw):
    return {t: (now, prior) for t, (now, prior) in kw.items()}


# ------------------------------------------------- the property that makes it work
def test_a_price_shock_common_to_every_peer_cancels():
    """Every peer's revenue doubles. Nobody gained share on anybody; all must read FLAT.
    This is the whole argument for using the layer on commodity businesses, where an
    absolute revenue series is a record of the price and not of the company."""
    prior = {"A": 100.0, "B": 200.0, "C": 300.0, "D": 400.0}
    rev = {t: (v * 2.0, v) for t, v in prior.items()}
    out = RS.direction_for_industry("x", list(rev), rev)
    assert {v["direction"] for v in out.values()} == {"FLAT"}
    assert all(abs(v["rel_change"]) < 1e-9 for v in out.values())


def test_shares_sum_to_one_in_both_windows():
    rev = _rev(A=(120.0, 100.0), B=(190.0, 200.0), C=(300.0, 300.0), D=(390.0, 400.0))
    out = RS.direction_for_industry("x", list(rev), rev)
    assert abs(sum(v["share_now"] for v in out.values()) - 1.0) < 1e-6
    assert abs(sum(v["share_prior"] for v in out.values()) - 1.0) < 1e-6


def test_a_real_gain_and_the_matching_loss_are_both_reported():
    """Share is zero-sum, so a gainer implies a loser. Both must appear.

    Written first with one peer doubling while three stayed flat, which returned
    nothing: doubling against flat peers is a 100-point excess over the median and the
    structural guard excluded it. That is the guard working - a company that doubles
    while nobody else moves has almost certainly bought something. The gain has to be
    the size of a real competitive move to be read as one."""
    rev = _rev(A=(130.0, 100.0), B=(130.0, 100.0), C=(85.0, 100.0), D=(85.0, 100.0))
    out = RS.direction_for_industry("x", list(rev), rev)
    assert out["A"]["direction"] == "GAINING" and out["B"]["direction"] == "GAINING"
    assert out["C"]["direction"] == "LOSING" and out["D"]["direction"] == "LOSING"


# --------------------------------------------------------------------- the guards
def test_a_structural_move_is_excluded_in_BOTH_directions():
    """The first draft guarded only growth. A divestiture loses share exactly the way an
    acquisition gains it, and OXY (-22.7%) and NOG (-25.6%) read as out-competed."""
    up = _rev(A=(200.0, 100.0), B=(100.0, 100.0), C=(100.0, 100.0), D=(100.0, 100.0),
              E=(100.0, 100.0))
    assert "A" not in RS.direction_for_industry("x", list(up), up)
    down = _rev(A=(40.0, 100.0), B=(100.0, 100.0), C=(100.0, 100.0), D=(100.0, 100.0),
                E=(100.0, 100.0))
    assert "A" not in RS.direction_for_industry("x", list(down), down)


def test_an_excluded_peer_leaves_the_denominator_too():
    """Otherwise the acquirer's new revenue inflates the total and every remaining peer
    reads as losing share for a reason that is not about them."""
    rev = _rev(A=(60.0, 10.0), B=(100.0, 100.0), C=(100.0, 100.0),
               D=(100.0, 100.0), E=(100.0, 100.0))
    out = RS.direction_for_industry("x", list(rev), rev)
    assert set(out) == {"B", "C", "D", "E"}
    assert {v["direction"] for v in out.values()} == {"FLAT"}


def test_excluding_a_LARGE_peer_abstains_entirely_rather_than_comparing_a_remnant():
    """A peer big enough that dropping it takes the remaining set under
    MIN_REVENUE_COVERED means the denominator has moved too much to compare against.
    Found by writing the test above with a 500-vs-100 acquirer: the four flat peers were
    only 44% of current revenue afterwards, and the module correctly returned nothing."""
    rev = _rev(A=(500.0, 100.0), B=(100.0, 100.0), C=(100.0, 100.0),
               D=(100.0, 100.0), E=(100.0, 100.0))
    assert RS.direction_for_industry("x", list(rev), rev) == {}


def test_a_smaller_structural_move_is_DECLARED_not_hidden():
    """The book carries no M&A metric, so a 32% move cannot be detected as an
    acquisition. EQT grew 32.3% in the window it absorbed Equitrans and reads as a top
    share gainer. It is flagged in its own claim text rather than trusted or withheld."""
    rev = _rev(A=(130.0, 100.0), B=(100.0, 100.0), C=(100.0, 100.0), D=(100.0, 100.0))
    out = RS.direction_for_industry("x", list(rev), rev)
    assert out["A"]["structural_suspect"] is True
    assert out["B"]["structural_suspect"] is False
    assert "CAVEAT" in RS.claim_for("A", out["A"])["text"]


def test_too_few_peers_abstains():
    rev = _rev(A=(200.0, 100.0), B=(100.0, 100.0), C=(100.0, 100.0))
    assert RS.direction_for_industry("x", list(rev), rev) == {}


def test_a_peer_missing_either_window_is_dropped_from_both_totals():
    rev = _rev(A=(100.0, 100.0), B=(100.0, 100.0), C=(100.0, 100.0), D=(100.0, 100.0))
    out = RS.direction_for_industry("x", list(rev) + ["MISSING"], rev)
    assert set(out) == {"A", "B", "C", "D"}


# ------------------------------------------- it must not undo the NOT_APPLICABLE rule
def test_a_nominated_industry_still_gets_a_PEER_POSITION_but_is_not_contestable():
    """Two different questions, and an earlier draft collapsed them into one.

    "Did contestable share move" is meaningless for a franchise monopoly, so
    market_share_direction stays NOT_APPLICABLE there. "Who is biggest in this product
    market and who is growing" is answerable everywhere - and refusing to compute it
    threw away a real answer for 54 of 59 utilities, where the share spread runs 1.6% to
    39.9%. The peer_* fields are filled for every industry; only `contestable` gates the
    categorical."""
    rev = _rev(A=(120.0, 100.0), B=(100.0, 100.0), C=(100.0, 100.0), D=(100.0, 100.0))
    for ind in ("electric_utilities", "multi_utilities", "gas_utilities", "water_utilities"):
        out = RS.direction_for_industry(ind, list(rev), rev)
        assert out, "peer position must still be computed"
        assert all(v["contestable"] is False for v in out.values())
        assert out["A"]["share_rank"] == 1 and out["A"]["peers_ranked"] == 4
    assert all(v["contestable"] for v in
               RS.direction_for_industry("upstream_oil_gas", list(rev), rev).values())


def test_a_non_contestable_industry_never_fills_market_share_direction(tmp_path):
    """The gate that makes the split safe. Writing a direction for a regulated utility
    would supply the very value applicability.py's two-condition rule needs to be absent,
    and would silently re-enable a field that was retired on purpose."""
    from clab.external.store import ExternalStore
    store = ExternalStore(tmp_path / "t.duckdb")
    store.upsert_company({"ticker": "AAA", "research_version": "v1",
                          "industry_id": "water_utilities",
                          "market_share_direction": UNKNOWN})
    rev = _rev(AAA=(120.0, 100.0), B=(100.0, 100.0), C=(100.0, 100.0), D=(100.0, 100.0))
    res = RS.direction_for_industry("water_utilities", list(rev), rev)
    out = RS.apply_to("v1", res, store=store)
    assert out["filled"] == []
    assert "AAA" in out["position_only"]
    row = store.company("AAA", "v1")
    assert row["market_share_direction"] == UNKNOWN
    assert row["peer_revenue_share"] and row["peer_growth_direction"]


# ---------------------------------------------------------------------- the claim
def test_the_claim_says_it_is_the_LISTED_PEER_SET_not_the_market():
    """XOM competes with Saudi Aramco and thousands of private operators, none of which
    are in this book. A reader must not take this for a market-share statistic."""
    rev = _rev(A=(120.0, 100.0), B=(100.0, 100.0), C=(100.0, 100.0), D=(100.0, 100.0))
    c = RS.claim_for("A", RS.direction_for_industry("x", list(rev), rev)["A"])
    assert "LISTED PEER SET" in c["text"]
    assert "NOT of the market" in c["text"]
    assert c["independence_domain"] == "PRIMARY_DATA"
    assert c["quote"] is None


def test_a_computed_direction_never_overwrites_a_researched_one(tmp_path):
    from clab.external.store import ExternalStore
    store = ExternalStore(tmp_path / "t.duckdb")
    store.upsert_company({"ticker": "AAA", "research_version": "v1",
                          "market_share_direction": "GAINING"})
    res = {"AAA": {"direction": "LOSING", "industry_id": "x", "share_now": 0.1,
                   "share_prior": 0.2, "rel_change": -0.5, "peers": 5,
                   "contestable": True, "share_rank": 3, "peers_ranked": 5,
                   "structural_suspect": False, "own_revenue_change": -0.1,
                   "excess_over_peers": -0.1, "peer_median_revenue_change": 0.0,
                   "excluded_restructured": [], "reason": "r"}}
    out = RS.apply_to("v1", res, store=store)
    assert out["filled"] == [] and out["conflicts"]
    assert store.company("AAA", "v1")["market_share_direction"] == "GAINING"


def test_a_computed_direction_fills_an_unknown(tmp_path):
    from clab.external.store import ExternalStore
    store = ExternalStore(tmp_path / "t.duckdb")
    store.upsert_company({"ticker": "AAA", "research_version": "v1",
                          "market_share_direction": UNKNOWN})
    res = {"AAA": {"direction": "LOSING", "industry_id": "x", "share_now": 0.1,
                   "share_prior": 0.2, "rel_change": -0.5, "peers": 5,
                   "contestable": True, "share_rank": 3, "peers_ranked": 5,
                   "structural_suspect": False, "own_revenue_change": -0.1,
                   "excess_over_peers": -0.1, "peer_median_revenue_change": 0.0,
                   "excluded_restructured": [], "reason": "r"}}
    assert RS.apply_to("v1", res, store=store)["filled"] == ["AAA"]
    assert store.company("AAA", "v1")["market_share_direction"] == "LOSING"
