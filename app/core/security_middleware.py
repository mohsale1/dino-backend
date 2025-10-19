"""

Security middleware for enhanced protection

Implements rate limiting, security headers, and request validation

"""

import time

from typing import Dict, Optional

from fastapi import Request, Response, HTTPException, status

try:

  from fastapi.middleware.base import BaseHTTPMiddleware

except ImportError:

  # Fallback for newer FastAPI versions

  from starlette.middleware.base import BaseHTTPMiddleware

from collections import defaultdict, deque

from datetime import datetime, timedelta



from  app.core.config import settings

from app.core.logging_config import get_logger



logger = get_logger(__name__)



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

   

  MAX_REQUEST_SIZE = 10 * 1024 * 1024 # 10MB

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

    self.auth_calls = 10 # Increased from 5 to 10 attempts

    self.auth_period = 300 # 5 minutes

   

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



class DevelopmentModeSecurityMiddleware(BaseHTTPMiddleware):

  """Security middleware for development mode warnings"""

   

  async def dispatch(self, request: Request, call_next):

    response = await call_next(request)

     

    # Add warning headers in development mode

    if not settings.is_jwt_auth_enabled:

      response.headers["X-Development-Mode"] = "true"

      response.headers["X-Security-Warning"] = "JWT authentication disabled"

       

      # Log development mode access

      if request.url.path.startswith("/api/v1/"):

        logger.info(f"Development mode access: {request.method} {request.url.path}")

     

    return response



def get_security_middleware_config() -> Dict[str, any]:
    """Get security middleware configuration"""
    return {
        "rate_limit_enabled": True,
        "rate_limit_calls": getattr(settings, 'RATE_LIMIT_PER_MINUTE', 300),
        "rate_limit_period": 60,
        "auth_rate_limit_enabled": True,
        "security_headers_enabled": True,
        "request_validation_enabled": True,
        "development_warnings_enabled": not settings.is_production
    }
