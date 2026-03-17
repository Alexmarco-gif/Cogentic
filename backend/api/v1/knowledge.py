"""Knowledge Base & Domains API.

Provides REST endpoints for:
- CRUD on knowledge entries (regulatory bodies, sectors, entity types, domains)
- Public /domains endpoint consumed by the frontend for dynamic domain filters
"""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.database import get_db
from backend.services.knowledge_service import KnowledgeService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/knowledge")


# ── Pydantic schemas ─────────────────────────────────────────────────────────


class KnowledgeEntryCreate(BaseModel):
    category: str = Field(..., max_length=100)
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    description: str | None = None
    country: str | None = Field(None, max_length=3)
    region: str | None = Field(None, max_length=100)
    aliases: list[str] = []
    keywords: list[str] = []
    metadata_: dict[str, Any] = Field(default_factory=dict, alias="metadata")
    sort_order: int = 0
    source: str = "manual"
    confidence: float = 1.0


class KnowledgeEntryUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    aliases: list[str] | None = None
    keywords: list[str] | None = None
    metadata_: dict[str, Any] | None = Field(None, alias="metadata")
    sort_order: int | None = None
    confidence: float | None = None


class KnowledgeEntryOut(BaseModel):
    id: UUID
    category: str
    code: str
    name: str
    description: str | None
    country: str | None
    region: str | None
    aliases: list[str] = []
    keywords: list[str] = []
    metadata_: dict[str, Any] = Field(alias="metadata", default_factory=dict)
    sort_order: int
    confidence: float
    source: str | None

    @field_validator("aliases", "keywords", mode="before")
    @classmethod
    def _coerce_list(cls, v: Any) -> list[str]:
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            import json

            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else []
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    @field_validator("metadata_", mode="before")
    @classmethod
    def _coerce_metadata(cls, v: Any) -> dict[str, Any]:
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            import json

            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, dict) else {}
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    model_config = {"from_attributes": True, "populate_by_name": True}


class DomainOut(BaseModel):
    id: str
    code: str
    name: str
    description: str | None = None
    metadata: dict[str, Any] = {}
    sort_order: int = 0


# ── Public endpoints ─────────────────────────────────────────────────────────


@router.get("/domains", response_model=list[DomainOut])
async def list_domains(
    country: str | None = Query(
        None, max_length=3, description="ISO 3166 alpha-3 country code"
    ),
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint — returns the list of active domains.

    Consumed by the frontend to populate domain filters, color-coded tabs, etc.
    No auth required so the login page and public dashboards can use it.
    """
    svc = KnowledgeService(db)
    return await svc.get_domains(country=country)


# ── CRUD (authenticated) ─────────────────────────────────────────────────────


@router.get("", response_model=list[KnowledgeEntryOut])
async def list_entries(
    category: str = Query(..., max_length=100),
    country: str | None = Query(None, max_length=3),
    db: AsyncSession = Depends(get_db),
    _auth=Depends(get_current_user),
):
    """List knowledge entries by category."""
    svc = KnowledgeService(db)
    entries = await svc.list_by_category(category, country=country)
    return entries


@router.post("", response_model=KnowledgeEntryOut, status_code=201)
async def create_entry(
    body: KnowledgeEntryCreate,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(get_current_user),
):
    """Create a new knowledge entry."""
    svc = KnowledgeService(db)
    entry = await svc.create(**body.model_dump(by_alias=False))
    await db.commit()
    return entry


@router.patch("/{entry_id}", response_model=KnowledgeEntryOut)
async def update_entry(
    entry_id: UUID,
    body: KnowledgeEntryUpdate,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(get_current_user),
):
    """Update a knowledge entry."""
    svc = KnowledgeService(db)
    entry = await svc.update_entry(
        entry_id, **body.model_dump(exclude_unset=True, by_alias=False)
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    await db.commit()
    return entry


@router.delete("/{entry_id}", status_code=204)
async def delete_entry(
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(get_current_user),
):
    """Delete a knowledge entry."""
    svc = KnowledgeService(db)
    deleted = await svc.delete_entry(entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Entry not found")
    await db.commit()
