"""
E2E Tests: Webhooks
===================

Tests for webhook endpoints, particularly Auth0 webhook integration.
These tests verify webhook signature validation and event handling.

Simulates: Auth0 sending user sync events to the API
"""

import hashlib
import hmac
import json
import time

import pytest


def _skip_if_webhook_missing(response):
    if response.status_code == 404:
        pytest.skip("Webhook endpoint not enabled in this environment")


@pytest.mark.e2e
class TestWebhookEndpoints:
    """Test webhook endpoint availability"""
    
    def test_auth0_webhook_endpoint_exists(self, client):
        """
        User Story: Auth0 webhook endpoint is available
        
        Expected: Endpoint exists (rejects requests without valid signature)
        """
        response = client.post(
            "/webhooks/auth0/events",
            json={"test": "data"}
        )
        
        _skip_if_webhook_missing(response)
        # Should reject due to missing/invalid signature
        assert response.status_code in [400, 401, 403, 422]
    
    def test_webhook_requires_post(self, client):
        """
        User Story: Webhook only accepts POST
        
        Expected: GET returns 405 or 404
        """
        response = client.get("/webhooks/auth0/events")
        
        assert response.status_code in [404, 405]


@pytest.mark.e2e
class TestWebhookSecurity:
    """Test webhook signature validation"""
    
    def test_webhook_rejects_missing_signature(self, client):
        """
        User Story: Webhooks without signature are rejected
        
        Expected: 401/403 Unauthorized
        """
        response = client.post(
            "/webhooks/auth0/events",
            json={"event": "user.created", "user_id": "test123"}
        )
        
        _skip_if_webhook_missing(response)
        assert response.status_code in [400, 401, 403]
    
    def test_webhook_rejects_invalid_signature(self, client):
        """
        User Story: Webhooks with invalid signature are rejected
        
        Expected: 401/403 Unauthorized
        """
        response = client.post(
            "/webhooks/auth0/events",
            json={"event": "user.created", "user_id": "test123"},
            headers={
                "X-Auth0-Signature": "invalid-signature",
                "X-Auth0-Signature-256": "sha256=invalid"
            }
        )
        
        _skip_if_webhook_missing(response)
        assert response.status_code in [400, 401, 403]
    
    def test_webhook_rejects_tampered_payload(self, client):
        """
        User Story: Tampered webhook payloads are rejected
        
        Expected: Signature mismatch detected
        """
        # Sign one payload, send different payload
        original_payload = {"event": "user.created", "user_id": "test123"}
        tampered_payload = {"event": "user.created", "user_id": "hacker456"}
        
        # Create signature for original payload with a test secret
        test_secret = "test-webhook-secret"
        signature = hmac.new(
            test_secret.encode(),
            json.dumps(original_payload).encode(),
            hashlib.sha256
        ).hexdigest()
        
        response = client.post(
            "/webhooks/auth0/events",
            json=tampered_payload,  # Send tampered
            headers={"X-Auth0-Signature-256": f"sha256={signature}"}
        )
        
        # Should reject - signature won't match
        _skip_if_webhook_missing(response)
        assert response.status_code in [400, 401, 403]
    
    def test_webhook_rejects_replay_attack(self, client):
        """
        User Story: Replay attacks with old timestamps are rejected
        
        Expected: Old timestamp detected and rejected
        """
        # Create payload with old timestamp
        old_timestamp = int(time.time()) - 3600  # 1 hour ago
        
        payload = {
            "event": "user.created",
            "user_id": "test123",
            "timestamp": old_timestamp
        }
        
        response = client.post(
            "/webhooks/auth0/events",
            json=payload,
            headers={
                "X-Auth0-Signature-256": "sha256=somesignature",
                "X-Auth0-Timestamp": str(old_timestamp)
            }
        )
        
        # Should reject due to old timestamp or invalid signature
        _skip_if_webhook_missing(response)
        assert response.status_code in [400, 401, 403]


@pytest.mark.e2e
class TestWebhookPayloadValidation:
    """Test webhook payload validation"""
    
    def test_webhook_rejects_empty_body(self, client):
        """
        User Story: Empty webhook body is rejected
        
        Expected: 400 Bad Request
        """
        response = client.post(
            "/webhooks/auth0/events",
            data="",
            headers={"Content-Type": "application/json"}
        )
        
        _skip_if_webhook_missing(response)
        assert response.status_code in [400, 422]
    
    def test_webhook_rejects_invalid_json(self, client):
        """
        User Story: Invalid JSON in webhook is rejected
        
        Expected: 400/422 Bad Request
        """
        response = client.post(
            "/webhooks/auth0/events",
            data="not valid json {{{",
            headers={"Content-Type": "application/json"}
        )
        
        _skip_if_webhook_missing(response)
        assert response.status_code in [400, 422]
    
    def test_webhook_validates_event_structure(self, client):
        """
        User Story: Webhook validates required event fields
        
        Expected: Missing required fields rejected
        """
        response = client.post(
            "/webhooks/auth0/events",
            json={},  # Missing required fields
            headers={"X-Auth0-Signature-256": "sha256=test"}
        )
        
        # Should fail - either signature check or validation
        _skip_if_webhook_missing(response)
        assert response.status_code in [400, 401, 403, 422]


@pytest.mark.e2e
class TestWebhookEventTypes:
    """Test handling of different webhook event types"""
    
    def test_unknown_event_type_handled(self, client):
        """
        User Story: Unknown event types don't crash the server
        
        Expected: Graceful handling (may ignore or log)
        """
        response = client.post(
            "/webhooks/auth0/events",
            json={"event": "unknown.event.type", "data": {}},
            headers={"X-Auth0-Signature-256": "sha256=test"}
        )
        
        # Should not crash - either reject signature or handle gracefully
        assert response.status_code != 500
    
    def test_malformed_event_data(self, client):
        """
        User Story: Malformed event data doesn't crash server
        
        Expected: Handled gracefully
        """
        response = client.post(
            "/webhooks/auth0/events",
            json={
                "event": "user.created",
                "data": "should-be-an-object-not-string"
            },
            headers={"X-Auth0-Signature-256": "sha256=test"}
        )
        
        # Should not crash
        assert response.status_code != 500


@pytest.mark.e2e
class TestWebhookIdempotency:
    """Test webhook idempotency handling"""
    
    def test_duplicate_webhook_handled(self, client):
        """
        User Story: Duplicate webhooks are handled idempotently
        
        Expected: Same result for same webhook sent twice
        """
        payload = {
            "event": "user.updated",
            "user_id": "test123",
            "idempotency_key": "unique-key-12345"
        }
        
        # First request
        response1 = client.post(
            "/webhooks/auth0/events",
            json=payload,
            headers={
                "X-Auth0-Signature-256": "sha256=test",
                "X-Idempotency-Key": "unique-key-12345"
            }
        )
        
        # Second request (duplicate)
        response2 = client.post(
            "/webhooks/auth0/events",
            json=payload,
            headers={
                "X-Auth0-Signature-256": "sha256=test",
                "X-Idempotency-Key": "unique-key-12345"
            }
        )
        
        # Both should have same result (fail due to invalid signature, but not differently)
        assert response1.status_code == response2.status_code


@pytest.mark.e2e
class TestWebhookResponseFormat:
    """Test webhook response format"""
    
    def test_webhook_error_returns_json(self, client):
        """
        User Story: Webhook errors return JSON responses
        
        Expected: JSON error response, not HTML
        """
        response = client.post(
            "/webhooks/auth0/events",
            json={"test": "data"}
        )
        
        assert "application/json" in response.headers.get("content-type", "")
        
        # Should be valid JSON
        data = response.json()
        assert isinstance(data, dict)
    
    def test_webhook_error_has_detail(self, client):
        """
        User Story: Webhook errors include helpful detail
        
        Expected: Error response has detail/message field
        """
        response = client.post(
            "/webhooks/auth0/events",
            json={"test": "data"}
        )
        
        data = response.json()
        
        # Should have error detail
        assert "detail" in data or "error" in data or "message" in data
