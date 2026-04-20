from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseRepository import BaseRepository
from src.models.Table import Table


class TableRepository(BaseRepository):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Table, db)

    async def get_by_workspace(self, workspace_id: str) -> List[Dict[str, Any]]:
        return await self.get_all(filters={"workspace_id": workspace_id})

    async def get_by_area(self, area_id: str) -> List[Dict[str, Any]]:
        return await self.get_all(filters={"area_id": area_id})

    async def get_paginated_by_workspace(
        self,
        workspace_id: str,
        page: int = 1,
        page_size: int = 10,
        area_id: Optional[str] = None,
        status: Optional[str] = None,
        order_by: str = "created_at",
        order_direction: str = "desc",
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        filters: Dict[str, Any] = {"workspace_id": workspace_id}
        if area_id is not None:
            filters["area_id"] = area_id
        if status is not None:
            filters["status"] = status
        return await self.get_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            order_by=order_by,
            order_direction=order_direction,
        )
