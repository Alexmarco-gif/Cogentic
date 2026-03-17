"""
Tests for the contract webhook delivery pipeline.

Covers:
  - WebhookFetcher always returns an empty list
  - send_webhook_notification: SSRF guard, happy path, HMAC signing
  - SignalAcquisitionService: webhook dispatch called post-store
  - Schema validation: webhook source_type accepted, URL validated at create time
"""

import hashlib
import hmac
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.schemas.signals import SignalContractCreate, SignalContractUpdate
from backend.signals.fetchers.webhook_fetcher import WebhookFetcher

pytestmark = pytest.mark.asyncio


# ═══════════════════════════════════════════════════════════════════════════════
# WebhookFetcher
# ═══════════════════════════════════════════════════════════════════════════════


class TestWebhookFetcher:
    async def test_fetch_returns_empty_list(self):
        fetcher = WebhookFetcher()
        result = await fetcher.fetch(
            source_url="https://example.com/hook",
            extraction_config={},
        )
        assert result == []

    async def test_fetch_ignores_source_url(self):
        """Any URL should yield the same empty list — no network call is made."""
        fetcher = WebhookFetcher()
        result = await fetcher.fetch(
            source_url="https://hooks.example.org/signal-events",
            extraction_config={"webhook_secret": "s3cr3t"},
        )
        assert result == []
        assert isinstance(result, list)

    def test_source_type_attribute(self):
        assert WebhookFetcher.source_type == "webhook"

    async def test_close_does_not_raise(self):
        fetcher = WebhookFetcher()
        await fetcher.close()  # must not raise even with no client

    async def test_registered_in_factory(self):
        from backend.signals.fetchers import get_fetcher

        fetcher = get_fetcher("webhook")
        assert isinstance(fetcher, WebhookFetcher)


# ═══════════════════════════════════════════════════════════════════════════════
# send_webhook_notification
# ═══════════════════════════════════════════════════════════════════════════════


class TestSendWebhookNotification:
    def _import(self):
        from backend.job_handlers import send_webhook_notification

        return send_webhook_notification

    def test_blocked_url_returns_failed_status(self):
        fn = self._import()
        result = fn("http://localhost/hook", "test.event", {"k": "v"})
        assert result["status"] == "failed"
        assert "blocked" in result["error"].lower()

    def test_blocked_loopback_ip(self):
        fn = self._import()
        result = fn("http://127.0.0.1/hook", "test.event", {})
        assert result["status"] == "failed"

    @patch("httpx.post")
    def test_happy_path_no_secret(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        fn = self._import()

        with patch("backend.job_handlers._validate_webhook_url", return_value=True):
            result = fn("https://example.com/hook", "signal.created", {"id": "abc"})

        assert result["status"] == "success"
        assert result["status_code"] == 200
        # No signature header added
        _, kwargs = mock_post.call_args
        assert "X-Cogent-Signature" not in kwargs.get("headers", {})

    @patch("httpx.post")
    def test_happy_path_with_signing_secret(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        fn = self._import()
        secret = "test-signing-secret"

        with patch("backend.job_handlers._validate_webhook_url", return_value=True):
            result = fn(
                "https://example.com/hook",
                "signals.created",
                {"contract_id": "x"},
                signing_secret=secret,
            )

        assert result["status"] == "success"
        _, kwargs = mock_post.call_args
        headers = kwargs.get("headers", {})
        assert "X-Cogent-Signature" in headers
        sig_header = headers["X-Cogent-Signature"]
        assert sig_header.startswith("sha256=")

        # Verify the HMAC value is correct
        body = kwargs.get("json")
        body_bytes = json.dumps(body, separators=(",", ":"), sort_keys=True).encode()
        expected_hex = hmac.new(
            secret.encode(), body_bytes, hashlib.sha256
        ).hexdigest()
        assert sig_header == f"sha256={expected_hex}"

    @patch("httpx.post", side_effect=Exception("connection refused"))
    def test_network_error_returns_failed_status(self, _mock_post):
        fn = self._import()
        with patch("backend.job_handlers._validate_webhook_url", return_value=True):
            result = fn("https://example.com/hook", "signal.created", {})
        assert result["status"] == "failed"
        assert "connection refused" in result["error"]


# ═══════════════════════════════════════════════════════════════════════════════
# Signal acquisition — webhook dispatch post-store
# ═══════════════════════════════════════════════════════════════════════════════


class TestSignalAcquisitionWebhookDispatch:
    """Verify that the acquisition service sends webhook notifications after
    persisting signals to webhook-type contracts."""

    def _make_contract(self, source_type="webhook", source_url="https://example.com/hook", secret=None):
        contract = MagicMock()
        contract.id = uuid4()
        contract.name = "Test Contract"
        contract.source_type = source_type
        contract.source_url = source_url
        contract.extraction_config = {"webhook_secret": secret} if secret else {}
        contract.is_active = True
        return contract

    def _make_signal(self):
        s = MagicMock()
        s.id = uuid4()
        return s

    @pytest.fixture()
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture()
    def service(self, mock_db):
        from backend.services.signal_acquisition import SignalAcquisitionService

        svc = SignalAcquisitionService.__new__(SignalAcquisitionService)
        svc.db = mock_db
        svc.contract_repo = AsyncMock()
        svc.signal_repo = AsyncMock()
        svc.dedup = AsyncMock()
        svc.extractor = MagicMock()
        return svc

    async def test_webhook_dispatch_called_for_webhook_contract(self, service):
        contract = self._make_contract(source_type="webhook", source_url="https://example.com/hook")
        signals = [self._make_signal(), self._make_signal()]

        service.signal_repo.create_many.return_value = signals
        service.dedup.filter_duplicates.return_value = [MagicMock()]
        service.extractor.process_batch.return_value = [MagicMock()]
        service.contract_repo.mark_fetched = AsyncMock()

        with patch(
            "backend.signals.fetchers.webhook_fetcher.WebhookFetcher.fetch",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "backend.job_handlers.send_webhook_notification"
        ) as mock_send, patch(
            "backend.job_queue.enqueue_job"
        ):
            await service.fetch_contract(contract)

        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args[0][0] == "https://example.com/hook"
        assert call_args[0][1] == "signals.created"
        payload = call_args[0][2]
        assert payload["signal_count"] == 2
        assert len(payload["signal_ids"]) == 2

    async def test_webhook_dispatch_passes_signing_secret(self, service):
        contract = self._make_contract(secret="my-secret")
        signals = [self._make_signal()]

        service.signal_repo.create_many.return_value = signals
        service.dedup.filter_duplicates.return_value = [MagicMock()]
        service.extractor.process_batch.return_value = [MagicMock()]
        service.contract_repo.mark_fetched = AsyncMock()

        with patch(
            "backend.signals.fetchers.webhook_fetcher.WebhookFetcher.fetch",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "backend.job_handlers.send_webhook_notification"
        ) as mock_send, patch(
            "backend.job_queue.enqueue_job"
        ):
            await service.fetch_contract(contract)

        _, _, _, signing_secret = mock_send.call_args[0]
        assert signing_secret == "my-secret"

    async def test_no_dispatch_for_api_contract(self, service):
        contract = self._make_contract(source_type="api", source_url="https://api.example.com/v1")
        signals = [self._make_signal()]

        service.signal_repo.create_many.return_value = signals
        service.dedup.filter_duplicates.return_value = [MagicMock()]
        service.extractor.process_batch.return_value = [MagicMock()]
        service.contract_repo.mark_fetched = AsyncMock()

        with patch("backend.signals.fetchers.api_fetcher.APIFetcher.fetch", new_callable=AsyncMock, return_value=[]), \
             patch("backend.job_handlers.send_webhook_notification") as mock_send, \
             patch("backend.job_queue.enqueue_job"):
            await service.fetch_contract(contract)

        mock_send.assert_not_called()

    async def test_no_dispatch_when_no_signals_stored(self, service):
        contract = self._make_contract()
        service.signal_repo.create_many.return_value = []
        service.dedup.filter_duplicates.return_value = []
        service.extractor.process_batch.return_value = []
        service.contract_repo.mark_fetched = AsyncMock()

        with patch(
            "backend.signals.fetchers.webhook_fetcher.WebhookFetcher.fetch",
            new_callable=AsyncMock,
            return_value=[],
        ), patch("backend.job_handlers.send_webhook_notification") as mock_send:
            await service.fetch_contract(contract)

        mock_send.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════════════
# Schema: webhook source_type + URL validation
# ═══════════════════════════════════════════════════════════════════════════════


class TestSignalContractWebhookSchema:
    def test_webhook_source_type_accepted_in_base(self):
        from backend.schemas.signals import SignalContractBase

        sc = SignalContractBase(
            name="Webhook Contract",
            source_url="https://example.com/hook",
            source_type="webhook",
        )
        assert sc.source_type == "webhook"

    def test_webhook_create_valid(self):
        sc = SignalContractCreate(
            name="Webhook Contract",
            source_url="https://hooks.example.com/signals",
            source_type="webhook",
            industry_id=uuid4(),
        )
        assert sc.source_type == "webhook"
        assert sc.source_url == "https://hooks.example.com/signals"

    def test_webhook_create_rejects_localhost(self):
        with pytest.raises(ValidationError, match="blocked"):
            SignalContractCreate(
                name="Bad Webhook",
                source_url="http://localhost/hook",
                source_type="webhook",
                industry_id=uuid4(),
            )

    def test_webhook_create_rejects_loopback_ip(self):
        with pytest.raises(ValidationError, match="blocked"):
            SignalContractCreate(
                name="Bad Webhook",
                source_url="http://127.0.0.1/hook",
                source_type="webhook",
                industry_id=uuid4(),
            )

    def test_webhook_create_rejects_file_scheme(self):
        with pytest.raises(ValidationError):
            SignalContractCreate(
                name="Bad Webhook",
                source_url="file:///etc/passwd",
                source_type="webhook",
                industry_id=uuid4(),
            )

    def test_webhook_create_rejects_metadata_host(self):
        with pytest.raises(ValidationError, match="blocked"):
            SignalContractCreate(
                name="Bad Webhook",
                source_url="http://metadata.google.internal/computeMetadata/v1/",
                source_type="webhook",
                industry_id=uuid4(),
            )

    def test_non_webhook_source_url_not_validated(self):
        """URL validation only applies when source_type is webhook."""
        sc = SignalContractCreate(
            name="API Contract",
            source_url="http://localhost/api",  # would be blocked if webhook
            source_type="api",
            industry_id=uuid4(),
        )
        assert sc.source_url == "http://localhost/api"

    def test_update_validates_url_when_both_set(self):
        with pytest.raises(ValidationError, match="blocked"):
            SignalContractUpdate(
                source_url="http://127.0.0.1/evil",
                source_type="webhook",
            )

    def test_update_skips_validation_when_type_not_webhook(self):
        upd = SignalContractUpdate(
            source_url="http://localhost/api",
            source_type="api",
        )
        assert upd.source_url == "http://localhost/api"

    def test_update_skips_validation_when_url_not_set(self):
        upd = SignalContractUpdate(source_type="webhook")
        assert upd.source_type == "webhook"
        assert upd.source_url is None
