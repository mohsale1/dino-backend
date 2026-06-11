"""
AreaService — business logic for dining areas.
Scoped by persona_id only (workspace_id removed from areas table).
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseService import BaseService
from src.core.Exceptions import BadRequestError, ConflictError
from src.repositories.AreaRepository import AreaRepository


class AreaService(BaseService):
    """Service for managing dining areas."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.area_repo = AreaRepository(db)
        super().__init__(self.area_repo)

    async def create_area(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new area scoped to a persona.

        Raises
        ------
        BadRequestError
            If persona_id is missing from data.
        ConflictError
            If an active area with the same name already exists for this persona.
        """
        persona_id = data.get("persona_id")
        if not persona_id:
            raise BadRequestError("persona_id is required to create an area")

        if await self.area_repo.name_exists_for_persona(data["name"], persona_id):
            raise ConflictError(
                f"An area named '{data['name']}' already exists for this persona"
            )

        data.setdefault("is_active", True)
        return await self.area_repo.create_area(data)

    async def get_all_areas(
        self,
        persona_id: int,
        is_available: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated active areas scoped to persona."""
        return await self.area_repo.get_all_by_persona(
            persona_id=persona_id,
            is_available=is_available,
            page=page,
            page_size=page_size,
        )

    async def get_area_for_persona(
        self,
        area_id: int,
        persona_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Fetch a single active area scoped to persona."""
        return await self.area_repo.get_by_id_for_persona(area_id, persona_id)

    async def update_area(
        self,
        area_id: int,
        persona_id: int,
        data: Dict[str, Any],
    ) -> bool:
        """Update an area scoped to persona.

        Raises
        ------
        ConflictError
            If the new name conflicts with another active area in the same persona.
        """
        if "name" in data:
            if await self.area_repo.name_exists_for_persona(
                data["name"], persona_id, exclude_id=area_id
            ):
                raise ConflictError(
                    f"An area named '{data['name']}' already exists for this persona"
                )

        return await self.area_repo.update_for_persona(area_id, persona_id, data)

    async def soft_delete_area(
        self,
        area_id: int,
        persona_id: int,
    ) -> bool:
        """Soft-delete an area scoped to persona."""
        return await self.area_repo.soft_delete_for_persona(area_id, persona_id)


    async def restore_area(
        self,
        area_id: int,
        persona_id: int,
    ) -> bool:
        """Restore a soft-deleted area scoped to persona."""
        return await self.area_repo.restore_for_persona(area_id, persona_id)
