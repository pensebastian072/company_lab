"""sector_id / industry_id / subindustry_id - the keys shared research hangs off.

## Why this module is not a one-line slugify

The obvious design is `industry_id = slugify(sub_industry)` and nothing else. It does
not work, and the reason is worth stating because it shapes the whole external layer.

Measured against the live book (1,501 companies, 155 distinct GICS sub-industries):

* **FICO is `Application Software`** - the same bucket as 39 unrelated companies. Its
  two closest competitors, EFX and TRU, are in `Industrials / Research & Consulting
  Services`. GICS scatters the US consumer-credit complex across two sectors and three
  sub-industries. A sector-agent-only design would never put those three companies in
  the same conversation, which is exactly the conversation the FICO case needs.
* **NVDA, MU, AMD and AVGO are all `Semiconductors`.** AI accelerators, DRAM/HBM and
  analog have different customers, different cycles and different metrics. Pooling them
  produces an industry brief true of none of them.
* **MSFT and CRWD are both `Systems Software`.** Cloud infrastructure and endpoint
  security share a label and nothing else.
* **VRT and ETN are `Electrical Components & Equipment`** - together with AYI
  (lighting), HAYW (pool equipment) and MRCY (defense electronics). The datacenter
  power and cooling unit is a subset of that bucket, not the bucket.

So GICS sub-industry is a good DEFAULT and a bad RULE. This module keeps it as the
default and carries a small, explicit override map for the research units where the
label and the industry genuinely diverge.

## The three ids

* `sector_id`      - one of the 11 GICS sectors, slugged. Owns a persistent analyst.
* `subindustry_id` - the GICS sub-industry, slugged. Descriptive; always present.
* `industry_id`    - the RESEARCH unit. Defaults to `subindustry_id`; overridden where
                     the override map says the real industry is finer or wider.

`industry_id` is what shared research is keyed on, so that a fact about US credit
scoring is researched once and referenced by FICO, EFX and TRU rather than three times.
"""
from __future__ import annotations

import re

from .schema import SECTOR_IDS

#: GICS sector string -> sector_id. Built from SECTOR_IDS so the two cannot drift.
_SECTOR_BY_SLUG = {s: s for s in SECTOR_IDS}


def slug(text: str | None) -> str:
    """Lowercase, ASCII, underscore-joined. Stable enough to be a directory name.

    `&`, `,`, `/` and `-` all appear in GICS labels and all become separators, so
    "Oil & Gas Exploration & Production" -> "oil_gas_exploration_production".
    """
    if not text:
        return ""
    s = re.sub(r"[^0-9a-zA-Z]+", "_", str(text).strip().lower())
    return s.strip("_")


def sector_id(sector: str | None) -> str | None:
    """GICS sector string -> sector_id, or None if it is not one of the 11.

    None rather than a coerced value: a company with no sector must not silently join
    a real sector's research. The book has 161 such rows from removed constituents and
    they would have formed one large pseudo-sector.
    """
    s = slug(sector)
    return s if s in _SECTOR_BY_SLUG else None


def subindustry_id(sub_industry: str | None) -> str | None:
    s = slug(sub_industry)
    return s or None


# ------------------------------------------------------- research-unit overrides
#: Ticker -> industry_id, for the research units GICS cannot express.
#:
#: Deliberately a TICKER map and not a sub-industry map: every entry here exists
#: because the sub-industry is the wrong unit, so keying on it would defeat the point.
#: Small on purpose. An override is a claim that we know better than GICS about a
#: specific company, and each one should be defensible in a sentence.
#:
#: Seeded with the 15 objects the V3 plan names, restricted to companies actually in
#: the S&P 500/400/600 book. ASML, TSM and other foreign filers arrive with the xsect
#: tier (P4) and are added then, not now - listing a ticker that has no scorecard would
#: create an industry object nothing references.
INDUSTRY_OVERRIDES: dict[str, str] = {
    # US_credit_scoring - split across IT/Application Software and
    # Industrials/Research & Consulting Services. The regulatory research (FHFA policy,
    # bi-merge/tri-merge, lender adoption) is identical for all three and must be
    # researched once.
    "FICO": "us_credit_scoring",
    "EFX": "us_credit_scoring",
    "TRU": "us_credit_scoring",

    # AI_accelerators vs DRAM_HBM vs the rest of "Semiconductors". Different customers,
    # different cycles, different metrics; a single semis brief is true of none of them.
    "NVDA": "ai_accelerators",
    "AMD": "ai_accelerators",
    "MU": "dram_hbm",

    # E65 taxonomy checkpoint. FSLR manufactures thin-film photovoltaic modules;
    # it does not participate in the semiconductor design/fabrication value chain.
    "FSLR": "solar_modules",

    # GICS places these six names in Internet Services & Infrastructure, but DNS,
    # registry, CDN and cloud-hosting economics do not share a cycle or metric with
    # proof-of-work mining. Keep the four network-service names together and separate
    # the two miners before constructing either research object.
    "AKAM": "internet_infrastructure_services",
    "DOCN": "internet_infrastructure_services",
    "GDDY": "internet_infrastructure_services",
    "VRSN": "internet_infrastructure_services",
    "CLSK": "bitcoin_mining",
    "MARA": "bitcoin_mining",

    # semiconductor_equipment - GICS's "Semiconductor Materials & Equipment" is the
    # right unit, but it is named here so the EUV research object has a stable id that
    # ASML can join at P4 without renaming anything.
    "AMAT": "semiconductor_equipment",
    "LRCX": "semiconductor_equipment",
    "KLAC": "semiconductor_equipment",

    # datacenter_power_cooling - a SUBSET of "Electrical Components & Equipment".
    # Aliasing the whole bucket was tried and reverted: it caught AYI, HAYW and MRCY,
    # whose research has nothing to do with datacenter power.
    "VRT": "datacenter_power_cooling",
    "ETN": "datacenter_power_cooling",

    # cloud_infrastructure vs cybersecurity, both "Systems Software".
    "MSFT": "cloud_infrastructure",
    "ORCL": "cloud_infrastructure",
    "PANW": "cybersecurity",
    "CRWD": "cybersecurity",
    "FTNT": "cybersecurity",
    "OKTA": "cybersecurity",
    # ZS (Zscaler) belongs in this unit and is deliberately ABSENT: it is not in the
    # S&P 500/400/600 book, and an override for a ticker with no scorecard creates an
    # industry object nothing references. test_every_override_ticker_exists_in_the_live_book
    # caught it. Add it with the xsect tier at P4 if it is wanted, not before.

    # uranium_enrichment - GICS files Centrus under "Coal & Consumable Fuels" beside
    # Peabody and Core Natural Resources. E46 measured the consequence: Codex built the
    # coal object, found the bucket incoherent, and returned UNKNOWN for structural
    # growth, replication difficulty AND substitution risk rather than fabricate a
    # shared score - "the products, customers, regulation, capital cycles and demand
    # drivers are incompatible". That refusal was correct and it cost all three
    # companies their industry-growth field.
    #
    # The fix is the taxonomy, not the research. Enrichment is a licensed,
    # capital-barriered fuel-cycle business whose competitors are Urenco, Orano and
    # Rosatom; coal mining is not. This is the same case as FICO sitting in
    # "Application Software".
    "LEU": "uranium_enrichment",

    # competitive_power_generation - the utilities version of the FICO case, and it
    # runs both ways at once.
    #
    # GICS files CEG and VST under "Electric Utilities" beside DUK, SO and PEG, and
    # files TLN under "Independent Power Producers & Energy Traders". None of those
    # four earns a regulated return. A rate-regulated utility is researched on rate
    # base growth, allowed ROE, regulatory lag and the posture of its state commission;
    # a competitive generator is researched on power prices, capacity auctions, PPA
    # pricing, the hedge book and nuclear production credits. An industry object
    # covering both is true of neither.
    #
    # The measured half corroborates it on the one metric that most encodes "is this
    # revenue guaranteed by a regulator": net debt / EBITDA is 5.2-6.6x across the
    # regulated fleet (DUK 5.2, SO 5.3, EXC 5.6, PEG 5.9, NEE 6.4, D 6.6) and 2.9-3.6x
    # for CEG and VST, because a merchant cash flow cannot carry rate-base leverage.
    #
    # And TLN sitting in a different GICS bucket from CEG while running the same
    # business - a nuclear fleet contracted to hyperscalers - is the FICO-split-across-
    # sectors case exactly.
    #
    # NRG is included deliberately. It looks least like CEG on margin (6.2% vs 18.5%)
    # but that gap is retail mix, not regulation: NRG is ERCOT generation plus the
    # largest US competitive retail book, which is the same shape as VST (Comanche Peak
    # plus TXU Energy). Splitting them would put the two most similar companies in the
    # book into different objects.
    "CEG": "competitive_power_generation",
    "VST": "competitive_power_generation",
    "TLN": "competitive_power_generation",
    "NRG": "competitive_power_generation",
    # AES is knowingly LEFT BEHIND in independent_power_producers_energy_traders as the
    # only member. It is not a competitive generator in the sense above: it owns AES
    # Indiana and AES Ohio, which are rate-regulated, alongside an international
    # development portfolio. A one-company object is a real cost - its research is
    # shared with nobody - and it is accepted here rather than forcing AES into a unit
    # half its business does not belong to. This is a decision, not an oversight.

    # interactive_media_services - PINS is filed by GICS under "Interactive Home
    # Entertainment", the VIDEO GAME bucket, beside Take-Two. Pinterest is an ad-supported
    # social platform: its economics are DAU/MAU, ad load and ARPU, and its named peers on
    # every one of those are META and RDDT. A games object would be researched on release
    # slates, franchise strength and live-service monetisation, none of which apply to it.
    # Same case as CEG sitting among regulated utilities.
    "PINS": "interactive_media_services",
    # TTWO is knowingly LEFT ALONE in interactive_home_entertainment once PINS moves out.
    # It is a genuine video-game publisher and the book contains no other one. A
    # one-company object is a real cost, accepted rather than keeping a games bucket that
    # is half not-games. Same decision as AES, recorded so it is not "fixed" later.

    # ad_tech - "Advertising" holds two different businesses. APP, TTD and DV sell
    # SOFTWARE to advertisers and are researched on take rate, platform spend, supply-path
    # economics, identity and measurement rules. OMC sells agency SERVICES and is
    # researched on client wins, headcount and principal-versus-agent media buying.
    # The 77.4% versus 2.2% operating-margin gap overstates it - an agency books
    # pass-through media spend as revenue - but the businesses are not the same unit, and
    # one object covering both would be true of neither.
    "APP": "ad_tech",
    "TTD": "ad_tech",
    "DV": "ad_tech",
    # OMC and ZD are deliberately NOT moved. Both sell advertising as a service or as
    # media rather than as a platform, which leaves `advertising` a coherent 2-company
    # bucket. Moving ZD to publishing on the strength of PCMag and Mashable was considered
    # and refused: it would leave OMC alone, and a singleton needs a stronger argument
    # than "the neighbour looks tidier".

    # custody_banks - GICS files BNY, NTRS and STT under "Asset Management & Custody
    # Banks" beside BlackRock and T. Rowe. They are BANKS: they take deposits, run a
    # securities portfolio, are researched on net interest income, deposit betas, CET1 and
    # assets under custody, and they answer to the Fed. An asset manager is researched on
    # AUM, net flows and fee rate and answers to the SEC. One object covering both is true
    # of neither.
    "BNY": "custody_banks",
    "NTRS": "custody_banks",
    "STT": "custody_banks",

    # alternative_asset_management - the same bucket also holds the alt managers, whose
    # economics are fee-related earnings, carried interest, permanent capital and
    # increasingly an insurance balance sheet. A long-only manager lives or dies on net
    # flows against passive; APO and KKR are substantially insurance companies attached to
    # an origination engine. Different metrics, different cycle, different regulator.
    "APO": "alternative_asset_management",
    "ARES": "alternative_asset_management",
    "BX": "alternative_asset_management",
    "CG": "alternative_asset_management",
    "KKR": "alternative_asset_management",

    # financial_exchanges vs financial_data_ratings - GICS combines them as "Financial
    # Exchanges & Data". An exchange earns volume-linked transaction and clearing fees and
    # is researched on volumes, capture rate, open interest and clearing; a data or ratings
    # business earns subscriptions and issuance-linked fees and is researched on retention,
    # price increases, and debt issuance volumes. They share a "toll road" shape and
    # nothing else. SPGI and MCO in particular move with the credit cycle, not with
    # trading volume.
    "CBOE": "financial_exchanges",
    "CME": "financial_exchanges",
    "ICE": "financial_exchanges",
    "MKTX": "financial_exchanges",
    "NDAQ": "financial_exchanges",
    "VIRT": "financial_exchanges",
    "COIN": "financial_exchanges",
    "SPGI": "financial_data_ratings",
    "MCO": "financial_data_ratings",
    "MSCI": "financial_data_ratings",
    "MORN": "financial_data_ratings",
    "FDS": "financial_data_ratings",
    "DFIN": "financial_data_ratings",
    # E56 RE-CUT. Three buckets were kept whole on the argument that splitting them made
    # singletons, and that a singleton was the worse trade. E54 settled it by measurement:
    # researched as single objects, all three returned UNKNOWN on structural_growth,
    # replication_difficulty AND substitution_risk - every one of them argued, none of
    # them a gap. An incoherent bucket does not produce a weak shared answer, it produces
    # NO answer, so it was already delivering zero to its members. A singleton that can be
    # answered beats a bucket that cannot, and an industry object describes an industry
    # rather than a peer set - `key_participants` names the private and foreign
    # competitors the book does not hold, so a one-company bucket is still researchable.
    #
    # Most of the re-cut is not a singleton at all: six of the ten companies fold into
    # objects that already exist and already carry the right metrics.
    #
    # multi_sector_holdings (BRK-B, JEF, VOYA) - a conglomerate, an investment bank and a
    # retirement business. JEF is an investment bank and the existing object is researched
    # on advisory and underwriting backlog, trading VaR and compensation ratio, which is
    # exactly how Jefferies is read. BRK-B and VOYA get their own units.
    "BRK-B": "multi_industry_conglomerate",
    "JEF": "investment_banking_brokerage",
    "VOYA": "retirement_benefits",

    # specialized_finance (CACC, EFC, HASI) - subprime auto, mortgage credit and climate
    # infrastructure. consumer_finance is already researched on receivables growth, net
    # charge-offs, reserve rate, funding mix and prime-versus-subprime mix, which is the
    # whole of how CACC is read; mortgage_reits already covers the agency-versus-credit
    # mix that EFC sits on. HASI - project finance against contracted climate
    # infrastructure, competing with private infrastructure funds - is its own unit.
    "CACC": "consumer_finance",
    "EFC": "mortgage_reits",
    "HASI": "climate_infrastructure_finance",

    # commercial_residential_mortgage_finance (ACT, ESNT, NMIH, WD) - three private
    # mortgage insurers and a commercial mortgage bank. The insurers are a genuine
    # 3-company unit researched on insurance-in-force, persistency, PMIERs capital and
    # cure rates. WD originates and services commercial mortgages for the GSEs and is
    # researched on origination volume and the servicing book, which shares none of that.
    "ACT": "private_mortgage_insurance",
    "ESNT": "private_mortgage_insurance",
    "NMIH": "private_mortgage_insurance",
    "WD": "commercial_mortgage_banking_servicing",

    # MTG is MGIC, the LARGEST of those private mortgage insurers, and it was missing from
    # its own peer group: the book files it as GICS "Reinsurance", so it resolved to
    # `reinsurance` and E59 batch 3 judged it against treaty pricing, retrocession cost and
    # ILS capacity - none of which MGIC has. A unit of ACT/ESNT/NMIH without MTG is also the
    # wrong comparison set for the other three. Same class as ALRM's sector error, but
    # fixable here because the sub-industry is wrong rather than the sector.
    "MTG": "private_mortgage_insurance",

    # Two more GICS singletons folded on the same argument, because leaving them alone
    # blocks their company from the research phase for no gain. LAZ is an advisory and
    # asset-management house that sits beside EVR, PJT, HLI and MC in the existing
    # object. EQH is retirement, wealth management and AllianceBernstein - the same
    # business as VOYA, which turns retirement_benefits from a singleton into a pair.
    # ALRM is deliberately NOT handled here: it is Alarm.com, home-security software,
    # carried into Financials by an error in the BOOK's sector data. A taxonomy override
    # would paper over that rather than fix it - the sector field is what is wrong.
    "LAZ": "investment_banking_brokerage",
    "EQH": "retirement_benefits",

    # managed_health_care - GICS files CVS, CI and ALHC under "Health Care Services",
    # beside dialysis clinics, imaging centres and a company that owns both hospice care
    # and Roto-Rooter. All three are INSURERS. Cigna and Alignment underwrite medical
    # risk; CVS owns Aetna. They are researched on medical loss ratio, membership and
    # mix, Medicare Advantage star ratings, risk adjustment and PBM rebate economics -
    # the same questions UNH, ELV, HUM, CNC and MOH already answer. A care-delivery
    # object cannot ask any of them.
    "CVS": "managed_health_care",
    "CI": "managed_health_care",
    "ALHC": "managed_health_care",

    # clinical_laboratories - LH and DGX are the two national reference labs and NEO and
    # VCYT are specialty diagnostics. Test volume, reimbursement per test, payer mix,
    # PAMA rate cuts and lab consolidation are their whole economics, and none of it
    # applies to a dialysis provider or a staffing agency.
    "LH": "clinical_laboratories",
    "DGX": "clinical_laboratories",
    "NEO": "clinical_laboratories",
    "VCYT": "clinical_laboratories",

    # SDGR is computational drug-discovery SOFTWARE - subscriptions, compute, and a
    # co-development pipeline. It sits in health_care_services in the book and belongs
    # with VEEV and the rest of health_care_technology.
    "SDGR": "health_care_technology",
    # What is LEFT in health_care_services is a genuine diversified-care-delivery bucket:
    # dialysis, imaging, home health, behavioural, staffing and benefits management.
    # Mixed, but splitting further makes singletons, and that trade was measured at E56 -
    # a singleton that can be answered beats a bucket that cannot, but only when the
    # bucket ACTUALLY cannot. Codex is asked to say which this is.

    # payments - "Transaction & Payment Processing Services" is already right, named
    # for the same reason as semiconductor_equipment.
    "V": "payments",
    "MA": "payments",
    "PYPL": "payments",
    "FIS": "payments",
    "GPN": "payments",
}

# E79 Industrials re-research.  E61 showed that the inherited GICS buckets below
# were not merely broad: several combined businesses with different customers,
# capital cycles, regulatory regimes and operating metrics, and the completeness
# gate retired every one of those objects.  Keep this map separate so its exact
# 236-company scope can be regression-tested without disturbing the cross-sector
# overrides above.  The seven current Industrials units intentionally do not appear
# here and remain owned by their earlier decisions.
E79_INDUSTRIALS_OVERRIDES: dict[str, str] = {
    **{t: "civil_aerospace_platforms_components" for t in
       "AIR ATI BA GE HONA HWM HXL KRMN MOG-A RTX SARO TDG TXT VSEC WWD".split()},
    **{t: "defense_mission_systems" for t in
       "AVAV BWXT CW GD HII KTOS LHX LMT MRCY NOC NPK PSN VVX".split()},
    "AXON": "public_safety_technology",

    **{t: "agricultural_farm_machinery" for t in "AGCO CNH DE TTC".split()},
    **{t: "integrated_parcel_delivery" for t in "FDX UPS".split()},
    **{t: "freight_forwarding_brokerage" for t in "CHRW EXPD HUBG".split()},
    "GXO": "contract_logistics",

    **{t: "building_climate_controls" for t in "AAON CARR JCI LII TT".split()},
    **{t: "building_materials_envelope" for t in
       "APOG AWI CSL CSW GFF LPX MBC NX OC ROCK SSD TREX UFPI WMS WOR".split()},
    **{t: "building_products_distribution" for t in "BCC BLDR FERG".split()},
    **{t: "building_fixtures_access" for t in "ALLE AOS FBIN MAS WTS".split()},
    "RUN": "residential_solar_services",

    **{t: "construction_engineering" for t in
       "ACA ACM AGX APG DY ECG EME FIX FLR GVA IESC J MTZ MYRG PRIM PWR ROAD STRL TPC TTEK".split()},
    **{t: "off_highway_equipment" for t in "ALG ASTE CAT FSS OSK TEX".split()},
    **{t: "commercial_vehicle_powertrain" for t in "ALSN CMI PCAR RUSHA".split()},
    **{t: "rail_equipment_leasing" for t in "GATX GBX TRN WAB".split()},

    **{t: "business_process_outsourcing" for t in "CNXC EXLS G".split()},
    # FOLDS, 2026-09-11. E79 split these out and the gate retired the pieces as concluding
    # nothing; every one below is a single filing trying to evidence an industry. The rule
    # applied: fold back into the unit that shares the GICS bucket, unless an economic
    # argument names a better host. Decision recorded in docs/MASTER_PLAN_TO_1500_2026-09-11.md.
    "BR": "business_process_outsourcing",       # same GICS bucket as CNXC/EXLS/G
    "MMS": "government_program_administration",
    "VRRM": "public_safety_technology",         # government enforcement tech, with AXON:
                                                # camera hardware + processing sold to agencies
    "MBGL": "automotive_data_analytics",

    **{t: "government_mission_services" for t in "AMTM BAH CACI KBR LDOS SAIC".split()},
    **{t: "auction_marketplaces" for t in "CPRT LQDT OPLN RBA".split()},
    **{t: "uniform_rental_services" for t in "CTAS UNF VSTS".split()},
    **{t: "corrections_facilities" for t in "CXW GEO".split()},

    **{t: "industrial_controls_sensors" for t in "AME EMR ROK RRX ST".split()},
    "AYI": "electrical_enclosures_switchgear",   # FOLD: same GICS bucket as NVT/POWL and the
                                                # same electrical-distributor channel
    **{t: "energy_storage_power_conversion" for t in "ENS VICR".split()},
    **{t: "electrical_enclosures_switchgear" for t in "NVT POWL".split()},
    "NXT": "solar_tracking_systems",
    "HAYW": "pool_equipment",

    **{t: "facilities_services" for t in "ABM HCSG".split()},
    **{t: "waste_environmental_services" for t in "CLH CWST RSG WM".split()},
    "ROL": "pest_control_services",
    **{t: "water_infrastructure_analytics" for t in "FELE MWA VLTO XYL ZWS".split()},

    **{t: "payroll_hcm" for t in "ADP NSP PAYC PAYX PCTY".split()},
    **{t: "staffing_executive_search" for t in "KFY MAN RHI".split()},
    "FA": "background_screening",
    "UPWK": "talent_marketplaces",

    # FOLD: HON, MMM and DD are all GICS Industrial Conglomerates. E79 made HON+MMM a
    # two-member "multi_industry" unit and DD a singleton, and both were retired empty.
    # Re-unified into the bucket's own unit, which the Industrials top-up must evidence -
    # a 3-member conglomerate unit is a real industry, a 1-member one was not.
    **{t: "industrial_conglomerates" for t in "DD HON MMM".split()},

    **{t: "flow_filtration_equipment" for t in
       "ATMU DCI FLS GGG IEX IR ITT PNR SPXC".split()},
    **{t: "engineered_motion_components" for t in
       "AIN CR CRS DOV ESE GTES HUBB ITW MLI NPO PH RBC SXI TKR VMI".split()},
    # FOLD: all six are GICS Industrial Machinery & Supplies, the bucket E79 split them out
    # of. Retired empty; their filings never named a substitute or a barrier in quotable terms.
    **{t: "engineered_motion_components" for t in "EPAC ESAB KMT LECO SNA SWK".split()},
    **{t: "food_processing_equipment" for t in "JBTM MFP MIDD".split()},
    # FOLD: same bucket, same reason as the tools above.
    **{t: "engineered_motion_components" for t in "FTV KAI NDSN PRLB".split()},
    "OTIS": "elevators_escalators",
    **{t: "industrial_distribution" for t in "AIT DNOW DXPE FAST GWW MSM".split()},
    "TNC": "surface_maintenance_equipment",

    **{t: "marine_transportation" for t in "KEX MATX".split()},
    **{t: "commercial_workplace_products" for t in "HNI MLKN TILE".split()},
    "MSA": "safety_equipment",
    "PBI": "mailing_shipping_technology",
    "WSC": "modular_space_storage",

    **{t: "passenger_airlines" for t in "AAL ALGT ALK DAL JBLU LUV SKYW UAL".split()},
    **{t: "ride_hailing_platforms" for t in "LYFT UBER".split()},
    "CAR": "vehicle_rental",

    **{t: "economic_forensics_consulting" for t in "EXPO FCN".split()},
    "LZ": "online_legal_services",
    "ULS": "testing_inspection_certification",
    "VRSK": "insurance_data_analytics",
    "BCO": "cash_logistics",

    **{t: "construction_electrical_distribution" for t in "CNM REZI WCC WSO".split()},
    "URI": "equipment_rental",
}

INDUSTRY_OVERRIDES.update(E79_INDUSTRIALS_OVERRIDES)

#: sub_industry slug -> industry_id, applied when no ticker override matches.
#: Every entry here is a PURE RENAME of a GICS bucket that already is a coherent
#: research unit. None of them changes membership.
#:
#: Two candidates were tried and REMOVED after checking who they actually caught:
#:   electrical_components_equipment -> datacenter_power_cooling swept in AYI
#:     (lighting), HAYW (pool equipment) and MRCY (defense electronics). VRT and ETN
#:     get that unit through the ticker map instead, where the claim is defensible.
#:   oil_gas_exploration_production -> upstream_shale is false for offshore and
#:     conventional producers, so the neutral name is used.
#: A rename that changes meaning is not a rename.
SUBINDUSTRY_ALIASES: dict[str, str] = {
    "oil_gas_exploration_production": "upstream_oil_gas",
    "oil_gas_storage_transportation": "midstream",
    "oil_gas_refining_marketing": "refining",
    "life_health_insurance": "life_insurance",
    "property_casualty_insurance": "pc_insurance",
    "regional_banks": "regional_banking",
    "semiconductor_materials_equipment": "semiconductor_equipment",
    "transaction_payment_processing_services": "payments",
    "data_center_reits": "datacenter_reits",
}


def industry_id(ticker: str | None, sub_industry: str | None) -> str | None:
    """The research unit for a company. Ticker override wins, then alias, then the
    GICS sub-industry slug.

    Returns None only when the sub-industry is unknown AND there is no override -
    which is the honest answer, and keeps the company out of every shared research
    object rather than dropping it into an arbitrary one.
    """
    if ticker:
        override = INDUSTRY_OVERRIDES.get(str(ticker).strip().upper())
        if override:
            return override
    sub = subindustry_id(sub_industry)
    if sub is None:
        return None
    return SUBINDUSTRY_ALIASES.get(sub, sub)


def resolve(ticker: str | None, sector: str | None,
            sub_industry: str | None) -> dict[str, str | None]:
    """All three ids for one company, as they are stored on the external record."""
    return {
        "sector_id": sector_id(sector),
        "industry_id": industry_id(ticker, sub_industry),
        "subindustry_id": subindustry_id(sub_industry),
    }


def industry_members(rows) -> dict[str, list[str]]:
    """industry_id -> tickers, over an iterable of dicts with ticker/sub_industry.

    The reverse index the research priority engine needs to answer "which companies
    does this industry object cover?" and the exporter needs to build the Industries
    sheet. Built on demand rather than stored; it is cheap and it cannot go stale.
    """
    out: dict[str, list[str]] = {}
    for r in rows:
        iid = industry_id(r.get("ticker"), r.get("sub_industry"))
        if iid:
            out.setdefault(iid, []).append(r.get("ticker"))
    for members in out.values():
        members.sort()
    return out
