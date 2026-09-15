"""Fill the missing sector for removed constituents, from the SEC SIC code.

Why this exists. The GICS sector on the panel comes from the Wikipedia CURRENT-members
table, so the 161 companies the survivorship fix added have no sector at all - 15.4% of
rows. Left alone they form one pseudo-sector that mixes utilities with software, and F1 is
a SECTOR fix, so its headline statistic would have been measured against a fake sector
variable. That is a wasted study, not a small imprecision.

The SIC code IS available for every filer, in the EDGAR submissions blob already cached on
disk from the crawl, so this costs no requests.

**SIC to GICS is approximate and this module does not pretend otherwise.** A filer picks
its own SIC and never revises it, the ranges below are judgement calls at the edges, and
some SIC codes genuinely straddle two GICS sectors (7372 prepackaged software vs 7379
computer services; 3826 lab instruments sits between Health Care and IT). So E05 reports
F1 three ways - GICS only, SIC-filled, and SIC for everyone - and a verdict that depends on
which one is used is reported as exactly that.

Sector names match the GICS names already on the panel so the two can be mixed in one
column: Communication Services, Consumer Discretionary, Consumer Staples, Energy,
Financials, Health Care, Industrials, Information Technology, Materials, Real Estate,
Utilities.
"""
from __future__ import annotations

import bisect

import pandas as pd

#: (upper_bound_inclusive, sector). Ordered; the first range whose bound is >= the code
#: and whose lower bound is <= it wins. Written as explicit (lo, hi, sector) triples
#: because the boundaries are irregular and a range table read as contiguous would be
#: wrong in a dozen places.
SIC_RANGES: tuple[tuple[int, int, str], ...] = (
    (100, 999, "Consumer Staples"),          # agriculture
    (1000, 1099, "Materials"),               # metal mining
    (1200, 1299, "Energy"),                  # coal
    (1300, 1399, "Energy"),                  # oil and gas extraction
    (1400, 1499, "Materials"),               # nonmetallic minerals
    (1500, 1799, "Industrials"),             # construction
    (2000, 2141, "Consumer Staples"),        # food, beverages, tobacco
    (2200, 2399, "Consumer Discretionary"),  # textiles, apparel
    (2400, 2499, "Industrials"),             # lumber and wood
    (2500, 2599, "Consumer Discretionary"),  # furniture
    (2600, 2699, "Materials"),               # paper
    (2700, 2799, "Communication Services"),  # printing and publishing
    (2800, 2829, "Materials"),               # industrial chemicals
    (2830, 2836, "Health Care"),             # drugs, biologicals
    (2840, 2899, "Materials"),               # soaps, paints, chemicals
    (2900, 2999, "Energy"),                  # petroleum refining
    (3000, 3099, "Materials"),               # rubber and plastics
    (3100, 3199, "Consumer Discretionary"),  # leather, footwear
    (3200, 3299, "Materials"),               # stone, clay, glass
    (3300, 3399, "Materials"),               # primary metals
    (3400, 3499, "Industrials"),             # fabricated metal
    (3500, 3569, "Industrials"),             # industrial machinery
    (3570, 3579, "Information Technology"),  # computer and office equipment
    (3580, 3599, "Industrials"),             # service machinery
    (3600, 3629, "Industrials"),             # electrical equipment
    (3630, 3639, "Consumer Discretionary"),  # household appliances
    (3640, 3652, "Consumer Discretionary"),  # lighting, audio/video
    (3660, 3669, "Information Technology"),  # communications equipment
    (3670, 3679, "Information Technology"),  # semiconductors, components
    (3680, 3689, "Information Technology"),  # computers
    (3690, 3699, "Industrials"),             # misc electrical
    (3700, 3716, "Consumer Discretionary"),  # motor vehicles
    (3720, 3729, "Industrials"),             # aircraft and parts
    (3730, 3743, "Industrials"),             # ships, rail equipment
    (3751, 3751, "Consumer Discretionary"),  # motorcycles, bicycles
    (3760, 3769, "Industrials"),             # guided missiles
    (3800, 3825, "Information Technology"),  # measuring instruments
    (3826, 3829, "Health Care"),             # lab analytical instruments
    (3841, 3851, "Health Care"),             # medical devices, ophthalmic
    (3860, 3869, "Information Technology"),  # photographic equipment
    (3870, 3873, "Consumer Discretionary"),  # watches, clocks
    (3900, 3999, "Consumer Discretionary"),  # misc manufacturing
    (4000, 4799, "Industrials"),             # transportation
    (4800, 4813, "Communication Services"),  # telephone
    (4820, 4899, "Communication Services"),  # broadcasting, cable
    (4900, 4999, "Utilities"),               # electric, gas, water, sanitary
    (5000, 5149, "Industrials"),             # durable + nondurable wholesale
    (5150, 5199, "Consumer Staples"),        # farm product, grocery wholesale
    (5200, 5399, "Consumer Discretionary"),  # building, general merchandise
    (5400, 5499, "Consumer Staples"),        # food stores
    (5500, 5599, "Consumer Discretionary"),  # auto dealers
    (5600, 5799, "Consumer Discretionary"),  # apparel, furniture, eating
    (5812, 5813, "Consumer Discretionary"),  # eating and drinking places
    (5900, 5911, "Consumer Discretionary"),  # misc retail
    (5912, 5912, "Consumer Staples"),        # drug stores
    (5913, 5999, "Consumer Discretionary"),  # misc retail
    (6000, 6499, "Financials"),              # banks, credit, insurance
    (6500, 6599, "Real Estate"),             # real estate
    (6700, 6725, "Financials"),              # holding, investment offices
    (6726, 6726, "Financials"),              # investment offices
    (6770, 6795, "Financials"),              # blank checks, mineral royalties
    (6798, 6798, "Real Estate"),             # REITs
    (6799, 6799, "Financials"),              # investors
    (7000, 7099, "Consumer Discretionary"),  # hotels, lodging
    (7200, 7299, "Consumer Discretionary"),  # personal services
    (7310, 7319, "Communication Services"),  # advertising
    (7320, 7369, "Industrials"),             # business services
    (7370, 7379, "Information Technology"),  # software, data processing
    (7380, 7389, "Industrials"),             # misc business services
    (7500, 7699, "Consumer Discretionary"),  # auto and misc repair
    (7800, 7841, "Communication Services"),  # motion pictures
    (7900, 7999, "Communication Services"),  # amusement and recreation
    (8000, 8099, "Health Care"),             # health services
    (8111, 8111, "Industrials"),             # legal services
    (8200, 8299, "Consumer Discretionary"),  # educational services
    (8300, 8399, "Health Care"),             # social services
    (8600, 8699, "Industrials"),             # membership organisations
    (8711, 8713, "Industrials"),             # engineering, architectural
    (8721, 8721, "Industrials"),             # accounting
    (8731, 8733, "Health Care"),             # commercial and biological research
    (8734, 8734, "Health Care"),             # testing laboratories
    (8741, 8748, "Industrials"),             # management consulting
    (8880, 8888, "Financials"),              # foreign filers, conglomerate
)

_LOS = [lo for lo, _hi, _s in SIC_RANGES]

UNKNOWN = "Unclassified"

#: SIC description -> the GICS sub-industry it is the same thing as.
#:
#: Companies whose index page carries no GICS sub-industry fall back to the SEC's SIC
#: description. Left raw, that SPLITS real peer groups: the workbook showed
#: "Semiconductors" (26 companies) beside "Semiconductors & Related Devices" (9), and
#: "Application Software" (33) beside "Services-Prepackaged Software" (9). Two half
#: groups are worse than one whole one both for reading the sheet and for the
#: peer-median valuation sub-tests, which need a minimum peer count.
#:
#: Only unambiguous equivalences are listed. Anything genuinely without a GICS
#: counterpart keeps its SIC description - a truthful odd label beats a wrong merge.
#: Keys are lowercased and whitespace-collapsed before lookup.
SIC_DESC_TO_GICS_SUB = {
    "services-prepackaged software": "Application Software",
    "services-computer programming, data processing, etc.": "IT Consulting & Other Services",
    "services-computer integrated systems design": "IT Consulting & Other Services",
    "semiconductors & related devices": "Semiconductors",
    "printed circuit boards": "Electronic Components",
    "electronic components, nec": "Electronic Components",
    "pharmaceutical preparations": "Pharmaceuticals",
    "biological products, (no diagnostic substances)": "Biotechnology",
    "in vitro & in vivo diagnostic substances": "Life Sciences Tools & Services",
    "laboratory analytical instruments": "Life Sciences Tools & Services",
    "surgical & medical instruments & apparatus": "Health Care Equipment",
    "electromedical & electrotherapeutic apparatus": "Health Care Equipment",
    "orthopedic, prosthetic & surgical appliances & supplies": "Health Care Supplies",
    "national commercial banks": "Diversified Banks",
    "state commercial banks": "Regional Banks",
    "savings institution, federally chartered": "Regional Banks",
    "security brokers, dealers & flotation companies": "Investment Banking & Brokerage",
    "investment advice": "Asset Management & Custody Banks",
    "life insurance": "Life & Health Insurance",
    "fire, marine & casualty insurance": "Property & Casualty Insurance",
    "accident & health insurance": "Life & Health Insurance",
    "real estate investment trusts": "Diversified REITs",
    "crude petroleum & natural gas": "Oil & Gas Exploration & Production",
    "natural gas transmission": "Oil & Gas Storage & Transportation",
    "petroleum refining": "Oil & Gas Refining & Marketing",
    "retail-auto dealers & gasoline stations": "Automotive Retail",
    "retail-eating places": "Restaurants",
    "retail-eating & drinking places": "Restaurants",
    "electric services": "Electric Utilities",
    "air transportation, scheduled": "Passenger Airlines",
    "trucking (no local)": "Cargo Ground Transportation",
    "pumps & pumping equipment": "Industrial Machinery & Supplies & Components",
    "ball & roller bearings": "Industrial Machinery & Supplies & Components",
    "metalworkg machinery & equipment": "Industrial Machinery & Supplies & Components",
    "misc industrial & commercial machinery & equipment":
        "Industrial Machinery & Supplies & Components",
    "general industrial machinery & equipment":
        "Industrial Machinery & Supplies & Components",
    "fabricated structural metal products": "Building Products",
    "miscellaneous fabricated metal products": "Building Products",
    "industrial instruments for measurement, display, and control":
        "Electronic Equipment & Instruments",
    "services-to dwellings & other buildings": "Environmental & Facilities Services",
    "services-business services, nec": "Diversified Support Services",
    "hotels & motels": "Hotels, Resorts & Cruise Lines",
    "gold mining": "Gold",
    "wholesale-drugs, proprietaries & druggists' sundries":
        "Health Care Distributors",
}


def normalize_sub_industry(label: str | None) -> str:
    """Map a SIC description onto its GICS sub-industry where one clearly exists.

    A GICS label passes through untouched; an unmapped SIC description is returned as
    given, because a truthful odd label beats a confident wrong merge.
    """
    if not label:
        return ""
    key = " ".join(str(label).split()).strip().lower()
    return SIC_DESC_TO_GICS_SUB.get(key, str(label).strip())


def sector_from_sic(sic: str | int | None) -> str | None:
    """GICS-style sector for a SIC code, or None when the code is absent or unmapped."""
    if sic is None or (isinstance(sic, float) and pd.isna(sic)):
        return None
    try:
        code = int(str(sic).strip().lstrip("0") or 0)
    except (TypeError, ValueError):
        return None
    if code <= 0:
        return None
    i = bisect.bisect_right(_LOS, code) - 1
    if i < 0:
        return None
    lo, hi, sector = SIC_RANGES[i]
    return sector if lo <= code <= hi else None


def sic_map(ciks: dict[str, str]) -> dict[str, str]:
    """{ticker: sic} read from the CACHED submissions blobs. Costs no requests.

    `EdgarSubmissions.fetch()` is cache-first and never raises, so a cold entry degrades
    to a missing SIC rather than failing the study.
    """
    from ..sources.edgar_facts import EdgarSubmissions, sic_from_submissions

    out: dict[str, str] = {}
    for ticker, cik in ciks.items():
        if not cik:
            continue
        res = EdgarSubmissions(str(cik)).fetch()
        sic, _desc = sic_from_submissions(res.payload or {})
        if sic:
            out[ticker] = str(sic)
    return out


def fill(p: pd.DataFrame) -> pd.DataFrame:
    """Add `sector_filled` (GICS, SIC-filled) and `sector_sic` (SIC for everyone).

    Both are added rather than overwriting `sector`, so every statistic can be reported
    against each definition and the reader can see which one a verdict depends on.
    """
    p = p.copy()
    ciks = (p.dropna(subset=["cik"]).drop_duplicates("ticker")
             .set_index("ticker")["cik"].astype(str).to_dict())
    sics = sic_map(ciks)
    p["sic"] = p["ticker"].map(sics)
    p["sector_sic"] = p["sic"].map(sector_from_sic).fillna(UNKNOWN)

    gics = p["sector"].fillna("").astype(str)
    p["sector_filled"] = gics.where(gics != "", p["sector_sic"])
    p["sector_basis"] = pd.Series("gics", index=p.index).where(gics != "", "sic")
    return p


def report(p: pd.DataFrame) -> dict:
    """Coverage numbers to state alongside any sector-conditioned result."""
    gics = p["sector"].fillna("").astype(str)
    filled = p["sector_filled"]
    return {
        "rows": int(len(p)),
        "symbols": int(p.ticker.nunique()),
        "rows_without_gics_sector": int((gics == "").sum()),
        "share_rows_without_gics_sector": float((gics == "").mean()),
        "symbols_without_gics_sector": int(p.loc[gics == "", "ticker"].nunique()),
        "sic_resolved_share_of_those": (
            float((filled[gics == ""] != UNKNOWN).mean()) if (gics == "").any() else None),
        "rows_still_unclassified": int((filled == UNKNOWN).sum()),
        "symbols_still_unclassified": int(
            p.loc[filled == UNKNOWN, "ticker"].nunique()),
        "sector_sic_distribution": {k: int(v) for k, v in
                                    p["sector_sic"].value_counts().items()},
        "disagreement_where_both_known": _disagreement(p),
    }


def _disagreement(p: pd.DataFrame) -> dict:
    """How often SIC and GICS disagree where BOTH exist.

    This is the honest measure of how much the SIC fill can be trusted for the 161
    companies where GICS is the one that is missing.
    """
    d = p[(p["sector"].fillna("") != "") & (p["sector_sic"] != UNKNOWN)]
    d = d.drop_duplicates("ticker")
    if d.empty:
        return {"n_symbols": 0}
    agree = (d["sector"] == d["sector_sic"])
    worst = (d.loc[~agree].groupby(["sector", "sector_sic"]).size()
             .sort_values(ascending=False).head(8))
    return {"n_symbols": int(len(d)),
            "agreement_rate": float(agree.mean()),
            "top_mismatches": {f"{g} -> {s}": int(n)
                               for (g, s), n in worst.items()}}
