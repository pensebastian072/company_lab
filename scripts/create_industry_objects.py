"""Create industry-object skeletons for one GICS sector, minimally and honestly.

Started at E63 as five Consumer Discretionary objects; takes `--sector` since 2026-09-12 so
the remaining empty sectors do not each acquire a near-copy of this file. The sector name is
the GICS string as the book spells it.

A skeleton carries only what is FACTUAL without research: its id, sector, version, status,
the member list from the book, and the refresh class. Every ordinal starts UNKNOWN and is
filled only by a verified claim through scripts/e79b_merge.py. Free-text fields are left
ABSENT rather than filled with process prose - E79's objects carried boilerplate like "the
cited evidence is tested for capital, certification, installed-base..." in moat_mechanism,
which says nothing about the industry and is worse than an empty field.
"""
import collections
import io
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, r"C:\Users\<your-user>\company_lab")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd

from clab.external import research_ingest as RI
from clab.external import taxonomy as T

ROOT = Path(r"D:\company_lab_data\external\research\industries")
VERSION = "2026-09-12"
NEXT_REFRESH = "2026-12-12"

UNITS = ["restaurants", "automotive_retail", "apparel_retail", "home_furnishings",
         "home_improvement_retail",
         # batch 2, 2026-09-12
         "hotels_resorts_cruise_lines", "automotive_parts_equipment", "homebuilding",
         "apparel_accessories_luxury_goods", "casinos_gaming", "leisure_products",
         "education_services", "specialty_stores",
         # Consumer Staples, 2026-09-12 - the sector had zero objects
         "packaged_foods_meats", "household_products",
         "soft_drinks_non_alcoholic_beverages", "food_retail",
         "consumer_staples_merchandise_retail", "personal_care_products",
         "food_distributors", "agricultural_products_services", "tobacco",
         "distillers_vintners", "brewers",
         # Materials, 2026-09-12 - the sector had one object of sixteen
         "specialty_chemicals", "steel", "paper_plastic_packaging_products_materials",
         "construction_materials", "metal_glass_plastic_containers",
         "fertilizers_agricultural_chemicals", "diversified_chemicals", "gold",
         "aluminum", "commodity_chemicals", "industrial_gases",
         "diversified_metals_mining", "silver", "copper", "paper_products",
         # Real Estate, 2026-09-12 - two objects of sixteen
         "retail_reits", "health_care_reits", "office_reits", "hotel_resort_reits",
         "industrial_reits", "multi_family_residential_reits", "other_specialized_reits",
         "real_estate_services", "diversified_reits", "single_family_residential_reits",
         "telecom_tower_reits", "self_storage_reits", "timber_reits",
         "real_estate_development",
         # Consumer Discretionary tail, 2026-09-12 - the last 14 units with no object
         "specialized_consumer_services", "other_specialty_retail", "broadline_retail",
         "leisure_facilities", "footwear", "distributors", "automobile_manufacturers",
         "computer_electronics_retail", "household_appliances", "homefurnishing_retail",
         "consumer_electronics", "tires_rubber", "motorcycle_manufacturers",
         "housewares_specialties"]

#: Only where the metric is the one the industry itself reports and an analyst tracks.
#: Absent for a unit where I have not read that evidence yet.
KEY_METRICS = {
    "restaurants": ["same-store sales", "traffic versus check", "unit count and net openings",
                    "franchised versus company-operated mix", "restaurant-level margin",
                    "average unit volume"],
    "automotive_retail": ["new and used unit sales", "gross profit per unit retailed",
                          "days supply of inventory", "finance and insurance gross per unit",
                          "parts and service absorption rate"],
    "apparel_retail": ["comparable store sales", "sales per square foot", "inventory turns",
                       "markdown rate", "digital penetration", "store count"],
    "home_furnishings": ["written versus delivered orders", "average ticket",
                         "gross margin", "delivery and warehouse cost per order"],
    "home_improvement_retail": ["comparable sales", "average ticket versus transactions",
                                "professional versus do-it-yourself mix",
                                "sales per square foot"],
    "hotels_resorts_cruise_lines": ["RevPAR and occupancy", "net yield per passenger cruise day",
                                    "occupancy versus rate", "rooms or berths added",
                                    "forward bookings and deposits", "management and franchise fee mix"],
    "automotive_parts_equipment": ["content per vehicle", "light-vehicle production volumes",
                                   "book-to-bill on new platform awards", "aftermarket versus OE mix",
                                   "vehicle age and miles driven"],
    "homebuilding": ["net new orders", "cancellation rate", "backlog and community count",
                     "gross margin per home", "spec versus build-to-order mix",
                     "lots owned and controlled"],
    "apparel_accessories_luxury_goods": ["brand comparable sales", "full-price sell-through",
                                         "markdown rate", "wholesale versus direct mix",
                                         "inventory turns"],
    "casinos_gaming": ["gross gaming revenue by state", "win per unit per day", "hold percentage",
                       "online versus land-based mix", "EBITDAR margin"],
    "leisure_products": ["retail unit registrations", "dealer inventory weeks on hand",
                         "wholesale versus retail sell-through", "average selling price"],
    "education_services": ["total and new enrolment", "persistence and completion rates",
                           "revenue per student", "regulatory cohort default rate"],
    "specialty_stores": ["comparable sales", "sales per square foot", "store count and net openings",
                         "attachment and services mix"],
    # ---------------------------------------------------------------- Consumer Staples
    # Volume and price are listed SEPARATELY for every unit in this sector on purpose:
    # staples grow their dollars through price far more often than through units, and a
    # single "sales growth" metric hides exactly the distinction that matters here.
    "packaged_foods_meats": ["organic sales growth split into price and volume",
                             "volume or tonnage shipped", "gross margin versus input costs",
                             "private-label share of category", "trade spend as a percent of sales"],
    "household_products": ["organic sales split into price and volume",
                           "category market share by measured channel",
                           "gross margin versus commodity basket", "private-label share"],
    "soft_drinks_non_alcoholic_beverages": ["unit-case volume", "price/mix per case",
                                            "concentrate versus finished-goods mix",
                                            "away-from-home versus at-home channel mix"],
    "food_retail": ["identical or comparable store sales excluding fuel",
                    "transaction count versus basket size", "digital and delivery penetration",
                    "gross margin rate", "square footage growth"],
    "consumer_staples_merchandise_retail": ["comparable sales and traffic",
                                            "membership or renewal rate where applicable",
                                            "consumables versus discretionary mix",
                                            "sales per square foot"],
    "personal_care_products": ["organic sales split into price and volume",
                               "category share in measured channels", "gross margin",
                               "advertising as a percent of sales"],
    "food_distributors": ["case volume growth", "gross profit per case",
                          "independent versus chain customer mix", "food-cost inflation pass-through"],
    "agricultural_products_services": ["volumes processed or crushed", "crush or processing margin",
                                       "capacity utilisation", "inventory and basis position"],
    "tobacco": ["industry cigarette volume decline rate", "net price realisation per thousand",
                "retail share of market", "smoke-free or reduced-risk volume and share"],
    "distillers_vintners": ["depletions and shipments", "price/mix per case",
                            "premium versus value mix", "inventory in the three-tier channel"],
    "brewers": ["shipment and depletion volume", "revenue per hectolitre",
                "share of total alcohol servings", "on-premise versus off-premise mix"],
    # ----------------------------------------------------------------------- Materials
    # Every unit here has a PHYSICAL output measure and a spread, and both are listed,
    # because a commodity producer's revenue moves with price while its business moves
    # with tons. Conflating the two is how an E&P's revenue tripling gets read as growth
    # (the lesson already written into revenue_share.py).
    "specialty_chemicals": ["volume versus price/mix in organic growth",
                            "capacity utilisation", "raw-material spread per pound",
                            "industrial production index for chemicals",
                            "destocking versus end-demand"],
    "steel": ["raw steel production and capability utilisation", "shipments in tons",
              "metal spread (selling price less scrap or iron ore)",
              "imports as a share of apparent consumption", "order backlog and lead times"],
    "paper_plastic_packaging_products_materials": [
        "tons or units shipped", "operating rate", "price per ton realised",
        "resin or containerboard input spread", "e-commerce versus industrial end-market mix"],
    "construction_materials": ["volumes shipped in tons", "price per ton",
                               "cement and aggregates capacity utilisation",
                               "public versus private construction mix",
                               "freight distance and cost per ton"],
    "metal_glass_plastic_containers": ["units shipped", "contract pass-through lag on metal",
                                       "capacity utilisation", "beverage versus food end-market mix"],
    "fertilizers_agricultural_chemicals": ["nutrient tons shipped", "realised price per ton",
                                           "gas or ammonia input spread", "planted acreage",
                                           "channel inventory"],
    "diversified_chemicals": ["volume versus price in organic growth", "operating rate",
                              "spread over the feedstock basket"],
    "commodity_chemicals": ["volume shipped", "ethylene or chlor-alkali spread",
                            "operating rate", "export share"],
    "industrial_gases": ["volumes by molecule", "on-site versus merchant versus packaged mix",
                         "project backlog", "pricing actions versus power cost pass-through"],
    "gold": ["gold produced in ounces", "all-in sustaining cost per ounce",
             "reserve grade and mine life", "realised price versus spot"],
    "silver": ["silver produced in ounces", "all-in sustaining cost per ounce",
               "by-product credits", "reserve grade and mine life"],
    "copper": ["copper produced in pounds", "cash cost per pound net of by-products",
               "mill throughput and head grade", "realised price versus LME"],
    "aluminum": ["primary aluminium produced in tonnes", "Midwest premium plus LME realised",
                 "smelter operating rate", "power cost per tonne", "alumina integration"],
    "diversified_metals_mining": ["production by metal", "cost per unit by metal",
                                  "reserve life", "customer qualification cycle"],
    "paper_products": ["tons shipped", "operating rate", "price per ton",
                       "pulp integration and fibre cost"],
    # --------------------------------------------------------------------- Real Estate
    # Occupancy and a releasing spread lead every list here, because those are the two
    # PHYSICAL facts about a property portfolio; FFO per share is an accounting output of
    # them plus leverage plus share count, and reading it first is how a levered roll-up
    # gets mistaken for an operator.
    "retail_reits": ["same-property NOI growth", "occupancy and leased-versus-occupied spread",
                     "releasing spreads on new and renewal leases",
                     "tenant sales per square foot and occupancy cost ratio",
                     "bad debt and tenant bankruptcies"],
    "health_care_reits": ["same-store NOI by segment", "senior-housing occupancy and RevPOR",
                          "operator rent coverage (EBITDARM)", "triple-net versus SHOP mix",
                          "skilled-nursing reimbursement exposure"],
    "office_reits": ["same-property NOI growth", "occupancy and leased percentage",
                     "net effective rent after concessions and tenant improvements",
                     "lease expiry schedule and mark-to-market", "capex per square foot"],
    "hotel_resort_reits": ["RevPAR and its occupancy-versus-rate split", "hotel EBITDA margin",
                           "group versus transient mix", "renovation displacement"],
    "industrial_reits": ["same-store NOI growth", "occupancy", "cash releasing spreads",
                         "development pipeline and yield on cost",
                         "net absorption versus completions"],
    "multi_family_residential_reits": ["same-store revenue and NOI growth",
                                       "blended lease-rate growth, new versus renewal",
                                       "physical occupancy and resident turnover",
                                       "bad debt", "supply deliveries in the submarket"],
    "single_family_residential_reits": ["same-home NOI growth", "blended rent growth",
                                        "turnover and days to re-resident", "occupancy",
                                        "acquisition versus disposition pace"],
    "self_storage_reits": ["same-store revenue growth", "occupancy and street versus in-place rate",
                           "existing-customer rate increases", "new supply in the trade area"],
    "telecom_tower_reits": ["organic tenant billings growth", "colocations and amendments",
                            "churn", "tenants per tower", "escalator and ground-lease cost"],
    "timber_reits": ["harvest volume in tons", "price realisations by log grade",
                     "timberland acres owned", "wood-products segment spread"],
    "other_specialized_reits": ["same-store NOI growth", "occupancy or utilisation",
                                "rent coverage by tenant", "lease term remaining"],
    "diversified_reits": ["same-property NOI growth by property type",
                          "occupancy and weighted lease term", "portfolio mix by asset class"],
    "real_estate_services": ["organic revenue growth by service line",
                             "transaction versus recurring revenue mix",
                             "leasing and capital-markets volumes", "headcount productivity"],
    "real_estate_development": ["acres sold and price per acre", "entitlement pipeline",
                                "homesite versus commercial mix", "development spend"],
    # ------------------------------------------------- Consumer Discretionary, the tail
    "specialized_consumer_services": ["organic revenue growth", "customer or membership count",
                                      "retention and churn", "price per transaction"],
    "other_specialty_retail": ["comparable sales", "sales per square foot",
                               "store count and net openings", "gross margin rate"],
    "broadline_retail": ["comparable sales and traffic", "gross merchandise value",
                         "digital penetration", "inventory turns"],
    "leisure_facilities": ["membership or visitation count", "revenue per member or visit",
                           "facility count and openings", "utilisation and seasonality"],
    "footwear": ["pairs shipped or unit volume", "full-price sell-through",
                 "wholesale versus direct mix", "average selling price"],
    "distributors": ["organic daily sales growth", "gross margin per order",
                     "fill rate and service level", "end-market mix"],
    "automobile_manufacturers": ["unit deliveries", "average transaction price and incentives",
                                 "plant utilisation", "warranty cost per unit",
                                 "electric versus combustion mix"],
    "computer_electronics_retail": ["comparable sales", "services and membership attach rate",
                                    "average selling price versus units", "store count"],
    "household_appliances": ["unit shipments", "price/mix versus volume",
                             "replacement versus new-construction demand", "capacity utilisation"],
    "homefurnishing_retail": ["comparable sales", "average ticket", "delivered versus written",
                              "sales per square foot"],
    "consumer_electronics": ["unit shipments", "average selling price",
                             "attach rate on accessories and services", "channel inventory"],
    "tires_rubber": ["replacement versus original-equipment unit volumes",
                     "price/mix per tire", "raw-material spread", "capacity utilisation"],
    "motorcycle_manufacturers": ["retail unit registrations", "dealer inventory weeks",
                                 "average selling price", "financial-services credit losses"],
    "housewares_specialties": ["unit shipments", "price/mix", "channel mix",
                               "new-product contribution"],
}


def main(apply: bool = False, sector: str = "Consumer Discretionary") -> int:
    b = pd.read_parquet(r"C:\Users\<your-user>\company_lab\data\scores.parquet")
    # The stored id comes from the taxonomy, never from a hand-typed slug: a slug typed
    # here is a slug that can disagree with `taxonomy.sector_id` and nothing would say so.
    sector_id = T.sector_id(sector)
    if sector_id is None:
        raise SystemExit(f"not one of the 11 GICS sectors: {sector!r}")
    mem = collections.defaultdict(list)
    for r in b[b["sector"] == sector].to_dict("records"):
        mem[T.industry_id(r.get("ticker"), r.get("sub_industry"))].append(r["ticker"])

    # A unit is only built for the sector it belongs to, so a stale name in UNITS cannot
    # quietly create an object under the wrong sector_id.
    for iid in [u for u in UNITS if u in mem]:
        members = sorted(mem.get(iid, []))
        if not members:
            print(f"SKIP {iid}: no members in the book")
            continue
        path = ROOT / iid / "industry_state.json"
        if path.exists():
            print(f"SKIP {iid}: an artifact already exists - not overwriting")
            continue
        obj = {
            "industry_id": iid,
            "sector_id": sector_id,
            "version": VERSION,
            "status": "SHADOW",
            # every ordinal starts UNKNOWN; only a verified claim moves one
            "structural_growth": "UNKNOWN",
            "replication_difficulty": "UNKNOWN",
            "substitution_risk": "UNKNOWN",
            # FACTUAL without research: who is in the unit, from the book
            "key_participants": members,
            "key_metrics": KEY_METRICS[iid],
            "refresh_class": "QUARTERLY",
            "next_refresh_due": NEXT_REFRESH,
            "claims": [],
            "last_updated": f"{date.today().isoformat()}T00:00:00-04:00",
        }
        res = RI.validate_industry(obj)
        bad = res.get("reasons") or res.get("claim_reasons")
        print(f"{'OK  ' if not bad else 'INVALID'} {iid:28} members={len(members):2} {' '.join(members)}"
              + (f"  {bad}" if bad else ""))
        if apply and not bad:
            path.parent.mkdir(parents=True, exist_ok=True)
            io.open(path, "w", encoding="utf-8").write(json.dumps(obj, indent=1))
    print("\nDRY RUN - nothing written" if not apply else "\nskeletons written")
    return 0


if __name__ == "__main__":
    _argv = sys.argv[1:]
    _sector = (_argv[_argv.index("--sector") + 1] if "--sector" in _argv
               else "Consumer Discretionary")
    raise SystemExit(main(apply="--apply" in _argv, sector=_sector))
