"""
Code Management API Endpoints
Handles the 4-digit code display and refresh functionality
Only accessible to users with 'dinos' role
"""
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends
import random

from app.models.requests import ApiResponseDTO
from app.database.repository_manager import get_config_repo
from app.core.security import get_current_user
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Configuration key for the code
CODE_CONFIG_KEY = "dino.registration.code"


async def verify_dinos_role(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Verify that the current user has the 'dinos' role
    This endpoint is ONLY accessible to dinos role users
    """
    from app.core.security import _get_user_role
    
    user_role = await _get_user_role(current_user)
    
    # Log for debugging
    logger.info(f"Code access attempt - User: {current_user.get('email')}, Role: {user_role}, Role ID: {current_user.get('role_id')}")
    
    # Check if user has dinos role (case-insensitive)
    if user_role.lower() != 'dinos':
        logger.warning(f"Access denied to code module - User: {current_user.get('email')}, Role: {user_role}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. This feature is only accessible to dinos role. Your role: {user_role}"
        )
    
    return current_user


def generate_random_code() -> str:
    """Generate a random 4-digit code"""
    return str(random.randint(1000, 9999))


@router.get("/current",
            response_model=ApiResponseDTO,
            summary="Get current code",
            description="Get the current 4-digit code (dinos role only)")
async def get_current_code(
    current_user: Dict[str, Any] = Depends(verify_dinos_role)
):
    """
    Get the current 4-digit code
    Only accessible to users with 'dinos' role
    """
    try:
        config_repo = get_config_repo()
        
        # Try to get existing code
        code_value = await config_repo.get_value_by_key(CODE_CONFIG_KEY)
        
        # If code doesn't exist, create a new one
        if not code_value:
            code_value = generate_random_code()
            await config_repo.set_value(CODE_CONFIG_KEY, code_value)
            logger.info(f"Created initial code: {code_value}")
        
        logger.info(f"Code retrieved by user: {current_user.get('email')}")
        
        return ApiResponseDTO(
            success=True,
            message="Code retrieved successfully",
            data={
                "code": str(code_value),
                "digits": list(str(code_value).zfill(4))  # Ensure 4 digits
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current code: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve code"
        )


@router.post("/refresh",
             response_model=ApiResponseDTO,
             summary="Refresh code",
             description="Generate and update a new random 4-digit code (dinos role only)")
async def refresh_code(
    current_user: Dict[str, Any] = Depends(verify_dinos_role)
):
    """
    Generate and update a new random 4-digit code
    Only accessible to users with 'dinos' role
    """
    try:
        config_repo = get_config_repo()
        
        # Generate new random code
        new_code = generate_random_code()
        
        # Update in database
        await config_repo.set_value(CODE_CONFIG_KEY, new_code)
        
        logger.info(f"Code refreshed by user: {current_user.get('email')} - New code: {new_code}")
        
        return ApiResponseDTO(
            success=True,
            message="Code refreshed successfully",
            data={
                "code": new_code,
                "digits": list(new_code)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing code: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh code"
        )


@router.get("/debug/my-role",
            response_model=ApiResponseDTO,
            summary="Debug: Check my role",
            description="Debug endpoint to check current user's role information")
async def debug_my_role(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Debug endpoint to check current user's role
    Helps diagnose role-related access issues
    """
    try:
        from app.core.security import _get_user_role
        from app.database.repository_manager import get_role_repo
        
        user_role = await _get_user_role(current_user)
        role_id = current_user.get('role_id')
        
        # Get full role details if role_id exists
        role_details = None
        if role_id:
            role_repo = get_role_repo()
            role_details = await role_repo.get_by_id(role_id)
        
        return ApiResponseDTO(
            success=True,
            message="Role information retrieved",
            data={
                "user_email": current_user.get('email'),
                "user_id": current_user.get('id'),
                "role_name": user_role,
                "role_id": role_id,
                "role_details": role_details,
                "has_dinos_access": user_role.lower() == 'dinos',
                "raw_user_data": {
                    "role": current_user.get('role'),
                    "role_id": current_user.get('role_id'),
                    "venue_ids": current_user.get('venue_ids', [])
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Error in debug endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get role information: {str(e)}"
        )