"""Locust load test suite for Cogent API.

Tests critical endpoints identified in the Production Readiness Report:
  - Signal listing / feed / trending
  - AI synthesis (search)
  - Brief generation
  - Document export (DOCX / PPTX)
  - Situation room dashboard
  - Health / metrics

Prerequisites:
    pip install locust

Usage:
    # Quick smoke test (10 users, 60s)
    locust -f scripts/load_test.py --headless -u 10 -r 2 -t 60s --host http://localhost:8000

    # Full load test (100 users, 5 min, web UI)
    locust -f scripts/load_test.py --host http://localhost:8000

    # Target staging
    locust -f scripts/load_test.py --host https://api-staging.cogent.ai

Environment variables:
    LOAD_TEST_TOKEN  — Bearer token for authenticated endpoints
    LOAD_TEST_ORG_ID — UUID of the test organisation
"""

import os
import random
import uuid

from locust import HttpUser, between, tag, task


class CogentUser(HttpUser):
    """Simulates an authenticated Cogent platform user."""

    wait_time = between(1, 5)

    def on_start(self):
        """Set up auth headers and test data."""
        token = os.environ.get("LOAD_TEST_TOKEN", "test-token")
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Request-ID": str(uuid.uuid4()),
        }
        self.org_id = os.environ.get(
            "LOAD_TEST_ORG_ID", "00000000-0000-0000-0000-000000000001"
        )

    # ── Health & Metrics ────────────────────────────────────────────

    @tag("health")
    @task(2)
    def health_check(self):
        """GET /health — container orchestrator probe."""
        self.client.get("/health", name="/health")

    @tag("health")
    @task(1)
    def root(self):
        """GET / — basic root check."""
        self.client.get("/", name="/")

    # ── Signals ─────────────────────────────────────────────────────

    @tag("signals", "read")
    @task(10)
    def list_signals(self):
        """GET /api/v1/signals — paginated signal listing."""
        skip = random.choice([0, 10, 20, 50])
        limit = random.choice([20, 50, 100])
        self.client.get(
            f"/api/v1/signals?skip={skip}&limit={limit}&min_confidence=0.5",
            headers=self.headers,
            name="/api/v1/signals",
        )

    @tag("signals", "read")
    @task(5)
    def signal_feed(self):
        """GET /api/v1/signals/feed — real-time feed."""
        self.client.get(
            "/api/v1/signals/feed?limit=50&min_confidence=0.6",
            headers=self.headers,
            name="/api/v1/signals/feed",
        )

    @tag("signals", "read")
    @task(3)
    def trending_signals(self):
        """GET /api/v1/signals/trending — ML-ranked trending."""
        self.client.get(
            "/api/v1/signals/trending?limit=20",
            headers=self.headers,
            name="/api/v1/signals/trending",
        )

    # ── Search / Synthesis ──────────────────────────────────────────

    @tag("search", "ai")
    @task(4)
    def search(self):
        """POST /api/v1/search — AI-powered semantic search."""
        queries = [
            "What are the latest regulatory changes in Nigerian banking?",
            "Technology trends in African fintech sector",
            "Oil price impact on Nigerian economy",
            "Cybersecurity threats targeting financial institutions",
            "ESG compliance requirements for West African companies",
        ]
        self.client.post(
            "/api/v1/search",
            json={
                "query": random.choice(queries),
                "limit": 10,
            },
            headers=self.headers,
            name="/api/v1/search",
        )

    # ── Briefs ──────────────────────────────────────────────────────

    @tag("briefs", "read")
    @task(3)
    def list_briefs(self):
        """GET /api/v1/briefs — paginated brief listing."""
        self.client.get(
            "/api/v1/briefs?limit=20",
            headers=self.headers,
            name="/api/v1/briefs",
        )

    @tag("briefs", "write", "ai")
    @task(1)
    def generate_brief(self):
        """POST /api/v1/briefs/generate — AI brief generation (heavy)."""
        self.client.post(
            "/api/v1/briefs/generate",
            json={
                "title": f"Load Test Brief {uuid.uuid4().hex[:8]}",
                "query": "Analysis of fintech regulatory landscape Q1 2026",
                "industry_id": None,
            },
            headers=self.headers,
            name="/api/v1/briefs/generate",
        )

    # ── Exports ─────────────────────────────────────────────────────

    @tag("exports", "write")
    @task(2)
    def export_docx(self):
        """POST /api/v1/exports/brief — DOCX export."""
        self.client.post(
            "/api/v1/exports/brief",
            json={
                "title": "Load Test Export",
                "subtitle": "Automated performance test",
                "domain": "Test",
                "confidence": 85,
                "sections": [
                    {
                        "heading": f"Section {i}",
                        "content": "Lorem ipsum dolor sit amet. " * 50,
                    }
                    for i in range(5)
                ],
                "format": "docx",
            },
            headers=self.headers,
            name="/api/v1/exports/brief [docx]",
        )

    @tag("exports", "write")
    @task(1)
    def export_pptx(self):
        """POST /api/v1/exports/brief — PPTX export."""
        self.client.post(
            "/api/v1/exports/brief",
            json={
                "title": "Load Test Slides",
                "subtitle": "Automated test",
                "domain": "Test",
                "sections": [
                    {"heading": f"Slide {i}", "content": "Content " * 100}
                    for i in range(3)
                ],
                "format": "pptx",
            },
            headers=self.headers,
            name="/api/v1/exports/brief [pptx]",
        )

    # ── Situation Room ──────────────────────────────────────────────

    @tag("situationroom", "read")
    @task(3)
    def situation_room_dashboard(self):
        """GET /api/v1/situation-room/{slug} — dashboard snapshot."""
        slugs = ["fintech", "oil-gas", "banking", "telecom"]
        slug = random.choice(slugs)
        self.client.get(
            f"/api/v1/situation-room/{slug}?hours=168&limit=50",
            headers=self.headers,
            name="/api/v1/situation-room/{slug}",
        )

    # ── Monitoring ──────────────────────────────────────────────────

    @tag("monitoring")
    @task(1)
    def monitoring_health(self):
        """GET /api/v1/monitoring/health — system health summary."""
        self.client.get(
            "/api/v1/monitoring/health",
            headers=self.headers,
            name="/api/v1/monitoring/health",
        )


class CogentHeavyUser(HttpUser):
    """Simulates a power user hammering AI endpoints.

    Lower weight — represents ~10% of traffic performing expensive
    AI operations (synthesis, brief gen, exports).
    """

    weight = 1  # vs CogentUser default weight of 10
    wait_time = between(3, 10)

    def on_start(self):
        token = os.environ.get("LOAD_TEST_TOKEN", "test-token")
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    @tag("ai", "search")
    @task(3)
    def deep_search(self):
        """Long-form synthesis query."""
        self.client.post(
            "/api/v1/search",
            json={
                "query": (
                    "Provide a comprehensive analysis of the intersection between "
                    "Nigeria's new data protection regulation (NDPR) and the fintech "
                    "sector, including compliance timelines and enforcement precedents"
                ),
                "limit": 20,
            },
            headers=self.headers,
            name="/api/v1/search [deep]",
        )

    @tag("exports", "write")
    @task(1)
    def large_export(self):
        """Large document export (many sections)."""
        self.client.post(
            "/api/v1/exports/brief",
            json={
                "title": "Comprehensive Industry Report",
                "subtitle": "Full Analysis",
                "domain": "Multi-sector",
                "confidence": 90,
                "sections": [
                    {
                        "heading": f"Chapter {i}: Analysis",
                        "content": "Detailed analysis text. " * 200,
                    }
                    for i in range(20)
                ],
                "format": "docx",
            },
            headers=self.headers,
            name="/api/v1/exports/brief [large]",
        )
