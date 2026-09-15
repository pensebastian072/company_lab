"""Point-in-time S&P 500 membership, reconstructed backwards from today.

Why this exists: every result in E01/E02/E03 was computed on **today's** index members,
so companies that scored badly and were then removed are absent from the data. That
makes the bottom decile "low scores that survived", which is close to a definition of
names that were beaten down and recovered. It biases every long result and it makes the
Balance Sheet component untestable, because every company it would have saved you from
is missing by construction.

The fix, in two halves:

  1. WHO was in the index on a past date. Reconstructed here, by walking the Wikipedia
     changes table backwards from the current constituents: to step back past a change,
     un-add what was added and re-add what was removed.
  2. WHAT their prices were. `D:\\ohlcv_1m` retains delisted tickers - stock_xsect_lab
     documents that 75.7% of 1992's names are absent by 2026 and still in the panel -
     so the price side is solved by joining to that archive rather than to yfinance,
     which will not serve a delisted ticker.

Fundamentals for a removed company are still on EDGAR under its old CIK; the hard part
is the ticker->CIK mapping, because `company_tickers.json` only lists current
registrants. Resolution rates are measured and reported rather than assumed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from .. import config
from ..net import atomic_write_json
from . import edgar_tickers as et

MONTHS = ("january", "february", "march", "april", "may", "june", "july", "august",
          "september", "october", "november", "december")


def parse_change_date(raw: str) -> date | None:
    """Wikipedia writes 'August 5, 2026'. Also tolerates ISO and a few variants."""
    if not raw or not isinstance(raw, str):
        return None
    s = raw.strip().replace("\u00a0", " ")
    s = re.sub(r"\[.*?\]", "", s).strip()          # drop footnote markers
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        pass
    m = re.match(r"([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})", s)
    if m:
        mon = m.group(1).lower()
        if mon in MONTHS:
            try:
                return date(int(m.group(3)), MONTHS.index(mon) + 1, int(m.group(2)))
            except ValueError:
                return None
    m = re.match(r"([A-Za-z]+)\s+(\d{4})", s)      # month + year only
    if m and m.group(1).lower() in MONTHS:
        return date(int(m.group(2)), MONTHS.index(m.group(1).lower()) + 1, 1)
    return None


def _tickers(cell) -> list[str]:
    """A change cell can hold several tickers, or junk."""
    if cell is None or not isinstance(cell, str):
        return []
    s = cell.strip()
    if not s or s.lower() in ("nan", "none", "-", "—"):
        return []
    parts = re.split(r"[,/;]| and ", s)
    out = []
    for p in parts:
        t = re.sub(r"[^A-Za-z0-9.\-]", "", p).strip()
        if 1 <= len(t) <= 8 and any(c.isalpha() for c in t):
            out.append(et.normalize_ticker(t))
    return out


@dataclass
class Reconstruction:
    by_date: dict[date, set[str]] = field(default_factory=dict)
    ever: set[str] = field(default_factory=set)
    current: set[str] = field(default_factory=set)
    unparsed_dates: int = 0
    n_changes: int = 0
    warnings: list[str] = field(default_factory=list)

    @property
    def removed_since_start(self) -> set[str]:
        """Names that appear in history but are NOT in the index today - the hole."""
        return self.ever - self.current


def reconstruct(start: str = "2016-01-01") -> Reconstruction:
    """Membership at each month-end from `start` to today, walking changes backwards.

    To step back across a change: whatever was ADDED on that date was not a member
    before it, and whatever was REMOVED was.
    """
    r = Reconstruction()
    members_file = config.UNIVERSE_MEMBERS
    changes_file = config.UNIVERSE_CHANGES
    if not members_file.exists() or not changes_file.exists():
        r.warnings.append("members.parquet or changes.parquet missing - run the crawl first")
        return r

    mem = pd.read_parquet(members_file)
    mem = mem[mem.tier == "sp500"]
    latest = mem[mem.as_of == mem.as_of.max()]
    current = {et.normalize_ticker(str(t)) for t in latest.ticker}
    r.current = set(current)

    ch = pd.read_parquet(changes_file)
    ch = ch[ch.tier == "sp500"].copy()
    ch["d"] = ch["date"].map(parse_change_date)
    r.unparsed_dates = int(ch["d"].isna().sum())
    ch = ch.dropna(subset=["d"]).sort_values("d", ascending=False)
    r.n_changes = int(len(ch))

    start_d = date.fromisoformat(start)
    today = date.today()
    # month-ends, newest first, so we can unwind as we go
    grid = sorted(pd.date_range(start=start_d, end=today, freq="ME").date, reverse=True)

    working = set(current)
    r.by_date[today] = set(working)
    ci = 0
    rows = ch.to_dict("records")

    for me in grid:
        # unwind every change that happened AFTER this month-end
        while ci < len(rows) and rows[ci]["d"] > me:
            row = rows[ci]
            for t in _tickers(row.get("added_ticker")):
                working.discard(t)          # it was not a member before it was added
            for t in _tickers(row.get("removed_ticker")):
                working.add(t)              # it WAS a member before it was removed
            ci += 1
        r.by_date[me] = set(working)
        r.ever |= working

    r.ever |= current
    return r


def to_frame(r: Reconstruction) -> pd.DataFrame:
    rows = []
    for d, members in sorted(r.by_date.items()):
        for t in sorted(members):
            rows.append({"date": pd.Timestamp(d), "ticker": t,
                         "in_index_today": t in r.current})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ coverage
def price_coverage(tickers: set[str]) -> dict:
    """Which of these names does the delisted-retaining archive actually carry?

    Reads the daily panel stock_xsect_lab already built from D:\\ohlcv_1m rather than
    re-reducing 82 GB of minute bars.
    """
    out = {"checked": len(tickers), "in_panel": 0, "missing": [], "panel_source": None}
    import glob

    candidates = [
        r"D:\stock_xsect_data\daily\*.parquet",
        r"D:\stock_xsect_data\universe.parquet",
    ]
    src = None
    for pat in candidates:
        if glob.glob(pat):
            src = pat
            break
    if src is None:
        out["error"] = "no stock_xsect_data daily panel found"
        return out
    out["panel_source"] = src
    try:
        # pyarrow, not polars: company_lab's venv has pyarrow already and reading a
        # single column out of a partitioned dataset is cheap. stock_xsect_lab uses
        # polars in its own venv; no need to duplicate that dependency here.
        import pyarrow.dataset as ds

        files = sorted(glob.glob(src))
        dataset = ds.dataset(files, format="parquet")
        table = dataset.to_table(columns=["ticker"])
        have = set(table.column("ticker").to_pylist())
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"{type(exc).__name__}: {exc}"
        return out
    have = {et.normalize_ticker(str(t)) for t in have}
    present = {t for t in tickers if t in have}
    out["in_panel"] = len(present)
    out["missing"] = sorted(tickers - present)[:60]
    out["n_missing"] = len(tickers - present)
    out["panel_distinct_tickers"] = len(have)
    return out


def removed_names() -> dict[str, str]:
    """{ticker: company name} for every removed constituent, from the changes table."""
    out: dict[str, str] = {}
    if not config.UNIVERSE_CHANGES.exists():
        return out
    ch = pd.read_parquet(config.UNIVERSE_CHANGES)
    if "removed_name" not in ch.columns:
        return out
    for _i, row in ch.iterrows():
        name = str(row.get("removed_name") or "").strip()
        if not name or name.lower() == "nan":
            continue
        for t in _tickers(row.get("removed_ticker")):
            out.setdefault(t, name)
    return out


def cik_coverage(tickers: set[str]) -> dict:
    """How many removed tickers can be resolved to a CIK, and by which route?

    Two routes, tried in order:
      1. company_tickers.json - works only for companies that still file;
      2. the SEC's full registrant list, matched on company NAME - recovers the
         acquired ones, which are precisely the names a survivorship-free study needs.
    """
    from . import cik_lookup

    m = et.load_map()
    by_ticker = {t for t in tickers if t in m}
    out: dict = {
        "checked": len(tickers),
        "resolved_by_ticker_file": len(by_ticker),
    }

    still_missing = sorted(tickers - by_ticker)
    names = removed_names()
    named = {t: names[t] for t in still_missing if t in names}
    out["have_a_company_name"] = len(named)
    out["no_name_available"] = sorted(set(still_missing) - set(named))[:40]

    # validated: a CIK only counts if companyfacts carries a real filing history.
    # Unvalidated matching resolved 115 of 116 and was frequently the wrong legal
    # entity (AETNA HOLDINGS INC, Celgene International Inc), which is worse than a
    # miss because it would silently score the wrong company.
    resolved_by_name = cik_lookup.resolve_many(named, validate=True)
    good = {t: v for t, v in resolved_by_name.items() if v.get("cik")}
    out["resolved_by_name_match"] = len(good)
    out["rejected_wrong_entity_or_no_xbrl"] = {
        t: [c["raw_name"] + " -> " + c["note"][:40]
            for c in (v.get("candidates") or [])[:3]]
        for t, v in list(resolved_by_name.items())[:15] if not v.get("cik")}
    out["total_resolved"] = len(by_ticker) + len(good)
    out["total_unresolved"] = len(tickers) - out["total_resolved"]
    out["resolution_rate"] = out["total_resolved"] / len(tickers) if tickers else None
    how = {}
    for v in resolved_by_name.values():
        how[v["how"]] = how.get(v["how"], 0) + 1
    out["match_methods"] = how
    out["name_match_examples"] = {
        t: {"name": v["name"], "cik": v["cik"], "how": v["how"]}
        for t, v in list(good.items())[:20]}
    out["still_unresolved_examples"] = sorted(
        t for t, v in resolved_by_name.items() if not v.get("cik"))[:40]
    return out


def report(start: str = "2016-01-01") -> dict:
    r = reconstruct(start)
    removed = r.removed_since_start
    rep = {
        "start": start,
        "n_change_events": r.n_changes,
        "unparsed_change_dates": r.unparsed_dates,
        "current_members": len(r.current),
        "distinct_members_ever": len(r.ever),
        "removed_since_start": len(removed),
        "survivorship_hole_pct": (len(removed) / len(r.ever)) if r.ever else None,
        "removed_examples": sorted(removed)[:60],
        "warnings": r.warnings,
    }
    rep["price_coverage_of_removed"] = price_coverage(removed)
    rep["cik_coverage_of_removed"] = cik_coverage(removed)
    by_year = {}
    for d, members in sorted(r.by_date.items()):
        by_year.setdefault(d.year, []).append(len(members))
    rep["members_by_year"] = {y: int(sum(v) / len(v)) for y, v in by_year.items()}
    return rep


def main(argv=None) -> int:
    import argparse
    import json

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", default="2016-01-01")
    ap.add_argument("--write", action="store_true",
                    help="write the reconstructed membership panel to D:")
    args = ap.parse_args(argv)

    rep = report(args.start)
    print(json.dumps({k: v for k, v in rep.items()
                      if k not in ("removed_examples",)}, indent=2, default=str))
    print("\nremoved-since-start examples:")
    print("  " + ", ".join(rep["removed_examples"]))

    if args.write:
        r = reconstruct(args.start)
        df = to_frame(r)
        out = config.UNIVERSE_DIR / "members_pit.parquet"
        df.to_parquet(out, index=False)
        print(f"\nwrote {out}  ({len(df)} rows, {df.ticker.nunique()} distinct tickers)")
    atomic_write_json(config.JOURNAL_DIR / "experiments" / "E04_survivorship_report.json",
                      rep)
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
