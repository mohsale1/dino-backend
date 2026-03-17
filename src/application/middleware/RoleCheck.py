from src.base.BaseRoleCheck import BaseRoleCheck
from typing import Dict, Any
from fastapi import Depends, HTTPException, status
from src.core.Dependencies import get_current_application_user, get_current_user

class ApplicationRoleCheck(BaseRoleCheck):
    """Application role checking middleware"""
    
    @staticmethod
    def require_admin(user: Dict[str, Any] = Depends(get_current_application_user)):
        """Require Admin role"""
        BaseRoleCheck.require_role(user, ["Admin"])
        return user
    
    @staticmethod
    def require_manager(user: Dict[str, Any] = Depends(get_current_application_user)):
        """Require Manager role"""
        BaseRoleCheck.require_role(user, ["Admin", "Manager"])
        return user
    
    @staticmethod
    def require_operator(user: Dict[str, Any] = Depends(get_current_application_user)):
        """Require Operator role (or higher)"""
        BaseRoleCheck.require_role(user, ["Admin", "Manager", "Operator"])
        return user
    
    @staticmethod
    def require_manager_or_superadmin(user: Dict[str, Any] = Depends(get_current_user)):
        """Require Manager role (application) or SuperAdmin (system)"""
        user_type = user.get('user_type', 'application')
        role_name = user.get('role', {}).get('name', '')
        
        # Allow SuperAdmin (system users)
        if user_type == 'system' and role_name == 'SuperAdmin':
            return user
        
        # Allow Admin and Manager (application users)
        if user_type == 'application' and role_name in ['Admin', 'Manager']:
            return user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Requires Manager/Admin (application) or SuperAdmin (system) role."
        )
    
    @staticmethod
    def require_admin_or_superadmin(user: Dict[str, Any] = Depends(get_current_user)):
        """Require Admin role (application) or SuperAdmin (system)"""
        user_type = user.get('user_type', 'application')
        role_name = user.get('role', {}).get('name', '')
        
        # Allow SuperAdmin (system users)
        if user_type == 'system' and role_name == 'SuperAdmin':
            return user
        
        # Allow Admin (application users)
        if user_type == 'application' and role_name == 'Admin':
            return user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Requires Admin (application) or SuperAdmin (system) role."
        )
