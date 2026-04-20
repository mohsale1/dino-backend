"""
RoleRepository — async SQLAlchemy 2.x repository for the Role model.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.Role import Role, role_permissions


class RoleRepository(BaseRepository):
    """Repository for Role entities."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Role, db)

    # ------------------------------------------------------------------
    # Basic lookups
    # ------------------------------------------------------------------

    async def get_by_type(self, role_type: int) -> List[Dict[str, Any]]:
        """Return all active roles of the given type (0=System, 1=Application)."""
        return await self.get_all(filters={"role_type": role_type})

    async def get_by_name_and_type(
        self, name: str, role_type: int
    ) -> Optional[Dict[str, Any]]:
        """Return the first active role matching both name and role_type."""
        stmt = (
            select(self.model)
            .where(self.model.name == name)
            .where(self.model.role_type == role_type)
            .where(self.model.is_active == True)  # noqa: E712
            .limit(1)
        )
        result = await self.db.execute(stmt)
        row = result.scalars().first()
        return row_to_dict(row) if row is not None else None

    # ------------------------------------------------------------------
    # Permission association management
    # ------------------------------------------------------------------

    async def add_permissions(
        self, role_id: str, permission_ids: List[str]
    ) -> bool:
        """
        Insert rows into role_permissions for each permission_id.
        Silently skips any pair that already exists (ON CONFLICT DO NOTHING).
        Returns True on success.
        """
        if not permission_ids:
            return True

        stmt = pg_insert(role_permissions).values(
            [{"role_id": role_id, "permission_id": pid} for pid in permission_ids]
        ).on_conflict_do_nothing()

        await self.db.execute(stmt)
        await self.db.flush()
        return True

    async def remove_permissions(
        self, role_id: str, permission_ids: List[str]
    ) -> bool:
        """
        Delete rows from role_permissions for the given role_id / permission_id pairs.
        Returns True on success.
        """
        if not permission_ids:
            return True

        stmt = delete(role_permissions).where(
            role_permissions.c.role_id == role_id,
            role_permissions.c.permission_id.in_(permission_ids),
        )
        await self.db.execute(stmt)
        await self.db.flush()
        return True

    async def get_role_permissions(self, role_id: str) -> List[str]:
        """
        Return the list of permission_id strings assigned to the given role.
        """
        stmt = select(role_permissions.c.permission_id).where(
            role_permissions.c.role_id == role_id
        )
        result = await self.db.execute(stmt)
        return [str(row) for (row,) in result.all()]
