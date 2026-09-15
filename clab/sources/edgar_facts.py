"""EDGAR XBRL companyfacts - the authoritative financial statement feed.

Verified live: CIK0000320193 (AAPL) -> 200, 3.79 MB, 0.61s, 503 distinct
us-gaap tags. ~2 GB raw for 500 names, so this lives on D: gzipped (~400 MB).

Cache immutability rule: a companyfacts blob is keyed by the newest accession
number it contains. An accession number never changes, so a blob whose latest
accn is unchanged is valid forever. We cannot cheaply ask "what is the latest
accn" without downloading, so the practical rule is a 24 h TTL plus an accn
comparison recorded in the crawl manifest - which is what makes the
earnings-triggered re-run (runner/earnings_watch.py) able to skip no-ops.
"""
from __future__ import annotations

from pathlib import Path

from .. import config
from ..net import (SEC_LIMITER, atomic_write_gzip_json, http_get_json,
                   read_gzip_json)
from .base import Source


class EdgarFacts(Source):
    source_id = "edgar_facts"

    def __init__(self, cik: str) -> None:
        self.cik = str(cik).zfill(10)

    def _cache_path(self) -> Path:
        return config.EDGAR_FACTS_DIR / f"CIK{self.cik}.json.gz"

    def _cache_ttl_hours(self) -> float:
        return float(config.FACTS_TTL_HOURS)

    def _load_cache(self):
        return read_gzip_json(self._cache_path())

    def _write_cache(self, payload) -> None:
        atomic_write_gzip_json(self._cache_path(), payload)

    def _is_cacheable(self, payload) -> bool:
        return isinstance(payload, dict) and bool(payload.get("facts"))

    def _data_through(self, payload) -> str | None:
        return latest_period_end(payload)

    def _fetch_raw(self) -> dict:
        url = config.EDGAR_FACTS_URL.format(cik=self.cik)
        return http_get_json(url, limiter=SEC_LIMITER)


class EdgarSubmissions(Source):
    """Filing history + SIC code. SIC is the authoritative sector key.

    yfinance info["sector"] is not used: it is a scraped field that changes
    shape without notice, and the sector profile (which decides whether gross
    margin is even meaningful) is too load-bearing to hang off it.
    """

    source_id = "edgar_submissions"

    def __init__(self, cik: str) -> None:
        self.cik = str(cik).zfill(10)

    def _cache_path(self) -> Path:
        return config.EDGAR_SUBMISSIONS_DIR / f"CIK{self.cik}.json.gz"

    def _cache_ttl_hours(self) -> float:
        return float(config.FACTS_TTL_HOURS)

    def _load_cache(self):
        return read_gzip_json(self._cache_path())

    def _write_cache(self, payload) -> None:
        atomic_write_gzip_json(self._cache_path(), payload)

    def _is_cacheable(self, payload) -> bool:
        return isinstance(payload, dict) and "cik" in payload

    def _fetch_raw(self) -> dict:
        url = config.EDGAR_SUBMISSIONS_URL.format(cik=self.cik)
        return http_get_json(url, limiter=SEC_LIMITER)


# ------------------------------------------------------------------ helpers
def iter_facts(payload: dict, taxonomy: str = "us-gaap"):
    """Yield (tag, unit, rows) for one taxonomy."""
    facts = (payload or {}).get("facts", {}).get(taxonomy, {})
    for tag, body in facts.items():
        for unit, rows in (body.get("units") or {}).items():
            yield tag, unit, rows


def tag_rows(payload: dict, tag: str, *, taxonomy: str = "us-gaap",
             unit: str | None = None) -> list[dict]:
    """Raw fact rows for one tag. Picks the largest unit bucket when unit is None.

    Row shape (confirmed): {start, end, val, accn, fy, fp, form, filed, frame?}.
    Up to 4 rows can share one (start, end) - restatements. Deduping is
    fundamentals/normalize.py's job, not this one's.
    """
    body = (payload or {}).get("facts", {}).get(taxonomy, {}).get(tag)
    if not body:
        return []
    units = body.get("units") or {}
    if unit is not None:
        return list(units.get(unit) or [])
    if not units:
        return []
    best = max(units.items(), key=lambda kv: len(kv[1] or []))
    return list(best[1] or [])


def tag_unit(payload: dict, tag: str, taxonomy: str = "us-gaap") -> str | None:
    body = (payload or {}).get("facts", {}).get(taxonomy, {}).get(tag)
    if not body:
        return None
    units = body.get("units") or {}
    if not units:
        return None
    return max(units.items(), key=lambda kv: len(kv[1] or []))[0]


def latest_accn(payload: dict) -> str | None:
    """Newest accession number anywhere in the blob - the cache identity key."""
    best_filed = ""
    best_accn = None
    for _tag, _unit, rows in iter_facts(payload):
        for r in rows:
            f = r.get("filed") or ""
            if f > best_filed:
                best_filed, best_accn = f, r.get("accn")
    return best_accn


def latest_period_end(payload: dict) -> str | None:
    """Newest reported period end - `data_through` for the fundamentals side."""
    best = ""
    for _tag, _unit, rows in iter_facts(payload):
        for r in rows:
            e = r.get("end") or ""
            if e > best:
                best = e
    return best or None


def count_quarter_rows(payload: dict, tag_candidates=("Revenues",
                                                      "RevenueFromContractWithCustomerExcludingAssessedTax")) -> int:
    """Rough history depth: how many revenue fact rows exist at all."""
    return max((len(tag_rows(payload, t)) for t in tag_candidates), default=0)


def filer_cik_from_accn(payload: dict) -> str | None:
    """The CIK that actually filed the newest fact, taken from the accession prefix.

    Reorganizations create a new registrant CIK with almost no history while the
    real series stays under the predecessor. Measured: company_tickers.json maps
    XOM to CIK 0002115436, whose companyfacts holds 4 revenue rows, while the
    accession numbers on those rows begin 0000034088 - the historical Exxon
    filer. The accession prefix is therefore a free, reliable pointer to the
    entity that owns the history.
    """
    accn = latest_accn(payload)
    if not accn or "-" not in accn:
        return None
    head = accn.split("-", 1)[0]
    if not head.isdigit():
        return None
    return head.zfill(10)


def resolve_facts(cik: str, *, force: bool = False, min_rows: int = 12):
    """Fetch companyfacts, following a reorganization to the predecessor CIK.

    Returns (FetchResult, cik_used, note). Never raises.
    """
    res = EdgarFacts(cik).fetch(force=force)
    payload = res.payload if isinstance(res.payload, dict) else {}
    if count_quarter_rows(payload) >= min_rows:
        return res, str(cik).zfill(10), None
    alt = filer_cik_from_accn(payload)
    if not alt or alt == str(cik).zfill(10):
        return res, str(cik).zfill(10), None
    alt_res = EdgarFacts(alt).fetch(force=force)
    alt_payload = alt_res.payload if isinstance(alt_res.payload, dict) else {}
    if count_quarter_rows(alt_payload) > count_quarter_rows(payload):
        note = (f"followed reorganization: CIK {str(cik).zfill(10)} had "
                f"{count_quarter_rows(payload)} revenue rows, predecessor {alt} has "
                f"{count_quarter_rows(alt_payload)}")
        return alt_res, alt, note
    return res, str(cik).zfill(10), None


def sic_from_submissions(payload: dict) -> tuple[str | None, str | None]:
    if not isinstance(payload, dict):
        return None, None
    sic = payload.get("sic")
    return (str(sic) if sic else None), payload.get("sicDescription")


def entity_name(payload: dict) -> str | None:
    if isinstance(payload, dict):
        return payload.get("entityName") or payload.get("name")
    return None


def recent_filings(payload: dict, forms=("10-K", "10-Q")) -> list[dict]:
    """Filing rows from the submissions feed, newest first."""
    recent = ((payload or {}).get("filings") or {}).get("recent") or {}
    cols = ("form", "accessionNumber", "filingDate", "reportDate",
            "primaryDocument", "primaryDocDescription")
    if not all(c in recent for c in ("form", "accessionNumber", "filingDate")):
        return []
    n = len(recent["form"])
    out = []
    for i in range(n):
        if recent["form"][i] not in forms:
            continue
        out.append({c: (recent.get(c) or [None] * n)[i] for c in cols})
    return out
