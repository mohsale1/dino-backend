"""
ID Generator Utilities
Provides functions for generating unique IDs for various entities

IMPORTANT: All document IDs across all collections use generate_document_id()
for consistency. This ensures uniform ID format throughout the database.
"""
import uuid
from datetime import datetime


def generate_document_id() -> str:
 """
 Generate a unique document ID for ANY collection in the database.
 
 This is the SINGLE source of truth for all document ID generation.
 Use this for: users, venues, orders, customers, workspaces, roles, 
 permissions, menu items, tables, and ALL other collections.
 
 Returns:
 str: A unique ID string (UUID4 format)
 """
 return str(uuid.uuid4())


def generate_firestore_id() -> str:
 """
 Generate a Firestore-compatible unique ID
 Alias for generate_document_id() for backward compatibility
 
 Returns:
 str: A unique ID string (UUID4 format)
 """
 return generate_document_id()


def generate_user_id() -> str:
 """
 Generate a unique user ID
 Uses generate_document_id() for consistency
 
 Returns:
 str: A unique user ID string
 """
 return generate_document_id()


def generate_order_id() -> str:
 """
 Generate a unique order ID
 Uses generate_document_id() for consistency
 
 Returns:
 str: A unique order ID string
 """
 return generate_document_id()


def generate_venue_id() -> str:
 """
 Generate a unique venue ID
 Uses generate_document_id() for consistency
 
 Returns:
 str: A unique venue ID string
 """
 return generate_document_id()


def generate_workspace_id() -> str:
 """
 Generate a unique workspace ID
 Uses generate_document_id() for consistency
 
 Returns:
 str: A unique workspace ID string
 """
 return generate_document_id()


def generate_short_id(prefix: str = "", length: int = 8) -> str:
 """
 Generate a short unique ID with optional prefix
 
 Args:
 prefix: Optional prefix for the ID
 length: Length of the random part (default: 8)
 
 Returns:
 str: A short unique ID
 """
 random_part = str(uuid.uuid4()).replace('-', '')[:length].upper()
 if prefix:
    return f"{prefix}_{random_part}"
 return random_part


def generate_order_number() -> str:
 """
 Generate a human-readable order number
 
 Returns:
 str: Order number in format ORD-YYYYMMDDHHMMSS-XXXX
 """
 timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
 random_suffix = str(uuid.uuid4())[:4].upper()
 return f"ORD-{timestamp}-{random_suffix}"


def generate_table_qr_code() -> str:
 """
 Generate a unique QR code identifier for tables
 
 Returns:
 str: A unique QR code string
 """
 return str(uuid.uuid4())


def generate_customer_id() -> str:
 """
 Generate a unique customer ID
 Uses generate_document_id() for consistency
 
 Returns:
 str: A unique customer ID string
 """
 return generate_document_id()


def generate_transaction_id() -> str:
 """
 Generate a unique transaction ID
 Uses generate_document_id() for consistency
 
 Returns:
 str: A unique transaction ID string
 """
 return generate_document_id()


def generate_role_id() -> str:
 """
 Generate a unique role ID
 Uses generate_document_id() for consistency
 
 Returns:
 str: A unique role ID string
 """
 return generate_document_id()


def generate_permission_id() -> str:
 """
 Generate a unique permission ID
 Uses generate_document_id() for consistency
 
 Returns:
 str: A unique permission ID string
 """
 return generate_document_id()


def generate_menu_item_id() -> str:
 """
 Generate a unique menu item ID
 Uses generate_document_id() for consistency
 
 Returns:
 str: A unique menu item ID string
 """
 return generate_document_id()


def generate_menu_category_id() -> str:
 """
 Generate a unique menu category ID
 Uses generate_document_id() for consistency
 
 Returns:
 str: A unique menu category ID string
 """
 return generate_document_id()


def generate_table_id() -> str:
 """
 Generate a unique table ID
 Uses generate_document_id() for consistency
 
 Returns:
 str: A unique table ID string
 """
 return generate_document_id()


def generate_notification_id() -> str:
 """
 Generate a unique notification ID
 Uses generate_document_id() for consistency
 
 Returns:
 str: A unique notification ID string
 """
 return generate_document_id()


def generate_review_id() -> str:
 """
 Generate a unique review ID
 Uses generate_document_id() for consistency
 
 Returns:
 str: A unique review ID string
 """
 return generate_document_id()