"""Bootstrap the minimum viable catalog for real product usage.

This module seeds global industries and marketplace templates so fresh
environments do not boot into an empty shell. The data is intentionally
curated and idempotent: we only create missing records and do not overwrite
existing tenant or admin edits.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.models.industry import Industry
from backend.models.signal_template import SignalTemplate
from backend.signals.provider_presets import DEFAULT_NEWSAPI_URL, DEFAULT_X_SEARCH_URL

logger = logging.getLogger(__name__)


CORE_INDUSTRIES: Sequence[dict[str, str]] = (
    {
        "slug": "financial-services",
        "name": "Financial Services",
        "description": "Banking, payments, capital markets, and macro-financial monitoring.",
    },
    {
        "slug": "fintech",
        "name": "Fintech",
        "description": "Digital payments, embedded finance, lending, and financial infrastructure.",
    },
    {
        "slug": "agriculture-agritech",
        "name": "Agriculture & Agritech",
        "description": "Agricultural production, pricing, commodity flows, and agritech innovation.",
    },
    {
        "slug": "energy",
        "name": "Energy",
        "description": "Power, oil and gas, renewables, and energy policy developments.",
    },
    {
        "slug": "technology",
        "name": "Technology",
        "description": "Cloud, AI, telecoms, startups, and digital infrastructure.",
    },
    {
        "slug": "healthcare",
        "name": "Healthcare",
        "description": "Healthcare delivery, pharmaceuticals, public health, and medical supply chains.",
    },
    {
        "slug": "logistics",
        "name": "Logistics",
        "description": "Ports, trade corridors, warehousing, fulfilment, and transportation.",
    },
    {
        "slug": "real-estate",
        "name": "Real Estate",
        "description": "Property markets, construction, housing policy, and commercial development.",
    },
)


def _marketplace_specs() -> list[dict[str, object]]:
    settings = get_settings()
    ngx_url = settings.ngx_market_data_base_url or "https://ngxpulse.ng/api/ngxdata/market"

    return [
        {
            "slug": "nigeria-fintech-watch",
            "name": "Nigeria Fintech Watch",
            "short_description": "Managed news and intelligence watch for Nigerian fintech activity.",
            "description": (
                "Tracks funding, product launches, regulation, partnerships, and market-moving"
                " developments across Nigerian fintech."
            ),
            "industry_slug": "fintech",
            "signal_type": "technology",
            "primary_country": "NGA",
            "regions": ["Nigeria", "West Africa"],
            "tags": ["fintech", "payments", "banking", "Nigeria"],
            "source_type": "api",
            "source_url": DEFAULT_NEWSAPI_URL,
            "schedule_tier": "standard",
            "preview_signal_count": 18,
            "is_featured": True,
            "extraction_config": {
                "provider": "newsapi",
                "nl_query": "Nigeria fintech funding payments banking regulation",
                "params": {"q": "Nigeria fintech OR payments OR digital banking"},
                "managed_source": True,
            },
        },
        {
            "slug": "nigeria-regulatory-watch",
            "name": "Nigeria Regulatory Watch",
            "short_description": "Managed policy and regulatory monitoring for critical market changes.",
            "description": (
                "Tracks policy updates, regulator actions, enforcement changes, and public notices"
                " affecting monitored sectors in Nigeria."
            ),
            "industry_slug": "financial-services",
            "signal_type": "regulatory",
            "primary_country": "NGA",
            "regions": ["Nigeria", "ECOWAS"],
            "tags": ["regulation", "policy", "CBN", "SEC", "Nigeria"],
            "source_type": "api",
            "source_url": DEFAULT_NEWSAPI_URL,
            "schedule_tier": "standard",
            "preview_signal_count": 14,
            "is_featured": True,
            "extraction_config": {
                "provider": "newsapi",
                "nl_query": "Nigeria regulation policy SEC CBN compliance",
                "params": {"q": "Nigeria regulation OR policy OR central bank OR SEC"},
                "managed_source": True,
            },
        },
        {
            "slug": "ngx-market-overview",
            "name": "NGX Market Overview",
            "short_description": "Exchange-level market movements from NGX Pulse.",
            "description": (
                "Tracks NGX market summary movements so teams can monitor broad exchange activity"
                " without configuring exchange feeds themselves."
            ),
            "industry_slug": "financial-services",
            "signal_type": "market",
            "primary_country": "NGA",
            "regions": ["Nigeria"],
            "tags": ["NGX", "equities", "market", "prices"],
            "source_type": "api",
            "source_url": ngx_url,
            "schedule_tier": "standard",
            "preview_signal_count": 24,
            "is_featured": True,
            "extraction_config": {
                "provider": "ngx_market_data",
                "pulse_endpoint": "market",
                "managed_source": True,
            },
        },
        {
            "slug": "nigeria-agri-price-watch",
            "name": "Nigeria Agri Price Watch",
            "short_description": "Agricultural pricing and supply-chain developments across Nigeria.",
            "description": (
                "Tracks commodity pricing, harvest cycles, supply constraints, and agritech activity"
                " relevant to agricultural operators and investors."
            ),
            "industry_slug": "agriculture-agritech",
            "signal_type": "market",
            "primary_country": "NGA",
            "regions": ["Nigeria", "West Africa"],
            "tags": ["agriculture", "commodity prices", "maize", "rice"],
            "source_type": "api",
            "source_url": DEFAULT_NEWSAPI_URL,
            "schedule_tier": "daily",
            "preview_signal_count": 12,
            "is_featured": True,
            "extraction_config": {
                "provider": "newsapi",
                "nl_query": "Nigeria agriculture commodity prices maize sorghum rice",
                "params": {"q": "Nigeria agriculture OR maize OR rice OR commodity prices"},
                "managed_source": True,
            },
        },
        {
            "slug": "nigeria-energy-transition-watch",
            "name": "Nigeria Energy Transition Watch",
            "short_description": "Energy market, policy, and infrastructure intelligence.",
            "description": (
                "Tracks grid changes, generation policy, fuel-market shifts, and energy investment"
                " developments across the Nigerian energy landscape."
            ),
            "industry_slug": "energy",
            "signal_type": "news",
            "primary_country": "NGA",
            "regions": ["Nigeria", "West Africa"],
            "tags": ["energy", "power", "renewables", "oil and gas"],
            "source_type": "api",
            "source_url": DEFAULT_NEWSAPI_URL,
            "schedule_tier": "daily",
            "preview_signal_count": 10,
            "is_featured": False,
            "extraction_config": {
                "provider": "newsapi",
                "nl_query": "Nigeria energy power grid renewables oil gas",
                "params": {"q": "Nigeria energy OR power OR grid OR renewables OR oil and gas"},
                "managed_source": True,
            },
        },
        {
            "slug": "west-africa-tech-pulse",
            "name": "West Africa Tech Pulse",
            "short_description": "Regional technology and startup developments in one managed feed.",
            "description": (
                "Tracks startup launches, fundraising, platform changes, and market expansion across"
                " West African technology ecosystems."
            ),
            "industry_slug": "technology",
            "signal_type": "technology",
            "primary_country": "NGA",
            "regions": ["West Africa", "ECOWAS"],
            "tags": ["technology", "startup", "AI", "West Africa"],
            "source_type": "api",
            "source_url": DEFAULT_NEWSAPI_URL,
            "schedule_tier": "standard",
            "preview_signal_count": 16,
            "is_featured": False,
            "extraction_config": {
                "provider": "newsapi",
                "nl_query": "West Africa technology startups AI telecoms",
                "params": {"q": "West Africa technology OR startups OR AI OR telecoms"},
                "managed_source": True,
            },
        },
        {
            "slug": "nigeria-real-estate-watch",
            "name": "Nigeria Real Estate Watch",
            "short_description": "Property and construction intelligence for the Nigerian market.",
            "description": (
                "Tracks property-market sentiment, construction activity, housing policy, and"
                " commercial real-estate shifts in Nigeria."
            ),
            "industry_slug": "real-estate",
            "signal_type": "market",
            "primary_country": "NGA",
            "regions": ["Nigeria"],
            "tags": ["real estate", "construction", "housing", "property"],
            "source_type": "api",
            "source_url": DEFAULT_NEWSAPI_URL,
            "schedule_tier": "daily",
            "preview_signal_count": 8,
            "is_featured": False,
            "extraction_config": {
                "provider": "newsapi",
                "nl_query": "Nigeria real estate construction housing property",
                "params": {"q": "Nigeria real estate OR construction OR housing OR property"},
                "managed_source": True,
            },
        },
        {
            "slug": "nigeria-public-sentiment-x",
            "name": "Nigeria Public Sentiment on X",
            "short_description": "Social listening for emerging public narrative shifts in Nigeria.",
            "description": (
                "Tracks public conversation on X around regulated sectors, market events, and brand"
                " or policy developments that can move sentiment quickly."
            ),
            "industry_slug": "financial-services",
            "signal_type": "social",
            "primary_country": "NGA",
            "regions": ["Nigeria"],
            "tags": ["social", "sentiment", "X", "Nigeria"],
            "source_type": "social",
            "source_url": DEFAULT_X_SEARCH_URL,
            "schedule_tier": "standard",
            "preview_signal_count": 20,
            "is_featured": False,
            "extraction_config": {
                "provider": "x",
                "platform": "x",
                "nl_query": "Nigeria banking fintech regulation",
                "params": {"query": "Nigeria (banking OR fintech OR regulation)"},
                "managed_source": True,
            },
        },
    ]


async def ensure_core_catalog(db: AsyncSession) -> dict[str, int]:
    """Ensure core industries and marketplace templates exist."""

    industry_result = await db.execute(select(Industry))
    industries = {industry.slug: industry for industry in industry_result.scalars().all()}
    created_industries = 0

    for spec in CORE_INDUSTRIES:
        if spec["slug"] in industries:
            continue
        industry = Industry(
            id=uuid4(),
            slug=spec["slug"],
            name=spec["name"],
            description=spec["description"],
        )
        db.add(industry)
        industries[spec["slug"]] = industry
        created_industries += 1

    if created_industries:
        await db.flush()

    template_result = await db.execute(select(SignalTemplate.slug))
    existing_template_slugs = {row[0] for row in template_result.all()}
    created_templates = 0

    for spec in _marketplace_specs():
        slug = str(spec["slug"])
        if slug in existing_template_slugs:
            continue

        industry = industries.get(str(spec["industry_slug"]))
        if not industry:
            logger.warning("bootstrap_template_missing_industry", extra={"template_slug": slug})
            continue

        template = SignalTemplate(
            id=uuid4(),
            name=str(spec["name"]),
            slug=slug,
            description=str(spec["description"]),
            short_description=str(spec["short_description"]),
            industry_id=industry.id,
            signal_type=str(spec["signal_type"]),
            primary_country=spec["primary_country"],
            regions=list(spec["regions"]),
            tags=list(spec["tags"]),
            source_url=str(spec["source_url"]),
            source_type=str(spec["source_type"]),
            refresh_cron="0 * * * *",
            schedule_tier=str(spec["schedule_tier"]),
            extraction_config=dict(spec["extraction_config"]),
            is_official=True,
            is_active=True,
            is_featured=bool(spec["is_featured"]),
            subscription_count=0,
            preview_signal_count=int(spec["preview_signal_count"]),
            created_by_org_id=None,
        )
        db.add(template)
        created_templates += 1

    if created_industries or created_templates:
        await db.commit()

    summary = {
        "created_industries": created_industries,
        "created_templates": created_templates,
        "total_industries": len(industries),
        "total_templates": len(existing_template_slugs) + created_templates,
    }
    logger.info("bootstrap_catalog_ready", extra=summary)
    return summary
