import json

import pytest

from backend.services.paystack_service import PaystackService
from tests.conftest import make_auth_header


@pytest.mark.asyncio
async def test_upgrade_route_initializes_paystack_checkout(owner_client, monkeypatch):
    client, auth = owner_client

    async def fake_initialize(
        self,
        organization,
        *,
        user_id,
        user_email,
        target_tier,
        callback_url=None,
    ):
        assert str(organization.id) == str(auth.org_id)
        assert str(user_id) == str(auth.user_id)
        assert user_email == auth.email
        assert target_tier == "growth"
        assert callback_url == "https://example.ngrok.app/dashboard/settings?tab=plan"
        return {
            "reference": "cogent_ref_123",
            "access_code": "access_123",
            "authorization_url": "https://checkout.paystack.test",
            "public_key": "pk_test_public",
        }

    monkeypatch.setattr(
        PaystackService, "initialize_subscription_checkout", fake_initialize
    )

    response = await client.post(
        "/api/v1/pricing/upgrade",
        headers=make_auth_header(auth),
        json={
            "target_tier": "growth",
            "callback_url": "https://example.ngrok.app/dashboard/settings?tab=plan",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "checkout_initialized"
    assert payload["requested_tier"] == "growth"
    assert payload["reference"] == "cogent_ref_123"


@pytest.mark.asyncio
async def test_verify_route_activates_verified_checkout(owner_client, monkeypatch):
    client, auth = owner_client

    async def fake_verify(self, reference):
        assert reference == "cogent_ref_123"
        return {
            "status": "activated",
            "tier": "growth",
            "message": "Growth is now active.",
            "reference": reference,
            "transaction_status": "success",
        }

    monkeypatch.setattr(PaystackService, "verify_and_activate_checkout", fake_verify)

    response = await client.post(
        "/api/v1/pricing/verify",
        headers=make_auth_header(auth),
        json={"reference": "cogent_ref_123"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "activated"
    assert payload["tier"] == "growth"


@pytest.mark.asyncio
async def test_paystack_webhook_route_processes_verified_events(client, monkeypatch):
    monkeypatch.setattr(
        PaystackService,
        "verify_webhook_signature",
        lambda self, body, signature: signature == "valid-signature",
    )

    async def fake_process(self, payload):
        assert payload["event"] == "charge.success"
        return {"status": "processed", "event": "charge.success"}

    monkeypatch.setattr(PaystackService, "process_webhook_event", fake_process)

    response = await client.post(
        "/webhooks/paystack/events",
        headers={"x-paystack-signature": "valid-signature"},
        content=json.dumps({"event": "charge.success", "data": {"reference": "ref"}}),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["result"]["event"] == "charge.success"
