"""Go to the live web and settle the claims whose quote is not on the page they cite.

## The ambiguity this exists to close

The 2026-09-11 verification-strength audit found 146 `VERIFIED_LOCAL` claims whose quote
is not on their cited page in any sequence, even ignoring whitespace, and whose certifying
overlap score has a **median of 1.0**. Three causes fit that evidence equally well:

1. an IR index page was cited instead of the specific release it links to;
2. the figure came from a PDF or a deck while the cached page is the HTML landing page;
3. the quote was invented.

**The audit could not tell them apart, because every check in it ran against the CACHED
page.** A source that changed after we cached it is indistinguishable there from a bad
citation. Closing that is this module's whole job, and it needs the live page.

## What it does, and the one thing it refuses to do

For each unlocatable claim, in order:

    live         re-fetch the CITED url and test the quote against the fresh page
    sibling      read the links OUT of that page and test the quote against the ones
                 whose own text is closest to it
    demote       otherwise: UNVERIFIABLE

**It never assembles a URL.** A citation is data to be read, never a string to be built:
guessing `.../q2-2026-results` from a quote about the second quarter would manufacture a
source, and a manufactured source that happens to contain the words is the worst possible
outcome here. Candidates come only from anchors the cited page itself publishes, on the
cited page's own host.

## A refetch overwrites evidence, so it snapshots first

`verify.fetch(refetch=True)` replaces the cached bytes. Those bytes are what the audit ran
against and what every prior verification rests on, so this module copies the existing
cache entry aside before replacing it. The cost of keeping it is a few MB; the cost of
losing it is that the audit stops being reproducible.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .. import net
from . import verify as V
from .store import ExternalStore

#: How many sibling pages one claim may cost. A cap, not a target: the point of ranking
#: candidates by their own text is that the right one is usually first or not there.
MAX_CANDIDATES = 8

#: A candidate must share at least this much of the quote's vocabulary in its anchor text
#: and slug before it is worth a fetch. Below it, we are guessing.
MIN_CANDIDATE_AFFINITY = 0.05

#: What happened to a claim. The first two restore VERIFIED_LOCAL; the last two do not.
OUT_LIVE = "live_exact"            #: the cited page holds it now - the cache was stale
OUT_SIBLING = "sibling_exact"      #: a page the citation links to holds it
OUT_UNREACHABLE = "unreachable"    #: we could not fetch it: SELF_ATTESTED, not a failure
OUT_ABSENT = "still_absent"        #: fetched live, not there, not on any sibling


@dataclass
class Resolution:
    claim_id: str
    outcome: str
    status: str
    url_was: str
    url_now: str | None = None
    mode: str | None = None
    overlap: float | None = None
    reason: str | None = None
    candidates_tried: int = 0
    note: str | None = None


@dataclass
class _Page:
    """One live fetch, kept with its raw bytes so links can be read out of it."""
    fetched: V.Fetched
    raw: bytes = b""
    links: list[tuple[str, str]] = field(default_factory=list)


_TOKENS = re.compile(r"[a-z0-9]{4,}")


def _tokens(text: str | None) -> set[str]:
    return set(_TOKENS.findall((text or "").lower()))


def _snapshot_cache(url: str) -> Path | None:
    """Keep the bytes the previous verification ran against, before replacing them."""
    src = V._cache_path(url)
    if not src.exists():
        return None
    dest = src.with_suffix(f".pre-relocate-{net.utc_now_iso()[:10]}.gz")
    if not dest.exists():
        shutil.copy2(src, dest)
    return dest


def same_host_links(raw: bytes, base_url: str) -> list[tuple[str, str]]:
    """(absolute url, anchor text) for every same-host link the page publishes.

    Reading the citation rather than rewriting it. An IR index page cited instead of the
    release it links to is the single most likely benign cause of an unlocatable quote,
    and the release is one anchor away.
    """
    try:
        from lxml import html as lx
        doc = lx.fromstring(raw.decode("utf-8", errors="replace"))
    except Exception:                       # noqa: BLE001 - an unparseable page has no links
        return []
    try:
        doc.make_links_absolute(base_url)
    except Exception:                       # noqa: BLE001 - a page with no base still has hrefs
        pass
    host = V._host(base_url)
    out, seen = [], set()
    for a in doc.iter("a"):
        href = (a.get("href") or "").strip()
        if not href.startswith("http") or V._host(href) != host:
            continue
        href = href.split("#")[0]
        if href in seen or href == base_url:
            continue
        seen.add(href)
        out.append((href, " ".join((a.text_content() or "").split())[:200]))
    return out


def rank_candidates(quote: str, links: list[tuple[str, str]],
                    limit: int = MAX_CANDIDATES,
                    min_affinity: float = MIN_CANDIDATE_AFFINITY
                    ) -> list[tuple[str, str, float]]:
    """Order the page's own links by how much of the quote's vocabulary they carry.

    The affinity is over the anchor TEXT and the URL slug, which is all a link tells us
    before it is fetched. It is a search order, never a verdict: a candidate still has to
    contain the quote verbatim to resolve anything.
    """
    q = _tokens(quote)
    if not q:
        return []
    scored = []
    for url, anchor in links:
        slug = re.sub(r"[^a-z0-9]+", " ", url.lower().split("?")[0].rsplit("/", 1)[-1])
        affinity = len(q & (_tokens(anchor) | _tokens(slug))) / len(q)
        if affinity >= min_affinity:
            scored.append((url, anchor, round(affinity, 4)))
    scored.sort(key=lambda t: -t[2])
    return scored[:limit]


_EDGAR_DOC = re.compile(
    r"^(https://www\.sec\.gov/Archives/edgar/data/\d+/\d+/)[^/]+$")


def edgar_accession_index(url: str) -> str | None:
    """The accession DIRECTORY a filing document lives in, if this is one.

    An EDGAR filing document publishes no outbound links, so `same_host_links` finds
    nothing and the sibling step has nothing to try - which matters, because the most
    likely benign story for a quote missing from a 10-K is that it is in an EXHIBIT of
    the same filing. This function only truncates a URL to its own directory; it never
    invents a filename.
    """
    m = _EDGAR_DOC.match((url or "").split("?")[0])
    return m.group(1) if m else None


#: The complete-submission text file: the accession number with dashes, `.txt`. EDGAR
#: publishes every accession this way, and it is ONE request that carries every document
#: in the filing with its own SGML header.
_ACCESSION_TXT = re.compile(r"/(\d{10}-?\d{2}-?\d{6})\.txt$")
_DOC_SPLIT = re.compile(rb"<DOCUMENT>(.*?)</DOCUMENT>", re.S | re.I)
_DOC_FILENAME = re.compile(rb"<FILENAME>\s*([^\r\n<]+)", re.I)
_DOC_TYPE = re.compile(rb"<TYPE>\s*([^\r\n<]+)", re.I)

#: An `R<n>.htm` in an accession is not a document. It is one pane of EDGAR's own XBRL
#: "Financial Report" rendering of the PRIMARY document, so a quote found only there is
#: already inside the filing we cited and the citation is not what is wrong - our text
#: extraction of the primary document is. Those two need different fixes, so they must
#: not be collapsed into one "resolved".
_XBRL_RENDER = re.compile(r"/R\d+\.htm$", re.I)


def accession_complete_submission(index_url: str) -> str:
    """`<accession dir>/<accession-number>.txt`, read from the directory LISTING.

    Not assembled: `same_host_links` on the directory finds the file EDGAR publishes
    there, and this picks the one whose name matches the complete-submission pattern.
    """
    return index_url


def edgar_documents(raw: bytes) -> list[tuple[str, str, bytes]]:
    """(filename, type, body) for every document inside a complete submission.

    One fetch, exact answer. The alternative - sweeping the directory's 59 to 182
    published files eight at a time - costs a hundred requests to arrive at the same
    place, and arrives at it by guessing which eight.
    """
    out = []
    for blob in _DOC_SPLIT.findall(raw):
        fn = _DOC_FILENAME.search(blob)
        ty = _DOC_TYPE.search(blob)
        if not fn:
            continue
        body = blob.split(b"<TEXT>", 1)[-1]
        out.append((fn.group(1).decode("ascii", "replace").strip(),
                    (ty.group(1).decode("ascii", "replace").strip() if ty else ""),
                    body))
    return out


OUT_RENDERING = "rendering_only"   #: found only in EDGAR's XBRL rendering of the same doc


def _search_accession(quote: str, docs: list[tuple[str, str, bytes]],
                      accession_dir: str, cited_url: str):
    """Which document of this filing holds the quote - and which KIND of answer it is.

    Three outcomes, and the difference between the last two is the whole point:

    * a real exhibit or sibling document holds it -> the CITATION was wrong, correct it;
    * only `R<n>.htm` holds it -> the quote is inside the primary document we already
      cited, in a table our text extraction did not surface. The citation is right and
      OUR INSTRUMENT is lossy. Correcting the URL there would paper over an extraction
      bug with a citation fix;
    * nothing holds it -> the accession does not contain the quote at all.

    Returns a callable that builds the Resolution, or None to fall through.
    """
    cited_name = cited_url.rsplit("/", 1)[-1].lower()
    real, rendering = None, None
    for filename, doctype, body in docs:
        if filename.lower() == cited_name:
            continue
        text, reason = V._extract_fetched(body, filename)
        if reason or len(text) < V.MIN_PAGE_CHARS:
            continue
        m = V.match_quote(quote, text)
        if m.status != "VERIFIED_LOCAL":
            continue
        url = accession_dir + filename
        if _XBRL_RENDER.search("/" + filename) or doctype.upper() == "XML":
            rendering = rendering or (filename, m)
        else:
            real = (url, filename, doctype, m)
            break

    if real:
        url, filename, doctype, m = real
        return lambda cid, was: Resolution(
            cid, OUT_SIBLING, "VERIFIED_LOCAL", was, url_now=url, mode=m.mode,
            overlap=m.overlap, candidates_tried=len(docs),
            note=f"the quote is in {filename} ({doctype or 'document'}) of the same "
                 f"accession, not in the document cited")
    if rendering:
        filename, m = rendering
        return lambda cid, was: Resolution(
            cid, OUT_RENDERING, "UNVERIFIABLE", was, mode=m.mode, overlap=m.overlap,
            reason="quote_only_in_xbrl_rendering", candidates_tried=len(docs),
            note=f"found in {filename}, which is EDGAR's XBRL RENDERING of the cited "
                 f"document, not a separate source. The citation is right and our text "
                 f"extraction of the primary document is lossy - this is an INSTRUMENT "
                 f"defect, not a bad citation, and it needs an extraction fix")
    return None



def _fetch_live(url: str, cache: dict[str, _Page]) -> _Page:
    if url in cache:
        return cache[url]
    _snapshot_cache(url)
    fetched = V.fetch(url, refetch=True)
    raw = net.read_gzip_bytes(V._cache_path(url)) or b""
    page = _Page(fetched, raw)
    cache[url] = page
    return page


def _fetch_candidate(url: str, cache: dict[str, _Page]) -> _Page:
    """A candidate is fetched through the normal cache - it may already be held."""
    if url in cache:
        return cache[url]
    fetched = V.fetch(url)
    page = _Page(fetched, b"")
    cache[url] = page
    return page


def _testable(page: _Page) -> bool:
    return (page.fetched.ok and not page.fetched.unverifiable_reason
            and len(page.fetched.text) >= V.MIN_PAGE_CHARS)


def resolve_claims(claims: list[dict], *, max_candidates: int = MAX_CANDIDATES,
                   verbose: bool = True) -> list[Resolution]:
    """Settle each claim live. Pure: it reads the web and returns proposals."""
    live: dict[str, _Page] = {}
    out: list[Resolution] = []
    by_url = collections.defaultdict(list)
    for c in claims:
        by_url[c["source_url"]].append(c)

    for i, (url, group) in enumerate(sorted(by_url.items()), 1):
        page = _fetch_live(url, live)
        if verbose:
            state = "ok" if _testable(page) else "UNUSABLE"
            print(f"  [{i:>2}/{len(by_url)}] {state:<8} {len(group):>2} claim(s)  "
                  f"{url[:90]}")
            if not page.fetched.ok:
                print(f"            {page.fetched.error}")

        if not _testable(page):
            # Could not check LIVE. That is our failure, not the researcher's, and the
            # module's founding distinction says it is SELF_ATTESTED.
            why = page.fetched.error or page.fetched.unverifiable_reason or (
                f"live page extracted to {len(page.fetched.text)} chars")
            for c in group:
                out.append(Resolution(c["claim_id"], OUT_UNREACHABLE, "SELF_ATTESTED",
                                      url, reason=str(why)[:300]))
            continue

        if not page.links:
            page.links = same_host_links(page.raw, url)
        edgar_docs: list[tuple[str, str, bytes]] = []
        edgar_dir = edgar_accession_index(url)
        if not page.links and edgar_dir:
            # ONE request for the whole filing. The complete-submission file is listed
            # in the accession directory EDGAR publishes, so it is read, not built.
            listing = _fetch_candidate(edgar_dir, live)
            listing_raw = net.read_gzip_bytes(V._cache_path(edgar_dir)) or b""
            txt_url = next(
                (u for u, _a in same_host_links(listing_raw, edgar_dir)
                 if _ACCESSION_TXT.search(u)), None) if listing.fetched.ok else None
            if txt_url:
                _fetch_candidate(txt_url, live)
                edgar_docs = edgar_documents(
                    net.read_gzip_bytes(V._cache_path(txt_url)) or b"")
                if verbose:
                    print(f"            + {len(edgar_docs)} document(s) in the "
                          f"accession, read from one complete-submission fetch")

        for c in group:
            m = V.match_quote(c["quote"], page.fetched.text)
            if m.status == "VERIFIED_LOCAL":
                out.append(Resolution(c["claim_id"], OUT_LIVE, "VERIFIED_LOCAL", url,
                                      url_now=url, mode=m.mode, overlap=m.overlap,
                                      note="cached page was stale; the live page "
                                           "contains the quote"))
                continue
            # An accession listing names its documents by FILENAME, so anchor
            # affinity is near zero for every one of them and the vocabulary floor
            # would reject the exhibit we are looking for. The set is small and
            # published, so try it in full instead of ranking it away.
            if edgar_docs:
                res = _search_accession(c["quote"], edgar_docs, edgar_dir, url)
                if res is not None:
                    out.append(res(c["claim_id"], url))
                    continue
                ranked = []
            else:
                ranked = rank_candidates(c["quote"], page.links, max_candidates)
            hit = None
            for cand_url, anchor, affinity in ranked:
                cand = _fetch_candidate(cand_url, live)
                if not _testable(cand):
                    continue
                cm = V.match_quote(c["quote"], cand.fetched.text)
                if cm.status == "VERIFIED_LOCAL":
                    hit = (cand_url, anchor, affinity, cm)
                    break
            if hit:
                cand_url, anchor, affinity, cm = hit
                out.append(Resolution(
                    c["claim_id"], OUT_SIBLING, "VERIFIED_LOCAL", url,
                    url_now=cand_url, mode=cm.mode, overlap=cm.overlap,
                    candidates_tried=len(ranked),
                    note=f"quote is on a page the citation links to "
                         f"(anchor affinity {affinity}): {anchor[:80]}"))
            else:
                out.append(Resolution(
                    c["claim_id"], OUT_ABSENT, "UNVERIFIABLE", url,
                    mode=m.mode, overlap=m.overlap,
                    reason="quote_not_locatable_live",
                    candidates_tried=len(ranked),
                    note="fetched live and tested against "
                         f"{len(ranked)} linked page(s); not found on any"))
    return out


def load_unlocatable(store: ExternalStore | None = None,
                     claim_ids: list[str] | None = None) -> list[dict]:
    """The claims to resolve: an explicit list, or every claim the restatement demoted.

    Read from the STORE, never from the report. Reports in this repo have been wrong
    twice while otherwise accurate.
    """
    store = store or ExternalStore()
    sql = ("SELECT claim_id, ticker, industry_id, field, source_url, source_type, "
           "       quote, verify_status, overlap, match_mode "
           "FROM external_claim WHERE quote IS NOT NULL AND quote <> '' "
           "  AND source_url IS NOT NULL AND ")
    params: list = []
    if claim_ids:
        sql += "claim_id IN (SELECT UNNEST(?))"
        params.append(claim_ids)
    else:
        sql += ("match_mode IN (?, ?)")
        params += [V.MATCH_OVERLAP_ONLY, V.MATCH_ABSENT]
    with store.connect() as con:
        rows = con.execute(sql + " ORDER BY claim_id", params).fetchall()
    cols = ("claim_id", "ticker", "industry_id", "field", "source_url", "source_type",
            "quote", "was", "was_overlap", "was_mode")
    return [dict(zip(cols, r)) for r in rows]


def apply_resolutions(store: ExternalStore, resolutions: list[Resolution]) -> dict:
    """Write status, and the corrected URL where one was found. Read back afterwards."""
    updates = [(r.claim_id, r.status, r.overlap, r.reason or (r.note or "")[:300],
                r.mode) for r in resolutions]
    res = V.apply_updates(store, updates)

    moves = [(r.url_now, r.claim_id) for r in resolutions
             if r.outcome == OUT_SIBLING and r.url_now]
    if moves:
        with store.connect() as con:
            con.execute("BEGIN TRANSACTION")
            con.executemany(
                "UPDATE external_claim SET source_url = ? WHERE claim_id = ?", moves)
            con.execute("COMMIT")
        with store.connect() as con:
            got = dict(con.execute(
                "SELECT claim_id, source_url FROM external_claim "
                "WHERE claim_id IN (SELECT UNNEST(?))",
                [[cid for _u, cid in moves]]).fetchall())
        bad = [cid for url, cid in moves if got.get(cid) != url]
        if bad:
            raise RuntimeError(f"url correction did not land for {len(bad)} claims: "
                               f"{bad[:5]}")
    res["urls_corrected"] = len(moves)
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Re-fetch unlocatable claims live and resolve or demote them")
    ap.add_argument("--apply", action="store_true", help="write the resolutions back")
    ap.add_argument("--claim-ids", type=Path, default=None,
                    help="JSON file of claim_ids (a list, or the restatement report)")
    ap.add_argument("--max-candidates", type=int, default=MAX_CANDIDATES)
    ap.add_argument("--report", type=Path, default=None)
    args = ap.parse_args(argv)

    net.trust_windows_certs()
    store = ExternalStore()

    ids = None
    if args.claim_ids:
        blob = json.loads(args.claim_ids.read_text(encoding="utf-8"))
        if isinstance(blob, dict) and "moved" in blob:
            ids = [m["claim_id"] for m in blob["moved"]
                   if m.get("now") == "UNVERIFIABLE"]
        elif isinstance(blob, list):
            ids = [b["claim_id"] if isinstance(b, dict) else b for b in blob]
        else:
            print("could not read claim ids from that file")
            return 1

    claims = load_unlocatable(store, ids)
    if not claims:
        print("nothing to resolve")
        return 1
    print(f"resolving {len(claims)} claims over "
          f"{len({c['source_url'] for c in claims})} distinct urls, live\n")

    resolutions = resolve_claims(claims, max_candidates=args.max_candidates)
    tally = collections.Counter(r.outcome for r in resolutions)
    status = collections.Counter(r.status for r in resolutions)

    print("\nOUTCOMES:")
    for outcome, n in tally.most_common():
        print(f"  {outcome:<14} {n:>4}")
    print("\nRESULTING STATUS:")
    for st, n in status.most_common():
        print(f"  {st:<16} {n:>4}")

    was = {c["claim_id"]: c["was"] for c in claims}
    delta = sum(1 for r in resolutions
                if was[r.claim_id] == "VERIFIED_LOCAL" and r.status != "VERIFIED_LOCAL")
    regained = sum(1 for r in resolutions
                   if was[r.claim_id] != "VERIFIED_LOCAL"
                   and r.status == "VERIFIED_LOCAL")
    print(f"\nVERIFIED_LOCAL lost {delta}, regained {regained}, "
          f"net {regained - delta}")

    report = args.report or (V.REPORTS_DIR /
                             f"RELOCATE_{net.utc_now_iso()[:10]}.json")
    V.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"resolved_at": net.utc_now_iso(), "n": len(resolutions),
               "outcomes": dict(tally), "status": dict(status),
               "resolutions": [vars(r) for r in resolutions]}
    net.atomic_write_json(report, payload)
    print(f"full listing: {report}")

    if args.apply:
        out = apply_resolutions(store, resolutions)
        print(f"APPLIED: {out['written']} rows written, "
              f"{out['verified_in_store']} verified by reading the store back, "
              f"{out['urls_corrected']} urls corrected")
    else:
        print("DRY RUN - nothing written. Re-run with --apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
