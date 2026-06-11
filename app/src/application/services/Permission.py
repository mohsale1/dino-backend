"""
PermissionService — business logic for application permissions.
Read-only from the application side — permissions are managed by the system service.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.Exceptions import NotFoundError
from src.repositories.PermissionRepository import PermissionRepository

logger = logging.getLogger(__name__)


class PermissionService:
    """Service for reading application permissions."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = PermissionRepository(db)

    async def get_paginated(
        self,
        page: int = 1,
        page_size: int = 50,
        category: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated active permissions with optional filters."""
        logger.debug(
            "permission.list category=%s resource=%s action=%s search=%r page=%s page_size=%s",
            category, resource, action, search, page, page_size,
        )
        items, total, total_pages = await self.repo.get_paginated_with_filters(
            page=page,
            page_size=page_size,
            category=category,
            resource=resource,
            action=action,
            search_query=search,
        )
        logger.debug(
            "permission.list.result total=%s returned=%s page=%s",
            total, len(items), page,
        )
        return items, total, total_pages

    async def get_by_id(self, permission_id: int) -> Dict[str, Any]:
        """Fetch a single permission by ID.

        Raises
        ------
        NotFoundError
            If the permission does not exist or is inactive.
        """
        logger.debug("permission.get permission_id=%s", permission_id)
        permission = await self.repo.get_by_id(permission_id)
        if not permission:
            logger.warning("permission.get.not_found permission_id=%s", permission_id)
            raise NotFoundError("Permission not found")
        logger.debug(
            "permission.get.found permission_id=%s resource=%s action=%s",
            permission_id, permission.get("resource"), permission.get("action"),
        )
        return permission

    async def get_resources(self) -> List[str]:
        """Return distinct active resource names — for UI filter dropdowns."""
        resources = await self.repo.get_resources()
        logger.debug("permission.resources count=%s", len(resources))
        return resources

    async def get_actions(self) -> List[str]:
        """Return distinct active action names — for UI filter dropdowns."""
        actions = await self.repo.get_actions()
        logger.debug("permission.actions count=%s", len(actions))
        return actions
