"""
BaseModel compatibility shim.

The real ORM models live in src/models/ (SQLAlchemy 2.x DeclarativeBase).
This module provides shared dict-conversion utilities used across the codebase.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional


SENSITIVE_FIELDS: frozenset = frozenset([
    "password_hash",
    "password",
    "reset_token",
    "reset_token_expires_at",
])


def row_to_dict(row) -> dict:
    """
    Convert a SQLAlchemy ORM model instance to a plain Python dict.

    Type coercions applied:
      - uuid.UUID  -> str  (hex with hyphens)
      - datetime   -> str  (ISO-8601 via isoformat())
      - Decimal    -> float
      - everything else passes through as-is
    """
    result: dict = {}

    for column in row.__table__.columns:
        value = getattr(row, column.name)

        if isinstance(value, uuid.UUID):
            value = str(value)
        elif isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            value = value.isoformat()
        elif isinstance(value, Decimal):
            value = float(value)

        result[column.name] = value

    return result


def sanitize_dict(data: dict, extra_fields: Optional[set] = None) -> dict:
    """
    Return a shallow copy of *data* with SENSITIVE_FIELDS (and any
    caller-supplied *extra_fields*) removed.
    """
    fields_to_remove = SENSITIVE_FIELDS
    if extra_fields:
        fields_to_remove = fields_to_remove | set(extra_fields)

    return {k: v for k, v in data.items() if k not in fields_to_remove}
