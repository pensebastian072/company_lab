"""E79 Industrials re-research taxonomy boundaries."""

from clab.external import taxonomy as T


def test_e79_override_scope_is_exact_and_does_not_capture_protected_units():
    assert len(T.E79_INDUSTRIALS_OVERRIDES) == 236
    # 64 units at E79. Seven were retired empty by the gate and folded 2026-09-11
    # (industrial_tools_fabrication, automation_precision_equipment,
    # multi_industry_industrials, specialty_materials_products,
    # investor_communications_processing, lighting_controls, road_tolling_enforcement)
    # and one was re-unified (industrial_conglomerates): 64 - 7 + 1 = 58.
    assert len(set(T.E79_INDUSTRIALS_OVERRIDES.values())) == 58
    protected = {
        "ARCB", "FDXF", "HTLD", "JBHT", "KNX", "LSTR", "MRTN", "ODFL",
        "R", "RXO", "SAIA", "SNDR", "WERN", "XPO", "BRC", "DLX", "ETN",
        "VRT", "AZZ", "GEV", "GNRC", "CSX", "NSC", "UNP", "NSIT", "EFX",
        "TRU",
    }
    assert protected.isdisjoint(T.E79_INDUSTRIALS_OVERRIDES)


def test_e79_separates_materially_different_economic_units():
    expected = {
        "BA": "civil_aerospace_platforms_components",
        "LMT": "defense_mission_systems",
        "AXON": "public_safety_technology",
        "FDX": "integrated_parcel_delivery",
        "EXPD": "freight_forwarding_brokerage",
        "GXO": "contract_logistics",
        "CARR": "building_climate_controls",
        "BLDR": "building_products_distribution",
        "RUN": "residential_solar_services",
        "CAT": "off_highway_equipment",
        "PCAR": "commercial_vehicle_powertrain",
        "GATX": "rail_equipment_leasing",
        "G": "business_process_outsourcing",
        "MBGL": "automotive_data_analytics",
        "BR": "business_process_outsourcing",       # folded 2026-09-11
        "MMS": "government_program_administration",
        "VRRM": "public_safety_technology",         # folded 2026-09-11
        "CACI": "government_mission_services",
        "CTAS": "uniform_rental_services",
        "CXW": "corrections_facilities",
        "ROK": "industrial_controls_sensors",
        "NXT": "solar_tracking_systems",
        "WM": "waste_environmental_services",
        "ROL": "pest_control_services",
        "ADP": "payroll_hcm",
        "RHI": "staffing_executive_search",
        "UPWK": "talent_marketplaces",
        "HON": "industrial_conglomerates",          # re-unified 2026-09-11
        "DD": "industrial_conglomerates",
        "FLS": "flow_filtration_equipment",
        "PH": "engineered_motion_components",
        "LECO": "engineered_motion_components",     # folded 2026-09-11
        "MIDD": "food_processing_equipment",
        "OTIS": "elevators_escalators",
        "GWW": "industrial_distribution",
        "MSA": "safety_equipment",
        "WSC": "modular_space_storage",
        "UBER": "ride_hailing_platforms",
        "CAR": "vehicle_rental",
        "VRSK": "insurance_data_analytics",
        "BCO": "cash_logistics",
        "URI": "equipment_rental",
    }
    for ticker, industry_id in expected.items():
        assert T.industry_id(ticker, "deliberately ignored by override") == industry_id


def test_e79_cross_bucket_folds_are_deliberate():
    assert T.industry_id("GEO", "Environmental & Facilities Services") == \
        "corrections_facilities"
    assert T.industry_id("BAH", "Research & Consulting Services") == \
        "government_mission_services"
    assert T.industry_id("XYL", "Industrial Machinery & Supplies & Components") == \
        "water_infrastructure_analytics"
    assert T.industry_id("GWW", "Industrial Machinery & Supplies & Components") == \
        "industrial_distribution"


def test_the_retired_e79_residue_is_folded_not_evidenced():
    """Seven units the gate retired as concluding nothing are folded, by the rule
    'back into the unit sharing the GICS bucket unless an economic argument names a
    better host'. A split that leaves one company in a unit leaves one filing to
    evidence it from, which is why these never reached even one ordinal.

    Decision and per-unit reasoning: docs/MASTER_PLAN_TO_1500_2026-09-11.md.
    """
    # all ten are GICS Industrial Machinery & Supplies - the bucket E79 split them out of
    for t in "EPAC ESAB KMT LECO SNA SWK FTV KAI NDSN PRLB".split():
        assert T.industry_id(t, "Industrial Machinery & Supplies & Components") == \
            "engineered_motion_components", t
    # three GICS Industrial Conglomerates re-unified into the bucket's own unit
    for t in "HON MMM DD".split():
        assert T.industry_id(t, "Industrial Conglomerates") == "industrial_conglomerates", t
    assert T.industry_id("BR", "Data Processing & Outsourced Services") == \
        "business_process_outsourcing"
    assert T.industry_id("VRRM", "Data Processing & Outsourced Services") == \
        "public_safety_technology"
    assert T.industry_id("AYI", "Electrical Components & Equipment") == \
        "electrical_enclosures_switchgear"
    # the two exceptions stay singletons and must name foreign peers in their objects
    assert T.industry_id("URI", "Trading Companies & Distributors") == "equipment_rental"
    assert T.industry_id("BCO", "Diversified Support Services") == "cash_logistics"
    # and none of the retired ids can be produced by the taxonomy any more
    retired = {"industrial_tools_fabrication", "automation_precision_equipment",
               "multi_industry_industrials", "specialty_materials_products",
               "investor_communications_processing", "lighting_controls",
               "road_tolling_enforcement"}
    assert retired.isdisjoint(T.E79_INDUSTRIALS_OVERRIDES.values())
