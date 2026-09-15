"""Flat CSV: one row per company.

utf-8-sig (BOM) and CRLF so Excel opens it correctly with no import wizard the day
Excel gets installed, while staying a perfectly ordinary UTF-8 CSV for pandas.
"""
from __future__ import annotations

import csv
import io
from pathlib import Path

from ..scoring import rubric

COLUMNS: tuple[str, ...] = (
    # THE answer, first, and there is only one of it. `score` is the ex-entry sum
    # normalised to 100 - the number the bands read and the number to rank on. Four
    # near-identical score columns in the first screenful was the single most confusing
    # thing in the workbook.
    "ticker", "name", "sector", "score", "band", "coverage",
    # ...and beside it, the answer to the question `score` cannot answer. E03 R1 measured
    # 95.6% of this ranking's power as sector selection and the median score still runs
    # from Information Technology 59 to Real Estate 33. `score` compares a company with
    # its own sector; `sector_rank` and `sector_neutral_score` compare it across sectors.
    # Both are in the first screenful because leaving the cross-sector answer 25 columns
    # to the right meant nobody used it.
    "sector_rank", "sector_rank_n", "sector_neutral_score",
    # identity and provenance
    "cik", "sub_industry", "profile", "as_of", "data_through", "price_as_of",
    # the audit trail behind `score`: the raw /94 sum, the coverage-extrapolated form,
    # and the ex-entry sum before normalisation. Kept because every study and snapshot
    # before 2026-08-23 is expressed in composite_strict, but moved out of the way.
    "composite_strict", "composite_normalized", "composite_ex_entry",
    "quant_only_50", "quant_normalized", "quant_band", "quant_coverage",
    "qual_available", "points_earned", "points_available", "n_subtests_no_data",
    "scorecard_age_days",
    # the audit trail behind the two sector-neutral columns above: which peer group the
    # percentile was taken against, how many peers it had, and - the one that catches a
    # real misreading - which score column it ranked. It is `composite_strict`, not the
    # `score` sitting next to it, and those two do not order identically.
    "sub_industry_percentile", "sector_percentile",
    "sector_neutral_basis", "sector_neutral_n", "sector_neutral_score_col",
    # components
    *[c.lower() for c in rubric.COMPONENT_ORDER],
    *[f"{c.lower()}_max" for c in rubric.COMPONENT_ORDER],
    *[f"{c.lower()}_available" for c in rubric.COMPONENT_ORDER],
    # financial engine
    "revenue_ttm", "revenue_cagr_1y", "revenue_cagr_3y", "revenue_cagr_5y",
    "eps_ttm", "fcf_ttm", "gross_margin", "operating_margin", "fcf_margin",
    "margin_trend_bps_yr", "roic", "roe", "fcf_conversion",
    # balance sheet
    "net_debt", "net_debt_ebitda", "interest_coverage", "current_ratio",
    "dilution_yoy", "stress_verdict",
    # valuation
    "price", "market_cap", "pe", "fwd_pe", "peg", "ev_ebitda", "ev_sales", "p_fcf",
    "reverse_dcf_implied_growth", "reverse_dcf_wacc", "analyst_growth_3y",
    # entry: the multiple against its own history, and where price sits vs the EMAs
    "pe_current", "pe_pctile_own", "pe_median_own", "pe_min_own", "pe_max_own",
    "pe_history_years", "en_best_timeframe_weight", "en_confluence",
    "pct_vs_ema20_daily", "pct_vs_ema72_daily",
    "pct_vs_ema20_weekly", "pct_vs_ema72_weekly",
    "pct_vs_ema20_monthly", "pct_vs_ema72_monthly",
    "drawdown_from_ath",
    # the targeted repair pass: what a second look added with a verified quote behind it,
    # what it offered without one (shown, never scored), and the coverage before it ran
    "coverage_before_repair", "repaired_points_quoted", "repaired_points_unquoted",
    "repaired_subtests", "repaired_subtests_unquoted",
    # the forward DCF: a fair value per share beside the score, never inside it
    "dcf_fair_value", "dcf_margin_of_safety", "dcf_bear", "dcf_bull",
    "dcf_growth", "dcf_growth_basis", "dcf_wacc", "dcf_implausible",
    "dcf_shares_basis", "dcf_shares_disputed", "dcf_shares_filed_vs_market",
    "dcf_reason",
)

PERCENT_COLUMNS = frozenset({
    # a fraction like `coverage`; without it the workbook showed 0.72 beside coverage at 86%
    "coverage_before_repair",
    "dcf_margin_of_safety", "dcf_growth",
    "coverage", "quant_coverage", "revenue_cagr_1y", "revenue_cagr_3y",
    "revenue_cagr_5y", "gross_margin", "operating_margin", "fcf_margin", "roic",
    "roe", "dilution_yoy", "reverse_dcf_implied_growth", "reverse_dcf_wacc",
    "analyst_growth_3y", "drawdown_from_ath", "pe_pctile_own",
    "pct_vs_ema20_daily", "pct_vs_ema72_daily",
    "pct_vs_ema20_weekly", "pct_vs_ema72_weekly",
    "pct_vs_ema20_monthly", "pct_vs_ema72_monthly",
})


def _cell(row: dict, col: str):
    v = row.get(col)
    if isinstance(v, float):
        return round(v, 6)
    return v


def write_csv(fh, rows: list[dict], columns: tuple[str, ...] = COLUMNS) -> None:
    w = csv.DictWriter(fh, fieldnames=list(columns), extrasaction="ignore",
                       lineterminator="\r\n")
    w.writeheader()
    for r in rows:
        w.writerow({c: _cell(r, c) for c in columns})


def to_string(rows: list[dict], columns: tuple[str, ...] = COLUMNS) -> str:
    buf = io.StringIO(newline="")
    write_csv(buf, rows, columns)
    return buf.getvalue()


def to_bytes(rows: list[dict], columns: tuple[str, ...] = COLUMNS) -> bytes:
    return to_string(rows, columns).encode("utf-8-sig")


def write_csv_file(path: Path, rows: list[dict],
                   columns: tuple[str, ...] = COLUMNS) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".csv.tmp")
    tmp.write_bytes(to_bytes(rows, columns))
    tmp.replace(path)
    return path


def scorecard_long_rows(card: dict) -> list[dict]:
    """One scorecard as long-format rows: the full audit trail for one company."""
    out = []
    for code, comp in (card.get("components") or {}).items():
        for st in comp.get("subtests") or []:
            out.append({
                "ticker": card.get("ticker"),
                "component": code,
                "component_label": comp.get("label"),
                "subtest": st.get("key"),
                "label": st.get("label"),
                "earned": st.get("effective"),
                "max_points": st.get("max_points"),
                "status": st.get("status"),
                "source": (st.get("provenance") or {}).get("source"),
                "tag_used": str((st.get("provenance") or {}).get("tags_used")
                                or (st.get("provenance") or {}).get("tag_used") or ""),
                "threshold_note": st.get("threshold_note"),
                "rationale": st.get("rationale"),
                "evidence": st.get("evidence"),
                "evidence_unverified": st.get("evidence_unverified"),
                # `source` reads "repair" for a point the first call declined and a
                # targeted second call answered; the gate says what verified its quote.
                "origin": (st.get("provenance") or {}).get("origin") or "first_call",
                "quote_gate": (st.get("provenance") or {}).get("repair_gate"),
                "repair_run_id": (st.get("provenance") or {}).get("repair_run_id"),
            })
    return out
