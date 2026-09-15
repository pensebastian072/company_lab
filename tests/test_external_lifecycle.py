"""Company research is retired operationally and retained evidentially."""
from __future__ import annotations

import pytest

from clab.external.lifecycle import (supersede_company_version,
                                     supersede_industry_versions)
from clab.external.schema import Claim
from clab.external.store import ExternalStore

pytest.importorskip("duckdb")


def _row(ticker, version, request_id):
    return {
        "ticker": ticker,
        "research_version": version,
        "request_id": request_id,
        "external_score": 50.0,
    }


def _store(tmp_path):
    store = ExternalStore(tmp_path / "lifecycle.duckdb")
    store.upsert_company(_row("AAA", "burned", "req-burned"))
    store.upsert_company(_row("AAA", "accepted", "req-good"))
    store.insert_claims([
        Claim(claim_id="c_000000000001", ticker="AAA", field="pricing_power",
              text="retained", source_url="https://example.test/filing",
              quote="retained", verify_status="VERIFIED_LOCAL", overlap=1.0),
    ], request_id="req-burned")
    return store


def test_lifecycle_is_dry_run_by_default_and_carries_corpus_state(tmp_path):
    store = _store(tmp_path)
    result = supersede_company_version(
        "burned", superseded_by="accepted", reason="wrong peer evidence",
        store=store,
    )

    assert result["applied"] is False
    assert result["rows_changed"] == 0
    assert result["store_sha256_before"] == result["store_sha256_after"]
    assert result["target_before"]["company_rows"] == 1
    assert result["target_before"]["claim_counts"] == [{
        "request_id": "req-burned",
        "verify_status": "VERIFIED_LOCAL",
        "claims": 1,
    }]
    assert result["corpus_claims"] == {"VERIFIED_LOCAL": 1}
    assert store.company("AAA", "burned")["status"] is None


def test_apply_marks_rows_but_preserves_explicit_reads_and_claims(tmp_path):
    store = _store(tmp_path)
    result = supersede_company_version(
        "burned", superseded_by="accepted", reason="wrong peer evidence",
        apply=True, store=store,
    )

    assert result["rows_changed"] == 1
    assert result["target_after"]["status_counts"] == {"SUPERSEDED": 1}
    assert store.companies("burned")[0]["status"] == "SUPERSEDED"
    assert store.claims_for("AAA")[0]["text"] == "retained"
    assert store.latest_companies()[0]["research_version"] == "accepted"


def test_lifecycle_refuses_a_missing_target_or_replacement(tmp_path):
    store = _store(tmp_path)
    with pytest.raises(ValueError, match="no company rows"):
        supersede_company_version("missing", reason="bad arm", store=store)
    with pytest.raises(ValueError, match="superseding version"):
        supersede_company_version(
            "burned", superseded_by="missing", reason="bad arm", store=store)


def test_industry_lifecycle_is_atomic_and_keeps_claims(tmp_path):
    store = ExternalStore(tmp_path / "industry-lifecycle.duckdb")
    for iid in ("alpha", "beta"):
        store.upsert_industry({"industry_id": iid, "version": "v1",
                               "structural_growth": "MODERATE"})
    store.insert_claims([
        Claim(claim_id="c_000000000002", industry_id="alpha",
              field="structural_growth", text="retained",
              source_url="https://example.test/industry", quote="retained",
              verify_status="VERIFIED_LOCAL", overlap=1.0),
    ], request_id="phase0:alpha:v1")

    dry = supersede_industry_versions(
        ["alpha", "beta"], version="v1", reason="semantic evidence failed",
        store=store)
    assert dry["rows_changed"] == 0
    assert dry["store_sha256_before"] == dry["store_sha256_after"]
    assert dry["target_before"]["industry_rows"] == 2
    assert dry["target_before"]["claim_counts"][0]["claims"] == 1

    applied = supersede_industry_versions(
        ["alpha", "beta"], version="v1", reason="semantic evidence failed",
        apply=True, store=store)
    assert applied["rows_changed"] == 2
    assert applied["target_after"]["status_counts"] == {"SUPERSEDED": 2}
    assert store.industry("alpha") is None
    assert store.industry("alpha", version="v1")["status"] == "SUPERSEDED"
    assert store.verify_rates("phase0:alpha:v1") == {"VERIFIED_LOCAL": 1}


def test_industry_lifecycle_refuses_a_partial_target_set(tmp_path):
    store = ExternalStore(tmp_path / "industry-missing.duckdb")
    store.upsert_industry({"industry_id": "alpha", "version": "v1"})
    with pytest.raises(ValueError, match="missing industry/version rows"):
        supersede_industry_versions(
            ["alpha", "missing"], version="v1", reason="bad evidence", store=store)
    assert store.industry("alpha")["status"] is None
