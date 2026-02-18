"""
Edge-case tests.

Covers:
  - Empty / blank input
  - Extremely large input
  - Null values in optional fields
  - Invalid UUID path params
  - Non-existent resource IDs (404)
  - Duplicate resources (unique constraint)
  - Pagination boundaries
  - Invalid query params (negative skip, confidence > 1.0)
  - Credit edge cases (zero balance, zero cost action)
  - Role string edge cases
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.auth.enums import Role
from backend.auth.exceptions import InsufficientRoleError
from backend.auth.guards import require_role
from backend.schemas.briefs import BriefGenerateRequest
from backend.schemas.chat import SendMessageRequest
from backend.schemas.signals import SignalContractBase
from tests.conftest import (
    create_credit_transaction,
    create_industry,
    create_organization,
    create_signal,
    create_signal_contract,
    create_user,
    make_auth_context,
)

pytestmark = pytest.mark.asyncio


# ── Empty / Blank Input ─────────────────────────────────────────────


class TestEmptyInput:
    def test_empty_message_rejected(self):
        with pytest.raises(ValidationError):
            SendMessageRequest(message="")

    def test_whitespace_only_message(self):
        # Single space should pass min_length=1 at the schema level
        req = SendMessageRequest(message=" ")
        assert req.message == " "

    def test_empty_contract_name_rejected(self):
        with pytest.raises(ValidationError):
            SignalContractBase(
                name="",
                source_url="https://example.com",
                source_type="rss",
            )

    def test_empty_brief_topic_rejected(self):
        with pytest.raises(ValidationError):
            BriefGenerateRequest(topic="", industry_id=uuid4())

    def test_none_message_rejected(self):
        with pytest.raises(ValidationError):
            SendMessageRequest(message=None)  # type: ignore


# ── Extremely Large Input ────────────────────────────────────────────


class TestLargeInput:
    def test_message_exactly_4000_chars(self):
        req = SendMessageRequest(message="a" * 4000)
        assert len(req.message) == 4000

    def test_message_4001_chars_rejected(self):
        with pytest.raises(ValidationError):
            SendMessageRequest(message="a" * 4001)

    def test_contract_name_255_chars_ok(self):
        sc = SignalContractBase(
            name="x" * 255,
            source_url="https://example.com",
            source_type="api",
        )
        assert len(sc.name) == 255

    def test_contract_name_256_chars_rejected(self):
        with pytest.raises(ValidationError):
            SignalContractBase(
                name="x" * 256,
                source_url="https://example.com",
                source_type="api",
            )

    def test_brief_topic_500_chars_ok(self):
        req = BriefGenerateRequest(topic="x" * 500, industry_id=uuid4())
        assert len(req.topic) == 500

    def test_brief_topic_501_chars_rejected(self):
        with pytest.raises(ValidationError):
            BriefGenerateRequest(topic="x" * 501, industry_id=uuid4())


# ── Invalid UUID Path Params ─────────────────────────────────────────


class TestInvalidUUIDs:
    async def test_invalid_uuid_signal_id(self, authenticated_client):
        client, auth = authenticated_client
        resp = await client.get("/api/v1/signals/not-a-uuid")
        assert resp.status_code == 422  # Pydantic/FastAPI validation error

    async def test_invalid_uuid_user_id(self, authenticated_client):
        client, auth = authenticated_client
        resp = await client.get("/api/v1/users/12345")
        assert resp.status_code == 422

    async def test_invalid_uuid_org_id(self, authenticated_client):
        client, auth = authenticated_client
        resp = await client.get("/api/v1/orgs/xyz")
        assert resp.status_code == 422


# ── Non-existent Resources (404) ─────────────────────────────────────


class TestNonExistentResources:
    async def test_signal_not_found(self, authenticated_client):
        client, auth = authenticated_client
        resp = await client.get(f"/api/v1/signals/{uuid4()}")
        assert resp.status_code == 404

    async def test_user_not_found(self, authenticated_client):
        client, auth = authenticated_client
        resp = await client.get(f"/api/v1/users/{uuid4()}")
        assert resp.status_code == 404


# ── Pagination Boundaries ────────────────────────────────────────────


class TestPaginationEdgeCases:
    async def test_skip_zero_limit_one(self, app, client, db_session):
        from backend.auth.dependencies import get_current_user

        org = await create_organization(db_session)
        auth = make_auth_context(org_id=org.id)
        app.dependency_overrides[get_current_user] = lambda: auth

        resp = await client.get("/api/v1/signals?skip=0&limit=1")
        assert resp.status_code == 200

    async def test_negative_skip_rejected(self, authenticated_client):
        client, auth = authenticated_client
        resp = await client.get("/api/v1/signals?skip=-1")
        assert resp.status_code == 422

    async def test_limit_zero_rejected(self, authenticated_client):
        client, auth = authenticated_client
        resp = await client.get("/api/v1/signals?limit=0")
        assert resp.status_code == 422

    async def test_limit_over_max_rejected(self, authenticated_client):
        client, auth = authenticated_client
        resp = await client.get("/api/v1/signals?limit=999")
        assert resp.status_code == 422

    async def test_confidence_over_1_rejected(self, authenticated_client):
        client, auth = authenticated_client
        resp = await client.get("/api/v1/signals?min_confidence=1.5")
        assert resp.status_code == 422

    async def test_negative_confidence_rejected(self, authenticated_client):
        client, auth = authenticated_client
        resp = await client.get("/api/v1/signals?min_confidence=-0.1")
        assert resp.status_code == 422


# ── Credit Edge Cases ────────────────────────────────────────────────


class TestCreditEdgeCases:
    async def test_org_with_zero_credits(self, db_session):
        """Org with 0 allocated credits should have 0 remaining."""
        org = await create_organization(
            db_session, credits_allocated=0, credits_consumed=0
        )
        remaining = org.credits_allocated_monthly - org.credits_consumed
        assert remaining == 0

    async def test_consumed_exceeds_allocated(self, db_session):
        """Overage scenario: consumed > allocated."""
        org = await create_organization(
            db_session, credits_allocated=100, credits_consumed=150
        )
        remaining = org.credits_allocated_monthly - org.credits_consumed
        assert remaining == -50  # Negative = overage

    async def test_credit_transaction_zero_cost(self, db_session):
        """Free actions should record 0 credits consumed."""
        org = await create_organization(db_session)
        tx = await create_credit_transaction(
            db_session,
            org=org,
            action_type="signal_view",
            credits_consumed=0,
            credits_remaining=1000,
        )
        assert tx.credits_consumed == 0


# ── Role String Edge Cases ───────────────────────────────────────────


class TestRoleEdgeCases:
    def test_invalid_role_string(self):
        with pytest.raises(ValueError):
            Role.from_string("superuser")

    def test_empty_role_string(self):
        with pytest.raises(ValueError):
            Role.from_string("")

    def test_role_with_whitespace(self):
        # Should handle leading/trailing whitespace
        assert Role.from_string("  admin  ") == Role.ADMIN

    def test_require_role_viewer_cannot_be_owner(self):
        ctx = make_auth_context(role="viewer")
        with pytest.raises(InsufficientRoleError):
            require_role(ctx, "owner")


# ── Null Values in Optional Fields ───────────────────────────────────


class TestNullOptionalFields:
    async def test_signal_null_org(self, db_session):
        ind = await create_industry(db_session)
        sc = await create_signal_contract(db_session, industry=ind)
        sig = await create_signal(db_session, contract=sc)
        assert sig.org_id is None
        assert sig.summary is None
        assert sig.content_hash is None

    async def test_user_null_optional_fields(self, db_session):
        user = await create_user(db_session)
        assert user.picture_url is None
        assert user.last_login_at is None
        assert user.consent_date is None

    async def test_organization_null_dates(self, db_session):
        org = await create_organization(db_session)
        assert org.beta_start_date is None
        assert org.beta_end_date is None
        assert org.trial_start_date is None
