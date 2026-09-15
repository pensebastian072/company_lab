"""DuckDB store for external intelligence.

company_lab has had no database for its whole life - parquet, gzipped JSON, and a
scorecard file per company. That is the right shape for a book that is rebuilt whole
each crawl. It is the wrong shape for research that arrives in fragments, is reused
across companies, expires on three different clocks, and has to answer "what do we
already know, and when did we learn it?" before spending anything.

Idiom borrowed intact from futures_intelligence/storage/manifest.py, including the
parts that look like fussiness and are not:

* **A connection per call, never a long-lived one.** Windows holds file locks, and a
  held connection turns "the UI is open" into "the ingest cannot write".
* **The DB is a CATALOG, not a second copy of the data.** Payloads stay as JSON on
  disk; the parquet book stays the book. What lives here is the structured record, the
  claim index, the manifests and the ledgers - the things you need to query across
  companies and across time.
* **`fail()` stores `type(exc).__name__`, never the message.** An exception message
  can carry a URL, a key, or a chunk of someone's filing. A catalog is not the place
  to find out.

Everything is keyed by (ticker, research_version) so a re-research never overwrites the
record it should be compared against.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .. import config
from .industry_versions import active_industry_rows
from .schema import Claim, EXTERNAL_SCHEMA_VERSION

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS company_external (
    ticker VARCHAR NOT NULL,
    research_version VARCHAR NOT NULL,
    cik VARCHAR,
    sector_id VARCHAR,
    industry_id VARCHAR,
    subindustry_id VARCHAR,
    current_moat_strength VARCHAR,
    moat_trajectory VARCHAR,
    competitive_position VARCHAR,
    competitive_position_trend VARCHAR,
    industry_structural_growth VARCHAR,
    company_specific_capture VARCHAR,
    demand_visibility VARCHAR,
    market_share_direction VARCHAR,
    pricing_power VARCHAR,
    technology_risk VARCHAR,
    disruption_risk VARCHAR,
    regulatory_risk VARCHAR,
    cheapness_quality VARCHAR,
    why_is_it_cheap VARCHAR,
    bull_case VARCHAR,
    bear_case VARCHAR,
    major_thesis_risk VARCHAR,
    thesis_break_condition VARCHAR,
    key_monitoring_variables VARCHAR,
    external_score DOUBLE,
    external_confidence DOUBLE,
    -- Peer POSITION, computed from revenue share of the listed peer set. Deliberately
    -- separate from `market_share_direction`, which asks a different question: whether
    -- CONTESTABLE share moved. A rate-regulated utility has no contestable share and
    -- market_share_direction is NOT_APPLICABLE for it, but "who is biggest in this
    -- product market and who is growing" is answerable for every industry and is real
    -- information. Conflating the two threw that away for 54 of 59 utilities.
    -- Reported, NOT scored: these earn no points pending an argument that they should.
    peer_revenue_share DOUBLE,
    peer_share_rank INTEGER,
    peer_share_n INTEGER,
    peer_growth_direction VARCHAR,
    peer_growth_vs_median DOUBLE,
    research_depth INTEGER,
    distinct_domains INTEGER,
    claims_total INTEGER,
    claims_verified INTEGER,
    claims_self_attested INTEGER,
    claims_unverifiable INTEGER,
    flags VARCHAR,
    request_id VARCHAR,
    external_schema_version VARCHAR,
    last_research_date TIMESTAMPTZ,
    next_refresh_due DATE,
    refresh_class VARCHAR,
    status VARCHAR,
    superseded_by VARCHAR,
    superseded_reason VARCHAR,
    superseded_at TIMESTAMPTZ,
    PRIMARY KEY (ticker, research_version)
);

CREATE TABLE IF NOT EXISTS external_claim (
    claim_id VARCHAR PRIMARY KEY,
    ticker VARCHAR,
    industry_id VARCHAR,
    field VARCHAR NOT NULL,
    text VARCHAR NOT NULL,
    source_url VARCHAR,
    source_title VARCHAR,
    source_date DATE,
    source_type VARCHAR,
    independence_domain VARCHAR,
    quote VARCHAR,
    excerpt_sha1 VARCHAR,
    stance VARCHAR,
    fact_or_inference VARCHAR,
    verify_status VARCHAR,
    overlap DOUBLE,
    verify_reason VARCHAR,
    request_id VARCHAR,
    created_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS industry_intelligence (
    industry_id VARCHAR NOT NULL,
    version VARCHAR NOT NULL,
    sector_id VARCHAR,
    brief VARCHAR,
    structural_growth VARCHAR,
    moat_mechanism VARCHAR,
    replication_difficulty VARCHAR,
    substitution_risk VARCHAR,
    key_metrics VARCHAR,
    refresh_class VARCHAR,
    last_updated TIMESTAMPTZ,
    next_refresh_due DATE,
    PRIMARY KEY (industry_id, version)
);

CREATE TABLE IF NOT EXISTS sector_brief (
    sector_id VARCHAR NOT NULL,
    version VARCHAR NOT NULL,
    brief VARCHAR,
    what_changed VARCHAR,
    winners VARCHAR,
    losers VARCHAR,
    capital_cycle VARCHAR,
    metrics_that_matter VARCHAR,
    last_updated TIMESTAMPTZ,
    PRIMARY KEY (sector_id, version)
);

CREATE TABLE IF NOT EXISTS research_manifest (
    request_id VARCHAR PRIMARY KEY,
    generated_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    roster_sha1 VARCHAR,
    spec_fingerprint VARCHAR,
    depth INTEGER,
    status VARCHAR,
    n_requested INTEGER,
    n_returned INTEGER,
    n_rejected INTEGER,
    cost_tokens BIGINT,
    cost_searches INTEGER,
    error_type VARCHAR,
    base_book VARCHAR,
    company_lab_version VARCHAR,
    external_schema_version VARCHAR,
    local_llm_model VARCHAR,
    local_llm_prompt_version VARCHAR
);

CREATE TABLE IF NOT EXISTS reconciliation_ledger (
    ticker VARCHAR,
    component VARCHAR,
    subtest VARCHAR,
    before_points INTEGER,
    after_points INTEGER,
    delta INTEGER,
    rule_id VARCHAR,
    claim_ids VARCHAR,
    request_id VARCHAR,
    applied_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS priority_ledger (
    ticker VARCHAR,
    run_date DATE,
    arm VARCHAR,
    priority_score DOUBLE,
    inputs_json VARCHAR,
    selected BOOLEAN,
    seed BIGINT
);
"""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _json(value: Any) -> str | None:
    """Lists and dicts go into VARCHAR columns as JSON, not as `str(list)`.

    `str(["a"])` round-trips to the string "['a']", which no reader can parse back and
    which silently becomes a one-element list of garbage in the workbook.
    """
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


class ExternalStore:
    """Catalog over the external-intelligence layer.

    Every method opens and closes its own connection. That is deliberate on this box:
    a held DuckDB handle blocks other writers under Windows file locking, and the
    ingest, the exporter and an interactive query all want the same file.
    """

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path is not None else config.EXTERNAL_DB
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as con:
            con.execute(SCHEMA_SQL)
            self._migrate(con)

    #: Columns added after the first databases were created. CREATE TABLE IF NOT EXISTS
    #: does nothing to a table that already exists, so a new column is invisible in every
    #: live database until it is added explicitly - and the failure is silent: the write
    #: succeeds and the value is simply not there. Additive only; nothing here ever drops
    #: or retypes a column.
    _ADDED_COLUMNS = (
        # Lifecycle for an industry object that a later re-cut replaced. RETIRED
        # OPERATIONALLY, RETAINED EVIDENTIALLY: the row, its brief and its verified
        # claims all stay for audit, and only the ACTIVE corpus excludes it.
        ("industry_intelligence", "status", "VARCHAR"),
        ("industry_intelligence", "superseded_by", "VARCHAR"),
        ("industry_intelligence", "superseded_reason", "VARCHAR"),
        ("industry_intelligence", "superseded_at", "TIMESTAMPTZ"),
        # Lifecycle for a company research arm that was rejected after ingest. The
        # row and its claims remain queryable by explicit research_version; unscoped
        # operational readers use latest_companies() and do not see it.
        ("company_external", "status", "VARCHAR"),
        ("company_external", "superseded_by", "VARCHAR"),
        ("company_external", "superseded_reason", "VARCHAR"),
        ("company_external", "superseded_at", "TIMESTAMPTZ"),
        ("company_external", "peer_revenue_share", "DOUBLE"),
        ("company_external", "peer_share_rank", "INTEGER"),
        ("company_external", "peer_share_n", "INTEGER"),
        ("company_external", "peer_growth_direction", "VARCHAR"),
        ("company_external", "peer_growth_vs_median", "DOUBLE"),
        # Why the verifier could not accept a fetched source. This is distinct from
        # network failure: pdf_not_extracted means we fetched bytes but never obtained
        # text that a quote could be checked against.
        ("external_claim", "verify_reason", "VARCHAR"),
        # HOW the quote matched its page: exact / no_whitespace certify, overlap_only,
        # numeric_mismatch, absent and unreadable do not. Recorded per claim so the
        # STRENGTH of VERIFIED_LOCAL is queryable instead of needing an audit to
        # re-derive it - see clab/external/verify.py:match_quote.
        ("external_claim", "match_mode", "VARCHAR"),
    )

    @classmethod
    def _migrate(cls, con) -> None:
        for table, column, sqltype in cls._ADDED_COLUMNS:
            try:
                con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {sqltype}")
            except Exception:
                pass                        # already present

    def connect(self):
        import duckdb                      # local: keeps import cost off cold paths
        return duckdb.connect(str(self.path))

    # ------------------------------------------------------------- manifests
    def begin(self, request: dict, *, base_book: str | None = None,
              local_llm_model: str | None = None,
              local_llm_prompt_version: str | None = None) -> str:
        """Record a request as pending. Idempotent on request_id."""
        request_id = request["request_id"]
        with self.connect() as con:
            con.execute(
                """
                INSERT INTO research_manifest
                    (request_id, generated_at, roster_sha1, spec_fingerprint, depth,
                     status, n_requested, base_book, external_schema_version,
                     local_llm_model, local_llm_prompt_version)
                VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?)
                ON CONFLICT (request_id) DO UPDATE SET
                    generated_at = excluded.generated_at,
                    roster_sha1 = excluded.roster_sha1,
                    spec_fingerprint = excluded.spec_fingerprint,
                    depth = excluded.depth,
                    status = 'pending',
                    n_requested = excluded.n_requested
                """,
                [request_id, request.get("generated_at"), request.get("roster_sha1"),
                 request.get("spec_fingerprint"), request.get("depth"),
                 len(request.get("roster") or []), base_book,
                 EXTERNAL_SCHEMA_VERSION, local_llm_model, local_llm_prompt_version],
            )
        return request_id

    def complete(self, request_id: str, *, n_returned: int, n_rejected: int,
                 cost_tokens: int = 0, cost_searches: int = 0) -> None:
        with self.connect() as con:
            con.execute(
                """
                UPDATE research_manifest SET
                    status = 'complete', completed_at = ?, n_returned = ?,
                    n_rejected = ?, cost_tokens = ?, cost_searches = ?
                WHERE request_id = ?
                """,
                [_now(), n_returned, n_rejected, cost_tokens, cost_searches,
                 request_id],
            )

    def fail(self, request_id: str, exc: BaseException) -> None:
        """Record a failure by exception TYPE only.

        An exception message can carry a source URL, a chunk of a filing, or a path
        into someone else's data. The catalog is not where that should surface.
        """
        with self.connect() as con:
            con.execute(
                "UPDATE research_manifest SET status = 'failed', completed_at = ?, "
                "error_type = ? WHERE request_id = ?",
                [_now(), type(exc).__name__, request_id],
            )

    def manifest(self, request_id: str) -> dict | None:
        with self.connect() as con:
            cur = con.execute(
                "SELECT * FROM research_manifest WHERE request_id = ?", [request_id])
            row = cur.fetchone()
            if row is None:
                return None
            return dict(zip([d[0] for d in cur.description], row))

    # ------------------------------------------------------------- companies
    def upsert_company(self, row: dict) -> None:
        """Write one finalized company record.

        Keyed by (ticker, research_version): a later run never overwrites the record a
        comparison is being made against.
        """
        cols = [
            "ticker", "research_version", "cik", "sector_id", "industry_id",
            "subindustry_id", "current_moat_strength", "moat_trajectory",
            "competitive_position", "competitive_position_trend",
            "industry_structural_growth", "company_specific_capture",
            "demand_visibility", "market_share_direction", "pricing_power",
            "technology_risk", "disruption_risk", "regulatory_risk",
            "cheapness_quality", "why_is_it_cheap", "bull_case", "bear_case",
            "major_thesis_risk", "thesis_break_condition", "key_monitoring_variables",
            "external_score", "external_confidence",
            "peer_revenue_share", "peer_share_rank", "peer_share_n",
            "peer_growth_direction", "peer_growth_vs_median",
            "research_depth",
            "distinct_domains", "claims_total", "claims_verified",
            "claims_self_attested", "claims_unverifiable", "flags", "request_id",
            "external_schema_version", "last_research_date", "next_refresh_due",
            "refresh_class",
        ]
        values = [_json(row.get(c)) if c in ("key_monitoring_variables", "flags")
                  else row.get(c) for c in cols]
        updates = ", ".join(f"{c} = excluded.{c}" for c in cols
                            if c not in ("ticker", "research_version"))
        with self.connect() as con:
            con.execute(
                f"INSERT INTO company_external ({', '.join(cols)}) "
                f"VALUES ({', '.join('?' * len(cols))}) "
                f"ON CONFLICT (ticker, research_version) DO UPDATE SET {updates}",
                values,
            )

    def company(self, ticker: str, research_version: str) -> dict | None:
        with self.connect() as con:
            cur = con.execute(
                "SELECT * FROM company_external WHERE ticker = ? "
                "AND research_version = ?", [ticker, research_version])
            row = cur.fetchone()
            if row is None:
                return None
            return dict(zip([d[0] for d in cur.description], row))

    def companies(self, research_version: str) -> list[dict]:
        """Every row in one explicitly named arm, including a superseded arm.

        Explicit version means audit intent. Operational readers that want the current
        corpus must call latest_companies() instead.
        """
        with self.connect() as con:
            cur = con.execute(
                "SELECT * FROM company_external WHERE research_version = ? "
                "ORDER BY ticker", [research_version])
            names = [d[0] for d in cur.description]
            return [dict(zip(names, r)) for r in cur.fetchall()]

    def company_records(self, *, include_superseded: bool = False) -> list[dict]:
        """All company-version rows, active by default and historical on request."""
        sql = "SELECT * FROM company_external"
        if not include_superseded:
            sql += " WHERE coalesce(upper(status), '') != 'SUPERSEDED'"
        sql += " ORDER BY ticker, research_version"
        with self.connect() as con:
            cur = con.execute(sql)
            names = [d[0] for d in cur.description]
            return [dict(zip(names, r)) for r in cur.fetchall()]

    def latest_companies(self, *, before_version: str | None = None,
                         include_superseded: bool = False) -> list[dict]:
        """Latest row per ticker for unscoped operational readers. NO FALLBACK.

        If a ticker's NEWEST arm is SUPERSEDED, that company has no current research and
        is omitted. It does not fall back to an older accepted arm.

        This used to fall back, and the fallback did real damage. E53 re-ran Utilities on
        the symmetric prompt and was later retired for a B3 evidence defect with no
        replacement; selection then served all 59 utilities their pre-fix E47 arm, and on
        the four rank-order fields that carry 45 of the 100 external points that arm reads
        **20 of 236 answered (8.5%) against E53's 155 of 236 (65.7%)**. The corpus
        silently regressed to the abstention collapse E51 and E53 existed to repair, and
        nothing announced it.

        The rule is now the same one `industry()` already follows: a retired newest
        version means retired, not "use the previous one". A company that drops out is
        visible; a company quietly served worse research is not.

        `include_superseded=True` returns the newest row whatever its lifecycle state, for
        audit. `before_version` gives batch-health a baseline fixed strictly before the arm
        under test.
        """
        # Select the newest row per ticker from EVERY row, then drop the ticker if that
        # newest row is retired. Filtering superseded rows out FIRST is what produced the
        # fallback - the older arm simply became the newest surviving candidate.
        rows = self.company_records(include_superseded=True)
        if before_version is not None:
            rows = [r for r in rows
                    if str(r.get("research_version") or "") < before_version]

        latest: dict[str, tuple[tuple[str, str], dict]] = {}
        for row in rows:
            ticker = str(row.get("ticker") or "")
            key = (str(row.get("last_research_date") or ""),
                   str(row.get("research_version") or ""))
            current = latest.get(ticker)
            if current is None or key > current[0]:
                latest[ticker] = (key, row)

        if include_superseded:
            return [latest[t][1] for t in sorted(latest)]

        # A retired newest arm is resolved by FOLLOWING superseded_by, never by dropping
        # to whatever happens to be next in the list.
        #
        #   named replacement that exists -> serve it. E59 batch 1 was burned and names
        #       its rerun; the rerun is the company's current research. Note the rerun
        #       does not always SORT newer, so "next newest row" is not the same answer.
        #   no replacement, or a named one that is absent -> OMIT the company. It has no
        #       current research, and saying so is the point.
        by_version: dict[tuple[str, str], dict] = {}
        for row in rows:
            by_version[(str(row.get("ticker") or ""),
                        str(row.get("research_version") or ""))] = row

        out = []
        for ticker in sorted(latest):
            row = latest[ticker][1]
            seen = set()
            while str(row.get("status") or "").upper() == "SUPERSEDED":
                nxt = str(row.get("superseded_by") or "")
                if not nxt or (ticker, nxt) in seen:
                    row = None
                    break
                seen.add((ticker, nxt))
                row = by_version.get((ticker, nxt))
                if row is None:
                    break
            if row is not None:
                out.append(row)
        return out

    def supersede_company_version(self, research_version: str, *,
                                  reason: str,
                                  superseded_by: str | None = None) -> int:
        """Retire one research arm without deleting its company rows or claims."""
        version = str(research_version or "").strip()
        why = str(reason or "").strip()
        replacement = str(superseded_by or "").strip() or None
        if not version:
            raise ValueError("research_version is required")
        if not why:
            raise ValueError("superseded reason is required")
        if replacement == version:
            raise ValueError("a company research version cannot supersede itself")

        with self.connect() as con:
            n = con.execute(
                "SELECT count(*) FROM company_external WHERE research_version = ? "
                "AND (coalesce(upper(status), '') != 'SUPERSEDED' "
                "OR superseded_by IS DISTINCT FROM ? "
                "OR superseded_reason IS DISTINCT FROM ?)",
                [version, replacement, why],
            ).fetchone()[0]
            if n:
                con.execute(
                    "UPDATE company_external SET status = 'SUPERSEDED', "
                    "superseded_by = ?, superseded_reason = ?, superseded_at = ? "
                    "WHERE research_version = ? "
                    "AND (coalesce(upper(status), '') != 'SUPERSEDED' "
                    "OR superseded_by IS DISTINCT FROM ? "
                    "OR superseded_reason IS DISTINCT FROM ?)",
                    [replacement, why, _now(), version, replacement, why],
                )
        return n

    def known_tickers(self, research_version: str) -> set[str]:
        with self.connect() as con:
            return {r[0] for r in con.execute(
                "SELECT ticker FROM company_external WHERE research_version = ?",
                [research_version]).fetchall()}

    # ---------------------------------------------------------------- claims
    def insert_claims(self, claims: Iterable[Claim], *, request_id: str,
                      excerpt_sha1: dict[str, str] | None = None) -> int:
        """Insert or refresh claims WITHOUT ever downgrading a verification.

        Note what is NOT stored: the excerpt itself. Only its sha1. The excerpt exists
        to check the quote against, and keeping megabytes of scraped page text in the
        catalog would make it a content store, which it is not.

        The `ON CONFLICT` clause is the load-bearing part. This method was
        `INSERT OR REPLACE`, and the ingest path builds every claim as SELF_ATTESTED,
        so re-running `research_ingest --apply` after `verify.py` had done its work
        would have silently reset all 90 VERIFIED_LOCAL rows to SELF_ATTESTED - hours
        of fetching thrown away by a command whose output said "written". Only
        verify.py may set VERIFIED_LOCAL or UNVERIFIABLE, and only verify.py may clear
        them; an ingest carries the research forward and leaves the verdict alone.
        """
        excerpt_sha1 = excerpt_sha1 or {}
        rows = []
        now = _now()
        for c in claims:
            rows.append([
                c.claim_id, c.ticker, c.industry_id, c.field, c.text, c.source_url,
                c.source_title, c.source_date, c.source_type, c.independence_domain,
                c.quote, excerpt_sha1.get(c.claim_id), c.stance, c.fact_or_inference,
                c.verify_status, c.overlap, request_id, now,
            ])
        if not rows:
            return 0
        with self.connect() as con:
            con.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_claim_id "
                        "ON external_claim (claim_id)")
            con.executemany(
                "INSERT INTO external_claim "
                "(claim_id, ticker, industry_id, field, text, source_url, "
                " source_title, source_date, source_type, independence_domain, quote, "
                " excerpt_sha1, stance, fact_or_inference, verify_status, overlap, "
                " request_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT (claim_id) DO UPDATE SET "
                "  ticker = excluded.ticker, industry_id = excluded.industry_id, "
                "  field = excluded.field, text = excluded.text, "
                "  source_url = excluded.source_url, "
                "  source_title = excluded.source_title, "
                "  source_date = excluded.source_date, "
                "  source_type = excluded.source_type, "
                "  independence_domain = excluded.independence_domain, "
                "  quote = excluded.quote, excerpt_sha1 = excluded.excerpt_sha1, "
                "  stance = excluded.stance, "
                "  fact_or_inference = excluded.fact_or_inference, "
                "  request_id = excluded.request_id",
                # verify_status and overlap are DELIBERATELY ABSENT from this update.
                # This method is the ingest path and nothing else; `verify.py` reaches
                # verdicts through its own UPDATE. Keying the rule on who writes rather
                # than on what value arrives is what makes it hold: an earlier draft
                # preserved the row only when the incoming status was SELF_ATTESTED,
                # which silently let `Claim`'s UNVERIFIABLE default clobber a real
                # verdict the moment anyone built a Claim without naming a status.
                rows,
            )
        return len(rows)

    def claims_for(self, ticker: str) -> list[dict]:
        with self.connect() as con:
            cur = con.execute(
                "SELECT * FROM external_claim WHERE ticker = ? "
                "ORDER BY field, claim_id", [ticker])
            names = [d[0] for d in cur.description]
            return [dict(zip(names, r)) for r in cur.fetchall()]

    def verify_rates(self, request_id: str | None = None) -> dict[str, int]:
        """Counts by verify_status. This is the number reported beside every score."""
        sql = "SELECT verify_status, count(*) FROM external_claim"
        args: list = []
        if request_id:
            sql += " WHERE request_id = ?"
            args.append(request_id)
        sql += " GROUP BY verify_status"
        with self.connect() as con:
            return dict(con.execute(sql, args).fetchall())

    # -------------------------------------------------- sectors / industries
    def upsert_industry(self, row: dict) -> None:
        cols = ["industry_id", "version", "sector_id", "brief", "structural_growth",
                "moat_mechanism", "replication_difficulty", "substitution_risk",
                "key_metrics", "refresh_class", "last_updated", "next_refresh_due"]
        values = [_json(row.get(c)) if c == "key_metrics" else row.get(c) for c in cols]
        updates = ", ".join(f"{c} = excluded.{c}" for c in cols
                            if c not in ("industry_id", "version"))
        with self.connect() as con:
            con.execute(
                f"INSERT INTO industry_intelligence ({', '.join(cols)}) "
                f"VALUES ({', '.join('?' * len(cols))}) "
                f"ON CONFLICT (industry_id, version) DO UPDATE SET {updates}",
                values,
            )

    def industry(self, industry_id: str, version: str | None = None, *,
                 include_superseded: bool = False) -> dict | None:
        """The ACTIVE industry object, a named version, or None.

        Two things this deliberately does NOT do by default.

        It does not return a SUPERSEDED object or fall back to an older version when the
        newest version is SUPERSEDED. E56 re-cut three Financials buckets that had
        returned UNKNOWN on all three industry fields; retiring the newest record
        retires the object. `include_superseded=True` returns that newest record anyway,
        for audit.

        It does not order versions by string compare. `ORDER BY version DESC` puts
        "2026-09-02.10" below "2026-09-02.9", so the tenth re-cut of a day would lose to
        the ninth. Ordering happens in Python on a parsed key instead.

        A named `version` is returned whatever its status - asking for a specific one is
        asking for that one.
        """
        with self.connect() as con:
            if version:
                cur = con.execute(
                    "SELECT * FROM industry_intelligence WHERE industry_id = ? "
                    "AND version = ?", [industry_id, version])
                row = cur.fetchone()
                if row is None:
                    return None
                return dict(zip([d[0] for d in cur.description], row))

            cur = con.execute(
                "SELECT * FROM industry_intelligence WHERE industry_id = ?",
                [industry_id])
            rows = cur.fetchall()
            if not rows:
                return None
            cols = [d[0] for d in cur.description]

        recs = [dict(zip(cols, r)) for r in rows]
        selected = active_industry_rows(recs, include_superseded=include_superseded)
        return selected[0] if selected else None

    def supersede_industry_versions(self, industry_ids: Iterable[str], *,
                                    version: str, reason: str,
                                    superseded_by: str | None = None) -> int:
        """Atomically retire exact industry/version rows while retaining evidence."""
        ids = sorted({str(i or "").strip() for i in industry_ids if str(i or "").strip()})
        ver = str(version or "").strip()
        why = str(reason or "").strip()
        replacement = str(superseded_by or "").strip() or None
        if not ids:
            raise ValueError("at least one industry_id is required")
        if not ver:
            raise ValueError("industry version is required")
        if not why:
            raise ValueError("superseded reason is required")

        marks = ", ".join("?" for _ in ids)
        predicate = (
            f"version = ? AND industry_id IN ({marks}) "
            "AND (coalesce(upper(status), '') != 'SUPERSEDED' "
            "OR superseded_by IS DISTINCT FROM ? "
            "OR superseded_reason IS DISTINCT FROM ?)"
        )
        params = [ver, *ids, replacement, why]
        with self.connect() as con:
            n = con.execute(
                f"SELECT count(*) FROM industry_intelligence WHERE {predicate}",
                params,
            ).fetchone()[0]
            if n:
                con.execute(
                    "UPDATE industry_intelligence SET status = 'SUPERSEDED', "
                    "superseded_by = ?, superseded_reason = ?, superseded_at = ? "
                    f"WHERE {predicate}",
                    [replacement, why, _now(), *params],
                )
        return n

    def upsert_sector(self, row: dict) -> None:
        cols = ["sector_id", "version", "brief", "what_changed", "winners", "losers",
                "capital_cycle", "metrics_that_matter", "last_updated"]
        values = [_json(row.get(c)) if c in ("winners", "losers", "metrics_that_matter")
                  else row.get(c) for c in cols]
        updates = ", ".join(f"{c} = excluded.{c}" for c in cols
                            if c not in ("sector_id", "version"))
        with self.connect() as con:
            con.execute(
                f"INSERT INTO sector_brief ({', '.join(cols)}) "
                f"VALUES ({', '.join('?' * len(cols))}) "
                f"ON CONFLICT (sector_id, version) DO UPDATE SET {updates}",
                values,
            )

    def sector(self, sector_id: str, version: str | None = None) -> dict | None:
        with self.connect() as con:
            if version:
                cur = con.execute(
                    "SELECT * FROM sector_brief WHERE sector_id = ? AND version = ?",
                    [sector_id, version])
            else:
                cur = con.execute(
                    "SELECT * FROM sector_brief WHERE sector_id = ? "
                    "ORDER BY version DESC LIMIT 1", [sector_id])
            row = cur.fetchone()
            if row is None:
                return None
            return dict(zip([d[0] for d in cur.description], row))

    # --------------------------------------------------------------- ledgers
    def log_reconciliation(self, rows: Iterable[dict]) -> int:
        payload = [[r.get("ticker"), r.get("component"), r.get("subtest"),
                    r.get("before_points"), r.get("after_points"), r.get("delta"),
                    r.get("rule_id"), _json(r.get("claim_ids")), r.get("request_id"),
                    _now()] for r in rows]
        if not payload:
            return 0
        with self.connect() as con:
            con.executemany(
                "INSERT INTO reconciliation_ledger (ticker, component, subtest, "
                "before_points, after_points, delta, rule_id, claim_ids, request_id, "
                "applied_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", payload)
        return len(payload)

    def reconciliations_for(self, ticker: str) -> list[dict]:
        with self.connect() as con:
            cur = con.execute(
                "SELECT * FROM reconciliation_ledger WHERE ticker = ? "
                "ORDER BY applied_at", [ticker])
            names = [d[0] for d in cur.description]
            return [dict(zip(names, r)) for r in cur.fetchall()]

    def log_priority(self, rows: Iterable[dict], *, run_date: date | None = None,
                     seed: int | None = None) -> int:
        run_date = run_date or _now().date()
        payload = [[r.get("ticker"), run_date, r.get("arm"), r.get("priority_score"),
                    _json(r.get("inputs")), bool(r.get("selected")), seed]
                   for r in rows]
        if not payload:
            return 0
        with self.connect() as con:
            con.executemany(
                "INSERT INTO priority_ledger (ticker, run_date, arm, priority_score, "
                "inputs_json, selected, seed) VALUES (?, ?, ?, ?, ?, ?, ?)", payload)
        return len(payload)

    def priority_arms(self, run_date: date) -> dict[str, int]:
        """Selected count by arm for a run. The control-arm audit reads this."""
        with self.connect() as con:
            return dict(con.execute(
                "SELECT arm, count(*) FROM priority_ledger "
                "WHERE run_date = ? AND selected GROUP BY arm", [run_date]).fetchall())
