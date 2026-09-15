"""Point-in-time score panel: the measured half, recomputed monthly through history.

Pre-registered in journal/experiments/E02_measured_half_battery_preregistration.md.

The panel calls the PRODUCTION scoring functions (`scoring.fe/bs/va/en`) against
historical inputs rather than reimplementing them, so a result is a statement about
the real scorer and not about a lookalike written for the study.

Point-in-time discipline:
  * fundamentals use the `as_first_filed` view - the value as first reported, never a
    restatement published later;
  * a quarter enters only from its FILING date, so metrics are rebuilt at each filing
    date and held forward to month-ends;
  * P/E percentile ranks against the trailing 5 years up to t;
  * weekly and monthly EMAs use completed bars only;
  * peer medians at t come from companies that had a score at t.

Not reconstructible, therefore absent: ER (needs historical consensus estimates),
PEG and forward P/E (same), reverse DCF (needs a historical beta and risk-free), and
the entire LLM half. Scores are reported as a percentage of points AVAILABLE at that
date, never as a fraction of 100.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .. import config
from ..fundamentals import metrics as mx
from ..fundamentals import normalize as nz
from ..fundamentals import pe_history
from ..fundamentals import profile as pf
from ..fundamentals.metrics import MetricBundle
from ..net import trust_windows_certs, utc_now_iso
from ..scoring import bs as bs_mod
from ..scoring import en as en_mod
from ..scoring import fe as fe_mod
from ..scoring import rubric
from ..scoring import va as va_mod
from ..scoring.context import SymbolContext
from ..sources import yf_prices
from ..sources.edgar_facts import (EdgarSubmissions, resolve_facts,
                                   sic_from_submissions)
from . import entry_study as es

START = "2016-01-01"
MIN_FILINGS = 8


# ------------------------------------------------------------------ as-of filtering
def filed_dates(payload: dict) -> list[str]:
    """Every distinct filing date in the blob, ascending."""
    seen: set[str] = set()
    facts = (payload or {}).get("facts", {})
    for tax in facts.values():
        for body in tax.values():
            for rows in (body.get("units") or {}).values():
                for r in rows:
                    f = r.get("filed")
                    if f:
                        seen.add(f[:10])
    return sorted(seen)


def payload_asof(payload: dict, asof: str) -> dict:
    """A copy of the blob containing only rows filed on or before `asof`.

    This is what makes the panel point-in-time. Filtering the nested structure is
    cheap relative to the metric build that follows.
    """
    out_facts: dict = {}
    for tax, tags in (payload or {}).get("facts", {}).items():
        new_tags = {}
        for tag, body in tags.items():
            new_units = {}
            for unit, rows in (body.get("units") or {}).items():
                kept = [r for r in rows if (r.get("filed") or "9999") <= asof]
                if kept:
                    new_units[unit] = kept
            if new_units:
                new_tags[tag] = {**body, "units": new_units}
        if new_tags:
            out_facts[tax] = new_tags
    return {**{k: v for k, v in (payload or {}).items() if k != "facts"},
            "facts": out_facts}


# ------------------------------------------------------------------ per symbol
@dataclass
class SymbolHistory:
    ticker: str
    cik: str
    sector: str = ""
    sub_industry: str = ""
    rows: list[dict] = field(default_factory=list)
    ok: bool = True
    note: str = ""
    price_source: str = "yfinance"


def _month_ends(index: pd.DatetimeIndex) -> list[pd.Timestamp]:
    if len(index) == 0:
        return []
    s = pd.Series(1, index=index)
    return list(s.resample("ME").last().dropna().index)


def build_symbol_history(ticker: str, cik: str, *, sector: str = "",
                         sub_industry: str = "", allow_archive: bool = False,
                         last_date: pd.Timestamp | None = None) -> SymbolHistory:
    """FE and BS at every filing date; VA and EN inputs at every month-end.

    `allow_archive` lets a DELISTED name fall through to the price archive that retains
    it. `last_date` truncates the history at the date the company left the index, so a
    removed constituent contributes only the months it was actually a member.
    """
    hist = SymbolHistory(ticker, cik, sector, sub_industry)

    if allow_archive:
        from ..sources import archive_prices

        px, src = archive_prices.load_prices_any(ticker)
        hist.price_source = src
    else:
        px = yf_prices.load_prices(ticker)
        hist.price_source = "yfinance"
    if px is None or px.empty:
        hist.ok, hist.note = False, "no prices"
        return hist
    px = px.copy()
    px["date"] = pd.to_datetime(px["date"], errors="coerce")
    px = px.dropna(subset=["date", "close"]).set_index("date").sort_index()
    close = px["close"].astype(float)
    suspects = es.suspect_mask(close)

    facts_res, cik_used, _n = resolve_facts(cik)
    payload = facts_res.payload if isinstance(facts_res.payload, dict) else {}
    if not payload.get("facts"):
        hist.ok, hist.note = False, "no companyfacts"
        return hist

    subs = EdgarSubmissions(cik_used).fetch()
    sic, _desc = sic_from_submissions(subs.payload or {})
    prof = pf.profile_for(sic, sector)

    fdates = [d for d in filed_dates(payload) if d >= "2013-01-01"]
    if len(fdates) < MIN_FILINGS:
        hist.ok, hist.note = False, f"only {len(fdates)} filing dates"
        return hist

    # FE and BS depend on fundamentals alone -> compute once per filing date
    fund: dict[str, dict] = {}
    for d in fdates:
        sub_payload = payload_asof(payload, d)
        M = mx.build_metrics(sub_payload, profile=prof, view="as_first_filed")
        ctx = SymbolContext(ticker=ticker, cik=cik_used, sector=sector,
                            sub_industry=sub_industry, profile=prof, metrics=M)
        try:
            fe_c = fe_mod.score(ctx)
            bs_c = bs_mod.score(ctx)
        except Exception:  # noqa: BLE001 - a bad vintage must not kill the symbol
            continue
        # F1 needs a cross-section that does not exist yet at filing-vintage time, so
        # FE is split: the sector-relative sub-tests are kept separately (with their
        # absolute-basis points as the fallback) and recomputed in score_panel once the
        # month's sector distribution is known.
        sec_earned = sec_avail = 0
        rest_earned = rest_avail = 0
        sec_scored: list[str] = []
        for st in fe_c.subtests:
            is_sec = st.key in rubric.SECTOR_RELATIVE_METRICS
            scored = st.status.value == "scored"
            earned = st.effective or 0 if scored else 0
            avail = st.max_points if scored else 0
            if is_sec:
                sec_earned += earned
                sec_avail += avail
                if scored:
                    # F1 may only rescore a sub-test the real scorer actually scored;
                    # a NOT_APPLICABLE gross margin at a bank must stay unavailable or
                    # the sector-relative pass would hand banks free points.
                    sec_scored.append(st.key)
            else:
                rest_earned += earned
                rest_avail += avail
        fund[d] = {
            "fe": fe_c.earned_points, "fe_avail": fe_c.available_points,
            "fe_rest": rest_earned, "fe_rest_avail": rest_avail,
            "fe_sector_abs": sec_earned, "fe_sector_avail": sec_avail,
            "fe_sector_scored": ",".join(sec_scored),
            "bs": bs_c.earned_points, "bs_avail": bs_c.available_points,
            "M": M, "profile": prof.name,
        }
    if not fund:
        hist.ok, hist.note = False, "no usable fundamental vintages"
        return hist

    # price-dependent pieces, monthly
    peh = pe_history.build(payload, px.reset_index(), view="as_first_filed",
                           lookback_years=15)
    pctile = (es.rolling_pe_percentile(peh.series).reindex(close.index).ffill()
              if len(peh) else pd.Series(index=close.index, dtype=float))
    emas = es.timeframe_ema_frame(close)

    vintages = sorted(fund.keys())
    for me in _month_ends(close.index):
        if me < pd.Timestamp(START):
            continue
        # a removed constituent contributes only the months it was actually a member
        if last_date is not None and me > last_date:
            continue
        v = None
        for d in reversed(vintages):
            if pd.Timestamp(d) <= me:
                v = d
                break
        if v is None:
            continue
        M: MetricBundle = fund[v]["M"]
        price = float(close.loc[:me].iloc[-1])
        shares = M.raw("diluted_shares_ttm")
        mcap = price * shares if (shares and shares > 0) else None
        nd = M.raw("net_debt")
        ev = (mcap + nd) if (mcap is not None and nd is not None) else None
        ebitda, rev, fcf = M.raw("ebitda_ttm"), M.raw("revenue_ttm"), M.raw("fcf_ttm")
        pc = pctile.loc[:me].iloc[-1] if len(pctile.loc[:me]) else np.nan

        row = {
            "ticker": ticker, "cik": cik_used, "date": me,
            "sector": sector, "sub_industry": sub_industry,
            "profile": fund[v]["profile"], "vintage": v,
            "price_source": hist.price_source,
            "in_index_today": last_date is None,
            "fe": fund[v]["fe"], "fe_avail": fund[v]["fe_avail"],
            "fe_rest": fund[v]["fe_rest"], "fe_rest_avail": fund[v]["fe_rest_avail"],
            "fe_sector_abs": fund[v]["fe_sector_abs"],
            "fe_sector_avail": fund[v]["fe_sector_avail"],
            "fe_sector_scored": fund[v]["fe_sector_scored"],
            "bs": fund[v]["bs"], "bs_avail": fund[v]["bs_avail"],
            # the five scalars F1 scores relative to sector
            "gross_margin": M.raw("gross_margin"),
            "fcf_margin": M.raw("fcf_margin"),
            "roe": M.raw("roe"),
            "price": price, "market_cap": mcap,
            "ev": ev,
            "ev_ebitda": (ev / ebitda) if (ev and ebitda and ebitda > 0) else None,
            "ev_sales": (ev / rev) if (ev and rev and rev > 0) else None,
            "p_fcf": (mcap / fcf) if (mcap and fcf and fcf > 0) else None,
            "pe_pctile_own": None if pd.isna(pc) else float(pc),
            "revenue_cagr_3y": M.raw("revenue_cagr_3y"),
            "operating_margin": M.raw("operating_margin"),
            "roic": M.raw("roic"),
            "fcf_ttm": fcf, "revenue_ttm": rev,
        }
        for tf in ("daily", "weekly", "monthly"):
            for span in (20, 72):
                col = f"ema{span}_{tf}"
                sl = emas[col].loc[:me]
                row[col] = float(sl.iloc[-1]) if len(sl) and pd.notna(sl.iloc[-1]) else None
        # forward returns, dropping windows that straddle an implausible print
        for h, bars in (("1y", 252), ("3y", 756)):
            row[f"fwd_{h}"] = es.forward_return(close, close.loc[:me].index[-1],
                                                bars, suspects)
        hist.rows.append(row)
    return hist


# ------------------------------------------------------------------ scoring pass
#: F1 sub-test -> (panel metric column, max points). Maxima are READ FROM THE RUBRIC, not
#: restated here: a reweighting that changed a sub-test max while this table kept the old
#: number would silently mis-scale FE, which is exactly the bug check_points() caught once
#: already. The panel needs the table at all only because it scores FE per filing vintage,
#: before the month's cross-section exists.
_FE_SUBTEST_MAX = {f"fe_{k}": mx for k, _label, mx in rubric.FE_SUBTESTS}
_SECTOR_SUBTEST_MAX = {
    key: (key[len("fe_"):], _FE_SUBTEST_MAX[key])
    for key in rubric.SECTOR_RELATIVE_METRICS
}
assert set(_SECTOR_SUBTEST_MAX) == set(rubric.SECTOR_RELATIVE_METRICS)


def _sector_distributions(grp: pd.DataFrame,
                          sector_col: str = "sector") -> dict[str, dict[str, list]]:
    """Per-sector sorted values for each F1 metric, from THIS month's cross-section."""
    out: dict[str, dict[str, list]] = {}
    scored = grp.get("fe_sector_scored")
    for sec, sgrp in grp.groupby(sector_col):
        entry: dict[str, list] = {}
        for _key, (metric, _mx) in _SECTOR_SUBTEST_MAX.items():
            if metric not in sgrp:
                continue
            col = sgrp[metric]
            if scored is not None:
                # the percentile denominator is the peers the metric was scored for,
                # so a sector's NOT_APPLICABLE filers do not shift everyone's rank
                col = col[sgrp["fe_sector_scored"].fillna("").str.contains(
                    _key, regex=False)]
            vals = col.dropna()
            vals = vals[(vals > -5) & (vals < 20)].tolist()
            vals.sort()
            entry[metric] = vals
        out[str(sec)] = entry
    return out


def _fe_sector_relative(row, dists: dict,
                        sector_col: str = "sector") -> tuple[int, int, str]:
    """(earned, available, basis) for the five F1 sub-tests, sector-relative.

    Falls back to the stored absolute-basis points when the sector has too few peers,
    which is the same rule the live scorer applies.
    """
    import bisect

    sec = str(row.get(sector_col) or "")
    entry = dists.get(sec, {})
    scored_keys = set(str(row.get("fe_sector_scored") or "").split(","))
    earned = avail = 0
    used_relative = False
    for _key, (metric, mx) in _SECTOR_SUBTEST_MAX.items():
        v = row.get(metric)
        vals = entry.get(metric) or []
        if _key not in scored_keys:
            continue        # NOT_APPLICABLE / NO_DATA in the real scorer: stays that way
        if v is None or pd.isna(v):
            continue                                  # NO_DATA stays NO_DATA
        if len(vals) < rubric.SECTOR_RELATIVE_MIN_PEERS:
            return (int(row.get("fe_sector_abs") or 0),
                    int(row.get("fe_sector_avail") or 0), "absolute")
        pctile = bisect.bisect_right(vals, float(v)) / len(vals)
        ladder = {2: (2, 2, 1, 0), 1: (1, 1, 0, 0)}[mx]
        pts = rubric.band_from_thresholds(pctile, rubric.SECTOR_PCTILE_BANDS, ladder)
        earned += pts or 0
        avail += mx
        used_relative = True
    if not used_relative:
        return (int(row.get("fe_sector_abs") or 0),
                int(row.get("fe_sector_avail") or 0), "absolute")
    return earned, avail, "sector_relative"


def score_panel(df: pd.DataFrame, *, sector_relative: bool = False,
                sector_col: str = "sector") -> pd.DataFrame:
    """Add VA and EN using peer medians computed WITHIN each month.

    With sector_relative=True the five F1 sub-tests inside FE are also recomputed
    against the month's own sector distribution (E05 F1). `sector_col` chooses the sector
    definition, which matters: the GICS sector is missing for every removed constituent.
    """
    if sector_relative:
        # A MISSING column is a wiring bug, not thin data, and the fallback would hide it:
        # fe_sector_scored was computed but not copied onto the row once, every sector
        # distribution filtered to zero peers, and all 67,889 rows silently scored on the
        # absolute basis while the run reported success. Fail loudly instead.
        for col in ("fe_sector_scored", "fe_rest", "fe_rest_avail"):
            if col not in df.columns:
                raise ValueError(
                    f"sector_relative=True needs the {col!r} column; without it every "
                    f"row falls back to the absolute basis and F1 is silently not "
                    f"applied")
        if sector_col not in df.columns:
            raise ValueError(f"sector column {sector_col!r} is not on the panel")

    out_rows = []
    for date, grp in df.groupby("date"):
        sector_dists = (_sector_distributions(grp, sector_col) if sector_relative else {})
        # peer medians from companies that had a score at this date, not the final set
        peers_by_si: dict[str, dict] = {}
        for si, sgrp in grp.groupby("sub_industry"):
            entry = {}
            for metric in ("ev_ebitda", "ev_sales", "pe", "p_fcf"):
                vals = sgrp[metric].dropna() if metric in sgrp else pd.Series(dtype=float)
                vals = vals[(vals > 0) & (vals < 1000)]
                entry[f"{metric}_peer_median"] = float(vals.median()) if len(vals) else None
                entry[f"{metric}_peer_n"] = int(len(vals))
            peers_by_si[si] = entry

        for _i, r in grp.iterrows():
            M = MetricBundle()
            for k in ("fcf_ttm", "revenue_ttm", "operating_margin", "roic",
                      "revenue_cagr_3y"):
                M.set(k, r.get(k))
            M.set("eps_cagr_3y", None)
            prof = pf.PROFILES.get(r.get("profile") or "STANDARD",
                                   pf.PROFILES[pf.STANDARD])
            prices = {"price": r["price"]}
            for tf in ("daily", "weekly", "monthly"):
                for span in (20, 72):
                    prices[f"ema{span}_{tf}"] = r.get(f"ema{span}_{tf}")
            peers = dict(peers_by_si.get(r.get("sub_industry") or "", {}))
            peers["pe_pctile_own"] = r.get("pe_pctile_own")
            market = {"market_cap": r.get("market_cap"), "ev": r.get("ev"),
                      "ev_ebitda": r.get("ev_ebitda"), "ev_sales": r.get("ev_sales"),
                      "pe": None, "fwd_pe": None, "beta": None,
                      "analyst_growth_1y": None, "analyst_growth_3y": None}
            ctx = SymbolContext(ticker=r["ticker"], cik=r["cik"], profile=prof,
                                metrics=M, market=market, prices=prices, peers=peers,
                                sector=r.get("sector", ""),
                                sub_industry=r.get("sub_industry", ""))
            try:
                va_c = va_mod.score(ctx)
                en_c = en_mod.score(ctx)
            except Exception:  # noqa: BLE001
                continue
            rec = dict(r)
            rec.update({"va": va_c.earned_points, "va_avail": va_c.available_points,
                        "en": en_c.earned_points, "en_avail": en_c.available_points})
            if sector_relative:
                sec_e, sec_a, basis = _fe_sector_relative(r, sector_dists, sector_col)
                rec["fe"] = int(r.get("fe_rest") or 0) + sec_e
                rec["fe_avail"] = int(r.get("fe_rest_avail") or 0) + sec_a
                rec["fe_basis"] = basis
            else:
                rec["fe_basis"] = "absolute"
            earned = rec["fe"] + rec["bs"] + rec["va"] + rec["en"]
            avail = (rec["fe_avail"] + rec["bs_avail"] + rec["va_avail"]
                     + rec["en_avail"])
            rec["measured_earned"] = earned
            rec["measured_avail"] = avail
            rec["measured_pct"] = (earned / avail) if avail else None
            out_rows.append(rec)
    out = pd.DataFrame(out_rows)
    if sector_relative and len(out):
        share = float((out.fe_basis == "sector_relative").mean())
        if share == 0.0:
            raise ValueError(
                "sector_relative=True produced ZERO sector-relative rows. Every row fell "
                "back to the absolute basis, so F1 was not applied. Check that "
                "fe_sector_scored is populated and that sectors have at least "
                f"{rubric.SECTOR_RELATIVE_MIN_PEERS} scored peers per month.")
        if share < 0.5:
            print(f"  WARNING: only {share:.1%} of rows scored on the sector-relative "
                  f"basis; the rest fell back to absolute", flush=True)
    return out


def apply_sector_relative(df: pd.DataFrame,
                          sector_col: str = "sector") -> pd.DataFrame:
    """Recompute ONLY the F1 half of FE on an already-scored panel.

    Exists so the sector DEFINITION can be varied without paying for another crawl. The
    GICS sector is missing for every removed constituent (15.4% of rows), which would put
    them all in one pseudo-sector mixing utilities with software - and F1 is a sector fix,
    so that would measure it against a fake sector variable.

    VA and EN are untouched: they depend on sub-industry peer medians, not on sector, so
    recomputing them here would only burn time and risk drift from the stored arm.
    """
    need = {"fe_rest", "fe_rest_avail", "fe_sector_abs", "fe_sector_avail",
            "fe_sector_scored", "bs", "bs_avail", "va", "va_avail", "en", "en_avail"}
    missing = need - set(df.columns)
    if missing:
        raise ValueError(f"panel is missing columns needed to re-score FE: "
                         f"{sorted(missing)}")

    out = []
    for _date, grp in df.groupby("date"):
        dists = _sector_distributions(grp, sector_col)
        for _i, r in grp.iterrows():
            sec_e, sec_a, basis = _fe_sector_relative(r, dists, sector_col)
            rec = dict(r)
            rec["fe"] = int(r.get("fe_rest") or 0) + sec_e
            rec["fe_avail"] = int(r.get("fe_rest_avail") or 0) + sec_a
            rec["fe_basis"] = basis
            earned = rec["fe"] + rec["bs"] + rec["va"] + rec["en"]
            avail = (rec["fe_avail"] + rec["bs_avail"] + rec["va_avail"]
                     + rec["en_avail"])
            rec["measured_earned"] = earned
            rec["measured_avail"] = avail
            rec["measured_pct"] = (earned / avail) if avail else None
            out.append(rec)
    res = pd.DataFrame(out)
    if len(res) and float((res.fe_basis == "sector_relative").mean()) == 0.0:
        raise ValueError(
            "apply_sector_relative produced ZERO sector-relative rows: every row fell "
            "back to the absolute basis, so nothing was re-scored. Check that "
            "fe_sector_scored is populated on the panel.")
    return res


# ------------------------------------------------------------------ build
def removed_constituents() -> list[dict]:
    """The companies that LEFT the index, with a CIK and the date they left.

    These are the 29.7% of the study window that every earlier result omitted. Their
    prices come from the delisted-retaining archive and their CIKs from the SEC's full
    registrant list; both coverage rates are measured in
    journal/experiments/E04_survivorship_report.json.
    """
    from ..sources import cik_lookup, universe_pit
    from ..sources import edgar_tickers as et

    r = universe_pit.reconstruct(START)
    removed = r.removed_since_start
    if not removed:
        return []
    names = universe_pit.removed_names()
    ticker_map = et.load_map()

    # the last month-end at which each removed name was still a member
    last_seen: dict[str, pd.Timestamp] = {}
    for d, members in sorted(r.by_date.items()):
        for t in members:
            if t in removed:
                last_seen[t] = pd.Timestamp(d)

    need_name = {t: names[t] for t in removed if t not in ticker_map and t in names}
    by_name = cik_lookup.resolve_many(need_name)

    out = []
    for t in sorted(removed):
        cik = None
        how = None
        if t in ticker_map:
            cik, how = ticker_map[t].cik, "ticker_file"
        elif t in by_name and by_name[t].get("cik"):
            cik, how = by_name[t]["cik"], by_name[t]["how"]
        if not cik:
            continue
        out.append({"ticker": t, "cik": cik, "name": names.get(t, ""),
                    "cik_source": how,
                    "last_in_index": last_seen.get(t, pd.Timestamp(START))})
    return out


def build_raw(top: int | None = None, limit: int | None = None, *,
              include_removed: bool = False) -> pd.DataFrame:
    """Every month-end row with FE split, BEFORE the cross-sectional scoring pass.

    Separated from build() so one expensive crawl can be scored several ways - the F1
    holdout needs the same rows on both an absolute and a sector-relative basis, and
    rebuilding for each would be 70 minutes apiece.
    """
    return _build_rows(top=top, limit=limit, include_removed=include_removed)


def _build_rows(top: int | None = None, limit: int | None = None, *,
                include_removed: bool = False) -> pd.DataFrame:
    trust_windows_certs()
    scores = pd.read_parquet(config.SCORES_PARQUET)
    uni = scores.sort_values("composite_strict", ascending=False)
    if top:
        uni = uni.head(top)
    if limit:
        uni = uni.head(limit)

    targets: list[dict] = [
        {"ticker": r.ticker, "cik": r.cik, "sector": r.get("sector") or "",
         "sub_industry": r.get("sub_industry") or "", "last_in_index": None}
        for _i, r in uni.iterrows()
    ]
    n_current = len(targets)
    if include_removed:
        rem = removed_constituents()
        # sector/sub_industry are unknown for a company that has left the index; they
        # are filled from EDGAR's SIC inside build_symbol_history via the profile, and
        # left blank here rather than guessed
        targets += [{"ticker": d["ticker"], "cik": d["cik"], "sector": "",
                     "sub_industry": "", "last_in_index": d["last_in_index"]}
                    for d in rem]
        print(f"including {len(rem)} removed constituents "
              f"({n_current} current + {len(rem)} = {len(targets)})", flush=True)

    all_rows: list[dict] = []
    skipped: dict[str, str] = {}
    for n, t in enumerate(targets, 1):
        is_removed = t["last_in_index"] is not None
        h = build_symbol_history(t["ticker"], t["cik"], sector=t["sector"],
                                 sub_industry=t["sub_industry"],
                                 allow_archive=is_removed,
                                 last_date=t["last_in_index"])
        tag = " [removed]" if is_removed else ""
        if not h.ok:
            skipped[t["ticker"]] = h.note
            print(f"  [{n}/{len(targets)}] {t['ticker']:6s}{tag} skipped: {h.note}",
                  flush=True)
            continue
        all_rows.extend(h.rows)
        print(f"  [{n}/{len(targets)}] {t['ticker']:6s}{tag} {len(h.rows):4d} "
              f"month-ends via {h.price_source}", flush=True)
    raw = pd.DataFrame(all_rows)
    raw.attrs["skipped"] = skipped
    return raw


def build(top: int | None = None, limit: int | None = None, *,
          include_removed: bool = False, sector_relative: bool = False) -> pd.DataFrame:
    raw = _build_rows(top=top, limit=limit, include_removed=include_removed)
    if raw.empty:
        return raw
    print(f"scoring {len(raw)} rows across {raw.date.nunique()} months "
          f"(sector_relative={sector_relative})", flush=True)
    panel = score_panel(raw, sector_relative=sector_relative)
    panel.attrs["skipped"] = raw.attrs.get("skipped", {})
    return panel


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--top", type=int, default=None,
                    help="restrict to the top N by current composite")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--include-removed", action="store_true",
                    help="add the 213 companies removed from the index since 2016 - "
                         "the survivorship fix")
    ap.add_argument("--sector-relative", action="store_true",
                    help="score the five F1 sub-tests as percentiles within sector")
    ap.add_argument("--both", action="store_true",
                    help="crawl once, write BOTH an absolute and a sector-relative "
                         "panel - the F1 holdout comparison without paying twice")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    default_out = str(config.JOURNAL_DIR / "experiments" / "E02_panel.parquet")

    def _write(panel: pd.DataFrame, path: str) -> None:
        panel.to_parquet(path, index=False)
        print(f"\npanel: {len(panel)} rows, {panel.ticker.nunique()} symbols, "
              f"{panel.date.min().date()} -> {panel.date.max().date()}")
        print(f"median available points: {panel.measured_avail.median():.0f}")
        if "fe_basis" in panel:
            print(f"fe_basis: {panel.fe_basis.value_counts().to_dict()}")
        print(f"written: {path}")

    if args.both:
        raw = build_raw(top=args.top, limit=args.limit,
                        include_removed=args.include_removed)
        if raw.empty:
            print("empty panel")
            return 1
        base = args.out or default_out
        for flag, suffix in ((False, "_abs"), (True, "_secrel")):
            print(f"\nscoring {len(raw)} rows (sector_relative={flag})", flush=True)
            panel = score_panel(raw, sector_relative=flag)
            path = base.replace(".parquet", f"{suffix}.parquet")
            _write(panel, path)
        print(f"built_at {utc_now_iso()}")
        return 0

    panel = build(top=args.top, limit=args.limit,
                  include_removed=args.include_removed,
                  sector_relative=args.sector_relative)
    if panel.empty:
        print("empty panel")
        return 1
    _write(panel, args.out or default_out)
    print(f"built_at {utc_now_iso()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
