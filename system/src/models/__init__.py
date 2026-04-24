"""
system ORM models package.

Importing this package registers all mapped classes against Base.metadata,
which is required for Alembic autogenerate to discover every table.

Usage in alembic/env.py
-----------------------
    from src.models import Base          # noqa: F401  (triggers all imports)
    target_metadata = Base.metadata
"""

# Base must be imported first so metadata is initialised before any model
# references it.
from src.models.Base import (  # noqa: F401
    Base,
    BigIntPrimaryKeyMixin,
    EntityMixin,
)

# Association tables are defined inside their primary model modules; importing
# those modules is sufficient to register the Table objects with Base.metadata.
from src.models.Permission import Permission  # noqa: F401
from src.models.Role import Role, role_permissions  # noqa: F401
from src.models.Workspace import Workspace, workspace_personas  # noqa: F401
from src.models.WorkspaceBilling import WorkspaceBilling  # noqa: F401
from src.models.BillingTransaction import BillingTransaction  # noqa: F401
from src.models.Persona import Persona  # noqa: F401
from src.models.User import User  # noqa: F401
from src.models.WorkspaceRequest import WorkspaceRequest  # noqa: F401

__all__ = [
    # Base
    "Base",
    "BigIntPrimaryKeyMixin",
    "EntityMixin",
    # Entity models
    "Permission",
    "Role",
    "User",
    "Workspace",
    "WorkspaceBilling",
    "BillingTransaction",
    "Persona",
    "WorkspaceRequest",
    # Association tables
    "role_permissions",
    "workspace_personas",
]