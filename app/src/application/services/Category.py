"""
CategoryService — business logic for menu categories.
Scoped by persona_id only (workspace_id removed from categories table).
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseService import BaseService
from src.core.Exceptions import BadRequestError, ConflictError
from src.repositories.CategoryRepository import CategoryRepository


class CategoryService(BaseService):
    """Service for managing menu categories."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.category_repo = CategoryRepository(db)
        super().__init__(self.category_repo)

    async def create_category(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new category scoped to a persona.

        Raises
        ------
        BadRequestError
            If persona_id is missing.
        ConflictError
            If an active category with the same name already exists for this persona.
        """
        persona_id = data.get("persona_id")
        if not persona_id:
            raise BadRequestError("persona_id is required to create a category")

        if await self.category_repo.name_exists_for_persona(data["name"], persona_id):
            raise ConflictError(
                f"A category named '{data['name']}' already exists for this persona"
            )

        data.setdefault("is_active", True)
        return await self.category_repo.create_category(data)

    async def get_paginated_categories(
        self,
        persona_id: int,
        is_available: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated active categories scoped to persona."""
        return await self.category_repo.get_paginated_by_persona(
            persona_id=persona_id,
            is_available=is_available,
            page=page,
            page_size=page_size,
        )

    async def get_category_for_persona(
        self,
        category_id: int,
        persona_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Fetch a single active category scoped to persona."""
        return await self.category_repo.get_by_id_for_persona(category_id, persona_id)

    async def update_category(
        self,
        category_id: int,
        persona_id: int,
        data: Dict[str, Any],
    ) -> bool:
        """Update a category scoped to persona.

        Raises
        ------
        ConflictError
            If the new name conflicts with another active category in the same persona.
        """
        if "name" in data:
            if await self.category_repo.name_exists_for_persona(
                data["name"], persona_id, exclude_id=category_id
            ):
                raise ConflictError(
                    f"A category named '{data['name']}' already exists for this persona"
                )

        return await self.category_repo.update_for_persona(category_id, persona_id, data)

    async def soft_delete_category(
        self,
        category_id: int,
        persona_id: int,
    ) -> bool:
        """Soft-delete a category scoped to persona."""
        return await self.category_repo.soft_delete_for_persona(category_id, persona_id)

    async def restore_category(
        self,
        category_id: int,
        persona_id: int,
    ) -> bool:
        """Restore a soft-deleted category scoped to persona."""
        return await self.category_repo.restore_for_persona(category_id, persona_id)
