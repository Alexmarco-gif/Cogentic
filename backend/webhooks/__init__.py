"""Webhooks package"""

from backend.webhooks.auth0 import router as auth0_router

__all__ = ["auth0_router"]
