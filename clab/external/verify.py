"""Fetch the sources ourselves and settle what a claim is actually worth.

## The distinction this module exists to make

Codex reported "six sampled source URLs were re-fetched successfully and all six
sampled quotes matched". That was Codex re-fetching Codex's own URLs. Nothing in this
repo had seen those pages, so all 109 Phase 0 claims were stored SELF_ATTESTED and
none counted as verified. This module is the thing that changes that, and it is the
external-layer analogue of E40, which measured the local model citing text absent from
the filing 9.7% of the time against qwen's 0.5%.

## Three outcomes, and the one that is NOT a failure

    VERIFIED_LOCAL  we fetched the page and the quote clears MIN_EVIDENCE_OVERLAP
    UNVERIFIABLE    we fetched the source and either the quote is NOT in it or the
                    fetched PDF/binary payload could not be converted to text
    SELF_ATTESTED   we could not fetch the page at all

The third is load-bearing. A 403 from a WAF, a paywall, a moved PDF or a timeout is
OUR failure to check, not evidence that the researcher invented anything. Collapsing it
into UNVERIFIABLE would manufacture a fabrication rate out of network conditions -
exactly the UNKNOWN-is-not-NEGATIVE rule the rest of this layer runs on, applied to
ourselves. The report separates "checked and failed" from "could not check", and only
the first is a fabrication signal.

## Sources are cached, because a fetch is a spend

Every fetched page is written to D:\\company_lab_data\\external\\sources\\ and replayed
free. This box's rule for metered data is that a point spent must never be spent twice;
a re-verification run months from now must not re-hit forty hosts to re-check claims
whose pages have not changed. `--refetch` overrides.

## Reuses, does not re-implement

`_token_overlap` and `MIN_EVIDENCE_OVERLAP = 0.60` come from `clab/qual/scorer.py`.
The judged half and the external half must agree on what "the quote is present" means,
or the two halves' unverifiable rates are not comparable and E40's number stops being a
baseline for this one.
"""
from __future__ import annotations

import argparse
import collections
import decimal
import gzip
import html
import io
import json
import random
import re
import string
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from .. import config, net
from ..qual.scorer import MIN_EVIDENCE_OVERLAP, _token_overlap
from .store import ExternalStore

#: Cached source pages. Bulk, regenerable, on D: like every other cache.
SOURCE_CACHE = config.EXTERNAL_ROOT / "sources"

#: Polite pacing across ~40 distinct hosts. 1 req/s, well under anything these serve.
_LIMITER = net.RateLimiter(1.0)

#: A browser-ish UA. The SEC UA is correct for sec.gov and gets 403s from commercial
#: WAFs, which would turn a policy problem into a fake fabrication signal.
FETCH_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) company_lab/0.1 "
                   "(+research-contact@example.com)"),
    "Accept": "text/html,application/pdf,application/xhtml+xml,*/*",
}

_TAG_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)
_ANY_TAG = re.compile(r"<[^>]+>")
_TAG_RE_BYTES = re.compile(rb"<(script|style)[^>]*>.*?</\1>", re.S | re.I)

#: A page must yield at least this much text before a quote can be tested against it.
#:
#: Found on the first run. Two DOJ press-release URLs fetched with HTTP 200 and
#: extracted to ONE character - a JavaScript shell with no server-rendered body. The
#: guard above was `if not page.text`, and a single space is truthy, so both claims were
#: tested against nothing, scored 0.0 overlap, and were reported as UNVERIFIABLE. That
#: is a fabrication signal manufactured out of a rendering failure, which is precisely
#: what the SELF_ATTESTED tier exists to prevent. An empty page is a page we could not
#: read, not a page that contradicts the quote.
MIN_PAGE_CHARS = 400


@dataclass
class Fetched:
    url: str
    ok: bool
    text: str = ""
    error: str | None = None
    from_cache: bool = False
    n_bytes: int = 0
    unverifiable_reason: str | None = None


def _cache_path(url: str) -> Path:
    return SOURCE_CACHE / f"{net.sha1_text(url)}.gz"


def _meta_path(url: str) -> Path:
    return SOURCE_CACHE / f"{net.sha1_text(url)}.meta.json"


def cached_pdf_urls(urls: list[str]) -> set[str]:
    """URLs whose existing cache entry is a PDF, detected from bytes not suffix."""
    out: set[str] = set()
    for url in urls:
        raw = net.read_gzip_bytes(_cache_path(url))
        if raw is not None and raw[:5] == b"%PDF-":
            out.add(url)
    return out


#: The XML declaration an inline-XBRL document opens with. `lxml.html.fromstring` refuses
#: a str that carries one - and handing it BYTES instead is not the fix, because lxml then
#: guesses the encoding and guesses Latin-1, turning a UTF-8 bullet into `a€¢`. So: decode
#: it ourselves, drop the declaration, and hand lxml a clean string.
_XML_DECL = re.compile(r"<\?xml[^>]*\?>", re.I)


def _decode_page(raw: bytes) -> str:
    """UTF-8 if it really is UTF-8, cp1252 otherwise.

    A strict attempt first, because `errors="replace"` cannot tell a cp1252 document from
    a corrupt UTF-8 one and silently turns every non-ASCII character into U+FFFD. EDGAR
    serves both: POR's 10-Q is cp1252 (a raw \x95 bullet), Goldman's is UTF-8.
    """
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


def _html_to_text(raw: bytes) -> str:
    """Markup to searchable text.

    Two defects lived here and they pulled in opposite directions, which is why neither
    was visible on its own:

    * `lxml.html.fromstring` REFUSES a str carrying an encoding declaration, and every
      modern EDGAR primary document is inline XBRL and opens with one. The raise was
      caught by a bare except and the regex tag-stripper ran instead - which does not
      decode entities - so those pages kept `&#149;` and `&#160;` as literal text.
    * Handing lxml the BYTES instead makes it guess the encoding, and on these documents
      it guesses Latin-1: a UTF-8 bullet became `a€¢` and 309 quotes stopped matching.

    Decode first, strip the declaration, then parse. `markup`, not `html`: the stdlib
    `html` module is imported at module scope for `html.unescape`, and a local of that
    name would shadow it silently.
    """
    markup = _TAG_RE.sub(" ", _decode_page(raw))
    try:
        from lxml import html as lx
        return re.sub(r"\s+", " ", lx.fromstring(_XML_DECL.sub(" ", markup)).text_content())
    except Exception:                       # noqa: BLE001 - any parser failure
        # A parser failure must cost STRUCTURE, not vocabulary: unescape here too, or the
        # fallback silently changes what the page appears to say.
        return re.sub(r"\s+", " ", html.unescape(_ANY_TAG.sub(" ", markup)))


def _pdf_to_text(raw: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(raw))
    parts = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:                   # noqa: BLE001 - one bad page is not fatal
            continue
    return re.sub(r"\s+", " ", " ".join(parts))


def _raw_is_plausibly_text(raw: bytes) -> bool:
    """Reject a binary payload before an HTML decoder turns it into vocabulary.

    The verifier once had VERIFIED_LOCAL claims backed by cached PDF bytes. Binary
    streams contain enough coincidental words to clear a token-set overlap, so content
    type is a precondition to evidence matching, not another score.
    """
    sample = raw[:8192]
    if not sample:
        return False
    printable = sum(b in b"\t\n\r" or 32 <= b < 127 for b in sample) / len(sample)
    alpha_tokens = len(re.findall(rb"[A-Za-z]{3,}", sample))
    # Short, valid HTML fixtures and error pages are allowed through extraction; the
    # existing MIN_PAGE_CHARS gate then classifies them as unreadable/SELF_ATTESTED.
    # The 20-token floor applies only once a payload is large enough to masquerade as
    # a real source page.
    token_floor = 20 if len(sample) >= MIN_PAGE_CHARS else 3
    return printable >= 0.85 and alpha_tokens >= token_floor


def _extracted_is_plausibly_text(text: str) -> bool:
    if not isinstance(text, str) or not text:
        return False
    printable = sum(c in string.printable or c.isprintable() for c in text) / len(text)
    return printable >= 0.90 and len(re.findall(r"[A-Za-z]{3,}", text)) >= 20


def _extract_fetched(raw: bytes, url: str) -> tuple[str, str | None]:
    """Return searchable text and a loud reason when fetched bytes are unusable."""
    is_pdf = raw[:5] == b"%PDF-" or url.lower().split("?")[0].endswith(".pdf")
    if is_pdf:
        try:
            text = _pdf_to_text(raw)
        except Exception:                  # noqa: BLE001 - reason travels to catalog
            return "", "pdf_not_extracted"
        return (text, None) if _extracted_is_plausibly_text(text) else (
            "", "pdf_not_extracted")
    if not _raw_is_plausibly_text(raw):
        return "", "non_text_payload"
    return _html_to_text(raw), None


def extract_text(raw: bytes, url: str) -> str:
    """Bytes to searchable text. PDF detected by magic number, not by extension -
    several of these URLs serve a PDF from a path with no .pdf on it."""
    return _extract_fetched(raw, url)[0]


def fetch(url: str, *, refetch: bool = False) -> Fetched:
    """Fetch and cache one source. Never raises."""
    SOURCE_CACHE.mkdir(parents=True, exist_ok=True)
    cache, meta = _cache_path(url), _meta_path(url)

    if cache.exists() and not refetch:
        raw = net.read_gzip_bytes(cache)
        if raw is not None:
            text, reason = _extract_fetched(raw, url)
            return Fetched(url, True, text, from_cache=True, n_bytes=len(raw),
                           unverifiable_reason=reason)
    if meta.exists() and not refetch:
        prior = net.read_json(meta) or {}
        if prior.get("error"):
            return Fetched(url, False, error=prior["error"], from_cache=True)

    try:
        raw = net.http_get(url, headers=FETCH_HEADERS, limiter=_LIMITER, timeout=45)
    except Exception as exc:                # noqa: BLE001 - a dead link is data
        err = f"{type(exc).__name__}: {exc}"[:300]
        net.atomic_write_json(meta, {"url": url, "error": err,
                                     "fetched_at": net.utc_now_iso()})
        return Fetched(url, False, error=err)

    net.atomic_write_gzip_bytes(cache, raw)
    net.atomic_write_json(meta, {"url": url, "bytes": len(raw), "error": None,
                                 "fetched_at": net.utc_now_iso()})
    text, reason = _extract_fetched(raw, url)
    return Fetched(url, True, text, n_bytes=len(raw), unverifiable_reason=reason)


def _numeric_tokens(text: str) -> set[str]:
    """Numbers must survive a fuzzy quote match; vocabulary cannot substitute for them."""
    found = re.findall(
        r"(?<![A-Za-z0-9])[-+]?\$?\d[\d,]*(?:\.\d+)?%?(?![A-Za-z0-9])",
        text or "")
    out = set()
    for token in found:
        raw = token.replace("$", "").replace(",", "").rstrip("%").lstrip("+-")
        try:
            value = decimal.Decimal(raw)
            out.add(format(value.normalize(), "f"))
        except decimal.InvalidOperation:
            continue
    return out


#: How a quote was matched against its page. Recorded per claim so the strength of
#: VERIFIED_LOCAL is queryable from the store instead of being re-derived by an audit.
#:
#: Only the first two certify. `overlap_only` is the old fallback, kept as a REPORTED
#: warning and never as a pass - it is the path that produced the ICI false match.
MATCH_EXACT = "exact"                  #: normalised character containment
MATCH_NO_WHITESPACE = "no_whitespace"  #: containment once whitespace is ignored
MATCH_OVERLAP_ONLY = "overlap_only"    #: vocabulary agrees, the sentence is not there
MATCH_NUMERIC_MISMATCH = "numeric_mismatch"  #: the quote's own figures are not on the page
MATCH_ABSENT = "absent"                #: neither containment nor enough vocabulary
MATCH_UNREADABLE = "unreadable"        #: no quote, or no page text to test against

CERTIFYING_MATCH_MODES = (MATCH_EXACT, MATCH_NO_WHITESPACE)

#: Characters that differ between a quote as a researcher copied it and the same
#: sentence as a page encodes it. NFKC handles the compatibility forms (including
#: U+00A0 and the ligatures); it does NOT touch curly quotes or dashes, so they are
#: mapped explicitly. Measured yield over the corpus is in
#: journal/experiments/VERIFICATION_STRENGTH_AUDIT_2026-09-11.md.
_PUNCT_MAP = {
    0x2018: "'", 0x2019: "'", 0x201A: "'", 0x201B: "'", 0x2032: "'",
    0x00B4: "'", 0x0060: "'", 0x02BC: "'",
    0x201C: '"', 0x201D: '"', 0x201E: '"', 0x201F: '"', 0x2033: '"', 0x00AB: '"',
    0x00BB: '"',
    0x2010: "-", 0x2011: "-", 0x2012: "-", 0x2013: "-", 0x2014: "-", 0x2015: "-",
    0x2212: "-", 0x00AD: "",          # soft hyphen: a break hint, not a character
    0x200B: "", 0x200C: "", 0x200D: "", 0xFEFF: "",   # zero-width / BOM
    0x2026: "...",
}
#: The C1 block, folded through cp1252. A raw U+0080-U+009F in prose is never a control
#: character - it is a cp1252 byte that was decoded as Latin-1 somewhere upstream. Python's
#: own `html.unescape` already applies this table to NUMERIC references, so `&#149;`
#: decodes to U+2022 BULLET while a raw `` in a stored quote stays U+0095, and the two
#: sides of the comparison disagree about a character that is the same character. Measured
#: on POR's rate-case quote, which is where this was found.
_C1_CP1252 = {i: bytes([i]).decode("cp1252") for i in range(0x80, 0xA0)
              if i not in (0x81, 0x8D, 0x8F, 0x90, 0x9D)}

#: Anything Unicode calls a space becomes one ASCII space before comparison.
_SPACE_RE = re.compile(r"[\s   -     　]+")
_WS_STRIP_RE = re.compile(r"[\s   -     　]+")


def normalize_for_match(text: str | None) -> str:
    """Fold away every difference that is ENCODING rather than CONTENT.

    EDGAR wraps figures in `&#160;`, so `$3,619&#160;million` can never be a verbatim
    substring of a quote a human copied - which is why `data.sec.gov` (JSON, no
    entities) had a 0.0% fallback rate over 321 claims while `sec.gov` HTML had 39.3%
    over 5,484. Same filer, same facts, different encoding. That control is what proves
    this is an encoding problem and not a citation problem.

    Order matters: unescape before NFKC (an entity can decode TO a compatibility
    character), map punctuation after NFKC (NFKC leaves curly quotes alone), collapse
    whitespace last.
    """
    if not text or not isinstance(text, str):
        return ""
    out = html.unescape(text)
    if "&" in out:
        # Double-escaped pages exist (`&amp;#160;`). One more pass, never a loop:
        # unescaping to a fixed point would let a page containing the literal text
        # "&amp;" match a quote containing "&".
        out = html.unescape(out)
    out = unicodedata.normalize("NFKC", out)
    out = out.translate(_C1_CP1252).translate(_PUNCT_MAP)
    return _SPACE_RE.sub(" ", out).strip().lower()


def _strip_whitespace(text: str) -> str:
    return _WS_STRIP_RE.sub("", text)


@dataclass
class QuoteMatch:
    """The verdict on one quote against one page, with HOW it was reached."""
    status: str
    overlap: float | None
    mode: str
    reason: str | None = None


def match_quote(quote: str | None, page_text: str) -> QuoteMatch:
    """Exact containment is the bar. Vocabulary overlap warns and never certifies.

    Two comparisons certify, both of them CONTAINMENT of the whole quote:

    1. `exact` - the normalised quote is a substring of the normalised page.
    2. `no_whitespace` - the same, once whitespace is ignored on both sides. This is
       what catches text lifted out of an HTML table, where the cells concatenate:
       `...customer balances$3,619$3,5263%`. The character sequence is still all there
       and in order, so it is containment, not similarity.

    Everything else records `_token_overlap` as a WARNING and returns UNVERIFIABLE. The
    fallback compared vocabulary, not language: the 146 claims it certified on the
    cached corpus have a MEDIAN overlap of 1.0 on text that is not on their page in any
    sequence, and the ICI page scored 0.8182 while saying $47.6T/-2.5% where the quote
    said $49.1T/+11.2%.
    """
    if (not quote or not isinstance(page_text, str) or not page_text
            or page_text.lstrip().startswith("%PDF-")):
        return QuoteMatch("UNVERIFIABLE", None, MATCH_UNREADABLE, "no_text_to_check")

    norm_q = normalize_for_match(quote)
    norm_p = normalize_for_match(page_text)
    if not norm_q:
        return QuoteMatch("UNVERIFIABLE", None, MATCH_UNREADABLE, "empty_quote")
    if norm_q in norm_p:
        return QuoteMatch("VERIFIED_LOCAL", 1.0, MATCH_EXACT, None)
    if _strip_whitespace(norm_q) in _strip_whitespace(norm_p):
        return QuoteMatch("VERIFIED_LOCAL", 1.0, MATCH_NO_WHITESPACE, None)

    overlap = round(_token_overlap(quote, page_text), 4)
    if not _numeric_tokens(quote).issubset(_numeric_tokens(page_text)):
        return QuoteMatch("UNVERIFIABLE", overlap, MATCH_NUMERIC_MISMATCH,
                          "quote_figures_not_on_page")
    if overlap >= MIN_EVIDENCE_OVERLAP:
        # The old pass. It is now a warning, and it is the interesting one: the page
        # shares this quote's vocabulary and its figures but not its sentence.
        return QuoteMatch("UNVERIFIABLE", overlap, MATCH_OVERLAP_ONLY,
                          "quote_not_contained_vocabulary_only")
    return QuoteMatch("UNVERIFIABLE", overlap, MATCH_ABSENT, "quote_not_found")


def check_quote(quote: str | None, page_text: str) -> tuple[str, float | None]:
    """(verify_status, overlap) for one quote against one fetched page.

    Kept as the two-tuple the callers already read; `match_quote` carries the mode.
    """
    m = match_quote(quote, page_text)
    return m.status, m.overlap


#: A bulk write to the store contends with the other session. DuckDB takes a single
#: writer lock on the file, and the failure mode already seen here is the bad one: the
#: loop dies PART WAY through, 134 of 212 rows landed, and neither session can see it
#: from its own output. So: one transaction, retried on the lock, and read back.
_LOCK_RETRIES = 6
_LOCK_SLEEP_S = 5.0


def apply_updates(store: ExternalStore, updates: list[tuple]) -> dict:
    """Write (claim_id, status, overlap, reason, match_mode) rows, then VERIFY them.

    Idempotent: re-running writes the same values. Never reports success it has not
    read back out of the store - see CHAT_A_B_PROTOCOL.md rule 3.
    """
    import time

    rows = [(st, ov, reason, mode, cid) for cid, st, ov, reason, mode in updates]
    if not rows:
        # Nothing to write is a legitimate outcome - every claim was left alone - and
        # must not read as a failed write.
        return {"written": 0, "verified_in_store": 0}
    last: Exception | None = None
    for attempt in range(1, _LOCK_RETRIES + 1):
        try:
            with store.connect() as con:
                con.execute("BEGIN TRANSACTION")
                con.executemany(
                    "UPDATE external_claim SET verify_status = ?, overlap = ?, "
                    "verify_reason = ?, match_mode = ? WHERE claim_id = ?", rows)
                con.execute("COMMIT")
            last = None
            break
        except Exception as exc:            # noqa: BLE001 - the lock is the expected one
            last = exc
            print(f"  store write attempt {attempt}/{_LOCK_RETRIES} failed: "
                  f"{type(exc).__name__}: {str(exc)[:120]}")
            if attempt < _LOCK_RETRIES:
                time.sleep(_LOCK_SLEEP_S)
    if last is not None:
        raise RuntimeError(
            f"could not write {len(rows)} claim updates after {_LOCK_RETRIES} "
            f"attempts: {last}") from last

    # Read back. A silent partial write is the thing this exists to catch.
    want = {cid: (st, mode) for cid, st, _ov, _r, mode in updates}
    with store.connect() as con:
        got = dict(con.execute(
            "SELECT claim_id, verify_status || '|' || COALESCE(match_mode, '') "
            "FROM external_claim WHERE claim_id IN "
            "(SELECT UNNEST(?))", [list(want)]).fetchall())
    mismatched = [cid for cid, (st, mode) in want.items()
                  if got.get(cid) != f"{st}|{mode or ''}"]
    if mismatched:
        raise RuntimeError(
            f"store read-back disagrees on {len(mismatched)} of {len(want)} claims "
            f"(first: {mismatched[:5]}) - the write was PARTIAL, do not trust any "
            f"count taken from this run")
    return {"written": len(rows), "verified_in_store": len(want) - len(mismatched)}


def verify_all(*, store: ExternalStore | None = None, refetch: bool = False,
               sample: float = 1.0, seed: int = 42,
               apply: bool = False, cached_pdfs_only: bool = False) -> dict:
    """Fetch every distinct source once, then settle every claim that cites it."""
    store = store or ExternalStore()
    with store.connect() as con:
        rows = con.execute(
            "SELECT claim_id, ticker, industry_id, source_url, quote, verify_status "
            "FROM external_claim ORDER BY claim_id").fetchall()
    claims = [{"claim_id": r[0], "ticker": r[1], "industry_id": r[2],
               "source_url": r[3], "quote": r[4], "was": r[5]} for r in rows]
    if not claims:
        return {"claims": 0}

    urls = sorted({c["source_url"] for c in claims
                   if c["source_url"] and c.get("quote")})
    if cached_pdfs_only:
        urls = sorted(cached_pdf_urls(urls))
    if sample < 1.0:
        rng = random.Random(seed)
        keep = set(rng.sample(urls, max(1, int(len(urls) * sample))))
        urls = sorted(keep)

    pages: dict[str, Fetched] = {}
    for i, url in enumerate(urls, 1):
        pages[url] = fetch(url, refetch=refetch)
        f = pages[url]
        state = "cache" if f.from_cache else ("ok" if f.ok else "FAIL")
        print(f"  [{i:>2}/{len(urls)}] {state:<5} {url[:96]}"
              + (f"\n            {f.error}" if not f.ok else ""))

    updates, tally, modes = [], collections.Counter(), collections.Counter()
    unfetched, contradicted = [], []
    for c in claims:
        # A COMPUTED claim has no quote, because it is not a quotation - it is a number
        # we derived from a dataset we hold. There is nothing to match it against and
        # running it through check_quote would score it UNVERIFIABLE, turning our own
        # arithmetic into a fabrication signal.
        if not c.get("quote"):
            tally["VERIFIED_LOCAL"] += 1
            continue
        page = pages.get(c["source_url"])
        if page is None:
            continue                        # not in this sample
        if page.unverifiable_reason:
            tally["UNVERIFIABLE"] += 1
            contradicted.append((c["claim_id"], c["industry_id"] or c["ticker"],
                                 None, c["source_url"]))
            unfetched.append((c["claim_id"], c["source_url"],
                              page.unverifiable_reason))
            updates.append((c["claim_id"], "UNVERIFIABLE", None,
                            page.unverifiable_reason, MATCH_UNREADABLE))
            continue
        if not page.ok or len(page.text) < MIN_PAGE_CHARS:
            # Could not check. NOT a fabrication signal - see the module docstring.
            reason = page.error or (
                f"page extracted to {len(page.text)} chars (< {MIN_PAGE_CHARS}); "
                f"likely a JS shell or an unreadable PDF")
            tally["SELF_ATTESTED"] += 1
            unfetched.append((c["claim_id"], c["source_url"], reason))
            updates.append((c["claim_id"], "SELF_ATTESTED", None, reason, None))
            continue
        m = match_quote(c["quote"], page.text)
        tally[m.status] += 1
        modes[m.mode] += 1
        if m.status == "UNVERIFIABLE":
            contradicted.append((c["claim_id"], c["industry_id"] or c["ticker"],
                                 m.overlap, c["source_url"]))
        updates.append((c["claim_id"], m.status, m.overlap, m.reason, m.mode))

    if apply and updates:
        apply_updates(store, updates)

    checked = tally["VERIFIED_LOCAL"] + tally["UNVERIFIABLE"]
    return {
        "claims": len(claims), "urls": len(urls),
        "fetched_ok": sum(1 for f in pages.values() if f.ok),
        "fetch_failed": sum(1 for f in pages.values() if not f.ok),
        "from_cache": sum(1 for f in pages.values() if f.from_cache),
        "tally": dict(tally), "modes": dict(modes),
        "checked": checked,
        "exact_containment_rate": (
            round(sum(modes[k] for k in CERTIFYING_MATCH_MODES) / checked, 4)
            if checked else None),
        "unverifiable_rate": round(tally["UNVERIFIABLE"] / checked, 4) if checked else None,
        "contradicted": contradicted, "unfetched": unfetched,
        "applied": bool(apply),
    }


# --------------------------------------------------------------------- restate
#: Where the restatement dry-run writes the full per-claim listing. The console
#: prints the transition TABLE; the file carries every claim behind it, because a
#: normalisation that re-labels thousands of claims must be readable one row at a time
#: before it is applied.
REPORTS_DIR = config.EXTERNAL_ROOT / "reports"


def _host(url: str | None) -> str:
    parts = (url or "").split("/")
    return parts[2] if len(parts) > 2 else "?"


def cached_page(url: str) -> Fetched:
    """The cached page for a URL, or ok=False. NEVER fetches.

    A restatement must not spend forty hosts' patience re-fetching pages it already
    holds, and more importantly it must be comparable to the audit, which ran entirely
    against this cache.
    """
    raw = net.read_gzip_bytes(_cache_path(url))
    if raw is None:
        return Fetched(url, False, error="not_cached")
    text, reason = _extract_fetched(raw, url)
    return Fetched(url, True, text, from_cache=True, n_bytes=len(raw),
                   unverifiable_reason=reason)


def restate_corpus(*, store: ExternalStore | None = None, apply: bool = False,
                   refetch: bool = False,
                   report_path: Path | None = None) -> dict:
    """Re-settle every quoted claim under the containment rule, and SAY WHAT MOVES.

    Dry by default. `apply=False` writes nothing at all - not a status, not an overlap,
    not a mode - and returns the complete list of proposed transitions. This is the
    whole point: re-labelling 7,000-odd claims on a normalisation change is the same
    class of edit as the DSR unit bug, and it gets the same treatment.

    A claim whose page is NOT in the cache is left ALONE and reported as
    `no_cached_page`. It is not demoted: "we did not look" is not "we looked and it was
    not there", which is the distinction the whole module is built around.
    """
    store = store or ExternalStore()
    with store.connect() as con:
        rows = con.execute(
            "SELECT claim_id, ticker, industry_id, field, source_url, source_type, "
            "       quote, verify_status, overlap, verify_reason "
            "FROM external_claim WHERE quote IS NOT NULL AND quote <> '' "
            "  AND source_url IS NOT NULL ORDER BY claim_id").fetchall()
    cols = ("claim_id", "ticker", "industry_id", "field", "source_url", "source_type",
            "quote", "was", "was_overlap", "was_reason")
    claims = [dict(zip(cols, r)) for r in rows]
    if not claims:
        return {"claims": 0}

    urls = sorted({c["source_url"] for c in claims})
    pages: dict[str, Fetched] = {}
    for i, url in enumerate(urls, 1):
        pages[url] = fetch(url, refetch=True) if refetch else cached_page(url)
        if i % 200 == 0 or i == len(urls):
            print(f"  pages {i}/{len(urls)}")

    transitions = collections.Counter()
    modes = collections.Counter()
    skipped = collections.Counter()
    updates, moved, unchanged_but_weak, skipped_rows = [], [], [], []

    for c in claims:
        page = pages[c["source_url"]]
        if not page.ok:
            skipped["no_cached_page"] += 1
            skipped_rows.append({**{k: c[k] for k in
                                    ("claim_id", "ticker", "industry_id", "field",
                                     "source_url", "was")},
                                 "why": page.error or "not_cached"})
            continue
        if page.unverifiable_reason:
            skipped[page.unverifiable_reason] += 1
            skipped_rows.append({**{k: c[k] for k in
                                    ("claim_id", "ticker", "industry_id", "field",
                                     "source_url", "was")},
                                 "why": page.unverifiable_reason})
            continue
        if len(page.text) < MIN_PAGE_CHARS:
            skipped["page_under_min_chars"] += 1
            skipped_rows.append({**{k: c[k] for k in
                                    ("claim_id", "ticker", "industry_id", "field",
                                     "source_url", "was")},
                                 "why": f"page extracted to {len(page.text)} chars"})
            continue

        m = match_quote(c["quote"], page.text)
        modes[m.mode] += 1
        transitions[(c["was"], m.status)] += 1
        updates.append((c["claim_id"], m.status, m.overlap, m.reason, m.mode))
        if m.status != c["was"]:
            moved.append({**{k: c[k] for k in
                             ("claim_id", "ticker", "industry_id", "field",
                              "source_url", "source_type", "was", "was_overlap")},
                          "now": m.status, "mode": m.mode, "reason": m.reason,
                          "overlap": m.overlap, "quote": c["quote"]})
        elif m.status == "VERIFIED_LOCAL" and m.mode not in CERTIFYING_MATCH_MODES:
            unchanged_but_weak.append(c["claim_id"])

    checked = sum(modes.values())
    res = {
        "claims": len(claims), "urls": len(urls), "checked": checked,
        "modes": dict(modes), "skipped": dict(skipped),
        "transitions": {f"{a}->{b}": n for (a, b), n in sorted(transitions.items())},
        "exact_containment": sum(modes[k] for k in CERTIFYING_MATCH_MODES),
        "exact_containment_rate": (
            round(sum(modes[k] for k in CERTIFYING_MATCH_MODES) / checked, 4)
            if checked else None),
        "moved": moved, "skipped_rows": skipped_rows,
        "applied": False,
    }
    if report_path is None:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        report_path = REPORTS_DIR / (
            f"RESTATE_CONTAINMENT_{net.utc_now_iso()[:10]}.json")
    net.atomic_write_json(report_path, res)
    res["report_path"] = str(report_path)

    if apply:
        res.update(apply_updates(store, updates))
        res["applied"] = True
        net.atomic_write_json(report_path, res)
    return res


def _restate_main(args) -> int:
    res = restate_corpus(apply=args.apply, refetch=args.refetch,
                         report_path=args.report)
    if not res.get("claims"):
        print("no quoted claims in the catalog")
        return 1
    print(f"\nquoted claims {res['claims']}  distinct urls {res['urls']}  "
          f"tested {res['checked']}")
    print("\nHOW each tested quote matches its page:")
    for mode, n in sorted(res["modes"].items(), key=lambda kv: -kv[1]):
        mark = "certifies" if mode in CERTIFYING_MATCH_MODES else "does NOT certify"
        print(f"  {mode:<18} {n:>6}  {n / res['checked']:>7.1%}  {mark}")
    print(f"\nexact containment (either certifying mode): "
          f"{res['exact_containment']} / {res['checked']} "
          f"= {res['exact_containment_rate']:.1%}")

    if res["skipped"]:
        print("\nNOT tested, and therefore NOT re-labelled:")
        for why, n in sorted(res["skipped"].items(), key=lambda kv: -kv[1]):
            print(f"  {why:<24} {n:>6}")

    print("\nPROPOSED TRANSITIONS (was -> now):")
    for key, n in sorted(res["transitions"].items(), key=lambda kv: -kv[1]):
        was, now = key.split("->")
        print(f"  {was:<16} -> {now:<16} {n:>6}"
              + ("" if was == now else "   <- A CHANGE"))
    print(f"\nclaims that CHANGE status: {len(res['moved'])}")
    for (was, now, mode), n in collections.Counter(
            (m["was"], m["now"], m["mode"]) for m in res["moved"]).most_common():
        print(f"  {was} -> {now}  via {mode:<18} {n:>5}")
    by_field = collections.Counter(m["field"] for m in res["moved"])
    if by_field:
        print("  by field: " + ", ".join(f"{f} {n}" for f, n in by_field.most_common(8)))
    by_host = collections.Counter(_host(m["source_url"]) for m in res["moved"])
    if by_host:
        print("  by host:  " + ", ".join(f"{h} {n}" for h, n in by_host.most_common(8)))

    print(f"\nfull per-claim listing: {res['report_path']}")
    if res["applied"]:
        print(f"APPLIED: {res['written']} rows written, "
              f"{res['verified_in_store']} verified by reading the store back")
    else:
        print("DRY RUN - nothing written. Read the listing, then re-run with --apply.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verify external claims against sources")
    ap.add_argument("--apply", action="store_true", help="write verify_status back")
    ap.add_argument("--refetch", action="store_true", help="ignore the source cache")
    ap.add_argument("--sample", type=float, default=1.0,
                    help="fraction of distinct URLs to check (default all)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--cached-pdfs-only", action="store_true",
                    help="re-verify only URLs whose existing cache begins with %PDF")
    ap.add_argument("--restate", action="store_true",
                    help="re-settle every quoted claim under the containment rule "
                         "against the CACHED pages and report every transition")
    ap.add_argument("--report", type=Path, default=None,
                    help="where --restate writes its full per-claim listing")
    args = ap.parse_args(argv)

    if args.restate:
        if args.refetch:
            net.trust_windows_certs()
        return _restate_main(args)

    # Called at the entrypoint, not from config (which stays import-safe). The
    # TLS-intercepting proxy died with Norton, but usgs.gov still failed CERTIFICATE_
    # VERIFY_FAILED on the first run, so the Windows trust store is still worth loading
    # before reaching forty unrelated hosts.
    net.trust_windows_certs()
    print(f"overlap threshold {MIN_EVIDENCE_OVERLAP} (shared with the judged half)")
    print(f"source cache: {SOURCE_CACHE}\n")
    res = verify_all(refetch=args.refetch, sample=args.sample, seed=args.seed,
                     apply=args.apply, cached_pdfs_only=args.cached_pdfs_only)
    if not res.get("claims"):
        print("no claims in the catalog")
        return 1

    print(f"\nurls {res['urls']}  fetched {res['fetched_ok']}  "
          f"failed {res['fetch_failed']}  from cache {res['from_cache']}")
    print(f"claims {res['claims']}  tally {res['tally']}")
    print(f"\nCHECKED (fetched and tested): {res['checked']}")
    if res.get("modes"):
        print("  how each quote matched its page:")
        for mode, n in sorted(res["modes"].items(), key=lambda kv: -kv[1]):
            mark = "certifies" if mode in CERTIFYING_MATCH_MODES else "WARNS ONLY"
            print(f"    {mode:<18} {n:>6}   {mark}")
        print(f"  exact containment rate: {res.get('exact_containment_rate')}  "
              f"<- what VERIFIED_LOCAL now means")
    print(f"  unverifiable rate: {res['unverifiable_rate']}  "
          f"<- the E40 analogue. LFM2.5 on filings was 0.097, qwen 0.005.")
    print(f"COULD NOT VERIFY (fetch/extraction failed): {len(res['unfetched'])} "
          f"- fetch failures stay SELF_ATTESTED; extraction failures are UNVERIFIABLE")

    if res["contradicted"]:
        print("\nquote NOT found in its own source:")
        for cid, owner, ov, url in res["contradicted"]:
            print(f"  {cid}  {owner}  overlap {ov}  {url[:80]}")
    if res["unfetched"]:
        print("\nunreachable sources:")
        for cid, url, err in res["unfetched"][:20]:
            print(f"  {cid}  {url[:70]}  {err[:60]}")

    if not args.apply:
        print("\nDRY RUN - verify_status not written. Re-run with --apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
