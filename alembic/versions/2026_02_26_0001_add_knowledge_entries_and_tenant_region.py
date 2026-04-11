"""Add knowledge_entries table and seed Nigeria data.

Creates the knowledge_entries table for dynamic regulatory bodies,
sectors, entity types, and domain definitions. Seeds with the
Nigeria-specific data that was previously hardcoded in Python.

Also adds tenant region fields to organizations table.

Revision ID: 2026_02_26_0001
Revises: 2026_02_25_0001
Create Date: 2026-02-26 00:01:00.000000

"""

from collections.abc import Sequence
from typing import Union
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026_02_26_0001"
down_revision: Union[str, None] = "2026_02_25_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    org_columns = {
        column["name"] for column in inspector.get_columns("organizations")
    }

    # ── 1. Create knowledge_entries table ─────────────────────────────────
    if "knowledge_entries" not in existing_tables:
        op.create_table(
            "knowledge_entries",
            sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid4),
            sa.Column("category", sa.String(100), nullable=False, index=True),
            sa.Column("country", sa.String(3), nullable=True, index=True),
            sa.Column("region", sa.String(100), nullable=True),
            sa.Column("code", sa.String(50), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("description", sa.Text, nullable=True),
            sa.Column("aliases", ARRAY(sa.String), server_default="{}"),
            sa.Column("keywords", ARRAY(sa.String), server_default="{}"),
            sa.Column("metadata", JSONB, server_default="{}"),
            sa.Column("sort_order", sa.Integer, server_default="0"),
            sa.Column("confidence", sa.Float, server_default="1.0"),
            sa.Column("source", sa.String(100), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

    knowledge_indexes = {
        index["name"] for index in inspector.get_indexes("knowledge_entries")
    } if "knowledge_entries" in set(inspector.get_table_names()) else set()

    if "ix_knowledge_category_country" not in knowledge_indexes:
        op.create_index(
            "ix_knowledge_category_country", "knowledge_entries", ["category", "country"]
        )
    if "ix_knowledge_category_code" not in knowledge_indexes:
        op.create_index(
            "ix_knowledge_category_code",
            "knowledge_entries",
            ["category", "code"],
            unique=True,
        )

    # ── 2. Add tenant region fields to organizations ──────────────────────
    if "default_country" not in org_columns:
        op.add_column(
            "organizations", sa.Column("default_country", sa.String(3), nullable=True)
        )
    if "default_timezone" not in org_columns:
        op.add_column(
            "organizations", sa.Column("default_timezone", sa.String(50), nullable=True)
        )
    if "default_language" not in org_columns:
        op.add_column(
            "organizations", sa.Column("default_language", sa.String(10), nullable=True)
        )
    if "supported_regions" not in org_columns:
        op.add_column(
            "organizations",
            sa.Column("supported_regions", ARRAY(sa.String), server_default="{}"),
        )

    # ── 3. Seed Nigeria regulatory bodies ─────────────────────────────────
    knowledge_entries = sa.table(
        "knowledge_entries",
        sa.column("id", UUID(as_uuid=True)),
        sa.column("category", sa.String),
        sa.column("country", sa.String),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("aliases", ARRAY(sa.String)),
        sa.column("keywords", ARRAY(sa.String)),
        sa.column("metadata", JSONB),
        sa.column("sort_order", sa.Integer),
        sa.column("confidence", sa.Float),
        sa.column("source", sa.String),
    )

    regulatory_bodies = [
        (
            "CBN",
            "Central Bank of Nigeria",
            ["Central Bank of Nigeria", "CBN", "central bank"],
        ),
        (
            "SEC",
            "Securities and Exchange Commission",
            ["Securities and Exchange Commission", "SEC Nigeria", "SEC"],
        ),
        (
            "FIRS",
            "Federal Inland Revenue Service",
            ["Federal Inland Revenue Service", "FIRS", "tax authority"],
        ),
        (
            "NCC",
            "Nigerian Communications Commission",
            ["Nigerian Communications Commission", "NCC", "telecom regulator"],
        ),
        (
            "NERC",
            "Nigerian Electricity Regulatory Commission",
            ["Nigerian Electricity Regulatory Commission", "NERC"],
        ),
        (
            "NAFDAC",
            "National Agency for Food and Drug Administration",
            ["National Agency for Food and Drug Administration", "NAFDAC"],
        ),
        (
            "SON",
            "Standards Organisation of Nigeria",
            ["Standards Organisation of Nigeria", "SON"],
        ),
        (
            "CAC",
            "Corporate Affairs Commission",
            ["Corporate Affairs Commission", "CAC"],
        ),
        (
            "NAICOM",
            "National Insurance Commission",
            ["National Insurance Commission", "NAICOM"],
        ),
        (
            "PENCOM",
            "National Pension Commission",
            ["National Pension Commission", "PENCOM"],
        ),
        (
            "BPE",
            "Bureau of Public Enterprises",
            ["Bureau of Public Enterprises", "BPE"],
        ),
    ]

    entry_count = bind.execute(sa.text("SELECT count(*) FROM knowledge_entries")).scalar()
    if entry_count == 0:
        for i, (code, name, aliases) in enumerate(regulatory_bodies):
            op.execute(
                knowledge_entries.insert().values(
                    id=uuid4(),
                    category="regulatory_body",
                    country="NGA",
                    code=code,
                    name=name,
                    aliases=aliases,
                    keywords=aliases,
                    metadata={},
                    sort_order=i,
                    confidence=1.0,
                    source="seed",
                )
            )

        # ── 4. Seed sectors ───────────────────────────────────────────────
        sectors = [
            ("banking", "Banking", ["bank", "banking", "financial institution"]),
            (
                "fintech",
                "Fintech",
                ["fintech", "payment", "mobile money", "digital finance"],
            ),
            (
                "agriculture",
                "Agriculture",
                ["agriculture", "farming", "agribusiness", "crop"],
            ),
            (
                "telecommunications",
                "Telecommunications",
                ["telecom", "telco", "communication service"],
            ),
            ("energy", "Energy", ["energy", "power", "electricity", "NERC"]),
            ("manufacturing", "Manufacturing", ["manufact", "production", "industrial"]),
            ("oil_gas", "Oil & Gas", ["oil", "petroleum", "gas", "upstream", "downstream"]),
            ("insurance", "Insurance", ["insurance", "underwriting", "NAICOM"]),
        ]

        for i, (code, name, keywords) in enumerate(sectors):
            op.execute(
                knowledge_entries.insert().values(
                    id=uuid4(),
                    category="sector",
                    country=None,
                    code=code,
                    name=name,
                    aliases=[],
                    keywords=keywords,
                    metadata={},
                    sort_order=i,
                    confidence=1.0,
                    source="seed",
                )
            )

        # ── 5. Seed entity types ─────────────────────────────────────────
        entity_types = [
            ("banks", "Banks", ["bank", "banking institution"]),
            ("mmos", "Mobile Money Operators", ["mobile money", "MMO", "payment service"]),
            ("telcos", "Telcos", ["telecommunications", "telecom", "mobile network"]),
            (
                "insurance_companies",
                "Insurance Companies",
                ["insurance company", "insurer", "underwriter"],
            ),
            ("oil_companies", "Oil Companies", ["oil company", "petroleum", "IOC"]),
            (
                "manufacturers",
                "Manufacturers",
                ["manufacturer", "factory", "production company"],
            ),
        ]

        for i, (code, name, keywords) in enumerate(entity_types):
            op.execute(
                knowledge_entries.insert().values(
                    id=uuid4(),
                    category="entity_type",
                    country=None,
                    code=code,
                    name=name,
                    aliases=[],
                    keywords=keywords,
                    metadata={},
                    sort_order=i,
                    confidence=1.0,
                    source="seed",
                )
            )

        # ── 6. Seed domains (the 5 Nigeria strategic domains) ───────────
        domains = [
            (
                "E-Commerce & Retail",
                "E-Commerce & Retail",
                "Retail and online commerce intelligence",
            ),
            (
                "Financial Services",
                "Financial Services",
                "Banking, fintech, and capital markets",
            ),
            ("Media & Brand", "Media & Brand", "Media, advertising, and brand sentiment"),
            (
                "Telecom & Digital",
                "Telecom & Digital",
                "Telecommunications and digital infrastructure",
            ),
            (
                "Agriculture & Agritech",
                "Agriculture & Agritech",
                "Agriculture, food systems, and agritech",
            ),
        ]

        for i, (code, name, description) in enumerate(domains):
            op.execute(
                knowledge_entries.insert().values(
                    id=uuid4(),
                    category="domain",
                    country="NGA",
                    code=code,
                    name=name,
                    aliases=[],
                    keywords=[],
                    metadata={},
                    sort_order=i,
                    confidence=1.0,
                    source="seed",
                    description=description,
                )
            )


def downgrade() -> None:
    op.drop_column("organizations", "supported_regions")
    op.drop_column("organizations", "default_language")
    op.drop_column("organizations", "default_timezone")
    op.drop_column("organizations", "default_country")
    op.drop_index("ix_knowledge_category_code", table_name="knowledge_entries")
    op.drop_index("ix_knowledge_category_country", table_name="knowledge_entries")
    op.drop_table("knowledge_entries")
