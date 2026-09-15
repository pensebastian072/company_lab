"""E07's bake-off harness.

The property worth a test above all others: **the harness must never write into the
production qual cache.** A candidate model's scores landing in `config.QUAL_DIR` would
be unrecoverable without re-scoring the whole universe, and nothing in the output would
look wrong.
"""
from __future__ import annotations

import pytest

from clab import config
from clab.qual import bakeoff


# --------------------------------------------------------- the safety property
def test_the_harness_writes_nowhere_near_the_production_cache():
    assert bakeoff.BAKEOFF_DIR != config.QUAL_DIR
    assert config.QUAL_DIR not in bakeoff.BAKEOFF_DIR.parents
    assert bakeoff.BAKEOFF_DIR.name != config.QUAL_DIR.name


def test_QUAL_DIR_is_never_referenced_in_EXECUTABLE_code():
    """AST, not grep. A docstring may describe the rule; no code may reach the cache.

    A text search fails on this module's own docstring, which explains the rule - and a
    test that trips over prose gets weakened until it stops catching anything.
    """
    import ast
    import inspect
    tree = ast.parse(inspect.getsource(bakeoff))
    hits = [n for n in ast.walk(tree)
            if isinstance(n, ast.Attribute) and n.attr == "QUAL_DIR"]
    assert not hits, f"bakeoff reaches config.QUAL_DIR at line(s) {[n.lineno for n in hits]}"


def test_the_scorer_cache_writers_are_not_imported():
    """cache_path/stable_key are how a score reaches the production cache."""
    import inspect
    src = inspect.getsource(bakeoff)
    import_lines = [ln for ln in src.splitlines()
                    if ln.startswith(("from ", "import "))]
    joined = " ".join(import_lines)
    assert "cache_path" not in joined
    assert "stable_key" not in joined
    assert "score_company" not in joined


# ------------------------------------------------------------ model resolution
def test_a_family_match_is_not_an_install():
    """qwen2.5:7b being present does NOT mean qwen2.5:14b-... is present.

    The first cut compared `name.split(':')[0]`, which reported the 14B as installed
    because the 7B was, and would have walked into a multi-GB pull it had just said was
    unnecessary.
    """
    have = {bakeoff._norm_model(i) for i in ["qwen2.5:7b", "nomic-embed-text:latest"]}
    assert bakeoff._norm_model("qwen2.5:14b-instruct-q4_K_M") not in have
    assert bakeoff._norm_model("qwen2.5:7b") in have


def test_a_bare_name_means_latest():
    assert bakeoff._norm_model("gemma4") == "gemma4:latest"
    assert bakeoff._norm_model("qwen2.5:7b") == "qwen2.5:7b"


def test_installed_models_degrades_to_empty_not_an_exception(monkeypatch):
    monkeypatch.setattr(config, "OLLAMA_URL", "http://127.0.0.1:1")   # nothing listening
    assert bakeoff.installed_models() == []


# ------------------------------------------------------------------ the metrics
def _summary(scores, **kw):
    m = {"scores": scores, "elapsed_s": kw.get("elapsed", [10.0]),
         "generations": kw.get("generations", 1),
         "parse_failures": kw.get("parse_failures", 0),
         "unverified_flagged": kw.get("uf", 0), "unverified_total": kw.get("ut", 0),
         "nulls": kw.get("nulls", 0), "score_slots": kw.get("slots", 0),
         "bq_null_by_dimension": kw.get("bq_null", {}),
         "bq_seen_by_dimension": kw.get("bq_seen", {}), "load_error": None}
    return bakeoff._summarise(m)


def test_M1_measures_the_spread_across_repeats():
    s = _summary({"AAA|SG|growth": [4, 4, 4], "AAA|BQ|brand": [1, 3, 2]})
    assert s["M1_mean_spread"] == pytest.approx(1.0)      # (0 + 2) / 2
    assert s["M1_max_spread"] == 2
    assert s["M1_share_unstable"] == pytest.approx(0.5)


def test_M1_ignores_a_slot_that_only_answered_once():
    """One usable answer has no spread. Counting it as 0 would flatter a model that
    abstained on everything it was unsure about."""
    s = _summary({"AAA|SG|growth": [4, None, None]})
    assert s["M1_mean_spread"] is None


def test_a_perfectly_consistent_model_scores_zero_spread():
    s = _summary({"AAA|SG|growth": [3, 3, 3], "AAA|BQ|brand": [2, 2, 2]})
    assert s["M1_mean_spread"] == 0.0
    assert s["M1_share_unstable"] == 0.0


def test_E12_abstention_is_reported_per_dimension():
    s = _summary({}, bq_seen={"network_effects": 10, "brand": 10},
                 bq_null={"network_effects": 8, "brand": 1})
    assert s["E12_bq_null_by_dimension"]["network_effects"] == 0.8
    assert s["E12_bq_null_by_dimension"]["brand"] == 0.1


# ------------------------------------------------------------------ the verdicts
def _res(inc, cand):
    return {"incumbent": "inc", "models": {"inc": inc, "cand": cand}}


def test_an_unmeasured_metric_is_NOT_MEASURED_and_never_FAIL():
    """A 1-repeat smoke run cannot produce an M1 spread at all.

    The first cut returned False for a None comparison, so every candidate printed
    `M1_no_worse_consistency: FAIL` for consistency it had never been tested for -
    a missing measurement rendered as a verdict.
    """
    out = _res({"M1_mean_spread": None, "M2_parse_failure_rate": 0.0,
                "M3_unverified_rate": 0.0, "M5_projected_hours_for_1500": 20},
               {"M1_mean_spread": None, "M2_parse_failure_rate": 0.0,
                "M3_unverified_rate": 0.0, "M5_projected_hours_for_1500": 76})
    bakeoff._compare(out)
    c = out["models"]["cand"]["criteria"]
    assert c["M1_no_worse_consistency"] is None
    assert c["M5_under_24h_rescore"] is False          # measured, and it failed
    assert out["models"]["cand"]["verdict"].startswith("INCOMPLETE")
    assert "M1_no_worse_consistency" in out["models"]["cand"]["verdict"]


def test_the_rendered_report_says_NOT_MEASURED():
    out = _res({"M1_mean_spread": None, "M2_parse_failure_rate": 0.0,
                "M3_unverified_rate": 0.0, "M5_projected_hours_for_1500": 20},
               {"M1_mean_spread": None, "M2_parse_failure_rate": 0.0,
                "M3_unverified_rate": 0.0, "M5_projected_hours_for_1500": 76})
    bakeoff._compare(out)
    out.update({"as_of": "x", "preregistration": "p", "sample": ["A"], "repeats": 1})
    md = bakeoff.render(out)
    assert "NOT MEASURED" in md


def test_a_fully_measured_failure_is_still_REJECTED():
    out = _res({"M1_mean_spread": 1.0, "M2_parse_failure_rate": 0.0,
                "M3_unverified_rate": 0.0, "M5_projected_hours_for_1500": 20},
               {"M1_mean_spread": 1.0, "M2_parse_failure_rate": 0.0,
                "M3_unverified_rate": 0.0, "M5_projected_hours_for_1500": 76})
    bakeoff._compare(out)
    assert out["models"]["cand"]["verdict"] == "REJECTED"


def test_a_less_consistent_model_is_rejected_however_fast_it_is():
    out = _res({"M1_mean_spread": 1.0, "M2_parse_failure_rate": 0.0,
                "M3_unverified_rate": 0.1, "M5_projected_hours_for_1500": 20},
               {"M1_mean_spread": 2.0, "M2_parse_failure_rate": 0.0,
                "M3_unverified_rate": 0.1, "M5_projected_hours_for_1500": 2})
    bakeoff._compare(out)
    assert out["models"]["cand"]["verdict"] == "REJECTED"
    assert out["models"]["cand"]["criteria"]["M1_no_worse_consistency"] is False


def test_a_model_that_wins_everything_is_only_a_CANDIDATE():
    """Never 'adopt'. The qual half has no forward-return validation, so 'better' is
    not a thing this harness can measure."""
    out = _res({"M1_mean_spread": 2.0, "M2_parse_failure_rate": 0.05,
                "M3_unverified_rate": 0.2, "M5_projected_hours_for_1500": 20},
               {"M1_mean_spread": 1.0, "M2_parse_failure_rate": 0.0,
                "M3_unverified_rate": 0.1, "M5_projected_hours_for_1500": 8})
    bakeoff._compare(out)
    assert out["models"]["cand"]["verdict"] == "CANDIDATE"
    assert out["promoted"] is False


def test_a_model_that_will_not_load_is_a_result_not_a_retry():
    out = _res({"M1_mean_spread": 1.0}, {"load_error": "OllamaUnavailable: no such model"})
    bakeoff._compare(out)
    assert "would not load" in out["models"]["cand"]["verdict"]


def test_a_rescore_over_24h_fails_M5():
    out = _res({"M1_mean_spread": 1.0, "M2_parse_failure_rate": 0.0,
                "M3_unverified_rate": 0.1, "M5_projected_hours_for_1500": 11},
               {"M1_mean_spread": 0.5, "M2_parse_failure_rate": 0.0,
                "M3_unverified_rate": 0.1, "M5_projected_hours_for_1500": 40})
    bakeoff._compare(out)
    assert out["models"]["cand"]["criteria"]["M5_under_24h_rescore"] is False
    assert out["models"]["cand"]["verdict"] == "REJECTED"
