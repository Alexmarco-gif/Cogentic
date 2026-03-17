"""
Tests for the dynamic knowledge system:
  - KnowledgeService (CRUD, query helpers, upsert)
  - Knowledge API (/api/v1/knowledge)
  - Compositional prompts (agent/prompts.py)
"""

from uuid import uuid4

import pytest

from backend.models.knowledge_entry import KnowledgeEntry
from backend.services.knowledge_service import KnowledgeService

pytestmark = pytest.mark.asyncio


# ═══════════════════════════════════════════════════════════════════════
# ── Helpers ───────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════


async def _seed_entry(
    db,
    *,
    category: str = "regulatory_body",
    code: str = "CBN",
    name: str = "Central Bank of Nigeria",
    country: str | None = "NGA",
    aliases: list[str] | None = None,
    keywords: list[str] | None = None,
    sort_order: int = 0,
) -> KnowledgeEntry:
    """Insert a knowledge entry directly for test setup."""
    entry = KnowledgeEntry(
        id=uuid4(),
        category=category,
        code=code,
        name=name,
        country=country,
        aliases=aliases or [],
        keywords=keywords or [],
        metadata_={},
        sort_order=sort_order,
        confidence=1.0,
        source="test",
    )
    db.add(entry)
    await db.flush()
    return entry


# ═══════════════════════════════════════════════════════════════════════
# ── KnowledgeService Tests ────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════


class TestKnowledgeServiceCRUD:
    """CRUD operations on knowledge entries."""

    async def test_create_entry(self, db_session):
        svc = KnowledgeService(db_session)
        entry = await svc.create(
            category="sector",
            code="fintech",
            name="Fintech",
            keywords=["fintech", "payment", "digital finance"],
        )
        assert entry.id is not None
        assert entry.category == "sector"
        assert entry.code == "fintech"
        assert entry.name == "Fintech"

    async def test_list_by_category(self, db_session):
        await _seed_entry(db_session, category="sector", code="banking", name="Banking")
        await _seed_entry(db_session, category="sector", code="energy", name="Energy")
        await _seed_entry(db_session, category="domain", code="retail", name="Retail")

        svc = KnowledgeService(db_session)
        sectors = await svc.list_by_category("sector")
        assert len(sectors) == 2
        codes = {s.code for s in sectors}
        assert codes == {"banking", "energy"}

    async def test_list_by_category_with_country_filter(self, db_session):
        await _seed_entry(
            db_session, category="domain", code="d1", name="D1", country="NGA"
        )
        await _seed_entry(
            db_session, category="domain", code="d2", name="D2", country="KEN"
        )
        await _seed_entry(
            db_session, category="domain", code="d3", name="D3", country=None
        )

        svc = KnowledgeService(db_session)
        # include_global=True (default) → returns country-specific + global (NULL)
        nga_global = await svc.list_by_category("domain", country="NGA")
        assert len(nga_global) == 2
        codes = {e.code for e in nga_global}
        assert codes == {"d1", "d3"}

        # include_global=False → strict country match only
        nga_strict = await svc.list_by_category(
            "domain", country="NGA", include_global=False
        )
        assert len(nga_strict) == 1
        assert nga_strict[0].code == "d1"

    async def test_get_by_code(self, db_session):
        await _seed_entry(
            db_session, category="regulatory_body", code="SEC", name="SEC Nigeria"
        )

        svc = KnowledgeService(db_session)
        entry = await svc.get_by_code("regulatory_body", "SEC")
        assert entry is not None
        assert entry.name == "SEC Nigeria"

    async def test_get_by_code_not_found(self, db_session):
        svc = KnowledgeService(db_session)
        entry = await svc.get_by_code("regulatory_body", "NONEXISTENT")
        assert entry is None

    async def test_update_entry(self, db_session):
        entry = await _seed_entry(db_session, code="OLD", name="Old Name")

        svc = KnowledgeService(db_session)
        updated = await svc.update_entry(entry.id, name="New Name")
        assert updated is not None
        assert updated.name == "New Name"

    async def test_update_nonexistent_entry(self, db_session):
        svc = KnowledgeService(db_session)
        result = await svc.update_entry(uuid4(), name="No Such Entry")
        assert result is None

    async def test_delete_entry(self, db_session):
        entry = await _seed_entry(db_session, code="DEL", name="To Delete")

        svc = KnowledgeService(db_session)
        deleted = await svc.delete_entry(entry.id)
        assert deleted is True

        # Verify it's gone
        fetched = await svc.get_by_code("regulatory_body", "DEL")
        assert fetched is None

    async def test_delete_nonexistent(self, db_session):
        svc = KnowledgeService(db_session)
        deleted = await svc.delete_entry(uuid4())
        assert deleted is False


class TestKnowledgeServiceQueryHelpers:
    """Specialised query methods used by agent/regulatory_intelligence."""

    async def test_get_regulatory_bodies(self, db_session):
        await _seed_entry(
            db_session,
            category="regulatory_body",
            code="CBN",
            name="Central Bank of Nigeria",
            aliases=["Central Bank of Nigeria", "CBN"],
            country="NGA",
        )
        await _seed_entry(
            db_session,
            category="regulatory_body",
            code="SEC",
            name="Securities and Exchange Commission",
            aliases=["SEC Nigeria", "SEC"],
            country="NGA",
        )

        svc = KnowledgeService(db_session)
        bodies = await svc.get_regulatory_bodies(country="NGA")

        assert isinstance(bodies, dict)
        assert "CBN" in bodies
        assert "SEC" in bodies
        assert "Central Bank of Nigeria" in bodies["CBN"]

    async def test_get_sector_keywords(self, db_session):
        await _seed_entry(
            db_session,
            category="sector",
            code="fintech",
            name="Fintech",
            keywords=["fintech", "payment", "mobile money"],
            country=None,
        )

        svc = KnowledgeService(db_session)
        sectors = await svc.get_sector_keywords()

        assert isinstance(sectors, dict)
        assert "fintech" in sectors
        assert "payment" in sectors["fintech"]

    async def test_get_entity_type_keywords(self, db_session):
        await _seed_entry(
            db_session,
            category="entity_type",
            code="banks",
            name="Banks",
            keywords=["bank", "banking institution"],
            country=None,
        )

        svc = KnowledgeService(db_session)
        types = await svc.get_entity_type_keywords()

        assert isinstance(types, dict)
        assert "banks" in types
        assert "bank" in types["banks"]

    async def test_get_domains(self, db_session):
        await _seed_entry(
            db_session,
            category="domain",
            code="Financial Services",
            name="Financial Services",
            country="NGA",
            sort_order=0,
        )
        await _seed_entry(
            db_session,
            category="domain",
            code="E-Commerce",
            name="E-Commerce & Retail",
            country="NGA",
            sort_order=1,
        )

        svc = KnowledgeService(db_session)
        domains = await svc.get_domains(country="NGA")

        assert len(domains) == 2
        assert domains[0]["name"] == "Financial Services"
        assert domains[1]["name"] == "E-Commerce & Retail"
        # Should include id, code, name, description, metadata, sort_order
        assert "id" in domains[0]
        assert "code" in domains[0]

    async def test_get_domains_empty(self, db_session):
        svc = KnowledgeService(db_session)
        domains = await svc.get_domains(country="XYZ")
        assert domains == []


class TestKnowledgeServiceUpsert:
    """Upsert method used for idempotent seeding."""

    async def test_upsert_creates_new(self, db_session):
        svc = KnowledgeService(db_session)
        entry = await svc.upsert(
            "sector",
            "agri",
            name="Agriculture",
            keywords=["farming"],
        )
        assert entry.id is not None
        assert entry.code == "agri"

    async def test_upsert_updates_existing(self, db_session):
        await _seed_entry(
            db_session, category="sector", code="agri", name="Agriculture"
        )

        svc = KnowledgeService(db_session)
        entry = await svc.upsert(
            "sector",
            "agri",
            name="Agriculture & Agritech",
            keywords=["farming", "agritech"],
        )
        assert entry.name == "Agriculture & Agritech"


# ═══════════════════════════════════════════════════════════════════════
# ── Knowledge API Tests ───────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════


class TestKnowledgeDomainsEndpoint:
    """GET /api/v1/knowledge/domains (public, no auth)."""

    async def test_domains_returns_list(self, client, db_session):
        await _seed_entry(
            db_session,
            category="domain",
            code="Finserv",
            name="Financial Services",
            country="NGA",
            sort_order=0,
        )
        await db_session.commit()

        resp = await client.get("/api/v1/knowledge/domains", params={"country": "NGA"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["name"] == "Financial Services"

    async def test_domains_empty_for_unknown_country(self, client):
        resp = await client.get("/api/v1/knowledge/domains", params={"country": "ZZZ"})
        assert resp.status_code == 200
        assert resp.json() == []


class TestKnowledgeCRUDEndpoints:
    """CRUD endpoints require auth."""

    async def test_list_entries_by_category(self, client, db_session):
        await _seed_entry(db_session, category="sector", code="bank", name="Banking")
        await db_session.commit()

        resp = await client.get("/api/v1/knowledge", params={"category": "sector"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

    async def test_create_entry(self, client):
        resp = await client.post(
            "/api/v1/knowledge",
            json={
                "category": "sector",
                "code": "telecom",
                "name": "Telecommunications",
                "country": "NGA",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["code"] == "telecom"
        assert data["name"] == "Telecommunications"

    async def test_update_entry(self, client, db_session):
        entry = await _seed_entry(db_session, code="UPD", name="Original")
        await db_session.commit()

        resp = await client.patch(
            f"/api/v1/knowledge/{entry.id}",
            json={"name": "Updated"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"

    async def test_update_nonexistent_returns_404(self, client):
        resp = await client.patch(
            f"/api/v1/knowledge/{uuid4()}",
            json={"name": "Nope"},
        )
        assert resp.status_code == 404

    async def test_delete_entry(self, client, db_session):
        entry = await _seed_entry(db_session, code="DELAPI", name="Delete Me")
        await db_session.commit()

        resp = await client.delete(f"/api/v1/knowledge/{entry.id}")
        assert resp.status_code == 204

    async def test_delete_nonexistent_returns_404(self, client):
        resp = await client.delete(f"/api/v1/knowledge/{uuid4()}")
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════
# ── Prompts Tests ─────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════


class TestComposablePrompts:
    """Verify that get_system_prompt dynamically builds context."""

    async def test_base_prompt_always_present(self, db_session):
        from backend.agent.prompts import BASE_SYSTEM_PROMPT, get_system_prompt

        prompt = await get_system_prompt(db_session)
        assert BASE_SYSTEM_PROMPT in prompt

    async def test_domains_injected_into_prompt(self, db_session):
        await _seed_entry(
            db_session,
            category="domain",
            code="Finserv",
            name="Financial Services",
            country="NGA",
            sort_order=0,
        )
        await db_session.flush()

        from backend.agent.prompts import get_system_prompt

        prompt = await get_system_prompt(db_session, country="NGA")
        assert "Financial Services" in prompt
        assert "Active Intelligence Domains" in prompt

    async def test_regulatory_bodies_in_prompt(self, db_session):
        await _seed_entry(
            db_session,
            category="regulatory_body",
            code="CBN",
            name="Central Bank of Nigeria",
            aliases=["Central Bank of Nigeria", "CBN"],
            country="NGA",
        )
        await db_session.flush()

        from backend.agent.prompts import get_system_prompt

        prompt = await get_system_prompt(db_session, country="NGA")
        assert "CBN" in prompt
        assert "Known Regulatory Bodies" in prompt

    async def test_sectors_in_prompt(self, db_session):
        await _seed_entry(
            db_session,
            category="sector",
            code="fintech",
            name="Fintech",
            country=None,
        )
        await db_session.flush()

        from backend.agent.prompts import get_system_prompt

        prompt = await get_system_prompt(db_session)
        assert "Fintech" in prompt
        assert "Tracked Industry Sectors" in prompt

    async def test_industry_focus_in_prompt(self, db_session):
        await _seed_entry(
            db_session,
            category="domain",
            code="agri",
            name="Agriculture & Agritech",
            country="NGA",
        )
        await db_session.flush()

        from backend.agent.prompts import get_system_prompt

        prompt = await get_system_prompt(db_session, industry_code="agri")
        assert "Agriculture & Agritech" in prompt
        assert "Focus Area" in prompt

    async def test_prompt_without_data_returns_base_only(self, db_session):
        """When the knowledge base is empty, only the base prompt is returned."""
        from backend.agent.prompts import BASE_SYSTEM_PROMPT, get_system_prompt

        prompt = await get_system_prompt(db_session, country="EMPTY")
        assert prompt == BASE_SYSTEM_PROMPT

    async def test_get_available_industries(self, db_session):
        await _seed_entry(
            db_session,
            category="domain",
            code="FinServ",
            name="Financial Services",
            country="NGA",
        )
        await _seed_entry(
            db_session,
            category="domain",
            code="Retail",
            name="E-Commerce & Retail",
            country="NGA",
        )
        await db_session.flush()

        from backend.agent.prompts import get_available_industries

        codes = await get_available_industries(db_session)
        assert "FinServ" in codes
        assert "Retail" in codes
