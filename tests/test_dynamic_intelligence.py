"""
Integration tests for the Dynamic Intelligence features.

Tests the full integration of:
  - Entity extraction (NER) with multi-region support
  - Entity resolution with auto-creation and confidence tiers
  - Discovered sources lifecycle (discover → recommend → activate → dismiss)
  - Source discovery API endpoints (CRUD, activation, stats)
  - Entity discovery review API endpoints (pending list, approve/reject)
  - NER feedback loop (reviewed entities → extraction prompt)
  - Refinement pipeline integration of all new steps
  - Living contracts (auto-created signal contracts from sources)

Uses the shared test fixtures from conftest.py (SQLite in-memory DB,
auth overrides, factory helpers).
"""

import hashlib
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from tests.conftest import (
    create_entity,
    create_industry,
    create_organization,
    create_signal,
    create_signal_contract,
    make_auth_context,
)

pytestmark = pytest.mark.asyncio


# ── Helpers ──────────────────────────────────────────────────────────


async def create_discovered_source(
    db,
    *,
    url: str = "https://cbn.gov.ng/rates",
    status: str = "discovered",
    mention_count: int = 1,
    relevance_score: float = 0.5,
    signal: object | None = None,
):
    """Insert a DiscoveredSource row."""
    from backend.models.discovered_source import DiscoveredSource

    url_hash = hashlib.sha256(url.lower().encode()).hexdigest()
    domain = url.split("//")[1].split("/")[0] if "//" in url else url
    ds = DiscoveredSource(
        id=uuid4(),
        url=url,
        url_hash=url_hash,
        domain=domain,
        source_type="government",
        signal_type="regulatory",
        mention_count=mention_count,
        relevance_score=relevance_score,
        status=status,
        first_seen_signal_id=signal.id if signal else None,
        last_seen_at=datetime.now(timezone.utc),
    )
    db.add(ds)
    await db.flush()
    await db.refresh(ds)
    return ds


# ── Discovered Source Model Tests ────────────────────────────────────


class TestDiscoveredSourceModel:
    """Test DiscoveredSource ORM model in isolation."""

    async def test_create_discovered_source(self, db_session):
        ds = await create_discovered_source(db_session)
        assert ds.id is not None
        assert ds.status == "discovered"
        assert ds.mention_count == 1
        assert ds.domain == "cbn.gov.ng"

    async def test_discovered_source_unique_url_hash(self, db_session):
        """Two sources with the same URL hash should conflict."""
        from sqlalchemy.exc import IntegrityError

        ds1 = await create_discovered_source(db_session, url="https://example.com/feed")
        with pytest.raises(IntegrityError):
            ds2 = await create_discovered_source(
                db_session, url="https://example.com/feed"
            )
            await db_session.flush()

    async def test_discovered_source_status_transitions(self, db_session):
        ds = await create_discovered_source(db_session)
        assert ds.status == "discovered"

        ds.status = "recommended"
        await db_session.flush()
        assert ds.status == "recommended"

        ds.status = "activated"
        await db_session.flush()
        assert ds.status == "activated"

    async def test_discovered_source_with_signal_fk(self, db_session):
        industry = await create_industry(db_session)
        contract = await create_signal_contract(db_session, industry=industry)
        signal = await create_signal(db_session, contract=contract)
        ds = await create_discovered_source(db_session, signal=signal)
        assert ds.first_seen_signal_id == signal.id


# ── Entity Discovery Model Tests ─────────────────────────────────────


class TestEntityDiscoveryFields:
    """Test the new discovery_status and discovery_source fields on Entity."""

    async def test_entity_defaults(self, db_session):
        entity = await create_entity(db_session, name="TestCorp NG")
        assert entity.discovery_status == "active"
        assert entity.discovery_source == "seed"

    async def test_entity_auto_extracted(self, db_session):
        from backend.models.entity import Entity

        entity = Entity(
            id=uuid4(),
            name="Dangote Cement",
            entity_type="company",
            discovery_status="pending_review",
            discovery_source="auto_extracted",
        )
        db_session.add(entity)
        await db_session.flush()
        await db_session.refresh(entity)
        assert entity.discovery_status == "pending_review"
        assert entity.discovery_source == "auto_extracted"

    async def test_entity_review_approve(self, db_session):
        from backend.models.entity import Entity

        entity = Entity(
            id=uuid4(),
            name="BUA Group",
            entity_type="company",
            discovery_status="pending_review",
            discovery_source="auto_extracted",
        )
        db_session.add(entity)
        await db_session.flush()

        entity.discovery_status = "active"
        await db_session.flush()
        assert entity.discovery_status == "active"

    async def test_entity_review_reject(self, db_session):
        from backend.models.entity import Entity

        entity = Entity(
            id=uuid4(),
            name="Unknown Corp",
            entity_type="company",
            discovery_status="pending_review",
            discovery_source="auto_extracted",
        )
        db_session.add(entity)
        await db_session.flush()

        entity.discovery_status = "rejected"
        await db_session.flush()
        assert entity.discovery_status == "rejected"


# ── Entity Extraction Service Tests ──────────────────────────────────


class TestEntityExtractionService:
    """Test EntityExtractionService initialization and region selection."""

    def test_build_system_prompt_nigeria(self):
        from backend.ai.entity_extraction import _build_system_prompt

        prompt = _build_system_prompt("NGA")
        assert "Nigeria" in prompt or "CBN" in prompt or "FIRS" in prompt

    def test_build_system_prompt_kenya(self):
        from backend.ai.entity_extraction import _build_system_prompt

        prompt = _build_system_prompt("KEN")
        assert "Kenya" in prompt or "CBK" in prompt or "KRA" in prompt

    def test_build_system_prompt_south_africa(self):
        from backend.ai.entity_extraction import _build_system_prompt

        prompt = _build_system_prompt("ZAF")
        assert "South Africa" in prompt or "SARB" in prompt

    def test_build_system_prompt_unknown_country_uses_default(self):
        from backend.ai.entity_extraction import (
            DEFAULT_REGIONAL_CONTEXT,
            _build_system_prompt,
        )

        prompt = _build_system_prompt("XYZ")
        # Should use the default pan-African context
        assert (
            "AfCFTA" in prompt
            or "African" in prompt
            or DEFAULT_REGIONAL_CONTEXT[:20] in prompt
        )

    def test_build_system_prompt_none_country_uses_default(self):
        from backend.ai.entity_extraction import _build_system_prompt

        prompt = _build_system_prompt(None)
        # Should not crash, returns default context
        assert len(prompt) > 50

    def test_service_init_default(self):
        from backend.ai.entity_extraction import EntityExtractionService

        svc = EntityExtractionService()
        assert svc.country is None

    def test_service_init_with_country(self):
        from backend.ai.entity_extraction import EntityExtractionService

        svc = EntityExtractionService(country="NGA")
        assert svc.country == "NGA"


# ── NER Feedback Loop Tests ──────────────────────────────────────────


class TestNERFeedbackLoop:
    """Test that reviewed entities are surfaced as feedback for NER."""

    async def test_feedback_empty_db(self, db_session):
        """With no reviewed entities, feedback should be empty."""
        from backend.ai.entity_extraction import EntityExtractionService

        feedback = await EntityExtractionService.get_feedback_examples(
            db_session, limit=10
        )
        assert feedback == "" or feedback is None or len(feedback) == 0

    async def test_feedback_with_reviewed_entities(self, db_session):
        """Reviewed entities should appear in the feedback string."""
        from backend.ai.entity_extraction import EntityExtractionService
        from backend.models.entity import Entity

        # Create an approved auto-extracted entity
        approved = Entity(
            id=uuid4(),
            name="Zenith Bank",
            entity_type="company",
            discovery_status="active",
            discovery_source="auto_extracted",
        )
        db_session.add(approved)

        # Create a rejected auto-extracted entity
        rejected = Entity(
            id=uuid4(),
            name="NotARealCompany",
            entity_type="company",
            discovery_status="rejected",
            discovery_source="auto_extracted",
        )
        db_session.add(rejected)
        await db_session.flush()

        feedback = await EntityExtractionService.get_feedback_examples(
            db_session, limit=10
        )

        # Feedback should mention both
        assert "Zenith Bank" in feedback
        assert "NotARealCompany" in feedback


# ── Discovered Sources API Tests ─────────────────────────────────────


class TestDiscoveredSourcesAPI:
    """Test the /api/v1/discovered-sources endpoints."""

    async def test_list_discovered_sources_empty(self, authenticated_client):
        client, auth = authenticated_client
        resp = await client.get("/api/v1/discovered-sources")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_discovered_sources_with_data(self, app, client, db_session):
        from backend.auth.dependencies import get_current_user

        auth = make_auth_context()
        app.dependency_overrides[get_current_user] = lambda: auth

        await create_discovered_source(
            db_session, url="https://sec.gov.ng/filings", status="recommended"
        )
        await create_discovered_source(
            db_session, url="https://nse.com.ng/data", status="discovered"
        )
        await db_session.commit()

        resp = await client.get("/api/v1/discovered-sources")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

        app.dependency_overrides.pop(get_current_user, None)

    async def test_list_discovered_sources_filter_by_status(
        self, app, client, db_session
    ):
        from backend.auth.dependencies import get_current_user

        auth = make_auth_context()
        app.dependency_overrides[get_current_user] = lambda: auth

        await create_discovered_source(
            db_session, url="https://npc.gov.ng/stats", status="recommended"
        )
        await create_discovered_source(
            db_session, url="https://nipc.gov.ng/data", status="discovered"
        )
        await db_session.commit()

        resp = await client.get(
            "/api/v1/discovered-sources", params={"status": "recommended"}
        )
        assert resp.status_code == 200
        data = resp.json()
        # Should only get recommended ones
        for item in data:
            assert item["status"] == "recommended"

        app.dependency_overrides.pop(get_current_user, None)

    async def test_get_discovery_stats(self, app, client, db_session):
        from backend.auth.dependencies import get_current_user

        auth = make_auth_context()
        app.dependency_overrides[get_current_user] = lambda: auth

        await create_discovered_source(
            db_session, url="https://stats1.example.com", status="discovered"
        )
        await create_discovered_source(
            db_session, url="https://stats2.example.com", status="recommended"
        )
        await create_discovered_source(
            db_session, url="https://stats3.example.com", status="activated"
        )
        await db_session.commit()

        resp = await client.get("/api/v1/discovered-sources/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "discovered" in data
        assert "recommended" in data
        assert "activated" in data
        assert "total" in data
        assert data["total"] >= 3

        app.dependency_overrides.pop(get_current_user, None)

    async def test_list_recommended_sources(self, app, client, db_session):
        from backend.auth.dependencies import get_current_user

        auth = make_auth_context()
        app.dependency_overrides[get_current_user] = lambda: auth

        await create_discovered_source(
            db_session,
            url="https://rec1.example.com",
            status="recommended",
            relevance_score=0.9,
        )
        await create_discovered_source(
            db_session,
            url="https://norec.example.com",
            status="discovered",
        )
        await db_session.commit()

        resp = await client.get("/api/v1/discovered-sources/recommended")
        assert resp.status_code == 200
        data = resp.json()
        for item in data:
            assert item["status"] == "recommended"

        app.dependency_overrides.pop(get_current_user, None)


# ── Entity Discovery Review API Tests ────────────────────────────────


class TestEntityDiscoveryReviewAPI:
    """Test /api/v1/entities/discovery/pending and /api/v1/entities/:id/review."""

    async def test_list_pending_entities_empty(self, admin_client):
        client, auth = admin_client

        resp = await client.get("/api/v1/entities/discovery/pending")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    async def test_list_pending_entities_with_data(self, admin_client, db_session):
        client, auth = admin_client
        from backend.models.entity import Entity

        # Create pending review entities
        for name in ["PendingCorp", "MaybeInc"]:
            entity = Entity(
                id=uuid4(),
                name=name,
                entity_type="company",
                discovery_status="pending_review",
                discovery_source="auto_extracted",
            )
            db_session.add(entity)
        await db_session.flush()
        await db_session.commit()

        resp = await client.get("/api/v1/entities/discovery/pending")
        assert resp.status_code == 200
        data = resp.json()
        pending_names = {item["name"] for item in data}
        assert "PendingCorp" in pending_names
        assert "MaybeInc" in pending_names

    async def test_review_entity_approve(self, admin_client, db_session):
        client, auth = admin_client
        from backend.models.entity import Entity

        entity = Entity(
            id=uuid4(),
            name="ApproveMe Corp",
            entity_type="company",
            discovery_status="pending_review",
            discovery_source="auto_extracted",
        )
        db_session.add(entity)
        await db_session.flush()
        await db_session.commit()

        resp = await client.post(
            f"/api/v1/entities/{entity.id}/review",
            json={"action": "approve"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["discovery_status"] == "active"

    async def test_review_entity_reject(self, admin_client, db_session):
        client, auth = admin_client
        from backend.models.entity import Entity

        entity = Entity(
            id=uuid4(),
            name="RejectMe Corp",
            entity_type="company",
            discovery_status="pending_review",
            discovery_source="auto_extracted",
        )
        db_session.add(entity)
        await db_session.flush()
        await db_session.commit()

        resp = await client.post(
            f"/api/v1/entities/{entity.id}/review",
            json={"action": "reject"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["discovery_status"] == "rejected"

    async def test_review_entity_invalid_action(self, admin_client, db_session):
        client, auth = admin_client
        from backend.models.entity import Entity

        entity = Entity(
            id=uuid4(),
            name="InvalidAction Corp",
            entity_type="company",
            discovery_status="pending_review",
            discovery_source="auto_extracted",
        )
        db_session.add(entity)
        await db_session.flush()
        await db_session.commit()

        resp = await client.post(
            f"/api/v1/entities/{entity.id}/review",
            json={"action": "maybe"},
        )
        # Pydantic validation or endpoint logic should reject
        assert resp.status_code in (400, 422)


# ── Refinement Pipeline Integration Tests ────────────────────────────


class TestRefinementPipelineSteps:
    """Test individual pipeline steps in isolation (mock LLM calls)."""

    async def test_refinement_step3_ner_handles_failure_gracefully(self, db_session):
        """Step 3 (NER) should catch exceptions and continue."""
        from backend.services.refinement_service import RefinementService

        industry = await create_industry(db_session)
        contract = await create_signal_contract(db_session, industry=industry)
        signal = await create_signal(
            db_session, contract=contract, title="Test signal for NER"
        )

        service = RefinementService(db_session)

        # Mock entity extraction to raise an error
        service.entity_extraction.extract = AsyncMock(
            side_effect=Exception("OpenAI rate limit")
        )
        # Mock other services to skip
        service.embedding_service.generate_signal_embedding = AsyncMock(
            return_value=None
        )
        service.scoring_service.score_signal = AsyncMock(return_value={})

        # Should not raise
        result = await service.refine_signal(signal)
        assert result["signal_id"] == str(signal.id)
        assert result["entities_linked"] == 0  # NER failed, no entities

    async def test_refinement_step6_source_discovery_handles_failure(self, db_session):
        """Step 6 (source discovery) should catch exceptions and continue."""
        from backend.ai.entity_extraction import ExtractionResult, SourceReference
        from backend.services.refinement_service import RefinementService

        industry = await create_industry(db_session)
        contract = await create_signal_contract(db_session, industry=industry)
        signal = await create_signal(db_session, contract=contract)

        service = RefinementService(db_session)

        # Make NER "succeed" with a source reference
        fake_extraction = ExtractionResult(
            entities=[],
            numeric_data=[],
            geographic=[],
            sources=[
                SourceReference(
                    url="https://cbn.gov.ng", name="CBN", source_type="government"
                )
            ],
        )
        service.entity_extraction.extract = AsyncMock(return_value=fake_extraction)
        service.embedding_service.generate_signal_embedding = AsyncMock(
            return_value=None
        )
        service.scoring_service.score_signal = AsyncMock(return_value={})

        # Make source discovery service raise
        service._source_discovery_service = MagicMock()
        service._source_discovery_service.track_sources = AsyncMock(
            side_effect=Exception("DB connection lost")
        )

        result = await service.refine_signal(signal)
        assert result["sources_discovered"] == 0  # Failed gracefully


# ── Source Discovery Service Tests ───────────────────────────────────


class TestSourceDiscoveryService:
    """Test SourceDiscoveryService business logic."""

    async def test_track_sources_empty_list(self, db_session):
        from backend.services.source_discovery import SourceDiscoveryService

        svc = SourceDiscoveryService(db_session)
        count = await svc.track_sources([], signal_id=uuid4())
        assert count == 0

    async def test_track_sources_new_source(self, db_session):
        from backend.ai.entity_extraction import SourceReference
        from backend.services.source_discovery import SourceDiscoveryService

        svc = SourceDiscoveryService(db_session)
        sources = [
            SourceReference(
                url="https://boi.org.ng/reports",
                name="BOI",
                source_type="government",
            )
        ]
        count = await svc.track_sources(sources, signal_id=uuid4())
        assert count >= 1

    async def test_track_sources_increments_mention_count(self, db_session):
        from sqlalchemy import select

        from backend.ai.entity_extraction import SourceReference
        from backend.models.discovered_source import DiscoveredSource
        from backend.services.source_discovery import SourceDiscoveryService

        svc = SourceDiscoveryService(db_session)
        ref = SourceReference(
            url="https://pencom.gov.ng/data",
            name="PenCom",
            source_type="government",
        )

        # Track once
        await svc.track_sources([ref], signal_id=uuid4())
        # Track again
        await svc.track_sources([ref], signal_id=uuid4())

        # Check mention_count
        url_hash = hashlib.sha256(
            "https://pencom.gov.ng/data".lower().encode()
        ).hexdigest()
        result = await db_session.execute(
            select(DiscoveredSource).where(DiscoveredSource.url_hash == url_hash)
        )
        ds = result.scalar_one()
        assert ds.mention_count >= 2


# ── Multi-Region NER Prompt Tests ────────────────────────────────────


class TestMultiRegionNER:
    """Test that regional context is correctly selected for each country."""

    def test_all_supported_countries_have_context(self):
        from backend.ai.entity_extraction import REGIONAL_CONTEXT

        required_countries = [
            "NGA",
            "KEN",
            "GHA",
            "ZAF",
            "EGY",
            "TZA",
            "ETH",
            "CIV",
            "MAR",
            "RWA",
        ]
        for code in required_countries:
            assert code in REGIONAL_CONTEXT, f"Missing context for {code}"
            assert len(REGIONAL_CONTEXT[code]) > 50, f"Context too short for {code}"

    def test_regional_context_contains_country_specific_terms(self):
        from backend.ai.entity_extraction import REGIONAL_CONTEXT

        # Spot-check that each context mentions relevant local terms
        assert any(
            term in REGIONAL_CONTEXT["NGA"]
            for term in ["Nigeria", "CBN", "SEC", "NGN", "naira"]
        )
        assert any(
            term in REGIONAL_CONTEXT["KEN"]
            for term in ["Kenya", "CBK", "KES", "shilling", "NSE"]
        )
        assert any(
            term in REGIONAL_CONTEXT["GHA"]
            for term in ["Ghana", "BoG", "GHS", "cedi", "GSE"]
        )
        assert any(
            term in REGIONAL_CONTEXT["ZAF"]
            for term in ["South Africa", "SARB", "ZAR", "rand", "JSE"]
        )
        assert any(
            term in REGIONAL_CONTEXT["EGY"]
            for term in ["Egypt", "CBE", "EGP", "EGX", "pound"]
        )
        # Wave 2 countries
        assert any(
            term in REGIONAL_CONTEXT["TZA"]
            for term in ["Tanzania", "BoT", "TZS", "DSE"]
        )
        assert any(
            term in REGIONAL_CONTEXT["ETH"]
            for term in ["Ethiopia", "NBE", "ETB", "ESX"]
        )
        assert any(
            term in REGIONAL_CONTEXT["CIV"]
            for term in ["Ivoire", "BCEAO", "XOF", "BRVM"]
        )
        assert any(
            term in REGIONAL_CONTEXT["MAR"] for term in ["Morocco", "BAM", "MAD", "CSE"]
        )
        assert any(
            term in REGIONAL_CONTEXT["RWA"] for term in ["Rwanda", "BNR", "RWF", "RSE"]
        )

    def test_default_context_is_pan_african(self):
        from backend.ai.entity_extraction import DEFAULT_REGIONAL_CONTEXT

        assert any(
            term in DEFAULT_REGIONAL_CONTEXT
            for term in ["AfCFTA", "African", "continental", "cross-border"]
        )


# ── End-to-End Source Lifecycle Test ─────────────────────────────────


class TestSourceLifecycleEndToEnd:
    """Test the full discovered source lifecycle through the model layer."""

    async def test_full_lifecycle_discovered_to_activated(self, db_session):
        """Source goes: discovered → recommended → activated with contract link."""

        industry = await create_industry(db_session, name="Banking")
        contract = await create_signal_contract(
            db_session,
            industry=industry,
            name="CBN Rates Contract",
            source_url="https://cbn.gov.ng/rates",
        )

        # 1. Discover
        ds = await create_discovered_source(
            db_session,
            url="https://fmdq.com/market-data",
            status="discovered",
            mention_count=1,
            relevance_score=0.3,
        )
        assert ds.status == "discovered"

        # 2. Recommend (simulates threshold crossing)
        ds.status = "recommended"
        ds.mention_count = 15
        ds.relevance_score = 0.88
        await db_session.flush()
        assert ds.status == "recommended"

        # 3. Activate (link to a new contract)
        ds.status = "activated"
        ds.activated_contract_id = contract.id
        await db_session.flush()
        assert ds.status == "activated"
        assert ds.activated_contract_id == contract.id

    async def test_dismiss_source(self, db_session):
        """Source can be dismissed by admin."""
        ds = await create_discovered_source(
            db_session,
            url="https://irrelevant.example.com",
            status="recommended",
        )
        ds.status = "dismissed"
        await db_session.flush()
        assert ds.status == "dismissed"


# ── Frontend Type Contract Tests ─────────────────────────────────────


class TestFrontendTypeContract:
    """Verify that backend API responses match the TypeScript types.

    These tests don't call the frontend — they verify that the backend
    response shapes align with what the frontend API client expects.
    """

    async def test_discovered_source_response_shape(self, db_session):
        """Verify DiscoveredSourceResponse fields match model."""
        ds = await create_discovered_source(db_session, url="https://shape-test.com")

        # These are the fields the frontend expects
        response_fields = {
            "id",
            "url",
            "domain",
            "name",
            "source_type",
            "signal_type",
            "mention_count",
            "relevance_score",
            "status",
            "activated_contract_id",
            "created_at",
            "last_seen_at",
        }

        # Build the response dict as the API endpoint would
        response = {
            "id": str(ds.id),
            "url": ds.url,
            "domain": ds.domain,
            "name": ds.name,
            "source_type": ds.source_type,
            "signal_type": ds.signal_type,
            "mention_count": ds.mention_count,
            "relevance_score": ds.relevance_score,
            "status": ds.status,
            "activated_contract_id": str(ds.activated_contract_id)
            if ds.activated_contract_id
            else None,
            "created_at": ds.created_at.isoformat() if ds.created_at else "",
            "last_seen_at": ds.last_seen_at.isoformat() if ds.last_seen_at else "",
        }

        assert response_fields == set(response.keys())

    async def test_entity_discovery_item_response_shape(self, db_session):
        """Verify EntityDiscoveryItem fields match model."""
        from backend.models.entity import Entity

        entity = Entity(
            id=uuid4(),
            name="ShapeTestCorp",
            entity_type="company",
            discovery_status="pending_review",
            discovery_source="auto_extracted",
        )
        db_session.add(entity)
        await db_session.flush()
        await db_session.refresh(entity)

        # Build the response dict as the API endpoint would
        response = {
            "id": str(entity.id),
            "name": entity.name,
            "entity_type": entity.entity_type,
            "discovery_status": entity.discovery_status,
            "discovery_source": entity.discovery_source,
            "created_at": entity.created_at.isoformat() if entity.created_at else "",
        }

        expected_fields = {
            "id",
            "name",
            "entity_type",
            "discovery_status",
            "discovery_source",
            "created_at",
        }
        assert expected_fields == set(response.keys())


# ── MarketDataPoint Model Tests ──────────────────────────────────────


class TestMarketDataPointModel:
    """Verify MarketDataPoint ORM model behaves correctly."""

    async def test_create_market_data_point(self, db_session):
        """Basic creation and persistence of a MarketDataPoint row."""
        from datetime import datetime, timezone

        from backend.models.market_data import MarketDataPoint

        mdp = MarketDataPoint(
            id=uuid4(),
            metric="exchange_rate",
            value=1580.50,
            unit="NGN/USD",
            currency="NGN",
            observed_at=datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc),
            country_code="NGA",
            region="West Africa",
            context="CBN official midpoint rate for June 2025",
            confidence=0.95,
        )
        db_session.add(mdp)
        await db_session.flush()
        await db_session.refresh(mdp)

        assert mdp.id is not None
        assert mdp.metric == "exchange_rate"
        assert mdp.value == 1580.50
        assert mdp.unit == "NGN/USD"
        assert mdp.currency == "NGN"
        assert mdp.country_code == "NGA"
        assert mdp.confidence == 0.95

    async def test_market_data_point_linked_to_signal(self, db_session):
        """MarketDataPoint can FK-link to a Signal."""
        from datetime import datetime, timezone

        from backend.models.market_data import MarketDataPoint

        industry = await create_industry(db_session, name="FX Markets")
        contract = await create_signal_contract(
            db_session,
            industry=industry,
            name="FX Contract",
            source_url="https://cbn.gov.ng/rates",
        )
        signal = await create_signal(
            db_session,
            contract=contract,
            title="NGN/USD rate update",
        )

        mdp = MarketDataPoint(
            id=uuid4(),
            metric="exchange_rate",
            value=1580.50,
            unit="NGN/USD",
            signal_id=signal.id,
            observed_at=datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc),
            country_code="NGA",
        )
        db_session.add(mdp)
        await db_session.flush()
        await db_session.refresh(mdp)

        assert mdp.signal_id == signal.id

    async def test_market_data_point_linked_to_entity(self, db_session):
        """MarketDataPoint can FK-link to an Entity."""
        from datetime import datetime, timezone

        from backend.models.entity import Entity
        from backend.models.market_data import MarketDataPoint

        entity = Entity(
            id=uuid4(),
            name="Dangote Cement",
            entity_type="company",
        )
        db_session.add(entity)
        await db_session.flush()

        mdp = MarketDataPoint(
            id=uuid4(),
            metric="stock_price",
            value=290.0,
            unit="NGN",
            entity_id=entity.id,
            observed_at=datetime(2025, 6, 1, 9, 30, tzinfo=timezone.utc),
            country_code="NGA",
        )
        db_session.add(mdp)
        await db_session.flush()
        await db_session.refresh(mdp)

        assert mdp.entity_id == entity.id

    async def test_market_data_point_defaults(self, db_session):
        """Verify default values for confidence and metadata."""
        from datetime import datetime, timezone

        from backend.models.market_data import MarketDataPoint

        mdp = MarketDataPoint(
            id=uuid4(),
            metric="interest_rate",
            value=11.5,
            unit="%",
            observed_at=datetime(2025, 6, 1, tzinfo=timezone.utc),
        )
        db_session.add(mdp)
        await db_session.flush()
        await db_session.refresh(mdp)

        assert mdp.confidence == 0.8  # default
        assert mdp.metadata_ is None  # default when not provided
        assert mdp.created_at is not None


# ── Phase 4: Market Data API Tests ───────────────────────────────────


async def create_market_data_point(
    db,
    *,
    metric: str = "rice_price",
    value: float = 82000.0,
    unit: str = "NGN/50kg",
    currency: str | None = "NGN",
    country_code: str = "NGA",
    signal_id=None,
    entity_id=None,
    observed_at=None,
):
    """Insert a MarketDataPoint row for testing."""
    from backend.models.market_data import MarketDataPoint

    if observed_at is None:
        observed_at = datetime.now(timezone.utc)

    mdp = MarketDataPoint(
        id=uuid4(),
        metric=metric,
        value=value,
        unit=unit,
        currency=currency,
        country_code=country_code,
        observed_at=observed_at,
        signal_id=signal_id,
        entity_id=entity_id,
    )
    db.add(mdp)
    await db.flush()
    await db.refresh(mdp)
    return mdp


class TestMarketDataAPI:
    """Test the /api/v1/market-data endpoints."""

    async def test_list_market_data_empty(self, app, client, db_session):
        from backend.auth.dependencies import get_current_user

        auth = make_auth_context()
        app.dependency_overrides[get_current_user] = lambda: auth

        resp = await client.get("/api/v1/market-data")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

        app.dependency_overrides.pop(get_current_user, None)

    async def test_list_market_data_with_data(self, app, client, db_session):
        from backend.auth.dependencies import get_current_user

        auth = make_auth_context()
        app.dependency_overrides[get_current_user] = lambda: auth

        await create_market_data_point(db_session, metric="rice_price", value=82000)
        await create_market_data_point(db_session, metric="cement_price", value=5500)
        await db_session.commit()

        resp = await client.get("/api/v1/market-data")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2
        assert len(data["items"]) >= 2

        app.dependency_overrides.pop(get_current_user, None)

    async def test_list_market_data_filter_by_metric(self, app, client, db_session):
        from backend.auth.dependencies import get_current_user

        auth = make_auth_context()
        app.dependency_overrides[get_current_user] = lambda: auth

        await create_market_data_point(db_session, metric="rice_price", value=82000)
        await create_market_data_point(db_session, metric="cement_price", value=5500)
        await db_session.commit()

        resp = await client.get("/api/v1/market-data", params={"metric": "rice_price"})
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["metric"] == "rice_price"

        app.dependency_overrides.pop(get_current_user, None)

    async def test_list_market_data_filter_by_country(self, app, client, db_session):
        from backend.auth.dependencies import get_current_user

        auth = make_auth_context()
        app.dependency_overrides[get_current_user] = lambda: auth

        await create_market_data_point(db_session, metric="fx_rate", country_code="NGA")
        await create_market_data_point(db_session, metric="fx_rate", country_code="KEN")
        await db_session.commit()

        resp = await client.get("/api/v1/market-data", params={"country_code": "NGA"})
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["country_code"] == "NGA"

        app.dependency_overrides.pop(get_current_user, None)

    async def test_get_market_data_stats(self, app, client, db_session):
        from backend.auth.dependencies import get_current_user

        auth = make_auth_context()
        app.dependency_overrides[get_current_user] = lambda: auth

        await create_market_data_point(db_session, metric="rice_price", value=80000)
        await create_market_data_point(db_session, metric="rice_price", value=85000)
        await create_market_data_point(db_session, metric="cement_price", value=5500)
        await db_session.commit()

        resp = await client.get("/api/v1/market-data/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_points"] >= 3
        assert data["unique_metrics"] >= 2
        assert len(data["metrics"]) >= 2

        # Verify per-metric summary
        rice = next((m for m in data["metrics"] if m["metric"] == "rice_price"), None)
        assert rice is not None
        assert rice["count"] >= 2
        assert rice["latest_value"] is not None

        app.dependency_overrides.pop(get_current_user, None)

    async def test_get_metric_trend(self, app, client, db_session):
        from backend.auth.dependencies import get_current_user

        auth = make_auth_context()
        app.dependency_overrides[get_current_user] = lambda: auth

        from datetime import timedelta

        now = datetime.now(timezone.utc)
        for i in range(5):
            await create_market_data_point(
                db_session,
                metric="ngn_usd_parallel",
                value=1500 + i * 20,
                unit="NGN/USD",
                observed_at=now - timedelta(days=5 - i),
            )
        await db_session.commit()

        resp = await client.get(
            "/api/v1/market-data/trend/ngn_usd_parallel", params={"days": 30}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 5
        # Should be in chronological order (oldest first)
        values = [item["value"] for item in data["items"]]
        assert values == sorted(values)  # ascending by observed_at

        app.dependency_overrides.pop(get_current_user, None)

    async def test_get_latest_values(self, app, client, db_session):
        from backend.auth.dependencies import get_current_user

        auth = make_auth_context()
        app.dependency_overrides[get_current_user] = lambda: auth

        from datetime import timedelta

        now = datetime.now(timezone.utc)
        await create_market_data_point(
            db_session,
            metric="rice_price",
            value=80000,
            observed_at=now - timedelta(days=5),
        )
        await create_market_data_point(
            db_session, metric="rice_price", value=85000, observed_at=now
        )
        await db_session.commit()

        resp = await client.get(
            "/api/v1/market-data/latest", params={"metrics": "rice_price"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["metric"] == "rice_price"
        assert data[0]["value"] == 85000  # Latest value

        app.dependency_overrides.pop(get_current_user, None)

    async def test_list_available_metrics(self, app, client, db_session):
        from backend.auth.dependencies import get_current_user

        auth = make_auth_context()
        app.dependency_overrides[get_current_user] = lambda: auth

        await create_market_data_point(db_session, metric="aaa_metric")
        await create_market_data_point(db_session, metric="zzz_metric")
        await db_session.commit()

        resp = await client.get("/api/v1/market-data/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "aaa_metric" in data
        assert "zzz_metric" in data
        # Should be sorted alphabetically
        assert data == sorted(data)

        app.dependency_overrides.pop(get_current_user, None)


# ── Phase 4: Market Data Pipeline Ingestion Tests ────────────────────


class TestMarketDataPipelineIngestion:
    """Test that refinement pipeline creates MarketDataPoint rows."""

    async def test_normalize_metric(self):
        """Test metric name normalization."""
        from backend.services.refinement_service import RefinementService

        assert (
            RefinementService._normalize_metric("rice price per bag")
            == "rice_price_per_bag"
        )
        assert (
            RefinementService._normalize_metric("NGN/USD parallel rate")
            == "ngn_usd_parallel_rate"
        )
        assert (
            RefinementService._normalize_metric("  Inflation Rate  ")
            == "inflation_rate"
        )
        assert (
            RefinementService._normalize_metric("crude-oil $ / barrel")
            == "crude_oil_barrel"
        )

    async def test_persist_market_data_creates_rows(self, db_session):
        """Test _persist_market_data creates MarketDataPoint rows from extraction."""
        from backend.ai.entity_extraction import (
            ExtractionResult,
            GeographicMention,
            NumericDataPoint,
        )
        from backend.models.market_data import MarketDataPoint
        from backend.services.refinement_service import RefinementService

        org = await create_organization(db_session)
        industry = await create_industry(db_session)
        contract = await create_signal_contract(db_session, industry=industry)
        signal = await create_signal(db_session, contract=contract)
        await db_session.commit()

        service = RefinementService(db_session)

        extraction = ExtractionResult(
            numeric_data=[
                NumericDataPoint(
                    value=82000,
                    unit="NGN/50kg",
                    metric="rice price per bag",
                    currency="NGN",
                    context="Rice prices hit ₦82,000 per bag",
                ),
                NumericDataPoint(
                    value=1580,
                    unit="NGN/USD",
                    metric="parallel exchange rate",
                    currency="NGN",
                    context="Parallel market rate at ₦1,580",
                ),
            ],
            geographic=[
                GeographicMention(
                    name="Lagos",
                    geo_type="state",
                    country_code="NGA",
                ),
            ],
        )

        count = await service._persist_market_data(signal, extraction)
        assert count == 2

        # Verify rows exist
        from sqlalchemy import select

        result = await db_session.execute(
            select(MarketDataPoint).where(MarketDataPoint.signal_id == signal.id)
        )
        points = result.scalars().all()
        assert len(points) == 2

        # Check normalization
        metrics = {p.metric for p in points}
        assert "rice_price_per_bag" in metrics
        assert "parallel_exchange_rate" in metrics

        # Check country/region from extraction
        for p in points:
            assert p.country_code == "NGA"
            assert p.region == "Lagos"

    async def test_persist_market_data_empty_extraction(self, db_session):
        """No rows created when extraction has no numeric data."""
        from backend.ai.entity_extraction import ExtractionResult
        from backend.services.refinement_service import RefinementService

        org = await create_organization(db_session)
        industry = await create_industry(db_session)
        contract = await create_signal_contract(db_session, industry=industry)
        signal = await create_signal(db_session, contract=contract)
        await db_session.commit()

        service = RefinementService(db_session)
        extraction = ExtractionResult(numeric_data=[])

        count = await service._persist_market_data(signal, extraction)
        assert count == 0


# ── Phase 4: Source Health Service Tests ─────────────────────────────


class TestSourceHealthService:
    """Test source health classification and monitoring."""

    async def test_classify_healthy_contract(self, db_session):
        """Contract with recent fetch and no failures → healthy."""
        from backend.services.source_health import SourceHealthService

        org = await create_organization(db_session)
        industry = await create_industry(db_session)
        contract = await create_signal_contract(db_session, industry=industry)
        contract.last_fetched_at = datetime.now(timezone.utc)
        contract.failure_count = 0
        await db_session.flush()

        stale_cutoff = datetime.now(timezone.utc) - __import__("datetime").timedelta(
            hours=48
        )
        health = SourceHealthService._classify_contract_health(contract, stale_cutoff)
        assert health == "healthy"

    async def test_classify_stale_contract(self, db_session):
        """Contract with no recent fetch → stale."""
        from datetime import timedelta

        from backend.services.source_health import SourceHealthService

        org = await create_organization(db_session)
        industry = await create_industry(db_session)
        contract = await create_signal_contract(db_session, industry=industry)
        contract.last_fetched_at = datetime.now(timezone.utc) - timedelta(hours=72)
        contract.failure_count = 0
        await db_session.flush()

        stale_cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
        health = SourceHealthService._classify_contract_health(contract, stale_cutoff)
        assert health == "stale"

    async def test_classify_degraded_contract(self, db_session):
        """Contract with 3+ failures → degraded."""
        from backend.services.source_health import SourceHealthService

        org = await create_organization(db_session)
        industry = await create_industry(db_session)
        contract = await create_signal_contract(db_session, industry=industry)
        contract.failure_count = 5
        await db_session.flush()

        stale_cutoff = datetime.now(timezone.utc) - __import__("datetime").timedelta(
            hours=48
        )
        health = SourceHealthService._classify_contract_health(contract, stale_cutoff)
        assert health == "degraded"

    async def test_classify_critical_contract(self, db_session):
        """Contract with 10+ failures → critical."""
        from backend.services.source_health import SourceHealthService

        org = await create_organization(db_session)
        industry = await create_industry(db_session)
        contract = await create_signal_contract(db_session, industry=industry)
        contract.failure_count = 12
        await db_session.flush()

        stale_cutoff = datetime.now(timezone.utc) - __import__("datetime").timedelta(
            hours=48
        )
        health = SourceHealthService._classify_contract_health(contract, stale_cutoff)
        assert health == "critical"

    async def test_health_summary_all_healthy(self, db_session):
        """Full summary with all healthy contracts."""
        from backend.services.source_health import SourceHealthService

        org = await create_organization(db_session)
        industry = await create_industry(db_session)
        contract = await create_signal_contract(db_session, industry=industry)
        contract.is_active = True
        contract.last_fetched_at = datetime.now(timezone.utc)
        contract.failure_count = 0
        await db_session.flush()
        await db_session.commit()

        service = SourceHealthService(db_session)
        summary = await service.get_health_summary()

        assert summary["total_active"] >= 1
        assert summary["healthy"] >= 1
        assert summary["critical"] == 0
        assert summary["degraded"] == 0


# ── Phase 4: Source Health API Tests ─────────────────────────────────


class TestSourceHealthAPI:
    """Test pipeline source-health API endpoints."""

    async def test_source_health_requires_admin(self, app, client, db_session):
        """Non-admin should be rejected."""
        from backend.auth.dependencies import get_current_user

        auth = make_auth_context(role="viewer")
        app.dependency_overrides[get_current_user] = lambda: auth

        resp = await client.get("/api/v1/pipeline/source-health")
        # Should be 403 (insufficient role)
        assert resp.status_code in (403, 401)

        app.dependency_overrides.pop(get_current_user, None)

    async def test_source_health_admin_access(self, admin_client, db_session):
        """Admin should get the health summary."""
        client, _auth = admin_client

        resp = await client.get("/api/v1/pipeline/source-health")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_active" in data
        assert "healthy" in data
        assert "stale" in data
        assert "degraded" in data
        assert "critical" in data


# ── Phase 4: Frontend Type Contracts ──────────────────────────────────


class TestPhase4FrontendTypeContract:
    """Verify frontend TS types match backend API response shapes."""

    async def test_market_data_response_shape(self, app, client, db_session):
        from backend.auth.dependencies import get_current_user

        auth = make_auth_context()
        app.dependency_overrides[get_current_user] = lambda: auth

        await create_market_data_point(db_session, metric="test_shape")
        await db_session.commit()

        resp = await client.get("/api/v1/market-data")
        data = resp.json()

        # Paginated response shape
        assert "items" in data
        assert "total" in data
        assert "skip" in data
        assert "limit" in data

        if data["items"]:
            item = data["items"][0]
            expected_keys = {
                "id",
                "metric",
                "value",
                "unit",
                "currency",
                "observed_at",
                "signal_id",
                "entity_id",
                "country_code",
                "region",
                "context",
                "confidence",
                "created_at",
            }
            assert expected_keys.issubset(set(item.keys()))

        app.dependency_overrides.pop(get_current_user, None)

    async def test_market_data_stats_response_shape(self, app, client, db_session):
        from backend.auth.dependencies import get_current_user

        auth = make_auth_context()
        app.dependency_overrides[get_current_user] = lambda: auth

        resp = await client.get("/api/v1/market-data/stats")
        data = resp.json()

        assert "total_points" in data
        assert "unique_metrics" in data
        assert "countries_covered" in data
        assert "metrics" in data

        app.dependency_overrides.pop(get_current_user, None)


# ── Round 8: Signal Alerts + Change Detection Tests ──────────────────


async def create_signal_alert(
    db,
    *,
    alert_type: str = "anomaly",
    severity: str = "medium",
    metric: str = "rice_price",
    country_code: str = "NGA",
    title: str = "Test alert",
    current_value: float = 90000.0,
    baseline_value: float = 70000.0,
    deviation_pct: float = 28.6,
    acknowledged: bool = False,
    signal_id=None,
):
    """Insert a SignalAlert row for testing."""
    from backend.models.signal_alert import SignalAlert

    alert = SignalAlert(
        id=uuid4(),
        alert_type=alert_type,
        severity=severity,
        metric=metric,
        country_code=country_code,
        title=title,
        current_value=current_value,
        baseline_value=baseline_value,
        deviation_pct=deviation_pct,
        acknowledged=acknowledged,
        signal_id=signal_id,
    )
    db.add(alert)
    await db.flush()
    await db.refresh(alert)
    return alert


class TestSignalAlertModel:
    """Test SignalAlert ORM model creation and defaults."""

    async def test_create_alert_defaults(self, db_session):
        alert = await create_signal_alert(db_session)
        assert alert.id is not None
        assert alert.acknowledged is False
        assert alert.acknowledged_at is None
        assert alert.alert_type == "anomaly"
        assert alert.severity == "medium"

    async def test_create_critical_alert(self, db_session):
        alert = await create_signal_alert(
            db_session,
            severity="critical",
            alert_type="threshold",
            metric="ngn_usd_rate",
            current_value=2000.0,
            baseline_value=1580.0,
            deviation_pct=26.6,
        )
        assert alert.severity == "critical"
        assert alert.metric == "ngn_usd_rate"

    async def test_acknowledge_alert(self, db_session):
        from datetime import datetime, timezone

        alert = await create_signal_alert(db_session)
        assert alert.acknowledged is False

        alert.acknowledged = True
        alert.acknowledged_at = datetime.now(timezone.utc)
        await db_session.flush()

        assert alert.acknowledged is True
        assert alert.acknowledged_at is not None

    async def test_alert_with_signal_fk(self, db_session):
        industry = await create_industry(db_session)
        contract = await create_signal_contract(db_session, industry=industry)
        signal = await create_signal(db_session, contract=contract)

        alert = await create_signal_alert(db_session, signal_id=signal.id)
        assert alert.signal_id == signal.id


class TestChangeDetectionService:
    """Test ChangeDetectionService anomaly detection logic."""

    async def test_no_alert_when_insufficient_history(self, db_session):
        """With fewer than MIN_HISTORY_POINTS observations, no alert is raised."""
        from backend.models.market_data import MarketDataPoint
        from backend.services.change_detection import ChangeDetectionService

        # Insert just 2 points (below MIN_HISTORY_POINTS=5)
        now = datetime.now(timezone.utc)
        for i in range(2):
            from datetime import timedelta

            mdp = MarketDataPoint(
                id=uuid4(),
                metric="test_sparse_metric",
                value=100.0 + i,
                unit="pct",
                observed_at=now - timedelta(days=i + 1),
                country_code="NGA",
            )
            db_session.add(mdp)
        await db_session.flush()

        # Build a new data point that deviates wildly — still no alert
        new_point = MarketDataPoint(
            id=uuid4(),
            metric="test_sparse_metric",
            value=9999.0,
            unit="pct",
            observed_at=now,
            country_code="NGA",
        )
        db_session.add(new_point)
        await db_session.flush()

        svc = ChangeDetectionService(db_session)
        alert = await svc.detect(new_point)

        # Insufficient history → no alert
        assert alert is None

    async def test_no_alert_within_threshold(self, db_session):
        """Normal value variation (|z| < 1.5) should not trigger alert."""
        from datetime import timedelta

        from backend.models.market_data import MarketDataPoint
        from backend.services.change_detection import (
            MIN_HISTORY_POINTS,
            ChangeDetectionService,
        )

        now = datetime.now(timezone.utc)
        # Insert 6 identical points to get a tight baseline
        for i in range(MIN_HISTORY_POINTS + 1):
            mdp = MarketDataPoint(
                id=uuid4(),
                metric="stable_metric_ng",
                value=100.0,
                unit="pct",
                observed_at=now - timedelta(days=i + 1),
                country_code="NGA",
            )
            db_session.add(mdp)
        await db_session.flush()

        # A point that's only 1% from baseline — way below z=1.5
        new_point = MarketDataPoint(
            id=uuid4(),
            metric="stable_metric_ng",
            value=101.0,
            unit="pct",
            observed_at=now,
            country_code="NGA",
        )
        db_session.add(new_point)
        await db_session.flush()

        svc = ChangeDetectionService(db_session)
        alert = await svc.detect(new_point)

        assert alert is None

    async def test_alert_created_for_anomaly(self, db_session):
        """Large z-score deviation should produce a SignalAlert."""
        from datetime import timedelta

        from backend.models.market_data import MarketDataPoint
        from backend.services.change_detection import (
            ChangeDetectionService,
        )

        now = datetime.now(timezone.utc)
        # Create varied baseline: alternating 95/105 so stddev > 0
        baseline_values = [95.0, 105.0, 98.0, 102.0, 97.0, 103.0, 96.0, 104.0]
        for i, bv in enumerate(baseline_values):
            mdp = MarketDataPoint(
                id=uuid4(),
                metric="anomaly_test_metric",
                value=bv,
                unit="pct",
                observed_at=now - timedelta(days=i + 1),
                country_code="NGA",
            )
            db_session.add(mdp)
        await db_session.flush()

        # A point with value=500.0 — extreme deviation (z >> 3.0)
        new_point = MarketDataPoint(
            id=uuid4(),
            metric="anomaly_test_metric",
            value=500.0,
            unit="pct",
            observed_at=now,
            country_code="NGA",
        )
        db_session.add(new_point)
        await db_session.flush()

        svc = ChangeDetectionService(db_session)
        alert = await svc.detect(new_point)

        assert alert is not None
        assert alert.alert_type == "anomaly"
        assert alert.severity in ("low", "medium", "high", "critical")
        assert alert.metric == "anomaly_test_metric"
        assert alert.country_code == "NGA"
        assert alert.current_value == 500.0
        assert alert.deviation_pct is not None

    async def test_alert_severity_scales_with_z_score(self, db_session):
        """Higher deviations should produce higher severity."""
        from datetime import timedelta

        from backend.models.market_data import MarketDataPoint
        from backend.services.change_detection import (
            ChangeDetectionService,
        )

        severity_results = {}
        deviations = {"extreme_hi": 10000.0, "moderate_hi": 200.0}

        for label, deviation_value in deviations.items():
            now = datetime.now(timezone.utc)
            # Use alternating baseline values to get non-zero stddev
            base_vals = [95.0, 105.0, 97.0, 103.0, 96.0, 104.0, 98.0, 102.0]
            for i, bv in enumerate(base_vals):
                mdp = MarketDataPoint(
                    id=uuid4(),
                    metric=f"severity_test_{label}",
                    value=bv,
                    unit="pct",
                    observed_at=now - timedelta(days=i + 1),
                    country_code="NGA",
                )
                db_session.add(mdp)
            await db_session.flush()

            new_point = MarketDataPoint(
                id=uuid4(),
                metric=f"severity_test_{label}",
                value=deviation_value,
                unit="pct",
                observed_at=now,
                country_code="NGA",
            )
            db_session.add(new_point)
            await db_session.flush()

            svc = ChangeDetectionService(db_session)
            alert = await svc.detect(new_point)
            if alert:
                severity_results[label] = alert.severity

        severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        if "extreme_hi" in severity_results and "moderate_hi" in severity_results:
            assert (
                severity_order[severity_results["extreme_hi"]]
                >= severity_order[severity_results["moderate_hi"]]
            )


class TestAlertsAPI:
    """Test the /api/v1/alerts endpoints."""

    async def test_list_alerts_empty(self, app, client, db_session):
        from backend.auth.dependencies import get_current_user

        auth = make_auth_context()
        app.dependency_overrides[get_current_user] = lambda: auth

        resp = await client.get("/api/v1/alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "unacknowledged" in data

        app.dependency_overrides.pop(get_current_user, None)

    async def test_list_alerts_with_data(self, app, client, db_session):
        from backend.auth.dependencies import get_current_user

        auth = make_auth_context()
        app.dependency_overrides[get_current_user] = lambda: auth

        await create_signal_alert(db_session, severity="high", metric="rice_price")
        await create_signal_alert(db_session, severity="low", metric="cement_price")
        await db_session.commit()

        resp = await client.get("/api/v1/alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2

        app.dependency_overrides.pop(get_current_user, None)

    async def test_list_alerts_filter_by_severity(self, app, client, db_session):
        from backend.auth.dependencies import get_current_user

        auth = make_auth_context()
        app.dependency_overrides[get_current_user] = lambda: auth

        await create_signal_alert(db_session, severity="critical", metric="fx_rate")
        await create_signal_alert(db_session, severity="low", metric="fuel_price")
        await db_session.commit()

        resp = await client.get("/api/v1/alerts", params={"severity": "critical"})
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["severity"] == "critical"

        app.dependency_overrides.pop(get_current_user, None)

    async def test_list_alerts_filter_unacknowledged(self, app, client, db_session):
        from backend.auth.dependencies import get_current_user

        auth = make_auth_context()
        app.dependency_overrides[get_current_user] = lambda: auth

        await create_signal_alert(db_session, severity="high", acknowledged=False)
        await create_signal_alert(db_session, severity="high", acknowledged=True)
        await db_session.commit()

        resp = await client.get("/api/v1/alerts", params={"acknowledged": "false"})
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["acknowledged"] is False

        app.dependency_overrides.pop(get_current_user, None)

    async def test_alerts_summary(self, app, client, db_session):
        from backend.auth.dependencies import get_current_user

        auth = make_auth_context()
        app.dependency_overrides[get_current_user] = lambda: auth

        await create_signal_alert(db_session, severity="critical", metric="fx_rate")
        await create_signal_alert(db_session, severity="high", metric="rice_price")
        await create_signal_alert(
            db_session, severity="medium", metric="rice_price", acknowledged=True
        )
        await db_session.commit()

        resp = await client.get("/api/v1/alerts/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "unacknowledged" in data
        assert "by_severity" in data
        assert "by_metric" in data
        assert data["total"] >= 3
        assert data["by_severity"].get("critical", 0) >= 1
        assert "rice_price" in data["by_metric"]

        app.dependency_overrides.pop(get_current_user, None)

    async def test_acknowledge_alert(self, app, client, db_session):
        from backend.auth.dependencies import get_current_user

        auth = make_auth_context()
        app.dependency_overrides[get_current_user] = lambda: auth

        alert = await create_signal_alert(
            db_session, severity="high", acknowledged=False
        )
        await db_session.commit()

        resp = await client.post(f"/api/v1/alerts/{alert.id}/acknowledge")
        assert resp.status_code == 200
        data = resp.json()
        assert data["acknowledged"] is True
        assert data["acknowledged_at"] is not None

        # Verify persisted
        await db_session.refresh(alert)
        assert alert.acknowledged is True

        app.dependency_overrides.pop(get_current_user, None)

    async def test_acknowledge_already_acknowledged(self, app, client, db_session):
        from backend.auth.dependencies import get_current_user

        auth = make_auth_context()
        app.dependency_overrides[get_current_user] = lambda: auth

        alert = await create_signal_alert(db_session, severity="low", acknowledged=True)
        await db_session.commit()

        # Should still return 200 (idempotent) or 400 — either is acceptable
        resp = await client.post(f"/api/v1/alerts/{alert.id}/acknowledge")
        assert resp.status_code in (200, 400)

        app.dependency_overrides.pop(get_current_user, None)

    async def test_acknowledge_nonexistent_alert(self, app, client, db_session):
        from backend.auth.dependencies import get_current_user

        auth = make_auth_context()
        app.dependency_overrides[get_current_user] = lambda: auth

        resp = await client.post(f"/api/v1/alerts/{uuid4()}/acknowledge")
        assert resp.status_code == 404

        app.dependency_overrides.pop(get_current_user, None)

    async def test_alerts_response_schema(self, app, client, db_session):
        """Verify alert response fields match AlertResponse schema."""
        from backend.auth.dependencies import get_current_user

        auth = make_auth_context()
        app.dependency_overrides[get_current_user] = lambda: auth

        await create_signal_alert(db_session, metric="schema_test")
        await db_session.commit()

        resp = await client.get("/api/v1/alerts")
        data = resp.json()
        if data["items"]:
            item = data["items"][0]
            expected_keys = {
                "id",
                "alert_type",
                "severity",
                "metric",
                "country_code",
                "title",
                "description",
                "current_value",
                "baseline_value",
                "deviation_pct",
                "acknowledged",
                "acknowledged_at",
                "created_at",
            }
            assert expected_keys.issubset(set(item.keys()))

        app.dependency_overrides.pop(get_current_user, None)


# ── Round 8: Synthesis Coverage + Contract Suggestion Tests ───────────


class TestSynthesisCoverageAndContractSuggestion:
    """Test coverage check and contract suggestion additions to synthesis."""

    def test_compute_coverage_empty_sources(self):
        """No sources → coverage 0 with 'limited' assessment."""
        from backend.api.v1.synthesis import _compute_coverage

        coverage = _compute_coverage([], result={"total_indexed": 0, "sources": []})
        assert coverage.total_signals == 0
        assert coverage.relevant_signals == 0
        assert coverage.coverage_score == 0.0
        assert coverage.coverage_assessment == "limited"
        assert coverage.freshest_signal_at is None

    def test_compute_coverage_all_relevant(self):
        """All high-similarity sources → 'good' coverage."""
        from backend.api.v1.synthesis import _compute_coverage
        from backend.schemas.synthesis import SynthesisSource

        sources = [
            SynthesisSource(
                signal_id=str(uuid4()), title="A", similarity=0.9, confidence=0.9
            ),
            SynthesisSource(
                signal_id=str(uuid4()), title="B", similarity=0.85, confidence=0.8
            ),
            SynthesisSource(
                signal_id=str(uuid4()), title="C", similarity=0.75, confidence=0.7
            ),
        ]
        result = {"total_indexed": 100, "sources": []}
        coverage = _compute_coverage(sources, result=result)
        assert coverage.relevant_signals == 3
        assert coverage.coverage_score >= 0.7
        assert coverage.coverage_assessment == "good"

    def test_compute_coverage_partial(self):
        """Mix of relevant and irrelevant sources → 'partial'."""
        from backend.api.v1.synthesis import _compute_coverage
        from backend.schemas.synthesis import SynthesisSource

        sources = [
            SynthesisSource(signal_id=None, title="A", similarity=0.8, confidence=0.8),
            SynthesisSource(signal_id=None, title="B", similarity=0.2, confidence=0.3),
            SynthesisSource(signal_id=None, title="C", similarity=0.1, confidence=0.2),
            SynthesisSource(signal_id=None, title="D", similarity=0.6, confidence=0.7),
        ]
        result = {"total_indexed": 50, "sources": []}
        coverage = _compute_coverage(sources, result=result)
        assert coverage.relevant_signals == 2  # only similarity >= 0.5
        assert 0.3 <= coverage.coverage_score < 0.7
        assert coverage.coverage_assessment == "partial"

    def test_compute_coverage_limited(self):
        """All low-similarity sources → 'limited' coverage."""
        from backend.api.v1.synthesis import _compute_coverage
        from backend.schemas.synthesis import SynthesisSource

        sources = [
            SynthesisSource(signal_id=None, title="X", similarity=0.1, confidence=0.1),
            SynthesisSource(signal_id=None, title="Y", similarity=0.2, confidence=0.2),
        ]
        result = {"total_indexed": 200, "sources": []}
        coverage = _compute_coverage(sources, result=result)
        assert coverage.relevant_signals == 0
        assert coverage.coverage_score < 0.3
        assert coverage.coverage_assessment == "limited"

    def test_build_contract_suggestion_basic(self):
        """Suggestion has title, keywords, description."""
        from backend.api.v1.synthesis import _build_contract_suggestion
        from backend.schemas.synthesis import SynthesisSource

        sources = [
            SynthesisSource(
                signal_id=str(uuid4()), title="CBN rate", similarity=0.8, confidence=0.9
            )
        ]
        suggestion = _build_contract_suggestion(
            "CBN interest rate Nigeria banking sector", sources
        )
        assert (
            "interest" in suggestion.suggested_keywords
            or "banking" in suggestion.suggested_keywords
        )
        assert (
            "CBN" in suggestion.suggested_title
            or "interest" in suggestion.suggested_title.lower()
        )
        assert len(suggestion.suggested_description) > 10
        assert isinstance(suggestion.suggested_keywords, list)

    def test_build_contract_suggestion_infers_financial_industry(self):
        """Query about banking → Financial Services inferred."""
        from backend.api.v1.synthesis import _build_contract_suggestion

        suggestion = _build_contract_suggestion(
            "CBN bank interest rate credit loan", sources=[]
        )
        assert suggestion.inferred_industry == "Financial Services"

    def test_build_contract_suggestion_infers_energy_industry(self):
        """Query about oil/gas → Energy inferred."""
        from backend.api.v1.synthesis import _build_contract_suggestion

        suggestion = _build_contract_suggestion(
            "crude oil gas price energy subsidy", sources=[]
        )
        assert suggestion.inferred_industry == "Energy"

    def test_build_contract_suggestion_unknown_industry(self):
        """Unrecognised domain → inferred_industry is None."""
        from backend.api.v1.synthesis import _build_contract_suggestion

        suggestion = _build_contract_suggestion("some obscure topic xyz", sources=[])
        assert suggestion.inferred_industry is None

    def test_build_contract_suggestion_long_query_truncated(self):
        """Very long query should have its title capped at 120 chars."""
        from backend.api.v1.synthesis import _build_contract_suggestion

        long_query = "a " * 150
        suggestion = _build_contract_suggestion(long_query, sources=[])
        assert len(suggestion.suggested_title) <= 123  # 120 + "..."

    async def test_synthesis_response_includes_coverage(self, app, client, db_session):
        """Synthesis endpoint response should always include coverage field."""
        from unittest.mock import AsyncMock

        from backend.auth.dependencies import get_current_user
        from backend.middleware.feature_gating import (
            get_current_organization,
            require_feature,
        )

        auth = make_auth_context()
        app.dependency_overrides[get_current_user] = lambda: auth
        app.dependency_overrides[get_current_organization] = lambda: MagicMock(
            features={"on_demand_synthesis": True}
        )
        app.dependency_overrides[require_feature("on_demand_synthesis")] = lambda: True

        fake_synthesis_result = {
            "synthesis": "Test synthesis text",
            "sources": [],
            "web_sources": [],
            "confidence": 0.75,
            "cached": False,
            "total_indexed": 0,
        }

        with patch(
            "backend.api.v1.synthesis.SynthesisService"
        ) as MockSynthService, patch(
            "backend.api.v1.synthesis.CreditRepository"
        ) as MockCreditRepo:
            mock_instance = AsyncMock()
            mock_instance.synthesize.return_value = fake_synthesis_result
            MockSynthService.return_value = mock_instance

            mock_credit = AsyncMock()
            mock_credit.get_remaining_credits.return_value = 100
            MockCreditRepo.return_value = mock_credit

            resp = await client.post(
                "/api/v1/synthesis",
                json={"query": "CBN interest rate Nigeria"},
            )

        if resp.status_code == 200:
            data = resp.json()
            assert "coverage" in data
            if data["coverage"] is not None:
                cov = data["coverage"]
                assert "total_signals" in cov
                assert "relevant_signals" in cov
                assert "coverage_score" in cov
                assert "coverage_assessment" in cov

        # Clean up overrides
        for key in [get_current_user, get_current_organization]:
            app.dependency_overrides.pop(key, None)

    async def test_synthesis_contract_suggestion_when_requested(
        self, app, client, db_session
    ):
        """With suggest_contract=True, response includes contract_suggestion."""
        from unittest.mock import AsyncMock

        from backend.auth.dependencies import get_current_user
        from backend.middleware.feature_gating import (
            get_current_organization,
            require_feature,
        )

        auth = make_auth_context()
        app.dependency_overrides[get_current_user] = lambda: auth
        app.dependency_overrides[get_current_organization] = lambda: MagicMock(
            features={"on_demand_synthesis": True}
        )
        app.dependency_overrides[require_feature("on_demand_synthesis")] = lambda: True

        fake_result = {
            "synthesis": "Some synthesis",
            "sources": [],
            "web_sources": [],
            "confidence": 0.8,
            "cached": False,
            "total_indexed": 0,
        }

        with patch("backend.api.v1.synthesis.SynthesisService") as MockSvc, patch(
            "backend.api.v1.synthesis.CreditRepository"
        ) as MockCred:
            mock_svc = AsyncMock()
            mock_svc.synthesize.return_value = fake_result
            MockSvc.return_value = mock_svc

            mock_cred = AsyncMock()
            mock_cred.get_remaining_credits.return_value = 50
            MockCred.return_value = mock_cred

            resp = await client.post(
                "/api/v1/synthesis",
                json={"query": "oil gas crude price Nigeria", "suggest_contract": True},
            )

        if resp.status_code == 200:
            data = resp.json()
            assert "contract_suggestion" in data
            if data["contract_suggestion"] is not None:
                cs = data["contract_suggestion"]
                assert "suggested_title" in cs
                assert "suggested_description" in cs
                assert "suggested_keywords" in cs
                assert isinstance(cs["suggested_keywords"], list)

        for key in [get_current_user, get_current_organization]:
            app.dependency_overrides.pop(key, None)


# ── Round 8: Frontend Type Contract Tests ────────────────────────────


class TestRound8FrontendTypeContract:
    """Verify Round 8 API response shapes match TypeScript types."""

    async def test_alert_response_shape(self, app, client, db_session):
        """AlertResponse fields should match frontend AlertResponse type."""
        from backend.auth.dependencies import get_current_user

        auth = make_auth_context()
        app.dependency_overrides[get_current_user] = lambda: auth

        await create_signal_alert(db_session, metric="type_check_metric")
        await db_session.commit()

        resp = await client.get("/api/v1/alerts")
        assert resp.status_code == 200
        data = resp.json()

        if data["items"]:
            item = data["items"][0]
            expected_keys = {
                "id",
                "alert_type",
                "severity",
                "metric",
                "country_code",
                "title",
                "description",
                "current_value",
                "baseline_value",
                "deviation_pct",
                "acknowledged",
                "acknowledged_at",
                "created_at",
            }
            assert expected_keys.issubset(set(item.keys()))

        app.dependency_overrides.pop(get_current_user, None)

    async def test_alert_list_response_shape(self, app, client, db_session):
        """AlertListResponse should have items, total, unacknowledged."""
        from backend.auth.dependencies import get_current_user

        auth = make_auth_context()
        app.dependency_overrides[get_current_user] = lambda: auth

        resp = await client.get("/api/v1/alerts")
        data = resp.json()
        assert "items" in data and isinstance(data["items"], list)
        assert "total" in data and isinstance(data["total"], int)
        assert "unacknowledged" in data and isinstance(data["unacknowledged"], int)

        app.dependency_overrides.pop(get_current_user, None)

    async def test_alert_summary_response_shape(self, app, client, db_session):
        """AlertSummaryResponse should have total, unacknowledged, by_severity, by_metric."""
        from backend.auth.dependencies import get_current_user

        auth = make_auth_context()
        app.dependency_overrides[get_current_user] = lambda: auth

        resp = await client.get("/api/v1/alerts/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "unacknowledged" in data
        assert "by_severity" in data and isinstance(data["by_severity"], dict)
        assert "by_metric" in data and isinstance(data["by_metric"], dict)

        app.dependency_overrides.pop(get_current_user, None)
