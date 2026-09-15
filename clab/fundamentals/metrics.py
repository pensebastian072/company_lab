"""The metric bundle: raw XBRL -> every number the quantitative components need.

One pass over a companyfacts blob produces a MetricBundle holding values,
per-value provenance (which tag, which accession, whether derived), and the
diagnostics that let a scorecard show its work.

Rules that hold throughout:
  - A missing input yields None, never 0. The scoring layer turns None into
    NO_DATA, which is structurally different from earning zero points.
  - Growth is measured TTM-over-TTM (4 / 12 / 20 quarters back) rather than from
    FY facts, because TTM sidesteps fiscal-calendar misalignment entirely. FY
    facts are the fallback when quarterly history is too short.
  - Derived quantities (FCF, EBITDA, net debt, ROIC) record the inputs they were
    built from so a wrong number is traceable to its source in one step.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from ..scoring import rubric
from . import normalize as nz
from . import tags
from .profile import SectorProfile

#: interest coverage above this is reported as this value with a flag, so no
#: Infinity ever reaches JSON, parquet or CSV.
COVERAGE_CAP = 999.0

#: Two facts sharing an end date may be combined only if their periods are the same
#: length to within this many days. Wide enough for 13-week vs 3-month quarter drift and
#: a 52/53-week retail calendar; far narrower than a quarter-vs-year mismatch.
PERIOD_MATCH_TOLERANCE_DAYS = 20


@dataclass
class MetricBundle:
    values: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, dict] = field(default_factory=dict)
    series: dict[str, nz.QuarterSeries] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    #: metric -> why it was rejected. Read by `context.subtest` to raise
    #: DATA_QUALITY_FAIL instead of the NO_DATA a nulled value would otherwise produce.
    quality_failures: dict[str, str] = field(default_factory=dict)
    view: str = "current"

    def set(self, key: str, value: Any, prov: dict | None = None) -> None:
        self.values[key] = value
        if prov:
            self.provenance[key] = prov

    def get(self, key: str, default=None):
        v = self.values.get(key, default)
        return default if v is None else v

    def raw(self, key: str):
        return self.values.get(key)

    def prov(self, *keys: str) -> dict:
        """Merged provenance for the named metrics - what a SubTest records."""
        out: dict[str, Any] = {"source": "edgar", "tags_used": {}}
        for k in keys:
            p = self.provenance.get(k)
            if not p:
                continue
            if p.get("tag_used"):
                out["tags_used"][k] = p["tag_used"]
            for f in ("accn", "filed", "period_end"):
                if p.get(f) and f not in out:
                    out[f] = p[f]
            if p.get("derived"):
                out.setdefault("derived", []).append(k)
        return out

    def as_flat(self) -> dict:
        return {k: v for k, v in self.values.items()
                if isinstance(v, (int, float, str, bool)) or v is None}


# ------------------------------------------------------------------ extraction
def _flow_series(payload: dict, metric: str, view: str) -> tuple[str | None, nz.QuarterSeries]:
    tag, rows = tags.resolve(payload, metric)
    if tag is None:
        return None, nz.QuarterSeries()
    return tag, nz.discrete_quarters(rows, view=view)


def _instant_latest(payload: dict, metric: str, view: str) -> tuple[str | None, nz.Fact | None]:
    tag, rows = tags.resolve_instant(payload, metric)
    if tag is None:
        return None, None
    return tag, nz.latest_instant(rows, view)


def _instant_at(payload: dict, metric: str, view: str, back: int = 4):
    """The instant fact ~`back` quarters before the latest (for average balances)."""
    tag, rows = tags.resolve_instant(payload, metric)
    if tag is None:
        return None, None
    seq = nz.instants(rows, view)
    if not seq:
        return tag, None
    idx = len(seq) - 1 - back
    return tag, (seq[idx] if idx >= 0 else seq[0])


def _sum_instants(payload: dict, metrics: tuple[str, ...], view: str) -> tuple[float | None, dict]:
    """Sum of several instant tags at their latest values. None if none resolve."""
    total = 0.0
    used: dict[str, str] = {}
    found = False
    for m in metrics:
        tag, fact = _instant_latest(payload, m, view)
        if tag and fact is not None:
            total += fact.val
            used[m] = tag
            found = True
    return (total if found else None), {"tag_used": used or None}


def _dominates(candidate, incumbent, ratio: float = 1.5) -> bool:
    """True when `candidate` is materially larger than `incumbent` on shared periods.

    An EMPTY incumbent is dominated by anything - that is the original "no revenue tag at
    all" fallback, preserved. With no shared periods the incumbent is left alone: two
    series covering different years say nothing about each other's completeness.
    """
    if not len(incumbent):
        return bool(len(candidate))
    a = {(f.start, f.end): f.val for f in candidate.facts}
    b = {(f.start, f.end): f.val for f in incumbent.facts}
    keys = [k for k in a.keys() & b.keys()
            if isinstance(a[k], (int, float)) and isinstance(b[k], (int, float))]
    if not keys:
        return False
    va = sorted(abs(float(a[k])) for k in keys)
    vb = sorted(abs(float(b[k])) for k in keys)
    med_b = vb[len(vb) // 2]
    return med_b > 0 and va[len(va) // 2] / med_b >= ratio


def _overlap_ratio(candidate, incumbent) -> float | None:
    """Median |candidate| / |incumbent| over the periods they SHARE, or None if none.

    None means "these two series say nothing about each other", which must never be read
    as agreement - the A/B caught a filer whose lease income shared no period with its
    revenue tag and replaced a $7.56bn series with a $2.99bn one on freshness alone.
    """
    a = {(f.start, f.end): f.val for f in candidate.facts}
    b = {(f.start, f.end): f.val for f in incumbent.facts}
    keys = [k for k in a.keys() & b.keys()
            if isinstance(a[k], (int, float)) and isinstance(b[k], (int, float))]
    if not keys:
        return None
    va = sorted(abs(float(a[k])) for k in keys)
    vb = sorted(abs(float(b[k])) for k in keys)
    med_b = vb[len(vb) // 2]
    return None if med_b <= 0 else va[len(va) // 2] / med_b


#: On the periods two revenue series share, the substitute must be at least this much of
#: the incumbent to count as measuring the same business rather than a piece of it. A
#: lessor's rent IS its revenue, so the real cases sit near 1.0; a component sits far below.
SUBSTITUTE_MIN_OVERLAP_RATIO = 0.67
#: and materially ABOVE the incumbent means it is not the same measurement either -
#: Iron Mountain's storage rent is 1.72x its contract-revenue tag because they are two
#: halves of one business, not two attempts at the same total.
SUBSTITUTE_MAX_OVERLAP_RATIO = 1.5


def _rescues_a_stranded_series(candidate, incumbent) -> bool:
    """Prefer `candidate` when the incumbent cannot reach the present and they agree.

    The generalisation of the lessor-revenue rule to the rest of the income statement. A
    filer that stops tagging `GrossProfit` or `OperatingIncomeLoss` leaves a full-length
    series stranded years in the past; pairing it with current revenue produces a ratio
    spanning two different periods, which `RATIO_PERIOD_MAX_GAP_DAYS` correctly refuses -
    so the sub-test is WITHHELD when a perfectly good derivation was available.

    Same two guards the lessor case needed, and for the same reason: the replacement must
    reach further, and it must AGREE with the incumbent where the two overlap, or it is
    measuring something else and swapping it in is the fragment bug wearing a new hat.
    """
    if not len(candidate) or not _reaches_further(candidate, incumbent):
        return False
    ratio = _overlap_ratio(candidate, incumbent)
    return (ratio is not None
            and SUBSTITUTE_MIN_OVERLAP_RATIO <= ratio <= SUBSTITUTE_MAX_OVERLAP_RATIO
            and nz.ttm(candidate)[0] is not None)


def _reaches_further(candidate, incumbent, days: int = 400) -> bool:
    """True when `candidate` supplies a recent end the incumbent cannot reach.

    The `days` default is `tags.STALE_TAG_DAYS`, repeated rather than imported so the two
    stay independently adjustable: this one governs whether a WHOLE series is stranded in
    the past, not whether one tag may supply the end of another's.
    """
    if not len(candidate):
        return False
    if not len(incumbent):
        return True
    c = max(f.end for f in candidate.facts)
    i = max(f.end for f in incumbent.facts)
    return (c - i).days > days


def ttm_share_count(series) -> tuple[float | None, dict]:
    """Average diluted share count over the last four CLEAN quarters.

    A share count is an AVERAGE, not a flow, so one poisoned quarter wrecks the mean
    rather than nudging it. Measured on AAPL 2026-08-20: the FY 10-K filed a Q-duration
    `diluted_shares` row of **-47,029,000** - a change in shares, not a count - and
    averaging it with three real quarters gave 11.05bn against a true ~14.8bn.
    Universe-wide the TTM count ran 25% light (median implied/actual 1.32, p10 1.23,
    p90 1.39), and every per-share number downstream inherited it. The forward DCF is
    what finally made it visible: a median margin of safety of +24%, which is the market
    being wrong about 60% of the universe or us being wrong about share counts.

    `normalize.py`'s derived-quarter guard cannot catch this one - the row is DIRECT,
    filed with a ~91-day duration, so nothing about it looks derived. A count is
    therefore filtered on its own terms: positive, and within a factor of two of its
    neighbours' median.
    """
    # `QuarterSeries.last(n)` returns [] when the series holds FEWER than n facts, so
    # asking it for 8 would silently wipe the share count of every company with 5-7
    # quarters of history. The tail slice is what was meant.
    recent = series.facts[-8:]
    window = [f for f in recent if f.val is not None and f.val > 0]
    if not window:
        return None, {"quarters_used": [], "quarters_dropped": [],
                      "rule": "no positive share count in the last 8 quarters"}
    vals = sorted(f.val for f in window)
    med = vals[len(vals) // 2]
    clean = [f for f in window if 0.5 * med <= f.val <= 2.0 * med][-4:]
    used = {f.end_iso for f in clean}
    dropped = [f.end_iso for f in recent if f.end_iso not in used]
    if not clean:
        return None, {"quarters_used": [], "quarters_dropped": dropped,
                      "rule": "every quarter was an outlier against its own median"}
    return sum(f.val for f in clean) / len(clean), {
        "quarters_used": sorted(used),
        "quarters_dropped": dropped,
        "rule": "positive and within 2x the 8-quarter median; a share count is an "
                "average, so one bad quarter cannot be averaged in",
    }


def build_metrics(
    payload: dict,
    *,
    profile: SectorProfile | None = None,
    view: str = "current",
) -> MetricBundle:
    """Everything the quant components need, from one companyfacts blob."""
    M = MetricBundle(view=view)
    if not isinstance(payload, dict) or not payload.get("facts"):
        M.warnings.append("companyfacts payload empty or malformed")
        return M

    # ---------------------------------------------------------- flow series
    flow_metrics = (
        "revenue", "cogs", "gross_profit", "operating_income", "operating_expenses",
        "net_income", "eps_diluted", "diluted_shares", "cfo", "capex", "rnd",
        "dep_amort", "sbc", "interest_expense", "tax_expense", "pretax_income",
        "buybacks", "dividends", "ma_spend", "impairment",
    )
    tag_used: dict[str, str | None] = {}
    for m in flow_metrics:
        tag, series = _flow_series(payload, m, view)
        tag_used[m] = tag
        M.series[m] = series

    # financial-sector revenue substitute.
    #
    # E30, 2026-08-25: this used to fire ONLY on `len(...) == 0`, and that is one guard
    # short in exactly the way the COST gross-profit note below describes. FITB files no
    # `Revenues` at all, but it does file
    # `RevenueFromContractWithCustomerIncludingAssessedTax` of $617m - card and deposit
    # fees - so the chain came back NON-EMPTY and the substitute never ran. Its real
    # revenue is interest and dividend income $11.35bn plus non-interest income $3.49bn.
    # Measured across the universe, 41 of 257 Financials carried a fragment this way, and
    # every margin, growth rate and revenue multiple inherited it.
    #
    # An empty series is a fallback; a series dwarfed by the sum of its own components is
    # a bug, so the trigger is dominance, not absence.
    ii_tag, ii = _flow_series(payload, "interest_income_operating", view)
    ni_tag, nii = _flow_series(payload, "noninterest_income", view)
    if len(ii) and len(nii):
        substitute = _add_series(ii, nii)
        if _dominates(substitute, M.series["revenue"]):
            M.series["revenue"] = substitute
            tag_used["revenue"] = f"{ii_tag}+{ni_tag}"

    # REIT / lessor revenue substitute. Same shape as the bank one and a second trigger:
    # a lease series that REACHES THE PRESENT beats a revenue series that stopped years
    # ago, even when it is not larger. EQR's `Revenues` and contract-revenue tags both
    # end 2020-03-31 while `OperatingLeaseLeaseIncome` runs to 2026-06-30, so without
    # this the company is scored on six-year-old revenue and its growth rates are
    # arithmetic about a period nobody asked about. Replaced wholesale rather than
    # merged: splicing a component onto a total's history manufactures a growth rate at
    # the join.
    #
    # The freshness trigger needs its own guard, and the A/B caught the case: one filer
    # went from $7.56bn to $2.99bn because its lease income simply ran further than its
    # revenue tag. Replacing a larger series with a smaller one on freshness alone is the
    # fragment bug in reverse, so a lease series the incumbent DOMINATES on their shared
    # periods is a component and never substitutes - only one that is comparable or
    # larger there, which is what a lessor's rent is.
    # NOTE the dominance test used for the bank substitute is deliberately NOT used here.
    # "A component cannot exceed its total" holds INSIDE the revenue chain, where every
    # member is a candidate total. Lease income is not a candidate total - for a filer
    # with both, it is one half of the business. The A/B caught it: Iron Mountain's
    # storage rent runs 1.72x its contract-revenue tag over their shared periods, because
    # those are two HALVES of $7.56bn, and dominance replaced the total with the half.
    #
    # So the only trigger here is the stranded case: the incumbent cannot reach the
    # present at all, and this is the only series that still measures the company. Even
    # then it must overlap the incumbent, AGREE with it in magnitude there (so it is the
    # same business and not a piece of it), and yield a usable TTM - without those two
    # guards the A/B found a filer that shared no period at all and another whose revenue
    # became None outright.
    li_tag, li = _flow_series(payload, "lease_income", view)
    if len(li) and _reaches_further(li, M.series["revenue"]):
        ratio = _overlap_ratio(li, M.series["revenue"])
        if (ratio is not None
                and SUBSTITUTE_MIN_OVERLAP_RATIO <= ratio <= SUBSTITUTE_MAX_OVERLAP_RATIO
                and nz.ttm(li)[0] is not None):
            M.series["revenue"] = li
            tag_used["revenue"] = li_tag

    # interest expense: fall back to the NET tag, which needs a sign flip
    if len(M.series["interest_expense"]) == 0:
        tag, net_series = _flow_series(payload, "interest_expense_net", view)
        if len(net_series):
            flipped = nz.QuarterSeries(
                facts=[nz.Fact(end=f.end, val=-f.val, start=f.start, duration=f.duration,
                               accn=f.accn, filed=f.filed, form=f.form, fy=f.fy, fp=f.fp,
                               frame=f.frame, derived=True,
                               derivation="sign_flip:InterestIncomeExpenseNet",
                               n_restatements=f.n_restatements)
                       for f in net_series.facts],
                n_direct=net_series.n_direct, n_derived=len(net_series.facts),
                notes=["interest expense derived from the net tag (sign flipped)"],
            )
            M.series["interest_expense"] = flipped
            tag_used["interest_expense"] = f"{tag} (sign flipped)"

    # derived: gross profit = revenue - cogs.
    # Also PREFER the derivation when the direct GrossProfit series is far shorter
    # than revenue: measured on COST, whose GrossProfit tag carries 4 rows against
    # 71 revenue quarters and produced a 5.6% gross margin against a true ~11%.
    # A 4-row tag is a partial disclosure, not the consolidated line.
    # E30 adds the STRANDED case beside the thin one: measured over 235 filings,
    # `GrossProfit` is stale by more than 400 days against revenue for 6.4% of filers and
    # absent for 52.8%. A stale full-length series passes the length test and then pairs a
    # 2020 numerator with 2026 revenue, which the ratio guard refuses - so the point was
    # withheld while `revenue - cogs` sat there current and usable.
    gp_thin = len(M.series["gross_profit"]) < 0.5 * max(len(M.series["revenue"]), 1)
    if len(M.series["revenue"]) and len(M.series["cogs"]):
        derived_gp = _sub_series(M.series["revenue"], M.series["cogs"])
        gp_stranded = _rescues_a_stranded_series(derived_gp, M.series["gross_profit"])
        if (gp_thin and len(derived_gp) > len(M.series["gross_profit"])) or gp_stranded:
            M.series["gross_profit"] = derived_gp
            tag_used["gross_profit"] = f"derived: {tag_used['revenue']} - {tag_used['cogs']}"
    # The length test above is necessary and NOT sufficient. It catches a 4-row partial
    # disclosure; it cannot catch a full-length GrossProfit that is simply wrong, and
    # measured 2026-08-16 that is the common case - INTU 30.1% (true ~81.5%), ORCL 96.3%
    # (~70%), FICO 39.0% (~80%), EXEL 29.0% (~96%), all inside 0-100% and all wrong.
    #
    # `cogs` is a PRIORITY chain (tags.py) and `resolve()` merges by (start, end) with
    # the earlier chain position winning, so a filer splitting cost across product and
    # service tags has the second silently dropped. Rather than guess which tag set to
    # sum - summing a consolidated total with its own components double-counts - the two
    # independent derivations are compared. Disagreement means the pairing is wrong, and
    # that is recorded rather than resolved in favour of whichever looks nicer.
    _cross_check_gross_profit(M, tag_used)

    # derived: operating income = gross profit - operating expenses
    if len(M.series["operating_income"]) == 0 and len(M.series["gross_profit"]) \
            and len(M.series["operating_expenses"]):
        M.series["operating_income"] = _sub_series(
            M.series["gross_profit"], M.series["operating_expenses"])
        tag_used["operating_income"] = "derived: gross_profit - operating_expenses"

    # derived: EBIT = pretax income + interest expense.
    # Oil majors and banks (XOM, JPM measured) file no OperatingIncomeLoss line
    # at all - they present "total revenues and other income" less costs. This is
    # the standard EBIT reconstruction and it rescues operating margin, EBITDA,
    # ROIC and the stress test for those filers instead of leaving a quarter of
    # the framework blank.
    #
    # E30: also when the filed series is STRANDED rather than absent. 4.7% of filers stop
    # tagging `OperatingIncomeLoss` and leave a series years behind their revenue - one
    # sampled filer's ends 2010-12-31 - and the reconstruction is available and current.
    if len(M.series["pretax_income"]):
        if len(M.series["interest_expense"]):
            ebit = _add_series(M.series["pretax_income"], M.series["interest_expense"])
            label = "derived: pretax_income + interest_expense (EBIT)"
        else:
            ebit = M.series["pretax_income"]
            label = "derived: pretax_income (no interest expense filed)"
        if (len(M.series["operating_income"]) == 0
                or _rescues_a_stranded_series(ebit, M.series["operating_income"])):
            M.series["operating_income"] = ebit
            tag_used["operating_income"] = label

    # derived: D&A from parts
    if len(M.series["dep_amort"]) == 0:
        _, dep = _flow_series(payload, "dep_amort_parts", view)
        if len(dep):
            M.series["dep_amort"] = dep
            tag_used["dep_amort"] = "Depreciation/AmortizationOfIntangibleAssets"

    # ---------------------------------------------------------- TTM levels
    annual_cache: dict[str, list[nz.Fact]] = {}

    def _annual(m: str) -> list[nz.Fact]:
        if m not in annual_cache:
            _t, rows = tags.resolve(payload, m)
            annual_cache[m] = nz.annual_facts(rows, view=view) if rows else []
        return annual_cache[m]

    for m in ("revenue", "gross_profit", "operating_income", "net_income", "cfo",
              "capex", "rnd", "dep_amort", "sbc", "interest_expense", "tax_expense",
              "pretax_income", "buybacks", "dividends", "ma_spend", "impairment",
              "operating_expenses", "cogs"):
        s = M.series.get(m) or nz.QuarterSeries()
        val, diag = nz.ttm(s)
        prov = {"tag_used": tag_used.get(m), **diag, **s.provenance()}
        if val is None:
            # Annual fallback: a filer with only FY rows for this line (measured on
            # XOM cash flow, NVDA capex before the tag merge) still has a usable
            # trailing-year figure. Flagged so the scorecard shows it is an annual
            # number standing in for a TTM, not a computed TTM.
            fy = _annual(m)
            if fy:
                val = fy[-1].val
                prov = {**prov, "annual_fallback": True,
                        "period_end": fy[-1].end_iso, "accn": fy[-1].accn,
                        "reason": "fewer than 4 discrete quarters; latest FY fact used"}
        M.set(f"{m}_ttm", val, prov)
        for off, label, yrs in ((4, "prior", 1), (12, "3y_ago", 3), (20, "5y_ago", 5)):
            v, _ = nz.ttm_at(s, off)
            if v is None:
                fy = _annual(m)
                idx = len(fy) - 1 - yrs
                if fy and idx >= 0:
                    v = fy[idx].val
            M.set(f"{m}_ttm_{label}", v)

    # diluted shares / EPS are averages, not sums
    for m in ("diluted_shares", "eps_diluted"):
        s = M.series.get(m) or nz.QuarterSeries()
        if m == "eps_diluted":
            val, diag = nz.ttm(s)          # EPS does sum across quarters
        else:
            val, diag = ttm_share_count(s)
        M.set(f"{m}_ttm", val, {"tag_used": tag_used.get(m), **diag})
        for off, label in ((4, "prior"), (12, "3y_ago"), (20, "5y_ago")):
            if m == "eps_diluted":
                v, _ = nz.ttm_at(s, off)
            else:
                # E30: this was a hand-rolled `sum(facts[-4:]) / 4.0` while the CURRENT
                # value went through `ttm_share_count`. Two code paths for one quantity,
                # and only one of them had E28's outlier filter - so the prior window
                # still averaged in the poisoned rows and came out ~25% light. The
                # result was a UNIVERSAL fake dilution: median `dilution_yoy` +32.5%,
                # almost exactly 4/3, so 97% of all 1,469 companies scored 0 on
                # `bs_dilution` in all eleven sectors, including every serial
                # repurchaser. One derivation, one filter, both windows.
                facts = s.facts[:len(s.facts) - off]
                v, _ = ttm_share_count(nz.QuarterSeries(facts=facts)) if facts \
                    else (None, {})
            M.set(f"{m}_ttm_{label}", v)

    # ---------------------------------------------------------- derived flows
    cfo, capex = M.raw("cfo_ttm"), M.raw("capex_ttm")
    # FCF = CFO - capex. SBC is NOT added back: it is a real cost. sbc_pct_revenue
    # is surfaced separately so FCF quality stays visible.
    M.set("fcf_ttm", (cfo - capex) if (cfo is not None and capex is not None) else None,
          {"derived": True, "formula": "cfo_ttm - capex_ttm",
           "tag_used": {"cfo": tag_used.get("cfo"), "capex": tag_used.get("capex")}})
    for label in ("prior", "3y_ago", "5y_ago"):
        c, k = M.raw(f"cfo_ttm_{label}"), M.raw(f"capex_ttm_{label}")
        M.set(f"fcf_ttm_{label}", (c - k) if (c is not None and k is not None) else None)

    opinc, da = M.raw("operating_income_ttm"), M.raw("dep_amort_ttm")
    M.set("ebitda_ttm", (opinc + da) if (opinc is not None and da is not None) else None,
          {"derived": True, "formula": "operating_income_ttm + dep_amort_ttm"})

    # ---------------------------------------------------------- instants
    cash_tag, cash_f = _instant_latest(payload, "cash", view)
    M.set("cash", cash_f.val if cash_f else None,
          {"tag_used": cash_tag, **(cash_f.provenance() if cash_f else {})})
    sti_tag, sti_f = _instant_latest(payload, "short_term_investments", view)
    M.set("short_term_investments", sti_f.val if sti_f else None, {"tag_used": sti_tag})
    cash_sti = None
    if cash_f is not None:
        cash_sti = cash_f.val + (sti_f.val if sti_f else 0.0)
    M.set("cash_sti", cash_sti, {"derived": True, "formula": "cash + short_term_investments"})

    for m in ("assets", "assets_current", "liabilities_current", "equity", "goodwill",
              "tier1_ratio", "debt_long_noncurrent", "debt_long_current", "debt_short",
              "maturity_1y"):
        t, f = _instant_latest(payload, m, view)
        M.set(m, f.val if f else None, {"tag_used": t})

    # total debt: components first, combined tag as fallback
    parts = []
    for m in ("debt_long_noncurrent", "debt_long_current", "debt_short"):
        v = M.raw(m)
        if v is not None:
            parts.append(v)
    lease_total, lease_prov = _sum_instants(
        payload, ("finance_lease_noncurrent", "finance_lease_current"), view)
    op_lease_total, _ = _sum_instants(
        payload, ("operating_lease_noncurrent", "operating_lease_current"), view)
    # `if parts:` was true when ANY SINGLE component resolved, so a filer whose long-term
    # debt tag is missing got a total_debt of just its short-term borrowings, a tiny net
    # debt, and 2/2 on bs_net_debt_ebitda. Oracle is the worked example: -0.96x reported
    # (implying net cash) against roughly $97.6B of real net debt.
    #
    # The combined tag is now preferred whenever it is MATERIALLY LARGER than the parts
    # we could assemble, because that is the signature of a component having gone
    # missing. Both figures are recorded either way.
    t_comb, f_comb = _instant_latest(payload, "debt_combined", view)
    combined = (f_comb.val + (lease_total or 0.0)) if f_comb else None
    parts_total = (sum(parts) + (lease_total or 0.0)) if parts else None

    if parts_total is not None and combined is not None and \
            combined > parts_total * (1.0 + rubric.DEBT_PARTS_TOLERANCE):
        total_debt = combined
        debt_prov = {"tag_used": t_comb, "derived": True,
                     "formula": "combined debt tag (components were incomplete)",
                     "parts_total": parts_total, "combined": combined,
                     "parts_resolved": len(parts)}
    elif parts_total is not None:
        total_debt = parts_total
        debt_prov = {"derived": True,
                     "formula": "long-term (noncurrent+current) + short-term + finance leases",
                     "tag_used": lease_prov.get("tag_used"),
                     "parts_resolved": len(parts), "combined": combined}
    else:
        total_debt = combined
        debt_prov = {"tag_used": t_comb, "derived": f_comb is not None}
    M.set("total_debt", total_debt, debt_prov)
    M.set("finance_leases", lease_total)
    # Operating leases are reported both ways: headline leverage is
    # ex-operating-lease (covenant convention), with the inclusive figure beside it.
    M.set("operating_leases", op_lease_total)
    M.set("total_debt_incl_op_leases",
          (total_debt + op_lease_total) if (total_debt is not None and op_lease_total is not None)
          else total_debt)

    net_debt = None
    if total_debt is not None:
        net_debt = total_debt - (cash_sti or 0.0)
    M.set("net_debt", net_debt, {"derived": True, "formula": "total_debt - cash_sti"})

    # ---------------------------------------------------------- ratios
    rev = M.raw("revenue_ttm")
    M.set("gross_margin", _safe_div(M.raw("gross_profit_ttm"), rev))
    M.set("operating_margin", _safe_div(M.raw("operating_income_ttm"), rev))
    M.set("net_margin", _safe_div(M.raw("net_income_ttm"), rev))
    M.set("fcf_margin", _safe_div(M.raw("fcf_ttm"), rev))
    M.set("rnd_pct_revenue", _safe_div(M.raw("rnd_ttm"), rev))
    M.set("sbc_pct_revenue", _safe_div(M.raw("sbc_ttm"), rev))
    M.set("capex_pct_revenue", _safe_div(M.raw("capex_ttm"), rev))
    M.set("fcf_conversion", _safe_div(M.raw("fcf_ttm"), M.raw("net_income_ttm")))

    tax_rate = _effective_tax_rate(M)
    M.set("effective_tax_rate", tax_rate[0], tax_rate[1])

    # ROIC = NOPAT / average invested capital
    equity, equity_prior = M.raw("equity"), _instant_at(payload, "equity", view, 4)[1]
    eq_prior_val = equity_prior.val if equity_prior else None
    ic_now = _invested_capital(total_debt, equity, cash_sti)
    ic_prior = _invested_capital(
        total_debt, eq_prior_val, cash_sti)   # debt/cash history not carried: documented approx
    ic_avg = _avg(ic_now, ic_prior)
    nopat = None
    if opinc is not None and tax_rate[0] is not None:
        nopat = opinc * (1.0 - tax_rate[0])
    M.set("nopat_ttm", nopat, {"derived": True,
                               "formula": "operating_income_ttm * (1 - effective_tax_rate)"})
    M.set("invested_capital", ic_avg,
          {"derived": True,
           "formula": "avg(total_debt + equity - cash_sti); equity averaged over 4 quarters"})
    M.set("roic", _safe_div(nopat, ic_avg), {"derived": True, "formula": "nopat / invested_capital"})
    M.set("roe", _safe_div(M.raw("net_income_ttm"), _avg(equity, eq_prior_val)),
          {"derived": True, "formula": "net_income_ttm / avg(equity)"})

    M.set("current_ratio", _safe_div(M.raw("assets_current"), M.raw("liabilities_current")))
    M.set("net_debt_ebitda", _safe_div(net_debt, M.raw("ebitda_ttm")))
    M.set("debt_ebitda_incl_leases",
          _safe_div(M.raw("total_debt_incl_op_leases"), M.raw("ebitda_ttm")))

    # interest coverage: an absent interest expense with net cash is genuinely
    # infinite coverage (full marks); absent WITH positive debt is NO_DATA.
    # Coverage is capped rather than stored as inf: JSON has no portable Infinity
    # and parquet/CSV round-trips of inf are a reliable source of downstream NaN.
    int_exp = M.raw("interest_expense_ttm")
    M.set("interest_coverage_uncapped", False)
    if int_exp is not None and abs(int_exp) > 0 and opinc is not None:
        cov = opinc / abs(int_exp)
        M.set("interest_coverage", min(cov, COVERAGE_CAP),
              {"derived": True, "formula": "operating_income_ttm / abs(interest_expense_ttm)",
               "capped": cov > COVERAGE_CAP})
        M.set("interest_coverage_uncapped", cov > COVERAGE_CAP)
    elif (int_exp is None or int_exp == 0) and net_debt is not None and net_debt < 0:
        M.set("interest_coverage", COVERAGE_CAP,
              {"derived": True,
               "formula": "no interest expense filed and net cash -> effectively uncovered debt-free",
               "capped": True})
        M.set("interest_coverage_uncapped", True)
    else:
        M.set("interest_coverage", None,
              {"derived": True, "reason": "interest expense absent with positive net debt"})

    # dilution: TTM average diluted share count vs the prior-year TTM average
    M.set("dilution_yoy", nz.yoy(M.raw("diluted_shares_ttm"), M.raw("diluted_shares_ttm_prior")),
          {"tag_used": tag_used.get("diluted_shares"),
           "formula": "TTM avg diluted shares vs prior-year TTM avg"})

    # ---------------------------------------------------------- growth
    for m, key in (("revenue", "revenue"), ("eps_diluted", "eps"), ("fcf", "fcf"),
                   ("operating_income", "operating_income"), ("net_income", "net_income")):
        latest = M.raw(f"{m}_ttm")
        M.set(f"{key}_yoy", nz.yoy(latest, M.raw(f"{m}_ttm_prior")))
        M.set(f"{key}_cagr_1y", nz.cagr(latest, M.raw(f"{m}_ttm_prior"), 1.0))
        M.set(f"{key}_cagr_3y", nz.cagr(latest, M.raw(f"{m}_ttm_3y_ago"), 3.0))
        M.set(f"{key}_cagr_5y", nz.cagr(latest, M.raw(f"{m}_ttm_5y_ago"), 5.0))

    # FY fallback for long-horizon CAGR when quarterly history is short
    _fy_fallback_cagr(M, payload, view, tag_used)

    # ---------------------------------------------------------- margin trend
    _margin_trend(M)

    # revenue acceleration: last 4 YoY growth rates, is the newest above the mean
    _revenue_acceleration(M)

    # Line-item applicability. "This filer has no gross-profit line" is a fact
    # about its income statement, not a gap in our data, so the scoring layer
    # renders the dependent sub-test NOT_APPLICABLE instead of NO_DATA.
    M.set("has_gross_profit_line",
          tags.has_any(payload, "gross_profit") or tags.has_any(payload, "cogs"))
    M.set("has_operating_income_line", tags.has_any(payload, "operating_income"))
    M.set("has_current_balance_sheet",
          tags.has_any(payload, "assets_current", tags.INSTANT_CHAINS))
    M.set("has_capex_line", tags.has_any(payload, "capex"))

    # Plausibility. These USED to be warnings only - "These never change a score" - and
    # nothing ever read them, so a gross margin of 340% scored normally and a company
    # with roic=10000 took full sector-relative marks. They now fail the metric.
    gm, om = M.raw("gross_margin"), M.raw("operating_margin")
    if gm is not None and om is not None and (gm - om) > 0.70:
        M.warnings.append(
            f"gross margin {gm:.1%} sits {gm - om:.0%} above operating margin - the filer's "
            f"tagged cost line may cover only part of its cost of revenue"
        )
    if M.raw("revenue_ttm") is not None and M.raw("revenue_ttm") <= 0:
        M.warnings.append("TTM revenue is zero or negative")
    _quality_check(M)

    M.set("data_through", _latest_period_end(M))
    M.set("tags_used", {k: v for k, v in tag_used.items() if v})
    M.set("quarters_available", {k: len(v) for k, v in M.series.items() if len(v)})
    if profile is not None:
        M.set("profile", profile.name)
    return M


def _as_date(v):
    """Accept either an ISO string or a date. Facts carry both shapes in practice."""
    if v is None:
        return None
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v))
    except (TypeError, ValueError):
        return None


def _series_end(series):
    """Latest period end in a series as a `date`, or None if empty."""
    if not series or not getattr(series, "facts", None):
        return None
    ends = [d for d in (_as_date(f.end) for f in series.facts) if d]
    return max(ends, default=None)


def _stale_ratio_check(M: MetricBundle) -> None:
    """Fail any margin whose numerator and denominator cover different periods.

    A TTM ratio is only meaningful when both sides span the same twelve months. Nothing
    enforced that, and the result is the single largest source of wrong margins measured
    on 2026-08-16:

      INTU  revenue runs to 2026-04-30, `cogs` STOPS AT 2020-07-31, so gross margin was
            2020's gross profit over 2026's revenue -> 30.1% against a true ~81.5%.
      ORCL  `cogs` stops at 2018-05-31 -> 96.3% against a true ~70%.

    Both sat inside 0-100% and so passed every range check, and both reported
    `warnings: []`. A retired or sparsely-filed cost tag is common; silently pairing it
    with current revenue is what made it dangerous.
    """
    rev_end = _series_end(M.series.get("revenue"))
    if not rev_end:
        return
    for metric, numerator in (("gross_margin", "gross_profit"),
                              ("operating_margin", "operating_income"),
                              ("net_margin", "net_income"),
                              ("fcf_margin", "fcf")):
        if M.raw(metric) is None or metric in M.quality_failures:
            continue
        num_end = _series_end(M.series.get(numerator))
        if not num_end:
            continue
        # No try/except here on purpose. `_series_end` already returns a date or None,
        # and the first cut of this wrapped the subtraction in `except (TypeError,
        # ValueError): continue` - which silently swallowed the fact that ends are dates
        # rather than strings, so the whole check ran and caught nothing. A guard that
        # cannot fail loudly is the bug it is supposed to catch.
        gap = (rev_end - num_end).days
        if gap <= rubric.RATIO_PERIOD_MAX_GAP_DAYS:
            continue
        reason = (f"{metric} pairs a {numerator} series ending {num_end.isoformat()} "
                  f"with revenue ending {rev_end.isoformat()} - {gap} days apart, so "
                  f"the ratio spans two different periods and is not a margin")
        M.quality_failures[metric] = reason
        M.warnings.append(reason)
        prov = dict(M.provenance.get(metric) or {})
        prov.update({"data_quality_fail": True, "rejected_value": M.raw(metric),
                     "numerator_series_end": num_end.isoformat(),
                     "revenue_series_end": rev_end.isoformat()})
        M.set(metric, None, prov)


def _cross_check_gross_profit(M: MetricBundle, tag_used: dict) -> None:
    """Compare GrossProfit-direct against revenue - cogs, and record disagreement.

    Deliberately does NOT pick a winner. Both derivations are legitimate readings of the
    filing and there is no general rule for which is right - the failure mode runs in
    both directions, cost over-captured for INTU/FICO/EXEL and under-captured for ORCL.
    Choosing one would be guessing with a confident face.

    Stores the comparison so `_quality_check` can fail `gross_margin` on it and the QA
    report can name the companies.
    """
    rev = M.series.get("revenue")
    gp = M.series.get("gross_profit")
    cogs = M.series.get("cogs")
    if not (rev and gp and cogs) or not (len(rev) and len(gp) and len(cogs)):
        return
    if str(tag_used.get("gross_profit", "")).startswith("derived:"):
        return          # already the subtraction; there is nothing independent to compare
    direct = nz.ttm(gp)[0]
    derived = nz.ttm(_sub_series(rev, cogs))[0]
    rev_ttm = nz.ttm(rev)[0]
    if None in (direct, derived, rev_ttm) or not rev_ttm:
        return
    gm_direct, gm_derived = direct / rev_ttm, derived / rev_ttm
    M.set("gross_margin_direct", gm_direct)
    M.set("gross_margin_from_cogs", gm_derived)
    M.set("gross_margin_disagreement", abs(gm_direct - gm_derived))


def _quality_check(M: MetricBundle) -> None:
    """Fail metrics whose value is not believable, and NULL them.

    Nulling matters as much as the status. A bad value left in `values` reaches the
    parquet, the workbook and - worst - `va.sector_percentiles`, which ranks a company
    against its sector WITHOUT any range filter of its own, so a company with roic=10000
    scored percentile 1.0 and took full marks. Removing the value at source fixes every
    downstream consumer at once; the original is kept in provenance so the defect can
    still be traced.

    Bounds live in `rubric.QUALITY_BOUNDS` and are deliberately wide: they catch broken
    derivations, never unusual businesses.
    """
    # The two independent gross-margin derivations disagreeing means the tag pairing is
    # wrong, whichever one is currently in `gross_margin`. This is the check that catches
    # INTU, ORCL, FICO and EXEL - every one of them inside 0-100% and so invisible to the
    # range bounds below.
    _stale_ratio_check(M)

    gap = M.raw("gross_margin_disagreement")
    if gap is not None and gap > rubric.GROSS_MARGIN_MAX_DISAGREEMENT:
        reason = (f"gross margin derivations disagree by {gap:.1%} "
                  f"(GrossProfit tag {M.raw('gross_margin_direct'):.1%} vs "
                  f"revenue-cogs {M.raw('gross_margin_from_cogs'):.1%}) - the cost line "
                  f"is partially tagged, so neither reading can be trusted")
        M.quality_failures["gross_margin"] = reason
        M.warnings.append(reason)
        prov = dict(M.provenance.get("gross_margin") or {})
        prov.update({"data_quality_fail": True,
                     "rejected_value": M.raw("gross_margin"),
                     "gross_margin_direct": M.raw("gross_margin_direct"),
                     "gross_margin_from_cogs": M.raw("gross_margin_from_cogs")})
        M.set("gross_margin", None, prov)

    for metric, (lo, hi) in rubric.QUALITY_BOUNDS.items():
        v = M.raw(metric)
        if v is None:
            continue
        try:
            bad = not (lo <= v <= hi)
        except TypeError:
            bad = True
        if not bad:
            continue
        reason = (f"{metric} {v!r} outside the believable range [{lo}, {hi}] - "
                  f"the XBRL tag pairing behind it is wrong, so it is not scored")
        M.quality_failures[metric] = reason
        M.warnings.append(reason)
        prov = dict(M.provenance.get(metric) or {})
        prov.update({"data_quality_fail": True, "rejected_value": v,
                     "bounds": [lo, hi]})
        M.set(metric, None, prov)


# ------------------------------------------------------------------ helpers
def _safe_div(a, b):
    if a is None or b in (None, 0):
        return None
    try:
        return a / b
    except (TypeError, ZeroDivisionError):
        return None


def _avg(a, b):
    vals = [v for v in (a, b) if v is not None]
    return sum(vals) / len(vals) if vals else None


def _invested_capital(debt, equity, cash_sti):
    """Invested capital, or None when it is too small to divide by.

    `_safe_div` rejects only an exact zero, so a buyback-heavy net-cash filer with a
    small book value produced an invested capital near zero and an ROIC of +/-1000%.
    DXCM measured -15,208% on 2026-08-16. A near-zero denominator does not mean
    spectacular returns on capital, it means the ratio is meaningless for that filer.

    The floor is expressed relative to the inputs rather than as an absolute dollar
    amount so it works for a $2B company and a $2T one alike.
    """
    if equity is None:
        return None
    ic = (debt or 0.0) + equity - (cash_sti or 0.0)
    scale = max(abs(equity), abs(debt or 0.0), abs(cash_sti or 0.0))
    if scale and abs(ic) < scale * rubric.INVESTED_CAPITAL_MIN_FRACTION:
        return None
    return ic


def _effective_tax_rate(M: MetricBundle) -> tuple[float | None, dict]:
    tax, pretax = M.raw("tax_expense_ttm"), M.raw("pretax_income_ttm")
    if tax is not None and pretax not in (None, 0) and pretax > 0:
        rate = tax / pretax
        clamped = min(max(rate, rubric.EFFECTIVE_TAX_FLOOR), rubric.EFFECTIVE_TAX_CEIL)
        return clamped, {"derived": True, "raw_rate": rate,
                         "clamped": clamped != rate,
                         "formula": "tax_expense_ttm / pretax_income_ttm"}
    return rubric.EFFECTIVE_TAX_DEFAULT, {"assumed": True,
                                          "reason": "tax or pretax income unavailable"}


def _add_series(a: nz.QuarterSeries, b: nz.QuarterSeries) -> nz.QuarterSeries:
    return _combine(a, b, lambda x, y: x + y, "sum")


def _sub_series(a: nz.QuarterSeries, b: nz.QuarterSeries) -> nz.QuarterSeries:
    return _combine(a, b, lambda x, y: x - y, "difference")


def _span_days(f) -> int | None:
    """Length of a fact's period in days, or None when its start is not recorded."""
    if not getattr(f, "start", None) or not getattr(f, "end", None):
        return None
    try:
        return (date.fromisoformat(f.end) - date.fromisoformat(f.start)).days
    except (TypeError, ValueError):
        return None


def _combine(a: nz.QuarterSeries, b: nz.QuarterSeries, op, label: str) -> nz.QuarterSeries:
    """Combine two quarterly series, matching on the PERIOD, not just the end date.

    This used to join on `end` alone. Two facts can share an end date and cover wildly
    different spans - a fiscal quarter and the full year both end on the same day - so
    `revenue - cogs` was capable of subtracting a YEAR of cost from a QUARTER of revenue
    or the reverse, while labelling the result `duration="Q"`.

    That is the mechanism behind the two worst measured gross margins: ORCL 96.3% against
    a true ~70% (a quarter of cost taken off a year of revenue) and INTU 30.1% against a
    true ~81.5% (the reverse). Both were inside 0-100% and so invisible to every range
    check, and both had `warnings: []`.

    Mismatched pairs are DROPPED rather than combined. A shorter honest series beats a
    long wrong one.
    """
    bmap = {f.end: f for f in b.facts}
    out = nz.QuarterSeries(notes=[f"{label} of two series"])
    dropped = 0
    for f in a.facts:
        g = bmap.get(f.end)
        if g is None:
            continue
        sa, sb = _span_days(f), _span_days(g)
        if sa is not None and sb is not None and abs(sa - sb) > PERIOD_MATCH_TOLERANCE_DAYS:
            dropped += 1
            continue
        out.facts.append(nz.Fact(
            end=f.end, val=op(f.val, g.val), start=f.start, duration="Q",
            accn=f.accn, filed=f.filed, form=f.form, fy=f.fy, fp=f.fp, frame=f.frame,
            derived=True, derivation=f"{label}:{f.derivation}|{g.derivation}",
            n_restatements=max(f.n_restatements, g.n_restatements),
        ))
    out.n_derived = len(out.facts)
    if dropped:
        out.notes.append(f"{dropped} period-mismatched pairs dropped")
    return out


def _fy_fallback_cagr(M: MetricBundle, payload: dict, view: str, tag_used: dict) -> None:
    """Where TTM history is too short, fall back to annual FY facts for 3Y/5Y CAGR."""
    for metric, key in (("revenue", "revenue"), ("net_income", "net_income")):
        if M.raw(f"{key}_cagr_5y") is not None:
            continue
        tag, rows = tags.resolve(payload, metric)
        if tag is None:
            continue
        fy = nz.annual_facts(rows, view=view)
        if len(fy) < 2:
            continue
        latest = fy[-1]
        for years in (5, 3):
            if M.raw(f"{key}_cagr_{years}y") is not None:
                continue
            idx = len(fy) - 1 - years
            if idx < 0:
                continue
            val = nz.cagr(latest.val, fy[idx].val, float(years))
            if val is not None:
                M.set(f"{key}_cagr_{years}y", val,
                      {"tag_used": tag, "derived": True,
                       "formula": f"FY-fact CAGR {fy[idx].end_iso} -> {latest.end_iso}",
                       "fallback": "annual_facts"})


def _margin_trend(M: MetricBundle) -> None:
    """OLS slope of quarterly operating margin, in bps/year. The FE key test."""
    rev, op = M.series.get("revenue"), M.series.get("operating_income")
    if not rev or not op or len(rev) < rubric.FE_MARGIN_QUARTERS \
            or len(op) < rubric.FE_MARGIN_QUARTERS:
        M.set("margin_trend_bps_yr", None)
        M.set("margin_trend_quarters", 0)
        return
    rmap = {f.end: f.val for f in rev.facts}
    pts: list[tuple] = []
    for f in op.facts[-rubric.FE_MARGIN_QUARTERS:]:
        r = rmap.get(f.end)
        if r and r > 0:
            pts.append((f.end, f.val / r))
    if len(pts) < 4:
        M.set("margin_trend_bps_yr", None)
        M.set("margin_trend_quarters", len(pts))
        return
    ys = [p[1] for p in pts]
    slope_per_quarter = nz.linreg_slope(ys)
    M.set("margin_trend_bps_yr",
          None if slope_per_quarter is None else slope_per_quarter * 4.0 * 10_000.0,
          {"derived": True,
           "formula": f"OLS slope of operating margin over {len(pts)} quarters, annualized to bps"})
    M.set("margin_trend_quarters", len(pts))
    M.set("margin_first_last",
          {"first": round(ys[0], 5), "last": round(ys[-1], 5),
           "from": pts[0][0].isoformat(), "to": pts[-1][0].isoformat()})


def _revenue_acceleration(M: MetricBundle) -> None:
    """Is revenue growth accelerating? Independent corroboration of the LLM's SG claim."""
    rev = M.series.get("revenue")
    if not rev or len(rev) < 8:
        M.set("revenue_accelerating", None)
        return
    facts = rev.facts
    yoys: list[float] = []
    for i in range(len(facts) - 4, len(facts)):
        prior = facts[i - 4]
        if prior.val and prior.val > 0:
            yoys.append((facts[i].val - prior.val) / prior.val)
    if len(yoys) < 3:
        M.set("revenue_accelerating", None)
        return
    M.set("revenue_yoy_last4", [round(y, 5) for y in yoys])
    M.set("revenue_accelerating", bool(yoys[-1] > sum(yoys[:-1]) / len(yoys[:-1])),
          {"derived": True, "formula": "latest quarterly YoY vs mean of the prior three"})


def _latest_period_end(M: MetricBundle) -> str | None:
    best = ""
    for s in M.series.values():
        if s and s.facts:
            e = s.facts[-1].end_iso
            if e > best:
                best = e
    return best or None
