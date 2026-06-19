from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import FinancialEventType, NotificationChannel
from app.db.base import get_db
from app.middleware.auth_middleware import require_admin, require_analyst, require_manager
from app.repositories.template_repository import TemplateRepository
from app.schemas.common import MessageResponse, PaginatedResponse, PaginationParams
from app.schemas.template import (
    TemplateCreate,
    TemplateRenderRequest,
    TemplateResponse,
    TemplateUpdate,
)
from app.services.template_service import TemplateService

router = APIRouter(prefix="/templates", tags=["Templates"])


@router.get("/", response_model=PaginatedResponse[TemplateResponse])
async def list_templates(
    pagination: PaginationParams = Depends(),
    event_type: Optional[FinancialEventType] = Query(default=None),
    channel: Optional[NotificationChannel] = Query(default=None),
    locale: Optional[str] = Query(default=None),
    _=Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import and_, func, select
    from app.models.template import NotificationTemplate

    query = select(NotificationTemplate)
    count_q = select(func.count()).select_from(NotificationTemplate)

    filters = []
    if event_type:
        filters.append(NotificationTemplate.event_type == event_type)
    if channel:
        filters.append(NotificationTemplate.channel == channel)
    if locale:
        filters.append(NotificationTemplate.locale == locale)

    if filters:
        query = query.where(and_(*filters))
        count_q = count_q.where(and_(*filters))

    query = query.order_by(NotificationTemplate.created_at.desc()).offset(pagination.offset).limit(pagination.page_size)

    items_result = await db.execute(query)
    count_result = await db.execute(count_q)

    items = list(items_result.scalars().all())
    total = count_result.scalar_one()

    return PaginatedResponse.build(
        items=[TemplateResponse.model_validate(t) for t in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    payload: TemplateCreate,
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = TemplateRepository(db)
    existing = await repo.get_by_event_channel_locale(
        payload.event_type, payload.channel, payload.locale
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Template already exists for {payload.event_type}/{payload.channel}/{payload.locale}",
        )

    template = await repo.create(payload.model_dump())
    return template


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: UUID,
    _=Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    repo = TemplateRepository(db)
    template = await repo.get(template_id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return template


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: UUID,
    payload: TemplateUpdate,
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = TemplateRepository(db)
    template = await repo.get(template_id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    updates = payload.model_dump(exclude_none=True)
    if updates:
        updates["version"] = template.version + 1
        template = await repo.update(template, updates)
    return template


@router.delete("/{template_id}", response_model=MessageResponse)
async def delete_template(
    template_id: UUID,
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = TemplateRepository(db)
    template = await repo.get(template_id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    await repo.delete(template)
    return MessageResponse(message="Template deleted successfully")


@router.post("/render", response_model=dict)
async def render_template(
    payload: TemplateRenderRequest,
    _=Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    service = TemplateService(db)
    result = await service.render_by_id(str(payload.template_id), payload.variables)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found or render failed")
    return result
