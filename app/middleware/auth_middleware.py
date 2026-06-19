from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.constants import UserRole
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import decode_token, is_token_expired

security = HTTPBearer()


class CurrentUser:
    def __init__(self, user_id: UUID, role: UserRole, email: Optional[str] = None):
        self.user_id = user_id
        self.role = role
        self.email = email


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> CurrentUser:
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if is_token_expired(payload):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return CurrentUser(
        user_id=UUID(payload["sub"]),
        role=UserRole(payload["role"]),
    )


def require_roles(*roles: UserRole):
    async def _check(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return _check


require_admin = require_roles(UserRole.SUPERADMIN, UserRole.ADMIN)
require_manager = require_roles(UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.MANAGER)
require_analyst = require_roles(UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.MANAGER, UserRole.ANALYST)
require_superadmin = require_roles(UserRole.SUPERADMIN)
