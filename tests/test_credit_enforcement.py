from uuid import uuid4

import pytest

from backend.services.credit_service import CreditService, InsufficientCreditsError
from backend.services.deep_search import DeepSearchService
from tests.conftest import create_organization


@pytest.mark.asyncio
async def test_consume_credits_strict_records_transaction_and_metadata(db_session):
    org = await create_organization(db_session, credits_allocated=100, credits_consumed=10)
    service = CreditService(db_session)

    txn = await service.consume_credits(
        org_id=org.id,
        user_id=uuid4(),
        action_type="deep_search",
        credits=10,
        metadata={"query": "fx outlook"},
    )

    await db_session.refresh(org)

    assert txn.credits_consumed == 10
    assert txn.credits_remaining == 80
    assert txn.transaction_metadata == {"query": "fx outlook"}
    assert org.credits_consumed == 20


@pytest.mark.asyncio
async def test_consume_credits_strict_blocks_when_balance_is_exhausted(db_session):
    org = await create_organization(db_session, credits_allocated=25, credits_consumed=20)
    service = CreditService(db_session)

    with pytest.raises(InsufficientCreditsError) as exc_info:
        await service.consume_credits(
            org_id=org.id,
            user_id=uuid4(),
            action_type="contract_create",
            credits=25,
            metadata={"contract_name": "Blocked Contract"},
        )

    await db_session.refresh(org)

    assert exc_info.value.required == 25
    assert exc_info.value.remaining == 5
    assert org.credits_consumed == 20


@pytest.mark.asyncio
async def test_search_route_returns_402_for_insufficient_credits(
    authenticated_client,
    monkeypatch,
):
    client, auth = authenticated_client

    async def fake_consume(self, org_id, user_id, action_type, credits=None, metadata=None):
        raise InsufficientCreditsError(action_type=action_type, required=10, remaining=0)

    async def unexpected_search(self, **kwargs):
        raise AssertionError("Deep search should not run when credits are insufficient")

    monkeypatch.setattr(CreditService, "consume_credits", fake_consume)
    monkeypatch.setattr(DeepSearchService, "search", unexpected_search)

    response = await client.post(
        "/api/v1/search",
        json={"query": "fx outlook", "include_synthesis": False},
        headers={"Authorization": "Bearer test-jwt-token"},
    )

    assert response.status_code == 402
    assert "Insufficient credits" in response.json()["detail"]


@pytest.mark.asyncio
async def test_credit_balance_reports_strict_prepaid_flag(client, app, auth_context):
    from backend.auth.dependencies import get_current_user

    app.dependency_overrides[get_current_user] = lambda: auth_context
    response = await client.get(
        "/api/v1/credits/balance",
        headers={"Authorization": "Bearer test-jwt-token"},
    )
    app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["strict_prepaid_enabled"] is True
