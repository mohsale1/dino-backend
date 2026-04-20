from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseRepository import BaseRepository
from src.models.Persona import Persona


class PersonaRepository(BaseRepository):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Persona, db)

    async def get_by_workspace(self, workspace_id: str) -> List[Dict[str, Any]]:
        return await self.get_all(filters={"workspace_id": workspace_id})
