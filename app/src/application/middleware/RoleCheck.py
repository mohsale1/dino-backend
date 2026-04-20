from typing import Callable, Dict, Any, List

from fastapi import Depends

from src.base.BaseRoleCheck import BaseRoleCheck
from src.core.Dependencies import get_current_application_user, get_current_user


class ApplicationPermissionCheck(BaseRoleCheck):
    """Permission-based access control for dino-application.

    Usage in routes — single permission:
        Depends(ApplicationPermissionCheck.require("categories:create"))

    Usage in routes — any of several permissions:
        Depends(ApplicationPermissionCheck.require_any(["orders:read", "orders:manage"]))

    Permission codename convention: ``resource:action``

    Standard actions:
        read     — list / retrieve
        create   — create new records
        update   — modify existing records
        delete   — soft-delete records
        restore  — restore soft-deleted records
        manage   — full CRUD (superset of all above)

    Resources and their codenames:
        dashboard   : dashboard:read
        users       : users:read, users:create, users:update, users:delete, users:manage
        roles       : roles:read
        permissions : permissions:read
        categories  : categories:read, categories:create, categories:update, categories:delete, categories:restore
        items       : items:read, items:create, items:update, items:delete, items:restore, items:manage
        orders      : orders:read, orders:create, orders:update, orders:delete, orders:restore, orders:manage
        areas       : areas:read, areas:create, areas:update, areas:delete, areas:restore
        tables      : tables:read, tables:create, tables:update, tables:delete, tables:restore, tables:manage
        coupons     : coupons:read, coupons:create, coupons:update, coupons:delete, coupons:restore
        reviews     : reviews:read, reviews:create, reviews:update, reviews:delete, reviews:manage
        personas    : personas:read, personas:create, personas:update, personas:delete, personas:restore
        workspaces  : workspaces:read, workspaces:update
        homepage    : homepage:read, homepage:update
    """

    @staticmethod
    def require(permission: str) -> Callable:
        """Return a FastAPI dependency that enforces a single permission codename."""
        def _check(user: Dict[str, Any] = Depends(get_current_application_user)) -> Dict[str, Any]:
            BaseRoleCheck.require_permission(user, permission)
            return user
        # Give the dependency a unique name so FastAPI caches it correctly
        _check.__name__ = f"require_{permission.replace(':', '_')}"
        return _check

    @staticmethod
    def require_any(permissions: List[str]) -> Callable:
        """Return a FastAPI dependency that enforces at least one of the given permission codenames."""
        def _check(user: Dict[str, Any] = Depends(get_current_application_user)) -> Dict[str, Any]:
            BaseRoleCheck.require_any_permission(user, permissions)
            return user
        _check.__name__ = f"require_any_{'_or_'.join(p.replace(':', '_') for p in permissions)}"
        return _check

    @staticmethod
    def require_authenticated(user: Dict[str, Any] = Depends(get_current_application_user)) -> Dict[str, Any]:
        """Require only that the user is authenticated (no specific permission needed)."""
        return user

    @staticmethod
    def require_authenticated_any(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        """Require authentication via the generic user dependency (cross-service compatible)."""
        return user
