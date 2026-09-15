"""Index membership. No S&P 500 constituent list existed on this box.

Source: the Wikipedia S&P 500 page (probed 200). Chosen over the SPY holdings
XLSX because it carries a CIK column - which removes all ticker-mapping
guesswork - and a *changes* table going back to ~1990, the only free path to
point-in-time membership.

Parsed by HEADER SIGNATURE, never by table index: Wikipedia reorders tables.

Every successful fetch appends an immutable, date-stamped snapshot to
universe/members.parquet. That snapshot is the only future defence against
survivorship bias in the deferred forward-return grader, and it cannot be
backfilled - which is why it is written from day one.
"""
from __future__ import annotations

import io
from datetime import date
from pathlib import Path

import pandas as pd

from .. import config
from ..net import (atomic_write_gzip_bytes, http_get, read_gzip_bytes,
                   utc_today)
from .base import Source
from .edgar_tickers import normalize_ticker, pad_cik

MEMBER_HEADERS = ({"Symbol", "Security"}, {"Ticker", "Company"})
CHANGE_HEADER_HINTS = ("Added", "Removed")


class WikiIndexPage(Source):
    """Raw HTML for one index page, cached gzipped on D:."""

    source_id = "wiki_index"

    def __init__(self, tier: str = "sp500") -> None:
        self.tier = tier
        self.url = config.WIKI_TIER_URLS.get(tier, config.WIKI_SP500_URL)

    def _cache_path(self) -> Path:
        return config.UNIVERSE_DIR / f"wikipedia_{self.tier}_{utc_today()}.html.gz"

    def _cache_ttl_hours(self) -> float:
        return config.UNIVERSE_TTL_DAYS * 24.0

    def _load_cache(self):
        return read_gzip_bytes(self._cache_path())

    def _write_cache(self, payload) -> None:
        atomic_write_gzip_bytes(self._cache_path(), payload)

    def _is_cacheable(self, payload) -> bool:
        return isinstance(payload, (bytes, bytearray)) and len(payload) > 10_000

    def _fetch_raw(self) -> bytes:
        # Wikipedia rejects the default urllib UA; SEC_USER_AGENT is a real
        # contactable string so it passes.
        return http_get(self.url)

    def latest_cached(self) -> Path | None:
        """Newest cached snapshot of this tier, whatever its date."""
        hits = sorted(config.UNIVERSE_DIR.glob(f"wikipedia_{self.tier}_*.html.gz"))
        return hits[-1] if hits else None


def _pick_table(tables: list[pd.DataFrame], required: set[str]) -> pd.DataFrame | None:
    for t in tables:
        cols = {str(c).strip() for c in t.columns}
        if required <= cols:
            return t
    return None


def _flatten_columns(t: pd.DataFrame) -> pd.DataFrame:
    if isinstance(t.columns, pd.MultiIndex):
        t = t.copy()
        t.columns = [" ".join(str(x) for x in tup if str(x) != "nan").strip()
                     for tup in t.columns]
    return t


def parse_members(html: bytes) -> pd.DataFrame:
    """-> [ticker, name, cik, gics_sector, gics_sub_industry, date_added]."""
    tables = [_flatten_columns(t) for t in pd.read_html(io.BytesIO(html))]
    tbl = None
    for req in MEMBER_HEADERS:
        tbl = _pick_table(tables, req)
        if tbl is not None:
            break
    if tbl is None:
        raise ValueError("no constituents table matched the expected header signature")

    def col(*names, default=None):
        for n in names:
            for c in tbl.columns:
                if str(c).strip().lower() == n.lower():
                    return tbl[c]
        return default

    sym = col("Symbol", "Ticker")
    if sym is None:
        raise ValueError("constituents table has no Symbol column")
    out = pd.DataFrame({
        "ticker": [normalize_ticker(str(s)) for s in sym],
        "name": col("Security", "Company", default=pd.Series([""] * len(tbl))).astype(str),
    })
    cik = col("CIK")
    out["cik"] = [pad_cik(c) if pd.notna(c) else None for c in cik] if cik is not None \
        else [None] * len(out)
    gs = col("GICS Sector", "GICS  Sector")
    out["gics_sector"] = gs.astype(str) if gs is not None else ""
    gsi = col("GICS Sub-Industry", "GICS  Sub-Industry", "GICS Sub Industry")
    out["gics_sub_industry"] = gsi.astype(str) if gsi is not None else ""
    da = col("Date added", "Date first added")
    out["date_added"] = da.astype(str) if da is not None else ""
    out = out[out["ticker"].str.len().between(1, 8)]
    return out.drop_duplicates(subset=["ticker"]).reset_index(drop=True)


def parse_changes(html: bytes) -> pd.DataFrame:
    """-> [date, added_ticker, removed_ticker]. Empty frame if unparseable."""
    try:
        tables = [_flatten_columns(t) for t in pd.read_html(io.BytesIO(html))]
    except Exception:  # noqa: BLE001
        return pd.DataFrame(columns=["date", "added_ticker", "removed_ticker"])
    for t in tables:
        cols = [str(c) for c in t.columns]
        joined = " ".join(cols)
        if all(h in joined for h in CHANGE_HEADER_HINTS) and "Date" in joined:
            def find(*keys):
                for c in cols:
                    lc = c.lower()
                    if all(k in lc for k in keys):
                        return t[c]
                return None

            def first(*specs):
                # explicit None checks: `a or b` on a pandas Series raises
                for spec in specs:
                    got = find(*spec)
                    if got is not None:
                        return got
                return None

            date_c = find("date")
            add_c = first(("added", "ticker"), ("added", "symbol"))
            rem_c = first(("removed", "ticker"), ("removed", "symbol"))
            # Company NAMES matter as much as tickers: a company removed by
            # acquisition is absent from company_tickers.json, so its CIK can only be
            # recovered by matching the name against the SEC's full registrant list.
            add_n = first(("added", "security"), ("added", "company"))
            rem_n = first(("removed", "security"), ("removed", "company"))
            reason_c = find("reason")
            if date_c is None:
                continue
            n = len(t)
            blank = pd.Series([""] * n)
            return pd.DataFrame({
                "date": date_c.astype(str),
                "added_ticker": (add_c.astype(str) if add_c is not None else blank),
                "removed_ticker": (rem_c.astype(str) if rem_c is not None else blank),
                "added_name": (add_n.astype(str) if add_n is not None else blank),
                "removed_name": (rem_n.astype(str) if rem_n is not None else blank),
                "reason": (reason_c.astype(str) if reason_c is not None else blank),
            })
    return pd.DataFrame(columns=["date", "added_ticker", "removed_ticker"])


def fetch_universe(tier: str = "sp500", *, force: bool = False) -> pd.DataFrame:
    """Members for a tier. Falls back to the newest cached snapshot on failure."""
    if tier == "xsect":
        return _xsect_universe()
    page = WikiIndexPage(tier)
    res = page.fetch(force=force)
    html = res.payload
    if not html:
        cached = page.latest_cached()
        html = read_gzip_bytes(cached) if cached else None
    if not html:
        return _from_members_parquet(tier)
    members = parse_members(html)
    members["tier"] = tier
    _snapshot_members(members, tier)
    changes = parse_changes(html)
    if not changes.empty:
        # keys deliberately exclude the name/reason columns so re-parsing an older
        # cached page cannot duplicate a row that gained a name column later
        _write_parquet(config.UNIVERSE_CHANGES, changes.assign(tier=tier),
                       keys=["tier", "date", "added_ticker", "removed_ticker"])
    return members


#: Hand-curated cross-listed / foreign-filer members, with their classification.
XSECT_MEMBERS_FILE = config.BASE_DIR / "data" / "xsect_members.json"


def _xsect_curated() -> pd.DataFrame:
    """The named foreign-filer list, read in preference to the liquidity screen.

    `config.XSECT_UNIVERSE` is a 44-million-row daily bar file carrying no CIK, no
    sector and no sub-industry. A company loaded from it arrives with an empty
    `sub_industry`, and CLAUDE.md already records what that costs: it is the only thing
    separating a mortgage REIT from an equity REIT, and an empty one changes which
    sub-tests a company is even asked. A curated list keeps the classification attached.
    """
    import json

    if not XSECT_MEMBERS_FILE.exists():
        return pd.DataFrame()
    try:
        members = (json.loads(XSECT_MEMBERS_FILE.read_text(encoding="utf-8"))
                   or {}).get("members") or []
    except (json.JSONDecodeError, ValueError):
        return pd.DataFrame()
    if not members:
        return pd.DataFrame()
    out = pd.DataFrame([{
        "ticker": normalize_ticker(str(m.get("ticker", ""))),
        "name": str(m.get("name") or ""),
        "cik": str(m.get("cik") or "") or None,
        "gics_sector": str(m.get("gics_sector") or ""),
        "gics_sub_industry": str(m.get("gics_sub_industry") or ""),
        "date_added": "",
    } for m in members if m.get("ticker")])
    out["tier"] = "xsect"
    return out.drop_duplicates(subset=["ticker"]).reset_index(drop=True)


def _xsect_universe() -> pd.DataFrame:
    """The ~1,960-name liquidity-screened universe from stock_xsect_lab (down-cap tier).

    The curated foreign-filer list wins when it exists, because it carries the
    classification the screen does not.
    """
    curated = _xsect_curated()
    if not curated.empty:
        return curated
    p = config.XSECT_UNIVERSE
    if not p.exists():
        return pd.DataFrame(columns=["ticker", "name", "cik", "gics_sector",
                                     "gics_sub_industry", "date_added", "tier"])
    df = pd.read_parquet(p)
    tcol = "ticker" if "ticker" in df.columns else df.columns[0]
    if "session" in df.columns:
        df = df[df["session"] == df["session"].max()]
    if "eligible" in df.columns:
        df = df[df["eligible"].astype(bool)]
    out = pd.DataFrame({"ticker": [normalize_ticker(str(t)) for t in df[tcol]]})
    for c, v in (("name", ""), ("cik", None), ("gics_sector", ""),
                 ("gics_sub_industry", ""), ("date_added", "")):
        out[c] = v
    out["tier"] = "xsect"
    return out.drop_duplicates(subset=["ticker"]).reset_index(drop=True)


def _snapshot_members(members: pd.DataFrame, tier: str) -> None:
    """Append an immutable point-in-time membership snapshot. Cannot be backfilled."""
    snap = members[["ticker", "cik", "gics_sector"]].copy()
    snap["as_of"] = utc_today()
    snap["tier"] = tier
    snap["in_index"] = True
    _write_parquet(config.UNIVERSE_MEMBERS, snap, keys=["as_of", "tier", "ticker"])


def _write_parquet(path: Path, new: pd.DataFrame, keys: list[str]) -> None:
    """Read-merge-dedupe-write. Never raises: a snapshot failure must not kill a crawl."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            try:
                old = pd.read_parquet(path)
                new = pd.concat([old, new], ignore_index=True)
            except Exception:  # noqa: BLE001 - corrupt parquet: start fresh
                pass
        have = [k for k in keys if k in new.columns]
        if have:
            new = new.drop_duplicates(subset=have, keep="last")
        tmp = path.with_suffix(".parquet.tmp")
        new.to_parquet(tmp, index=False)
        tmp.replace(path)
    except Exception:  # noqa: BLE001
        pass


def _from_members_parquet(tier: str) -> pd.DataFrame:
    """Last-resort: rebuild the member list from the newest stored snapshot."""
    p = config.UNIVERSE_MEMBERS
    if not p.exists():
        return pd.DataFrame(columns=["ticker", "name", "cik", "gics_sector",
                                     "gics_sub_industry", "date_added", "tier"])
    try:
        df = pd.read_parquet(p)
    except Exception:  # noqa: BLE001
        return pd.DataFrame(columns=["ticker", "name", "cik", "gics_sector",
                                     "gics_sub_industry", "date_added", "tier"])
    df = df[df.get("tier", tier) == tier]
    if df.empty:
        return df
    df = df[df["as_of"] == df["as_of"].max()]
    out = df[["ticker", "cik", "gics_sector"]].copy()
    out["name"] = ""
    out["gics_sub_industry"] = ""
    out["date_added"] = ""
    out["tier"] = tier
    return out.reset_index(drop=True)


def active_universe(tier: str = "sp500", as_of: str | None = None) -> pd.DataFrame:
    """Membership for a date from the stored snapshots (no network)."""
    p = config.UNIVERSE_MEMBERS
    if not p.exists():
        return pd.DataFrame(columns=["ticker", "cik", "gics_sector", "as_of", "tier"])
    df = pd.read_parquet(p)
    df = df[df["tier"] == tier]
    if df.empty:
        return df
    cutoff = as_of or df["as_of"].max()
    df = df[df["as_of"] <= cutoff]
    if df.empty:
        return df
    return df[df["as_of"] == df["as_of"].max()].reset_index(drop=True)


def cross_check(members: pd.DataFrame, cik_map: dict) -> dict:
    """Log-worthy sanity counts. A non-zero missing_cik means a normalization bug."""
    tickers = set(members["ticker"])
    missing = sorted(t for t in tickers if t not in cik_map)
    by_cik: dict[str, list[str]] = {}
    for _, r in members.iterrows():
        if r.get("cik"):
            by_cik.setdefault(str(r["cik"]), []).append(r["ticker"])
    dual = {k: v for k, v in by_cik.items() if len(v) > 1}
    return {
        "members": len(tickers),
        "missing_from_sec_map": missing,
        "n_missing_from_sec_map": len(missing),
        "dual_class_ciks": dual,
        "as_of": utc_today(),
        "checked_on": date.today().isoformat(),
    }
