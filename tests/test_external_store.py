"""The catalog's contract.

The store is the first database this repo has ever had, so the properties it must
guarantee are pinned here rather than assumed: keying that never overwrites a
comparison arm, JSON round-tripping that does not produce `str(list)`, and a failure
path that cannot leak a source URL into the catalog.
"""
from __future__ import annotations

import datetime
import json

import pytest

from clab.external.schema import Claim
from clab.external.store import ExternalStore

pytest.importorskip("duckdb")


@pytest.fixture()
def store(tmp_path):
    return ExternalStore(tmp_path / "t.duckdb")


def _request(request_id="req1", n=2):
    return {
        "request_id": request_id,
        "generated_at": datetime.datetime.now(datetime.timezone.utc),
        "roster_sha1": "deadbeef", "spec_fingerprint": "ffff", "depth": 3,
        "roster": [{"ticker": f"T{i}"} for i in range(n)],
    }


# ------------------------------------------------------------------ lifecycle
def test_begin_complete_roundtrip(store):
    store.begin(_request(), base_book="v2_lfm25_20260901")
    assert store.manifest("req1")["status"] == "pending"
    assert store.manifest("req1")["n_requested"] == 2
    store.complete("req1", n_returned=2, n_rejected=0, cost_tokens=99, cost_searches=3)
    m = store.manifest("req1")
    assert m["status"] == "complete"
    assert m["cost_tokens"] == 99
    assert m["completed_at"] is not None


def test_begin_is_idempotent_on_request_id(store):
    store.begin(_request(n=2))
    store.begin(_request(n=5))
    assert store.manifest("req1")["n_requested"] == 5


def test_missing_manifest_is_none_not_an_exception(store):
    assert store.manifest("nope") is None


def test_fail_records_the_exception_TYPE_and_never_its_message(store):
    """An exception message can carry a source URL, an API key or a chunk of someone
    else's filing. A catalog is not where that should surface."""
    store.begin(_request())
    try:
        raise ValueError("https://internal.example/doc?token=SECRET123")
    except ValueError as exc:
        store.fail("req1", exc)
    m = store.manifest("req1")
    assert m["error_type"] == "ValueError"
    assert "SECRET123" not in json.dumps(m, default=str)
    assert "internal.example" not in json.dumps(m, default=str)
    assert m["status"] == "failed"


# ------------------------------------------------------------------ companies
def _company(ticker="FICO", version="2026-09-01", **kw):
    row = {"ticker": ticker, "research_version": version, "external_score": 70.0,
           "moat_trajectory": "WEAKENING", "research_depth": 3,
           "flags": ["MOAT_CONTRADICTION"],
           "key_monitoring_variables": ["FHFA policy", "lender adoption"]}
    row.update(kw)
    return row


def test_a_new_research_version_never_overwrites_the_old_one(store):
    """The comparison arm must survive the run it is being compared against."""
    store.upsert_company(_company(version="2026-09-01", external_score=70.0))
    store.upsert_company(_company(version="2026-12-01", external_score=55.0))
    assert store.company("FICO", "2026-09-01")["external_score"] == 70.0
    assert store.company("FICO", "2026-12-01")["external_score"] == 55.0


def test_same_version_upserts_in_place(store):
    store.upsert_company(_company(external_score=70.0))
    store.upsert_company(_company(external_score=71.5))
    assert store.company("FICO", "2026-09-01")["external_score"] == 71.5
    assert len(store.companies("2026-09-01")) == 1


def test_list_columns_round_trip_as_json_not_as_str_of_a_list(store):
    """`str(["a"])` -> "['a']", which no reader can parse back and which becomes a
    one-element list of garbage in the workbook."""
    store.upsert_company(_company())
    row = store.company("FICO", "2026-09-01")
    assert json.loads(row["flags"]) == ["MOAT_CONTRADICTION"]
    assert json.loads(row["key_monitoring_variables"]) == ["FHFA policy",
                                                          "lender adoption"]


def test_companies_are_scoped_to_their_research_version(store):
    store.upsert_company(_company("FICO", "v1"))
    store.upsert_company(_company("VRT", "v1"))
    store.upsert_company(_company("NVDA", "v2"))
    assert store.known_tickers("v1") == {"FICO", "VRT"}
    assert store.known_tickers("v2") == {"NVDA"}


def test_company_lifecycle_retires_operationally_and_retains_evidence(store):
    store.upsert_company(_company("FICO", "v1", external_score=70.0))
    store.upsert_company(_company("FICO", "v2", external_score=20.0))
    store.insert_claims([_claim("c_burned")], request_id="burned")

    n = store.supersede_company_version(
        "v2", superseded_by="v3",
        reason="peer evidence was assigned to the wrong company")

    assert n == 1
    retired = store.company("FICO", "v2")
    assert retired["status"] == "SUPERSEDED"
    assert retired["superseded_by"] == "v3"
    assert retired["superseded_reason"] == (
        "peer evidence was assigned to the wrong company")
    assert retired["superseded_at"] is not None
    assert store.companies("v2")[0]["external_score"] == 20.0
    assert store.claims_for("FICO")[0]["claim_id"] == "c_burned"

    # NO FALLBACK, changed 2026-09-09 on the user's decision. A retired newest arm means
    # the company has no current research and is omitted; it does NOT drop back to v1.
    # The fallback this replaced served all 59 utilities their pre-fix E47 arm after E53
    # was retired - 20 of 236 answered on the four rank-order fields against E53's 155 of
    # 236 - so the corpus silently regressed to the abstention collapse E51 and E53
    # existed to repair. Note this holds even though a replacement IS named here
    # (superseded_by="v3"): the replacement is v3, and v3 is not v1.
    assert store.latest_companies() == []
    assert store.latest_companies(
        include_superseded=True)[0]["research_version"] == "v2"
    first_at = retired["superseded_at"]
    assert store.supersede_company_version(
        "v2", superseded_by="v3",
        reason="peer evidence was assigned to the wrong company") == 0
    assert store.company("FICO", "v2")["superseded_at"] == first_at


def test_reingest_does_not_resurrect_a_superseded_company_arm(store):
    store.upsert_company(_company("FICO", "v1", external_score=20.0))
    store.supersede_company_version("v1", reason="rejected research arm")
    store.upsert_company(_company("FICO", "v1", external_score=21.0))
    row = store.company("FICO", "v1")
    assert row["external_score"] == 21.0
    assert row["status"] == "SUPERSEDED"
    assert row["superseded_reason"] == "rejected research arm"


def test_company_lifecycle_requires_a_reason_and_cannot_point_to_itself(store):
    store.upsert_company(_company("FICO", "v1"))
    with pytest.raises(ValueError, match="reason"):
        store.supersede_company_version("v1", reason="")
    with pytest.raises(ValueError, match="cannot supersede itself"):
        store.supersede_company_version("v1", reason="bad arm", superseded_by="v1")


def test_latest_company_baseline_is_strictly_before_the_named_version(store):
    store.upsert_company(_company("FICO", "v1", external_score=10.0))
    store.upsert_company(_company("FICO", "v2", external_score=20.0))
    store.upsert_company(_company("VRT", "v2", external_score=30.0))
    rows = store.latest_companies(before_version="v2")
    assert [(r["ticker"], r["research_version"]) for r in rows] == [("FICO", "v1")]


# --------------------------------------------------------------------- claims
def _claim(cid="c_1", status="VERIFIED_LOCAL", domain="REGULATOR", ticker="FICO"):
    return Claim(claim_id=cid, field="moat_trajectory", text="t",
                 source_url="https://x/y", source_type="REGULATOR",
                 independence_domain=domain, quote="q", verify_status=status,
                 overlap=0.9, ticker=ticker)


def test_claims_insert_and_report_their_verify_rates(store):
    store.insert_claims([_claim("c_1", "VERIFIED_LOCAL"),
                         _claim("c_2", "SELF_ATTESTED"),
                         _claim("c_3", "UNVERIFIABLE")], request_id="req1")
    assert store.verify_rates("req1") == {
        "VERIFIED_LOCAL": 1, "SELF_ATTESTED": 1, "UNVERIFIABLE": 1}


def test_the_excerpt_itself_is_not_stored_only_its_hash(store):
    """The excerpt exists to check the quote against. Keeping megabytes of scraped
    page text would make the catalog a content store, which it is not."""
    store.insert_claims([_claim()], request_id="req1",
                        excerpt_sha1={"c_1": "abc123"})
    row = store.claims_for("FICO")[0]
    assert row["excerpt_sha1"] == "abc123"
    assert "excerpt" not in row


def test_reinserting_a_claim_id_refreshes_the_row_but_never_the_verdict(store):
    """One row, research fields updated, verdict untouched.

    insert_claims is the INGEST path. verify.py reaches verdicts through its own
    UPDATE. Letting an ingest carry a verify_status would mean re-running
    research_ingest --apply reset every verification the fetcher had earned.
    """
    store.insert_claims([_claim("c_1", "VERIFIED_LOCAL")], request_id="req1")
    store.insert_claims([_claim("c_1", "SELF_ATTESTED")], request_id="req2")
    rows = store.claims_for("FICO")
    assert len(rows) == 1
    assert rows[0]["verify_status"] == "VERIFIED_LOCAL"   # sticky
    assert rows[0]["request_id"] == "req2"                # but the row did refresh


def test_inserting_no_claims_is_a_no_op(store):
    assert store.insert_claims([], request_id="req1") == 0


# -------------------------------------------------------------------- ledgers
def test_reconciliation_ledger_records_before_after_and_the_rule(store):
    store.log_reconciliation([{
        "ticker": "FICO", "component": "BQ", "before_points": 13,
        "after_points": 11, "delta": -2, "rule_id": "R3_MOAT_TRAJECTORY_WEAKENING",
        "claim_ids": ["c_1", "c_2"], "request_id": "req1"}])
    row = store.reconciliations_for("FICO")[0]
    assert (row["before_points"], row["after_points"], row["delta"]) == (13, 11, -2)
    assert row["rule_id"] == "R3_MOAT_TRAJECTORY_WEAKENING"
    assert json.loads(row["claim_ids"]) == ["c_1", "c_2"]
    assert row["applied_at"] is not None


def test_the_pre_reconciliation_score_is_always_recoverable(store):
    """Reversibility is the whole licence for letting external evidence move points."""
    store.log_reconciliation([
        {"ticker": "FICO", "component": "SG", "before_points": 18,
         "after_points": 16, "delta": -2, "rule_id": "R1", "request_id": "r"},
        {"ticker": "FICO", "component": "BQ", "before_points": 13,
         "after_points": 12, "delta": -1, "rule_id": "R3", "request_id": "r"},
    ])
    rows = store.reconciliations_for("FICO")
    final = {"SG": 16, "BQ": 12}
    restored = {r["component"]: final[r["component"]] - r["delta"] for r in rows}
    assert restored == {"SG": 18, "BQ": 13}


def test_priority_ledger_separates_the_arms(store):
    today = datetime.date.today()
    store.log_priority([
        {"ticker": "A", "arm": "priority", "priority_score": 0.9, "selected": True},
        {"ticker": "B", "arm": "priority", "priority_score": 0.8, "selected": True},
        {"ticker": "C", "arm": "control", "priority_score": 0.1, "selected": True},
        {"ticker": "D", "arm": "priority", "priority_score": 0.2, "selected": False},
    ], run_date=today, seed=42)
    assert store.priority_arms(today) == {"priority": 2, "control": 1}


# ------------------------------------------------------- sectors / industries
def test_industry_returns_the_latest_version_when_none_is_named(store):
    store.upsert_industry({"industry_id": "us_credit_scoring", "version": "2026-06-01",
                           "structural_growth": "HIGH", "key_metrics": ["a"]})
    store.upsert_industry({"industry_id": "us_credit_scoring", "version": "2026-09-01",
                           "structural_growth": "MODERATE", "key_metrics": ["a", "b"]})
    assert store.industry("us_credit_scoring")["version"] == "2026-09-01"
    assert store.industry("us_credit_scoring")["structural_growth"] == "MODERATE"
    assert store.industry("us_credit_scoring", "2026-06-01")["structural_growth"] == "HIGH"
    assert json.loads(store.industry("us_credit_scoring")["key_metrics"]) == ["a", "b"]


def test_industry_does_not_resurrect_an_older_version_when_latest_is_retired(store):
    store.upsert_industry({"industry_id": "retired_bucket", "version": "2026-09-01",
                           "structural_growth": "MODERATE"})
    store.upsert_industry({"industry_id": "retired_bucket", "version": "2026-09-02",
                           "structural_growth": "UNKNOWN"})
    with store.connect() as con:
        con.execute(
            "UPDATE industry_intelligence SET status = 'SUPERSEDED' "
            "WHERE industry_id = 'retired_bucket' AND version = '2026-09-02'"
        )

    assert store.industry("retired_bucket") is None
    assert store.industry("retired_bucket", "2026-09-01")["structural_growth"] == "MODERATE"
    audit_row = store.industry("retired_bucket", include_superseded=True)
    assert audit_row["version"] == "2026-09-02"
    assert audit_row["status"] == "SUPERSEDED"


def test_industry_lifecycle_retires_exact_rows_atomically(store):
    for iid in ("alpha", "beta"):
        store.upsert_industry({"industry_id": iid, "version": "v1",
                               "structural_growth": "MODERATE"})
    changed = store.supersede_industry_versions(
        ["beta", "alpha"], version="v1", reason="semantic evidence failed")
    assert changed == 2
    for iid in ("alpha", "beta"):
        assert store.industry(iid) is None
        row = store.industry(iid, version="v1")
        assert row["status"] == "SUPERSEDED"
        assert row["superseded_reason"] == "semantic evidence failed"
        assert row["superseded_at"] is not None
    store.upsert_industry({"industry_id": "alpha", "version": "v1",
                           "structural_growth": "HIGH"})
    assert store.industry("alpha", version="v1")["status"] == "SUPERSEDED"
    assert store.industry("alpha", version="v1")["structural_growth"] == "HIGH"
    assert store.supersede_industry_versions(
        ["alpha", "beta"], version="v1", reason="semantic evidence failed") == 0


def test_sector_brief_versions_the_same_way(store):
    store.upsert_sector({"sector_id": "financials", "version": "2026-09-01",
                         "what_changed": "FIRST_BUILD", "winners": ["X"]})
    row = store.sector("financials")
    assert row["what_changed"] == "FIRST_BUILD"
    assert json.loads(row["winners"]) == ["X"]
    assert store.sector("energy") is None


def test_opening_the_same_db_twice_is_fine(tmp_path):
    """A connection per call, not a long-lived one: on Windows a held DuckDB handle
    turns "the UI is open" into "the ingest cannot write"."""
    path = tmp_path / "t.duckdb"
    a = ExternalStore(path)
    a.upsert_company(_company())
    b = ExternalStore(path)
    assert b.company("FICO", "2026-09-01") is not None


def test_latest_companies_does_not_fall_back_to_an_older_arm(store):
    """A retired NEWEST arm means the company has no current research.

    This used to fall back and the fallback did real damage. E53 re-ran Utilities on the
    symmetric prompt, was later retired for a B3 evidence defect with no replacement, and
    selection then served all 59 utilities their pre-fix E47 arm - 20 of 236 answered on
    the four rank-order fields against E53's 155 of 236. The corpus silently regressed to
    the abstention collapse E51 and E53 existed to repair.

    A company that drops out is visible. A company quietly served worse research is not.
    """
    import datetime as dt

    def _co(ticker, version, day, moat="STRONG"):
        return {"ticker": ticker, "research_version": version,
                "industry_id": "electric_utilities", "sector_id": "utilities",
                "current_moat_strength": moat,
                "last_research_date": dt.date(2026, 9, day)}

    store.upsert_company(_co("AEP", "2026-09-05+E47", 5, "WEAK"))
    store.upsert_company(_co("AEP", "2026-09-07+E53", 7, "STRONG"))

    # both arms live: the newest wins
    assert [r["research_version"] for r in store.latest_companies()] == ["2026-09-07+E53"]

    store.supersede_company_version("2026-09-07+E53", reason="B3 evidence defect")

    # newest arm retired -> the company is OMITTED, not served the older arm
    assert store.latest_companies() == []

    # ...and it is still reachable for audit
    audit = store.latest_companies(include_superseded=True)
    assert [r["research_version"] for r in audit] == ["2026-09-07+E53"]


def test_a_company_whose_only_arm_is_retired_is_omitted(store):
    """No arm at all is the same answer as a retired newest arm."""
    import datetime as dt
    store.upsert_company({"ticker": "ZZZ", "research_version": "v1",
                          "industry_id": "electric_utilities",
                          "last_research_date": dt.date(2026, 9, 1)})
    assert len(store.latest_companies()) == 1
    store.supersede_company_version("v1", reason="burned")
    assert store.latest_companies() == []
