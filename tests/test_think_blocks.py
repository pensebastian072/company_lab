"""Reasoning-model output, found before the E07 arm burned an hour producing garbage.

qwen3 emits a <think> block ahead of its answer and that block routinely contains
braces. `extract_json` greedy-matches from the first `{` to the last `}`, so without
stripping it the parse starts INSIDE the reasoning.
"""
from __future__ import annotations

from clab.qual.scorer import extract_json, parse_bq


def test_a_think_block_containing_braces_does_not_capture_the_parse():
    raw = ('<think>Maybe I should answer {"score": 9} but that is out of range, '
           'let me reconsider the moat.</think>\n'
           '{"dimensions": {"brand": {"score": 3, "rationale": "strong"}}}')
    got = extract_json(raw)
    assert got is not None
    assert "dimensions" in got
    assert got["dimensions"]["brand"]["score"] == 3


def test_the_reasoning_never_leaks_into_a_score():
    raw = ('<think>{"brand": {"score": 4}}</think>'
           '{"dimensions": {"brand": {"score": 1, "rationale": "commodity"}}}')
    parsed = parse_bq(raw, "brand commodity pack text")
    assert parsed["parse_ok"]
    assert parsed["dimensions"]["brand"]["score"] == 1      # the ANSWER, not the thought


def test_an_unterminated_think_block_yields_no_json_rather_than_the_reasoning():
    """A response that is all reasoning has no answer. NO_DATA, never a salvaged score."""
    raw = '<think>I am still thinking about {"score": 2} and never finished'
    assert extract_json(raw) is None


def test_a_normal_response_is_untouched():
    raw = '{"dimensions": {"brand": {"score": 2, "rationale": "ok"}}}'
    assert extract_json(raw)["dimensions"]["brand"]["score"] == 2


def test_case_and_whitespace_variants_are_stripped():
    raw = '<THINK>\nnoise {1}\n</THINK>\n{"a": 1}'
    assert extract_json(raw) == {"a": 1}


def test_a_think_block_after_the_json_still_parses():
    raw = '{"a": 1}\n<think>on reflection {2}</think>'
    assert extract_json(raw) == {"a": 1}


def test_an_UNPAIRED_closing_think_tag_is_stripped():
    """LFM2.5-2.6B-Finance reasons in plain prose and then emits `</think>` with no
    opening tag. Measured on its first smoke test 2026-08-26:
    `The user wants me to...</think>{"ok": true}`.

    Neither paired-tag branch fires on that shape, so the prose stayed in front of the
    JSON - and the extractor's greedy brace match starts at the FIRST brace, so any brace
    inside the reasoning swallows the answer and reads as a parse failure. That is how a
    format quirk gets measured as bad judgement.
    """
    raw = ('The user wants me to return a specific JSON format. I should provide '
           'exactly what was asked for.</think>{"ok": true}')
    assert extract_json(raw) == {"ok": True}


def test_an_unpaired_closing_tag_whose_reasoning_CONTAINS_braces():
    """The case that would actually have broken it - the docstring notes braces in
    reasoning are routine, and a scoring prompt invites them."""
    raw = ('Maybe {"score": 3}? No, I think 4 is better.</think>'
           '{"brand": {"score": 4, "rationale": "x"}}')
    out = extract_json(raw)
    assert out is not None and "brand" in out
    assert out["brand"]["score"] == 4


def test_a_normal_response_with_no_tags_is_untouched():
    assert extract_json('{"ok": true}') == {"ok": True}


def test_a_closing_tag_INSIDE_the_json_does_not_delete_the_answer():
    """The repair above, turned on its own answer.

    Measured 2026-08-31: every parse failure in the v2 lane was this shape. A
    schema-constrained model wrote the literal characters `</think>` inside a rationale,
    mid-quote, in JSON that `json.loads` accepts as it stands - and the unpaired-tag
    branch rewrote `^.*?</think>` to a space, deleting everything before it. Five whole
    judged components were lost that way (KGS, R, PLMR on SG; AIZ, NWSA on BQ), which
    read downstream as the model declining to answer.

    A defensive repair that fires on valid input is not defensive.
    """
    raw = ('{"tam_expanding": {"score": 4, "rationale": "strength of our customer '
           'relationships and contract structur</think>"}, '
           '"secular_not_cyclical": {"score": 3, "rationale": "ok"}}')
    out = extract_json(raw)
    assert out is not None
    assert out["tam_expanding"]["score"] == 4
    assert out["secular_not_cyclical"]["score"] == 3


def test_valid_json_is_returned_before_any_repair_runs():
    """No salvage step gets a chance to touch a response that already parses."""
    raw = '{"a": {"b": "text with <think> and </think> in it"}}'
    assert extract_json(raw) == {"a": {"b": "text with <think> and </think> in it"}}
