"""The gate. Codex does not apply the gates - this does.

Ported straight from `options_desk/desk/etf_options.py::finalize_payload`, which has
been running this contract with Codex since July. Four guards fire before a single
returned field is trusted:

    1. `request_id` matches the frozen request
    2. the request was generated on TODAY's NY session date
    3. the request's `status` is READY
    4. every returned ticker exists in the frozen roster

Then the schema layer: closed vocabularies, text caps, depth range, and per-claim
structural checks. Anything that fails lands in `rejected` WITH A REASON. Nothing is
silently dropped - a payload that half-arrives must say which half and why, or the
next run cannot tell a research gap from a parsing accident.

## Two things this refuses on principle

**A score.** Codex returns categoricals and cited claims. If a payload carries
`external_score`, `rank`, `rating` or a point total, that field is rejected and
recorded, because a number we did not compute is a number we cannot audit.

**A verification.** `verify_status` arriving in a payload is discarded, not read.
Every accepted claim enters SELF_ATTESTED and only `verify.py` can promote it, having
fetched the page from this side.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .. import config, net
from . import schema as S
from .research_ingest import _sha1, to_claim, validate_claim
from .schema import EXTERNAL_SCHEMA_VERSION

NY = ZoneInfo("America/New_York")

#: Fields Codex may return per company. Anything else is reported, not stored.
#: COMPANY_ORDINALS, not ORDINAL_FIELDS: the latter also holds the three industry-object
#: vocabularies, and accepting `replication_difficulty` on a company record would store
#: an industry fact in a company row.
#: ALL, not just the scored set: a retired field may still be supplied and stored, it
#: simply earns nothing and is not counted in coverage. Rejecting it would break every
#: payload built against the previous prompt.
ALLOWED_CATEGORICALS = tuple(S.COMPANY_ORDINALS_ALL)
ALLOWED_TEXTS = tuple(S.TEXT_LIMITS)

#: Fields that are OURS to compute. Their presence in a payload is a contract breach.
FORBIDDEN_FIELDS = ("external_score", "external_confidence", "rank", "rating",
                    "score", "sector_rank", "industry_rank", "points",
                    "high_conviction", "recommendation", "price_target")


class Rejected(RuntimeError):
    """The whole payload is refused. Distinct from a per-company rejection."""


def _ny_date(stamp: str | None) -> str | None:
    if not stamp:
        return None
    try:
        dt = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(NY).date().isoformat()


def check_request(request: dict, payload: dict, *, now: datetime | None = None) -> None:
    """The four guards. Raises Rejected, which refuses the payload entire."""
    now = now or datetime.now(timezone.utc)
    if not request:
        raise Rejected("no frozen request on disk; nothing to validate against")

    if payload.get("request_id") != request.get("request_id"):
        raise Rejected(
            f"request_id mismatch: payload {payload.get('request_id')!r} vs frozen "
            f"{request.get('request_id')!r}")

    # Staleness is not the same question as "did this run today". An age window said
    # yes to a 21.6h-old signal on the options desk and the desk published a request
    # built on the previous session. Check the session DATE.
    today = now.astimezone(NY).date().isoformat()
    made = _ny_date(request.get("generated_at"))
    if made != today:
        raise Rejected(f"frozen request is dated {made}, not today ({today}). "
                       f"Rebuild it before finalizing.")

    if request.get("status") != "READY":
        raise Rejected(f"request status is {request.get('status')!r}, not READY")

    if payload.get("spec_fingerprint") and \
            payload["spec_fingerprint"] != request.get("spec_fingerprint"):
        raise Rejected("spec_fingerprint mismatch: the payload was built against a "
                       "different request shape")


def apply_citation_rule(cats: dict, claims: list[dict]) -> tuple[dict, list[str]]:
    """Demote any non-UNKNOWN categorical that no claim cites, to UNKNOWN.

    Measured on the first pilot: 39 categoricals asserted across three companies
    against 14 claims, and only 10 of the 36 non-UNKNOWN assertions had a claim naming
    that field. FICO's `current_moat_strength: STRONG`, NVDA's `moat_trajectory:
    STABLE` and VRT's `competitive_position_trend: IMPROVING` all arrived with no
    evidence attached. That is E39's shape in a new place - 271 companies' moat scores
    existed only because unexplained dimensions made the quorum.

    DEMOTED, not rejected. Rejecting the company would throw away the cited fields
    alongside the uncited ones, and the cited fields are the good part. Demotion is
    also not a punishment: UNKNOWN is a real value that scores as NO_DATA, so an
    uncited assertion simply stops counting - which is the same rule the framework
    already applies to a sub-test that was never scored.

    Asking for citations in the prompt and not enforcing them here is exactly how the
    schema gap happened: a contract stated in prose that the code did not hold.
    """
    cited = {c.get("field") for c in claims}
    demoted: list[str] = []
    out = dict(cats)
    for field, value in cats.items():
        if value == S.UNKNOWN or field not in S.COMPANY_ORDINALS:
            continue
        if field not in cited:
            out[field] = S.UNKNOWN
            demoted.append(field)
    return out, sorted(demoted)


def finalize_company(row: dict, roster: dict[str, dict],
                     require_citation: bool = False) -> tuple[dict | None, list[str]]:
    """(record, reasons). A record of None means this company was rejected."""
    reasons: list[str] = []
    ticker = str(row.get("ticker") or "").upper()
    if ticker not in roster:
        return None, [f"{ticker!r} is not in the frozen roster"]

    for bad in FORBIDDEN_FIELDS:
        if bad in row or bad in (row.get("pass_a") or {}):
            reasons.append(f"payload carries {bad!r}; that field is computed locally "
                           f"and may not be supplied")

    pass_a = row.get("pass_a") or {}
    if not pass_a:
        reasons.append("no pass_a block - the blind pass is the point of the design")

    cats = {k: v for k, v in pass_a.items() if k in ALLOWED_CATEGORICALS}
    texts = {k: v for k, v in pass_a.items() if k in ALLOWED_TEXTS}
    unknown = [k for k in pass_a
               if k not in ALLOWED_CATEGORICALS and k not in ALLOWED_TEXTS
               and k not in ("key_monitoring_variables",)]
    if unknown:
        reasons.append(f"unrecognised pass_a fields: {sorted(unknown)}")

    reasons += S.validate_categoricals(cats)
    reasons += S.validate_texts(texts)
    reasons += S.validate_depth(row.get("research_depth"))

    claims, claim_reasons = [], []
    seen: set[str] = set()
    for raw in row.get("claims") or []:
        r = validate_claim(raw)
        cid = raw.get("claim_id")
        if cid in seen:
            r.append("duplicate claim_id within this company")
        seen.add(cid)
        if r:
            claim_reasons.append(f"{cid}: {'; '.join(r)}")
            continue
        claims.append(raw)
    reasons += claim_reasons

    if reasons:
        return None, reasons

    demoted: list[str] = []
    if require_citation:
        cats, demoted = apply_citation_rule(cats, claims)

    entry = roster[ticker]
    record = {
        "demoted": demoted,
        "ticker": ticker,
        "cik": entry.get("cik"),
        "sector_id": entry.get("sector_id"),
        "industry_id": entry.get("industry_id"),
        "subindustry_id": entry.get("subindustry_id"),
        "research_depth": row["research_depth"],
        "categoricals": cats,
        "texts": texts,
        "key_monitoring_variables": pass_a.get("key_monitoring_variables"),
        "reconciliation": (row.get("pass_b") or {}).get("reconciliation"),
        "refresh_class": row.get("refresh_class"),
        "next_refresh_due": row.get("next_suggested_refresh"),
        "claims": claims,
    }
    return record, []


def finalize(payload: dict, *, request: dict | None = None,
             now: datetime | None = None, apply: bool = False,
             store=None) -> dict:
    from .store import ExternalStore

    request = request if request is not None else (net.read_json(config.EXTERNAL_REQUEST) or {})
    check_request(request, payload, now=now)

    roster = {str(r["ticker"]).upper(): r for r in request.get("roster") or []}
    require_citation = bool(request.get("require_citation"))
    accepted, rejected = [], []
    for row in payload.get("companies") or []:
        record, reasons = finalize_company(row, roster,
                                           require_citation=require_citation)
        if record is None:
            rejected.append({"ticker": row.get("ticker"), "reasons": reasons})
        else:
            accepted.append(record)

    answered = {r["ticker"] for r in accepted} | {
        str(r.get("ticker") or "").upper() for r in rejected}
    unanswered = sorted(t for t in roster if t not in answered)

    store = store or ExternalStore()
    # The sample label is part of the version. Two runs over the same roster under
    # different research rules must not overwrite each other, or the arm being compared
    # against is destroyed by the comparison.
    version = str(request.get("generated_at", ""))[:10] or net.utc_today()
    if request.get("sample"):
        version = f"{version}+{request['sample']}"
    n_claims = 0
    if apply:
        for rec in accepted:
            claims = [to_claim(c, ticker=rec["ticker"],
                               industry_id=rec.get("industry_id"))
                      for c in rec["claims"]]
            store.upsert_company({
                "ticker": rec["ticker"], "research_version": version,
                "cik": rec["cik"], "sector_id": rec["sector_id"],
                "industry_id": rec["industry_id"],
                "subindustry_id": rec["subindustry_id"],
                **rec["categoricals"],
                "why_is_it_cheap": rec["texts"].get("why_is_it_cheap"),
                "bull_case": rec["texts"].get("bull_case"),
                "bear_case": rec["texts"].get("bear_case"),
                "major_thesis_risk": rec["texts"].get("major_thesis_risk"),
                "thesis_break_condition": rec["texts"].get("thesis_break_condition"),
                "key_monitoring_variables": rec["key_monitoring_variables"],
                "research_depth": rec["research_depth"],
                "claims_total": len(claims),
                # external_score and external_confidence stay NULL. score.py computes
                # them from the categoricals and the VERIFIED claim mix, after
                # verify.py has run. A score written here would be a score computed
                # from unverified evidence.
                "external_score": None, "external_confidence": None,
                "request_id": request.get("request_id"),
                "external_schema_version": EXTERNAL_SCHEMA_VERSION,
                "last_research_date": net.utc_now_iso(),
                "next_refresh_due": rec.get("next_refresh_due"),
                "refresh_class": rec.get("refresh_class"),
            })
            store.insert_claims(
                claims, request_id=request.get("request_id", ""),
                excerpt_sha1={c["claim_id"]: _sha1(c.get("excerpt") or "")
                              for c in rec["claims"]})
            n_claims += len(claims)
        store.complete(request.get("request_id", ""), n_returned=len(accepted),
                       n_rejected=len(rejected),
                       cost_tokens=int((payload.get("cost") or {}).get("tokens") or 0),
                       cost_searches=int((payload.get("cost") or {}).get("searches") or 0))

    demotions = {r["ticker"]: r.get("demoted") or [] for r in accepted
                 if r.get("demoted")}
    backing = {}
    for r in accepted:
        cited = {c.get("field") for c in r["claims"]}
        asserted = [k for k, v in r["categoricals"].items() if v != S.UNKNOWN]
        backing[r["ticker"]] = {
            "asserted_non_unknown": len(asserted),
            "backed": len([k for k in asserted if k in cited]),
            "claims": len(r["claims"]),
        }
    # Counted, never fatal on the company lane - a 42-company batch costs hundreds of
    # metered searches and must not be rejected over a missing label. But an unlabelled
    # claim is now stored as NULL rather than silently CONTEXT (E78), so the count has to
    # be visible or the batch report reads as if every claim was judged.
    unlabelled = {
        f: sum(1 for r in accepted for c in r["claims"] if not c.get(f))
        for f in ("stance", "fact_or_inference")}
    return {"accepted": [r["ticker"] for r in accepted], "rejected": rejected,
            "unanswered": unanswered, "claims": n_claims,
            "require_citation": require_citation, "demoted": demotions,
            "backing": backing, "unlabelled": unlabelled,
            "research_version": version, "applied": bool(apply)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Finalize a Codex research payload")
    ap.add_argument("payload", help="path to <request_id>.json")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)

    payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
    try:
        res = finalize(payload, apply=args.apply)
    except Rejected as exc:
        print(f"PAYLOAD REFUSED: {exc}")
        return 2

    print(f"accepted  {len(res['accepted'])}: {res['accepted']}")
    print(f"rejected  {len(res['rejected'])}")
    for r in res["rejected"]:
        print(f"  {r['ticker']}")
        for reason in r["reasons"]:
            print(f"    - {reason}")
    if res["unanswered"]:
        print(f"unanswered (in the roster, absent from the payload): {res['unanswered']}")
    print(f"claims stored {res['claims']} (all SELF_ATTESTED; run verify.py next)")
    print()
    print(f"citation rule: {'ENFORCED' if res['require_citation'] else 'off'}")
    tot_a = sum(b["asserted_non_unknown"] for b in res["backing"].values())
    tot_b = sum(b["backed"] for b in res["backing"].values())
    for t, b in sorted(res["backing"].items()):
        print(f"  {t:<6} non-UNKNOWN {b['asserted_non_unknown']:>2}  "
              f"claim-backed {b['backed']:>2}  claims {b['claims']:>2}")
    if tot_a:
        print(f"  TOTAL  non-UNKNOWN {tot_a}  backed {tot_b}  "
              f"({tot_b / tot_a:.0%})")
    if res["demoted"]:
        print("  demoted to UNKNOWN (asserted with no claim citing that field):")
        for t, fields in sorted(res["demoted"].items()):
            print(f"    {t}: {fields}")
    if not args.apply:
        print("\nDRY RUN - nothing written. Re-run with --apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
