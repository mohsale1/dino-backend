from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import insert, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseAuth import BaseAuth
from src.core.Security import get_password_hash
from src.models.Persona import workspace_personas
from src.repositories.PersonaRepository import PersonaRepository
from src.repositories.RoleRepository import RoleRepository
from src.repositories.UserRepository import UserRepository
from src.repositories.WorkspaceRepository import WorkspaceRepository

# NOTE: Rate limiting for login and signup endpoints must be applied at the
# API gateway or middleware level (e.g. slowapi, nginx limit_req, or a reverse
# proxy).  Implementing it inside the service layer is insufficient because it
# does not protect against distributed attacks and bypasses load-balancer
# routing.


class ApplicationAuthService(BaseAuth):
    """Application authentication service — async SQLAlchemy 2.x."""

    def __init__(self, db: AsyncSession, system_db: Optional[AsyncSession] = None) -> None:
        user_repo = UserRepository(db)
        role_repo = RoleRepository(db)
        super().__init__(user_repo, role_repo)

        self.db = db
        # When no separate system DB session is provided fall back to the
        # primary session (single-DB deployments share the same instance).
        self.system_db: AsyncSession = system_db if system_db is not None else db

        self.user_repo = user_repo
        self.role_repo = role_repo
        self.workspace_repo = WorkspaceRepository(db)
        self.persona_repo = PersonaRepository(db)

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    async def login(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate an application user and return tokens + user data.

        Returns None when credentials are invalid.
        Raises PermissionError when the user's workspace is inactive.
        """
        user = await self.authenticate_user(email, password)

        if not user:
            return None

        # Reject login when the workspace has been deactivated.
        workspace_id = user.get("workspace_id")
        if workspace_id is not None:
            workspace = await self.workspace_repo.get_by_id(workspace_id)
            if workspace is None or not workspace.get("is_active", False):
                raise PermissionError(
                    "Your workspace is inactive. Please contact support."
                )

        token_data = {
            "sub": user["id"],
            "email": user["email"],
            "user_type": "application",
        }

        access_token = self.create_access_token(token_data)
        refresh_token = self.create_refresh_token(token_data)

        user_with_role = await self.get_user_with_role(user["id"])

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": user_with_role,
        }

    # ------------------------------------------------------------------
    # System-user lookup (cross-service via system_db session)
    # ------------------------------------------------------------------

    async def get_system_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Look up a system_users row by its 4-digit string ID.

        Uses a raw SQL query so that dino-application does not need to import
        the dino-system ORM models.  The query targets the system_users table
        which lives in the system DB (or the shared DB in dev).
        """
        stmt = text(
            "SELECT id, email, first_name, last_name, is_active "
            "FROM system_users "
            "WHERE id = :user_id AND is_active = TRUE "
            "LIMIT 1"
        )
        result = await self.system_db.execute(stmt, {"user_id": user_id})
        row = result.mappings().first()
        if row is None:
            return None
        return dict(row)

    # ------------------------------------------------------------------
    # Signup
    # ------------------------------------------------------------------

    async def signup(
        self,
        referral_code: str,
        workspace_data: Dict[str, Any],
        persona_data: Dict[str, Any],
        admin_data: Dict[str, Any],
        billing_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Complete signup process: create workspace, persona, and admin user.

        All writes are performed inside a single database transaction.  Any
        failure causes a full rollback — no compensating deletes are needed.

        Validates the referral code against system_users and tracks who
        onboarded the workspace.

        The workspace_personas join table is populated after both the
        workspace and persona are successfully created.  The Workspace
        ORM model has no persona_ids column — the many-to-many
        relationship is managed exclusively through the join table.

        Note: referred_by, subscription_plan, subscription_status, and
        next_billing_date exist in the DB schema but are not mapped on the
        Workspace ORM model.  referred_by is written via a raw SQL UPDATE
        after the workspace row is created; the subscription fields rely on
        their server-side defaults ('Free' / 'Active' / NULL).

        Email uniqueness is enforced by the database unique constraint.  An
        IntegrityError is caught and re-raised as a ValueError so callers
        receive a clear, actionable message without relying on a racy
        pre-check SELECT.
        """
        # 1. Validate referral code (4-digit system user ID) — done before
        #    opening the transaction because it hits the system DB, not the
        #    application DB, and has no side-effects to roll back.
        if not referral_code or not referral_code.isdigit() or len(referral_code) != 4:
            raise ValueError("Invalid referral code. Must be a 4-digit number.")

        referred_by_user = await self.get_system_user_by_id(referral_code)
        if not referred_by_user:
            raise ValueError(
                f"Invalid referral code '{referral_code}'. User not found."
            )

        if not referred_by_user.get("is_active", False):
            raise ValueError(
                f"Referral code '{referral_code}' is inactive. Please contact support."
            )

        # 2. Execute all writes in a single atomic transaction.
        #    db.begin() is a no-op when the session already has an open
        #    transaction (e.g. in tests that wrap everything in a savepoint),
        #    so this is safe in all deployment configurations.
        try:
            async with self.db.begin():
                # 2a. Get or create Owner role.
                owner_role = await self.role_repo.get_by_name_and_type("Owner", 1)
                if not owner_role:
                    now = datetime.now(timezone.utc)
                    owner_role = await self.role_repo.create(
                        {
                            "name": "Owner",
                            "role_type": 1,
                            "description": "Workspace owner with full access to all resources",
                            "permissions": ["workspace:*"],
                            "is_system": True,
                            "is_active": True,
                            "created_at": now,
                            "updated_at": now,
                        }
                    )

                # 2b. Create workspace.
                now = datetime.now(timezone.utc)
                workspace_payload: Dict[str, Any] = {
                    "name": workspace_data["name"],
                    "description": workspace_data.get("description"),
                    "owner_id": None,  # Back-filled after user creation.
                    "created_at": now,
                    "updated_at": now,
                    "is_active": True,
                }

                if billing_data:
                    workspace_payload.update(
                        {
                            "billing_name": billing_data.get("billing_name"),
                            "billing_email": billing_data.get("billing_email"),
                            "billing_phone": billing_data.get("billing_phone"),
                            "billing_address": billing_data.get("billing_address"),
                            "billing_city": billing_data.get("billing_city"),
                            "billing_state": billing_data.get("billing_state"),
                            "billing_postal_code": billing_data.get("billing_postal_code"),
                            "billing_country": billing_data.get("billing_country"),
                        }
                    )

                created_workspace = await self.workspace_repo.create(workspace_payload)
                workspace_id = created_workspace["id"]

                # Write referred_by via raw SQL (column exists in DB but is
                # not mapped on the Workspace ORM model).
                await self.db.execute(
                    text(
                        "UPDATE workspaces SET referred_by = :referred_by "
                        "WHERE id = :workspace_id"
                    ),
                    {"referred_by": referral_code, "workspace_id": workspace_id},
                )

                # 2c. Create persona.
                now = datetime.now(timezone.utc)
                created_persona = await self.persona_repo.create(
                    {
                        "name": persona_data["name"],
                        "description": persona_data.get("description"),
                        "workspace_id": workspace_id,
                        "address": persona_data.get("address"),
                        "city": persona_data.get("city"),
                        "state": persona_data.get("state"),
                        "country": persona_data.get("country"),
                        "postal_code": persona_data.get("postal_code"),
                        "phone": persona_data.get("phone"),
                        "email": persona_data.get("email"),
                        "organization_type": persona_data.get("organization_type", 0),
                        "order_type": persona_data.get("order_type", 0),
                        "created_at": now,
                        "updated_at": now,
                        "is_active": True,
                    }
                )
                persona_id = created_persona["id"]

                # 2d. Link workspace ↔ persona in the join table.
                await self.db.execute(
                    insert(workspace_personas).values(
                        workspace_id=workspace_id,
                        persona_id=persona_id,
                    )
                )

                # 2e. Create owner user.
                #     The DB unique constraint on (email) will raise
                #     IntegrityError if the address is already taken; that is
                #     caught below and surfaced as a ValueError.
                now = datetime.now(timezone.utc)
                created_owner = await self.user_repo.create(
                    {
                        "email": admin_data["email"],
                        "password_hash": get_password_hash(admin_data["password"]),
                        "first_name": admin_data["first_name"],
                        "last_name": admin_data["last_name"],
                        "phone": admin_data.get("phone"),
                        "role_id": owner_role["id"],
                        "workspace_id": workspace_id,
                        "persona_id": persona_id,
                        "created_at": now,
                        "updated_at": now,
                        "is_active": True,
                    }
                )

                # 2f. Back-fill workspace.owner_id now that we have the user PK.
                await self.workspace_repo.update(
                    workspace_id,
                    {"owner_id": created_owner["id"]},
                )
                created_workspace["owner_id"] = created_owner["id"]

        except IntegrityError as exc:
            # The transaction is already rolled back by the context manager.
            # Surface a clear message for duplicate-email violations.
            raise ValueError(
                f"User with email '{admin_data['email']}' already exists."
            ) from exc

        # 3. Strip sensitive data before returning.
        created_owner.pop("password_hash", None)

        return {
            "workspace": created_workspace,
            "persona": created_persona,
            "admin_user": created_owner,
        }
