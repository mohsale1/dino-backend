"""
ItemService — business logic for menu items.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseService import BaseService
from src.repositories.ItemRepository import ItemRepository


class ItemService(BaseService):
    """Service for managing menu items."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.item_repo = ItemRepository(db)
        super().__init__(self.item_repo)

    async def create_item(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new menu item. Persona isolation is enforced via category_id.
        persona_id is used for scoping reads/writes but is not a column on Item."""
        data.pop("persona_id", None)  # not a column on Item — scoped via category_id
        data.setdefault("is_active", True)
        data.setdefault("is_available", True)
        return await self.item_repo.create(data)


    async def get_paginated_items(
        self,
        workspace_id: int,
        persona_id: int,
        category_id: Optional[int] = None,
        is_available: Optional[bool] = None,
        is_vegetarian: Optional[bool] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated items scoped to the given persona."""
        return await self.item_repo.get_paginated_by_workspace(
            workspace_id=workspace_id,
            persona_id=persona_id,
            page=page,
            page_size=page_size,
            category_id=category_id,
            is_available=is_available,
            is_vegetarian=is_vegetarian,
            search_query=search,
        )

    async def get_item_for_persona(
        self,
        item_id: int,
        workspace_id: int,
        persona_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Fetch a single active item that belongs to the given persona."""
        return await self.item_repo.get_by_id_for_persona(
            item_id, workspace_id, persona_id
        )

    async def update_item(
        self,
        item_id: int,
        workspace_id: int,
        persona_id: int,
        data: Dict[str, Any],
    ) -> bool:
        """Update an item scoped to the given persona."""
        return await self.item_repo.update_for_persona(
            item_id, workspace_id, persona_id, data
        )

    async def update_availability(
        self,
        item_id: int,
        workspace_id: int,
        persona_id: int,
        is_available: bool,
    ) -> bool:
        """Toggle the availability of an item scoped to the given persona."""
        return await self.item_repo.update_for_persona(
            item_id, workspace_id, persona_id, {"is_available": is_available}
        )

    async def soft_delete_item(
        self,
        item_id: int,
        workspace_id: int,
        persona_id: int,
    ) -> bool:
        """Soft-delete an item scoped to the given persona."""
        return await self.item_repo.soft_delete_for_persona(
            item_id, workspace_id, persona_id
        )

    async def restore_item(
        self,
        item_id: int,
        workspace_id: int,
        persona_id: int,
    ) -> bool:
        """Restore a soft-deleted item scoped to the given persona."""
        return await self.item_repo.restore_for_persona(
            item_id, workspace_id, persona_id
        )
