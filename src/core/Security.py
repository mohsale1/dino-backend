from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from src.config.Settings import settings
import hashlib
import base64
import bcrypt

security = HTTPBearer()

def _prehash_password(password: str) -> bytes:
    """
    Pre-hash password with SHA256 to avoid bcrypt's 72-byte limit.
    
    This allows passwords of any length while maintaining security.
    The SHA256 hash is base64-encoded to produce a fixed-length string
    that's always under bcrypt's limit.
    
    Args:
        password: Plain text password of any length
        
    Returns:
        Base64-encoded SHA256 hash as bytes (always 44 bytes)
    """
    # Hash with SHA256
    sha256_hash = hashlib.sha256(password.encode('utf-8')).digest()
    # Encode to base64 for bcrypt compatibility
    return base64.b64encode(sha256_hash)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.
    
    Uses SHA256 pre-hashing to support passwords of any length.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Stored bcrypt hash
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        prehashed = _prehash_password(plain_password)
        return bcrypt.checkpw(prehashed, hashed_password.encode('utf-8'))
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """
    Hash a password using SHA256 + bcrypt.
    
    This approach:
    1. Pre-hashes the password with SHA256 (produces 32 bytes)
    2. Base64 encodes it (produces 44 bytes)
    3. Hashes with bcrypt (always under 72-byte limit)
    
    Benefits:
    - Supports passwords of ANY length
    - No truncation or length restrictions
    - Strong security (SHA256 + bcrypt)
    - Fixed-length input to bcrypt
    
    Args:
        password: Plain text password of any length
        
    Returns:
        Bcrypt hash of the SHA256-hashed password
    """
    prehashed = _prehash_password(password)
    # Generate salt and hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(prehashed, salt)
    return hashed.decode('utf-8')

def decode_token(token: str) -> Optional[dict]:
    """Decode JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None

async def get_current_user_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Extract token from Authorization header (or return empty if JWT disabled)"""
    if not settings.ENABLE_JWT:
        return ""  # Return empty token when JWT is disabled
    return credentials.credentials

def verify_token_type(token: str, expected_type: str) -> bool:
    """Verify token type (access or refresh)"""
    payload = decode_token(token)
    if not payload:
        return False
    return payload.get("type") == expected_type


