"""One command, one exit code, run BEFORE a batch is ingested.

## Why this exists at all

Every defect in this layer was found *after* the batch landed. E61 shipped 25 Industrials
objects that concluded nothing and it took a retirement sweep to see it. E79 built 64
objects whose evidence was 100% `sec.gov`. E43-E46 lost the four rank-order fields from
92% filled to 0% over eight batches while every quality metric stayed perfect. In each
case the gauge that would have caught it either did not exist yet or existed and was not
run in the same breath as the ingest.

So the gauges are not new. `batch_health.compare`, `batch_health.constant_fields`,
`batch_health.completeness` and `research_ingest.evidence_profile` all already measured
these things. What was missing is a single thing to RUN, with a single answer, positioned
one step earlier than the audit. That is all this module is.

## What it refuses on, and what it merely says out loud

A gate that fails on everything suspicious gets disabled within a week, and a gate that
fails on nothing is decoration. The split here is deliberate and each side is argued:

    FAIL   a defect whose cost is a re-run and whose cause is mechanical
           - an object that concludes nothing (E61)
           - an object or batch with NO non-issuer evidence at all (E79)
           - the four rank-order fields falling against the same sector's last batch
             (the abstention collapse, 45 of the 100 external points)
           - a rank-order field arriving all-UNKNOWN across the whole batch
           - citations that cannot be found on their own pages at any usable rate

    WARN   a pattern that is often correct and sometimes a defect, where only the
           researcher can tell which
           - a constant non-UNKNOWN field (a finding, or a stuck derivation: E30)
           - evidence concentrated on one host without being entirely issuer-sourced
           - an object sitting at 1 or 2 of 3 structural fields

`constant_fields` REPORTS and never fails in `batch_health`, on the argument that a
regulated sector can honestly answer UNKNOWN to every market-share question - E53 returned
0 of 59 correctly. That argument is kept. The single exception is a rank-order field that
is all-UNKNOWN, which is the abstention collapse by definition and is not a sector fact.

## What it cannot do

It cannot tell a sector that honestly answers less from a researcher that answered less.
Nothing can, from the numbers alone. It fails on the DIRECTION and size of a move against
the same sector's own previous batch, which is the narrowest comparison available, and it
names what it failed on so the argument can be had.
"""
from __future__ import annotations

import argparse
import collections
import json
from dataclasses import dataclass, field as dc_field
from pathlib import Path

from .. import config
from . import batch_health as BH
from . import research_ingest as RI
from . import schema as S
from . import verify as V
from .schema import UNKNOWN

PASS, WARN, FAIL, SKIP = "PASS", "WARN", "FAIL", "SKIP"

#: Evidence domains that are NOT the issuers' own filings. The plan's rule 5, stated as a
#: set: an object evidenced only by its members' own paperwork has no outside view of the
#: industry it claims to describe, whatever its claim count.
NON_ISSUER_DOMAINS = ("REGULATOR", "TRADE_PRESS", "PRIMARY_DATA", "ACADEMIC")
#: The fallback when a claim carries no `independence_domain`: its source_type.
NON_ISSUER_SOURCE_TYPES = ("REGULATOR", "TRADE_PUBLICATION", "PRIMARY_DATA", "NEWS")

#: One host supplying this much of a batch's evidence is reported. E61 ran 96.6% on a
#: single domain and E79 100% on `sec.gov`; neither was visible in any metric at the time.
HOST_CONCENTRATION_WARN = 0.90

#: Below this share of a batch's own quoted claims being findable on their own cited
#: pages, the batch is refused.
#:
#: CHOSEN FROM THE MEASURED DISTRIBUTION, not from taste. `--containment-history` over
#: every ingested batch, after the restatement, is bimodal and the gap is wide:
#:
#:     ten batches          99.3% - 100.0%
#:     ---------- nothing between 91.5% and 99.3% ----------
#:     three batches        89.2%, 91.1%, 91.5%   (E45-rest and its neighbours, the
#:                                                 batches researched during the
#:                                                 abstention collapse)
#:
#: 0.95 sits in the empty gap. It refuses a batch that looks like the low cluster and
#: passes every batch that looks like the high one, and it does not need a judgement about
#: how much slop is tolerable - the corpus already answered that in two voices. A first
#: draft used 0.90, which sits INSIDE the low cluster and would have refused one of those
#: three while passing the other two, on no principle at all.
MIN_CONTAINMENT_RATE = 0.95

#: Below this many quoted claims a RATE is noise, so the rate is not applied. A small
#: object is refused only when NOTHING it cites is findable; one bad citation out of eight
#: is reported and costs that claim its status, which is punishment enough and already
#: automatic. Refusing the whole object for it would delete seven good claims to punish
#: one bad one.
MIN_CLAIMS_FOR_RATE = 20


@dataclass
class Check:
    name: str
    verdict: str
    detail: str
    data: dict = dc_field(default_factory=dict)

    @property
    def failed(self) -> bool:
        return self.verdict == FAIL


@dataclass
class Report:
    subject: str
    checks: list[Check] = dc_field(default_factory=list)

    @property
    def failures(self) -> list[Check]:
        return [c for c in self.checks if c.verdict == FAIL]

    @property
    def exit_code(self) -> int:
        return 1 if self.failures else 0

    def add(self, name: str, verdict: str, detail: str, **data) -> None:
        self.checks.append(Check(name, verdict, detail, data))


# --------------------------------------------------------------- shared checks
def _is_non_issuer(claim: dict) -> bool:
    dom = str(claim.get("independence_domain") or "").upper()
    if dom:
        return dom in NON_ISSUER_DOMAINS
    return str(claim.get("source_type") or "").upper() in NON_ISSUER_SOURCE_TYPES


def check_source_diversity(report: Report, claims: list[dict], label: str) -> None:
    """Refuse evidence that is ENTIRELY the issuers' own paperwork.

    The bar is `entirely`, not `mostly`, on purpose. A company batch legitimately rests
    on the companies' own filings for most of what it says - that is where the facts are.
    What cannot stand is an industry description with no outside source at all, which is
    what E79 produced 64 times.
    """
    if not claims:
        report.add(f"source_diversity[{label}]", SKIP, "no claims to profile")
        return
    outside = [c for c in claims if _is_non_issuer(c)]
    hosts = collections.Counter(RI._host(c.get("source_url")) for c in claims)
    top_host, top_n = (hosts.most_common(1) or [("", 0)])[0]
    share = top_n / len(claims)

    if not outside:
        report.add(f"source_diversity[{label}]", FAIL,
                   f"{len(claims)} claims and NOT ONE from a non-issuer source "
                   f"({', '.join(NON_ISSUER_DOMAINS)}); every host is "
                   f"{', '.join(sorted(h for h in hosts if h)[:3])}",
                   claims=len(claims), non_issuer=0, top_host=top_host)
        return
    verdict = WARN if share >= HOST_CONCENTRATION_WARN else PASS
    report.add(f"source_diversity[{label}]", verdict,
               f"{len(outside)}/{len(claims)} claims from a non-issuer source; "
               f"top host {top_host or '?'} carries {share:.1%}",
               claims=len(claims), non_issuer=len(outside),
               top_host=top_host, top_host_share=round(share, 4))


def check_containment(report: Report, claims: list[dict], label: str, *,
                      fetch: bool = True) -> None:
    """Test the batch's OWN citations against their OWN pages, before ingest.

    This is the single most expensive check here, because it fetches. It is also the one
    that moves the 2026-09-11 audit from a post-mortem into a gate: a claim that fails
    exact containment will be stored UNVERIFIABLE and contribute nothing, so finding that
    out now costs a re-emission and finding it out later costs a sector.
    """
    quoted = [c for c in claims if c.get("quote") and c.get("source_url")]
    if not quoted:
        report.add(f"exact_containment[{label}]", SKIP, "no quoted claims")
        return
    if not fetch:
        report.add(f"exact_containment[{label}]", SKIP,
                   f"{len(quoted)} quoted claims NOT tested (--no-fetch); "
                   f"this batch has not had its citations checked")
        return

    pages: dict[str, V.Fetched] = {}
    tested = certified = 0
    unreachable = 0
    failures = []
    for c in quoted:
        url = c["source_url"]
        if url not in pages:
            pages[url] = V.fetch(url)
        page = pages[url]
        if (not page.ok or page.unverifiable_reason
                or len(page.text) < V.MIN_PAGE_CHARS):
            unreachable += 1            # our failure to check, never the batch's fault
            continue
        m = V.match_quote(c["quote"], page.text)
        tested += 1
        if m.mode in V.CERTIFYING_MATCH_MODES:
            certified += 1
        else:
            failures.append({"claim_id": c.get("claim_id"), "field": c.get("field"),
                             "mode": m.mode, "overlap": m.overlap, "url": url,
                             "quote": (c.get("quote") or "")[:160]})
    if not tested:
        report.add(f"exact_containment[{label}]", SKIP,
                   f"none of {len(quoted)} quoted claims could be fetched "
                   f"({unreachable} unreachable) - could not check, not a failure")
        return

    rate = certified / tested
    if tested < MIN_CLAIMS_FOR_RATE:
        verdict = FAIL if certified == 0 else (WARN if failures else PASS)
        detail = (f"{certified}/{tested} citations found on their own page "
                  f"({unreachable} unreachable, not counted); under "
                  f"{MIN_CLAIMS_FOR_RATE} claims a rate is noise, so this refuses only "
                  f"when NOTHING cited is findable")
    else:
        verdict = FAIL if rate < MIN_CONTAINMENT_RATE else (
            WARN if failures else PASS)
        detail = (f"{certified}/{tested} = {rate:.1%} of citations found on their own "
                  f"page (floor {MIN_CONTAINMENT_RATE:.0%}; {unreachable} unreachable, "
                  f"not counted)")
    report.add(f"exact_containment[{label}]", verdict, detail,
               tested=tested, certified=certified, rate=round(rate, 4),
               unreachable=unreachable, failures=failures[:40])


# ------------------------------------------------------- Phase A: industry objects
def check_objects(report: Report, results: list[dict], *, store=None,
                  fetch: bool = True) -> None:
    """Phase A: does each object CONCLUDE anything, and is anything behind it."""
    from .store import ExternalStore
    st = store or ExternalStore(config.EXTERNAL_DB)
    with st.connect() as con:
        known = {r[0] for r in con.execute(
            "SELECT DISTINCT industry_id FROM industry_intelligence").fetchall()}
        sectors_with_objects = {r[0] for r in con.execute(
            "SELECT DISTINCT sector_id FROM industry_intelligence "
            "WHERE status IS NULL OR upper(status) != 'SUPERSEDED'").fetchall()}

    empty, thin, unsplit = [], [], []
    for r in results:
        obj = r.get("_obj") or {}
        iid = r.get("industry_id")
        answered = [f for f in S.INDUSTRY_ORDINALS
                    if obj.get(f) and str(obj[f]).strip().upper() != UNKNOWN]
        claims = obj.get("claims") or []
        ordinal_claims = [c for c in claims
                          if c.get("field") in S.INDUSTRY_ORDINALS]
        if len(answered) < BH.RETIRE_BELOW_ANSWERED:
            empty.append(iid)
        elif len(answered) < BH.REQUIRED_ANSWERED_FIELDS:
            thin.append(f"{iid} ({len(answered)}/3)")

        # A unit that is NEW inside a sector that already has objects is a unit that
        # appeared by splitting something. Rule 6: it may only exist if the researcher
        # can already evidence it, because the completeness gate deletes the pieces
        # otherwise and strands their companies.
        is_new_unit = iid not in known and obj.get("sector_id") in sectors_with_objects
        if is_new_unit and not ordinal_claims:
            unsplit.append(iid)

    if empty:
        report.add("structural_ordinals", FAIL,
                   f"{len(empty)} object(s) answer NONE of "
                   f"{S.INDUSTRY_ORDINALS}: {', '.join(sorted(empty))}. An object that "
                   f"concludes nothing gives the companies resolving to it nothing to "
                   f"be judged against - E61 shipped 25 of these",
                   objects=sorted(empty))
    elif thin:
        report.add("structural_ordinals", WARN,
                   f"every object answers at least one, but {len(thin)} are below "
                   f"3 of 3 and owe a written reason per UNKNOWN field: "
                   f"{', '.join(sorted(thin))}", objects=sorted(thin))
    else:
        report.add("structural_ordinals", PASS,
                   f"all {len(results)} objects answer all 3 structural fields")

    if unsplit:
        report.add("split_unit_evidence", FAIL,
                   f"{len(unsplit)} NEW unit(s) in a sector that already has objects "
                   f"carry no claim on any of {S.INDUSTRY_ORDINALS}: "
                   f"{', '.join(sorted(unsplit))}. A split without evidence in hand is "
                   f"strictly worse than no split: the gate deletes the pieces and "
                   f"strands their companies",
                   objects=sorted(unsplit))
    else:
        report.add("split_unit_evidence", PASS,
                   "every new unit carries at least one ordinal-supporting claim")

    for r in results:
        obj = r.get("_obj") or {}
        check_source_diversity(report, obj.get("claims") or [],
                               str(r.get("industry_id")))
    all_claims = [c for r in results for c in (r.get("_obj") or {}).get("claims") or []]
    check_containment(report, all_claims, "objects", fetch=fetch)


# -------------------------------------------------- Phase B: a company batch
#: Where a company row's categorical answers live, in the order `finalize.py` would read
#: them. `pass_a` is the WIRE shape a finished payload carries; `categoricals` is the
#: NORMALISED shape `finalize.py:193` writes out of it and `store.upsert_company` takes.
#: Reading only the latter is how this gate came to score every real payload at 0.0% fill
#: with all four rank-order fields "all-UNKNOWN" - the fields were right there, one level
#: down, and the `or c` fallback turned their absence into an answer.
#:
#: `categoricals` is FIRST on purpose. Where a row carries both, `categoricals` is what
#: will land: `finalize` filters `pass_a` through ALLOWED_CATEGORICALS, so the two can
#: legitimately differ and the gate must grade the one the store will hold. The rule this
#: encodes, from ACCEPTANCE_GATE_FALSE_REJECT_2026-09-11: an acceptance check reads a
#: payload through the same accessor the finalizer uses, or it grades a different object
#: than the one that lands.
_ROW_FIELD_HOLDERS = ("categoricals", "pass_a")


def _row_fields(c: dict) -> dict:
    """The dict carrying one company's categorical answers.

    Falls through to the row itself so an already-flat row still reads, and merges
    rather than picks so a payload that splits fields across `pass_a` and `pass_b`
    does not lose half of them.
    """
    held = [c[k] for k in _ROW_FIELD_HOLDERS if isinstance(c.get(k), dict)]
    if not held:
        return c
    merged: dict = {}
    for d in reversed(held):
        merged.update(d)
    return merged


def _book_ids() -> dict[str, dict]:
    """ticker -> taxonomy ids, from the live book. Resolved exactly as `request.py`
    resolves them when the roster is built, so the gate groups a batch the same way
    the ingest will store it."""
    import pandas as pd

    from . import taxonomy as T

    try:
        df = pd.read_parquet(config.SCORES_PARQUET)
    except Exception:
        return {}
    return {str(r["ticker"]): T.resolve(str(r["ticker"]), r.get("sector"),
                                       r.get("sub_industry"))
            for r in df.to_dict("records")}


def _payload_rows(payload: dict, *, book: dict | None = None) -> list[dict]:
    """Company rows flattened to the shape `batch_health._fill` reads.

    A payload names its companies by ticker and does NOT carry their taxonomy ids -
    `research_ingest` resolves those on the way in. This gate runs one step EARLIER
    than that, so it resolves them itself; without this, `sector_id` is None for every
    row, the four-field comparison has no sector to compare against and SKIPs, and the
    abstention collapse this gate exists to catch walks straight through it.
    """
    rows = []
    ids = None
    for c in payload.get("companies") or []:
        cats = _row_fields(c)
        ticker = c.get("ticker")
        sector_id, industry_id = c.get("sector_id"), c.get("industry_id")
        if not (sector_id and industry_id) and ticker:
            if ids is None:
                ids = book if book is not None else _book_ids()
            resolved = ids.get(str(ticker)) or {}
            sector_id = sector_id or resolved.get("sector_id")
            industry_id = industry_id or resolved.get("industry_id")
        row = {"ticker": ticker, "industry_id": industry_id, "sector_id": sector_id}
        for f in S.COMPANY_ORDINALS:
            row[f] = cats.get(f)
        rows.append(row)
    return rows


def check_company_batch(report: Report, payload: dict, *, store=None,
                        fetch: bool = True, book: dict | None = None) -> None:
    from .store import ExternalStore
    st = store or ExternalStore(config.EXTERNAL_DB)
    rows = _payload_rows(payload, book=book)
    if not rows:
        report.add("batch_rows", FAIL, "payload contains no companies")
        return
    sectors = collections.Counter(r.get("sector_id") for r in rows if r.get("sector_id"))
    sector_id = sectors.most_common(1)[0][0] if sectors else None

    # ---- four-field fill against the SAME SECTOR's previous batch
    base_all = st.latest_companies()
    base = [r for r in base_all if r.get("sector_id") == sector_id] if sector_id else []
    b_rate, b_n = BH._rate(rows, BH.RANK_ORDER_FIELDS)
    p_rate, p_n = BH._rate(base, BH.RANK_ORDER_FIELDS)

    if p_rate is None or not base:
        report.add("four_field_fill", SKIP,
                   f"no previous {sector_id or '?'} batch to compare against; "
                   f"this batch fills {b_rate if b_rate is None else f'{b_rate:.1%}'} "
                   f"of the four rank-order fields",
                   batch_fill=b_rate, sector_id=sector_id)
    else:
        # Within-industry where the industries overlap - the number that holds the peer
        # set and the industry object fixed. Pooled is reported beside it and is
        # confounded by industry mix even inside one sector.
        by_b, by_p = collections.defaultdict(list), collections.defaultdict(list)
        for r in rows:
            by_b[r.get("industry_id")].append(r)
        for r in base:
            by_p[r.get("industry_id")].append(r)
        deltas = []
        for ind in sorted(set(by_b) & set(by_p)):
            if len(by_b[ind]) < BH.MIN_SHARED or len(by_p[ind]) < BH.MIN_SHARED:
                continue
            br, _ = BH._rate(by_b[ind], BH.RANK_ORDER_FIELDS)
            pr, _ = BH._rate(by_p[ind], BH.RANK_ORDER_FIELDS)
            if br is not None and pr is not None:
                deltas.append({"industry_id": ind, "batch": round(br, 3),
                               "baseline": round(pr, 3), "delta": round(br - pr, 3)})
        within = (round(sum(d["delta"] for d in deltas) / len(deltas), 3)
                  if deltas else None)
        headline = within if within is not None else round(b_rate - p_rate, 3)
        basis = "within-industry" if within is not None else "pooled (no shared industry)"
        verdict = FAIL if headline <= -BH.REGRESSION_DROP else PASS
        report.add("four_field_fill", verdict,
                   f"{sector_id}: {p_rate:.1%} -> {b_rate:.1%}, {basis} delta "
                   f"{headline:+.3f} (refuses at {-BH.REGRESSION_DROP:+.2f}). These four "
                   f"fields carry 45 of the 100 external points and went 92% -> 0% over "
                   f"eight unwatched batches",
                   batch_fill=round(b_rate, 4), baseline_fill=round(p_rate, 4),
                   within_industry_delta=within, per_industry=deltas,
                   sector_id=sector_id)

    # ---- constant fields: the E30 symptom, one layer up
    constants = _constant_fields_in_rows(rows)
    rank_order_dead = [c for c in constants["all_unknown"]
                       if c["field"] in BH.RANK_ORDER_FIELDS]
    if rank_order_dead:
        report.add("constant_fields", FAIL,
                   "rank-order field(s) all-UNKNOWN across the whole batch: "
                   + ", ".join(f"{c['field']} ({c['n']} rows)" for c in rank_order_dead)
                   + ". A sector can honestly answer UNKNOWN to market share; it cannot "
                     "honestly answer UNKNOWN to its own competitive position for every "
                     "company in a batch",
                   all_unknown=constants["all_unknown"])
    elif constants["all_unknown"] or constants["single_value"]:
        report.add("constant_fields", WARN,
                   "constant across the batch - a finding, or a stuck derivation "
                   "(`bs_dilution` was dead in all eleven sectors and constancy was the "
                   "only visible trace): "
                   + "; ".join(f"{c['field']}={c['value']} ({c['n']})"
                               for c in constants["all_unknown"]
                               + constants["single_value"]),
                   **constants)
    elif constants["checked"]:
        report.add("constant_fields", PASS,
                   f"no field is constant across {len(rows)} rows "
                   f"({constants['checked']} fields checked)")
    else:
        report.add("constant_fields", SKIP,
                   f"{len(rows)} rows < {BH.CONSTANT_MIN_ROWS}; constancy is not "
                   f"measurable")

    claims = [c for row in payload.get("companies") or []
              for c in (row.get("claims") or [])]
    check_source_diversity(report, claims, "batch")
    check_containment(report, claims, "batch", fetch=fetch)


def _constant_fields_in_rows(rows: list[dict]) -> dict:
    """`batch_health.constant_fields`, computed on a payload instead of the store.

    Same rule, same NOT_APPLICABLE exclusion, same minimum row count - moved one step
    earlier so it can refuse rather than describe.
    """
    from . import applicability as AP
    out = {"all_unknown": [], "single_value": [], "checked": 0, "n_rows": len(rows)}
    if len(rows) < BH.CONSTANT_MIN_ROWS:
        return out
    for f in S.COMPANY_ORDINALS:
        vals = [r.get(f) for r in rows
                if not AP.is_not_applicable(r.get("industry_id"), f, r.get(f))]
        vals = [(str(v).strip().upper() if v else UNKNOWN) for v in vals]
        if len(vals) < BH.CONSTANT_MIN_ROWS:
            continue
        out["checked"] += 1
        distinct = set(vals)
        if len(distinct) != 1:
            continue
        only = distinct.pop()
        rec = {"field": f, "value": only, "n": len(vals)}
        out["all_unknown" if only == UNKNOWN else "single_value"].append(rec)
    return out


# ------------------------------------------------------------------ entry points
def accept_objects(results: list[dict] | None = None, *, store=None,
                   fetch: bool = True) -> Report:
    results = RI.load_and_validate() if results is None else results
    report = Report(f"phase A: {len(results)} industry object(s)")
    invalid = [r["industry_id"] for r in results if not r.get("ok")]
    if invalid:
        report.add("schema", FAIL,
                   f"{len(invalid)} object(s) fail schema validation: "
                   f"{', '.join(sorted(invalid))}", objects=sorted(invalid))
    else:
        report.add("schema", PASS, f"all {len(results)} objects validate")
    check_objects(report, results, store=store, fetch=fetch)
    return report


def accept_payload(payload_path: Path, *, store=None, fetch: bool = True) -> Report:
    payload = json.loads(Path(payload_path).read_text(encoding="utf-8"))
    n = len(payload.get("companies") or [])
    report = Report(f"phase B: {payload_path.name}, {n} compan(ies)")
    check_company_batch(report, payload, store=store, fetch=fetch)
    return report


def containment_history(*, store=None) -> list[dict]:
    """Exact-containment rate per ingested batch, from the store's recorded match_mode.

    Grouped by `request_id`, which IS the batch. The first draft joined claims to
    `company_external` on ticker and grouped by `research_version`: claims are not
    versioned, so every claim was counted once per arm the ticker appears in and E47's
    59 utilities reported 1,475 tested. A count that can exceed its own population is
    the symptom; group by the key that identifies the batch.

    Reads `match_mode`, so it is empty until `verify --restate` has run.
    """
    from .store import ExternalStore
    st = store or ExternalStore(config.EXTERNAL_DB)
    with st.connect() as con:
        rows = con.execute(
            "SELECT COALESCE(request_id, '(none)') AS batch, count(*) AS n, "
            "       sum(CASE WHEN match_mode IN (?, ?) THEN 1 ELSE 0 END) AS ok "
            "FROM external_claim WHERE match_mode IS NOT NULL "
            "GROUP BY 1 ORDER BY 3.0 / n",
            [V.MATCH_EXACT, V.MATCH_NO_WHITESPACE]).fetchall()
    return [{"batch": r[0], "tested": r[1], "certified": r[2],
             "rate": round(r[2] / r[1], 4) if r[1] else None} for r in rows]


def render(report: Report) -> str:
    lines = [f"ACCEPTANCE - {report.subject}", ""]
    order = {FAIL: 0, WARN: 1, SKIP: 2, PASS: 3}
    for c in sorted(report.checks, key=lambda c: (order[c.verdict], c.name)):
        lines.append(f"[{c.verdict:<4}] {c.name}")
        lines.append(f"        {c.detail}")
        for f in (c.data.get("failures") or [])[:10]:
            lines.append(f"          - {f['claim_id']} {f['field']} {f['mode']} "
                         f"overlap {f['overlap']}  {f['url'][:70]}")
    lines.append("")
    if report.failures:
        lines.append(f"REFUSED: {len(report.failures)} check(s) failed - "
                     + ", ".join(c.name for c in report.failures))
    else:
        lines.append("ACCEPTED: no check failed. Warnings above are for the researcher, "
                     "not the gate.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Accept or refuse one batch, before it is ingested")
    ap.add_argument("--payload", type=Path, default=None,
                    help="a company batch payload; omit to check the staged Phase A "
                         "industry objects")
    ap.add_argument("--no-fetch", action="store_true",
                    help="skip the exact-containment check (it fetches every cited url)")
    ap.add_argument("--containment-history", action="store_true",
                    help="per-batch containment rate from the store, for calibration")
    ap.add_argument("--json", type=Path, default=None, help="write the full report")
    args = ap.parse_args(argv)

    if args.containment_history:
        print(f"{'batch':<36}{'tested':>8}{'certified':>11}{'rate':>8}")
        for h in containment_history():
            rate = "-" if h["rate"] is None else f"{100 * h['rate']:.1f}%"
            print(f"{h['batch']:<36}{h['tested']:>8}{h['certified']:>11}{rate:>8}")
        return 0

    if not args.no_fetch:
        from .. import net
        net.trust_windows_certs()

    report = (accept_payload(args.payload, fetch=not args.no_fetch)
              if args.payload else accept_objects(fetch=not args.no_fetch))
    print(render(report))
    if args.json:
        from .. import net
        net.atomic_write_json(args.json, {
            "subject": report.subject,
            "exit_code": report.exit_code,
            "checks": [vars(c) for c in report.checks]})
        print(f"\nfull report: {args.json}")
    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
