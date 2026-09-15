"""SEC Form 3/4/5 insider transactions, from the DERA quarterly bulk datasets.

Why this exists: the LSE vault advertised 11.3M insider rows spanning 2003-2026 and
actually serves five months, six months stale, with the same filing re-ingested up to 320
times (see `journal/experiments/E06_insider_signal_STATUS.md`). Form 4 is a public filing,
so the honest source is the SEC itself.

Why the BULK datasets rather than per-filing XML: filtering EDGAR's full index to this
repo's ~675 symbols still leaves roughly 340,000 individual Form 4 documents, which at the
SEC's rate limit is about 16 hours. The DERA quarterly ZIPs are ~14 MB each and one file
covers every filer for a quarter - about 41 files for 2016-2026. That is the difference
between a job that runs and a job that does not.

    https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets/

Each ZIP holds tab-separated tables sharing ACCESSION_NUMBER:

    SUBMISSION.tsv      one row per filing: FILING_DATE, ISSUERCIK, ISSUERTRADINGSYMBOL
    REPORTINGOWNER.tsv  who filed: RPTOWNERCIK, RPTOWNER_RELATIONSHIP, RPTOWNER_TITLE
    NONDERIV_TRANS.tsv  the trades: TRANS_DATE, TRANS_CODE, TRANS_SHARES, price, holdings

What this gives that the vendor feed could not:

  * **FILING_DATE**, which is the only defensible signal date. A Form 4 is filed up to two
    business days after the trade and the gap can run to months; acting on TRANS_DATE uses
    information nobody had.
  * **TRANS_CODE**, so open-market purchases (P) are separable from option exercises (M),
    tax withholding (F), awards (A) and gifts (G). Counting mechanical transactions as
    conviction would be nonsense.
  * **No congressional rows at all** - this is Form 4 only, so one of E06's three data
    disciplines is satisfied by construction.
  * **SHRS_OWND_FOLWNG_TRANS**, which measures the ownership level the Management
    component currently has the LLM guess at.

Cached under DATA_ROOT/edgar_form4/. Quarterly files for a closed quarter never change, so
a re-run is free.
"""
from __future__ import annotations

import csv
import io
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from .. import config
from ..net import RateLimiter, trust_windows_certs

BASE = ("https://www.sec.gov/files/structureddata/data/"
        "insider-transactions-data-sets")
CACHE_DIR = config.DATA_ROOT / "edgar_form4"
FIRST_YEAR = 2016

#: Form 4 transaction codes. Only P and S are open-market decisions; the rest are
#: mechanical or non-economic and must never be counted as conviction.
DISCRETIONARY_CODES = ("P", "S")
CODE_MEANING = {
    "P": "open-market purchase", "S": "open-market sale",
    "A": "grant/award", "M": "option exercise", "F": "tax withholding",
    "G": "gift", "D": "return to issuer", "C": "conversion", "X": "option expiration",
    "J": "other", "I": "discretionary transaction",
}
#: RPTOWNER_RELATIONSHIP is a free-ish text field; these substrings mark the people whose
#: trades the literature finds informative.
OFFICER_HINTS = ("officer", "director")
CEO_CFO_HINTS = ("chief executive", "chief financial", "ceo", "cfo", "president")

_rate = RateLimiter(6.0)


class Form4Unavailable(RuntimeError):
    pass


@dataclass
class Quarter:
    year: int
    q: int

    @property
    def name(self) -> str:
        return f"{self.year}q{self.q}"

    @property
    def url(self) -> str:
        return f"{BASE}/{self.name}_form345.zip"

    @property
    def path(self) -> Path:
        return CACHE_DIR / f"{self.name}_form345.zip"

    @property
    def is_closed(self) -> bool:
        """A closed quarter's file never changes, so its cache is permanent."""
        today = date.today()
        end_year, end_month = self.year, self.q * 3
        return (end_year, end_month) < (today.year, today.month)


def quarters(start_year: int = FIRST_YEAR, end: date | None = None) -> list[Quarter]:
    end = end or date.today()
    out = []
    for y in range(start_year, end.year + 1):
        for q in (1, 2, 3, 4):
            if (y, q * 3 - 2) > (end.year, end.month):
                break
            out.append(Quarter(y, q))
    return out


def fetch_quarter(qtr: Quarter, *, force: bool = False) -> Path | None:
    """Download one quarterly ZIP to the cache. Returns None when unavailable.

    Never raises: a quarter the SEC has not published yet is a normal condition, not an
    error, and must not kill a ten-year crawl.
    """
    import urllib.error
    import urllib.request

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if qtr.path.exists() and not force and qtr.path.stat().st_size > 0:
        return qtr.path

    trust_windows_certs()
    _rate.wait()
    req = urllib.request.Request(qtr.url,
                                 headers={"User-Agent": config.SEC_USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=config.HTTP_TIMEOUT * 6) as fh:
            body = fh.read()
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return None
    if not body or len(body) < 1000:
        return None
    tmp = qtr.path.with_suffix(".zip.tmp")
    tmp.write_bytes(body)
    tmp.replace(qtr.path)
    return qtr.path


def _parse_date(s: str) -> str | None:
    """'31-JAN-2024' -> '2024-01-31'. The datasets use this format everywhere."""
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%d-%b-%Y", "%Y-%m-%d", "%d-%B-%Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _read_tsv(z: zipfile.ZipFile, name: str) -> list[dict]:
    try:
        with z.open(name) as fh:
            text = io.TextIOWrapper(fh, "utf-8", errors="replace")
            return list(csv.DictReader(text, delimiter="\t"))
    except KeyError:
        return []


def parse_quarter(path: Path, *, symbols: set[str] | None = None,
                  ciks: set[str] | None = None) -> list[dict]:
    """Joined transaction rows for one quarter, optionally filtered to a universe.

    Filtering happens on SUBMISSION first, so the two large child tables are only walked
    for filings that matter.
    """
    try:
        z = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError):
        return []

    subs = {}
    for r in _read_tsv(z, "SUBMISSION.tsv"):
        if str(r.get("DOCUMENT_TYPE") or "").strip() != "4":
            continue                      # Form 3 is a holdings snapshot, Form 5 is late
        sym = (r.get("ISSUERTRADINGSYMBOL") or "").strip().upper()
        cik = (r.get("ISSUERCIK") or "").strip().lstrip("0")
        if symbols is not None and sym not in symbols:
            if ciks is None or cik not in ciks:
                continue
        subs[r["ACCESSION_NUMBER"]] = {
            "symbol": sym,
            "issuer_cik": cik,
            "issuer_name": (r.get("ISSUERNAME") or "").strip(),
            "filing_date": _parse_date(r.get("FILING_DATE", "")),
            "period_of_report": _parse_date(r.get("PERIOD_OF_REPORT", "")),
        }
    if not subs:
        return []

    owners: dict[str, dict] = {}
    for r in _read_tsv(z, "REPORTINGOWNER.tsv"):
        acc = r.get("ACCESSION_NUMBER")
        if acc in subs and acc not in owners:      # first owner on a joint filing
            rel = (r.get("RPTOWNER_RELATIONSHIP") or "").lower()
            title = (r.get("RPTOWNER_TITLE") or "").strip()
            owners[acc] = {
                "owner_cik": (r.get("RPTOWNERCIK") or "").strip().lstrip("0"),
                "owner_name": (r.get("RPTOWNERNAME") or "").strip(),
                "relationship": rel,
                "title": title,
                "is_officer_or_director": any(h in rel for h in OFFICER_HINTS),
                "is_ceo_cfo": any(h in (rel + " " + title).lower()
                                  for h in CEO_CFO_HINTS),
            }

    out = []
    for r in _read_tsv(z, "NONDERIV_TRANS.tsv"):
        acc = r.get("ACCESSION_NUMBER")
        sub = subs.get(acc)
        if sub is None:
            continue
        code = (r.get("TRANS_CODE") or "").strip().upper()

        def _f(key):
            try:
                return float(r.get(key) or "")
            except (TypeError, ValueError):
                return None

        shares = _f("TRANS_SHARES")
        price = _f("TRANS_PRICEPERSHARE")
        out.append({
            **sub,
            **owners.get(acc, {}),
            "accession": acc,
            "trans_date": _parse_date(r.get("TRANS_DATE", "")),
            "code": code,
            "code_meaning": CODE_MEANING.get(code, "unknown"),
            "acquired_disposed": (r.get("TRANS_ACQUIRED_DISP_CD") or "").strip().upper(),
            "shares": shares,
            "price": price,
            "value": (shares * price) if (shares and price) else None,
            "shares_owned_after": _f("SHRS_OWND_FOLWNG_TRANS"),
            "direct_indirect": (r.get("DIRECT_INDIRECT_OWNERSHIP") or "").strip(),
            "is_discretionary": code in DISCRETIONARY_CODES,
        })
    return out


def load(symbols: set[str] | None = None, *, start_year: int = FIRST_YEAR,
         ciks: set[str] | None = None, progress: bool = True):
    """Every Form 4 non-derivative transaction for `symbols`, as a DataFrame."""
    import pandas as pd

    rows: list[dict] = []
    qs = quarters(start_year)
    missing = []
    for i, qtr in enumerate(qs, 1):
        path = fetch_quarter(qtr)
        if path is None:
            missing.append(qtr.name)
            continue
        got = parse_quarter(path, symbols=symbols, ciks=ciks)
        rows.extend(got)
        if progress:
            print(f"  [{i}/{len(qs)}] {qtr.name}: {len(got):,} rows "
                  f"({len(rows):,} total)", flush=True)
    df = pd.DataFrame(rows)
    if len(df):
        df["filing_date"] = pd.to_datetime(df["filing_date"], errors="coerce")
        df["trans_date"] = pd.to_datetime(df["trans_date"], errors="coerce")
        # The signal date is the FILING date, never the transaction date - the single
        # easiest way to manufacture a fake edge in this dataset.
        df = df.dropna(subset=["filing_date"]).sort_values("filing_date")
    df.attrs["missing_quarters"] = missing
    return df


def main(argv=None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--symbols", default="AAPL,MSFT,NVDA,JPM,XOM,FICO,PYPL")
    ap.add_argument("--start-year", type=int, default=FIRST_YEAR)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    syms = {s.strip().upper() for s in args.symbols.split(",") if s.strip()}
    df = load(syms, start_year=args.start_year)
    print(f"\n{len(df):,} transactions, {df.symbol.nunique() if len(df) else 0} symbols")
    if len(df):
        print(f"filing_date span: {df.filing_date.min().date()} -> "
              f"{df.filing_date.max().date()}")
        print("\ncodes:")
        print(df.code.value_counts().head(12).to_string())
        p = df[df.code == "P"]
        print(f"\nopen-market purchases: {len(p):,}")
    if df.attrs.get("missing_quarters"):
        print(f"quarters unavailable: {df.attrs['missing_quarters']}")
    if args.out and len(df):
        df.to_parquet(args.out, index=False)
        print(f"written: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
