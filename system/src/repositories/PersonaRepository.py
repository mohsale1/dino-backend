"""
PersonaRepository — async SQLAlchemy 2.x repository for the Persona model.
"""

from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseRepository import BaseRepository
from src.models.Persona import Persona


class PersonaRepository(BaseRepository):
    """Repository for Persona entities."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Persona, db)

    async def get_by_workspace(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Return all active personas belonging to the given workspace."""
        return await self.get_all(filters={"workspace_id": workspace_id})
