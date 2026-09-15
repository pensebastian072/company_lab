"""The research units, and the reason they are not just GICS sub-industries.

The load-bearing claim of this module is that GICS cannot express the units shared
research needs. These tests pin the specific cases that proved it, so a later
simplification back to `slugify(sub_industry)` fails loudly instead of quietly
scattering FICO's competitors across two sectors again.
"""
from __future__ import annotations

import pytest

from clab.external import taxonomy as T
from clab.external.schema import SECTOR_IDS


# ------------------------------------------------------------------ sector_id
def test_all_eleven_gics_sectors_resolve():
    labels = ["Information Technology", "Health Care", "Financials",
              "Consumer Discretionary", "Communication Services", "Industrials",
              "Consumer Staples", "Energy", "Utilities", "Real Estate", "Materials"]
    got = {T.sector_id(x) for x in labels}
    assert got == set(SECTOR_IDS)
    assert None not in got


def test_an_unknown_sector_is_none_not_a_bucket():
    """The book carries rows from removed constituents with no sector. Coercing them
    would build one large pseudo-sector out of unrelated companies."""
    for bad in (None, "", "   ", "Miscellaneous", "Tech"):
        assert T.sector_id(bad) is None


# --------------------------------------------------------------------- slug
def test_slug_handles_every_separator_gics_actually_uses():
    assert T.slug("Oil & Gas Exploration & Production") == "oil_gas_exploration_production"
    assert T.slug("Hotels, Resorts & Cruise Lines") == "hotels_resorts_cruise_lines"
    assert T.slug("Technology Hardware, Storage & Peripherals") == \
        "technology_hardware_storage_peripherals"
    assert T.slug("  Trailing & ") == "trailing"
    assert T.slug(None) == ""


# ---------------------------------------------------------------- industry_id
def test_gics_scatters_the_credit_complex_and_the_override_reunites_it():
    """FICO is Information Technology / Application Software. EFX and TRU are
    Industrials / Research & Consulting Services. Two sectors, three sub-industries,
    one regulatory research problem."""
    assert T.industry_id("FICO", "Application Software") == "us_credit_scoring"
    assert T.industry_id("EFX", "Research & Consulting Services") == "us_credit_scoring"
    assert T.industry_id("TRU", "Research & Consulting Services") == "us_credit_scoring"
    # and the override must not capture the whole bucket it came from
    assert T.industry_id("ADBE", "Application Software") == "application_software"


def test_e65_splits_bitcoin_mining_from_dns_cdn_infrastructure():
    """Hash rate, power cost and network difficulty are not DNS/CDN metrics."""
    for ticker in ("AKAM", "DOCN", "GDDY", "VRSN"):
        assert T.industry_id(ticker, "Internet Services & Infrastructure") == \
            "internet_infrastructure_services"
    for ticker in ("CLSK", "MARA"):
        assert T.industry_id(ticker, "Internet Services & Infrastructure") == \
            "bitcoin_mining"


def test_e65_splits_solar_modules_from_semiconductors():
    """FSLR sells photovoltaic modules, not semiconductor devices."""
    assert T.industry_id("FSLR", "Semiconductors") == "solar_modules"
    assert T.industry_id("TXN", "Semiconductors") == "semiconductors"


def test_health_insurers_leave_the_care_delivery_bucket():
    """GICS files CVS, CI and ALHC under Health Care Services beside dialysis clinics
    and imaging centres. All three underwrite medical risk; CVS owns Aetna. They belong
    with UNH and ELV on MLR, membership, star ratings and risk adjustment."""
    for t in ("CVS", "CI", "ALHC"):
        assert T.industry_id(t, "Health Care Services") == "managed_health_care"
    # ...and the override must not swallow the care-delivery companies it came from
    assert T.industry_id("DVA", "Health Care Services") == "health_care_services"


def test_reference_labs_are_their_own_unit():
    for t in ("LH", "DGX", "NEO", "VCYT"):
        assert T.industry_id(t, "Health Care Services") == "clinical_laboratories"


def test_drug_discovery_software_is_health_care_TECHNOLOGY():
    assert T.industry_id("SDGR", "Health Care Services") == "health_care_technology"


def test_custody_banks_leave_the_asset_manager_bucket():
    """BNY, NTRS and STT take deposits, run a securities portfolio and answer to the Fed.
    BlackRock is researched on AUM, net flows and fee rate and answers to the SEC."""
    for t in ("BNY", "NTRS", "STT"):
        assert T.industry_id(t, "Asset Management & Custody Banks") == "custody_banks"
    assert T.industry_id("BLK", "Asset Management & Custody Banks") ==         "asset_management_custody_banks"


def test_alternative_managers_leave_the_long_only_bucket():
    for t in ("APO", "ARES", "BX", "CG", "KKR"):
        assert T.industry_id(t, "Asset Management & Custody Banks") ==             "alternative_asset_management"


def test_exchanges_and_data_are_different_businesses():
    """An exchange earns volume-linked transaction fees; a ratings business moves with
    the credit cycle. GICS calls them one sub-industry."""
    assert T.industry_id("CME", "Financial Exchanges & Data") == "financial_exchanges"
    assert T.industry_id("SPGI", "Financial Exchanges & Data") == "financial_data_ratings"
    assert T.industry_id("MCO", "Financial Exchanges & Data") == "financial_data_ratings"


def test_e56_recut_the_three_incoherent_buckets():
    """E54 settled the singleton argument by measurement.

    All three of these were kept whole because splitting made singletons. Researched as
    single objects they returned UNKNOWN on structural_growth, replication_difficulty AND
    substitution_risk - so they were delivering nothing to their members, and a singleton
    that can be answered beats a bucket that cannot.
    """
    assert T.industry_id("BRK-B", "Multi-Sector Holdings") == "multi_industry_conglomerate"
    assert T.industry_id("VOYA", "Multi-Sector Holdings") == "retirement_benefits"
    assert T.industry_id("HASI", "Specialized Finance") == "climate_infrastructure_finance"
    assert T.industry_id("WD", "Commercial & Residential Mortgage Finance") ==         "commercial_mortgage_banking_servicing"
    for t in ("ACT", "ESNT", "NMIH"):
        assert T.industry_id(t, "Commercial & Residential Mortgage Finance") ==             "private_mortgage_insurance"


def test_e56_folds_into_existing_objects_rather_than_making_singletons():
    """Six of the ten re-cut companies land in objects that already carry their metrics.

    This is the half of the re-cut that is NOT a singleton, and it is most of it. JEF and
    LAZ are investment banks; CACC is a subprime consumer lender and the object already
    holds WRLD, ENVA and ECPG; EFC sits on the agency-versus-credit mix mortgage_reits is
    already researched on.
    """
    assert T.industry_id("JEF", "Multi-Sector Holdings") == "investment_banking_brokerage"
    assert T.industry_id("LAZ", "Diversified Capital Markets") == "investment_banking_brokerage"
    assert T.industry_id("CACC", "Specialized Finance") == "consumer_finance"
    assert T.industry_id("EFC", "Specialized Finance") == "mortgage_reits"
    assert T.industry_id("EQH", "Diversified Financial Services") == "retirement_benefits"


def test_alrm_is_not_papered_over_with_an_override():
    """ALRM is Alarm.com, home-security software, carried into Financials by an error in
    the BOOK's sector data. The sector field is what is wrong; an industry override would
    hide that. It stays blocked until the sector data is fixed."""
    assert "ALRM" not in T.INDUSTRY_OVERRIDES


def test_pinterest_leaves_the_video_game_bucket():
    """GICS files PINS under Interactive Home Entertainment beside Take-Two. Pinterest is
    an ad-supported social platform whose peers on DAU, ad load and ARPU are META and
    RDDT. A games object is researched on release slates and live-service monetisation."""
    assert T.industry_id("PINS", "Interactive Home Entertainment") == "interactive_media_services"
    assert T.industry_id("TTWO", "Interactive Home Entertainment") == "interactive_home_entertainment"


def test_ad_platforms_leave_the_agency_bucket():
    """APP, TTD and DV sell software to advertisers; OMC sells agency services. One
    object covering both would be true of neither."""
    for t in ("APP", "TTD", "DV"):
        assert T.industry_id(t, "Advertising") == "ad_tech"
    for t in ("OMC", "ZD"):
        assert T.industry_id(t, "Advertising") == "advertising"


def test_competitive_generators_leave_the_regulated_utility_bucket():
    """A rate-regulated utility is researched on rate base, allowed ROE and the state
    commission. A merchant generator is researched on power prices, capacity auctions
    and PPA pricing. CEG and VST are filed beside DUK and SO; TLN is filed in a
    different bucket from CEG while running the same nuclear-to-hyperscaler business."""
    for t in ("CEG", "VST", "TLN", "NRG"):
        assert T.industry_id(t, "Electric Utilities") == "competitive_power_generation"
    # ...and the override must not swallow the regulated fleet it came from
    assert T.industry_id("DUK", "Electric Utilities") == "electric_utilities"
    assert T.industry_id("SO", "Electric Utilities") == "electric_utilities"


def test_AES_is_deliberately_left_in_the_IPP_bucket_alone():
    """A knowing one-company object. AES owns rate-regulated utilities in Ohio and
    Indiana alongside international development, so it is not a competitive generator
    in the sense the override means. Pinned so a later reader does not 'fix' it."""
    assert "AES" not in T.INDUSTRY_OVERRIDES
    assert T.industry_id(
        "AES", "Independent Power Producers & Energy Traders"
    ) == "independent_power_producers_energy_traders"


def test_semiconductors_splits_into_units_with_different_metrics():
    assert T.industry_id("NVDA", "Semiconductors") == "ai_accelerators"
    assert T.industry_id("AMD", "Semiconductors") == "ai_accelerators"
    assert T.industry_id("MU", "Semiconductors") == "dram_hbm"
    assert T.industry_id("TXN", "Semiconductors") == "semiconductors"


def test_systems_software_splits_cloud_from_security():
    assert T.industry_id("MSFT", "Systems Software") == "cloud_infrastructure"
    assert T.industry_id("CRWD", "Systems Software") == "cybersecurity"
    assert T.industry_id("ADSK", "Systems Software") == "systems_software"


def test_datacenter_power_is_a_subset_not_the_whole_bucket():
    """Aliasing "Electrical Components & Equipment" wholesale was tried and reverted:
    it swept in AYI (lighting), HAYW (pool equipment) and MRCY (defense electronics).
    E79 now gives those three their own economically scoped units without changing the
    protected ETN/VRT decision."""
    assert T.industry_id("VRT", "Electrical Components & Equipment") == \
        "datacenter_power_cooling"
    assert T.industry_id("ETN", "Electrical Components & Equipment") == \
        "datacenter_power_cooling"
    # AYI's own unit was retired empty and folded 2026-09-11 into the switchgear/
    # enclosures unit that shares its GICS bucket and channel. The point this test makes
    # is unchanged: AYI is NOT datacenter_power_cooling.
    assert T.industry_id("AYI", "Electrical Components & Equipment") == \
        "electrical_enclosures_switchgear"
    assert T.industry_id("HAYW", "Electrical Components & Equipment") == \
        "pool_equipment"
    assert T.industry_id("MRCY", "Electrical Components & Equipment") == \
        "defense_mission_systems"


def test_aliases_rename_but_never_change_membership():
    """Every SUBINDUSTRY_ALIASES entry must be a pure rename. `upstream_shale` was
    rejected for exactly this reason: it is false for offshore and conventional."""
    assert T.industry_id("EOG", "Oil & Gas Exploration & Production") == \
        "upstream_oil_gas"
    assert T.industry_id("KMI", "Oil & Gas Storage & Transportation") == "midstream"
    assert T.industry_id("VLO", "Oil & Gas Refining & Marketing") == "refining"
    assert "upstream_shale" not in T.SUBINDUSTRY_ALIASES.values()


def test_ticker_override_beats_alias():
    assert T.industry_id("V", "Transaction & Payment Processing Services") == "payments"
    assert T.industry_id("XYZ", "Transaction & Payment Processing Services") == "payments"


def test_ticker_lookup_is_case_and_whitespace_insensitive():
    assert T.industry_id("fico", "Application Software") == "us_credit_scoring"
    assert T.industry_id("  FICO  ", "Application Software") == "us_credit_scoring"


def test_no_sub_industry_and_no_override_is_none_not_a_default_bucket():
    assert T.industry_id(None, None) is None
    assert T.industry_id("ZZZZ", "") is None
    # ...but an override still works with no sub-industry, which is how an xsect
    # company can join a research unit before it has a GICS label.
    assert T.industry_id("FICO", None) == "us_credit_scoring"


def test_resolve_returns_all_three_ids():
    got = T.resolve("FICO", "Information Technology", "Application Software")
    assert got == {"sector_id": "information_technology",
                   "industry_id": "us_credit_scoring",
                   "subindustry_id": "application_software"}


def test_subindustry_id_is_always_kept_even_when_industry_id_overrides_it():
    """The descriptive label must survive the research-unit decision, or the workbook
    loses the ability to say what GICS actually thinks."""
    got = T.resolve("NVDA", "Information Technology", "Semiconductors")
    assert got["industry_id"] == "ai_accelerators"
    assert got["subindustry_id"] == "semiconductors"


# ---------------------------------------------------------- reverse index
def test_industry_members_is_sorted_and_groups_the_override():
    rows = [{"ticker": "FICO", "sub_industry": "Application Software"},
            {"ticker": "TRU", "sub_industry": "Research & Consulting Services"},
            {"ticker": "EFX", "sub_industry": "Research & Consulting Services"},
            {"ticker": "ADBE", "sub_industry": "Application Software"}]
    idx = T.industry_members(rows)
    assert idx["us_credit_scoring"] == ["EFX", "FICO", "TRU"]
    assert idx["application_software"] == ["ADBE"]


def test_industry_members_drops_rows_with_no_resolvable_unit():
    idx = T.industry_members([{"ticker": "X", "sub_industry": None}])
    assert idx == {}


# ------------------------------------------------- against the real book
def test_every_company_in_the_live_book_resolves_to_a_sector_and_an_industry():
    """Guards the case the whole module exists to avoid: a silent None that drops a
    company out of every shared research object."""
    pd = pytest.importorskip("pandas")
    from clab import config
    if not config.SCORES_PARQUET.exists():
        pytest.skip("no book on disk")
    df = pd.read_parquet(config.SCORES_PARQUET)[["ticker", "sector", "sub_industry"]]
    rows = df.to_dict("records")
    no_sector = [r["ticker"] for r in rows if T.sector_id(r["sector"]) is None]
    no_industry = [r["ticker"] for r in rows
                   if T.industry_id(r["ticker"], r["sub_industry"]) is None]
    assert no_sector == [], f"{len(no_sector)} rows have no sector_id: {no_sector[:10]}"
    assert no_industry == [], \
        f"{len(no_industry)} rows have no industry_id: {no_industry[:10]}"


def test_every_override_ticker_exists_in_the_live_book():
    """An override for a ticker with no scorecard creates an industry object nothing
    references. ASML and other foreign filers join at P4 with the xsect tier, not
    before."""
    pd = pytest.importorskip("pandas")
    from clab import config
    if not config.SCORES_PARQUET.exists():
        pytest.skip("no book on disk")
    known = set(pd.read_parquet(config.SCORES_PARQUET)["ticker"].dropna())
    orphans = sorted(t for t in T.INDUSTRY_OVERRIDES if t not in known)
    assert orphans == [], f"override tickers not in the book: {orphans}"


def test_mgic_is_researched_as_a_private_mortgage_insurer_not_a_reinsurer():
    """MTG's GICS sub-industry is wrong and the override is what protects the comparison.

    The book files MGIC as "Reinsurance", so before the override it resolved to
    `reinsurance` and E59 batch 3 judged it on treaty pricing, retrocession cost and ILS
    capacity - none of which a private mortgage insurer has. ACT, ESNT and NMIH were
    already overridden; MTG, the largest of the four, was missing from its own peer group,
    which made the unit the wrong comparison set for the other three as well.
    """
    assert T.industry_id("MTG", "Reinsurance") == "private_mortgage_insurance"
    peers = {T.industry_id(t, "Reinsurance") for t in ("ACT", "ESNT", "NMIH", "MTG")}
    assert peers == {"private_mortgage_insurance"}, (
        "the four US private mortgage insurers must share one research unit")
