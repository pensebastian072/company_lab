"""Build the frozen research request Codex answers against.

Same contract the options desk has used with Codex since July, and for the same reason:
a content-hashed `request_id`, an explicit `read_only`, a `steps` list naming the only
work being asked for, and a **frozen roster**. `finalize.py` then refuses anything that
does not match. The invariant, from `options_desk/CLAUDE.md`, is that Codex does not
apply the gates - the finalizer does.

## Why the request is written as TWO files

`external_research_request.json` carries the blind half: identity, the measured
metrics, and the VERBATIM filing evidence the local model scored from.

`external_research_conclusions.json` carries what the local model actually concluded -
SG and BQ points, the per-dimension rationales, the BQ killer answer.

Telling a researcher "this field is in the payload, do not read it until pass B" is an
honour system, and anchoring on the incumbent's answer is precisely what the blind pass
exists to measure.

## Two files was not enough, and E53 proved it

Until E53 both files were written at stage time. The conclusions therefore sat on disk,
at a documented path, for the entire duration of the blind pass - and on E53 they were
opened during routine inventory and the breach was reported honestly.

**That is a design defect, not a protocol failure. A blind anyone can lift by opening a
file is not a blind.** Splitting the payload in two only moves the honour system; it does
not remove it.

So the conclusions are now WITHHELD: `write()` stashes them under `EXTERNAL_ROOT/withheld/`
and deletes any stale release, and `release_conclusions()` writes the real file only once
a FROZEN pass A exists on disk. It records that pass A's sha256 in the released file,
which is what turns "reconciliation did not alter pass A" from something reported into
something checkable - compare the hash against the pass A inside the final payload.

The split is also the reason `filing_half` carries `evidence` and not `rationale`.
Evidence is verbatim text out of the 10-K - what the company said. A rationale is the
local model's opinion about that text, and putting an opinion in the blind pass would
leak the very thing being withheld.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .. import config, net
from ..scoring import rubric
from . import taxonomy
from .schema import EXTERNAL_SCHEMA_VERSION

#: Bumped when the roster's SHAPE changes. Travels into `spec_fingerprint` so a payload
#: built against an older shape is visible rather than silently mis-parsed.
REQUEST_SPEC_VERSION = "1.0.0"

#: The measured fields a sector specialist actually needs to argue with. Not the whole
#: 135-column row: a roster that dumps every metric buys tokens, not judgement.
MEASURED_FIELDS = (
    "revenue_ttm", "revenue_cagr_3y", "gross_margin", "operating_margin", "fcf_margin",
    "roic", "roe", "net_debt_ebitda", "interest_coverage", "stress_verdict",
    "market_cap", "pe", "fwd_pe", "ev_ebitda", "p_fcf", "drawdown_from_ath",
    "analyst_growth_3y",
)

#: The only tool calls this request authorises. Mirrors the options desk's `steps`.
STEPS = (
    "read the sector brief at research/sectors/<sector_id>/sector_state.json",
    "read the industry object at research/industries/<industry_id>/industry_state.json",
    "hypothesis-driven external search per company (never 'latest COMPANY news')",
    "read competitor filings, earnings calls and investor presentations",
    "write pass A blind, then request the conclusions file and write pass B",
    "write the payload to external/payloads/<request_id>.json",
)


def _scorecard_path(cik: str, ticker: str) -> Path:
    hits = sorted(config.SCORECARD_DIR.glob(f"{cik}_*.json"))
    for h in hits:
        if h.stem.endswith(f"_{ticker}"):
            return h
    return hits[0] if hits else Path()


def _filing_evidence(card: dict) -> dict:
    """Verbatim 10-K text the local model scored from - never its rationales.

    `evidence_unverified` rows are dropped. E40 measured LFM2.5 citing text absent from
    the filing 9.7% of the time; handing an unverified quote to an external researcher
    as "what the company said" would launder that straight into the external layer.
    """
    out: dict[str, list[str]] = {}
    for code in rubric.GENERATED_COMPONENTS:
        comp = (card.get("components") or {}).get(code) or {}
        quotes = []
        for st in comp.get("subtests") or []:
            ev = st.get("evidence")
            if ev and not st.get("evidence_unverified"):
                quotes.append(f"[{st.get('key')}] {ev}")
        if quotes:
            out[code] = quotes
    return out


def _local_conclusions(card: dict) -> dict:
    """Pass B only. What the incumbent concluded, and why."""
    comps = card.get("components") or {}
    out: dict = {}
    for code in ("SG", "BQ"):
        c = comps.get(code) or {}
        out[code.lower()] = c.get("earned_points")
        out[f"{code.lower()}_max"] = c.get("max_points")
        out[f"{code.lower()}_available"] = c.get("available_points")
        out[f"{code.lower()}_rationales"] = {
            st.get("key"): st.get("rationale")
            for st in c.get("subtests") or [] if st.get("rationale")}
    out["bq_killer_answer"] = (comps.get("BQ") or {}).get("note")
    return out


def build_roster(tickers: list[str], *, store=None) -> tuple[list[dict], list[dict]]:
    """(blind roster, conclusions) for the named tickers, from the live book."""
    import pandas as pd
    from .store import ExternalStore

    df = pd.read_parquet(config.SCORES_PARQUET)
    want = [t.strip().upper() for t in tickers]
    rows = df[df["ticker"].isin(want)]
    found = set(rows["ticker"])
    missing = [t for t in want if t not in found]
    if missing:
        raise SystemExit(f"not in the book: {missing}")

    st = store or ExternalStore(config.EXTERNAL_DB)
    roster, conclusions = [], []
    blocked: dict[str, list[str]] = {}
    active_objects: dict[str, bool] = {}
    for _, r in rows.iterrows():
        ticker, cik = str(r["ticker"]), str(r["cik"])
        card_path = _scorecard_path(cik, ticker)
        card = json.loads(card_path.read_text(encoding="utf-8")) if card_path.name else {}
        ids = taxonomy.resolve(ticker, r.get("sector"), r.get("sub_industry"))
        iid = ids.get("industry_id")
        if iid and iid not in active_objects:
            active_objects[iid] = st.industry(iid) is not None
        if not iid or not active_objects.get(iid, False):
            blocked.setdefault(str(iid or "<missing>"), []).append(ticker)

        measured = {}
        for f in MEASURED_FIELDS:
            v = r.get(f)
            if v is None:
                continue
            # NaN is not a measurement. It also passes isinstance(v, float), which is
            # how this repo has been bitten before.
            if isinstance(v, float) and v != v:
                continue
            measured[f] = float(v) if isinstance(v, (int, float)) else str(v)

        roster.append({
            "ticker": ticker, "cik": cik, "name": str(r.get("name") or ""),
            "sector": str(r.get("sector") or ""),
            "sub_industry": str(r.get("sub_industry") or ""),
            **ids,
            "data_through": str(r.get("data_through") or ""),
            "measured": measured,
            "filing_evidence": _filing_evidence(card),
        })
        conclusions.append({"ticker": ticker, **_local_conclusions(card)})
    if blocked:
        detail = "; ".join(
            f"{iid}: {','.join(sorted(names))}" for iid, names in sorted(blocked.items()))
        raise SystemExit(
            "no active industry object for requested companies; Phase A must land and "
            f"verify before Phase B: {detail}")
    roster.sort(key=lambda x: x["ticker"])
    conclusions.sort(key=lambda x: x["ticker"])
    return roster, conclusions


def build_request(tickers: list[str], *, depth: int = 3,
                  sample: str | None = None,
                  require_citation: bool = False,
                  store=None) -> tuple[dict, dict]:
    roster, conclusions = build_roster(tickers, store=store)

    # The id is a hash of the CONTENT, so a roster edited after the fact produces a
    # different id and the finalizer rejects the payload built against the old one.
    # `sample` is in the seed on purpose. Two runs over the same roster under different
    # research rules are two different requests, and they must get different ids or
    # they collide in the manifest and overwrite each other's company records - which
    # would destroy the arm being compared against.
    seed = {"roster": roster, "depth": depth, "spec": REQUEST_SPEC_VERSION,
            "schema": EXTERNAL_SCHEMA_VERSION, "sample": sample}
    blob = json.dumps(seed, sort_keys=True, ensure_ascii=True)
    request_id = hashlib.sha256(blob.encode("utf-8")).hexdigest()[:20]
    roster_sha1 = net.sha1_text(json.dumps(roster, sort_keys=True, ensure_ascii=True))
    spec_fingerprint = net.sha1_text(
        f"{REQUEST_SPEC_VERSION}|{EXTERNAL_SCHEMA_VERSION}|{'|'.join(STEPS)}")[:16]

    request = {
        "request_id": request_id,
        "spec_fingerprint": spec_fingerprint,
        "roster_sha1": roster_sha1,
        "generated_at": net.utc_now_iso(),
        "status": "READY",
        "read_only": True,
        "depth": depth,
        "sample": sample,
        #: When true, the finalizer DEMOTES any non-UNKNOWN categorical that no claim
        #: cites to UNKNOWN. Measured on the first pilot: 39 categoricals asserted, 14
        #: claims, only 10 of 36 non-UNKNOWN assertions backed by a claim naming that
        #: field. Asking for citations without enforcing them is how the schema gap
        #: happened.
        "require_citation": bool(require_citation),
        "external_schema_version": EXTERNAL_SCHEMA_VERSION,
        "request_spec_version": REQUEST_SPEC_VERSION,
        "base_book": str(config.SCORES_PARQUET),
        "local_llm_model": config.QUAL_MODEL,
        "pass": "A",
        "note": ("Blind pass. This file deliberately omits what the local model "
                 "concluded; ask for the conclusions file after pass A is written."),
        "steps": list(STEPS),
        "roster": roster,
    }
    conclusions_file = {
        "request_id": request_id,
        "spec_fingerprint": spec_fingerprint,
        "generated_at": request["generated_at"],
        "pass": "B",
        "note": "Release only after pass A is written and frozen.",
        "conclusions": conclusions,
    }
    return request, conclusions_file


def write(request: dict, conclusions: dict) -> tuple[Path, Path | None]:
    """Stage pass A. The conclusions file is DELIBERATELY NOT WRITTEN.

    Until E53 this wrote both files at stage time, which meant the pass-B conclusions -
    our local model's SG/BQ - sat on disk, at a documented path, for the entire duration
    of the blind pass. Blindness was enforced by asking the researcher not to look.

    On E53 it was looked at, during routine inventory, and reported honestly. That is a
    design defect, not a protocol failure: a blind that anyone can lift by opening a file
    is not a blind. The conclusions are now withheld until `release_conclusions()` is
    called, which requires a frozen pass A to exist first.
    """
    net.atomic_write_json(config.EXTERNAL_REQUEST, request)
    _stash_conclusions(conclusions)
    if config.EXTERNAL_CONCLUSIONS.exists():
        # A stale release from a previous request must not stand in for this one.
        config.EXTERNAL_CONCLUSIONS.unlink()
    return config.EXTERNAL_REQUEST, None


def _stash_path(request_id: str) -> Path:
    """Where the withheld conclusions wait. Under EXTERNAL_ROOT on D:, not in
    journal/flags, so it is not somewhere a researcher inventories by habit."""
    return config.EXTERNAL_ROOT / "withheld" / f"{request_id}.conclusions.json"


def _stash_conclusions(conclusions: dict) -> Path:
    path = _stash_path(conclusions["request_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    net.atomic_write_json(path, conclusions)
    return path


def release_conclusions(request_id: str, pass_a_path: str | Path) -> dict:
    """Release pass B's conclusions, once a frozen pass A is on disk.

    Records the sha256 of the frozen pass A at release time. That hash is what makes
    "reconciliation did not alter pass A" checkable rather than merely reported - compare
    it against the pass A inside the final payload and the two must match.
    """
    pass_a = Path(pass_a_path)
    if not pass_a.exists():
        raise FileNotFoundError(
            f"pass A must be frozen before conclusions are released; {pass_a} not found")
    stash = _stash_path(request_id)
    if not stash.exists():
        raise FileNotFoundError(
            f"no withheld conclusions for request {request_id} at {stash}")

    digest = hashlib.sha256(pass_a.read_bytes()).hexdigest()
    conclusions = json.loads(stash.read_text(encoding="utf-8"))
    conclusions["released_at"] = net.utc_now_iso()
    conclusions["pass_a_sha256"] = digest
    conclusions["pass_a_path"] = str(pass_a)
    net.atomic_write_json(config.EXTERNAL_CONCLUSIONS, conclusions)
    return {"request_id": request_id, "pass_a_sha256": digest,
            "released_to": str(config.EXTERNAL_CONCLUSIONS)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build the external research request")
    ap.add_argument("--symbols", default=None,
                    help="comma-separated tickers, e.g. FICO,VRT,NVDA")
    ap.add_argument("--depth", type=int, default=3, choices=range(0, 5))
    ap.add_argument("--sample", default=None, help="label, e.g. E42-pilot")
    ap.add_argument("--require-citation", action="store_true",
                    help="finalizer demotes any uncited non-UNKNOWN categorical")
    ap.add_argument("--release", metavar="REQUEST_ID", default=None,
                    help="release the withheld pass-B conclusions for this request")
    ap.add_argument("--pass-a", default=None,
                    help="path to the FROZEN pass A, required with --release")
    args = ap.parse_args(argv)

    if args.release:
        if not args.pass_a:
            ap.error("--release requires --pass-a pointing at the frozen pass A")
        out = release_conclusions(args.release, args.pass_a)
        print(f"released      {out['released_to']}")
        print(f"pass_a_sha256 {out['pass_a_sha256']}")
        print("\nThat hash is recorded in the conclusions file. Compare it against the "
              "pass A inside\nthe final payload; if they differ, pass A was rewritten "
              "after the reveal.")
        return 0

    if not args.symbols:
        ap.error("--symbols is required unless --release is used")

    request, conclusions = build_request(
        [t for t in args.symbols.split(",") if t.strip()],
        depth=args.depth, sample=args.sample,
        require_citation=args.require_citation)
    a, b = write(request, conclusions)

    from .store import ExternalStore
    ExternalStore().begin(request, base_book=request["base_book"],
                          local_llm_model=request["local_llm_model"])

    print(f"request_id      {request['request_id']}")
    print(f"spec_fingerprint {request['spec_fingerprint']}")
    print(f"roster          {len(request['roster'])} companies, depth {request['depth']}")
    for row in request["roster"]:
        ev = sum(len(v) for v in row["filing_evidence"].values())
        print(f"  {row['ticker']:<6} {row['sector_id'] or '?':<24} "
              f"{row['industry_id'] or '?':<26} measured {len(row['measured'])} "
              f"filing quotes {ev}")
    print(f"\npass A (blind)  {a}")
    print("pass B          WITHHELD - not written to disk")
    print(f"                stashed at {_stash_path(request['request_id'])}")
    print("\nHand over pass A. When the researcher reports pass A FROZEN, release with:")
    print(f"  -m clab.external.request --release {request['request_id']} "
          f"--pass-a <frozen pass_a.json>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
