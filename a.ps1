#Requires -Version 5.1
<#
.SYNOPSIS
    Restores all backend changes made in this session to disk.

.DESCRIPTION
    Self-extracting script. Run from the repo root (backend/) to write every
    modified file to its correct path. Safe to re-run — existing files are
    overwritten with the correct content.

.NOTES
    Run from repo root:
        .\Dump-GitChanges.ps1

    Changes included
    ----------------
    app
      - models/Category.py          drop image_url
      - schemas/Category.py         drop image_url
      - models/Table.py             drop display_order, add persona_id
      - schemas/Table.py            drop display_order, add persona_id
      - models/Workspace.py         drop stale requested_by column
      - repositories/AreaRepository.py   workspace_personas upsert, flat list + index
      - repositories/TableRepository.py  direct persona_id scoping, no Area join
      - services/Area.py            paginated list, persona validation
      - services/Table.py           persona_id guard
      - routes/Areas.py             paginated GET, persona_id in POST body
      - routes/Tables.py            persona_id in POST body, drop display_order

    system (migrations)
      - 004_drop_image_url_from_categories.py
      - 005_workspace_requests_refactor.py
      - 006_drop_display_order_from_tables.py
      - 007_simplify_workspace_requests_referral.py

    system (app)
      - models/Workspace.py         drop requested_by
      - models/WorkspaceRequest.py  referred_by (system user who referred)
      - schemas/Workspace.py        drop requested_by from response
      - schemas/WorkspaceRequest.py referred_by + referral_email
      - repositories/WorkspaceRequestRepository.py  referred_by stats
      - routes/WorkspaceRequests.py clean submit route
      - services/WorkspaceRequest.py referral_email -> referred_by resolution
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$_scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$_repoRoot  = $_scriptDir

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
Write-Host "Restoring backend changes..." -ForegroundColor Cyan
Write-Host ""

# ==============================================================================
# FILE: app/src/models/Category.py
# ==============================================================================
Write-EmbeddedFile "app/src/models/Category.py" @'
"""
Category ORM model. No sort_order, no parent_id.
"""

from typing import Optional

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, BigIntPrimaryKeyMixin, EntityMixin


class Category(BigIntPrimaryKeyMixin, EntityMixin, Base):
    """A menu category."""

    __tablename__ = "categories"

    __table_args__ = (
        Index("ix_categories_workspace_id", "workspace_id"),
        Index("ix_categories_persona_id", "persona_id"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_available: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    workspace_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    persona_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("personas.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    items: Mapped[list["Item"]] = relationship(  # noqa: F821
        "Item",
        back_populates="category",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Category id={self.id} name={self.name!r}>"

'@

# ==============================================================================
# FILE: app/src/schemas/Category.py
# ==============================================================================
Write-EmbeddedFile "app/src/schemas/Category.py" @'
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    is_available: bool = True


class CategoryCreate(CategoryBase):
    persona_id: Optional[int] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    is_available: Optional[bool] = None
    persona_id: Optional[int] = None


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    workspace_id: int
    persona_id: Optional[int] = None
    is_available: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

'@

# ==============================================================================
# FILE: app/src/models/Table.py
# ==============================================================================
Write-EmbeddedFile "app/src/models/Table.py" @'
"""
Table ORM model. No qr_code_url, no qr_menu_url.
Unique: (area_id, table_number).
"""

from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, BigIntPrimaryKeyMixin, EntityMixin


class Table(BigIntPrimaryKeyMixin, EntityMixin, Base):
    """A physical table within an area."""

    __tablename__ = "tables"

    __table_args__ = (
        UniqueConstraint("area_id", "table_number", name="uq_tables_area_table_number"),
        Index("ix_tables_workspace_id", "workspace_id"),
        Index("ix_tables_area_id", "area_id"),
        Index("ix_tables_persona_id", "persona_id"),
    )

    table_number: Mapped[str] = mapped_column(String(50), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("4"))
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("''available''"),
        comment="available | occupied | reserved | out_of_service",
    )
    workspace_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    area_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("areas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    persona_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("personas.id", ondelete="SET NULL"),
        nullable=True,
        comment="Denormalised from areas.persona_id for direct query scoping",
    )

    # Relationships
    area: Mapped["Area"] = relationship(  # noqa: F821
        "Area",
        back_populates="tables",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Table id={self.id} number={self.table_number!r} status={self.status!r}>"

'@

# ==============================================================================
# FILE: app/src/schemas/Table.py
# ==============================================================================
Write-EmbeddedFile "app/src/schemas/Table.py" @'
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

TableStatus = Literal[''available'', ''occupied'', ''reserved'', ''out_of_service'']


class TableBase(BaseModel):
    table_number: str = Field(..., min_length=1, max_length=50)
    area_id: int
    capacity: int = Field(default=4, ge=1)
    status: TableStatus = ''available''


class TableCreate(TableBase):
    persona_id: Optional[int] = None


class TableUpdate(BaseModel):
    table_number: Optional[str] = Field(None, min_length=1, max_length=50)
    capacity: Optional[int] = Field(None, ge=1)
    status: Optional[TableStatus] = None


class TableResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    table_number: str
    area_id: int
    workspace_id: int
    capacity: int
    status: str
    persona_id: Optional[int] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

'@

# ==============================================================================
# FILE: app/src/models/Workspace.py
# ==============================================================================
Write-EmbeddedFile "app/src/models/Workspace.py" @'
"""
Workspace ORM model and workspace_personas association table (shared).
"""

from typing import Optional

from sqlalchemy import BigInteger, Boolean, Column, ForeignKey, String, Table, Text, text
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
)


# ---------------------------------------------------------------------------
# Workspace entity
# ---------------------------------------------------------------------------

class Workspace(BigIntPrimaryKeyMixin, EntityMixin, Base):
    """A tenant-level container."""

    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    owner_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )

    # Relationships
    owner: Mapped[Optional["User"]] = relationship(  # noqa: F821
        "User",
        foreign_keys="[Workspace.owner_id]",
        lazy="noload",
    )
    billing: Mapped[Optional["WorkspaceBilling"]] = relationship(  # noqa: F821
        "WorkspaceBilling",
        back_populates="workspace",
        uselist=False,
        lazy="noload",
    )
    billing_details: Mapped[Optional["BillingDetail"]] = relationship(  # noqa: F821
        "BillingDetail",
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
        foreign_keys="[User.workspace_id]",
        back_populates="workspace",
        lazy="noload",
    )
    customers: Mapped[list["Customer"]] = relationship(  # noqa: F821
        "Customer",
        back_populates="workspace",
        lazy="noload",
    )
    reviews: Mapped[list["Review"]] = relationship(  # noqa: F821
        "Review",
        back_populates="workspace",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Workspace id={self.id} name={self.name!r}>"

'@

# ==============================================================================
# FILE: app/src/repositories/AreaRepository.py
# ==============================================================================
Write-EmbeddedFile "app/src/repositories/AreaRepository.py" @'
"""
AreaRepository — async SQLAlchemy 2.x repository for the Area model.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.Area import Area
from src.models.Workspace import workspace_personas


class AreaRepository(BaseRepository):
    """Repository for Area entities."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Area, db)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _persona_belongs_to_workspace(
        self, workspace_id: int, persona_id: int
    ) -> bool:
        """Return True if the persona is linked to the workspace."""
        stmt = (
            select(func.count())
            .select_from(workspace_personas)
            .where(
                and_(
                    workspace_personas.c.workspace_id == workspace_id,
                    workspace_personas.c.persona_id == persona_id,
                )
            )
        )
        count = (await self.db.execute(stmt)).scalar_one()
        return count > 0

    async def _ensure_workspace_persona(
        self, workspace_id: int, persona_id: int
    ) -> None:
        """Insert into workspace_personas if the link does not already exist."""
        exists = await self._persona_belongs_to_workspace(workspace_id, persona_id)
        if not exists:
            stmt = insert(workspace_personas).values(
                workspace_id=workspace_id,
                persona_id=persona_id,
            )
            await self.db.execute(stmt)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def create_area(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate persona → workspace membership, ensure workspace_personas link,
        then INSERT the area. All within the same transaction.
        """
        workspace_id: int = data["workspace_id"]
        persona_id: int = data["persona_id"]

        await self._ensure_workspace_persona(workspace_id, persona_id)

        instance = Area(**data)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return row_to_dict(instance)

    async def update_for_workspace(
        self,
        area_id: int,
        workspace_id: int,
        persona_id: int,
        data: Dict[str, Any],
    ) -> bool:
        """
        UPDATE active area scoped to workspace + persona in a single round-trip.
        Stamps updated_at automatically. Returns True when a row was affected.
        """
        payload = {
            **data,
            "updated_at": datetime.now(timezone.utc),
        }
        stmt = (
            update(Area)
            .where(
                and_(
                    Area.id == area_id,
                    Area.workspace_id == workspace_id,
                    Area.persona_id == persona_id,
                    Area.is_active.is_(True),
                )
            )
            .values(**payload)
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    async def soft_delete_for_workspace(
        self,
        area_id: int,
        workspace_id: int,
        persona_id: int,
        updated_by: Optional[int] = None,
    ) -> bool:
        """Soft-delete an active area by setting is_active=False."""
        data: Dict[str, Any] = {"is_active": False}
        if updated_by is not None:
            data["updated_by"] = updated_by
        return await self.update_for_workspace(
            area_id=area_id,
            workspace_id=workspace_id,
            persona_id=persona_id,
            data=data,
        )

    async def restore_for_workspace(
        self,
        area_id: int,
        workspace_id: int,
        persona_id: int,
    ) -> bool:
        """
        Restore a soft-deleted area (is_active=False → True) in a single round-trip.
        Returns True when a row was affected.
        """
        stmt = (
            update(Area)
            .where(
                and_(
                    Area.id == area_id,
                    Area.workspace_id == workspace_id,
                    Area.persona_id == persona_id,
                    Area.is_active.is_(False),
                )
            )
            .values(
                is_active=True,
                updated_at=datetime.now(timezone.utc),
            )
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_all_by_persona(
        self,
        workspace_id: int,
        persona_id: int,
        is_available: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        Return paginated active areas scoped to workspace + persona, ordered
        oldest-first. Each dict includes a 1-based `index` field that reflects
        the absolute position across all pages.
        """
        conditions = [
            Area.workspace_id == workspace_id,
            Area.persona_id == persona_id,
            Area.is_active.is_(True),
        ]

        if is_available is not None:
            conditions.append(Area.is_available == is_available)

        count_stmt = select(func.count()).select_from(Area).where(and_(*conditions))
        total = (await self.db.execute(count_stmt)).scalar_one() or 0
        total_pages = max(1, (total + page_size - 1) // page_size)

        offset = (page - 1) * page_size
        data_stmt = (
            select(Area)
            .where(and_(*conditions))
            .order_by(Area.created_at.asc())
            .limit(page_size)
            .offset(offset)
        )
        rows = (await self.db.execute(data_stmt)).scalars().all()

        result = []
        for idx, row in enumerate(rows, start=offset + 1):
            d = row_to_dict(row)
            d["index"] = idx
            result.append(d)

        return result, total, total_pages


    async def get_by_id_for_persona(
        self,
        area_id: int,
        workspace_id: int,
        persona_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Return a single active area scoped to workspace + persona, or None."""
        stmt = select(Area).where(
            and_(
                Area.id == area_id,
                Area.workspace_id == workspace_id,
                Area.persona_id == persona_id,
                Area.is_active.is_(True),
            )
        )
        row = (await self.db.execute(stmt)).scalars().first()
        return row_to_dict(row) if row is not None else None

    # kept for backward-compat with other callers
    async def get_by_workspace(self, workspace_id: int) -> List[Dict[str, Any]]:
        """Return all active areas for a workspace."""
        return await self.get_all(filters={"workspace_id": workspace_id})

'@

# ==============================================================================
# FILE: app/src/repositories/TableRepository.py
# ==============================================================================
Write-EmbeddedFile "app/src/repositories/TableRepository.py" @'
"""
TableRepository — async SQLAlchemy 2.x repository for the Table model.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.Table import Table


class TableRepository(BaseRepository):
    """Repository for Table entities."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Table, db)

    async def get_by_workspace(self, workspace_id: int) -> List[Dict[str, Any]]:
        """Return all active tables for a workspace."""
        return await self.get_all(filters={"workspace_id": workspace_id})

    async def get_paginated_by_workspace(
        self,
        workspace_id: int,
        persona_id: int,
        area_id: Optional[int] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated tables for a workspace scoped to a persona, with optional filters."""
        conditions = [
            Table.workspace_id == workspace_id,
            Table.is_active.is_(True),
            Table.persona_id == persona_id,
        ]

        if area_id is not None:
            conditions.append(Table.area_id == area_id)
        if status is not None:
            conditions.append(Table.status == status)

        count_stmt = (
            select(func.count())
            .select_from(Table)
            .where(and_(*conditions))
        )
        total = (await self.db.execute(count_stmt)).scalar_one() or 0
        total_pages = max(1, (total + page_size - 1) // page_size)

        offset = (page - 1) * page_size
        data_stmt = (
            select(Table)
            .where(and_(*conditions))
            .order_by(Table.table_number.asc())
            .limit(page_size)
            .offset(offset)
        )
        rows = (await self.db.execute(data_stmt)).scalars().all()
        result = []
        for index, row in enumerate(rows, start=offset + 1):
            d = row_to_dict(row)
            d["index"] = index
            result.append(d)
        return result, total, total_pages

    async def get_by_id_for_persona(
        self,
        table_id: int,
        workspace_id: int,
        persona_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Return a single active table by id, scoped to a persona via Table.persona_id."""
        stmt = (
            select(Table)
            .where(
                Table.id == table_id,
                Table.workspace_id == workspace_id,
                Table.is_active.is_(True),
                Table.persona_id == persona_id,
            )
        )
        row = (await self.db.execute(stmt)).scalars().one_or_none()
        return row_to_dict(row) if row is not None else None

    async def update_for_persona(
        self,
        table_id: int,
        workspace_id: int,
        persona_id: int,
        data: Dict[str, Any],
    ) -> bool:
        """
        Update an active table scoped directly to the given persona.
        Does NOT call self.db.commit() — commit is managed by get_db.
        """
        payload = {**data, "updated_at": datetime.now(timezone.utc)}

        stmt = (
            update(Table)
            .where(
                Table.id == table_id,
                Table.workspace_id == workspace_id,
                Table.persona_id == persona_id,
                Table.is_active.is_(True),
            )
            .values(**payload)
            .execution_options(synchronize_session=False)
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    async def soft_delete_for_persona(
        self,
        table_id: int,
        workspace_id: int,
        persona_id: int,
    ) -> bool:
        """Soft-delete an active table scoped to a persona by setting is_active=False."""
        return await self.update_for_persona(
            table_id=table_id,
            workspace_id=workspace_id,
            persona_id=persona_id,
            data={"is_active": False},
        )

    async def restore_for_persona(
        self,
        table_id: int,
        workspace_id: int,
        persona_id: int,
    ) -> bool:
        """
        Restore a soft-deleted table scoped directly to the given persona.
        Matches only rows where is_active=False.
        Does NOT call self.db.commit() — commit is managed by get_db.
        """
        payload = {
            "is_active": True,
            "updated_at": datetime.now(timezone.utc),
        }

        stmt = (
            update(Table)
            .where(
                Table.id == table_id,
                Table.workspace_id == workspace_id,
                Table.persona_id == persona_id,
                Table.is_active.is_(False),
            )
            .values(**payload)
            .execution_options(synchronize_session=False)
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    async def get_status_counts(
        self,
        workspace_id: int,
        persona_id: int,
    ) -> Dict[str, int]:
        """Return counts of tables grouped by status for a workspace, scoped to a persona."""
        stmt = (
            select(
                func.count(case((Table.status == "available", 1))).label("available"),
                func.count(case((Table.status == "occupied", 1))).label("occupied"),
                func.count(case((Table.status == "reserved", 1))).label("reserved"),
                func.count(case((Table.is_active.is_(False), 1))).label("inactive"),
            )
            .select_from(Table)
            .where(
                Table.workspace_id == workspace_id,
                Table.persona_id == persona_id,
            )
        )

        row = (await self.db.execute(stmt)).one_or_none()
        if row is None:
            return {"available": 0, "occupied": 0, "reserved": 0, "inactive": 0}
        return {
            "available": row.available,
            "occupied": row.occupied,
            "reserved": row.reserved,
            "inactive": row.inactive,
        }

'@

# ==============================================================================
# FILE: app/src/application/services/Area.py
# ==============================================================================
Write-EmbeddedFile "app/src/application/services/Area.py" @'
"""
AreaService — business logic for dining areas.
"""

from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseService import BaseService
from src.repositories.AreaRepository import AreaRepository


class AreaService(BaseService):
    """Service for managing dining areas."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.area_repo = AreaRepository(db)
        super().__init__(self.area_repo)

    async def create_area(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new area.
        - Validates persona_id is provided.
        - Ensures workspace_personas link exists (creates it if not).
        - Inserts the area row.
        """
        if not data.get("persona_id"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="persona_id is required to create an area",
            )
        data.setdefault("is_active", True)
        return await self.area_repo.create_area(data)

    async def get_all_areas(
        self,
        workspace_id: int,
        persona_id: int,
        is_available: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated active areas scoped to workspace and persona, with 1-based absolute index."""
        return await self.area_repo.get_all_by_persona(
            workspace_id=workspace_id,
            persona_id=persona_id,
            is_available=is_available,
            page=page,
            page_size=page_size,
        )


    async def get_area_for_persona(
        self,
        area_id: int,
        workspace_id: int,
        persona_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Fetch a single area scoped to workspace and persona."""
        return await self.area_repo.get_by_id_for_persona(
            area_id, workspace_id, persona_id
        )

    async def update_area(
        self,
        area_id: int,
        workspace_id: int,
        persona_id: int,
        data: Dict[str, Any],
    ) -> bool:
        """Update an area scoped to workspace and persona."""
        return await self.area_repo.update_for_workspace(
            area_id, workspace_id, persona_id, data
        )

    async def soft_delete_area(
        self,
        area_id: int,
        workspace_id: int,
        persona_id: int,
        updated_by: Optional[int] = None,
    ) -> bool:
        """Soft-delete an area scoped to workspace and persona."""
        return await self.area_repo.soft_delete_for_workspace(
            area_id, workspace_id, persona_id, updated_by=updated_by
        )

    async def restore_area(
        self,
        area_id: int,
        workspace_id: int,
        persona_id: int,
    ) -> bool:
        """Restore a soft-deleted area scoped to workspace and persona."""
        return await self.area_repo.restore_for_workspace(
            area_id, workspace_id, persona_id
        )

'@

# ==============================================================================
# FILE: app/src/application/services/Table.py
# ==============================================================================
Write-EmbeddedFile "app/src/application/services/Table.py" @'
"""
TableService — business logic for restaurant tables.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseService import BaseService
from src.repositories.TableRepository import TableRepository


class TableService(BaseService):
    """Service for managing restaurant tables."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.table_repo = TableRepository(db)
        super().__init__(self.table_repo)

    async def create_table(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new table. Requires persona_id in data for isolation."""
        if not data.get("persona_id"):
            raise ValueError("persona_id is required to create a table")
        data.setdefault("is_active", True)
        data.setdefault("status", "available")
        return await self.table_repo.create(data)


    async def get_paginated_tables(
        self,
        workspace_id: int,
        persona_id: int,
        area_id: Optional[int] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated tables scoped to the given persona."""
        return await self.table_repo.get_paginated_by_workspace(
            workspace_id=workspace_id,
            persona_id=persona_id,
            area_id=area_id,
            status=status,
            page=page,
            page_size=page_size,
        )

    async def get_table_for_persona(
        self,
        table_id: int,
        workspace_id: int,
        persona_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Fetch a single active table that belongs to the given persona."""
        return await self.table_repo.get_by_id_for_persona(
            table_id, workspace_id, persona_id
        )

    async def update_table(
        self,
        table_id: int,
        workspace_id: int,
        persona_id: int,
        data: Dict[str, Any],
    ) -> bool:
        """Update a table scoped to the given persona."""
        return await self.table_repo.update_for_persona(
            table_id, workspace_id, persona_id, data
        )

    async def update_table_status(
        self,
        table_id: int,
        workspace_id: int,
        persona_id: int,
        status: str,
    ) -> bool:
        """Update only the status field of a table scoped to the given persona."""
        return await self.table_repo.update_for_persona(
            table_id, workspace_id, persona_id, {"status": status}
        )

    async def soft_delete_table(
        self,
        table_id: int,
        workspace_id: int,
        persona_id: int,
    ) -> bool:
        """Soft-delete a table scoped to the given persona."""
        return await self.table_repo.soft_delete_for_persona(
            table_id, workspace_id, persona_id
        )

    async def restore_table(
        self,
        table_id: int,
        workspace_id: int,
        persona_id: int,
    ) -> bool:
        """Restore a soft-deleted table scoped to the given persona."""
        return await self.table_repo.restore_for_persona(
            table_id, workspace_id, persona_id
        )

    async def get_table_status_summary(
        self,
        workspace_id: int,
        persona_id: int,
    ) -> Dict[str, int]:
        """Return counts of tables grouped by status, scoped to the given persona."""
        return await self.table_repo.get_status_counts(workspace_id, persona_id)

'@

# ==============================================================================
# FILE: app/src/application/routes/Areas.py
# ==============================================================================
Write-EmbeddedFile "app/src/application/routes/Areas.py" @'
"""
Areas router — CRUD for dining areas, scoped by workspace (JWT) and persona.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Area import AreaService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db

router = APIRouter(prefix="/areas", tags=["Areas"])


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CreateAreaRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    persona_id: int = Field(..., ge=1)
    is_available: bool = True


class UpdateAreaRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    is_available: Optional[bool] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_workspace(current_user: Dict[str, Any]) -> int:
    """Extract workspace_id from JWT claims; raise 400 if absent."""
    wid = current_user.get("workspace_id")
    if not wid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="workspace_id required",
        )
    return wid


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=BaseResponse)
async def get_areas(
    persona_id: int = Query(..., ge=1),
    is_available: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("areas:read")),
    db: AsyncSession = Depends(get_db),
):
    """List paginated areas scoped to workspace + persona, ordered oldest-first with 1-based absolute index."""
    wid = _require_workspace(current_user)
    service = AreaService(db)
    items, total, total_pages = await service.get_all_areas(
        workspace_id=wid,
        persona_id=persona_id,
        is_available=is_available,
        page=page,
        page_size=page_size,
    )
    return {
        "success": True,
        "message": "Areas retrieved successfully",
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



@router.post("", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_area(
    request: CreateAreaRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("areas:create")),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new area scoped to workspace + persona.
    Automatically links the persona to the workspace in workspace_personas if not already linked.
    """
    wid = _require_workspace(current_user)
    service = AreaService(db)
    data = request.model_dump()
    data["workspace_id"] = wid
    area = await service.create_area(data)
    return {"success": True, "message": "Area created successfully", "data": area}


@router.get("/{area_id}", response_model=BaseResponse)
async def get_area(
    area_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("areas:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a single area scoped to workspace + persona."""
    wid = _require_workspace(current_user)
    service = AreaService(db)
    area = await service.get_area_for_persona(area_id, wid, persona_id)
    if not area:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")
    return {"success": True, "message": "Area retrieved successfully", "data": area}


@router.put("/{area_id}", response_model=BaseResponse)
async def update_area(
    area_id: int,
    request: UpdateAreaRequest,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("areas:update")),
    db: AsyncSession = Depends(get_db),
):
    """Update name, description, or is_available for an area scoped to workspace + persona."""
    wid = _require_workspace(current_user)
    data = request.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )
    service = AreaService(db)
    updated = await service.update_area(area_id, wid, persona_id, data)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")
    return {"success": True, "message": "Area updated successfully"}


@router.delete("/{area_id}", response_model=BaseResponse)
async def delete_area(
    area_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("areas:delete")),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete an area (sets is_active=False) scoped to workspace + persona."""
    wid = _require_workspace(current_user)
    service = AreaService(db)
    deleted = await service.soft_delete_area(
        area_id, wid, persona_id, updated_by=current_user.get("id")
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")
    return {"success": True, "message": "Area deleted successfully"}


@router.post("/{area_id}/restore", response_model=BaseResponse)
async def restore_area(
    area_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("areas:update")),
    db: AsyncSession = Depends(get_db),
):
    """Restore a soft-deleted area scoped to workspace + persona."""
    wid = _require_workspace(current_user)
    service = AreaService(db)
    restored = await service.restore_area(area_id, wid, persona_id)
    if not restored:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Area not found or is not deleted",
        )
    return {"success": True, "message": "Area restored successfully"}

'@

# ==============================================================================
# FILE: app/src/application/routes/Tables.py
# ==============================================================================
Write-EmbeddedFile "app/src/application/routes/Tables.py" @'
"""
Tables router — CRUD for restaurant tables.
"""

from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Table import TableService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db

router = APIRouter(prefix="/tables", tags=["Tables"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_workspace(current_user: Dict[str, Any]) -> int:
    wid = current_user.get("workspace_id")
    if not wid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="workspace_id required",
        )
    return wid


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CreateTableRequest(BaseModel):
    table_number: str = Field(..., min_length=1, max_length=50)
    area_id: int = Field(..., ge=1)
    persona_id: int = Field(..., ge=1)
    capacity: int = Field(4, ge=1, le=50)
    status: Literal["available", "occupied", "reserved", "out_of_service"] = "available"



class UpdateTableRequest(BaseModel):
    table_number: Optional[str] = Field(None, min_length=1, max_length=50)
    capacity: Optional[int] = Field(None, ge=1, le=50)
    status: Optional[Literal["available", "occupied", "reserved", "out_of_service"]] = None



class UpdateTableStatusRequest(BaseModel):
    status: Literal["available", "occupied", "reserved", "out_of_service"]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/summary", response_model=BaseResponse)
async def get_table_summary(
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("tables:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get table status counts summary."""
    wid = _require_workspace(current_user)
    service = TableService(db)
    summary = await service.get_table_status_summary(wid, persona_id)
    return {"success": True, "message": "Table summary retrieved successfully", "data": summary}


@router.get("", response_model=BaseResponse)
async def get_tables(
    persona_id: int = Query(..., ge=1),
    area_id: Optional[int] = Query(None),
    table_status: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("tables:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated tables."""
    wid = _require_workspace(current_user)
    service = TableService(db)
    items, total, total_pages = await service.get_paginated_tables(
        workspace_id=wid,
        persona_id=persona_id,
        area_id=area_id,
        status=table_status,
        page=page,
        page_size=page_size,
    )
    return {
        "success": True,
        "message": "Tables retrieved successfully",
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


@router.post("", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_table(
    request: CreateTableRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("tables:create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new table."""
    wid = _require_workspace(current_user)
    service = TableService(db)
    data = request.model_dump(exclude_none=True)
    data["workspace_id"] = wid
    table = await service.create_table(data)
    return {"success": True, "message": "Table created successfully", "data": table}



@router.get("/{table_id}", response_model=BaseResponse)
async def get_table(
    table_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("tables:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a table by ID scoped to persona."""
    wid = _require_workspace(current_user)
    service = TableService(db)
    table = await service.get_table_for_persona(table_id, wid, persona_id)
    if not table:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    return {"success": True, "message": "Table retrieved successfully", "data": table}


@router.put("/{table_id}", response_model=BaseResponse)
async def update_table(
    table_id: int,
    request: UpdateTableRequest,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("tables:update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a table."""
    wid = _require_workspace(current_user)
    data = request.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )
    service = TableService(db)
    updated = await service.update_table(table_id, wid, persona_id, data)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    return {"success": True, "message": "Table updated successfully"}


@router.put("/{table_id}/status", response_model=BaseResponse)
async def update_table_status(
    table_id: int,
    request: UpdateTableStatusRequest,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("tables:update")),
    db: AsyncSession = Depends(get_db),
):
    """Update only the status of a table."""
    wid = _require_workspace(current_user)
    service = TableService(db)
    updated = await service.update_table_status(table_id, wid, persona_id, request.status)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    return {"success": True, "message": "Table status updated successfully"}


@router.delete("/{table_id}", response_model=BaseResponse)
async def delete_table(
    table_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("tables:delete")),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a table."""
    wid = _require_workspace(current_user)
    service = TableService(db)
    deleted = await service.soft_delete_table(table_id, wid, persona_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    return {"success": True, "message": "Table deleted successfully"}


@router.post("/{table_id}/restore", response_model=BaseResponse)
async def restore_table(
    table_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("tables:update")),
    db: AsyncSession = Depends(get_db),
):
    """Restore a soft-deleted table."""
    wid = _require_workspace(current_user)
    service = TableService(db)
    restored = await service.restore_table(table_id, wid, persona_id)
    if not restored:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found or is not deleted",
        )
    return {"success": True, "message": "Table restored successfully"}

'@

# ==============================================================================
# FILE: system/src/alembic/versions/004_drop_image_url_from_categories.py
# ==============================================================================
Write-EmbeddedFile "system/src/alembic/versions/004_drop_image_url_from_categories.py" @'
"""Drop image_url from categories

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-04-30 00:00:00.000000

Changes:
  - categories: drop image_url column (String 500, nullable)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------
revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    """Return True if *column* exists in *table* in the current DB."""
    bind = op.get_bind()
    insp = inspect(bind)
    return any(c["name"] == column for c in insp.get_columns(table))


def upgrade() -> None:
    if _column_exists("categories", "image_url"):
        op.drop_column("categories", "image_url")


def downgrade() -> None:
    if not _column_exists("categories", "image_url"):
        op.add_column(
            "categories",
            sa.Column("image_url", sa.String(500), nullable=True),
        )

'@

# ==============================================================================
# FILE: system/src/alembic/versions/005_workspace_requests_refactor.py
# ==============================================================================
Write-EmbeddedFile "system/src/alembic/versions/005_workspace_requests_refactor.py" @'
"""Refactor workspace_requests: rename user_id→referred_by, add referred_by_user_id; drop workspaces.requested_by

Revision ID: e7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-04-30 00:00:00.000000

Changes:
  - workspaces: drop index ix_workspaces_requested_by, FK fk_workspaces_requested_by, column requested_by
  - workspace_requests: rename column user_id → referred_by
      - rename FK  fk_workspace_requests_user_id  → fk_workspace_requests_referred_by
      - rename index ix_workspace_requests_user_id → ix_workspace_requests_referred_by
  - workspace_requests: add column referred_by_user_id (BigInteger, nullable, FK → users.id SET NULL)
      - FK  fk_workspace_requests_referred_by_user_id
      - index ix_workspace_requests_referred_by_user_id
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------
revision: str = "e7a8b9c0d1e2"
down_revision: Union[str, None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Guard helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    # -----------------------------------------------------------------------
    # 1. workspaces — drop ix_workspaces_requested_by index
    # -----------------------------------------------------------------------
    if _index_exists("workspaces", "ix_workspaces_requested_by"):
        op.drop_index("ix_workspaces_requested_by", table_name="workspaces")

    # -----------------------------------------------------------------------
    # 2. workspaces — drop fk_workspaces_requested_by FK
    # -----------------------------------------------------------------------
    if _fk_exists("workspaces", "fk_workspaces_requested_by"):
        op.drop_constraint("fk_workspaces_requested_by", "workspaces", type_="foreignkey")

    # -----------------------------------------------------------------------
    # 3. workspaces — drop requested_by column
    # -----------------------------------------------------------------------
    if _column_exists("workspaces", "requested_by"):
        op.drop_column("workspaces", "requested_by")

    # -----------------------------------------------------------------------
    # 4. workspace_requests — drop old index on user_id before renaming column
    # -----------------------------------------------------------------------
    if _index_exists("workspace_requests", "ix_workspace_requests_user_id"):
        op.drop_index("ix_workspace_requests_user_id", table_name="workspace_requests")

    # -----------------------------------------------------------------------
    # 5. workspace_requests — drop old FK on user_id before renaming column
    # -----------------------------------------------------------------------
    if _fk_exists("workspace_requests", "fk_workspace_requests_user_id"):
        op.drop_constraint("fk_workspace_requests_user_id", "workspace_requests", type_="foreignkey")

    # -----------------------------------------------------------------------
    # 6. workspace_requests — rename column user_id → referred_by
    # -----------------------------------------------------------------------
    if _column_exists("workspace_requests", "user_id") and not _column_exists("workspace_requests", "referred_by"):
        op.alter_column("workspace_requests", "user_id", new_column_name="referred_by")

    # -----------------------------------------------------------------------
    # 7. workspace_requests — recreate FK on referred_by → users.id SET NULL
    # -----------------------------------------------------------------------
    if not _fk_exists("workspace_requests", "fk_workspace_requests_referred_by"):
        op.create_foreign_key(
            "fk_workspace_requests_referred_by",
            "workspace_requests",
            "users",
            ["referred_by"],
            ["id"],
            ondelete="SET NULL",
        )

    # -----------------------------------------------------------------------
    # 8. workspace_requests — recreate index on referred_by
    # -----------------------------------------------------------------------
    if not _index_exists("workspace_requests", "ix_workspace_requests_referred_by"):
        op.create_index(
            "ix_workspace_requests_referred_by",
            "workspace_requests",
            ["referred_by"],
        )

    # -----------------------------------------------------------------------
    # 9. workspace_requests — add referred_by_user_id column
    # -----------------------------------------------------------------------
    if not _column_exists("workspace_requests", "referred_by_user_id"):
        op.add_column(
            "workspace_requests",
            sa.Column(
                "referred_by_user_id",
                sa.BigInteger(),
                nullable=True,
                comment="System user who submitted the referral request",
            ),
        )

    # -----------------------------------------------------------------------
    # 10. workspace_requests — FK for referred_by_user_id → users.id SET NULL
    # -----------------------------------------------------------------------
    if not _fk_exists("workspace_requests", "fk_workspace_requests_referred_by_user_id"):
        op.create_foreign_key(
            "fk_workspace_requests_referred_by_user_id",
            "workspace_requests",
            "users",
            ["referred_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # -----------------------------------------------------------------------
    # 11. workspace_requests — index on referred_by_user_id
    # -----------------------------------------------------------------------
    if not _index_exists("workspace_requests", "ix_workspace_requests_referred_by_user_id"):
        op.create_index(
            "ix_workspace_requests_referred_by_user_id",
            "workspace_requests",
            ["referred_by_user_id"],
        )


# ---------------------------------------------------------------------------
# Downgrade — fully reverses all upgrade steps in reverse order
# ---------------------------------------------------------------------------

def downgrade() -> None:
    # -----------------------------------------------------------------------
    # 1. workspace_requests — drop index + FK + column referred_by_user_id
    # -----------------------------------------------------------------------
    if _index_exists("workspace_requests", "ix_workspace_requests_referred_by_user_id"):
        op.drop_index("ix_workspace_requests_referred_by_user_id", table_name="workspace_requests")

    if _fk_exists("workspace_requests", "fk_workspace_requests_referred_by_user_id"):
        op.drop_constraint(
            "fk_workspace_requests_referred_by_user_id",
            "workspace_requests",
            type_="foreignkey",
        )

    if _column_exists("workspace_requests", "referred_by_user_id"):
        op.drop_column("workspace_requests", "referred_by_user_id")

    # -----------------------------------------------------------------------
    # 2. workspace_requests — drop index + FK on referred_by before renaming back
    # -----------------------------------------------------------------------
    if _index_exists("workspace_requests", "ix_workspace_requests_referred_by"):
        op.drop_index("ix_workspace_requests_referred_by", table_name="workspace_requests")

    if _fk_exists("workspace_requests", "fk_workspace_requests_referred_by"):
        op.drop_constraint(
            "fk_workspace_requests_referred_by",
            "workspace_requests",
            type_="foreignkey",
        )

    # -----------------------------------------------------------------------
    # 3. workspace_requests — rename column referred_by → user_id
    # -----------------------------------------------------------------------
    if _column_exists("workspace_requests", "referred_by") and not _column_exists("workspace_requests", "user_id"):
        op.alter_column("workspace_requests", "referred_by", new_column_name="user_id")

    # -----------------------------------------------------------------------
    # 4. workspace_requests — restore FK fk_workspace_requests_user_id
    # -----------------------------------------------------------------------
    if not _fk_exists("workspace_requests", "fk_workspace_requests_user_id"):
        op.create_foreign_key(
            "fk_workspace_requests_user_id",
            "workspace_requests",
            "users",
            ["user_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # -----------------------------------------------------------------------
    # 5. workspace_requests — restore index ix_workspace_requests_user_id
    # -----------------------------------------------------------------------
    if not _index_exists("workspace_requests", "ix_workspace_requests_user_id"):
        op.create_index(
            "ix_workspace_requests_user_id",
            "workspace_requests",
            ["user_id"],
        )

    # -----------------------------------------------------------------------
    # 6. workspaces — restore requested_by column
    # -----------------------------------------------------------------------
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

    # -----------------------------------------------------------------------
    # 7. workspaces — restore FK fk_workspaces_requested_by
    # -----------------------------------------------------------------------
    if not _fk_exists("workspaces", "fk_workspaces_requested_by"):
        op.create_foreign_key(
            "fk_workspaces_requested_by",
            "workspaces",
            "users",
            ["requested_by"],
            ["id"],
            ondelete="SET NULL",
        )

    # -----------------------------------------------------------------------
    # 8. workspaces — restore index ix_workspaces_requested_by
    # -----------------------------------------------------------------------
    if not _index_exists("workspaces", "ix_workspaces_requested_by"):
        op.create_index(
            "ix_workspaces_requested_by",
            "workspaces",
            ["requested_by"],
        )

'@

# ==============================================================================
# FILE: system/src/alembic/versions/006_drop_display_order_from_tables.py
# ==============================================================================
Write-EmbeddedFile "system/src/alembic/versions/006_drop_display_order_from_tables.py" @'
"""Drop display_order from tables

Revision ID: f8b9c0d1e2f3
Revises: e7a8b9c0d1e2
Create Date: 2026-04-30 00:00:00.000000

Changes:
  - tables: drop display_order column (Integer, not null, server_default=0)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------
revision: str = "f8b9c0d1e2f3"
down_revision: Union[str, None] = "e7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    """Return True if *column* exists in *table* in the current DB."""
    bind = op.get_bind()
    insp = inspect(bind)
    return any(c["name"] == column for c in insp.get_columns(table))


def upgrade() -> None:
    if _column_exists("tables", "display_order"):
        op.drop_column("tables", "display_order")


def downgrade() -> None:
    if not _column_exists("tables", "display_order"):
        op.add_column(
            "tables",
            sa.Column(
                "display_order",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )

'@

# ==============================================================================
# FILE: system/src/alembic/versions/007_simplify_workspace_requests_referral.py
# ==============================================================================
Write-EmbeddedFile "system/src/alembic/versions/007_simplify_workspace_requests_referral.py" @'
"""Simplify workspace_requests referral columns: drop referred_by, rename referred_by_user_id → referred_by

Revision ID: a1b2c3d4e5f7
Revises: f8b9c0d1e2f3
Create Date: 2026-04-30 00:00:00.000000

Changes:
  - workspace_requests: drop index ix_workspace_requests_referred_by
  - workspace_requests: drop FK fk_workspace_requests_referred_by
  - workspace_requests: drop column referred_by
      (was the user.id resolved from the referral email — redundant, email already captures this)
  - workspace_requests: drop index ix_workspace_requests_referred_by_id
  - workspace_requests: drop FK fk_workspace_requests_referred_by_id
  - workspace_requests: rename column referred_by_user_id → referred_by
      (the logged-in system user who submitted the request — the meaningful FK)
  - workspace_requests: recreate FK fk_workspace_requests_referred_by on referred_by → users.id SET NULL
  - workspace_requests: recreate index ix_workspace_requests_referred_by
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------
revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, None] = "f8b9c0d1e2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Guard helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    # -----------------------------------------------------------------------
    # 1. workspace_requests — drop index ix_workspace_requests_referred_by
    # -----------------------------------------------------------------------
    if _index_exists("workspace_requests", "ix_workspace_requests_referred_by"):
        op.drop_index("ix_workspace_requests_referred_by", table_name="workspace_requests")

    # -----------------------------------------------------------------------
    # 2. workspace_requests — drop FK fk_workspace_requests_referred_by
    # -----------------------------------------------------------------------
    if _fk_exists("workspace_requests", "fk_workspace_requests_referred_by"):
        op.drop_constraint(
            "fk_workspace_requests_referred_by",
            "workspace_requests",
            type_="foreignkey",
        )

    # -----------------------------------------------------------------------
    # 3. workspace_requests — drop column referred_by
    # -----------------------------------------------------------------------
    if _column_exists("workspace_requests", "referred_by"):
        op.drop_column("workspace_requests", "referred_by")

    # -----------------------------------------------------------------------
    # 4. workspace_requests — drop index ix_workspace_requests_referred_by_id
    # -----------------------------------------------------------------------
    if _index_exists("workspace_requests", "ix_workspace_requests_referred_by_id"):
        op.drop_index(
            "ix_workspace_requests_referred_by_id",
            table_name="workspace_requests",
        )

    # -----------------------------------------------------------------------
    # 5. workspace_requests — drop FK fk_workspace_requests_referred_by_id
    # -----------------------------------------------------------------------
    if _fk_exists("workspace_requests", "fk_workspace_requests_referred_by_id"):
        op.drop_constraint(
            "fk_workspace_requests_referred_by_id",
            "workspace_requests",
            type_="foreignkey",
        )

    # -----------------------------------------------------------------------
    # 6. workspace_requests — rename column referred_by_user_id → referred_by
    # -----------------------------------------------------------------------
    if _column_exists("workspace_requests", "referred_by_user_id") and not _column_exists(
        "workspace_requests", "referred_by"
    ):
        op.alter_column(
            "workspace_requests",
            "referred_by_user_id",
            new_column_name="referred_by",
        )

    # -----------------------------------------------------------------------
    # 7. workspace_requests — recreate FK fk_workspace_requests_referred_by
    # -----------------------------------------------------------------------
    if not _fk_exists("workspace_requests", "fk_workspace_requests_referred_by"):
        op.create_foreign_key(
            "fk_workspace_requests_referred_by",
            "workspace_requests",
            "users",
            ["referred_by"],
            ["id"],
            ondelete="SET NULL",
        )

    # -----------------------------------------------------------------------
    # 8. workspace_requests — recreate index ix_workspace_requests_referred_by
    # -----------------------------------------------------------------------
    if not _index_exists("workspace_requests", "ix_workspace_requests_referred_by"):
        op.create_index(
            "ix_workspace_requests_referred_by",
            "workspace_requests",
            ["referred_by"],
        )


# ---------------------------------------------------------------------------
# Downgrade — fully reverses all upgrade steps in reverse order
# ---------------------------------------------------------------------------

def downgrade() -> None:
    # -----------------------------------------------------------------------
    # 1. workspace_requests — drop index ix_workspace_requests_referred_by
    # -----------------------------------------------------------------------
    if _index_exists("workspace_requests", "ix_workspace_requests_referred_by"):
        op.drop_index(
            "ix_workspace_requests_referred_by",
            table_name="workspace_requests",
        )

    # -----------------------------------------------------------------------
    # 2. workspace_requests — drop FK fk_workspace_requests_referred_by
    # -----------------------------------------------------------------------
    if _fk_exists("workspace_requests", "fk_workspace_requests_referred_by"):
        op.drop_constraint(
            "fk_workspace_requests_referred_by",
            "workspace_requests",
            type_="foreignkey",
        )

    # -----------------------------------------------------------------------
    # 3. workspace_requests — rename column referred_by → referred_by_user_id
    # -----------------------------------------------------------------------
    if _column_exists("workspace_requests", "referred_by") and not _column_exists(
        "workspace_requests", "referred_by_user_id"
    ):
        op.alter_column(
            "workspace_requests",
            "referred_by",
            new_column_name="referred_by_user_id",
        )

    # -----------------------------------------------------------------------
    # 4. workspace_requests — restore FK fk_workspace_requests_referred_by_id
    # -----------------------------------------------------------------------
    if not _fk_exists("workspace_requests", "fk_workspace_requests_referred_by_id"):
        op.create_foreign_key(
            "fk_workspace_requests_referred_by_id",
            "workspace_requests",
            "users",
            ["referred_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # -----------------------------------------------------------------------
    # 5. workspace_requests — restore index ix_workspace_requests_referred_by_id
    # -----------------------------------------------------------------------
    if not _index_exists("workspace_requests", "ix_workspace_requests_referred_by_id"):
        op.create_index(
            "ix_workspace_requests_referred_by_id",
            "workspace_requests",
            ["referred_by_user_id"],
        )

    # -----------------------------------------------------------------------
    # 6. workspace_requests — restore column referred_by
    # -----------------------------------------------------------------------
    if not _column_exists("workspace_requests", "referred_by"):
        op.add_column(
            "workspace_requests",
            sa.Column(
                "referred_by",
                sa.BigInteger(),
                nullable=True,
                comment="User ID resolved from the referral email (person being referred)",
            ),
        )

    # -----------------------------------------------------------------------
    # 7. workspace_requests — restore FK fk_workspace_requests_referred_by
    # -----------------------------------------------------------------------
    if not _fk_exists("workspace_requests", "fk_workspace_requests_referred_by"):
        op.create_foreign_key(
            "fk_workspace_requests_referred_by",
            "workspace_requests",
            "users",
            ["referred_by"],
            ["id"],
            ondelete="SET NULL",
        )

    # -----------------------------------------------------------------------
    # 8. workspace_requests — restore index ix_workspace_requests_referred_by
    # -----------------------------------------------------------------------
    if not _index_exists("workspace_requests", "ix_workspace_requests_referred_by"):
        op.create_index(
            "ix_workspace_requests_referred_by",
            "workspace_requests",
            ["referred_by"],
        )

'@

# ==============================================================================
# FILE: system/src/models/Workspace.py
# ==============================================================================
Write-EmbeddedFile "system/src/models/Workspace.py" @'
"""
Workspace ORM model and workspace_personas association table.

owner_id    – references users.id (SET NULL on delete)
is_verified – set to True when an admin approves the workspace request
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

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    owner_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
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
        foreign_keys="[User.workspace_id]",
        back_populates="workspace",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Workspace id={self.id} name={self.name!r} verified={self.is_verified}>"


'@

# ==============================================================================
# FILE: system/src/models/WorkspaceRequest.py
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
        Index("ix_workspace_requests_referred_by", "referred_by"),
        Index("ix_workspace_requests_workspace_id", "workspace_id"),
        Index("ix_workspace_requests_status", "status"),
    )

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    referred_by: Mapped[Optional[int]] = mapped_column(
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
    referred_by_user: Mapped[Optional["User"]] = relationship(  # noqa: F821
        "User",
        foreign_keys=[referred_by],
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
# FILE: system/src/schemas/Workspace.py
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
# FILE: system/src/schemas/WorkspaceRequest.py
# ==============================================================================
Write-EmbeddedFile "system/src/schemas/WorkspaceRequest.py" @'
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class WorkspaceRequestCreate(BaseModel):
    """Create workspace request schema"""
    email: EmailStr
    workspace_id: int
    referral_email: Optional[str] = None  # email of the system user who referred this workspace; null = no referral




class WorkspaceRequestReject(BaseModel):
    """Reject workspace request schema"""
    rejection_reason: Optional[str] = None


class WorkspaceRequestResponse(BaseModel):
    """Workspace request response schema"""
    id: int
    email: str
    referred_by: Optional[int] = None
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
# FILE: system/src/repositories/WorkspaceRequestRepository.py
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
        Return True if any active WorkspaceRequest with status=''pending''
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

    async def get_referral_stats(self, days: int = 30) -> Dict:
        """
        Return submission statistics derived from workspace_requests.

        Computes:
        - Summary counts: total, by status, last N days vs previous N days
        - Per-submitter breakdown: name, email, counts by status, workspaces list
        """
        from datetime import datetime, timedelta, timezone

        from sqlalchemy import case, distinct

        from src.models.User import User
        from src.models.Workspace import Workspace

        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=days)
        prev_period_start = now - timedelta(days=days * 2)

        # ------------------------------------------------------------------
        # 1. Summary counts — total submissions and breakdown by status
        # ------------------------------------------------------------------
        summary_stmt = select(
            func.count().label("total"),
            func.count(case((WorkspaceRequest.status == "pending", 1))).label("pending"),
            func.count(case((WorkspaceRequest.status == "approved", 1))).label("approved"),
            func.count(case((WorkspaceRequest.status == "rejected", 1))).label("rejected"),
            func.count(case((WorkspaceRequest.created_at >= period_start, 1))).label("last_n_days"),
            func.count(case((
                and_(
                    WorkspaceRequest.created_at >= prev_period_start,
                    WorkspaceRequest.created_at < period_start,
                ), 1,
            ))).label("prev_n_days"),
            func.count(distinct(WorkspaceRequest.referred_by)).label("total_referrers"),
        ).where(WorkspaceRequest.is_active == True)  # noqa: E712

        summary_row = (await self.db.execute(summary_stmt)).one()

        # ------------------------------------------------------------------
        # 2. Per-submitter aggregates — grouped by user_id
        # ------------------------------------------------------------------
        referrer_agg_stmt = (
            select(
                WorkspaceRequest.referred_by,
                WorkspaceRequest.email,
                func.count().label("total"),
                func.count(case((WorkspaceRequest.status == "pending", 1))).label("pending"),
                func.count(case((WorkspaceRequest.status == "approved", 1))).label("approved"),
                func.count(case((WorkspaceRequest.status == "rejected", 1))).label("rejected"),
            )
            .where(WorkspaceRequest.is_active == True)  # noqa: E712
            .group_by(WorkspaceRequest.referred_by, WorkspaceRequest.email)
            .order_by(func.count().desc())
        )
        referrer_rows = (await self.db.execute(referrer_agg_stmt)).all()

        # ------------------------------------------------------------------
        # 3. All request records joined with workspace name for detail list
        # ------------------------------------------------------------------
        detail_stmt = (
            select(
                WorkspaceRequest.id,
                WorkspaceRequest.referred_by,
                WorkspaceRequest.email,
                WorkspaceRequest.workspace_id,
                WorkspaceRequest.status,
                WorkspaceRequest.reviewed_at,
                WorkspaceRequest.rejection_reason,
                WorkspaceRequest.created_at,
                Workspace.name.label("workspace_name"),
                Workspace.is_active.label("workspace_active"),
                Workspace.is_verified.label("workspace_verified"),
                (User.first_name + " " + User.last_name).label("referrer_name"),
            )
            .outerjoin(Workspace, Workspace.id == WorkspaceRequest.workspace_id)
            .outerjoin(User, User.id == WorkspaceRequest.referred_by)
            .where(WorkspaceRequest.is_active == True)  # noqa: E712
            .order_by(WorkspaceRequest.created_at.desc())
        )
        detail_rows = (await self.db.execute(detail_stmt)).all()

        # ------------------------------------------------------------------
        # 4. Fetch submitter full names for the aggregated list
        # ------------------------------------------------------------------
        user_ids = [r.referred_by for r in referrer_rows if r.referred_by is not None]
        user_map: Dict[int, Dict] = {}
        if user_ids:
            user_stmt = select(
                User.id,
                User.first_name,
                User.last_name,
                User.email,
            ).where(User.id.in_(user_ids))
            for u in (await self.db.execute(user_stmt)).all():
                user_map[u.id] = {
                    "first_name": u.first_name,
                    "last_name": u.last_name,
                    "email": u.email,
                }

        # ------------------------------------------------------------------
        # 5. Build workspace detail list per submitter
        # ------------------------------------------------------------------
        workspaces_by_referrer: Dict[Optional[int], list] = {}
        for row in detail_rows:
            key = row.referred_by
            if key not in workspaces_by_referrer:
                workspaces_by_referrer[key] = []
            workspaces_by_referrer[key].append({
                "request_id": row.id,
                "workspace_id": row.workspace_id,
                "workspace_name": row.workspace_name,
                "workspace_active": row.workspace_active,
                "workspace_verified": row.workspace_verified,
                "status": row.status,
                "rejection_reason": row.rejection_reason,
                "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
                "referred_at": row.created_at.isoformat() if row.created_at else None,
            })

        # ------------------------------------------------------------------
        # 6. Assemble top_referrers list
        # ------------------------------------------------------------------
        top_referrers = []
        for row in referrer_rows:
            uid = row.referred_by
            user_info = user_map.get(uid, {})
            first = user_info.get("first_name", "")
            last = user_info.get("last_name", "")
            top_referrers.append({
                "referred_by": uid,
                "name": f"{first} {last}".strip() or row.email,
                "email": user_info.get("email", row.email),
                "total": row.total,
                "pending": row.pending,
                "approved": row.approved,
                "rejected": row.rejected,
                "workspaces": workspaces_by_referrer.get(uid, []),
            })

        return {
            "summary_row": summary_row,
            "top_referrers": top_referrers,
        }



'@

# ==============================================================================
# FILE: system/src/system/routes/WorkspaceRequests.py
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
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_system_user),
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
# FILE: system/src/system/services/WorkspaceRequest.py
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
        """
        Submit a new workspace join request.

        referred_by is resolved from referral_email when provided:
          - If referral_email is a non-empty string and matches an active system user,
            referred_by is set to that user''s id.
          - If referral_email is empty/None or no matching user is found, referred_by is null.
        """
        email: str = data["email"]
        workspace_id: int = data["workspace_id"]
        referral_email: Optional[str] = (data.get("referral_email") or "").strip() or None

        has_pending: bool = await self.workspace_request_repo.has_pending_request(workspace_id)
        if has_pending:
            raise HTTPException(
                status_code=409,
                detail="A pending request already exists for this workspace",
            )

        referred_by: Optional[int] = None
        if referral_email:
            referrer: Optional[Dict] = await self.user_repo.get_by_field("email", referral_email)
            if referrer and referrer.get("user_type") == 0 and referrer.get("is_active"):
                referred_by = referrer["id"]

        record = await self.create(
            {
                "email": email,
                "referred_by": referred_by,
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
            {"is_verified": True},
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
Write-Host "Done. All files restored successfully." -ForegroundColor Green
Write-Host ""
