"""
BaseModel — thin shim providing row_to_dict() and sanitize_dict() utilities
for converting SQLAlchemy ORM row objects to plain Python dicts.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Set


def row_to_dict(row) -> dict:
    """
    Convert a SQLAlchemy ORM instance to a plain dict.

    Type coercions applied:
      - datetime    -> ISO-8601 string (isoformat())
      - Decimal     -> float
      - everything else passes through as-is
    """
    result = {}
    for column in row.__table__.columns:
        value = getattr(row, column.name)
        if isinstance(value, datetime):
            value = value.isoformat()
        elif isinstance(value, Decimal):
            value = float(value)
        result[column.name] = value
    return result


# Fields that must never appear in outbound API responses
SENSITIVE_FIELDS: frozenset = frozenset(["password_hash", "password", "reset_token"])


def sanitize_dict(data: dict, extra_fields: Optional[Set[str]] = None) -> dict:
    """
    Remove sensitive keys from *data* in-place and return the dict.

    Args:
        data:         The dictionary to sanitize (mutated in-place).
        extra_fields: Additional field names to strip beyond SENSITIVE_FIELDS.

    Returns:
        The same dict with sensitive keys removed.
    """
    fields_to_remove = SENSITIVE_FIELDS
    if extra_fields:
        fields_to_remove = SENSITIVE_FIELDS | extra_fields

    for field in fields_to_remove:
        data.pop(field, None)

    return data
