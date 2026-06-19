from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import UserRole
from app.core.exceptions import AuthenticationError, ConflictError, NotFoundError
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    is_token_expired,
    verify_password,
)
from app.models.user import User
from app.models.user_preference import UserPreference
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, TokenResponse

logger = get_logger(__name__)


class AuthService:
    def __init__(self, session: AsyncSession):
        self.repo = UserRepository(session)
        self.session = session

    async def register(
        self,
        email: str,
        password: str,
        full_name: str,
        phone: str | None = None,
        role: UserRole = UserRole.USER,
    ) -> User:
        existing = await self.repo.get_by_email(email.lower())
        if existing:
            raise ConflictError(f"User with email {email} already exists")

        if phone:
            existing_phone = await self.repo.get_by_phone(phone)
            if existing_phone:
                raise ConflictError(f"User with phone {phone} already exists")

        user = await self.repo.create({
            "email": email.lower(),
            "hashed_password": get_password_hash(password),
            "full_name": full_name,
            "phone": phone,
            "role": role,
        })

        # Create default preferences
        pref = UserPreference(user_id=user.id)
        self.session.add(pref)
        await self.session.flush()

        logger.info("user_registered", user_id=str(user.id), email=email)
        return user

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self.repo.get_by_email(email.lower())
        if not user:
            raise AuthenticationError("Invalid email or password")

        if not verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")

        if not user.is_active:
            raise AuthenticationError("Account is disabled")

        await self.repo.update(user, {"last_login_at": datetime.now(timezone.utc)})

        access_token = create_access_token(user.id, user.role)
        refresh_token = create_refresh_token(user.id, user.role)

        from app.core.config import settings
        logger.info("user_logged_in", user_id=str(user.id))
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_token(refresh_token)
        except ValueError as e:
            raise AuthenticationError(str(e))

        if payload.get("type") != "refresh":
            raise AuthenticationError("Invalid token type")

        if is_token_expired(payload):
            raise AuthenticationError("Refresh token expired")

        user_id = UUID(payload["sub"])
        user = await self.repo.get(user_id)
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")

        access_token = create_access_token(user.id, user.role)
        new_refresh_token = create_refresh_token(user.id, user.role)

        from app.core.config import settings
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def change_password(self, user_id: UUID, current_password: str, new_password: str) -> None:
        user = await self.repo.get(user_id)
        if not user:
            raise NotFoundError("User not found")

        if not verify_password(current_password, user.hashed_password):
            raise AuthenticationError("Current password is incorrect")

        await self.repo.update(user, {"hashed_password": get_password_hash(new_password)})
        logger.info("password_changed", user_id=str(user_id))
