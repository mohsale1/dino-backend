#Requires -Version 5.1
<#
.SYNOPSIS
    Self-extracting script that restores all git-changed files to disk.

.DESCRIPTION
    When executed, this script writes each embedded file to its correct path
    relative to the repository root (the parent of the system folder).

.NOTES
    Run from anywhere:
        .\system\Dump-GitChanges.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Resolve repo root (parent of the system folder this script lives in)
$_scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$_repoRoot  = Split-Path -Parent $_scriptDir

function Write-EmbeddedFile {
    param(
        [string]$RelativePath,
        [string]$Content
    )
    $fullPath = Join-Path $_repoRoot $RelativePath
    $dir = Split-Path -Parent $fullPath
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    [System.IO.File]::WriteAllText($fullPath, $Content, [System.Text.Encoding]::UTF8)
    Write-Host "  [OK] $RelativePath"
}

Write-Host ""
Write-Host "Restoring git-changed files..." -ForegroundColor Cyan
Write-Host ""

# ==============================================================================
# FILE: system/src/Main.py  [M]
# ==============================================================================
Write-EmbeddedFile "system/src/Main.py" @'
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from src.config.Database import async_session_factory, close_db, initialize_db
from src.config.Settings import settings
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.system.routes import Auth as SystemAuth
from src.system.routes import Billing as SystemBilling
from src.system.routes import Dashboard as SystemDashboard
from src.system.routes import Permissions as SystemPermissions
from src.system.routes import Personas as SystemPersonas
from src.system.routes import Roles as SystemRoles
from src.system.routes import Users as SystemUsers
from src.system.routes import Workspaces as SystemWorkspaces
from src.system.routes import WorkspaceRequests as SystemWorkspaceRequests

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)


async def _run_migrations() -> None:
    """
    Run Alembic migrations fully in-process using the Python API.

    Strategy:
      1. Connect via asyncpg to check the current alembic_version.
      2. Load the ScriptDirectory to find the head revision.
      3. If already at head, skip.
      4. Otherwise run upgrade using EnvironmentContext.configure() on a
         live synchronous connection — no subprocess, no env.py file
         loading, no double-connection conflicts.
         EnvironmentContext.__enter__ installs the 'op' proxy that
         migration scripts depend on (from alembic import op).

    SSL is passed via connect_args; the URL never carries ?sslmode=...
    """
    import asyncpg
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from alembic.runtime.environment import EnvironmentContext
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import pool as sa_pool
    from src.config.Database import _normalize_db_url

    raw_url = os.environ.get("DATABASE_URL", settings.DATABASE_URL)
    clean_url, connect_args = _normalize_db_url(raw_url)

    # asyncpg uses the plain postgresql:// scheme
    dsn = clean_url.replace("postgresql+asyncpg://", "postgresql://")
    ssl_ctx = connect_args.get("ssl")

    # ------------------------------------------------------------------
    # Step 1 — check current revision via asyncpg
    # ------------------------------------------------------------------
    current_revision = None
    try:
        conn = await asyncpg.connect(dsn=dsn, ssl=ssl_ctx)
        try:
            exists = await conn.fetchval(
                "SELECT EXISTS ("
                "  SELECT 1 FROM information_schema.tables"
                "  WHERE table_name = 'alembic_version'"
                ")"
            )
            if exists:
                current_revision = await conn.fetchval(
                    "SELECT version_num FROM alembic_version LIMIT 1"
                )
        finally:
            await conn.close()
    except Exception as exc:
        logger.warning(
            f"Could not check alembic_version: {exc} — will attempt migration anyway."
        )

    # ------------------------------------------------------------------
    # Step 2 — resolve head revision from the script directory
    # ------------------------------------------------------------------
    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", "src/alembic")
    alembic_cfg.set_main_option("sqlalchemy.url", clean_url)

    script = ScriptDirectory.from_config(alembic_cfg)
    head_revision = script.get_current_head()

    if current_revision is None:
        logger.info("Fresh database — running full migration from base...")
    elif current_revision == head_revision:
        logger.info(
            f"Database already at head ({head_revision}) — no migrations needed."
        )
        return
    else:
        logger.info(
            f"Database at {current_revision}, head is {head_revision} — upgrading..."
        )

    # ------------------------------------------------------------------
    # Step 3 — run upgrade in-process via EnvironmentContext
    #
    # EnvironmentContext.__enter__ installs the 'op' proxy (and the
    # 'context' proxy) that migration scripts import at module level.
    # We call env_ctx.configure(connection=sync_conn) to bind the live
    # connection, then env_ctx.run_migrations() to execute the steps.
    # env.py is never loaded — we replicate exactly what it does.
    # ------------------------------------------------------------------
    def _do_upgrade(sync_conn):
        with EnvironmentContext(
            alembic_cfg,
            script,
            fn=lambda rev, context: script._upgrade_revs("head", rev),
            as_sql=False,
            starting_rev=None,
            destination_rev="head",
        ) as env_ctx:
            env_ctx.configure(
                connection=sync_conn,
                target_metadata=None,
                compare_type=True,
                transaction_per_migration=True,
            )
            env_ctx.run_migrations()

    async_engine = create_async_engine(
        clean_url,
        connect_args=connect_args,
        poolclass=sa_pool.NullPool,
    )
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(_do_upgrade)
    finally:
        await async_engine.dispose()

    logger.info("Alembic upgrade head completed successfully.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    _banner = "=" * 60
    logger.info(_banner)
    logger.info("  DINO SYSTEM — STARTING UP")
    logger.info(_banner)
    logger.info(f"  App Version  : {settings.APP_VERSION}")
    logger.info(f"  Build ID     : {settings.BUILD_ID}")
    logger.info(f"  Deployed At  : {settings.DEPLOYED_AT}")
    logger.info(f"  Environment  : {settings.ENVIRONMENT}")
    logger.info(f"  Port         : {settings.PORT}")
    logger.info(f"  Database     : PostgreSQL (asyncpg)")
    logger.info(_banner)

    try:
        settings._validate_production_config()
        logger.info("[OK] Configuration validated")
    except RuntimeError as e:
        logger.critical(f"[FAIL] Invalid production configuration:\n{e}")
        raise

    try:
        await _run_migrations()
        logger.info("[OK] Database migrations applied")
    except Exception as e:
        logger.critical(f"[FAIL] Migration failed: {e}", exc_info=True)
        raise

    try:
        await initialize_db()
        logger.info("[OK] PostgreSQL connection pool initialized")
    except Exception as e:
        logger.critical(f"[FAIL] PostgreSQL connection failed: {e}")
        raise

    logger.info(_banner)
    logger.info(f"  DINO SYSTEM — READY  (build: {settings.BUILD_ID})")
    logger.info(_banner)

    yield

    logger.info(_banner)
    logger.info("  DINO SYSTEM — SHUTTING DOWN")
    logger.info(_banner)
    try:
        await close_db()
        logger.info("[OK] PostgreSQL connection pool closed")
    except Exception as e:
        logger.error(f"[FAIL] Error closing database connection: {e}")


_docs_url = None if settings.ENVIRONMENT == "production" else "/docs"
_redoc_url = None if settings.ENVIRONMENT == "production" else "/redoc"

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Dino System Service — system-level administration and management",
    lifespan=lifespan,
    docs_url=_docs_url,
    redoc_url=_redoc_url,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "error": str(exc) if settings.DEBUG else "An error occurred",
        },
    )


@app.get("/")
async def root():
    """Root endpoint."""
    response: dict = {
        "success": True,
        "message": f"Welcome to {settings.APP_NAME} System Service",
        "version": settings.APP_VERSION,
    }
    if settings.ENVIRONMENT != "production":
        response["docs"] = "/docs"
        response["redoc"] = "/redoc"
    return response


@app.get("/health")
async def health_check():
    """Health check endpoint — probes live PostgreSQL connectivity."""
    if async_session_factory is None:
        return {"status": "starting"}
    try:
        async with async_session_factory() as db:
            await db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Health check failed — PostgreSQL unreachable: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "status": "unhealthy",
                "version": settings.APP_VERSION,
                "detail": "PostgreSQL connectivity check failed",
            },
        )
    return {
        "success": True,
        "status": "healthy",
        "version": settings.APP_VERSION,
    }


_PREFIX = "/api/v1/system"

app.include_router(SystemAuth.router, prefix=_PREFIX, tags=["System"])
app.include_router(SystemDashboard.router, prefix=_PREFIX, tags=["System"])
app.include_router(SystemRoles.router, prefix=_PREFIX, tags=["System"])
app.include_router(SystemPermissions.router, prefix=_PREFIX, tags=["System"])
app.include_router(SystemUsers.router, prefix=_PREFIX, tags=["System"])
app.include_router(SystemWorkspaces.router, prefix=_PREFIX, tags=["System"])
app.include_router(SystemBilling.router, prefix=_PREFIX, tags=["System"])
app.include_router(SystemPersonas.router, prefix=_PREFIX, tags=["System"])
app.include_router(SystemWorkspaceRequests.router, prefix=_PREFIX, tags=["System"])

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.Main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
'@

# ==============================================================================
# FILE: system/src/models/Workspace.py  [M]
# ==============================================================================
Write-EmbeddedFile "system/src/models/Workspace.py" @'
"""
Workspace ORM model and workspace_personas association table.

owner_id      – references users.id (SET NULL on delete)
requested_by  – system user who submitted the verification request (SET NULL on delete)
is_verified   – set to True when an admin approves the workspace request
No billing columns — billing is in workspace_billing table.
"""

from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    ForeignKey,
    Index,
    String,
    Table,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, BigIntPrimaryKeyMixin, EntityMixin


# ---------------------------------------------------------------------------
# Association table
# ---------------------------------------------------------------------------

workspace_personas = Table(
    "workspace_personas",
    Base.metadata,
    Column(
        "workspace_id",
        BigInteger,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "persona_id",
        BigInteger,
        ForeignKey("personas.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Index("ix_workspace_personas_persona_id", "persona_id"),
)


# ---------------------------------------------------------------------------
# Workspace entity
# ---------------------------------------------------------------------------

class Workspace(BigIntPrimaryKeyMixin, EntityMixin, Base):
    """A tenant-level container that groups Personas and holds billing info."""

    __tablename__ = "workspaces"

    __table_args__ = (
        Index("ix_workspaces_requested_by", "requested_by"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    owner_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    requested_by: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="System user who submitted the workspace verification request",
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        comment="Set to true when an admin approves the workspace request",
    )

    # Relationships
    owner: Mapped[Optional["User"]] = relationship(  # noqa: F821
        "User",
        foreign_keys=[owner_id],
        lazy="noload",
    )
    requested_by_user: Mapped[Optional["User"]] = relationship(  # noqa: F821
        "User",
        foreign_keys=[requested_by],
        lazy="noload",
    )
    billing: Mapped[Optional["WorkspaceBilling"]] = relationship(  # noqa: F821
        "WorkspaceBilling",
        back_populates="workspace",
        uselist=False,
        lazy="noload",
    )
    personas: Mapped[list["Persona"]] = relationship(  # noqa: F821
        "Persona",
        secondary="workspace_personas",
        primaryjoin="Workspace.id == workspace_personas.c.workspace_id",
        secondaryjoin="Persona.id == workspace_personas.c.persona_id",
        lazy="noload",
    )
    users: Mapped[list["User"]] = relationship(  # noqa: F821
        "User",
        foreign_keys="User.workspace_id",
        back_populates="workspace",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Workspace id={self.id} name={self.name!r} verified={self.is_verified}>"
'@

# ==============================================================================
# FILE: system/src/models/__init__.py  [M]
# ==============================================================================
Write-EmbeddedFile "system/src/models/__init__.py" @'
"""
system ORM models package.

Importing this package registers all mapped classes against Base.metadata,
which is required for Alembic autogenerate to discover every table.

Usage in alembic/env.py
-----------------------
    from src.models import Base          # noqa: F401  (triggers all imports)
    target_metadata = Base.metadata
"""

# Base must be imported first so metadata is initialised before any model
# references it.
from src.models.Base import (  # noqa: F401
    Base,
    BigIntPrimaryKeyMixin,
    EntityMixin,
)

# Association tables are defined inside their primary model modules; importing
# those modules is sufficient to register the Table objects with Base.metadata.
from src.models.Permission import Permission  # noqa: F401
from src.models.Role import Role, role_permissions  # noqa: F401
from src.models.Workspace import Workspace, workspace_personas  # noqa: F401
from src.models.WorkspaceBilling import WorkspaceBilling  # noqa: F401
from src.models.BillingTransaction import BillingTransaction  # noqa: F401
from src.models.Persona import Persona  # noqa: F401
from src.models.User import User  # noqa: F401
from src.models.WorkspaceRequest import WorkspaceRequest  # noqa: F401

__all__ = [
    # Base
    "Base",
    "BigIntPrimaryKeyMixin",
    "EntityMixin",
    # Entity models
    "Permission",
    "Role",
    "User",
    "Workspace",
    "WorkspaceBilling",
    "BillingTransaction",
    "Persona",
    "WorkspaceRequest",
    # Association tables
    "role_permissions",
    "workspace_personas",
]
'@

# ==============================================================================
# FILE: system/src/repositories/__init__.py  [M]
# ==============================================================================
Write-EmbeddedFile "system/src/repositories/__init__.py" @'
"""
system repositories package.
"""

from src.repositories.UserRepository import UserRepository  # noqa: F401
from src.repositories.RoleRepository import RoleRepository  # noqa: F401
from src.repositories.PermissionRepository import PermissionRepository  # noqa: F401
from src.repositories.WorkspaceRepository import WorkspaceRepository  # noqa: F401
from src.repositories.PersonaRepository import PersonaRepository  # noqa: F401
from src.repositories.WorkspaceRequestRepository import WorkspaceRequestRepository  # noqa: F401

__all__ = [
    "UserRepository",
    "RoleRepository",
    "PermissionRepository",
    "WorkspaceRepository",
    "PersonaRepository",
    "WorkspaceRequestRepository",
]
'@

# ==============================================================================
# FILE: system/src/schemas/Workspace.py  [M]
# ==============================================================================
Write-EmbeddedFile "system/src/schemas/Workspace.py" @'
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class WorkspaceBase(BaseModel):
    """Base workspace schema"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None


class WorkspaceCreate(WorkspaceBase):
    """Create workspace schema"""
    owner_id: Optional[int] = None
    persona_ids: Optional[List[int]] = None


class WorkspaceUpdate(BaseModel):
    """Update workspace schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    owner_id: Optional[int] = None
    is_active: Optional[bool] = None
    persona_ids: Optional[List[int]] = None


class WorkspaceResponse(BaseModel):
    """Workspace response schema"""
    id: int
    name: str
    description: Optional[str] = None
    owner_id: Optional[int] = None
    requested_by: Optional[int] = None
    is_verified: bool = False
    is_active: bool
    created_at: datetime
    updated_at: datetime
    persona_ids: Optional[List[int]] = None

    class Config:
        from_attributes = True


class WorkspaceBillingUpdate(BaseModel):
    """Update workspace billing schema"""
    plan: Optional[str] = None
    plan_status: Optional[str] = None
    billing_cycle: Optional[str] = None
    billing_email: Optional[str] = None
    billing_name: Optional[str] = None
    billing_address: Optional[str] = None
    billing_city: Optional[str] = None
    billing_state: Optional[str] = None
    billing_country: Optional[str] = None
    billing_postal_code: Optional[str] = None
    billing_phone: Optional[str] = None
    next_billing_date: Optional[datetime] = None


class WorkspaceBillingResponse(BaseModel):
    """Workspace billing response schema"""
    id: int
    workspace_id: int
    plan: str
    plan_status: str
    billing_cycle: Optional[str] = None
    billing_email: Optional[str] = None
    billing_name: Optional[str] = None
    billing_address: Optional[str] = None
    billing_city: Optional[str] = None
    billing_state: Optional[str] = None
    billing_country: Optional[str] = None
    billing_postal_code: Optional[str] = None
    billing_phone: Optional[str] = None
    next_billing_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
'@

# ==============================================================================
# FILE: system/src/system/routes/__init__.py  [M]
# ==============================================================================
Write-EmbeddedFile "system/src/system/routes/__init__.py" @'
from . import Auth, Dashboard, Users, Roles, Permissions, Workspaces, Personas, Billing, WorkspaceRequests

__all__ = ["Auth", "Dashboard", "Users", "Roles", "Permissions", "Workspaces", "Personas", "Billing", "WorkspaceRequests"]
'@

# ==============================================================================
# FILE: system/src/system/services/__init__.py  [M]
# ==============================================================================
Write-EmbeddedFile "system/src/system/services/__init__.py" @'
from .Dashboard import SystemDashboardService
from .WorkspaceRequest import WorkspaceRequestService

__all__ = ['SystemDashboardService', 'WorkspaceRequestService']
'@

# ==============================================================================
# FILE: system/Run-AddWorkspaceRequest.ps1  [??]
# ==============================================================================
Write-EmbeddedFile "system/Run-AddWorkspaceRequest.ps1" @'
#Requires -Version 5.1
<#
.SYNOPSIS
    Self-extracting launcher for the Add-WorkspaceRequest feature script.

.DESCRIPTION
    Reads Add-WorkspaceRequest.ps1 (stored as pure ASCII), decodes it from
    base64, writes it to a temp file, executes it, then cleans up.

.NOTES
    Run from the repo root:
        .\system\Run-AddWorkspaceRequest.ps1

    Preview only (no writes):
        .\system\Run-AddWorkspaceRequest.ps1 -WhatIf
#>

[CmdletBinding(SupportsShouldProcess)]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Locate the sibling script and execute it directly
# ---------------------------------------------------------------------------

$_scriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$_targetScript = Join-Path $_scriptDir "Add-WorkspaceRequest.ps1"

if (-not (Test-Path $_targetScript)) {
    Write-Error "Cannot find Add-WorkspaceRequest.ps1 next to this launcher at: $_targetScript"
    exit 1
}

Write-Host ""
Write-Host "Launcher: forwarding to Add-WorkspaceRequest.ps1" -ForegroundColor DarkGray
Write-Host ""

if ($WhatIfPreference) {
    & $_targetScript -WhatIf
} else {
    & $_targetScript
}
'@

# ==============================================================================
# FILE: system/src/alembic/versions/002_workspace_requests.py  [??]
# ==============================================================================
Write-EmbeddedFile "system/src/alembic/versions/002_workspace_requests.py" @'
"""Add workspace_requests table and update workspaces

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-04-23 00:00:00.000000

Changes:
  - workspaces: drop referred_by FK and column (was created in 001)
  - workspaces: add requested_by (BigInteger, FK -> users.id SET NULL)
  - workspaces: add is_verified (Boolean, NOT NULL, server_default false)
  - Create workspace_requests table
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NOW = sa.text("now()")


def _column_exists(table: str, column: str) -> bool:
    """Return True if *column* exists in *table* in the current DB."""
    bind = op.get_bind()
    insp = inspect(bind)
    return any(c["name"] == column for c in insp.get_columns(table))


def _fk_exists(table: str, fk_name: str) -> bool:
    """Return True if a FK constraint with *fk_name* exists on *table*."""
    bind = op.get_bind()
    insp = inspect(bind)
    return any(fk["name"] == fk_name for fk in insp.get_foreign_keys(table))


def _index_exists(table: str, index_name: str) -> bool:
    """Return True if *index_name* exists on *table*."""
    bind = op.get_bind()
    insp = inspect(bind)
    return any(ix["name"] == index_name for ix in insp.get_indexes(table))


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. workspaces — drop referred_by FK (created in 001_initial_schema)
    # ------------------------------------------------------------------
    if _fk_exists("workspaces", "fk_workspaces_referred_by"):
        op.drop_constraint("fk_workspaces_referred_by", "workspaces", type_="foreignkey")

    # ------------------------------------------------------------------
    # 2. workspaces — drop referred_by column
    # ------------------------------------------------------------------
    if _column_exists("workspaces", "referred_by"):
        op.drop_column("workspaces", "referred_by")

    # ------------------------------------------------------------------
    # 3. workspaces — add requested_by column
    # ------------------------------------------------------------------
    if not _column_exists("workspaces", "requested_by"):
        op.add_column(
            "workspaces",
            sa.Column(
                "requested_by",
                sa.BigInteger(),
                nullable=True,
                comment="System user who submitted the workspace verification request",
            ),
        )

    # ------------------------------------------------------------------
    # 4. workspaces — FK for requested_by -> users.id
    # ------------------------------------------------------------------
    if not _fk_exists("workspaces", "fk_workspaces_requested_by"):
        op.create_foreign_key(
            "fk_workspaces_requested_by", "workspaces", "users",
            ["requested_by"], ["id"], ondelete="SET NULL",
        )

    # ------------------------------------------------------------------
    # 5. workspaces — index on requested_by
    # ------------------------------------------------------------------
    if not _index_exists("workspaces", "ix_workspaces_requested_by"):
        op.create_index("ix_workspaces_requested_by", "workspaces", ["requested_by"])

    # ------------------------------------------------------------------
    # 6. workspaces — add is_verified column
    # ------------------------------------------------------------------
    if not _column_exists("workspaces", "is_verified"):
        op.add_column(
            "workspaces",
            sa.Column(
                "is_verified",
                sa.Boolean(),
                nullable=False,
                server_default="false",
                comment="Set to true when an admin approves the workspace request",
            ),
        )

    # ------------------------------------------------------------------
    # 7. Create workspace_requests table
    # ------------------------------------------------------------------
    op.create_table(
        "workspace_requests",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Sequence("workspace_requests_id_seq"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
            comment="pending / approved / rejected",
        ),
        sa.Column("reviewed_by", sa.BigInteger(), nullable=True),
        sa.Column("reviewed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_workspace_requests_user_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"],
            name="fk_workspace_requests_workspace_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"], ["users.id"],
            name="fk_workspace_requests_reviewed_by",
            ondelete="SET NULL",
        ),
    )

    # ------------------------------------------------------------------
    # 8. workspace_requests — indexes
    # ------------------------------------------------------------------
    op.create_index("ix_workspace_requests_user_id", "workspace_requests", ["user_id"])
    op.create_index("ix_workspace_requests_workspace_id", "workspace_requests", ["workspace_id"])
    op.create_index("ix_workspace_requests_status", "workspace_requests", ["status"])
    op.create_index("ix_workspace_requests_is_active", "workspace_requests", ["is_active"])


def downgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Drop workspace_requests indexes then table
    # ------------------------------------------------------------------
    op.drop_index("ix_workspace_requests_is_active", table_name="workspace_requests")
    op.drop_index("ix_workspace_requests_status", table_name="workspace_requests")
    op.drop_index("ix_workspace_requests_workspace_id", table_name="workspace_requests")
    op.drop_index("ix_workspace_requests_user_id", table_name="workspace_requests")
    op.drop_table("workspace_requests")

    # ------------------------------------------------------------------
    # 2. workspaces — drop is_verified column
    # ------------------------------------------------------------------
    op.drop_column("workspaces", "is_verified")

    # ------------------------------------------------------------------
    # 3. workspaces — drop requested_by index, FK, and column
    # ------------------------------------------------------------------
    op.drop_index("ix_workspaces_requested_by", table_name="workspaces")
    op.drop_constraint("fk_workspaces_requested_by", "workspaces", type_="foreignkey")
    op.drop_column("workspaces", "requested_by")

    # ------------------------------------------------------------------
    # 4. workspaces — restore referred_by column and FK (as in 001)
    # ------------------------------------------------------------------
    op.add_column(
        "workspaces",
        sa.Column("referred_by", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        "fk_workspaces_referred_by", "workspaces", "users",
        ["referred_by"], ["id"], ondelete="SET NULL",
    )
'@

# ==============================================================================
# FILE: system/src/models/WorkspaceRequest.py  [??]
# ==============================================================================
Write-EmbeddedFile "system/src/models/WorkspaceRequest.py" @'
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, BigIntPrimaryKeyMixin, EntityMixin


class WorkspaceRequest(BigIntPrimaryKeyMixin, EntityMixin, Base):
    """Workspace access request submitted by a user for a given workspace."""

    __tablename__ = "workspace_requests"

    __table_args__ = (
        Index("ix_workspace_requests_user_id", "user_id"),
        Index("ix_workspace_requests_workspace_id", "workspace_id"),
        Index("ix_workspace_requests_status", "status"),
    )

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    workspace_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
        comment="pending/approved/rejected",
    )
    reviewed_by: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped[Optional["User"]] = relationship(  # noqa: F821
        "User",
        foreign_keys=[user_id],
        lazy="noload",
    )
    workspace: Mapped["Workspace"] = relationship(  # noqa: F821
        "Workspace",
        lazy="noload",
    )
    reviewer: Mapped[Optional["User"]] = relationship(  # noqa: F821
        "User",
        foreign_keys=[reviewed_by],
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<WorkspaceRequest id={self.id} email={self.email!r} status={self.status!r}>"
'@

# ==============================================================================
# FILE: system/src/repositories/WorkspaceRequestRepository.py  [??]
# ==============================================================================
Write-EmbeddedFile "system/src/repositories/WorkspaceRequestRepository.py" @'
"""
WorkspaceRequestRepository — async SQLAlchemy 2.x repository for the WorkspaceRequest model.
"""

from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.WorkspaceRequest import WorkspaceRequest


class WorkspaceRequestRepository(BaseRepository):
    """Repository for WorkspaceRequest entities."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(WorkspaceRequest, db)

    async def get_paginated_requests(
        self,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict], int, int]:
        """
        Return (items, total_count, total_pages) for active workspace requests.

        Optionally filters by status. Always restricts to is_active=True.
        Uses COUNT + LIMIT/OFFSET pattern matching BaseRepository.get_paginated.
        """
        conditions = [WorkspaceRequest.is_active == True]  # noqa: E712

        if status is not None:
            conditions.append(WorkspaceRequest.status == status)

        # --- COUNT query ---
        count_stmt = (
            select(func.count())
            .select_from(WorkspaceRequest)
            .where(and_(*conditions))
        )
        total_count: int = (await self.db.execute(count_stmt)).scalar_one()

        total_pages = max(1, (total_count + page_size - 1) // page_size)
        offset = (page - 1) * page_size

        # --- Data query ---
        data_stmt = (
            select(WorkspaceRequest)
            .where(and_(*conditions))
            .order_by(WorkspaceRequest.created_at.desc())
            .limit(page_size)
            .offset(offset)
        )
        rows = (await self.db.execute(data_stmt)).scalars().all()

        return [row_to_dict(r) for r in rows], total_count, total_pages

    async def get_by_workspace_and_status(
        self,
        workspace_id: int,
        status: str,
    ) -> Optional[Dict]:
        """
        Return the first active WorkspaceRequest matching workspace_id and status.

        Returns None if no matching record exists.
        """
        stmt = (
            select(WorkspaceRequest)
            .where(
                and_(
                    WorkspaceRequest.workspace_id == workspace_id,
                    WorkspaceRequest.status == status,
                    WorkspaceRequest.is_active == True,  # noqa: E712
                )
            )
            .limit(1)
        )
        row = (await self.db.execute(stmt)).scalars().first()
        return row_to_dict(row) if row is not None else None

    async def has_pending_request(self, workspace_id: int) -> bool:
        """
        Return True if any active WorkspaceRequest with status='pending'
        exists for the given workspace_id.
        """
        stmt = (
            select(literal(1))
            .select_from(WorkspaceRequest)
            .where(
                and_(
                    WorkspaceRequest.workspace_id == workspace_id,
                    WorkspaceRequest.status == "pending",
                    WorkspaceRequest.is_active == True,  # noqa: E712
                )
            )
            .limit(1)
        )
        result = (await self.db.execute(stmt)).scalar()
        return result is not None
'@

# ==============================================================================
# FILE: system/src/schemas/WorkspaceRequest.py  [??]
# ==============================================================================
Write-EmbeddedFile "system/src/schemas/WorkspaceRequest.py" @'
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class WorkspaceRequestCreate(BaseModel):
    """Create workspace request schema"""
    email: EmailStr
    workspace_id: int


class WorkspaceRequestReject(BaseModel):
    """Reject workspace request schema"""
    rejection_reason: Optional[str] = None


class WorkspaceRequestResponse(BaseModel):
    """Workspace request response schema"""
    id: int
    email: str
    user_id: Optional[int] = None
    workspace_id: int
    status: str
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
'@

# ==============================================================================
# FILE: system/src/system/routes/WorkspaceRequests.py  [??]
# ==============================================================================
Write-EmbeddedFile "system/src/system/routes/WorkspaceRequests.py" @'
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.core.Dependencies import get_current_system_user
from src.schemas.WorkspaceRequest import WorkspaceRequestCreate, WorkspaceRequestReject
from src.system.middleware.RoleCheck import SystemPermissionCheck
from src.system.services.WorkspaceRequest import WorkspaceRequestService

router = APIRouter(prefix="/workspace-requests", tags=["System Workspace Requests"])


@router.post(
    "",
    response_model=BaseResponse,
)
async def submit_workspace_request(
    body: WorkspaceRequestCreate,
    current_user: dict = Depends(get_current_system_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a new workspace request."""
    service = WorkspaceRequestService(db)
    result = await service.submit_request(body.model_dump())
    return {
        "success": True,
        "message": "Workspace request submitted successfully",
        "data": {"id": result.get("id")},
    }


@router.get(
    "",
    dependencies=[Depends(SystemPermissionCheck.require("workspaces:read"))],
)
async def get_workspace_requests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated workspace requests."""
    service = WorkspaceRequestService(db)
    items, total, total_pages = await service.get_paginated_requests(
        status=status,
        page=page,
        page_size=page_size,
    )
    return {
        "success": True,
        "message": "Workspace requests retrieved successfully",
        "data": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        },
    }


@router.get(
    "/{request_id}",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("workspaces:read"))],
)
async def get_workspace_request(request_id: int, db: AsyncSession = Depends(get_db)):
    """Get workspace request details."""
    service = WorkspaceRequestService(db)
    request = await service.get_request(request_id)
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace request not found")
    return {"success": True, "message": "Workspace request retrieved successfully", "data": request}


@router.post(
    "/{request_id}/approve",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("workspaces:update"))],
)
async def approve_workspace_request(
    request_id: int,
    current_user: dict = Depends(get_current_system_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve a workspace request."""
    service = WorkspaceRequestService(db)
    result = await service.approve_request(request_id, current_user["id"])
    return {
        "success": True,
        "message": "Request approved successfully",
        "data": result,
    }


@router.post(
    "/{request_id}/reject",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("workspaces:update"))],
)
async def reject_workspace_request(
    request_id: int,
    body: WorkspaceRequestReject,
    current_user: dict = Depends(get_current_system_user),
    db: AsyncSession = Depends(get_db),
):
    """Reject a workspace request."""
    service = WorkspaceRequestService(db)
    result = await service.reject_request(request_id, current_user["id"], body.rejection_reason)
    return {
        "success": True,
        "message": "Request rejected successfully",
        "data": result,
    }


@router.delete(
    "/{request_id}",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("workspaces:delete"))],
)
async def delete_workspace_request(request_id: int, db: AsyncSession = Depends(get_db)):
    """Soft delete a workspace request."""
    service = WorkspaceRequestService(db)
    success = await service.soft_delete(request_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace request not found")
    return {"success": True, "message": "Request deleted successfully"}
'@

# ==============================================================================
# FILE: system/src/system/services/WorkspaceRequest.py  [??]
# ==============================================================================
Write-EmbeddedFile "system/src/system/services/WorkspaceRequest.py" @'
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseService import BaseService
from src.repositories.UserRepository import UserRepository
from src.repositories.WorkspaceRepository import WorkspaceRepository
from src.repositories.WorkspaceRequestRepository import WorkspaceRequestRepository


class WorkspaceRequestService(BaseService):
    """Business logic for workspace join requests."""

    def __init__(self, db: AsyncSession) -> None:
        self.workspace_request_repo = WorkspaceRequestRepository(db)
        self.user_repo = UserRepository(db)
        self.workspace_repo = WorkspaceRepository(db)
        super().__init__(self.workspace_request_repo)

    async def submit_request(self, data: dict) -> dict:
        """Submit a new workspace join request."""
        email: str = data["email"]
        workspace_id: int = data["workspace_id"]

        user: Optional[Dict] = await self.user_repo.get_by_field("email", email)
        if not user or user.get("user_type") != 0 or not user.get("is_active"):
            raise HTTPException(
                status_code=422,
                detail="Email does not belong to an active system user",
            )

        has_pending: bool = await self.workspace_request_repo.has_pending_request(workspace_id)
        if has_pending:
            raise HTTPException(
                status_code=409,
                detail="A pending request already exists for this workspace",
            )

        record = await self.create(
            {
                "email": email,
                "user_id": user["id"],
                "workspace_id": workspace_id,
                "status": "pending",
            }
        )
        return record

    async def get_paginated_requests(
        self,
        status: Optional[str],
        page: int,
        page_size: int,
    ) -> Tuple[List, int, int]:
        """Return paginated workspace requests filtered by status."""
        return await self.workspace_request_repo.get_paginated_requests(status, page, page_size)

    async def get_request(self, request_id: int) -> Optional[dict]:
        """Fetch a single workspace request by id."""
        return await self.get_by_id(request_id)

    async def approve_request(self, request_id: int, reviewed_by_user_id: int) -> dict:
        """Approve a pending workspace request and verify the workspace."""
        request: Optional[dict] = await self.get_by_id(request_id)
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")

        if request.get("status") != "pending":
            raise HTTPException(status_code=409, detail="Request is not pending")

        await self.update(
            request_id,
            {
                "status": "approved",
                "reviewed_by": reviewed_by_user_id,
                "reviewed_at": datetime.now(timezone.utc),
            },
        )

        await self.workspace_repo.update(
            request["workspace_id"],
            {
                "is_verified": True,
                "requested_by": request["user_id"],
            },
        )

        return await self.get_by_id(request_id)

    async def reject_request(
        self,
        request_id: int,
        reviewed_by_user_id: int,
        rejection_reason: Optional[str],
    ) -> dict:
        """Reject a pending workspace request."""
        request: Optional[dict] = await self.get_by_id(request_id)
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")

        if request.get("status") != "pending":
            raise HTTPException(status_code=409, detail="Request is not pending")

        await self.update(
            request_id,
            {
                "status": "rejected",
                "reviewed_by": reviewed_by_user_id,
                "reviewed_at": datetime.now(timezone.utc),
                "rejection_reason": rejection_reason,
            },
        )

        return await self.get_by_id(request_id)
'@

Write-Host ""
Write-Host "All files restored successfully." -ForegroundColor Green
Write-Host ""
