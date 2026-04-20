from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseRepository import BaseRepository
from src.models.Workspace import Workspace


class WorkspaceRepository(BaseRepository):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Workspace, db)

    async def get_by_owner(self, owner_id: str) -> List[Dict[str, Any]]:
        return await self.get_all(filters={"owner_id": owner_id})
