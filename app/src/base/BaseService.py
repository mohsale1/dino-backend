"""
BaseService — thin async delegation layer over BaseRepository.

All methods are async and simply await the corresponding repository method,
keeping business-logic services free of direct database concerns.
"""

from typing import Any, Dict, List, Optional, Tuple

from src.base.BaseRepository import BaseRepository


class BaseService:
    """Async service base class. Concrete services extend this and inject a repository."""

    def __init__(self, repository: BaseRepository) -> None:
        self.repository = repository

    async def create(self, data: Dict[str, Any]) -> dict:
        """Create a new entity."""
        return await self.repository.create(data)

    async def get_by_id(
        self,
        entity_id: str,
        include_deleted: bool = False,
    ) -> Optional[dict]:
        """Retrieve an entity by primary key."""
        return await self.repository.get_by_id(entity_id, include_deleted)

    async def get_all(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        include_deleted: bool = False,
        order_by: str = "created_at",
        order_direction: str = "desc",
    ) -> List[dict]:
        """Retrieve all entities matching optional filters."""
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
        order_by: str = "created_at",
        order_direction: str = "desc",
    ) -> Tuple[List[dict], int, int]:
        """
        Retrieve a paginated slice of entities.

        Returns
        -------
        (items, total_count, total_pages)
        """
        return await self.repository.get_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            include_deleted=include_deleted,
            order_by=order_by,
            order_direction=order_direction,
        )

    async def update(self, entity_id: str, data: Dict[str, Any]) -> bool:
        """Update an entity by primary key."""
        return await self.repository.update(entity_id, data)

    async def soft_delete(self, entity_id: str) -> bool:
        """Soft-delete an entity (recommended over hard delete)."""
        return await self.repository.soft_delete(entity_id)

    async def restore(self, entity_id: str) -> bool:
        """Restore a soft-deleted entity."""
        return await self.repository.restore(entity_id)

    async def delete(self, entity_id: str) -> bool:
        """Hard-delete an entity."""
        return await self.repository.delete(entity_id)

    async def exists(
        self,
        field: str,
        value: Any,
        include_deleted: bool = False,
    ) -> bool:
        """Check whether an entity with the given field value exists."""
        return await self.repository.exists(field, value, include_deleted)

    async def count(
        self,
        filters: Optional[Dict[str, Any]] = None,
        include_deleted: bool = False,
    ) -> int:
        """Count entities matching optional filters."""
        return await self.repository.count(filters, include_deleted)

    async def bulk_create(self, items: List[Dict[str, Any]]) -> List[dict]:
        """Bulk-insert multiple entities."""
        return await self.repository.bulk_create(items)
