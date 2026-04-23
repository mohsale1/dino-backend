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
        Sensitive fields are stripped before returning.
        """
        user = await self.user_repository.get_by_id(user_id)

        if not user:
            return None

        role = await self.role_repository.get_by_id(user.get("role_id", ""))

        # Strip sensitive / internal fields
        for field in ("password_hash", "created_by", "is_system"):
            user.pop(field, None)

        if role:
            user["role"] = {
                "id": role.get("id"),
                "name": role.get("name"),
                "role_type": role.get("role_type"),
                "permissions": role.get("permissions", []),
            }
            user["role_name"] = role.get("name")

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
