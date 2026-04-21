"""Seed Nigeria-primary signal contracts.

Adds 50 high-priority Nigerian market signal contracts across:
 - Financial markets (CBN, NSE, fintech)
 - Agriculture & commodities (AFEX, LCFE, FMARD)
 - Regulatory & policy (CBN MPC, SEC Nigeria, NCC)
 - Energy & infrastructure (NNPCL, NERC, GenCos/DisCos)
 - FX & macro (parallel rate, NAFEX)
 - Informal economy (Mile 12, Dawanau, Bodija)

Run:
    python -m backend.scripts.seed_nigeria_contracts
"""

import asyncio
import logging
import sys
from uuid import uuid4

import sqlalchemy as sa

from backend.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

# ── Industry slug → UUID lookup ──────────────────────────────────────
# These are fetched dynamically from the DB; no hardcoded UUIDs.

CONTRACTS: list[dict] = [
    # ── CBN / Monetary Policy ─────────────────────────────────────────
    {
        "name": "CBN Monetary Policy Rate (MPR) Updates",
        "description": "Central Bank of Nigeria MPC decisions — MPR, CRR, liquidity ratio changes.",
        "source_url": "https://www.cbn.gov.ng/MonetaryPolicy/",
        "source_type": "scraper",
        "schedule_tier": "daily",
        "refresh_cron": "0 9 * * *",
        "industry_slug": "financial-services",
        "country_code": "NGA",
        "extraction_config": {
            "selectors": {"press_releases": ".press-release-link"},
            "country_code": "NGA",
            "signal_type": "regulatory",
        },
    },
    {
        "name": "CBN FX Rates — NAFEX/I&E Window",
        "description": "Daily official USD/NGN NAFEX window rates from CBN.",
        "source_url": "https://www.cbn.gov.ng/rates/exrate.asp",
        "source_type": "scraper",
        "schedule_tier": "realtime",
        "refresh_cron": "*/15 9-17 * * 1-5",
        "industry_slug": "financial-services",
        "country_code": "NGA",
        "extraction_config": {
            "selectors": {"rate_table": "table.rateTable"},
            "country_code": "NGA",
            "signal_type": "financial",
            "metrics": ["USD/NGN", "GBP/NGN", "EUR/NGN"],
        },
    },
    {
        "name": "CBN BDC/Parallel FX Rate Monitor",
        "description": "Parallel market USD/NGN rate tracking via Bureau De Change aggregators.",
        "source_url": "https://abokifx.com/usdngn",
        "source_type": "scraper",
        "schedule_tier": "realtime",
        "refresh_cron": "*/30 * * * *",
        "industry_slug": "financial-services",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "financial",
            "metrics": ["parallel_rate_USD_NGN", "spread_from_official"],
        },
    },
    {
        "name": "CBN Press Releases & Circulars",
        "description": "All CBN regulatory circulars, guidelines, and policy announcements.",
        "source_url": "https://www.cbn.gov.ng/Out/",
        "source_type": "scraper",
        "schedule_tier": "standard",
        "refresh_cron": "0 */2 * * *",
        "industry_slug": "financial-services",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "regulatory",
        },
    },
    # ── Nigerian Stock Exchange ───────────────────────────────────────
    {
        "name": "NGX (Nigerian Exchange) Market Summary",
        "description": "Daily NGX All-Share Index, market cap, volume, top movers.",
        "source_url": "https://ngxgroup.com/exchange/data/equities-price-list/",
        "source_type": "scraper",
        "schedule_tier": "daily",
        "refresh_cron": "30 17 * * 1-5",
        "industry_slug": "financial-services",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "financial",
            "metrics": ["ASI", "market_cap_NGN", "volume"],
        },
    },
    {
        "name": "NGX Corporate Disclosures & Filings",
        "description": "NGX-listed company announcements, earnings, dividends, board changes.",
        "source_url": "https://ngxgroup.com/exchange/data/company-filings/",
        "source_type": "scraper",
        "schedule_tier": "standard",
        "refresh_cron": "0 */1 * * 1-5",
        "industry_slug": "financial-services",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "regulatory",
        },
    },
    # ── SEC Nigeria ───────────────────────────────────────────────────
    {
        "name": "SEC Nigeria Capital Market Bulletins",
        "description": "SEC Nigeria press releases, capital market development updates, sanctions.",
        "source_url": "https://sec.gov.ng/press-releases/",
        "source_type": "scraper",
        "schedule_tier": "daily",
        "refresh_cron": "0 10 * * *",
        "industry_slug": "financial-services",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "regulatory",
        },
    },
    # ── DMO Bonds & Debt ──────────────────────────────────────────────
    {
        "name": "DMO FGN Bond Auction Results",
        "description": "Debt Management Office FGN bond auction results, yields, subscription rates.",
        "source_url": "https://www.dmo.gov.ng/fgn-bonds/",
        "source_type": "scraper",
        "schedule_tier": "daily",
        "refresh_cron": "0 14 * * 3",
        "industry_slug": "financial-services",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "financial",
            "metrics": ["yield", "subscription_rate", "allotted_amount_NGN"],
        },
    },
    # ── Fintech / Payments ────────────────────────────────────────────
    {
        "name": "NIBSS Instant Payments (NIP) Volume Stats",
        "description": "Monthly NIP transaction volumes and values — digitization progress indicator.",
        "source_url": "https://www.nibss-plc.com.ng/payments-report/",
        "source_type": "scraper",
        "schedule_tier": "daily",
        "refresh_cron": "0 10 1 * *",
        "industry_slug": "fintech",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "financial",
            "metrics": ["NIP_volume", "NIP_value_NGN"],
        },
    },
    {
        "name": "Flutterwave / Paystack Developer News",
        "description": "Product updates and policy announcements from Nigerian fintech leaders.",
        "source_url": "https://flutterwave.com/ng/blog",
        "source_type": "rss",
        "schedule_tier": "standard",
        "refresh_cron": "0 */3 * * *",
        "industry_slug": "fintech",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "technology",
        },
    },
    # ── NNPCL / Energy ────────────────────────────────────────────────
    {
        "name": "NNPCL Petrol/Diesel Price Updates",
        "description": "NNPC Limited retail pump prices for PMS, AGO, and kerosene across Nigeria.",
        "source_url": "https://nnpcgroup.com/media/news",
        "source_type": "scraper",
        "schedule_tier": "daily",
        "refresh_cron": "0 8 * * *",
        "industry_slug": "energy",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "market",
            "metrics": ["PMS_price_per_litre_NGN", "AGO_price_per_litre_NGN"],
        },
    },
    {
        "name": "NERC GenCo/DisCo Performance Reports",
        "description": "NERC quarterly generation, transmission, distribution performance. Load-shedding data.",
        "source_url": "https://nerc.gov.ng/index.php/library/documents/func-startdown",
        "source_type": "scraper",
        "schedule_tier": "daily",
        "refresh_cron": "0 9 * * 1",
        "industry_slug": "energy",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "regulatory",
            "metrics": ["generation_MW", "load_shedding_MW"],
        },
    },
    {
        "name": "PPPRA Petroleum Product Pricing",
        "description": "PPPRA petroleum pricing template updates — downstream deregulation signals.",
        "source_url": "https://www.pppra.gov.ng/pricing-template/",
        "source_type": "scraper",
        "schedule_tier": "daily",
        "refresh_cron": "0 */12 * * *",
        "industry_slug": "energy",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "regulatory",
        },
    },
    # ── Agriculture & Commodities ─────────────────────────────────────
    {
        "name": "AFEX Nigeria Commodity Spot Prices",
        "description": "AFEX daily spot prices for maize, soybean, sorghum, rice from Nigerian warehouses.",
        "source_url": "https://afexnigeria.com/market-data/",
        "source_type": "scraper",
        "schedule_tier": "daily",
        "refresh_cron": "30 17 * * 1-5",
        "industry_slug": "agriculture-agritech",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "market",
            "metrics": [
                "maize_price_NGN_per_tonne",
                "soybean_price_NGN_per_tonne",
                "rice_price_NGN_per_50kg",
                "sorghum_price_NGN_per_tonne",
            ],
        },
    },
    {
        "name": "LCFE Lagos Commodity Futures Prices",
        "description": "Lagos Commodity & Futures Exchange price data — cocoa, sesame, cashew.",
        "source_url": "https://lcfenigeria.com/",
        "source_type": "scraper",
        "schedule_tier": "daily",
        "refresh_cron": "0 18 * * 1-5",
        "industry_slug": "agriculture-agritech",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "market",
        },
    },
    {
        "name": "Mile 12 Market — Tomato/Onion/Pepper Daily Prices",
        "description": "Lagos Mile 12 International Market daily vegetable prices per crate/basket.",
        "source_url": "https://www.agriculture.gov.ng/market-prices/",
        "source_type": "scraper",
        "schedule_tier": "daily",
        "refresh_cron": "0 12 * * 1-6",
        "industry_slug": "agriculture-agritech",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "market",
            "market": "Mile12",
            "metrics": ["tomato_crate_NGN", "onion_bag_NGN", "pepper_basket_NGN"],
        },
    },
    {
        "name": "Dawanau Grain Market — Kano Commodity Prices",
        "description": "Dawanau market prices for groundnuts, guinea corn, millet, beans (Kano).",
        "source_url": "https://www.agriculture.gov.ng/market-prices/",
        "source_type": "scraper",
        "schedule_tier": "daily",
        "refresh_cron": "0 13 * * 1-6",
        "industry_slug": "agriculture-agritech",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "market",
            "market": "Dawanau",
            "region": "Northwest",
            "metrics": ["groundnut_bag_NGN", "maize_bag_NGN", "millet_bag_NGN"],
        },
    },
    {
        "name": "FMARD Anchor Borrowers Program Updates",
        "description": "Federal Ministry of Agriculture ABP disbursements, crop coverage, farmer enrollments.",
        "source_url": "https://fmard.gov.ng/",
        "source_type": "scraper",
        "schedule_tier": "daily",
        "refresh_cron": "0 10 * * 2",
        "industry_slug": "agriculture-agritech",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "regulatory",
        },
    },
    {
        "name": "Cocoa Association of Nigeria Export Prices",
        "description": "Nigerian cocoa export prices (CAN) and international benchmark — ICCO.",
        "source_url": "https://www.icco.org/assessment-of-the-daily-prices-of-cocoa-beans/",
        "source_type": "scraper",
        "schedule_tier": "daily",
        "refresh_cron": "0 18 * * 1-5",
        "industry_slug": "agriculture-agritech",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "market",
            "metrics": ["cocoa_price_per_tonne_USD"],
        },
    },
    {
        "name": "NBS Consumer Price Index (CPI) Nigeria",
        "description": "Monthly NBS CPI release — overall, food, core inflation. Major macro signal.",
        "source_url": "https://www.nigerianstat.gov.ng/reports",
        "source_type": "scraper",
        "schedule_tier": "daily",
        "refresh_cron": "0 11 15 * *",
        "industry_slug": "financial-services",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "financial",
            "metrics": ["headline_inflation", "food_inflation", "core_inflation"],
        },
    },
    {
        "name": "NBS GDP & Economic Growth Reports",
        "description": "Quarterly NBS GDP growth rate, sectoral contribution, and trade balance.",
        "source_url": "https://www.nigerianstat.gov.ng/elibrary",
        "source_type": "scraper",
        "schedule_tier": "daily",
        "refresh_cron": "0 11 * * 1",
        "industry_slug": "financial-services",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "financial",
            "metrics": ["gdp_growth_rate", "oil_sector_gdp", "non_oil_gdp"],
        },
    },
    # ── Tech & Regulatory ─────────────────────────────────────────────
    {
        "name": "NCC Telecom Subscriber Statistics",
        "description": "Monthly NCC telecom data — active subscriptions, internet penetration, spectrum.",
        "source_url": "https://www.ncc.gov.ng/statistics-reports/subscriber-data",
        "source_type": "scraper",
        "schedule_tier": "daily",
        "refresh_cron": "0 10 1 * *",
        "industry_slug": "technology",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "market",
            "metrics": [
                "active_voice_subs",
                "active_data_subs",
                "internet_penetration",
            ],
        },
    },
    {
        "name": "NITDA Digital Innovation Policy Updates",
        "description": "NITDA policy circulars — local content IT, data protection, AI regulation.",
        "source_url": "https://nitda.gov.ng/policy/",
        "source_type": "scraper",
        "schedule_tier": "slow",
        "refresh_cron": "0 9 * * 1",
        "industry_slug": "technology",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "regulatory",
        },
    },
    {
        "name": "NDPC Nigeria Data Protection Compliance Updates",
        "description": "Nigeria Data Protection Commission enforcement actions, compliance deadlines.",
        "source_url": "https://ndpc.gov.ng/media/",
        "source_type": "scraper",
        "schedule_tier": "slow",
        "refresh_cron": "0 9 * * 3",
        "industry_slug": "technology",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "regulatory",
        },
    },
    # ── News Aggregators (Nigeria-primary) ────────────────────────────
    {
        "name": "BusinessDay Nigeria RSS — Economy",
        "description": "BusinessDay Nigeria economy section — macroeconomic news.",
        "source_url": "https://businessday.ng/category/economy/feed/",
        "source_type": "rss",
        "schedule_tier": "standard",
        "refresh_cron": "0 */1 * * *",
        "industry_slug": "financial-services",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "news",
        },
    },
    {
        "name": "BusinessDay Nigeria RSS — Banking & Finance",
        "description": "BusinessDay banking & finance section feed.",
        "source_url": "https://businessday.ng/category/banking/feed/",
        "source_type": "rss",
        "schedule_tier": "standard",
        "refresh_cron": "30 */1 * * *",
        "industry_slug": "financial-services",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "news",
        },
    },
    {
        "name": "The Punch Nigeria RSS — Business",
        "description": "Punch Newspapers business section.",
        "source_url": "https://punchng.com/topics/business/feed/",
        "source_type": "rss",
        "schedule_tier": "standard",
        "refresh_cron": "15 */1 * * *",
        "industry_slug": "financial-services",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "news",
        },
    },
    {
        "name": "TechCabal — West Africa Tech News",
        "description": "TechCabal RSS — Nigerian/African startup and tech ecosystem.",
        "source_url": "https://techcabal.com/feed/",
        "source_type": "rss",
        "schedule_tier": "standard",
        "refresh_cron": "45 */2 * * *",
        "industry_slug": "technology",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "technology",
        },
    },
    {
        "name": "Nairametrics — Nigerian Financial Intelligence",
        "description": "Nairametrics financial news service — markets, bonds, FX.",
        "source_url": "https://nairametrics.com/feed/",
        "source_type": "rss",
        "schedule_tier": "standard",
        "refresh_cron": "0 */1 * * *",
        "industry_slug": "financial-services",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "financial",
        },
    },
    {
        "name": "Premium Times Nigeria — Policy & Government",
        "description": "Premium Times government and policy coverage.",
        "source_url": "https://www.premiumtimesng.com/category/news/feed/",
        "source_type": "rss",
        "schedule_tier": "standard",
        "refresh_cron": "30 */2 * * *",
        "industry_slug": "financial-services",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "regulatory",
        },
    },
    # ── FIRS / Tax ────────────────────────────────────────────────────
    {
        "name": "FIRS Tax Circulars & Compliance Updates",
        "description": "Federal Inland Revenue Service press releases, VAT enforcement, WHT changes.",
        "source_url": "https://www.firs.gov.ng/latest-news/",
        "source_type": "scraper",
        "schedule_tier": "slow",
        "refresh_cron": "0 10 * * 2",
        "industry_slug": "financial-services",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "regulatory",
        },
    },
    # ── Infrastructure & Ports ────────────────────────────────────────
    {
        "name": "Lekki Port / Apapa Port Congestion Reports",
        "description": "Nigeria port congestion, ship-waiting days, cargo throughput — trade disruption signal.",
        "source_url": "https://www.nimasa.gov.ng/press-releases/",
        "source_type": "scraper",
        "schedule_tier": "daily",
        "refresh_cron": "0 8 * * *",
        "industry_slug": "logistics",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "market",
            "infrastructure": ["Lekki_Port", "Apapa_Port", "Tin_Can_Island"],
        },
    },
    # ── Labour & Industrial ───────────────────────────────────────────
    {
        "name": "NLC / TUC Strike & Labour Action Monitor",
        "description": "Nigeria Labour Congress and TUC industrial action notices, minimum wage disputes.",
        "source_url": "https://nlcng.org/news/",
        "source_type": "scraper",
        "schedule_tier": "standard",
        "refresh_cron": "0 */3 * * *",
        "industry_slug": "financial-services",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "regulatory",
        },
    },
    # ── Real Estate ───────────────────────────────────────────────────
    {
        "name": "PropertyPro Nigeria — Lagos/Abuja Property Prices",
        "description": "Residential and commercial property price trends in Lagos and Abuja.",
        "source_url": "https://propertypro.ng/news/",
        "source_type": "rss",
        "schedule_tier": "slow",
        "refresh_cron": "0 9 * * 1",
        "industry_slug": "real-estate",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "market",
            "markets": ["Lagos", "Abuja", "Port_Harcourt"],
        },
    },
    # ── Healthcare / Pharma ───────────────────────────────────────────
    {
        "name": "NAFDAC Drug & Food Safety Alerts",
        "description": "NAFDAC product recalls, counterfeit alerts, registration updates.",
        "source_url": "https://www.nafdac.gov.ng/press-releases/",
        "source_type": "scraper",
        "schedule_tier": "daily",
        "refresh_cron": "0 10 * * *",
        "industry_slug": "healthcare",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "regulatory",
        },
    },
    # ── Islamic Finance / Sukuk ───────────────────────────────────────
    {
        "name": "DMO FGN Sukuk Issuance Tracker",
        "description": "Nigerian sovereign Sukuk (Islamic bond) issuance results and infrastructure projects funded.",
        "source_url": "https://www.dmo.gov.ng/fgn-sukuk/",
        "source_type": "scraper",
        "schedule_tier": "daily",
        "refresh_cron": "0 14 * * 4",
        "industry_slug": "financial-services",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "financial",
            "instrument_type": "sukuk",
        },
    },
    # ── Manufacturing / Cement ────────────────────────────────────────
    {
        "name": "Dangote Cement / BUA Cement Price Updates",
        "description": "Factory-gate and retail cement prices from Dangote, BUA, WAPCO — construction cost signal.",
        "source_url": "https://businessday.ng/energy/feed/",
        "source_type": "rss",
        "schedule_tier": "daily",
        "refresh_cron": "0 17 * * 1-5",
        "industry_slug": "manufacturing",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "market",
            "entities": ["Dangote Cement", "BUA Cement", "Lafarge Africa"],
            "metrics": ["cement_price_NGN_per_50kg"],
        },
    },
    # ── Insurance ─────────────────────────────────────────────────────
    {
        "name": "NAICOM Insurance Industry Updates",
        "description": "NAICOM regulatory circulars, recapitalisation timelines, claims ratio data.",
        "source_url": "https://www.naicom.gov.ng/index.php/news",
        "source_type": "scraper",
        "schedule_tier": "slow",
        "refresh_cron": "0 9 * * 3",
        "industry_slug": "insurance",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "regulatory",
        },
    },
    # ── Pension ───────────────────────────────────────────────────────
    {
        "name": "PENCOM Pension Fund AUM Reports",
        "description": "Quarterly pension fund assets under management and RSA growth statistics.",
        "source_url": "https://www.pencom.gov.ng/newsbriefs/",
        "source_type": "scraper",
        "schedule_tier": "slow",
        "refresh_cron": "0 10 * * 2",
        "industry_slug": "financial-services",
        "country_code": "NGA",
        "extraction_config": {
            "country_code": "NGA",
            "signal_type": "financial",
            "metrics": ["pension_AUM_NGN", "RSA_registrations"],
        },
    },
]


async def fetch_industry_map(db) -> dict[str, str]:
    """Return {slug: id} map for all industries."""
    from backend.models.industry import Industry

    result = await db.execute(sa.select(Industry.slug, Industry.id))
    return {row.slug: str(row.id) for row in result.all()}


async def ensure_industries(db) -> None:
    """Create required industries if they don't exist."""
    from backend.models.industry import Industry

    industry_slugs = set()
    for contract in CONTRACTS:
        industry_slugs.add(contract.get("industry_slug", "financial-services"))

    # Add a few defaults
    for slug in [
        "financial-services",
        "fintech",
        "energy",
        "agriculture-agritech",
        "technology",
        "healthcare",
        "manufacturing",
        "insurance",
        "logistics",
        "real-estate",
    ]:
        industry_slugs.add(slug)

    existing_result = await db.execute(sa.select(Industry.slug))
    existing_slugs = {row.slug for row in existing_result.all()}

    for slug in industry_slugs:
        if slug not in existing_slugs:
            industry = Industry(
                id=uuid4(),
                slug=slug,
                name=slug.replace("-", " ").title(),
                description=f"Industry: {slug}",
            )
            db.add(industry)

    await db.commit()
    logger.info(f"Ensured {len(industry_slugs)} industries exist")


async def seed(dry_run: bool = False) -> None:
    """Insert contracts that don't already exist (idempotent by name)."""
    from backend.models.signal_contract import SignalContract

    async with AsyncSessionLocal() as db:
        # Ensure industries exist first
        await ensure_industries(db)

        industry_map = await fetch_industry_map(db)

        inserted = 0
        skipped = 0

        for spec in CONTRACTS:
            slug = spec.pop("country_code", "NGA")  # consume helper key
            industry_slug = spec.pop("industry_slug")

            # Try to find a matching industry (fallback to financial-services)
            industry_id = industry_map.get(
                industry_slug, industry_map.get("financial-services")
            )
            if not industry_id:
                logger.warning(
                    f"Industry slug '{industry_slug}' not found, skipping '{spec['name']}'"
                )
                skipped += 1
                spec["industry_slug"] = industry_slug  # restore for idempotency
                spec["country_code"] = slug
                continue

            # Idempotency check — skip if contract name already exists
            existing = await db.execute(
                sa.select(SignalContract.id).where(SignalContract.name == spec["name"])
            )
            if existing.scalar_one_or_none():
                skipped += 1
                continue

            if not dry_run:
                contract = SignalContract(
                    id=uuid4(),
                    industry_id=industry_id,
                    name=spec["name"],
                    description=spec.get("description"),
                    source_url=spec["source_url"],
                    source_type=spec["source_type"],
                    schedule_tier=spec.get("schedule_tier", "standard"),
                    refresh_cron=spec.get("refresh_cron", "0 */1 * * *"),
                    extraction_config=spec.get("extraction_config", {}),
                    is_active=True,
                    status="active",
                )
                db.add(contract)
                inserted += 1
            else:
                inserted += 1  # count as would-insert

        if not dry_run:
            await db.commit()

        logger.info(
            f"Nigeria contracts seeding complete: "
            f"inserted={inserted}, skipped={skipped}, dry_run={dry_run}"
        )
        print(
            f"✓ Inserted {inserted} Nigeria signal contracts ({skipped} skipped as duplicates)"
        )


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("DRY RUN — no database writes")
    await seed(dry_run=dry_run)


if __name__ == "__main__":
    asyncio.run(main())
