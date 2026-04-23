"""
ApplicationAuthService — authentication for application users (user_type=1).
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseAuth import BaseAuth
from src.config.Settings import settings
from src.core.Security import get_password_hash
from src.models.Workspace import workspace_personas
from src.models.WorkspaceBilling import WorkspaceBilling
from src.repositories.PersonaRepository import PersonaRepository
from src.repositories.RoleRepository import RoleRepository
from src.repositories.UserRepository import UserRepository
from src.repositories.WorkspaceRepository import WorkspaceRepository


class ApplicationAuthService(BaseAuth):
    """Application authentication service — async SQLAlchemy 2.x."""

    def __init__(self, db: AsyncSession) -> None:
        user_repo = UserRepository(db)
        role_repo = RoleRepository(db)
        super().__init__(user_repo, role_repo)

        self.db = db
        self.user_repo = user_repo
        self.role_repo = role_repo
        self.workspace_repo = WorkspaceRepository(db)
        self.persona_repo = PersonaRepository(db)

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    async def login(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate an application user and return tokens + user data."""
        user = await self.authenticate_user(email, password)
        if not user:
            return None

        # Enforce application user type
        if user.get("user_type") != 1:
            return None

        # Reject login when the workspace has been deactivated
        workspace_id = user.get("workspace_id")
        if workspace_id is not None:
            workspace = await self.workspace_repo.get_by_id(workspace_id)
            if workspace is None or not workspace.get("is_active", False):
                raise PermissionError(
                    "Your workspace is inactive. Please contact support."
                )

        token_data = {
            "sub": str(user["id"]),
            "email": user["email"],
            "user_type": 1,
        }

        access_token = self.create_access_token(token_data)
        refresh_token = self.create_refresh_token(token_data)
        user_with_role = await self.get_user_with_role(user["id"])

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": user_with_role,
            "jwt_enabled": True,
        }

    # ------------------------------------------------------------------
    # Signup
    # ------------------------------------------------------------------

    async def signup(
        self,
        workspace_data: Dict[str, Any],
        persona_data: Dict[str, Any],
        admin_data: Dict[str, Any],
        referred_by: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Complete signup: create workspace, workspace_billing, persona, and admin user.
        All writes are in a single atomic transaction.
        """
        try:
            # 1. Get or create Owner role (role_type=1)
            owner_role = await self.role_repo.get_by_name_and_type("Owner", 1)
            if not owner_role:
                owner_role = await self.role_repo.create({
                    "name": "Owner",
                    "role_type": 1,
                    "description": "Workspace owner with full access",
                    "is_active": True,
                })

            # 2. Create workspace
            workspace_payload: Dict[str, Any] = {
                "name": workspace_data["name"],
                "description": workspace_data.get("description"),
                "owner_id": None,  # Back-filled after user creation
                "referred_by": referred_by,
                "is_active": True,
            }
            created_workspace = await self.workspace_repo.create(workspace_payload)
            workspace_id = created_workspace["id"]

            # 3. Create workspace_billing (plan=free)
            billing = WorkspaceBilling(
                workspace_id=workspace_id,
                plan="free",
                plan_status="active",
            )
            self.db.add(billing)
            await self.db.flush()

            # 4. Create persona
            persona_payload: Dict[str, Any] = {
                "name": persona_data["name"],
                "description": persona_data.get("description"),
                "workspace_id": workspace_id,
                "persona_type": persona_data.get("persona_type", 0),
                "order_type": persona_data.get("order_type", 0),
                "address": persona_data.get("address"),
                "city": persona_data.get("city"),
                "state": persona_data.get("state"),
                "country": persona_data.get("country"),
                "postal_code": persona_data.get("postal_code"),
                "phone": persona_data.get("phone"),
                "email": persona_data.get("email"),
                "is_active": True,
            }
            created_persona = await self.persona_repo.create(persona_payload)
            persona_id = created_persona["id"]

            # 5. Link workspace <-> persona
            stmt = (
                pg_insert(workspace_personas)
                .values(workspace_id=workspace_id, persona_id=persona_id)
                .on_conflict_do_nothing()
            )
            await self.db.execute(stmt)

            # 6. Create admin user (user_type=1)
            created_owner = await self.user_repo.create({
                "user_type": 1,
                "email": admin_data["email"],
                "password_hash": get_password_hash(admin_data["password"]),
                "first_name": admin_data["first_name"],
                "last_name": admin_data["last_name"],
                "phone": admin_data.get("phone"),
                "role_id": owner_role["id"],
                "workspace_id": workspace_id,
                "is_active": True,
            })

            # 7. Back-fill workspace.owner_id
            await self.workspace_repo.update(workspace_id, {"owner_id": created_owner["id"]})
            created_workspace["owner_id"] = created_owner["id"]

        except IntegrityError as exc:
            raise ValueError(
                f"User with email '{admin_data['email']}' already exists."
            ) from exc

        created_owner.pop("password_hash", None)

        return {
            "workspace": created_workspace,
            "persona": created_persona,
            "user": created_owner,
        }
