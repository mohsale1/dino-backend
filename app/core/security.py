"""
Security utilities for authentication and authorization
Simplified password handling with BCrypt only
"""
import secrets
import string
import re
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# BCrypt context for password hashing
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=getattr(settings, 'BCRYPT_ROUNDS', 12)
)

# JWT token security
security = HTTPBearer()


class PasswordPolicy:
    """Centralized password policy configuration"""
    
    MIN_LENGTH = 8
    MAX_LENGTH = 128
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGITS = True
    REQUIRE_SPECIAL = False  # Made optional for better UX
    SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
    # Common weak passwords to reject
    WEAK_PASSWORDS = {
        "password", "123456", "password123", "admin", "qwerty",
        "letmein", "welcome", "monkey", "dragon", "master",
        "password1", "123456789", "12345678", "admin123"
    }


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
    
    if PasswordPolicy.REQUIRE_DIGITS and not re.search(r'\d', password):
        errors.append("Password must contain at least one digit")
    else:
        score += 15
    
    if PasswordPolicy.REQUIRE_SPECIAL and not re.search(f'[{re.escape(PasswordPolicy.SPECIAL_CHARS)}]', password):
        errors.append(f"Password must contain at least one special character: {PasswordPolicy.SPECIAL_CHARS}")
    elif re.search(f'[{re.escape(PasswordPolicy.SPECIAL_CHARS)}]', password):
        score += 15
    
    # Check for common weak passwords
    if password.lower() in PasswordPolicy.WEAK_PASSWORDS:
        errors.append("Password is too common and easily guessable")
    
    # Check for repeated characters
    if re.search(r'(.)\1{2,}', password):
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


def get_password_hash(password: str) -> str:
    """
    Hash password using BCrypt
    
    Args:
        password: Plain text password
        
    Returns:
        BCrypt hashed password
    """
    try:
        # Validate password strength
        validation_result = validate_password_strength(password)
        if not validation_result["is_valid"]:
            raise ValueError(f"Password validation failed: {', '.join(validation_result['errors'])}")
        
        # Hash with BCrypt
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Password hashing error: {e}")
        raise


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against its BCrypt hash
    
    Args:
        plain_password: Plain text password from user
        hashed_password: BCrypt hash from database
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


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


class SecurityValidator:
    """Security validation utilities"""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_password_strength(password: str) -> Dict[str, Any]:
        """Validate password strength - delegates to validate_password_strength function"""
        return validate_password_strength(password)
    
    @staticmethod
    def sanitize_input(input_str: str) -> str:
        """Sanitize user input to prevent injection attacks"""
        if not isinstance(input_str, str):
            return str(input_str)
        
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\'`]', '', input_str)
        
        # Limit length
        if len(sanitized) > 1000:
            sanitized = sanitized[:1000]
        
        return sanitized.strip()


class SecurityHeaders:
    """Security headers middleware"""
    
    @staticmethod
    def add_security_headers(response):
        """Add security headers to response"""
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Content Security Policy (basic)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' https:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none';"
        )
        
        return response


# Global instances
login_tracker = LoginAttemptTracker()
security_validator = SecurityValidator()
security_headers = SecurityHeaders()


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


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token with enhanced security"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Add security claims
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),  # Issued at
        "nbf": datetime.utcnow(),  # Not before
        "iss": "dino-api",         # Issuer
        "aud": "dino-client"       # Audience
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """Verify and decode JWT token with enhanced security"""
    try:
        # First try with audience and issuer validation
        try:
            payload = jwt.decode(
                token, 
                settings.SECRET_KEY, 
                algorithms=[settings.ALGORITHM],
                audience="dino-client",
                issuer="dino-api"
            )
        except JWTError as e:
            # Fallback: try without audience/issuer validation for backward compatibility
            logger.info(f"JWT verification with audience/issuer failed ({e}), trying without validation")
            try:
                payload = jwt.decode(
                    token, 
                    settings.SECRET_KEY, 
                    algorithms=[settings.ALGORITHM]
                )
            except JWTError as fallback_error:
                # If both fail, raise the original error
                logger.error(f"JWT verification failed completely: {fallback_error}")
                raise JWTError(f"Token verification failed: {fallback_error}")
        
        # Additional security checks
        if not payload.get("sub"):
            raise JWTError("Missing subject claim")
        
        return payload
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=sanitize_error_message("Could not validate credentials"),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Get current user ID from JWT token"""
    token = credentials.credentials
    payload = verify_token(token)
    user_id: str = payload.get("sub")
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_id


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Get current authenticated user with enhanced validation
    """
    try:
        token = credentials.credentials
        
        # Use the enhanced verify_token function
        try:
            payload = verify_token(token)
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user from database
        from app.database.repository_manager import get_user_repo
        user_repo = get_user_repo()
        user = await user_repo.get_by_id(user_id)
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if user is active
        if not user.get('is_active', True):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is deactivated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Resolve role from role_id if not already present
        if 'role' not in user and user.get('role_id'):
            try:
                resolved_role = await _get_user_role(user)
                user['role'] = resolved_role
            except Exception as e:
                logger.warning(f"Failed to resolve role for user {user.get('id')}: {e}")
                user['role'] = 'operator'
        elif 'role' not in user:
            user['role'] = 'operator'
        
        # Remove sensitive information
        user.pop('hashed_password', None)
        
        return user
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_admin_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Get current user with admin privileges"""
    # Get the actual role name from role_id
    user_role = await _get_user_role(current_user)
    
    if user_role not in ['admin', 'superadmin']:
        logger.warning(f"Admin access denied for user {current_user.get('id')} with role: {user_role}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    return current_user


async def get_current_superadmin_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Get current user with superadmin privileges"""
    # Get the actual role name from role_id
    user_role = await _get_user_role(current_user)
    
    if user_role != 'superadmin':
        logger.warning(f"Superadmin access denied for user {current_user.get('id')} with role: {user_role}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin privileges required"
        )
    
    return current_user


async def validate_venue_access(user: Dict[str, Any], venue_id: str) -> bool:
    """
    Validate if user has access to specific venue
    Implements strict venue-based data isolation
    """
    try:
        # Get the actual role name from role_id
        user_role = await _get_user_role(user)
        
        # SuperAdmin has access to all venues (for system management only)
        if user_role == 'superadmin':
            return True
        
        # Get user's assigned venues from venue_ids list
        user_venue_ids = user.get('venue_ids', [])
        
        # Check if user has access to this venue
        if venue_id in user_venue_ids:
            return True
        
        # No workspace-level access in new hierarchy
        # Users must be explicitly assigned to venues
        
        return False
        
    except Exception as e:
        logger.error(f"Error validating venue access: {e}")
        return False


async def require_venue_access(venue_id: str, current_user: Dict[str, Any]) -> None:
    """
    Require venue access for the current user
    Raises HTTPException if access is denied
    """
    has_access = await validate_venue_access(current_user, venue_id)
    
    if not has_access:
        logger.warning(f"Venue access denied for user {current_user.get('id')} to venue {venue_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You don't have permission to access this venue"
        )


async def get_user_accessible_venues(user: Dict[str, Any]) -> List[str]:
    """Get list of venue IDs user has access to"""
    try:
        # Get the actual role name from role_id
        user_role = await _get_user_role(user)
        
        # SuperAdmin gets all venues (for system management)
        if user_role == 'superadmin':
            from app.database.repository_manager import get_venue_repo
            venue_repo = get_venue_repo()
            all_venues = await venue_repo.get_all()
            return [venue['id'] for venue in all_venues if venue.get('is_active', True)]
        
        # Get user's assigned venues from venue_ids list
        user_venue_ids = user.get('venue_ids', [])
        return user_venue_ids
        
    except Exception as e:
        logger.error(f"Error getting accessible venues: {e}")
        return []


async def get_user_primary_venue(current_user: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Get user's primary venue (first venue in their venue_ids list)"""
    try:
        # Get user's venue IDs
        user_venue_ids = current_user.get('venue_ids', [])
        
        if not user_venue_ids:
            return None
        
        # Get first venue as primary
        primary_venue_id = user_venue_ids[0]
        
        # Get venue details
        from app.database.repository_manager import get_venue_repo
        venue_repo = get_venue_repo()
        venue = await venue_repo.get_by_id(primary_venue_id)
        
        return venue
        
    except Exception as e:
        logger.error(f"Error getting user primary venue: {e}")
        return None


async def _get_user_role(user_data: Dict[str, Any]) -> str:
    """Get user role from role_id"""
    role_id = user_data.get("role_id")
    if not role_id:
        return "operator"  # Default role
    
    try:
        from app.database.repository_manager import get_role_repo
        role_repo = get_role_repo()
        role = await role_repo.get_by_id(role_id)
        
        if role:
            return role.get("name", "operator")
    except Exception as e:
        logger.warning(f"Failed to get user role: {e}")
    
    return "operator"


async def get_optional_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    Get current user optionally (for public endpoints that can work with or without auth)
    """
    try:
        # Try to get authorization header
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return None
        
        token = authorization.replace("Bearer ", "")
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        
        # Get user from database
        from app.database.repository_manager import get_user_repo
        user_repo = get_user_repo()
        user = await user_repo.get_by_id(user_id)
        
        if user and user.get('is_active', True):
            user.pop('hashed_password', None)
            return user
        
        return None
        
    except Exception as e:
        logger.debug(f"Optional auth failed: {e}")
        return None

async def verify_venue_access(venue_id: str, current_user: Dict[str, Any]) -> bool:
    """Verify if current user has access to venue (legacy function)"""
    return await validate_venue_access(current_user, venue_id)


async def verify_workspace_access(workspace_id: str, current_user: Dict[str, Any]) -> bool:
    """Verify if current user has access to workspace"""
    from app.database.repository_manager import get_workspace_repo
    
    workspace_repo = get_workspace_repo()
    workspace = await workspace_repo.get_by_id(workspace_id)
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    # Get user role
    user_role = await _get_user_role(current_user)
    
    # SuperAdmin can access all workspaces
    if user_role == "superadmin":
        return True
    
    # Admin and operator roles have limited workspace access
    if user_role in ["admin", "operator"]:
        return True
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not enough permissions to access this workspace"
    )


# =============================================================================
# SECURITY MIDDLEWARE
# =============================================================================

try:
    from fastapi.middleware.base import BaseHTTPMiddleware
except ImportError:
    # Fallback for newer FastAPI versions
    from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict, deque


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware to prevent abuse"""
    
    def __init__(self, app, calls: int = 300, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients = defaultdict(deque)
    
    async def dispatch(self, request: Request, call_next):
        # Get client identifier (IP address)
        client_ip = self.get_client_ip(request)
        
        # Check rate limit
        if self.is_rate_limited(client_ip):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": str(self.period)}
            )
        
        # Process request
        response = await call_next(request)
        return response
    
    def get_client_ip(self, request: Request) -> str:
        """Get client IP address with proxy support"""
        # Check for forwarded headers (common in production)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        return request.client.host if request.client else "unknown"
    
    def is_rate_limited(self, client_ip: str) -> bool:
        """Check if client is rate limited"""
        now = time.time()
        
        # Clean old entries
        while self.clients[client_ip] and self.clients[client_ip][0] <= now - self.period:
            self.clients[client_ip].popleft()
        
        # Check if limit exceeded
        if len(self.clients[client_ip]) >= self.calls:
            return True
        
        # Add current request
        self.clients[client_ip].append(now)
        return False


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # HSTS for HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # CSP for API (restrictive)
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none';"
        
        return response


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Validate and sanitize incoming requests"""
    
    MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB
    SUSPICIOUS_PATTERNS = [
        # SQL injection patterns
        r"(\bunion\b|\bselect\b|\binsert\b|\bdelete\b|\bdrop\b|\bupdate\b)",
        # XSS patterns
        r"(<script|javascript:|on\w+\s*=)",
        # Path traversal
        r"(\.\./|\.\.\\)",
        # Command injection
        r"(;|\||&|\$\(|\`)"
    ]
    
    async def dispatch(self, request: Request, call_next):
        # Check request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.MAX_REQUEST_SIZE:
            logger.warning(f"Request too large: {content_length} bytes from {request.client.host}")
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Request too large"
            )
        
        # Validate request path and query parameters
        self.validate_request_data(request)
        
        response = await call_next(request)
        return response
    
    def validate_request_data(self, request: Request):
        """Validate request data for suspicious patterns"""
        import re
        
        # Check URL path
        path = str(request.url.path)
        for pattern in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, path, re.IGNORECASE):
                logger.warning(f"Suspicious pattern in path: {path} from {request.client.host}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid request"
                )
        
        # Check query parameters
        for key, value in request.query_params.items():
            for pattern in self.SUSPICIOUS_PATTERNS:
                if re.search(pattern, f"{key}={value}", re.IGNORECASE):
                    logger.warning(f"Suspicious pattern in query: {key}={value} from {request.client.host}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid request parameters"
                    )


class AuthenticationRateLimitMiddleware(BaseHTTPMiddleware):
    """Special rate limiting for authentication endpoints"""
    
    def __init__(self, app):
        super().__init__(app)
        self.auth_attempts = defaultdict(deque)
        self.auth_calls = 10  # 10 attempts
        self.auth_period = 300  # 5 minutes
    
    async def dispatch(self, request: Request, call_next):
        # Only apply to auth endpoints
        if not request.url.path.startswith("/api/v1/auth/"):
            return await call_next(request)
        
        # Skip for non-sensitive endpoints
        if request.url.path in ["/api/v1/auth/me", "/api/v1/auth/permissions"]:
            return await call_next(request)
        
        client_ip = self.get_client_ip(request)
        
        # Check auth rate limit
        if self.is_auth_rate_limited(client_ip):
            logger.warning(f"Auth rate limit exceeded for IP: {client_ip}")
            from fastapi import Response
            return Response(
                content='{"detail": "Too many authentication attempts. Please try again later."}',
                status_code=429,
                headers={
                    "Content-Type": "application/json",
                    "Retry-After": str(self.auth_period)
                }
            )
        
        try:
            response = await call_next(request)
            
            # Record failed auth attempts
            if response.status_code in [401, 403] and request.method == "POST":
                self.record_auth_attempt(client_ip)
            
            return response
        except Exception as e:
            logger.error(f"Internal server error occurred: {e}")
            from fastapi import Response
            return Response(
                content='{"detail": "Internal server error occurred"}',
                status_code=500,
                headers={"Content-Type": "application/json"}
            )
    
    def get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    def is_auth_rate_limited(self, client_ip: str) -> bool:
        """Check if client is rate limited for auth"""
        now = time.time()
        
        # Clean old entries
        while (self.auth_attempts[client_ip] and 
               self.auth_attempts[client_ip][0] <= now - self.auth_period):
            self.auth_attempts[client_ip].popleft()
        
        return len(self.auth_attempts[client_ip]) >= self.auth_calls
    
    def record_auth_attempt(self, client_ip: str):
        """Record a failed auth attempt"""
        try:
            self.auth_attempts[client_ip].append(time.time())
            logger.info(f"Recorded failed auth attempt for IP: {client_ip}")
        except Exception as e:
            logger.error(f"Failed to record auth attempt: {e}")


def get_security_middleware_config() -> Dict[str, any]:
    """Get security middleware configuration"""
    return {
        "rate_limit_enabled": True,
        "rate_limit_calls": getattr(settings, 'RATE_LIMIT_PER_MINUTE', 300),
        "rate_limit_period": 60,
        "auth_rate_limit_enabled": True,
        "security_headers_enabled": True,
        "request_validation_enabled": True
    }