from typing import Any, Callable, Dict

from fastapi import Depends

from src.base.BaseRoleCheck import BaseRoleCheck
from src.core.Dependencies import get_current_application_user


class ApplicationPermissionCheck(BaseRoleCheck):
    """Permission-based access control for dino-application.

    Usage in routes:
        Depends(ApplicationPermissionCheck.require("categories:create"))
        Depends(ApplicationPermissionCheck.require_authenticated)

    Permission codename convention: ``resource:action``

    Standard actions:
        read, create, update, delete, restore, manage

    Resources:
        dashboard, users, roles, permissions, categories, items, orders,
        areas, tables, reviews, personas, customers, workspaces, homepage,
        billing, coupons
    """

    @staticmethod
    def require(permission: str) -> Callable:
        """Return a FastAPI dependency that enforces a single permission codename."""
        def _check(
            user: Dict[str, Any] = Depends(get_current_application_user),
        ) -> Dict[str, Any]:
            BaseRoleCheck.require_permission(user, permission)
            return user

        # Unique name ensures FastAPI dependency cache works correctly per permission
        _check.__name__ = f"require_{permission.replace(':', '_')}"
        return _check


    @staticmethod
    def require_authenticated(
        user: Dict[str, Any] = Depends(get_current_application_user),
    ) -> Dict[str, Any]:
        """Require only that the user is authenticated — no specific permission needed."""
        return user
