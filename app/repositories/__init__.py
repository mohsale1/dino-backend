"""
Repositories Package
Data access layer for all collections
"""

# Base Repository
from app.repositories.base import BaseRepository

# Collection Repositories
from app.repositories.workspace import WorkspaceRepository, get_workspace_repository
from app.repositories.user import UserRepository, get_user_repository
from app.repositories.venue import VenueRepository, get_venue_repository
from app.repositories.menu import (
    MenuCategoryRepository, MenuItemRepository,
    get_menu_category_repository, get_menu_item_repository
)
from app.repositories.table import (
    TableAreaRepository, TableRepository,
    get_table_area_repository, get_table_repository
)
from app.repositories.customer import CustomerRepository, get_customer_repository
from app.repositories.order import OrderRepository, get_order_repository
from app.repositories.role import RoleRepository, get_role_repository
from app.repositories.permission import PermissionRepository, get_permission_repository
from app.repositories.transaction import TransactionRepository, get_transaction_repository
from app.repositories.notification import NotificationRepository, get_notification_repository
from app.repositories.review import ReviewRepository, get_review_repository

__all__ = [
    # Base
    'BaseRepository',
    
    # Repository Classes
    'WorkspaceRepository',
    'UserRepository',
    'VenueRepository',
    'MenuCategoryRepository',
    'MenuItemRepository',
    'TableAreaRepository',
    'TableRepository',
    'CustomerRepository',
    'OrderRepository',
    'RoleRepository',
    'PermissionRepository',
    'TransactionRepository',
    'NotificationRepository',
    'ReviewRepository',
    
    # Getter Functions
    'get_workspace_repository',
    'get_user_repository',
    'get_venue_repository',
    'get_menu_category_repository',
    'get_menu_item_repository',
    'get_table_area_repository',
    'get_table_repository',
    'get_customer_repository',
    'get_order_repository',
    'get_role_repository',
    'get_permission_repository',
    'get_transaction_repository',
    'get_notification_repository',
    'get_review_repository',
]