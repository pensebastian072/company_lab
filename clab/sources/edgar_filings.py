"""10-K / 10-Q document text from EDGAR, sliced into the sections worth reading.

One extra fetch per company per year, and the document is immutable once filed, so
it is cached gzipped on D: forever.

Item 1 (Business), Item 1A (Risk Factors) and Item 7 (MD&A) are the three sections
that actually answer the framework's qualitative questions: what the company does,
what could go wrong, and what management says about the trend. Everything else in a
10-K is boilerplate or the financial statements we already have in XBRL form.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

from .. import config
from ..net import SEC_LIMITER, atomic_write_gzip_bytes, http_get, read_gzip_bytes
from .edgar_facts import EdgarSubmissions, recent_filings

ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accn}/{doc}"

# Item headings vary wildly in punctuation and case across filers, so match loosely
# and take the LAST occurrence of each heading before the next one - the table of
# contents mentions every heading first, and the real section follows it.
_ITEM_PATTERNS = {
    "business": r"item\s*1\s*[\.\:\-\s]*business",
    "risk_factors": r"item\s*1a\s*[\.\:\-\s]*risk\s*factors",
    "mdna": (r"item\s*7\s*[\.\:\-\s]*management['’]?s?\s*discussion"),
    "_end_business": r"item\s*1a\s*[\.\:\-\s]*risk\s*factors",
    "_end_risk": r"item\s*(1b|2)\s*[\.\:\-\s]*",
    "_end_mdna": r"item\s*7a\s*[\.\:\-\s]*quantitative",
}


def strip_html(raw: bytes) -> str:
    """HTML -> readable text. Deliberately crude; we only need prose for retrieval."""
    try:
        text = raw.decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        text = str(raw)
    text = re.sub(r"(?is)<(script|style|head)[^>]*>.*?</\1>", " ", text)
    text = re.sub(r"(?is)<br\s*/?>|</p>|</div>|</tr>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()


def latest_annual(cik: str) -> dict | None:
    """The newest 10-K row from the submissions feed, or a 10-Q as a fallback."""
    subs = EdgarSubmissions(cik).fetch()
    payload = subs.payload if isinstance(subs.payload, dict) else {}
    for forms in (("10-K",), ("10-K", "10-K/A"), ("10-Q",)):
        rows = recent_filings(payload, forms=forms)
        if rows:
            return rows[0]
    return None


def _cache_path(cik: str, accn: str) -> Path:
    return config.EDGAR_FILINGS_DIR / str(cik).zfill(10) / f"{accn}.txt.gz"


def proxy_filings(cik: str, limit: int = 12) -> list[dict]:
    """DEF 14A rows from the submissions feed, newest first.

    E22 measured MG's stability at 0.29 and the cause was the document: `founder_led`,
    `tenure` and `ownership` are stated in the proxy, not the 10-K, and were scored for
    5-7% of companies because the model was reading a filing that does not contain them.
    """
    subs = EdgarSubmissions(cik).fetch()
    payload = subs.payload if isinstance(subs.payload, dict) else {}
    # DEF 14A only. DEFA14A is "additional proxy soliciting material" - a voting-results
    # letter or a supplemental slide deck, typically 3-8 KB - and it is what the feed
    # returns FIRST because it is filed later. Measured 2026-08-22: AAPL's newest DEFA14A
    # is 3,866 characters and contains none of "beneficial ownership", "has served" or
    # "founder"; the real proxy is the DEF 14A behind it.
    rows = recent_filings(payload, forms=("DEF 14A",))
    return rows[:limit]


def proxy_text(cik: str, *, as_of: str | None = None,
               force: bool = False) -> tuple[str, dict]:
    """(text, meta) for the proxy current at `as_of`, or the newest one.

    Shares `filing_text`'s cache, rate limiter and HTML stripping - a proxy is just
    another EDGAR document, and giving it its own fetch path would mean two things to
    keep correct instead of one.
    """
    rows = proxy_filings(cik)
    if as_of:
        rows = [r for r in rows if str(r.get("filingDate") or "") <= as_of]
    if not rows:
        return "", {"cik": str(cik).zfill(10),
                    "error": f"no DEF 14A{' on or before ' + as_of if as_of else ''}"}
    return filing_text(cik, row=rows[0], force=force)


def annual_filings(cik: str, limit: int = 12) -> list[dict]:
    """Every 10-K row on the submissions feed, newest first.

    E22 needs the filing that was CURRENT at a past date, not today's. The feed carries a
    decade of them (11 for AAPL back to 2015), so a point-in-time evidence pack is
    reconstructible rather than something only forward snapshots can produce.
    """
    subs = EdgarSubmissions(cik).fetch()
    payload = subs.payload if isinstance(subs.payload, dict) else {}
    rows = recent_filings(payload, forms=("10-K", "10-K/A"))
    return rows[:limit]


def filing_text(cik: str, *, force: bool = False, row: dict | None = None,
                as_of: str | None = None) -> tuple[str, dict]:
    """(text, meta). Returns ("", meta) rather than raising when unavailable.

    `row` scores a specific filing; `as_of` picks the newest 10-K filed on or before that
    date - the one an analyst could actually have read then. Neither is used by the daily
    crawl, which always wants the latest.
    """
    meta: dict = {"cik": str(cik).zfill(10)}
    if row is None and as_of:
        candidates = [r for r in annual_filings(cik)
                      if str(r.get("filingDate") or "") <= as_of]
        row = candidates[0] if candidates else None
        if row is None:
            meta["error"] = f"no 10-K filed on or before {as_of}"
            return "", meta
    if row is None:
        row = latest_annual(cik)
    if not row:
        meta["error"] = "no 10-K or 10-Q in the submissions feed"
        return "", meta
    accn_raw = str(row.get("accessionNumber") or "")
    doc = str(row.get("primaryDocument") or "")
    meta.update({"accn": accn_raw, "form": row.get("form"),
                 "filed": row.get("filingDate"), "report_date": row.get("reportDate"),
                 "primary_document": doc})
    if not accn_raw or not doc:
        meta["error"] = "filing row has no accession number or primary document"
        return "", meta

    path = _cache_path(cik, accn_raw)
    if path.exists() and not force:
        cached = read_gzip_bytes(path)
        if cached:
            meta["from_cache"] = True
            return cached.decode("utf-8", errors="replace"), meta

    url = ARCHIVE_URL.format(cik=str(int(cik)), accn=accn_raw.replace("-", ""), doc=doc)
    meta["url"] = url
    try:
        raw = http_get(url, limiter=SEC_LIMITER, timeout=90)
    except Exception as exc:  # noqa: BLE001 - a missing filing is not a crawl failure
        meta["error"] = f"{type(exc).__name__}: {exc}"
        return "", meta
    text = strip_html(raw)
    if len(text) < 2000:
        meta["error"] = f"document too short after stripping ({len(text)} chars)"
        return "", meta
    try:
        atomic_write_gzip_bytes(path, text.encode("utf-8"))
    except Exception:  # noqa: BLE001
        pass
    meta["chars"] = len(text)
    meta["from_cache"] = False
    return text, meta


def _last_match_before(text: str, pattern: str, limit: int | None = None) -> int | None:
    """Last occurrence of a heading, which skips the table-of-contents mention."""
    body = text if limit is None else text[:limit]
    hits = list(re.finditer(pattern, body, re.I))
    return hits[-1].start() if hits else None


def slice_sections(text: str) -> dict[str, str]:
    """Extract Item 1, Item 1A and Item 7. Missing sections are simply absent."""
    if not text:
        return {}
    out: dict[str, str] = {}

    def grab(start_pat: str, end_pat: str, key: str) -> None:
        starts = list(re.finditer(start_pat, text, re.I))
        if not starts:
            return
        # prefer the last heading occurrence that still leaves a plausible body
        for m in reversed(starts):
            s = m.start()
            ends = [e.start() for e in re.finditer(end_pat, text[s + 200:], re.I)]
            e = (s + 200 + ends[0]) if ends else min(s + 120_000, len(text))
            if e - s > 1500:
                out[key] = text[s:e].strip()
                return

    grab(_ITEM_PATTERNS["business"], _ITEM_PATTERNS["_end_business"], "business")
    grab(_ITEM_PATTERNS["risk_factors"], _ITEM_PATTERNS["_end_risk"], "risk_factors")
    grab(_ITEM_PATTERNS["mdna"], _ITEM_PATTERNS["_end_mdna"], "mdna")
    return out


def chunk_text(text: str, size: int = 1600, overlap: int = 160) -> list[str]:
    """Paragraph-aware chunking (same shape as research_rag/rag/ingest.py)."""
    if not text:
        return []
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buf = ""
    for p in paras:
        if len(buf) + len(p) + 2 <= size:
            buf = (buf + "\n\n" + p) if buf else p
            continue
        if buf:
            chunks.append(buf)
            tail = buf[-overlap:] if overlap else ""
            buf = (tail + "\n\n" + p) if tail else p
        else:
            for i in range(0, len(p), size):
                chunks.append(p[i:i + size])
            buf = ""
    if buf:
        chunks.append(buf)
    return [c for c in chunks if len(c) > 120]
