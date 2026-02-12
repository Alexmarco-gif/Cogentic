"""API v1 router aggregator"""

from fastapi import APIRouter

from backend.api.v1 import (
    api_keys,
    auth,
    briefs,
    bulk,
    causal,
    contracts,
    documents,
    entities,
    features,
    feedback,
    health,
    influence,
    ml,
    moat,
    monitoring,
    orgs,
    pipeline,
    recommendations,
    regulatory,
    search,
    signals,
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

# Efficiency enhancements
api_v1_router.include_router(bulk.router, tags=["bulk"])
api_v1_router.include_router(monitoring.router, tags=["monitoring"])

# Intelligence Moat — Proprietary Intelligence Layer
api_v1_router.include_router(entities.router, tags=["entities"])
api_v1_router.include_router(causal.router, tags=["causal-intelligence"])
api_v1_router.include_router(feedback.router, tags=["feedback"])
api_v1_router.include_router(influence.router, tags=["influence-mapping"])
api_v1_router.include_router(regulatory.router, tags=["regulatory-knowledge"])
api_v1_router.include_router(moat.router, tags=["moat-metrics"])
