"""The evidence pack: what the model is allowed to reason from.

Bounded, cited, and built from material we already have. The model never sees a raw
10-K - that would blow the context window and, worse, let it answer from whichever
fragment happened to survive truncation.

Slots and their budgets follow the design: identity, the computed quant fact sheet,
retrieved 10-K Item 1 / 1A / 7 chunks, recent headlines, estimate context, and the
capital-allocation history. Retrieval is embedding-based via nomic-embed-text with a
keyword fallback, so a company still gets a sane pack when the embedder is down.

The pack's sha1 is the qual cache key, so anything that changes the evidence - a new
filing, refreshed fundamentals, a different retrieval result - automatically forces
a re-score, and nothing else does.
"""
from __future__ import annotations

from ..net import sha1_text
from ..scoring import rubric
from ..sources import edgar_filings
from . import ollama

# Retrieval queries, one per component. Kept here rather than in prompts.py so the
# retrieved evidence and the question asked of it cannot drift apart.
QUERIES = {
    "SG": ("total addressable market growth, demand drivers, backlog, capacity "
           "expansion, secular trends, new products, long-term growth outlook"),
    "BQ": ("competitive advantages, barriers to entry, switching costs, patents and "
           "intellectual property, brand, scale, network effects, competition"),
    "MG": ("management experience, executive leadership, capital allocation, "
           "acquisitions, share repurchases, dividends, capital expenditure plans"),
}

MAX_CHUNKS_PER_COMPONENT = 8
MAX_CHUNK_CHARS = 1600
#: Hard cap on chunks embedded per company. A bank's 10-K runs to hundreds of
#: pages; without this, JPM alone produced enough chunks to stall the batch for
#: half an hour. The cap keeps the slowest filer within a few times the median.
MAX_CHUNKS_TOTAL = 160


def _fmt(v, kind: str = "num") -> str:
    if v is None:
        return "n/a"
    if kind == "pct":
        return f"{v * 100:.1f}%"
    if kind == "big":
        a = abs(v)
        if a >= 1e12:
            return f"${v / 1e12:.2f}T"
        if a >= 1e9:
            return f"${v / 1e9:.1f}B"
        if a >= 1e6:
            return f"${v / 1e6:.1f}M"
        return f"${v:,.0f}"
    if isinstance(v, float):
        return f"{v:,.2f}"
    return str(v)


def fact_sheet(ctx) -> str:
    """The measured half, rendered for the model.

    This is deliberately included: it anchors the qualitative judgement to what the
    filings actually show, and it is what makes a contradiction between the model's
    growth story and the measured revenue series visible on the scorecard.
    """
    M = ctx.metrics
    lines = [
        f"Company: {ctx.name} ({ctx.ticker})",
        f"Sector: {ctx.sector or 'n/a'} / {ctx.sub_industry or 'n/a'}",
        f"Filer profile: {ctx.profile.name}",
        f"Fundamentals through: {M.raw('data_through') or 'n/a'}",
        "",
        "MEASURED FINANCIALS (trailing twelve months unless stated):",
        f"  Revenue: {_fmt(M.raw('revenue_ttm'), 'big')}"
        f"   YoY: {_fmt(M.raw('revenue_yoy'), 'pct')}"
        f"   3Y CAGR: {_fmt(M.raw('revenue_cagr_3y'), 'pct')}"
        f"   5Y CAGR: {_fmt(M.raw('revenue_cagr_5y'), 'pct')}",
        f"  Quarterly revenue YoY, last four: "
        f"{[f'{y * 100:.1f}%' for y in (M.raw('revenue_yoy_last4') or [])] or 'n/a'}",
        f"  Revenue growth accelerating (measured): {M.raw('revenue_accelerating')}",
        f"  Gross margin: {_fmt(M.raw('gross_margin'), 'pct')}"
        f"   Operating margin: {_fmt(M.raw('operating_margin'), 'pct')}"
        f"   FCF margin: {_fmt(M.raw('fcf_margin'), 'pct')}",
        f"  Operating margin trend: {_fmt(M.raw('margin_trend_bps_yr'))} bps/year",
        f"  ROIC: {_fmt(M.raw('roic'), 'pct')}   ROE: {_fmt(M.raw('roe'), 'pct')}",
        f"  EPS 3Y CAGR: {_fmt(M.raw('eps_cagr_3y'), 'pct')}"
        f"   FCF 3Y CAGR: {_fmt(M.raw('fcf_cagr_3y'), 'pct')}",
        f"  FCF: {_fmt(M.raw('fcf_ttm'), 'big')}"
        f"   conversion vs net income: {_fmt(M.raw('fcf_conversion'))}",
        f"  R&D: {_fmt(M.raw('rnd_pct_revenue'), 'pct')} of revenue"
        f"   Capex: {_fmt(M.raw('capex_pct_revenue'), 'pct')} of revenue"
        f"   SBC: {_fmt(M.raw('sbc_pct_revenue'), 'pct')} of revenue",
        f"  Net debt: {_fmt(M.raw('net_debt'), 'big')}"
        f"   Net debt/EBITDA: {_fmt(M.raw('net_debt_ebitda'))}",
        f"  Diluted share count YoY: {_fmt(M.raw('dilution_yoy'), 'pct')}",
        "",
        "CAPITAL ALLOCATION (trailing twelve months):",
        f"  Buybacks: {_fmt(M.raw('buybacks_ttm'), 'big')}"
        f"   Dividends: {_fmt(M.raw('dividends_ttm'), 'big')}"
        f"   Acquisitions: {_fmt(M.raw('ma_spend_ttm'), 'big')}",
        f"  Impairments: {_fmt(M.raw('impairment_ttm'), 'big')}"
        f"   Goodwill on the balance sheet: {_fmt(M.raw('goodwill'), 'big')}",
        "",
        "MARKET AND EXPECTATIONS:",
        f"  Price: {_fmt(ctx.mk('price'))}"
        f"   Market cap: {_fmt(ctx.mk('market_cap'), 'big')}"
        f"   P/E: {_fmt(ctx.mk('pe'))}   Forward P/E: {_fmt(ctx.mk('fwd_pe'))}",
        f"  Analyst growth next year: {_fmt(ctx.mk('analyst_growth_1y'), 'pct')}"
        f"   long term: {_fmt(ctx.mk('analyst_growth_3y'), 'pct')}",
        f"  Beat consensus in {_fmt(ctx.mk('surprise_beat_rate'), 'pct')} of "
        f"{_fmt(ctx.mk('surprise_quarters'))} reported quarters",
    ]
    return "\n".join(lines)


def _is_prose(chunk: str) -> bool:
    """Reject XBRL context junk when falling back to a whole document.

    The head of these filings is thousands of tokens of taxonomy URIs and member
    names; embedding them wastes the chunk budget on text no analyst would read.
    """
    if len(chunk) < 200:
        return False
    noise = chunk.count("http://") + chunk.count("us-gaap") + chunk.count("fasb.org")
    words = chunk.count(" ") + 1
    if noise * 12 > words:
        return False
    letters = sum(c.isalpha() for c in chunk)
    return letters / max(len(chunk), 1) > 0.55 and chunk.count(".") >= 2


def _keyword_rank(chunks: list[str], query: str, k: int) -> list[str]:
    """Fallback retrieval when the embedder is unavailable."""
    terms = [t for t in query.lower().replace(",", " ").split() if len(t) > 3]
    scored = []
    for c in chunks:
        low = c.lower()
        scored.append((sum(low.count(t) for t in terms), len(c), c))
    scored.sort(key=lambda x: (-x[0], -x[1]))
    return [c for score, _len, c in scored[:k] if score > 0] or chunks[:k]


def embed_chunks(chunks: list[str], *, use_embeddings: bool = True) -> list[list[float]]:
    """Embed the document ONCE per company.

    The three component queries then score against these same vectors. Embedding
    per component instead would triple the cost for no gain - the documents do
    not change between questions.
    """
    if not chunks or not use_embeddings:
        return []
    try:
        return ollama.embed(chunks)
    except Exception:  # noqa: BLE001 - retrieval quality is never worth a crash
        return []


def retrieve(chunks: list[str], query: str, k: int = MAX_CHUNKS_PER_COMPONENT,
             *, doc_vectors: list[list[float]] | None = None,
             use_embeddings: bool = True) -> tuple[list[str], str]:
    """Top-k chunks for one component question. Returns (chunks, method)."""
    if not chunks:
        return [], "none"
    if len(chunks) <= k:
        return chunks, "all"
    if use_embeddings and doc_vectors and len(doc_vectors) == len(chunks):
        try:
            qv = ollama.embed([query], is_query=True)[0]
            if qv:
                scored = [(ollama.cosine(qv, dv), c)
                          for dv, c in zip(doc_vectors, chunks) if dv]
                if any(s > 0 for s, _c in scored):
                    scored.sort(key=lambda x: -x[0])
                    return [c for _s, c in scored[:k]], "embedding"
        except Exception:  # noqa: BLE001
            pass
    return _keyword_rank(chunks, query, k), "keyword"


def chunk_pool(ctx, *, force_filing: bool = False,
               use_embeddings: bool = True) -> dict:
    """The retrievable chunks for one company, embedded once.

    Extracted from `build_pack` so the repair pass can retrieve against the SAME pool with
    a different query without paying for a second embedding run - it is the expensive step
    and all three components share it. `build_pack` calls this, so the rendered pack text
    and therefore every cache key are unchanged by the extraction.
    """
    text, fmeta = edgar_filings.filing_text(ctx.cik, force=force_filing)
    sections = edgar_filings.slice_sections(text)
    # Round-robin across the three sections when capping, so a 300-page risk-factor
    # section cannot crowd out the business description entirely.
    per_section: dict[str, list[str]] = {}
    for name in ("business", "risk_factors", "mdna"):
        body = sections.get(name)
        if body:
            per_section[name] = [f"[{name}] {c[:MAX_CHUNK_CHARS]}"
                                 for c in edgar_filings.chunk_text(body[:400_000])]
    # Whole-document fallback. Measured on Morgan Stanley and Citigroup: both file
    # a 10-K that incorporates the business discussion by reference, so the primary
    # document is ~1-1.5 MB of XBRL boilerplate and statement notes with no Item 1 /
    # 1A / 7 headings to slice. Retrieving from the unsectioned document beats
    # handing the model no filing evidence at all - and it is labelled
    # `_whole_document` so the scorecard never implies the excerpt came from Item 1.
    whole_doc_fallback = False
    if not per_section and text:
        whole_doc_fallback = True
        per_section["_whole_document"] = [
            f"[filing] {c[:MAX_CHUNK_CHARS]}"
            for c in edgar_filings.chunk_text(text[:600_000])
            if _is_prose(c)
        ]

    chunks: list[str] = []
    if per_section:
        share = max(MAX_CHUNKS_TOTAL // len(per_section), 1)
        for name, cs in per_section.items():
            chunks.extend(cs[:share])
    n_chunks_raw = sum(len(v) for v in per_section.values())

    return {
        "chunks": chunks,
        "vectors": embed_chunks(chunks, use_embeddings=use_embeddings),
        "filing": fmeta,
        "per_section": per_section,
        "sections": sections,
        "whole_document_fallback": whole_doc_fallback,
        "n_chunks_before_cap": n_chunks_raw,
    }


#: what the CEO block needs from the proxy, in the words a proxy uses
PROXY_QUERY = ("has served as our chief executive officer since, founder and chief "
               "executive officer, director since, prior to joining the company, "
               "beneficial ownership of common stock, shares beneficially owned by "
               "executive officers and directors, business experience")
#: proxy excerpts appended to the MG pack. Fewer than the 10-K's eight because they sit
#: alongside those, and the CEO block is 8 of the 100 points.
MAX_PROXY_CHUNKS = 6


def proxy_pool(ctx, *, as_of: str | None = None, use_embeddings: bool = True) -> dict:
    """Chunks from the DEF 14A, embedded. Empty and harmless when there is no proxy.

    Kept SEPARATE from `chunk_pool` on purpose. Adding proxy chunks to the shared pool
    would make them compete for SG's and BQ's eight retrieval slots and change all three
    pack hashes - a 20-hour regeneration to fix an 8-point block. This way only MG's
    rendered text moves.
    """
    from ..sources import edgar_filings as ef

    text, meta = ef.proxy_text(ctx.cik, as_of=as_of)
    if not text:
        return {"chunks": [], "vectors": [], "proxy": meta}
    chunks = [f"[proxy] {c[:MAX_CHUNK_CHARS]}"
              for c in edgar_filings.chunk_text(text[:600_000]) if _is_prose(c)]
    chunks = chunks[:MAX_CHUNKS_TOTAL]
    return {"chunks": chunks,
            "vectors": embed_chunks(chunks, use_embeddings=use_embeddings),
            "proxy": {**meta, "n_chunks": len(chunks)}}


def _proxy_block(proxy: dict, *, use_embeddings: bool = True) -> str:
    """The proxy excerpts, or a line saying plainly that there are none."""
    chunks = proxy.get("chunks") or []
    meta = proxy.get("proxy") or {}
    if not chunks:
        return ("PROXY STATEMENT: unavailable "
                f"({meta.get('error', 'no DEF 14A on the submissions feed')}). "
                "Use null for anything about the CEO that the material above does not "
                "support.")
    picked, _method = retrieve(chunks, PROXY_QUERY, k=MAX_PROXY_CHUNKS,
                               doc_vectors=proxy.get("vectors"),
                               use_embeddings=use_embeddings)
    lines = [f"EXCERPTS FROM THE PROXY STATEMENT ({meta.get('form', 'DEF 14A')}, filed "
             f"{meta.get('filed', 'n/a')}) - this is where tenure, founder status and "
             f"ownership are stated:", ""]
    lines += [f"--- proxy excerpt {i + 1} ---\n{c}" for i, c in enumerate(picked)]
    return "\n".join(lines)


def build_pack(ctx, *, force_filing: bool = False, use_embeddings: bool = True,
               pool: dict | None = None, proxy: dict | None = None) -> dict:
    """The evidence pack for one company, one entry per component.

    `proxy` is `proxy_pool(ctx)` and reaches MG ONLY. E22 measured MG's year-over-year
    stability at 0.29 because `founder_led`, `tenure` and `ownership` are proxy facts and
    the pack held only the 10-K; passing it here is E24's whole change.

    Returns {"components": {code: text}, "meta": {...}, "sha1": {code: hash}}.
    """
    sheet = fact_sheet(ctx)
    if pool is None:
        pool = chunk_pool(ctx, force_filing=force_filing,
                          use_embeddings=use_embeddings)
    chunks = pool["chunks"]
    doc_vectors = pool["vectors"]
    fmeta = pool["filing"]
    per_section = pool["per_section"]
    sections = pool["sections"]
    whole_doc_fallback = pool["whole_document_fallback"]
    n_chunks_raw = pool["n_chunks_before_cap"]
    news = _news_lines(ctx)
    packs: dict[str, str] = {}
    hashes: dict[str, str] = {}
    methods: dict[str, str] = {}

    for code in rubric.GENERATED_COMPONENTS:
        picked, method = retrieve(chunks, QUERIES[code], doc_vectors=doc_vectors,
                                  use_embeddings=use_embeddings)
        methods[code] = method
        parts = [sheet, ""]
        if picked:
            where = ("(this filer incorporates its business discussion by reference, so "
                     "these excerpts are from the filing as a whole rather than Item 1 "
                     "/ 1A / 7)" if whole_doc_fallback else "")
            parts += [f"EXCERPTS FROM THE LATEST {fmeta.get('form', 'ANNUAL REPORT')} "
                      f"(filed {fmeta.get('filed', 'n/a')}) {where}:", ""]
            parts += [f"--- excerpt {i + 1} ---\n{c}" for i, c in enumerate(picked)]
        else:
            parts += ["FILING EXCERPTS: unavailable. "
                      f"({fmeta.get('error', 'no sections could be extracted')}) "
                      "Score only what the measured financials above support, and use "
                      "null for anything they do not."]
        if code == "MG" and proxy:
            parts += ["", _proxy_block(proxy, use_embeddings=use_embeddings)]
        parts += ["", news]
        body = "\n".join(parts)
        packs[code] = body
        hashes[code] = sha1_text(body)

    return {
        "components": packs,
        "sha1": hashes,
        "meta": {
            "filing": fmeta,
            "sections_found": sorted(per_section.keys()),
            "item_sections_found": sorted(sections.keys()),
            "whole_document_fallback": whole_doc_fallback,
            "n_chunks": len(chunks),
            "n_chunks_before_cap": n_chunks_raw,
            "chunks_capped": n_chunks_raw > len(chunks),
            "n_embedded": sum(1 for v in doc_vectors if v),
            "retrieval": methods,
            "has_filing_evidence": bool(chunks),
            "fact_sheet_chars": len(sheet),
        },
    }


def _news_lines(ctx) -> str:
    """Recent headlines if we have any. Marked explicitly unavailable when not, so
    the model is not free to invent momentum."""
    items = (ctx.market or {}).get("news") or []
    if not items:
        return ("RECENT NEWS: unavailable. Do not infer recent events or momentum; "
                "treat this slot as empty.")
    lines = ["RECENT NEWS HEADLINES:"]
    for it in items[:20]:
        if isinstance(it, dict):
            t = it.get("title") or it.get("headline")
            if t:
                lines.append(f"  - {t}")
    return "\n".join(lines) if len(lines) > 1 else (
        "RECENT NEWS: unavailable. Do not infer recent events or momentum.")
