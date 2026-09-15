"""An outside model's scores get in only if the FILING says what they claim.

The local repair verifies a quote against the eight-chunk evidence pack. An external
reader had the whole 10-K, so its quotes are checked against the whole filing text - a
stricter question about truth, a looser one about which paragraph. Both refuse a sentence
that is not in the document.
"""
from clab.runner import ingest_external as ix

FILING = ("Our manufacturing footprint spans fourteen facilities across North America "
          "and Europe, and we operate the largest distribution network in the sector.")


def test_a_quote_that_is_in_the_filing_verifies():
    r = ix.verify_against_filing("we operate the largest distribution network in the "
                                 "sector", FILING)
    assert r["verified"] is True


def test_reflowed_whitespace_still_verifies():
    r = ix.verify_against_filing("fourteen facilities   across\n North America", FILING)
    assert r["verified"] is True


def test_an_invented_quote_is_refused():
    r = ix.verify_against_filing("we enjoy powerful network effects across our platform",
                                 FILING)
    assert r["verified"] is False


def test_a_short_quote_cannot_verify_by_accident():
    """"the" is in every filing. A three-word quote is not evidence."""
    r = ix.verify_against_filing("we operate", FILING)
    assert r["verified"] is False
    assert "shorter than" in r["why"]


def test_no_filing_on_disk_means_no_verification():
    r = ix.verify_against_filing("a perfectly reasonable sentence about scale", "")
    assert r["verified"] is False


def test_reply_survives_code_fences_and_chatter():
    blob = ('Sure! Here is the JSON:\n```json\n{"companies": [{"ticker": "AAA", '
            '"dimensions": {}}]}\n```\n')
    out = ix._extract(blob)
    assert out and out["companies"][0]["ticker"] == "AAA"


def test_an_unparseable_reply_returns_none():
    assert ix._extract("no json here at all") is None
