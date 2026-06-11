"""
Application exception hierarchy.

Every exception carries:
  - http_status  : HTTP status code
  - error_code   : machine-readable snake_case string (stable across releases)
  - message      : human-readable description (may be overridden per raise site)

The global handler in Main.py catches AppException and serialises it as:
  {
    "success":    false,
    "error_code": "RESOURCE_NOT_FOUND",
    "message":    "Order ORD-1-... not found",
  }

Error code registry
-------------------
4xx — client errors
  VALIDATION_ERROR          400  malformed / missing request fields
  BAD_REQUEST               400  generic bad request
  INVALID_CREDENTIALS       401  wrong email or password
  TOKEN_EXPIRED             401  JWT has expired
  TOKEN_INVALID             401  JWT is malformed / signature mismatch
  TOKEN_MISSING             401  Authorization header absent
  JWT_DISABLED              503  JWT auth is turned off server-side
  WORKSPACE_INACTIVE        403  workspace has been deactivated
  PERMISSION_DENIED         403  authenticated but lacks the required permission
  NOT_AUTHENTICATED         401  no valid session / token
  RESOURCE_NOT_FOUND        404  requested entity does not exist or is not visible
  RESOURCE_GONE             410  entity existed but has been permanently removed
  CONFLICT                  409  unique-constraint / duplicate resource
  CANNOT_CANCEL_ORDER       400  order is in a terminal state
  NO_ITEMS_IN_ORDER         400  order submitted with an empty items list
  ITEM_NOT_FOUND_OR_INACTIVE 400 line-item references an unknown / inactive item
  INVALID_ROLE              400  role_id does not exist or is wrong type
  EMAIL_ALREADY_EXISTS      409  email already registered in this workspace
  WORKSPACE_MISMATCH        403  caller tried to access another workspace's data
  PERSONA_MISMATCH          403  persona does not belong to caller's workspace
  PASSWORD_TOO_SHORT        400  new password is fewer than 8 characters
  PASSWORD_SAME             400  new password matches the current password
  PASSWORD_INCORRECT        400  current password verification failed
  USER_NOT_DELETED          400  restore attempted on an active user
  PERSONA_NOT_DELETED       400  restore attempted on an active persona
  BULK_LIMIT_EXCEEDED       400  bulk_create called with > 500 rows

5xx — server errors
  DATABASE_ERROR            503  unhandled SQLAlchemy / DB error
  INTERNAL_ERROR            500  unexpected server-side failure
"""

from fastapi import status


class AppException(Exception):
    """Base class for all application exceptions.

    Attributes
    ----------
    http_status : int
        HTTP status code to return.
    error_code : str
        Stable machine-readable identifier (UPPER_SNAKE_CASE).
    message : str
        Human-readable description sent to the client.
    """

    http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.__class__.message
        super().__init__(self.message)


# ---------------------------------------------------------------------------
# 400 Bad Request
# ---------------------------------------------------------------------------

class ValidationError(AppException):
    http_status = status.HTTP_400_BAD_REQUEST
    error_code = "VALIDATION_ERROR"
    message = "Request validation failed"


class BadRequestError(AppException):
    http_status = status.HTTP_400_BAD_REQUEST
    error_code = "BAD_REQUEST"
    message = "Bad request"


class NoItemsInOrderError(AppException):
    http_status = status.HTTP_400_BAD_REQUEST
    error_code = "NO_ITEMS_IN_ORDER"
    message = "Order must contain at least one item"


class ItemNotFoundOrInactiveError(AppException):
    http_status = status.HTTP_400_BAD_REQUEST
    error_code = "ITEM_NOT_FOUND_OR_INACTIVE"
    message = "One or more items were not found or are inactive"


class CannotCancelOrderError(AppException):
    http_status = status.HTTP_400_BAD_REQUEST
    error_code = "CANNOT_CANCEL_ORDER"
    message = "Cannot cancel an order that is already in a terminal state"


class InvalidRoleError(AppException):
    http_status = status.HTTP_400_BAD_REQUEST
    error_code = "INVALID_ROLE"
    message = "Role does not exist or is not an application role"


class PasswordTooShortError(AppException):
    http_status = status.HTTP_400_BAD_REQUEST
    error_code = "PASSWORD_TOO_SHORT"
    message = "Password must be at least 8 characters"


class PasswordSameError(AppException):
    http_status = status.HTTP_400_BAD_REQUEST
    error_code = "PASSWORD_SAME"
    message = "New password must differ from the current password"


class PasswordIncorrectError(AppException):
    http_status = status.HTTP_400_BAD_REQUEST
    error_code = "PASSWORD_INCORRECT"
    message = "Current password is incorrect"


class UserNotDeletedError(AppException):
    http_status = status.HTTP_400_BAD_REQUEST
    error_code = "USER_NOT_DELETED"
    message = "User is not deleted"


class PersonaNotDeletedError(AppException):
    http_status = status.HTTP_400_BAD_REQUEST
    error_code = "PERSONA_NOT_DELETED"
    message = "Persona is not deleted"


class BulkLimitExceededError(AppException):
    http_status = status.HTTP_400_BAD_REQUEST
    error_code = "BULK_LIMIT_EXCEEDED"
    message = "Bulk create limit is 500 rows"


# ---------------------------------------------------------------------------
# 401 Unauthorized
# ---------------------------------------------------------------------------

class NotAuthenticatedError(AppException):
    http_status = status.HTTP_401_UNAUTHORIZED
    error_code = "NOT_AUTHENTICATED"
    message = "Authentication required"


class InvalidCredentialsError(AppException):
    http_status = status.HTTP_401_UNAUTHORIZED
    error_code = "INVALID_CREDENTIALS"
    message = "Invalid email or password"


class TokenExpiredError(AppException):
    http_status = status.HTTP_401_UNAUTHORIZED
    error_code = "TOKEN_EXPIRED"
    message = "Token has expired"


class TokenInvalidError(AppException):
    http_status = status.HTTP_401_UNAUTHORIZED
    error_code = "TOKEN_INVALID"
    message = "Invalid token"


class TokenMissingError(AppException):
    http_status = status.HTTP_401_UNAUTHORIZED
    error_code = "TOKEN_MISSING"
    message = "Authorization credentials are missing"


# ---------------------------------------------------------------------------
# 403 Forbidden
# ---------------------------------------------------------------------------

class PermissionDeniedError(AppException):
    http_status = status.HTTP_403_FORBIDDEN
    error_code = "PERMISSION_DENIED"
    message = "You do not have permission to perform this action"


class WorkspaceInactiveError(AppException):
    http_status = status.HTTP_403_FORBIDDEN
    error_code = "WORKSPACE_INACTIVE"
    message = "Your workspace is inactive. Please contact support"


class WorkspaceMismatchError(AppException):
    http_status = status.HTTP_403_FORBIDDEN
    error_code = "WORKSPACE_MISMATCH"
    message = "Access denied"


class PersonaMismatchError(AppException):
    http_status = status.HTTP_403_FORBIDDEN
    error_code = "PERSONA_MISMATCH"
    message = "Persona does not belong to your workspace"


# ---------------------------------------------------------------------------
# 404 Not Found
# ---------------------------------------------------------------------------

class NotFoundError(AppException):
    http_status = status.HTTP_404_NOT_FOUND
    error_code = "RESOURCE_NOT_FOUND"
    message = "Resource not found"


# ---------------------------------------------------------------------------
# 409 Conflict
# ---------------------------------------------------------------------------

class ConflictError(AppException):
    http_status = status.HTTP_409_CONFLICT
    error_code = "CONFLICT"
    message = "Resource already exists"


class EmailAlreadyExistsError(AppException):
    http_status = status.HTTP_409_CONFLICT
    error_code = "EMAIL_ALREADY_EXISTS"
    message = "Email already registered"


# ---------------------------------------------------------------------------
# 410 Gone
# ---------------------------------------------------------------------------

class ResourceGoneError(AppException):
    http_status = status.HTTP_410_GONE
    error_code = "RESOURCE_GONE"
    message = "This resource is no longer available"


# ---------------------------------------------------------------------------
# 503 Service Unavailable
# ---------------------------------------------------------------------------

class JwtDisabledError(AppException):
    http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "JWT_DISABLED"
    message = "JWT authentication is disabled"


class DatabaseError(AppException):
    http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "DATABASE_ERROR"
    message = "Service temporarily unavailable"


# ---------------------------------------------------------------------------
# 500 Internal Server Error
# ---------------------------------------------------------------------------

class InternalError(AppException):
    http_status = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "INTERNAL_ERROR"
    message = "An unexpected error occurred"
