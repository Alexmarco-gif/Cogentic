"""Entity resolution and data-fusion service.

Resolves entity mentions to canonical entities using multi-stage matching:
  1. Exact alias lookup
  2. Fuzzy string matching (RapidFuzz)
  3. Embedding similarity (pgvector) with context

Manages entity aliases, cross-source profiles, and relationship graph.
This is a core intelligence moat component — the entity graph can't be
replicated without the accumulated data and resolution history.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from rapidfuzz import fuzz, process
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.embeddings import EmbeddingService
from backend.models.entity import Entity
from backend.models.entity_alias import EntityAlias
from backend.models.entity_relationship import EntityRelationship
from backend.models.entity_source_profile import EntitySourceProfile
from backend.models.signal_entity import SignalEntity

logger = logging.getLogger(__name__)


class EntityResolutionService:
    """Cross-source entity resolution engine.

    Resolves raw entity mentions (from scraped content, filings, etc.)
    to canonical Entity records using a multi-stage matching pipeline.

    Pipeline:
      Stage 1 — Exact alias match (O(1) DB lookup, confidence: 1.0)
      Stage 2 — Fuzzy name match (RapidFuzz token_sort_ratio, confidence: 0.7-0.95)
      Stage 3 — Embedding similarity with context (pgvector cosine, confidence: 0.6-0.85)

    If no match found, optionally creates a new canonical entity.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = EmbeddingService(db)

    # ── Core Resolution ──────────────────────────────────────────────

    async def resolve(
        self,
        mention: str,
        *,
        entity_type: str | None = None,
        industry_id: UUID | None = None,
        context: str | None = None,
        min_confidence: float = 0.75,
        auto_create: bool = False,
    ) -> tuple[Entity | None, float]:
        """Resolve an entity mention to a canonical entity.

        Args:
            mention: Entity name as mentioned in source text.
            entity_type: Optional filter (company, person, product, etc.).
            industry_id: Optional industry filter.
            context: Surrounding text for embedding-based matching.
            min_confidence: Minimum match confidence threshold.
            auto_create: If True, create a new entity when no match found.

        Returns:
            Tuple of (Entity or None, confidence_score).
        """
        mention = mention.strip()
        if not mention:
            return None, 0.0

        # Stage 1: Exact alias match
        exact = await self._exact_alias_match(mention, entity_type, industry_id)
        if exact:
            logger.debug(f"Entity resolved (exact): '{mention}' → '{exact.name}'")
            return exact, 1.0

        # Stage 2: Fuzzy string match
        fuzzy_entity, fuzzy_score = await self._fuzzy_match(
            mention, entity_type, industry_id
        )
        if fuzzy_entity and fuzzy_score >= min_confidence:
            logger.debug(
                f"Entity resolved (fuzzy {fuzzy_score:.2f}): "
                f"'{mention}' → '{fuzzy_entity.name}'"
            )
            return fuzzy_entity, fuzzy_score

        # Stage 3: Embedding similarity (if context provided)
        if context:
            emb_entity, emb_score = await self._embedding_match(
                mention, context, entity_type, industry_id
            )
            if emb_entity and emb_score >= min_confidence:
                # Prefer higher-scoring match
                if fuzzy_entity and fuzzy_score > emb_score:
                    return fuzzy_entity, fuzzy_score
                logger.debug(
                    f"Entity resolved (embedding {emb_score:.2f}): "
                    f"'{mention}' → '{emb_entity.name}'"
                )
                return emb_entity, emb_score

        # No match found
        if auto_create:
            new_entity = await self.create_entity(
                name=mention,
                entity_type=entity_type or "company",
                industry_id=industry_id,
            )
            logger.info(f"Auto-created entity: '{mention}' ({new_entity.id})")
            return new_entity, 0.6  # Low confidence for auto-created

        return None, 0.0

    async def resolve_batch(
        self,
        mentions: list[str],
        *,
        entity_type: str | None = None,
        industry_id: UUID | None = None,
        min_confidence: float = 0.75,
    ) -> list[tuple[str, Entity | None, float]]:
        """Resolve a batch of entity mentions.

        Returns:
            List of (mention, Entity or None, confidence) tuples.
        """
        results = []
        for mention in mentions:
            entity, confidence = await self.resolve(
                mention,
                entity_type=entity_type,
                industry_id=industry_id,
                min_confidence=min_confidence,
            )
            results.append((mention, entity, confidence))
        return results

    # ── Matching Stages ──────────────────────────────────────────────

    async def _exact_alias_match(
        self,
        mention: str,
        entity_type: str | None,
        industry_id: UUID | None,
    ) -> Entity | None:
        """Stage 1: Exact match against entity names and aliases."""
        # First check canonical names
        query = select(Entity).where(
            func.lower(Entity.name) == mention.lower(),
            Entity.deleted_at.is_(None) if hasattr(Entity, "deleted_at") else True,
        )
        if entity_type:
            query = query.where(Entity.entity_type == entity_type)
        if industry_id:
            query = query.where(Entity.industry_id == industry_id)

        result = await self.db.execute(query)
        match = result.scalars().first()
        if match:
            return match

        # Then check structured aliases
        alias_query = (
            select(Entity)
            .join(EntityAlias, EntityAlias.entity_id == Entity.id)
            .where(func.lower(EntityAlias.alias_name) == mention.lower())
        )
        if entity_type:
            alias_query = alias_query.where(Entity.entity_type == entity_type)
        if industry_id:
            alias_query = alias_query.where(Entity.industry_id == industry_id)

        result = await self.db.execute(alias_query)
        return result.scalars().first()

    async def _fuzzy_match(
        self,
        mention: str,
        entity_type: str | None,
        industry_id: UUID | None,
    ) -> tuple[Entity | None, float]:
        """Stage 2: Fuzzy string matching using RapidFuzz."""
        # Load candidate entities (capped for performance)
        query = select(Entity)
        if entity_type:
            query = query.where(Entity.entity_type == entity_type)
        if industry_id:
            query = query.where(Entity.industry_id == industry_id)
        query = query.limit(500)

        result = await self.db.execute(query)
        candidates = result.scalars().all()

        if not candidates:
            return None, 0.0

        # Build name→entity mapping (canonical + aliases)
        name_map: dict[str, Entity] = {}
        for entity in candidates:
            name_map[entity.name] = entity
            # Include legacy JSON aliases
            if entity.aliases:
                for alias in entity.aliases:
                    if isinstance(alias, str):
                        name_map[alias] = entity

        # Also include structured aliases
        entity_ids = [e.id for e in candidates]
        if entity_ids:
            alias_query = select(EntityAlias).where(
                EntityAlias.entity_id.in_(entity_ids)
            )
            alias_result = await self.db.execute(alias_query)
            for alias in alias_result.scalars():
                # Map alias to its parent entity
                parent = next((e for e in candidates if e.id == alias.entity_id), None)
                if parent:
                    name_map[alias.alias_name] = parent

        if not name_map:
            return None, 0.0

        # Fuzzy match
        match_result = process.extractOne(
            mention,
            name_map.keys(),
            scorer=fuzz.token_sort_ratio,
        )

        if not match_result:
            return None, 0.0

        matched_name, score, _ = match_result
        confidence = score / 100.0
        return name_map[matched_name], confidence

    async def _embedding_match(
        self,
        mention: str,
        context: str,
        entity_type: str | None,
        industry_id: UUID | None,
    ) -> tuple[Entity | None, float]:
        """Stage 3: Embedding-based semantic matching with context."""
        try:
            query_text = f"{mention}: {context[:300]}"
            query_embedding = await self.embedding_service.generate_query_embedding(
                query_text
            )

            # Build pgvector similarity query
            embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

            conditions = ["e.embedding IS NOT NULL"]
            if entity_type:
                conditions.append(f"e.entity_type = '{entity_type}'")
            if industry_id:
                conditions.append(f"e.industry_id = '{industry_id}'")
            where_clause = " AND ".join(conditions)

            from sqlalchemy import text

            sql = text(f"""
                SELECT
                    e.id,
                    e.name,
                    e.entity_type,
                    e.embedding <=> :embedding AS distance
                FROM entities e
                WHERE {where_clause}
                ORDER BY e.embedding <=> :embedding
                LIMIT 1
            """)

            result = await self.db.execute(sql, {"embedding": embedding_str})
            row = result.fetchone()

            if not row:
                return None, 0.0

            similarity = 1.0 - (row.distance or 1.0)
            if similarity < 0.5:
                return None, 0.0

            entity = await self.db.get(Entity, row.id)
            return entity, round(similarity, 4)

        except Exception as e:
            logger.warning(f"Embedding-based entity match failed: {e}")
            return None, 0.0

    # ── Entity CRUD ──────────────────────────────────────────────────

    async def create_entity(
        self,
        name: str,
        entity_type: str,
        *,
        industry_id: UUID | None = None,
        description: str | None = None,
        aliases: list[str] | None = None,
        extra_data: dict[str, Any] | None = None,
    ) -> Entity:
        """Create a new canonical entity with optional aliases."""
        entity = Entity(
            id=uuid4(),
            name=name,
            entity_type=entity_type,
            industry_id=industry_id,
            description=description,
            aliases=aliases or [],
            extra_data=extra_data or {},
            verified=False,
        )
        self.db.add(entity)
        await self.db.flush()

        # Create structured alias records
        if aliases:
            for alias_name in aliases:
                alias = EntityAlias(
                    id=uuid4(),
                    entity_id=entity.id,
                    alias_name=alias_name,
                    alias_type="trading_name",
                    source="manual",
                    confidence=0.95,
                )
                self.db.add(alias)
            await self.db.flush()

        return entity

    async def add_alias(
        self,
        entity_id: UUID,
        alias_name: str,
        *,
        alias_type: str = "trading_name",
        source: str = "manual",
        confidence: float = 0.95,
    ) -> EntityAlias:
        """Add an alias to an existing entity."""
        alias = EntityAlias(
            id=uuid4(),
            entity_id=entity_id,
            alias_name=alias_name,
            alias_type=alias_type,
            source=source,
            confidence=confidence,
        )
        self.db.add(alias)
        await self.db.flush()
        return alias

    # ── Source Profiles ───────────────────────────────────────────────

    async def upsert_source_profile(
        self,
        entity_id: UUID,
        source_type: str,
        profile_data: dict[str, Any],
        *,
        source_id: str | None = None,
        confidence: float = 0.8,
    ) -> EntitySourceProfile:
        """Add or update a cross-source profile for an entity.

        If a profile for this entity+source_type already exists, updates it.
        Otherwise creates a new one.
        """
        existing = await self.db.execute(
            select(EntitySourceProfile).where(
                and_(
                    EntitySourceProfile.entity_id == entity_id,
                    EntitySourceProfile.source_type == source_type,
                )
            )
        )
        profile = existing.scalars().first()
        now = datetime.now(timezone.utc)

        if profile:
            # Merge profile data (deep merge top-level keys)
            merged = {**profile.profile_data, **profile_data}
            profile.profile_data = merged
            profile.source_id = source_id or profile.source_id
            profile.last_synced_at = now
            profile.confidence = max(profile.confidence, confidence)
            await self.db.flush()
            return profile

        profile = EntitySourceProfile(
            id=uuid4(),
            entity_id=entity_id,
            source_type=source_type,
            source_id=source_id,
            profile_data=profile_data,
            confidence=confidence,
            last_synced_at=now,
        )
        self.db.add(profile)
        await self.db.flush()
        return profile

    async def get_entity_profiles(
        self,
        entity_id: UUID,
    ) -> list[EntitySourceProfile]:
        """Get all source profiles for an entity."""
        result = await self.db.execute(
            select(EntitySourceProfile).where(
                EntitySourceProfile.entity_id == entity_id
            )
        )
        return list(result.scalars().all())

    # ── Relationship Graph ───────────────────────────────────────────

    async def upsert_relationship(
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
        """Create or update an entity relationship.

        If the relationship already exists, strengthens it (upgrades
        strength/confidence, adds evidence signal).
        """
        existing = await self.db.execute(
            select(EntityRelationship).where(
                and_(
                    EntityRelationship.source_entity_id == source_entity_id,
                    EntityRelationship.target_entity_id == target_entity_id,
                    EntityRelationship.relationship_type == relationship_type,
                )
            )
        )
        rel = existing.scalars().first()
        now = datetime.now(timezone.utc)

        if rel:
            # Strengthen existing relationship
            rel.strength = min(1.0, max(rel.strength, strength))
            rel.confidence = min(1.0, max(rel.confidence, confidence))
            rel.last_observed_at = now
            rel.is_active = True
            if evidence_signal_id:
                current = rel.evidence_signals or []
                sig_str = str(evidence_signal_id)
                if sig_str not in current:
                    rel.evidence_signals = [*current, sig_str]
            await self.db.flush()
            return rel

        rel = EntityRelationship(
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
        self.db.add(rel)
        await self.db.flush()
        return rel

    async def get_entity_network(
        self,
        entity_id: UUID,
        *,
        relationship_types: list[str] | None = None,
        max_depth: int = 2,
        min_strength: float = 0.3,
    ) -> dict[str, Any]:
        """Get entity relationship network as a graph.

        BFS traversal up to max_depth. Returns nodes and edges.
        """
        visited: set[UUID] = set()
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        queue: list[tuple[UUID, int]] = [(entity_id, 0)]

        while queue:
            current_id, depth = queue.pop(0)
            if current_id in visited or depth > max_depth:
                continue
            visited.add(current_id)

            # Fetch entity
            entity = await self.db.get(Entity, current_id)
            if entity:
                nodes.append({
                    "id": str(entity.id),
                    "name": entity.name,
                    "type": entity.entity_type,
                    "industry_id": str(entity.industry_id) if entity.industry_id else None,
                    "depth": depth,
                    "verified": entity.verified,
                })

            # Fetch outgoing relationships
            rels_query = select(EntityRelationship).where(
                and_(
                    EntityRelationship.source_entity_id == current_id,
                    EntityRelationship.is_active.is_(True),
                    EntityRelationship.strength >= min_strength,
                )
            )
            if relationship_types:
                rels_query = rels_query.where(
                    EntityRelationship.relationship_type.in_(relationship_types)
                )

            result = await self.db.execute(rels_query)
            for rel in result.scalars():
                edges.append({
                    "id": str(rel.id),
                    "source": str(rel.source_entity_id),
                    "target": str(rel.target_entity_id),
                    "type": rel.relationship_type,
                    "strength": rel.strength,
                    "confidence": rel.confidence,
                    "evidence_count": len(rel.evidence_signals or []),
                })
                if depth + 1 <= max_depth:
                    queue.append((rel.target_entity_id, depth + 1))

            # Also fetch incoming relationships (for bidirectional traversal)
            incoming_query = select(EntityRelationship).where(
                and_(
                    EntityRelationship.target_entity_id == current_id,
                    EntityRelationship.is_active.is_(True),
                    EntityRelationship.strength >= min_strength,
                    EntityRelationship.bidirectional.is_(True),
                )
            )
            if relationship_types:
                incoming_query = incoming_query.where(
                    EntityRelationship.relationship_type.in_(relationship_types)
                )

            result = await self.db.execute(incoming_query)
            for rel in result.scalars():
                edges.append({
                    "id": str(rel.id),
                    "source": str(rel.source_entity_id),
                    "target": str(rel.target_entity_id),
                    "type": rel.relationship_type,
                    "strength": rel.strength,
                    "confidence": rel.confidence,
                    "evidence_count": len(rel.evidence_signals or []),
                })
                if depth + 1 <= max_depth:
                    queue.append((rel.source_entity_id, depth + 1))

        return {
            "center_entity_id": str(entity_id),
            "nodes": nodes,
            "edges": edges,
            "depth": max_depth,
        }

    async def get_entity_full_profile(
        self,
        entity_id: UUID,
    ) -> dict[str, Any]:
        """Get a comprehensive entity profile with all cross-source data.

        This is the proprietary data fusion output — combining data from
        all tracked sources into a single rich profile that can't be
        replicated from any single source.
        """
        entity = await self.db.get(Entity, entity_id)
        if not entity:
            return {}

        # Get aliases
        alias_result = await self.db.execute(
            select(EntityAlias).where(EntityAlias.entity_id == entity_id)
        )
        aliases = [
            {
                "name": a.alias_name,
                "type": a.alias_type,
                "source": a.source,
                "confidence": a.confidence,
            }
            for a in alias_result.scalars()
        ]

        # Get source profiles
        profiles = await self.get_entity_profiles(entity_id)
        source_data = {
            p.source_type: {
                "source_id": p.source_id,
                "data": p.profile_data,
                "confidence": p.confidence,
                "last_synced": p.last_synced_at.isoformat() if p.last_synced_at else None,
            }
            for p in profiles
        }

        # Get relationship counts
        out_count = await self.db.execute(
            select(func.count(EntityRelationship.id)).where(
                and_(
                    EntityRelationship.source_entity_id == entity_id,
                    EntityRelationship.is_active.is_(True),
                )
            )
        )
        in_count = await self.db.execute(
            select(func.count(EntityRelationship.id)).where(
                and_(
                    EntityRelationship.target_entity_id == entity_id,
                    EntityRelationship.is_active.is_(True),
                )
            )
        )

        # Signal count
        signal_count = await self.db.execute(
            select(func.count(SignalEntity.id)).where(
                SignalEntity.entity_id == entity_id
            )
        )

        return {
            "entity": {
                "id": str(entity.id),
                "name": entity.name,
                "type": entity.entity_type,
                "industry_id": str(entity.industry_id) if entity.industry_id else None,
                "description": entity.description,
                "verified": entity.verified,
            },
            "aliases": aliases,
            "source_profiles": source_data,
            "relationships": {
                "outgoing_count": out_count.scalar_one(),
                "incoming_count": in_count.scalar_one(),
            },
            "signal_count": signal_count.scalar_one(),
            "data_richness": len(source_data),  # More profiles = richer intelligence
        }

    # ── P1 Feature: Influence Integration ───────────────────────────

    async def get_entity_with_influence(
        self,
        entity_id: UUID,
        *,
        industry_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Get comprehensive entity profile including influence metrics.

        Combines entity resolution data with influence scoring from network analysis.
        This provides a complete intelligence picture of an entity.

        Args:
            entity_id: Entity UUID
            industry_id: Optional industry filter for influence calculation

        Returns:
            Entity profile with influence metrics and network position
        """
        from backend.services.influence_mapping import InfluenceMappingService

        # Get base entity profile
        profile = await self.get_entity_profile(entity_id)

        # Get influence metrics
        influence_service = InfluenceMappingService(self.db)
        influence_data = await influence_service.calculate_entity_influence_score(
            entity_id,
            industry_id=industry_id,
            algorithm="composite"
        )

        # Merge the data
        profile["influence"] = {
            "score": influence_data.get("influence_score", 0.0),
            "metrics": influence_data.get("metrics", {}),
            "interpretation": influence_data.get("interpretation", ""),
            "network_size": influence_data.get("network_size", 0),
        }

        return profile
