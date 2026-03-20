from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status

class BaseRoleCheck:
    """Base role checking functionality"""
    
    @staticmethod
    def check_role(user: Dict[str, Any], allowed_roles: List[str]) -> bool:
        """Check if user has one of the allowed roles"""
        user_role = user.get('role', {})
        role_name = user_role.get('name', '')
        return role_name in allowed_roles
    
    @staticmethod
    def check_permission(user: Dict[str, Any], required_permission: str) -> bool:
        """Check if user has required permission"""
        user_role = user.get('role', {})
        permissions = user_role.get('permissions', [])
        
        # Check for wildcard permission
        if '*' in permissions:
            return True
        
        # Check for exact permission
        if required_permission in permissions:
            return True
        
        # Check for wildcard in permission category (dot-notation: e.g. "application.orders.*")
        permission_parts = required_permission.split('.')
        if len(permission_parts) > 1:
            wildcard_permission = f"{permission_parts[0]}.*"
            if wildcard_permission in permissions:
                return True
        
        return False
    
    @staticmethod
    def require_role(user: Optional[Dict[str, Any]], allowed_roles: List[str]):
        """Require user to have one of the allowed roles"""
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        
        if not BaseRoleCheck.check_role(user, allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
    
    @staticmethod
    def require_permission(user: Optional[Dict[str, Any]], required_permission: str):
        """Require user to have specific permission"""
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        
        if not BaseRoleCheck.check_permission(user, required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )