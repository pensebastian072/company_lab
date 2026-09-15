"""Retire rejected research arms or objects without deleting their evidence.

Dry-run is the default. Lifecycle writes mark exact stored rows SUPERSEDED; claims and
manifests remain intact for audit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .. import config
from .store import ExternalStore


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _target_receipt(store: ExternalStore, research_version: str) -> dict:
    rows = store.companies(research_version)
    request_ids = sorted({str(r.get("request_id")) for r in rows
                          if r.get("request_id")})
    claims = []
    if request_ids:
        marks = ", ".join("?" for _ in request_ids)
        with store.connect() as con:
            claims = con.execute(
                "SELECT request_id, verify_status, count(*) FROM external_claim "
                f"WHERE request_id IN ({marks}) GROUP BY 1, 2 ORDER BY 1, 2",
                request_ids,
            ).fetchall()
    statuses: dict[str, int] = {}
    for row in rows:
        status = str(row.get("status") or "ACTIVE").upper()
        statuses[status] = statuses.get(status, 0) + 1
    return {
        "research_version": research_version,
        "company_rows": len(rows),
        "distinct_tickers": len({r.get("ticker") for r in rows}),
        "request_ids": request_ids,
        "status_counts": dict(sorted(statuses.items())),
        "claim_counts": [
            {"request_id": request_id, "verify_status": verify_status, "claims": n}
            for request_id, verify_status, n in claims
        ],
    }


def supersede_company_version(research_version: str, *, reason: str,
                              superseded_by: str | None = None,
                              apply: bool = False,
                              store: ExternalStore | None = None) -> dict:
    """Return a corpus-pinned dry-run/apply receipt for one lifecycle transition."""
    st = store or ExternalStore(config.EXTERNAL_DB)
    target = _target_receipt(st, research_version)
    if not target["company_rows"]:
        raise ValueError(f"no company rows for research_version {research_version!r}")
    if superseded_by and not st.companies(superseded_by):
        raise ValueError(f"superseding version {superseded_by!r} has no company rows")

    before_hash = _sha256(st.path)
    changed = 0
    if apply:
        changed = st.supersede_company_version(
            research_version, reason=reason, superseded_by=superseded_by)
    after_hash = _sha256(st.path)

    return {
        "applied": apply,
        "rows_changed": changed,
        "superseded_by": superseded_by,
        "reason": reason,
        "target_before": target,
        "target_after": _target_receipt(st, research_version),
        "corpus_claims": st.verify_rates(),
        "store_sha256_before": before_hash,
        "store_sha256_after": after_hash,
    }


def _industry_receipt(store: ExternalStore, industry_ids: list[str],
                      version: str) -> dict:
    ids = sorted(set(industry_ids))
    marks = ", ".join("?" for _ in ids)
    with store.connect() as con:
        cur = con.execute(
            "SELECT * FROM industry_intelligence WHERE version = ? "
            f"AND industry_id IN ({marks}) ORDER BY industry_id",
            [version, *ids],
        )
        names = [d[0] for d in cur.description]
        rows = [dict(zip(names, r)) for r in cur.fetchall()]
        claims = con.execute(
            "SELECT industry_id, request_id, verify_status, count(*) "
            "FROM external_claim WHERE (ticker IS NULL OR ticker = '') "
            f"AND industry_id IN ({marks}) "
            "AND request_id = 'phase0:' || industry_id || ':' || ? "
            "GROUP BY 1, 2, 3 ORDER BY 1, 2, 3",
            [*ids, version],
        ).fetchall()
    statuses: dict[str, int] = {}
    for row in rows:
        status = str(row.get("status") or "ACTIVE").upper()
        statuses[status] = statuses.get(status, 0) + 1
    found = {r.get("industry_id") for r in rows}
    return {
        "version": version,
        "requested_industry_ids": ids,
        "industry_rows": len(rows),
        "missing_industry_ids": sorted(set(ids) - found),
        "status_counts": dict(sorted(statuses.items())),
        "claim_counts": [
            {"industry_id": iid, "request_id": request_id,
             "verify_status": verify_status, "claims": n}
            for iid, request_id, verify_status, n in claims
        ],
    }


def supersede_industry_versions(industry_ids: list[str], *, version: str,
                                reason: str,
                                superseded_by: str | None = None,
                                apply: bool = False,
                                store: ExternalStore | None = None) -> dict:
    """Return a corpus-pinned receipt for an atomic industry-object retirement."""
    st = store or ExternalStore(config.EXTERNAL_DB)
    target = _industry_receipt(st, industry_ids, version)
    if target["missing_industry_ids"]:
        raise ValueError(
            f"missing industry/version rows: {target['missing_industry_ids']}")

    before_hash = _sha256(st.path)
    changed = 0
    if apply:
        changed = st.supersede_industry_versions(
            industry_ids, version=version, reason=reason,
            superseded_by=superseded_by)
    after_hash = _sha256(st.path)
    return {
        "applied": apply,
        "rows_changed": changed,
        "superseded_by": superseded_by,
        "reason": reason,
        "target_before": target,
        "target_after": _industry_receipt(st, industry_ids, version),
        "corpus_claims": st.verify_rates(),
        "store_sha256_before": before_hash,
        "store_sha256_after": after_hash,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Retire exact research rows; dry-run unless --apply")
    target = ap.add_mutually_exclusive_group(required=True)
    target.add_argument("--company-version")
    target.add_argument("--industry-version")
    ap.add_argument("--industry-id", action="append", default=[])
    ap.add_argument("--reason", required=True)
    ap.add_argument("--superseded-by")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)

    try:
        if args.company_version:
            if args.industry_id:
                ap.error("--industry-id requires --industry-version")
            result = supersede_company_version(
                args.company_version,
                reason=args.reason,
                superseded_by=args.superseded_by,
                apply=args.apply,
            )
        else:
            if not args.industry_id:
                ap.error("--industry-version requires at least one --industry-id")
            result = supersede_industry_versions(
                args.industry_id,
                version=args.industry_version,
                reason=args.reason,
                superseded_by=args.superseded_by,
                apply=args.apply,
            )
    except ValueError as exc:
        ap.error(str(exc))
    print(json.dumps(result, indent=2, default=str, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
