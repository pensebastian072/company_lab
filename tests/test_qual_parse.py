"""JSON extraction and the two model pathologies observed on a real 500-company run.

Both fixtures below are the actual shapes qwen2.5:7b produced, not invented ones.
Repairs are conservative: they recover structure the model clearly intended and
never invent a score.
"""
from __future__ import annotations

from clab.qual import scorer
from clab.scoring import rubric


# ------------------------------------------------------------------ extraction
def test_plain_object():
    assert scorer.extract_json('{"a": 1}') == {"a": 1}


def test_survives_prose_and_code_fences():
    raw = 'Here is my analysis.\n```json\n{"a": 1}\n```\nHope that helps.'
    assert scorer.extract_json(raw) == {"a": 1}


def test_survives_trailing_comma():
    assert scorer.extract_json('{"a": 1,\n}') == {"a": 1}


def test_no_json_at_all():
    assert scorer.extract_json("I cannot answer that.") is None
    assert scorer.extract_json("") is None


def test_non_object_json_rejected():
    assert scorer.extract_json("[1, 2, 3]") is None


# ------------------------------------------------------------------ pathology 1: UNP
UNP_SHAPE = '''{
  "dimensions": {
    "brand": {"score": 3, "rationale": "Strong brand recognition in rail."},
    "regulatory_barriers": {"score": 4, null: "Significant regulatory hurdles."},
    "economies_of_scale": {"score": 5, "rationale": "Significant scale."}
  },
  "killer_answer": "Scale and network density.",
  "summary": "Wide moat."
}'''


def test_bare_null_key_is_dropped_and_the_score_survives():
    """Observed on UNP: a bare `null` where the key should be. The score in that
    object is unambiguous, so it is kept and only the uninterpretable pair goes."""
    out = scorer.extract_json(UNP_SHAPE)
    assert out is not None
    dims = out["dimensions"]
    assert dims["regulatory_barriers"]["score"] == 4
    assert "rationale" not in dims["regulatory_barriers"]
    assert dims["brand"]["score"] == 3
    assert dims["economies_of_scale"]["score"] == 5
    assert out["killer_answer"] == "Scale and network density."


def test_bare_null_key_flows_through_the_bq_parser():
    parsed = scorer.parse_bq(UNP_SHAPE, "")
    assert parsed["parse_ok"]
    assert parsed["dimensions"]["regulatory_barriers"]["score"] == 4
    assert parsed["dimensions"]["brand"]["score"] == 3


# ------------------------------------------------------------------ pathology 2: QCOM
QCOM_SHAPE = ('{"tam_expanding": {"score": 3, "rationale": "On-device AI.", '
              '"evidence": "on-device artificial intelligence"}},\n'
              '{"revenue_growth_sustainable": {"score": 2, "rationale": "Mixed."}},\n'
              '{"secular_not_cyclical": {"score": 1, "rationale": "Handset cycle."}}')


def test_sibling_objects_are_merged():
    """Observed on QCOM: the model closed the object after each sub-test and opened
    a new one, so the response is a comma-separated sequence rather than one object."""
    out = scorer.extract_json(QCOM_SHAPE)
    assert out is not None
    assert out["tam_expanding"]["score"] == 3
    assert out["revenue_growth_sustainable"]["score"] == 2
    assert out["secular_not_cyclical"]["score"] == 1


def test_sibling_objects_flow_through_the_sg_parser():
    parsed = scorer.parse_sg(QCOM_SHAPE, "on-device artificial intelligence drives it")
    assert parsed["parse_ok"]
    assert parsed["scores"]["tam_expanding"]["score"] == 3
    assert parsed["scores"]["secular_not_cyclical"]["score"] == 1


def test_sibling_objects_separated_by_newline_only():
    """Measured on SYY: same pathology as QCOM but with no comma between objects."""
    blob = ('{"tam_expanding": {"score": 3, "evidence": "we serve about 17%"}}\n'
            '{"revenue_growth_sustainable": {"score": 4}}\n'
            '{"secular_not_cyclical": {"score": 2}}')
    out = scorer.extract_json(blob)
    assert out is not None
    assert out["tam_expanding"]["score"] == 3
    assert out["revenue_growth_sustainable"]["score"] == 4
    assert out["secular_not_cyclical"]["score"] == 2


def test_nested_repeated_keys_merge_rather_than_overwrite():
    blob = ('{"dimensions": {"brand": {"score": 1}}},'
            '{"dimensions": {"network_effects": {"score": 2}}}')
    out = scorer.extract_json(blob)
    assert out["dimensions"]["brand"]["score"] == 1
    assert out["dimensions"]["network_effects"]["score"] == 2


# ------------------------------------------------------------------ pathology 3: ITW / UPS
def test_unescaped_quotes_inside_evidence_are_escaped():
    """The commonest failure by far. The model copies a verbatim filing quote that
    itself contains quotation marks - measured on ITW and UPS."""
    blob = ('{"tam_expanding": {"score": 3, "rationale": "Innovation focus.", '
            '"evidence": "Customer-back Innovation ("CBI") is the most impactful driver"}}')
    out = scorer.extract_json(blob)
    assert out is not None
    assert out["tam_expanding"]["score"] == 3
    assert "CBI" in out["tam_expanding"]["evidence"]


def test_multiple_inner_quote_pairs():
    blob = ('{"a": {"evidence": "we acquired Foo ("Foo") and Bar ("Bar") in 2025", '
            '"score": 1}}')
    out = scorer.extract_json(blob)
    assert out["a"]["score"] == 1
    assert out["a"]["evidence"].count('"') == 4


def test_already_escaped_quotes_are_not_double_escaped():
    blob = '{"a": {"evidence": "he said \\"hello\\" once", "score": 2}}'
    out = scorer.extract_json(blob)
    assert out["a"]["evidence"] == 'he said "hello" once'


# ------------------------------------------------------------------ pathology 4: DIS
def test_truncated_response_keeps_the_completed_subtests():
    """Measured on DIS: the reply hit the token cap mid-string. Sub-tests already
    finished are kept; the truncated one becomes NO_DATA, which is honest."""
    blob = ('{"tam_expanding": {"score": 2, "rationale": "Parks growth."},\n'
            ' "secular_not_cyclical": {"score": 1, "rationale": "these metrics are useful')
    out = scorer.extract_json(blob)
    assert out is not None
    assert out["tam_expanding"]["score"] == 2


def test_truncation_does_not_fabricate_the_lost_subtest():
    blob = '{"tam_expanding": {"score": 2}, "secular_not_cyclical": {"score'
    parsed = scorer.parse_sg(blob, "")
    assert parsed["scores"]["tam_expanding"]["score"] == 2
    assert parsed["scores"].get("secular_not_cyclical", {}).get("score") is None


# ------------------------------------------------------------------ pathology 5: PYPL
def test_stray_paren_after_a_closing_brace():
    """Measured on PYPL: `...36 % ** **"}),` - a spurious paren between objects."""
    blob = ('{"tam_expanding": {"score": 3, "evidence": "Percent of TPV 37 %"}),\n'
            ' "secular_not_cyclical": {"score": 2}}')
    out = scorer.extract_json(blob)
    assert out is not None
    assert out["tam_expanding"]["score"] == 3
    assert out["secular_not_cyclical"]["score"] == 2


def test_parens_inside_quoted_text_survive():
    blob = '{"a": {"score": 1, "rationale": "revenue (excluding FX) rose"}}'
    out = scorer.extract_json(blob)
    assert out["a"]["rationale"] == "revenue (excluding FX) rose"


# ------------------------------------------------------------------ repairs stay honest
def test_repairs_never_invent_a_score():
    out = scorer.extract_json('{"tam_expanding": {null: "no score here"}}')
    assert out is not None
    assert out["tam_expanding"] == {}
    parsed = scorer.parse_sg('{"tam_expanding": {null: "no score"}}', "")
    assert parsed["scores"]["tam_expanding"]["score"] is None


def test_out_of_range_still_rejected_after_a_repair():
    blob = '{"tam_expanding": {"score": 99, null: "x"}}'
    parsed = scorer.parse_sg(blob, "")
    st = parsed["scores"]["tam_expanding"]
    assert st["score"] is None
    assert st["rejected_value"] == 99


def test_float_still_rejected_after_a_repair():
    parsed = scorer.parse_sg('{"tam_expanding": {"score": 2.5, null: "x"}}', "")
    assert parsed["scores"]["tam_expanding"]["score"] is None


def test_string_integers_are_accepted():
    parsed = scorer.parse_sg('{"tam_expanding": {"score": "3"}}', "")
    assert parsed["scores"]["tam_expanding"]["score"] == 3


# ------------------------------------------------------------------ cache key stability
def test_stable_key_ignores_daily_market_noise():
    """The bug this prevents: the old key hashed the RENDERED pack, which embeds
    price, market cap and P/E. The yfinance cache is date-partitioned, so at UTC
    midnight every key changed and a resume re-scored the entire universe."""
    a = scorer.stable_key("SG", cik="0000320193", accn="0000320193-26-000020",
                          data_through="2026-06-27")
    b = scorer.stable_key("SG", cik="0000320193", accn="0000320193-26-000020",
                          data_through="2026-06-27")
    assert a == b


def test_stable_key_changes_on_a_new_filing():
    base = dict(cik="0000320193", data_through="2026-06-27")
    assert scorer.stable_key("SG", accn="acc-1", **base) != \
        scorer.stable_key("SG", accn="acc-2", **base)


def test_stable_key_changes_on_new_fundamentals():
    base = dict(cik="0000320193", accn="acc-1")
    assert scorer.stable_key("SG", data_through="2026-06-27", **base) != \
        scorer.stable_key("SG", data_through="2026-09-27", **base)


def test_stable_key_differs_per_component_and_company():
    base = dict(accn="acc-1", data_through="2026-06-27")
    assert scorer.stable_key("SG", cik="1", **base) != \
        scorer.stable_key("BQ", cik="1", **base)
    assert scorer.stable_key("SG", cik="1", **base) != \
        scorer.stable_key("SG", cik="2", **base)


def test_stable_key_survives_missing_metadata():
    k = scorer.stable_key("SG", cik="1", accn=None, data_through=None)
    assert isinstance(k, str) and len(k) == 40


# ------------------------------------------------------------------ evidence check
def test_quoted_evidence_must_overlap_the_pack():
    pack = "The Company designs and markets smartphones and wearable devices."
    good = scorer.parse_sg(
        '{"tam_expanding": {"score": 2, "evidence": "designs and markets smartphones"}}',
        pack)
    assert good["scores"]["tam_expanding"]["evidence_unverified"] is False

    bad = scorer.parse_sg(
        '{"tam_expanding": {"score": 2, "evidence": "quantum blockchain fusion reactors"}}',
        pack)
    assert bad["scores"]["tam_expanding"]["evidence_unverified"] is True
    assert bad["scores"]["tam_expanding"]["score"] == 2   # kept, but flagged


def test_mg_takes_nothing_at_all_from_the_model():
    """E25 removed the five model-scored CEO attributes; the block is fully measured.

    E24 first tested the obvious excuse - that founder_led, tenure and ownership are DEF
    14A facts and the pack held only the 10-K. Putting the proxy in fixed AVAILABILITY
    (ownership 4 -> 163 companies scored) and not RELIABILITY: tenure, a fact that
    increments by one a year, round-tripped at kappa 0.29.
    """
    blob = ('{"ceo": {"founder_led": {"score": 1}, "tenure": {"score": 2}, '
            '"hits_guidance": {"score": 2}, "navigated_downturns": {"score": 2}}}')
    parsed = scorer.parse_mg(blob, "")
    assert parsed["ceo"] == {}


def test_parse_failure_is_reported_not_hidden():
    for parser in (scorer.parse_sg, scorer.parse_bq, scorer.parse_mg):
        out = parser("the model refused to answer", "")
        assert out["parse_ok"] is False


def test_every_sg_subtest_key_is_recognised():
    fields = ", ".join(f'"{k}": {{"score": 0}}' for k, _l, _m in rubric.SG_SUBTESTS)
    parsed = scorer.parse_sg("{" + fields + "}", "")
    assert set(parsed["scores"]) == {k for k, _l, _m in rubric.SG_SUBTESTS}
