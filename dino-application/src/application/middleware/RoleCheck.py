from src.base.BaseRoleCheck import BaseRoleCheck
from typing import Dict, Any
from fastapi import Depends, HTTPException, status
from src.core.Dependencies import get_current_application_user, get_current_user

class ApplicationRoleCheck(BaseRoleCheck):
    @staticmethod
    def require_admin(user: Dict[str, Any] = Depends(get_current_application_user)):
        BaseRoleCheck.require_role(user, ['Owner'])
        return user
    @staticmethod
    def require_manager(user: Dict[str, Any] = Depends(get_current_application_user)):
        BaseRoleCheck.require_role(user, ['Owner', 'Manager'])
        return user
    @staticmethod
    def require_operator(user: Dict[str, Any] = Depends(get_current_application_user)):
        BaseRoleCheck.require_role(user, ['Owner', 'Manager', 'User'])
        return user
    @staticmethod
    def require_manager_or_superadmin(user: Dict[str, Any] = Depends(get_current_user)):
        return user
    @staticmethod
    def require_admin_or_superadmin(user: Dict[str, Any] = Depends(get_current_user)):
        return user