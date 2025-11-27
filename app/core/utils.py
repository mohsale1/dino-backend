"""
Core Utilities
Essential utility functions used across the application
Refactored to remove redundancy and improve maintainability
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from fastapi import HTTPException, status

from app.core.logging import get_logger
from app.models.requests import UserResponseDTO

logger = get_logger(__name__)


# =============================================================================
# VALIDATION UTILITIES
# =============================================================================

def validate_required_fields(
    data: Dict[str, Any],
    required_fields: List[str]
) -> List[str]:
    """
    Validate that all required fields are present and not empty
    
    Args:
        data: Data dictionary to validate
        required_fields: List of required field names
    
    Returns:
        List of missing field names
    """
    missing_fields = []
    
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == "":
            missing_fields.append(field)
    
    return missing_fields


def raise_validation_error(
    missing_fields: List[str],
    custom_message: Optional[str] = None
):
    """
    Raise HTTPException for validation errors
    
    Args:
        missing_fields: List of missing field names
        custom_message: Custom error message
    """
    if missing_fields:
        if custom_message:
            detail = custom_message
        else:
            detail = f"Missing required fields: {', '.join(missing_fields)}"
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


# =============================================================================
# TIMESTAMP UTILITIES
# =============================================================================

def add_timestamps(
    data: Dict[str, Any],
    is_update: bool = False
) -> Dict[str, Any]:
    """
    Add creation and update timestamps
    
    Args:
        data: Data dictionary to add timestamps to
        is_update: Whether this is an update operation
    
    Returns:
        Data with timestamps added
    """
    now = datetime.now(timezone.utc)
    
    if not is_update:
        data['created_at'] = now
    
    data['updated_at'] = now
    return data


def get_current_timestamp() -> datetime:
    """Get current UTC timestamp"""
    return datetime.now(timezone.utc)


# =============================================================================
# DATA CLEANING UTILITIES
# =============================================================================

def remove_sensitive_fields(
    data: Dict[str, Any],
    sensitive_fields: List[str] = None
) -> Dict[str, Any]:
    """
    Remove sensitive fields from data
    
    Args:
        data: Data dictionary
        sensitive_fields: List of sensitive field names
    
    Returns:
        Data with sensitive fields removed
    """
    if sensitive_fields is None:
        sensitive_fields = ['hashed_password', 'password', 'secret_key']
    
    cleaned_data = data.copy()
    for field in sensitive_fields:
        cleaned_data.pop(field, None)
    
    return cleaned_data


def sanitize_dict(
    data: Dict[str, Any],
    allowed_fields: Optional[List[str]] = None,
    exclude_fields: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Sanitize dictionary by including only allowed fields or excluding specific fields
    
    Args:
        data: Data dictionary
        allowed_fields: List of allowed field names (whitelist)
        exclude_fields: List of fields to exclude (blacklist)
    
    Returns:
        Sanitized data dictionary
    """
    if allowed_fields:
        return {k: v for k, v in data.items() if k in allowed_fields}
    
    if exclude_fields:
        return {k: v for k, v in data.items() if k not in exclude_fields}
    
    return data.copy()


# =============================================================================
# RESPONSE UTILITIES (Backward Compatibility)
# =============================================================================

def create_success_response(message: str, data: Any = None) -> Dict[str, Any]:
    """
    Create standardized success response
    DEPRECATED: Use app.core.response_builder instead
    """
    from app.core.response_builder import response_builder
    return response_builder.success(message, data)


def create_error_response(
    message: str,
    error_code: str = None,
    details: Any = None
) -> Dict[str, Any]:
    """
    Create standardized error response
    DEPRECATED: Use app.core.response_builder instead
    """
    from app.core.response_builder import response_builder
    return response_builder.error(message, error_code, details)


# =============================================================================
# PAGINATION UTILITIES (Backward Compatibility)
# =============================================================================

def paginate_list(
    data: List[Dict[str, Any]],
    page: int = 1,
    page_size: int = 20
) -> tuple:
    """
    Paginate a list of data
    DEPRECATED: Use app.core.query_builder instead
    """
    from app.core.query_builder import query_builder
    return query_builder.paginate(data, page, page_size)


def apply_search_filter(
    data: List[Dict[str, Any]],
    search: str,
    search_fields: List[str]
) -> List[Dict[str, Any]]:
    """
    Apply search filter to data
    DEPRECATED: Use app.core.query_builder instead
    """
    from app.core.query_builder import query_builder
    return query_builder.apply_search_filter(data, search, search_fields)


# =============================================================================
# LOGGING UTILITIES
# =============================================================================

def log_operation(operation: str, entity_id: str = None, **kwargs):
    """
    Log service operations consistently
    
    Args:
        operation: Operation description
        entity_id: Optional entity ID
        **kwargs: Additional log data
    """
    log_data = {"operation": operation}
    if entity_id:
        log_data["entity_id"] = entity_id
    log_data.update(kwargs)
    
    logger.info(f"{operation} completed", extra=log_data)


# =============================================================================
# PERMISSION UTILITIES (Backward Compatibility)
# =============================================================================

async def validate_user_role(
    current_user: Dict[str, Any],
    required_roles: List[str],
    error_message: str = "Insufficient permissions"
) -> str:
    """
    Generic role validation utility
    DEPRECATED: Use app.core.permissions instead
    """
    from app.core.permissions import permission_checker
    return await permission_checker.validate_user_role(
        current_user, required_roles, error_message
    )


async def validate_admin_or_superadmin(current_user: Dict[str, Any]) -> str:
    """
    Validate that user is admin or superadmin
    DEPRECATED: Use app.core.permissions instead
    """
    from app.core.permissions import permission_checker
    return await permission_checker.validate_admin_or_superadmin(current_user)


# =============================================================================
# RESOURCE UTILITIES
# =============================================================================

async def safe_get_resource(
    repo: Any,
    resource_id: str,
    resource_name: str = "Resource"
) -> Dict[str, Any]:
    """
    Safely get a resource by ID with consistent error handling
    
    Args:
        repo: Repository instance
        resource_id: ID of resource to get
        resource_name: Name of resource for error messages
        
    Returns:
        Dict[str, Any]: Resource data
        
    Raises:
        HTTPException: If resource not found
    """
    resource = await repo.get_by_id(resource_id)
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource_name} not found"
        )
    return resource


async def validate_resource_exists(
    repo: Any,
    resource_id: str,
    resource_name: str = "Resource"
) -> Dict[str, Any]:
    """Alias for safe_get_resource for consistency"""
    return await safe_get_resource(repo, resource_id, resource_name)


async def validate_uniqueness(
    repo: Any,
    field: str,
    value: str,
    exclude_id: Optional[str] = None,
    error_message: Optional[str] = None
) -> None:
    """
    Generic uniqueness validation for any field
    
    Args:
        repo: Repository instance
        field: Field name to check
        value: Value to check for uniqueness
        exclude_id: ID to exclude from check (for updates)
        error_message: Custom error message
    """
    existing = await repo.query([(field, "==", value)])
    
    if exclude_id:
        existing = [item for item in existing if item.get("id") != exclude_id]
    
    if existing:
        msg = error_message or f"{field.replace('_', ' ').title()} already in use"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )


# =============================================================================
# GENERIC CRUD OPERATIONS
# =============================================================================

async def generic_get_paginated(
    repo: Any,
    page: int,
    page_size: int,
    filters: Optional[Dict[str, Any]] = None,
    search: Optional[str] = None,
    search_fields: Optional[List[str]] = None
) -> tuple:
    """
    Generic paginated get with filtering and search
    
    Returns:
        tuple: (items, pagination_meta)
    """
    from app.core.query_builder import query_builder
    
    # Build query filters
    query_filters = query_builder.build_filters(filters)
    
    # Get items
    if query_filters:
        items = await repo.query(query_filters)
    else:
        items = await repo.get_all()
    
    # Apply search if provided
    if search and search_fields:
        items = query_builder.apply_search_filter(items, search, search_fields)
    
    # Paginate
    return query_builder.paginate(items, page, page_size)


async def generic_create(
    repo: Any,
    data: Dict[str, Any],
    prepare_func: Optional[callable] = None,
    validate_func: Optional[callable] = None
) -> Dict[str, Any]:
    """
    Generic create operation with optional preparation and validation
    
    Returns:
        Created item data
    """
    if prepare_func:
        data = await prepare_func(data)
    
    if validate_func:
        await validate_func(data)
    
    created = await repo.create(data)
    return created if isinstance(created, dict) else await repo.get_by_id(created)


async def generic_update(
    repo: Any,
    item_id: str,
    data: Dict[str, Any],
    validate_func: Optional[callable] = None,
    resource_name: str = "Resource"
) -> Dict[str, Any]:
    """
    Generic update operation with validation
    
    Returns:
        Updated item data
    """
    # Verify exists
    existing = await safe_get_resource(repo, item_id, resource_name)
    
    if validate_func:
        await validate_func(existing, data)
    
    await repo.update(item_id, data)
    return await repo.get_by_id(item_id)


async def generic_delete(
    repo: Any,
    item_id: str,
    soft_delete: bool = True,
    validate_func: Optional[callable] = None,
    resource_name: str = "Resource"
) -> bool:
    """
    Generic delete operation (soft or hard)
    
    Returns:
        True if successful
    """
    existing = await safe_get_resource(repo, item_id, resource_name)
    
    if validate_func:
        await validate_func(existing)
    
    if soft_delete:
        await repo.update(item_id, {"is_active": False})
    else:
        await repo.delete(item_id)
    
    return True


# =============================================================================
# USER UTILITIES
# =============================================================================

def convert_user_to_response_dto(user_data: Dict[str, Any]) -> UserResponseDTO:
    """
    Convert user dictionary to UserResponseDTO with proper field handling
    
    Handles:
    - Legacy field mapping (venu_ids -> venue_ids, role -> role_id)
    - Missing required fields with sensible defaults
    - Sensitive data removal
    - Proper error handling
    
    Args:
        user_data: Raw user data dictionary from database
        
    Returns:
        UserResponseDTO: Properly formatted user response object
        
    Raises:
        HTTPException: If user data conversion fails
    """
    # Create a copy to avoid modifying original
    data = user_data.copy()
    
    # Remove sensitive data
    data.pop("hashed_password", None)
    data.pop("password_salt", None)
    
    # Handle legacy field mapping for venue_ids
    if "venu_ids" in data and "venue_ids" not in data:
        data["venue_ids"] = data.get("venu_ids", [])
    
    # Ensure venue_ids exists (required field)
    if "venue_ids" not in data:
        data["venue_ids"] = data.get("venu_ids", [])
    
    # Handle legacy role field mapping
    if not data.get("role_id") and "role" in data:
        legacy_role = data.get("role")
        logger.warning(f"User {data.get('id', 'unknown')} has legacy role field: {legacy_role}")
        data["role_id"] = f"legacy_{legacy_role}" if legacy_role else "unknown"
    
    # Ensure required fields have defaults
    data.setdefault("phone", "")
    data.setdefault("role_id", "unknown")
    data.setdefault("venue_ids", [])
    data.setdefault("is_active", True)
    data.setdefault("is_verified", False)
    data.setdefault("email_verified", False)
    data.setdefault("phone_verified", False)
    
    # Log warnings for missing critical fields
    if not data.get("phone"):
        logger.warning(f"User {data.get('id', 'unknown')} missing phone field")
    
    if data.get("role_id") in ["unknown", "legacy_role_conversion_needed"]:
        logger.warning(f"User {data.get('id', 'unknown')} needs role migration: {data.get('role_id')}")
    
    try:
        return UserResponseDTO(**data)
    except Exception as e:
        logger.error(f"Failed to create UserResponseDTO: {e}")
        logger.error(f"User data keys: {list(data.keys())}")
        logger.error(f"Problematic data: {data}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process user data: {str(e)}"
        )


def validate_user_data_completeness(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate user data completeness and return validation results
    
    Args:
        user_data: User data dictionary
        
    Returns:
        Dict with validation results and warnings
    """
    warnings = []
    missing_fields = []
    
    # Check required fields
    required_fields = ["id", "email", "first_name", "last_name"]
    for field in required_fields:
        if not user_data.get(field):
            missing_fields.append(field)
    
    # Check important fields
    if not user_data.get("phone"):
        warnings.append("Phone number is missing")
    
    if not user_data.get("role_id"):
        warnings.append("Role ID is missing")
    
    if not user_data.get("venue_ids") and not user_data.get("venu_ids"):
        warnings.append("No venue associations found")
    
    return {
        "is_valid": len(missing_fields) == 0,
        "missing_fields": missing_fields,
        "warnings": warnings,
        "needs_migration": bool(warnings)
    }
