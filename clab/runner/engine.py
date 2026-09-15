"""Per-symbol pipeline: fetch -> normalize -> score -> scorecard.

One function, `score_symbol`, walks the stages and returns (Scorecard, meta). It
raises nothing that the caller has to guard beyond a bare `except Exception` for
per-symbol isolation - a malformed companyfacts blob must never kill a 500-name
crawl.

The qualitative half is READ from cache here and never generated: the LLM scorer
is a separate offline batch (clab.qual.scorer). If the cache is cold, SG/BQ/MG
come back all-NO_DATA, coverage lands near 0.50, and the band renders
INSUFFICIENT_DATA - honest, and the quant /50 stays fully usable.
"""
from __future__ import annotations

import time
from typing import Any

from .. import config
from ..fundamentals import metrics as mx
from ..fundamentals import profile as pf
from ..net import atomic_write_json, read_json, utc_now_iso
from ..scoring import bq, composite, en, er, fe, forward_dcf, mg, sg, va
from ..scoring import bs as bs_mod
from ..scoring.context import SymbolContext
from ..scoring.repair_merge import (SPEC as REPAIR_SPEC, repaired_points,
                                    repaired_summary)
from ..sources import yf_prices
from ..sources.edgar_facts import (EdgarSubmissions, entity_name, latest_accn,
                                   resolve_facts, sic_from_submissions)
from ..sources.yf_market import YfMarket, market_metrics

COMPONENT_MODULES = {
    "SG": sg, "BQ": bq, "FE": fe, "MG": mg, "BS": bs_mod, "VA": va, "ER": er, "EN": en,
}


def load_qual(cik: str) -> dict:
    """Cached LLM output for one company, keyed by CIK. Absent -> empty dict."""
    out: dict[str, Any] = {}
    d = config.QUAL_DIR
    if not d.exists():
        return out
    for comp in ("SG", "BQ", "MG"):
        hits = sorted(d.glob(f"{cik}_{comp}_*.json"))
        if hits:
            payload = read_json(hits[-1])
            if isinstance(payload, dict):
                out[comp] = payload
    return out


def build_context(
    ticker: str,
    cik: str,
    *,
    as_of: str,
    name: str = "",
    sector: str = "",
    sub_industry: str = "",
    force: bool = False,
    with_market: bool = True,
    cached_market: bool = False,
    with_prices: bool = True,
    peers: dict | None = None,
    sector_stats: dict | None = None,
) -> tuple[SymbolContext, dict]:
    """Fetch every input for one symbol and assemble the scoring context."""
    meta: dict[str, Any] = {"ticker": ticker, "cik_requested": cik, "timings": {},
                            "sources": {}, "warnings": []}

    t0 = time.perf_counter()
    facts_res, cik_used, note = resolve_facts(cik, force=force)
    meta["timings"]["edgar_facts"] = round(time.perf_counter() - t0, 3)
    meta["cik_used"] = cik_used
    meta["sources"]["edgar_facts"] = facts_res.freshness_record()
    if note:
        meta["warnings"].append(note)
    payload = facts_res.payload if isinstance(facts_res.payload, dict) else {}
    if not payload.get("facts"):
        raise ValueError(f"no companyfacts for {ticker} (CIK {cik_used})")
    meta["latest_accn"] = latest_accn(payload)

    t0 = time.perf_counter()
    subs = EdgarSubmissions(cik_used).fetch(force=force)
    meta["timings"]["edgar_submissions"] = round(time.perf_counter() - t0, 3)
    meta["sources"]["edgar_submissions"] = subs.freshness_record()
    from ..research.sector_fill import (normalize_sub_industry,
                                        sector_from_sic)
    sic, sic_desc = sic_from_submissions(subs.payload or {})
    meta["sic"], meta["sic_description"] = sic, sic_desc
    # sub_industry separates a mortgage REIT from an equity REIT (both file SIC 6798)
    # and a biotech from a pharma - but it must be the NORMALISED one. The raw universe
    # value is empty for every S&P 400/600 row (their index page carries no GICS data),
    # so resolving the profile before normalisation sent 8 of 16 Biotechnology companies
    # to STANDARD while the parquet showed them as Biotechnology, which reads as the code
    # contradicting its own output.
    _sub_for_profile = normalize_sub_industry(sub_industry or (sic_desc or ""))
    prof = pf.profile_for(sic, sector, _sub_for_profile)
    name = name or entity_name(subs.payload or {}) or entity_name(payload) or ticker

    t0 = time.perf_counter()
    M = mx.build_metrics(payload, profile=prof)
    meta["timings"]["normalize"] = round(time.perf_counter() - t0, 3)
    meta["warnings"].extend(M.warnings)

    market: dict = {}
    if with_market:
        t0 = time.perf_counter()
        src = YfMarket(ticker)
        if cached_market:
            # A SCORING change does not need fresher prices. Measured 2026-08-23 over a
            # sample of eight companies: `yf_market` is 76% of build_context's time -
            # mean 0.47s, median 0.01s, because it is a network fetch for whichever
            # companies' caches have aged out (KO 2.38s, NVDA 1.37s) and free for the
            # rest. Everything else in the stage table totals ~0.15s. So a re-score after
            # a rubric edit spends its time re-fetching data the edit did not touch.
            blob = src.latest_cached()
            market = market_metrics(blob or {})
            meta["sources"]["yf_market"] = {
                "source_id": "yf_market", "ok": bool(blob), "cached_only": True,
                "note": "cached market data by request (--cached-market): this run "
                        "re-scored, it did not refresh prices",
            }
            if not blob:
                # Loud, per the repo's rule: a company with no cached snapshot scores
                # with NO market data at all, and that is worth a warning rather than a
                # silently thinner scorecard.
                meta.setdefault("warnings", []).append(
                    f"{ticker}: --cached-market and no cached yf_market snapshot, so "
                    f"price, market cap and beta are absent from this scoring")
        else:
            res = src.fetch(force=force)
            blob = res.payload if isinstance(res.payload, dict) else src.latest_cached()
            market = market_metrics(blob or {})
            meta["sources"]["yf_market"] = res.freshness_record()
        meta["timings"]["yf_market"] = round(time.perf_counter() - t0, 3)

    prices: dict = {}
    if with_prices:
        t0 = time.perf_counter()
        df = yf_prices.load_prices(ticker)
        if df.empty:
            df = yf_prices.fetch_prices([ticker], force=force).get(ticker)
        prices = yf_prices.price_features(df) if df is not None else {}
        meta["timings"]["yf_prices"] = round(time.perf_counter() - t0, 3)
        if prices.get("price") and not market.get("price"):
            market["price"] = prices["price"]

    # Reconstructed P/E history. This is per-company and comes from artifacts
    # already on disk, so it does not depend on accumulated snapshots - which is
    # what previously left the own-history percentile NO_DATA for every company.
    peer_stats = dict(peers or {})
    if with_prices:
        t0 = time.perf_counter()
        try:
            from ..fundamentals import pe_history

            hist = pe_history.build(payload, yf_prices.load_prices(ticker))
            peer_stats.update(hist.stats())
        except Exception as exc:  # noqa: BLE001 - one component, never the whole symbol
            meta["warnings"].append(f"pe history failed: {type(exc).__name__}: {exc}")
        meta["timings"]["pe_history"] = round(time.perf_counter() - t0, 3)

    # F1: within-sector percentiles for the margin and returns metrics, so a utility is
    # judged against utilities rather than against a software threshold table.
    if sector_stats:
        from ..scoring import va as va_mod

        peer_stats.update(va_mod.sector_percentiles(sector_stats, M.as_flat()))

    # The qual cache is ALWAYS read; there is deliberately no flag to skip it.
    #
    # `with_qual=False` used to skip the read, so a quant-only re-score silently DELETED
    # the judgement half from the scorecard while the cached scores sat on disk
    # untouched. Re-scoring 208 companies to fix an unrelated sector bug took the LLM
    # half off 208 scorecards with it, twice in one afternoon, and the count of fully
    # scored companies fell 698 -> 465 with nothing reporting a failure.
    #
    # Safe to always read: the evidence pack does not consult ctx.qual, so this cannot
    # change a pack hash and invalidate the cache. Three JSON reads per company is
    # nothing against a ~40s generation.
    qual = load_qual(cik_used)
    meta["qual_components"] = sorted(qual.keys())

    # Falling back to the raw SIC DESCRIPTION put values like "Services-Prepackaged
    # Software" and "State Commercial Banks" in the sector column: 208 rows across 113
    # pseudo-sectors, so the Sectors sheet fragmented into 124 groups instead of 11 and
    # the sector-relative peer comparisons had almost no peers. sector_fill maps the SIC
    # CODE onto the same eleven GICS names the rest of the universe uses; the raw
    # description stays in meta["sic_description"] for auditing.
    resolved_sector = sector or sector_from_sic(sic) or ""
    # The SIC description is a SUB-INDUSTRY-grade label ("Semiconductors & Related
    # Devices", "State Commercial Banks"), so it belongs at the second level rather than
    # being discarded. Without it these 208 companies had an empty sub_industry and
    # therefore NO peer group at all, which silently disabled every peer-relative
    # valuation sub-test for them.
    #
    # ...and normalised onto the GICS name where one clearly exists, because leaving it
    # raw SPLITS real peer groups: the sheet showed "Semiconductors" (26 companies)
    # beside "Semiconductors & Related Devices" (9), and "Application Software" (33)
    # beside "Services-Prepackaged Software" (9). Two half groups read worse and score
    # worse, since the peer-median sub-tests need a minimum peer count. A SIC
    # description with no clear GICS counterpart is kept as-is.
    resolved_sub = normalize_sub_industry(sub_industry or (sic_desc or ""))

    ctx = SymbolContext(
        ticker=ticker, cik=cik_used, name=name, as_of=as_of,
        sector=resolved_sector, sub_industry=resolved_sub,
        profile=prof, metrics=M, market=market, prices=prices,
        peers=peer_stats, qual=qual,
    )
    return ctx, meta


def repair_bucket(component: str) -> str:
    return REPAIR_SPEC[component][0]


def _repair_fields(ctx: SymbolContext) -> dict:
    """What a second, targeted look contributed to this company - kept visible.

    Points backed by a verified quote are the only ones that reached a score; points the
    model offered without one are carried separately so the workbook can show both. A
    reader must never have to guess which half of the judgement came from the first call.
    """
    quoted_pts = unquoted_pts = 0
    quoted: list[str] = []
    unquoted: list[str] = []
    before = None
    for component in ("SG", "BQ", "MG"):
        payload = (ctx.qual or {}).get(component) or {}
        q, u = repaired_points(payload, component)
        quoted_pts += q
        unquoted_pts += u
        summary = repaired_summary(payload, repair_bucket(component))
        quoted += [f"{component.lower()}_{k}" for k in summary["quoted"]]
        unquoted += [f"{component.lower()}_{k}" for k in summary["unquoted"]]
        # The EARLIEST stamp wins. Taking the first component in iteration order let a
        # later SG pass overwrite BQ's true pre-repair coverage with an already-lifted
        # one, which would understate exactly what the column exists to show.
        stamp = payload.get("coverage_before_repair")
        if stamp is not None and (before is None or stamp < before):
            before = stamp
    return {
        "repaired_points_quoted": quoted_pts,
        "repaired_points_unquoted": unquoted_pts,
        "repaired_subtests": ", ".join(sorted(quoted)),
        "repaired_subtests_unquoted": ", ".join(sorted(unquoted)),
        "coverage_before_repair": before,
    }


def _dcf_fields(ctx: SymbolContext) -> dict:
    """The forward DCF's fair value, carried onto the row for the workbook.

    DISPLAY ONLY. `margin_of_safety` is not an input to any score and is not wired into
    the composite - E20 registered that decision, and scoring on it needs its own
    registration. It sits beside the score so the two can disagree in public: if the
    ranking says quality and the DCF says the price already assumes 20% growth forever,
    that disagreement is the useful output.

    The peer-median growth fallback is deliberately NOT applied here. It needs the whole
    cross-section, which a per-company scorer does not have; `clab/research/e20_forward_dcf.py`
    runs that second pass. A company that needs it shows no fair value on the row rather
    than one built from a number this function had to invent.
    """
    try:
        res = forward_dcf.analyse(ctx)
    except Exception as exc:                                # noqa: BLE001
        return {"dcf_reason": f"forward DCF failed: {type(exc).__name__}: {exc}"}
    return {
        "dcf_fair_value": res.get("fair_value_per_share"),
        "dcf_margin_of_safety": res.get("margin_of_safety"),
        "dcf_bear": (res.get("strip") or {}).get("bear"),
        "dcf_bull": (res.get("strip") or {}).get("bull"),
        "dcf_growth": res.get("growth") if isinstance(res.get("growth"), float) else None,
        "dcf_growth_basis": (res.get("growth_provenance") or {}).get("basis"),
        "dcf_wacc": res.get("wacc"),
        "dcf_implausible": res.get("implausible"),
        "dcf_shares_basis": (res.get("shares_provenance") or {}).get("basis"),
        "dcf_shares_disputed": (res.get("shares_provenance") or {}).get("disputed"),
        "dcf_shares_filed_vs_market": (res.get("shares_provenance") or {}).get("ratio"),
        "dcf_reason": res.get("reason"),
    }


def score_context(ctx: SymbolContext, meta: dict) -> composite.Scorecard:
    """Run all eight components. A component that raises becomes all-NO_DATA."""
    components = {}
    for code, module in COMPONENT_MODULES.items():
        t0 = time.perf_counter()
        try:
            components[code] = module.score(ctx)
        except Exception as exc:  # noqa: BLE001 - one bad component must not lose the other seven
            components[code] = composite.empty_component(
                code, f"scoring error: {type(exc).__name__}: {exc}")
            meta.setdefault("warnings", []).append(
                f"{code} scoring failed: {type(exc).__name__}: {exc}")
        meta.setdefault("timings", {})[f"score_{code}"] = round(time.perf_counter() - t0, 4)

    flat = {**ctx.metrics.as_flat(), **{k: v for k, v in ctx.market.items()},
            **{k: v for k, v in ctx.prices.items()}}
    # the reconstructed-P/E fields the entry component now turns on
    for key in ("pe_current", "pe_pctile_own", "pe_median_own", "pe_min_own",
                "pe_max_own", "pe_history_n", "pe_history_years"):
        flat[key] = ctx.peers.get(key)
    en_comp = components.get("EN")
    flat["en_best_timeframe_weight"] = _subtest_input(
        en_comp, "en_vs_emas", "best_timeframe_weight")
    flat["en_confluence"] = _subtest_input(
        en_comp, "en_confluence", "cheap_vs_own_history") and _subtest_input(
        en_comp, "en_confluence", "at_higher_timeframe_ema")
    flat["stress_verdict"] = _stress_verdict(components.get("BS"))
    flat["reverse_dcf_implied_growth"] = _dcf_field(components.get("VA"), "implied_growth")
    flat["reverse_dcf_wacc"] = _dcf_field(components.get("VA"), "wacc")
    flat["p_fcf"] = _subtest_input(components.get("VA"), "va_p_fcf", "p_fcf")
    flat["peg"] = _subtest_input(components.get("VA"), "va_peg", "peg")
    flat.update(_repair_fields(ctx))
    flat.update(_dcf_fields(ctx))

    # F3: carry the hysteresis state forward from the previous scorecard, so a band only
    # changes after BAND_CONFIRM_READINGS consecutive readings agree. A missing previous
    # scorecard is a first reading, which shows the raw band.
    prior = band_state(ctx.cik, ctx.ticker)      # (band, pending, streak, reading_date)

    return composite.build_scorecard(
        ticker=ctx.ticker, cik=ctx.cik, name=ctx.name, as_of=ctx.as_of,
        components=components, metrics=flat,
        data_through=ctx.metrics.raw("data_through"),
        price_as_of=ctx.prices.get("price_as_of") or ctx.market.get("price_as_of"),
        sector=ctx.sector, sub_industry=ctx.sub_industry, profile=ctx.profile.name,
        sources=meta.get("sources", {}), warnings=meta.get("warnings", []),
        prior_band=prior[0], prior_band_pending=prior[1], prior_band_streak=prior[2],
        prior_band_reading_date=prior[3],
    )


def band_state(cik: str, ticker: str) -> tuple[str | None, str | None, int, str | None]:
    """The F3 state left by the previous crawl: (band shown, pending, streak).

    Reads the stored scorecard rather than replaying history, so a crawl stays O(1) per
    company. A scorecard written before F3 existed has no `band_pending`, and its stored
    `band` is by definition the raw band - that is a valid starting state, so an upgrade
    does not reset every company's hysteresis to "first reading".
    """
    prev = load_scorecard(cik, ticker)
    if not isinstance(prev, dict):
        return None, None, 0, None
    band = prev.get("band")
    if not isinstance(band, str) or not band:
        return None, None, 0, None
    streak = prev.get("band_pending_streak")
    # E27: the date of the reading that produced the stored band. A scorecard written
    # before E27 has none, which reads as "a different day" and lets the first run after
    # the fix behave exactly as it did before - no company gets frozen by the upgrade.
    reading_date = prev.get("band_reading_date")
    if not isinstance(reading_date, str):
        reading_date = (prev.get("as_of") or "")[:10] or None
    return (band,
            prev.get("band_pending") if isinstance(prev.get("band_pending"), str)
            else None,
            int(streak) if isinstance(streak, (int, float)) else 0,
            reading_date)


def score_symbol(ticker: str, cik: str, *, as_of: str | None = None, **kw):
    """Full pipeline for one symbol. Returns (Scorecard, meta)."""
    as_of = as_of or utc_now_iso()
    ctx, meta = build_context(ticker, cik, as_of=as_of, **kw)
    card = score_context(ctx, meta)
    return card, meta


def write_scorecard(card: composite.Scorecard) -> None:
    """Persist the scorecard, plus an immutable history copy for delta detection."""
    payload = card.to_dict()
    atomic_write_json(config.SCORECARD_DIR / f"{card.cik}_{card.ticker}.json", payload)
    day = (card.as_of or "")[:10] or "unknown"
    atomic_write_json(config.SCORECARD_HISTORY_DIR / f"{card.cik}_{day}.json", payload)


def load_scorecard(cik: str, ticker: str) -> dict | None:
    return read_json(config.SCORECARD_DIR / f"{cik}_{ticker}.json")


# ------------------------------------------------------------------ small readers
def _find_subtest(comp, key):
    if comp is None:
        return None
    for st in comp.subtests:
        if st.key == key:
            return st
    return None


def _stress_verdict(comp):
    st = _find_subtest(comp, "bs_stress_test")
    return (st.inputs or {}).get("verdict") if st else None


def _dcf_field(comp, field):
    st = _find_subtest(comp, "va_reverse_dcf")
    return (st.inputs or {}).get(field) if st else None


def _subtest_input(comp, key, field):
    st = _find_subtest(comp, key)
    return (st.inputs or {}).get(field) if st else None
