import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# Actions that `resource:manage` implicitly covers.
_MANAGE_IMPLIES: frozenset = frozenset({"read", "create", "update", "delete"})


class BaseRoleCheck:
    """Permission-based access control foundation.

    Permissions are stored as codename strings on the user dict under
    ``user['role']['permissions']`` — a list populated by the dependency
    layer from the ``role_permissions`` join table.

    Codename convention: ``resource:action``
    Examples: ``categories:create``, ``orders:read``, ``users:manage``

    Wildcard / superset rules (checked in order):
      1. ``*``               — grants every permission
      2. ``resource:*``      — grants all actions on a resource
      3. ``resource:manage`` — grants read / create / update / delete on that resource
      4. exact codename      — grants that specific action
    """

    @staticmethod
    def check_permission(user: Dict[str, Any], required_permission: str) -> bool:
        """Return True if the user holds the required permission codename.

        Parameters
        ----------
        user:
            The current-user dict produced by the dependency layer.
            ``user['role']['permissions']`` must be a list of codename strings.
        required_permission:
            A codename in ``resource:action`` format.

        Raises
        ------
        ValueError
            If *required_permission* does not contain a colon separator.
        """
        if ":" not in required_permission:
            raise ValueError(
                f"Invalid permission codename '{required_permission}': "
                "expected 'resource:action' format containing a colon."
            )

        permissions: List[str] = user.get("role", {}).get("permissions", [])

        # 1. Global wildcard — user can do anything.
        if "*" in permissions:
            return True

        # 2. Exact match.
        if required_permission in permissions:
            return True

        resource, action = required_permission.split(":", 1)

        # 3. Resource-level wildcard: e.g. "categories:*" covers "categories:create".
        if f"{resource}:*" in permissions:
            return True

        # 4. Manage superset: "resource:manage" covers read/create/update/delete.
        if action in _MANAGE_IMPLIES and f"{resource}:manage" in permissions:
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

        Raises
        ------
        HTTP 401
            User is not authenticated.
        HTTP 403
            User is authenticated but lacks the permission.
        ValueError
            *required_permission* is not in ``resource:action`` format.
        """
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )
        if not BaseRoleCheck.check_permission(user, required_permission):
            logger.warning(
                "Permission denied for user '%s': '%s' is required",
                user.get("id"),
                required_permission,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )

    @staticmethod
    def require_any_permission(
        user: Optional[Dict[str, Any]], required_permissions: List[str]
    ) -> None:
        """Enforce that the authenticated user holds at least one of the given permissions.

        Raises
        ------
        HTTP 401
            User is not authenticated.
        HTTP 403
            User holds none of the required permissions.
        ValueError
            Any codename in *required_permissions* is not in ``resource:action`` format.
        """
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )
        if not BaseRoleCheck.check_any_permission(user, required_permissions):
            logger.warning(
                "Permission denied for user '%s': one of %s is required",
                user.get("id"),
                required_permissions,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
