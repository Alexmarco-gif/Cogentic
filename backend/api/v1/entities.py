"""Entity Resolution & Graph API endpoints.

Provides entity resolution, entity profiles, and relationship graph
data — the proprietary entity intelligence layer.
"""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user, require_permissions
from backend.auth.schemas import AuthContext
from backend.database import get_db
from backend.services.entity_resolution import EntityResolutionService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/entities")


# ── Schemas ──────────────────────────────────────────────────────────


class EntityResolveRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    entity_type: str | None = None


class EntityResolveResponse(BaseModel):
    entity_id: str | None
    name: str
    method: str
    confidence: float
    resolved: bool


class EntityCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    entity_type: str = "company"
    aliases: list[str] = Field(default_factory=list)


class EntityProfileResponse(BaseModel):
    id: str
    name: str
    entity_type: str
    verified: bool
    aliases: list[dict]
    source_profiles: list[dict]
    relationship_count: int
    signal_count: int
    data_richness: float


class EntityNetworkResponse(BaseModel):
    nodes: list[dict]
    edges: list[dict]


class RelationshipUpsertRequest(BaseModel):
    source_entity_id: str
    target_entity_id: str
    relationship_type: str = "related_to"
    strength: float = Field(0.5, ge=0, le=1)
    confidence: float = Field(0.7, ge=0, le=1)
    evidence_signals: list[str] = Field(default_factory=list)


class EntityCreateResponse(BaseModel):
    """Response for creating an entity."""

    id: str
    name: str
    entity_type: str
    aliases: list[str]


class RelationshipUpsertResponse(BaseModel):
    """Response for upserting a relationship."""

    id: str
    relationship_type: str
    strength: float
    confidence: float


# ── Endpoints ────────────────────────────────────────────────────────


@router.post("/resolve", response_model=EntityResolveResponse)
async def resolve_entity(
    body: EntityResolveRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Resolve an entity name to a canonical entity.

    Multi-stage resolution: exact alias → fuzzy match → embedding similarity.
    """
    service = EntityResolutionService(db)
    result = await service.resolve(body.name, entity_type=body.entity_type)

    if result:
        return EntityResolveResponse(
            entity_id=str(result["entity_id"]),
            name=result["name"],
            method=result["method"],
            confidence=result["confidence"],
            resolved=True,
        )
    return EntityResolveResponse(
        entity_id=None,
        name=body.name,
        method="none",
        confidence=0.0,
        resolved=False,
    )


@router.post("", status_code=201, response_model=EntityCreateResponse)
async def create_entity(
    body: EntityCreateRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_permissions(["admin"])),
):
    """Create a new canonical entity with aliases. Requires admin or owner role."""
    service = EntityResolutionService(db)
    entity = await service.create_entity(
        name=body.name,
        entity_type=body.entity_type,
        aliases=body.aliases,
    )
    await db.commit()

    return {
        "id": str(entity.id),
        "name": entity.name,
        "entity_type": entity.entity_type,
        "aliases": body.aliases,
    }


@router.get("/{entity_id}/profile", response_model=EntityProfileResponse)
async def get_entity_profile(
    entity_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Get complete fused profile for an entity.

    Returns data from all source profiles (CAC, customs, LinkedIn, etc.),
    aliases, relationship summary, and data richness score.
    """
    service = EntityResolutionService(db)
    profile = await service.get_entity_full_profile(entity_id)

    if not profile:
        raise HTTPException(status_code=404, detail="Entity not found")

    return EntityProfileResponse(
        id=str(profile["id"]),
        name=profile["name"],
        entity_type=profile["entity_type"],
        verified=profile.get("verified", False),
        aliases=profile.get("aliases", []),
        source_profiles=profile.get("source_profiles", []),
        relationship_count=profile.get("relationship_count", 0),
        signal_count=profile.get("signal_count", 0),
        data_richness=profile.get("data_richness", 0.0),
    )


@router.get("/{entity_id}/network", response_model=EntityNetworkResponse)
async def get_entity_network(
    entity_id: UUID,
    max_depth: int = Query(default=2, ge=1, le=4),
    min_strength: float = Query(default=0.3, ge=0, le=1),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Get entity relationship network (graph traversal).

    Returns nodes and edges up to max_depth from the given entity.
    Useful for visualizing supply chains, competitive landscapes,
    and corporate hierarchies.
    """
    service = EntityResolutionService(db)
    network = await service.get_entity_network(
        entity_id, max_depth=max_depth, min_strength=min_strength
    )
    return EntityNetworkResponse(
        nodes=network["nodes"],
        edges=network["edges"],
    )


@router.post(
    "/relationships", status_code=201, response_model=RelationshipUpsertResponse
)
async def upsert_relationship(
    body: RelationshipUpsertRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_permissions(["admin"])),
):
    """Create or strengthen a relationship between two entities. Requires admin or owner role."""
    service = EntityResolutionService(db)
    rel = await service.upsert_relationship(
        source_entity_id=UUID(body.source_entity_id),
        target_entity_id=UUID(body.target_entity_id),
        relationship_type=body.relationship_type,
        strength=body.strength,
        confidence=body.confidence,
        evidence_signals=body.evidence_signals,
    )
    await db.commit()

    return {
        "id": str(rel.id),
        "relationship_type": rel.relationship_type,
        "strength": rel.strength,
        "confidence": rel.confidence,
    }


@router.get("/{entity_id}/with-influence", response_model=dict[str, Any])
async def get_entity_with_influence(
    entity_id: UUID,
    industry_id: UUID | None = Query(
        None, description="Filter influence network by industry"
    ),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Get comprehensive entity profile including influence metrics.

    Combines entity resolution data (aliases, profiles, relationships)
    with influence scoring from network analysis (PageRank, betweenness, etc.).

    This is the complete intelligence picture — entity data + network position.
    Useful for:
    - Understanding power dynamics
    - Identifying key decision-makers
    - Assessing entity importance
    - Planning stakeholder engagement
    """
    service = EntityResolutionService(db)
    profile = await service.get_entity_with_influence(
        entity_id, industry_id=industry_id
    )

    if not profile:
        raise HTTPException(status_code=404, detail="Entity not found")

    return profile


# ── Entity Discovery Review ──────────────────────────────────────────


class EntityDiscoveryItem(BaseModel):
    id: str
    name: str
    entity_type: str
    discovery_status: str
    discovery_source: str
    created_at: str


class EntityReviewRequest(BaseModel):
    action: str = Field(..., description="approve or reject")


@router.get("/discovery/pending", response_model=list[EntityDiscoveryItem])
async def list_pending_entities(
    discovery_source: str | None = Query(
        None, description="Filter by source: auto_extracted, agent, manual"
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_permissions(["admin"])),
):
    """List entities pending review (auto-discovered by NER).

    These are entities the system discovered during signal refinement
    with moderate confidence. Admin review ensures data quality.
    """
    from sqlalchemy import select

    from backend.models.entity import Entity

    query = (
        select(Entity)
        .where(Entity.discovery_status == "pending_review")
        .order_by(Entity.created_at.desc())
    )
    if discovery_source:
        query = query.where(Entity.discovery_source == discovery_source)
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    entities = result.scalars().all()

    return [
        EntityDiscoveryItem(
            id=str(e.id),
            name=e.name,
            entity_type=e.entity_type,
            discovery_status=e.discovery_status or "active",
            discovery_source=e.discovery_source or "seed",
            created_at=e.created_at.isoformat() if e.created_at else "",
        )
        for e in entities
    ]


@router.post("/{entity_id}/review", status_code=200)
async def review_entity(
    entity_id: UUID,
    body: EntityReviewRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_permissions(["admin"])),
):
    """Approve or reject a pending entity. Requires admin role.

    - approve: sets discovery_status to 'active'
    - reject: sets discovery_status to 'rejected'
    """
    from backend.models.entity import Entity

    entity = await db.get(Entity, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    if body.action == "approve":
        entity.discovery_status = "active"
    elif body.action == "reject":
        entity.discovery_status = "rejected"
    else:
        raise HTTPException(
            status_code=400, detail="action must be 'approve' or 'reject'"
        )

    await db.commit()
    return {
        "entity_id": str(entity_id),
        "name": entity.name,
        "discovery_status": entity.discovery_status,
    }
