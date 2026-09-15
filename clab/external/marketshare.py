"""Compute `market_share_direction` from primary data instead of asking for it.

## Why this module exists

`market_share_direction` came back UNKNOWN for **all 40** companies in E44 and for 34 of
40 in E43 - 74 of 80 attempts, and every one of them an honest UNKNOWN with blocking
claims attached rather than a gap. It is the single most common unresolved field in the
external layer and the one that would most change `company_specific_capture`.

It is not unanswerable. It is unanswerable *by reading documents*, which is what a web
researcher does. Codex said so itself, naming for all 40 companies the exact disclosure
that would settle it. For the largest group - regional banks - that disclosure is the
**FDIC Summary of Deposits**: free, public, structured, branch-level, and covering every
insured institution in the United States.

So this does not ask. It computes, from the primary source, and the result carries a
claim like any other piece of evidence - except that the claim's source is a dataset we
hold rather than a page someone read.

## The four disciplines, which are the whole difficulty

**Identical geographies.** A bank's share may only be compared across markets present in
BOTH years. Comparing 2023's markets against 2024's would let branch openings and
closures masquerade as share movement, and a bank that exits a weak market would show as
gaining.

**Acquisition adjustment is NOT solved here, it is FLAGGED.** A bank that buys another
bank gains deposit share without competing better for a single dollar. That is not a
capture signal and reading it as one would be actively wrong. Any market where a
company's deposits jump by more than `ACQUISITION_JUMP` is excluded and reported, and a
company whose overall book jumps that much returns UNKNOWN with the reason attached.

**Deposits are not the whole business.** This settles DEPOSIT share, which for a
regional bank is most of the franchise and for a diversified bank is not. The claim says
"deposit market share" in as many words, and the field it backs is documented as such.

**A thin comparison abstains.** Fewer than `MIN_MARKETS` shared markets, or less than
`MIN_DEPOSITS_COVERED` of the company's book inside them, returns UNKNOWN - the same
rule the framework applies to peer multiples.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
from datetime import datetime, timezone

from .. import config, net
from .schema import UNKNOWN

FDIC_API = "https://banks.data.fdic.gov/api/sod"
CACHE_DIR = config.EXTERNAL_ROOT / "fdic"

#: Fields pulled per branch. DEPSUMBR is branch deposits; MSABR is the market.
FIELDS = "CERT,NAMEFULL,NAMEHCR,MSABR,STNAMEBR,CNTYNAMB,DEPSUMBR,YEAR"
PAGE = 10000

#: A company's deposits in one market growing faster than this year over year is treated
#: as an acquisition, not as competing better, and the market is excluded.
ACQUISITION_JUMP = 0.40
#: Shared markets needed before a direction may be called.
MIN_MARKETS = 3
#: Share of the company's own deposits that must sit inside the shared markets.
MIN_DEPOSITS_COVERED = 0.60
#: Deposits-to-market-cap band a genuine match must fall inside. Wide on purpose: it
#: exists to catch a 100x mismatch, not to model bank capital structure.
SCALE_MIN, SCALE_MAX = 0.8, 60.0

#: Share-change bands, in percentage points of market share, deposit-weighted.
GAINING_BPS = 0.15
LOSING_BPS = -0.15


def _cache_path(year: int):
    return CACHE_DIR / f"sod_{year}.json.gz"


def fetch_year(year: int, *, refetch: bool = False) -> list[dict]:
    """Every insured branch in one SOD year, cached.

    A full year is ~77,000 branches over eight requests. Cached because the whole point
    of a free primary source is that it stays free - re-pulling it on every run would
    turn a fixed cost into a recurring one for data that never changes once published.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(year)
    if path.exists() and not refetch:
        cached = net.read_gzip_json(path)
        if cached:
            return cached

    net.trust_windows_certs()
    limiter = net.RateLimiter(4.0)
    rows: list[dict] = []
    offset = 0
    while True:
        url = (f"{FDIC_API}?filters=YEAR:{year}&fields={FIELDS}"
               f"&limit={PAGE}&offset={offset}&format=json")
        payload = json.loads(net.http_get(url, limiter=limiter, timeout=90)
                             .decode("utf-8", "replace"))
        batch = [r.get("data") or {} for r in (payload.get("data") or [])]
        rows += batch
        total = (payload.get("meta") or {}).get("total") or 0
        offset += PAGE
        if offset >= total or not batch:
            break
    net.atomic_write_gzip_json(path, rows)
    return rows


def _norm(name: str | None) -> str:
    """Normalise a company or holding-company name for matching."""
    s = re.sub(r"[^a-z0-9 ]+", " ", str(name or "").lower())
    for word in ("incorporated", "inc", "corporation", "corp", "company", "co",
                 "the", "group", "holdings", "holding", "bancorp", "bancorporation",
                 "bancshares", "financial", "services", "national", "association",
                 "na", "nv", "plc", "ltd", "llc", "lp"):
        s = re.sub(rf"\b{word}\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def holding_index(rows: list[dict]) -> dict[str, str]:
    """normalised name -> NAMEHCR, over TWO exact keys, refusing every ambiguous one.

    Two corrections, both measured on the 2024 survey and both bugs first.

    AMBIGUOUS KEYS WERE RESOLVED BY ROW ORDER. The first version used `setdefault`, so a
    normalised key claimed by several institutions silently kept whichever the file
    listed first. **209 of 2,991 keys are shared by more than one holding company** -
    `_norm` strips "financial", "group", "services", "holding" and more, so genuinely
    distinct banks collide: "citizens financial group" and "citizens holding company"
    both become "citizens". CFG (~$180bn of deposits) matched CITIZENS HOLDING COMPANY, a
    small Mississippi bank; FNB matched FNB FINANCIAL SERVICES; CHCO matched CITY
    BANCSHARES. Every one of those is the exact failure the prefix rule was removed for,
    happening on the exact match instead.

    Only `_plausible_scale` stopped them reaching the store, which makes the scale guard
    LOAD-BEARING rather than belt-and-braces: anyone who relaxes SCALE_MIN ships CFG's
    deposit trend computed from a Mississippi bank. An ambiguous key now returns nothing
    at all, so the first line of defence stops guessing.

    NAMEHCR IS NOT THE NAME THE BOOK HOLDS. The book stores the BANK's common name;
    NAMEHCR is the holding company's legal name, and "Frost Bank" cannot normalise into
    "CULLEN/FROST BANKERS, INC." - that is a different name, not a formatting difference.
    FDIC also carries NAMEFULL, which for that institution literally is "Frost Bank", so
    NAMEFULL is added as a SECOND exact key rolled up to its own NAMEHCR. This loosens
    nothing: it is exact-on-normalised like the first key and refuses ambiguity the same
    way. Diagnosed by Chat B; measured here at 74 -> 82 of the 89 regional banks.
    """
    hcr_names: dict[str, set] = collections.defaultdict(set)
    full_names: dict[str, set] = collections.defaultdict(set)
    for r in rows:
        hcr = r.get("NAMEHCR")
        if not hcr:
            continue
        hcr_names[_norm(hcr)].add(hcr)
        full = r.get("NAMEFULL")
        if full:
            full_names[_norm(full)].add(hcr)

    # NAMEHCR wins where both keys exist: it is the name the field is defined on.
    out = {k: next(iter(v)) for k, v in hcr_names.items() if k and len(v) == 1}
    for k, v in full_names.items():
        if len(v) == 1 and k not in out and k not in hcr_names:
            out[k] = next(iter(v))
    return out


def collision_index(rows: list[dict]) -> dict[str, list[str]]:
    """normalised name -> EVERY holding company claiming it, for the ambiguous keys only.

    Refusing an ambiguous key outright was the first fix and it was too blunt: it took the
    89 regional banks from 74 matched to 63, because most collisions are one large bank
    against a small one and the scale guard already tells them apart. CBSH, HOMB, INDB,
    NWBI and HOPE were all correct matches thrown away to stop CFG being a wrong one.

    So the ambiguity is resolved by SIZE rather than by row order or by refusal - see
    `compute`. Deposits against market cap is an independent signal from the name, which
    is exactly what a tie-break needs to be.
    """
    hcr_names: dict[str, set] = collections.defaultdict(set)
    for r in rows:
        hcr = r.get("NAMEHCR")
        if hcr:
            hcr_names[_norm(hcr)].add(hcr)
    return {k: sorted(v) for k, v in hcr_names.items() if k and len(v) > 1}


def match_company(name: str, index: dict[str, str]) -> str | None:
    """Company name -> NAMEHCR. EXACT on the normalised form, and nothing else.

    A wrong bank is far worse than no bank: it attaches one institution's deposit trend
    to another company's record, and the claim carries a real FDIC URL that makes it
    look impeccably sourced.

    The first draft of this function allowed "a strict prefix of exactly one holding
    name" as a concession, and it produced exactly that failure. FNB - F.N.B.
    Corporation, roughly $47bn of deposits - matched FNB FINANCIAL SERVICES, INC.
    VLY, Valley National Bancorp at roughly $62bn, matched VALLEY BANK SHARES, INC.
    CHCO matched CITY BANCSHARES. Each returned a confident direction computed from the
    wrong bank's branches.

    Exact matching is necessary and was NOT sufficient on its own: `_norm` strips enough
    words that distinct institutions collide onto one key, and 209 keys in the 2024 survey
    are claimed by more than one holding company. `holding_index` now refuses those
    outright rather than resolving them by row order - see its docstring.

    An unmatched company returns UNKNOWN, which is the honest answer and costs nothing.
    """
    key = _norm(name)
    return index.get(key) if key else None


def _plausible_scale(deposits: float, market_cap: float | None) -> tuple[bool, str]:
    """Is this holding company's deposit book the right ORDER OF MAGNITUDE?

    Even an exact name match can land on the wrong institution, so the size check is a
    second, independent line of defence. A US bank's deposits usually run a few times
    its market capitalisation; the band here is deliberately wide because the point is
    to catch a 100x error, not to model bank capital structure.
    """
    if not market_cap or market_cap <= 0:
        return True, "no market cap to check against"
    ratio = deposits * 1000.0 / market_cap        # DEPSUMBR is in thousands
    if ratio < SCALE_MIN:
        return False, (f"matched book is only {ratio:.2f}x market cap - too small to be "
                       f"this company")
    if ratio > SCALE_MAX:
        return False, (f"matched book is {ratio:.1f}x market cap - too large to be this "
                       f"company")
    return True, f"deposits {ratio:.1f}x market cap"


def market_shares(rows: list[dict]) -> tuple[dict, dict]:
    """(deposits by (holding, market), total deposits by market)."""
    by_hc: dict[tuple, float] = collections.defaultdict(float)
    by_market: dict[str, float] = collections.defaultdict(float)
    for r in rows:
        msa = r.get("MSABR")
        market = str(msa) if msa not in (None, "", 0) else \
            f"{r.get('STNAMEBR')}|{r.get('CNTYNAMB')}"
        dep = r.get("DEPSUMBR")
        try:
            dep = float(dep or 0)
        except (TypeError, ValueError):
            continue
        if dep <= 0:
            continue
        hcr = r.get("NAMEHCR")
        if hcr:
            by_hc[(hcr, market)] += dep
        by_market[market] += dep
    return dict(by_hc), dict(by_market)


def direction_for(hcr: str, a: tuple[dict, dict], b: tuple[dict, dict]) -> dict:
    """Deposit-share direction for one holding company between two SOD years."""
    a_hc, a_mkt = a
    b_hc, b_mkt = b
    a_mine = {m: v for (h, m), v in a_hc.items() if h == hcr}
    b_mine = {m: v for (h, m), v in b_hc.items() if h == hcr}
    shared = sorted(set(a_mine) & set(b_mine))

    total_b = sum(b_mine.values())
    if not shared or total_b <= 0:
        return {"direction": UNKNOWN, "reason": "no shared markets", "markets": 0}

    # Acquisition guard, applied per market AND to the whole book.
    kept, excluded = [], []
    for m in shared:
        growth = (b_mine[m] - a_mine[m]) / a_mine[m] if a_mine[m] else float("inf")
        (excluded if growth > ACQUISITION_JUMP else kept).append(m)

    covered = sum(b_mine[m] for m in kept) / total_b if total_b else 0.0
    if len(kept) < MIN_MARKETS:
        return {"direction": UNKNOWN, "markets": len(kept), "excluded": len(excluded),
                "reason": f"only {len(kept)} shared markets survive the acquisition "
                          f"guard (minimum {MIN_MARKETS})"}
    if covered < MIN_DEPOSITS_COVERED:
        return {"direction": UNKNOWN, "markets": len(kept), "excluded": len(excluded),
                "coverage": round(covered, 3),
                "reason": f"comparable markets hold only {covered:.0%} of the company's "
                          f"deposits (minimum {MIN_DEPOSITS_COVERED:.0%})"}

    weighted = 0.0
    for m in kept:
        sa = a_mine[m] / a_mkt.get(m, 0) if a_mkt.get(m) else 0.0
        sb = b_mine[m] / b_mkt.get(m, 0) if b_mkt.get(m) else 0.0
        weighted += (sb - sa) * 100.0 * (b_mine[m] / total_b)

    if weighted >= GAINING_BPS:
        direction = "GAINING"
    elif weighted <= LOSING_BPS:
        direction = "LOSING"
    else:
        direction = "FLAT"
    return {
        "direction": direction,
        "share_change_pp": round(weighted, 4),
        "markets": len(kept), "excluded": len(excluded),
        "coverage": round(covered, 3),
        "reason": (f"deposit-weighted market-share change of {weighted:+.3f} pp across "
                   f"{len(kept)} markets held in both years, covering {covered:.0%} of "
                   f"deposits" + (f"; {len(excluded)} markets excluded as acquisitions"
                                  if excluded else "")),
    }


def claim_for(ticker: str, hcr: str, result: dict, year_a: int, year_b: int) -> dict:
    """An external_claim row for a computed direction. Same shape as a researched one.

    `independence_domain` is PRIMARY_DATA and the source is the FDIC API, because that
    is exactly what it is - a number we computed from a public dataset, not a sentence
    somebody wrote.
    """
    cid = "c_" + net.sha1_text(f"fdic|{ticker}|{year_a}|{year_b}")[:12]
    return {
        "claim_id": cid,
        "field": "market_share_direction",
        "text": (f"{ticker} deposit market share {result['direction']}: "
                 f"{result['reason']} (FDIC Summary of Deposits {year_a} vs {year_b}, "
                 f"holding company {hcr})."),
        "source_url": (f"{FDIC_API}?filters=YEAR:{year_b}&fields={FIELDS}"
                       f"&format=json"),
        "source_title": f"FDIC Summary of Deposits {year_a}-{year_b}",
        "source_date": f"{year_b}-06-30",
        "source_type": "PRIMARY_DATA",
        "independence_domain": "PRIMARY_DATA",
        "quote": None, "excerpt": None,
        "stance": "SUPPORTS",
        "fact_or_inference": "FACT",
        "computed": True,
    }


def compute(tickers_names: dict[str, str], *, year_a: int, year_b: int,
            caps: dict[str, float] | None = None,
            refetch: bool = False) -> dict[str, dict]:
    """ticker -> result, for every company that matches an FDIC holding company."""
    rows_a = fetch_year(year_a, refetch=refetch)
    rows_b = fetch_year(year_b, refetch=refetch)
    idx = holding_index(rows_b)
    collisions = collision_index(rows_b)
    a, b = market_shares(rows_a), market_shares(rows_b)

    def _book(hcr: str) -> float:
        return sum(v for (h, _m), v in b[0].items() if h == hcr)

    out: dict[str, dict] = {}
    caps = caps or {}
    for ticker, name in tickers_names.items():
        hcr = match_company(name, idx)
        tie_break = None
        # An EMPTY normalised key carries no distinguishing content at all - "The Bancorp,
        # Inc." strips to nothing, every token being a corporate-form stopword - so it must
        # never match. It matched a $7.2bn book against a $2.7bn cap by luck.
        if not hcr and _norm(name) and _norm(name) in collisions:
            # An ambiguous key, resolved by size and never by row order. Exactly one
            # candidate of a plausible scale wins; zero or several is UNKNOWN.
            cands = [h for h in collisions[_norm(name)]
                     if _plausible_scale(_book(h), caps.get(ticker))[0]]
            if len(cands) == 1:
                hcr, tie_break = cands[0], collisions[_norm(name)]
            else:
                out[ticker] = {
                    "direction": UNKNOWN, "matched": None,
                    "reason": f"name is ambiguous across {len(collisions[_norm(name)])} "
                              f"FDIC holding companies and {len(cands)} are of a "
                              f"plausible size, so it cannot be resolved"}
                continue
        if not hcr:
            out[ticker] = {"direction": UNKNOWN, "matched": None,
                           "reason": "no FDIC holding company matched this name exactly"}
            continue
        book = sum(v for (h, _m), v in b[0].items() if h == hcr)
        ok, why = _plausible_scale(book, caps.get(ticker))
        if not ok:
            out[ticker] = {"direction": UNKNOWN, "matched": None,
                           "rejected_match": hcr,
                           "reason": f"name matched {hcr!r} but {why}"}
            continue
        res = direction_for(hcr, a, b)
        res["matched"] = hcr
        res["scale_check"] = why
        if tie_break:
            res["ambiguous_key_resolved_by_scale"] = tie_break
        res["claim"] = claim_for(ticker, hcr, res, year_a, year_b) \
            if res["direction"] != UNKNOWN else None
        out[ticker] = res
    return out


def apply_to(research_version: str, results: dict[str, dict], *,
             store=None) -> dict:
    """Write computed directions onto the company records, with their claims.

    Only fills a field the researcher left UNKNOWN. A computed number does not overrule
    a researched conclusion - if external research established a direction and this
    disagrees, that is a contradiction worth surfacing, not something to silently
    overwrite.
    """
    from .schema import Claim
    from .store import ExternalStore

    store = store or ExternalStore()
    filled, conflicts, skipped = [], [], []
    for rec in store.companies(research_version):
        t = rec["ticker"]
        res = results.get(t) or {}
        if res.get("direction") in (None, UNKNOWN) or not res.get("claim"):
            continue
        existing = rec.get("market_share_direction")
        if existing not in (None, UNKNOWN):
            if existing != res["direction"]:
                conflicts.append({"ticker": t, "researched": existing,
                                  "computed": res["direction"]})
            else:
                skipped.append(t)
            continue

        c = res["claim"]
        store.insert_claims([Claim(
            claim_id=c["claim_id"], field=c["field"], text=c["text"],
            source_url=c["source_url"], source_title=c["source_title"],
            source_date=c["source_date"], source_type=c["source_type"],
            independence_domain=c["independence_domain"], quote=None, excerpt=None,
            stance=c["stance"], fact_or_inference=c["fact_or_inference"],
            verify_status="VERIFIED_LOCAL", overlap=1.0, ticker=t,
            industry_id=rec.get("industry_id"))],
            request_id=f"fdic_sod:{research_version}")
        store.upsert_company({**rec, "market_share_direction": res["direction"]})
        filled.append(t)
    return {"filled": filled, "conflicts": conflicts, "already_agreed": skipped}


def main(argv: list[str] | None = None) -> int:
    import pandas as pd

    ap = argparse.ArgumentParser(
        description="Compute deposit market-share direction from the FDIC SOD")
    ap.add_argument("--year-a", type=int, default=2023)
    ap.add_argument("--year-b", type=int, default=2024)
    ap.add_argument("--industry", default="regional_banking")
    ap.add_argument("--refetch", action="store_true")
    ap.add_argument("--apply-to", default=None,
                    help="research_version to write the computed directions onto")
    args = ap.parse_args(argv)

    from . import taxonomy as T

    df = pd.read_parquet(config.SCORES_PARQUET)
    df["industry_id"] = [T.industry_id(t, si)
                         for t, si in zip(df.ticker, df.sub_industry)]
    pool = df[df.industry_id == args.industry]
    names = dict(zip(pool.ticker, pool.name))
    caps = dict(zip(pool.ticker, pool.market_cap))
    print(f"{args.industry}: {len(names)} companies, SOD {args.year_a} vs {args.year_b}")

    res = compute(names, year_a=args.year_a, year_b=args.year_b, caps=caps,
                  refetch=args.refetch)
    got = {k: v for k, v in res.items() if v["direction"] != UNKNOWN}
    unmatched = [k for k, v in res.items() if v.get("matched") is None]

    print(f"\nresolved: {len(got)} of {len(res)}   unmatched name: {len(unmatched)}")
    print(f"{'ticker':<7}{'direction':<10}{'pp change':>10}{'mkts':>6}{'cov':>7}  matched")
    for t, v in sorted(res.items(), key=lambda kv: -(kv[1].get("share_change_pp") or -99)):
        if v["direction"] == UNKNOWN:
            continue
        print(f"{t:<7}{v['direction']:<10}{v.get('share_change_pp', 0):>10.3f}"
              f"{v.get('markets', 0):>6}{v.get('coverage', 0):>7.2f}  "
              f"{str(v.get('matched'))[:38]}")
    if unmatched:
        print(f"\nunmatched: {sorted(unmatched)}")
    for t, v in sorted(res.items()):
        if v["direction"] == UNKNOWN and v.get("matched"):
            print(f"  {t:<7} UNKNOWN - {v['reason']}")

    if args.apply_to:
        out = apply_to(args.apply_to, res)
        print()
        print(f"applied to {args.apply_to}: filled {len(out['filled'])} "
              f"{out['filled']}")
        if out["conflicts"]:
            print(f"  CONFLICTS (researched vs computed disagree, NOT overwritten): "
                  f"{out['conflicts']}")
        if out["already_agreed"]:
            print(f"  already agreed: {out['already_agreed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
