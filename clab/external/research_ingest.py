"""Validate and ingest Codex's industry / sector research objects.

## Why this is not "Codex said validation passed"

The first delivery reported "validation passed for all 19 unique claims ... six sampled
source URLs were re-fetched successfully and all six sampled quotes matched." That is
the researcher grading its own work with its own validator. Two of those words do a lot
of load-bearing:

* "validation" meant Codex's checks, not this schema's. Run against `schema.py`, all
  three objects came back `unknown field 'structural_growth'` and two siblings, because
  those vocabularies were missing from `schema.py` entirely. The research was fine and
  the promise was false, which is the harder failure to notice.
* "re-fetched successfully" was Codex re-fetching Codex's own URLs. Nothing in this
  repo saw those pages. Until `verify.py` (P1) fetches them from here, every claim is
  **SELF_ATTESTED**, never `VERIFIED_LOCAL`. A researcher marking its own work verified
  is not verification, so `verify_status` is assigned here and any value arriving in
  the payload is overwritten.

## The check Codex could not have run on itself

Confidence in this system counts DISTINCT INDEPENDENCE DOMAINS. That makes the domain
label a lever: relabel two claims and the same evidence reports as more independent.
Nothing about a single object looks wrong when that happens, so the check has to be
structural.

`evidence_profile()` measures the lever directly - claims vs distinct URLs vs distinct
hosts vs distinct domains, how many domains rest on a single claim, and whether one
host has been filed under two different domains. On the first delivery that last check
found `www.se.com` (Schneider Electric) entered as both `COMPETITOR_FILING` and
`SUPPLIER` inside `datacenter_power_cooling`, which manufactures a fourth domain out of
one organisation.

This is the E40 lesson in a different costume: measure whether the researcher is being
more generous than informative, and report the rate rather than assume it away.
"""
from __future__ import annotations

import collections
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from .. import config
from . import schema as S
from .schema import Claim

#: Categorical fields an industry object carries.
INDUSTRY_CATEGORICALS = ("structural_growth", "replication_difficulty",
                         "substitution_risk", "refresh_class")
#: Free-text fields and their caps, as stated in the Phase 0 prompt.
INDUSTRY_TEXT_LIMITS = {"market_structure": 1500, "moat_mechanism": 1000,
                        "technology_trajectory": 1000, "regulatory_trajectory": 1000}
SECTOR_TEXT_LIMITS = {"market_structure": 1500, "regulatory_environment": 1000,
                      "what_changed": 1200}

CLAIM_ID_RE = re.compile(r"^c_[0-9a-f]{12}$")
MAX_QUOTE = 300


def _host(url: str | None) -> str:
    try:
        return (urlsplit(url or "").netloc or "").lower()
    except ValueError:
        return ""


def _sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", "replace")).hexdigest()


# --------------------------------------------------------------------- claims
def validate_claim(raw: dict, *, require_labels: bool = False) -> list[str]:
    """Rejection reasons for one claim. Empty means structurally clean.

    Note what this does NOT establish: that the excerpt is real. A quote inside a
    fabricated excerpt passes every check here. Only a local re-fetch settles that, and
    until then the claim is SELF_ATTESTED.

    `require_labels` makes an omitted `stance` or `fact_or_inference` a rejection. It is
    ON for industry objects and OFF for company batches, and the asymmetry is about cost,
    not about principle: a Phase A object is cheap to re-emit, while a 42-company batch
    costs hundreds of metered searches and must not be rejected wholesale over a missing
    label. On the company side the omission is recorded as NULL and counted, not fatal.
    """
    reasons: list[str] = []
    if require_labels:
        for f in ("stance", "fact_or_inference"):
            if not raw.get(f):
                reasons.append(f"no {f} - it must be stated, not left to a default")
    cid = raw.get("claim_id")
    if not isinstance(cid, str) or not CLAIM_ID_RE.match(cid):
        reasons.append(f"claim_id {cid!r} is not c_<12 hex>")
    if not raw.get("field"):
        reasons.append("no field")
    if not raw.get("text"):
        reasons.append("no text")

    reasons += S.validate_categoricals({
        k: raw[k] for k in ("stance", "fact_or_inference", "source_type",
                            "independence_domain") if raw.get(k) is not None})

    quote, excerpt = raw.get("quote"), raw.get("excerpt")
    if not isinstance(quote, str) or not quote.strip():
        reasons.append("no quote")
    elif len(quote) > MAX_QUOTE:
        reasons.append(f"quote is {len(quote)} chars, cap is {MAX_QUOTE}")
    if not isinstance(excerpt, str) or not excerpt.strip():
        reasons.append("no excerpt")
    if isinstance(quote, str) and isinstance(excerpt, str) and quote not in excerpt:
        reasons.append("quote is NOT present in its own excerpt")
    if not raw.get("source_url"):
        reasons.append("no source_url")
    if not raw.get("source_date"):
        reasons.append("no source_date")
    return reasons


def to_claim(raw: dict, *, industry_id: str | None = None,
             ticker: str | None = None) -> Claim:
    """Build a Claim with `verify_status` assigned HERE, never taken from the payload.

    `stance` and `fact_or_inference` are NOT defaulted. They were, to "CONTEXT" and
    "INFERENCE", and E78 measured what that cost: an unlabelled run is indistinguishable
    in the store from one that judged every claim to be context, and the two runs that
    never labelled stance (Financials 103 CONTEXT / 29 SUPPORTS, Industrials 134 / 11)
    read as evidence quality when they were recording nothing at all. Three sectors filed
    zero FACT claims by the same mechanism.

    NULL now means "the researcher did not say", which is a different fact from CONTEXT
    and the only one that can be counted honestly.
    """
    quote, excerpt = raw.get("quote") or "", raw.get("excerpt") or ""
    status = "SELF_ATTESTED" if (quote and excerpt and quote in excerpt) \
        else "UNVERIFIABLE"
    if not raw.get("source_url"):
        status = "UNVERIFIABLE"
    return Claim(
        claim_id=raw.get("claim_id", ""), field=raw.get("field", ""),
        text=raw.get("text", ""), source_url=raw.get("source_url"),
        source_title=raw.get("source_title"), source_date=raw.get("source_date"),
        source_type=raw.get("source_type"),
        independence_domain=raw.get("independence_domain"),
        quote=quote or None, excerpt=excerpt or None,
        stance=raw.get("stance"),
        fact_or_inference=raw.get("fact_or_inference"),
        verify_status=status, overlap=None,
        ticker=ticker, industry_id=industry_id,
    )


# ---------------------------------------------------------- evidence profile
def evidence_profile(claims: list[dict]) -> dict:
    """Measure the independence lever rather than trusting the domain labels.

    `domains_on_one_claim` is the number that matters most: an object reporting five
    domains where four of them rest on a single claim each has one supporting source
    per domain, not five independent lines of evidence.
    """
    doms = collections.Counter(c.get("independence_domain") for c in claims)
    urls = {c.get("source_url") for c in claims if c.get("source_url")}
    hosts = collections.Counter(_host(c.get("source_url")) for c in claims)

    host_domains: dict[str, set] = collections.defaultdict(set)
    for c in claims:
        host_domains[_host(c.get("source_url"))].add(c.get("independence_domain"))
    conflicts = {h: sorted(d) for h, d in host_domains.items() if len(d) > 1}

    # The stance split is reported beside the domain counts because E78 found it was the
    # less trustworthy of the two and nothing was showing it. `unlabelled_stance` is the
    # number that makes the rest readable: a batch of zeros there means the split is a
    # judgement, and anything else means it is partly a default.
    stances = collections.Counter(c.get("stance") for c in claims)

    return {
        "claims": len(claims),
        "distinct_urls": len(urls),
        "distinct_hosts": len([h for h in hosts if h]),
        "distinct_domains": len([d for d in doms if d]),
        "domain_counts": dict(doms),
        "domains_on_one_claim": sorted(d for d, n in doms.items() if n == 1 and d),
        "host_domain_conflicts": conflicts,
        "claims_per_url": round(len(claims) / max(len(urls), 1), 2),
        "stance_counts": {k: v for k, v in stances.items() if k},
        "unlabelled_stance": stances.get(None, 0),
        "unlabelled_fact_or_inference": sum(
            1 for c in claims if not c.get("fact_or_inference")),
        "inference_claims": sum(1 for c in claims
                                if c.get("fact_or_inference") == "INFERENCE"),
    }


# --------------------------------------------------------------- validation
def validate_industry(obj: dict) -> dict:
    reasons: list[str] = []
    if not obj.get("industry_id"):
        reasons.append("no industry_id")
    if not obj.get("version"):
        reasons.append("no version")
    if obj.get("status") != "SHADOW":
        reasons.append(f"status is {obj.get('status')!r}, must be SHADOW")
    if obj.get("sector_id") and obj["sector_id"] not in S.SECTOR_IDS:
        reasons.append(f"sector_id {obj['sector_id']!r} is not one of the 11")

    reasons += S.validate_categoricals(
        {k: obj[k] for k in INDUSTRY_CATEGORICALS if obj.get(k) is not None})
    for name, cap in INDUSTRY_TEXT_LIMITS.items():
        v = obj.get(name)
        if isinstance(v, str) and len(v) > cap:
            reasons.append(f"{name} is {len(v)} chars, cap is {cap}")

    claims = obj.get("claims") or []
    claim_reasons: dict[str, list[str]] = {}
    for c in claims:
        # Industry objects carry the label requirement; see validate_claim's docstring
        # for why the company lane does not.
        r = validate_claim(c, require_labels=True)
        if r:
            claim_reasons[c.get("claim_id") or "<no id>"] = r
    seen = collections.Counter(c.get("claim_id") for c in claims)
    dupes = [k for k, n in seen.items() if n > 1]
    if dupes:
        reasons.append(f"duplicate claim_ids: {dupes}")

    return {"industry_id": obj.get("industry_id"), "ok": not reasons and not
            claim_reasons, "reasons": reasons, "claim_reasons": claim_reasons,
            "evidence": evidence_profile(claims)}


def validate_sector(obj: dict, known_industries: set[str] | None = None) -> dict:
    """Checks for one sector object.

    The checker shipped on 2026-09-01 read `industries/` and nothing else, so it
    returned exit 0 over a tree in which 11 of the 26 artifacts had never been looked
    at. A green check that does not cover the artifact is worse than no check, because
    it is reported as coverage - the same failure as E34's verification reading the
    wrong field and passing quietly.
    """
    reasons: list[str] = []
    sid = obj.get("sector_id")
    if sid not in S.SECTOR_IDS:
        reasons.append(f"sector_id {sid!r} is not one of the 11")
    if not obj.get("version"):
        reasons.append("no version")
    if obj.get("status") != "SHADOW":
        reasons.append(f"status is {obj.get('status')!r}, must be SHADOW")
    if obj.get("capital_cycle") is not None:
        reasons += S.validate_categoricals({"capital_cycle": obj["capital_cycle"]})

    for name, cap in SECTOR_TEXT_LIMITS.items():
        v = obj.get(name)
        if isinstance(v, str) and len(v) > cap:
            reasons.append(f"{name} is {len(v)} chars, cap is {cap}")

    # major_industries must point at objects that exist, or the sector and industry
    # layers are two prose documents rather than one graph.
    majors = obj.get("major_industries") or []
    if known_industries is not None:
        dangling = [m for m in majors if m not in known_industries]
        if dangling:
            reasons.append(f"major_industries reference no built object: {dangling}")

    claims = obj.get("claims") or []
    claim_ids = {c.get("claim_id") for c in claims}
    # A winner or loser without a citation is the easiest thing in the file to write
    # and the least useful. Every named company must point at a claim in this object.
    for bucket in ("current_winners", "current_losers"):
        for row in obj.get(bucket) or []:
            if not isinstance(row, dict):
                reasons.append(f"{bucket} entry is not an object: {row!r}")
                continue
            cids = row.get("claim_ids") or []
            if not cids:
                reasons.append(
                    f"{bucket}: {row.get('ticker')!r} named with no claim_ids")
            missing = [c for c in cids if c not in claim_ids]
            if missing:
                reasons.append(
                    f"{bucket}: {row.get('ticker')!r} cites claim ids absent from this "
                    f"object: {missing}")

    claim_reasons: dict[str, list[str]] = {}
    for c in claims:
        r = validate_claim(c)
        if r:
            claim_reasons[c.get("claim_id") or "<no id>"] = r

    return {"sector_id": sid, "ok": not reasons and not claim_reasons,
            "reasons": reasons, "claim_reasons": claim_reasons,
            "evidence": evidence_profile(claims),
            "n_majors": len(majors),
            "n_winners": len(obj.get("current_winners") or []),
            "n_losers": len(obj.get("current_losers") or [])}


def load_and_validate_sectors(root: Path | None = None,
                              known_industries: set[str] | None = None) -> list[dict]:
    root = root or (config.EXTERNAL_RESEARCH_DIR / "sectors")
    out: list[dict] = []
    if not root.exists():
        return out
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        f = d / "sector_state.json"
        if not f.exists():
            out.append({"sector_id": d.name, "ok": False,
                        "reasons": ["no sector_state.json"], "claim_reasons": {},
                        "evidence": evidence_profile([]), "n_majors": 0,
                        "n_winners": 0, "n_losers": 0})
            continue
        try:
            obj = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError) as exc:
            out.append({"sector_id": d.name, "ok": False,
                        "reasons": [f"unparseable: {type(exc).__name__}"],
                        "claim_reasons": {}, "evidence": evidence_profile([]),
                        "n_majors": 0, "n_winners": 0, "n_losers": 0})
            continue
        res = validate_sector(obj, known_industries=known_industries)
        res["_obj"] = obj
        if obj.get("sector_id") and obj["sector_id"] != d.name:
            res["reasons"].append(
                f"sector_id {obj['sector_id']!r} does not match directory {d.name!r}")
            res["ok"] = False
        out.append(res)
    return out


def ingest_sectors(results: list[dict], *, store=None, apply: bool = False) -> dict:
    from .store import ExternalStore

    store = store or ExternalStore()
    written, skipped, n_claims = [], [], 0
    for res in results:
        if not res.get("ok"):
            skipped.append(res["sector_id"])
            continue
        obj = res["_obj"]
        if apply:
            store.upsert_sector({
                "sector_id": obj["sector_id"], "version": obj["version"],
                "brief": obj.get("market_structure"),
                "what_changed": obj.get("what_changed"),
                "winners": obj.get("current_winners"),
                "losers": obj.get("current_losers"),
                "capital_cycle": obj.get("capital_cycle"),
                "metrics_that_matter": obj.get("metrics_that_matter"),
                "last_updated": obj.get("last_updated"),
            })
            claims = [to_claim(c) for c in obj.get("claims") or []]
            store.insert_claims(
                claims, request_id=f"phase0:sector:{obj['sector_id']}:{obj['version']}",
                excerpt_sha1={c["claim_id"]: _sha1(c.get("excerpt") or "")
                              for c in obj.get("claims") or []})
            n_claims += len(claims)
        written.append(res["sector_id"])
    return {"written": written, "skipped": skipped, "claims": n_claims}


def load_and_validate(root: Path | None = None) -> list[dict]:
    root = root or (config.EXTERNAL_RESEARCH_DIR / "industries")
    out = []
    if not root.exists():
        return out
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        f = d / "industry_state.json"
        if not f.exists():
            out.append({"industry_id": d.name, "ok": False,
                        "reasons": ["no industry_state.json"], "claim_reasons": {},
                        "evidence": evidence_profile([])})
            continue
        try:
            obj = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError) as exc:
            out.append({"industry_id": d.name, "ok": False,
                        "reasons": [f"unparseable: {type(exc).__name__}"],
                        "claim_reasons": {}, "evidence": evidence_profile([])})
            continue
        res = validate_industry(obj)
        res["_obj"] = obj
        res["_dir"] = d
        if obj.get("industry_id") and obj["industry_id"] != d.name:
            res["reasons"].append(
                f"industry_id {obj['industry_id']!r} does not match its directory "
                f"{d.name!r} - company records join on the directory id")
            res["ok"] = False
        out.append(res)
    return out


# ------------------------------------------------------------------- ingest
def ingest(results: list[dict], *, store=None, apply: bool = False) -> dict:
    """Write validated industry objects and their claims into the catalog."""
    from .store import ExternalStore

    store = store or ExternalStore()
    written, skipped, n_claims = [], [], 0
    for res in results:
        if not res.get("ok"):
            skipped.append(res["industry_id"])
            continue
        obj = res["_obj"]
        if apply:
            store.upsert_industry({
                "industry_id": obj["industry_id"], "version": obj["version"],
                "sector_id": obj.get("sector_id"),
                "brief": obj.get("market_structure"),
                "structural_growth": obj.get("structural_growth"),
                "moat_mechanism": obj.get("moat_mechanism"),
                "replication_difficulty": obj.get("replication_difficulty"),
                "substitution_risk": obj.get("substitution_risk"),
                "key_metrics": obj.get("key_metrics"),
                "refresh_class": obj.get("refresh_class"),
                "last_updated": obj.get("last_updated"),
                "next_refresh_due": obj.get("next_refresh_due"),
            })
            claims = [to_claim(c, industry_id=obj["industry_id"])
                      for c in obj.get("claims") or []]
            store.insert_claims(
                claims, request_id=f"phase0:{obj['industry_id']}:{obj['version']}",
                excerpt_sha1={c["claim_id"]: _sha1(c.get("excerpt") or "")
                              for c in obj.get("claims") or []})
            n_claims += len(claims)
        written.append(res["industry_id"])
    return {"written": written, "skipped": skipped, "claims": n_claims}


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Validate and ingest Codex research")
    ap.add_argument("--apply", action="store_true", help="write to the catalog")
    ap.add_argument("--no-fetch", action="store_true",
                    help="skip the acceptance check's exact-containment test, which "
                         "fetches every cited url")
    ap.add_argument("--override-acceptance", metavar="REASON", default=None,
                    help="ingest a batch the acceptance gate refused. Takes a written "
                         "reason and says so loudly; there is no silent bypass")
    args = ap.parse_args(argv)

    results = load_and_validate()
    if not results:
        print(f"no industry objects under {config.EXTERNAL_RESEARCH_DIR / 'industries'}")
        return 1

    for r in results:
        e = r["evidence"]
        mark = "OK  " if r["ok"] else "FAIL"
        print(f"[{mark}] {r['industry_id']}")
        print(f"       claims {e['claims']}  urls {e['distinct_urls']}  "
              f"hosts {e['distinct_hosts']}  domains {e['distinct_domains']}  "
              f"claims/url {e['claims_per_url']}  inference {e['inference_claims']}")
        print(f"       domains {e['domain_counts']}")
        if e["domains_on_one_claim"]:
            print(f"       THIN: domains resting on a single claim: "
                  f"{e['domains_on_one_claim']}")
        if e["host_domain_conflicts"]:
            print(f"       CONFLICT: one host filed under two domains: "
                  f"{e['host_domain_conflicts']}")
        for reason in r["reasons"]:
            print(f"       - {reason}")
        for cid, rs in r["claim_reasons"].items():
            print(f"       - {cid}: {'; '.join(rs)}")

    known = {r["industry_id"] for r in results if r.get("ok")}
    sectors = load_and_validate_sectors(known_industries=known)
    print()
    for r in sectors:
        e = r["evidence"]
        mark = "OK  " if r["ok"] else "FAIL"
        print(f"[{mark}] sector {r['sector_id']}")
        print(f"       claims {e['claims']}  urls {e['distinct_urls']}  "
              f"domains {e['distinct_domains']}  industries {r['n_majors']}  "
              f"winners {r['n_winners']}  losers {r['n_losers']}")
        if e["host_domain_conflicts"]:
            print(f"       CONFLICT: one host under two domains: "
                  f"{e['host_domain_conflicts']}")
        for reason in r["reasons"]:
            print(f"       - {reason}")
        for cid, rs in r["claim_reasons"].items():
            print(f"       - {cid}: {'; '.join(rs)}")

    # ------------------------------------------------------------ corpus view
    all_claims: list[dict] = []
    for r in results:
        all_claims += (r.get("_obj") or {}).get("claims") or []
    for r in sectors:
        all_claims += (r.get("_obj") or {}).get("claims") or []
    corpus = evidence_profile(all_claims)
    ids = collections.Counter(c.get("claim_id") for c in all_claims)
    reused = {k: n for k, n in ids.items() if n > 1}
    single_domain = [r["industry_id"] for r in results
                     if r["evidence"]["distinct_domains"] <= 1]

    print("\n--- corpus ---")
    print(f"objects: {len(results)} industries + {len(sectors)} sectors")
    print(f"claims {corpus['claims']}  distinct_ids {len(ids)}  "
          f"distinct_urls {corpus['distinct_urls']}  "
          f"distinct_hosts {corpus['distinct_hosts']}  "
          f"claims_per_url {corpus['claims_per_url']}")
    print(f"domains across the corpus: {corpus['domain_counts']}")
    if reused:
        print(f"REUSED claim_ids across objects: {reused}")
    if single_domain:
        print(f"SINGLE-DOMAIN objects (all evidence from one kind of source): "
              f"{len(single_domain)} -> {single_domain}")

    # ------------------------------------------------- the acceptance gate
    # Every defect in this layer was found AFTER the batch landed. This is the same
    # measurements, run one step earlier, with the authority to refuse. It runs on a
    # dry run too, so `--apply` never shows a researcher something new.
    from . import acceptance as ACC

    report = ACC.accept_objects(results, fetch=not args.no_fetch)
    print()
    print(ACC.render(report))
    if report.failures and args.apply:
        if not args.override_acceptance:
            print("\nINGEST REFUSED. Fix the batch and re-run, or pass "
                  "--override-acceptance '<why>' if the gate is wrong about this one.")
            return 2
        print("\n" + "!" * 70)
        print("ACCEPTANCE GATE OVERRIDDEN: " + args.override_acceptance)
        print("Refused: " + ", ".join(c.name for c in report.failures))
        print("!" * 70)

    res = ingest(results, apply=args.apply)
    sres = ingest_sectors(sectors, apply=args.apply)
    print(f"\ningest industries: {res}")
    print(f"ingest sectors   : {sres}")
    if not args.apply:
        print("DRY RUN - nothing written. Re-run with --apply.")
    else:
        print("Claims stored SELF_ATTESTED. Nothing is VERIFIED_LOCAL until verify.py "
              "(P1) re-fetches the sources from here.")
    ok = (all(r["ok"] for r in results) and all(r["ok"] for r in sectors)
          and not report.failures)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
