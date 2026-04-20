"""
BaseService — async business-logic layer that delegates to BaseRepository.
"""

from typing import Any, Dict, List, Optional, Tuple

from src.base.BaseRepository import BaseRepository


class BaseService:
    """Base service with common async business logic."""

    def __init__(self, repository: BaseRepository) -> None:
        self.repository = repository

    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new entity."""
        return await self.repository.create(data)

    async def get_by_id(
        self, entity_id: Any, include_deleted: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get entity by primary key (excludes soft-deleted by default)."""
        return await self.repository.get_by_id(entity_id, include_deleted)

    async def get_all(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        include_deleted: bool = False,
        order_by: Optional[str] = None,
        order_direction: str = "asc",
    ) -> List[Dict[str, Any]]:
        """Get all entities (excludes soft-deleted by default)."""
        return await self.repository.get_all(
            filters=filters,
            limit=limit,
            include_deleted=include_deleted,
            order_by=order_by,
            order_direction=order_direction,
        )

    async def get_paginated(
        self,
        page: int = 1,
        page_size: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        include_deleted: bool = False,
        order_by: Optional[str] = None,
        order_direction: str = "asc",
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        Get paginated entities (excludes soft-deleted by default).
        Returns: (items, total_count, total_pages)
        """
        return await self.repository.get_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            include_deleted=include_deleted,
            order_by=order_by,
            order_direction=order_direction,
        )

    async def update(self, entity_id: Any, data: Dict[str, Any]) -> bool:
        """Update entity by primary key."""
        return await self.repository.update(entity_id, data)

    async def delete(self, entity_id: Any) -> bool:
        """Hard-delete entity (NOT RECOMMENDED — use soft_delete instead)."""
        return await self.repository.delete(entity_id)

    async def soft_delete(self, entity_id: Any) -> bool:
        """Soft-delete entity (RECOMMENDED)."""
        return await self.repository.soft_delete(entity_id)

    async def restore(self, entity_id: Any) -> bool:
        """Restore a soft-deleted entity."""
        return await self.repository.restore(entity_id)

    async def exists(
        self, field: str, value: Any, include_deleted: bool = False
    ) -> bool:
        """Check if an entity exists (excludes soft-deleted by default)."""
        return await self.repository.exists(field, value, include_deleted)

    async def count(
        self,
        filters: Optional[Dict[str, Any]] = None,
        include_deleted: bool = False,
    ) -> int:
        """Count entities (excludes soft-deleted by default)."""
        return await self.repository.count(filters, include_deleted)
