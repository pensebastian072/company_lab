"""Write `structural_growth` from the members' own revenue, for units with no agency series.

## Why this is a separate applier and not a claim through e79b_merge

`research_ingest.validate_claim` requires every industry claim to carry a quote AND an
excerpt containing it. That guard is right: an industry object's claims are citations, and a
quote-less claim in that list would let any later pass write an assertion into the corpus
with a citation's authority. It is not relaxed here.

The consequence is worth stating plainly rather than working around. The revenue aggregate is
**our arithmetic over filed XBRL**, so it has no page to quote. So:

* the ORDINAL is written from `industry_growth.growth_for_industry`, reproducible by
  re-running that function;
* the CLAIM attached to it cites the BLS CPI release, with a real quote that passes exact
  containment, because the deflator is the half of the arithmetic that comes from outside -
  and it is the half that decides the sign;
* the claim's own text carries the revenue aggregate, the member count, the largest member's
  share, the median member, and the nominal-to-real arithmetic, so the number can be
  audited without re-running anything.

**This is the weakest ordinal in the corpus and it should be read that way.** Every other
non-UNKNOWN field is backed by a quote on a page that says it. This one is backed by a quote
for the price level and a computation for the quantity. A unit that later gets a real
published quantity should be overwritten by it: `--force` is deliberately NOT implemented, so
a researched value can never be replaced by this, only the other way round.

## `--units` is REQUIRED, and that is the most important line in this file

A dry run over the whole corpus on 2026-09-12 passed every guard on **18** units and would
have written:

    regional_banking                      n=79  +7.7% nominal  -> MODERATE
    civil_aerospace_platforms_components  n=14 +18.5% nominal  -> EXCEPTIONAL
    health_care_services                  n=14 +14.9% nominal  -> HIGH

Those are a rate cycle and a post-pandemic recovery, not structural growth, and the guards
cannot see the difference: they test whether the members resemble each other, which in a
cyclical industry they do - all of them are up together. **A one-year window reads a cycle as
a structure, and no concentration or dispersion test catches that.** Writing EXCEPTIONAL onto
aerospace and MODERATE onto seventy-nine banks would have put a known-bad signal into the two
largest units in the book.

So this script refuses to run without an explicit `--units` list. Each unit named is a unit
someone has looked at and argued for.

## What changed a few hours later: the agreement test does most of that work now

`industry_growth.agreeing_growth` requires every window to pass AND to land in the same band,
and it independently refuses the units that `--units` was protecting the corpus from -
`regional_banking` reads MODERATE at one year and HIGH at three, `civil_aerospace` is refused
outright at three years. It also killed three of the five units this script had already
written that morning, which were retracted by `scripts/retract_unstable_growth.py`.

`--units` stays anyway. A guard that happens to catch today's bad cases is not a substitute
for a human naming the units they have argued for, and the agreement test cannot see scope:
it would happily write an ordinal for a unit whose members do not belong together, because
two windows of the same wrong aggregate agree with each other perfectly.
"""
from __future__ import annotations

import collections
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, r"C:\Users\<your-user>\company_lab")

import pandas as pd

from clab import net
from clab.external import industry_growth as IG
from clab.external import research_ingest as RI
from clab.external import revenue_share as RS
from clab.external import taxonomy as T
from clab.external import verify as V

ROOT = Path(r"D:\company_lab_data\external\research\industries")
BOOK = Path(r"C:\Users\<your-user>\company_lab\data\scores.parquet")

#: The deflator's source. A headline all-items index, not a unit-specific one: a per-unit
#: PPI would be better and is a separate research task, and using all-items is stated on
#: every claim rather than hidden. The quote is cut from the fetched page by this pattern.
CPI_URL = "https://www.bls.gov/news.release/cpi.nr0.htm"
CPI_TITLE = "U.S. Bureau of Labor Statistics, Consumer Price Index, August 2026"
CPI_DATE = "2026-09-11"

#: CPI-U index levels, for the multi-year deflator. The news release only carries a
#: 12-month change, so a 3-year window needs the series itself. v2 of the public API
#: reaches back far enough without a key; v1 returns only three years and would have
#: silently left the 3-year window un-deflated, which is the error that turns a shrinking
#: industry into a growing one.
CPI_SERIES = ("https://api.bls.gov/publicAPI/v2/timeseries/data/CUUR0000SA0"
              "?startyear=2021&endyear=2026")
#: Which windows must agree before an ordinal is written. Two is the minimum that can test
#: its own stability; see industry_growth.agreeing_growth.
WINDOWS = (1, 3)
CPI_PATTERN = re.compile(
    r"The Consumer Price Index for All Urban Consumers \(CPI-U\) increased "
    r"(\d+\.\d) percent over the last 12 months to an index level of [\d.,]+ "
    r"\(1982-84=100\)\.")
EXCERPT_PAD = 420


def _deflators(windows) -> dict[int, float]:
    """Annualised CPI-U change for each window, from the BLS series.

    August-to-August, matched to the index month the news release quotes, so the deflator
    covers the same months as the revenue windows rather than a calendar year. A missing
    year raises: an absent deflator read as zero would turn every shrinking industry into a
    growing one, which is the single worst failure this script could have.
    """
    js = json.loads(net.http_get(CPI_SERIES, timeout=60))
    if js.get("status") != "REQUEST_SUCCEEDED":
        raise SystemExit(f"BLS series request failed: {js.get('status')} "
                         f"{js.get('message')}")
    data = js["Results"]["series"][0]["data"]
    aug = {int(d["year"]): float(d["value"]) for d in data if d["period"] == "M08"}
    latest = max(aug)
    out: dict[int, float] = {}
    for w in windows:
        base = latest - w
        if base not in aug:
            raise SystemExit(f"CPI-U has no August {base} level, so the {w}-year window "
                             f"cannot be deflated - widen the series request")
        out[w] = (aug[latest] / aug[base]) ** (1.0 / w) - 1.0
    return out


def _excerpt(quote: str, page: str) -> str | None:
    i = page.lower().find(quote.lower())
    if i < 0:
        return None
    s, e = max(0, i - EXCERPT_PAD), min(len(page), i + len(quote) + EXCERPT_PAD)
    return page[s:e]


def _claim(res: dict, quote: str, excerpt: str) -> dict:
    top = f"{res['top_ticker']} is {res['top_share']:.0%} of the unit's revenue"
    excluded = (f" Excluded for a structural revenue move: {', '.join(res['excluded'])}."
                if res.get("excluded") else "")
    cid = "c_" + hashlib.sha1(
        f"IG|{res['industry_id']}|{res['nominal_growth']:.6f}".encode()).hexdigest()[:12]
    return {
        "claim_id": cid,
        "field": "structural_growth",
        "text": (
            f"COMPUTED, NOT PUBLISHED. The {res['peers']} listed members of "
            f"{res['industry_id']} grew their combined filed TTM revenue "
            f"{res['nominal_growth']:+.1%} a year over the last "
            f"{res['window_years']} year(s), with a median member at "
            f"{res['median_growth']:+.1%} and {top}.{excluded} Deflated by CPI-U all items "
            f"over the same window ({res['deflator']:+.1%} annualised, the quote on this "
            f"claim carries the 12-month figure) that is {res['real_growth']:+.1%} real, "
            f"which is {res['value']} on the pre-registered bands in "
            f"clab/external/industry_growth.py. "
            f"EXTERNAL GROWTH: the unit's share count moved "
            f"{res.get('share_growth', float('nan')):+.1%} a year over the same window, so "
            f"this growth was earned rather than bought - revenue per share grew "
            f"{res.get('revenue_per_share_growth', float('nan')):+.1%}. A unit whose share "
            f"count grows faster than 2% a year is refused outright, because assets bought "
            f"from owners outside the listed set grow the listed aggregate without growing "
            f"the industry. "
            f"STABILITY: this band is the SAME at every window tested "
            f"({', '.join(f'{w}y {v}' for w, v in sorted(res['agreed_bands'].items()))}), "
            f"which is the condition for writing it at all - an ordinal that changes with "
            f"the window is a property of the window. Three of the five units filled on "
            f"2026-09-12 failed this test and were retracted the same day. "
            f"WHAT THIS IS NOT: it is not a published industry quantity. It is the sum of "
            f"the members' own revenue, so part of it is an output of the very companies "
            f"this unit is used to score, and no private, foreign or unlisted competitor "
            f"is in it. Revenue is also not volume, even three years sits inside a longer "
            f"cycle, and the deflator is a headline index rather than this unit's own "
            f"prices. It is used because no trade body, regulator or statistical agency "
            f"publishes a quantity covering this unit - authorised by the user on "
            f"2026-09-12 as an exception to the plan's rule 4, and to be replaced by a "
            f"real published quantity the moment one is found."),
        "source_url": CPI_URL,
        "source_title": CPI_TITLE,
        "source_date": CPI_DATE,
        "source_type": "PRIMARY_DATA",
        # NOT PRIMARY_DATA: the quantity is built from the members' own filings, and
        # labelling it independent would let it satisfy the plan's non-issuer rule on
        # evidence about the members themselves. The deflator is independent; the
        # quantity is not, and the weaker of the two labels is the honest one.
        "independence_domain": "COMPETITOR_FILING",
        "quote": quote,
        "excerpt": excerpt,
        "stance": "SUPPORTS",
        "fact_or_inference": "INFERENCE",
    }


def main(apply: bool = False, units: list[str] | None = None) -> int:
    page = re.sub(r"\s+", " ", V._extract_fetched(
        net.http_get(CPI_URL, headers=getattr(V, "FETCH_HEADERS", None), timeout=90),
        CPI_URL)[0] or "")
    m = CPI_PATTERN.search(page)
    if not m:
        raise SystemExit("the CPI release no longer carries the 12-month sentence this "
                         "reads - re-read the release before changing the pattern")
    quote, excerpt = m.group(0), _excerpt(m.group(0), page)
    if not excerpt:
        raise SystemExit("quote not found in its own page")

    deflators = _deflators(WINDOWS)
    one_year_release = float(m.group(1)) / 100.0
    # The release's 12-month figure and the series' 1-year figure are the same number from
    # two places. If they disagree, the series is not the index the quote describes and the
    # claim would cite a figure it did not use.
    if abs(deflators[1] - one_year_release) > 0.001:
        raise SystemExit(f"the CPI series' 1-year change ({deflators[1]:+.3%}) does not "
                         f"match the release's ({one_year_release:+.3%}) - do not write a "
                         f"claim citing a figure it did not use")
    for w in WINDOWS:
        print(f"deflator {w}y {deflators[w]:+.3%} annualised")
    print()

    book = pd.read_parquet(BOOK)
    mem: dict[str, list[str]] = collections.defaultdict(list)
    for r in book.to_dict("records"):
        mem[T.industry_id(r.get("ticker"), r.get("sub_industry"))].append(r["ticker"])
    revenue = {w: IG.load_revenue(w) for w in WINDOWS}
    shares = {w: IG.load_shares(w) for w in WINDOWS}
    for w in WINDOWS:
        print(f"{w}y window: {len(revenue[w])} companies carry both revenue ends, "
              f"{len(shares[w])} both share-count ends")
    print()

    targets = units or sorted(p.parent.name for p in ROOT.glob("*/industry_state.json"))
    if apply:
        stamp = datetime.now().strftime("%Y%m%d-%H%M")
        backup = ROOT.parent / f"industries_backup_{stamp}"
        if not backup.exists():
            shutil.copytree(ROOT, backup)
            print(f"backup -> {backup}\n")

    filled, refused, already = [], [], []
    for iid in targets:
        p = ROOT / iid / "industry_state.json"
        if not p.exists():
            continue
        obj = json.loads(p.read_text(encoding="utf-8"))
        if str(obj.get("structural_growth") or "UNKNOWN").upper() != "UNKNOWN":
            already.append((iid, obj["structural_growth"]))
            continue
        res = IG.agreeing_growth(iid, sorted(mem.get(iid, [])), revenue, deflators, shares)
        if not res["ok"]:
            refused.append((iid, res.get("reason", "no reason given")))
            continue
        c = _claim(res, quote, excerpt)
        if c["claim_id"] in {x.get("claim_id") for x in (obj.get("claims") or [])}:
            continue
        obj["structural_growth"] = res["value"]
        obj["claims"] = (obj.get("claims") or []) + [c]
        chk = RI.validate_industry(obj)
        bad = chk.get("reasons") or chk.get("claim_reasons")
        answered = [f for f in ("structural_growth", "replication_difficulty",
                                "substitution_risk")
                    if str(obj.get(f) or "UNKNOWN").upper() != "UNKNOWN"]
        filled.append((iid, res, len(answered), bad))
        if apply and not bad:
            p.write_text(json.dumps(obj, indent=1), encoding="utf-8")

    print(f"{'APPLIED' if apply else 'DRY RUN'}  filled {len(filled)}, "
          f"refused {len(refused)}, already answered {len(already)}\n")
    for iid, res, ans, bad in filled:
        flag = "OK" if not bad else f"INVALID: {bad}"
        print(f"  FILL   {iid:36} n={res['peers']:2} nom={res['nominal_growth']:+6.1%} "
              f"real={res['real_growth']:+6.1%} -> {res['value']:11} "
              f"ordinals {ans}/3  {flag}")
    for iid, reason in refused:
        print(f"  REFUSE {iid:36} {reason}")
    return 0


if __name__ == "__main__":
    _argv = sys.argv[1:]
    if "--units" not in _argv:
        raise SystemExit(
            "--units <a,b,c> is required. This script will not run over the corpus: a "
            "one-year revenue window reads a rate cycle as structural growth, and no guard "
            "in industry_growth.py can tell the two apart. See the module docstring - a "
            "corpus-wide run would have written EXCEPTIONAL onto civil aerospace and "
            "MODERATE onto 79 regional banks. Name the units you have argued for.")
    _units = _argv[_argv.index("--units") + 1].split(",")
    raise SystemExit(main(apply="--apply" in _argv, units=_units))
