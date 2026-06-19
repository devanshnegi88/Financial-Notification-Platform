from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.middleware.auth_middleware import CurrentUser, get_current_user
from app.models.device_token import DeviceToken
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/device-tokens", tags=["Device Tokens"])


class DeviceTokenCreate(BaseModel):
    token: str
    platform: str  # android, ios, web
    device_id: Optional[str] = None
    device_name: Optional[str] = None


class DeviceTokenResponse(BaseModel):
    id: UUID
    token: str
    platform: str
    device_id: Optional[str]
    device_name: Optional[str]
    is_active: bool

    model_config = {"from_attributes": True}


@router.post("/", response_model=DeviceTokenResponse, status_code=status.HTTP_201_CREATED)
async def register_device_token(
    payload: DeviceTokenCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import and_, select
    from datetime import datetime, timezone

    # Check if token already exists for this user
    result = await db.execute(
        select(DeviceToken).where(
            and_(
                DeviceToken.user_id == current_user.user_id,
                DeviceToken.token == payload.token,
            )
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.is_active = True
        existing.last_used_at = datetime.now(timezone.utc)
        if payload.device_name:
            existing.device_name = payload.device_name
        db.add(existing)
        await db.flush()
        await db.refresh(existing)
        return existing

    device_token = DeviceToken(
        user_id=current_user.user_id,
        token=payload.token,
        platform=payload.platform,
        device_id=payload.device_id,
        device_name=payload.device_name,
    )
    db.add(device_token)
    await db.flush()
    await db.refresh(device_token)

    # Update user's firebase_token
    from app.models.user import User
    user_result = await db.execute(select(User).where(User.id == current_user.user_id))
    user = user_result.scalar_one_or_none()
    if user:
        user.firebase_token = payload.token
        db.add(user)
        await db.flush()

    return device_token


@router.delete("/{token_id}", response_model=MessageResponse)
async def deactivate_device_token(
    token_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select

    result = await db.execute(
        select(DeviceToken).where(
            DeviceToken.id == token_id,
            DeviceToken.user_id == current_user.user_id,
        )
    )
    token = result.scalar_one_or_none()
    if not token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device token not found")

    token.is_active = False
    db.add(token)
    await db.flush()
    return MessageResponse(message="Device token deactivated")
