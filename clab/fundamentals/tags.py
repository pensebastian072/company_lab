"""XBRL tag fallback chains - the metric dictionary.

`resolve()` walks a chain in order and returns the first tag with usable rows,
along with the tag it used, which is recorded in provenance. A scorecard
therefore says "revenue via RevenueFromContractWithCustomerExcludingAssessedTax"
rather than asserting a number from nowhere.

Chains were checked against real companyfacts blobs for AAPL, NVDA, JPM and XOM.
Two findings worth keeping in mind while reading this file:

  - JPM has no GrossProfit, OperatingIncomeLoss, AssetsCurrent,
    LiabilitiesCurrent, capex or R&D tag. XOM has no GrossProfit or
    OperatingIncomeLoss. Those absences are handled by profile.py marking the
    dependent sub-tests NOT_APPLICABLE - never by scoring them zero.
  - plain `ShortTermInvestments` was absent on all four issuers checked. Do not
    rely on it; the chain below uses MarketableSecuritiesCurrent first.
"""
from __future__ import annotations

from ..sources.edgar_facts import tag_rows

# ------------------------------------------------------------------ flow chains
CHAINS: dict[str, tuple[str, ...]] = {
    "revenue": (
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
        "RevenuesNetOfInterestExpense",
    ),
    "revenue_parts": ("SalesRevenueGoodsNet", "SalesRevenueServicesNet"),
    "cogs": (
        "CostOfGoodsAndServicesSold",
        "CostOfRevenue",
        "CostOfGoodsSold",
        "CostOfServices",
    ),
    "gross_profit": ("GrossProfit",),
    "operating_income": ("OperatingIncomeLoss",),
    "operating_expenses": ("OperatingExpenses", "CostsAndExpenses"),
    "net_income": (
        "NetIncomeLoss",
        "ProfitLoss",
        "NetIncomeLossAvailableToCommonStockholdersBasic",
    ),
    "eps_diluted": (
        "EarningsPerShareDiluted",
        "IncomeLossFromContinuingOperationsPerDilutedShare",
    ),
    "diluted_shares": (
        "WeightedAverageNumberOfDilutedSharesOutstanding",
        "WeightedAverageNumberOfSharesOutstandingBasic",
        "WeightedAverageNumberOfSharesOutstandingDiluted",
    ),
    "cfo": (
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
    ),
    "capex": (
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
        "PaymentsForCapitalImprovements",
    ),
    "rnd": ("ResearchAndDevelopmentExpense",),
    "dep_amort": (
        "DepreciationDepletionAndAmortization",
        "DepreciationAmortizationAndAccretionNet",
        "DepreciationAndAmortization",
    ),
    "dep_amort_parts": ("Depreciation", "AmortizationOfIntangibleAssets"),
    "sbc": ("ShareBasedCompensation", "AllocatedShareBasedCompensationExpense"),
    # InterestIncomeExpenseNet is a NET tag and often negative: sign flip needed.
    "interest_expense": (
        "InterestExpense",
        "InterestExpenseNonoperating",
        "InterestExpenseDebt",
        "InterestExpenseOperating",
    ),
    "interest_expense_net": ("InterestIncomeExpenseNet",),
    "tax_expense": ("IncomeTaxExpenseBenefit",),
    "pretax_income": (
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
    ),
    "buybacks": ("PaymentsForRepurchaseOfCommonStock",),
    "dividends": ("PaymentsOfDividendsCommonStock", "PaymentsOfDividends"),
    "ma_spend": ("PaymentsToAcquireBusinessesNetOfCashAcquired",),
    "impairment": ("GoodwillImpairmentLoss", "AssetImpairmentCharges"),
    # financial-sector revenue substitutes
    "interest_income_operating": ("InterestAndDividendIncomeOperating",),
    "noninterest_income": ("NoninterestIncome",),
    # REIT / lessor revenue. ASC 842 lease income is NOT ASC 606 contract revenue, so a
    # REIT's rent does not appear under any member of the `revenue` chain. Measured on
    # EQR 2026-08-25: `Revenues` and `RevenueFromContractWithCustomerIncludingAssessedTax`
    # BOTH stop at 2020-03-31, while `OperatingLeaseLeaseIncome` runs to 2026-06-30 - so
    # the whole sector's current revenue was invisible and EQR was scored on a six-year-old
    # number. Kept OUT of the `revenue` chain deliberately: for an ordinary filer lease
    # income is a small line (FITB files $85m of it against $14.9bn of revenue) and
    # merging it in could let a component fill a gap and pass as a total.
    "lease_income": ("OperatingLeaseLeaseIncome",
                     "OperatingLeasesIncomeStatementLeaseRevenue"),
}

# ------------------------------------------------------------------ instant chains
INSTANT_CHAINS: dict[str, tuple[str, ...]] = {
    "cash": ("CashAndCashEquivalentsAtCarryingValue",
             "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"),
    "short_term_investments": (
        "MarketableSecuritiesCurrent",
        "AvailableForSaleSecuritiesDebtSecuritiesCurrent",
        "OtherShortTermInvestments",
        "ShortTermInvestments",
    ),
    "assets": ("Assets",),
    "assets_current": ("AssetsCurrent",),
    "liabilities_current": ("LiabilitiesCurrent",),
    "equity": ("StockholdersEquity",
               "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"),
    "debt_long_noncurrent": ("LongTermDebtNoncurrent",),
    "debt_long_current": ("LongTermDebtCurrent",),
    "debt_short": ("ShortTermBorrowings", "OtherShortTermBorrowings",
                   "CommercialPaper"),
    "debt_combined": ("DebtLongtermAndShorttermCombinedAmount", "LongTermDebt",
                      "DebtInstrumentCarryingAmount"),
    "finance_lease_noncurrent": ("FinanceLeaseLiabilityNoncurrent",),
    "finance_lease_current": ("FinanceLeaseLiabilityCurrent",),
    "operating_lease_noncurrent": ("OperatingLeaseLiabilityNoncurrent",),
    "operating_lease_current": ("OperatingLeaseLiabilityCurrent",),
    "goodwill": ("Goodwill",),
    "tier1_ratio": ("TierOneRiskBasedCapitalToRiskWeightedAssets",),
    "maturity_1y": ("LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths",),
    "maturity_2y": ("LongTermDebtMaturitiesRepaymentsOfPrincipalInYearTwo",),
    "maturity_3y": ("LongTermDebtMaturitiesRepaymentsOfPrincipalInYearThree",),
    "maturity_4y": ("LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFour",),
    "maturity_5y": ("LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFive",),
}

DEI_CHAINS: dict[str, tuple[str, ...]] = {
    "shares_outstanding": ("EntityCommonStockSharesOutstanding",),
}


# A tag whose newest fact is older than this is treated as retired: the filer
# switched taxonomy mid-history and the newer tag must win. Measured need: NVDA
# stopped filing RevenueFromContractWithCustomerExcludingAssessedTax after
# FY2022 and moved to Revenues, so naive chain order produced a revenue series
# that ended in 2020 and a "TTM revenue" of $10.9B against a true ~$200B.
STALE_TAG_DAYS = 400


#: Metrics where a bigger number on the SAME period means "more consolidated", so a
#: dominating tag outranks the declared chain order. Revenue only, and deliberately so:
#: for revenue the semantics are guaranteed - every revenue tag in one filing is either
#: the consolidated total or a component of it, and a component cannot exceed its own
#: total. That is not true of `interest_expense` or `cogs`, where a larger number can
#: simply be a different (worse) measurement, so they are NOT listed here.
MAGNITUDE_PREFERRED = frozenset({"revenue"})

#: How much larger a fresh tag must be, on the periods the two actually share, before it
#: overrides declared chain order. 1.5x is far beyond a reclassification or a rounding
#: difference and far below the failures this catches: EQR's contract revenue is 0.00014x
#: its `Revenues`, and CDP's is 0.04x.
CONSOLIDATED_DOMINANCE = 1.5


def _overlap_medians(a: list[dict], b: list[dict]) -> tuple[float, float] | None:
    """Median |value| of two row sets over the (start, end) periods they SHARE.

    Compared only on shared periods, because two tags covering different years would
    otherwise be ranked on how much history they happen to carry rather than on how much
    of the business they measure.
    """
    ma = {(r.get("start"), r.get("end")): r.get("val") for r in a}
    mb = {(r.get("start"), r.get("end")): r.get("val") for r in b}
    keys = [k for k in ma.keys() & mb.keys()
            if isinstance(ma[k], (int, float)) and isinstance(mb[k], (int, float))]
    if not keys:
        return None
    va = sorted(abs(float(ma[k])) for k in keys)
    vb = sorted(abs(float(mb[k])) for k in keys)
    return va[len(va) // 2], vb[len(vb) // 2]


def _prefer_consolidated(found: list[tuple[str, list[dict]]],
                         best_end: str) -> list[tuple[str, list[dict]]]:
    """Move a dominating FRESH tag ahead of the chain order it would otherwise lose to.

    Measured 2026-08-25. The merge below lets the earliest chain position win every
    period it covers, which is right when chain order encodes semantic preference and
    wrong when the preferred tag is a fragment. EQR (Equity Residential) files
    `RevenueFromContractWithCustomerIncludingAssessedTax` of **$384,000** - management
    fees - alongside `Revenues` of **$2,699,485,000**, its actual rental revenue. Chain
    order preferred the fragment, so EQR's revenue_ttm read $216,000 against a real
    ~$2.9bn, its operating margin computed to 5,373 and every margin, growth rate and
    revenue multiple downstream was meaningless. 17% of Real Estate and 16% of
    Financials carried a revenue number this way.

    A REIT is the clean case because ASC 842 lease income is not ASC 606 contract
    revenue, so the tag the chain prefers is structurally a minor line for the whole
    sector. Stale tags are untouched - freshness is still decided first, and this only
    reorders among tags already allowed to supply the recent end.
    """
    fresh = [(t, r) for t, r in found if _within_days(_newest_end(r), best_end,
                                                     STALE_TAG_DAYS)]
    if len(fresh) < 2:
        return found
    lead_tag, lead_rows = fresh[0]
    best = None
    for tag, rows in fresh[1:]:
        med = _overlap_medians(rows, lead_rows)
        if med is None:
            continue
        cand, lead = med
        if lead > 0 and cand / lead >= CONSOLIDATED_DOMINANCE:
            if best is None or cand > best[1]:
                best = ((tag, rows), cand)
    if best is None:
        return found
    winner = best[0]
    return [winner] + [x for x in found if x[0] != winner[0]]


def _newest_end(rows: list[dict]) -> str:
    best = ""
    for r in rows:
        e = r.get("end") or ""
        if e > best:
            best = e
    return best


def resolve(
    payload: dict,
    metric: str,
    *,
    chains: dict[str, tuple[str, ...]] | None = None,
    taxonomy: str = "us-gaap",
    min_rows: int = 1,
    merge: bool = True,
) -> tuple[str | None, list[dict]]:
    """Resolve a metric to fact rows across its whole fallback chain.

    Filers switch tags mid-history, so a single tag routinely gives a truncated
    series. This merges every tag in the chain into one row set:

      - a tag is only allowed to supply the RECENT end of the series if its own
        newest fact is within STALE_TAG_DAYS of the chain's newest fact;
      - on a (start, end) collision the earlier chain position wins, because
        chain order encodes semantic preference;
      - older retired tags still contribute the history the current tag lacks.

    Returns (tag_label, rows). tag_label names every tag that contributed, so
    provenance shows "Revenues + RevenueFromContractWithCustomerExcludingAssessedTax".
    (None, []) means the metric is genuinely absent for this filer, which callers
    must render as NO_DATA - never as 0.
    """
    table = chains if chains is not None else CHAINS
    found: list[tuple[str, list[dict]]] = []
    for tag in table.get(metric, ()):
        rows = tag_rows(payload, tag, taxonomy=taxonomy)
        if len(rows) >= min_rows:
            found.append((tag, rows))
    if not found:
        return None, []
    if not merge or len(found) == 1:
        # single candidate, or merging disabled: still prefer a non-retired tag
        best_end = max(_newest_end(r) for _t, r in found)
        for tag, rows in found:
            if _within_days(_newest_end(rows), best_end, STALE_TAG_DAYS):
                return tag, rows
        return found[0]

    best_end = max(_newest_end(rows) for _t, rows in found)
    if metric in MAGNITUDE_PREFERRED:
        found = _prefer_consolidated(found, best_end)
    merged: dict[tuple, dict] = {}
    used: list[str] = []
    for tag, rows in found:
        fresh = _within_days(_newest_end(rows), best_end, STALE_TAG_DAYS)
        contributed = False
        for r in rows:
            key = (r.get("start"), r.get("end"))
            if key in merged:
                continue
            if not fresh and _within_days(r.get("end") or "", best_end, STALE_TAG_DAYS):
                # a retired tag must not supply the recent end of the series
                continue
            merged[key] = r
            contributed = True
        if contributed:
            used.append(tag)
    if not merged:
        return found[0]
    return " + ".join(used), list(merged.values())


def _within_days(end: str, ref: str, days: int) -> bool:
    """True when `end` is no more than `days` older than `ref` (ISO date strings)."""
    if not end or not ref:
        return False
    try:
        from datetime import date

        e = date.fromisoformat(end[:10])
        r = date.fromisoformat(ref[:10])
    except ValueError:
        return False
    return (r - e).days <= days


def resolve_instant(payload: dict, metric: str, **kw) -> tuple[str | None, list[dict]]:
    return resolve(payload, metric, chains=INSTANT_CHAINS, **kw)


def resolve_dei(payload: dict, metric: str, **kw) -> tuple[str | None, list[dict]]:
    return resolve(payload, metric, chains=DEI_CHAINS, taxonomy="dei", **kw)


def available_tags(payload: dict, taxonomy: str = "us-gaap") -> set[str]:
    return set((payload or {}).get("facts", {}).get(taxonomy, {}).keys())


def has_any(payload: dict, metric: str, chains: dict | None = None) -> bool:
    tag, rows = resolve(payload, metric, chains=chains)
    return tag is not None and bool(rows)


def has_line_item(payload: dict, metric: str) -> bool:
    """Does this filer's income statement contain the line at all?

    The distinction matters for honesty. XOM files no GrossProfit and no
    OperatingIncomeLoss; JPM files neither, plus no AssetsCurrent. That is a
    reporting-format fact about the filer, not a data gap on our side, so the
    dependent sub-test should read NOT_APPLICABLE rather than NO_DATA - the
    latter would drag an otherwise well-covered company under the band gate for
    something it will never report.
    """
    return has_any(payload, metric) or (
        metric in INSTANT_CHAINS and has_any(payload, metric, INSTANT_CHAINS)
    )
