"""Industries API — read-only taxonomy endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.schemas import AuthContext
from backend.database import get_db
from backend.repositories.industry import IndustryRepository

router = APIRouter(prefix="/industries", tags=["industries"])


class IndustryItem(BaseModel):
    id: str
    name: str
    slug: str


@router.get("", response_model=list[IndustryItem])
async def list_industries(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all root industry verticals available on the platform."""
    repo = IndustryRepository(db)
    industries = await repo.get_root_industries()
    return [IndustryItem(id=str(i.id), name=i.name, slug=i.slug) for i in industries]
