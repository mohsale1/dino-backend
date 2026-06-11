"""
BaseAuth — async authentication helpers.
Token creation/verification are synchronous (no DB calls).
All user/role lookups are async and delegate to injected repositories.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from jwt.exceptions import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.base.BaseRepository import BaseRepository
from src.base.BaseModel import row_to_dict, SENSITIVE_FIELDS
from src.config.Settings import settings
from src.core.Constants import ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
from src.core.Exceptions import NotFoundError, PasswordIncorrectError, PasswordSameError, PasswordTooShortError
from src.core.Security import get_password_hash, verify_password
from src.models.Role import Role
from src.models.User import User

logger = logging.getLogger(__name__)


class BaseAuth:
    """Base authentication service. Concrete auth services extend this class."""

    def __init__(
        self,
        user_repository: BaseRepository,
        role_repository: BaseRepository,
    ) -> None:
        self.user_repository = user_repository
        self.role_repository = role_repository

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    async def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Verify email + password. Returns user dict on success, None on failure.
        Stamps last_login best-effort after successful auth.
        """
        user = await self.user_repository.get_by_field("email", email.lower())

        if not user:
            logger.warning("auth.authenticate.not_found email=%s", email)
            return None

        if not user.get("password_hash"):
            logger.warning("auth.authenticate.no_password user_id=%s", user.get("id"))
            return None

        # Verify password before checking is_active — prevents timing side-channel
        if not verify_password(password, user["password_hash"]):
            logger.warning("auth.authenticate.bad_password user_id=%s", user.get("id"))
            return None

        if not user.get("is_active", False):
            logger.warning("auth.authenticate.inactive user_id=%s", user.get("id"))
            return None

        # Stamp last_login — best-effort, never blocks login
        now = datetime.now(timezone.utc)
        try:
            await self.user_repository.update(user["id"], {"last_login": now})
        except Exception:
            pass
        user["last_login"] = now.isoformat()

        return user

    # ------------------------------------------------------------------
    # Token operations (synchronous — no DB access)
    # ------------------------------------------------------------------

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (
            expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        to_encode.update({"exp": expire, "type": "access"})
        logger.debug(
            "auth.token.access.created sub=%s expires_at=%s",
            data.get("sub"), expire.isoformat(),
        )
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


    def create_refresh_token(self, data: dict) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        logger.debug(
            "auth.token.refresh.created sub=%s expires_at=%s",
            data.get("sub"), expire.isoformat(),
        )
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        except InvalidTokenError:
            return None

    # ------------------------------------------------------------------
    # User helpers
    # ------------------------------------------------------------------

    async def get_user_with_role(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch user + role + permissions in a single query via selectinload.
        Strips sensitive fields before returning.
        """
        stmt = (
            select(User)
            .where(User.id == user_id, User.is_active.is_(True))
            .options(selectinload(User.role).selectinload(Role.permissions))
        )
        user_obj = (await self.user_repository.db.execute(stmt)).scalar_one_or_none()
        if user_obj is None:
            return None

        user: Dict[str, Any] = row_to_dict(user_obj)

        # Strip sensitive fields
        for field in SENSITIVE_FIELDS | {"created_by", "is_system"}:
            user.pop(field, None)

        role_obj = user_obj.role
        if role_obj is not None:
            user["role"] = {
                "id": role_obj.id,
                "name": role_obj.name,
                "role_type": role_obj.role_type,
                "permissions": [
                    f"{p.resource}:{p.action}"
                    for p in role_obj.permissions
                    if p.resource and p.action
                ],
            }
            user["role_name"] = role_obj.name

        return user

    # ------------------------------------------------------------------
    # Change password
    # ------------------------------------------------------------------

    async def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """
        Verify old_password then replace with new_password.
        Row is locked with SELECT FOR UPDATE to eliminate TOCTOU race.
        """
        if len(new_password) < 8:
            raise PasswordTooShortError()
        if new_password == old_password:
            raise PasswordSameError()

        stmt = (
            select(self.user_repository.model)
            .where(self.user_repository.model.id == user_id)
            .with_for_update()
        )
        if hasattr(self.user_repository.model, "is_active"):
            stmt = stmt.where(self.user_repository.model.is_active.is_(True))

        row = (await self.user_repository.db.execute(stmt)).scalars().first()
        if row is None:
            raise NotFoundError("User not found")

        if not verify_password(old_password, row_to_dict(row).get("password_hash", "")):
            raise PasswordIncorrectError()

        return await self.user_repository.update(user_id, {
            "password_hash": get_password_hash(new_password),
            "updated_at": datetime.now(timezone.utc),
        })
