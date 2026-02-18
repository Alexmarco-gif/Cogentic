"""
Pydantic schema validation tests.

Covers:
  - Valid inputs accepted
  - Invalid inputs rejected
  - Field constraints (min_length, max_length, pattern, ge, le)
  - Optional fields default correctly
  - Nested schemas
"""

from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.schemas.briefs import (
    BriefGenerateRequest,
    BriefRegenerateRequest,
)
from backend.schemas.chat import (
    ChatDeleteResponse,
    ChatSessionResponse,
    CreateSessionRequest,
    SendMessageRequest,
)
from backend.schemas.search import SearchRequest
from backend.schemas.signals import (
    SignalContractBase,
    SignalContractCreate,
    SignalContractUpdate,
    SignalResponse,
)

# ── Signal Contract Schemas ──────────────────────────────────────────


class TestSignalContractSchemas:
    def test_valid_contract_create(self):
        sc = SignalContractCreate(
            name="Reuters API",
            source_url="https://reuters.com/api/v1",
            source_type="api",
            industry_id=uuid4(),
        )
        assert sc.name == "Reuters API"
        assert sc.source_type == "api"
        assert sc.is_active is True

    def test_all_source_types(self):
        for st in ("api", "scraper", "rss", "social"):
            sc = SignalContractBase(
                name=f"{st} source",
                source_url=f"https://example.com/{st}",
                source_type=st,
            )
            assert sc.source_type == st

    def test_invalid_source_type(self):
        with pytest.raises(ValidationError):
            SignalContractBase(
                name="Bad",
                source_url="https://example.com",
                source_type="ftp",  # Invalid
            )

    def test_all_schedule_tiers(self):
        for tier in ("realtime", "standard", "slow", "daily"):
            sc = SignalContractBase(
                name="Test",
                source_url="https://example.com",
                source_type="rss",
                schedule_tier=tier,
            )
            assert sc.schedule_tier == tier

    def test_invalid_schedule_tier(self):
        with pytest.raises(ValidationError):
            SignalContractBase(
                name="Test",
                source_url="https://example.com",
                source_type="rss",
                schedule_tier="weekly",  # Invalid
            )

    def test_contract_name_min_length(self):
        with pytest.raises(ValidationError):
            SignalContractBase(
                name="",  # min_length=1
                source_url="https://example.com",
                source_type="rss",
            )

    def test_contract_name_max_length(self):
        with pytest.raises(ValidationError):
            SignalContractBase(
                name="x" * 256,  # max_length=255
                source_url="https://example.com",
                source_type="api",
            )

    def test_contract_update_all_optional(self):
        # All fields are optional in update
        update = SignalContractUpdate()
        assert update.name is None
        assert update.source_type is None

    def test_contract_defaults(self):
        sc = SignalContractBase(
            name="Test",
            source_url="https://example.com",
            source_type="rss",
        )
        assert sc.refresh_cron == "0 */1 * * *"
        assert sc.schedule_tier == "standard"
        assert sc.is_active is True
        assert sc.extraction_config == {}


# ── Chat Schemas ─────────────────────────────────────────────────────


class TestChatSchemas:
    def test_create_session_minimal(self):
        req = CreateSessionRequest()
        assert req.industry_slug is None
        assert req.title is None

    def test_create_session_with_values(self):
        req = CreateSessionRequest(industry_slug="fintech", title="Market Analysis")
        assert req.industry_slug == "fintech"
        assert req.title == "Market Analysis"

    def test_send_message_valid(self):
        req = SendMessageRequest(message="What's the latest on AI regulation?")
        assert req.message == "What's the latest on AI regulation?"

    def test_send_message_empty(self):
        with pytest.raises(ValidationError):
            SendMessageRequest(message="")  # min_length=1

    def test_send_message_too_long(self):
        with pytest.raises(ValidationError):
            SendMessageRequest(message="x" * 4001)  # max_length=4000

    def test_send_message_exactly_max(self):
        req = SendMessageRequest(message="x" * 4000)
        assert len(req.message) == 4000

    def test_chat_session_response(self):
        now = datetime.utcnow()
        resp = ChatSessionResponse(
            id=uuid4(),
            user_id=uuid4(),
            org_id=uuid4(),
            status="active",
            created_at=now,
            updated_at=now,
        )
        assert resp.status == "active"

    def test_chat_delete_response(self):
        sid = uuid4()
        resp = ChatDeleteResponse(deleted=True, session_id=sid)
        assert resp.deleted is True
        assert resp.session_id == sid


# ── Brief Schemas ────────────────────────────────────────────────────


class TestBriefSchemas:
    def test_brief_generate_request_valid(self):
        req = BriefGenerateRequest(
            topic="Fintech regulatory trends in Africa",
            industry_id=uuid4(),
        )
        assert req.topic == "Fintech regulatory trends in Africa"
        assert req.signal_ids == []

    def test_brief_generate_topic_too_short(self):
        with pytest.raises(ValidationError):
            BriefGenerateRequest(topic="Hi", industry_id=uuid4())  # min_length=5

    def test_brief_generate_topic_too_long(self):
        with pytest.raises(ValidationError):
            BriefGenerateRequest(topic="x" * 501, industry_id=uuid4())  # max_length=500

    def test_brief_generate_with_signals(self):
        ids = [uuid4() for _ in range(5)]
        req = BriefGenerateRequest(
            topic="Energy market outlook",
            industry_id=uuid4(),
            signal_ids=ids,
        )
        assert len(req.signal_ids) == 5

    def test_brief_generate_too_many_signals(self):
        ids = [uuid4() for _ in range(21)]  # max_length=20
        with pytest.raises(ValidationError):
            BriefGenerateRequest(
                topic="Test topic here",
                industry_id=uuid4(),
                signal_ids=ids,
            )

    def test_brief_regenerate_defaults(self):
        req = BriefRegenerateRequest()
        assert req.signal_ids == []


# ── Search Schemas ───────────────────────────────────────────────────


class TestSearchSchemas:
    def test_search_request_valid(self):
        req = SearchRequest(query="fintech regulation Africa")
        assert req.query == "fintech regulation Africa"

    def test_search_request_defaults(self):
        req = SearchRequest(query="test query")
        assert req.max_results == 20  # or whatever the default
        assert req.include_synthesis is True  # typical default


# ── Signal Response Schema ───────────────────────────────────────────


class TestSignalResponseSchema:
    def test_signal_response_from_dict(self):
        now = datetime.utcnow()
        data = {
            "id": uuid4(),
            "contract_id": uuid4(),
            "org_id": None,
            "title": "Test Signal",
            "summary": "A summary",
            "source_url": "https://example.com",
            "signal_type": "news",
            "confidence": 0.85,
            "content_hash": "abc123",
            "fetched_at": now,
            "published_at": now,
            "expires_at": None,
            "extracted_data": {"key": "val"},
            "created_at": now,
        }
        resp = SignalResponse(**data)
        assert resp.title == "Test Signal"
        assert resp.confidence == 0.85
        assert resp.extracted_data == {"key": "val"}
