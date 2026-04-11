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
from backend.models.organization import Organization
from backend.schemas.synthesis import (
    ContractSuggestion,
    CoverageCheckResult,
    SynthesisRequest,
    SynthesisResponse,
    SynthesisSource,
    SynthesisWebSource,
)
from backend.services.credit_service import CreditService, InsufficientCreditsError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/synthesis")


@router.post("", response_model=SynthesisResponse)
async def synthesize(
    body: SynthesisRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
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
    credit_service = CreditService(db)

    try:
        # Consume credits for synthesis (100 credits)
        await credit_service.consume_credits(
            org_id=organization.id,
            user_id=auth.user_id,
            action_type="on_demand_synthesis",
            credits=100,
            metadata={"query": body.query, "max_sources": body.max_sources},
        )

        # Optionally fetch live web results for synthesis enrichment
        web_context = None
        web_sources_raw = []
        if body.include_web_search:
            try:
                from backend.services.web_search import (
                    WebSearchError,
                    get_web_search_provider,
                )
                from backend.services.web_search.localization import (
                    resolve_search_locale,
                )

                provider = get_web_search_provider()
                search_country, search_language = resolve_search_locale(
                    country=organization.default_country,
                    language=organization.default_language,
                )
                if await provider.is_available():
                    web_results = await provider.search(
                        body.query,
                        num_results=5,
                        country=search_country,
                        language=search_language,
                    )
                    if web_results and not isinstance(web_results, WebSearchError):
                        web_context = web_results
                        web_sources_raw = [
                            r.to_dict() if hasattr(r, "to_dict") else r
                            for r in web_results
                        ]
            except Exception as e:
                logger.warning(f"Web search for synthesis failed: {e}")

        result = await service.synthesize(
            query=body.query,
            top_k=body.max_sources,
            web_context=web_context,
        )

        duration_ms = int((time.monotonic() - start) * 1000)

        sources = []
        for s in result.get("sources", []):
            sources.append(
                SynthesisSource(
                    signal_id=s.get("signal_id"),
                    title=s.get("title"),
                    similarity=s.get("similarity", 0.0),
                    confidence=s.get("confidence", 0.0),
                    source_url=s.get("source_url"),
                )
            )

        web_sources = []
        for ws in web_sources_raw:
            web_sources.append(
                SynthesisWebSource(
                    title=ws.get("title"),
                    url=ws.get("url"),
                    source=ws.get("source"),
                    snippet=ws.get("snippet"),
                )
            )

        # Coverage check — always computed from retrieved sources
        coverage = _compute_coverage(sources, result)

        # Contract suggestion — only when requested
        contract_suggestion = None
        if body.suggest_contract:
            contract_suggestion = _build_contract_suggestion(body.query, sources)

        return SynthesisResponse(
            query=body.query,
            synthesis=result.get("synthesis") or result.get("answer", ""),
            sources=sources,
            web_sources=web_sources,
            confidence=result.get("confidence", 0.0),
            cached=result.get("cached", False),
            response_time_ms=duration_ms,
            coverage=coverage,
            contract_suggestion=contract_suggestion,
        )

    except InsufficientCreditsError as e:
        raise HTTPException(
            status_code=402,
            detail=(
                f"Insufficient credits for synthesis. "
                f"Requires {e.required} credits and {e.remaining} remain."
            ),
        ) from e
    except Exception as e:
        logger.error(f"Synthesis failed: {e}")
        raise HTTPException(status_code=500, detail="Synthesis failed")


# ── Helper functions ──────────────────────────────────────────────────────────


def _compute_coverage(
    sources: list[SynthesisSource],
    result: dict,
) -> CoverageCheckResult:
    """Compute a coverage assessment from the retrieved source signals."""
    total = result.get("total_indexed", 0)
    relevant = len([s for s in sources if s.similarity >= 0.5])
    freshest: str | None = None

    # Try to derive freshest_signal_at from result metadata if available
    raw_sources = result.get("sources", [])
    published_dates = [
        s.get("published_at") for s in raw_sources if s.get("published_at")
    ]
    if published_dates:
        freshest = str(max(published_dates))

    # Normalise score against requested top-k cap
    top_k = max(len(sources), 1)
    score = round(min(relevant / top_k, 1.0), 3)

    if score >= 0.7:
        assessment = "good"
    elif score >= 0.3:
        assessment = "partial"
    else:
        assessment = "limited"

    return CoverageCheckResult(
        total_signals=total,
        relevant_signals=relevant,
        coverage_score=score,
        freshest_signal_at=freshest,
        coverage_assessment=assessment,
    )


def _build_contract_suggestion(
    query: str,
    sources: list[SynthesisSource],
) -> ContractSuggestion:
    """Build a contract promotion suggestion from the synthesis query and sources."""
    import re

    # Derive title: capitalise words, cap length
    title_raw = re.sub(r"\s+", " ", query).strip()
    title = title_raw[:120] if len(title_raw) <= 120 else title_raw[:117] + "..."
    if not title[0].isupper():
        title = title[0].upper() + title[1:]

    # Extract simple keywords (non-stopwords, 3+ chars)
    _STOP = {
        "the",
        "and",
        "for",
        "are",
        "was",
        "were",
        "will",
        "has",
        "have",
        "been",
        "that",
        "this",
        "from",
        "with",
        "what",
        "how",
        "why",
        "when",
    }
    words = re.findall(r"\b[a-z]{3,}\b", query.lower())
    keywords = list(dict.fromkeys(w for w in words if w not in _STOP))[:8]

    # Simple industry inference from keywords
    industry_map = {
        "bank|cbn|interest|rate|credit|loan|fintech|forex|exchange": "Financial Services",
        "oil|gas|crude|energy|power|electricity": "Energy",
        "price|retail|consumer|fmcg|food|market|commodity": "FMCG & Retail",
        "telecom|mobile|mtn|airtel|network|internet|data": "Telecommunications",
        "agric|farm|crop|harvest|yield|fertilizer": "Agriculture",
        "regulator|compliance|sec|cac|cbn|policy|rule": "Regulatory & Compliance",
    }
    inferred_industry = None
    query_lower = query.lower()
    for pattern, industry in industry_map.items():
        if re.search(pattern, query_lower):
            inferred_industry = industry
            break

    description = (
        f"Continuously monitor signals related to: {title}. "
        f"Based on on-demand synthesis with {len(sources)} relevant source(s) found."
    )

    return ContractSuggestion(
        suggested_title=title,
        suggested_description=description,
        suggested_keywords=keywords,
        inferred_industry=inferred_industry,
    )
