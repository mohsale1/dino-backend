from typing import Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseService import BaseService
from src.repositories.PersonaRepository import PersonaRepository


class PersonaService(BaseService):
    """Persona service"""

    def __init__(self, db: AsyncSession):
        super().__init__(PersonaRepository(db))

    async def get_by_workspace(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get all personas in a workspace"""
        return await self.repository.get_by_workspace(workspace_id)
