from typing import Callable, Dict, Any, List

from fastapi import Depends

from src.base.BaseRoleCheck import BaseRoleCheck
from src.core.Dependencies import get_current_system_user


class SystemPermissionCheck(BaseRoleCheck):
    """Permission-based access control for dino-system.

    Usage in routes — single permission:
        Depends(SystemPermissionCheck.require("system:manage"))

    Usage in routes — any of several permissions:
        Depends(SystemPermissionCheck.require_any(["billing:manage", "system:manage"]))

    Permission codename convention: ``resource:action``

    Standard actions:
        read     — list / retrieve
        create   — create new records
        update   — modify existing records
        delete   — soft-delete records
        restore  — restore soft-deleted records
        manage   — full CRUD (superset of all above)

    Resources and their codenames:
        system          : system:manage  (full system administration)
        users           : users:read, users:create, users:update, users:delete, users:manage
        roles           : roles:read, roles:create, roles:update, roles:delete, roles:manage
        permissions     : permissions:read, permissions:create, permissions:update, permissions:delete, permissions:manage
        workspaces      : workspaces:read, workspaces:create, workspaces:update, workspaces:delete, workspaces:manage
        personas        : personas:read, personas:update, personas:delete, personas:manage
        dashboard       : dashboard:read
        billing         : billing:read, billing:update, billing:manage
        registration    : registration:read, registration:create, registration:update, registration:delete, registration:manage
        settings        : settings:read, settings:update, settings:manage
    """

    @staticmethod
    def require(permission: str) -> Callable:
        """Return a FastAPI dependency that enforces a single permission codename."""
        def _check(user: Dict[str, Any] = Depends(get_current_system_user)) -> Dict[str, Any]:
            BaseRoleCheck.require_permission(user, permission)
            return user
        _check.__name__ = f"require_{permission.replace(':', '_')}"
        return _check

    @staticmethod
    def require_any(permissions: List[str]) -> Callable:
        """Return a FastAPI dependency that enforces at least one of the given permission codenames."""
        def _check(user: Dict[str, Any] = Depends(get_current_system_user)) -> Dict[str, Any]:
            BaseRoleCheck.require_any_permission(user, permissions)
            return user
        _check.__name__ = f"require_any_{'_or_'.join(p.replace(':', '_') for p in permissions)}"
        return _check

    @staticmethod
    def require_authenticated(user: Dict[str, Any] = Depends(get_current_system_user)) -> Dict[str, Any]:
        """Require only that the user is authenticated (no specific permission needed)."""
        return user
