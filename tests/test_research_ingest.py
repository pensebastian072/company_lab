"""Validating research we did not produce.

The first Codex delivery reported its own validation as passing. It largely was - but
the report could not have caught the two things that mattered: that this schema was
missing the vocabularies the prompt said it enforced, and that the independence-domain
labels can be moved without anything looking wrong.
"""
from __future__ import annotations

import json

import pytest

from clab.external import research_ingest as RI
from clab.external import schema as S
from conftest import skip_if_locked


def _claim(cid="c_0123456789ab", **over):
    c = {"claim_id": cid, "field": "structural_growth", "text": "a finding",
         "source_url": "https://example.gov/doc", "source_date": "2026-01-01",
         "source_type": "REGULATOR", "independence_domain": "REGULATOR",
         "quote": "the quoted words", "excerpt": "before the quoted words after",
         "stance": "SUPPORTS", "fact_or_inference": "FACT"}
    c.update(over)
    return c


def _industry(**over):
    obj = {"industry_id": "us_credit_scoring", "sector_id": "financials",
           "version": "2026-09-01", "status": "SHADOW",
           "structural_growth": "UNKNOWN", "replication_difficulty": "HIGH",
           "substitution_risk": "ELEVATED", "refresh_class": "EVENT_DRIVEN",
           "claims": [_claim()]}
    obj.update(over)
    return obj


# ------------------------------------------------- the vocabularies that were missing
@pytest.mark.parametrize("field,value", [
    ("structural_growth", "HIGH"),
    ("replication_difficulty", "EXTREME"),
    ("substitution_risk", "ELEVATED"),
])
def test_the_industry_object_fields_are_actually_in_the_schema(field, value):
    """The Phase 0 prompt told the researcher these were "CLOSED and enforced
    mechanically by clab/external/schema.py". They were not in that file at all, so
    every delivered object validated as `unknown field`. The research was fine; the
    promise was false."""
    assert field in S.VOCABULARIES
    assert S.is_valid(field, value)
    assert S.validate_categoricals({field: value}) == []


def test_structural_growth_is_the_same_scale_under_both_names():
    """The industry object says structural_growth, the company record says
    industry_structural_growth. One scale, or MODERATE means two things."""
    a = [v for v in S.VOCABULARIES["structural_growth"] if v != S.UNKNOWN]
    b = [v for v in S.VOCABULARIES["industry_structural_growth"] if v != S.UNKNOWN]
    assert a == b
    assert S.normalized("structural_growth", "HIGH") == \
        S.normalized("industry_structural_growth", "HIGH")


def test_harder_to_replicate_normalises_as_better_and_higher_risk_as_worse():
    assert S.normalized("replication_difficulty", "EXTREME") == 1.0
    assert S.normalized("replication_difficulty", "LOW") == 0.0
    assert S.normalized("substitution_risk", "LOW") == 1.0
    assert S.normalized("substitution_risk", "SEVERE") == 0.0
    for f in ("structural_growth", "replication_difficulty", "substitution_risk"):
        assert S.normalized(f, "UNKNOWN") is None


# ------------------------------------------------------------------ claim checks
def test_a_quote_absent_from_its_own_excerpt_is_rejected():
    r = RI.validate_claim(_claim(quote="words that are not there"))
    assert any("NOT present in its own excerpt" in x for x in r)


def test_a_bad_claim_id_shape_is_rejected():
    assert any("c_<12 hex>" in x for x in RI.validate_claim(_claim(cid="claim-1")))
    assert any("c_<12 hex>" in x for x in RI.validate_claim(_claim(cid="c_XYZ")))


def test_an_out_of_vocabulary_domain_is_rejected():
    r = RI.validate_claim(_claim(independence_domain="THE_INTERNET"))
    assert any("independence_domain" in x for x in r)


def test_an_overlong_quote_is_rejected():
    long = "x" * 301
    r = RI.validate_claim(_claim(quote=long, excerpt=long))
    assert any("cap is 300" in x for x in r)


def test_a_clean_claim_has_no_reasons():
    assert RI.validate_claim(_claim()) == []


# ------------------------------------------------- verify_status is assigned HERE
def test_verify_status_from_the_payload_is_overwritten():
    """A researcher marking its own work verified is not verification. Codex re-fetching
    Codex's own URLs is the same thing one level up."""
    c = RI.to_claim(_claim(verify_status="VERIFIED_LOCAL"))
    assert c.verify_status == "SELF_ATTESTED"


def test_a_quote_inside_its_excerpt_is_only_self_attested():
    """The cheap check catches quote fabrication. It cannot catch EXCERPT fabrication,
    so it may never produce VERIFIED_LOCAL."""
    assert RI.to_claim(_claim()).verify_status == "SELF_ATTESTED"


def test_a_missing_url_or_a_broken_quote_is_unverifiable():
    assert RI.to_claim(_claim(source_url=None)).verify_status == "UNVERIFIABLE"
    assert RI.to_claim(_claim(quote="absent")).verify_status == "UNVERIFIABLE"


# --------------------------------------------------------- the independence lever
def test_one_host_filed_under_two_domains_is_flagged():
    """Found on the first delivery: www.se.com (Schneider Electric) entered as both
    COMPETITOR_FILING and SUPPLIER inside datacenter_power_cooling, manufacturing an
    extra domain out of one organisation."""
    e = RI.evidence_profile([
        _claim("c_00000000000a", source_url="https://www.se.com/a",
               independence_domain="COMPETITOR_FILING"),
        _claim("c_00000000000b", source_url="https://www.se.com/b",
               independence_domain="SUPPLIER"),
    ])
    assert e["host_domain_conflicts"] == {
        "www.se.com": ["COMPETITOR_FILING", "SUPPLIER"]}
    assert e["distinct_domains"] == 2
    assert e["distinct_hosts"] == 1


def test_domains_resting_on_a_single_claim_are_reported():
    """Five domains where four rest on one claim each is one source per domain, not
    five independent lines of evidence."""
    e = RI.evidence_profile([
        _claim("c_00000000000a", independence_domain="REGULATOR"),
        _claim("c_00000000000b", independence_domain="REGULATOR"),
        _claim("c_00000000000c", independence_domain="ACADEMIC"),
        _claim("c_00000000000d", independence_domain="SUPPLIER"),
    ])
    assert e["domains_on_one_claim"] == ["ACADEMIC", "SUPPLIER"]


def test_claims_per_url_exposes_reuse_of_one_source():
    """Six claims over four URLs is not six sources."""
    e = RI.evidence_profile([
        _claim("c_00000000000a", source_url="https://x/1"),
        _claim("c_00000000000b", source_url="https://x/1"),
        _claim("c_00000000000c", source_url="https://x/2"),
    ])
    assert e["distinct_urls"] == 2
    assert e["claims_per_url"] == 1.5


def test_an_empty_evidence_profile_does_not_divide_by_zero():
    e = RI.evidence_profile([])
    assert e["claims"] == 0 and e["claims_per_url"] == 0.0


# ------------------------------------------------------------- object validation
def test_a_clean_industry_object_validates():
    assert validate_ok(_industry())


def validate_ok(obj):
    res = RI.validate_industry(obj)
    return res["ok"], res["reasons"], res["claim_reasons"]


def test_status_must_be_shadow():
    res = RI.validate_industry(_industry(status="LIVE"))
    assert not res["ok"] and any("must be SHADOW" in r for r in res["reasons"])


def test_an_unknown_sector_id_is_rejected():
    res = RI.validate_industry(_industry(sector_id="tech"))
    assert not res["ok"]


def test_duplicate_claim_ids_are_rejected():
    res = RI.validate_industry(_industry(claims=[_claim(), _claim()]))
    assert not res["ok"] and any("duplicate claim_ids" in r for r in res["reasons"])


def test_an_industry_id_that_disagrees_with_its_directory_is_rejected(tmp_path):
    """Company records join on the directory id, so a mismatch orphans the object."""
    d = tmp_path / "us_credit_scoring"
    d.mkdir()
    (d / "industry_state.json").write_text(
        json.dumps(_industry(industry_id="credit_scoring")), encoding="utf-8")
    res = RI.load_and_validate(tmp_path)[0]
    assert not res["ok"]
    assert any("does not match its directory" in r for r in res["reasons"])


def test_unparseable_json_is_a_failure_not_a_crash(tmp_path):
    d = tmp_path / "broken"
    d.mkdir()
    (d / "industry_state.json").write_text("{not json", encoding="utf-8")
    res = RI.load_and_validate(tmp_path)[0]
    assert not res["ok"] and "unparseable" in res["reasons"][0]


def test_a_missing_state_file_is_reported(tmp_path):
    (tmp_path / "empty_unit").mkdir()
    res = RI.load_and_validate(tmp_path)[0]
    assert not res["ok"] and "no industry_state.json" in res["reasons"]


def test_ingest_skips_objects_that_failed_validation(tmp_path):
    from clab.external.store import ExternalStore
    store = ExternalStore(tmp_path / "t.duckdb")
    bad = RI.validate_industry(_industry(status="LIVE"))
    bad["_obj"] = _industry(status="LIVE")
    res = RI.ingest([bad], store=store, apply=True)
    assert res["written"] == [] and res["skipped"] == ["us_credit_scoring"]


# -------------------------------------------------- against what is actually on disk
def test_the_delivered_objects_validate_against_this_schema():
    """The end-to-end check the delivery report could not make: OUR validator, OUR
    vocabularies, over the files as they actually sit on disk."""
    results = RI.load_and_validate()
    if not results:
        pytest.skip("no research objects on disk")
    failed = {r["industry_id"]: (r["reasons"], r["claim_reasons"])
              for r in results if not r["ok"]}
    assert failed == {}, f"objects failing validation: {failed}"


def test_re_ingesting_research_never_downgrades_a_verification(tmp_path):
    """The regression this test was rewritten to catch.

    Its original form asserted the catalog held ZERO verified claims, which was true
    until verify.py ran and then correctly failed. Rewriting it exposed a real defect:
    insert_claims used INSERT OR REPLACE, and the ingest path builds every claim as
    SELF_ATTESTED, so re-running `research_ingest --apply` after a verification pass
    would have silently reset all 90 VERIFIED_LOCAL rows - hours of fetching thrown
    away by a command whose output said "written".
    """
    from clab.external.schema import Claim
    from clab.external.store import ExternalStore

    store = ExternalStore(tmp_path / "t.duckdb")
    base = dict(claim_id="c_0123456789ab", field="f", text="t",
                source_url="https://x/1", quote="q", industry_id="payments")

    store.insert_claims([Claim(**base, verify_status="SELF_ATTESTED")],
                        request_id="ingest-1")
    assert store.verify_rates() == {"SELF_ATTESTED": 1}

    # verify.py reaches a verdict
    with store.connect() as con:
        con.execute("UPDATE external_claim SET verify_status = 'VERIFIED_LOCAL', "
                    "overlap = 1.0 WHERE claim_id = ?", [base["claim_id"]])
    assert store.verify_rates() == {"VERIFIED_LOCAL": 1}

    # a later ingest of the same research must NOT undo it
    store.insert_claims([Claim(**base, verify_status="SELF_ATTESTED")],
                        request_id="ingest-2")
    assert store.verify_rates() == {"VERIFIED_LOCAL": 1}
    row = store.claims_for("payments") or []
    with store.connect() as con:
        got = con.execute("SELECT verify_status, overlap, request_id FROM "
                          "external_claim WHERE claim_id = ?",
                          [base["claim_id"]]).fetchone()
    assert got[0] == "VERIFIED_LOCAL" and got[1] == 1.0
    assert got[2] == "ingest-2", "the research fields SHOULD refresh, only the verdict is sticky"


def test_even_an_unverifiable_default_cannot_clobber_a_verdict(tmp_path):
    """Claim's default verify_status is UNVERIFIABLE - guilty until proven. An earlier
    draft of the ON CONFLICT rule keyed on the incoming VALUE and preserved the row
    only when SELF_ATTESTED arrived, so anyone building a Claim without naming a status
    would have wiped a real verdict. The rule keys on WHO WRITES instead: insert_claims
    is the ingest path and never touches a verdict; verify.py has its own UPDATE.
    """
    from clab.external.schema import Claim
    from clab.external.store import ExternalStore

    store = ExternalStore(tmp_path / "t.duckdb")
    base = dict(claim_id="c_0123456789ab", field="f", text="t",
                source_url="https://x/1", quote="q")
    store.insert_claims([Claim(**base, verify_status="VERIFIED_LOCAL", overlap=1.0)],
                        request_id="seed")
    store.insert_claims([Claim(**base)], request_id="careless")   # default UNVERIFIABLE
    assert store.verify_rates() == {"VERIFIED_LOCAL": 1}


@skip_if_locked
def test_the_catalog_never_holds_a_verified_claim_without_an_overlap():
    """VERIFIED_LOCAL is only ever set by verify.py, which always records the overlap
    it measured. A verified row with no overlap means something else set it."""
    from clab.external.store import ExternalStore
    from clab import config
    if not config.EXTERNAL_DB.exists():
        pytest.skip("no catalog on disk")
    with ExternalStore().connect() as con:
        bad = con.execute("SELECT claim_id FROM external_claim WHERE "
                          "verify_status = 'VERIFIED_LOCAL' AND overlap IS NULL"
                          ).fetchall()
    assert bad == [], f"verified with no measured overlap: {bad}"


# ------------------------------------------- the silent default E78 measured the cost of
def test_an_omitted_stance_is_null_and_never_context():
    """`stance` defaulted to CONTEXT and `fact_or_inference` to INFERENCE, so a run that
    never labelled either was indistinguishable in the store from one that had judged
    every claim. E78 measured it: Financials filed 103 CONTEXT to 29 SUPPORTS and
    Industrials 134 to 11, while three sectors filed zero FACT claims - all of it read as
    evidence quality, none of it a judgement. NULL means "not said", which is a different
    fact and the only one that can be counted."""
    raw = _claim()
    raw.pop("stance")
    raw.pop("fact_or_inference")
    c = RI.to_claim(raw)
    assert c.stance is None
    assert c.fact_or_inference is None


def test_the_dataclass_itself_carries_no_stance_default():
    """Belt and braces: the default lived on the dataclass too, so a future caller that
    builds a Claim directly would reintroduce it."""
    c = S.Claim(claim_id="c_0123456789ab", field="structural_growth", text="x")
    assert c.stance is None and c.fact_or_inference is None


def test_industry_claims_must_state_both_labels():
    raw = _claim()
    raw.pop("stance")
    reasons = RI.validate_claim(raw, require_labels=True)
    assert any("no stance" in r for r in reasons)
    res = RI.validate_industry(_industry(claims=[raw]))
    assert res["ok"] is False


def test_the_company_lane_does_not_reject_over_a_missing_label():
    """Cost asymmetry, not a different principle: a Phase A object is cheap to re-emit, a
    42-company batch is hundreds of metered searches. The company lane records NULL and
    counts it; `finalize` reports the count."""
    raw = _claim()
    raw.pop("stance")
    assert RI.validate_claim(raw) == []


def test_evidence_profile_reports_what_was_left_unlabelled():
    raw = _claim("c_00000000000b")
    raw.pop("stance")
    e = RI.evidence_profile([_claim("c_00000000000a"), raw])
    assert e["unlabelled_stance"] == 1
    assert e["stance_counts"] == {"SUPPORTS": 1}
