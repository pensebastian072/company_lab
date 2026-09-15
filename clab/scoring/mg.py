"""MG - Management & Capital Allocation /9. FULLY MEASURED.

The docstring this replaces said "Part LLM, part measured ... 9.4 of MG's 15 points
are measured and 5.6 are model judgement". That was stale by two experiments and one
component resize, and because rubric.LLM_COMPONENTS still listed MG, those 9 measured
points were being reported as model judgement and excluded from the measured-half
columns. Corrected in V3 P0; see journal/experiments/mg_label_correction.md.

CEO block /2 (rubric A3): E25 removed the five model-scored attributes and E26 cut the
block 8 -> 2. Both survivors carry source "data" in MG_CEO_ATTRIBUTES, so _LLM_ATTRS
below is an EMPTY tuple and nothing here asks the model for a score:
  - "hits guidance"              <- ctx.mk("surprise_beat_rate") over >=4 quarters
  - "navigated previous downturns" <- worst YoY decline in the EDGAR revenue and
    operating-income series, and whether operating income stayed positive there

Capital allocation block /7: every input the framework names - capex, R&D, buybacks,
M&A spend, goodwill impairments, debt, dilution - is a filed number, so this block is
measured rather than asked. The framework's own good/bad pattern is implemented
directly: FCF into productive capex and R&D and accretive M&A and buybacks when cheap
scores well; debt into overpriced acquisitions and buybacks at absurd valuations
scores badly.

The model is still asked for MG (rubric.GENERATED_COMPONENTS includes it) but its
payload contributes only a display-only `ceo_summary` string used as this block's
rationale. Every MG payload on disk carries `ceo = {}`. ComponentScore.is_llm is
False and every sub-test comes back source=edgar.
"""
from __future__ import annotations

from . import rubric
from .context import SymbolContext, num, pct, subtest
from . import repair_merge
from .sg import read_llm_subtests
from .types import ComponentScore, no_data, scored

CODE = "MG"

_LLM_ATTRS = tuple((k, lbl) for k, lbl, src in rubric.MG_CEO_ATTRIBUTES if src == "llm")


def score(ctx: SymbolContext) -> ComponentScore:
    sts = _ceo_block(ctx) + _capital_allocation(ctx)
    comp = ComponentScore(
        code=CODE, label=rubric.COMPONENTS[CODE][0],
        max_points=rubric.COMPONENTS[CODE][1], subtests=sts,
        note=("Fully measured. CEO 2 (guidance-hit rate from the surprise history, "
              "downturn behaviour from the filed revenue and operating-income series) "
              "/ capital allocation 7 (filed capex, R&D, buybacks, M&A and "
              "impairments). No MG point is model-scored."),
    )
    comp.check_points()
    return comp


# ------------------------------------------------------------------ CEO /8
def _ceo_block(ctx: SymbolContext):
    payload = (ctx.qual or {}).get("MG") or {}
    attrs = repair_merge.merged_items(payload, "ceo")
    raw: dict[str, int] = {}
    detail: dict[str, dict] = {}
    rejected: dict[str, object] = {}

    for key, label, source in rubric.MG_CEO_ATTRIBUTES:
        if source == "llm":
            rec = attrs.get(key)
            v = rec.get("score") if isinstance(rec, dict) else None
            if v is None:
                pass
            elif isinstance(v, bool) or not isinstance(v, int) \
                    or not 0 <= v <= rubric.MG_CEO_ATTRIBUTE_MAX:
                rejected[key] = v
                v = None
            if v is not None:
                raw[key] = v
            detail[key] = {
                "label": label, "score": v, "max": rubric.MG_CEO_ATTRIBUTE_MAX,
                "source": "llm",
                "origin": (rec or {}).get("origin", "first_call")
                if isinstance(rec, dict) else "first_call",
                "rationale": (rec or {}).get("rationale", "")[:300] if isinstance(rec, dict) else "",
                "rejected_value": rejected.get(key),
            }
        else:
            v, why = _measured_attr(ctx, key)
            if v is not None:
                raw[key] = v
            detail[key] = {"label": label, "score": v,
                           "max": rubric.MG_CEO_ATTRIBUTE_MAX,
                           "source": "measured", "rationale": why}

    inputs = {
        "attributes": detail,
        "n_scored": len(raw),
        "min_required": rubric.MG_MIN_ATTRIBUTES_SCORED,
        "mapping": f"round(sum/14*{rubric.MG_CEO_POINTS})",
    }
    prov = {
        "source": "llm" if any(d["source"] == "llm" and d["score"] is not None
                               for d in detail.values()) else "edgar",
        "mixed": True,
        "model": payload.get("model"),
        "prompt_sha1": payload.get("prompt_sha1"),
        "evidence_sha1": payload.get("evidence_sha1"),
        "generated_at": payload.get("generated_at"),
    }
    mx = rubric.MG_CEO_POINTS
    n_attrs = len(raw)
    n_total = len(rubric.MG_CEO_ATTRIBUTES)
    # E19, the same cliff one component over: 121 companies sat at exactly 3 of 15 on MG
    # because four of seven CEO attributes had to be scored or the whole 8-point block
    # vanished. Assessed share is scored, the rest is NO_DATA.
    # E19 Amendment 1, same shape as BQ: full block at or above the existing 4-of-7
    # threshold, proportional below it instead of zero.
    if n_attrs >= rubric.MG_MIN_ATTRIBUTES_SCORED:
        assessed = mx
    else:
        assessed = int(round(mx * n_attrs / n_total))
        if n_attrs:
            assessed = max(1, min(assessed, mx))
    inputs["attributes_assessed"] = n_attrs
    inputs["points_assessed"] = assessed
    if n_attrs == 0:
        return [no_data("mg_ceo", "CEO quality and track record", mx,
                        "no CEO attribute could be scored",
                        inputs=inputs, provenance=prov)]
    scored_raw = n_attrs * rubric.MG_CEO_ATTRIBUTE_MAX
    pts = int(round(sum(raw.values()) / scored_raw * assessed))
    out = [scored("mg_ceo", "CEO quality and track record", assessed,
                  max(0, min(pts, assessed)),
                  inputs=inputs, provenance=prov,
                  rationale=(payload.get("ceo_summary") or "")[:300],
                  threshold_note=f"{sum(raw.values())}/{scored_raw} raw over "
                                 f"{n_attrs} of {n_total} attributes -> "
                                 f"{pts}/{assessed} assessed points")]
    remainder = mx - assessed
    if remainder > 0:
        out.append(no_data(
            "mg_ceo_unassessed", "CEO attributes the filing did not support", remainder,
            f"{n_total - n_attrs} of {n_total} CEO attributes were not scored",
            inputs={"attributes_missing": sorted(
                k for k, _lbl, _src in rubric.MG_CEO_ATTRIBUTES if k not in raw)},
            provenance=prov))
    return out


def _measured_attr(ctx: SymbolContext, key: str) -> tuple[int | None, str]:
    if key == "hits_guidance":
        rate = ctx.mk("surprise_beat_rate")
        n = ctx.mk("surprise_quarters") or 0
        if rate is None or n < 4:
            return None, "insufficient reported-surprise history"
        if rate >= 0.75:
            return 2, f"beat consensus in {pct(rate)} of {int(n)} quarters"
        if rate >= 0.5:
            return 1, f"beat consensus in {pct(rate)} of {int(n)} quarters"
        return 0, f"beat consensus in only {pct(rate)} of {int(n)} quarters"

    if key == "navigated_downturns":
        return _downturn_score(ctx)
    return None, ""


def _downturn_score(ctx: SymbolContext) -> tuple[int | None, str]:
    """Did the business hold up through its own worst historical revenue decline?

    Measured from the discrete quarterly revenue and operating-income series
    already built for this company, so it needs no extra data.
    """
    rev = ctx.metrics.series.get("revenue")
    op = ctx.metrics.series.get("operating_income")
    if not rev or len(rev) < 12:
        return None, "fewer than 12 quarters of revenue history"

    facts = rev.facts
    worst = 0.0
    worst_end = None
    for i in range(4, len(facts)):
        prior = facts[i - 4].val
        if prior and prior > 0:
            chg = (facts[i].val - prior) / prior
            if chg < worst:
                worst, worst_end = chg, facts[i].end_iso
    if worst_end is None:
        return None, "no computable year-over-year revenue history"

    stayed_profitable = None
    if op and op.facts:
        opmap = {f.end_iso: f.val for f in op.facts}
        v = opmap.get(worst_end)
        if v is not None:
            stayed_profitable = v > 0

    if worst > -0.05:
        return 2, (f"never saw a material revenue decline in the filed history "
                   f"(worst YoY {pct(worst)})")
    if stayed_profitable is True:
        return 2, (f"stayed operating-profitable through its worst revenue decline "
                   f"({pct(worst)} YoY into {worst_end})")
    if stayed_profitable is False:
        return 0, (f"went operating-loss-making in its worst revenue decline "
                   f"({pct(worst)} YoY into {worst_end})")
    return 1, f"worst revenue decline {pct(worst)} YoY into {worst_end}; margin outcome unknown"


# ------------------------------------------------------------------ capital allocation /7
def _capital_allocation(ctx: SymbolContext) -> list:
    M = ctx.metrics
    out = []

    fcf = M.raw("fcf_ttm")
    capex, rnd = M.raw("capex_ttm"), M.raw("rnd_ttm")
    roic = M.raw("roic")
    reinvest = None
    if fcf not in (None, 0) and fcf > 0:
        reinvest = ((capex or 0.0) + (rnd or 0.0)) / fcf
    if reinvest is not None and roic is not None:
        if roic >= 0.15 and reinvest >= 0.30:
            pts, why = 2, (f"reinvests {pct(reinvest)} of FCF at a {pct(roic)} ROIC - "
                           f"growth is being bought at a good return")
        elif roic >= 0.10:
            pts, why = 1, f"reinvests {pct(reinvest)} of FCF at a {pct(roic)} ROIC"
        else:
            pts, why = 0, f"reinvests {pct(reinvest)} of FCF at only a {pct(roic)} ROIC"
    else:
        pts, why = None, ""
    out.append(subtest(
        ctx, "mg_reinvestment_quality",
        "Reinvestment: capex + R&D vs FCF, and the ROIC it earns", 2,
        value=reinvest, points=pts,
        inputs={"capex_ttm": capex, "rnd_ttm": rnd, "fcf_ttm": fcf,
                "reinvestment_rate": reinvest, "roic": roic},
        prov_keys=("capex_ttm", "rnd_ttm", "fcf_ttm", "roic"), note=why,
    ))

    # buyback discipline: are repurchases happening when the multiple is low?
    buybacks = M.raw("buybacks_ttm")
    pctile = (ctx.peers or {}).get("pe_pctile_own")
    dil = M.raw("dilution_yoy")
    if buybacks is not None and fcf not in (None, 0) and fcf > 0:
        intensity = buybacks / fcf
        if pctile is not None:
            if intensity > 0.15 and pctile <= 0.5:
                pts, why = 2, (f"buying back {pct(intensity)} of FCF while the multiple "
                               f"sits in its own {pctile:.0%} percentile")
            elif intensity > 0.15 and pctile > 0.8:
                pts, why = 0, (f"buying back {pct(intensity)} of FCF at a multiple in its "
                               f"own {pctile:.0%} percentile - value-destructive timing")
            else:
                pts, why = 1, f"buybacks {pct(intensity)} of FCF, multiple percentile {pctile:.0%}"
        elif dil is not None:
            # no own-multiple history yet: fall back to whether the count actually shrinks
            if dil < -0.01 and intensity > 0.10:
                pts, why = 2, (f"buybacks {pct(intensity)} of FCF and the share count is "
                               f"genuinely shrinking ({pct(dil)} YoY)")
            elif dil > 0.02:
                pts, why = 0, (f"buybacks {pct(intensity)} of FCF yet the share count still "
                               f"grew {pct(dil)} - repurchases are offsetting issuance")
            else:
                pts, why = 1, f"buybacks {pct(intensity)} of FCF, share count {pct(dil)} YoY"
        else:
            pts, why = None, ""
    elif buybacks is None and dil is not None:
        # `buybacks is None` explicitly, not just "the branch above declined". That branch
        # also declines when buybacks EXIST but FCF is zero or negative, and reading those
        # as "no repurchases" would be a false statement in the note - the company did
        # repurchase, we simply cannot express it as a share of cash flow. Zero companies
        # are in that state today; the guard is here so it stays true.
        #
        # E34: no repurchases at all. "Did not repurchase" is a FACT, not a gap, and the
        # sibling sub-test ten lines below already reads its analogous absence that way -
        # `mg_ma_track_record` scores 2 for "no acquisitions and no impairments in the
        # trailing year". 268 companies were reading NO_DATA here on "input unavailable".
        #
        # The tag chain was checked FIRST and is not the cause: A/B over 240 filings,
        # adding alternate repurchase tags rescued 6 while PERTURBING 44 existing values,
        # and a substitute that fires only on an empty series rescued 0. The absence is
        # real.
        #
        # It is scored from the share count rather than assumed, and only where that
        # second series exists - `dil is None` still falls through to NO_DATA below, which
        # is what keeps this a measurement instead of a default. `dilution_yoy` only
        # became usable today (E33: 3.1% -> 78.7% of companies earning its point).
        intensity = 0.0
        if dil <= 0:
            pts, why = 2, (f"no repurchases, and the share count is flat or shrinking "
                           f"({pct(dil)} YoY) - nothing to offset")
        elif dil <= rubric.BS_DILUTION_BANDS[1]:
            pts, why = 1, (f"no repurchases and the share count grew {pct(dil)} YoY - "
                           f"ordinary share-based compensation, not offset")
        else:
            pts, why = 0, (f"no repurchases while the share count grew {pct(dil)} YoY - "
                           f"issuing and not offsetting it")
    else:
        intensity, pts, why = None, None, ""
    out.append(subtest(
        ctx, "mg_buyback_discipline", "Buybacks when cheap, not at peak multiples", 2,
        value=intensity, points=pts,
        inputs={"buybacks_ttm": buybacks, "fcf_ttm": fcf, "buyback_intensity": intensity,
                "pe_pctile_own": pctile, "dilution_yoy": dil,
                "dividends_ttm": M.raw("dividends_ttm")},
        prov_keys=("buybacks_ttm", "dilution_yoy"), note=why,
    ))

    # M&A track record: spend against subsequent goodwill impairment
    ma = M.raw("ma_spend_ttm")
    imp = M.raw("impairment_ttm")
    if ma is None and imp is None:
        pts, why, val = None, "", None
    else:
        ma_v, imp_v = (ma or 0.0), (imp or 0.0)
        val = imp_v / ma_v if ma_v > 0 else (1.0 if imp_v > 0 else 0.0)
        if imp_v <= 0 and ma_v > 0:
            pts, why = 2, "acquisitive with no goodwill impairment in the trailing year"
        elif imp_v <= 0:
            pts, why = 2, "no acquisitions and no impairments in the trailing year"
        elif ma_v > 0 and val < 0.25:
            pts, why = 1, f"impairments equal {pct(val)} of M&A spend"
        else:
            pts, why = 0, "impairment charges without matching acquisition value"
    out.append(subtest(
        ctx, "mg_ma_track_record", "M&A accretive, not goodwill-impairing", 2,
        value=val, points=pts,
        inputs={"ma_spend_ttm": ma, "impairment_ttm": imp,
                "impairment_over_ma": val, "goodwill": M.raw("goodwill")},
        prov_keys=("ma_spend_ttm", "impairment_ttm"), note=why,
    ))

    # balance-sheet stewardship: is debt funding growth or financial engineering?
    nde = M.raw("net_debt_ebitda")
    if nde is not None and buybacks is not None and fcf is not None:
        overspend = (buybacks + (M.raw("dividends_ttm") or 0.0)) > fcf
        if nde <= 2.0 and not overspend:
            pts, why = 1, f"net debt/EBITDA {num(nde)} and shareholder returns inside FCF"
        elif nde > 3.5 and overspend:
            pts, why = 0, (f"net debt/EBITDA {num(nde)} while returning more than FCF - "
                           f"returns are being funded with debt")
        else:
            pts, why = 0 if nde > 3.5 else 1, f"net debt/EBITDA {num(nde)}"
    elif nde is not None:
        pts, why = (1 if nde <= 2.0 else 0), f"net debt/EBITDA {num(nde)}"
    else:
        pts, why = None, ""
    out.append(subtest(
        ctx, "mg_balance_sheet_stewardship",
        "Debt used productively, not for financial engineering", 1,
        value=nde, points=pts,
        inputs={"net_debt_ebitda": nde, "buybacks_ttm": buybacks,
                "dividends_ttm": M.raw("dividends_ttm"), "fcf_ttm": fcf},
        prov_keys=("net_debt", "ebitda_ttm"), note=why,
        na_reason="covenant leverage is not defined for this filer type",
    ))
    return out
