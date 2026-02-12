"""RAG Synthesis API endpoint.

On-demand synthesis: embed query → retrieve signals → LLM synthesis.
"""

import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.schemas import AuthContext
from backend.database import get_db
from backend.schemas.synthesis import (
    SynthesisRequest,
    SynthesisResponse,
    SynthesisSource,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/synthesis")


@router.post("", response_model=SynthesisResponse)
async def synthesize(
    body: SynthesisRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """On-demand RAG synthesis.

    Embeds the query, retrieves top-K similar signals via pgvector,
    synthesizes a response via GPT-4o with guardrails.
    Results cached in Redis for 15 minutes.
    """
    start = time.monotonic()

    from backend.ai.synthesis import SynthesisService

    service = SynthesisService(db)
    try:
        result = await service.synthesize(
            query=body.query,
            top_k=body.max_sources,
        )

        duration_ms = int((time.monotonic() - start) * 1000)

        sources = []
        for s in result.get("sources", []):
            sources.append(SynthesisSource(
                signal_id=s.get("signal_id", ""),
                title=s.get("title"),
                similarity=s.get("similarity", 0.0),
                confidence=s.get("confidence", 0.0),
            ))

        return SynthesisResponse(
            query=body.query,
            synthesis=result.get("synthesis", ""),
            sources=sources,
            confidence=result.get("confidence", 0.0),
            cached=result.get("cached", False),
            response_time_ms=duration_ms,
        )

    except Exception as e:
        logger.error(f"Synthesis failed: {e}")
        raise HTTPException(status_code=500, detail="Synthesis failed")
