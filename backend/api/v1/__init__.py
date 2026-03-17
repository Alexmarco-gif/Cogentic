"""API v1 router aggregator"""

from fastapi import APIRouter

from backend.api.v1 import (
    admin,
    alerts,
    api_keys,
    auth,
    briefs,
    bulk,
    causal,
    chat,
    contracts,
    credits,
    discovered_sources,
    documents,
    entities,
    exports,
    features,
    feedback,
    health,
    industries,
    influence,
    knowledge,
    market_data,
    marketplace,
    ml,
    moat,
    monitoring,
    notifications,
    orgs,
    pipeline,
    pricing,
    recommendations,
    regulatory,
    search,
    signals,
    situation_room,
    synthesis,
    users,
)

api_v1_router = APIRouter(prefix="/api/v1")

# Include sub-routers
api_v1_router.include_router(auth.router, tags=["auth"])
api_v1_router.include_router(health.router, tags=["health"])
api_v1_router.include_router(orgs.router, tags=["organizations"])
api_v1_router.include_router(documents.router, tags=["documents"])
api_v1_router.include_router(users.router, tags=["users"])
api_v1_router.include_router(api_keys.router, tags=["api-keys"])
api_v1_router.include_router(features.router, tags=["features"])

# Pricing & Feature Gating
api_v1_router.include_router(pricing.router, tags=["pricing"])
api_v1_router.include_router(credits.router, tags=["credits"])
api_v1_router.include_router(admin.router, tags=["admin"])

# Sprint 2 — Signal Acquisition Pipeline
api_v1_router.include_router(contracts.router, tags=["contracts"])
api_v1_router.include_router(signals.router, tags=["signals"])
api_v1_router.include_router(pipeline.router, tags=["pipeline"])

# Sprint 3 — ML Pipeline
api_v1_router.include_router(ml.router, tags=["ml"])

# Sprint 4 — Intelligence Briefs + Deep Search + AI Synthesis
api_v1_router.include_router(briefs.router, tags=["briefs"])
api_v1_router.include_router(search.router, tags=["search"])
api_v1_router.include_router(synthesis.router, tags=["synthesis"])
api_v1_router.include_router(recommendations.router, tags=["recommendations"])

# Sprint 5 — AI Chat Agent
api_v1_router.include_router(chat.router, tags=["chat"])

# Sprint 6 — Situation Room (REST + WebSocket)
api_v1_router.include_router(situation_room.router, tags=["situation-room"])

# Efficiency enhancements
api_v1_router.include_router(bulk.router, tags=["bulk"])
api_v1_router.include_router(monitoring.router, tags=["monitoring"])

# Intelligence Moat — Proprietary Intelligence Layer
api_v1_router.include_router(entities.router, tags=["entities"])
api_v1_router.include_router(causal.router, tags=["causal-intelligence"])
api_v1_router.include_router(feedback.router, tags=["feedback"])
api_v1_router.include_router(influence.router, tags=["influence-mapping"])
api_v1_router.include_router(regulatory.router, tags=["regulatory-knowledge"])
api_v1_router.include_router(knowledge.router, tags=["knowledge-base"])
api_v1_router.include_router(moat.router, tags=["moat-metrics"])

# Dynamic Intelligence — Source Discovery & Living Contracts
api_v1_router.include_router(industries.router, tags=["industries"])
api_v1_router.include_router(discovered_sources.router, tags=["discovered-sources"])
api_v1_router.include_router(market_data.router, tags=["market-data"])
api_v1_router.include_router(alerts.router, tags=["alerts"])

# Platform utilities
api_v1_router.include_router(exports.router, tags=["exports"])
api_v1_router.include_router(notifications.router, tags=["notifications"])

# Signal Marketplace
api_v1_router.include_router(marketplace.router, tags=["marketplace"])
