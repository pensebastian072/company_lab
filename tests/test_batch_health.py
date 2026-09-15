"""The gauge that was missing for eight batches.

Every metric reported per batch was a QUALITY metric - rejections, demotions, UNKNOWN
gaps, unverifiable rate - and all of them stayed perfect while the four rank-order fields
fell from 92% filled to 0%. A batch that answered nothing, perfectly, scored perfectly.
These tests pin the coverage side, and especially the confound that makes a naive fill
rate useless.
"""
from __future__ import annotations

from clab.external import batch_health as BH
from clab.external.schema import UNKNOWN


class _FakeStore:
    def __init__(self, rows):
        self._rows = rows

    def company_records(self, *, include_superseded=False):
        if include_superseded:
            return list(self._rows)
        return [r for r in self._rows
                if str(r.get("status") or "").upper() != "SUPERSEDED"]

    def companies(self, research_version):
        return [r for r in self._rows
                if r.get("research_version") == research_version]

    def latest_companies(self, *, before_version=None, include_superseded=False):
        rows = self.company_records(include_superseded=include_superseded)
        if before_version is not None:
            rows = [r for r in rows if r["research_version"] < before_version]
        latest = {}
        for r in rows:
            key = (str(r.get("last_research_date") or ""), r["research_version"])
            cur = latest.get(r["ticker"])
            if cur is None or key > cur[0]:
                latest[r["ticker"]] = (key, r)
        return [r for _key, r in latest.values()]

    def connect(self):
        rows = self._rows

        class _Con:
            def __enter__(self_):
                return self_

            def __exit__(self_, *a):
                return False

            def execute(self_, sql, params=None):
                cols = sql.split("SELECT ")[1].split(" FROM ")[0].split(", ")
                self_._out = [tuple(r.get(c) for c in cols) for r in rows]
                return self_

            def fetchall(self_):
                return self_._out
        return _Con()


def _co(ticker, version, industry, **fields):
    row = {"ticker": ticker, "research_version": version, "industry_id": industry}
    for f in ("moat_trajectory", "competitive_position", "competitive_position_trend",
              "company_specific_capture", "current_moat_strength",
              "industry_structural_growth", "demand_visibility",
              "market_share_direction", "pricing_power", "technology_risk",
              "disruption_risk", "regulatory_risk"):
        row[f] = UNKNOWN
    row.update(fields)
    return row


def _batch(version, industry, n, answered):
    """n companies, the first `answered` of which fill all four rank-order fields."""
    out = []
    for i in range(n):
        filled = {f: "STABLE" for f in BH.RANK_ORDER_FIELDS} if i < answered else {}
        out.append(_co(f"{industry}-{version}{i}", version, industry, **filled))
    return out


# ------------------------------------------------------- it catches the real decay
def test_a_batch_that_answers_less_than_its_baseline_is_a_REGRESSION():
    rows = _batch("v1", "upstream_oil_gas", 10, 7) + _batch("v2", "upstream_oil_gas", 10, 1)
    res = BH.compare("v2", store=_FakeStore(rows))
    assert res["verdict"] == "REGRESSION"
    assert res["within_industry_delta"] <= -BH.REGRESSION_DROP


def test_a_batch_that_holds_its_baseline_is_OK():
    rows = _batch("v1", "upstream_oil_gas", 10, 7) + _batch("v2", "upstream_oil_gas", 10, 7)
    res = BH.compare("v2", store=_FakeStore(rows))
    assert res["verdict"] == "OK"


def test_the_first_batch_has_no_baseline_and_is_not_accused():
    res = BH.compare("v1", store=_FakeStore(_batch("v1", "x", 10, 0)))
    assert res["verdict"] == "NO_BASELINE"


def test_a_superseded_arm_is_not_a_baseline_by_default():
    accepted = _batch("v0", "x", 10, 10)
    burned = _batch("v1", "x", 10, 0)
    for row in burned:
        row["status"] = "SUPERSEDED"
    target = _batch("v2", "x", 10, 5)
    store = _FakeStore(accepted + burned + target)

    clean = BH.compare("v2", store=store)
    contaminated = BH.compare(
        "v2", store=store, include_superseded_baseline=True)
    assert clean["baseline_fill"] == 1.0
    assert clean["verdict"] == "REGRESSION"
    assert contaminated["baseline_fill"] == 0.5
    assert contaminated["verdict"] == "OK"


def test_an_explicit_superseded_version_remains_auditable():
    accepted = _batch("v0", "x", 10, 10)
    burned = _batch("v1", "x", 10, 0)
    for row in burned:
        row["status"] = "SUPERSEDED"
    res = BH.compare("v1", store=_FakeStore(accepted + burned))
    assert res["n_companies"] == 10
    assert res["batch_fill"] == 0.0
    assert res["verdict"] == "REGRESSION"


def test_history_hides_retired_arms_unless_audit_is_explicit():
    active = _batch("v0", "x", 3, 3)
    burned = _batch("v1", "x", 3, 0)
    for row in burned:
        row["status"] = "SUPERSEDED"
    store = _FakeStore(active + burned)
    assert [r["research_version"] for r in BH.history(store=store)] == ["v0"]
    assert [r["research_version"] for r in BH.history(
        store=store, include_superseded=True)] == ["v0", "v1"]


# --------------------------------------------- the confound that makes it non-trivial
def test_a_NOT_APPLICABLE_field_is_excluded_from_the_DENOMINATOR():
    """market_share_direction SHOULD be 0% in a batch of regulated utilities -
    applicability.py says the question is meaningless there. Counting it as an unanswered
    field would fire this alarm on correct behaviour, which is how a monitor gets
    switched off."""
    fields = ("market_share_direction",)
    util = [_co("A", "v1", "water_utilities")]
    engy = [_co("B", "v1", "upstream_oil_gas")]
    assert BH._fill(util, fields) == (0, 0)      # nominated: not applicable, not counted
    assert BH._fill(engy, fields) == (0, 1)      # merely unmeasured: still costs


def test_the_headline_is_WITHIN_industry_not_pooled():
    """Pooled fill rate moves when the sector mix moves, with nothing changing about the
    research. The within-industry number holds the peer set and the industry object
    fixed - it is what showed upstream_oil_gas at 92%, 38% then 5%."""
    rows = (_batch("v1", "easy_industry", 10, 10)
            + _batch("v2", "easy_industry", 10, 10)
            + _batch("v2", "hard_industry", 30, 0))
    res = BH.compare("v2", store=_FakeStore(rows))
    assert res["pooled_delta"] < -0.5, "pooled reads as collapse"
    assert res["within_industry_delta"] == 0.0, "within-industry sees no change"
    assert res["verdict"] == "OK"


def test_a_thin_industry_is_not_compared():
    """Two companies cannot establish that an industry's fill rate moved."""
    rows = _batch("v1", "tiny", 2, 2) + _batch("v2", "tiny", 2, 0)
    res = BH.compare("v2", store=_FakeStore(rows))
    assert res["shared_industries"] == []


def test_it_reports_which_industries_regressed_by_name():
    rows = (_batch("v1", "held", 5, 5) + _batch("v2", "held", 5, 5)
            + _batch("v1", "dropped", 5, 5) + _batch("v2", "dropped", 5, 0))
    res = BH.compare("v2", store=_FakeStore(rows))
    assert [r["industry_id"] for r in res["regressions"]] == ["dropped"]


def test_the_watched_fields_are_the_ones_worth_45_points():
    from clab.external import score as SC
    pts = {f: p for dim in SC.DIMENSIONS.values() for f, p in dim.items()}
    assert sum(pts[f] for f in BH.RANK_ORDER_FIELDS) == 45


# ------------------------------------------------- the constant-field check (E30 shape)
def _const_batch(version, n, **fields):
    """n rows in one version, every row carrying the same given field values."""
    base = {"moat_trajectory": "STRENGTHENING", "competitive_position": "LEADER",
            "competitive_position_trend": "STABLE", "company_specific_capture": "HIGH",
            "current_moat_strength": "STRONG", "pricing_power": "STRONG",
            "demand_visibility": "HIGH", "market_share_direction": "GAINING",
            "technology_risk": "LOW", "disruption_risk": "LOW",
            "regulatory_risk": "LOW", "industry_structural_growth": "HIGH"}
    rows = []
    for i in range(n):
        r = {"ticker": f"T{i}", "research_version": version, "industry_id": "widgets",
             **base, **fields}
        # vary one field so the batch is not constant EVERYWHERE by construction
        r["demand_visibility"] = "HIGH" if i % 2 else "MODERATE"
        rows.append(r)
    return rows


def test_a_field_unknown_across_the_whole_batch_is_reported():
    """market_share_direction came back UNKNOWN for 85 of 85 Financials companies while a
    module built to compute it had no production caller, and both batches reported OK -
    compare() watches four rank-order fields and this is not one of them."""
    rows = _const_batch("v1", 40, market_share_direction=UNKNOWN)
    res = BH.constant_fields("v1", store=_FakeStore(rows))
    assert [r["field"] for r in res["all_unknown"]] == ["market_share_direction"]
    assert res["all_unknown"][0]["n"] == 40


def test_a_field_answered_identically_every_time_is_reported_separately():
    """All-UNKNOWN and always-the-same-answer ask a reviewer different questions, so they
    are not pooled: the first is 'was this answerable', the second is 'finding or stuck
    derivation'."""
    rows = _const_batch("v1", 40, pricing_power="MODERATE")
    res = BH.constant_fields("v1", store=_FakeStore(rows))
    single = {r["field"]: r["value"] for r in res["single_value"]}
    assert single["pricing_power"] == "MODERATE"
    assert res["all_unknown"] == []


def test_one_dissenting_row_is_enough_to_clear_the_check():
    """Deliberately strict. E43 answered market_share_direction 1 of 40 and does NOT trip
    this - constancy is the signal, and a near-constant field needs a rate, which is what
    compare() is for. Stated so nobody reads a clean result as 'well distributed'."""
    rows = _const_batch("v1", 40, market_share_direction=UNKNOWN)
    rows[7]["market_share_direction"] = "GAINING"
    res = BH.constant_fields("v1", store=_FakeStore(rows))
    flagged = {r["field"] for r in res["all_unknown"]} | {r["field"] for r in res["single_value"]}
    assert "market_share_direction" not in flagged


def test_a_small_batch_is_skipped_rather_than_flagged():
    res = BH.constant_fields("v1", store=_FakeStore(_const_batch("v1", 3)))
    assert "skipped" in res and res["all_unknown"] == [] and res["checked"] == 0
