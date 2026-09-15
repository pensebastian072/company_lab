"""The workbook - the whole system in one file, rebuilt by the weekly crawl.

Eleven sheets, in reading order:
  Rank        the flat table, frozen panes + autofilter + colour scale on the score
  Changes     what moved since the previous weekly snapshot, band moves first
  Sectors     per-sector aggregates and a bar chart, because E03 R1 measured that the
              ranking is substantially a SECTOR bet and that must not be buried
  Findings    what the studies did and did not establish, including the failures
  Entry       the own-history P/E percentile and price vs the 20/72 EMAs
  Components  one row per (ticker, component): earned / available / max / coverage
  Subtests    one row per (ticker, component, subtest) - the full audit trail
  Thesis      belief, expectations, falsifiers, status and its reasons
  Valuation   every multiple, plus the reverse-DCF block and its wacc sensitivity
  Stress      the whole simulated downturn P&L, one column per intermediate
  Meta        run metadata, source freshness, the horizon note, and the ADVISORY/SHADOW
              disclaimer in row 1 in bold red - seen before any number

Changes/Sectors/Findings sit directly behind Rank on purpose: a workbook that shows 500
confident-looking scores without the negative results next to them is misleading by
omission.

The Subtests sheet is ~45 rows per company (~22,500 for the S&P 500), well inside
xlsx limits but the slowest sheet to build, so it can be omitted via `sheets=`.
"""
from __future__ import annotations

import io
import math
from pathlib import Path

from .. import config
from ..external.industry_versions import active_industry_rows as select_active_industries
from ..net import read_json, utc_now_iso
from ..scoring import rubric
from . import csv_export

ALL_SHEETS = ("rank", "changes", "sectors", "findings", "entry", "components",
              "subtests", "thesis", "valuation", "dcf", "stress", "meta",
              "external", "industries", "claims")

#: TAB ORDER IS A HUMAN CONTRACT, and it is not the order the sheets are built in.
#:
#: The person opening this workbook wants the rankings first and never wants to hunt for
#: them. So the left-hand tabs are what a human watches - company rank, sector rank, what
#: moved, what the studies actually found - and everything that exists so a machine or an
#: auditor can check the work goes to the right. Evidence rows, per-sub-test dumps and
#: run metadata are all real and all kept; they are simply not what the workbook is for.
#:
#: Build order stays as it is, because sheets depend on data loaded at different points.
#: `_apply_sheet_order` reorders at the end, so adding a sheet in the middle of
#: `build_workbook` cannot quietly change what the first tab is.
SHEET_ORDER = (
    # --- what a human opens the file to see
    "Rank", "Sectors", "Changes", "Findings", "Entry",
    "Valuation", "DCF", "Thesis", "Stress",
    # --- the external research layer, human-readable but secondary
    "External", "Industries",
    # --- back end: dumps, evidence and provenance
    "Components", "Subtests", "Claims", "Meta",
)


def _apply_sheet_order(wb) -> None:
    """Reorder tabs to SHEET_ORDER. Anything unlisted keeps its build position, after
    the listed sheets, so a new sheet can never silently land in front of Rank."""
    index = {name: i for i, name in enumerate(SHEET_ORDER)}
    tail = len(index)
    wb._sheets.sort(key=lambda ws: (index.get(ws.title, tail), ws.title))

BAND_FILLS = {
    "EXCEPTIONAL": "FF1B7F4B",
    "HIGH_CONVICTION": "FF2E7D32",
    "INVESTABLE": "FF5D8A33",
    "WATCHLIST": "FF8A6D1F",
    "WEAK": "FF8A4B1F",
    "REJECT": "FF8A2222",
    "INSUFFICIENT_DATA": "FF4A4A4A",
}
STATUS_EMOJI = {"INTACT": "\U0001F7E2", "UNCERTAIN": "\U0001F7E1", "BROKEN": "\U0001F534"}

#: a sector with fewer than this many scored companies has a median that is one or two
#: companies, not a sector level. Same floor MIN_SUB_INDUSTRY_N uses a level down.
MIN_SECTOR_N = 5


def _finite(v) -> bool:
    """A real number, and NOT NaN or inf.

    `isinstance(v, (int, float))` is not enough and the difference is not cosmetic: NaN
    IS a float, and every comparison against it is False, so a single NaN does not merely
    skew a sorted list - it silently scrambles the ORDER. Measured here on 2026-08-25:
    three of 1,501 rows have a null `score`, and with them included the Real Estate
    median read 12 (its minimum) instead of 33. bool is excluded because True would
    otherwise sort as 1.
    """
    return (isinstance(v, (int, float)) and not isinstance(v, bool)
            and math.isfinite(v))


def _sector_medians(rows: list[dict] | None,
                    col: str = "score") -> list[tuple[str, int, float, float]]:
    """(sector, n, median score, banded share), richest sector first.

    Read live rather than hand-typed: the spread this whole presentation change rests on
    is a measurement, and a measurement quoted from memory in a workbook goes stale
    silently. Sectors below MIN_SECTOR_N are excluded from the headline spread.
    """
    by: dict[str, list[dict]] = {}
    for r in rows or []:
        sec = str(r.get("sector") or "").strip()
        if sec and _finite(r.get(col)):
            by.setdefault(sec, []).append(r)
    out = []
    for sec, rs in by.items():
        if len(rs) < MIN_SECTOR_N:
            continue
        vals = sorted(float(r[col]) for r in rs)
        banded = sum(1 for r in rs
                     if r.get("band") and str(r.get("band")) != "INSUFFICIENT_DATA")
        out.append((sec, len(rs), vals[len(vals) // 2], banded / len(rs)))
    out.sort(key=lambda t: -t[2])
    return out


def _cross_sector_note(rows: list[dict] | None) -> str:
    """One sentence, on Rank, Sectors and Findings, because the mistake is made on all three.

    Wording is deliberate: `score` is not wrong, it answers a different question, and
    neither column is validated against forward returns.
    """
    med = _sector_medians(rows)
    if len(med) >= 2:
        (hs, _hn, hm, hb), (ls, _ln, lm, lb) = med[0], med[-1]
        evidence = (f"median score runs from {hs} {hm:.0f} ({hb:.0%} banded) to {ls} "
                    f"{lm:.0f} ({lb:.0%} banded), a {hm - lm:.0f}-point spread")
    else:
        evidence = "the median score differs by sector by more than it differs by company"
    return ("COMPARING ACROSS SECTORS? Use sector_rank and sector_neutral_score, not "
            f"score. The headline score is comparable WITHIN a sector and misleading "
            f"across them - {evidence} (E03 R1: 95.6% of the ranking's power was sector "
            "selection). sector_neutral_score is this company's percentile among its own "
            "sub-industry peers and is taken over composite_strict, NOT over the score "
            "column beside it. Neither column is validated against forward returns - "
            "see Findings.")


def _autosize(ws, max_width: int = 42) -> None:
    from openpyxl.utils import get_column_letter

    widths: dict[int, int] = {}
    for row in ws.iter_rows():
        for cell in row:
            if cell.value is None:
                continue
            n = len(str(cell.value))
            if n > widths.get(cell.column, 0):
                widths[cell.column] = n
    for col, n in widths.items():
        ws.column_dimensions[get_column_letter(col)].width = min(max(n + 2, 9), max_width)


def _header(ws, columns: list[str]) -> None:
    from openpyxl.styles import Alignment, Font, PatternFill

    ws.append(columns)
    # Style the row that was just appended, not row 1: the Rank sheet may carry a note
    # above the header, and styling a fixed row 1 would decorate the note and leave the
    # real header unformatted.
    hdr = ws.max_row
    fill = PatternFill("solid", fgColor="FF22272E")
    for cell in ws[hdr]:
        cell.font = Font(bold=True, color="FFFFFFFF")
        cell.fill = fill
        cell.alignment = Alignment(vertical="center", wrap_text=False)
    ws.freeze_panes = f"B{hdr + 1}"



def _filterable(ws, cols, header_row: int = 1) -> None:
    """Turn the header row into real Excel filter controls.

    Every sheet a person reads down a column of needs this. Without it the column headers
    are inert and the only ordering available is whatever the exporter happened to write -
    which is how the DCF sheet shipped: sorted by margin of safety, and no way to ask it
    for anything else.
    """
    from openpyxl.utils import get_column_letter as _letter

    if ws.max_row <= header_row:
        return
    ws.auto_filter.ref = f"A{header_row}:{_letter(len(cols))}{ws.max_row}"

def _sheet_rank(wb, rows: list[dict]) -> None:
    from openpyxl.formatting.rule import ColorScaleRule
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter

    ws = wb.create_sheet("Rank")
    cols = list(csv_export.COLUMNS)

    # While the judgement half is still rolling out the ordering is misleading, and the
    # Rank sheet is where someone acts on it - so the caveat goes HERE, not only on
    # Findings three tabs away. It is written BEFORE the header so nothing downstream
    # has to be shifted; every offset below derives from `hdr` rather than assuming 1.
    roll = _qual_rollout(rows)
    banner = _rollout_banner(roll)
    if banner:
        ws.append([banner])
        ws.cell(row=1, column=1).font = Font(bold=True, color="FFB42318")

    # The cross-sector caveat, on the sheet where the comparison actually gets made.
    # E03 R1 measured 95.6% of the ranking's power as sector selection; sorting this
    # sheet by `score` and reading off the top 20 is substantially sorting by sector.
    ws.append([_cross_sector_note(rows)])
    ws.cell(row=ws.max_row, column=1).font = Font(bold=True, color="FF1F6FEB")

    _header(ws, cols)
    hdr = ws.max_row                      # 1 normally, 2 when the rollout note is present
    ws.freeze_panes = f"B{hdr + 1}"
    for r in rows:
        ws.append([r.get(c) for c in cols])

    n = len(rows) + hdr
    ws.auto_filter.ref = f"A{hdr}:{get_column_letter(len(cols))}{n}"

    idx = {c: i + 1 for i, c in enumerate(cols)}
    first = hdr + 1                       # first data row

    # clickable ticker -> the local scorecard page
    tcol = idx["ticker"]
    for row in range(first, n + 1):
        cell = ws.cell(row=row, column=tcol)
        tick = cell.value
        if tick:
            cell.value = (f'=HYPERLINK("http://{config.UI_HOST}:{config.UI_PORT}'
                          f'/c/{tick}","{tick}")')
            cell.font = Font(color="FF1F6FEB", underline="single")

    # 3-colour scale on the headline score: red 50 -> yellow 70 -> green 90
    if "composite_strict" in idx and n > hdr:
        letter = get_column_letter(idx["composite_strict"])
        ws.conditional_formatting.add(
            f"{letter}{first}:{letter}{n}",
            ColorScaleRule(start_type="num", start_value=50, start_color="FFF8696B",
                           mid_type="num", mid_value=70, mid_color="FFFFEB84",
                           end_type="num", end_value=90, end_color="FF63BE7B"),
        )
    # The same scale on the cross-sector column, so the two are read side by side. It is
    # a percentile, so the anchors are 25/50/75 rather than the raw score's 50/70/90 -
    # painting a percentile on the raw ladder would make a median company look like a
    # failing one.
    if "sector_neutral_score" in idx and n > hdr:
        letter = get_column_letter(idx["sector_neutral_score"])
        ws.conditional_formatting.add(
            f"{letter}{first}:{letter}{n}",
            ColorScaleRule(start_type="num", start_value=25, start_color="FFF8696B",
                           mid_type="num", mid_value=50, mid_color="FFFFEB84",
                           end_type="num", end_value=75, end_color="FF63BE7B"),
        )

    # band cells filled by band
    if "band" in idx:
        bcol = idx["band"]
        for row in range(first, n + 1):
            cell = ws.cell(row=row, column=bcol)
            colour = BAND_FILLS.get(str(cell.value))
            if colour:
                cell.fill = PatternFill("solid", fgColor=colour)
                cell.font = Font(color="FFFFFFFF", bold=True)

    # number formats
    for col in cols:
        fmt = None
        if col in csv_export.PERCENT_COLUMNS:
            fmt = "0.0%"
        elif col in ("revenue_ttm", "fcf_ttm", "net_debt", "market_cap", "eps_ttm"):
            fmt = "#,##0"
        elif col in ("sector_rank", "sector_rank_n"):
            fmt = "0"
        elif col == "sector_neutral_score":
            fmt = "0.0"
        elif col in ("pe", "fwd_pe", "peg", "ev_ebitda", "ev_sales", "p_fcf",
                     "net_debt_ebitda", "interest_coverage", "current_ratio",
                     "fcf_conversion", "price", "margin_trend_bps_yr",
                     "composite_normalized"):
            fmt = "#,##0.0"
        if not fmt:
            continue
        letter = get_column_letter(idx[col])
        for row in range(first, n + 1):
            ws.cell(row=row, column=idx[col]).number_format = fmt
    _autosize(ws)


def _sheet_entry(wb, rows: list[dict]) -> None:
    """The entry screen: multiple against its own history, and distance to each EMA.

    Sorted by entry score then by P/E percentile, so the top of the sheet is
    "companies whose multiple is at the low end of its own range and whose price has
    come back to a higher-timeframe average".
    """
    from openpyxl.formatting.rule import CellIsRule, ColorScaleRule
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter

    ws = wb.create_sheet("Entry")
    cols = [
        "ticker", "name", "sector", "composite_strict", "band", "en",
        "price", "pe_current", "pe_pctile_own", "pe_median_own", "pe_min_own",
        "pe_max_own", "pe_history_years",
        "pct_vs_ema20_monthly", "pct_vs_ema72_monthly",
        "pct_vs_ema20_weekly", "pct_vs_ema72_weekly",
        "pct_vs_ema20_daily", "pct_vs_ema72_daily",
        "en_best_timeframe_weight", "en_confluence", "drawdown_from_ath",
        "revenue_cagr_3y", "roic", "fe", "va",
    ]
    _header(ws, cols)

    def sort_key(r):
        en = r.get("en")
        pc = r.get("pe_pctile_own")
        return (-(en if isinstance(en, (int, float)) else -1),
                pc if isinstance(pc, (int, float)) else 9.9)

    ordered = sorted(rows, key=sort_key)
    for r in ordered:
        ws.append([r.get(c) for c in cols])

    n = len(ordered) + 1
    idx = {c: i + 1 for i, c in enumerate(cols)}
    ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{n}"

    pct_cols = {"pe_pctile_own", "drawdown_from_ath", "revenue_cagr_3y", "roic",
                "pct_vs_ema20_monthly", "pct_vs_ema72_monthly",
                "pct_vs_ema20_weekly", "pct_vs_ema72_weekly",
                "pct_vs_ema20_daily", "pct_vs_ema72_daily"}
    for c in cols:
        letter = get_column_letter(idx[c])
        fmt = "0.0%" if c in pct_cols else (
            "#,##0.00" if c.startswith("pe_") or c == "price" else None)
        if fmt:
            for row in range(2, n + 1):
                ws.cell(row=row, column=idx[c]).number_format = fmt

    if n > 1:
        # green where the multiple sits low in its own range
        letter = get_column_letter(idx["pe_pctile_own"])
        ws.conditional_formatting.add(
            f"{letter}2:{letter}{n}",
            ColorScaleRule(start_type="num", start_value=0, start_color="FF63BE7B",
                           mid_type="num", mid_value=0.5, mid_color="FFFFEB84",
                           end_type="num", end_value=1, end_color="FFF8696B"))
        # highlight price at or just under each higher-timeframe EMA
        for c in ("pct_vs_ema20_monthly", "pct_vs_ema72_monthly",
                  "pct_vs_ema20_weekly", "pct_vs_ema72_weekly"):
            letter = get_column_letter(idx[c])
            ws.conditional_formatting.add(
                f"{letter}2:{letter}{n}",
                CellIsRule(operator="between", formula=["-0.12", "0.04"],
                           fill=PatternFill("solid", fgColor="FFD6F5D6")))
        letter = get_column_letter(idx["en"])
        ws.conditional_formatting.add(
            f"{letter}2:{letter}{n}",
            CellIsRule(operator="greaterThanOrEqual", formula=["4"],
                       font=Font(bold=True), fill=PatternFill("solid", fgColor="FFB7E1CD")))
    _autosize(ws)


def _sheet_components(wb, cards: list[dict]) -> None:
    ws = wb.create_sheet("Components")
    cols = ["ticker", "component", "label", "earned_points", "available_points",
            "max_points", "applicable_points", "not_applicable_points",
            "no_data_points", "coverage", "is_llm", "note"]
    _header(ws, cols)
    for card in cards:
        for code in rubric.COMPONENT_ORDER:
            c = (card.get("components") or {}).get(code)
            if not c:
                continue
            ws.append([card.get("ticker"), code, c.get("label"),
                       c.get("earned_points"), c.get("available_points"),
                       c.get("max_points"), c.get("applicable_points"),
                       c.get("not_applicable_points"), c.get("no_data_points"),
                       c.get("coverage"), c.get("is_llm"), c.get("note")])
    _filterable(ws, cols)
    _autosize(ws)


def _sheet_subtests(wb, cards: list[dict]) -> None:
    ws = wb.create_sheet("Subtests")
    cols = ["ticker", "component", "subtest", "label", "earned", "max_points",
            "status", "source", "origin", "quote_gate", "tag_used", "threshold_note",
            "rationale",
            "evidence", "evidence_unverified", "repair_run_id"]
    _header(ws, cols)
    for card in cards:
        for row in csv_export.scorecard_long_rows(card):
            ws.append([row.get(c) for c in cols])
    _filterable(ws, cols)
    _autosize(ws, max_width=60)


def _sheet_thesis(wb, cards: list[dict]) -> None:
    from openpyxl.styles import Alignment

    ws = wb.create_sheet("Thesis")
    cols = ["ticker", "status", "status_reasons", "belief", "market_underestimating",
            "primary_thesis", "primary_risk", "falsifier_1", "falsifier_2",
            "falsifier_3", "sell_triggers", "target_bear", "target_base",
            "target_bull", "cagr_base", "authored_by"]
    _header(ws, cols)
    for card in cards:
        t = read_json(config.THESIS_DIR / f"{card.get('cik')}.json") or {}
        status = (t.get("status") or {})
        fals = t.get("falsifiers") or []
        targets = t.get("targets_5y") or {}
        ws.append([
            card.get("ticker"),
            STATUS_EMOJI.get(status.get("status", ""), "") + " " + str(status.get("status") or ""),
            "; ".join(str(r.get("signal")) for r in (status.get("reasons") or [])),
            (t.get("belief") or {}).get("text"),
            (t.get("market_underestimating") or {}).get("text"),
            t.get("primary_thesis_line"), t.get("primary_risk_line"),
            *[(fals[i].get("text") if i < len(fals) else None) for i in range(3)],
            "; ".join(str(s.get("text")) for s in (t.get("sell_triggers") or [])),
            (targets.get("bear") or {}).get("price"),
            (targets.get("base") or {}).get("price"),
            (targets.get("bull") or {}).get("price"),
            (targets.get("base") or {}).get("cagr"),
            t.get("thesis_authored_by") or ("llm" if t else None),
        ])
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    _filterable(ws, cols)
    _autosize(ws, max_width=55)


def _sheet_dcf(wb, rows: list[dict]) -> None:
    """The forward DCF: a fair value per share beside the score, and every refusal.

    Sorted by margin of safety, cheapest first, with the companies that got no fair value
    listed underneath carrying the reason. A DCF that produced a number for all 1,500
    would be worth less than one that refuses 478 and says why - a bank valued off
    CFO-minus-capex is arithmetic, not valuation.

    Display only. `dcf_margin_of_safety` is not an input to any score (E20).
    """
    from openpyxl.styles import Alignment, Font

    ws = wb.create_sheet("DCF")
    ws["A1"] = ("Forward DCF - ADVISORY. A fair value is four assumptions in a trench "
                "coat: the growth rate, where it fades, the terminal rate and the "
                "discount rate. Margin of safety = (fair value - price) / fair value. "
                "None of it is validated against forward returns, none of it feeds a "
                "score, and a large margin of safety is a hypothesis, not a signal. "
                "Energy screens cheapest because trailing free cash flow sits at a cycle "
                "high - the E03 R5 trap, arriving through a new door. A BLANK margin of "
                "safety means the DCF was refused or flagged implausible and the column "
                "is withheld on purpose - it does NOT mean the company is expensive; the "
                "reason is in the last column.")
    ws["A1"].font = Font(bold=True, color="FFB42318")
    ws["A1"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=14)
    ws.row_dimensions[1].height = 58

    cols = ["ticker", "name", "sector", "band", "score", "price",
            "dcf_fair_value", "dcf_margin_of_safety", "dcf_bear", "dcf_bull",
            "dcf_growth", "dcf_growth_basis", "dcf_wacc", "dcf_implausible",
            "dcf_shares_disputed", "dcf_reason"]
    _header(ws, cols)
    hdr = ws.max_row
    ws.freeze_panes = f"B{hdr + 1}"

    # `_finite`, not `is not None`. The rows come back from parquet, which turns every
    # None into NaN - so `is not None` was true for all 1,501 companies, the 520 refusals
    # were treated as valued, and the sort key was NaN for each of them, which makes the
    # whole ordering arbitrary. The sheet's own docstring promises refusals listed
    # underneath with their reason; until this fix that did not happen. Same NaN class as
    # `_finite`'s original bug, in the one sheet that was missed.
    def mos(r):
        v = r.get("dcf_margin_of_safety")
        return v if _finite(v) else None

    valued = [r for r in rows if _finite(r.get("dcf_fair_value"))]
    refused = [r for r in rows if not _finite(r.get("dcf_fair_value"))]
    valued.sort(key=lambda r: (mos(r) is None, -(mos(r) or 0)))
    refused.sort(key=lambda r: (str(r.get("dcf_reason") or ""), str(r.get("ticker"))))
    for r in valued + refused:
        ws.append([r.get(c) for c in cols])

    idx = {c: i + 1 for i, c in enumerate(cols)}
    n = len(valued) + len(refused) + hdr
    for col, fmt in (("dcf_margin_of_safety", "0.0%"), ("dcf_growth", "0.0%"),
                     ("dcf_wacc", "0.0%"), ("price", "#,##0.00"),
                     ("dcf_fair_value", "#,##0.00"), ("dcf_bear", "#,##0.00"),
                     ("dcf_bull", "#,##0.00")):
        letter = idx[col]
        for row in range(hdr + 1, n + 1):
            ws.cell(row=row, column=letter).number_format = fmt
    # Sortable and filterable, which it was not: the sheet had freeze_panes but no
    # AutoFilter, so every column header was dead and the only ordering available was the
    # one the exporter happened to write.
    _filterable(ws, cols, header_row=hdr)
    _autosize(ws, max_width=52)


def _sheet_valuation(wb, cards: list[dict]) -> None:
    ws = wb.create_sheet("Valuation")
    cols = ["ticker", "price", "market_cap", "pe", "fwd_pe", "peg", "ev_ebitda",
            "ev_sales", "p_fcf", "pe_pctile_own", "ev_ebitda_peer_median",
            "reverse_dcf_implied_growth", "reverse_dcf_wacc",
            "implied_growth_wacc_minus", "implied_growth_wacc_plus",
            "reference_growth", "gap_vs_reference", "va_points", "va_available"]
    _header(ws, cols)
    for card in cards:
        va = (card.get("components") or {}).get("VA") or {}
        dcf, pe_pct, peer_med = {}, None, None
        for st in va.get("subtests") or []:
            if st.get("key") == "va_reverse_dcf":
                dcf = st.get("inputs") or {}
            elif st.get("key") == "va_pe_vs_own_history":
                pe_pct = (st.get("inputs") or {}).get("pe_pctile_own_history")
            elif st.get("key") == "va_ev_ebitda_vs_peers":
                peer_med = (st.get("inputs") or {}).get("peer_median")
        sens = dcf.get("sensitivity") or {}
        m = card.get("metrics") or {}
        ws.append([
            card.get("ticker"), m.get("price"), m.get("market_cap"), m.get("pe"),
            m.get("fwd_pe"), m.get("peg"), m.get("ev_ebitda"), m.get("ev_sales"),
            m.get("p_fcf"), pe_pct, peer_med,
            dcf.get("implied_growth"), dcf.get("wacc"),
            (sens.get("wacc_minus") or {}).get("implied_growth"),
            (sens.get("wacc_plus") or {}).get("implied_growth"),
            dcf.get("reference_growth"), dcf.get("gap_vs_reference"),
            va.get("earned_points"), va.get("available_points"),
        ])
    _filterable(ws, cols)
    _autosize(ws)


def _sheet_stress(wb, cards: list[dict]) -> None:
    ws = wb.create_sheet("Stress")
    cols = ["ticker", "verdict", "points", "revenue_base", "operating_margin_base",
            "revenue_stressed", "operating_margin_stressed", "operating_income_stressed",
            "interest_stressed", "ebitda_stressed", "capex_stressed", "fcf_stressed",
            "interest_coverage_stressed", "net_debt_ebitda_stressed",
            "cash_runway_years", "missing"]
    _header(ws, cols)
    for card in cards:
        bs = (card.get("components") or {}).get("BS") or {}
        sim = {}
        for st in bs.get("subtests") or []:
            if st.get("key") == "bs_stress_test":
                sim = st.get("inputs") or {}
        s = sim.get("simulated") or {}
        i = sim.get("inputs") or {}
        ws.append([
            card.get("ticker"), sim.get("verdict"), sim.get("points"),
            i.get("revenue_ttm"), i.get("operating_margin"),
            s.get("revenue"), s.get("operating_margin"), s.get("operating_income"),
            s.get("interest_expense"), s.get("ebitda"), s.get("capex"), s.get("fcf"),
            s.get("interest_coverage"), s.get("net_debt_ebitda"),
            s.get("cash_runway_years"), ", ".join(sim.get("missing") or []),
        ])
    _filterable(ws, cols)
    _autosize(ws)


def _sheet_meta(wb, rows: list[dict]) -> None:
    from openpyxl.styles import Font

    ws = wb.create_sheet("Meta")
    ws["A1"] = config.ADVISORY_BANNER
    ws["A1"].font = Font(bold=True, color="FFCC0000", size=12)
    # F4: the workbook states the horizon too, so a sheet mailed to someone without the
    # dashboard still carries it. Presentation only - no score changes.
    ws["A2"] = f"Read on a {rubric.HORIZON_LABEL} horizon. {rubric.HORIZON_NOTE}"
    ws["A2"].font = Font(italic=True, color="FF0A3069", size=11)
    ws.append([])

    flag = read_json(config.STATE_FLAG) or {}
    cov = [r.get("coverage") for r in rows if isinstance(r.get("coverage"), (int, float))]
    facts = [
        ("generated_at", utc_now_iso()),
        ("companies", len(rows)),
        ("universe_tier", flag.get("tier")),
        ("as_of", flag.get("as_of")),
        ("data_through", flag.get("data_through")),
        ("symbols_scored", flag.get("symbols_scored")),
        ("symbols_failed", flag.get("symbols_failed")),
        ("median_coverage", (sorted(cov)[len(cov) // 2] if cov else None)),
        ("companies_with_llm_qualitative",
         sum(1 for r in rows if r.get("qual_available"))),
        ("qual_model", config.QUAL_MODEL),
        ("default_horizon", rubric.DEFAULT_HORIZON),
        ("band_gate_min_coverage", rubric.MIN_COVERAGE_FOR_BAND),
        ("framework_total_points", rubric.TOTAL_POINTS),
        ("llm_components", ", ".join(rubric.JUDGED_COMPONENTS)),
        ("measured_components", ", ".join(rubric.MEASURED_COMPONENTS)),
        ("fundamentals_source", "SEC EDGAR XBRL companyfacts"),
        ("market_source", "yfinance"),
        ("validated_against_forward_returns", "NO - see ADVISORY note above"),
        ("dashboard", f"http://{config.UI_HOST}:{config.UI_PORT}"),
    ]
    ws.append(["key", "value"])
    for c in ws[ws.max_row]:      # not a fixed row: the preamble above has grown before
        c.font = Font(bold=True)
    for k, v in facts:
        ws.append([k, v])
    ws.append([])
    ws.append(["source", "ok", "health", "data_through", "error"])
    for c in ws[ws.max_row]:
        c.font = Font(bold=True)
    fresh = read_json(config.FRESHNESS_FILE) or {}
    for name, rec in (fresh.get("sources") or {}).items():
        ws.append([name, rec.get("ok"), rec.get("health"),
                   rec.get("data_through"), rec.get("error")])
    _autosize(ws, max_width=100)


def _sheet_sectors(wb, rows: list[dict]) -> None:
    """Per-sector aggregates and a bar chart of the mean score.

    This sheet exists because of a FINDING, not for decoration: E03 R1 measured that
    95.6% of the ranking's power was sector selection and that mean score ran from
    Financials 62.6% down to Utilities 41.2%. Anyone comparing two companies from
    different sectors on the Rank sheet is partly comparing their sectors, and that has
    to be visible next to the ranking rather than buried in a journal file.
    """
    from openpyxl.chart import BarChart, Reference
    from openpyxl.styles import Font

    ws = wb.create_sheet("Sectors")
    ws["A1"] = ("Mean score by sector. E03 R1 found the ranking is SUBSTANTIALLY A "
                "SECTOR BET - comparing a bank with a utility on the headline score "
                "partly compares their sectors, not the companies.")
    ws["A1"].font = Font(italic=True, size=11)
    ws["A2"] = _cross_sector_note(rows)
    ws["A2"].font = Font(bold=True, color="FF1F6FEB")
    ws.append([])

    by: dict[str, list[dict]] = {}
    for r in rows:
        by.setdefault(str(r.get("sector") or "Unclassified"), []).append(r)

    def _num(rs, key):
        # _finite, not isinstance: one NaN scrambles the sort order outright, and this
        # list is read for a median, a min and a max.
        return sorted(v for v in (x.get(key) for x in rs) if _finite(v))

    # max_row is read AFTER the append: an empty ws.append([]) advances the write cursor
    # but writes no cells, so max_row does not move and predicting the row is off by one.
    ws.append(["sector", "companies", "mean_score", "median_score", "min", "max",
               "mean_coverage", "best_company", "best_score", "bands"])
    header_row = ws.max_row
    for c in ws[header_row]:
        c.font = Font(bold=True)

    table = []
    for sector, rs in by.items():
        vals = _num(rs, "composite_strict")
        if not vals:
            continue
        cov = _num(rs, "coverage")
        best = max((x for x in rs if _finite(x.get("composite_strict"))),
                   key=lambda x: x["composite_strict"], default=None)
        bands: dict[str, int] = {}
        for x in rs:
            b = x.get("band")
            if b:
                bands[b] = bands.get(b, 0) + 1
        table.append((sector, len(rs), sum(vals) / len(vals), vals[len(vals) // 2],
                      vals[0], vals[-1],
                      (sum(cov) / len(cov)) if cov else None,
                      (best or {}).get("ticker"), (best or {}).get("composite_strict"),
                      ", ".join(f"{k} {v}" for k, v in sorted(bands.items(),
                                                              key=lambda kv: -kv[1]))))
    table.sort(key=lambda t: -t[2])
    for row in table:
        ws.append(list(row))
        for col in (3, 4):
            ws.cell(row=ws.max_row, column=col).number_format = "0.0"
        ws.cell(row=ws.max_row, column=7).number_format = "0%"

    if table:
        first = header_row + 1
        last = header_row + len(table)
        ch = BarChart()
        ch.type = "bar"
        ch.title = "Mean composite score by sector"
        ch.y_axis.title = "points / 100"
        ch.height, ch.width = max(7.0, 0.5 * len(table)), 16.0
        ch.add_data(Reference(ws, min_col=3, min_row=header_row, max_row=last),
                    titles_from_data=True)
        ch.set_categories(Reference(ws, min_col=1, min_row=first, max_row=last))
        ch.legend = None
        ws.add_chart(ch, f"L{header_row}")

        spread = table[0][2] - table[-1][2]
        ws.append([])
        ws.append([f"spread between the highest and lowest sector: {spread:.1f} points "
                   f"({table[0][0]} to {table[-1][0]})"])
        ws.cell(row=ws.max_row, column=1).font = Font(bold=True)

    _within_sector_leaderboard(ws, rows)
    _sub_industry_block(ws, rows)
    _autosize(ws, max_width=54)


#: how many names each sector's leaderboard shows. Ten is the largest list a person reads
#: without scrolling past the sector below it.
LEADERBOARD_N = 10


def _within_sector_leaderboard(ws, rows: list[dict]) -> None:
    """The best companies IN each sector - the comparison the raw ranking cannot make.

    A single global top-20 sorted on `score` is mostly a list of Information Technology
    companies, which is what E03 R1's sector-bet finding means in practice. This block is
    the same data asked the question that survives that finding: within Real Estate, who
    is at the top? A Real Estate name at rank 1 of 104 is a stronger statement than its
    score of 41 looks beside a software company's 78.

    `sector_neutral_score` travels with each name because the two disagree: the rank is
    over `composite_strict` and the sheet's ordering is over `score`, so a company can
    lead its sector on one and not the other. Showing both is the point.
    """
    from openpyxl.styles import Font

    ws.append([])
    ws.append([])
    ws.append([f"Top {LEADERBOARD_N} within each sector - who leads where"])
    ws.cell(row=ws.max_row, column=1).font = Font(bold=True, size=12)
    ws.append(["Ranked against its OWN sector. This is the comparison the headline score "
               "cannot make: a global top-20 on score is substantially a list of one or "
               "two sectors."])
    ws.cell(row=ws.max_row, column=1).font = Font(italic=True, size=10)
    ws.append([])

    ws.append(["sector", "rank_in_sector", "of", "ticker", "name", "score",
               "sector_neutral_score", "band", "coverage"])
    for c in ws[ws.max_row]:
        c.font = Font(bold=True)

    by: dict[str, list[dict]] = {}
    for r in rows:
        sec = str(r.get("sector") or "Unclassified")
        if _finite(r.get("score")):
            by.setdefault(sec, []).append(r)

    for sec in sorted(by):
        rs = sorted(by[sec], key=lambda x: -float(x["score"]))
        for i, r in enumerate(rs[:LEADERBOARD_N], start=1):
            ws.append([sec, i, len(rs), r.get("ticker"), r.get("name"), r.get("score"),
                       r.get("sector_neutral_score"), r.get("band"), r.get("coverage")])
            r_i = ws.max_row
            ws.cell(row=r_i, column=7).number_format = "0.0"
            ws.cell(row=r_i, column=9).number_format = "0%"
            cell = ws.cell(row=r_i, column=8)
            colour = BAND_FILLS.get(str(cell.value))
            if colour:
                cell.font = Font(color=colour, bold=True)


#: a group smaller than this is one or two companies wearing a category name, so its
#: mean says nothing about an industry. Matches the peer-median floor used in scoring.
MIN_SUB_INDUSTRY_N = 5


def _sub_industry_block(ws, rows: list[dict]) -> None:
    """The second level: sub-industries within each sector.

    Eleven sectors is the right top level for reading a ranking, but the movement is a
    level down - which sub-industries inside a sector lead and lag says more about where
    the market is than the sector average does. Groups below MIN_SUB_INDUSTRY_N are
    listed separately rather than ranked, because a "sub-industry" of two companies is
    a name, not an industry.
    """
    from openpyxl.styles import Font

    ws.append([])
    ws.append([])
    ws.append(["Sub-industries - the level below, where the movement actually shows"])
    ws.cell(row=ws.max_row, column=1).font = Font(bold=True, size=12)
    ws.append(["Ranked within each sector. A sub-industry far above or below its own "
               "sector average is the thing worth looking at."])
    ws.cell(row=ws.max_row, column=1).font = Font(italic=True, size=10)
    ws.append([])

    ws.append(["sector", "sub_industry", "companies", "mean_score", "vs_sector",
               "median", "best_company", "best_score", "bands"])
    for c in ws[ws.max_row]:
        c.font = Font(bold=True)

    by_sector: dict[str, dict[str, list[dict]]] = {}
    for r in rows:
        sec = str(r.get("sector") or "Unclassified")
        sub = str(r.get("sub_industry") or "Unclassified")
        by_sector.setdefault(sec, {}).setdefault(sub, []).append(r)

    def _scores(rs):
        return sorted(v for v in (x.get("composite_strict") for x in rs) if _finite(v))

    thin: list[tuple[str, str, int]] = []
    sector_means: dict[str, float] = {}
    for sec, subs in by_sector.items():
        allv = _scores([r for rs in subs.values() for r in rs])
        if allv:
            sector_means[sec] = sum(allv) / len(allv)

    for sec in sorted(sector_means, key=lambda s: -sector_means[s]):
        subs = by_sector[sec]
        ranked = []
        for sub, rs in subs.items():
            vals = _scores(rs)
            if not vals:
                continue
            if len(rs) < MIN_SUB_INDUSTRY_N:
                thin.append((sec, sub, len(rs)))
                continue
            best = max((x for x in rs if _finite(x.get("composite_strict"))),
                       key=lambda x: x["composite_strict"], default={})
            bands: dict[str, int] = {}
            for x in rs:
                b = x.get("band")
                if b:
                    bands[b] = bands.get(b, 0) + 1
            mean = sum(vals) / len(vals)
            ranked.append((sub, len(rs), mean, mean - sector_means[sec],
                           vals[len(vals) // 2], best.get("ticker"),
                           best.get("composite_strict"),
                           ", ".join(f"{k} {v}" for k, v in
                                     sorted(bands.items(), key=lambda kv: -kv[1]))))
        ranked.sort(key=lambda t: -t[2])
        for row in ranked:
            ws.append([sec, *row])
            r_i = ws.max_row
            for col in (4, 5, 6):
                ws.cell(row=r_i, column=col).number_format = "0.0"
            delta = ws.cell(row=r_i, column=5)
            if isinstance(row[3], (int, float)):
                delta.font = Font(bold=True,
                                  color="FF1B7F4B" if row[3] >= 0 else "FFB42318")

    if thin:
        ws.append([])
        ws.append([f"{len(thin)} sub-industries have fewer than {MIN_SUB_INDUSTRY_N} "
                   f"companies and are not ranked - a group that small is a company "
                   f"name, not an industry: "
                   + ", ".join(f"{sub} ({n})" for _s, sub, n in sorted(thin)[:12])
                   + ("..." if len(thin) > 12 else "")])
        ws.cell(row=ws.max_row, column=1).font = Font(italic=True, size=9)


def _qual_rollout(rows: list[dict]) -> dict:
    """How far through the judgement half the universe is.

    Matters because the LLM half is 50 of the 100 points. Until a company has it, its
    composite_strict is structurally ~23 points lower and it CANNOT appear near the top
    of the ranking. Ranking a half-scored universe by raw points without saying so is
    misleading by omission.

    A company can be missing BQ for two completely different reasons and they must not be
    added together. Either the crawl has NOT REACHED it yet - which a wait fixes - or the
    crawl ran and the model DECLINED to answer on enough moat dimensions, which no amount
    of waiting fixes (E12: that is the state of 462 of them). Reporting the sum as "being
    filled in at 100 a day" promised a rollout that would never finish.
    """
    def _ran(r) -> bool:
        # SG is the tell that the LLM was called at all: it has no non-LLM points, so a
        # company with SG available has been through the model whatever BQ says.
        return float(r.get("sg_available") or 0) > 0

    def _has_qual(r) -> bool:
        # SG and BQ only. MG is DELIBERATELY a mixture - 9.4 of its 15 points come from
        # filed guidance, downturn survival and capital allocation - so it has available
        # points with no LLM at all. Counting MG here reported 1,481 of 1,497 companies
        # as LLM-scored when the true figure was 698.
        return _ran(r) and float(r.get("bq_available") or 0) > 0

    with_q = [r for r in rows if _has_qual(r)]
    without = [r for r in rows if not _has_qual(r)]
    not_run = [r for r in rows if not _ran(r)]
    abstained = [r for r in rows if _ran(r) and float(r.get("bq_available") or 0) <= 0]

    def _med(rs):
        vals = sorted(v for v in (r.get("composite_strict") for r in rs)
                      if isinstance(v, (int, float)))
        return vals[len(vals) // 2] if vals else None

    return {"total": len(rows), "with_qual": len(with_q), "without_qual": len(without),
            "not_run": len(not_run), "abstained": len(abstained),
            "median_with": _med(with_q), "median_without": _med(without),
            # "complete" means the CRAWL is done. Abstention is a separate finding and
            # must not keep this false forever, or the banner never stops crying wolf.
            "complete": bool(rows) and not not_run}


def _rollout_banner(roll: dict) -> str | None:
    """The Rank sheet's one-line warning about companies missing the judgement half.

    Two causes, and the banner must name whichever is bigger FIRST while still reporting
    the other. They are not interchangeable: an unfinished crawl is fixed by waiting, and
    an abstention never is. Reporting only the unfinished crawl - which the code did while
    1 company was unreached and 462 had been refused - buries the finding behind a
    rounding error.
    """
    total = roll.get("total") or 0
    n, a = roll.get("not_run") or 0, roll.get("abstained") or 0
    if not total or not (n or a):
        return None

    tail = ("A company missing the judgement half cannot rank near the top, so this "
            "ordering reflects who has been scored as much as who is good.")
    crawl = (f"{n} of {total} companies have not been through the judgement half yet "
             f"(100 added per day), so they score out of ~50")
    refused = (f"{a} of {total} companies went through the model and it DECLINED to "
               f"answer on Business Quality, so they score 0 of 15 there - see E12 on "
               f"the Findings sheet. More crawling will not change those")
    if n and a:
        first, second = (crawl, refused) if n >= a else (refused, crawl)
        return f"{first}. Separately, {second}. {tail}"
    if n:
        return f"PARTIAL: {crawl}. {tail}"
    return f"The crawl is COMPLETE, but {refused}. {tail}"


def _sheet_findings(wb, rows: list[dict] | None = None) -> None:
    """What the studies did and did not establish. Read this before trusting a rank.

    A workbook that shows 500 confident-looking scores and says nothing about their
    measured predictive power is misleading by omission, so the negative results travel
    with the file.
    """
    from openpyxl.styles import Alignment, Font

    ws = wb.create_sheet("Findings")
    ws["A1"] = "What has and has not been established about this ranking"
    ws["A1"].font = Font(bold=True, size=13)

    exp = config.JOURNAL_DIR / "experiments"

    def percent(value) -> str:
        return "n/a" if value is None else f"{value:.1%}"

    roll = _qual_rollout(rows or [])
    # Measured off the rows BEFORE `rows` is rebound below to the findings table.
    _sector_med = _sector_medians(rows or [])
    _rollout_rows: list[tuple[str, str, str]] = []
    if roll.get("total") and roll.get("with_qual") != roll.get("total"):
        n, a = roll.get("not_run") or 0, roll.get("abstained") or 0
        was = "company was" if n == 1 else "companies were"
        why = (f"Two different reasons, and they must not be added together. {n} {was} "
               f"never reached by the crawl, which waiting fixes. The other {a} WERE "
               f"scored: the model went through them and declined to answer on enough "
               f"moat dimensions to earn any Business Quality points (E12 below). "
               f"Waiting does not fix those - only a change to the rubric or the "
               f"retrieval does.")
        _rollout_rows.append((
            "Is the whole universe scored on all 100 points?",
            f"NO - {roll['with_qual']} of {roll['total']}",
            f"{why} A company without it scores out of ~50 rather than 100 - median "
            f"{roll['median_without']} against {roll['median_with']} for companies that "
            f"have it - so it CANNOT appear near the top of the Rank sheet. Compare "
            f"within the scored group."))

    rows: list[tuple[str, str, str]] = _rollout_rows + [
        ("Validated against forward returns?",
         "NO",
         "Nothing here is promoted. Every flag file carries promoted=false and there is "
         "no code path that sets it true."),
        ("E01 - entry timing (EMAs + own-history P/E)",
         "FAILED three times",
         "Waiting for a 20-EMA touch or a low own-history P/E percentile did not improve "
         "forward returns in any of three independent constructions."),
        ("E02 - measured half over 2016-2026",
         "WEAK",
         "The decile curve was U-shaped rather than monotonic, which is what an artifact "
         "looks like, not an edge."),
        ("E03 R1 - is it a quality bet or a sector bet?",
         "SUBSTANTIALLY A SECTOR BET",
         "95.6% of the ranking power was sector selection; 18.1% of score variance was "
         "sector alone. See the Sectors sheet."),
        ("So how do I compare two companies in DIFFERENT sectors?",
         "USE sector_neutral_score, NOT score",
         (("Measured on this workbook: "
           + "; ".join(f"{s} median {m:.0f} ({b:.0%} banded, n={n})"
                       for s, n, m, b in
                       (_sector_med[0], _sector_med[len(_sector_med) // 2],
                        _sector_med[-1]))
           + f", a {_sector_med[0][2] - _sector_med[-1][2]:.0f}-point median-to-median "
             "spread. ")
          if len(_sector_med) >= 3 else "")
         + "`score` is comparable within a sector and misleading across them, so the "
           "Rank sheet carries sector_rank (place within its own sector) and "
           "sector_neutral_score (percentile among its own sub-industry peers) beside "
           "it, and the Sectors sheet ranks the top names within each sector. This is a "
           "PRESENTATION change made 2026-08-25: nothing was rescored, no weight moved, "
           "and it carries no claim that either column predicts returns. The supporting "
           "result is E14 below, which passed all four of its registered criteria and "
           "still fails the promotion gate. One trap: sector_neutral_score is a "
           "percentile of composite_strict, not of the `score` column beside it, so the "
           "two can disagree - sector_neutral_score_col records which was used."),
        ("E03 R3 - horizon",
         "3 YEARS, NOT 1",
         f"IC was far higher at three years than at one, which is why this workbook is "
         f"labelled {rubric.HORIZON_LABEL}."),
        ("E03 R4 - band stability",
         "TOO JUMPY, then fixed",
         "Bands changed in 27.2% of months with a median 2-month life. F3 now requires "
         f"{rubric.BAND_CONFIRM_READINGS} consecutive readings to change a band."),
        ("E03 R5 - cyclicals",
         "SCORE IS INVERTED FOR THEM",
         "TTM earnings peak as the cycle turns, so the score is highest at the top. F2 "
         "(mid-cycle earnings) is NOT yet implemented - treat cyclical scores with care."),
        ("E04 - survivorship",
         "WAS HIDING REAL SKILL",
         "Adding back the companies removed from the index roughly doubled the IC. The "
         "earlier U-shaped decile curve was indeed an artifact."),
        ("E05 - does the top decile beat just holding SPY?",
         "NO - median pick LOSES to SPY",
         "On the survivorship-free holdout the top decile's 3-year excess over SPY "
         "averages +11.9% but its MEDIAN is -7.6%, and only 45.3% of its picks beat "
         "SPY (48.4% at 1 year). The positive average comes from a few very large "
         "winners, so the typical top-decile name underperforms the index. This is the "
         "answer to 'should I follow this instead of holding the index': on this "
         "evidence, no."),
        ("E05 - top vs bottom decile at 3 years",
         "NOT MONOTONIC",
         "Rank correlation is positive (IC +0.081) yet the top decile's mean 3-year "
         "return is 14.1 points BELOW the bottom decile's. The bottom decile contains "
         "the violent recoveries (the CVNA pattern), so the extremes misbehave even "
         "though the middle of the ranking is ordered correctly."),
    ]

    # The repair pass, if it has run. Reported with what it could NOT cite beside what
    # it could: E17 measured 40 of 73 scores offered with no quote at all, and those earn
    # nothing here.
    rep = read_json(exp / "repair_summary.json")
    if isinstance(rep, dict) and rep.get("companies"):
        per = ", ".join(f"{c} {d.get('kept', 0)}"
                        for c, d in sorted((rep.get("by_component") or {}).items()))
        impact = read_json(exp / "repair_impact.json") or {}
        gained = impact.get("companies_repaired")
        rows.append((
            "Targeted repair pass over the judgement half",
            (f"{rep.get('kept', 0)} sub-tests recovered; "
             f"{gained} companies gained points"
             if gained is not None else
             f"{rep.get('kept', 0)} sub-tests recovered"),
            f"The first call gets one retrieval query per component and declines a great "
            f"deal. A second call asks again with a query per unanswered sub-test, and a "
            f"recovered score counts ONLY when it carries a verbatim quote found in the "
            f"filing ({rep.get('gate', 'strict')} gate). {rep.get('answered', 0)} were "
            f"answered, {rep.get('kept', 0)} could be cited and scored. The rest earn "
            f"NOTHING and are not in the Subtests sheet at all - they are counted in the "
            f"Rank sheet's repaired_points_unquoted and repaired_subtests_unquoted "
            f"columns. {rep.get('companies', 0)} companies were attempted; a recovered "
            f"sub-test only changes a score when it lifts a component over its floor. "
            f"By component: {per}. "
            f"This adds COVERAGE, not accuracy - none of it is validated against forward "
            f"returns."))

    # Studies that finished after the Findings sheet was first written. Each is read
    # from its own results file, so a study that has not run yet simply does not appear
    # rather than showing a stale hand-typed verdict.
    e06 = read_json(exp / "E06_results.json")
    if isinstance(e06, dict):
        cn = e06.get("concentration") or {}
        rows_out_extra = (
            "E06 - do insiders beat the index? (large caps)",
            "NO",
            f"Following insider buying across 675 large caps. The entire edge was "
            f"{cn.get('best_year', 2020)}: drop that one year and it falls from "
            f"{(cn.get('pooled_mean_all_years') or 0) * 100:.1f}% to "
            f"{(cn.get('pooled_mean_excluding_best_year') or 0) * 100:.1f}%. Selling "
            f"predicted too, which means the construction was measuring attention.")
        rows.append(rows_out_extra)

    e10 = read_json(exp / "E10_results.json")
    if isinstance(e10, dict):
        sp600 = (e10.get("buckets") or {}).get("sp600") or {}
        ex = ((sp600.get("ex2020") or {}).get("1y") or {})
        med = (((sp600.get("1y") or {}).get("on") or {}).get("median"))
        rows.append((
            "E10 - do insiders beat the index? (small caps)",
            "YES on the mean, NO on the median",
            f"S&P 600 open-market buying, excluding 2020: an edge of "
            f"{(ex.get('edge_mean') or 0) * 100:.1f}% over non-buyers at 1y. The size "
            f"gradient runs the way the literature says and the falsification checks "
            f"pass. BUT the median is {(med or 0) * 100:.1f}% - the typical company an "
            f"insider bought still underperformed SPY, so the edge is a right tail, not "
            f"a typical outcome. Not a tested strategy: no costs, sizing or capacity "
            f"check."))

    e08 = read_json(exp / "E08_results.json")
    if isinstance(e08, dict):
        h3 = (e08.get("h3") or {}).get("3y") or {}
        unf = (h3.get("unfiltered") or {}).get("median")
        filt = (h3.get("filtered_rising_share") or {}).get("median")
        rows.append((
            "E08 - is a cheap company cheap for a reason?",
            "NOT DEMONSTRATED",
            f"Screening out companies losing market share moved the top decile's median "
            f"3-year excess from {(unf or 0) * 100:.1f}% to {(filt or 0) * 100:.1f}%. "
            f"The effect also ran backwards - 'harvesting' (margin up, share down) was "
            f"among the BEST quadrants. Selection dominates: the subset where share is "
            f"computable performs far worse to begin with."))

    e05 = read_json(exp / "E05_results.json")
    if isinstance(e05, dict):
        for key, label in (("f1", "E05 F1 - sector-relative margins"),
                           ("f3", "E05 F3 - band hysteresis"),
                           ("f4", "E05 F4 - default to 3 years")):
            blk = e05.get(key) or {}
            if not blk:
                continue
            checks = blk.get("checks") or {}
            detail = ", ".join(f"{k}={'yes' if v else 'no'}" for k, v in checks.items())
            rows.append((label, "PASS" if blk.get("passes") else "FAIL",
                         detail or str(blk.get("note") or "")))
        rb = e05.get("f1_robustness") or {}
        if rb:
            rows.append((
                "E05 F1 - does the verdict depend on the sector definition?",
                "YES" if rb.get("verdict_depends_on_sector_definition") else "NO",
                "GICS sector is missing for every company removed from the index, so it "
                "was filled from the SEC SIC code. SIC and GICS agree on only ~78% of "
                "companies where both exist."))
    else:
        rows.append(("E05 - the four fixes", "NOT YET MEASURED",
                     "F1/F3/F4 are implemented; the holdout measurement has not been "
                     "written to E05_results.json yet."))

    e08 = read_json(exp / "E08_results.json")
    e08_limit = ("Limit: peer share covers S&P 500 large-cap listed peers only, not "
                 "true market share; private, foreign and small-cap rivals are absent.")
    if isinstance(e08, dict):
        for key, label in (("h1", "E08 H1 - rising vs declining peer share"),
                           ("h2", "E08 H2 - is harvesting the worst quadrant?"),
                           ("h4", "E08 H4 - independent of the existing score?")):
            blk = e08.get(key) or {}
            checks = blk.get("checks") or {}
            detail = ", ".join(f"{k}={'yes' if v else 'no'}"
                               for k, v in checks.items())
            rows.append((label, "PASS" if blk.get("passes") else "FAIL",
                         f"{detail}. {e08_limit}"))

        h3 = e08.get("h3") or {}
        h3_3y = h3.get("3y") or {}
        before = (h3_3y.get("unfiltered") or {}).get("median")
        after = (h3_3y.get("filtered_excluding_declining_share") or {}).get("median")
        dropped = h3_3y.get("share_of_top_decile_excluded")
        rows.append((
            "E08 H3 - does excluding declining peer-share names beat SPY?",
            "PASS" if h3.get("passes") else "FAIL",
            f"Top-decile 3-year median excess: {percent(before)} unfiltered, "
            f"{percent(after)} after excluding {percent(dropped)} of names with measured "
            f"share deterioration; NO_DATA names remain eligible. {e08_limit}"))
    else:
        rows.append(("E08 - value-trap filter", "NOT YET MEASURED",
                     "The pre-registered study has not written E08_results.json yet. "
                     f"{e08_limit}"))

    # --- the portfolio studies -------------------------------------------------------
    # E11/E13/E14 share a shape: pre-registered criteria, then the canonical overfit gate
    # applied on top. Reporting the criteria without the gate is how a SHADOW result gets
    # read as a promotable one, so both travel in the same cell, always.
    def _gate_txt(variant: dict) -> str:
        g = (variant or {}).get("gate") or {}
        dsr = (g.get("deflated_sharpe") or {}).get("ratio")
        pbo = g.get("pbo")
        if dsr is None or pbo is None:
            return "the overfit gate was not computed"
        thr = (g.get("thresholds") or {}).get("deflated_sharpe_min", 1.645)
        return (f"the overfit gate {'PASSES' if g.get('passes') else 'FAILS'}: deflated "
                f"Sharpe {dsr:.2f} against a {thr} threshold, PBO {pbo:.2f}")

    e09 = read_json(exp / "E09_results.json")
    if isinstance(e09, dict):
        rows.append((
            "E09 - should the fundamentals come from somewhere other than EDGAR?",
            "NO - EDGAR STAYS",
            "The commercial alternative was tested on five filers and rejected on three "
            "counts: no per-number traceability back to a filing tag, depth only to 2017 "
            "against EDGAR's ~2009, and disagreement with the filings where it matters - "
            "JPM's 2018 revenue differs by 16%. Every number in this workbook is still "
            "traceable to a us-gaap tag in a filed document."))

    e11 = read_json(exp / "E11_results.json")
    if isinstance(e11, dict):
        v = (e11.get("variants") or {}).get("sp600_insiders_ge_3") or {}
        rows.append((
            "E11 - is E10's insider edge actually investable?",
            "PASSES THE ECONOMICS, FAILS THE GATE",
            f"All six registered criteria passed - net of a 40 bps round trip, with a "
            f"capacity check and a breakeven cost of "
            f"{v.get('breakeven_cost_bps', 0):.0f} bps - and it still does not clear the "
            f"overfit gate. {e11.get('headline') or ''} Status "
            f"{e11.get('status', 'SHADOW')}, promoted="
            f"{str(e11.get('promoted')).lower()}."))

    e13f = read_json(exp / "E13_results_v2_full.json")
    e13m = read_json(exp / "E13_results_v2_matched.json")
    if isinstance(e13f, dict):
        v = (e13f.get("variants") or {}).get("top20") or {}
        rows.append((
            "E13 - does a top-20 portfolio of the measured half make money?",
            "NO - FLAT ON THE FULL UNIVERSE",
            f"1,449 symbols, 120 months, 12-month hold, 40 bps round trip: "
            f"{(v.get('annualised_excess_net_ex2020') or 0) * 100:+.1f}% annualised "
            f"excess ex-2020, median month "
            f"{((v.get('monthly_excess_net') or {}).get('median') or 0) * 100:+.2f}%, "
            f"and {_gate_txt(v)}. Widening to the top 40 or 80 does not rescue it."))
    if isinstance(e13m, dict) and isinstance(e13f, dict):
        vm = (e13m.get("variants") or {}).get("top20") or {}
        rows.append((
            "E13 - so why did an earlier run of this look better?",
            "IT WAS A LARGE-CAP ARTEFACT",
            f"Restricting to the 619 symbols of the earlier large-cap panel turns the "
            f"same construction positive "
            f"({(vm.get('annualised_excess_net_ex2020') or 0) * 100:+.1f}% ex-2020, "
            f"registered verdict {e13m.get('overall_registered')}) while the full "
            f"universe is flat. The apparent edge was the universe, not the score. Both "
            f"numbers sit here on purpose - reporting the favourable one alone IS the "
            f"artefact."))

    e14 = read_json(exp / "E14_results.json")
    if isinstance(e14, dict):
        v = (e14.get("variants") or {}).get("neutral_top20") or {}
        raw = (e14.get("variants") or {}).get("raw_top20") or {}
        comp = v.get("composition") or {}
        rows.append((
            "E14 - does ranking WITHIN each sector pick better than ranking raw?",
            "GENUINELY BETTER, STILL FAILS THE GATE",
            f"All four registered criteria passed: "
            f"{(v.get('annualised_excess_net_ex2020') or 0) * 100:+.1f}% annualised "
            f"excess ex-2020 against "
            f"{(raw.get('annualised_excess_net_ex2020') or 0) * 100:+.1f}% for the raw "
            f"ranking, and it survives the control that asks whether this is merely "
            f"diversification ({comp.get('mean_distinct_sectors')} sectors held on "
            f"average, largest weight "
            f"{(comp.get('mean_largest_sector_weight') or 0):.0%}). This is the direct "
            f"follow-on from E03 R1's sector-bet finding and it is the strongest result "
            f"in the project. It is still not promotable: {_gate_txt(v)}. Status "
            f"{e14.get('status', 'SHADOW')}, promoted="
            f"{str(e14.get('promoted')).lower()}."))

    # --- the Business Quality abstention block ---------------------------------------
    # E12's measurement writes a DATED file on each run and has no stable name, so read
    # the newest and let the row say which day it came from. This is the largest single
    # sink in the whole system; it belongs beside the scores rather than in a journal.
    _abst = sorted(exp.glob("E12_abstention_*.json"))
    e12 = read_json(_abst[-1]) if _abst else None
    if isinstance(e12, dict):
        below, total = e12.get("below_floor"), e12.get("companies")
        worst = sorted((e12.get("null_rate_by_dimension") or {}).items(),
                       key=lambda kv: -kv[1])[:4]
        rows.append((
            "E12 - how often does the model DECLINE to answer on Business Quality?",
            f"{below} of {total} SCORE ZERO",
            f"Measured {_abst[-1].stem.split('_')[-1]}. Every one of those companies went "
            f"through the LLM; it returned no usable answer on enough moat dimensions to "
            f"reach the {e12.get('floor')}-dimension floor, so BQ scores 0 of 15. That is "
            f"{(below or 0) * 15:,} points of NO_DATA, the largest single sink in the "
            f"system, and it is why median coverage sits where it does - crawling more "
            f"filings will not move it. Worst dimensions: "
            + ", ".join(f"{k} {v:.0f}% null" for k, v in worst)
            + ". A model bake-off (E07) found that every candidate which abstains less "
              "also fabricates more, so the answer is not simply a bigger model."))

    e15 = read_json(exp / "E15_results.json")
    if isinstance(e15, dict):
        eos = (e15.get("weak_dimension_recovery") or {}).get("economies_of_scale") or {}
        rows.append((
            "E15 - does asking a second, targeted question fix that abstention?",
            "NO - FAILED 3 OF 4",
            f"REPLACING the call with a weak-dimension-targeted one moved the median "
            f"dimensions scored {e15.get('median_dims_A')} -> {e15.get('median_dims_B')} "
            f"against a registered bar of +1.5, and cost "
            f"{len(e15.get('controls_losing_a_dimension') or [])} of "
            f"{e15.get('n_control')} CONTROL companies a dimension they already had - a "
            f"repair that damages what it was not aimed at. One useful fact survived: "
            f"economies_of_scale went {eos.get('A')} -> {eos.get('B')} of "
            f"{e15.get('n_under')}, so ONE of the four weak dimensions is a retrieval "
            f"failure and the other three are not."))

    e16 = read_json(exp / "E16_results.json")
    if isinstance(e16, dict):
        rows.append((
            "E16 - does an ADDITIVE repair pass fix it without that damage?",
            f"YES ON CLEARANCE ({e16.get('Q1_cleared_pct')}%), NOT IN PRODUCTION",
            f"Keeping the original call and adding a second that may only ADD dimensions: "
            f"{e16.get('cleared_before')} -> {e16.get('cleared_after')} of "
            f"{e16.get('n_under')} under-floor companies cleared the floor, "
            f"{len(e16.get('Q3_controls_losing_a_dimension') or [])} controls lost "
            f"anything, and economies_of_scale recovered "
            f"{e16.get('Q4_economies_of_scale_pct')}%. Two caveats that belong next to "
            f"that number. Without economies_of_scale most of those companies would still "
            f"be under the floor. And re-running the UNCHANGED prompt cleared 10 of "
            f"{e16.get('n_under')} on its own, so part of this is run-to-run variance at "
            f"temperature 0.1 rather than structure. The fabrication criterion Q2 could "
            f"not succeed as written - one quote per call makes 0.00% or >=1.92% the only "
            f"reachable rates - so it is recorded FAIL and replaced by E17, not waived."))

    e17 = read_json(exp / "E17_results.json")
    if isinstance(e17, dict):
        y = e17.get("R2_yield") or {}
        strict_kept = (y.get("strict") or {}).get("kept") or 0
        strict_pct = (y.get("strict") or {}).get("pct") or 0
        prod_kept = (y.get("production") or {}).get("kept") or 0
        quoted = (y.get("has_quote") or {}).get("kept") or 0
        proposed = round(strict_kept / strict_pct * 100) if strict_pct else 0
        # The registered rule is R1 AND R3 AND R4, so R1 passing is not the verdict.
        rows.append((
            "E17 - can fabrication be made IMPOSSIBLE rather than measured afterwards?",
            "YES, BUT THE REGISTERED RULE FAILED",
            f"Requiring a verbatim quote per recovered dimension, and DROPPING any "
            f"dimension whose quote does not verify, holds up on two of three bars: "
            f"floor clearance {e17.get('R1_cleared_strict')} of "
            f"{e17.get('n_under_total')} ({e17.get('R1_cleared_strict_pct')}%, R1 bar "
            f"35% - PASS) and {len(e17.get('R3_controls_losing_a_dimension') or [])} "
            f"controls damaged (R3 PASS). R4 FAILS: economies_of_scale recovery is "
            f"{e17.get('R4_eos_strict_pct')}% against a 50% bar, where E16 measured "
            f"67.8% with no verification at all. R1 AND R3 AND R4 was the registered "
            f"rule, so the repair pass does NOT reach production. Read E16's 52.5% "
            f"clearance as {e17.get('R1_cleared_strict_pct')}%: about two thirds of what "
            f"it recovered cannot be traced to a sentence in the filing. The leak is not "
            f"the paraphrase this was built to catch - "
            f"{e17.get('quotes_missing_entirely')} of {proposed} proposed dimensions "
            f"came with NO QUOTE AT ALL, and the {quoted} that did were near-verbatim "
            f"(median token overlap {e17.get('median_overlap')}), so production's 0.60 "
            f"gate rescues only {prod_kept - strict_kept} of what the strict gate "
            f"rejects. The registered prediction - that 0.60 would wave through over 90% "
            f"of the strict rejections - was wrong, and wrong in the reassuring "
            f"direction. The exposure worth worrying about is a scored dimension with NO "
            f"evidence attached, not a cleverly worded one."))
    else:
        rows.append((
            "E17 - can fabrication be made IMPOSSIBLE rather than measured afterwards?",
            "NOT YET MEASURED",
            "Pre-registered: the repair call must supply a verbatim quote per recovered "
            "dimension, and a dimension whose quote does not verify against the evidence "
            "pack is DROPPED rather than scored, so invention cannot reach the composite "
            "at all. It also measures today's defence, which accepts a quote at 0.60 "
            "token overlap - a paraphrase built from the pack's own vocabulary passes "
            "that. The run has not completed and nothing in this workbook has changed as "
            "a result of it."))

    # E29 asked whether the sector gap is the framework asking questions that have no
    # referent. The honest answer was no, and an empty map is a result: it belongs beside
    # the scores precisely because "we checked and refused it" is the kind of finding
    # that otherwise disappears into a journal file.
    e29 = read_json(exp / "E29_results.json")
    if isinstance(e29, dict) and e29.get("candidates"):
        cands = e29["candidates"]
        passed = [c for c in cands if c.get("machine_criteria_pass")]
        item = e29.get("itemisation") or {}
        re_ = item.get("Real Estate") or {}
        rows.append((
            "E29 - is Real Estate's low score the rubric asking questions it has no "
            "answer to?",
            "NO - THE MAP IS EMPTY",
            f"A per-sector applicability map would let a REIT stop being asked about "
            f"things a REIT does not have. Of {len(cands)} (sub-test, sector) pairs, "
            f"{len(passed)} cleared the null-rate criteria and it was then REFUSED on "
            f"the criterion that mattered - E12's P3, a named written business reason. "
            f"The predicted winner, backlog-and-contracts for Real Estate, failed "
            f"outright: 34.9% of REITs were scored on it, because a long-term lease IS "
            f"contracted forward revenue. Nothing was rescored. What the measurement did "
            f"establish is that `sg_tam_expanding` is 22.1% null in Information "
            f"Technology and 64-85% null in nine of the other ten sectors - a question "
            f"that only works for high-growth technology businesses, which is a "
            f"retrieval problem and not an applicability one. And the split that reframes "
            f"the whole complaint: Real Estate loses "
            f"{re_.get('category_error_total', 0):,} judged points to questions it was "
            f"never assessed on and {re_.get('scored_shortfall_total', 0):,} to questions "
            f"the model DID assess and scored low. Every sector's shortfall exceeds its "
            f"category error. Use sector_neutral_score for the cross-sector comparison; "
            f"the rubric was not the problem."))

    # E30/E31/E32 are not studies about predictive power - they are about whether the
    # numbers are RIGHT. A workbook that reports what a score predicts and never reports
    # whether its inputs were correct is missing the more basic question, and 2026-08-25
    # answered it four times in a row with "no".
    e30 = read_json(exp / "E30_results_after.json")
    if isinstance(e30, dict) and e30.get("records"):
        rows.append((
            "Are the INPUTS right? (E30 - every sub-test audited in every sector)",
            "FOUR BUGS FOUND AND FIXED",
            "A per-sector audit of all 473 (sub-test x sector) cells asked what a "
            "coverage figure cannot: does this metric separate any two companies HERE? "
            "It found (1) `bs_dilution` earning nothing in all eleven sectors - the "
            "prior-year share count skipped a filter the current one had, so median "
            "share growth read +32.5% and every company looked like it was issuing a "
            "third of its shares a year; (2) revenue resolving to a FRAGMENT for 1 "
            "company in 22 - Equity Residential read $216,000 against a real ~$2.9bn, "
            "Humana $6.18bn against $137.2bn; (3) a lessor's rent invisible to the "
            "revenue chain, leaving REITs scored on six-year-old revenue; (4) stranded "
            "income-statement lines withheld while their own derivation sat unused. "
            "Data-quality failures fell 502 -> 307. AND THE RESULT THAT MATTERS: fixing "
            "all four moved sector medians by about one point and changed 17 of 1,501 "
            "bands. The cross-sector gap is not broken inputs, just as E29 found it is "
            "not the rubric. Use sector_neutral_score to compare across sectors."))
    e32 = read_json(exp / "E32_results.json")
    if isinstance(e32, dict) and e32.get("sectors"):
        worst = max(e32["sectors"].items(),
                    key=lambda kv: kv[1].get("constant_share_of_earned") or 0)
        rows.append((
            "How much of a sector's score separates nobody? (E32)",
            f"AT MOST {(worst[1].get('constant_share_of_earned') or 0):.1%}",
            f"A sub-test where nearly every company in a sector earns the same number is "
            f"weight without information. The worst case is {worst[0]} at "
            f"{(worst[1].get('constant_share_of_earned') or 0):.1%} of earned points - "
            f"about one point - and eight of eleven sectors have none at all. Nothing "
            f"was changed: a per-sector threshold cannot be calibrated without a "
            f"forward-return grader, and inventing one is what this project refuses to "
            f"do. Worth knowing because the constant part bounds how much of a "
            f"sector-to-sector gap is an artefact: at most ~2 points of the 27 between "
            f"Information Technology and Real Estate."))

    judged = ", ".join(rubric.JUDGED_COMPONENTS)
    rows.append((f"Judged half ({judged} - {rubric.JUDGED_POINTS} of "
                 f"{rubric.TOTAL_POINTS} points)", "LLM, UNREVIEWED",
                 f"Generated by a local {config.QUAL_MODEL} with no human review step. "
                 f"Sub-tests sourced from it are marked LLM on the dashboard. The other "
                 f"{rubric.MEASURED_POINTS} points are measured from filings. These "
                 f"totals are read from the framework itself, not typed here - the "
                 f"framework went from 100 points to {rubric.TOTAL_POINTS} at E26 and "
                 f"this sheet went on saying '50 of 100' for weeks."))
    rows.append(("Coverage gate", f"below {rubric.MIN_COVERAGE_FOR_BAND:.0%} = no band",
                 "A company scored on too little of the framework reads "
                 "INSUFFICIENT_DATA rather than getting a flattering label."))

    ws.append([])
    ws.append(["question", "answer", "detail"])
    for c in ws[ws.max_row]:      # after the append: an empty append does not move max_row
        c.font = Font(bold=True)
    for q, a, d in rows:
        ws.append([q, a, d])
        cell = ws.cell(row=ws.max_row, column=2)
        low = str(a).lower()
        if low.startswith(("no", "fail", "weak", "too jumpy", "substantially",
                           "score is inverted")):
            cell.font = Font(bold=True, color="FFB42318")
        elif low.startswith(("pass", "yes")):
            cell.font = Font(bold=True, color="FF1B7F4B")
        ws.cell(row=ws.max_row, column=3).alignment = Alignment(wrap_text=True,
                                                               vertical="top")
    _autosize(ws, max_width=44)
    ws.column_dimensions["C"].width = 78


def _sheet_changes(wb, rows: list[dict]) -> None:
    """Week-over-week moves, so the workbook can be READ each week rather than re-read.

    Compares today's scores against the most recent weekly snapshot at least 5 days old.
    A band move is listed before a score move because the band is what the user acts on.
    """
    from openpyxl.styles import Font

    ws = wb.create_sheet("Changes")
    prev, prev_day = _previous_snapshot()
    if prev is None:
        ws["A1"] = ("No earlier weekly snapshot to compare against yet. Snapshots cannot "
                    "be backfilled, so this sheet fills in from the second weekly run.")
        ws["A1"].font = Font(italic=True)
        _autosize(ws)
        return

    import datetime as _dt

    try:
        gap = (_dt.date.today() - _dt.date.fromisoformat(prev_day)).days
        gap_txt = f"{gap} day{'s' if gap != 1 else ''} ago"
    except ValueError:
        gap_txt = "unknown age"
    ws["A1"] = (f"Change since the snapshot of {prev_day} ({gap_txt}). Band moves first - "
                f"the band is what gets acted on; a 1-point score wobble is not news.")
    ws["A1"].font = Font(italic=True, size=11)

    # If the FRAMEWORK changed between the two dates, most of the moves below are the
    # reweighting rather than anything the companies did. Detectable from the component
    # maxima, and stating it is the difference between a change log and a misleading one.
    reweighted = _reweighting_between(prev, rows)
    if reweighted:
        ws["A2"] = ("WARNING: the framework itself changed between these two dates, so "
                    "many moves below are the reweighting, NOT company news. Components "
                    "whose maximum changed: " + ", ".join(reweighted))
        ws["A2"].font = Font(bold=True, color="FFB42318", size=11)
    ws.append([])
    ws.append(["ticker", "sector", "band_now", "band_then", "band_moved",
               "score_now", "score_then", "score_change", "coverage_now",
               "coverage_then"])
    for c in ws[ws.max_row]:      # after the append: an empty append does not move max_row
        c.font = Font(bold=True)

    out = []
    for r in rows:
        t = r.get("ticker")
        old = prev.get(t)
        if not old:
            continue
        now_s, then_s = r.get("composite_strict"), old.get("composite_strict")
        delta = (now_s - then_s if isinstance(now_s, (int, float))
                 and isinstance(then_s, (int, float)) else None)
        moved = (r.get("band") != old.get("band")) and bool(r.get("band")) \
            and bool(old.get("band"))
        out.append({"ticker": t, "sector": r.get("sector"), "band": r.get("band"),
                    "band_then": old.get("band"), "moved": moved,
                    "now": now_s, "then": then_s, "delta": delta,
                    "cov": r.get("coverage"), "cov_then": old.get("coverage")})

    out.sort(key=lambda d: (not d["moved"], -abs(d["delta"] or 0)))
    for d in out:
        ws.append([d["ticker"], d["sector"], d["band"], d["band_then"],
                   "YES" if d["moved"] else "", d["now"], d["then"], d["delta"],
                   d["cov"], d["cov_then"]])
        if d["moved"]:
            for col in range(1, 6):
                ws.cell(row=ws.max_row, column=col).font = Font(bold=True)

    n_moved = sum(1 for d in out if d["moved"])
    new_names = [r.get("ticker") for r in rows if r.get("ticker") not in prev]
    gone = [t for t in prev if t not in {r.get("ticker") for r in rows}]
    ws.append([])
    ws.append([f"{n_moved} of {len(out)} compared companies changed band."])
    ws.cell(row=ws.max_row, column=1).font = Font(bold=True)
    if new_names:
        ws.append([f"new since {prev_day} ({len(new_names)}): "
                   + ", ".join(sorted(map(str, new_names))[:40])])
    if gone:
        ws.append([f"absent since {prev_day} ({len(gone)}): "
                   + ", ".join(sorted(map(str, gone))[:40])])
    _autosize(ws, max_width=60)


def _reweighting_between(prev: dict, rows: list[dict]) -> list[str]:
    """Components whose MAXIMUM differs between the snapshot and today.

    A component max is a property of the rubric, not of a company, so a change here means
    the framework was reweighted between the two dates. Without this note a reweighting
    reads as 500 companies simultaneously changing quality - which is how the weights v2
    change (FE 15->18, EN 5->2) appeared in the first build of this sheet.
    """
    changed: list[str] = []
    if not prev or not rows:
        return changed
    sample = next(iter(prev.values()))
    for comp in rubric.COMPONENT_ORDER:
        key = f"{comp.lower()}_max"
        then = sample.get(key)
        now = next((r.get(key) for r in rows if r.get(key) is not None), None)
        if (then is not None and now is not None
                and isinstance(then, (int, float)) and isinstance(now, (int, float))
                and int(then) != int(now)):
            changed.append(f"{comp} {int(then)}->{int(now)}")
    return changed


def _previous_snapshot(min_age_days: int = 5) -> tuple[dict | None, str | None]:
    """{ticker: row} from the newest weekly snapshot at least `min_age_days` old.

    The age floor is what makes this a WEEK-over-week comparison: the crawl also runs on
    the snapshot day, and diffing against a file written hours earlier would show nothing.

    Falls back to the OLDEST snapshot on disk when nothing is that old yet, so the sheet
    is useful before a full week of history exists. The caller prints the real gap, so a
    two-day comparison is never presented as a week.
    """
    import datetime as _dt

    def _load(path):
        try:
            import pandas as pd

            df = pd.read_parquet(path)
        except Exception:  # noqa: BLE001 - a corrupt snapshot must not fail the workbook
            return None
        if "ticker" not in df.columns:
            return None
        return {str(r["ticker"]): dict(r) for _i, r in df.iterrows()}

    snaps = []
    for path in sorted((config.JOURNAL_DIR / "snapshots").glob("scores_*.parquet")):
        day = path.stem.replace("scores_", "")
        try:
            snaps.append((_dt.date.fromisoformat(day), day, path))
        except ValueError:
            continue
    if not snaps:
        return None, None

    today = _dt.date.today()
    for d, day, path in reversed(snaps):
        if (today - d).days < min_age_days:
            continue
        loaded = _load(path)
        if loaded is not None:
            return loaded, day
    # nothing old enough yet: use the oldest we have rather than showing an empty sheet
    for d, day, path in snaps:
        loaded = _load(path)
        if loaded is not None:
            return loaded, day
    return None, None



# --------------------------------------------------------------- external layer
#: The company-level external columns a human wants, plus the freshness columns that
#: make "how old is this research" answerable without opening a database.
EXTERNAL_COLUMNS = [
    "ticker", "sector_id", "industry_id", "external_score", "external_coverage",
    "current_moat_strength", "competitive_position", "moat_trajectory",
    "pricing_power", "regulatory_risk", "disruption_risk",
    "last_research_date", "next_refresh_due", "days_since_research", "refresh_due",
    "research_version", "research_depth",
]

EXTERNAL_INDUSTRY_COLUMNS = [
    "industry_id", "sector_id", "structural_growth", "replication_difficulty",
    "substitution_risk", "refresh_class", "next_refresh_due", "version",
    "key_metrics", "brief",
]

EXTERNAL_CLAIM_COLUMNS = [
    "claim_id", "ticker", "industry_id", "field", "verify_status",
    "independence_domain", "source_date", "source_title", "source_url", "quote",
]



def _excel_safe(v):
    """Excel cannot store a timezone-aware datetime - openpyxl raises on save.

    The external store's date columns are TIMESTAMPTZ, so every value read out of it and
    written to a cell has to be flattened first. This raised only at SAVE time, which
    meant the workbook built cleanly and then died writing the file - the sheets looked
    fine right up until nothing shipped.
    """
    import datetime as _dt
    if isinstance(v, _dt.datetime):
        return v.replace(tzinfo=None) if v.tzinfo is not None else v
    if isinstance(v, (list, dict)):
        return str(v)
    return v


def _sheet_external_block(wb, rows: list[dict], sheets) -> None:
    """Fold the external research layer into the ONE workbook a human opens.

    Defensive about ABSENCE, loud about BREAKAGE. No external database at all is a
    legitimate state - the layer is optional and the weekly artifact must not depend on
    it - so the sheets are simply skipped. But a database that EXISTS and fails to read
    is a wiring bug, and it raises rather than shipping a workbook that silently lost a
    sheet. That distinction is the difference between thin data and the failure this
    repo keeps rediscovering.
    """
    import datetime as dt
    from .. import config

    if not config.EXTERNAL_DB.exists():
        return

    from ..external.store import ExternalStore
    from ..external.taxonomy import resolve

    today = dt.date.today()
    sect = {}
    for r in rows:
        try:
            sect[r.get("ticker")] = resolve(
                r.get("ticker"), r.get("sector"), r.get("sub_industry"))["sector_id"]
        except Exception:
            sect[r.get("ticker")] = None

    st = ExternalStore(config.EXTERNAL_DB)
    with st.connect() as con:
        # THE ACTIVE CORPUS, not every stored arm. `company_external` is keyed
        # (ticker, research_version) and a company legitimately carries several - E51 and
        # E53 were re-runs, E59's batch 1 was burned after a peer defect. A plain SELECT
        # showed all of them, so the workbook listed a company once per arm INCLUDING
        # arms we rejected, with nothing marking which was current.
        #
        # `latest_companies()` resolves a retired newest arm by following superseded_by,
        # and omits the company when there is no replacement - the E53 case, where a
        # fallback silently served 59 utilities their pre-fix arm at 8.5% fill against
        # 65.7%. A company missing from this sheet has no current research, which is a
        # coverage gap and is meant to be visible as one.
        companies = st.latest_companies()
        industries = _active_industry_rows(con)
        claim_cols = [d[0] for d in con.execute(
            "SELECT * FROM external_claim LIMIT 1").description]
        claims = [dict(zip(claim_cols, r)) for r in con.execute(
            "SELECT * FROM external_claim ORDER BY ticker, industry_id, field"
        ).fetchall()]

    if "external" in sheets and companies:
        ws = wb.create_sheet("External")
        ws.append(["External research on each company. `days_since_research` and "
                   "`refresh_due` are the freshness columns - a blank research date "
                   "means this company has never been researched, which is NOT a "
                   "negative signal, it is an absence."])
        _header(ws, EXTERNAL_COLUMNS)
        hdr = ws.max_row
        for c in companies:
            last = c.get("last_research_date")
            last_d = last.date() if hasattr(last, "date") else last
            days = None
            if isinstance(last_d, dt.date):
                days = (today - last_d).days
            nxt = c.get("next_refresh_due")
            nxt_d = nxt.date() if hasattr(nxt, "date") else nxt
            due = ""
            if isinstance(nxt_d, dt.date):
                due = "DUE" if nxt_d <= today else ""
            c = dict(c)
            c["sector_id"] = sect.get(c.get("ticker"))
            c["days_since_research"] = days
            c["refresh_due"] = due
            ws.append([_excel_safe(c.get(k)) for k in EXTERNAL_COLUMNS])
        _filterable(ws, EXTERNAL_COLUMNS, header_row=hdr)
        _autosize(ws)

    if "industries" in sheets and industries:
        ws = wb.create_sheet("Industries")
        ws.append(["The ACTIVE industry corpus - one row per industry, current version, "
                   "retired objects excluded. Superseded objects are kept in the store "
                   "for audit and are reachable there, not here."])
        _header(ws, EXTERNAL_INDUSTRY_COLUMNS)
        hdr = ws.max_row
        for d in industries:
            ws.append([_excel_safe(d.get(k)) for k in EXTERNAL_INDUSTRY_COLUMNS])
        _filterable(ws, EXTERNAL_INDUSTRY_COLUMNS, header_row=hdr)
        _autosize(ws)

    if "claims" in sheets and claims:
        ws = wb.create_sheet("Claims")
        ws.append(["Every cited claim behind the external layer. This is the audit "
                   "trail, not a reading sheet - one row per claim, with the verbatim "
                   "quote and the source it came from."])
        _header(ws, EXTERNAL_CLAIM_COLUMNS)
        hdr = ws.max_row
        for c in claims:
            ws.append([_excel_safe(c.get(k)) for k in EXTERNAL_CLAIM_COLUMNS])
        _filterable(ws, EXTERNAL_CLAIM_COLUMNS, header_row=hdr)
        _autosize(ws)


def _active_industry_rows(con) -> list[dict]:
    """One row per industry: latest version, nothing superseded.

    Same parsed-version rule as the store and `xlsx_external.active_industries`. The
    table is keyed (industry_id, version), so a plain SELECT shows every re-cut; the
    shared helper selects the newest row and applies retirement after selection.
    """
    cur = con.execute("SELECT * FROM industry_intelligence")
    names = [d[0] for d in cur.description]
    rows = [dict(zip(names, r)) for r in cur.fetchall()]
    return select_active_industries(rows)


def build_workbook(rows: list[dict], *, cards: list[dict] | None = None,
                   sheets: tuple[str, ...] = ALL_SHEETS):
    """Return an openpyxl Workbook. `cards` are full scorecard dicts."""
    from openpyxl import Workbook

    # The Rank sheet now LEADS with sector_rank / sector_neutral_score, so they cannot be
    # allowed to render blank. The crawl already computes them, but a workbook rebuilt
    # from a parquet written before 2026-08-25 has no sector_rank column at all, and a
    # silently empty headline column is precisely the failure mode this repo keeps
    # hitting. No-op on the normal path.
    from ..scoring import sector_neutral
    sector_neutral.ensure(rows)

    cards = cards if cards is not None else _load_cards(rows)
    wb = Workbook()
    wb.remove(wb.active)
    if "rank" in sheets:
        _sheet_rank(wb, rows)
    if "changes" in sheets:
        _sheet_changes(wb, rows)
    if "sectors" in sheets:
        _sheet_sectors(wb, rows)
    if "findings" in sheets:
        _sheet_findings(wb, rows)
    if "entry" in sheets:
        _sheet_entry(wb, rows)
    if "components" in sheets:
        _sheet_components(wb, cards)
    if "subtests" in sheets:
        _sheet_subtests(wb, cards)
    if "thesis" in sheets:
        _sheet_thesis(wb, cards)
    if "valuation" in sheets:
        _sheet_valuation(wb, cards)
    if "dcf" in sheets:
        _sheet_dcf(wb, rows)
    if "stress" in sheets:
        _sheet_stress(wb, cards)
    if "meta" in sheets:
        _sheet_meta(wb, rows)
    # The external research layer, folded into the ONE workbook a human opens rather
    # than living in a second file. It is defensive on purpose: a cold or absent
    # external store must never take the weekly artifact down with it.
    if any(s in sheets for s in ("external", "industries", "claims")):
        _sheet_external_block(wb, rows, sheets)
    if not wb.sheetnames:            # openpyxl refuses to save a book with no sheets
        _sheet_meta(wb, rows)
    _apply_sheet_order(wb)
    return wb


def _load_cards(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        d = read_json(config.SCORECARD_DIR / f"{r.get('cik')}_{r.get('ticker')}.json")
        if isinstance(d, dict):
            out.append(d)
    return out


def to_bytes(rows: list[dict], *, cards: list[dict] | None = None,
             sheets: tuple[str, ...] = ALL_SHEETS) -> bytes:
    buf = io.BytesIO()
    build_workbook(rows, cards=cards, sheets=sheets).save(buf)
    return buf.getvalue()


def write_workbook_file(path: Path, rows: list[dict], *,
                        cards: list[dict] | None = None,
                        sheets: tuple[str, ...] = ALL_SHEETS) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".xlsx.tmp")
    tmp.write_bytes(to_bytes(rows, cards=cards, sheets=sheets))
    tmp.replace(path)
    return path
