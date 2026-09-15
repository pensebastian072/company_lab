"""The repair pass may only fill holes, and only when it can cite the filing.

E16 recovered a dimension for half the under-floor sample; E17 showed the recovery is
much smaller once a verbatim quote is required (40 of 73 scores were offered with no
quote at all). These pin the rules that make the difference safe to ship:

  * an unquoted repair never reaches `earned`, `available` or the band;
  * a repair never overwrites what the production call scored;
  * an out-of-range repair is rejected, not clamped (hard rule 4);
  * a repaired point is labelled `repair`, never indistinguishable from a first-call one.
"""
import json

from clab.qual import repair
from clab.scoring import repair_merge


def _payload(scores=None, repairs=None, bucket="dimensions"):
    return {bucket: scores or {}, repair_merge.REPAIRS_KEY: repairs or {}}


def _rep(score=3, gate="strict", quote="a quote"):
    return {"score": score, "gate": gate, "quote": quote, "rationale": "because",
            "run_id": "repair_test", "source": "repair"}


def test_an_unquoted_repair_never_reaches_the_score():
    """The whole safety argument. E17 measured how often the model scores without a
    quote - 40 of 73 - so this is the common case, not an edge case."""
    for gate in ("no_quote", "unverified", "production", "tight"):
        payload = _payload({"brand": {"score": None}}, {"brand": _rep(gate=gate)})
        merged = repair_merge.merged_items(payload, "dimensions")
        assert merged["brand"]["score"] is None, gate


def test_a_strict_repair_fills_a_null():
    payload = _payload({"brand": {"score": None}}, {"brand": _rep()})
    merged = repair_merge.merged_items(payload, "dimensions")
    assert merged["brand"]["score"] == 3
    assert merged["brand"]["origin"] == "repair"
    assert merged["brand"]["evidence"] == "a quote"
    assert merged["brand"]["evidence_unverified"] is False


def test_a_repair_never_overwrites_a_production_score():
    payload = _payload({"brand": {"score": 1, "rationale": "first call"}},
                       {"brand": _rep(score=5)})
    merged = repair_merge.merged_items(payload, "dimensions")
    assert merged["brand"]["score"] == 1
    assert merged["brand"].get("origin") != "repair"


def test_a_missing_repairs_key_changes_nothing():
    payload = {"dimensions": {"brand": {"score": 2}}}
    assert repair_merge.merged_items(payload, "dimensions") == payload["dimensions"]


def test_out_of_range_is_rejected_not_clamped():
    items = [("brand", "Brand", 5)]
    raw = '{"brand": {"score": 9, "rationale": "r", "evidence": "the pack says brand"}}'
    reps = repair.parse_repair(raw, "the pack says brand", items, run_id="t")
    assert reps["brand"]["score"] is None
    assert reps["brand"]["rejected_value"] == 9


def test_a_quote_that_is_not_in_the_pack_is_gated_out():
    items = [("brand", "Brand", 5)]
    raw = '{"brand": {"score": 4, "rationale": "r", "evidence": "invented sentence"}}'
    reps = repair.parse_repair(raw, "an unrelated pack about turbines", items,
                               run_id="t")
    assert reps["brand"]["score"] == 4          # parsed
    assert reps["brand"]["gate"] != "strict"    # but it cannot be used
    payload = _payload({"brand": {"score": None}}, reps)
    assert repair_merge.merged_items(payload, "dimensions")["brand"]["score"] is None


def test_whitespace_differences_still_verify():
    """The model reflows a quote across lines; that is not a fabrication."""
    pack = "we operate the largest\n    distribution network in the region"
    items = [("distribution", "Distribution", 5)]
    raw = ('{"distribution": {"score": 4, "rationale": "r", '
           '"evidence": "the largest distribution network"}}')
    reps = repair.parse_repair(raw, pack, items, run_id="t")
    assert reps["distribution"]["gate"] == "strict"


def test_repaired_points_counts_points_not_subtests():
    """SG's sub-tests are worth 2-4 each; counting sub-tests would flatter SG."""
    payload = {"scores": {}, repair_merge.REPAIRS_KEY: {
        "tam_expanding": _rep(score=3),                 # 4 points
        "multiple_independent_drivers": _rep(score=1),  # 2 points
        "secular_not_cyclical": _rep(score=2, gate="no_quote"),   # 3 points, unquoted
    }}
    quoted, unquoted = repair_merge.repaired_points(payload, "SG")
    assert (quoted, unquoted) == (6, 3)


def test_null_items_lists_only_the_unscored():
    payload = {"scores": {"tam_expanding": {"score": 2},
                          "secular_not_cyclical": {"score": None}}}
    keys = [k for k, _l, _m in repair_merge.null_items(payload, "SG")]
    assert "tam_expanding" not in keys
    assert "secular_not_cyclical" in keys
    # a sub-test the payload never mentions is null too, not absent
    assert "revenue_growth_sustainable" in keys


def test_every_component_has_a_query_for_every_subtest():
    """A missing query silently means that sub-test can never be repaired."""
    for component, (_bucket, spec) in repair_merge.SPEC.items():
        have = set(repair.QUERIES[component])
        want = {k for k, _l, _m in spec}
        if component == "BQ":
            # BQ repairs only the four E12 named; the other seven answer already
            assert have.issubset(want) and have
        elif not want:
            # E25 left MG with no model-scored sub-tests, so it has nothing to repair.
            assert not have, f"{component}: queries for sub-tests that no longer exist"
        else:
            assert want == have, f"{component}: missing {want - have}"


def test_targeted_body_reads_the_dict_chunk_pool_returns(monkeypatch):
    """`evidence.chunk_pool` returns a DICT. Unpacking it as a 3-tuple failed on every
    company of a 100-company run - loudly, but only after the GPU had started."""
    from clab.qual import evidence as ev_mod

    monkeypatch.setattr(ev_mod, "fact_sheet", lambda ctx: "FACTS")
    monkeypatch.setattr(ev_mod, "retrieve",
                        lambda chunks, q, k=2, doc_vectors=None: (chunks[:k], "stub"))
    pool = {"chunks": ["[business] the largest distribution network"],
            "vectors": [None], "filing": {"form": "10-K", "filed": "2026-01-01"},
            "per_section": {}, "whole_document_fallback": False,
            "n_chunks_before_cap": 1}
    body, meta = repair.targeted_body(object(), ["economies_of_scale"], "BQ", pool)
    assert "FACTS" in body and "distribution network" in body
    assert meta["n_chunks_picked"] == 1


def test_a_null_without_a_query_is_left_alone():
    """BQ has queries for the four dimensions E12 named, not all eleven. Asking about a
    dimension with no targeted evidence is asking the model to answer from nothing."""
    payload = {"dimensions": {k: {"score": None}
                              for k, _lbl in __import__(
                                  "clab.scoring.rubric", fromlist=["x"]).BQ_DIMENSIONS}}
    nulls = [k for k, _l, _m in repair_merge.null_items(payload, "BQ")]
    assert "brand" in nulls                       # it IS null
    assert "brand" not in repair.QUERIES["BQ"]    # but there is no query for it


def test_the_fold_notices_a_company_whose_sixth_dimension_came_from_a_repair(tmp_path,
                                                                             monkeypatch):
    """The repair only pays off if the fold re-scores the company afterwards.

    `_cached_bq_dimensions` counted the raw payload, so a company sitting at 5 production
    dimensions plus 1 repaired one looked unchanged, the fold skipped it, and the
    scorecard kept saying NO_DATA - a whole run of GPU with nothing to show for it.
    """
    from clab import config as clab_config
    from clab.runner import fold_qual

    monkeypatch.setattr(clab_config, "QUAL_DIR", tmp_path)
    payload = {
        "dimensions": {f"d{i}": {"score": 3} for i in range(5)},
        repair_merge.REPAIRS_KEY: {"economies_of_scale": _rep()},
    }
    (tmp_path / "0000000001_BQ_abc.json").write_text(json.dumps(payload),
                                                     encoding="utf-8")
    assert fold_qual._cached_bq_dimensions("0000000001") == 6
    assert fold_qual._cache_has_any_score("0000000001", "BQ") is True


def test_engine_reports_repair_fields_on_the_row():
    """These fields feed the Rank sheet's `repaired_points_quoted` column.

    The first wiring of this shipped without its import: `score_context` raised
    NameError for every company in the fold. Nothing in the suite called it, so only the
    fold caught it - after 41 minutes of GPU had already been spent.
    """
    from clab.runner import engine

    class _Ctx:
        qual = {"BQ": {"dimensions": {"brand": {"score": None}},
                       repair_merge.REPAIRS_KEY: {"economies_of_scale": _rep()},
                       "coverage_before_repair": 0.85}}

    fields = engine._repair_fields(_Ctx())
    assert fields["repaired_points_quoted"] == 5        # BQ dimensions are worth 5
    assert fields["repaired_subtests"] == "bq_economies_of_scale"
    assert fields["coverage_before_repair"] == 0.85


def test_build_pack_still_works_after_the_chunk_pool_extraction(monkeypatch):
    """`build_pack` is the production generation path and NOTHING in the suite called it.

    Pulling `chunk_pool` out of it left `sections` undefined in the meta block, so every
    fresh qual generation would have raised NameError - after paying for the filing fetch
    and the embedding run. The nightly crawl is the only thing that would have noticed.
    """
    from clab.qual import evidence as ev_mod

    monkeypatch.setattr(ev_mod, "fact_sheet", lambda ctx: "FACTS")
    monkeypatch.setattr(ev_mod, "_news_lines", lambda ctx: "NEWS")
    monkeypatch.setattr(ev_mod, "retrieve",
                        lambda chunks, q, k=8, doc_vectors=None, use_embeddings=True:
                        (chunks[:k], "stub"))
    pool = {"chunks": ["[business] we run four plants"], "vectors": [None],
            "filing": {"form": "10-K", "filed": "2026-01-01"},
            "per_section": {"business": ["[business] we run four plants"]},
            "sections": {"business": "we run four plants"},
            "whole_document_fallback": False, "n_chunks_before_cap": 1}
    pack = ev_mod.build_pack(object(), pool=pool)
    assert set(pack["components"]) == {"SG", "BQ", "MG"}
    assert pack["meta"]["item_sections_found"] == ["business"]
    assert all(pack["sha1"].values())


def test_a_repaired_subtest_is_still_marked_LLM():
    """`SubTest.is_llm` tests provenance source == "llm", and the UI's purple chip and
    the parquet's `*_is_llm` columns follow it. Writing "repair" into `source` made a
    repaired point read as measured EDGAR data - the opposite of disclosing it."""
    payload = _payload({"brand": {"score": None}}, {"brand": _rep()})
    merged = repair_merge.merged_items(payload, "dimensions")
    assert merged["brand"]["source"] == "llm"
    assert merged["brand"]["origin"] == "repair"


def test_sg_provenance_keeps_is_llm_true_for_a_repair():
    from clab.scoring import sg
    from clab.scoring.types import Status, SubTest

    rec = {"score": 3, "source": "llm", "origin": "repair", "repair_gate": "strict"}
    prov = sg._llm_prov({"model": "qwen2.5:7b"}, "tam_expanding", rec)
    st = SubTest(key="sg_tam_expanding", label="TAM", max_points=4, earned=3,
                 status=Status.SCORED, provenance=prov)
    assert st.is_llm is True
    assert prov["origin"] == "repair"


def test_repaired_points_cannot_exceed_the_component_budget():
    """BQ's 11 dimensions are worth 5 raw each but map onto a 15-point component by
    their MEAN, so summing maxima reported up to 20 points against a 15-point budget."""
    payload = {"dimensions": {}, repair_merge.REPAIRS_KEY: {
        k: _rep() for k in ("economies_of_scale", "manufacturing_complexity",
                            "data_advantages", "network_effects")}}
    quoted, _unquoted = repair_merge.repaired_points(payload, "BQ")
    assert quoted <= 15


def test_a_collided_repair_is_not_counted_as_recovered():
    """It changed no score. Counting it would credit points that never landed and hide
    the stale-payload signal the collision exists to raise."""
    payload = {"dimensions": {"brand": {"score": 2}},
               repair_merge.REPAIRS_KEY: {"brand": _rep(score=5)}}
    quoted, _ = repair_merge.repaired_points(payload, "BQ")
    assert quoted == 0
    summary = repair_merge.repaired_summary(payload, "dimensions")
    assert summary["collided"] == ["brand"]
    assert summary["quoted"] == []


def test_e19_is_monotone_against_the_old_cliff():
    """Amendment 1's defence: no company can score higher than the pre-E19 rule allowed,
    and none lower. Six dimensions still award 15; five award a share instead of zero."""
    from clab.scoring import bq, rubric
    from clab.scoring.context import SymbolContext

    def comp(n):
        dims = {k: {"score": 5} for k, _l in rubric.BQ_DIMENSIONS[:n]}
        ctx = SymbolContext(ticker="T", cik="1",
                            qual={"BQ": {"dimensions": dims, "model": "m"}})
        return bq.score(ctx)

    assert comp(11).available_points == 15
    assert comp(6).available_points == 15          # the sufficiency threshold holds
    assert comp(5).available_points == 7           # was 0 before E19
    assert comp(2).available_points == 3
    assert comp(0).available_points == 0
    # monotone: more dimensions never buys less availability
    avail = [comp(n).available_points for n in range(0, 12)]
    assert avail == sorted(avail)
