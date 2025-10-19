"""
Unified Password Security Module
Consolidates all password handling into a single, efficient implementation
"""
import hashlib
import hmac
import secrets
import string
import re
import os
from typing import Dict, List, Optional, Tuple, Any
from passlib.context import CryptContext
from datetime import datetime, timedelta

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Configuration
FIXED_CLIENT_SALT = os.getenv("CLIENT_PASSWORD_SALT", "dino-default-salt-2024-secure-hashing")
CLIENT_HASH_ALGORITHM = "sha256"
CLIENT_SALT_LENGTH = 32

# BCrypt context for server-side hashing
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=getattr(settings, 'BCRYPT_ROUNDS', 12)
)


class PasswordPolicy:
    """Centralized password policy configuration"""
    
    MIN_LENGTH = 8
    MAX_LENGTH = 128
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGITS = True
    REQUIRE_SPECIAL = True
    SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
    # Common weak passwords to reject
    WEAK_PASSWORDS = {
        "password", "123456", "password123", "admin", "qwerty",
        "letmein", "welcome", "monkey", "dragon", "master",
        "password1", "123456789", "12345678", "admin123"
    }


class UnifiedPasswordHandler:
    """Unified password handler supporting multiple authentication modes"""
    
    @staticmethod
    def is_client_hashed(password_input: str) -> bool:
        """Check if password is client-hashed (64 hex characters)"""
        if len(password_input) != 64:
            return False
        
        try:
            int(password_input, 16)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def create_client_hash(password: str, salt: str = None) -> str:
        """Create client-side hash using fixed or provided salt"""
        salt = salt or FIXED_CLIENT_SALT
        salted_password = f"{password}{salt}"
        return hashlib.sha256(salted_password.encode('utf-8')).hexdigest()
    
    @staticmethod
    def create_server_hash(client_hash: str) -> str:
        """Create server-side BCrypt hash from client hash"""
        return pwd_context.hash(client_hash)
    
    @staticmethod
    def verify_password(client_hash: str, stored_hash: str) -> bool:
        """Verify client hash against stored BCrypt hash"""
        try:
            return pwd_context.verify(client_hash, stored_hash)
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    @staticmethod
    def handle_password_input(password_input: str, require_client_hash: bool = True) -> Tuple[str, bool]:
        """
        Handle password input with unified logic
        
        Args:
            password_input: Password (plain text or client hash)
            require_client_hash: Whether to require client-hashed passwords
            
        Returns:
            Tuple[str, bool]: (server_hash, is_client_hashed)
        """
        is_client_hashed = UnifiedPasswordHandler.is_client_hashed(password_input)
        
        if require_client_hash and not is_client_hashed:
            logger.warning("Plain text password rejected - client hashing required")
            raise ValueError("Plain text passwords are not allowed. Password must be client-hashed.")
        
        if is_client_hashed:
            # Process client-hashed password
            logger.info("Processing client-hashed password")
            server_hash = UnifiedPasswordHandler.create_server_hash(password_input)
        else:
            # Process plain text password (legacy/development mode)
            logger.info("Processing plain text password (legacy mode)")
            
            # Validate password strength
            validation_result = validate_password_strength(password_input)
            if not validation_result["is_valid"]:
                raise ValueError(f"Password validation failed: {', '.join(validation_result['errors'])}")
            
            # Convert to client hash then server hash
            client_hash = UnifiedPasswordHandler.create_client_hash(password_input)
            server_hash = UnifiedPasswordHandler.create_server_hash(client_hash)
        
        return server_hash, is_client_hashed
    
    @staticmethod
    def verify_password_input(password_input: str, stored_hash: str, require_client_hash: bool = True) -> bool:
        """
        Verify password input against stored hash
        
        Args:
            password_input: Password (plain text or client hash)
            stored_hash: Stored BCrypt hash
            require_client_hash: Whether to require client-hashed passwords
            
        Returns:
            bool: True if password is valid
        """
        is_client_hashed = UnifiedPasswordHandler.is_client_hashed(password_input)
        
        if require_client_hash and not is_client_hashed:
            logger.warning("Plain text password verification rejected - client hashing required")
            raise ValueError("Plain text passwords are not allowed. Password must be client-hashed.")
        
        if is_client_hashed:
            # Verify client hash directly
            return UnifiedPasswordHandler.verify_password(password_input, stored_hash)
        else:
            # Convert plain text to client hash first, then verify
            client_hash = UnifiedPasswordHandler.create_client_hash(password_input)
            return UnifiedPasswordHandler.verify_password(client_hash, stored_hash)


def validate_password_strength(password: str) -> Dict[str, Any]:
    """
    Validate password strength according to security policy
    Returns dict with validation results
    """
    errors = []
    warnings = []
    score = 0
    
    # Check if strong passwords are required
    if not getattr(settings, 'REQUIRE_STRONG_PASSWORDS', True):
        return {"is_valid": True, "errors": [], "warnings": [], "score": 100, "strength": "Bypassed"}
    
    # Length checks
    if len(password) < PasswordPolicy.MIN_LENGTH:
        errors.append(f"Password must be at least {PasswordPolicy.MIN_LENGTH} characters long")
    elif len(password) < 12:
        warnings.append("Consider using a longer password for better security")
        score += 10
    else:
        score += 25
    
    if len(password) > PasswordPolicy.MAX_LENGTH:
        errors.append(f"Password must not exceed {PasswordPolicy.MAX_LENGTH} characters")
    
    # Character type checks
    if PasswordPolicy.REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")
    else:
        score += 15
    
    if PasswordPolicy.REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")
    else:
        score += 15
    
    if PasswordPolicy.REQUIRE_DIGITS and not re.search(r'\\d', password):
        errors.append("Password must contain at least one digit")
    else:
        score += 15
    
    if PasswordPolicy.REQUIRE_SPECIAL and not re.search(f'[{re.escape(PasswordPolicy.SPECIAL_CHARS)}]', password):
        errors.append(f"Password must contain at least one special character: {PasswordPolicy.SPECIAL_CHARS}")
    else:
        score += 15
    
    # Check for common weak passwords
    if password.lower() in PasswordPolicy.WEAK_PASSWORDS:
        errors.append("Password is too common and easily guessable")
    
    # Check for repeated characters
    if re.search(r'(.)\\1{2,}', password):
        warnings.append("Avoid repeating the same character multiple times")
        score -= 5
    
    # Check for sequential characters
    if re.search(r'(012|123|234|345|456|567|678|789|890|abc|bcd|cde|def)', password.lower()):
        warnings.append("Avoid sequential characters")
        score -= 5
    
    # Bonus points for length
    if len(password) >= 16:
        score += 15
    elif len(password) >= 12:
        score += 10
    
    # Ensure score is within bounds
    score = max(0, min(100, score))
    
    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "score": score,
        "strength": get_password_strength_label(score)
    }


def get_password_strength_label(score: int) -> str:
    """Get password strength label based on score"""
    if score >= 90:
        return "Very Strong"
    elif score >= 75:
        return "Strong"
    elif score >= 60:
        return "Good"
    elif score >= 40:
        return "Fair"
    else:
        return "Weak"


class LoginAttemptTracker:
    """Track login attempts to prevent brute force attacks"""
    
    def __init__(self):
        self.attempts = {}  # In production, use Redis or database
        self.lockouts = {}
    
    def record_failed_attempt(self, identifier: str) -> None:
        """Record a failed login attempt"""
        now = datetime.utcnow()
        
        if identifier not in self.attempts:
            self.attempts[identifier] = []
        
        # Clean old attempts (older than 1 hour)
        self.attempts[identifier] = [
            attempt for attempt in self.attempts[identifier]
            if now - attempt < timedelta(hours=1)
        ]
        
        self.attempts[identifier].append(now)
        
        # Check if we should lock the account
        max_attempts = getattr(settings, 'MAX_LOGIN_ATTEMPTS', 5)
        lockout_duration = getattr(settings, 'LOCKOUT_DURATION_MINUTES', 15)
        
        if len(self.attempts[identifier]) >= max_attempts:
            self.lockouts[identifier] = now + timedelta(minutes=lockout_duration)
            logger.warning(f"Account locked due to too many failed attempts: {identifier}")
    
    def record_successful_attempt(self, identifier: str) -> None:
        """Record a successful login attempt"""
        # Clear failed attempts on successful login
        if identifier in self.attempts:
            del self.attempts[identifier]
        if identifier in self.lockouts:
            del self.lockouts[identifier]
    
    def is_locked(self, identifier: str) -> bool:
        """Check if an account is currently locked"""
        if identifier not in self.lockouts:
            return False
        
        now = datetime.utcnow()
        if now > self.lockouts[identifier]:
            # Lockout expired
            del self.lockouts[identifier]
            return False
        
        return True
    
    def get_remaining_lockout_time(self, identifier: str) -> Optional[int]:
        """Get remaining lockout time in seconds"""
        if not self.is_locked(identifier):
            return None
        
        now = datetime.utcnow()
        remaining = self.lockouts[identifier] - now
        return int(remaining.total_seconds())


# Global instances
login_tracker = LoginAttemptTracker()
password_handler = UnifiedPasswordHandler()


# Convenience functions for backward compatibility
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password with unified handler"""
    try:
        return password_handler.verify_password_input(
            plain_password, 
            hashed_password, 
            require_client_hash=False  # Allow both for compatibility
        )
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def get_password_hash(password: str) -> str:
    """Generate password hash with unified handler"""
    try:
        server_hash, _ = password_handler.handle_password_input(
            password, 
            require_client_hash=False  # Allow both for compatibility
        )
        return server_hash
    except Exception as e:
        logger.error(f"Password hashing error: {e}")
        raise


def get_client_hashing_info() -> Dict[str, Any]:
    """Get information for frontend to implement client-side hashing"""
    return {
        "algorithm": CLIENT_HASH_ALGORITHM,
        "salt_type": "fixed",
        "salt_source": "environment_variable",
        "implementation_guide": {
            "step1": "Get fixed salt from REACT_APP_PASSWORD_SALT environment variable",
            "step2": "Combine password + salt: `password + salt`",
            "step3": "Create SHA256 hash: `sha256(password + salt).hexdigest()`",
            "step4": "Send hashed password to backend",
            "example_js": """
// JavaScript implementation
function getFixedSalt() {
    return process.env.REACT_APP_PASSWORD_SALT || 'dino-default-salt-2024-secure-hashing';
}

async function hashPassword(password) {
    const salt = getFixedSalt();
    const combined = password + salt;
    const encoder = new TextEncoder();
    const data = encoder.encode(combined);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}
            """,
            "example_python": """
# Python implementation (for testing)
import hashlib
import os

def hash_password(password):
    salt = os.getenv('CLIENT_PASSWORD_SALT', 'dino-default-salt-2024-secure-hashing')
    combined = password + salt
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()
            """
        }
    }


def sanitize_error_message(error_msg: str, is_production: bool = None) -> str:
    """Sanitize error messages to prevent information disclosure"""
    if is_production is None:
        is_production = getattr(settings, 'is_production', False)
    
    if not is_production:
        return error_msg
    
    # In production, return generic error messages
    sensitive_keywords = [
        "database", "sql", "firestore", "connection", "timeout",
        "internal", "server", "exception", "traceback", "stack"
    ]
    
    error_lower = error_msg.lower()
    for keyword in sensitive_keywords:
        if keyword in error_lower:
            return "An error occurred. Please try again later."
    
    return error_msg


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token"""
    return secrets.token_urlsafe(length)