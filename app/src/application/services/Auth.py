"""
ApplicationAuthService — authentication for application users (user_type=1).
"""

import asyncio
from typing import Any, Dict, Optional

from sqlalchemy import text as sa_text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseAuth import BaseAuth
from src.core.Security import get_password_hash
from src.models.User import user_personas
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
    # Login — 2 DB round-trips total
    # ------------------------------------------------------------------

    async def login(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate an app user and return tokens + enriched user dict.
        """
        user = await self.authenticate_user(email, password)
        if not user or user.get("user_type") != 1:
            return None

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
    # Signup — atomic, pre-flight checks sequential
    # ------------------------------------------------------------------

    async def signup(
        self,
        workspace_data: Dict[str, Any],
        persona_data: Dict[str, Any],
        admin_data: Dict[str, Any],
        referral_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Complete signup: workspace + billing + persona + admin user, all atomic.
        """
        admin_email = admin_data["email"].strip().lower()
        _DEFAULT_REFERRER_EMAIL = "default@dino.internal"

        async def _check_email() -> bool:
            return await self.user_repo.email_exists(admin_email)

        async def _resolve_referrer() -> Optional[int]:
            from sqlalchemy import select as _select
            from src.models.User import User as _User
            async def _lookup_system_user(email: str) -> Optional[int]:
                stmt = _select(_User.id).where(
                    _User.email == email,
                    _User.user_type == 0,
                    _User.is_active.is_(True),
                )
                return (await self.db.execute(stmt)).scalar_one_or_none()

            if referral_email:
                ref_id = await _lookup_system_user(referral_email.strip().lower())
                if ref_id is not None:
                    return ref_id
            return await _lookup_system_user(_DEFAULT_REFERRER_EMAIL)

        async def _get_owner_role() -> Optional[Dict[str, Any]]:
            return await self.role_repo.get_by_name_and_type("Owner", 1)

        # ✅ Run sequentially instead of asyncio.gather
        email_taken = await _check_email()
        referrer_user_id = await _resolve_referrer()
        owner_role = await _get_owner_role()

        if email_taken:
            raise ValueError(
                f"An account with the email '{admin_email}' already exists. "
                "Please use a different email address."
            )

        recorded_referral_email = (
            referral_email.strip().lower()
            if referral_email
            else _DEFAULT_REFERRER_EMAIL
        )

        # ------------------------------------------------------------------
        # All writes inside a transaction — fully atomic
        # ------------------------------------------------------------------
        async with self.db.begin():  # ✅ changed from begin_nested()
            try:
                if not owner_role:
                    owner_role = await self.role_repo.create({
                        "name": "Owner",
                        "role_type": 1,
                        "description": "Workspace owner with full access",
                        "is_active": True,
                    })

                created_workspace = await self.workspace_repo.create({
                    "name": workspace_data["name"],
                    "description": workspace_data.get("description"),
                    "is_active": True,
                })
                workspace_id = created_workspace["id"]

                self.db.add(WorkspaceBilling(
                    workspace_id=workspace_id,
                    plan="free",
                    plan_status="active",
                ))

                created_persona = await self.persona_repo.create({
                    "name": persona_data["name"],
                    "description": persona_data.get("description"),
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
                })
                persona_id = created_persona["id"]
                await self.db.flush()

                created_owner = await self.user_repo.create({
                    "user_type": 1,
                    "email": admin_email,
                    "password_hash": get_password_hash(admin_data["password"]),
                    "first_name": admin_data["first_name"],
                    "last_name": admin_data["last_name"],
                    "phone": admin_data.get("phone"),
                    "role_id": owner_role["id"],
                    "is_active": True,
                })
                user_id = created_owner["id"]

                await self.db.execute(
                    pg_insert(workspace_personas)
                    .values(workspace_id=workspace_id, persona_id=persona_id)
                    .on_conflict_do_nothing()
                )
                await self.db.execute(
                    pg_insert(user_personas)
                    .values(user_id=user_id, persona_id=persona_id)
                    .on_conflict_do_nothing()
                )

                if referrer_user_id is not None:
                    await self.db.execute(
                        sa_text(
                            "INSERT INTO workspace_requests"
                            " (email, user_id, workspace_id, status, is_active, created_at, updated_at)"
                            " VALUES (:email, :user_id, :workspace_id, 'pending', true, now(), now())"
                        ),
                        {
                            "email": recorded_referral_email,
                            "user_id": referrer_user_id,
                            "workspace_id": workspace_id,
                        },
                    )

            except IntegrityError as exc:
                await self.db.rollback()  # ✅ added rollback
                err_str = str(exc).lower()
                if "uq_users_email" in err_str or ("users" in err_str and "email" in err_str):
                    raise ValueError(
                        f"An account with the email '{admin_email}' already exists. "
                        "Please use a different email address."
                    ) from exc
                if "workspace" in err_str and "name" in err_str:
                    raise ValueError(
                        f"A workspace named '{workspace_data['name']}' already exists. "
                        "Please choose a different workspace name."
                    ) from exc
                raise ValueError(
                    "Registration failed due to a data conflict. "
                    "Please check your details and try again."
                ) from exc

        created_owner.pop("password_hash", None)
        return {
            "workspace": created_workspace,
            "persona": created_persona,
            "user": created_owner,
        }
    
