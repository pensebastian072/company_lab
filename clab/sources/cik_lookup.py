"""Resolve a company NAME to a CIK, including registrants that no longer exist.

`company_tickers.json` lists current registrants only, so it resolves 97 of the 213
companies removed from the S&P 500 since 2016 and misses the 116 that were acquired -
Aetna, Allergan, Alexion, Activision Blizzard, Celgene, Cerner and the rest. Those are
exactly the names a survivorship-free study needs, and their filings are still on EDGAR
under the old CIK.

`https://www.sec.gov/Archives/edgar/cik-lookup-data.txt` is the way in: ~40 MB,
1.05M lines of `COMPANY NAME:CIK:`, and it includes inactive registrants. Cached on D:
because it is large and changes slowly.

Matching is by normalized name with a tiered fallback, and every match records HOW it
was made so a wrong one can be found later rather than silently trusted.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .. import config
from ..net import (atomic_write_gzip_bytes, http_get, is_fresh, read_gzip_bytes,
                   trust_windows_certs)

LOOKUP_URL = "https://www.sec.gov/Archives/edgar/cik-lookup-data.txt"
CACHE = config.EDGAR_DIR / "cik_lookup_data.txt.gz"
CACHE_TTL_HOURS = 24 * 30

#: Suffixes and corporate furniture that differ between Wikipedia and EDGAR for the
#: same company. Stripped from both sides before comparison.
_SUFFIXES = (
    "incorporated", "inc", "corporation", "corp", "company", "co", "limited", "ltd",
    "plc", "lp", "llc", "holdings", "holding", "group", "the", "sa", "nv", "ag",
    "class a", "class b", "class c", "cl a", "cl b", "trust", "reit", "worldwide",
    "international", "industries", "enterprises", "technologies", "systems",
    "communications", "partners", "companies", "brands", "financial", "energy",
    "pharmaceuticals", "pharma",
)


def normalize_name(name: str) -> str:
    """Lowercase, drop punctuation, drop corporate suffixes, collapse whitespace."""
    if not name:
        return ""
    s = str(name).lower()
    s = re.sub(r"\[.*?\]", " ", s)
    s = re.sub(r"\(.*?\)", " ", s)
    s = s.replace("&amp;", "&").replace("&", " and ")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    changed = True
    while changed:
        changed = False
        for suf in _SUFFIXES:
            if s.endswith(" " + suf):
                s = s[: -(len(suf) + 1)].strip()
                changed = True
            elif s == suf:
                return ""
    if s.startswith("the "):
        s = s[4:]
    return re.sub(r"\s+", " ", s).strip()


@dataclass
class LookupTable:
    exact: dict[str, list[tuple[str, str]]]    # normalized name -> [(cik, raw name)]
    prefix: dict[str, list[tuple[str, str]]]   # leading words -> [(cik, raw name)]
    n_lines: int = 0

    def candidates(self, name: str) -> list[tuple[str, str, str]]:
        """All plausible (cik, raw_name, how) for a company name, best guess first.

        Returning a LIST rather than one answer is the whole point. EDGAR contains
        many entities per corporate family and the shortest normalized name is often a
        subsidiary: 'Aetna' matched AETNA HOLDINGS INC and 'Celgene' matched Celgene
        International Inc, both of which 404 on companyfacts because neither filed the
        10-Ks. The caller validates each candidate against real filings.
        """
        n = normalize_name(name)
        if not n:
            return []
        seen: set[str] = set()
        out: list[tuple[str, str, str]] = []

        def add(items, how):
            for cik, raw in items:
                if cik not in seen:
                    seen.add(cik)
                    out.append((cik, raw, how))

        add(self.exact.get(n, []), "exact")
        words = n.split()
        for k in (3, 2, 1):
            if len(words) >= k:
                key = " ".join(words[:k])
                add(self.exact.get(key, []), f"prefix_{k}w")
                add(self.prefix.get(key, []), f"prefix_index_{k}w")
        # widen: anything whose normalized name starts with the target
        starts = [(cik, raw) for k, items in self.exact.items() if k.startswith(n)
                  for cik, raw in items]
        starts.sort(key=lambda cr: len(cr[1]))
        add(starts[:12], "startswith")
        return out

    def resolve(self, name: str) -> tuple[str | None, str]:
        """First candidate, unvalidated. Kept for the coverage report only."""
        c = self.candidates(name)
        return (c[0][0], c[0][2]) if c else (None, "no_match")


_TABLE: LookupTable | None = None


def load(*, force: bool = False) -> LookupTable:
    """Fetch (or reuse) the SEC lookup and index it. ~40 MB, cached a month."""
    global _TABLE
    if _TABLE is not None and not force:
        return _TABLE
    trust_windows_certs()
    raw: bytes | None = None
    if CACHE.exists() and not force and is_fresh(CACHE, CACHE_TTL_HOURS):
        raw = read_gzip_bytes(CACHE)
    if raw is None:
        raw = http_get(LOOKUP_URL, timeout=300)
        try:
            atomic_write_gzip_bytes(CACHE, raw)
        except Exception:  # noqa: BLE001 - a cache failure must not fail the lookup
            pass

    exact: dict[str, list[tuple[str, str]]] = {}
    prefix: dict[str, list[tuple[str, str]]] = {}
    n = 0
    MAX_PER_KEY = 12          # bound the fan-out for very common stems
    for line in raw.decode("latin-1").splitlines():
        n += 1
        # format: COMPANY NAME:0000000000:
        parts = line.rstrip(":").rsplit(":", 1)
        if len(parts) != 2:
            continue
        name, cik = parts[0], parts[1].strip()
        if not cik.isdigit():
            continue
        key = normalize_name(name)
        if not key:
            continue
        cik10 = cik.zfill(10)
        bucket = exact.setdefault(key, [])
        if len(bucket) < MAX_PER_KEY:
            bucket.append((cik10, name))
        words = key.split()
        for k in (2, 1):
            if len(words) >= k:
                pk = " ".join(words[:k])
                pb = prefix.setdefault(pk, [])
                if len(pb) < MAX_PER_KEY:
                    pb.append((cik10, name))
    # shortest raw name first within each bucket: the operating company usually has a
    # shorter name than its financing subsidiaries
    for d in (exact, prefix):
        for bucket in d.values():
            bucket.sort(key=lambda cr: len(cr[1]))
    _TABLE = LookupTable(exact=exact, prefix=prefix, n_lines=n)
    return _TABLE


#: A CIK only counts as resolved if companyfacts carries a real filing history. Below
#: this many us-gaap tags it is a shell, a financing subsidiary or a trust - the exact
#: thing name matching mistakes for the operating company.
MIN_TAGS = 40


def _facts_quality(cik: str) -> tuple[bool, int, str]:
    """(usable, n_us_gaap_tags, note). Uses the cached companyfacts fetcher."""
    from .edgar_facts import EdgarFacts

    res = EdgarFacts(cik).fetch()
    payload = res.payload if isinstance(res.payload, dict) else None
    if not payload or not payload.get("facts"):
        return False, 0, res.error or "no companyfacts"
    tags = payload.get("facts", {}).get("us-gaap", {})
    n = len(tags)
    return (n >= MIN_TAGS), n, ("ok" if n >= MIN_TAGS else f"only {n} us-gaap tags")


def resolve_validated(name: str, *, max_candidates: int = 6) -> dict:
    """Best CIK for a company name, VALIDATED against real filings.

    Walks candidates in best-guess order and returns the first whose companyfacts
    looks like an operating company. Without this step 'Aetna' resolves to AETNA
    HOLDINGS INC and 'Celgene' to Celgene International Inc - both 404, both silently
    wrong, and scoring the wrong entity is worse than scoring nothing.
    """
    try:
        table = load()
    except Exception as exc:  # noqa: BLE001
        return {"cik": None, "how": f"lookup_unavailable: {exc}", "name": name,
                "tried": 0}
    cands = table.candidates(name)[:max_candidates]
    tried = []
    for cik, raw, how in cands:
        usable, ntags, note = _facts_quality(cik)
        tried.append({"cik": cik, "raw_name": raw, "how": how, "tags": ntags,
                      "note": note})
        if usable:
            return {"cik": cik, "how": how, "name": name, "edgar_name": raw,
                    "tags": ntags, "tried": len(tried), "candidates": tried}
    return {"cik": None, "how": "no_candidate_with_filings", "name": name,
            "tried": len(tried), "candidates": tried}


def resolve_many(names: dict[str, str], *, validate: bool = True) -> dict[str, dict]:
    """{ticker: company_name} -> {ticker: {cik, how, name, ...}}. Never raises.

    validate=True costs one cached EDGAR fetch per candidate and is the default,
    because an unvalidated match is frequently the wrong legal entity.
    """
    try:
        table = load()
    except Exception as exc:  # noqa: BLE001
        return {t: {"cik": None, "how": f"lookup_unavailable: {exc}", "name": n}
                for t, n in names.items()}
    out = {}
    for ticker, name in names.items():
        if validate:
            out[ticker] = resolve_validated(name)
        else:
            cik, how = table.resolve(name)
            out[ticker] = {"cik": cik, "how": how, "name": name}
    return out
