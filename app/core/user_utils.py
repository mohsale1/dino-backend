"""
User utility functions for data conversion and validation
"""
from typing import Dict, Any
from fastapi import HTTPException, status
from app.models.dto import UserResponseDTO
from app.core.logging_config import get_logger

logger = get_logger(__name__)

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
        # For legacy users with role enum, we need to convert to role_id
        # This should be handled by a proper migration, but for now provide a placeholder
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

def sanitize_user_data(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize user data by removing sensitive information
    
    Args:
        user_data: Raw user data
        
    Returns:
        Sanitized user data dictionary
    """
    sanitized = user_data.copy()
    
    # Remove sensitive fields
    sensitive_fields = [
        "hashed_password", 
        "password_salt", 
        "password_hash",
        "salt"
    ]
    
    for field in sensitive_fields:
        sanitized.pop(field, None)
    
    return sanitized