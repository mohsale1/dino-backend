import logging
from typing import Any, Dict, FrozenSet

from src.core.Exceptions import PermissionDeniedError

logger = logging.getLogger(__name__)

# Actions that `resource:manage` implicitly covers
_MANAGE_IMPLIES: FrozenSet[str] = frozenset({"read", "create", "update", "delete"})


def _get_permissions(user: Dict[str, Any]) -> FrozenSet[str]:
    """Extract the user's permission codenames as a frozenset for O(1) lookups."""
    perms = user.get("role") and user["role"].get("permissions")
    return frozenset(perms) if perms else frozenset()


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
        All set lookups are O(1).
        """
        if ":" not in required_permission:
            raise ValueError(
                f"Invalid permission codename '{required_permission}': "
                "expected 'resource:action' format."
            )

        permissions = _get_permissions(user)

        if not permissions:
            return False
        if "*" in permissions or required_permission in permissions:
            return True

        resource, action = required_permission.split(":", 1)

        if f"{resource}:*" in permissions:
            return True
        if action in _MANAGE_IMPLIES and f"{resource}:manage" in permissions:
            return True

        return False


    @staticmethod
    def require_permission(user: Dict[str, Any], required_permission: str) -> None:
        """Enforce that the authenticated user holds the required permission."""
        if not BaseRoleCheck.check_permission(user, required_permission):
            logger.warning(
                "permission.denied user_id=%s required=%s",
                user.get("id"),
                required_permission,
            )
            raise PermissionDeniedError()

