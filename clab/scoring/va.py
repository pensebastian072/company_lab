"""VA - Valuation /15.

Allocation (rubric A4, unspecified): relative multiples 7, PEG 3, reverse DCF 5.

The load-bearing honesty rule here: a missing comparison is NO_DATA, never
"cheap". Own-5Y-average percentiles need history that only accumulates as the
date-partitioned yfinance snapshots pile up, and sub-industry medians need at
least VA_MIN_PEERS scored peers. Where neither exists the sub-test abstains
rather than flattering the company.
"""
from __future__ import annotations

from . import reverse_dcf, rubric
from .context import SymbolContext, num, pct, subtest
from .types import ComponentScore

CODE = "VA"


def _percentile_points(pctile: float | None, max_points: int):
    """Cheap relative to its own history = points."""
    if pctile is None:
        return None, ""
    if pctile <= rubric.VA_PERCENTILE_CHEAP:
        pts = max_points
        why = f"in the cheapest {rubric.VA_PERCENTILE_CHEAP:.0%} of its own history"
    elif pctile <= rubric.VA_PERCENTILE_RICH:
        pts = max(max_points - 1, 0)
        why = "mid-range versus its own history"
    else:
        pts = 0
        why = f"in the richest {1 - rubric.VA_PERCENTILE_RICH:.0%} of its own history"
    return pts, f"percentile {pctile:.2f}: {why}"


def _vs_peer_points(mine: float | None, peer_median: float | None, n_peers: int,
                    max_points: int):
    if mine is None or peer_median is None or peer_median <= 0:
        return None, ""
    if n_peers < rubric.VA_MIN_PEERS:
        return None, f"only {n_peers} scored peers (<{rubric.VA_MIN_PEERS})"
    ratio = mine / peer_median
    if ratio <= 0.8:
        pts, why = max_points, "20%+ below the sub-industry median"
    elif ratio <= 1.1:
        pts, why = max(max_points - 1, 0), "near the sub-industry median"
    else:
        pts, why = 0, "above the sub-industry median"
    return pts, f"{num(mine)} vs peer median {num(peer_median)} ({ratio:.2f}x): {why}"


def score(ctx: SymbolContext) -> ComponentScore:
    M = ctx.metrics
    peers = ctx.peers or {}
    sts = []

    # ------------------------------------------------------------ P/E vs own history /2
    pe = ctx.mk("pe")
    pctile = peers.get("pe_pctile_own")
    pts, why = _percentile_points(pctile, 2)
    sts.append(subtest(
        ctx, "va_pe_vs_own_history", "P/E vs its own history", 2,
        value=pctile, points=pts,
        inputs={"pe": pe, "pe_current": peers.get("pe_current"),
                "pe_pctile_own_history": pctile,
                "pe_own_median": peers.get("pe_median_own"),
                "pe_min_own": peers.get("pe_min_own"),
                "pe_max_own": peers.get("pe_max_own"),
                "n_history_points": peers.get("pe_history_n"),
                "history_years": peers.get("pe_history_years")},
        provenance={"source": "derived",
                    "formula": "close / TTM diluted EPS, EPS applied from its filing date",
                    "inputs_from": ["yfinance daily closes",
                                    "EDGAR EarningsPerShareDiluted"]},
        note=why,
        na_reason=(peers.get("pe_history_note")
                   or "no positive-earnings history to build a P/E series from"),
    ))

    # ------------------------------------------------------------ forward P/E /1
    fwd = ctx.mk("fwd_pe")
    growth = ctx.mk("analyst_growth_1y")
    if fwd is not None and fwd > 0:
        if growth is not None and growth > 0 and fwd <= 25 and growth > 0.10:
            pts, why = 1, f"forward P/E {num(fwd)} against {pct(growth)} expected growth"
        elif fwd <= 18:
            pts, why = 1, f"forward P/E {num(fwd)} is absolutely modest"
        else:
            pts, why = 0, f"forward P/E {num(fwd)} not supported by expected growth"
    else:
        pts, why = None, ""
    sts.append(subtest(
        ctx, "va_fwd_pe", "Forward P/E vs growth", 1, value=fwd, points=pts,
        inputs={"fwd_pe": fwd, "analyst_growth_1y": growth},
        provenance={"source": "yfinance"}, note=why,
    ))

    # ------------------------------------------------------------ EV multiples vs peers /3
    for key, label, mx, mkey, pkey in (
        ("va_ev_ebitda_vs_peers", "EV/EBITDA vs sub-industry", 2, "ev_ebitda", "ev_ebitda"),
        ("va_ev_sales_vs_peers", "EV/Sales vs sub-industry", 1, "ev_sales", "ev_sales"),
    ):
        mine = ctx.mk(mkey)
        med = peers.get(f"{pkey}_peer_median")
        n = int(peers.get(f"{pkey}_peer_n", 0) or 0)
        pts, why = _vs_peer_points(mine, med, n, mx)
        sts.append(subtest(
            ctx, key, label, mx, value=mine if pts is not None else None, points=pts,
            inputs={mkey: mine, "peer_median": med, "n_peers": n,
                    "sub_industry": ctx.sub_industry},
            provenance={"source": "yfinance + peer set computed across the scored universe"},
            note=why,
            na_reason=("enterprise value is not defined for this filer type"
                       if ctx.profile.na_candidate(key)
                       else f"fewer than {rubric.VA_MIN_PEERS} scored peers in this sub-industry"),
        ))

    # ------------------------------------------------------------ P/FCF /1
    mc, fcf = ctx.mk("market_cap"), M.raw("fcf_ttm")
    p_fcf = (mc / fcf) if (mc is not None and fcf not in (None, 0) and fcf > 0) else None
    pts = rubric.band_from_thresholds_asc(p_fcf, rubric.VA_P_FCF_BANDS, (1, 1, 0, 0))
    sts.append(subtest(
        ctx, "va_p_fcf", "P/FCF absolute and vs history", 1, value=p_fcf, points=pts,
        inputs={"p_fcf": p_fcf, "market_cap": mc, "fcf_ttm": fcf},
        prov_keys=("fcf_ttm",),
        note=f"P/FCF {num(p_fcf)} vs bands {rubric.VA_P_FCF_BANDS}",
    ))

    # ------------------------------------------------------------ PEG /3
    sts.append(_peg(ctx))

    # ------------------------------------------------------------ reverse DCF /5
    dcf = reverse_dcf.analyse(ctx)
    sts.append(subtest(
        ctx, "va_reverse_dcf", "Reverse DCF: growth the price requires", 5,
        value=dcf.get("implied_growth"), points=dcf.get("points"),
        inputs=dcf,
        provenance={"source": "derived", "assumed": ["wacc", "terminal_growth",
                                                     "equity_risk_premium", "fade_path"]},
        note=dcf.get("note", dcf.get("reason", "")),
        na_reason=dcf.get("reason", "reverse DCF not computable"),
    ))

    comp = ComponentScore(
        code=CODE, label=rubric.COMPONENTS[CODE][0],
        max_points=rubric.COMPONENTS[CODE][1], subtests=sts,
        note=("Relative multiples 7 / PEG 3 / reverse DCF 5. A missing comparison "
              "abstains - it never counts as cheap."),
    )
    comp.check_points()
    return comp


def _peg(ctx: SymbolContext):
    """Growth-adjusted P/E. A clue, not a verdict - which is why it is 3 of 15."""
    fwd = ctx.mk("fwd_pe") or ctx.mk("pe")
    growth = ctx.mk("analyst_growth_1y")
    if growth is None:
        growth = ctx.metrics.raw("eps_cagr_3y")
    vendor = ctx.mk("peg_vendor")

    peg = None
    basis = ""
    if fwd is not None and growth is not None and growth > 0:
        peg = fwd / (growth * 100.0)
        basis = "forward P/E / (expected growth x 100)"
    elif vendor is not None and vendor > 0:
        peg, basis = vendor, "vendor trailing PEG"

    pts = rubric.band_from_thresholds_asc(peg, rubric.VA_PEG_BANDS, (3, 2, 1, 0))
    if peg is not None and growth is not None and growth <= 0:
        pts = None      # PEG is undefined for a shrinking company; do not score it 0
    return subtest(
        ctx, "va_peg", "Growth-adjusted P/E (PEG)", 3,
        value=peg, points=pts,
        inputs={"peg": peg, "fwd_pe": fwd, "growth": growth, "peg_vendor": vendor,
                "basis": basis},
        provenance={"source": "yfinance"},
        note=f"PEG {num(peg)} via {basis} vs bands {rubric.VA_PEG_BANDS}",
        na_reason="no positive expected growth rate, so PEG is undefined",
    )


def sector_stats(rows: list[dict]) -> dict[str, dict]:
    """Percentile of each margin/returns metric WITHIN sector (F1, from E03 R1).

    `rows` are flat table rows. Returns sector -> {metric_values: sorted list,
    metric_sector_n} so a per-company percentile can be computed without keeping the
    whole panel around. Higher is better for all five metrics, so the percentile is the
    share of peers at or below the company's value.
    """
    buckets: dict[str, dict[str, list[float]]] = {}
    metrics = ("gross_margin", "operating_margin", "fcf_margin", "roic", "roe")
    for r in rows:
        sec = (r.get("sector") or "").strip()
        if not sec:
            continue
        b = buckets.setdefault(sec, {})
        for m in metrics:
            v = r.get(m)
            if isinstance(v, (int, float)) and v is not None and -5 < v < 20:
                b.setdefault(m, []).append(float(v))
    out: dict[str, dict] = {}
    for sec, mv in buckets.items():
        entry: dict = {}
        for m, vals in mv.items():
            vals.sort()
            entry[f"{m}_sector_values"] = vals
            entry[f"{m}_sector_n"] = len(vals)
        out[sec] = entry
    return out


def sector_percentiles(sector_entry: dict, metrics: dict) -> dict:
    """Turn a company's raw metrics into within-sector percentiles.

    The company's OWN value is filtered on the same `-5 < v < 20` band that governs the
    sector distribution above. Until 2026-08-16 it was not: the distribution was cleaned
    and the company's value was not, so a filer with `roic = 10000` landed at
    `bisect_right -> percentile 1.0` and took FULL sector-relative marks in `fe.py`. Bad
    data did not merely add noise, it earned points.

    `metrics.py` now nulls an implausible metric at source, so this is a second line of
    defence for rows that arrive from a cached scorecard written before that existed.
    """
    out: dict = {}
    for m in ("gross_margin", "operating_margin", "fcf_margin", "roic", "roe"):
        vals = (sector_entry or {}).get(f"{m}_sector_values")
        v = metrics.get(m)
        if not vals or v is None:
            continue
        if not isinstance(v, (int, float)) or not (-5 < v < 20):
            continue
        import bisect

        rank = bisect.bisect_right(vals, float(v))
        out[f"{m}_sector_pctile"] = rank / len(vals)
        out[f"{m}_sector_n"] = len(vals)
    return out


def peer_stats(rows: list[dict]) -> dict[str, dict]:
    """Sub-industry medians across the scored universe. Computed once per crawl.

    `rows` are flat table rows (Scorecard.table_row output). Returns
    sub_industry -> {metric_peer_median, metric_peer_n}.
    """
    import statistics

    buckets: dict[str, dict[str, list[float]]] = {}
    for r in rows:
        si = (r.get("sub_industry") or "").strip() or (r.get("sector") or "").strip()
        if not si:
            continue
        b = buckets.setdefault(si, {})
        for metric in ("ev_ebitda", "ev_sales", "pe", "p_fcf"):
            v = r.get(metric)
            if isinstance(v, (int, float)) and v is not None and 0 < v < 1000:
                b.setdefault(metric, []).append(float(v))
    out: dict[str, dict] = {}
    for si, metrics in buckets.items():
        entry: dict = {}
        for metric, vals in metrics.items():
            entry[f"{metric}_peer_median"] = statistics.median(vals) if vals else None
            entry[f"{metric}_peer_n"] = len(vals)
        out[si] = entry
    return out


def own_history_stats(ticker: str, snapshots: list[dict]) -> dict:
    """Percentile of the current multiple within this company's own stored history.

    Fed from journal/snapshots/*.parquet, which is why the weekly snapshot task
    starts on day one: this sub-test is unavailable until history exists, and it
    abstains rather than guessing in the meantime.
    """
    series = [s.get("pe") for s in snapshots
              if s.get("ticker") == ticker and isinstance(s.get("pe"), (int, float))
              and 0 < s["pe"] < 1000]
    if len(series) < 8:
        return {"pe_history_n": len(series)}
    current = series[-1]
    below = sum(1 for v in series if v <= current)
    import statistics
    return {
        "pe_pctile_own": below / len(series),
        "pe_median_own": statistics.median(series),
        "pe_history_n": len(series),
    }
