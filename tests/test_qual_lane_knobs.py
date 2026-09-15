"""The three env knobs that let a SECOND lane run a different model side by side.

Every one of them must default to the production lane's existing behaviour, because the
whole claim of the v2 lane is "identical except the model". A knob that changes something
when unset would make that claim false and nobody would notice.

See `docs/V2_LFM25_RUNBOOK.md`.
"""
from __future__ import annotations

import importlib

import pytest

from clab import config
from clab.qual import prompts
from clab.scoring import rubric


def _reload_config(monkeypatch, **env):
    """Re-import config with a patched environment and hand back the fresh module."""
    for k, v in env.items():
        if v is None:
            monkeypatch.delenv(k, raising=False)
        else:
            monkeypatch.setenv(k, v)
    return importlib.reload(config)


@pytest.fixture(autouse=True)
def _restore_config():
    """Always put the real module back, however the test ends."""
    yield
    importlib.reload(config)


# ------------------------------------------------------------------ defaults
def test_unset_knobs_are_exactly_the_production_lane(monkeypatch):
    cfg = _reload_config(monkeypatch, CLAB_QUAL_DIR=None,
                         CLAB_QUAL_NUM_PREDICT=None, CLAB_QUAL_STRUCTURED=None)
    assert cfg.QUAL_NUM_PREDICT == 700
    assert cfg.QUAL_STRUCTURED is False
    assert cfg.QUAL_DIR == cfg.DATA_ROOT / "qual"


def test_structured_is_on_only_for_the_exact_string_1(monkeypatch):
    """A truthy-string bug here would silently schema-constrain the production lane."""
    for value in ("", "0", "false", "no", "True"):
        cfg = _reload_config(monkeypatch, CLAB_QUAL_STRUCTURED=value)
        assert cfg.QUAL_STRUCTURED is False, value
    assert _reload_config(monkeypatch, CLAB_QUAL_STRUCTURED="1").QUAL_STRUCTURED is True


# ------------------------------------------------------------------ overrides
def test_a_lane_can_take_its_own_qual_dir(monkeypatch, tmp_path):
    """B2: `fold_qual` globs `{cik}_{component}_*.json`, which matches every model's
    payload for that CIK. The cache KEY carries the model so nothing is overwritten, but
    the fold's staleness question is model-blind - so a second lane needs its own
    directory, not just its own key."""
    lane = tmp_path / "qual_lfm25"
    cfg = _reload_config(monkeypatch, CLAB_QUAL_DIR=str(lane))
    assert cfg.QUAL_DIR == lane
    assert cfg.QUAL_DIR != cfg.DATA_ROOT / "qual"


def test_the_token_budget_is_raisable(monkeypatch):
    """B3: 700 truncated LFM2.5 mid-reasoning and the harness read it as a parse
    failure. The point of the knob is that a lane raises it for EVERY arm at once."""
    assert _reload_config(monkeypatch, CLAB_QUAL_NUM_PREDICT="2500").QUAL_NUM_PREDICT == 2500


# ------------------------------------------------------------------ scorer wiring
def test_the_scorer_sends_no_schema_when_structured_is_off(monkeypatch):
    """B4 defaults: production must keep sending an unconstrained request."""
    from clab.qual import ollama
    seen = {}

    def fake_post(path, payload, timeout=None):
        seen.update(payload)
        return {"response": "{}"}

    monkeypatch.setattr(ollama, "_post", fake_post)
    monkeypatch.setattr(config, "QUAL_STRUCTURED", False)
    ollama.chat("hi", system="s", fmt=None)
    assert "format" not in seen
    assert seen["options"]["num_predict"] == config.QUAL_NUM_PREDICT


def test_a_schema_reaches_ollama_as_format_when_asked(monkeypatch):
    from clab.qual import ollama
    seen = {}

    def fake_post(path, payload, timeout=None):
        seen.update(payload)
        return {"response": "{}"}

    monkeypatch.setattr(ollama, "_post", fake_post)
    ollama.chat("hi", system="s", fmt=prompts.schema_for("BQ"))
    assert seen["format"]["type"] == "object"
    assert "dimensions" in seen["format"]["properties"]


# ------------------------------------------------------------------ the schema itself
@pytest.mark.parametrize("component", rubric.GENERATED_COMPONENTS)
def test_every_llm_component_has_a_schema(component):
    schema = prompts.schema_for(component)
    assert schema["type"] == "object" and schema["properties"]


def _scored_bucket(component: str) -> dict:
    """The object holding this component's scored items.

    SG has NO wrapper - its sub-test keys sit at the top level, because that is the shape
    `sg_prompt` asks for and the only shape `parse_sg` reads. BQ and MG are wrapped.
    """
    schema = prompts.schema_for(component)
    if component == "SG":
        return schema
    return schema["properties"][{"BQ": "dimensions", "MG": "ceo"}[component]]


@pytest.mark.parametrize("component", ("SG", "BQ"))
def test_null_stays_a_legal_score_in_every_schema(component):
    """The one property that must never be optimised away. A schema that forced an
    integer would convert every honest abstention into a fabricated number - the exact
    opposite of what this pipeline needs, and it would raise the judged half's coverage
    while lowering its truthfulness."""
    items = {n: spec for n, spec in _scored_bucket(component)["properties"].items()
             if isinstance(spec, dict) and "score" in (spec.get("properties") or {})}
    assert items, f"{component} has no scored items"
    for name, item in items.items():
        assert "null" in item["properties"]["score"]["type"], f"{component}.{name}"


def test_MG_asks_the_model_for_an_empty_object_and_that_is_not_a_bug():
    """E25 moved BOTH CEO attributes to the measured half, so MG has no LLM-sourced
    attribute left: its schema's scored bucket is empty and the generation can award no
    points at all. What MG's LLM call still produces is `ceo_summary`, a <=300-character
    rationale string (`clab/scoring/mg.py:122`).

    It cannot simply be dropped from a run, and the reason is not obvious:
    `fold_qual.stale_tickers` starts from `ciks_with_all_components()`, which requires SG,
    BQ **and** MG on disk. A lane that skipped MG would cache SG and BQ for every company,
    have all of it silently declared not-done, and fold NOTHING - the scorecards and the
    workbook would stay empty while every run reported success.

    So this test pins the shape rather than the cost. If MG ever regains an LLM attribute,
    the parametrized null test above should gain "MG" back.
    """
    assert [k for k, _lbl, src in rubric.MG_CEO_ATTRIBUTES if src == "llm"] == []
    assert _scored_bucket("MG")["properties"] == {}
    assert "ceo" in prompts.schema_for("MG")["required"]


def test_the_schema_is_generated_from_the_rubric_not_hand_written():
    """If someone adds a BQ dimension, the schema must follow it. A hand-written copy
    would drift the way the '50 of 100 points' labels drifted from the framework (E33)."""
    keys = {k for k, _label in rubric.BQ_DIMENSIONS}
    assert set(prompts.schema_for("BQ")["properties"]["dimensions"]["properties"]) == keys


# ------------------------------------------------------------------ schema <-> parser
def _instance_from(schema: dict, *, score: int = 2, quote: str = "the filed sentence"):
    """The smallest JSON instance this schema permits, with every score filled in.

    Deliberately dumb: it walks the schema rather than being hand-written, so it cannot
    silently agree with a wrong schema the way a fixture would.
    """
    out = {}
    for name, spec in schema.get("properties", {}).items():
        types = spec.get("type")
        types = types if isinstance(types, list) else [types]
        if "object" in types:
            inner = spec.get("properties") or {}
            if "score" in inner:
                out[name] = {"score": score, "rationale": "because",
                             "evidence": quote}
            else:
                out[name] = _instance_from(spec, score=score, quote=quote)
        elif "string" in types:
            out[name] = quote
    return out


@pytest.mark.parametrize("component,parser_name,bucket", [
    ("SG", "parse_sg", "scores"),
    ("BQ", "parse_bq", "dimensions"),
])
def test_the_schema_and_the_parser_agree(component, parser_name, bucket):
    """THE test this file exists for, and the one whose absence cost a probe.

    A schema is ENFORCED, not suggested: whatever envelope it names, the model emits
    exactly that. So a schema whose shape the parser does not read is not a near-miss -
    it is total, silent data loss. The first draft wrapped SG in `{"subtests": {...}}`
    while `sg_prompt` asks for a FLAT object and `parse_sg` reads `data.get(key)` with no
    fallback. AAPL's SG came back `parse_ok: true` with `scores: {}` after 26.4 s of GPU,
    and a full run would have dropped all 20 SG points for every company while reporting
    success.

    Round-tripping an instance of the schema through the real parser is the only check
    that catches it, because both halves are generated from the same rubric and will
    always look right in isolation.
    """
    import json as _json
    from clab.qual import scorer

    schema = prompts.schema_for(component)
    payload = _json.dumps(_instance_from(schema))
    parsed = getattr(scorer, parser_name)(payload, "the filed sentence appears here")

    assert parsed["parse_ok"] is True
    expected = ({s[0] for s in rubric.SG_SUBTESTS} if component == "SG"
                else {k for k, _l in rubric.BQ_DIMENSIONS})
    assert set(parsed[bucket]) == expected, f"{component}: parser saw {set(parsed[bucket])}"
    assert all(v["score"] == 2 for v in parsed[bucket].values())


def test_per_subtest_evidence_survives_the_SG_schema():
    """`evidence` must be expressible per SG sub-test or `_verify_evidence` gets None
    every time, `evidence_unverified` is False for every sub-test, and the
    unverified-evidence rate - the number the E07 prior is actually about - reads 0.0% BY
    CONSTRUCTION. A destroyed metric that looks like a pass is worse than a missing one.

    SG only: `parse_bq` and `parse_mg` read evidence once at the top level and discard a
    per-item one, so the schema deliberately does not ask for it there."""
    import json as _json
    from clab.qual import scorer

    payload = _json.dumps(_instance_from(prompts.schema_for("SG"),
                                         quote="a quote that is nowhere in the pack"))
    parsed = scorer.parse_sg(payload, "an evidence pack about something else entirely")
    flagged = [v for v in parsed["scores"].values() if v["evidence_unverified"]]
    assert flagged, "no sub-test could be flagged unverified - the check is dead"


def test_BQ_keeps_its_top_level_evidence():
    """The other half of the same rule: BQ's single top-level quote must still reach
    `_verify_evidence`, or BQ's unverified rate is the one destroyed instead."""
    import json as _json
    from clab.qual import scorer

    payload = _json.dumps(_instance_from(prompts.schema_for("BQ"),
                                         quote="a quote that is nowhere in the pack"))
    parsed = scorer.parse_bq(payload, "an evidence pack about something else entirely")
    assert parsed["evidence_unverified"] is True


# --------------------------------------------------- the payload must say which regime
def test_the_payload_records_the_generation_regime():
    """Neither knob is in the cache key, so a payload that does not carry them cannot say
    which regime produced it.

    E38 hit this: its entire claim is "same model, different format", and 253 cached
    payloads could not confirm the format was on - the only evidence was re-reading the
    env plumbing. A comparison whose inputs cannot describe themselves is one bad
    environment variable away from being a comparison of nothing.
    """
    import inspect

    from clab.qual import scorer

    src = inspect.getsource(scorer)
    assert '"structured": bool(config.QUAL_STRUCTURED)' in src
    assert '"num_predict": int(config.QUAL_NUM_PREDICT)' in src
