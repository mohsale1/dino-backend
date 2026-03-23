from src.base.BaseRoleCheck import BaseRoleCheck
from typing import Dict, Any
from fastapi import Depends, HTTPException, status
from src.core.Dependencies import get_current_system_user

class SystemRoleCheck(BaseRoleCheck):
    @staticmethod
    def require_super_admin(user: Dict[str, Any] = Depends(get_current_system_user)):
        BaseRoleCheck.require_role(user, ["SuperAdmin"])
        return user
    @staticmethod
    def require_billing_manager(user: Dict[str, Any] = Depends(get_current_system_user)):
        BaseRoleCheck.require_role(user, ["SuperAdmin", "Admin"])
        return user
    @staticmethod
    def require_marketing_agent(user: Dict[str, Any] = Depends(get_current_system_user)):
        BaseRoleCheck.require_role(user, ["SuperAdmin", "Admin"])
        return user
    @staticmethod
    def require_admin(user: Dict[str, Any] = Depends(get_current_system_user)):
        BaseRoleCheck.require_role(user, ["SuperAdmin", "Admin"])
        return user
    @staticmethod
    def require_operator(user: Dict[str, Any] = Depends(get_current_system_user)):
        BaseRoleCheck.require_role(user, ["SuperAdmin", "Admin", "Operator"])
        return user