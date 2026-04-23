"""
SystemAuthService — authentication for system users (user_type=0).
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseAuth import BaseAuth
from src.config.Settings import settings
from src.repositories.RoleRepository import RoleRepository
from src.repositories.UserRepository import UserRepository


class SystemAuthService(BaseAuth):
    """System authentication service."""

    def __init__(self, db: AsyncSession) -> None:
        user_repo = UserRepository(db)
        role_repo = RoleRepository(db)
        super().__init__(user_repo, role_repo)

    async def login(self, email: str, password: str):
        """Authenticate a system user (user_type=0) and return tokens."""
        # authenticate_user from BaseAuth checks email + password
        user = await self.authenticate_user(email, password)
        if not user:
            return None

        # Enforce system-only login
        if user.get("user_type") != 0:
            return None

        user_with_role = await self.get_user_with_role(user["id"])

        if not settings.ENABLE_JWT:
            return {
                "access_token": None,
                "refresh_token": None,
                "token_type": "none",
                "user": user_with_role,
                "jwt_enabled": False,
            }

        token_data = {
            "sub": str(user["id"]),
            "email": user["email"],
            "user_type": 0,
        }
        access_token = self.create_access_token(token_data)
        refresh_token = self.create_refresh_token(token_data)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": user_with_role,
            "jwt_enabled": True,
        }

