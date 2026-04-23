"""
PermissionService — manages permissions (category+resource+action model).
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseService import BaseService
from src.repositories.PermissionRepository import PermissionRepository


class PermissionService(BaseService):
    """Service for managing permissions."""

    def __init__(self, db: AsyncSession) -> None:
        self._perm_repo = PermissionRepository(db)
        super().__init__(self._perm_repo)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create_permission(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Check uniqueness (category+resource+action), then create."""
        exists = await self._perm_repo.permission_exists(
            data["category"], data["resource"], data["action"]
        )
        if exists:
            raise ValueError(
                f"Permission '{data['category']}:{data['resource']}:{data['action']}' already exists"
            )
        return await self.create(data)

    async def get_permission_by_id(
        self, permission_id: int, include_deleted: bool = False
    ) -> Optional[Dict[str, Any]]:
        return await self.get_by_id(permission_id, include_deleted)

    async def update_permission(self, permission_id: int, data: Dict[str, Any]) -> bool:
        return await self.update(permission_id, data)

    async def soft_delete_permission(self, permission_id: int) -> bool:
        return await self.soft_delete(permission_id)

    async def restore_permission(self, permission_id: int) -> bool:
        return await self.restore(permission_id)

    # ------------------------------------------------------------------
    # Existence
    # ------------------------------------------------------------------

    async def permission_exists(
        self,
        category: str,
        resource: str,
        action: str,
        exclude_id: Optional[int] = None,
    ) -> bool:
        return await self._perm_repo.permission_exists(category, resource, action, exclude_id)

    # ------------------------------------------------------------------
    # Paginated query
    # ------------------------------------------------------------------

    async def get_paginated_permissions(
        self,
        category: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        return await self._perm_repo.get_paginated_with_filters(
            page=page,
            page_size=page_size,
            category=category,
            resource=resource,
            action=action,
            is_active=is_active,
        )

    # ------------------------------------------------------------------
    # Bulk create
    # ------------------------------------------------------------------

    async def bulk_create_permissions(
        self, permissions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Bulk create permissions, skipping duplicates."""
        return await self._perm_repo.bulk_create_permissions(permissions)

    # ------------------------------------------------------------------
    # Distinct value helpers
    # ------------------------------------------------------------------

    async def get_categories(self) -> List[str]:
        return await self._perm_repo.get_categories()

    async def get_resources(self) -> List[str]:
        return await self._perm_repo.get_resources()
