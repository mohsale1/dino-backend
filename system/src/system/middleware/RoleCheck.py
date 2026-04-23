"""
SystemPermissionCheck — permission-based access control for dino-system.

Permission codename convention: ``resource:action``
e.g. users:create, roles:read, workspaces:manage
"""

from typing import Any, Callable, Dict, List

from fastapi import Depends

from src.base.BaseRoleCheck import BaseRoleCheck
from src.core.Dependencies import get_current_system_user


class SystemPermissionCheck(BaseRoleCheck):
    """Permission-based access control for dino-system routes."""

    @staticmethod
    def require(permission: str) -> Callable:
        """Return a FastAPI dependency that enforces a single permission."""
        def _check(
            user: Dict[str, Any] = Depends(get_current_system_user),
        ) -> Dict[str, Any]:
            BaseRoleCheck.require_permission(user, permission)
            return user

        _check.__name__ = f"require_{permission.replace(':', '_')}"
        return _check

    @staticmethod
    def require_any(permissions: List[str]) -> Callable:
        """Return a FastAPI dependency that enforces at least one of the given permissions."""
        def _check(
            user: Dict[str, Any] = Depends(get_current_system_user),
        ) -> Dict[str, Any]:
            BaseRoleCheck.require_any_permission(user, permissions)
            return user

        _check.__name__ = f"require_any_{'_or_'.join(p.replace(':', '_') for p in permissions)}"
        return _check

    @staticmethod
    def require_authenticated(
        user: Dict[str, Any] = Depends(get_current_system_user),
    ) -> Dict[str, Any]:
        """Require only that the user is authenticated (no specific permission needed)."""
        return user
