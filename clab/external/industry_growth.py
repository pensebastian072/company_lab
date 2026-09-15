"""`structural_growth` from the listed members' own filed revenue, when nothing else exists.

## Why this exists, and what it costs

The master plan's rule 4 says `structural_growth` comes from a **published industry
quantity, never company revenue**. That rule is right and this module breaks it, on the
user's explicit instruction of 2026-09-12 ("just use their revenues since they are similar
companies"). The instruction is recorded in the plan as an authorised exception rather than
silently applied, and every claim this module writes says in its own text that the quantity
is the sum of the members' own filings.

What the rule was protecting against is real and worth naming, because it is the thing to
watch in anything built on top of this:

**the quantity is partly an output of the thing being scored.** A company's own revenue is
one of the inputs to the aggregate that then sets its industry's growth ordinal, which feeds
its score. With twenty-two members that contamination is small; with three it is most of the
number. That is what `MAX_TOP_SHARE` is for.

Against that: an industry nobody publishes a quantity for currently gets UNKNOWN, and UNKNOWN
on the ship bar means the unit never becomes an expert at all. Five units and 57 companies
sat there on 2026-09-12 with no agency series in existence - no trade body covers the span of
Brunswick plus Mattel plus Peloton, and the one BEA line whose scope fit survives PDF
extraction only as an unattributable chart. A flagged, guarded, reproducible number beats a
permanent UNKNOWN, as long as it is never mistaken for the other kind.

## The user's premise IS the test

"Since they are similar companies" is the load-bearing half of the instruction, and it is
checkable rather than assumed. Each guard below is one way the premise fails:

    MIN_PEERS          two companies are not an industry
    MAX_TOP_SHARE      if one member is most of the aggregate, the "industry" number is
                       that member's number wearing an industry's name. Tobacco reads
                       +4.9% while its own median member reads -0.6%, because Philip
                       Morris is 62% of the unit's revenue.
    MAX_AGG_MEDIAN_GAP if the aggregate and the median member disagree by more than a few
                       points, the aggregate is not describing the typical member.
                       specialty_stores reads +18.4% against a +3.8% median.
    STRUCTURAL_MOVE    borrowed from revenue_share: an acquirer or a divester moves the
                       total for a reason that is not growth. Excluded in BOTH directions.

A unit that fails any of them gets no claim and keeps UNKNOWN. That is the honest outcome,
not a shortfall to be engineered around.

## Nominal is not growth

Revenue is nominal. The ordinal is assigned to **real** growth, deflating by CPI-U all items
over the same window, which is cited as its own claim so the arithmetic is auditable rather
than asserted. A unit whose dollars grow slower than the price level is shrinking, and the
whole reason `packaged_foods_meats` reads DECLINING on agency data is exactly that
arithmetic - see the validation below.

## The window: one year reads a cycle, three years is why this module got a second half

The first version of this module had a one-year window only, and a corpus-wide dry run on
2026-09-12 exposed what that costs: it passed every guard on 79 regional banks at +7.7% and
on civil aerospace at +18.5%, and called them MODERATE and EXCEPTIONAL. Those are a rate
cycle and a delivery recovery. **The guards cannot catch it, because they test whether the
members resemble each other, and in a cyclical industry they resemble each other perfectly -
all up together, for a reason that has nothing to do with structural growth.** Thirteen units
were refused by hand that day rather than written.

`window_years` is the fix. Three years spans enough of a cycle that a single year's rate move
or restocking no longer carries the answer, and the scorecards already hold
`revenue_ttm_3y_ago` for 1,466 of 1,500 companies, so it costs nothing to compute. Growth is
reported **annualised** so the bands and the deflator mean the same thing at any window.

It is a damping, not a cure. A three-year window still sits inside a longer cycle, and an
industry measured from trough to peak will read as growing however wide the window.

## So the window became the test: `agreeing_growth`

Running both windows over the corpus on 2026-09-12 settled what a second window is actually
for, and it was not coverage. **The two windows disagree on the band for 8 of the 13 units
either one could answer**, and they disagreed on 3 of the 5 this module had already written
that morning:

    hotels_resorts_cruise_lines   1y +4.2% MODERATE    3y +6.8% HIGH
    automotive_parts_equipment    1y -0.1% FLAT        3y -3.0% DECLINING
    leisure_products              1y -0.4% FLAT        3y -7.6% DECLINING
    household_products            1y -3.5% DECLINING   3y -3.4% DECLINING   <- agrees
    food_distributors             1y +1.1% FLAT        3y +0.4% FLAT        <- agrees

An ordinal that changes when the analyst changes the window by two years is a property of the
window, not of the industry. The three unstable ones were **retracted** the same session and
their units returned to UNKNOWN.

So the supported entry point is `agreeing_growth`, which requires BOTH windows to pass every
guard AND to land in the same band. It is a stability test of the same kind as asking whether
a backtest survives a different sample split, and it refuses a great deal - `regional_banking`
among it, MODERATE at one year and HIGH at three, which is the rate cycle showing up exactly
where it was predicted to. `growth_for_industry` stays public because the comparison needs
both halves, but a caller writing an ordinal from one window alone is asserting something this
module cannot support.

## It was validated before it was used, and the validation is thinner than it looks

Three units already carry a `structural_growth` answered from a Census channel series, so
this module was run against them BEFORE being applied anywhere else. What came back:

    unit                                 agency route   this module   bands
    packaged_foods_meats                 -1.3% real     -1.7% real    DECLINING vs FLAT
    food_retail                          -1.3% real     -1.6% real    FLAT      vs FLAT
    consumer_staples_merchandise_retail  +3.0% real      REFUSED      WMT is 60% of it

**Two units comparable, not three** - this module's own concentration guard refuses the
third, which is the guard working rather than a gap. On the two that compare, the QUANTITIES
agree within 0.4 points and the BANDS agree on one of two. The packaged-foods disagreement
is entirely the -2% cut in GROWTH_BANDS: both routes say real growth is negative, and they
differ by less than the width of the uncertainty in either. So what is calibrated is the
measurement, and what is NOT calibrated is the band edge - a unit landing within half a
point of a cut could read either way, and the ordinal should not be leaned on there.

That is the whole basis for trusting this on the five units where no agency route exists:
two comparisons, one quarter, one year. It is a sanity check, not a validation.

**A computed ordinal never overwrites a researched one**, the same rule `revenue_share`
follows. `growth_for_industry` reports; the caller decides, and the caller only writes where
the field is UNKNOWN.
"""
from __future__ import annotations

import json
import math
import pathlib
import statistics

from .. import config
from . import revenue_share as RS

#: Which scorecard metric holds the older end of each window. `revenue_ttm_prior` is the
#: one-year field and is named differently from the others, which is why this is a map
#: rather than an f-string: a generated key would silently miss at one year and the unit
#: would read as having no revenue data rather than as a bug.
WINDOW_FIELD = {1: "revenue_ttm_prior", 3: "revenue_ttm_3y_ago", 5: "revenue_ttm_5y_ago"}

#: Two companies are not an industry. Same value and same argument as `revenue_share`.
MIN_PEERS = 4

#: The largest member's share of the aggregate. Above this, the aggregate is one company's
#: revenue with an industry's name on it: measured on 2026-09-12, tobacco's aggregate read
#: +4.9% against a -0.6% median member because Philip Morris is 62% of the unit's revenue,
#: and the industry's actual story - declining volume defended with price - is the opposite
#: of what the aggregate says. 0.50 is where "one member is most of it" begins, and it is
#: the bar that also keeps a 3-member unit from passing on concentration alone.
MAX_TOP_SHARE = 0.50

#: Distance between the aggregate's growth and the median member's. Above this the
#: aggregate is a large member's result, not the unit's: specialty_stores read +18.4%
#: against a +3.8% median. Five points is wide enough to allow the ordinary case where big
#: members grow a little differently from small ones, and narrow enough to catch one member
#: carrying the total.
MAX_AGG_MEDIAN_GAP = 0.05

#: Annualised growth in the unit's aggregate DILUTED SHARE COUNT, above which the revenue
#: growth is refused as bought rather than earned.
#:
#: Added 2026-09-12 from Real Estate, where it is the dominant confound rather than an edge
#: case. A REIT grows revenue by issuing equity and buying buildings, and the buildings come
#: from private owners — so the listed aggregate grows while the property sector does not. It
#: is `revenue_share.py`'s "share of the listed set, not of the market" problem, arriving in
#: a place where it moves the headline:
#:
#:     unit                  revenue 3y   shares 3y   revenue/share 3y
#:     retail_reits              +11.5%      +4.9%             +6.2%
#:     industrial_reits           +9.8%      +4.3%             +5.3%
#:     hotel_resort_reits         +4.5%      +0.0%             +4.4%
#:     real_estate_services      +10.0%      +0.1%             +9.9%
#:
#: Roughly 43% of retail REITs' revenue growth and 44% of industrial REITs' came with share
#: issuance. Calling either "the industry grew" would be wrong in a way no other guard here
#: can see: the members resemble each other, nobody is concentrated, and both windows agree,
#: because they are all doing the same thing.
#:
#: 0.02 a year is about where ordinary option dilution ends and funded external growth
#: begins. The two units that pass it have share counts flat to negative.
MAX_SHARE_GROWTH = 0.02

#: Real growth -> ordinal. Stated once, here, so no pass invents its own cut. The bands are
#: a judgement and not a measurement: FLAT is deliberately wide, because a one-year nominal
#: revenue window deflated by a headline price index cannot resolve two points of real
#: growth, and the cost of calling a flat industry MODERATE is worse than the reverse.
GROWTH_BANDS = (
    (-0.02, "DECLINING"),     # real growth below -2%
    (0.02, "FLAT"),           # -2% to +2%
    (0.06, "MODERATE"),       # +2% to +6%
    (0.12, "HIGH"),           # +6% to +12%
    (float("inf"), "EXCEPTIONAL"),
)


def band_for(real_growth: float) -> str:
    """The ordinal for a real ANNUALISED growth rate, by GROWTH_BANDS."""
    for bar, name in GROWTH_BANDS:
        if real_growth < bar:
            return name
    return GROWTH_BANDS[-1][1]


def load_revenue(window_years: int = 1,
                 scorecard_dir: pathlib.Path | None = None
                 ) -> dict[str, tuple[float, float]]:
    """ticker -> (revenue_ttm, revenue_ttm at the start of the window).

    Same contract as `revenue_share.load_revenue` - which is the one-year case and stays
    the caller for `market_share_direction` - extended to the 3- and 5-year fields the
    scorecards already carry. A company missing either end is absent from the result
    entirely rather than present with a None: both windows or nothing, the same rule the
    totals depend on.
    """
    if window_years not in WINDOW_FIELD:
        raise ValueError(f"window_years must be one of {sorted(WINDOW_FIELD)}, "
                         f"not {window_years!r}")
    field = WINDOW_FIELD[window_years]
    d = pathlib.Path(scorecard_dir or config.SCORECARD_DIR)
    out: dict[str, tuple[float, float]] = {}
    for p in d.glob("*.json"):
        try:
            card = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        t = card.get("ticker")
        m = card.get("metrics") or {}
        now, then = m.get("revenue_ttm"), m.get(field)
        if not t or now is None or then is None:
            continue
        if not (isinstance(now, (int, float)) and isinstance(then, (int, float))):
            continue
        if not (math.isfinite(now) and math.isfinite(then)) or now <= 0 or then <= 0:
            continue
        out[str(t).upper()] = (float(now), float(then))
    return out


def load_shares(window_years: int = 1,
                scorecard_dir: pathlib.Path | None = None
                ) -> dict[str, tuple[float, float]]:
    """ticker -> (diluted_shares_ttm, the same at the start of the window).

    Same both-ends-or-nothing rule as `load_revenue`. Used only by the external-growth
    guard; a unit with no share data cannot be tested for it and is refused rather than
    waved through, because the units where this matters most are exactly the ones whose
    filings are most likely to be awkward.
    """
    if window_years not in WINDOW_FIELD:
        raise ValueError(f"window_years must be one of {sorted(WINDOW_FIELD)}, "
                         f"not {window_years!r}")
    field = WINDOW_FIELD[window_years].replace("revenue_ttm", "diluted_shares_ttm")
    d = pathlib.Path(scorecard_dir or config.SCORECARD_DIR)
    out: dict[str, tuple[float, float]] = {}
    for p in d.glob("*.json"):
        try:
            card = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        t = card.get("ticker")
        m = card.get("metrics") or {}
        now, then = m.get("diluted_shares_ttm"), m.get(field)
        if not t or now is None or then is None:
            continue
        if not (isinstance(now, (int, float)) and isinstance(then, (int, float))):
            continue
        if not (math.isfinite(now) and math.isfinite(then)) or now <= 0 or then <= 0:
            continue
        out[str(t).upper()] = (float(now), float(then))
    return out


def _annualised(now: float, then: float, years: int) -> float:
    """Compound annual rate. At years=1 this is the plain percentage change, so the
    one-year path is not a special case anywhere downstream."""
    return (now / then) ** (1.0 / years) - 1.0


def growth_for_industry(industry_id: str, members: list[str],
                        revenue: dict[str, tuple[float, float]],
                        *, deflator: float, window_years: int = 1,
                        shares: dict[str, tuple[float, float]] | None = None) -> dict:
    """Aggregate revenue growth for one unit, with every guard applied.

    Returns a dict that ALWAYS says what happened - `ok` False plus a `reason` when a
    guard refused it, rather than an empty result a caller could read as "no data". The
    three refusal reasons are the three ways the "similar companies" premise fails, and a
    caller that wants to report refusals (the journal does) needs to tell them apart.
    """
    if window_years not in WINDOW_FIELD:
        raise ValueError(f"window_years must be one of {sorted(WINDOW_FIELD)}, "
                         f"not {window_years!r}")
    out: dict = {"industry_id": industry_id, "members": len(members), "ok": False,
                 "window_years": window_years}
    usable = {t: revenue[t] for t in members if t in revenue}
    out["usable"] = len(usable)
    out["coverage"] = (len(usable) / len(members)) if members else 0.0
    if len(usable) < MIN_PEERS:
        out["reason"] = (f"{len(usable)} member(s) carry both revenue windows, "
                         f"under the {MIN_PEERS}-peer floor")
        return out

    # The structural guard runs BEFORE the totals, so an acquirer does not move the
    # denominator and make the whole unit read as growing. Compared ANNUALISED, so the
    # 0.40 bar means the same thing at one year as at three - on a three-year window a
    # raw-percentage bar would let a tripling through as a 40%-a-year grower.
    growth = {t: _annualised(now, prior, window_years)
              for t, (now, prior) in usable.items()}
    median_growth = statistics.median(growth.values())
    kept = {t: v for t, v in usable.items()
            if abs(growth[t] - median_growth) <= RS.STRUCTURAL_MOVE}
    out["excluded"] = sorted(set(usable) - set(kept))
    if len(kept) < MIN_PEERS:
        out["reason"] = (f"{len(kept)} member(s) left after excluding structural revenue "
                         f"moves, under the {MIN_PEERS}-peer floor")
        return out

    now = sum(v[0] for v in kept.values())
    prior = sum(v[1] for v in kept.values())
    if now <= 0 or prior <= 0:
        out["reason"] = "aggregate revenue is not positive in both windows"
        return out

    nominal = _annualised(now, prior, window_years)
    kept_growth = {t: growth[t] for t in kept}
    kept_median = statistics.median(kept_growth.values())
    top_ticker = max(kept, key=lambda t: kept[t][0])
    top_share = kept[top_ticker][0] / now

    out.update({"peers": len(kept), "revenue_now": now, "revenue_prior": prior,
                "nominal_growth": nominal, "median_growth": kept_median,
                "top_ticker": top_ticker, "top_share": top_share,
                "deflator": deflator, "real_growth": nominal - deflator})

    if top_share > MAX_TOP_SHARE:
        out["reason"] = (f"{top_ticker} is {top_share:.0%} of the unit's revenue, over the "
                         f"{MAX_TOP_SHARE:.0%} bar - this would be one company's growth "
                         f"with an industry's name on it")
        return out
    if abs(nominal - kept_median) > MAX_AGG_MEDIAN_GAP:
        out["reason"] = (f"aggregate {nominal:+.1%} against a median member of "
                         f"{kept_median:+.1%}, a gap of {abs(nominal - kept_median):.1%} "
                         f"over the {MAX_AGG_MEDIAN_GAP:.0%} bar - the aggregate is not "
                         f"describing the typical member")
        return out

    # Growth that arrived with new shares was bought, not earned. Tested over the SAME
    # members the revenue totals used, so the two figures are comparable.
    if shares is not None:
        paired = {t: shares[t] for t in kept if t in shares}
        if len(paired) < len(kept):
            out["reason"] = (f"share counts are missing for "
                             f"{len(kept) - len(paired)} of {len(kept)} members, so "
                             f"revenue growth cannot be separated from issuance")
            return out
        s_now = sum(v[0] for v in paired.values())
        s_then = sum(v[1] for v in paired.values())
        share_growth = _annualised(s_now, s_then, window_years)
        out["share_growth"] = share_growth
        out["revenue_per_share_growth"] = _annualised(
            (now / s_now), (prior / s_then), window_years)
        if share_growth > MAX_SHARE_GROWTH:
            bought = share_growth / nominal if nominal > 0 else float("nan")
            out["reason"] = (
                f"the unit's share count grew {share_growth:+.1%} a year against revenue "
                f"{nominal:+.1%}, so roughly {bought:.0%} of the growth came with "
                f"issuance - bought, not earned, and the assets were bought from owners "
                f"outside the listed set, so the listed aggregate grew while the industry "
                f"may not have (bar is {MAX_SHARE_GROWTH:+.0%})")
            return out

    out["ok"] = True
    out["value"] = band_for(out["real_growth"])
    return out


def agreeing_growth(industry_id: str, members: list[str],
                    revenue_by_window: dict[int, dict[str, tuple[float, float]]],
                    deflator_by_window: dict[int, float],
                    shares_by_window: dict[int, dict[str, tuple[float, float]]]
                    | None = None) -> dict:
    """The supported way to get an ordinal: every window must pass, and they must agree.

    Returns the SHORTER window's numbers as the headline (it is the more current read) with
    every window's result under `windows`, so a caller can report the agreement rather than
    just assert it.

    Refuses when any window refuses - an industry whose three-year history is too
    concentrated to measure is not rescued by its one-year history being wider - and when the
    windows land in different bands. The second case is the one that matters: it caught 3 of
    the 5 units this module had already written on 2026-09-12, including leisure_products at
    FLAT on one year and DECLINING on three.
    """
    windows = sorted(revenue_by_window)
    if len(windows) < 2:
        raise ValueError("agreeing_growth needs at least two windows; one window cannot "
                         "test its own stability")
    results = {w: growth_for_industry(industry_id, members, revenue_by_window[w],
                                      deflator=deflator_by_window[w], window_years=w,
                                      shares=(shares_by_window or {}).get(w))
               for w in windows}
    head = dict(results[windows[0]])
    head["windows"] = results
    head["windows_tested"] = windows

    refused = [(w, r["reason"]) for w, r in results.items() if not r["ok"]]
    if refused:
        head["ok"] = False
        head["reason"] = "; ".join(f"{w}y window: {why}" for w, why in refused)
        return head

    bands = {w: r["value"] for w, r in results.items()}
    if len(set(bands.values())) > 1:
        head["ok"] = False
        head["reason"] = (
            "the windows disagree - "
            + ", ".join(f"{w}y {results[w]['real_growth']:+.1%} {bands[w]}"
                        for w in windows)
            + ". An ordinal that changes with the window is a property of the window, not "
              "of the industry")
        return head

    head["ok"] = True
    head["value"] = bands[windows[0]]
    head["agreed_bands"] = bands
    return head
