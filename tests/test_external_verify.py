"""What a fetched page can and cannot settle.

The whole point of this module is one distinction: "we checked and the quote is not
there" is a fabrication signal, and "we could not check" is not. Collapsing them
manufactures a fabrication rate out of network conditions, and the first run of this
verifier did exactly that before MIN_PAGE_CHARS existed.
"""
from __future__ import annotations

import pytest

from clab.external import verify as V
from clab.external.schema import Claim
from clab.external.store import ExternalStore
from clab.qual.scorer import MIN_EVIDENCE_OVERLAP
from conftest import skip_if_locked


# ------------------------------------------------------- one shared threshold
def test_the_threshold_is_the_judged_half_s_threshold():
    """If these ever differ, this layer's unverifiable rate stops being comparable to
    E40's 9.7% / 0.5% and the baseline is gone."""
    assert V.MIN_EVIDENCE_OVERLAP == MIN_EVIDENCE_OVERLAP == 0.60


# --------------------------------------------------------------- check_quote
def test_a_verbatim_substring_verifies():
    status, ov = V.check_quote("run on Visa's debit network",
                               "DOJ alleges transactions run on Visa's debit network.")
    assert status == "VERIFIED_LOCAL" and ov == 1.0


def test_whitespace_and_case_do_not_break_a_substring_match():
    """PDF extraction re-flows whitespace; a quote copied from a two-column PDF will
    not match byte-for-byte and is still genuinely on the page."""
    status, _ = V.check_quote("more  than\n60% of debit",
                              "text ... MORE THAN 60% OF DEBIT transactions ...")
    assert status == "VERIFIED_LOCAL"


def test_a_paraphrase_that_shares_most_tokens_NO_LONGER_verifies():
    """This test asserted VERIFIED_LOCAL until 2026-09-11, and that was the defect.

    `who` for `that` is one word and this particular paraphrase is harmless. But the
    rule that admits it is the rule that admitted the 146: a median overlap of 1.0 on
    text that is not on the page in any sequence. Vocabulary is not quotation, and the
    fallback cannot tell a re-worded sentence from a different one. It warns now."""
    page = "The agreements penalize customers who route transactions to a different " \
           "debit network or an alternative payment system entirely."
    m = V.match_quote(
        "agreements penalize customers that route transactions to a different debit "
        "network", page)
    assert m.status == "UNVERIFIABLE"
    assert m.mode == V.MATCH_OVERLAP_ONLY
    assert m.overlap >= MIN_EVIDENCE_OVERLAP     # it still SCORES well - and still fails


def test_a_quote_absent_from_the_page_is_unverifiable():
    status, ov = V.check_quote("quarterly bookings rose forty percent",
                               "An unrelated page about municipal water infrastructure.")
    assert status == "UNVERIFIABLE" and ov < MIN_EVIDENCE_OVERLAP


def test_a_raw_pdf_body_can_never_verify_as_page_text():
    status, overlap = V.check_quote(
        "retirement assets were 49.1 trillion",
        b"%PDF-1.4 FlateDecode retirement assets were 49.1 trillion")
    assert status == "UNVERIFIABLE" and overlap is None


def test_shared_vocabulary_cannot_replace_the_quoted_numbers():
    quote = ("Total retirement assets were $49.1 trillion as of December 31, 2025, "
             "up 11.2 percent for the year")
    page = ("Total retirement assets were $47.6 trillion as of March 31, 2026, "
            "down 2.5 percent for the year. " + "retirement assets " * 100)
    status, overlap = V.check_quote(quote, page)
    assert overlap >= V.MIN_EVIDENCE_OVERLAP
    assert status == "UNVERIFIABLE"


def test_numeric_guard_normalizes_format_but_never_reads_partial_numbers():
    assert V._numeric_tokens("up +17%, $11.50, (18,459)") == {"17", "11.5", "18459"}
    assert "8459" not in V._numeric_tokens("a truncated fragment ense18,459")


def test_an_empty_quote_or_page_is_unverifiable_not_a_crash():
    assert V.check_quote("", "some page")[0] == "UNVERIFIABLE"
    assert V.check_quote("a quote", "")[0] == "UNVERIFIABLE"
    assert V.check_quote(None, "some page")[0] == "UNVERIFIABLE"


# ------------------------------------------------- the bug MIN_PAGE_CHARS fixes
def test_a_page_that_extracts_to_almost_nothing_is_not_a_fabrication_signal(
        tmp_path, monkeypatch):
    """Two DOJ press-release URLs returned HTTP 200 and extracted to ONE character - a
    JavaScript shell with no server-rendered body. The guard was `if not page.text`,
    and a single space is truthy, so both claims were tested against nothing, scored
    0.0 overlap, and were reported as UNVERIFIABLE. A rendering failure is ours."""
    store = ExternalStore(tmp_path / "t.duckdb")
    store.insert_claims([Claim(
        claim_id="c_000000000001", field="market_structure", text="t",
        source_url="https://js-shell.example/pr", quote="a quote that is really there",
        industry_id="payments")], request_id="r")

    monkeypatch.setattr(V, "fetch",
                        lambda url, refetch=False: V.Fetched(url, True, " "))
    res = V.verify_all(store=store, apply=True)
    assert res["tally"].get("UNVERIFIABLE", 0) == 0
    assert res["tally"]["SELF_ATTESTED"] == 1
    assert store.verify_rates() == {"SELF_ATTESTED": 1}
    assert "400" in res["unfetched"][0][2]


def test_a_page_just_over_the_floor_is_checked(tmp_path, monkeypatch):
    store = ExternalStore(tmp_path / "t.duckdb")
    store.insert_claims([Claim(
        claim_id="c_000000000001", field="f", text="t",
        source_url="https://ok.example/x", quote="the exact words",
        industry_id="payments")], request_id="r")
    page = "padding " * 60 + "the exact words" + " padding" * 60
    assert len(page) >= V.MIN_PAGE_CHARS
    monkeypatch.setattr(V, "fetch",
                        lambda url, refetch=False: V.Fetched(url, True, page))
    res = V.verify_all(store=store, apply=True)
    assert res["tally"]["VERIFIED_LOCAL"] == 1


# ------------------------------------------- could-not-check is never a failure
def test_a_403_leaves_the_claim_self_attested(tmp_path, monkeypatch):
    """A WAF block, a paywall or a timeout is our failure to check. cbre.com, oecd.org,
    ferc.gov and semi.org all 403'd on the real run; none of that is evidence that
    anything was invented."""
    store = ExternalStore(tmp_path / "t.duckdb")
    store.insert_claims([Claim(
        claim_id="c_000000000001", field="f", text="t",
        source_url="https://waf.example/x", quote="q", industry_id="datacenter_reits")],
        request_id="r")
    monkeypatch.setattr(V, "fetch", lambda url, refetch=False: V.Fetched(
        url, False, error="HttpError: HTTP 403"))
    res = V.verify_all(store=store, apply=True)
    assert res["tally"]["SELF_ATTESTED"] == 1
    assert res["tally"].get("UNVERIFIABLE", 0) == 0
    assert store.verify_rates() == {"SELF_ATTESTED": 1}


def test_the_rate_is_computed_over_CHECKED_claims_only(tmp_path, monkeypatch):
    """Unfetchable claims must not sit in the denominator - that would let a run of
    403s quietly improve the reported fabrication rate."""
    store = ExternalStore(tmp_path / "t.duckdb")
    store.insert_claims([
        Claim(claim_id="c_00000000000a", field="f", text="t",
              source_url="https://ok.example/1", quote="present words"),
        Claim(claim_id="c_00000000000b", field="f", text="t",
              source_url="https://ok.example/2", quote="absent phrase entirely"),
        Claim(claim_id="c_00000000000c", field="f", text="t",
              source_url="https://blocked.example/3", quote="q"),
    ], request_id="r")

    def fake(url, refetch=False):
        if "blocked" in url:
            return V.Fetched(url, False, error="HTTP 403")
        body = "filler " * 80
        return V.Fetched(url, True, body + ("present words" if url.endswith("1") else ""))

    monkeypatch.setattr(V, "fetch", fake)
    res = V.verify_all(store=store, apply=True)
    assert res["checked"] == 2                 # not 3
    assert res["unverifiable_rate"] == 0.5     # 1 of the 2 actually checked


def test_verify_all_with_no_claims_is_not_a_crash(tmp_path):
    assert V.verify_all(store=ExternalStore(tmp_path / "t.duckdb"))["claims"] == 0


# ------------------------------------------------------------------ extraction
def test_a_pdf_is_detected_by_magic_number_not_by_extension():
    """Several of these URLs serve a PDF from a path with no .pdf on it."""
    assert V.extract_text(b"%PDF-1.7\nbroken", "https://x/no-extension") == ""


def test_a_pdf_extraction_failure_has_a_specific_reason(tmp_path, monkeypatch):
    monkeypatch.setattr(V, "SOURCE_CACHE", tmp_path / "sources")
    monkeypatch.setattr(V.net, "http_get", lambda *a, **k: b"%PDF-1.7\nbroken")
    fetched = V.fetch("https://x/no-extension")
    assert fetched.ok is True
    assert fetched.text == ""
    assert fetched.unverifiable_reason == "pdf_not_extracted"


def test_html_tags_and_scripts_are_stripped():
    html = b"<html><head><style>p{color:red}</style><script>var x=1;</script></head>" \
           b"<body><p>the visible text</p></body></html>"
    text = V.extract_text(html, "https://x/page")
    assert "the visible text" in text
    assert "color:red" not in text and "var x" not in text


# ------------------------------------------------------------------- caching
def test_a_fetched_source_is_cached_and_replayed_free(tmp_path, monkeypatch):
    """A point spent must never be spent twice. A re-verification months from now must
    not re-hit forty hosts to re-check claims whose pages have not changed."""
    monkeypatch.setattr(V, "SOURCE_CACHE", tmp_path / "sources")
    calls = []

    def fake_get(url, **kw):
        calls.append(url)
        return b"<html><body>" + b"a lot of text " * 60 + b"</body></html>"

    monkeypatch.setattr(V.net, "http_get", fake_get)
    first = V.fetch("https://example.com/doc")
    second = V.fetch("https://example.com/doc")
    assert first.ok and second.ok
    assert second.from_cache is True
    assert len(calls) == 1


def test_cached_pdf_filter_uses_magic_number_not_url_suffix(tmp_path, monkeypatch):
    monkeypatch.setattr(V, "SOURCE_CACHE", tmp_path / "sources")
    V.SOURCE_CACHE.mkdir()
    V.net.atomic_write_gzip_bytes(V._cache_path("https://x/no-extension"),
                                  b"%PDF-1.7\nbytes")
    V.net.atomic_write_gzip_bytes(V._cache_path("https://x/report.pdf"),
                                  b"<html>not really a pdf</html>")
    assert V.cached_pdf_urls([
        "https://x/no-extension", "https://x/report.pdf"
    ]) == {"https://x/no-extension"}


def test_a_failed_fetch_is_also_remembered(tmp_path, monkeypatch):
    """Otherwise every run re-hits every dead link."""
    monkeypatch.setattr(V, "SOURCE_CACHE", tmp_path / "sources")
    calls = []

    def boom(url, **kw):
        calls.append(url)
        raise RuntimeError("HTTP 403")

    monkeypatch.setattr(V.net, "http_get", boom)
    assert V.fetch("https://blocked.example/x").ok is False
    again = V.fetch("https://blocked.example/x")
    assert again.ok is False and again.from_cache is True
    assert len(calls) == 1


# -------------------------------------------------- against the live catalog
@skip_if_locked
def test_no_claim_is_verified_without_an_overlap_recorded():
    from clab import config
    if not config.EXTERNAL_DB.exists():
        pytest.skip("no catalog on disk")
    with ExternalStore().connect() as con:
        bad = con.execute(
            "SELECT claim_id FROM external_claim "
            "WHERE verify_status = 'VERIFIED_LOCAL' AND overlap IS NULL").fetchall()
    assert bad == [], f"verified with no recorded overlap: {bad}"


@skip_if_locked
def test_self_attested_claims_carry_no_overlap():
    """SELF_ATTESTED means we did not test it. An overlap number there would imply we
    had."""
    from clab import config
    if not config.EXTERNAL_DB.exists():
        pytest.skip("no catalog on disk")
    with ExternalStore().connect() as con:
        bad = con.execute(
            "SELECT claim_id FROM external_claim "
            "WHERE verify_status = 'SELF_ATTESTED' AND overlap IS NOT NULL").fetchall()
    assert bad == [], f"untested claims carrying an overlap: {bad}"


# ------------------------------------------- exact containment is now the bar
#
# Audited 2026-09-11 over all 6,966 quoted VERIFIED_LOCAL claims:
#
#     exact containment today                        4,607   66.1%
#     + html.unescape                                5,615   80.6%
#     + Unicode punctuation & whitespace normalise    6,820   97.9%
#     unlocatable even then                            146    2.1%
#
# The mechanism is proved by a control inside the data: data.sec.gov serves JSON and
# has a 0.0% fallback rate over 321 claims against sec.gov HTML's 39.3% over 5,484.
# Same filer, same facts, different encoding.

def test_an_entity_laden_edgar_page_passes_EXACTLY():
    """EDGAR wraps figures in &#160;, so a numeric quote could never match verbatim and
    every such claim fell through to the vocabulary fallback. That is an encoding
    difference, not a content one, and it is what the 66.1% -> 80.6% step recovers."""
    page = ("padding " * 80 + "Total net revenue of &#8220;the segment&#8221; was "
            "&#36;3,619&#160;million, up&#160;3&#37; year&#8211;over&#8211;year."
            + " padding" * 80)
    m = V.match_quote(
        'Total net revenue of "the segment" was $3,619 million, up 3% year-over-year.',
        page)
    assert m.status == "VERIFIED_LOCAL"
    assert m.mode == V.MATCH_EXACT, "an entity difference must not need the loose path"
    assert m.overlap == 1.0


def test_a_table_concatenated_quote_passes_ONLY_on_the_whitespace_insensitive_path():
    """Text lifted out of an HTML table arrives with the cell boundaries gone:
    `...customer balances$3,619$3,5263%`. Every character of the quote is present and
    in order, so it is containment - just not with the spaces a reader would put in."""
    quote = "Average customer balances $3,619 $3,526 3 %"
    page = ("padding " * 80
            + "Average customer balances$3,619$3,5263%"
            + " padding" * 80)
    m = V.match_quote(quote, page)
    assert m.status == "VERIFIED_LOCAL"
    assert m.mode == V.MATCH_NO_WHITESPACE

    # And the strict path really does decline it - otherwise this test proves nothing.
    assert V.normalize_for_match(quote) not in V.normalize_for_match(page)


def test_the_right_vocabulary_with_the_wrong_figures_still_FAILS():
    """The near-miss that must never pass again. The ICI page scored 0.8182 on the old
    fallback while stating $47.6T and -2.5% where the quote said $49.1T and +11.2% -
    every content word shared, both numbers wrong. It is UNVERIFIABLE twice over now:
    the figures are not on the page, AND the sentence is not contained."""
    quote = ("Total retirement assets were $49.1 trillion as of December 31, 2025, "
             "up 11.2 percent for the year")
    page = ("padding " * 60
            + "Total retirement assets were $47.6 trillion as of March 31, 2026, "
              "down 2.5 percent for the year. " + "retirement assets total " * 60)
    m = V.match_quote(quote, page)
    assert m.status == "UNVERIFIABLE"
    assert m.mode == V.MATCH_NUMERIC_MISMATCH
    assert m.overlap >= MIN_EVIDENCE_OVERLAP, (
        "this quote must still SCORE above the old threshold, or the test is not "
        "exercising the near-miss it claims to")

    # The same sentence with the right figures is the control: it passes exactly.
    right = ("padding " * 60
             + "Total retirement assets were $49.1 trillion as of December 31, 2025, "
               "up 11.2 percent for the year." + " padding" * 60)
    assert V.match_quote(quote, right).mode == V.MATCH_EXACT


def test_a_near_miss_with_matching_figures_is_still_refused():
    """The numeric guard is not the only thing standing between a near-miss and a pass.
    Right vocabulary, right numbers, different sentence: containment still refuses."""
    quote = "Revenue grew 12% to $4.2 billion on strength in the datacenter segment"
    page = ("padding " * 60 + "Datacenter segment strength drove revenue to "
            "$4.2 billion, a decline of 12% excluding the divested unit."
            + " padding" * 60)
    m = V.match_quote(quote, page)
    assert m.status == "UNVERIFIABLE"
    assert m.mode == V.MATCH_OVERLAP_ONLY


def test_only_containment_modes_certify():
    """The list is the contract. Adding a mode to it is a decision to certify on
    something other than containment, and it belongs in a commit message."""
    assert V.CERTIFYING_MATCH_MODES == (V.MATCH_EXACT, V.MATCH_NO_WHITESPACE)
    for mode in (V.MATCH_OVERLAP_ONLY, V.MATCH_NUMERIC_MISMATCH, V.MATCH_ABSENT,
                 V.MATCH_UNREADABLE):
        assert mode not in V.CERTIFYING_MATCH_MODES


def test_normalisation_folds_encoding_and_never_folds_content():
    assert V.normalize_for_match("&#36;3,619&#160;million") == "$3,619 million"
    assert V.normalize_for_match("\u201cquoted\u201d \u2013 dash") == '"quoted" - dash'
    assert V.normalize_for_match("soft\u00adhyphen") == "softhyphen"
    # Content is untouched: different figures stay different after normalising.
    assert V.normalize_for_match("$49.1 trillion") != V.normalize_for_match(
        "$47.6 trillion")


def test_unescaping_stops_at_two_passes():
    """Unescaping to a fixed point would let a page containing the literal text
    `&amp;` match a quote containing `&` - folding content, not encoding."""
    assert V.normalize_for_match("&amp;amp;lt;") == "&lt;"


def test_verify_all_reports_how_each_quote_matched(tmp_path, monkeypatch):
    """The strength of VERIFIED_LOCAL has to be readable without re-running an audit."""
    store = ExternalStore(tmp_path / "t.duckdb")
    store.insert_claims([
        Claim(claim_id="c_00000000000a", field="f", text="t",
              source_url="https://ok.example/1", quote="the exact words"),
        Claim(claim_id="c_00000000000b", field="f", text="t",
              source_url="https://ok.example/2", quote="wholly unrelated sentence"),
    ], request_id="r")
    pages = {"1": "padding " * 80 + "the exact words" + " padding" * 80,
             "2": "padding " * 80 + "a page about municipal water" + " padding" * 80}
    monkeypatch.setattr(V, "fetch", lambda url, refetch=False: V.Fetched(
        url, True, pages[url[-1]]))
    res = V.verify_all(store=store, apply=True)
    assert res["modes"][V.MATCH_EXACT] == 1
    assert res["exact_containment_rate"] == 0.5
    with store.connect() as con:
        got = dict(con.execute(
            "SELECT claim_id, match_mode FROM external_claim").fetchall())
    assert got["c_00000000000a"] == V.MATCH_EXACT
    assert got["c_00000000000b"] in (V.MATCH_ABSENT, V.MATCH_NUMERIC_MISMATCH)


# ------------------------------------------------- the restatement is DRY first
def test_restate_writes_nothing_without_apply(tmp_path, monkeypatch):
    """A normalisation that silently re-labels thousands of claims is the DSR-unit-bug
    class of change. The dry run must be provably inert."""
    store = ExternalStore(tmp_path / "t.duckdb")
    store.insert_claims([Claim(
        claim_id="c_00000000000a", field="f", text="t",
        source_url="https://ok.example/1", verify_status="VERIFIED_LOCAL",
        quote="agreements penalize customers that route transactions")], request_id="r")
    page = ("padding " * 80 + "agreements penalize customers who route transactions"
            + " padding" * 80)
    monkeypatch.setattr(V, "cached_page",
                        lambda url: V.Fetched(url, True, page, from_cache=True))
    before = store.verify_rates()
    res = V.restate_corpus(store=store, report_path=tmp_path / "r.json")
    assert res["applied"] is False
    assert res["transitions"] == {"VERIFIED_LOCAL->UNVERIFIABLE": 1}
    assert len(res["moved"]) == 1 and res["moved"][0]["mode"] == V.MATCH_OVERLAP_ONLY
    assert store.verify_rates() == before, "the DRY run wrote to the store"
    assert (tmp_path / "r.json").exists()


def test_restate_leaves_a_claim_alone_when_its_page_is_not_cached(tmp_path, monkeypatch):
    """`we did not look` is not `we looked and it was not there`. An uncached page must
    never cost a claim its status - the same rule as the 403."""
    store = ExternalStore(tmp_path / "t.duckdb")
    store.insert_claims([Claim(
        claim_id="c_00000000000a", field="f", text="t",
        source_url="https://gone.example/1", quote="a quote",
        verify_status="VERIFIED_LOCAL")], request_id="r")
    monkeypatch.setattr(V, "cached_page",
                        lambda url: V.Fetched(url, False, error="not_cached"))
    res = V.restate_corpus(store=store, apply=True, report_path=tmp_path / "r.json")
    assert res["skipped"] == {"no_cached_page": 1}
    assert res["transitions"] == {}
    assert store.verify_rates() == {"VERIFIED_LOCAL": 1}


def test_apply_updates_refuses_to_report_a_write_it_cannot_read_back(tmp_path):
    """134 of 212 updates once landed before a lock error and neither session could see
    it. A bulk write that cannot be read back must raise, not return a count."""
    store = ExternalStore(tmp_path / "t.duckdb")
    store.insert_claims([Claim(claim_id="c_00000000000a", field="f", text="t",
                               source_url="https://x/1", quote="q")], request_id="r")
    ok = V.apply_updates(store, [("c_00000000000a", "UNVERIFIABLE", 0.5, "r",
                                  V.MATCH_ABSENT)])
    assert ok == {"written": 1, "verified_in_store": 1}
    with pytest.raises(RuntimeError, match="read-back disagrees"):
        V.apply_updates(store, [("c_does_not_exist", "UNVERIFIABLE", 0.5, "r",
                                 V.MATCH_ABSENT)])


# ------------------------------- the extractor that quietly stopped decoding entities
def test_an_inline_xbrl_document_with_an_xml_declaration_still_decodes_entities():
    """`lxml.html.fromstring` REFUSES a str carrying an encoding declaration:

        ValueError: Unicode strings with encoding declaration are not supported.

    Every modern EDGAR primary document is inline XBRL and opens with one. The raise was
    caught by a bare except and the regex tag-stripper ran instead - which does not decode
    entities - so every 10-K and 10-Q in the corpus kept `&#149;` and `&#160;` as literal
    text. That is a large part of the 39.3% fallback rate on sec.gov HTML. Found on POR's
    rate-case quote, where the same document extracted two different ways depending on
    whether it was read on its own or out of its accession."""
    raw = (b'<?xml version="1.0" encoding="UTF-8"?>'
           b'<html><body><p>a rate base of &#36;8.6&#160;billion&#149; and more</p>'
           b'</body></html>')
    text = V.extract_text(raw, "https://www.sec.gov/Archives/edgar/x-20260630.htm")
    assert "&#" not in text, "the entity survived extraction"
    assert "8.6" in text


def test_a_cp1252_bullet_matches_its_own_numeric_reference():
    """`html.unescape` applies the HTML5 cp1252 table to numeric references, so `&#149;`
    becomes U+2022 while a raw \x95 in a stored quote stays U+0095. Same character, two
    encodings, and the comparison disagreed about it."""
    assert V.normalize_for_match("&#149; a rate base") == V.normalize_for_match(
        "\x95 a rate base")
    assert V.match_quote("\x95 a return on equity of 9.75%",
                         "padding " * 80 + "&#149; a return on equity of 9.75%"
                         + " padding" * 80).mode == V.MATCH_EXACT


def test_the_regex_fallback_unescapes_too(monkeypatch):
    """A parser failure must cost STRUCTURE, not vocabulary. The old fallback silently
    changed what the page appeared to SAY, which is worse than losing its shape."""
    def boom(*a, **k):
        raise ValueError("parser exploded")

    monkeypatch.setattr("lxml.html.fromstring", boom)
    text = V._html_to_text(b"<html><body>a total of &#36;3,619&#160;million</body></html>")
    assert "$3,619" in text and "&#" not in text
