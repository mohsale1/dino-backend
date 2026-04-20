"""
BaseUser — user-specific sanitisation utilities.

The ORM User model lives in src/models/User.py.
This module provides constants and helpers for stripping sensitive fields
from user dicts before they are returned to callers or serialised to JSON.
"""

from typing import Dict, Any

SENSITIVE_USER_FIELDS: frozenset = frozenset([
    "password_hash",
    "password",
    "reset_token",
    "reset_token_expires_at",
])


def sanitize_user(user: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return a shallow copy of *user* with all sensitive fields removed.

    Safe to call even when the fields are absent.
    """
    return {k: v for k, v in user.items() if k not in SENSITIVE_USER_FIELDS}
