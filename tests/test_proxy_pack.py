"""E24: the proxy reaches MG and nothing else.

E22 measured MG's year-over-year stability at 0.29. The cause was the document, not the
model: `founder_led`, `tenure` and `ownership` are DEF 14A facts, and the evidence pack
held only the 10-K, so they were scored 9, 14 and 10 times across ~200 companies against
`industry_expertise`'s 177.

The fix has one expensive way to go wrong. Proxy chunks added to the SHARED pool would
compete for SG's and BQ's eight retrieval slots and change all three pack hashes - a
20-hour regeneration instead of MG's alone. P4 in the registration is exactly that, and
this is P4 as a test.
"""
from clab.qual import evidence as ev_mod


class _M:
    def __init__(self, **v):
        self._v = v

    def raw(self, k):
        return self._v.get(k)

    def as_flat(self):
        return dict(self._v)


def _pool():
    return {"chunks": ["[business] we make industrial coatings"],
            "vectors": [None],
            "filing": {"form": "10-K", "filed": "2026-01-01"},
            "per_section": {"business": ["[business] we make industrial coatings"]},
            "sections": {"business": "we make industrial coatings"},
            "whole_document_fallback": False, "n_chunks_before_cap": 1}


def _proxy():
    return {"chunks": ["[proxy] Ms Chen has served as our chief executive officer "
                       "since 2011 and beneficially owns 4.2% of the common stock"],
            "vectors": [None],
            "proxy": {"form": "DEF 14A", "filed": "2026-03-01", "n_chunks": 1}}


def _ctx(monkeypatch):
    monkeypatch.setattr(ev_mod, "fact_sheet", lambda ctx: "FACTS")
    monkeypatch.setattr(ev_mod, "_news_lines", lambda ctx: "NEWS")
    monkeypatch.setattr(ev_mod, "retrieve",
                        lambda chunks, q, k=8, doc_vectors=None, use_embeddings=True:
                        (chunks[:k], "stub"))
    return object()


def test_the_proxy_reaches_MG_and_only_MG(monkeypatch):
    ctx = _ctx(monkeypatch)
    pool = _pool()
    before = ev_mod.build_pack(ctx, pool=pool)
    after = ev_mod.build_pack(ctx, pool=pool, proxy=_proxy())

    assert before["sha1"]["SG"] == after["sha1"]["SG"]
    assert before["sha1"]["BQ"] == after["sha1"]["BQ"]
    assert before["sha1"]["MG"] != after["sha1"]["MG"]
    assert "chief executive officer since 2011" in after["components"]["MG"]
    assert "chief executive officer since 2011" not in after["components"]["SG"]


def test_a_missing_proxy_says_so_rather_than_going_quiet(monkeypatch):
    """A company with no DEF 14A must produce a pack that TELLS the model the proxy is
    absent. Silence there reads as 'no evidence of founder status', which is a different
    claim from 'the document was not available'."""
    ctx = _ctx(monkeypatch)
    empty = {"chunks": [], "vectors": [], "proxy": {"error": "no DEF 14A"}}
    pack = ev_mod.build_pack(ctx, pool=_pool(), proxy=empty)
    assert "PROXY STATEMENT: unavailable" in pack["components"]["MG"]
    assert "no DEF 14A" in pack["components"]["MG"]


def test_no_proxy_argument_leaves_the_pack_exactly_as_it_was(monkeypatch):
    """The daily crawl must be able to keep calling build_pack unchanged."""
    ctx = _ctx(monkeypatch)
    a = ev_mod.build_pack(ctx, pool=_pool())
    b = ev_mod.build_pack(ctx, pool=_pool(), proxy=None)
    assert a["sha1"] == b["sha1"]
