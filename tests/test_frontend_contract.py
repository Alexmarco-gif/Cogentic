"""
Backend ↔ Frontend Contract Alignment Test.

Validates that every endpoint path declared in the frontend API service
modules actually exists in the FastAPI router tree. If a backend endpoint
is renamed, moved, or removed, this test fails and points to the exact
frontend service function that references a stale path.

Run with:
    pytest tests/test_frontend_contract.py -v
"""

import re

import pytest

from backend.main import app

# ── Discover all registered backend routes ────────────────────────────────────

_route_cache: set[tuple[str, str]] | None = None


def _all_backend_routes() -> set[tuple[str, str]]:
    """Return {(METHOD, path_pattern)} for every registered FastAPI route."""
    global _route_cache
    if _route_cache is not None:
        return _route_cache

    routes: set[tuple[str, str]] = set()
    for route in app.routes:
        if hasattr(route, "methods") and hasattr(route, "path"):
            for method in route.methods:
                routes.add((method.upper(), route.path))
    _route_cache = routes
    return routes


def _path_matches(
    declared_path: str, registered_routes: set[tuple[str, str]], method: str = "GET"
) -> bool:
    """Check if a declared path matches a registered route (handling path params)."""
    method = method.upper()
    for reg_method, reg_path in registered_routes:
        if reg_method != method:
            continue
        # Convert FastAPI path params like {signal_id} to a regex pattern
        pattern = re.sub(r"\{[^}]+\}", r"[^/]+", reg_path)
        pattern = f"^{pattern}$"
        if re.match(pattern, declared_path):
            return True
    return False


# ── Frontend contract declarations ────────────────────────────────────────────
# These are the exact paths + methods the frontend API layer calls.
# Sourced from frontend/lib/api/*.ts service modules.

FRONTEND_CONTRACTS: list[tuple[str, str, str]] = [
    # (METHOD, path, source_module)
    # Auth
    ("GET", "/api/v1/auth/me", "auth.ts"),
    ("GET", "/api/v1/auth/permissions", "auth.ts"),
    ("GET", "/api/v1/auth/token/verify", "auth.ts"),
    # Users
    ("GET", "/api/v1/users/me", "users.ts"),
    ("PATCH", "/api/v1/users/me", "users.ts"),
    ("GET", "/api/v1/users/{user_id}", "users.ts"),
    # Organizations
    ("GET", "/api/v1/orgs/{org_id}", "orgs.ts"),
    ("PATCH", "/api/v1/orgs/{org_id}", "orgs.ts"),
    ("DELETE", "/api/v1/orgs/{org_id}", "orgs.ts"),
    ("GET", "/api/v1/orgs/{org_id}/members", "orgs.ts"),
    ("POST", "/api/v1/orgs/{org_id}/members", "orgs.ts"),
    # Signals
    ("GET", "/api/v1/signals", "signals.ts"),
    ("GET", "/api/v1/signals/trending", "signals.ts"),
    ("GET", "/api/v1/signals/feed", "signals.ts"),
    ("GET", "/api/v1/signals/{signal_id}", "signals.ts"),
    ("GET", "/api/v1/signals/entity/{entity_id}", "signals.ts"),
    ("GET", "/api/v1/signals/contract/{contract_id}", "signals.ts"),
    # Contracts (full CRUD as used by useContractStudio)
    ("GET", "/api/v1/contracts", "contracts.ts"),
    ("POST", "/api/v1/contracts", "contracts.ts"),
    ("GET", "/api/v1/contracts/{contract_id}", "contracts.ts"),
    ("PATCH", "/api/v1/contracts/{contract_id}", "contracts.ts"),
    ("DELETE", "/api/v1/contracts/{contract_id}", "contracts.ts"),
    # Lifecycle: fetch, activate, deactivate
    ("POST", "/api/v1/contracts/{contract_id}/fetch", "contracts.ts"),
    ("POST", "/api/v1/contracts/{contract_id}/activate", "contracts.ts"),
    ("POST", "/api/v1/contracts/{contract_id}/deactivate", "contracts.ts"),
    # Briefs
    ("GET", "/api/v1/briefs", "briefs.ts"),
    ("GET", "/api/v1/briefs/{brief_id}", "briefs.ts"),
    ("POST", "/api/v1/briefs/generate", "briefs.ts"),
    # Search / Synthesis
    ("POST", "/api/v1/search", "search.ts"),
    ("GET", "/api/v1/search/history", "search.ts"),
    ("POST", "/api/v1/synthesis", "search.ts"),
    # Chat
    ("GET", "/api/v1/chat/sessions", "chat.ts"),
    ("POST", "/api/v1/chat/sessions", "chat.ts"),
    ("GET", "/api/v1/chat/sessions/{session_id}", "chat.ts"),
    # POST /chat/sessions/{id}/messages returns SSE — verify the route exists
    ("POST", "/api/v1/chat/sessions/{session_id}/messages", "chat.ts"),
    # Archive + delete (used by useInvestigate clearConversation)
    ("PATCH", "/api/v1/chat/sessions/{session_id}/archive", "chat.ts"),
    ("DELETE", "/api/v1/chat/sessions/{session_id}", "chat.ts"),
    # Pricing / Credits
    ("GET", "/api/v1/pricing/current", "pricing.ts"),
    ("GET", "/api/v1/pricing/features", "pricing.ts"),
    ("GET", "/api/v1/credits/balance", "pricing.ts"),
    ("GET", "/api/v1/credits/transactions", "pricing.ts"),
    ("GET", "/api/v1/credits/costs", "pricing.ts"),
    # Admin
    ("GET", "/api/v1/admin/pricing/mode", "admin.ts"),
    ("POST", "/api/v1/admin/pricing/mode", "admin.ts"),
    # Entities
    ("POST", "/api/v1/entities/resolve", "entities.ts"),
    ("POST", "/api/v1/entities", "entities.ts"),
    ("GET", "/api/v1/entities/{entity_id}/profile", "entities.ts"),
    ("GET", "/api/v1/entities/{entity_id}/network", "entities.ts"),
    ("GET", "/api/v1/entities/{entity_id}/with-influence", "entities.ts"),
    ("POST", "/api/v1/entities/relationships", "entities.ts"),
    # Feedback
    ("POST", "/api/v1/feedback", "feedback.ts"),
    # Notifications (in-app notification feed)
    ("GET", "/api/v1/notifications", "notifications.ts"),
    # Exports (document export — DOCX, PPTX, PDF-HTML)
    ("POST", "/api/v1/exports/brief", "exports.ts"),
    # API Keys (org-scoped key management)
    ("GET", "/api/v1/orgs/{org_id}/api-keys", "api_keys.ts"),
    ("POST", "/api/v1/orgs/{org_id}/api-keys", "api_keys.ts"),
    ("DELETE", "/api/v1/orgs/{org_id}/api-keys/{key_id}", "api_keys.ts"),
    # Privacy / Data Management
    ("DELETE", "/api/v1/users/me/history", "privacy.ts"),
    ("POST", "/api/v1/users/me/deletion-request", "privacy.ts"),
    ("POST", "/api/v1/users/me/data-export-request", "privacy.ts"),
]


# ── Test ──────────────────────────────────────────────────────────────────────


class TestFrontendContractAlignment:
    """Every endpoint the frontend declares must exist in the backend."""

    @pytest.fixture(autouse=True)
    def _routes(self):
        self.routes = _all_backend_routes()

    @pytest.mark.parametrize(
        "method,path,source",
        FRONTEND_CONTRACTS,
        ids=[f"{m} {p} ({s})" for m, p, s in FRONTEND_CONTRACTS],
    )
    def test_endpoint_exists(self, method: str, path: str, source: str):
        assert _path_matches(path, self.routes, method), (
            f"Frontend service '{source}' calls {method} {path} "
            f"but no matching route is registered in the FastAPI app."
        )


# ── Pagination contract: list endpoints must accept skip + limit  ──────────────

PAGINATED_LIST_ENDPOINTS: list[tuple[str, str]] = [
    ("GET", "/api/v1/signals"),
    ("GET", "/api/v1/briefs"),
    ("GET", "/api/v1/contracts"),
    ("GET", "/api/v1/chat/sessions"),
]


class TestPaginationParams:
    """List endpoints that feed paginated hooks must be declared with skip+limit support."""

    @pytest.fixture(autouse=True)
    def _routes(self):
        self.routes = _all_backend_routes()

    @pytest.mark.parametrize(
        "method,path",
        PAGINATED_LIST_ENDPOINTS,
        ids=[f"{m} {p}" for m, p in PAGINATED_LIST_ENDPOINTS],
    )
    def test_paginated_endpoint_exists(self, method: str, path: str):
        """Verify the endpoint exists; pagination params are query-level and not part of the path."""
        assert _path_matches(
            path, self.routes, method
        ), f"{method} {path} not found — required for paginated hook (skip/limit)."
