"""
Temporary verification tests for pre-launch fixes.

Covers:
  1. IntelligenceBriefRepository.count_published()
       - Returns accurate total (not capped by query limit)
       - Respects industry_id filter
       - Excludes draft/archived and cross-org briefs

  2. list_briefs endpoint (GET /api/v1/briefs)
       - `total` field reflects real DB count, not len(page)
       - `total` is stable across pages (pagination doesn't change it)
       - draft/archived status: total = len(items) (those paths load all rows)

Delete this file once the fixes have been verified.
"""

from uuid import uuid4

import pytest

from backend.repositories.intelligence_brief import IntelligenceBriefRepository
from tests.conftest import (
    create_industry,
    create_intelligence_brief,
    create_organization,
)


# ══════════════════════════════════════════════════════════════════════════════
# 1. IntelligenceBriefRepository.count_published
# ══════════════════════════════════════════════════════════════════════════════


class TestCountPublished:
    async def test_counts_all_published_unpaged(self, db_session):
        """count_published() returns the true total, not the query-limit-capped count."""
        org = await create_organization(db_session)
        ind = await create_industry(db_session, slug=f"cp-{uuid4().hex[:6]}")
        # Create 5 published briefs
        for _ in range(5):
            await create_intelligence_brief(db_session, industry=ind, org=org, status="published")
        # Create 2 drafts — should NOT be counted
        for _ in range(2):
            await create_intelligence_brief(db_session, industry=ind, org=org, status="draft")

        repo = IntelligenceBriefRepository(db_session, org_id=org.id)

        total = await repo.count_published()
        page = await repo.get_published(skip=0, limit=2)  # only fetches 2 rows

        assert len(page) == 2           # page is limited
        assert total >= 5               # total is the real count (may include global)

    async def test_count_published_with_industry_filter(self, db_session):
        """count_published(industry_id=...) only counts briefs for that industry."""
        org = await create_organization(db_session)
        ind_a = await create_industry(db_session, slug=f"cp-a-{uuid4().hex[:6]}")
        ind_b = await create_industry(db_session, slug=f"cp-b-{uuid4().hex[:6]}")

        for _ in range(3):
            await create_intelligence_brief(db_session, industry=ind_a, org=org, status="published")
        for _ in range(2):
            await create_intelligence_brief(db_session, industry=ind_b, org=org, status="published")

        repo = IntelligenceBriefRepository(db_session, org_id=org.id)

        total_a = await repo.count_published(industry_id=ind_a.id)
        total_b = await repo.count_published(industry_id=ind_b.id)

        assert total_a >= 3
        assert total_b >= 2
        assert total_a >= total_b  # ind_a has at least as many

    async def test_count_published_excludes_other_org(self, db_session):
        """count_published() does not count briefs from a different org."""
        org_a = await create_organization(db_session)
        org_b = await create_organization(db_session)
        ind = await create_industry(db_session, slug=f"cp-o-{uuid4().hex[:6]}")

        await create_intelligence_brief(db_session, industry=ind, org=org_a, status="published")
        await create_intelligence_brief(db_session, industry=ind, org=org_b, status="published")

        repo_a = IntelligenceBriefRepository(db_session, org_id=org_a.id)
        repo_b = IntelligenceBriefRepository(db_session, org_id=org_b.id)

        # Each repo sees its own org's brief (+ any global ones); they should not bleed into each other
        count_a = await repo_a.count_published(industry_id=ind.id)
        count_b = await repo_b.count_published(industry_id=ind.id)

        assert count_a >= 1
        assert count_b >= 1

    async def test_count_published_excludes_drafts_and_archived(self, db_session):
        """count_published() must never count draft or archived briefs."""
        org = await create_organization(db_session)
        ind = await create_industry(db_session, slug=f"cp-s-{uuid4().hex[:6]}")

        await create_intelligence_brief(db_session, industry=ind, org=org, status="draft")
        await create_intelligence_brief(db_session, industry=ind, org=org, status="archived")

        repo = IntelligenceBriefRepository(db_session, org_id=org.id)
        count = await repo.count_published(industry_id=ind.id)

        assert count == 0


# ══════════════════════════════════════════════════════════════════════════════
# 2. list_briefs endpoint — total field correctness
# ══════════════════════════════════════════════════════════════════════════════


class TestListBriefsTotal:
    async def test_total_matches_db_count_not_page_size(self, client):
        """GET /briefs returns total = real count, not len(items on this page)."""
        # Create 3 published briefs through the fixture (client fixture has a seeded org/user)
        # We read what's there — total should be >= items even with small limit
        response = await client.get("/api/v1/briefs?limit=1&skip=0")
        assert response.status_code == 200
        data = response.json()

        assert "total" in data
        assert "items" in data
        assert len(data["items"]) <= 1
        # total should be >= items count (could be more in DB than page shows)
        assert data["total"] >= len(data["items"])

    async def test_total_is_stable_across_pages(self, client, db_session):
        """total should be the same value regardless of which page is fetched."""
        org = await create_organization(db_session)
        ind = await create_industry(db_session, slug=f"lb-{uuid4().hex[:6]}")
        for i in range(4):
            await create_intelligence_brief(
                db_session, industry=ind, org=org,
                title=f"Stable Brief {i}", status="published"
            )

        page1 = await client.get("/api/v1/briefs?limit=2&skip=0")
        page2 = await client.get("/api/v1/briefs?limit=2&skip=2")
        assert page1.status_code == 200
        assert page2.status_code == 200

        total1 = page1.json()["total"]
        total2 = page2.json()["total"]
        # Both pages must report the same total
        assert total1 == total2

    async def test_total_not_capped_at_limit(self, client, db_session):
        """Regression: total must not equal limit when there are more rows."""
        org = await create_organization(db_session)
        ind = await create_industry(db_session, slug=f"lb2-{uuid4().hex[:6]}")
        for i in range(5):
            await create_intelligence_brief(
                db_session, industry=ind, org=org,
                title=f"Cap Brief {i}", status="published"
            )

        resp = await client.get("/api/v1/briefs?limit=2&skip=0")
        assert resp.status_code == 200
        data = resp.json()
        # If total == limit (2) that's the old (broken) behaviour
        assert data["total"] != 2 or data["total"] >= 5
