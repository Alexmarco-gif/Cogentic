"""Add Agriculture & Agritech domain (5th industry)

Revision ID: 2026_02_13_0001
Revises: 2026_02_12_0002
Create Date: 2026-02-13 00:01:00.000000

This migration adds:
  1. Agriculture & Agritech as 5th root industry
  2. 6 sub-vertical industries (crop farming, livestock, agritech, etc.)
  3. 20 core entities (companies, products, infrastructure, cooperatives)
  4. 70 signal contracts across API, RSS, scraper, and social sources

Signal focus areas:
  - Weather patterns & forecasting
  - Market pricing & volatility
  - Yield forecasting & production
  - Supply chain & logistics
  - Soil health & environmental
  - Regulatory & policy
  - Agritech innovation
  - Social sentiment
"""

import json
from collections.abc import Sequence
from typing import Union
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026_02_13_0001"
down_revision: Union[str, None] = "2026_02_12_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Pre-generate UUIDs for referential integrity
AGRI_ROOT_ID = uuid4()

# Sub-vertical IDs
CROP_FARMING_ID = uuid4()
LIVESTOCK_DAIRY_ID = uuid4()
AGRITECH_INNOVATION_ID = uuid4()
SUPPLY_CHAIN_LOGISTICS_ID = uuid4()
AGRI_INPUTS_ID = uuid4()
AQUACULTURE_FISHERIES_ID = uuid4()

# Entity IDs (for signal contract mapping)
ENTITY_FLOUR_MILLS = uuid4()
ENTITY_DANGOTE_SUGAR = uuid4()
ENTITY_OLAM_AGRI = uuid4()
ENTITY_WACOT_RICE = uuid4()
ENTITY_PRESCO = uuid4()
ENTITY_FARMCROWDY = uuid4()
ENTITY_THRIVEAGRIC = uuid4()
ENTITY_BABBAN_GONA = uuid4()
ENTITY_RICE_LOCAL = uuid4()
ENTITY_CASSAVA = uuid4()
ENTITY_PALM_OIL = uuid4()
ENTITY_COCOA_BEANS = uuid4()
ENTITY_MAIZE = uuid4()
ENTITY_YAM = uuid4()
ENTITY_TOMATOES = uuid4()
ENTITY_POULTRY = uuid4()
ENTITY_ABP = uuid4()
ENTITY_LCFE = uuid4()
ENTITY_FMARD = uuid4()
ENTITY_NALDA = uuid4()


def upgrade() -> None:
    """Add Agriculture domain with full seeding"""

    # =========================================================================
    # 1. ROOT INDUSTRY — Agriculture & Agritech
    # =========================================================================
    op.execute(
        sa.text(
            """
        INSERT INTO industries (id, name, slug, parent_id, description, metadata, created_at, updated_at)
        VALUES (
            :id,
            'Agriculture & Agritech',
            'agriculture-agritech',
            NULL,
            'Signal intelligence for agricultural production, agribusiness operations, supply chain optimization, and agritech innovation across crop farming, livestock, aquaculture, and forestry.',
            '{"domain": "agriculture", "launch_phase": "phase_3_extension", "signal_count": 70}',
            NOW(),
            NOW()
        )
        """
        ).bindparams(id=AGRI_ROOT_ID)
    )

    # =========================================================================
    # 2. SUB-VERTICALS (6 child industries)
    # =========================================================================
    sub_verticals = [
        {
            "id": CROP_FARMING_ID,
            "name": "Crop Farming & Horticulture",
            "slug": "crop-farming",
            "description": "Grains, vegetables, fruits, cash crops including cocoa, coffee, rubber, and rice production",
        },
        {
            "id": LIVESTOCK_DAIRY_ID,
            "name": "Livestock & Dairy",
            "slug": "livestock-dairy",
            "description": "Cattle, poultry, goat/sheep farming, and dairy production systems",
        },
        {
            "id": AGRITECH_INNOVATION_ID,
            "name": "Agritech & Innovation",
            "slug": "agritech-innovation",
            "description": "Precision agriculture, IoT sensors, drones, satellite monitoring, and fintech for farmers",
        },
        {
            "id": SUPPLY_CHAIN_LOGISTICS_ID,
            "name": "Agricultural Supply Chain & Logistics",
            "slug": "supply-chain-logistics",
            "description": "Post-harvest handling, cold storage, transportation, and commodity trading infrastructure",
        },
        {
            "id": AGRI_INPUTS_ID,
            "name": "Agricultural Inputs & Services",
            "slug": "agri-inputs",
            "description": "Seeds, fertilizers, pesticides, farm equipment, and veterinary services",
        },
        {
            "id": AQUACULTURE_FISHERIES_ID,
            "name": "Aquaculture & Fisheries",
            "slug": "aquaculture-fisheries",
            "description": "Fish farming, shrimp, tilapia cultivation, and coastal fisheries management",
        },
    ]

    for sv in sub_verticals:
        op.execute(
            sa.text(
                """
            INSERT INTO industries (id, name, slug, parent_id, description, metadata, created_at, updated_at)
            VALUES (:id, :name, :slug, :parent_id, :description, '{}', NOW(), NOW())
            """
            ).bindparams(
                id=sv["id"],
                name=sv["name"],
                slug=sv["slug"],
                parent_id=AGRI_ROOT_ID,
                description=sv["description"],
            )
        )

    # =========================================================================
    # 3. ENTITIES (20 core entities)
    # =========================================================================
    entities = [
        # Companies
        {
            "id": ENTITY_FLOUR_MILLS,
            "name": "Flour Mills of Nigeria",
            "entity_type": "company",
            "industry_id": AGRI_ROOT_ID,
            "aliases": '["FMN", "Flour Mills", "Golden Penny"]',
            "description": "Nigerian food and agro-allied conglomerate, major flour and rice producer",
        },
        {
            "id": ENTITY_DANGOTE_SUGAR,
            "name": "Dangote Sugar Refinery",
            "entity_type": "company",
            "industry_id": AGRI_ROOT_ID,
            "aliases": '["Dangote Sugar", "DSR"]',
            "description": "Largest sugar refinery in sub-Saharan Africa",
        },
        {
            "id": ENTITY_OLAM_AGRI,
            "name": "Olam Agri Nigeria",
            "entity_type": "company",
            "industry_id": CROP_FARMING_ID,
            "aliases": '["Olam", "Olam Nigeria"]',
            "description": "Global agri-business with Nigerian operations in grains, cocoa, and rice",
        },
        {
            "id": ENTITY_WACOT_RICE,
            "name": "Wacot Rice (Argungu)",
            "entity_type": "company",
            "industry_id": CROP_FARMING_ID,
            "aliases": '["Wacot Rice", "Argungu Rice Mill"]',
            "description": "Major rice milling operation in Kebbi State",
        },
        {
            "id": ENTITY_PRESCO,
            "name": "Presco Plc",
            "entity_type": "company",
            "industry_id": CROP_FARMING_ID,
            "aliases": '["Presco", "Presco Palm Oil"]',
            "description": "Leading palm oil production company in Nigeria",
        },
        {
            "id": ENTITY_FARMCROWDY,
            "name": "Farmcrowdy",
            "entity_type": "company",
            "industry_id": AGRITECH_INNOVATION_ID,
            "aliases": '["FarmCrowdy", "Farmcrowdy Digital"]',
            "description": "Agritech platform connecting farmers with sponsors and providing digital services",
        },
        {
            "id": ENTITY_THRIVEAGRIC,
            "name": "ThriveAgric",
            "entity_type": "company",
            "industry_id": AGRITECH_INNOVATION_ID,
            "aliases": '["Thrive Agric", "ThriveAgric Holdings"]',
            "description": "Agricultural financing and technology platform for smallholder farmers",
        },
        {
            "id": ENTITY_BABBAN_GONA,
            "name": "Babban Gona",
            "entity_type": "company",
            "industry_id": CROP_FARMING_ID,
            "aliases": '["Babban Gona Farmer Network"]',
            "description": "Farmer membership organization providing agricultural services",
        },
        # Products (Commodities)
        {
            "id": ENTITY_RICE_LOCAL,
            "name": "Rice (Local Nigerian)",
            "entity_type": "product",
            "industry_id": CROP_FARMING_ID,
            "aliases": '["Ofada Rice", "Abakaliki Rice", "Local Rice", "Nigerian Rice"]',
            "description": "Locally grown Nigerian rice varieties including Ofada and Abakaliki",
        },
        {
            "id": ENTITY_CASSAVA,
            "name": "Cassava",
            "entity_type": "product",
            "industry_id": CROP_FARMING_ID,
            "aliases": '["Cassava Flour", "Garri", "Cassava Tubers"]',
            "description": "Cassava root crop and processed products including flour and garri",
        },
        {
            "id": ENTITY_PALM_OIL,
            "name": "Palm Oil",
            "entity_type": "product",
            "industry_id": CROP_FARMING_ID,
            "aliases": '["Crude Palm Oil", "CPO", "Refined Palm Oil"]',
            "description": "Palm oil in crude and refined forms",
        },
        {
            "id": ENTITY_COCOA_BEANS,
            "name": "Cocoa Beans",
            "entity_type": "product",
            "industry_id": CROP_FARMING_ID,
            "aliases": '["Cocoa", "Nigerian Cocoa", "Export Cocoa"]',
            "description": "Nigerian cocoa beans for export and domestic processing",
        },
        {
            "id": ENTITY_MAIZE,
            "name": "Maize",
            "entity_type": "product",
            "industry_id": CROP_FARMING_ID,
            "aliases": '["Corn", "Yellow Maize", "White Maize"]',
            "description": "Maize grain in yellow and white varieties",
        },
        {
            "id": ENTITY_YAM,
            "name": "Yam",
            "entity_type": "product",
            "industry_id": CROP_FARMING_ID,
            "aliases": '["White Yam", "Yam Tubers"]',
            "description": "Yam tubers, staple root crop",
        },
        {
            "id": ENTITY_TOMATOES,
            "name": "Tomatoes",
            "entity_type": "product",
            "industry_id": CROP_FARMING_ID,
            "aliases": '["Fresh Tomatoes", "Tomato Paste"]',
            "description": "Fresh tomatoes and processed tomato products",
        },
        {
            "id": ENTITY_POULTRY,
            "name": "Poultry",
            "entity_type": "product",
            "industry_id": LIVESTOCK_DAIRY_ID,
            "aliases": '["Broilers", "Layers", "Chicken", "Eggs"]',
            "description": "Poultry products including broiler chickens, layers, and eggs",
        },
        # Infrastructure & Organizations
        {
            "id": ENTITY_ABP,
            "name": "Anchor Borrowers' Programme",
            "entity_type": "infrastructure",
            "industry_id": AGRI_ROOT_ID,
            "aliases": '["ABP", "CBN ABP", "Anchor Borrowers"]',
            "description": "Central Bank of Nigeria agricultural financing program",
        },
        {
            "id": ENTITY_LCFE,
            "name": "Lagos Commodities & Futures Exchange",
            "entity_type": "infrastructure",
            "industry_id": SUPPLY_CHAIN_LOGISTICS_ID,
            "aliases": '["LCFE", "Lagos Commodity Exchange"]',
            "description": "Commodity exchange for agricultural futures and spot trading",
        },
        {
            "id": ENTITY_FMARD,
            "name": "Federal Ministry of Agriculture & Rural Development",
            "entity_type": "infrastructure",
            "industry_id": AGRI_ROOT_ID,
            "aliases": '["FMARD", "Ministry of Agriculture", "Federal Agriculture Ministry"]',
            "description": "Nigerian federal ministry responsible for agricultural policy and development",
        },
        {
            "id": ENTITY_NALDA,
            "name": "National Agricultural Land Development Authority",
            "entity_type": "infrastructure",
            "industry_id": AGRI_ROOT_ID,
            "aliases": '["NALDA"]',
            "description": "Federal agency for agricultural land development and irrigation",
        },
    ]

    for entity in entities:
        op.execute(
            sa.text(
                """
            INSERT INTO entities (id, name, entity_type, industry_id, aliases, description, metadata, created_at, updated_at)
            VALUES (:id, :name, :entity_type, :industry_id, CAST(:aliases AS JSONB), :description, '{}', NOW(), NOW())
            """
            ).bindparams(**entity)
        )

    # =========================================================================
    # 4. SIGNAL CONTRACTS (70 contracts)
    # =========================================================================

    # Helper for creating contracts
    def create_contract(
        name: str,
        industry_id,
        source_url: str,
        source_type: str,
        schedule_tier: str,
        description: str,
        extraction_config: dict | None = None,
        entity_id=None,
        signal_type: str = "news",
    ):
        """Helper to insert a signal contract"""
        if extraction_config is None:
            extraction_config = {}

        extraction_config.setdefault("signal_type", signal_type)

        if signal_type == "social":
            platform = extraction_config.get("platform", "twitter")
            auth = extraction_config.get("auth") or {}
            if platform == "twitter":
                if not auth.get("bearer_token") and not auth.get("bearer_token_env"):
                    auth["bearer_token_env"] = "TWITTER_BEARER_TOKEN"
                extraction_config["auth"] = auth

        # Map schedule tier to cron
        cron_map = {
            "realtime": "*/15 * * * *",  # Every 15 minutes
            "standard": "0 * * * *",  # Every hour
            "slow": "0 */6 * * *",  # Every 6 hours
            "daily": "0 0 * * *",  # Daily at midnight
        }

        op.execute(
            sa.text(
                """
            INSERT INTO signal_contracts (
                id, name, description, industry_id, entity_id, source_url,
                source_type, refresh_cron, schedule_tier, extraction_config,
                is_active, status, failure_count, max_failures,
                created_at, updated_at
            )
            VALUES (
                :id, :name, :description, :industry_id, :entity_id, :source_url,
                :source_type, :refresh_cron, :schedule_tier, CAST(:extraction_config AS JSONB),
                true, 'active', 0, 3,
                NOW(), NOW()
            )
            """
            ).bindparams(
                id=uuid4(),
                name=name,
                description=description,
                industry_id=industry_id,
                entity_id=entity_id,
                source_url=source_url,
                source_type=source_type,
                refresh_cron=cron_map[schedule_tier],
                schedule_tier=schedule_tier,
                extraction_config=json.dumps(extraction_config),
            )
        )

    def create_weather_contract(*args, **kwargs):
        create_contract(*args, **kwargs, signal_type="weather")

    def create_market_contract(*args, **kwargs):
        create_contract(*args, **kwargs, signal_type="market")

    def create_production_contract(*args, **kwargs):
        create_contract(*args, **kwargs, signal_type="production")

    def create_logistics_contract(*args, **kwargs):
        create_contract(*args, **kwargs, signal_type="logistics")

    def create_environmental_contract(*args, **kwargs):
        create_contract(*args, **kwargs, signal_type="environmental")

    def create_regulatory_contract(*args, **kwargs):
        create_contract(*args, **kwargs, signal_type="regulatory")

    def create_technology_contract(*args, **kwargs):
        create_contract(*args, **kwargs, signal_type="technology")

    def create_social_contract(*args, **kwargs):
        create_contract(*args, **kwargs, signal_type="social")

    # Weather Patterns (10 contracts)
    create_weather_contract(
        "NIMET Daily Weather Forecast",
        AGRI_ROOT_ID,
        "https://nimet.gov.ng/api/forecast",
        "api",
        "realtime",
        "Nigerian Meteorological Agency daily weather forecasts for agricultural zones",
        {"api_key_env": "NIMET_API_KEY"},
    )

    create_weather_contract(
        "NIMET Rainfall Data (Historical)",
        AGRI_ROOT_ID,
        "https://nimet.gov.ng/api/rainfall",
        "api",
        "daily",
        "Historical rainfall data for crop planning and yield forecasting",
        {"api_key_env": "NIMET_API_KEY"},
    )

    create_weather_contract(
        "OpenWeather Nigeria Agricultural Zones",
        AGRI_ROOT_ID,
        "https://api.openweathermap.org/data/2.5/weather",
        "api",
        "standard",
        "OpenWeather API data for Nigerian agricultural zones",
        {"api_key_env": "OPENWEATHER_API_KEY"},
    )

    create_weather_contract(
        "Drought Risk Monitor (FAO)",
        AGRI_ROOT_ID,
        "https://fao.org/drought-monitor/nigeria",
        "scraper",
        "slow",
        "FAO drought risk assessments for Nigerian agricultural regions",
        {},
    )

    create_weather_contract(
        "Seasonal Weather Predictions (CBN Climate Desk)",
        AGRI_ROOT_ID,
        "https://cbn.gov.ng/climate/seasonal-forecast",
        "scraper",
        "daily",
        "Central Bank climate desk seasonal agricultural weather predictions",
        {},
    )

    create_weather_contract(
        "Flooding Alerts (NEMA)",
        AGRI_ROOT_ID,
        "https://nema.gov.ng/alerts/rss",
        "rss",
        "realtime",
        "National Emergency Management Agency flooding alerts affecting farmland",
        {"max_items": 50},
    )

    create_weather_contract(
        "Harmattan Impact on Agriculture",
        AGRI_ROOT_ID,
        "https://api.twitter.com/2/tweets/search/recent",
        "social",
        "standard",
        "Social media monitoring of harmattan weather impacts on crops",
        {"platform": "twitter", "params": {"query": "harmattan agriculture Nigeria"}},
    )

    create_weather_contract(
        "Sentinel-2 Satellite Vegetation Index",
        AGRI_ROOT_ID,
        "https://services.sentinel-hub.com/api/v1/process",
        "api",
        "slow",
        "Satellite NDVI data for crop health monitoring across Nigeria",
        {"api_key_env": "SENTINEL_HUB_KEY"},
    )

    create_weather_contract(
        "Temperature Extremes & Crop Stress",
        AGRI_ROOT_ID,
        "https://nigerian-meteorological.org/crop-stress",
        "scraper",
        "standard",
        "Temperature stress indicators for major crops",
        {},
    )

    create_weather_contract(
        "Irrigation Water Availability",
        AGRI_ROOT_ID,
        "https://irrigation-boards.gov.ng/water-levels",
        "scraper",
        "slow",
        "Water availability data from irrigation schemes",
        {},
    )

    # Market Pricing (10 contracts)
    create_market_contract(
        "Lagos Commodity Exchange Spot Prices",
        SUPPLY_CHAIN_LOGISTICS_ID,
        "https://lcfe.ng/api/prices",
        "api",
        "realtime",
        "Real-time spot prices for agricultural commodities on LCFE",
        {"api_key_env": "LCFE_API_KEY"},
        ENTITY_LCFE,
    )

    create_market_contract(
        "CBN Agricultural Commodity Price Index",
        AGRI_ROOT_ID,
        "https://cbn.gov.ng/rates/agric-prices",
        "scraper",
        "standard",
        "Central Bank agricultural commodity price tracking",
        {},
    )

    create_market_contract(
        "Open Market Rice Prices (Mile 12, Dawanau)",
        CROP_FARMING_ID,
        "https://mile12market.ng/prices",
        "scraper",
        "standard",
        "Open market rice prices from major Nigerian markets",
        {},
        ENTITY_RICE_LOCAL,
    )

    create_market_contract(
        "Palm Oil Export Prices (FOB)",
        CROP_FARMING_ID,
        "https://export-boards.ng/palm-oil",
        "scraper",
        "daily",
        "Free on board export prices for Nigerian palm oil",
        {},
        ENTITY_PALM_OIL,
    )

    create_market_contract(
        "Cocoa Spot Prices (Cocoa Board)",
        CROP_FARMING_ID,
        "https://cocoa-board.ng/api/prices",
        "api",
        "standard",
        "Nigerian Cocoa Board spot price data",
        {"api_key_env": "COCOA_BOARD_KEY"},
        ENTITY_COCOA_BEANS,
    )

    create_market_contract(
        "Maize Wholesale Prices (Northern States)",
        CROP_FARMING_ID,
        "https://kano-market-board.ng/maize-prices",
        "scraper",
        "standard",
        "Wholesale maize prices from northern agricultural zones",
        {},
        ENTITY_MAIZE,
    )

    create_market_contract(
        "Tomato Price Volatility (Kano Market)",
        CROP_FARMING_ID,
        "https://kano-agric-market.ng/tomatoes",
        "scraper",
        "standard",
        "Tomato price tracking from Kano wholesale market",
        {},
        ENTITY_TOMATOES,
    )

    create_market_contract(
        "Yam Festival Pricing Signals",
        CROP_FARMING_ID,
        "https://api.twitter.com/2/tweets/search/recent",
        "social",
        "standard",
        "Social sentiment and pricing discussions during yam harvest season",
        {"platform": "twitter", "params": {"query": "yam price Nigeria harvest"}},
        ENTITY_YAM,
    )

    create_market_contract(
        "Fertilizer Price Trends",
        AGRI_INPUTS_ID,
        "https://fertilizer-distributors.ng/prices",
        "scraper",
        "slow",
        "Fertilizer retail and wholesale price monitoring",
        {},
    )

    create_market_contract(
        "Commodity Futures (LCFE)",
        SUPPLY_CHAIN_LOGISTICS_ID,
        "https://lcfe.ng/api/futures",
        "api",
        "standard",
        "Agricultural commodity futures contracts and prices",
        {"api_key_env": "LCFE_API_KEY"},
        ENTITY_LCFE,
    )

    # Yield Forecasting (10 contracts)
    create_production_contract(
        "FMARD Crop Production Forecasts",
        AGRI_ROOT_ID,
        "https://fmard.gov.ng/forecasts",
        "scraper",
        "daily",
        "Federal Ministry of Agriculture crop production forecasts",
        {},
        ENTITY_FMARD,
    )

    create_production_contract(
        "NASC Seed Distribution Data",
        AGRI_INPUTS_ID,
        "https://nasc.gov.ng/distribution",
        "scraper",
        "slow",
        "National Agricultural Seed Council certified seed distribution data",
        {},
    )

    create_production_contract(
        "Fertilizer Application Rates (ABP)",
        AGRI_ROOT_ID,
        "https://abp-nigeria.ng/fertilizer-usage",
        "scraper",
        "slow",
        "Anchor Borrowers Programme fertilizer application tracking",
        {},
        ENTITY_ABP,
    )

    create_production_contract(
        "Harvest Calendar Tracker",
        CROP_FARMING_ID,
        "https://agric-extension.gov.ng/harvest-calendar",
        "scraper",
        "daily",
        "National harvest calendar and crop readiness indicators",
        {},
    )

    create_production_contract(
        "Planting Season Commencement Reports",
        CROP_FARMING_ID,
        "https://agricultural-states.gov.ng/rss/planting",
        "rss",
        "slow",
        "State agricultural bulletins on planting season start dates",
        {"max_items": 50},
    )

    create_production_contract(
        "Rice Mill Capacity Utilization",
        CROP_FARMING_ID,
        "https://rice-processors-ng.org/capacity",
        "scraper",
        "slow",
        "Rice milling capacity utilization rates nationwide",
        {},
        ENTITY_RICE_LOCAL,
    )

    create_production_contract(
        "NDVI Crop Health Monitoring (Satellite)",
        CROP_FARMING_ID,
        "https://services.sentinel-hub.com/api/v1/ndvi",
        "api",
        "slow",
        "Normalized Difference Vegetation Index for crop health assessment",
        {"api_key_env": "SENTINEL_HUB_KEY"},
    )

    create_production_contract(
        "Pest & Disease Outbreak Reports",
        CROP_FARMING_ID,
        "https://fmard.gov.ng/alerts/rss",
        "rss",
        "standard",
        "Plant health alerts and pest/disease outbreak notifications",
        {"max_items": 50},
        ENTITY_FMARD,
    )

    create_production_contract(
        "Irrigation Project Completion",
        AGRI_ROOT_ID,
        "https://water-resources.gov.ng/projects",
        "scraper",
        "daily",
        "Irrigation infrastructure project status and completion milestones",
        {},
    )

    create_production_contract(
        "Farm Mechanization Adoption Signals",
        AGRITECH_INNOVATION_ID,
        "https://api.twitter.com/2/tweets/search/recent",
        "social",
        "standard",
        "Social signals on farm mechanization and technology adoption",
        {
            "platform": "twitter",
            "params": {"query": "farm mechanization tractor Nigeria"},
        },
    )

    # Supply Chain & Logistics (10 contracts)
    create_logistics_contract(
        "Port Congestion (Apapa, Tin Can)",
        SUPPLY_CHAIN_LOGISTICS_ID,
        "https://ports.gov.ng/status",
        "scraper",
        "realtime",
        "Port congestion status affecting agricultural imports/exports",
        {},
    )

    create_logistics_contract(
        "Cold Storage Availability",
        SUPPLY_CHAIN_LOGISTICS_ID,
        "https://cold-chain-ng.com/capacity",
        "scraper",
        "standard",
        "Cold storage facility availability for perishable agricultural products",
        {},
    )

    create_logistics_contract(
        "Border Crossing Delays (Benin, Niger)",
        SUPPLY_CHAIN_LOGISTICS_ID,
        "https://customs.gov.ng/borders",
        "scraper",
        "standard",
        "Agricultural goods border crossing delays and clearance times",
        {},
    )

    create_logistics_contract(
        "Trucking Rates (Farm to Market)",
        SUPPLY_CHAIN_LOGISTICS_ID,
        "https://truckers-association-ng.org/rates",
        "scraper",
        "standard",
        "Agricultural commodity transportation rates across major routes",
        {},
    )

    create_logistics_contract(
        "Post-Harvest Loss Reports",
        SUPPLY_CHAIN_LOGISTICS_ID,
        "https://fmard.gov.ng/post-harvest/rss",
        "rss",
        "slow",
        "Post-harvest loss assessments and reduction initiatives",
        {"max_items": 50},
        ENTITY_FMARD,
    )

    create_logistics_contract(
        "Warehouse Receipt System Status",
        SUPPLY_CHAIN_LOGISTICS_ID,
        "https://afex.ng/api/warehouse",
        "api",
        "standard",
        "AFEX warehouse receipt system status and commodity stocks",
        {"api_key_env": "AFEX_API_KEY"},
    )

    create_logistics_contract(
        "Railway Freight Capacity (Agric Commodities)",
        SUPPLY_CHAIN_LOGISTICS_ID,
        "https://nrc.gov.ng/freight/agricultural",
        "scraper",
        "daily",
        "Nigerian Railway Corporation agricultural freight capacity and utilization",
        {},
    )

    create_logistics_contract(
        "Fuel Price Impact on Transportation",
        SUPPLY_CHAIN_LOGISTICS_ID,
        "https://pppra.gov.ng/prices",
        "scraper",
        "standard",
        "Fuel price changes affecting agricultural logistics costs",
        {},
    )

    create_logistics_contract(
        "Silo Capacity & Grain Storage",
        SUPPLY_CHAIN_LOGISTICS_ID,
        "https://strategic-grain-reserve.gov.ng/capacity",
        "scraper",
        "slow",
        "Strategic grain reserve silo capacity and stocks",
        {},
    )

    create_logistics_contract(
        "Export Documentation Delays",
        SUPPLY_CHAIN_LOGISTICS_ID,
        "https://nepc.gov.ng/export-status",
        "scraper",
        "standard",
        "Nigerian Export Promotion Council agricultural export documentation processing times",
        {},
    )

    # Soil Health (5 contracts)
    create_environmental_contract(
        "National Soil Survey Results",
        CROP_FARMING_ID,
        "https://soil-survey.gov.ng/reports",
        "scraper",
        "daily",
        "National soil survey data and soil health assessments",
        {},
    )

    create_environmental_contract(
        "Fertilizer Recommendations by Zone",
        AGRI_INPUTS_ID,
        "https://fepsan.ng/recommendations",
        "scraper",
        "slow",
        "Fertilizer Producers and Suppliers Association zone-specific recommendations",
        {},
    )

    create_environmental_contract(
        "Soil Degradation Risk Maps",
        CROP_FARMING_ID,
        "https://fao.org/soils/nigeria",
        "scraper",
        "slow",
        "FAO soil degradation risk assessments for Nigerian farmland",
        {},
    )

    create_environmental_contract(
        "pH & Nutrient Testing Services",
        CROP_FARMING_ID,
        "https://agric-extension.gov.ng/soil-testing",
        "scraper",
        "slow",
        "Soil testing services availability and results from extension services",
        {},
    )

    create_environmental_contract(
        "Organic Matter Content Trends",
        CROP_FARMING_ID,
        "https://research-institutes.gov.ng/soil/rss",
        "rss",
        "daily",
        "Research publications on soil organic matter trends",
        {"max_items": 50},
    )

    # Regulatory & Policy (10 contracts)
    create_regulatory_contract(
        "Agricultural Policy Updates (FMARD)",
        AGRI_ROOT_ID,
        "https://fmard.gov.ng/policies/rss",
        "rss",
        "daily",
        "Federal agricultural policy announcements and updates",
        {"max_items": 50},
        ENTITY_FMARD,
    )

    create_regulatory_contract(
        "Import/Export Ban Announcements",
        AGRI_ROOT_ID,
        "https://federal-gazette.gov.ng/agriculture",
        "scraper",
        "realtime",
        "Federal gazette agricultural import/export ban notifications",
        {},
    )

    create_regulatory_contract(
        "Anchor Borrowers' Programme Updates",
        AGRI_ROOT_ID,
        "https://cbn.gov.ng/abp/updates",
        "scraper",
        "slow",
        "CBN Anchor Borrowers Programme policy and operational updates",
        {},
        ENTITY_ABP,
    )

    create_regulatory_contract(
        "Land Tenure & Allocation Policies",
        AGRI_ROOT_ID,
        "https://lands.gov.ng/agricultural-allocation",
        "scraper",
        "daily",
        "Agricultural land tenure policies and allocation procedures",
        {},
    )

    create_regulatory_contract(
        "Subsidy Program Announcements",
        AGRI_ROOT_ID,
        "https://fmard.gov.ng/subsidies/rss",
        "rss",
        "standard",
        "Agricultural subsidy program announcements (inputs, equipment, etc.)",
        {"max_items": 50},
        ENTITY_FMARD,
    )

    create_regulatory_contract(
        "Agricultural Credit Schemes (BOA, BOI)",
        AGRI_ROOT_ID,
        "https://boa.gov.ng/credit-schemes",
        "scraper",
        "slow",
        "Bank of Agriculture and Bank of Industry agricultural credit offerings",
        {},
    )

    create_regulatory_contract(
        "Export Incentive Programs",
        AGRI_ROOT_ID,
        "https://nepc.gov.ng/incentives",
        "scraper",
        "slow",
        "Nigerian Export Promotion Council agricultural export incentives",
        {},
    )

    create_regulatory_contract(
        "Seed Certification Standards (NASC)",
        AGRI_INPUTS_ID,
        "https://nasc.gov.ng/standards",
        "scraper",
        "daily",
        "National Agricultural Seed Council certification standards and updates",
        {},
    )

    create_regulatory_contract(
        "Pesticide/Herbicide Approvals",
        AGRI_INPUTS_ID,
        "https://nafdac.gov.ng/agric-chemicals",
        "scraper",
        "slow",
        "NAFDAC agricultural chemical product approvals and warnings",
        {},
    )

    create_regulatory_contract(
        "State Agricultural Budgets",
        AGRI_ROOT_ID,
        "https://budget.gov.ng/state-agriculture",
        "scraper",
        "daily",
        "State government agricultural budget allocations and priorities",
        {},
    )

    # Agritech & Innovation (10 contracts)
    create_technology_contract(
        "Agritech Startup Funding Announcements",
        AGRITECH_INNOVATION_ID,
        "https://api.twitter.com/2/tweets/search/recent",
        "social",
        "standard",
        "Social monitoring of Nigerian agritech startup funding rounds",
        {"platform": "twitter", "params": {"query": "agritech funding Nigeria"}},
    )

    create_technology_contract(
        "Precision Agriculture Tool Adoption",
        AGRITECH_INNOVATION_ID,
        "https://agritech-companies.ng/blog",
        "scraper",
        "standard",
        "Agritech company blogs on precision agriculture adoption rates",
        {},
    )

    create_technology_contract(
        "Drone Usage in Nigerian Farms",
        AGRITECH_INNOVATION_ID,
        "https://api.twitter.com/2/tweets/search/recent",
        "social",
        "standard",
        "LinkedIn discussions on agricultural drone deployment",
        {"platform": "twitter", "params": {"query": "agriculture drones Nigeria"}},
    )

    create_technology_contract(
        "IoT Sensor Deployments",
        AGRITECH_INNOVATION_ID,
        "https://agritech-case-studies.org/iot",
        "scraper",
        "slow",
        "Case studies of IoT sensor networks in Nigerian agriculture",
        {},
    )

    create_technology_contract(
        "Mobile USSD Agric Services Usage",
        AGRITECH_INNOVATION_ID,
        "https://telco-reports.ng/ussd-agriculture",
        "scraper",
        "slow",
        "Telecom operator reports on agricultural USSD service adoption",
        {},
    )

    create_technology_contract(
        "Farmer Digital Literacy Programs",
        AGRITECH_INNOVATION_ID,
        "https://ngo-agricultural.org/rss",
        "rss",
        "slow",
        "NGO bulletins on farmer digital literacy and training programs",
        {"max_items": 50},
    )

    create_technology_contract(
        "Satellite Monitoring Service Launches",
        AGRITECH_INNOVATION_ID,
        "https://space-agency.gov.ng/agriculture/rss",
        "rss",
        "standard",
        "Space agency and agritech satellite monitoring service announcements",
        {"max_items": 50},
    )

    create_technology_contract(
        "Blockchain for Supply Chain (Pilots)",
        AGRITECH_INNOVATION_ID,
        "https://tech-news-ng.com/agritech",
        "scraper",
        "slow",
        "Technology news on blockchain pilot programs for agricultural supply chains",
        {},
    )

    create_technology_contract(
        "Agri-Fintech Loan Performance",
        AGRITECH_INNOVATION_ID,
        "https://farmcrowdy.com/reports",
        "scraper",
        "slow",
        "Farmcrowdy and ThriveAgric loan portfolio performance reports",
        {},
        ENTITY_FARMCROWDY,
    )

    create_technology_contract(
        "Weather Insurance Product Launches",
        AGRITECH_INNOVATION_ID,
        "https://insurance-companies-ng.org/rss",
        "rss",
        "standard",
        "Agricultural weather insurance product announcements",
        {"max_items": 50},
    )

    # Social & Market Sentiment (5 contracts)
    create_social_contract(
        "Farmer Association Social Sentiment",
        AGRI_ROOT_ID,
        "https://api.twitter.com/2/tweets/search/recent",
        "social",
        "standard",
        "All Farmers Association of Nigeria social media sentiment",
        {"platform": "twitter", "params": {"query": "All Farmers Association Nigeria"}},
    )

    create_social_contract(
        "Food Security Discussions (Twitter)",
        AGRI_ROOT_ID,
        "https://api.twitter.com/2/tweets/search/recent",
        "social",
        "standard",
        "Social media discussions on Nigerian food security",
        {"platform": "twitter", "params": {"query": "#FoodSecurity Nigeria"}},
    )

    create_social_contract(
        "Market Women Associations (Facebook)",
        SUPPLY_CHAIN_LOGISTICS_ID,
        "https://api.twitter.com/2/tweets/search/recent",
        "social",
        "standard",
        "Market women associations Facebook groups on commodity trading",
        {
            "platform": "twitter",
            "params": {"query": "market women association Nigeria"},
        },
    )

    create_social_contract(
        "Commodity Trader WhatsApp Groups",
        SUPPLY_CHAIN_LOGISTICS_ID,
        "https://api.twitter.com/2/tweets/search/recent",
        "social",
        "standard",
        "Public WhatsApp group monitoring for commodity trading signals",
        {
            "platform": "twitter",
            "params": {"query": "commodity traders Nigeria rice maize prices"},
        },
    )

    create_social_contract(
        "University Agricultural Research (Twitter)",
        CROP_FARMING_ID,
        "https://api.twitter.com/2/tweets/search/recent",
        "social",
        "standard",
        "Agricultural research institutions social media research announcements",
        {
            "platform": "twitter",
            "params": {
                "query": "(IAR_ABU OR UIAgric OR ABU_AGRIC) agriculture research"
            },
        },
    )

    # Migration complete:
    # - 1 root industry (Agriculture & Agritech)
    # - 6 sub-vertical industries
    # - 20 entities (companies, products, infrastructure)
    # - 70 signal contracts (10 weather, 10 market, 10 yield, etc.)


def downgrade() -> None:
    """Remove Agriculture domain"""

    # Delete in reverse dependency order
    op.execute(
        sa.text(
            """
        DELETE FROM signal_contracts WHERE industry_id IN (
            SELECT id FROM industries WHERE slug LIKE 'agriculture%' OR slug LIKE 'crop-%' OR slug LIKE 'livestock-%' OR slug LIKE 'agritech-%' OR slug LIKE 'supply-chain-%' OR slug LIKE 'agri-inputs' OR slug LIKE 'aquaculture-%'
        )
        """
        )
    )

    op.execute(
        sa.text(
            """
        DELETE FROM entities WHERE industry_id IN (
            SELECT id FROM industries WHERE slug LIKE 'agriculture%' OR slug LIKE 'crop-%' OR slug LIKE 'livestock-%' OR slug LIKE 'agritech-%' OR slug LIKE 'supply-chain-%' OR slug LIKE 'agri-inputs' OR slug LIKE 'aquaculture-%'
        )
        """
        )
    )

    op.execute(
        sa.text(
            """
        DELETE FROM industries WHERE slug LIKE 'agriculture%' OR slug LIKE 'crop-%' OR slug LIKE 'livestock-%' OR slug LIKE 'agritech-%' OR slug LIKE 'supply-chain-%' OR slug LIKE 'agri-inputs' OR slug LIKE 'aquaculture-%'
        """
        )
    )

    # Agriculture domain removed
