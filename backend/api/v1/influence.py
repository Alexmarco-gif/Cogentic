"""Influence mapping API endpoints.

Exposes network analysis and influence scoring functionality for identifying
key players, influence paths, and cascade predictions.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user, require_permissions
from backend.database import get_db
from backend.models.user import User
from backend.services.influence_mapping import InfluenceMappingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/influence", tags=["influence-mapping"])


# === Schemas ===

class InfluenceMetrics(BaseModel):
    """Detailed influence metrics for an entity."""
    pagerank: float = Field(..., description="PageRank centrality score")
    betweenness: float = Field(..., description="Betweenness centrality score")
    eigenvector: float = Field(..., description="Eigenvector centrality score")
    degree: float = Field(..., description="Degree centrality score")
    closeness: float = Field(..., description="Closeness centrality score")


class EntityInfluenceResponse(BaseModel):
    """Entity influence score response."""
    entity_id: str
    entity_name: str | None
    influence_score: float = Field(..., description="Composite influence score (0-1)")
    metrics: InfluenceMetrics
    interpretation: str
    network_size: int


class InfluencerRanking(BaseModel):
    """Ranked influencer in network."""
    entity_id: str
    entity_name: str
    entity_type: str
    influence_score: float
    rank: int
    full_metrics: dict


class KeyInfluencersResponse(BaseModel):
    """List of top influencers response."""
    influencers: list[InfluencerRanking]
    total_count: int
    network_size: int
    industry_id: str | None
    entity_type: str | None


class InfluencePathHop(BaseModel):
    """Single hop in influence path."""
    from_entity: dict
    to_entity: dict
    relationship_type: str
    strength: float


class InfluencePathResponse(BaseModel):
    """Influence path between two entities."""
    source_entity_id: str
    target_entity_id: str
    path_exists: bool
    path_length: int | None
    total_influence_strength: float | None
    path: list[InfluencePathHop] | None
    interpretation: str | None
    error: str | None = None


class AffectedEntity(BaseModel):
    """Entity affected by influence cascade."""
    entity_id: str
    entity_name: str | None
    influence_received: float
    cascade_depth: int


class CascadePredictionResponse(BaseModel):
    """Influence cascade prediction response."""
    origin_entity_id: str
    cascade_type: str
    total_affected_entities: int
    max_depth_reached: int
    affected_entities: list[AffectedEntity]
    propagation_parameters: dict


# === Endpoints ===

@router.get("/entity/{entity_id}/score", response_model=EntityInfluenceResponse)
async def get_entity_influence_score(
    entity_id: UUID,
    industry_id: UUID | None = Query(None, description="Filter network by industry"),
    algorithm: str = Query("composite", description="Scoring algorithm (pagerank, betweenness, composite)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["view_signals"])),
):
    """Calculate comprehensive influence score for an entity.
    
    Uses network centrality metrics to determine entity's influence within the network:
    - PageRank: Global importance
    - Betweenness: Bridge/broker position
    - Closeness: Access to network
    - Degree: Direct connections
    - Eigenvector: Connected to influential nodes
    
    Returns composite score and detailed breakdown.
    """
    influence_service = InfluenceMappingService(db)
    
    try:
        result = await influence_service.calculate_entity_influence_score(
            entity_id,
            industry_id=industry_id,
            algorithm=algorithm
        )
        
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return EntityInfluenceResponse(**result)
    
    except Exception as e:
        logger.error(f"Error calculating influence score for entity {entity_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/influencers", response_model=KeyInfluencersResponse)
async def get_key_influencers(
    industry_id: UUID | None = Query(None, description="Filter by industry"),
    entity_type: str | None = Query(None, description="Filter by entity type (company, person, etc.)"),
    top_k: int = Query(10, ge=1, le=100, description="Number of top influencers to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["view_signals"])),
):
    """Identify the most influential entities in a network.
    
    Returns ranked list of entities by influence score, useful for:
    - Identifying key decision-makers
    - Finding power brokers
    - Understanding network structure
    - Targeting outreach efforts
    """
    influence_service = InfluenceMappingService(db)
    
    try:
        influencers = await influence_service.identify_key_influencers(
            industry_id=industry_id,
            entity_type=entity_type,
            top_k=top_k
        )
        
        return KeyInfluencersResponse(
            influencers=influencers,
            total_count=len(influencers),
            network_size=influencers[0]["full_metrics"].get("network_size", 0) if influencers else 0,
            industry_id=str(industry_id) if industry_id else None,
            entity_type=entity_type
        )
    
    except Exception as e:
        logger.error(f"Error identifying key influencers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/path/{source_id}/{target_id}", response_model=InfluencePathResponse)
async def find_influence_path(
    source_id: UUID,
    target_id: UUID,
    max_hops: int = Query(5, ge=1, le=10, description="Maximum path length"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["view_signals"])),
):
    """Find the influence path between two entities.
    
    Identifies how influence flows from source to target through intermediaries.
    Useful for:
    - Understanding relationship chains
    - Finding connection paths
    - Analyzing influence propagation routes
    - Identifying gatekeepers
    """
    influence_service = InfluenceMappingService(db)
    
    try:
        result = await influence_service.find_influence_path(
            source_entity_id=source_id,
            target_entity_id=target_id,
            max_hops=max_hops
        )
        
        return InfluencePathResponse(**result)
    
    except Exception as e:
        logger.error(f"Error finding influence path from {source_id} to {target_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cascade/{origin_id}", response_model=CascadePredictionResponse)
async def predict_influence_cascade(
    origin_id: UUID,
    cascade_type: str = Query("positive", description="Type of influence (positive, negative, neutral)"),
    propagation_decay: float = Query(0.8, ge=0.1, le=1.0, description="Influence decay rate per hop"),
    max_depth: int = Query(3, ge=1, le=5, description="Maximum cascade depth"),
    min_threshold: float = Query(0.1, ge=0.01, le=0.5, description="Minimum influence threshold"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["view_signals"])),
):
    """Predict how influence/impact cascades through the network.
    
    Simulates influence propagation from origin entity to predict:
    - Which entities will be affected
    - How much influence they'll receive
    - At what cascade depth
    
    Example use cases:
    - Predict bankruptcy ripple effects
    - Model policy change impacts
    - Forecast supply chain disruptions
    - Estimate crisis contagion
    """
    influence_service = InfluenceMappingService(db)
    
    try:
        result = await influence_service.predict_influence_cascade(
            origin_entity_id=origin_id,
            cascade_type=cascade_type,
            propagation_decay=propagation_decay,
            max_depth=max_depth,
            min_influence_threshold=min_threshold
        )
        
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return CascadePredictionResponse(**result)
    
    except Exception as e:
        logger.error(f"Error predicting influence cascade from {origin_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entity/{entity_id}/changes")
async def get_influence_changes_over_time(
    entity_id: UUID,
    lookback_days: int = Query(90, ge=7, le=365, description="Lookback period in days"),
    granularity: str = Query("weekly", description="Time granularity (daily, weekly, monthly)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["view_signals"])),
):
    """Track how an entity's influence has changed over time.
    
    Identifies:
    - Rising stars (increasing influence)
    - Declining powers (decreasing influence)
    - Stable influencers (consistent influence)
    
    Note: Requires historical relationship data (not yet fully implemented).
    """
    influence_service = InfluenceMappingService(db)
    
    result = await influence_service.get_influence_changes_over_time(
        entity_id,
        lookback_days=lookback_days,
        granularity=granularity
    )
    
    return result
