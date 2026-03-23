
from typing import List, Dict, Any, Optional, Tuple
from src.base.BaseService import BaseService
from src.repositories.PermissionRepository import PermissionRepository

class PermissionService(BaseService):
    """Permission management service"""
    
    def __init__(self):
        repository = PermissionRepository()
        super().__init__(repository)
        self.system_permissions = self._define_system_permissions()
        self.application_permissions = self._define_application_permissions()
    
    def _define_system_permissions(self) -> List[Dict[str, str]]:
        """Define all system permissions"""
        return [
            # Wildcard
            {
                "name": "system:*",
                "description": "Full system access (all permissions)",
                "category": "system",
                "resource": "system",
                "action": "*"
            },
            
            # Workspace permissions
            {
                "name": "system:workspaces:*",
                "description": "Full workspace management access",
                "category": "system",
                "resource": "workspaces",
                "action": "*"
            },
            {
                "name": "system:workspaces:read",
                "description": "View workspace details",
                "category": "system",
                "resource": "workspaces",
                "action": "read"
            },
            {
                "name": "system:workspaces:create",
                "description": "Create new workspaces",
                "category": "system",
                "resource": "workspaces",
                "action": "create"
            },
            {
                "name": "system:workspaces:update",
                "description": "Update workspace details",
                "category": "system",
                "resource": "workspaces",
                "action": "update"
            },
            {
                "name": "system:workspaces:delete",
                "description": "Delete workspaces",
                "category": "system",
                "resource": "workspaces",
                "action": "delete"
            },
            
            # Billing permissions
            {
                "name": "system:billing:*",
                "description": "Full billing management access",
                "category": "system",
                "resource": "billing",
                "action": "*"
            },
            {
                "name": "system:billing:read",
                "description": "View billing information",
                "category": "system",
                "resource": "billing",
                "action": "read"
            },
            {
                "name": "system:billing:update",
                "description": "Update billing information",
                "category": "system",
                "resource": "billing",
                "action": "update"
            },
            {
                "name": "system:billing:subscription",
                "description": "Manage subscriptions",
                "category": "system",
                "resource": "billing",
                "action": "manage"
            },
            
            # Registration permissions
            {
                "name": "system:registration:*",
                "description": "Full registration code management",
                "category": "system",
                "resource": "registration",
                "action": "*"
            },
            {
                "name": "system:registration:read",
                "description": "View registration codes",
                "category": "system",
                "resource": "registration",
                "action": "read"
            },
            {
                "name": "system:registration:create",
                "description": "Create registration codes",
                "category": "system",
                "resource": "registration",
                "action": "create"
            },
            {
                "name": "system:registration:delete",
                "description": "Delete registration codes",
                "category": "system",
                "resource": "registration",
                "action": "delete"
            },
            
            # Role permissions
            {
                "name": "system:roles:*",
                "description": "Full role management access",
                "category": "system",
                "resource": "roles",
                "action": "*"
            },
            {
                "name": "system:roles:read",
                "description": "View roles",
                "category": "system",
                "resource": "roles",
                "action": "read"
            },
            {
                "name": "system:roles:create",
                "description": "Create new roles",
                "category": "system",
                "resource": "roles",
                "action": "create"
            },
            {
                "name": "system:roles:update",
                "description": "Update roles",
                "category": "system",
                "resource": "roles",
                "action": "update"
            },
            {
                "name": "system:roles:delete",
                "description": "Delete roles",
                "category": "system",
                "resource": "roles",
                "action": "delete"
            },
            
            # User permissions
            {
                "name": "system:users:*",
                "description": "Full user management access",
                "category": "system",
                "resource": "users",
                "action": "*"
            },
            {
                "name": "system:users:read",
                "description": "View system users",
                "category": "system",
                "resource": "users",
                "action": "read"
            },
            {
                "name": "system:users:create",
                "description": "Create system users",
                "category": "system",
                "resource": "users",
                "action": "create"
            },
            {
                "name": "system:users:update",
                "description": "Update system users",
                "category": "system",
                "resource": "users",
                "action": "update"
            },
            {
                "name": "system:users:delete",
                "description": "Delete system users",
                "category": "system",
                "resource": "users",
                "action": "delete"
            },
            
            # Permission permissions
            {
                "name": "system:permissions:*",
                "description": "Full permission management access",
                "category": "system",
                "resource": "permissions",
                "action": "*"
            },
            {
                "name": "system:permissions:read",
                "description": "View permissions",
                "category": "system",
                "resource": "permissions",
                "action": "read"
            },
            {
                "name": "system:permissions:create",
                "description": "Create permissions",
                "category": "system",
                "resource": "permissions",
                "action": "create"
            },
            {
                "name": "system:permissions:update",
                "description": "Update permissions",
                "category": "system",
                "resource": "permissions",
                "action": "update"
            },
            {
                "name": "system:permissions:delete",
                "description": "Delete permissions",
                "category": "system",
                "resource": "permissions",
                "action": "delete"
            }
        ]
    
    def _define_application_permissions(self) -> List[Dict[str, str]]:
        """Define all application permissions"""
        return [
            # Wildcard
            {
                "name": "workspace:*",
                "description": "Full workspace access (all permissions)",
                "category": "application",
                "resource": "workspace",
                "action": "*"
            },
            
            # Workspace permissions
            {
                "name": "workspace:read",
                "description": "View workspace details",
                "category": "application",
                "resource": "workspace",
                "action": "read"
            },
            {
                "name": "workspace:update",
                "description": "Update workspace settings",
                "category": "application",
                "resource": "workspace",
                "action": "update"
            },
            {
                "name": "workspace:manage",
                "description": "Manage workspace configuration",
                "category": "application",
                "resource": "workspace",
                "action": "manage"
            },
            
            # Organization permissions
            {
                "name": "organization:*",
                "description": "Full organization management access",
                "category": "application",
                "resource": "organization",
                "action": "*"
            },
            {
                "name": "organization:read",
                "description": "View organization details",
                "category": "application",
                "resource": "organization",
                "action": "read"
            },
            {
                "name": "organization:create",
                "description": "Create new organizations",
                "category": "application",
                "resource": "organization",
                "action": "create"
            },
            {
                "name": "organization:update",
                "description": "Update organization details",
                "category": "application",
                "resource": "organization",
                "action": "update"
            },
            {
                "name": "organization:delete",
                "description": "Delete organizations",
                "category": "application",
                "resource": "organization",
                "action": "delete"
            },
            
            # Item permissions (menu items)
            {
                "name": "items:*",
                "description": "Full item management access",
                "category": "application",
                "resource": "items",
                "action": "*"
            },
            {
                "name": "items:read",
                "description": "View items",
                "category": "application",
                "resource": "items",
                "action": "read"
            },
            {
                "name": "items:create",
                "description": "Create new items",
                "category": "application",
                "resource": "items",
                "action": "create"
            },
            {
                "name": "items:update",
                "description": "Update items",
                "category": "application",
                "resource": "items",
                "action": "update"
            },
            {
                "name": "items:delete",
                "description": "Delete items",
                "category": "application",
                "resource": "items",
                "action": "delete"
            },
            
            # Category permissions
            {
                "name": "categories:*",
                "description": "Full category management access",
                "category": "application",
                "resource": "categories",
                "action": "*"
            },
            {
                "name": "categories:read",
                "description": "View categories",
                "category": "application",
                "resource": "categories",
                "action": "read"
            },
            {
                "name": "categories:create",
                "description": "Create new categories",
                "category": "application",
                "resource": "categories",
                "action": "create"
            },
            {
                "name": "categories:update",
                "description": "Update categories",
                "category": "application",
                "resource": "categories",
                "action": "update"
            },
            {
                "name": "categories:delete",
                "description": "Delete categories",
                "category": "application",
                "resource": "categories",
                "action": "delete"
            },
            
            # Area permissions (service areas)
            {
                "name": "areas:*",
                "description": "Full area management access",
                "category": "application",
                "resource": "areas",
                "action": "*"
            },
            {
                "name": "areas:read",
                "description": "View areas",
                "category": "application",
                "resource": "areas",
                "action": "read"
            },
            {
                "name": "areas:create",
                "description": "Create new areas",
                "category": "application",
                "resource": "areas",
                "action": "create"
            },
            {
                "name": "areas:update",
                "description": "Update areas",
                "category": "application",
                "resource": "areas",
                "action": "update"
            },
            {
                "name": "areas:delete",
                "description": "Delete areas",
                "category": "application",
                "resource": "areas",
                "action": "delete"
            },
            
            # Table permissions
            {
                "name": "tables:*",
                "description": "Full table management access",
                "category": "application",
                "resource": "tables",
                "action": "*"
            },
            {
                "name": "tables:read",
                "description": "View tables",
                "category": "application",
                "resource": "tables",
                "action": "read"
            },
            {
                "name": "tables:create",
                "description": "Create new tables",
                "category": "application",
                "resource": "tables",
                "action": "create"
            },
            {
                "name": "tables:update",
                "description": "Update tables",
                "category": "application",
                "resource": "tables",
                "action": "update"
            },
            {
                "name": "tables:delete",
                "description": "Delete tables",
                "category": "application",
                "resource": "tables",
                "action": "delete"
            },
            
            # Review permissions
            {
                "name": "reviews:*",
                "description": "Full review management access",
                "category": "application",
                "resource": "reviews",
                "action": "*"
            },
            {
                "name": "reviews:read",
                "description": "View reviews",
                "category": "application",
                "resource": "reviews",
                "action": "read"
            },
            {
                "name": "reviews:create",
                "description": "Create new reviews",
                "category": "application",
                "resource": "reviews",
                "action": "create"
            },
            {
                "name": "reviews:update",
                "description": "Update reviews",
                "category": "application",
                "resource": "reviews",
                "action": "update"
            },
            {
                "name": "reviews:delete",
                "description": "Delete reviews",
                "category": "application",
                "resource": "reviews",
                "action": "delete"
            },
            {
                "name": "reviews:moderate",
                "description": "Moderate reviews (approve/reject)",
                "category": "application",
                "resource": "reviews",
                "action": "manage"
            },
            
            # Order permissions
            {
                "name": "orders:*",
                "description": "Full order management access",
                "category": "application",
                "resource": "orders",
                "action": "*"
            },
            {
                "name": "orders:read",
                "description": "View orders",
                "category": "application",
                "resource": "orders",
                "action": "read"
            },
            {
                "name": "orders:create",
                "description": "Create new orders",
                "category": "application",
                "resource": "orders",
                "action": "create"
            },
            {
                "name": "orders:update",
                "description": "Update orders",
                "category": "application",
                "resource": "orders",
                "action": "update"
            },
            {
                "name": "orders:delete",
                "description": "Delete orders",
                "category": "application",
                "resource": "orders",
                "action": "delete"
            },
            {
                "name": "orders:status",
                "description": "Update order status",
                "category": "application",
                "resource": "orders",
                "action": "manage"
            },
            {
                "name": "orders:payment",
                "description": "Update payment status",
                "category": "application",
                "resource": "orders",
                "action": "manage"
            },
            
            # User permissions (application users)
            {
                "name": "users:*",
                "description": "Full user management access",
                "category": "application",
                "resource": "users",
                "action": "*"
            },
            {
                "name": "users:read",
                "description": "View users",
                "category": "application",
                "resource": "users",
                "action": "read"
            },
            {
                "name": "users:create",
                "description": "Create new users",
                "category": "application",
                "resource": "users",
                "action": "create"
            },
            {
                "name": "users:update",
                "description": "Update users",
                "category": "application",
                "resource": "users",
                "action": "update"
            },
            {
                "name": "users:delete",
                "description": "Delete users",
                "category": "application",
                "resource": "users",
                "action": "delete"
            },
            
            # Dashboard permissions
            {
                "name": "dashboard:*",
                "description": "Full dashboard access",
                "category": "application",
                "resource": "dashboard",
                "action": "*"
            },
            {
                "name": "dashboard:read",
                "description": "View dashboard and analytics",
                "category": "application",
                "resource": "dashboard",
                "action": "read"
            }
        ]
    
    # CRUD Operations
    
    def create_permission(self, data: Dict[str, Any]) -> str:
        """Create new permission"""
        result = self.create(data)
        # BaseRepository.create returns the full document with 'id' field
        if isinstance(result, dict):
            return result.get('id')
        return result
    
    def get_permission_by_id(self, permission_id: str, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
        """Get permission by ID"""
        return self.get_by_id(permission_id, include_deleted)
    
    def get_permission_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get permission by name"""
        return self.repository.get_by_name(name)
    
    def update_permission(self, permission_id: str, data: Dict[str, Any]) -> bool:
        """Update permission"""
        return self.update(permission_id, data)
    
    def soft_delete_permission(self, permission_id: str) -> bool:
        """Soft delete permission"""
        return self.soft_delete(permission_id)
    
    def restore_permission(self, permission_id: str) -> bool:
        """Restore a soft-deleted permission"""
        return self.restore(permission_id)
    
    def permission_exists(self, name: str, exclude_id: Optional[str] = None) -> bool:
        """Check if permission exists with given name"""
        return self.repository.permission_exists(name, exclude_id)
    
    # Query Operations
    
    def get_all_permissions(self) -> List[Dict[str, Any]]:
        """Get all permissions"""
        return self.get_all()
    
    def get_paginated_permissions(
        self,
        page: int = 1,
        page_size: int = 10,
        category: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        is_active: Optional[bool] = None,
        search_query: Optional[str] = None,
        order_by: str = "created_at",
        order_direction: str = "desc"
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Get paginated permissions with filters"""
        return self.repository.get_paginated_with_filters(
            page=page,
            page_size=page_size,
            category=category,
            resource=resource,
            action=action,
            is_active=is_active,
            search_query=search_query,
            order_by=order_by,
            order_direction=order_direction
        )
    
    def get_permissions_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get permissions by category"""
        return self.repository.get_by_category(category)
    
    def get_permissions_by_resource(self, resource: str) -> List[Dict[str, Any]]:
        """Get permissions by resource"""
        return self.repository.get_by_resource(resource)
    
    def search_permissions(self, query: str) -> List[Dict[str, Any]]:
        """Search permissions"""
        return self.repository.search(query)
    
    # Bulk Operations
    
    def bulk_create_permissions(self, permissions: List[Dict[str, Any]]) -> List[str]:
        """Bulk create permissions"""
        return self.repository.bulk_create(permissions)
    
    # Metadata Operations
    
    def get_categories(self) -> List[str]:
        """Get all distinct categories"""
        return self.repository.get_categories()
    
    def get_resources(self) -> List[str]:
        """Get all distinct resources"""
        return self.repository.get_resources()
    
    def get_actions(self) -> List[str]:
        """Get all distinct actions"""
        return self.repository.get_actions()
    
    # Legacy/Compatibility Methods
    
    def get_all_available_permissions(self) -> Dict[str, List[Dict[str, str]]]:
        """Get all available permissions grouped by category"""
        return {
            "system": self.system_permissions,
            "application": self.application_permissions
        }
    
    def get_permission_categories(self) -> List[str]:
        """Get all permission categories"""
        return ["system", "application"]
    
    def validate_permissions(self, permissions: List[str]) -> Dict[str, Any]:
        """Validate if permissions are valid"""
        all_permissions = [p['name'] for p in self.system_permissions + self.application_permissions]
        
        valid_permissions = []
        invalid_permissions = []
        
        for permission in permissions:
            if permission in all_permissions or permission.endswith(':*'):
                valid_permissions.append(permission)
            else:
                invalid_permissions.append(permission)
        
        return {
            "valid": valid_permissions,
            "invalid": invalid_permissions,
            "is_valid": len(invalid_permissions) == 0
        }
    
    def get_permission_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get permission templates for predefined roles"""
        return {
            "system_roles": {
                "SuperAdmin": {
                    "role_type": 0,
                    "description": "Full system access, role and permission management",
                    "permissions": ["system:*"]
                },
                "BillingManager": {
                    "role_type": 0,
                    "description": "Billing and workspace financial details",
                    "permissions": [
                        "system:billing:*",
                        "system:workspaces:read"
                    ]
                },
                "MarketingAgent": {
                    "role_type": 0,
                    "description": "Registration code management",
                    "permissions": [
                        "system:registration:*"
                    ]
                }
            },
            "application_roles": {
                "Owner": {
                    "role_type": 1,
                    "description": "Workspace owner with full access to all resources",
                    "permissions": ["workspace:*"]
                },
                "Admin": {
                    "role_type": 1,
                    "description": "Administrator with full management access except workspace settings",
                    "permissions": [
                        "dashboard:*",
                        "items:*",
                        "categories:*",
                        "areas:*",
                        "tables:*",
                        "orders:*",
                        "reviews:*",
                        "users:read",
                        "users:update",
                        "organization:read",
                        "workspace:read"
                    ]
                },
                "Operator": {
                    "role_type": 1,
                    "description": "Operator with limited access to orders and items",
                    "permissions": [
                        "dashboard:read",
                        "items:read",
                        "categories:read",
                        "areas:read",
                        "tables:read",
                        "orders:read",
                        "orders:update",
                        "orders:status",
                        "reviews:read",
                        "organization:read",
                        "workspace:read"
                    ]
                }
            }
        }