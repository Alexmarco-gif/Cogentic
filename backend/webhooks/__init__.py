"""Webhooks package"""

from backend.webhooks.auth0 import router as auth0_router
from backend.webhooks.paystack import router as paystack_router

__all__ = ["auth0_router", "paystack_router"]
