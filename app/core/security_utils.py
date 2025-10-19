"""
Security Utilities
Additional security functions and middleware for production deployment
"""
import re
import hashlib
import secrets
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from fastapi import HTTPException, status, Request
from fastapi.security.utils import get_authorization_scheme_param

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class SecurityValidator:
    """Security validation utilities"""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_password_strength(password: str) -> Dict[str, Any]:
        """Validate password strength"""
        result = {
            "is_valid": True,
            "errors": [],
            "score": 0
        }
        
        if len(password) < 8:
            result["errors"].append("Password must be at least 8 characters long")
            result["is_valid"] = False
        else:
            result["score"] += 1
        
        if not re.search(r'[A-Z]', password):
            result["errors"].append("Password must contain at least one uppercase letter")
            result["is_valid"] = False
        else:
            result["score"] += 1
        
        if not re.search(r'[a-z]', password):
            result["errors"].append("Password must contain at least one lowercase letter")
            result["is_valid"] = False
        else:
            result["score"] += 1
        
        if not re.search(r'\d', password):
            result["errors"].append("Password must contain at least one number")
            result["is_valid"] = False
        else:
            result["score"] += 1
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            result["errors"].append("Password must contain at least one special character")
            result["is_valid"] = False
        else:
            result["score"] += 1
        
        return result
    
    @staticmethod
    def sanitize_input(input_str: str) -> str:
        """Sanitize user input to prevent injection attacks"""
        if not isinstance(input_str, str):
            return str(input_str)
        
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\']', '', input_str)
        
        # Limit length
        if len(sanitized) > 1000:
            sanitized = sanitized[:1000]
        
        return sanitized.strip()
    
    @staticmethod
    def validate_file_upload(filename: str, content_type: str, max_size_mb: int = 10) -> Dict[str, Any]:
        """Validate file upload security"""
        result = {
            "is_valid": True,
            "errors": []
        }
        
        # Check file extension
        allowed_extensions = {
            'image/jpeg': ['.jpg', '.jpeg'],
            'image/png': ['.png'],
            'image/gif': ['.gif'],
            'image/webp': ['.webp'],
            'application/pdf': ['.pdf'],
            'text/plain': ['.txt'],
            'application/json': ['.json']
        }
        
        if content_type not in allowed_extensions:
            result["errors"].append(f"File type {content_type} not allowed")
            result["is_valid"] = False
            return result
        
        # Check file extension matches content type
        file_ext = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
        if file_ext not in allowed_extensions[content_type]:
            result["errors"].append("File extension doesn't match content type")
            result["is_valid"] = False
        
        # Check for dangerous filenames
        dangerous_patterns = [
            r'\.\./',  # Path traversal
            r'[<>:"|?*]',  # Invalid filename characters
            r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$',  # Windows reserved names
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, filename, re.IGNORECASE):
                result["errors"].append("Invalid filename")
                result["is_valid"] = False
                break
        
        return result


class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self.requests = {}
        self.cleanup_interval = timedelta(minutes=5)
        self.last_cleanup = datetime.utcnow()
    
    def is_allowed(self, identifier: str, limit: int, window_minutes: int = 1) -> bool:
        """Check if request is allowed under rate limit"""
        now = datetime.utcnow()
        
        # Cleanup old entries periodically
        if now - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_entries()
            self.last_cleanup = now
        
        # Get or create request history for this identifier
        if identifier not in self.requests:
            self.requests[identifier] = []
        
        request_history = self.requests[identifier]
        
        # Remove requests outside the window
        window_start = now - timedelta(minutes=window_minutes)
        request_history[:] = [req_time for req_time in request_history if req_time > window_start]
        
        # Check if under limit
        if len(request_history) >= limit:
            return False
        
        # Add current request
        request_history.append(now)
        return True
    
    def _cleanup_old_entries(self):
        """Remove old entries to prevent memory leaks"""
        cutoff = datetime.utcnow() - timedelta(hours=1)
        
        for identifier in list(self.requests.keys()):
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier] 
                if req_time > cutoff
            ]
            
            # Remove empty entries
            if not self.requests[identifier]:
                del self.requests[identifier]


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
        
        # HSTS (only in production with HTTPS)
        # response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


class InputSanitizer:
    """Input sanitization utilities"""
    
    @staticmethod
    def sanitize_dict(data: Dict[str, Any], allowed_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """Sanitize dictionary input"""
        if not isinstance(data, dict):
            return {}
        
        sanitized = {}
        
        for key, value in data.items():
            # Skip if field not allowed
            if allowed_fields and key not in allowed_fields:
                continue
            
            # Sanitize key
            clean_key = SecurityValidator.sanitize_input(str(key))
            
            # Sanitize value based on type
            if isinstance(value, str):
                clean_value = SecurityValidator.sanitize_input(value)
            elif isinstance(value, dict):
                clean_value = InputSanitizer.sanitize_dict(value, allowed_fields)
            elif isinstance(value, list):
                clean_value = [
                    SecurityValidator.sanitize_input(str(item)) if isinstance(item, str) else item
                    for item in value[:100]  # Limit list size
                ]
            else:
                clean_value = value
            
            sanitized[clean_key] = clean_value
        
        return sanitized


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token"""
    return secrets.token_urlsafe(length)


def hash_sensitive_data(data: str, salt: Optional[str] = None) -> str:
    """Hash sensitive data with salt"""
    if salt is None:
        salt = secrets.token_hex(16)
    
    # Combine data and salt
    combined = f"{data}{salt}"
    
    # Hash with SHA-256
    hashed = hashlib.sha256(combined.encode()).hexdigest()
    
    return f"{salt}:{hashed}"


def verify_hashed_data(data: str, hashed_data: str) -> bool:
    """Verify hashed data"""
    try:
        salt, expected_hash = hashed_data.split(':', 1)
        combined = f"{data}{salt}"
        actual_hash = hashlib.sha256(combined.encode()).hexdigest()
        return actual_hash == expected_hash
    except ValueError:
        return False


def log_security_event(event_type: str, details: Dict[str, Any], request: Optional[Request] = None):
    """Log security-related events"""
    log_data = {
        "event_type": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        "details": details
    }
    
    if request:
        log_data.update({
            "client_ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
            "path": str(request.url.path),
            "method": request.method
        })
    
    logger.warning(f"Security Event: {event_type}", extra=log_data)


# Global instances
security_validator = SecurityValidator()
rate_limiter = RateLimiter()
input_sanitizer = InputSanitizer()
security_headers = SecurityHeaders()