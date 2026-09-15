"""E22 - score the judgement half as it WOULD have been read a year and two years ago.

Registered in `journal/experiments/E22_judgement_half_backtest_preregistration.md`.

`panel.py` excludes the LLM half by construction, so half of `composite_strict` has never
been in any backtest. This rebuilds the evidence pack a past reader would have had - the
10-K current at that date, and the fundamentals as first filed - and runs the production
SG / BQ / MG scorers against it.

Scope is the last two annual filings, not a decade. What that can answer is a STABILITY
question (does a component say the same thing about an unchanged business a year later?)
and, far more weakly, a direction question. The registration is explicit that two
cross-sections cannot carry a return claim, and no Deflated Sharpe is computed here.

    python -m clab.research.e22_judgement_backtest --probe 10
    python -m clab.research.e22_judgement_backtest --n 400
    python -m clab.research.e22_judgement_backtest --report
"""
from __future__ import annotations

import argparse
import json
import statistics
import time

from .. import config
from ..fundamentals import metrics as mx
from ..fundamentals import profile as pf
from ..net import log_stamp, read_json, utc_now_iso
from ..qual import evidence as ev_mod
from ..qual import ollama, prompts
from ..qual.scorer import PARSERS
from ..research.panel import payload_asof
from ..scoring import rubric
from ..scoring.context import SymbolContext
from ..sources import edgar_filings
from ..sources.edgar_facts import resolve_facts

RAW_DIR = config.JOURNAL_DIR / "experiments" / "E22_raw"
SEED = 1337
#: the two historical readings, as dates to look back from
LOOKBACKS = ("t_minus_2", "t_minus_1")



#: Windows reserves these as device names. A file called `CON.json` can be created by
#: some APIs and then cannot be opened by anything that resolves the path normally - git
#: reported `open("journal/experiments/E22_raw/CON.json"): No such file or directory` for
#: a file that was sitting right there, and refused to stage the whole tree because of it.
#: Ticker CON is a real S&P constituent, so this is not hypothetical.
_WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *{f"COM{i}" for i in range(1, 10)},
    *{f"LPT{i}" for i in range(1, 10)},
}


def safe_stem(ticker: str) -> str:
    """A ticker made safe to use as a filename on Windows."""
    t = str(ticker)
    return f"{t}_ticker" if t.upper() in _WINDOWS_RESERVED else t

def log(msg: str) -> None:
    print(f"[{log_stamp()}] {msg}", flush=True)


def _asof_dates() -> dict[str, str]:
    """Two anniversaries back from today, as ISO dates."""
    import datetime as dt

    today = dt.date.today()
    return {"t_minus_2": (today.replace(year=today.year - 2)).isoformat(),
            "t_minus_1": (today.replace(year=today.year - 1)).isoformat()}


def sample(n: int) -> list[dict]:
    """Stratified across sectors AND measured-half deciles.

    Drawing at random would over-weight whatever the measured half already likes, and the
    whole question is whether the judgement half says something different.
    """
    import pandas as pd
    df = pd.read_parquet(config.SCORES_PARQUET)
    df = df[df["ticker"].notna() & df["quant_normalized"].notna()].copy()
    df["cik"] = df["cik"].astype(str).str.zfill(10)
    df["decile"] = pd.qcut(df["quant_normalized"], 10, labels=False, duplicates="drop")
    rows = []
    groups = list(df.groupby(["sector", "decile"], observed=True))
    per = max(1, round(n / max(len(groups), 1)))
    for _key, grp in groups:
        rows += grp.sample(min(per, len(grp)), random_state=SEED).to_dict("records")
    rows.sort(key=lambda r: str(r["ticker"]))
    return [{"ticker": r["ticker"], "cik": r["cik"], "name": r.get("name", ""),
             "sector": r.get("sector", ""), "sub_industry": r.get("sub_industry", ""),
             "decile": int(r["decile"]) if r.get("decile") == r.get("decile") else None}
            for r in rows[:n]]


def context_asof(row: dict, as_of: str):
    """The company as it could have been read on `as_of`.

    Fundamentals use the `as_first_filed` view through `panel.payload_asof`, so a
    restatement published later cannot leak in; the filing is the 10-K current at that
    date. Market data is deliberately absent - the judgement components do not read it,
    and fabricating a historical price would add error for no gain.
    """
    facts_res, cik_used, _note = resolve_facts(row["cik"])
    payload = facts_res.payload if isinstance(facts_res.payload, dict) else {}
    if not payload.get("facts"):
        return None, {"error": "no companyfacts"}
    sub_payload = payload_asof(payload, as_of)
    prof = pf.profile_for("", row.get("sector", ""), row.get("sub_industry", ""))
    M = mx.build_metrics(sub_payload, profile=prof, view="as_first_filed")
    ctx = SymbolContext(
        ticker=row["ticker"], cik=cik_used, name=row.get("name", ""), as_of=as_of,
        sector=row.get("sector", ""), sub_industry=row.get("sub_industry", ""),
        profile=prof, metrics=M, market={}, prices={}, peers={}, qual={})
    return ctx, {"cik_used": cik_used}


def score_asof(row: dict, as_of: str, *, components=None,
               use_proxy: bool = False) -> dict:
    """Build the pack as of a date and run the judgement components on it.

    `use_proxy` adds the DEF 14A current at that date to MG's pack - E24's change. It
    reaches MG only, so SG's and BQ's readings stay comparable with the E22 baseline.
    """
    codes = tuple(components or rubric.GENERATED_COMPONENTS)
    t0 = time.perf_counter()
    ctx, meta = context_asof(row, as_of)
    if ctx is None:
        return {"as_of": as_of, "error": meta.get("error")}
    text, fmeta = edgar_filings.filing_text(ctx.cik, as_of=as_of)
    if not text:
        return {"as_of": as_of, "error": fmeta.get("error", "no filing text")}
    # `chunk_pool` always fetches the LATEST filing, which is precisely what a
    # point-in-time reading must not use, so the pool is built from the text of the
    # filing that was current on `as_of`.
    pool = _pool_from_text(ctx, text, fmeta)
    proxy = ev_mod.proxy_pool(ctx, as_of=as_of) if use_proxy else None
    pack = ev_mod.build_pack(ctx, pool=pool, proxy=proxy)
    t_pack = time.perf_counter() - t0

    out = {"as_of": as_of, "filing": {k: fmeta.get(k) for k in
                                      ("accn", "form", "filed", "chars")},
           "pack_secs": round(t_pack, 1), "components": {}}
    if proxy is not None:
        out["proxy"] = {k: (proxy.get("proxy") or {}).get(k)
                        for k in ("accn", "form", "filed", "error", "n_chunks")}
    for code in codes:
        body = pack["components"][code]
        t1 = time.perf_counter()
        raw = ollama.chat(prompts.prompt_for(code, body), system=prompts.SYSTEM,
                          timeout=900.0)
        parsed = PARSERS[code](raw, body)
        out["components"][code] = {
            "secs": round(time.perf_counter() - t1, 1),
            "parse_ok": bool(parsed.get("parse_ok")),
            "scores": _flatten(code, parsed),
        }
    out["total_secs"] = round(time.perf_counter() - t0, 1)
    return out


def _pool_from_text(ctx, text: str, fmeta: dict) -> dict:
    """A chunk pool built from a SPECIFIC filing's text rather than today's.

    Mirrors `evidence.chunk_pool`'s sectioning and round-robin cap so the only difference
    between a historical pack and a live one is which document it came from.
    """
    sections = edgar_filings.slice_sections(text)
    per_section: dict[str, list[str]] = {}
    for name in ("business", "risk_factors", "mdna"):
        body = sections.get(name)
        if body:
            per_section[name] = [f"[{name}] {c[:ev_mod.MAX_CHUNK_CHARS]}"
                                 for c in edgar_filings.chunk_text(body[:400_000])]
    whole_doc = False
    if not per_section and text:
        whole_doc = True
        per_section["_whole_document"] = [
            f"[filing] {c[:ev_mod.MAX_CHUNK_CHARS]}"
            for c in edgar_filings.chunk_text(text[:600_000]) if ev_mod._is_prose(c)]
    chunks: list[str] = []
    if per_section:
        share = max(ev_mod.MAX_CHUNKS_TOTAL // len(per_section), 1)
        for cs in per_section.values():
            chunks.extend(cs[:share])
    return {"chunks": chunks, "vectors": ev_mod.embed_chunks(chunks),
            "filing": fmeta, "per_section": per_section, "sections": sections,
            "whole_document_fallback": whole_doc,
            "n_chunks_before_cap": sum(len(v) for v in per_section.values())}


def _flatten(code: str, parsed: dict) -> dict:
    bucket = {"SG": "scores", "BQ": "dimensions", "MG": "ceo"}[code]
    return {k: v.get("score") for k, v in (parsed.get(bucket) or {}).items()
            if isinstance(v, dict)}


def run_one(row: dict, *, components=None, use_proxy: bool = False) -> dict:
    dates = _asof_dates()
    rec = {"ticker": row["ticker"], "cik": row["cik"], "sector": row.get("sector", ""),
           "decile": row.get("decile"), "readings": {}}
    for label in LOOKBACKS:
        try:
            rec["readings"][label] = score_asof(row, dates[label],
                                                components=components,
                                                use_proxy=use_proxy)
        except Exception as exc:                        # noqa: BLE001
            rec["readings"][label] = {"as_of": dates[label],
                                      "error": f"{type(exc).__name__}: {exc}"}
    return rec


def run(n: int, *, resume: bool = True, components=None, use_proxy: bool = False,
        raw_dir=None) -> list[dict]:
    raw_dir = raw_dir or RAW_DIR
    raw_dir.mkdir(parents=True, exist_ok=True)
    rows = sample(n)
    log(f"{len(rows)} companies, {len(LOOKBACKS)} historical readings each "
        f"({_asof_dates()})")
    ok, why = ollama.available()
    if not ok:
        log(f"ollama is not usable: {why}")
        return []
    out = []
    with ollama.gpu_lease(wait=True):
        for i, row in enumerate(rows, 1):
            path = raw_dir / f"{safe_stem(row['ticker'])}.json"
            if resume and path.exists():
                out.append(json.loads(path.read_text(encoding="utf-8")))
                continue
            rec = run_one(row, components=components, use_proxy=use_proxy)
            path.write_text(json.dumps(rec, indent=2), encoding="utf-8")
            out.append(rec)
            secs = sum(r.get("total_secs", 0) for r in rec["readings"].values())
            errs = [lbl for lbl, r in rec["readings"].items() if r.get("error")]
            log(f"  {rec['ticker']:<6} {secs:>5.0f}s"
                + (f"  ERRORS {errs}" if errs else "")
                + f"  ({i}/{len(rows)})")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--probe", type=int, default=0,
                    help="time this many companies and stop, before committing GPU")
    ap.add_argument("--no-resume", action="store_true")
    ap.add_argument("--components", default="",
                    help="comma-separated subset, e.g. MG for the E24 re-measure")
    ap.add_argument("--proxy", action="store_true",
                    help="E24: put the DEF 14A current at each date into MG's pack")
    ap.add_argument("--tag", default="",
                    help="write to E22_raw_<tag>/ so a re-measure never overwrites the "
                         "baseline it is compared against")
    args = ap.parse_args(argv)

    components = tuple(c.strip().upper() for c in args.components.split(",")
                       if c.strip()) or None
    raw_dir = (RAW_DIR.with_name(RAW_DIR.name + "_" + args.tag) if args.tag
               else RAW_DIR)

    if args.probe:
        recs = run(args.probe, resume=not args.no_resume, components=components,
                   use_proxy=args.proxy, raw_dir=raw_dir)
        per = [sum(r.get("total_secs", 0) for r in rec["readings"].values())
               for rec in recs]
        errs = sum(1 for rec in recs for r in rec["readings"].values() if r.get("error"))
        med = statistics.median(per) if per else 0
        summary = {
            "probe_companies": len(recs), "readings_failed": errs,
            "median_secs_per_company": round(med, 1),
            "projected_hours_for_400": round(med * 400 / 3600, 1),
            "projected_hours_for_200": round(med * 200 / 3600, 1),
            "as_of": utc_now_iso(),
        }
        path = config.JOURNAL_DIR / "experiments" / "E22_probe.json"
        path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary, indent=2))
        log("probe only - no long run started. Size the sample from these numbers.")
        return 0

    recs = run(args.n, resume=not args.no_resume, components=components,
               use_proxy=args.proxy, raw_dir=raw_dir)
    log(f"{len(recs)} companies scored; analysis is a separate step")
    return 0 if recs else 1


if __name__ == "__main__":
    raise SystemExit(main())
