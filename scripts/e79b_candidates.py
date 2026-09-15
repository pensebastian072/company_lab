"""E79B Pass 1 candidate extractor.

Retrieval only. It prints candidate sentences from the LOCAL cached EDGAR corpus for
`substitution_risk` and `replication_difficulty`; the claim/field judgement is made by
hand afterwards. This split is deliberate: E79's defect was mechanical field assignment,
so nothing here writes a claim or a categorical.
"""
from __future__ import annotations

import gzip
import json
import re
import sys
from pathlib import Path

# Filing text carries bullets and dashes outside cp1252, and a bare print() on this box
# dies with UnicodeEncodeError mid-unit - the same crash that failed a scheduled job here
# daily. Reconfigure once, loudly replacing what will not encode.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, r"C:\Users\<your-user>\company_lab")

import pandas as pd

from clab import config

QUEUE = Path(r"D:\company_lab_data\external\reports\E79B_pass1_queue.json")

SUBST = re.compile(
    r"\b(substitut\w*|alternative[s]? to|in lieu of|displac\w*|switch(?:ing)? (?:to|from)|"
    r"replac\w* (?:our|their|these) products|instead of (?:our|purchasing)|"
    r"competing (?:materials|technolog\w+)|in-hous\w+|insourc\w+|self-perform\w*|"
    # mode shift and own-versus-use, which is how substitution actually appears in
    # transport, rental and distribution filings
    r"rent(?:al)? (?:rather than|instead of)|purchas\w* rather than rent\w*|own\w* rather than rent\w*|"
    r"rental penetration|modal shift|mode[s]? of transport\w*|truck\w*, rail|rail\w* or truck\w*|"
    r"barge|intermodal|"
    # payment and channel displacement
    r"cashless|digital payment\w*|declin\w* (?:use|usage) of cash|electronic payment\w*|"
    r"e-commerce|online channel\w*|"
    # physical material substitution
    r"(?:wood|steel|concrete|vinyl|aluminum|composite|copper|plastic)[a-z]* (?:substitut|alternativ|in place of)|"
    r"competing material\w*|alternative material\w*)\b", re.I)
BARRIER = re.compile(
    r"\b(qualif\w+|certif\w+|approval\w*|accredit\w+|patent\w*|proprietary|"
    r"switching costs?|long-term (?:contracts?|agreements?)|sole[- ]source|"
    r"lead times?|barriers? to entry|licens\w+|regulat\w+ approval)\b", re.I)
NUM = re.compile(r"\b\d")


def filing_text(cik: str) -> tuple[str, str, str, str] | None:
    """(text, url, form, date) for the newest cached 10-K/10-Q of this CIK."""
    cik = str(cik).zfill(10)
    sub = config.EDGAR_SUBMISSIONS_DIR / f"CIK{cik}.json.gz"
    if not sub.exists():
        return None
    js = json.loads(gzip.open(sub, "rt", encoding="utf-8", errors="replace").read())
    rec = js.get("filings", {}).get("recent", {})
    for form, acc, date, doc in zip(rec.get("form", []), rec.get("accessionNumber", []),
                                    rec.get("filingDate", []), rec.get("primaryDocument", [])):
        if form not in ("10-K", "10-Q"):
            continue
        cached = config.EDGAR_FILINGS_DIR / cik / f"{acc}.txt.gz"
        if not cached.exists():
            continue
        body = gzip.open(cached, "rt", encoding="utf-8", errors="replace").read()
        url = (f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
               f"{acc.replace('-', '')}/{doc}")
        return body, url, form, str(date)
    return None


def sentences(raw: str) -> list[str]:
    txt = re.sub(r"<[^>]+>", " ", raw)
    txt = re.sub(r"&[a-z]+;|&#\d+;", " ", txt)
    txt = re.sub(r"\s+", " ", txt)
    return [s.strip() for s in re.split(r"(?<=[.;])\s+", txt) if 60 <= len(s.strip()) <= 400]


def main(start: int, stop: int, per_field: int = 3) -> int:
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))[start:stop]
    book = pd.read_parquet(r"C:\Users\<your-user>\company_lab\data\scores.parquet")
    cik_of = {r["ticker"]: r.get("cik") for r in book.to_dict("records")}
    for unit in queue:
        iid, members = unit["industry_id"], unit["members"]
        print(f"\n{'='*100}\n## {iid}   ({len(members)}: {' '.join(members)})")
        for tk in members[:4]:
            got = filing_text(cik_of.get(tk) or "")
            if not got:
                print(f"  [{tk}] no cached filing")
                continue
            body, url, form, date = got
            sents = sentences(body)
            for label, pat in (("SUBST", SUBST), ("BARRIER", BARRIER)):
                hits = [s for s in sents if pat.search(s) and NUM.search(s)][:per_field]
                if not hits:
                    hits = [s for s in sents if pat.search(s)][:per_field]
                for s in hits:
                    print(f"  [{tk} {form} {date}] {label}: {s[:260]}")
            print(f"      url: {url}")
    return 0


if __name__ == "__main__":
    a = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    b = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    raise SystemExit(main(a, b))
