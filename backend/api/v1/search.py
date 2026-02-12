"""Deep Live Search API endpoints.

Execute searches and view search history.
"""

import logging
import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.schemas import AuthContext
from backend.database import get_db
from backend.repositories.search_query import SearchQueryRepository
from backend.schemas.search import (
    SearchHistoryItem,
    SearchHistoryResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)
from backend.services.deep_search import DeepSearchService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/search")


@router.post("", response_model=SearchResponse)
async def execute_search(
    body: SearchRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Execute a deep live search.

    Performs parallel pgvector + entity search, composite ranking,
    optional AI synthesis. Target P95 < 5s.
    """
    start = time.monotonic()

    service = DeepSearchService(db)
    try:
        result = await service.search(
            query=body.query,
            user_id=auth.user_id,
            org_id=auth.org_id,
            max_results=body.max_results,
            include_synthesis=body.include_synthesis,
        )

        duration_ms = int((time.monotonic() - start) * 1000)

        # Map service result to response schema
        items = []
        for r in result.get("results", []):
            items.append(SearchResultItem(
                signal_id=r.get("signal_id", ""),
                title=r.get("title"),
                summary=r.get("summary"),
                signal_type=r.get("signal_type"),
                confidence=r.get("confidence", 0.0),
                similarity=r.get("similarity", 0.0),
                freshness_score=r.get("freshness_score", 0.0),
                composite_score=r.get("composite_score", 0.0),
                source_url=r.get("source_url"),
                published_at=r.get("published_at"),
            ))

        return SearchResponse(
            query=body.query,
            results=items,
            synthesis=result.get("synthesis"),
            total_results=len(items),
            response_time_ms=duration_ms,
            cached=result.get("cached", False),
        )

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


@router.get("/history", response_model=SearchHistoryResponse)
async def get_search_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Get user's search history."""
    repo = SearchQueryRepository(
        db, org_id=auth.org_id, user_id=auth.user_id
    )
    items = await repo.get_user_history(
        auth.user_id, skip=skip, limit=limit
    )

    return SearchHistoryResponse(
        items=[SearchHistoryItem.model_validate(q) for q in items],
        total=len(items),
        skip=skip,
        limit=limit,
    )
