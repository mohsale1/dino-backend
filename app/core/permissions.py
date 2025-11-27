"""
Unified Permission Utilities
Centralized permission and role checking logic
"""
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, status

from app.core.logging import get_logger

logger = get_logger(__name__)


class PermissionChecker:
    """Centralized permission checking utilities"""
    
    @staticmethod
    async def validate_user_role(
        current_user: Dict[str, Any],
        required_roles: List[str],
        error_message: str = "Insufficient permissions"
    ) -> str:
        """
        Validate that user has one of the required roles
        
        Args:
            current_user: Current user data
            required_roles: List of roles that are allowed
            error_message: Custom error message
            
        Returns:
            str: User's role
            
        Raises:
            HTTPException: If user doesn't have required role
        """
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        from app.core.security import _get_user_role
        user_role = await _get_user_role(current_user)
        
        if user_role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error_message
            )
        
        return user_role
    
    @staticmethod
    async def validate_admin_or_superadmin(current_user: Dict[str, Any]) -> str:
        """Validate that user is admin or superadmin"""
        return await PermissionChecker.validate_user_role(
            current_user,
            ["admin", "superadmin"],
            "Admin or superadmin role required"
        )
    
    @staticmethod
    async def validate_superadmin(current_user: Dict[str, Any]) -> str:
        """Validate that user is superadmin"""
        return await PermissionChecker.validate_user_role(
            current_user,
            ["superadmin"],
            "Superadmin role required"
        )
    
    @staticmethod
    async def check_resource_access(
        current_user: Dict[str, Any],
        resource: Dict[str, Any],
        resource_type: str = "resource"
    ) -> bool:
        """
        Check if user has access to a resource
        
        Args:
            current_user: Current user data
            resource: Resource to check access for
            resource_type: Type of resource (for error messages)
            
        Returns:
            bool: True if user has access
            
        Raises:
            HTTPException: If user doesn't have access
        """
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        from app.core.security import _get_user_role
        user_role = await _get_user_role(current_user)
        
        # Admin and superadmin have access to all resources
        if user_role in ['admin', 'superadmin']:
            return True
        
        # Check workspace isolation
        resource_workspace_id = resource.get('workspace_id')
        user_workspace_id = current_user.get('workspace_id')
        
        if resource_workspace_id and user_workspace_id != resource_workspace_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: {resource_type} not in your workspace"
            )
        
        return True
    
    @staticmethod
    async def check_ownership(
        current_user: Dict[str, Any],
        resource: Dict[str, Any],
        owner_field: str = 'owner_id'
    ) -> bool:
        """
        Check if user owns the resource
        
        Args:
            current_user: Current user data
            resource: Resource to check ownership for
            owner_field: Field name containing owner ID
            
        Returns:
            bool: True if user owns the resource or is admin
        """
        if not current_user:
            return False
        
        from app.core.security import _get_user_role
        user_role = await _get_user_role(current_user)
        
        # Admin and superadmin can access all resources
        if user_role in ['admin', 'superadmin']:
            return True
        
        # Check ownership
        return resource.get(owner_field) == current_user.get('id')
    
    @staticmethod
    def filter_by_workspace(
        items: List[Dict[str, Any]],
        workspace_id: Optional[str],
        user_role: str
    ) -> List[Dict[str, Any]]:
        """
        Filter items by workspace for non-admin users
        
        Args:
            items: List of items to filter
            workspace_id: User's workspace ID
            user_role: User's role
            
        Returns:
            Filtered list of items
        """
        # Admin and superadmin see all items
        if user_role in ['admin', 'superadmin']:
            return items
        
        # Filter by workspace
        if workspace_id:
            return [
                item for item in items
                if item.get('workspace_id') == workspace_id
            ]
        
        return []
    
    @staticmethod
    def filter_by_venue(
        items: List[Dict[str, Any]],
        venue_ids: List[str],
        user_role: str
    ) -> List[Dict[str, Any]]:
        """
        Filter items by venue for non-admin users
        
        Args:
            items: List of items to filter
            venue_ids: User's accessible venue IDs
            user_role: User's role
            
        Returns:
            Filtered list of items
        """
        # Admin and superadmin see all items
        if user_role in ['admin', 'superadmin']:
            return items
        
        # Filter by venue
        if venue_ids:
            return [
                item for item in items
                if item.get('venue_id') in venue_ids
            ]
        
        return []


# Global instance
permission_checker = PermissionChecker()


# Convenience functions for backward compatibility
async def validate_user_role(
    current_user: Dict[str, Any],
    required_roles: List[str],
    error_message: str = "Insufficient permissions"
) -> str:
    """Validate user role - convenience function"""
    return await permission_checker.validate_user_role(
        current_user, required_roles, error_message
    )


async def validate_admin_or_superadmin(current_user: Dict[str, Any]) -> str:
    """Validate admin or superadmin - convenience function"""
    return await permission_checker.validate_admin_or_superadmin(current_user)


async def check_resource_access(
    current_user: Dict[str, Any],
    resource: Dict[str, Any],
    resource_type: str = "resource"
) -> bool:
    """Check resource access - convenience function"""
    return await permission_checker.check_resource_access(
        current_user, resource, resource_type
    )
