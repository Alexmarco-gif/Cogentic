"""Deep Live Search API endpoints.

Execute searches and view search history.
"""

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.schemas import AuthContext
from backend.database import get_db
from backend.middleware.feature_gating import get_current_organization
from backend.models.organization import Organization
from backend.repositories.search_query import SearchQueryRepository
from backend.schemas.search import (
    SearchHistoryItem,
    SearchHistoryResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
    WebSearchResultItem,
)
from backend.services.credit_service import CreditService, InsufficientCreditsError
from backend.services.deep_search import DeepSearchService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/search")


@router.post("", response_model=SearchResponse)
async def execute_search(
    body: SearchRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    """Execute a deep live search.

    Performs parallel pgvector + entity search, composite ranking,
    optional AI synthesis. Target P95 < 5s.

    Consumes 10 credits (no synthesis) or 25 credits (with synthesis).
    """
    start = time.monotonic()

    credit_service = CreditService(db)
    action = "deep_search_synthesis" if body.include_synthesis else "deep_search"
    service = DeepSearchService(db)
    try:
        await credit_service.consume_credits(
            org_id=organization.id,
            user_id=auth.user_id,
            action_type=action,
            credits=CreditService.CREDIT_COSTS[action],
            metadata={"query": body.query, "synthesize": body.include_synthesis},
        )

        result = await service.search(
            query=body.query,
            user_id=auth.user_id,
            org_id=auth.org_id,
            country=organization.default_country,
            language=organization.default_language,
            max_results=body.max_results,
            synthesize=body.include_synthesis,
        )

        duration_ms = int((time.monotonic() - start) * 1000)

        # Map fused signal results (internal + live web) to response schema
        items = []
        for r in result.get("signals", []):
            items.append(
                SearchResultItem(
                    signal_id=str(r.get("id")) if r.get("id") else None,
                    title=r.get("title"),
                    summary=r.get("summary"),
                    signal_type=r.get("signal_type"),
                    confidence=r.get("confidence", 0.0),
                    similarity=r.get("similarity", 0.0),
                    freshness_score=r.get("freshness_score", 0.0),
                    composite_score=r.get("rank_score", r.get("composite_score", 0.0)),
                    source_url=r.get("source_url"),
                    published_at=r.get("published_at"),
                    is_live_web=r.get("is_live_web", False),
                    source=r.get("source"),
                )
            )

        # Map raw web results for dedicated display
        web_items = []
        for wr in result.get("web_results", []):
            web_items.append(
                WebSearchResultItem(
                    title=wr.get("title"),
                    snippet=wr.get("snippet"),
                    url=wr.get("url"),
                    source=wr.get("source"),
                    position=wr.get("position"),
                    published_at=wr.get("published_at"),
                    relevance_score=wr.get("relevance_score"),
                    confidence=wr.get("confidence"),
                )
            )

        return SearchResponse(
            query=body.query,
            results=items,
            web_results=web_items,
            synthesis=result.get("synthesis"),
            total_results=len(items),
            web_result_count=result.get("web_result_count", 0),
            response_time_ms=duration_ms,
            cached=result.get("cached", False),
        )

    except InsufficientCreditsError as e:
        raise HTTPException(
            status_code=402,
            detail=(
                f"Insufficient credits for search. "
                f"Requires {e.required} credits and {e.remaining} remain."
            ),
        ) from e
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
    repo = SearchQueryRepository(db, org_id=auth.org_id, user_id=auth.user_id)
    items = await repo.get_user_history(auth.user_id, skip=skip, limit=limit)

    return SearchHistoryResponse(
        items=[SearchHistoryItem.model_validate(q) for q in items],
        total=len(items),
        skip=skip,
        limit=limit,
    )
