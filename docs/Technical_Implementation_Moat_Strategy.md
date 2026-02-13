# Technical Implementation Guide: Building the Intelligence Moat

**Document Version:** 1.0
**Date:** February 12, 2026
**Status:** 🔴 CRITICAL - IMMEDIATE ACTION REQUIRED
**Classification:** Internal Engineering

---

## Executive Summary

This document translates the Strategic Intelligence Differentiation Blueprint into **concrete technical implementations** for the ESIP codebase. Each section includes:
- What to build
- Where in the codebase it goes
- Code examples
- Database schema changes
- Priority ranking (P0 = Critical, P1 = High, P2 = Medium)

---

## Part 1: Entity Resolution 2.0 (Proprietary Data Fusion)

**Priority:** P0 (Foundation for everything else)
**Timeline:** Week 1-2

### Current State

Your current entity extraction is basic:
- Simple entity type field (`company`, `person`, `product`, `brand`)
- No cross-source resolution
- No relationship mapping
- No canonical entity graph

### What to Build

**1.1 Enhanced Entity Model**

Create new tables for entity graph:

```sql
-- Location: alembic/versions/2026_02_13_0001_add_entity_graph.py

-- Canonical entities (single source of truth)
CREATE TABLE entities (
    id UUID PRIMARY KEY,
    canonical_name VARCHAR(255) NOT NULL,
    entity_type VARCHAR(50) NOT NULL, -- company, person, product, brand, infrastructure, cooperative
    industry_id UUID REFERENCES industries(id),
    slug VARCHAR(255) UNIQUE NOT NULL,

    -- Metadata
    confidence FLOAT DEFAULT 1.0, -- How confident we are this is a distinct entity
    verified BOOLEAN DEFAULT FALSE, -- Manual verification flag

    -- Rich profile data (JSONB for flexibility)
    attributes JSONB DEFAULT '{}', -- Industry-specific attributes
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP
);

-- Entity aliases (multiple names for same entity)
CREATE TABLE entity_aliases (
    id UUID PRIMARY KEY,
    entity_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    alias_name VARCHAR(255) NOT NULL,
    alias_type VARCHAR(50), -- legal_name, trading_name, abbreviation, former_name, local_name
    source VARCHAR(100), -- Where did we learn this alias?
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Cross-source entity profiles (data fusion)
CREATE TABLE entity_source_profiles (
    id UUID PRIMARY KEY,
    entity_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    source_type VARCHAR(100) NOT NULL, -- cac_nigeria, customs_data, linkedin, job_boards, procurement, etc.
    source_id VARCHAR(255), -- External ID in source system
    profile_data JSONB NOT NULL, -- Source-specific data
    last_synced_at TIMESTAMP DEFAULT NOW(),
    confidence FLOAT DEFAULT 0.8,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(entity_id, source_type) -- One profile per source per entity
);

-- Entity relationships (the relationship graph)
CREATE TABLE entity_relationships (
    id UUID PRIMARY KEY,
    source_entity_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    target_entity_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    relationship_type VARCHAR(100) NOT NULL, -- subsidiary, supplier, customer, competitor, partner, etc.

    -- Relationship metadata
    strength FLOAT DEFAULT 0.5, -- 0 = weak, 1 = strong
    confidence FLOAT DEFAULT 0.5,
    bidirectional BOOLEAN DEFAULT FALSE, -- Is relationship symmetric?

    -- Evidence
    evidence_signals JSON[] DEFAULT '{}', -- Array of signal IDs that support this relationship
    first_observed_at TIMESTAMP,
    last_observed_at TIMESTAMP,

    -- Temporal tracking
    is_active BOOLEAN DEFAULT TRUE,
    ended_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(source_entity_id, target_entity_id, relationship_type)
);

-- Indexes for performance
CREATE INDEX idx_entities_type_industry ON entities(entity_type, industry_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_entity_aliases_name ON entity_aliases(alias_name);
CREATE INDEX idx_entity_aliases_entity ON entity_aliases(entity_id);
CREATE INDEX idx_entity_source_profiles_entity ON entity_source_profiles(entity_id);
CREATE INDEX idx_entity_source_profiles_type ON entity_source_profiles(source_type);
CREATE INDEX idx_entity_relationships_source ON entity_relationships(source_entity_id) WHERE is_active = TRUE;
CREATE INDEX idx_entity_relationships_target ON entity_relationships(target_entity_id) WHERE is_active = TRUE;
CREATE INDEX idx_entity_relationships_type ON entity_relationships(relationship_type) WHERE is_active = TRUE;
```

**1.2 Entity Resolution Service**

Create entity resolution engine:

```python
# Location: backend/services/entity_resolution.py

"""Entity resolution and fusion service.

Responsibilities:
- Resolve entity mentions to canonical entities
- Merge entity profiles from multiple sources
- Detect and create entity relationships
- Maintain entity graph integrity
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from rapidfuzz import fuzz, process

from backend.models.entity import Entity, EntityAlias, EntitySourceProfile, EntityRelationship
from backend.models.signal import Signal
from backend.ai.embeddings import EmbeddingService

logger = logging.getLogger(__name__)


class EntityResolutionService:
    """Entity resolution engine with fuzzy matching + embedding similarity."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = EmbeddingService(db)

    async def resolve_entity(
        self,
        mention: str,
        *,
        entity_type: str | None = None,
        industry_id: UUID | None = None,
        context: str | None = None,
        min_confidence: float = 0.75,
    ) -> tuple[Entity | None, float]:
        """Resolve an entity mention to a canonical entity.

        Uses multi-stage matching:
        1. Exact alias match (confidence: 1.0)
        2. Fuzzy string matching (confidence: 0.7-0.95)
        3. Embedding similarity with context (confidence: 0.6-0.85)

        Args:
            mention: Entity name as mentioned in source
            entity_type: Filter by entity type
            industry_id: Filter by industry
            context: Surrounding text context for embedding-based matching
            min_confidence: Minimum confidence threshold

        Returns:
            Tuple of (Entity or None, confidence_score)
        """
        # Stage 1: Exact alias match
        exact_match = await self._exact_alias_match(mention, entity_type, industry_id)
        if exact_match:
            return exact_match, 1.0

        # Stage 2: Fuzzy string matching
        fuzzy_match, fuzzy_score = await self._fuzzy_match(
            mention, entity_type, industry_id
        )
        if fuzzy_match and fuzzy_score >= min_confidence:
            return fuzzy_match, fuzzy_score

        # Stage 3: Embedding similarity (if context provided)
        if context:
            embedding_match, embedding_score = await self._embedding_match(
                mention, context, entity_type, industry_id
            )
            if embedding_match and embedding_score >= min_confidence:
                # Prefer fuzzy match if both qualify (fuzzy is more precise for names)
                if fuzzy_score >= min_confidence and fuzzy_score > embedding_score:
                    return fuzzy_match, fuzzy_score
                return embedding_match, embedding_score

        # No match above threshold
        return None, 0.0

    async def _exact_alias_match(
        self,
        mention: str,
        entity_type: str | None,
        industry_id: UUID | None,
    ) -> Entity | None:
        """Exact match lookup in entity_aliases table."""
        query = (
            select(Entity)
            .join(EntityAlias, EntityAlias.entity_id == Entity.id)
            .where(
                EntityAlias.alias_name.ilike(mention.strip()),
                Entity.deleted_at.is_(None)
            )
        )

        if entity_type:
            query = query.where(Entity.entity_type == entity_type)
        if industry_id:
            query = query.where(Entity.industry_id == industry_id)

        result = await self.db.execute(query)
        return result.scalars().first()

    async def _fuzzy_match(
        self,
        mention: str,
        entity_type: str | None,
        industry_id: UUID | None,
    ) -> tuple[Entity | None, float]:
        """Fuzzy string matching using RapidFuzz."""
        # Get candidate entities
        query = select(Entity).where(Entity.deleted_at.is_(None))
        if entity_type:
            query = query.where(Entity.entity_type == entity_type)
        if industry_id:
            query = query.where(Entity.industry_id == industry_id)

        result = await self.db.execute(query.limit(500))  # Performance limit
        candidates = result.scalars().all()

        if not candidates:
            return None, 0.0

        # Build candidate list with all names (canonical + aliases)
        candidate_names = {}
        for entity in candidates:
            candidate_names[entity.canonical_name] = entity
            # Also load aliases
            alias_result = await self.db.execute(
                select(EntityAlias).where(EntityAlias.entity_id == entity.id)
            )
            for alias in alias_result.scalars():
                candidate_names[alias.alias_name] = entity

        # Fuzzy match
        match_result = process.extractOne(
            mention,
            candidate_names.keys(),
            scorer=fuzz.token_sort_ratio
        )

        if not match_result:
            return None, 0.0

        matched_name, score, _ = match_result
        confidence = score / 100.0  # Convert 0-100 to 0-1

        return candidate_names[matched_name], confidence

    async def _embedding_match(
        self,
        mention: str,
        context: str,
        entity_type: str | None,
        industry_id: UUID | None,
    ) -> tuple[Entity | None, float]:
        """Embedding-based semantic matching with context."""
        # Create query text with context
        query_text = f"{mention} {context[:200]}"  # Limit context length
        query_embedding = await self.embedding_service.generate_query_embedding(query_text)

        # Build vector similarity query (requires entity.description_embedding)
        # Note: Requires adding embedding column to entities table
        # For now, return None (implement after adding embedding column)
        logger.debug("Embedding-based entity matching not yet implemented")
        return None, 0.0

    async def create_or_update_entity(
        self,
        canonical_name: str,
        entity_type: str,
        *,
        industry_id: UUID | None = None,
        aliases: list[str] | None = None,
        attributes: dict[str, Any] | None = None,
        confidence: float = 0.9,
    ) -> Entity:
        """Create a new canonical entity or update existing one."""
        # Check if entity already exists
        existing = await self._exact_alias_match(canonical_name, entity_type, industry_id)

        if existing:
            # Update existing
            if attributes:
                existing.attributes = {**existing.attributes, **attributes}
            existing.updated_at = datetime.now(timezone.utc)
            await self.db.flush()
            entity = existing
        else:
            # Create new
            slug = canonical_name.lower().replace(" ", "-").replace("&", "and")
            entity = Entity(
                id=uuid4(),
                canonical_name=canonical_name,
                entity_type=entity_type,
                industry_id=industry_id,
                slug=slug,
                confidence=confidence,
                attributes=attributes or {},
                metadata={},
            )
            self.db.add(entity)
            await self.db.flush()

        # Add aliases
        if aliases:
            for alias in aliases:
                alias_obj = EntityAlias(
                    id=uuid4(),
                    entity_id=entity.id,
                    alias_name=alias,
                    alias_type="trading_name",
                    source="manual",
                    confidence=0.95,
                )
                self.db.add(alias_obj)

        await self.db.flush()
        return entity

    async def add_source_profile(
        self,
        entity_id: UUID,
        source_type: str,
        profile_data: dict[str, Any],
        *,
        source_id: str | None = None,
        confidence: float = 0.8,
    ) -> EntitySourceProfile:
        """Add or update a source-specific profile for an entity."""
        # Check if profile already exists
        existing = await self.db.execute(
            select(EntitySourceProfile).where(
                and_(
                    EntitySourceProfile.entity_id == entity_id,
                    EntitySourceProfile.source_type == source_type
                )
            )
        )
        existing_profile = existing.scalars().first()

        if existing_profile:
            # Update
            existing_profile.profile_data = profile_data
            existing_profile.source_id = source_id
            existing_profile.last_synced_at = datetime.now(timezone.utc)
            existing_profile.updated_at = datetime.now(timezone.utc)
            await self.db.flush()
            return existing_profile
        else:
            # Create
            profile = EntitySourceProfile(
                id=uuid4(),
                entity_id=entity_id,
                source_type=source_type,
                source_id=source_id,
                profile_data=profile_data,
                confidence=confidence,
            )
            self.db.add(profile)
            await self.db.flush()
            return profile

    async def create_relationship(
        self,
        source_entity_id: UUID,
        target_entity_id: UUID,
        relationship_type: str,
        *,
        strength: float = 0.5,
        confidence: float = 0.6,
        evidence_signal_id: UUID | None = None,
        bidirectional: bool = False,
    ) -> EntityRelationship:
        """Create or update an entity relationship."""
        # Check if relationship exists
        existing = await self.db.execute(
            select(EntityRelationship).where(
                and_(
                    EntityRelationship.source_entity_id == source_entity_id,
                    EntityRelationship.target_entity_id == target_entity_id,
                    EntityRelationship.relationship_type == relationship_type
                )
            )
        )
        existing_rel = existing.scalars().first()

        now = datetime.now(timezone.utc)

        if existing_rel:
            # Update
            existing_rel.strength = max(existing_rel.strength, strength)  # Upgrade strength
            existing_rel.confidence = max(existing_rel.confidence, confidence)
            existing_rel.last_observed_at = now
            existing_rel.is_active = True

            # Add evidence
            if evidence_signal_id:
                existing_rel.evidence_signals = existing_rel.evidence_signals or []
                if str(evidence_signal_id) not in existing_rel.evidence_signals:
                    existing_rel.evidence_signals.append(str(evidence_signal_id))

            await self.db.flush()
            return existing_rel
        else:
            # Create
            relationship = EntityRelationship(
                id=uuid4(),
                source_entity_id=source_entity_id,
                target_entity_id=target_entity_id,
                relationship_type=relationship_type,
                strength=strength,
                confidence=confidence,
                bidirectional=bidirectional,
                evidence_signals=[str(evidence_signal_id)] if evidence_signal_id else [],
                first_observed_at=now,
                last_observed_at=now,
                is_active=True,
            )
            self.db.add(relationship)
            await self.db.flush()
            return relationship

    async def get_entity_network(
        self,
        entity_id: UUID,
        *,
        relationship_types: list[str] | None = None,
        max_depth: int = 2,
        min_strength: float = 0.3,
    ) -> dict[str, Any]:
        """Get entity relationship network graph.

        Returns:
            Graph structure with nodes and edges.
        """
        # BFS traversal of entity graph
        visited = set()
        nodes = []
        edges = []
        queue = [(entity_id, 0)]  # (entity_id, depth)

        while queue:
            current_id, depth = queue.pop(0)

            if current_id in visited or depth > max_depth:
                continue

            visited.add(current_id)

            # Get entity node
            entity = await self.db.get(Entity, current_id)
            if entity:
                nodes.append({
                    "id": str(entity.id),
                    "name": entity.canonical_name,
                    "type": entity.entity_type,
                    "depth": depth,
                })

            # Get relationships
            query = select(EntityRelationship).where(
                and_(
                    EntityRelationship.source_entity_id == current_id,
                    EntityRelationship.is_active == True,
                    EntityRelationship.strength >= min_strength
                )
            )
            if relationship_types:
                query = query.where(EntityRelationship.relationship_type.in_(relationship_types))

            result = await self.db.execute(query)
            relationships = result.scalars().all()

            for rel in relationships:
                edges.append({
                    "source": str(rel.source_entity_id),
                    "target": str(rel.target_entity_id),
                    "type": rel.relationship_type,
                    "strength": rel.strength,
                    "confidence": rel.confidence,
                })

                # Add to queue for traversal
                if depth + 1 <= max_depth:
                    queue.append((rel.target_entity_id, depth + 1))

        return {
            "nodes": nodes,
            "edges": edges,
            "center_entity_id": str(entity_id),
        }
```

**1.3 ORM Models**

```python
# Location: backend/models/entity.py

"""Entity models for entity resolution and relationship graph."""

from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
import uuid

from backend.database import Base


class Entity(Base):
    """Canonical entity (single source of truth for companies, people, products, etc.)."""

    __tablename__ = "entities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canonical_name = Column(String(255), nullable=False)
    entity_type = Column(String(50), nullable=False)  # company, person, product, brand, infrastructure, cooperative
    industry_id = Column(UUID(as_uuid=True), ForeignKey("industries.id"), nullable=True)
    slug = Column(String(255), unique=True, nullable=False)

    confidence = Column(Float, default=1.0)
    verified = Column(Boolean, default=False)

    attributes = Column(JSONB, default={})
    metadata = Column(JSONB, default={})

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    aliases = relationship("EntityAlias", back_populates="entity", cascade="all, delete-orphan")
    source_profiles = relationship("EntitySourceProfile", back_populates="entity", cascade="all, delete-orphan")
    outgoing_relationships = relationship(
        "EntityRelationship",
        foreign_keys="EntityRelationship.source_entity_id",
        back_populates="source_entity",
        cascade="all, delete-orphan"
    )
    incoming_relationships = relationship(
        "EntityRelationship",
        foreign_keys="EntityRelationship.target_entity_id",
        back_populates="target_entity",
        cascade="all, delete-orphan"
    )


class EntityAlias(Base):
    """Entity aliases (multiple names for same entity)."""

    __tablename__ = "entity_aliases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    alias_name = Column(String(255), nullable=False)
    alias_type = Column(String(50), nullable=True)  # legal_name, trading_name, abbreviation, former_name
    source = Column(String(100), nullable=True)
    confidence = Column(Float, default=1.0)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    entity = relationship("Entity", back_populates="aliases")


class EntitySourceProfile(Base):
    """Cross-source entity profiles (data fusion layer)."""

    __tablename__ = "entity_source_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    source_type = Column(String(100), nullable=False)  # cac_nigeria, customs, linkedin, job_boards, procurement
    source_id = Column(String(255), nullable=True)  # External ID in source system
    profile_data = Column(JSONB, nullable=False)
    last_synced_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    confidence = Column(Float, default=0.8)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    entity = relationship("Entity", back_populates="source_profiles")


class EntityRelationship(Base):
    """Entity relationships (the relationship graph)."""

    __tablename__ = "entity_relationships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    target_entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    relationship_type = Column(String(100), nullable=False)  # subsidiary, supplier, customer, competitor, partner

    strength = Column(Float, default=0.5)  # 0 = weak, 1 = strong
    confidence = Column(Float, default=0.5)
    bidirectional = Column(Boolean, default=False)

    evidence_signals = Column(ARRAY(String), default=[])  # Array of signal IDs
    first_observed_at = Column(DateTime(timezone=True), nullable=True)
    last_observed_at = Column(DateTime(timezone=True), nullable=True)

    is_active = Column(Boolean, default=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    source_entity = relationship("Entity", foreign_keys=[source_entity_id], back_populates="outgoing_relationships")
    target_entity = relationship("Entity", foreign_keys=[target_entity_id], back_populates="incoming_relationships")
```

---

## Part 2: Causal Intelligence Engine

**Priority:** P0 (Core differentiation)
**Timeline:** Week 2-4

### What to Build

**2.1 Temporal Event Graph (Neo4j Integration)**

Add graph database for temporal causality:

```python
# Location: backend/services/causal_graph.py

"""Causal event graph for temporal reasoning.

Uses Neo4j for graph storage and traversal.
Detects cause-effect relationships over time.
"""

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from neo4j import AsyncGraphDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CausalGraphService:
    """Temporal causal graph for event sequence reasoning."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )

    async def close(self):
        """Close Neo4j driver."""
        await self.driver.close()

    async def add_event_node(
        self,
        signal_id: UUID,
        event_type: str,
        event_timestamp: datetime,
        *,
        entities: list[UUID] | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> str:
        """Add an event node to the causal graph.

        Args:
            signal_id: Signal UUID
            event_type: Type classification (e.g., 'policy_change', 'price_increase')
            event_timestamp: When event occurred
            entities: List of entity IDs involved
            attributes: Event-specific attributes

        Returns:
            Neo4j node ID
        """
        async with self.driver.session() as session:
            query = """
            CREATE (e:Event {
                signal_id: $signal_id,
                event_type: $event_type,
                timestamp: datetime($timestamp),
                entities: $entities,
                attributes: $attributes
            })
            RETURN elementId(e) as node_id
            """
            result = await session.run(
                query,
                signal_id=str(signal_id),
                event_type=event_type,
                timestamp=event_timestamp.isoformat(),
                entities=[str(e) for e in (entities or [])],
                attributes=attributes or {}
            )
            record = await result.single()
            return record["node_id"]

    async def detect_causal_link(
        self,
        source_signal_id: UUID,
        target_signal_id: UUID,
        *,
        max_lag_days: int = 30,
        min_confidence: float = 0.6,
    ) -> dict[str, Any] | None:
        """Detect potential causal link between two events.

        Uses:
        - Temporal proximity (is target after source within lag window?)
        - Entity overlap (do events involve same entities?)
        - Pattern matching (have we seen this sequence before?)

        Returns:
            Causal link metadata or None if no link detected
        """
        async with self.driver.session() as session:
            # Find events
            query = """
            MATCH (source:Event {signal_id: $source_id})
            MATCH (target:Event {signal_id: $target_id})
            WHERE target.timestamp > source.timestamp
              AND duration.between(source.timestamp, target.timestamp).days <= $max_lag_days
            RETURN
                source,
                target,
                duration.between(source.timestamp, target.timestamp) as lag
            """
            result = await session.run(
                query,
                source_id=str(source_signal_id),
                target_id=str(target_signal_id),
                max_lag_days=max_lag_days
            )
            record = await result.single()

            if not record:
                return None  # No temporal link

            source_node = record["source"]
            target_node = record["target"]
            lag = record["lag"]

            # Calculate entity overlap
            source_entities = set(source_node.get("entities", []))
            target_entities = set(target_node.get("entities", []))
            entity_overlap = len(source_entities & target_entities) / max(len(source_entities), len(target_entities)) if source_entities or target_entities else 0

            # Calculate confidence (simple heuristic for now)
            # TODO: Replace with ML model trained on historical causal links
            confidence = min(0.6 + (entity_overlap * 0.3), 1.0)

            if confidence < min_confidence:
                return None

            return {
                "source_signal_id": str(source_signal_id),
                "target_signal_id": str(target_signal_id),
                "lag_days": lag.days,
                "entity_overlap": entity_overlap,
                "confidence": confidence,
                "source_event_type": source_node.get("event_type"),
                "target_event_type": target_node.get("event_type"),
            }

    async def create_causal_edge(
        self,
        source_signal_id: UUID,
        target_signal_id: UUID,
        *,
        confidence: float,
        lag_days: int,
        relationship_label: str = "LEADS_TO",
    ):
        """Create a causal edge between two events."""
        async with self.driver.session() as session:
            query = """
            MATCH (source:Event {signal_id: $source_id})
            MATCH (target:Event {signal_id: $target_id})
            MERGE (source)-[r:""" + relationship_label + """ {
                confidence: $confidence,
                lag_days: $lag_days,
                created_at: datetime()
            }]->(target)
            RETURN r
            """
            await session.run(
                query,
                source_id=str(source_signal_id),
                target_id=str(target_signal_id),
                confidence=confidence,
                lag_days=lag_days
            )

    async def find_causal_chains(
        self,
        start_event_type: str,
        *,
        max_depth: int = 5,
        min_confidence: float = 0.6,
    ) -> list[dict[str, Any]]:
        """Find common causal chains starting from a specific event type.

        Example: "policy_change" → "lending_rate_change" → "loan_volume_decline"

        Returns:
            List of causal chains with frequencies and confidence scores
        """
        async with self.driver.session() as session:
            # Find paths of length up to max_depth
            query = f"""
            MATCH path = (start:Event {{event_type: $event_type}})-[r:LEADS_TO*1..{max_depth}]->(end:Event)
            WHERE ALL(rel IN r WHERE rel.confidence >= $min_confidence)
            RETURN
                [node IN nodes(path) | node.event_type] as chain,
                [rel IN relationships(path) | rel.lag_days] as lags,
                [rel IN relationships(path) | rel.confidence] as confidences,
                length(path) as depth
            ORDER BY depth
            LIMIT 100
            """
            result = await session.run(
                query,
                event_type=start_event_type,
                min_confidence=min_confidence
            )

            chains = []
            async for record in result:
                chains.append({
                    "chain": record["chain"],
                    "lags": record["lags"],
                    "confidences": record["confidences"],
                    "depth": record["depth"],
                    "avg_confidence": sum(record["confidences"]) / len(record["confidences"]),
                })

            return chains

    async def predict_next_events(
        self,
        current_signal_id: UUID,
        *,
        time_horizon_days: int = 30,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Predict likely next events based on current event and historical patterns.

        Returns:
            List of predicted events with probabilities and expected lags
        """
        async with self.driver.session() as session:
            query = """
            MATCH (current:Event {signal_id: $signal_id})
            MATCH (current)-[r:LEADS_TO]->(next:Event)
            WHERE r.lag_days <= $time_horizon
            WITH next.event_type as event_type,
                 AVG(r.lag_days) as avg_lag,
                 AVG(r.confidence) as avg_confidence,
                 COUNT(*) as frequency
            ORDER BY frequency DESC, avg_confidence DESC
            LIMIT $top_k
            RETURN event_type, avg_lag, avg_confidence, frequency
            """
            result = await session.run(
                query,
                signal_id=str(current_signal_id),
                time_horizon=time_horizon_days,
                top_k=top_k
            )

            predictions = []
            async for record in result:
                # Simple probability model: weighted by frequency and confidence
                # TODO: Replace with proper probabilistic model
                probability = min((record["frequency"] / 10.0) * record["avg_confidence"], 0.95)

                predictions.append({
                    "predicted_event_type": record["event_type"],
                    "expected_lag_days": int(record["avg_lag"]),
                    "probability": round(probability, 3),
                    "confidence": round(record["avg_confidence"], 3),
                    "historical_frequency": record["frequency"],
                })

            return predictions
```

**2.2 Causal Inference Models**

```python
# Location: backend/ml/causal_inference.py

"""Causal inference models for WHY analysis.

Uses:
- Propensity score matching
- Difference-in-differences estimation
- Granger causality tests (for time series)
- Counterfactual estimation
"""

import logging
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.stattools import grangercausalitytests
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.signal import Signal

logger = logging.getLogger(__name__)


class CausalInferenceService:
    """Causal inference engine for understanding WHY events occur."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def granger_causality_test(
        self,
        cause_signal_type: str,
        effect_signal_type: str,
        *,
        max_lag: int = 14,
        lookback_days: int = 180,
    ) -> dict[str, Any]:
        """Test if one signal type Granger-causes another.

        Granger causality: Does past values of X help predict Y?

        Args:
            cause_signal_type: Hypothesized cause
            effect_signal_type: Hypothesized effect
            max_lag: Maximum lag to test (days)
            lookback_days: How far back to pull data

        Returns:
            Test results with p-values and optimal lag
        """
        # Fetch time series data
        cutoff = datetime.utcnow() - timedelta(days=lookback_days)

        # Cause signals
        cause_query = (
            select(Signal.published_at, Signal.confidence)
            .where(
                and_(
                    Signal.signal_type == cause_signal_type,
                    Signal.published_at >= cutoff
                )
            )
            .order_by(Signal.published_at)
        )
        cause_result = await self.db.execute(cause_query)
        cause_data = [(r.published_at, r.confidence) for r in cause_result]

        # Effect signals
        effect_query = (
            select(Signal.published_at, Signal.confidence)
            .where(
                and_(
                    Signal.signal_type == effect_signal_type,
                    Signal.published_at >= cutoff
                )
            )
            .order_by(Signal.published_at)
        )
        effect_result = await self.db.execute(effect_query)
        effect_data = [(r.published_at, r.confidence) for r in effect_result]

        # Convert to daily time series
        cause_series = self._aggregate_to_daily(cause_data, lookback_days)
        effect_series = self._aggregate_to_daily(effect_data, lookback_days)

        # Create DataFrame for Granger test
        df = pd.DataFrame({
            "cause": cause_series,
            "effect": effect_series,
        })

        # Run Granger causality test
        try:
            gc_result = grangercausalitytests(
                df[["effect", "cause"]],
                maxlag=max_lag,
                verbose=False
            )

            # Extract p-values for each lag
            p_values = {}
            for lag in range(1, max_lag + 1):
                # Use F-test p-value
                p_val = gc_result[lag][0]["ssr_ftest"][1]
                p_values[lag] = p_val

            # Find optimal lag (minimum p-value)
            optimal_lag = min(p_values, key=p_values.get)
            optimal_p_value = p_values[optimal_lag]

            # Determine if causal relationship exists (p < 0.05)
            is_causal = optimal_p_value < 0.05

            return {
                "cause_signal_type": cause_signal_type,
                "effect_signal_type": effect_signal_type,
                "is_causal": is_causal,
                "optimal_lag_days": optimal_lag,
                "p_value": round(optimal_p_value, 4),
                "confidence": round(1 - optimal_p_value, 4) if is_causal else 0.0,
                "interpretation": (
                    f"{cause_signal_type} Granger-causes {effect_signal_type} "
                    f"with {optimal_lag} day lag (p={optimal_p_value:.4f})"
                    if is_causal
                    else f"No Granger causality detected between {cause_signal_type} and {effect_signal_type}"
                ),
            }

        except Exception as e:
            logger.error(f"Granger causality test failed: {e}")
            return {
                "cause_signal_type": cause_signal_type,
                "effect_signal_type": effect_signal_type,
                "is_causal": False,
                "error": str(e),
            }

    @staticmethod
    def _aggregate_to_daily(
        data: list[tuple[datetime, float]],
        lookback_days: int
    ) -> np.ndarray:
        """Aggregate signals to daily time series."""
        # Create daily buckets
        daily_counts = np.zeros(lookback_days)

        for timestamp, confidence in data:
            days_ago = (datetime.utcnow() - timestamp).days
            if 0 <= days_ago < lookback_days:
                # Aggregate by count * average confidence
                daily_counts[lookback_days - days_ago - 1] += confidence

        return daily_counts

    async def estimate_counterfactual(
        self,
        event_signal_id: str,
        outcome_metric: str,
        *,
        pre_event_days: int = 30,
        post_event_days: int = 30,
    ) -> dict[str, Any]:
        """Estimate counterfactual: What would have happened if event didn't occur?

        Uses synthetic control method: Build a synthetic baseline from similar periods
        without the event, then compare actual vs. baseline.

        Args:
            event_signal_id: The event whose impact we want to measure
            outcome_metric: The metric we're measuring (e.g., 'stock_price', 'loan_volume')
            pre_event_days: Days before event to establish baseline
            post_event_days: Days after event to measure impact

        Returns:
            Counterfactual estimate with impact quantification
        """
        # Placeholder implementation
        # TODO: Implement synthetic control method
        logger.warning("Counterfactual estimation not yet fully implemented")

        return {
            "event_signal_id": event_signal_id,
            "outcome_metric": outcome_metric,
            "estimated_impact": None,
            "counterfactual_baseline": None,
            "note": "Full counterfactual estimation requires more historical data and implementation",
        }
```

---

## Part 3: Predictive Signal Models (Proprietary)

**Priority:** P0 (Critical differentiation)
**Timeline:** Week 3-5

[Content continues with predictive models implementation...]

---

## Implementation Priority Matrix

| Component | Priority | Week | Dependencies | Impact |
|-----------|----------|------|--------------|--------|
| Entity Resolution 2.0 | P0 | 1-2 | None | Foundation for all proprietary data fusion |
| Causal Graph (Neo4j) | P0 | 2-3 | Entity Resolution | Enables temporal reasoning |
| Granger Causality Tests | P0 | 3 | Causal Graph | Proves WHY relationships |
| Predictive Models (1st model) | P0 | 4 | Causal Graph | First forecasting capability |
| Feedback Loop Infrastructure | P1 | 3-4 | None | Enables network effects |
| Influence Mapping | P1 | 5-6 | Entity Resolution | Relationship intelligence |
| Counterfactual Engine | P1 | 6-7 | Causal Models | Advanced analysis |
| Expert Annotation System | P2 | 7-8 | Feedback Loop | Collective intelligence |

---

## Success Metrics

Track these metrics to measure moat strength:

| Metric | Target (90 days) | Measurement |
|--------|-----------------|-------------|
| Entity Graph Coverage | 1,000+ Nigerian entities | Count of entities table |
| Causal Chains Discovered | 50+ validated chains | Count in Neo4j |
| Prediction Accuracy | >70% on 7-day forecasts | Backtest predictions |
| Replicability Score | <20% ChatGPT-replicable | Blind testing |
| User Retention (DAU/MAU) | >0.4 | User engagement analytics |

---

**CRITICAL NEXT STEP:** Review with engineering team, prioritize P0 items, begin Week 1 implementation.
