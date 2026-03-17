from src.base.BaseRoleCheck import BaseRoleCheck
from typing import Dict, Any
from fastapi import Depends
from src.core.Dependencies import get_current_system_user

class SystemRoleCheck(BaseRoleCheck):
    """System role checking middleware"""
    
    @staticmethod
    def require_super_admin(user: Dict[str, Any] = Depends(get_current_system_user)):
        """Require SuperAdmin role"""
        BaseRoleCheck.require_role(user, ["SuperAdmin"])
        return user
    
    @staticmethod
    def require_billing_manager(user: Dict[str, Any] = Depends(get_current_system_user)):
        """Require BillingManager role"""
        BaseRoleCheck.require_role(user, ["SuperAdmin", "BillingManager"])
        return user
    
    @staticmethod
    def require_marketing_agent(user: Dict[str, Any] = Depends(get_current_system_user)):
        """Require MarketingAgent role"""
        BaseRoleCheck.require_role(user, ["SuperAdmin", "MarketingAgent"])
        return user
