"""
Application-wide constants.

Token expiry values are derived from Settings at import time so they remain
configurable via environment variables while being referenced as named constants
throughout the codebase.
"""

from src.config.Settings import settings

# ---------------------------------------------------------------------------
# JWT token expiry
# ---------------------------------------------------------------------------

ACCESS_TOKEN_EXPIRE_MINUTES: int = settings.ACCESS_TOKEN_EXPIRE_MINUTES
"""Access token lifetime in minutes. Default: 300 (5 hours)."""

REFRESH_TOKEN_EXPIRE_DAYS: int = settings.REFRESH_TOKEN_EXPIRE_DAYS
"""Refresh token lifetime in days. Default: 1."""
