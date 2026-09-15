"""The gate, and the request it gates against.

"Codex does not apply the gates - the finalizer does." Every test here is a way a
payload could get something past that line, and the assertion that it does not.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from clab.external import finalize as F
from clab.external import request as R
from clab.external.store import ExternalStore


def _request(request_id="req123", generated_at=None, status="READY", tickers=("FICO",)):
    return {
        "request_id": request_id,
        "spec_fingerprint": "abc123",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "status": status,
        "read_only": True,
        "depth": 3,
        "roster": [{"ticker": t, "cik": "0000814547", "sector_id": "financials",
                    "industry_id": "us_credit_scoring",
                    "subindustry_id": "application_software"} for t in tickers],
    }


def _claim(cid="c_0123456789ab"):
    return {"claim_id": cid, "field": "moat_trajectory", "text": "a finding",
            "source_url": "https://fhfa.gov/x", "source_date": "2026-04-22",
            "source_type": "REGULATOR", "independence_domain": "REGULATOR",
            "quote": "the quoted words", "excerpt": "before the quoted words after",
            "stance": "CONTRADICTS", "fact_or_inference": "FACT"}


def _payload(request_id="req123", ticker="FICO", **over):
    company = {
        "ticker": ticker, "research_depth": 3,
        "pass_a": {"current_moat_strength": "STRONG", "moat_trajectory": "WEAKENING",
                   "competitive_position": "LEADER", "regulatory_risk": "ELEVATED",
                   "why_is_it_cheap": "structural uncertainty",
                   "key_monitoring_variables": ["FHFA policy"]},
        "pass_b": {"reconciliation": []},
        "claims": [_claim()],
        "refresh_class": "EVENT_DRIVEN", "next_suggested_refresh": "2026-12-01",
    }
    company.update(over)
    return {"request_id": request_id, "spec_fingerprint": "abc123",
            "companies": [company], "cost": {"tokens": 100, "searches": 5}}


# ============================================================= the four guards
def test_a_mismatched_request_id_refuses_the_whole_payload():
    with pytest.raises(F.Rejected, match="request_id mismatch"):
        F.finalize(_payload(request_id="tampered"), request=_request())


def test_a_request_from_yesterday_is_refused():
    """An age window is not a session check. On the options desk a 21.6h-old signal
    read as fresh and the desk published a request built on the previous session."""
    old = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    with pytest.raises(F.Rejected, match="not today"):
        F.finalize(_payload(), request=_request(generated_at=old))


def test_a_request_that_is_not_READY_is_refused():
    with pytest.raises(F.Rejected, match="not READY"):
        F.finalize(_payload(), request=_request(status="DRAFT"))


def test_a_missing_request_is_refused_rather_than_defaulted():
    with pytest.raises(F.Rejected, match="no frozen request"):
        F.finalize(_payload(), request={})


def test_a_ticker_outside_the_roster_is_rejected_but_the_rest_survives():
    """One bad row costs one company, not the payload."""
    req = _request(tickers=("FICO", "VRT"))
    pay = _payload()
    pay["companies"].append(_payload(ticker="TSLA")["companies"][0])
    res = F.finalize(pay, request=req)
    assert res["accepted"] == ["FICO"]
    assert res["rejected"][0]["ticker"] == "TSLA"
    assert "not in the frozen roster" in res["rejected"][0]["reasons"][0]
    assert res["unanswered"] == ["VRT"]


def test_a_changed_spec_fingerprint_is_refused():
    pay = _payload()
    pay["spec_fingerprint"] = "different"
    with pytest.raises(F.Rejected, match="spec_fingerprint"):
        F.finalize(pay, request=_request())


# ====================================================== what may not be supplied
@pytest.mark.parametrize("field", ["external_score", "rating", "price_target",
                                   "recommendation", "high_conviction"])
def test_a_payload_may_not_carry_a_number_we_did_not_compute(field):
    """A score we did not compute is a score we cannot audit."""
    res = F.finalize(_payload(**{field: 88}), request=_request())
    assert res["accepted"] == []
    assert any(field in r for r in res["rejected"][0]["reasons"])


def test_a_forbidden_field_hidden_inside_pass_a_is_also_caught():
    pay = _payload()
    pay["companies"][0]["pass_a"]["external_score"] = 91
    res = F.finalize(pay, request=_request())
    assert res["accepted"] == []


def test_a_verify_status_in_the_payload_never_becomes_a_verification(tmp_path):
    store = ExternalStore(tmp_path / "t.duckdb")
    pay = _payload()
    pay["companies"][0]["claims"][0]["verify_status"] = "VERIFIED_LOCAL"
    res = F.finalize(pay, request=_request(), apply=True, store=store)
    assert res["accepted"] == ["FICO"]
    assert store.verify_rates() == {"SELF_ATTESTED": 1}


def test_the_stored_record_carries_no_score(tmp_path):
    """score.py computes it, and only after verify.py has run. A score written here
    would be a score computed from unverified evidence."""
    store = ExternalStore(tmp_path / "t.duckdb")
    res = F.finalize(_payload(), request=_request(), apply=True, store=store)
    row = store.company("FICO", res["research_version"])
    assert row["external_score"] is None
    assert row["external_confidence"] is None
    assert row["moat_trajectory"] == "WEAKENING"


# ============================================================ schema enforcement
def test_an_out_of_vocabulary_categorical_rejects_the_company():
    pay = _payload()
    pay["companies"][0]["pass_a"]["moat_trajectory"] = "GETTING WORSE"
    res = F.finalize(pay, request=_request())
    assert res["accepted"] == []
    assert any("moat_trajectory" in r for r in res["rejected"][0]["reasons"])


def test_an_out_of_range_depth_rejects_the_company():
    res = F.finalize(_payload(research_depth=9), request=_request())
    assert res["accepted"] == []


def test_a_bool_depth_is_rejected_because_isinstance_bool_int_is_true():
    res = F.finalize(_payload(research_depth=True), request=_request())
    assert res["accepted"] == []


def test_an_overlong_text_rejects_the_company():
    pay = _payload()
    pay["companies"][0]["pass_a"]["bull_case"] = "x" * 801
    res = F.finalize(pay, request=_request())
    assert res["accepted"] == []


def test_a_missing_pass_a_rejects_the_company():
    """The blind pass is the point of the design."""
    pay = _payload()
    del pay["companies"][0]["pass_a"]
    res = F.finalize(pay, request=_request())
    assert res["accepted"] == []
    assert any("blind pass" in r for r in res["rejected"][0]["reasons"])


def test_a_claim_whose_quote_is_absent_from_its_excerpt_rejects_the_company():
    pay = _payload()
    pay["companies"][0]["claims"][0]["quote"] = "words that are not there"
    res = F.finalize(pay, request=_request())
    assert res["accepted"] == []


def test_a_duplicate_claim_id_within_one_company_is_caught():
    pay = _payload()
    pay["companies"][0]["claims"] = [_claim(), _claim()]
    res = F.finalize(pay, request=_request())
    assert res["accepted"] == []
    assert any("duplicate claim_id" in r for r in res["rejected"][0]["reasons"])


def test_nothing_is_ever_silently_dropped():
    """A payload that half-arrives must say which half and why, or the next run cannot
    tell a research gap from a parsing accident."""
    req = _request(tickers=("FICO", "VRT", "NVDA"))
    pay = _payload()
    pay["companies"].append(_payload(ticker="VRT", research_depth=99)["companies"][0])
    res = F.finalize(pay, request=req)
    assert set(res["accepted"]) == {"FICO"}
    assert {r["ticker"] for r in res["rejected"]} == {"VRT"}
    assert res["unanswered"] == ["NVDA"]
    assert res["rejected"][0]["reasons"]


# ================================================================= the request
def test_the_blind_pass_leaks_no_score_and_no_rationale():
    """Two files, not one field marked do-not-read. Anchoring on the incumbent's answer
    is exactly what the blind pass exists to measure."""
    from clab import config
    if not config.SCORES_PARQUET.exists():
        pytest.skip("no book on disk")
    request, conclusions = R.build_request(["FICO"], store=_ActiveObjects())
    blob = json.dumps(request)
    assert "rationale" not in blob
    assert "killer" not in blob
    assert "earned_points" not in blob
    assert request["pass"] == "A"
    # ...and the withheld half is real
    assert conclusions["conclusions"][0]["sg"] is not None
    assert conclusions["conclusions"][0]["bq_rationales"]
    assert conclusions["request_id"] == request["request_id"]


def test_the_request_id_is_a_hash_of_the_roster_content():
    """A roster edited after the fact yields a different id, so the finalizer rejects
    a payload built against the old one."""
    from clab import config
    if not config.SCORES_PARQUET.exists():
        pytest.skip("no book on disk")
    a, _ = R.build_request(["FICO"], store=_ActiveObjects())
    b, _ = R.build_request(["FICO"], store=_ActiveObjects())
    c, _ = R.build_request(["FICO", "VRT"], store=_ActiveObjects())
    assert a["request_id"] == b["request_id"]
    assert a["request_id"] != c["request_id"]


def test_the_roster_carries_evidence_but_never_unverified_evidence():
    """E40 measured LFM2.5 citing text absent from the filing 9.7% of the time.
    Handing an unverified quote to an external researcher as "what the company said"
    would launder that straight into the external layer."""
    from clab import config
    if not config.SCORES_PARQUET.exists():
        pytest.skip("no book on disk")
    roster, _ = R.build_roster(["FICO"], store=_ActiveObjects())
    assert "filing_evidence" in roster[0]
    card_path = R._scorecard_path(roster[0]["cik"], "FICO")
    if not card_path.name:
        pytest.skip("no scorecard")
    card = json.loads(card_path.read_text(encoding="utf-8"))
    unverified = {st.get("evidence") for c in card["components"].values()
                  for st in c.get("subtests") or [] if st.get("evidence_unverified")}
    shipped = {q.split("] ", 1)[-1] for v in roster[0]["filing_evidence"].values()
               for q in v}
    assert not (shipped & {u for u in unverified if u})


def test_an_unknown_ticker_stops_the_build_rather_than_shipping_a_gap():
    from clab import config
    if not config.SCORES_PARQUET.exists():
        pytest.skip("no book on disk")
    with pytest.raises(SystemExit, match="not in the book"):
        R.build_roster(["NOSUCHTICKER"])



class _ActiveObjects:
    """A store whose industry objects are all ACTIVE.

    `build_roster` checks the LIVE store for an active industry object, so any test that
    omits `store=` passes or fails on production state. The completeness gate retired
    `us_credit_scoring` on 2026-09-09 and four tests here went red - correct behaviour
    from the guard, wrong dependency in the test. Inject this instead.
    """

    @staticmethod
    def industry(industry_id, *a, **kw):
        return {"industry_id": industry_id, "status": None}



def test_a_missing_or_superseded_industry_object_blocks_phase_b():
    """Retiring B4 must be operational, not a note a future batch can ignore."""
    from clab import config
    if not config.SCORES_PARQUET.exists():
        pytest.skip("no book on disk")

    class _RetiredObjects:
        @staticmethod
        def industry(_industry_id):
            return None

    with pytest.raises(SystemExit, match="Phase A must land and verify before Phase B"):
        R.build_roster(["FICO"], store=_RetiredObjects())


def test_an_active_industry_object_allows_the_roster():
    from clab import config
    if not config.SCORES_PARQUET.exists():
        pytest.skip("no book on disk")

    roster, _ = R.build_roster(["FICO"], store=_ActiveObjects())
    assert [r["ticker"] for r in roster] == ["FICO"]


# ==================================================== the citation rule (E42 arm 2)
def _uncited_payload():
    """One cited field, one asserted with nothing behind it."""
    pay = _payload()
    pay["companies"][0]["pass_a"]["current_moat_strength"] = "EXCEPTIONAL"
    # the only claim cites moat_trajectory, so current_moat_strength is uncited
    return pay


def test_without_the_rule_an_uncited_assertion_is_kept(tmp_path):
    store = ExternalStore(tmp_path / "t.duckdb")
    res = F.finalize(_uncited_payload(), request=_request(), apply=True, store=store)
    row = store.company("FICO", res["research_version"])
    assert row["current_moat_strength"] == "EXCEPTIONAL"
    assert res["require_citation"] is False
    assert res["demoted"] == {}


def test_with_the_rule_an_uncited_assertion_becomes_unknown(tmp_path):
    """Measured on the first pilot: only 10 of 36 non-UNKNOWN assertions had a claim
    naming that field. Asking for citations in the prompt and not enforcing them here
    is exactly how the schema gap happened."""
    store = ExternalStore(tmp_path / "t.duckdb")
    req = _request()
    req["require_citation"] = True
    res = F.finalize(_uncited_payload(), request=req, apply=True, store=store)
    row = store.company("FICO", res["research_version"])
    assert row["current_moat_strength"] == "UNKNOWN"
    assert "current_moat_strength" in res["demoted"]["FICO"]


def test_a_cited_field_survives_the_rule(tmp_path):
    """Demotion must not touch the good part - the cited fields are why we ran."""
    store = ExternalStore(tmp_path / "t.duckdb")
    req = _request()
    req["require_citation"] = True
    res = F.finalize(_uncited_payload(), request=req, apply=True, store=store)
    row = store.company("FICO", res["research_version"])
    assert row["moat_trajectory"] == "WEAKENING"      # cited by c_0123456789ab
    assert "moat_trajectory" not in res["demoted"]["FICO"]


def test_demotion_never_rejects_the_company():
    """Rejecting would throw away the cited fields alongside the uncited ones."""
    req = _request()
    req["require_citation"] = True
    res = F.finalize(_uncited_payload(), request=req)
    assert res["accepted"] == ["FICO"]
    assert res["rejected"] == []


def test_an_already_unknown_field_is_not_reported_as_demoted():
    """UNKNOWN was already the honest answer; demoting it would inflate the count."""
    pay = _payload()
    pay["companies"][0]["pass_a"]["company_specific_capture"] = "UNKNOWN"
    req = _request()
    req["require_citation"] = True
    res = F.finalize(pay, request=req)
    assert "company_specific_capture" not in res["demoted"].get("FICO", [])


def test_backing_is_reported_whether_or_not_the_rule_is_on():
    """The measurement is the point of the arm, so it must not depend on the rule."""
    res = F.finalize(_uncited_payload(), request=_request())
    b = res["backing"]["FICO"]
    assert b["claims"] == 1
    assert b["backed"] < b["asserted_non_unknown"]


def test_two_runs_over_one_roster_do_not_overwrite_each_other(tmp_path):
    """A run label is part of research_version. Without it the second arm destroys the
    first, which is the arm it is being compared against."""
    store = ExternalStore(tmp_path / "t.duckdb")
    a = _request(); a["sample"] = "E42-pilot"
    b = _request(); b["sample"] = "E42-cited"; b["require_citation"] = True
    ra = F.finalize(_uncited_payload(), request=a, apply=True, store=store)
    rb = F.finalize(_uncited_payload(), request=b, apply=True, store=store)
    assert ra["research_version"] != rb["research_version"]
    assert store.company("FICO", ra["research_version"])["current_moat_strength"] == "EXCEPTIONAL"
    assert store.company("FICO", rb["research_version"])["current_moat_strength"] == "UNKNOWN"


def test_a_labelled_run_gets_its_own_request_id():
    """Same roster, different research rule, different request. Otherwise the two runs
    collide in the manifest."""
    from clab import config
    if not config.SCORES_PARQUET.exists():
        pytest.skip("no book on disk")
    a, _ = R.build_request(["FICO"], sample="E42-pilot", store=_ActiveObjects())
    b, _ = R.build_request(["FICO"], sample="E42-cited", require_citation=True,
                          store=_ActiveObjects())
    assert a["request_id"] != b["request_id"]
    assert b["require_citation"] is True
    assert a["require_citation"] is False
