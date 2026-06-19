from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import UserRole
from app.db.base import get_db
from app.middleware.auth_middleware import CurrentUser, get_current_user
from app.repositories.user_repository import UserRepository
from app.schemas.preference import UserPreferenceResponse, UserPreferenceUpdate

router = APIRouter(prefix="/preferences", tags=["Preferences"])


async def _resolve_target(
    user_id: UUID,
    current_user: CurrentUser,
) -> UUID:
    if user_id != current_user.user_id and current_user.role not in (
        UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.MANAGER
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return user_id


@router.get("/{user_id}", response_model=UserPreferenceResponse)
async def get_preferences(
    user_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _resolve_target(user_id, current_user)
    repo = UserRepository(db)
    pref = await repo.ensure_preferences(user_id)
    return pref


@router.put("/{user_id}", response_model=UserPreferenceResponse)
async def update_preferences(
    user_id: UUID,
    payload: UserPreferenceUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _resolve_target(user_id, current_user)
    repo = UserRepository(db)
    pref = await repo.ensure_preferences(user_id)

    updates = payload.model_dump(exclude_none=True)

    # Serialize disabled_event_types list to comma-separated string
    if "disabled_event_types" in updates:
        event_list = updates.pop("disabled_event_types")
        updates["disabled_event_types"] = ",".join(
            e.value if hasattr(e, "value") else e for e in event_list
        )

    for field, value in updates.items():
        if hasattr(pref, field):
            setattr(pref, field, value)

    db.add(pref)
    await db.flush()
    await db.refresh(pref)
    return pref


@router.post("/{user_id}/reset", response_model=UserPreferenceResponse)
async def reset_preferences(
    user_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _resolve_target(user_id, current_user)

    from sqlalchemy import delete
    from app.models.user_preference import UserPreference

    await db.execute(delete(UserPreference).where(UserPreference.user_id == user_id))
    await db.flush()

    repo = UserRepository(db)
    pref = await repo.ensure_preferences(user_id)
    return pref
