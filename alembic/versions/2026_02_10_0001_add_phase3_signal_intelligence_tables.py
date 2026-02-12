"""Add Phase 3 signal intelligence tables (13 new tables)

Revision ID: 2026_02_10_0001
Revises: 2026_01_30_1500
Create Date: 2026-02-10 00:01:00.000000

Tables created:
  1. industries          — Industry taxonomy (4 root + sub-verticals)
  2. entities            — Companies, products, people, brands (pgvector)
  3. signal_contracts    — HOW to acquire signals (280 seeded)
  4. signals             — Raw acquired signal instances (pgvector)
  5. signal_entities     — Many-to-many: signals ↔ entities
  6. intelligence_briefs — Pre-built + auto-generated briefs
  7. brief_signals       — Many-to-many: briefs ↔ signals
  8. chat_sessions       — AI Chat Agent conversations
  9. chat_messages       — Individual messages in sessions
  10. search_queries     — Deep Live Search log + cache
  11. recommendations    — Precomputed suggestions
  12. ml_model_runs      — ML pipeline audit trail
  13. signal_scores      — ML-computed scores per signal
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026_02_10_0001"
down_revision: Union[str, None] = "2026_01_30_1500"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # 1. Industries — hierarchical taxonomy
    # =========================================================================
    op.create_table(
        "industries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column(
            "parent_id",
            UUID(as_uuid=True),
            sa.ForeignKey("industries.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("metadata", sa.JSON, server_default="{}", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("idx_industries_slug", "industries", ["slug"])
    op.create_index("idx_industries_parent_id", "industries", ["parent_id"])

    # =========================================================================
    # 2. Entities — companies, products, people, brands
    # =========================================================================
    op.create_table(
        "entities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column(
            "industry_id",
            UUID(as_uuid=True),
            sa.ForeignKey("industries.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("aliases", sa.JSON, server_default="[]", nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("metadata", sa.JSON, server_default="{}", nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("idx_entities_name", "entities", ["name"])
    op.create_index("idx_entities_type", "entities", ["entity_type"])
    op.create_index("idx_entities_industry_id", "entities", ["industry_id"])

    # =========================================================================
    # 3. Signal Contracts — how to acquire signals
    # =========================================================================
    op.create_table(
        "signal_contracts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "industry_id",
            UUID(as_uuid=True),
            sa.ForeignKey("industries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "entity_id",
            UUID(as_uuid=True),
            sa.ForeignKey("entities.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source_url", sa.Text, nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column(
            "refresh_cron",
            sa.String(100),
            nullable=False,
            server_default="'0 */1 * * *'",
        ),
        sa.Column(
            "schedule_tier",
            sa.String(50),
            nullable=False,
            server_default="'standard'",
        ),
        sa.Column("extraction_config", sa.JSON, server_default="{}", nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
        sa.Column("status", sa.String(50), server_default="'active'", nullable=False),
        sa.Column("failure_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("max_failures", sa.Integer, server_default="3", nullable=False),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_signal_contracts_industry_id", "signal_contracts", ["industry_id"]
    )
    op.create_index("idx_signal_contracts_entity_id", "signal_contracts", ["entity_id"])
    op.create_index(
        "idx_signal_contracts_source_type", "signal_contracts", ["source_type"]
    )
    op.create_index("idx_signal_contracts_status", "signal_contracts", ["status"])
    op.create_index(
        "idx_signal_contracts_active",
        "signal_contracts",
        ["is_active", "status"],
        postgresql_where=sa.text("is_active = true"),
    )

    # =========================================================================
    # 4. Signals — raw acquired signal instances
    # =========================================================================
    op.create_table(
        "signals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "contract_id",
            UUID(as_uuid=True),
            sa.ForeignKey("signal_contracts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "org_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("raw_content", sa.Text, nullable=True),
        sa.Column("extracted_data", sa.JSON, server_default="{}", nullable=False),
        sa.Column("source_url", sa.Text, nullable=True),
        sa.Column("signal_type", sa.String(50), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("idx_signals_contract_id", "signals", ["contract_id"])
    op.create_index("idx_signals_org_id", "signals", ["org_id"])
    op.create_index("idx_signals_signal_type", "signals", ["signal_type"])
    op.create_index("idx_signals_content_hash", "signals", ["content_hash"])
    op.create_index("idx_signals_published_at", "signals", ["published_at"])
    op.create_index("idx_signals_expires_at", "signals", ["expires_at"])
    op.create_index(
        "idx_signals_confidence",
        "signals",
        ["confidence"],
        postgresql_where=sa.text("confidence >= 0.6"),
    )
    op.create_index(
        "idx_signals_brief_eligible",
        "signals",
        ["contract_id", "confidence"],
        postgresql_where=sa.text("confidence >= 0.85"),
    )

    # =========================================================================
    # 5. Signal-Entity join table
    # =========================================================================
    op.create_table(
        "signal_entities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "signal_id",
            UUID(as_uuid=True),
            sa.ForeignKey("signals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "entity_id",
            UUID(as_uuid=True),
            sa.ForeignKey("entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relevance_score", sa.Float, nullable=False, server_default="1.0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("idx_signal_entities_signal_id", "signal_entities", ["signal_id"])
    op.create_index("idx_signal_entities_entity_id", "signal_entities", ["entity_id"])
    op.create_unique_constraint(
        "uq_signal_entity", "signal_entities", ["signal_id", "entity_id"]
    )

    # =========================================================================
    # 6. Intelligence Briefs
    # =========================================================================
    op.create_table(
        "intelligence_briefs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "industry_id",
            UUID(as_uuid=True),
            sa.ForeignKey("industries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column(
            "brief_type",
            sa.String(50),
            nullable=False,
            server_default="'pre_built'",
        ),
        sa.Column("bluf", sa.Text, nullable=True),
        sa.Column("body_json", sa.JSON, server_default="{}", nullable=False),
        sa.Column("outlook", sa.Text, nullable=True),
        sa.Column("decision_lens", sa.Text, nullable=True),
        sa.Column("status", sa.String(50), server_default="'draft'", nullable=False),
        sa.Column("refreshed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_intelligence_briefs_org_id", "intelligence_briefs", ["org_id"])
    op.create_index(
        "idx_intelligence_briefs_industry_id",
        "intelligence_briefs",
        ["industry_id"],
    )
    op.create_index("idx_intelligence_briefs_status", "intelligence_briefs", ["status"])
    op.create_index(
        "idx_intelligence_briefs_published",
        "intelligence_briefs",
        ["status", "industry_id"],
        postgresql_where=sa.text("deleted_at IS NULL AND status = 'published'"),
    )

    # =========================================================================
    # 7. Brief-Signal join table
    # =========================================================================
    op.create_table(
        "brief_signals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "brief_id",
            UUID(as_uuid=True),
            sa.ForeignKey("intelligence_briefs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "signal_id",
            UUID(as_uuid=True),
            sa.ForeignKey("signals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relevance_rank", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("idx_brief_signals_brief_id", "brief_signals", ["brief_id"])
    op.create_index("idx_brief_signals_signal_id", "brief_signals", ["signal_id"])
    op.create_unique_constraint(
        "uq_brief_signal", "brief_signals", ["brief_id", "signal_id"]
    )

    # =========================================================================
    # 8. Chat Sessions
    # =========================================================================
    op.create_table(
        "chat_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "org_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "industry_id",
            UUID(as_uuid=True),
            sa.ForeignKey("industries.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("status", sa.String(50), server_default="'active'", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("idx_chat_sessions_user_id", "chat_sessions", ["user_id"])
    op.create_index("idx_chat_sessions_org_id", "chat_sessions", ["org_id"])
    op.create_index("idx_chat_sessions_industry_id", "chat_sessions", ["industry_id"])
    op.create_index("idx_chat_sessions_status", "chat_sessions", ["status"])
    op.create_index(
        "idx_chat_sessions_user_active",
        "chat_sessions",
        ["user_id", "org_id"],
        postgresql_where=sa.text("status = 'active'"),
    )

    # =========================================================================
    # 9. Chat Messages
    # =========================================================================
    op.create_table(
        "chat_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            UUID(as_uuid=True),
            sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("sources_json", sa.JSON, nullable=True),
        sa.Column("token_count", sa.Integer, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("idx_chat_messages_session_id", "chat_messages", ["session_id"])
    op.create_index(
        "idx_chat_messages_session_chrono",
        "chat_messages",
        ["session_id", "created_at"],
    )

    # =========================================================================
    # 10. Search Queries
    # =========================================================================
    op.create_table(
        "search_queries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "org_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("query_text", sa.Text, nullable=False),
        sa.Column("query_hash", sa.String(64), nullable=True),
        sa.Column("results_json", sa.JSON, nullable=True),
        sa.Column("source_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("response_time_ms", sa.Integer, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("idx_search_queries_user_id", "search_queries", ["user_id"])
    op.create_index("idx_search_queries_org_id", "search_queries", ["org_id"])
    op.create_index("idx_search_queries_hash", "search_queries", ["query_hash"])
    op.create_index(
        "idx_search_queries_user_history",
        "search_queries",
        ["user_id", "org_id", "created_at"],
    )

    # =========================================================================
    # 11. Recommendations
    # =========================================================================
    op.create_table(
        "recommendations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_id", UUID(as_uuid=True), nullable=False),
        sa.Column("target_type", sa.String(50), nullable=False),
        sa.Column("target_id", UUID(as_uuid=True), nullable=False),
        sa.Column("score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("algorithm_version", sa.String(50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_recommendations_source",
        "recommendations",
        ["source_type", "source_id"],
    )
    op.create_index(
        "idx_recommendations_target",
        "recommendations",
        ["target_type", "target_id"],
    )
    op.create_index(
        "idx_recommendations_score",
        "recommendations",
        ["source_type", "source_id", "score"],
    )

    # =========================================================================
    # 12. ML Model Runs
    # =========================================================================
    op.create_table(
        "ml_model_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("model_version", sa.String(50), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=True),
        sa.Column("output_json", sa.JSON, server_default="{}", nullable=False),
        sa.Column("signals_processed", sa.Integer, server_default="0", nullable=False),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column(
            "status",
            sa.String(50),
            server_default="'completed'",
            nullable=False,
        ),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("ran_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("idx_ml_model_runs_name", "ml_model_runs", ["model_name"])
    op.create_index("idx_ml_model_runs_status", "ml_model_runs", ["status"])
    op.create_index(
        "idx_ml_model_runs_latest",
        "ml_model_runs",
        ["model_name", "ran_at"],
    )

    # =========================================================================
    # 13. Signal Scores
    # =========================================================================
    op.create_table(
        "signal_scores",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "signal_id",
            UUID(as_uuid=True),
            sa.ForeignKey("signals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("score_type", sa.String(50), nullable=False),
        sa.Column("score_value", sa.Float, nullable=False),
        sa.Column(
            "model_run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ml_model_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("idx_signal_scores_signal_id", "signal_scores", ["signal_id"])
    op.create_index("idx_signal_scores_type", "signal_scores", ["score_type"])
    op.create_index("idx_signal_scores_model_run", "signal_scores", ["model_run_id"])
    op.create_index(
        "idx_signal_scores_composite",
        "signal_scores",
        ["signal_id", "score_type"],
    )

    # =========================================================================
    # Vector indexes for semantic search (HNSW — works with empty tables)
    # =========================================================================
    op.execute(
        "CREATE INDEX idx_signals_embedding ON signals "
        "USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute(
        "CREATE INDEX idx_entities_embedding ON entities "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    # Drop vector indexes first
    op.execute("DROP INDEX IF EXISTS idx_entities_embedding")
    op.execute("DROP INDEX IF EXISTS idx_signals_embedding")

    # Drop tables in reverse dependency order
    op.drop_table("signal_scores")
    op.drop_table("ml_model_runs")
    op.drop_table("recommendations")
    op.drop_table("search_queries")
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.drop_table("brief_signals")
    op.drop_table("intelligence_briefs")
    op.drop_table("signal_entities")
    op.drop_table("signals")
    op.drop_table("signal_contracts")
    op.drop_table("entities")
    op.drop_table("industries")
