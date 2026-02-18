"""RAG Synthesis API endpoint.

On-demand synthesis: embed query → retrieve signals → LLM synthesis.
"""

import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.synthesis import SynthesisService
from backend.auth.dependencies import get_current_user
from backend.auth.schemas import AuthContext
from backend.database import get_db
from backend.middleware.feature_gating import get_current_organization, require_feature
from backend.repositories.credit_repository import CreditRepository
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
    organization=Depends(get_current_organization),
    _feature_check: bool = Depends(require_feature("on_demand_synthesis")),
):
    """On-demand RAG synthesis.

    Embeds the query, retrieves top-K similar signals via pgvector,
    synthesizes a response via GPT-4o with guardrails.
    Results cached in Redis for 15 minutes.

    Consumes 100 credits per synthesis request.
    """
    start = time.monotonic()

    service = SynthesisService(db)
    credit_repo = CreditRepository(db)

    try:
        # Consume credits for synthesis (100 credits)
        await credit_repo.consume_credits(
            account_id=organization.id,
            user_id=auth.user_id,
            action_type="on_demand_synthesis",
            credits=100,
            metadata={"query": body.query, "max_sources": body.max_sources},
        )

        result = await service.synthesize(
            query=body.query,
            top_k=body.max_sources,
        )

        duration_ms = int((time.monotonic() - start) * 1000)

        sources = []
        for s in result.get("sources", []):
            sources.append(
                SynthesisSource(
                    signal_id=s.get("signal_id", ""),
                    title=s.get("title"),
                    similarity=s.get("similarity", 0.0),
                    confidence=s.get("confidence", 0.0),
                )
            )

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
