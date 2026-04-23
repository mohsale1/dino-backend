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
        data.setdefault("is_active", True)
        return await self.category_repo.create(data)

    async def get_paginated_categories(
        self,
        workspace_id: int,
        persona_id: Optional[int] = None,
        is_available: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated categories with optional filters."""
        return await self.category_repo.get_paginated_by_workspace(
            workspace_id=workspace_id,
            persona_id=persona_id,
            is_available=is_available,
            page=page,
            page_size=page_size,
        )

    async def update_category(self, category_id: int, data: Dict[str, Any]) -> bool:
        """Update a category by ID."""
        return await self.category_repo.update(category_id, data)

    async def soft_delete_category(self, category_id: int) -> bool:
        """Soft-delete a category."""
        return await self.category_repo.soft_delete(category_id)

    async def restore_category(self, category_id: int) -> bool:
        """Restore a soft-deleted category."""
        return await self.category_repo.restore(category_id)
