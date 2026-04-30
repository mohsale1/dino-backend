"""
CategoryService — business logic for menu categories.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseService import BaseService
from src.repositories.CategoryRepository import CategoryRepository


class CategoryService(BaseService):
    """Service for managing menu categories."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.category_repo = CategoryRepository(db)
        super().__init__(self.category_repo)

    async def create_category(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new category."""
        return await self.category_repo.create(data)

    async def get_paginated_categories(
        self,
        workspace_id: int,
        persona_id: int,
        is_available: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated categories filtered by workspace and persona."""
        return await self.category_repo.get_paginated_by_workspace(
            workspace_id=workspace_id,
            persona_id=persona_id,
            is_available=is_available,
            page=page,
            page_size=page_size,
        )

    async def get_category_for_persona(
        self,
        category_id: int,
        workspace_id: int,
        persona_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Fetch a single category scoped to the given workspace and persona."""
        return await self.category_repo.get_by_id_for_persona(
            category_id, workspace_id, persona_id
        )

    async def update_category(
        self,
        category_id: int,
        workspace_id: int,
        persona_id: int,
        data: Dict[str, Any],
    ) -> bool:
        """Update a category, scoped to the given workspace and persona. Single DB round-trip."""
        return await self.category_repo.update_for_workspace(
            category_id, workspace_id, persona_id, data
        )

    async def soft_delete_category(
        self,
        category_id: int,
        workspace_id: int,
        persona_id: int,
    ) -> bool:
        """Soft-delete a category, scoped to the given workspace and persona. Single DB round-trip."""
        return await self.category_repo.soft_delete_for_workspace(
            category_id, workspace_id, persona_id
        )

    async def restore_category(
        self,
        category_id: int,
        workspace_id: int,
        persona_id: int,
    ) -> bool:
        """Restore a soft-deleted category, scoped to the given workspace and persona. Single DB round-trip."""
        return await self.category_repo.restore_for_workspace(
            category_id, workspace_id, persona_id
        )