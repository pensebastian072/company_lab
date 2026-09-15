"""Market-share direction computed from revenue share of the listed peer set.

## Why this exists

`market_share_direction` resolved for **4 of 183** researched companies, and 29 of the 33
non-UNKNOWN values in the corpus came from the FDIC computation rather than from
research. Web research cannot obtain it: nobody publishes a share series for most
industries, so the field cost one blocking claim per company and returned nothing -
52 of E46's 634 claims, 8.2% of that batch's budget, spent documenting a dead end.

The FDIC module answered it for banks from a free primary registry. There is no registry
for oilfield services or media. But the quantity itself is computable from data the book
already holds, and the reason it works for commodity businesses is the whole point:

    **share is a RATIO, so a price shock COMMON to every peer cancels.**

"Common" carries the whole argument, and it is not always true. `upstream_oil_gas` holds
both gas-weighted producers (EQT, GPOR, CRK, AR, RRC) and oil-weighted ones, and a
divergence between gas and oil prices does NOT cancel inside that bucket. Measured: all
five gas names read GAINING and none reads LOSING, which is what a gas-versus-oil price
move would look like as well as what genuine capture would look like. The book carries no
commodity-mix field, so the two cannot be separated here. Stated, not solved.

An E&P's revenue tripling tells you what crude did. Its revenue as a fraction of its
peers' combined revenue does not move with crude at all - only with whether it grew
faster or slower than the companies it competes with. That is exactly the separation E46
asked Codex to make by hand and which defeated the rank-order method for all 20 upstream
producers.

## What it is NOT

**Share of the listed peer set in this book, not share of the market.** ExxonMobil
competes with Saudi Aramco, ADNOC, Petrobras and thousands of private operators, none of
which are here. A company can gain share of the listed set while losing share of the
world. Every claim says so in its own text; the number is a competitive-direction signal
among comparable public filers, and it is not a market-share statistic.

Revenue is also not volume. For an integrated oil company it mixes upstream, refining,
chemicals and trading. It is the best universally-available comparable, not the ideal one.

## The disciplines, borrowed from marketshare.py

Same failure modes, same guards:

* **Both windows or nothing.** A peer missing `revenue_ttm_prior` is dropped from BOTH
  totals, never counted in one - otherwise every remaining company's share moves for a
  reason that has nothing to do with them.
* **Structural-sized revenue moves are excluded in BOTH directions.** A company that buys
  a competitor gains share without competing better for a dollar of it, and a company that
  sells a division loses share the same way. Below the exclusion bar, a smaller structural
  move cannot be detected at all - the book carries no M&A metric - so it is DECLARED in
  the claim text rather than hidden.
* **A minimum peer count.** Share inside a 2-company industry is one company's mirror.
* **Nominated industries are skipped entirely.** A rate-regulated utility is
  NOT_APPLICABLE by construction (applicability.py) and computing a number for it would
  defeat the two-condition rule by supplying the value the rule requires to be absent.
* **A computed direction NEVER overwrites a researched one.** A disagreement is a
  contradiction to surface, not something to bury.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import statistics

from . import applicability as AP
from .schema import Claim, UNKNOWN
from .. import config

#: A peer whose revenue moved this much MORE THAN ITS INDUSTRY'S MEDIAN, in either
#: direction, is treated as having restructured rather than competed and is excluded.
#:
#: Two corrections are baked into that sentence and both were bugs first.
#:
#: SYMMETRIC: the first draft guarded only growth. A divestiture loses share exactly the
#: way an acquisition gains it, and OXY (-22.7%) and NOG (-25.6%) read as out-competed.
#:
#: RELATIVE TO THE PEER MEDIAN, not absolute: the second draft used the company's own
#: revenue change, which meant a commodity price move large enough to lift EVERY peer
#: past the bar excluded the entire industry - the exact case this module exists to
#: handle. Caught by test_a_price_shock_common_to_every_peer_cancels, which returned an
#: empty set. Excess over the median is what separates a company that restructured from
#: an industry that repriced.
STRUCTURAL_MOVE = 0.40

#: Below the exclusion bar but large enough that M&A cannot be ruled out. The book carries
#: no M&A metric, so this cannot be detected - only declared. EQT grew 32.3% in the window
#: it absorbed Equitrans and reads as the second-largest share gainer in upstream; that may
#: be entirely acquisition. Any company over this bar carries the caveat in its own claim
#: text rather than having the number quietly withheld or quietly trusted. Measured as
#: excess over the peer median, for the same reason as STRUCTURAL_MOVE.
STRUCTURAL_SUSPECT = 0.20

#: Below this many usable peers the industry cannot support a share statement.
MIN_PEERS = 4

#: Share of the industry's current revenue that must come from peers present in BOTH
#: windows. Below it the denominator has moved too much to compare against.
MIN_REVENUE_COVERED = 0.60

#: Direction thresholds, in RELATIVE share change, not percentage points. A company
#: holding 4% of a 20-peer industry and one holding 40% of a 3-peer industry are not
#: comparable in pp, so the test is proportional: a 5% relative move in a company's own
#: share. Scale-free, and chosen on that argument rather than fitted to the observed
#: distribution.
GAINING_REL = 0.05
LOSING_REL = -0.05


def load_revenue(scorecard_dir: pathlib.Path | None = None) -> dict[str, tuple[float, float]]:
    """ticker -> (revenue_ttm, revenue_ttm_prior), for companies carrying both."""
    d = pathlib.Path(scorecard_dir or config.SCORECARD_DIR)
    out: dict[str, tuple[float, float]] = {}
    for p in d.glob("*.json"):
        try:
            card = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        t = card.get("ticker")
        m = card.get("metrics") or {}
        now, prior = m.get("revenue_ttm"), m.get("revenue_ttm_prior")
        if not t or now is None or prior is None:
            continue
        if not (math.isfinite(now) and math.isfinite(prior)) or now <= 0 or prior <= 0:
            continue
        out[str(t).upper()] = (float(now), float(prior))
    return out


def direction_for_industry(industry_id: str, members: list[str],
                           revenue: dict[str, tuple[float, float]]) -> dict[str, dict]:
    """Share direction for every member of one industry. Empty dict if it cannot be done.

    Returns ticker -> {direction, share_now, share_prior, rel_change, peers, reason}.
    """
    # Peer POSITION is computed for EVERY industry, including the ones where
    # market_share_direction is NOT_APPLICABLE. Those are two different questions and an
    # earlier draft collapsed them, which threw away a real answer for 54 of 59 utilities.
    #
    #   contestable share moved?   meaningless for a franchise monopoly -> NOT_APPLICABLE
    #   who is biggest, who is
    #   growing or shrinking?      answerable everywhere, and it discriminates: AWK holds
    #                              39.9% of listed water revenue against 1.6% at the
    #                              bottom, and gas growth-vs-peers spans -9.9% to +35.2%
    #
    # `contestable` says which of the two this industry supports. Only a contestable
    # industry may fill market_share_direction; every industry fills the peer_* fields.
    contestable = "market_share_direction" not in AP.inapplicable_fields(industry_id)

    # Both windows or nothing. A peer present in one total and absent from the other
    # moves everybody else's share for a reason that is not about them.
    usable = {t: revenue[t] for t in members if t in revenue}
    if len(usable) < MIN_PEERS:
        return {}

    # The structural guard runs BEFORE the totals, so a restructurer does not move the
    # denominator and make every peer's share read as changing.
    growth = {t: (now - prior) / prior for t, (now, prior) in usable.items()}
    median_growth = statistics.median(growth.values())
    kept, excluded = {}, []
    for t, (now, prior) in usable.items():
        if abs(growth[t] - median_growth) > STRUCTURAL_MOVE:
            excluded.append(t)
        else:
            kept[t] = (now, prior)
    if len(kept) < MIN_PEERS:
        return {}

    all_now = sum(v[0] for v in usable.values())
    tot_now = sum(v[0] for v in kept.values())
    tot_prior = sum(v[1] for v in kept.values())
    if tot_now <= 0 or tot_prior <= 0 or all_now <= 0:
        return {}
    if tot_now / all_now < MIN_REVENUE_COVERED:
        return {}

    rank_of = {t: i + 1 for i, t in enumerate(
        sorted(kept, key=lambda k: -kept[k][0]))}

    out: dict[str, dict] = {}
    for t, (now, prior) in kept.items():
        s_now, s_prior = now / tot_now, prior / tot_prior
        rel = (s_now - s_prior) / s_prior if s_prior else 0.0
        if rel >= GAINING_REL:
            direction = "GAINING"
        elif rel <= LOSING_REL:
            direction = "LOSING"
        else:
            direction = "FLAT"
        out[t] = {
            "direction": direction,
            "contestable": contestable,
            "share_rank": rank_of[t],
            "peers_ranked": len(kept),
            "industry_id": industry_id,
            "share_now": round(s_now, 5),
            "share_prior": round(s_prior, 5),
            "rel_change": round(rel, 4),
            "peers": len(kept),
            "excluded_restructured": sorted(excluded),
            "structural_suspect": abs(growth[t] - median_growth) > STRUCTURAL_SUSPECT,
            "own_revenue_change": round(growth[t], 4),
            "peer_median_revenue_change": round(median_growth, 4),
            "excess_over_peers": round(growth[t] - median_growth, 4),
            "reason": (
                f"revenue share of the {len(kept)} listed peers in {industry_id} moved "
                f"{s_prior:.2%} -> {s_now:.2%} ({rel:+.1%} relative) between the prior "
                f"and current TTM windows"),
        }
    return out


def claim_for(ticker: str, res: dict) -> dict:
    """A PRIMARY_DATA claim with no quote - it is our arithmetic over filed revenue.

    The text carries the limitation rather than leaving it to a reader: this is share of
    the listed peer set, not of the market.
    """
    return {
        "claim_id": f"rs_{abs(hash((ticker, res['industry_id'], res['share_now']))) % 10**12:012d}",
        "field": "market_share_direction",
        "text": (
            f"{ticker} revenue share among the {res['peers']} listed peers in "
            f"{res['industry_id']} moved {res['share_prior']:.2%} -> {res['share_now']:.2%} "
            f"({res['rel_change']:+.1%} relative), computed from filed TTM revenue. This is "
            f"share of the LISTED PEER SET in the Company Lab book, NOT of the market: "
            f"private, foreign and unlisted competitors are absent. Share is a ratio, so a "
            f"price move common to every peer cancels - but only a COMMON one: inside a "
            f"bucket holding both gas-weighted and oil-weighted producers, a divergence "
            f"between gas and oil prices does not cancel."
            + (f" CAVEAT: {ticker}'s own revenue moved {res['own_revenue_change']:+.1%}, "
               f"which is {res['excess_over_peers']:+.1%} against a peer median of "
               f"{res['peer_median_revenue_change']:+.1%} - a gap large enough that an "
               f"acquisition or divestiture may account for this rather than "
               f"competition." if res.get("structural_suspect") else "")),
        "source_url": "computed://company_lab/revenue_share",
        "source_title": "Company Lab revenue-share computation over filed TTM revenue",
        "source_type": "PRIMARY_DATA",
        "independence_domain": "PRIMARY_DATA",
        "quote": None,
        "stance": "CONTEXT",
        "fact_or_inference": "FACT",
        "verify_status": "VERIFIED_LOCAL",
        "overlap": 1.0,
        "ticker": ticker,
    }


def apply_to(research_version: str, results: dict[str, dict], *, store=None) -> dict:
    """Fill UNKNOWN `market_share_direction` only. Never overwrite a researched value."""
    from .store import ExternalStore
    st = store or ExternalStore(config.EXTERNAL_DB)
    filled, conflicts, skipped, not_contestable = [], [], [], []
    for ticker, res in sorted(results.items()):
        rec = st.company(ticker, research_version)
        if not rec:
            continue
        # Peer position is written for everyone, contestable or not.
        st.upsert_company({**rec,
                           "peer_revenue_share": res["share_now"],
                           "peer_share_rank": res["share_rank"],
                           "peer_share_n": res["peers_ranked"],
                           "peer_growth_direction": res["direction"],
                           "peer_growth_vs_median": res.get("excess_over_peers")})
        rec = st.company(ticker, research_version) or rec

        if not res.get("contestable"):
            not_contestable.append(ticker)
            continue

        current = rec.get("market_share_direction")
        if current and str(current).upper() != UNKNOWN:
            if str(current).upper() != res["direction"]:
                conflicts.append({"ticker": ticker, "researched": current,
                                  "computed": res["direction"]})
            else:
                skipped.append(ticker)
            continue
        c = claim_for(ticker, res)
        st.insert_claims([Claim(
            claim_id=c["claim_id"], field=c["field"], text=c["text"],
            source_url=c["source_url"], source_title=c["source_title"],
            source_date=None, source_type=c["source_type"],
            independence_domain=c["independence_domain"], quote=None, excerpt=None,
            stance=c["stance"], fact_or_inference=c["fact_or_inference"],
            verify_status="VERIFIED_LOCAL", overlap=1.0, ticker=ticker,
            industry_id=res["industry_id"])],
            request_id=f"revenue_share:{research_version}")
        st.upsert_company({**rec, "market_share_direction": res["direction"]})
        filled.append(ticker)
    return {"filled": filled, "conflicts": conflicts, "agreed": skipped,
            "position_only": not_contestable}


def compute(sector_id: str | None = None) -> dict[str, dict]:
    """Every computable direction, keyed by ticker. Reads the book, no network."""
    import pandas as pd

    from .taxonomy import resolve
    df = pd.read_parquet(config.SCORES_PARQUET)
    df = df[df["sector"].notna()]
    rows = []
    for r in df.itertuples():
        ids = resolve(r.ticker, r.sector, r.sub_industry)
        if sector_id and ids["sector_id"] != sector_id:
            continue
        if ids["industry_id"]:
            rows.append((str(r.ticker).upper(), ids["industry_id"]))
    members: dict[str, list[str]] = {}
    for t, iid in rows:
        members.setdefault(iid, []).append(t)
    revenue = load_revenue()
    out: dict[str, dict] = {}
    for iid, mem in members.items():
        out.update(direction_for_industry(iid, mem, revenue))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Compute market-share direction from revenue share")
    ap.add_argument("--sector", default=None)
    ap.add_argument("--apply-to", default=None, metavar="RESEARCH_VERSION")
    args = ap.parse_args(argv)

    res = compute(args.sector)
    tally: dict[str, int] = {}
    for v in res.values():
        tally[v["direction"]] = tally.get(v["direction"], 0) + 1
    print(f"computed {len(res)} companies: {tally}")
    for t, v in sorted(res.items(), key=lambda kv: -kv[1]["rel_change"])[:12]:
        print(f"  {t:<7}{v['direction']:<9}{v['rel_change']:>+8.1%}  "
              f"{v['industry_id']} (n={v['peers']})")
    if args.apply_to:
        out = apply_to(args.apply_to, res)
        print(f"\nfilled {len(out['filled'])}, agreed {len(out['agreed'])}, "
              f"conflicts {len(out['conflicts'])}")
        for c in out["conflicts"]:
            print(f"  CONFLICT {c['ticker']}: researched {c['researched']} "
                  f"vs computed {c['computed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
