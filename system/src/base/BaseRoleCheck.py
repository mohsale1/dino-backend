from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status


class BaseRoleCheck:
    """Permission-based access control foundation.

    Permissions are stored as codename strings on the user dict under
    ``user['role']['permissions']`` — a list populated by the dependency
    layer from the ``role_permissions`` join table.

    Codename convention: ``resource:action``
    Examples: ``system:manage``, ``billing:manage``, ``registration:manage``

    Wildcard rules (checked in order):
      1. ``*``              — grants every permission
      2. ``resource:*``     — grants all actions on a resource
      3. exact codename     — grants that specific action
    """

    @staticmethod
    def check_permission(user: Dict[str, Any], required_permission: str) -> bool:
        """Return True if the user holds the required permission codename.

        Supports both legacy colon format ("dashboard:view") and current
        dot-notation format ("system.dashboard.view" / "application.orders.read").
        Wildcard rules (checked in order):
          1. ``*``              — grants every permission
          2. ``resource:*``     — grants all actions on a resource (legacy)
          3. exact match        — grants that specific permission
        """
        permissions: List[str] = user.get("role", {}).get("permissions", [])

        if "*" in permissions:
            return True

        if required_permission in permissions:
            return True

        # Legacy resource-level wildcard: e.g. "system:*" covers "system:manage"
        if ":" in required_permission:
            resource = required_permission.split(":")[0]
            if f"{resource}:*" in permissions:
                return True

        return False

    @staticmethod
    def check_any_permission(user: Dict[str, Any], required_permissions: List[str]) -> bool:
        """Return True if the user holds at least one of the given permission codenames."""
        return any(
            BaseRoleCheck.check_permission(user, perm)
            for perm in required_permissions
        )

    @staticmethod
    def require_permission(user: Optional[Dict[str, Any]], required_permission: str) -> None:
        """Enforce that the authenticated user holds the required permission.

        Raises:
            HTTP 401 — user is not authenticated
            HTTP 403 — user is authenticated but lacks the permission
        """
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )
        if not BaseRoleCheck.check_permission(user, required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: '{required_permission}' is required",
            )

    @staticmethod
    def require_any_permission(user: Optional[Dict[str, Any]], required_permissions: List[str]) -> None:
        """Enforce that the authenticated user holds at least one of the given permissions.

        Raises:
            HTTP 401 — user is not authenticated
            HTTP 403 — user holds none of the required permissions
        """
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )
        if not BaseRoleCheck.check_any_permission(user, required_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: one of {required_permissions} is required",
            )
