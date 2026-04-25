"""
BaseAuth — async authentication helpers.

Token creation and verification are synchronous (no DB calls).
All user/role lookups are async and delegate to injected repositories.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import HTTPException, status
import jwt
from jwt.exceptions import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.base.BaseRepository import BaseRepository
from src.base.BaseModel import row_to_dict, SENSITIVE_FIELDS
from src.config.Settings import settings
from src.core.Security import get_password_hash, verify_password
from src.models.Role import Role


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

    async def authenticate_user(
        self,
        email: str,
        password: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Verify *email* + *password* against the database.

        On success, stamps ``last_login`` on the user record and returns the
        user dict.  Returns ``None`` on any authentication failure.
        """
        user = await self.user_repository.get_by_field("email", email.lower())

        if not user:
            return None

        # Guard: no password set — cannot authenticate.
        if not user.get("password_hash"):
            return None

        # Always call verify_password before checking is_active to prevent
        # timing side-channel attacks that could reveal account existence.
        password_ok = verify_password(password, user["password_hash"])

        if not password_ok:
            return None

        if not user.get("is_active", False):
            return None

        # Stamp last_login — best-effort; do not let a failed update block login.
        now = datetime.now(timezone.utc)
        try:
            await self.user_repository.update(user["id"], {"last_login": now})
        except Exception:
            pass  # best-effort — do not block login on a failed timestamp update
        user["last_login"] = now.isoformat()

        return user


    # ------------------------------------------------------------------
    # Token operations (synchronous — no DB access)
    # ------------------------------------------------------------------

    def create_access_token(
        self,
        data: dict,
        expires_delta: Optional[timedelta] = None,
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
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode and verify a JWT token. Returns the payload or None."""
        try:
            return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        except InvalidTokenError:
            return None

    # ------------------------------------------------------------------
    # User helpers
    # ------------------------------------------------------------------

    async def get_user_with_role(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a user by ID and attach a sanitised role sub-dict.

        Issues a single ``selectinload`` query for the role and its permissions
        so that permission codenames are available without a second round-trip.
        Sensitive fields are stripped before returning.
        """
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            return None

        # Strip sensitive / internal fields (whitelist approach via exclusion
        # of the known-sensitive set defined in BaseUser).
        for field in SENSITIVE_FIELDS | {"created_by", "is_system"}:
            user.pop(field, None)

        role_id = user.get("role_id")
        if role_id:
            # Use a selectinload query directly on the repository's session so
            # that Role.permissions ORM objects are available for codename extraction.
            stmt = (
                select(Role)
                .where(Role.id == role_id, Role.is_active.is_(True))
                .options(selectinload(Role.permissions))
            )
            result = await self.role_repository.db.execute(stmt)
            role_obj: Optional[Role] = result.scalar_one_or_none()

            if role_obj is not None:
                codenames = [
                    f"{perm.resource}:{perm.action}"
                    for perm in role_obj.permissions
                    if perm.resource and perm.action
                ]
                user["role"] = {
                    "id": role_obj.id,
                    "name": role_obj.name,
                    "role_type": role_obj.role_type,
                    "permissions": codenames,
                }
                user["role_name"] = role_obj.name

        return user

    async def change_password(
        self,
        user_id: str,
        old_password: str,
        new_password: str,
    ) -> bool:
        """
        Verify *old_password* then replace it with *new_password*.

        The user row is locked with ``SELECT ... FOR UPDATE`` before the
        password is verified, eliminating the TOCTOU race condition that
        existed when a plain ``get_by_id`` read was followed by a separate
        ``update`` write.  The lock is held for the duration of the
        enclosing transaction, so no concurrent request can modify the
        password_hash between the verify and the update.

        Raises
        ------
        HTTPException 404
            If the user is not found (or is soft-deleted).
        HTTPException 400
            If the new password is too short, matches the current password,
            or the old password is incorrect.
        """
        if len(new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters",
            )

        if new_password == old_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must differ from current password",
            )

        # Lock the row for the duration of this transaction so that no
        # concurrent writer can change password_hash between our verify and
        # our update (eliminates the TOCTOU window).
        stmt = (
            select(self.user_repository.model)
            .where(self.user_repository.model.id == user_id)
            .with_for_update()
        )
        # Mirror the is_active guard applied by get_by_id so that
        # soft-deleted users are treated as not found.
        if hasattr(self.user_repository.model, "is_active"):
            stmt = stmt.where(self.user_repository.model.is_active.is_(True))

        result = await self.user_repository.db.execute(stmt)
        row = result.scalars().first()

        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        user = row_to_dict(row)

        if not verify_password(old_password, user.get("password_hash", "")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

        return await self.user_repository.update(user_id, {
            "password_hash": get_password_hash(new_password),
            "updated_at": datetime.now(timezone.utc),
        })


