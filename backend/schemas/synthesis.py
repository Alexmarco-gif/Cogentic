"""Pydantic schemas for RAG Synthesis.

Request/response models for on-demand synthesis endpoint.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class SynthesisRequest(BaseModel):
    """RAG synthesis request."""

    query: str = Field(
        ..., min_length=3, max_length=2000, description="Synthesis query"
    )
    max_sources: int = Field(
        default=10, ge=1, le=50, description="Max source signals to retrieve"
    )


class SynthesisSource(BaseModel):
    """Source signal used in synthesis."""

    signal_id: str
    title: str | None
    similarity: float
    confidence: float


class SynthesisResponse(BaseModel):
    """RAG synthesis response."""

    query: str
    synthesis: str
    sources: list[SynthesisSource]
    confidence: float
    cached: bool = False
    response_time_ms: int
