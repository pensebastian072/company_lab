"""P2 is a claim about a dimension's SPREAD across sectors, so it must be computable.

E12 says a dimension may only be considered inapplicable if abstention is *concentrated*
by sector - a >40pp gap between the highest and lowest sector null rate. The measurement
used to store each sector's worst four dimensions only, and the minimum of a spread is
exactly the entry a "worst four" view drops. These pin the parts that decide the
criterion: the denominator, the small-sector guard, and the high-floor qualifier that
separates "inapplicable here" from "unanswerable everywhere".
"""
import collections

from clab.research import bq_abstention as bq


def _sector(n, nulls, seen=None):
    return {"n": n, "below": 0,
            "nulls": collections.Counter(nulls),
            "seen": collections.Counter(seen or {k: n for k in nulls})}


def test_spread_uses_the_lowest_sector_not_the_worst_four():
    by_sector = {
        "Utilities": _sector(50, {"network_effects": 49}),
        "Communication Services": _sector(50, {"network_effects": 20}),
        "Industrials": _sector(50, {"network_effects": 40}),
    }
    p = bq._p2(by_sector)["network_effects"]
    assert p["max_sector"] == "Utilities" and p["max_pct"] == 98.0
    assert p["min_sector"] == "Communication Services" and p["min_pct"] == 40.0
    assert p["spread_pp"] == 58.0
    assert p["spread_over_40pp"] is True


def test_a_tiny_sector_cannot_set_an_endpoint():
    """Without the guard, the 1-company '?' sector defines every spread at 0 or 100."""
    by_sector = {
        "Financials": _sector(100, {"brand": 30}),
        "Industrials": _sector(100, {"brand": 35}),
        "?": _sector(1, {"brand": 1}),
    }
    p = bq._p2(by_sector)["brand"]
    assert p["sectors"] == 2
    assert p["max_pct"] == 35.0 and p["spread_pp"] == 5.0
    assert p["spread_over_40pp"] is False


def test_high_floor_count_separates_inapplicable_from_unanswerable():
    """Two dimensions with the SAME spread are not the same finding."""
    by_sector = {
        # null nearly everywhere: a big spread, but unanswerable, not inapplicable
        "A": _sector(40, {"network_effects": 40}), "B": _sector(40, {"network_effects": 38}),
        "C": _sector(40, {"network_effects": 32}), "D": _sector(40, {"network_effects": 16}),
        # null in one sector only: the H1 signature E12 is looking for
        "E": _sector(40, {"manufacturing_complexity": 4}),
    }
    for sec, s in by_sector.items():
        other = ("manufacturing_complexity" if "network_effects" in s["nulls"]
                 else "network_effects")
        s["nulls"][other] = {"A": 38, "B": 6, "C": 4, "D": 4, "E": 40}[sec]
        s["seen"][other] = s["n"]
    p = bq._p2(by_sector)
    assert p["network_effects"]["spread_pp"] == 60.0
    assert p["network_effects"]["sectors_at_or_above_75pct"] == 4
    assert p["manufacturing_complexity"]["spread_pp"] == 85.0
    assert p["manufacturing_complexity"]["sectors_at_or_above_75pct"] == 1


def test_null_rate_divides_by_the_dimension_seen_count():
    """A payload missing a dimension key must not deflate that dimension's null rate."""
    by_sector = {"Energy": _sector(50, {"data_advantages": 30},
                                   seen={"data_advantages": 40})}
    assert bq._matrix(by_sector)["Energy"]["data_advantages"] == 75.0
