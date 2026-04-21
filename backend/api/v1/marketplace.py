"""Signal Marketplace API.

Browse, subscribe, and manage signal template subscriptions.
"""

import logging
from typing import cast
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.auth.dependencies import get_current_user
from backend.auth.schemas import AuthContext
from backend.database import get_db, get_db_read
from backend.job_queue import enqueue_job
from backend.jobs.acquisition_job import fetch_single_contract
from backend.middleware.feature_gating import require_feature
from backend.models.signal_contract import SignalContract
from backend.models.signal_template import SignalTemplate, SignalTemplateSubscription

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/marketplace")


# ── Schemas ──────────────────────────────────────────────────────────


class SignalTemplateResponse(BaseModel):
    """Marketplace template card response."""

    id: UUID
    name: str
    slug: str
    description: str | None
    short_description: str | None
    industry_id: UUID
    signal_type: str
    primary_country: str | None
    regions: list[str]
    tags: list[str]
    source_type: str
    schedule_tier: str
    is_official: bool
    is_featured: bool
    subscription_count: int
    preview_signal_count: int
    # Contextual: is this org already subscribed?
    is_subscribed: bool = False

    model_config = {"from_attributes": True}


class SignalTemplateListResponse(BaseModel):
    items: list[SignalTemplateResponse]
    total: int
    skip: int
    limit: int


class SubscribeRequest(BaseModel):
    template_id: UUID


class SubscribeResponse(BaseModel):
    subscription_id: UUID
    contract_id: UUID
    template_id: UUID
    message: str


# ── Endpoints ────────────────────────────────────────────────────────


@router.get("", response_model=SignalTemplateListResponse)
async def list_templates(
    country: str | None = Query(None, description="ISO 3166-1 alpha-3 (e.g. NGA)"),
    industry_id: UUID | None = Query(None),
    signal_type: str | None = Query(None),
    tag: str | None = Query(None, description="Filter by a single tag"),
    search: str | None = Query(
        None, description="Full-text search on name/description"
    ),
    featured_only: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_read),
):
    """Browse the signal marketplace.

    Returns available templates ordered by featured → subscription count.
    Each result includes whether the current org is already subscribed.
    """
    stmt = select(SignalTemplate).where(SignalTemplate.is_active.is_(True))

    if country:
        stmt = stmt.where(
            or_(
                SignalTemplate.primary_country == country,
                SignalTemplate.regions.any(country),  # type: ignore[attr-defined]
            )
        )
    if industry_id:
        stmt = stmt.where(SignalTemplate.industry_id == industry_id)
    if signal_type:
        stmt = stmt.where(SignalTemplate.signal_type == signal_type)
    if tag:
        stmt = stmt.where(SignalTemplate.tags.any(tag))  # type: ignore[attr-defined]
    if featured_only:
        stmt = stmt.where(SignalTemplate.is_featured.is_(True))
    if search:
        search_term = f"%{search}%"
        stmt = stmt.where(
            or_(
                SignalTemplate.name.ilike(search_term),
                SignalTemplate.description.ilike(search_term),
                SignalTemplate.short_description.ilike(search_term),
            )
        )

    # Count for pagination
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        stmt.order_by(
            SignalTemplate.is_featured.desc(), SignalTemplate.subscription_count.desc()
        )
        .offset(skip)
        .limit(limit)
    )
    templates = (await db.execute(stmt)).scalars().all()

    # Load current org's subscriptions for these templates in one query
    template_ids = [t.id for t in templates]
    subscribed_ids: set[UUID] = set()
    if template_ids:
        sub_result = await db.execute(
            select(SignalTemplateSubscription.template_id).where(
                SignalTemplateSubscription.org_id == auth.org_id,
                SignalTemplateSubscription.template_id.in_(template_ids),
                SignalTemplateSubscription.is_active.is_(True),
            )
        )
        subscribed_ids = {row[0] for row in sub_result.all()}

    items = []
    for t in templates:
        resp = SignalTemplateResponse.model_validate(t)
        resp.is_subscribed = t.id in subscribed_ids
        items.append(resp)

    return SignalTemplateListResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/subscriptions", response_model=list[SignalTemplateResponse])
async def list_subscriptions(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_read),
):
    """List all active marketplace subscriptions for the current org."""
    result = await db.execute(
        select(SignalTemplate)
        .join(
            SignalTemplateSubscription,
            SignalTemplateSubscription.template_id == SignalTemplate.id,
        )
        .where(
            SignalTemplateSubscription.org_id == auth.org_id,
            SignalTemplateSubscription.is_active.is_(True),
        )
        .order_by(SignalTemplate.name)
    )
    templates = result.scalars().all()
    items = []
    for t in templates:
        resp = SignalTemplateResponse.model_validate(t)
        resp.is_subscribed = True
        items.append(resp)
    return items


@router.get("/{template_id}", response_model=SignalTemplateResponse)
async def get_template(
    template_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_read),
):
    """Get marketplace template detail."""
    result = await db.execute(
        select(SignalTemplate).where(
            SignalTemplate.id == template_id, SignalTemplate.is_active.is_(True)
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Check if already subscribed
    sub_result = await db.execute(
        select(SignalTemplateSubscription.id).where(
            SignalTemplateSubscription.template_id == template_id,
            SignalTemplateSubscription.org_id == auth.org_id,
            SignalTemplateSubscription.is_active.is_(True),
        )
    )
    resp = SignalTemplateResponse.model_validate(template)
    resp.is_subscribed = sub_result.scalar_one_or_none() is not None
    return resp


@router.post("/subscribe", response_model=SubscribeResponse)
async def subscribe_to_template(
    body: SubscribeRequest,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _feature_check: bool = Depends(require_feature("marketplace_subscribe")),
):
    """Subscribe to a marketplace template.

    Creates a per-org SignalContract clone at the template's source configuration.
    Idempotent: re-subscribing to an already-active subscription returns 200.
    """
    # Load template
    result = await db.execute(
        select(SignalTemplate).where(
            SignalTemplate.id == body.template_id, SignalTemplate.is_active.is_(True)
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Check existing active subscription
    existing = await db.execute(
        select(SignalTemplateSubscription)
        .where(
            SignalTemplateSubscription.template_id == body.template_id,
            SignalTemplateSubscription.org_id == auth.org_id,
            SignalTemplateSubscription.is_active.is_(True),
        )
        .options(selectinload(SignalTemplateSubscription.template))
    )
    existing_sub = existing.scalar_one_or_none()
    if existing_sub:
        if existing_sub.contract_id is None:
            logger.warning(
                "marketplace_subscription_missing_contract",
                extra={
                    "subscription_id": str(existing_sub.id),
                    "org_id": str(auth.org_id),
                },
            )
            raise HTTPException(
                status_code=409,
                detail="Existing subscription is missing a contract reference; unsubscribe and re-subscribe.",
            )
        contract_id = cast(UUID, existing_sub.contract_id)
        return SubscribeResponse(
            subscription_id=existing_sub.id,
            contract_id=contract_id,
            template_id=body.template_id,
            message="Already subscribed",
        )

    # Create the org-specific SignalContract from the template
    contract = SignalContract(
        id=uuid4(),
        org_id=auth.org_id,
        industry_id=template.industry_id,
        name=f"[{auth.org_id}] {template.name}",
        description=template.description,
        source_url=template.source_url,
        source_type=template.source_type,
        refresh_cron=template.refresh_cron,
        schedule_tier=template.schedule_tier,
        extraction_config=template.extraction_config,
        is_active=True,
        status="active",
    )
    db.add(contract)
    await db.flush()

    # Create subscription record
    subscription = SignalTemplateSubscription(
        id=uuid4(),
        template_id=body.template_id,
        org_id=auth.org_id,
        contract_id=contract.id,
        is_active=True,
    )
    db.add(subscription)

    # Increment template subscription count
    await db.execute(
        update(SignalTemplate)
        .where(SignalTemplate.id == body.template_id)
        .values(subscription_count=SignalTemplate.subscription_count + 1)
    )

    await db.commit()

    if contract.source_type != "webhook":
        try:
            enqueue_job(
                fetch_single_contract,
                str(contract.id),
                queue_name="high",
                job_timeout="5m",
            )
        except Exception as exc:
            logger.warning(
                "marketplace_initial_fetch_enqueue_failed",
                extra={"contract_id": str(contract.id), "error": str(exc)},
            )
    logger.info(
        f"Org {auth.org_id} subscribed to template {template.slug} "
        f"→ contract {contract.id}"
    )

    return SubscribeResponse(
        subscription_id=subscription.id,
        contract_id=contract.id,
        template_id=body.template_id,
        message=f"Subscribed to '{template.name}'. Signal contract created.",
    )


@router.delete("/subscribe/{template_id}", status_code=204)
async def unsubscribe_from_template(
    template_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Unsubscribe from a marketplace template.

    Deactivates the subscription and the associated SignalContract.
    """
    result = await db.execute(
        select(SignalTemplateSubscription).where(
            SignalTemplateSubscription.template_id == template_id,
            SignalTemplateSubscription.org_id == auth.org_id,
            SignalTemplateSubscription.is_active.is_(True),
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    # Deactivate subscription
    sub.is_active = False

    # Deactivate the associated contract
    if sub.contract_id:
        await db.execute(
            update(SignalContract)
            .where(
                SignalContract.id == sub.contract_id,
                SignalContract.org_id == auth.org_id,
            )
            .values(is_active=False, status="disabled")
        )

    # Decrement template subscription count (floor at 0)
    await db.execute(
        update(SignalTemplate)
        .where(SignalTemplate.id == template_id)
        .values(
            subscription_count=func.greatest(SignalTemplate.subscription_count - 1, 0)
        )
    )

    await db.commit()
    logger.info(f"Org {auth.org_id} unsubscribed from template {template_id}")
