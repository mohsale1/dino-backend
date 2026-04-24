from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.Role import Role


class RoleRepository(BaseRepository):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Role, db)

    async def get_by_type(self, role_type: int) -> List[Dict[str, Any]]:
        return await self.get_all(filters={"role_type": role_type})

    async def get_by_name_and_type(
        self, name: str, role_type: int
    ) -> Optional[Dict[str, Any]]:
        stmt = (
            select(Role)
            .where(
                Role.name == name,
                Role.role_type == role_type,
                Role.is_active.is_(True),  # noqa: E712
            )
            .limit(1)
        )
        result = await self.db.execute(stmt)
        row = result.scalars().first()
        return row_to_dict(row) if row is not None else None
