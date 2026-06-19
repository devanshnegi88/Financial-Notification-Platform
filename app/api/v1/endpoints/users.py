from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import UserRole
from app.core.exceptions import ConflictError, NotFoundError
from app.db.base import get_db
from app.middleware.auth_middleware import (
    CurrentUser,
    get_current_user,
    require_admin,
    require_manager,
)
from app.repositories.user_repository import UserRepository
from app.schemas.common import MessageResponse, PaginatedResponse, PaginationParams
from app.schemas.user import UserAdminUpdate, UserListResponse, UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=PaginatedResponse[UserListResponse])
async def list_users(
    pagination: PaginationParams = Depends(),
    is_active: bool | None = Query(default=None),
    role: UserRole | None = Query(default=None),
    _: CurrentUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import and_, func, select
    from app.models.user import User

    query = select(User)
    count_q = select(func.count()).select_from(User)

    filters = []
    if is_active is not None:
        filters.append(User.is_active == is_active)
    if role is not None:
        filters.append(User.role == role)

    if filters:
        query = query.where(and_(*filters))
        count_q = count_q.where(and_(*filters))

    query = query.order_by(User.created_at.desc()).offset(pagination.offset).limit(pagination.page_size)

    items_result = await db.execute(query)
    count_result = await db.execute(count_q)

    items = list(items_result.scalars().all())
    total = count_result.scalar_one()

    return PaginatedResponse.build(
        items=[UserListResponse.model_validate(u) for u in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Users can only fetch their own profile unless admin/manager
    if current_user.user_id != user_id and current_user.role not in (
        UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.MANAGER
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    repo = UserRepository(db)
    user = await repo.get(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.user_id != user_id and current_user.role not in (
        UserRole.SUPERADMIN, UserRole.ADMIN
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    repo = UserRepository(db)
    user = await repo.get(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    updates = payload.model_dump(exclude_none=True)
    if not updates:
        return user

    if "phone" in updates and updates["phone"]:
        existing = await repo.get_by_phone(updates["phone"])
        if existing and existing.id != user_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone already in use")

    updated = await repo.update(user, updates)
    return updated


@router.put("/{user_id}/admin", response_model=UserResponse)
async def admin_update_user(
    user_id: UUID,
    payload: UserAdminUpdate,
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository(db)
    user = await repo.get(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    updates = payload.model_dump(exclude_none=True)
    if not updates:
        return user

    updated = await repo.update(user, updates)
    return updated


@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: UUID,
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository(db)
    user = await repo.get(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await repo.delete(user)
    return MessageResponse(message="User deleted successfully")
