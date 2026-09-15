"""Tag resolution across a switched taxonomy, and the LLM parse rejection rules."""
from __future__ import annotations

import pytest

from clab.fundamentals import tags
from clab.scoring import bq, mg, rubric, sg
from clab.scoring.context import SymbolContext


def facts(**tag_rows) -> dict:
    """Build a companyfacts-shaped payload from {tag: [rows]}."""
    return {"facts": {"us-gaap": {
        tag: {"units": {"USD": rows}} for tag, rows in tag_rows.items()}}}


def row(start, end, val, filed="2026-05-01"):
    return {"start": start, "end": end, "val": val, "filed": filed,
            "accn": "a-1", "form": "10-Q"}


def q(year, qtr, val, filed="2026-05-01"):
    starts = {1: (f"{year}-01-01", f"{year}-03-31"), 2: (f"{year}-04-01", f"{year}-06-30"),
              3: (f"{year}-07-01", f"{year}-09-30"), 4: (f"{year}-10-01", f"{year}-12-31")}
    s, e = starts[qtr]
    return row(s, e, val, filed)


# ------------------------------------------------------------------ tag switching
def test_a_retired_tag_cannot_supply_the_recent_series():
    """The NVDA bug: it stopped filing RevenueFromContractWithCustomer... in 2022
    and moved to Revenues. Naive chain order produced a revenue series ending in
    2020 and a TTM of $10.9B against a true ~$200B."""
    payload = facts(
        RevenueFromContractWithCustomerExcludingAssessedTax=[
            q(2019, 1, 100), q(2019, 2, 110), q(2019, 3, 120), q(2019, 4, 130)],
        Revenues=[q(2025, 1, 900), q(2025, 2, 950), q(2025, 3, 1000), q(2025, 4, 1100)],
    )
    tag, rows = tags.resolve(payload, "revenue")
    ends = sorted(r["end"] for r in rows)
    assert ends[-1] == "2025-12-31"
    assert "Revenues" in tag


def test_history_from_a_retired_tag_is_still_merged():
    """The point of merging rather than just picking: the old tag supplies the
    history the current tag lacks."""
    payload = facts(
        RevenueFromContractWithCustomerExcludingAssessedTax=[q(2019, 1, 100)],
        Revenues=[q(2025, 1, 900), q(2025, 2, 950)],
    )
    tag, rows = tags.resolve(payload, "revenue")
    ends = sorted(r["end"] for r in rows)
    assert "2019-03-31" in ends and "2025-06-30" in ends
    assert "+" in tag                      # provenance names both contributors


def test_chain_order_wins_on_an_overlapping_period():
    """Chain order encodes semantic preference, so a comparable rival does not displace it."""
    payload = facts(
        RevenueFromContractWithCustomerExcludingAssessedTax=[q(2025, 1, 111)],
        Revenues=[q(2025, 1, 118)],         # 1.06x - a reclassification, not a fragment
    )
    _tag, rows = tags.resolve(payload, "revenue")
    assert len(rows) == 1
    assert rows[0]["val"] == 111            # earlier chain position is preferred


def test_a_dominating_tag_overrides_chain_order_because_a_part_cannot_exceed_its_whole():
    """E30: chain order preferring a FRAGMENT is how EQR got a $216,000 revenue.

    Equity Residential files `RevenueFromContractWithCustomerIncludingAssessedTax` of
    $384,000 - management fees - beside `Revenues` of $2,699,485,000, its rental income.
    ASC 842 lease income is not ASC 606 contract revenue, so for a REIT the tag the chain
    prefers is structurally a minor line. Chain order preferred the fragment and every
    margin, growth rate and revenue multiple downstream inherited it.

    The override is safe because of what revenue MEANS: every revenue tag in one filing
    is either the consolidated total or a component of it, and a component cannot exceed
    its own total. Measured on 220 companies, 10 changed and **every one increased**.
    """
    payload = facts(
        RevenueFromContractWithCustomerIncludingAssessedTax=[q(2025, 1, 384_000)],
        Revenues=[q(2025, 1, 2_699_485_000)],
    )
    _tag, rows = tags.resolve(payload, "revenue")
    assert len(rows) == 1
    assert rows[0]["val"] == 2_699_485_000


def test_the_override_only_compares_periods_the_two_tags_SHARE():
    """Otherwise a tag would be ranked on how much history it carries, not how much
    of the business it measures - and the retired-tag merge would break."""
    payload = facts(
        RevenueFromContractWithCustomerExcludingAssessedTax=[q(2025, 1, 100),
                                                             q(2025, 2, 100)],
        Revenues=[q(2019, 1, 900)],          # big, but no overlapping period
    )
    _tag, rows = tags.resolve(payload, "revenue")
    recent = [r for r in rows if r["end"] == "2025-03-31"]
    assert recent and recent[0]["val"] == 100
    assert any(r["end"] == "2019-03-31" for r in rows), "history must still merge"


def test_a_stale_dominating_tag_does_not_win_the_recent_end():
    """Freshness is decided FIRST. A retired tag cannot supply the recent end however
    large it is - the NVDA rule is not weakened by the fragment rule."""
    payload = facts(
        RevenueFromContractWithCustomerExcludingAssessedTax=[q(2025, 1, 100)],
        Revenues=[q(2015, 1, 5_000)],
    )
    _tag, rows = tags.resolve(payload, "revenue")
    recent = [r for r in rows if r["end"] == "2025-03-31"]
    assert recent and recent[0]["val"] == 100


def test_absent_metric_returns_none_not_zero():
    tag, rows = tags.resolve(facts(), "revenue")
    assert tag is None and rows == []


def test_has_line_item_distinguishes_format_from_gap():
    """JPM and XOM file no GrossProfit line. That is a fact about their income
    statement, so the dependent sub-test reads NOT_APPLICABLE, not NO_DATA."""
    with_gp = facts(GrossProfit=[q(2025, 1, 10)])
    assert tags.has_line_item(with_gp, "gross_profit")
    assert not tags.has_line_item(facts(), "gross_profit")


def test_instant_and_dei_chains_resolve():
    payload = {"facts": {
        "us-gaap": {"Assets": {"units": {"USD": [{"end": "2026-03-31", "val": 1,
                                                  "filed": "2026-05-01", "accn": "a"}]}}},
        "dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": [
            {"end": "2026-03-31", "val": 100, "filed": "2026-05-01", "accn": "a"}]}}},
    }}
    assert tags.resolve_instant(payload, "assets")[0] == "Assets"
    assert tags.resolve_dei(payload, "shares_outstanding")[0] == \
        "EntityCommonStockSharesOutstanding"


# ------------------------------------------------------------------ LLM parse rules
def ctx_with_qual(qual: dict) -> SymbolContext:
    return SymbolContext(ticker="T", cik="0000000001", as_of="2026-08-08T00:00:00+00:00",
                         qual=qual)


def sg_payload(scores: dict) -> dict:
    return {"SG": {"model": "qwen2.5:7b", "prompt_sha1": "p", "evidence_sha1": "e",
                   "generated_at": "2026-08-08T00:00:00+00:00", "scores": scores}}


def test_cold_qual_cache_is_all_no_data():
    comp = sg.score(ctx_with_qual({}))
    assert comp.earned_points == 0
    assert comp.available_points == 0
    assert all(st.status.value == "no_data" for st in comp.subtests)


def test_valid_integer_scores_are_accepted():
    comp = sg.score(ctx_with_qual(sg_payload({
        "tam_expanding": {"score": 4, "rationale": "big", "evidence": "quote"},
        "secular_not_cyclical": {"score": 3, "rationale": "secular"},
    })))
    assert comp.earned_points == 7
    st = [s for s in comp.subtests if s.key == "sg_tam_expanding"][0]
    assert st.is_llm and st.evidence == "quote"
    assert st.provenance["model"] == "qwen2.5:7b"


def test_out_of_range_score_is_rejected_not_clamped():
    """Clamping would launder a hallucinated 9/4 into a top score."""
    comp = sg.score(ctx_with_qual(sg_payload({"tam_expanding": {"score": 9}})))
    st = [s for s in comp.subtests if s.key == "sg_tam_expanding"][0]
    assert st.status.value == "no_data"
    assert st.provenance["rejected_value"] == 9
    assert comp.earned_points == 0


def test_float_score_is_rejected():
    comp = sg.score(ctx_with_qual(sg_payload({"tam_expanding": {"score": 3.5}})))
    st = [s for s in comp.subtests if s.key == "sg_tam_expanding"][0]
    assert st.status.value == "no_data"


def test_null_score_is_the_models_i_dont_know_channel():
    comp = sg.score(ctx_with_qual(sg_payload({
        "tam_expanding": {"score": None, "rationale": "the filing does not say"}})))
    st = [s for s in comp.subtests if s.key == "sg_tam_expanding"][0]
    assert st.status.value == "no_data"
    assert "does not say" in st.rationale


def test_unverified_evidence_is_kept_but_flagged():
    comp = sg.score(ctx_with_qual(sg_payload({
        "tam_expanding": {"score": 4, "evidence": "invented", "evidence_unverified": True}})))
    st = [s for s in comp.subtests if s.key == "sg_tam_expanding"][0]
    assert st.earned == 4 and st.evidence_unverified is True


def test_measured_contradiction_is_surfaced_not_averaged_away():
    from clab.fundamentals.metrics import MetricBundle

    m = MetricBundle()
    m.set("revenue_accelerating", False)
    c = SymbolContext(ticker="T", cik="1", metrics=m,
                      qual=sg_payload({"revenue_growth_sustainable": {"score": 4}}))
    comp = sg.score(c)
    st = [s for s in comp.subtests if s.key == "sg_revenue_growth_sustainable"][0]
    assert st.earned == 4
    assert "contradiction" in st.inputs


# ------------------------------------------------------------------ BQ mapping
def bq_payload(scores: dict, killer: str = "because of scale") -> dict:
    return {"BQ": {"model": "qwen2.5:7b", "killer_answer": killer,
                   "dimensions": {k: {"score": v} for k, v in scores.items()}}}


def test_bq_thin_assessment_is_down_weighted_not_deleted():
    """E19: the 6-of-11 floor became a weight.

    It used to award 15 points at six dimensions and ZERO below, which deleted 423
    companies from the ranking - 184 of them one dimension short, and concentrated in
    Financials and Real Estate because a REIT has no manufacturing complexity. Two
    dimensions now buy 3 of 15 points of AVAILABILITY, so such a company enters the
    ranking but cannot sit beside a fully assessed one.
    """
    comp = bq.score(ctx_with_qual(bq_payload({"brand": 5, "network_effects": 5})))
    assert comp.subtests[0].status.value == "scored"
    assert comp.available_points == 3            # round(15 * 2/11)
    assert comp.earned_points == 3               # both at 5/5 -> the whole assessed share
    assert comp.max_points == 15                 # the rest is NO_DATA, not deleted
    assert comp.no_data_points == 12
    missing = comp.subtests[1].inputs["dimensions_missing"]
    assert "economies_of_scale" in missing and len(missing) == 9


def test_bq_with_nothing_scored_is_still_no_data():
    """A filing that supported no dimension at all is not the same as a thin one."""
    comp = bq.score(ctx_with_qual(bq_payload({})))
    assert comp.subtests[0].status.value == "no_data"
    assert comp.available_points == 0


def test_bq_maps_mean_to_fifteen():
    """Mean, not sum: two overwhelming moats should not rank below eleven weak ones."""
    all_five = {k: 5 for k, _l in rubric.BQ_DIMENSIONS}
    assert bq.score(ctx_with_qual(bq_payload(all_five))).earned_points == 15
    all_three = {k: 3 for k, _l in rubric.BQ_DIMENSIONS}
    assert bq.score(ctx_with_qual(bq_payload(all_three))).earned_points == 9
    # E19 Amendment 1: six dimensions is the framework's own sufficiency threshold, so
    # it still awards the full 15. Removing that ceiling as well as the cliff cost 57
    # companies their band while rescuing 47 - the wrong trade.
    six = {k: 5 for k, _l in rubric.BQ_DIMENSIONS[:6]}
    comp = bq.score(ctx_with_qual(bq_payload(six)))
    assert comp.earned_points == 15
    assert comp.available_points == 15


def test_bq_rejects_out_of_range_dimensions():
    scores = {k: 5 for k, _l in rubric.BQ_DIMENSIONS[:7]}
    scores[rubric.BQ_DIMENSIONS[0][0]] = 99
    comp = bq.score(ctx_with_qual(bq_payload(scores)))
    detail = comp.subtests[0].inputs["dimensions"][rubric.BQ_DIMENSIONS[0][0]]
    assert detail["rejected_value"] == 99
    assert detail["score"] is None


def test_bq_carries_the_killer_question():
    comp = bq.score(ctx_with_qual(bq_payload({k: 4 for k, _l in rubric.BQ_DIMENSIONS})))
    assert rubric.BQ_KILLER_QUESTION in comp.note
    assert "because of scale" in comp.note


# ------------------------------------------------------------------ MG mix
def test_mg_ceo_with_no_attributes_at_all_is_no_data():
    comp = mg.score(SymbolContext(ticker="T", cik="1", qual={}))
    ceo = [s for s in comp.subtests if s.key == "mg_ceo"][0]
    assert ceo.status.value == "no_data"


def test_mg_ceo_partial_assessment_is_weighted_not_zeroed():
    """E19: the 4-of-7 cliff put 121 companies at exactly 3 of 15 on MG.

    Two measured attributes alone now carry their share of the CEO block instead of
    voiding it, and the unassessed remainder stays visible as NO_DATA.
    """
    ctx = SymbolContext(ticker="T", cik="1", qual={},
                        market={"surprise_beat_rate": 0.9, "surprise_quarters": 20})
    comp = mg.score(ctx)
    ceo = [s for s in comp.subtests if s.key == "mg_ceo"]
    if ceo and ceo[0].status.value == "scored":
        rest = [s for s in comp.subtests if s.key == "mg_ceo_unassessed"]
        assert ceo[0].max_points < rubric.MG_CEO_POINTS
        assert rest and rest[0].status.value == "no_data"
        assert ceo[0].max_points + rest[0].max_points == rubric.MG_CEO_POINTS


def test_mg_measures_guidance_from_the_surprise_history():
    """rubric A3: two of the seven CEO attributes are measurable, so they are
    measured rather than asked."""
    c = SymbolContext(ticker="T", cik="1",
                      market={"surprise_beat_rate": 0.9, "surprise_quarters": 20})
    val, why = mg._measured_attr(c, "hits_guidance")
    assert val == 2 and "90" in why

    c2 = SymbolContext(ticker="T", cik="1",
                       market={"surprise_beat_rate": 0.2, "surprise_quarters": 20})
    assert mg._measured_attr(c2, "hits_guidance")[0] == 0

    c3 = SymbolContext(ticker="T", cik="1", market={"surprise_quarters": 2})
    assert mg._measured_attr(c3, "hits_guidance")[0] is None


def test_mg_capital_allocation_is_measured_not_asked():
    """Every input the framework names for capital allocation is a filed number."""
    from clab.fundamentals.metrics import MetricBundle

    m = MetricBundle()
    for k, v in (("fcf_ttm", 100.0), ("capex_ttm", 30.0), ("rnd_ttm", 20.0),
                 ("roic", 0.25), ("buybacks_ttm", 40.0), ("dilution_yoy", -0.03),
                 ("dividends_ttm", 10.0), ("ma_spend_ttm", 5.0),
                 ("impairment_ttm", 0.0), ("net_debt_ebitda", 1.0)):
        m.set(k, v)
    comp = mg.score(SymbolContext(ticker="T", cik="1", metrics=m, qual={}))
    keys = {s.key for s in comp.subtests}
    assert {"mg_reinvestment_quality", "mg_buyback_discipline", "mg_ma_track_record",
            "mg_balance_sheet_stewardship"} <= keys
    capalloc = [s for s in comp.subtests if s.key.startswith("mg_") and s.key != "mg_ceo"]
    assert all(s.status.value == "scored" for s in capalloc)
    assert all(s.provenance.get("source") != "llm" for s in capalloc)
    assert sum(s.earned for s in capalloc) == 7


def test_component_maxima_are_enforced_for_every_llm_component():
    for module, code in ((sg, "SG"), (bq, "BQ"), (mg, "MG")):
        comp = module.score(SymbolContext(ticker="T", cik="1", qual={}))
        assert comp.max_points == rubric.COMPONENTS[code][1]
        comp.check_points()
