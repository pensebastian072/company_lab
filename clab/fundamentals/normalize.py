"""Restatements, fiscal-period alignment, and YTD de-cumulation.

This is where correctness is won or lost. Three measured facts drove the design:

1. RESTATEMENTS ARE EXPLICIT. Up to 4 fact rows share one (start, end) for AAPL
   revenue - the same economic period reported repeatedly. Deduping by
   max(filed) gives today's restated view; min(filed) gives the point-in-time
   view. Both are computable, the chosen one is stamped into provenance, because
   a forward-return study run on restated numbers is look-ahead biased.

2. `frame` IS LOSSY AND CANNOT BE THE SERIES BACKBONE. EDGAR's frame field
   ("CY2026Q2") maps fiscal periods onto calendar quarters and is tempting. But
   NKE (May FYE) has 44 quarter-duration rows and only 25 framed, and COST skips
   CY2025Q2 and Q3 entirely. Building a series from frames silently drops
   quarters and produces wrong CAGRs. We classify by DURATION instead and use
   frame only as a peer-alignment key.

3. CASH-FLOW FACTS ARE CUMULATIVE AND MIXED. Measured: AAPL operating cash flow
   arrives as {ann: 48, 9mo: 30, qtr: 28, half: 28} rows; NVDA capex has only 3
   annual rows against 18 quarterly. Naive summation double-counts massively, so
   discrete quarters are derived explicitly: Q2 = H - Q1, Q3 = 9M - H, Q4 = FY - 9M.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Iterable, Literal

Duration = Literal["Q", "H", "9M", "FY", "INSTANT", "OTHER"]
View = Literal["current", "as_first_filed"]

# Duration windows in days. Wider than a textbook quarter because fiscal
# calendars are 13-week/52-53-week and companies drift a few days.
_BANDS: tuple[tuple[Duration, int, int], ...] = (
    ("Q", 80, 100),
    ("H", 170, 200),
    ("9M", 260, 290),
    ("FY", 350, 380),
)
_ANNUAL_FORMS = {"10-K", "10-K/A", "20-F", "40-F"}


def _d(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def classify(row: dict) -> Duration:
    """Duration bucket for one fact row. Instant facts have no `start`."""
    start, end = _d(row.get("start")), _d(row.get("end"))
    if end is None:
        return "OTHER"
    if start is None:
        return "INSTANT"
    days = (end - start).days
    for name, lo, hi in _BANDS:
        if lo <= days <= hi:
            return name
    return "OTHER"


@dataclass
class Fact:
    """One economic observation, after dedupe and (possibly) derivation."""

    end: date
    val: float
    start: date | None = None
    duration: Duration = "OTHER"
    accn: str | None = None
    filed: str | None = None
    form: str | None = None
    fy: int | None = None
    fp: str | None = None
    frame: str | None = None
    derived: bool = False
    derivation: str = ""            # "direct" | "derived_from_ytd:Q4=FY-9M"
    n_restatements: int = 0

    @property
    def end_iso(self) -> str:
        return self.end.isoformat()

    def provenance(self) -> dict:
        return {
            "accn": self.accn,
            "filed": self.filed,
            "form": self.form,
            "period_end": self.end_iso,
            "duration": self.duration,
            "derived": self.derived,
            "derivation": self.derivation,
            "n_restatements": self.n_restatements,
        }


def _to_fact(row: dict, duration: Duration, n_restatements: int = 0) -> Fact | None:
    end = _d(row.get("end"))
    if end is None:
        return None
    try:
        val = float(row["val"])
    except (KeyError, TypeError, ValueError):
        return None
    return Fact(
        end=end, val=val, start=_d(row.get("start")), duration=duration,
        accn=row.get("accn"), filed=row.get("filed"), form=row.get("form"),
        fy=row.get("fy"), fp=row.get("fp"), frame=row.get("frame"),
        derived=False, derivation="direct", n_restatements=n_restatements,
    )


def dedupe(rows: Iterable[dict], view: View = "current") -> list[Fact]:
    """Collapse restatements. One Fact per (start, end).

    view="current"        -> max(filed): the latest restated value. Default; what
                             the scoring engine uses, because it is the best
                             current estimate of what happened.
    view="as_first_filed" -> min(filed): the point-in-time value. Used ONLY by
                             the deferred forward-return grader; scoring a past
                             date on restated data is look-ahead bias.

    Ties on `filed` break on the lexicographically greater `accn`.
    """
    groups: dict[tuple[str | None, str | None], list[dict]] = {}
    for r in rows or ():
        groups.setdefault((r.get("start"), r.get("end")), []).append(r)

    out: list[Fact] = []
    for (_start, _end), grp in groups.items():
        # Order the group by preference, then take the first row that actually
        # converts. Picking only the single most-preferred row would drop the whole
        # period when the newest filing carries a null or malformed value - and
        # then a quarter silently vanishes from the series.
        if view == "current":
            ordered = sorted(grp, key=lambda r: ((r.get("filed") or ""),
                                                 (r.get("accn") or "")), reverse=True)
        else:
            ordered = sorted(grp, key=lambda r: ((r.get("filed") or "9999"),
                                                 (r.get("accn") or "")))
        for pick in ordered:
            f = _to_fact(pick, classify(pick), n_restatements=len(grp) - 1)
            if f is not None:
                out.append(f)
                break
    out.sort(key=lambda f: (f.end, f.start or date.min))
    return out


def by_duration(facts: Iterable[Fact]) -> dict[Duration, list[Fact]]:
    buckets: dict[Duration, list[Fact]] = {}
    for f in facts:
        buckets.setdefault(f.duration, []).append(f)
    for v in buckets.values():
        v.sort(key=lambda f: f.end)
    return buckets


def instants(rows: Iterable[dict], view: View = "current") -> list[Fact]:
    """Balance-sheet series: keyed on `end` alone, sorted oldest first."""
    return [f for f in dedupe(rows, view) if f.duration == "INSTANT"]


def latest_instant(rows: Iterable[dict], view: View = "current") -> Fact | None:
    seq = instants(rows, view)
    return seq[-1] if seq else None


# ------------------------------------------------------------------ de-cumulation
@dataclass
class QuarterSeries:
    """Discrete (non-cumulative) quarterly facts, oldest first, plus diagnostics."""

    facts: list[Fact] = field(default_factory=list)
    n_direct: int = 0
    n_derived: int = 0
    n_suspect: int = 0
    notes: list[str] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.facts)

    @property
    def values(self) -> list[float]:
        return [f.val for f in self.facts]

    def last(self, n: int) -> list[Fact]:
        return self.facts[-n:] if n <= len(self.facts) else []

    def provenance(self) -> dict:
        return {
            "n_quarters": len(self.facts),
            "n_direct": self.n_direct,
            "n_derived": self.n_derived,
            "n_suspect_dropped": self.n_suspect,
            "notes": self.notes,
        }


def _fiscal_year_key(f: Fact) -> tuple:
    """Group cumulative rows by the fiscal year they accumulate within.

    YTD rows for one fiscal year share a `start`, so start is the natural key;
    fy is the fallback when start is absent.
    """
    return (f.start.isoformat() if f.start else f"fy{f.fy}",)


def discrete_quarters(
    rows: Iterable[dict],
    *,
    view: View = "current",
    suspect_ratio: float = -0.5,
) -> QuarterSeries:
    """Build a discrete quarterly series from mixed-duration cumulative facts.

    Algorithm:
      1. Every Q-duration row is taken directly.
      2. Within each fiscal year, fill gaps by differencing YTD rows:
             Q2 = H - Q1,  Q3 = 9M - H,  Q4 = FY - 9M
         Q4 is almost never filed discretely; this is the standard derivation.
      3. Every derived value is marked derivation="derived_from_ytd:...".
      4. Sanity guard: a derived quarter below `suspect_ratio` x the trailing 4Q
         mean is dropped to NO_DATA rather than scored on garbage.
    """
    facts = dedupe(rows, view)
    series = QuarterSeries()
    direct = {f.end: f for f in facts if f.duration == "Q"}
    series.facts = sorted(direct.values(), key=lambda f: f.end)
    series.n_direct = len(direct)

    # cumulative rows grouped by fiscal-year start
    cum: dict[tuple, dict[Duration, Fact]] = {}
    for f in facts:
        if f.duration in ("H", "9M", "FY"):
            cum.setdefault(_fiscal_year_key(f), {})[f.duration] = f

    derived: list[Fact] = []
    for _key, buckets in sorted(cum.items()):
        fy_start = None
        for f in buckets.values():
            fy_start = f.start or fy_start
        # ordered YTD ladder for this fiscal year
        ladder = [("H", 2), ("9M", 3), ("FY", 4)]
        prev_dur: Duration | None = None
        for dur, _n in ladder:
            cur = buckets.get(dur)
            if cur is None:
                continue
            # cumulative value already covered by direct quarters inside it?
            inner = [f for f in series.facts
                     if fy_start is not None and f.start is not None
                     and f.start >= fy_start and f.end <= cur.end]
            if any(f.end == cur.end for f in series.facts):
                prev_dur = dur
                continue
            prior = buckets.get(prev_dur) if prev_dur else None
            if prior is not None:
                base, label = prior.val, f"{dur}-{prev_dur}"
            elif inner:
                base, label = sum(f.val for f in inner), f"{dur}-sum(direct)"
            else:
                prev_dur = dur
                continue
            val = cur.val - base
            derived.append(Fact(
                end=cur.end, val=val,
                start=(inner[-1].end if inner else (prior.end if prior else fy_start)),
                duration="Q", accn=cur.accn, filed=cur.filed, form=cur.form,
                fy=cur.fy, fp=cur.fp, frame=cur.frame,
                derived=True, derivation=f"derived_from_ytd:{label}",
                n_restatements=cur.n_restatements,
            ))
            prev_dur = dur

    if derived:
        merged = {f.end: f for f in series.facts}
        for f in derived:
            merged.setdefault(f.end, f)     # direct always wins over derived
        series.facts = sorted(merged.values(), key=lambda f: f.end)
        series.n_derived = sum(1 for f in series.facts if f.derived)

    # sanity guard on derived values
    kept: list[Fact] = []
    for i, f in enumerate(series.facts):
        if f.derived and i >= 4:
            window = [g.val for g in series.facts[max(0, i - 4):i]]
            mean = sum(window) / len(window) if window else 0.0
            if mean > 0 and f.val < suspect_ratio * mean:
                series.n_suspect += 1
                series.notes.append(
                    f"dropped suspect derived quarter {f.end_iso} "
                    f"({f.val:.4g} vs trailing mean {mean:.4g})"
                )
                continue
        kept.append(f)
    series.facts = kept
    return series


def annual_facts(rows: Iterable[dict], *, view: View = "current") -> list[Fact]:
    """FY-duration facts only, oldest first. Used for long-horizon CAGRs."""
    return [f for f in dedupe(rows, view) if f.duration == "FY"]


def ttm(series: QuarterSeries, *, min_quarters: int = 4) -> tuple[float | None, dict]:
    """Trailing twelve months = the 4 most recent consecutive discrete quarters.

    Returns (None, diagnostics) with fewer than 4 - never 0, because 0 would be
    scored as a real value.
    """
    facts = series.facts
    if len(facts) < min_quarters:
        return None, {"quarters_available": len(facts), "reason": "insufficient_quarters"}
    window = facts[-min_quarters:]
    # consecutiveness check: ~90 days apart, tolerate 60..130
    gaps = [(window[i + 1].end - window[i].end).days for i in range(len(window) - 1)]
    if any(g < 55 or g > 135 for g in gaps):
        return None, {"quarters_available": len(facts), "gaps_days": gaps,
                      "reason": "non_consecutive_quarters"}
    total = sum(f.val for f in window)
    return total, {
        "quarters_available": len(facts),
        "quarters_used": [f.end_iso for f in window],
        "period_end": window[-1].end_iso,
        "any_derived": any(f.derived for f in window),
        "gaps_days": gaps,
    }


def ttm_at(series: QuarterSeries, offset_quarters: int, *, min_quarters: int = 4):
    """TTM ending `offset_quarters` before the latest. offset 4 = prior-year TTM."""
    facts = series.facts
    end_idx = len(facts) - offset_quarters
    if end_idx < min_quarters:
        return None, {"quarters_available": len(facts), "reason": "insufficient_history"}
    sub = QuarterSeries(facts=facts[:end_idx])
    return ttm(sub, min_quarters=min_quarters)


def cagr(latest: float | None, earlier: float | None, years: float) -> float | None:
    """Compound annual growth. None when undefined (sign change, zero base, <=0 years).

    A negative or zero base makes the root meaningless, so it returns None rather
    than a number that would be silently scored.
    """
    if latest is None or earlier is None or years <= 0:
        return None
    if earlier <= 0 or latest <= 0:
        return None
    try:
        return (latest / earlier) ** (1.0 / years) - 1.0
    except (ValueError, ZeroDivisionError, OverflowError):
        return None


def yoy(latest: float | None, prior: float | None) -> float | None:
    """Year-over-year change. Uses abs(prior) so a negative base gives a sane sign."""
    if latest is None or prior is None or prior == 0:
        return None
    return (latest - prior) / abs(prior)


def linreg_slope(ys: list[float], xs: list[float] | None = None) -> float | None:
    """OLS slope, stdlib only. Used for the margin-expansion trend."""
    n = len(ys)
    if n < 3:
        return None
    xs = xs if xs is not None else list(range(n))
    mx = sum(xs) / n
    my = sum(ys) / n
    denom = sum((x - mx) ** 2 for x in xs)
    if denom == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom


def align_frame_key(f: Fact) -> str | None:
    """Peer-comparison alignment key.

    `frame` where EDGAR supplies it, else the fiscal period end bucketed to the
    nearest calendar quarter. Only used for peer-relative valuation, where a
    one-quarter misalignment is noise - never for growth math, where it is fatal.
    """
    if f.frame:
        return f.frame
    if f.end is None:
        return None
    q = (f.end.month - 1) // 3 + 1
    return f"CY{f.end.year}Q{q}"
