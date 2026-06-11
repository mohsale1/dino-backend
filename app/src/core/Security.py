import base64
import hashlib
import logging
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from src.config.Settings import settings
from src.core.Exceptions import (
    JwtDisabledError,
    TokenExpiredError,
    TokenInvalidError,
    TokenMissingError,
)

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


def _prehash_password(password: str) -> bytes:
    """
    Pre-hash password with SHA256 to avoid bcrypt's 72-byte limit.

    SHA256 digest (32 bytes) is base64-encoded to 44 bytes — always under
    bcrypt's limit. This is the documented approach for long-password support.
    """
    sha256_hash = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(sha256_hash)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a stored bcrypt hash."""
    try:
        prehashed = _prehash_password(plain_password)
        return bcrypt.checkpw(prehashed, hashed_password.encode("utf-8"))
    except ValueError:
        return False
    except Exception:
        logger.error("Unexpected error during password verification", exc_info=True)
        return False


def get_password_hash(password: str) -> str:
    """Hash a password using SHA256 pre-hash + bcrypt."""
    prehashed = _prehash_password(password)
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(prehashed, salt)
    return hashed.decode("utf-8")


def decode_token(token: str) -> dict:
    """Decode and verify a JWT. Raises typed AppException on failure."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except ExpiredSignatureError:
        logger.warning("JWT decode failed: token expired")
        raise TokenExpiredError()
    except InvalidTokenError as exc:
        logger.warning("JWT decode failed: %s", type(exc).__name__)
        raise TokenInvalidError()


async def get_current_user_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    """Extract the raw JWT string from the Authorization header."""
    if not settings.ENABLE_JWT:
        raise JwtDisabledError()
    if credentials is None:
        raise TokenMissingError()
    return credentials.credentials


