"""
dino-application ORM models package.

Importing this package registers every model class with the shared
DeclarativeBase (Base) so that Alembic's autogenerate can discover all tables.
"""

from src.models.Base import (  # noqa: F401
    Base,
    EntityMixin,
    BigIntPrimaryKeyMixin,
)

# Association tables
from src.models.Role import role_permissions  # noqa: F401
from src.models.Workspace import workspace_personas  # noqa: F401
from src.models.User import user_personas  # noqa: F401

# ORM model classes — import order respects FK dependencies
from src.models.Permission import Permission  # noqa: F401
from src.models.Role import Role  # noqa: F401
from src.models.Workspace import Workspace  # noqa: F401
from src.models.WorkspaceBilling import WorkspaceBilling  # noqa: F401
from src.models.Persona import Persona  # noqa: F401
from src.models.User import User  # noqa: F401
from src.models.Customer import Customer  # noqa: F401
from src.models.Area import Area  # noqa: F401
from src.models.Table import Table  # noqa: F401
from src.models.Category import Category  # noqa: F401
from src.models.Item import Item  # noqa: F401
from src.models.OrderDetail import OrderDetail  # noqa: F401
from src.models.Order import Order  # noqa: F401
from src.models.OrderTransaction import OrderTransaction  # noqa: F401
from src.models.BillingDetail import BillingDetail  # noqa: F401
from src.models.BillingTransaction import BillingTransaction  # noqa: F401
from src.models.Review import Review  # noqa: F401
from src.models.BillingConfig import BillingConfig  # noqa: F401
from src.models.CustomerSession import CustomerSession  # noqa: F401

__all__ = [
    # Base & mixins
    "Base",
    "EntityMixin",
    "BigIntPrimaryKeyMixin",
    # Association tables
    "role_permissions",
    "workspace_personas",
    "user_personas",
    # Models
    "Permission",
    "Role",
    "Workspace",
    "WorkspaceBilling",
    "Persona",
    "User",
    "Customer",
    "Area",
    "Table",
    "Category",
    "Item",
    "OrderDetail",
    "Order",
    "OrderTransaction",
    "BillingDetail",
    "BillingTransaction",
    "Review",
    "BillingConfig",
    "CustomerSession",
]