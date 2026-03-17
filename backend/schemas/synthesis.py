"""Pydantic schemas for RAG Synthesis.

Request/response models for on-demand synthesis endpoint.
"""

from pydantic import BaseModel, Field


class SynthesisRequest(BaseModel):
    """RAG synthesis request."""

    query: str = Field(
        ..., min_length=3, max_length=2000, description="Synthesis query"
    )
    max_sources: int = Field(
        default=10, ge=1, le=50, description="Max source signals to retrieve"
    )
    include_web_search: bool = Field(
        default=True, description="Include live web search results in synthesis"
    )
    suggest_contract: bool = Field(
        default=False,
        description="If True, include a contract promotion suggestion in the response",
    )


class SynthesisSource(BaseModel):
    """Source signal used in synthesis."""

    signal_id: str | None = None
    title: str | None
    similarity: float
    confidence: float
    source_url: str | None = None


class SynthesisWebSource(BaseModel):
    """Live web source used in synthesis."""

    title: str | None
    url: str | None
    source: str | None
    snippet: str | None = None


class CoverageCheckResult(BaseModel):
    """How well the platform's existing signals cover the query."""

    total_signals: int
    relevant_signals: int
    coverage_score: float = Field(description="0.0–1.0 normalised coverage score")
    freshest_signal_at: str | None
    coverage_assessment: str = Field(
        description="good (>=0.7) | partial (0.3-0.7) | limited (<0.3)"
    )


class ContractSuggestion(BaseModel):
    """Suggested signal contract to promote this on-demand query to continuous monitoring."""

    suggested_title: str
    suggested_description: str
    suggested_keywords: list[str]
    inferred_industry: str | None


class SynthesisResponse(BaseModel):
    """RAG synthesis response."""

    query: str
    synthesis: str
    sources: list[SynthesisSource]
    web_sources: list[SynthesisWebSource] = Field(default_factory=list)
    confidence: float
    cached: bool = False
    response_time_ms: int
    coverage: CoverageCheckResult | None = None
    contract_suggestion: ContractSuggestion | None = None
