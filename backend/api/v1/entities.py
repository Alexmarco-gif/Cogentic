"""Entity Resolution & Graph API endpoints.

Provides entity resolution, entity profiles, and relationship graph
data — the proprietary entity intelligence layer.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.schemas import AuthContext
from backend.database import get_db

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
    from backend.services.entity_resolution import EntityResolutionService

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


@router.post("", status_code=201)
async def create_entity(
    body: EntityCreateRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Create a new canonical entity with aliases."""
    from backend.services.entity_resolution import EntityResolutionService

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
    from backend.services.entity_resolution import EntityResolutionService

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
    from backend.services.entity_resolution import EntityResolutionService

    service = EntityResolutionService(db)
    network = await service.get_entity_network(
        entity_id, max_depth=max_depth, min_strength=min_strength
    )
    return EntityNetworkResponse(
        nodes=network["nodes"],
        edges=network["edges"],
    )


@router.post("/relationships", status_code=201)
async def upsert_relationship(
    body: RelationshipUpsertRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Create or strengthen a relationship between two entities."""
    from backend.services.entity_resolution import EntityResolutionService

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


@router.get("/{entity_id}/with-influence")
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
    from backend.services.entity_resolution import EntityResolutionService

    service = EntityResolutionService(db)
    profile = await service.get_entity_with_influence(
        entity_id, industry_id=industry_id
    )

    if not profile:
        raise HTTPException(status_code=404, detail="Entity not found")

    return profile
