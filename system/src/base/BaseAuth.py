"""
BaseAuth — async authentication helpers for dino-system.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import HTTPException, status
import jwt
from jwt.exceptions import InvalidTokenError

from src.base.BaseRepository import BaseRepository
from src.config.Settings import settings
from src.core.Security import get_password_hash, verify_password


class BaseAuth:
    """Base authentication service backed by async repositories."""

    def __init__(
        self,
        user_repository: BaseRepository,
        role_repository: BaseRepository,
    ) -> None:
        self.user_repository = user_repository
        self.role_repository = role_repository

    # ------------------------------------------------------------------
    # Async methods
    # ------------------------------------------------------------------

    async def authenticate_user(
        self, email: str, password: str
    ) -> Optional[Dict[str, Any]]:
        """
        Verify email + password and return the user dict on success.
        Returns None if the user does not exist, is inactive, or the
        password does not match.
        """
        user = await self.user_repository.get_by_field("email", email.lower())

        if not user:
            return None

        if not user.get("is_active", False):
            return None

        if not verify_password(password, user.get("password_hash", "")):
            return None

        # Stamp last_login — best-effort; do not let a failed update block login.
        now = datetime.now(timezone.utc)
        await self.user_repository.update(user["id"], {"last_login": now})
        user["last_login"] = now.isoformat()

        return user

    async def get_user_with_role(
        self, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Return the user dict enriched with role information.
        Permissions are serialized as dot-notation strings:
          "{category.lower()}.{resource}.{action}"  e.g. "system.dashboard.view"
        Sensitive fields are stripped before returning.
        """
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from src.models.Role import Role

        user = await self.user_repository.get_by_id(user_id)

        if not user:
            return None

        # Strip sensitive / internal fields
        for field in ("password_hash", "created_by", "is_system"):
            user.pop(field, None)

        role_id = user.get("role_id")
        if role_id is None:
            return user

        # Load role with permissions eagerly in a single query
        stmt = (
            select(Role)
            .where(Role.id == role_id)
            .options(selectinload(Role.permissions))
        )
        result = await self.role_repository.db.execute(stmt)
        role_obj = result.scalars().first()

        if role_obj is not None:
            # Serialize each Permission as "category.lower().resource.action"
            # so the frontend constants (e.g. "system.dashboard.view") match exactly.
            permissions = [
                f"{p.category.lower()}.{p.resource}.{p.action}"
                for p in role_obj.permissions
            ]
            user["role"] = {
                "id": role_obj.id,
                "name": role_obj.name,
                "role_type": role_obj.role_type,
                "description": role_obj.description,
                "permissions": permissions,
            }
            user["role_name"] = role_obj.name

        return user

    async def change_password(
        self, user_id: str, old_password: str, new_password: str
    ) -> bool:
        """
        Verify *old_password* then replace it with *new_password*.
        Raises Exception on validation failure.
        """
        user = await self.user_repository.get_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if not verify_password(old_password, user.get("password_hash", "")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

        new_hash = get_password_hash(new_password)
        return await self.user_repository.update(user_id, {
            "password_hash": new_hash,
            "updated_at": datetime.now(timezone.utc),
        })

    # ------------------------------------------------------------------
    # Sync methods (pure JWT — no I/O)
    # ------------------------------------------------------------------

    def create_access_token(
        self, data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        """Encode a signed JWT access token."""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (
            expires_delta
            if expires_delta is not None
            else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        to_encode.update({"exp": expire, "type": "access"})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    def create_refresh_token(self, data: dict) -> str:
        """Encode a signed JWT refresh token."""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        to_encode.update({"exp": expire, "type": "refresh"})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode and verify a JWT token. Returns the payload or None."""
        try:
            return jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
        except InvalidTokenError:
            return None