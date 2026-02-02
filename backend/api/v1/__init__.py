"""API v1 router aggregator"""

from fastapi import APIRouter

from backend.api.v1 import auth, health, orgs, documents, users, api_keys, features

api_v1_router = APIRouter(prefix="/api/v1")

# Include sub-routers
api_v1_router.include_router(auth.router, tags=["auth"])
api_v1_router.include_router(health.router, tags=["health"])
api_v1_router.include_router(orgs.router, tags=["organizations"])
api_v1_router.include_router(documents.router, tags=["documents"])
api_v1_router.include_router(users.router, tags=["users"])
api_v1_router.include_router(api_keys.router, tags=["api-keys"])
api_v1_router.include_router(features.router, tags=["features"])
