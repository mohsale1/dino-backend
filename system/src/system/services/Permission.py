from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseService import BaseService
from src.repositories.PermissionRepository import PermissionRepository


class PermissionService(BaseService):
    """Service for managing permissions."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(PermissionRepository(db))
        # Static in-memory definitions — no DB access required
        self.system_permissions = self._define_system_permissions()
        self.application_permissions = self._define_application_permissions()

    # ------------------------------------------------------------------
    # Static permission definitions (sync — no DB)
    # ------------------------------------------------------------------

    def _define_system_permissions(self) -> List[Dict[str, str]]:
        return [
            # Wildcard
            {"name": "system:*", "description": "Full system access (all permissions)", "category": "system", "resource": "system", "action": "*"},
            # Workspaces
            {"name": "system:workspaces:*", "description": "Full workspace management access", "category": "system", "resource": "workspaces", "action": "*"},
            {"name": "system:workspaces:read", "description": "View workspace details", "category": "system", "resource": "workspaces", "action": "read"},
            {"name": "system:workspaces:create", "description": "Create new workspaces", "category": "system", "resource": "workspaces", "action": "create"},
            {"name": "system:workspaces:update", "description": "Update workspace details", "category": "system", "resource": "workspaces", "action": "update"},
            {"name": "system:workspaces:delete", "description": "Delete workspaces", "category": "system", "resource": "workspaces", "action": "delete"},
            # Billing
            {"name": "system:billing:*", "description": "Full billing management access", "category": "system", "resource": "billing", "action": "*"},
            {"name": "system:billing:read", "description": "View billing information", "category": "system", "resource": "billing", "action": "read"},
            {"name": "system:billing:update", "description": "Update billing information", "category": "system", "resource": "billing", "action": "update"},
            {"name": "system:billing:subscription", "description": "Manage subscriptions", "category": "system", "resource": "billing", "action": "manage"},
            # Roles
            {"name": "system:roles:*", "description": "Full role management access", "category": "system", "resource": "roles", "action": "*"},
            {"name": "system:roles:read", "description": "View roles", "category": "system", "resource": "roles", "action": "read"},
            {"name": "system:roles:create", "description": "Create new roles", "category": "system", "resource": "roles", "action": "create"},
            {"name": "system:roles:update", "description": "Update roles", "category": "system", "resource": "roles", "action": "update"},
            {"name": "system:roles:delete", "description": "Delete roles", "category": "system", "resource": "roles", "action": "delete"},
            # Users
            {"name": "system:users:*", "description": "Full user management access", "category": "system", "resource": "users", "action": "*"},
            {"name": "system:users:read", "description": "View system users", "category": "system", "resource": "users", "action": "read"},
            {"name": "system:users:create", "description": "Create system users", "category": "system", "resource": "users", "action": "create"},
            {"name": "system:users:update", "description": "Update system users", "category": "system", "resource": "users", "action": "update"},
            {"name": "system:users:delete", "description": "Delete system users", "category": "system", "resource": "users", "action": "delete"},
            # Permissions
            {"name": "system:permissions:*", "description": "Full permission management access", "category": "system", "resource": "permissions", "action": "*"},
            {"name": "system:permissions:read", "description": "View permissions", "category": "system", "resource": "permissions", "action": "read"},
            {"name": "system:permissions:create", "description": "Create permissions", "category": "system", "resource": "permissions", "action": "create"},
            {"name": "system:permissions:update", "description": "Update permissions", "category": "system", "resource": "permissions", "action": "update"},
            {"name": "system:permissions:delete", "description": "Delete permissions", "category": "system", "resource": "permissions", "action": "delete"},
        ]

    def _define_application_permissions(self) -> List[Dict[str, str]]:
        return [
            # Workspace
            {"name": "workspace:*", "description": "Full workspace access (all permissions)", "category": "application", "resource": "workspace", "action": "*"},
            {"name": "workspace:read", "description": "View workspace details", "category": "application", "resource": "workspace", "action": "read"},
            {"name": "workspace:update", "description": "Update workspace settings", "category": "application", "resource": "workspace", "action": "update"},
            {"name": "workspace:manage", "description": "Manage workspace configuration", "category": "application", "resource": "workspace", "action": "manage"},
            # Persona
            {"name": "persona:*", "description": "Full persona management access", "category": "application", "resource": "persona", "action": "*"},
            {"name": "persona:read", "description": "View persona details", "category": "application", "resource": "persona", "action": "read"},
            {"name": "persona:create", "description": "Create new personas", "category": "application", "resource": "persona", "action": "create"},
            {"name": "persona:update", "description": "Update persona details", "category": "application", "resource": "persona", "action": "update"},
            {"name": "persona:delete", "description": "Delete personas", "category": "application", "resource": "persona", "action": "delete"},
            # Items
            {"name": "items:*", "description": "Full item management access", "category": "application", "resource": "items", "action": "*"},
            {"name": "items:read", "description": "View items", "category": "application", "resource": "items", "action": "read"},
            {"name": "items:create", "description": "Create new items", "category": "application", "resource": "items", "action": "create"},
            {"name": "items:update", "description": "Update items", "category": "application", "resource": "items", "action": "update"},
            {"name": "items:delete", "description": "Delete items", "category": "application", "resource": "items", "action": "delete"},
            # Categories
            {"name": "categories:*", "description": "Full category management access", "category": "application", "resource": "categories", "action": "*"},
            {"name": "categories:read", "description": "View categories", "category": "application", "resource": "categories", "action": "read"},
            {"name": "categories:create", "description": "Create new categories", "category": "application", "resource": "categories", "action": "create"},
            {"name": "categories:update", "description": "Update categories", "category": "application", "resource": "categories", "action": "update"},
            {"name": "categories:delete", "description": "Delete categories", "category": "application", "resource": "categories", "action": "delete"},
            # Areas
            {"name": "areas:*", "description": "Full area management access", "category": "application", "resource": "areas", "action": "*"},
            {"name": "areas:read", "description": "View areas", "category": "application", "resource": "areas", "action": "read"},
            {"name": "areas:create", "description": "Create new areas", "category": "application", "resource": "areas", "action": "create"},
            {"name": "areas:update", "description": "Update areas", "category": "application", "resource": "areas", "action": "update"},
            {"name": "areas:delete", "description": "Delete areas", "category": "application", "resource": "areas", "action": "delete"},
            # Tables
            {"name": "tables:*", "description": "Full table management access", "category": "application", "resource": "tables", "action": "*"},
            {"name": "tables:read", "description": "View tables", "category": "application", "resource": "tables", "action": "read"},
            {"name": "tables:create", "description": "Create new tables", "category": "application", "resource": "tables", "action": "create"},
            {"name": "tables:update", "description": "Update tables", "category": "application", "resource": "tables", "action": "update"},
            {"name": "tables:delete", "description": "Delete tables", "category": "application", "resource": "tables", "action": "delete"},
            # Reviews
            {"name": "reviews:*", "description": "Full review management access", "category": "application", "resource": "reviews", "action": "*"},
            {"name": "reviews:read", "description": "View reviews", "category": "application", "resource": "reviews", "action": "read"},
            {"name": "reviews:create", "description": "Create new reviews", "category": "application", "resource": "reviews", "action": "create"},
            {"name": "reviews:update", "description": "Update reviews", "category": "application", "resource": "reviews", "action": "update"},
            {"name": "reviews:delete", "description": "Delete reviews", "category": "application", "resource": "reviews", "action": "delete"},
            {"name": "reviews:moderate", "description": "Moderate reviews (approve/reject)", "category": "application", "resource": "reviews", "action": "manage"},
            # Orders
            {"name": "orders:*", "description": "Full order management access", "category": "application", "resource": "orders", "action": "*"},
            {"name": "orders:read", "description": "View orders", "category": "application", "resource": "orders", "action": "read"},
            {"name": "orders:create", "description": "Create new orders", "category": "application", "resource": "orders", "action": "create"},
            {"name": "orders:update", "description": "Update orders", "category": "application", "resource": "orders", "action": "update"},
            {"name": "orders:delete", "description": "Delete orders", "category": "application", "resource": "orders", "action": "delete"},
            {"name": "orders:status", "description": "Update order status", "category": "application", "resource": "orders", "action": "manage"},
            {"name": "orders:payment", "description": "Update payment status", "category": "application", "resource": "orders", "action": "manage"},
            # Users (application)
            {"name": "users:*", "description": "Full user management access", "category": "application", "resource": "users", "action": "*"},
            {"name": "users:read", "description": "View users", "category": "application", "resource": "users", "action": "read"},
            {"name": "users:create", "description": "Create new users", "category": "application", "resource": "users", "action": "create"},
            {"name": "users:update", "description": "Update users", "category": "application", "resource": "users", "action": "update"},
            {"name": "users:delete", "description": "Delete users", "category": "application", "resource": "users", "action": "delete"},
            # Dashboard
            {"name": "dashboard:*", "description": "Full dashboard access", "category": "application", "resource": "dashboard", "action": "*"},
            {"name": "dashboard:read", "description": "View dashboard and analytics", "category": "application", "resource": "dashboard", "action": "read"},
        ]

    # ------------------------------------------------------------------
    # Static helpers (sync — no DB)
    # ------------------------------------------------------------------

    def validate_permissions(self, permissions: List[str]) -> Dict[str, Any]:
        """Validate whether the supplied permission names are known."""
        all_names = {p["name"] for p in self.system_permissions + self.application_permissions}
        valid, invalid = [], []
        for perm in permissions:
            if perm in all_names or perm.endswith(":*"):
                valid.append(perm)
            else:
                invalid.append(perm)
        return {"valid": valid, "invalid": invalid, "is_valid": len(invalid) == 0}

    def get_all_available_permissions(self) -> Dict[str, List[Dict[str, str]]]:
        """Return all static permission definitions grouped by category."""
        return {
            "system": self.system_permissions,
            "application": self.application_permissions,
        }

    def get_permission_categories(self) -> List[str]:
        return ["system", "application"]

    def get_permission_templates(self) -> Dict[str, Any]:
        """Return permission templates for predefined roles."""
        return {
            "system_roles": {
                "SuperAdmin": {
                    "role_type": 0,
                    "description": "Full system access, role and permission management",
                    "permissions": ["system:*"],
                },
                "BillingManager": {
                    "role_type": 0,
                    "description": "Billing and workspace financial details",
                    "permissions": ["system:billing:*", "system:workspaces:read"],
                },
            },
            "application_roles": {
                "Owner": {
                    "role_type": 1,
                    "description": "Workspace owner with full access to all resources",
                    "permissions": ["workspace:*"],
                },
                "Admin": {
                    "role_type": 1,
                    "description": "Administrator with full management access except workspace settings",
                    "permissions": [
                        "dashboard:*", "items:*", "categories:*", "areas:*", "tables:*",
                        "orders:*", "reviews:*", "users:read", "users:update",
                        "persona:read", "workspace:read",
                    ],
                },
                "Operator": {
                    "role_type": 1,
                    "description": "Operator with limited access to orders and items",
                    "permissions": [
                        "dashboard:read", "items:read", "categories:read", "areas:read",
                        "tables:read", "orders:read", "orders:update", "orders:status",
                        "reviews:read", "persona:read", "workspace:read",
                    ],
                },
            },
        }

    # ------------------------------------------------------------------
    # Async CRUD
    # ------------------------------------------------------------------

    async def create_permission(self, data: Dict[str, Any]):
        result = await self.create(data)
        return result.get("id") if isinstance(result, dict) else result

    async def get_permission_by_id(self, permission_id, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
        return await self.get_by_id(permission_id, include_deleted)

    async def get_permission_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        return await self.repository.get_by_name(name)

    async def update_permission(self, permission_id, data: Dict[str, Any]):
        return await self.update(permission_id, data)

    async def soft_delete_permission(self, permission_id):
        return await self.soft_delete(permission_id)

    async def restore_permission(self, permission_id):
        return await self.restore(permission_id)

    async def permission_exists(self, name: str, exclude_id: Optional[str] = None) -> bool:
        return await self.repository.permission_exists(name, exclude_id)

    async def get_all_permissions(self) -> List[Dict[str, Any]]:
        return await self.get_all()

    async def get_paginated_permissions(
        self,
        page: int = 1,
        page_size: int = 10,
        category: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        is_active: Optional[bool] = None,
        search_query: Optional[str] = None,
        order_by: str = "created_at",
        order_direction: str = "desc",
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return (items, total, total_pages) with optional filtering and pagination."""
        items, total = await self.repository.get_paginated_with_filters(
            page=page,
            page_size=page_size,
            category=category,
            resource=resource,
            action=action,
            is_active=is_active,
            search_query=search_query,
            order_by=order_by,
            order_direction=order_direction,
        )
        total_pages = max(1, (total + page_size - 1) // page_size)
        return items, total, total_pages

    async def get_permissions_by_category(self, category: str) -> List[Dict[str, Any]]:
        return await self.repository.get_by_category(category)

    async def get_permissions_by_resource(self, resource: str) -> List[Dict[str, Any]]:
        return await self.repository.get_by_resource(resource)

    async def search_permissions(self, query: str) -> List[Dict[str, Any]]:
        items, _, _ = await self.get_paginated_permissions(
            page=1, page_size=1000, search_query=query
        )
        return items

    async def bulk_create_permissions(self, permissions: List[Dict[str, Any]]) -> List[str]:
        """Bulk create permissions and return list of IDs."""
        results = await self.repository.bulk_create_permissions(permissions)
        ids = []
        for r in results:
            if isinstance(r, dict):
                ids.append(r.get("id"))
            else:
                ids.append(str(r))
        return ids

    async def get_categories(self) -> List[str]:
        return await self.repository.get_categories()

    async def get_resources(self) -> List[str]:
        return await self.repository.get_resources()

    async def get_actions(self) -> List[str]:
        return await self.repository.get_actions()
