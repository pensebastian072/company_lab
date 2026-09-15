"""One command, one exit code, run before ingest.

Every check here is proved in BOTH directions: that it refuses the defect it was built
for, and that it passes a clean batch. A gate that has only ever been seen returning zero
is indistinguishable from a gate that cannot return anything else - which is exactly how
E34's first draft reported 147 companies clean while JPM held $31.67bn of buybacks.
"""
from __future__ import annotations

import json

from clab.external import acceptance as A
from clab.external import research_ingest as RI
from clab.external import verify as V
from clab.external.store import ExternalStore


def _obj(industry_id, sector_id="industrials", *, growth="EXPANDING",
         replication="HARD", substitution="LOW", claims=None, ok=True):
    o = {"industry_id": industry_id, "sector_id": sector_id, "version": "2026-09-11",
         "structural_growth": growth, "replication_difficulty": replication,
         "substitution_risk": substitution, "claims": claims or []}
    return {"industry_id": industry_id, "ok": ok, "reasons": [], "claim_reasons": {},
            "evidence": RI.evidence_profile(o["claims"]), "_obj": o}


def _claim(cid="c_00000000000a", *, field="structural_growth",
           url="https://www.eia.gov/report", domain="PRIMARY_DATA",
           source_type="PRIMARY_DATA", quote="a quoted sentence"):
    return {"claim_id": cid, "field": field, "text": "t", "source_url": url,
            "independence_domain": domain, "source_type": source_type, "quote": quote}


def _store(tmp_path, industries=()):
    st = ExternalStore(tmp_path / "t.duckdb")
    for iid, sector in industries:
        st.upsert_industry({"industry_id": iid, "version": "2026-09-01",
                            "sector_id": sector, "structural_growth": "STABLE"})
    return st


# ------------------------------------------------------ an object that says nothing
def test_an_object_that_answers_nothing_is_REFUSED(tmp_path):
    """E61 shipped 25 of these. They passed every quality check there was: 138 of 138
    claims VERIFIED_LOCAL, no unsourced field, lifecycle guards intact - and 20 of 25
    concluded nothing, with 259 companies about to be judged against them."""
    st = _store(tmp_path)
    r = A.accept_objects([_obj("empty_unit", growth="UNKNOWN", replication="UNKNOWN",
                               substitution="UNKNOWN", claims=[_claim()])],
                         store=st, fetch=False)
    assert r.exit_code == 1
    fail = [c for c in r.checks if c.name == "structural_ordinals"][0]
    assert fail.verdict == A.FAIL and "empty_unit" in fail.detail


def test_an_object_answering_all_three_PASSES(tmp_path):
    """The other direction. Without this the test above proves only that the check
    fires, not that it discriminates."""
    st = _store(tmp_path)
    r = A.accept_objects([_obj("real_unit", claims=[_claim()])], store=st, fetch=False)
    assert r.exit_code == 0
    assert [c for c in r.checks
            if c.name == "structural_ordinals"][0].verdict == A.PASS


def test_an_object_at_two_of_three_WARNS_rather_than_refusing(tmp_path):
    """A reasoned UNKNOWN is a RESULT. A strict 3-of-3 auto-retire deleted 11 working
    objects on 2026-09-09, `regional_banking` among them, and blocked a staged
    42-company batch. Below three the object survives and owes a written reason."""
    st = _store(tmp_path)
    r = A.accept_objects([_obj("thin_unit", substitution="UNKNOWN",
                               claims=[_claim()])], store=st, fetch=False)
    assert r.exit_code == 0
    assert [c for c in r.checks
            if c.name == "structural_ordinals"][0].verdict == A.WARN


# ------------------------------------------------------------- source diversity
def test_an_object_evidenced_ONLY_by_issuer_filings_is_REFUSED(tmp_path):
    """E79 built 64 objects whose evidence was 100% sec.gov. An industry description
    sourced entirely from its own members' paperwork has no outside view of the
    industry it claims to describe, whatever its claim count."""
    st = _store(tmp_path)
    issuer = [_claim(f"c_00000000000{i}", url="https://www.sec.gov/Archives/x",
                     domain="COMPANY_IR", source_type="SEC_FILING")
              for i in "abc"]
    r = A.accept_objects([_obj("issuer_only", claims=issuer)], store=st, fetch=False)
    assert r.exit_code == 1
    fail = [c for c in r.checks if c.name.startswith("source_diversity")][0]
    assert fail.verdict == A.FAIL and "NOT ONE" in fail.detail


def test_one_non_issuer_source_is_enough_to_pass_the_bar(tmp_path):
    """The bar is `entirely`, not `mostly`, and that is deliberate: a batch legitimately
    rests on filings for most of what it says. What cannot stand is no outside source
    at all."""
    st = _store(tmp_path)
    claims = [_claim("c_00000000000a", url="https://www.sec.gov/x",
                     domain="COMPANY_IR", source_type="SEC_FILING"),
              _claim("c_00000000000b", url="https://www.eia.gov/y",
                     domain="PRIMARY_DATA", source_type="PRIMARY_DATA")]
    r = A.accept_objects([_obj("mixed", claims=claims)], store=st, fetch=False)
    assert r.exit_code == 0
    div = [c for c in r.checks if c.name.startswith("source_diversity")][0]
    assert div.verdict in (A.PASS, A.WARN)


def test_heavy_single_host_concentration_warns_without_refusing(tmp_path):
    """E61 ran 96.6% on a single domain and nothing showed it. It is a warning, not a
    refusal: one regulator publishing most of a sector's statistics is normal."""
    st = _store(tmp_path)
    claims = [_claim(f"c_0000000000{i:02d}", url="https://www.eia.gov/a",
                     domain="PRIMARY_DATA") for i in range(19)]
    claims.append(_claim("c_0000000000zz", url="https://www.eia.gov/b",
                         domain="REGULATOR"))
    r = A.accept_objects([_obj("one_host", claims=claims)], store=st, fetch=False)
    div = [c for c in r.checks if c.name.startswith("source_diversity")][0]
    assert div.verdict == A.WARN
    assert div.data["top_host_share"] >= A.HOST_CONCENTRATION_WARN
    assert r.exit_code == 0


# ---------------------------------------------------------------- split units
def test_a_NEW_unit_with_no_ordinal_claim_is_REFUSED(tmp_path):
    """Rule 6. The taxonomy split that took 20 units to 64 left 26 singletons, 36 of
    which the completeness gate then retired, stranding 131 companies. Splitting and
    then failing to evidence is strictly worse than not splitting."""
    st = _store(tmp_path, [("existing_unit", "industrials")])
    new = _obj("brand_new_unit", claims=[_claim(field="market_structure")])
    r = A.accept_objects([new], store=st, fetch=False)
    assert r.exit_code == 1
    fail = [c for c in r.checks if c.name == "split_unit_evidence"][0]
    assert fail.verdict == A.FAIL and "brand_new_unit" in fail.detail


def test_a_new_unit_that_carries_its_own_ordinal_claim_passes(tmp_path):
    st = _store(tmp_path, [("existing_unit", "industrials")])
    new = _obj("brand_new_unit", claims=[_claim(field="structural_growth")])
    r = A.accept_objects([new], store=st, fetch=False)
    assert r.exit_code == 0
    assert [c for c in r.checks
            if c.name == "split_unit_evidence"][0].verdict == A.PASS


def test_a_first_object_in_an_EMPTY_sector_is_not_treated_as_a_split(tmp_path):
    """A sector's first object cannot be a split of anything. Firing there would
    refuse every sector's Phase A on its opening batch."""
    st = _store(tmp_path, [("other_sector_unit", "energy")])
    r = A.accept_objects([_obj("first_in_sector", sector_id="materials",
                               claims=[_claim(field="market_structure")])],
                         store=st, fetch=False)
    assert [c for c in r.checks
            if c.name == "split_unit_evidence"][0].verdict == A.PASS


# ------------------------------------------------------- exact containment
def test_citations_that_are_not_on_their_own_pages_are_REFUSED(tmp_path, monkeypatch):
    """The 2026-09-11 audit, moved from a post-mortem into a gate. A claim that fails
    exact containment will be stored UNVERIFIABLE and contribute nothing, so finding
    out now costs a re-emission and finding out later costs a sector."""
    st = _store(tmp_path)
    claims = [_claim(f"c_0000000000{i:02d}", quote="a sentence that is simply not there")
              for i in range(25)]
    page = "padding " * 120 + "an entirely different sentence" + " padding" * 120
    monkeypatch.setattr(V, "fetch",
                        lambda url, refetch=False: V.Fetched(url, True, page))
    r = A.accept_objects([_obj("bad_cites", claims=claims)], store=st, fetch=True)
    check = [c for c in r.checks if c.name.startswith("exact_containment")][0]
    assert check.verdict == A.FAIL
    assert check.data["rate"] == 0.0 and check.data["failures"]
    assert r.exit_code == 1


def test_citations_that_ARE_on_their_pages_pass_containment(tmp_path, monkeypatch):
    st = _store(tmp_path)
    quote = "the quoted sentence appears verbatim"
    claims = [_claim(f"c_0000000000{i:02d}", quote=quote) for i in range(25)]
    page = "padding " * 120 + quote + " padding" * 120
    monkeypatch.setattr(V, "fetch",
                        lambda url, refetch=False: V.Fetched(url, True, page))
    r = A.accept_objects([_obj("good_cites", claims=claims)], store=st, fetch=True)
    check = [c for c in r.checks if c.name.startswith("exact_containment")][0]
    assert check.verdict == A.PASS and check.data["rate"] == 1.0


def test_an_unreachable_source_never_counts_against_the_batch(tmp_path, monkeypatch):
    """A 403 is our failure to check. Letting it fail the batch would manufacture a
    refusal out of network conditions - the same error MIN_PAGE_CHARS exists to
    prevent one layer down."""
    st = _store(tmp_path)
    claims = [_claim(f"c_0000000000{i:02d}") for i in range(25)]
    monkeypatch.setattr(V, "fetch", lambda url, refetch=False: V.Fetched(
        url, False, error="HttpError: HTTP 403"))
    r = A.accept_objects([_obj("blocked", claims=claims)], store=st, fetch=True)
    check = [c for c in r.checks if c.name.startswith("exact_containment")][0]
    assert check.verdict == A.SKIP
    assert r.exit_code == 0


def test_no_fetch_says_the_batch_was_not_checked_rather_than_passing_it(tmp_path):
    """SKIP, never PASS. A check that was not run must not read as a check that
    succeeded - that is the graceful-degradation bug this repo has been bitten by
    five times."""
    st = _store(tmp_path)
    r = A.accept_objects([_obj("u", claims=[_claim()])], store=st, fetch=False)
    check = [c for c in r.checks if c.name.startswith("exact_containment")][0]
    assert check.verdict == A.SKIP and "NOT tested" in check.detail


# ------------------------------------------------------ Phase B: a company batch
def _company(ticker, industry_id="diversified_banks", sector_id="financials",
             **cats):
    base = {f: "UNKNOWN" for f in
            ("current_moat_strength", "competitive_position",
             "competitive_position_trend", "moat_trajectory",
             "industry_structural_growth", "company_specific_capture",
             "demand_visibility", "market_share_direction", "pricing_power",
             "technology_risk", "disruption_risk", "regulatory_risk")}
    base.update(cats)
    return {"ticker": ticker, "industry_id": industry_id, "sector_id": sector_id,
            "categoricals": base, "claims": []}


def _seed_baseline(st, n=10, **cats):
    for i in range(n):
        st.upsert_company({"ticker": f"B{i:03d}", "research_version": "2026-09-01",
                           "sector_id": "financials",
                           "industry_id": "diversified_banks", **cats})


def test_a_four_field_fill_collapse_against_the_same_sector_is_REFUSED(tmp_path):
    """The failure that shaped this whole layer: 92% -> 0% over eight batches while
    every quality metric stayed perfect. These four fields carry 45 of the 100
    external points."""
    st = _store(tmp_path)
    _seed_baseline(st, 10, competitive_position="STRONG",
                   competitive_position_trend="IMPROVING",
                   moat_trajectory="WIDENING", company_specific_capture="HIGH")
    payload = {"companies": [_company(f"N{i:03d}") for i in range(10)]}
    report = A.Report("t")
    A.check_company_batch(report, payload, store=st, fetch=False)
    fill = [c for c in report.checks if c.name == "four_field_fill"][0]
    assert fill.verdict == A.FAIL
    assert report.exit_code == 1


def test_a_batch_that_holds_its_fill_rate_passes(tmp_path):
    st = _store(tmp_path)
    _seed_baseline(st, 10, competitive_position="STRONG",
                   competitive_position_trend="IMPROVING",
                   moat_trajectory="WIDENING", company_specific_capture="HIGH")
    payload = {"companies": [
        _company(f"N{i:03d}", competitive_position="STRONG",
                 competitive_position_trend="STABLE", moat_trajectory="WIDENING",
                 company_specific_capture="MODERATE") for i in range(10)]}
    report = A.Report("t")
    A.check_company_batch(report, payload, store=st, fetch=False)
    assert [c for c in report.checks
            if c.name == "four_field_fill"][0].verdict == A.PASS


def test_the_first_batch_of_a_sector_is_skipped_not_failed(tmp_path):
    """There is nothing to regress against. Reading `no baseline` as a regression would
    refuse every sector's opening batch."""
    st = _store(tmp_path)
    payload = {"companies": [_company(f"N{i:03d}") for i in range(10)]}
    report = A.Report("t")
    A.check_company_batch(report, payload, store=st, fetch=False)
    assert [c for c in report.checks
            if c.name == "four_field_fill"][0].verdict == A.SKIP


def test_a_rank_order_field_all_UNKNOWN_across_the_batch_is_REFUSED(tmp_path):
    """`constant_fields` reports and never fails in batch_health, because a regulated
    sector can honestly answer UNKNOWN to every market-share question - E53 returned
    0 of 59 correctly. The one exception is a RANK-ORDER field: a batch cannot honestly
    not know its own companies' competitive position, all of them, every time."""
    st = _store(tmp_path)
    payload = {"companies": [
        _company(f"N{i:03d}", competitive_position="STRONG",
                 competitive_position_trend="STABLE", moat_trajectory="WIDENING",
                 company_specific_capture="HIGH" if i % 2 else "MODERATE",
                 pricing_power="STRONG" if i % 3 else "MODERATE")
        for i in range(10)]}
    # moat_trajectory is constant but answered; competitive_position too. Make one
    # rank-order field genuinely all-UNKNOWN.
    for c in payload["companies"]:
        c["categoricals"]["competitive_position"] = "UNKNOWN"
    report = A.Report("t")
    A.check_company_batch(report, payload, store=st, fetch=False)
    const = [c for c in report.checks if c.name == "constant_fields"][0]
    assert const.verdict == A.FAIL
    assert "competitive_position" in const.detail


def test_a_non_rank_order_constant_only_warns(tmp_path):
    """`market_share_direction` came back UNKNOWN for 85 of 85 Financials companies and
    that was correct for regulated names. Report it; never refuse on it."""
    st = _store(tmp_path)
    payload = {"companies": [
        _company(f"N{i:03d}", competitive_position="STRONG" if i % 2 else "MODERATE",
                 competitive_position_trend="STABLE" if i % 3 else "IMPROVING",
                 moat_trajectory="WIDENING" if i % 2 else "STABLE",
                 company_specific_capture="HIGH" if i % 2 else "MODERATE")
        for i in range(10)]}
    report = A.Report("t")
    A.check_company_batch(report, payload, store=st, fetch=False)
    const = [c for c in report.checks if c.name == "constant_fields"][0]
    assert const.verdict == A.WARN
    assert any(c["field"] == "market_share_direction"
               for c in const.data["all_unknown"])


def test_accept_payload_reads_a_file_and_returns_one_exit_code(tmp_path):
    st = _store(tmp_path)
    path = tmp_path / "payload.json"
    path.write_text(json.dumps({"companies": [_company("AAA")]}), encoding="utf-8")
    report = A.accept_payload(path, store=st, fetch=False)
    assert report.exit_code in (0, 1)
    assert "payload.json" in report.subject


# ------------------------------------------------------ wired into the ingest
def test_research_ingest_refuses_a_failing_batch_and_says_which(tmp_path, monkeypatch,
                                                                capsys):
    """The whole point: one command, one exit code, positioned before the write."""
    from clab.external import research_ingest as RI

    bad = [_obj("empty_unit", growth="UNKNOWN", replication="UNKNOWN",
                substitution="UNKNOWN", claims=[_claim()])]
    st = _store(tmp_path)
    monkeypatch.setattr(RI, "load_and_validate", lambda *a, **k: bad)
    monkeypatch.setattr(RI, "load_and_validate_sectors", lambda *a, **k: [])
    real = A.accept_objects
    monkeypatch.setattr(A, "accept_objects",
                        lambda results, fetch=True: real(results, store=st,
                                                         fetch=False))
    written = []
    monkeypatch.setattr(RI, "ingest",
                        lambda results, **kw: written.append(kw) or {"written": [],
                                                                     "skipped": [],
                                                                     "claims": 0})
    monkeypatch.setattr(RI, "ingest_sectors",
                        lambda results, **kw: {"written": [], "claims": 0})
    code = RI.main(["--apply", "--no-fetch"])
    out = capsys.readouterr().out
    assert code == 2
    assert "INGEST REFUSED" in out
    assert "structural_ordinals" in out
    assert written == [], "a refused batch must not reach ingest()"


def test_the_override_is_loud_and_names_what_it_overrode(tmp_path, monkeypatch,
                                                         capsys):
    """A gate with no override gets deleted the first time it is wrong. A gate with a
    SILENT override gets used silently. This one takes a written reason and shouts."""
    from clab.external import research_ingest as RI

    bad = [_obj("empty_unit", growth="UNKNOWN", replication="UNKNOWN",
                substitution="UNKNOWN", claims=[_claim()])]
    st = _store(tmp_path)
    monkeypatch.setattr(RI, "load_and_validate", lambda *a, **k: bad)
    monkeypatch.setattr(RI, "load_and_validate_sectors", lambda *a, **k: [])
    real = A.accept_objects
    monkeypatch.setattr(A, "accept_objects",
                        lambda results, fetch=True: real(results, store=st,
                                                         fetch=False))
    monkeypatch.setattr(RI, "ingest", lambda results, **kw: {"written": ["empty_unit"],
                                                             "skipped": [], "claims": 0})
    monkeypatch.setattr(RI, "ingest_sectors",
                        lambda results, **kw: {"written": [], "claims": 0})
    code = RI.main(["--apply", "--no-fetch", "--override-acceptance", "known good"])
    out = capsys.readouterr().out
    assert "ACCEPTANCE GATE OVERRIDDEN: known good" in out
    assert "structural_ordinals" in out
    assert code == 1, "an overridden refusal still reports a non-zero exit"


def test_a_small_object_with_one_bad_citation_is_warned_not_refused(tmp_path,
                                                                    monkeypatch):
    """Under MIN_CLAIMS_FOR_RATE a rate is noise. One bad citation of eight already
    costs that claim its status; refusing the object would delete seven good claims to
    punish one bad one."""
    st = _store(tmp_path)
    good = [_claim(f"c_0000000000{i:02d}", quote="the quoted sentence appears")
            for i in range(7)]
    good.append(_claim("c_0000000000zz", quote="a sentence that is simply not there"))
    page = "padding " * 120 + "the quoted sentence appears" + " padding" * 120
    monkeypatch.setattr(V, "fetch",
                        lambda url, refetch=False: V.Fetched(url, True, page))
    r = A.accept_objects([_obj("small", claims=good)], store=st, fetch=True)
    check = [c for c in r.checks if c.name.startswith("exact_containment")][0]
    assert check.verdict == A.WARN and check.data["certified"] == 7
    assert r.exit_code == 0


def test_a_small_object_with_NOTHING_findable_is_refused(tmp_path, monkeypatch):
    """The floor at small n is zero, not a rate: an object none of whose citations can
    be found has no verifiable evidence at all."""
    st = _store(tmp_path)
    claims = [_claim(f"c_0000000000{i:02d}", quote="not on the page at all")
              for i in range(6)]
    page = "padding " * 120 + "an entirely different sentence" + " padding" * 120
    monkeypatch.setattr(V, "fetch",
                        lambda url, refetch=False: V.Fetched(url, True, page))
    r = A.accept_objects([_obj("empty_evidence", claims=claims)], store=st, fetch=True)
    check = [c for c in r.checks if c.name.startswith("exact_containment")][0]
    assert check.verdict == A.FAIL and check.data["certified"] == 0
    assert r.exit_code == 1


def test_the_containment_floor_sits_in_the_measured_gap():
    """0.95 is not taste. `--containment-history` over the ingested corpus is bimodal:
    ten batches at 99.3-100%, three at 89.2-91.5%, and nothing in between. The floor
    separates the two clusters; a floor inside the low one would pass two of the three
    bad batches on no principle."""
    assert 0.915 < A.MIN_CONTAINMENT_RATE < 0.993


# --------------------------------- the shape the producer actually emits
def _emitted(ticker, **pass_a):
    """A company row shaped the way a finished payload is shaped: answers under
    `pass_a`, and NO taxonomy ids - `research_ingest` resolves those on the way in."""
    base = {f: "UNKNOWN" for f in
            ("current_moat_strength", "competitive_position",
             "competitive_position_trend", "moat_trajectory",
             "industry_structural_growth", "company_specific_capture",
             "demand_visibility", "market_share_direction", "pricing_power",
             "technology_risk", "disruption_risk", "regulatory_risk")}
    base.update(pass_a)
    return {"ticker": ticker, "research_depth": "FULL", "pass_a": base, "claims": []}


_BOOK = {"E001": {"sector_id": "financials", "industry_id": "diversified_banks"}}


def test_the_gate_reads_the_answers_out_of_pass_a_not_just_categoricals():
    """The regression that mattered most. Every emitted payload carries its answers
    under `pass_a`; this module's first draft read `categoricals` only, fell through to
    the row, found nothing, and scored E47 and E59-b3 at **0.0% four-field fill with all
    four rank-order fields all-UNKNOWN**. Both payloads in fact answer three of the four.
    A gate whose measurement is wrong is worse than no gate: it refuses clean batches on
    a defect they do not have, and its real refusals become unreadable."""
    rows = A._payload_rows({"companies": [
        _emitted("E001", competitive_position="LEADER", moat_trajectory="STABLE")]})
    assert rows[0]["competitive_position"] == "LEADER"
    assert rows[0]["moat_trajectory"] == "STABLE"


def test_a_flat_row_and_a_categoricals_row_both_still_read():
    """`categoricals` is what `store.upsert_company` takes and what the rest of these
    tests build, and a flat row is what an ad-hoc caller passes. Reading `pass_a` must
    not cost either of them."""
    flat = A._payload_rows({"companies": [
        {"ticker": "F1", "competitive_position": "LAGGARD"}]})
    nested = A._payload_rows({"companies": [
        {"ticker": "F2", "categoricals": {"competitive_position": "CHALLENGER"}}]})
    assert flat[0]["competitive_position"] == "LAGGARD"
    assert nested[0]["competitive_position"] == "CHALLENGER"


def test_categoricals_wins_over_pass_a_because_that_is_what_lands():
    """`finalize.py` filters `pass_a` through ALLOWED_CATEGORICALS and writes
    `categoricals`, so where a row carries both, `categoricals` is the shape that reaches
    the store. The gate grades what lands. Merged rather than picked, so a row split
    across both holders keeps every field instead of half of them."""
    rows = A._payload_rows({"companies": [
        {"ticker": "F3", "categoricals": {"competitive_position": "LAGGARD"},
         "pass_a": {"competitive_position": "LEADER",
                    "moat_trajectory": "STABLE"}}]})
    assert rows[0]["competitive_position"] == "LAGGARD"    # the normalised one wins
    assert rows[0]["moat_trajectory"] == "STABLE"          # and nothing is lost


def test_a_payload_without_ids_is_resolved_against_the_book():
    """A payload names tickers. Without resolution `sector_id` is None on every row, the
    four-field check has no sector to compare against and SKIPs, and the abstention
    collapse walks through the gate that exists to catch it."""
    rows = A._payload_rows({"companies": [_emitted("E001")]}, book=_BOOK)
    assert rows[0]["sector_id"] == "financials"
    assert rows[0]["industry_id"] == "diversified_banks"


def test_an_id_already_on_the_payload_is_never_overwritten_by_the_book():
    """The payload is the authority on its own rows; the book is the fallback. A batch
    deliberately researched under an override must not be silently regrouped."""
    row = dict(_emitted("E001"), sector_id="utilities", industry_id="electric_utilities")
    rows = A._payload_rows({"companies": [row]}, book=_BOOK)
    assert rows[0]["sector_id"] == "utilities"
    assert rows[0]["industry_id"] == "electric_utilities"


def test_an_emitted_payload_that_answers_is_not_scored_as_a_collapse(tmp_path):
    """End to end on the emitted shape: a batch that answers three of four fields must
    not read as all-UNKNOWN. This is the assertion that would have failed before the
    fix, on both reference payloads at once."""
    st = _store(tmp_path)
    payload = {"companies": [
        _emitted(f"E{i:03d}", competitive_position="LEADER", moat_trajectory="STABLE",
                 company_specific_capture="MODERATE") for i in range(12)]}
    report = A.Report("t")
    A.check_company_batch(report, payload, store=st, fetch=False,
                          book={f"E{i:03d}": _BOOK["E001"] for i in range(12)})
    fill = [c for c in report.checks if c.name == "four_field_fill"][0]
    assert fill.data["batch_fill"] == 0.75
    assert fill.data["sector_id"] == "financials"
    constant = [c for c in report.checks if c.name == "constant_fields"][0]
    assert constant.verdict == A.FAIL          # trend IS all-UNKNOWN here
    assert "competitive_position_trend" in constant.detail
    assert "competitive_position (" not in constant.detail   # and that one is answered
