"""State builder behind a TTL memo, plus an LRU scorecard reader.

Missing, corrupt or stale artifacts return a neutral payload and HTTP 200 - never
a 5xx. A dashboard that 500s because a crawl is mid-write is a dashboard you stop
trusting, and the crawl writes atomically anyway.

The 500-row table payload comes from data/scores.parquet only. Full scorecards are
~40 KB each and are loaded per company on demand: putting 500 of them in one
response would be a 20 MB payload on a phone.
"""
from __future__ import annotations

import time
from functools import lru_cache

from .. import config
from ..net import read_json
from ..scoring import rubric

_CACHE: dict = {"at": 0.0, "state": None}


def _neutral(reason: str) -> dict:
    return {
        "ok": False,
        "reason": reason,
        "advisory": config.ADVISORY_BANNER,
        "rows": [],
        "n": 0,
        "flag": {},
        "sectors": [],
        "bands": [],
        "components": [
            {"code": c, "label": rubric.COMPONENTS[c][0],
             "max": rubric.COMPONENTS[c][1],
             "is_llm": c in rubric.JUDGED_COMPONENTS}
            for c in rubric.COMPONENT_ORDER
        ],
    }


def _load_rows() -> tuple[list[dict], str | None]:
    p = config.SCORES_PARQUET
    if not p.exists():
        return [], f"{p.name} does not exist yet - run clab.runner.batch"
    try:
        import pandas as pd

        df = pd.read_parquet(p)
    except Exception as exc:  # noqa: BLE001
        return [], f"could not read {p.name}: {type(exc).__name__}"
    if df.empty:
        return [], "scores table is empty"
    df = df.where(df.notna(), None)
    return df.to_dict(orient="records"), None


def build_state() -> dict:
    rows, err = _load_rows()
    flag = read_json(config.STATE_FLAG) or {}
    if err:
        st = _neutral(err)
        st["flag"] = flag
        return st

    def _sort_key(r):
        v = r.get("composite_strict")
        return -(v if isinstance(v, (int, float)) else -1)

    rows = sorted(rows, key=_sort_key)
    sectors = sorted({(r.get("sector") or "").strip() for r in rows if r.get("sector")})
    bands = [b for _, b in rubric.BANDS] + [rubric.INSUFFICIENT_BAND]
    cov = [r.get("coverage") for r in rows if isinstance(r.get("coverage"), (int, float))]
    n_qual = sum(1 for r in rows if r.get("qual_available"))

    return {
        "ok": True,
        "advisory": config.ADVISORY_BANNER,
        "rows": rows,
        "n": len(rows),
        "flag": flag,
        "sectors": sectors,
        "bands": bands,
        "components": [
            {"code": c, "label": rubric.COMPONENTS[c][0],
             "max": rubric.COMPONENTS[c][1],
             "is_llm": c in rubric.JUDGED_COMPONENTS}
            for c in rubric.COMPONENT_ORDER
        ],
        "summary": {
            "companies": len(rows),
            "median_coverage": (sorted(cov)[len(cov) // 2] if cov else None),
            "with_llm_qualitative": n_qual,
            "without_llm_qualitative": len(rows) - n_qual,
            "data_through": flag.get("data_through"),
            "as_of": flag.get("as_of"),
            "min_coverage_for_band": rubric.MIN_COVERAGE_FOR_BAND,
        },
    }


def cached_state(*, bust: bool = False) -> dict:
    now = time.time()
    if bust or _CACHE["state"] is None or (now - _CACHE["at"]) > config.UI_STATE_TTL_SECONDS:
        _CACHE["state"] = build_state()
        _CACHE["at"] = now
    return _CACHE["state"]


@lru_cache(maxsize=config.UI_SCORECARD_LRU)
def _scorecard_cached(path: str, mtime: float) -> dict | None:
    """mtime is part of the key, so an updated scorecard invalidates itself."""
    return read_json(path)


def scorecard_for(ticker: str) -> dict | None:
    ticker = (ticker or "").upper()
    hits = sorted(config.SCORECARD_DIR.glob(f"*_{ticker}.json"))
    if not hits:
        return None
    p = hits[-1]
    try:
        mt = p.stat().st_mtime
    except OSError:
        return None
    return _scorecard_cached(str(p), mt)


def thesis_for(ticker: str) -> dict | None:
    card = scorecard_for(ticker)
    if not card:
        return None
    return read_json(config.THESIS_DIR / f"{card.get('cik')}.json")


def all_rows() -> list[dict]:
    return cached_state().get("rows") or []
