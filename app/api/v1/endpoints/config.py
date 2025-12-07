"""
Config API Endpoints
Handles system configuration management
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query

from app.models.config import ConfigCreateDTO, ConfigUpdateDTO, ConfigResponseDTO
from app.models.requests import ApiResponseDTO
from app.database.repository_manager import get_config_repo
from app.core.security import get_current_user, get_current_admin_user
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/value/{key}", 
            response_model=ApiResponseDTO,
            summary="Get config value by key",
            description="Get configuration value by key (public endpoint for specific keys)")
async def get_config_value(key: str):
    """
    Get configuration value by key
    Public endpoint for specific allowed keys like registration code
    """
    try:
        # List of public keys that can be accessed without authentication
        public_keys = [
            "dino.registration.code"
        ]
        
        if key not in public_keys:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access to this configuration key is restricted"
            )
        
        config_repo = get_config_repo()
        config = await config_repo.get_by_key(key)
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration not found for key: {key}"
            )
        
        logger.info(f"Config value retrieved for key: {key}")
        
        return ApiResponseDTO(
            success=True,
            message="Configuration retrieved successfully",
            data={
                "key": key,
                "value": config.get("value")
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting config value for key {key}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get configuration value"
        )


@router.post("/verify-registration-code",
             response_model=ApiResponseDTO,
             summary="Verify registration code",
             description="Verify if the provided registration code is correct")
async def verify_registration_code(code: str = Query(..., min_length=4, max_length=4)):
    """
    Verify registration code
    Public endpoint to verify registration code before allowing workspace creation
    """
    try:
        config_repo = get_config_repo()
        stored_code = await config_repo.get_value_by_key("dino.registration.code")
        
        if not stored_code:
            logger.error("Registration code not configured in system")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Registration code not configured. Please contact administrator."
            )
        
        # Convert both to string for comparison
        is_valid = str(code).strip() == str(stored_code).strip()
        
        if is_valid:
            logger.info("Registration code verified successfully")
            return ApiResponseDTO(
                success=True,
                message="Registration code is valid",
                data={"valid": True}
            )
        else:
            logger.warning(f"Invalid registration code attempt: {code}")
            return ApiResponseDTO(
                success=False,
                message="Invalid registration code",
                data={"valid": False}
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying registration code: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify registration code"
        )


@router.get("",
            response_model=List[ConfigResponseDTO],
            summary="Get all configs",
            description="Get all system configurations (admin only)")
async def get_all_configs(
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Get all configurations (admin only)"""
    try:
        config_repo = get_config_repo()
        configs = await config_repo.get_all()
        
        logger.info(f"Retrieved {len(configs)} configs")
        return configs
        
    except Exception as e:
        logger.error(f"Error getting all configs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get configurations"
        )


@router.get("/{key}",
            response_model=ConfigResponseDTO,
            summary="Get config by key",
            description="Get specific configuration by key (admin only)")
async def get_config(
    key: str,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Get configuration by key (admin only)"""
    try:
        config_repo = get_config_repo()
        config = await config_repo.get_by_key(key)
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Configuration not found"
            )
        
        return config
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get configuration"
        )


@router.post("",
             response_model=ApiResponseDTO,
             status_code=status.HTTP_201_CREATED,
             summary="Create config",
             description="Create new configuration (admin only)")
async def create_config(
    config_data: ConfigCreateDTO,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Create new configuration (admin only)"""
    try:
        config_repo = get_config_repo()
        
        # Check if key already exists
        existing_config = await config_repo.get_by_key(config_data.key)
        if existing_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Configuration with key '{config_data.key}' already exists"
            )
        
        # Create config using key as document ID
        created_config = await config_repo.set_value(config_data.key, config_data.value)
        
        logger.info(f"Config created: {config_data.key}")
        
        return ApiResponseDTO(
            success=True,
            message="Configuration created successfully",
            data=created_config
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create configuration"
        )


@router.put("/{key}",
            response_model=ApiResponseDTO,
            summary="Update config",
            description="Update configuration value (admin only)")
async def update_config(
    key: str,
    config_update: ConfigUpdateDTO,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Update configuration value (admin only)"""
    try:
        config_repo = get_config_repo()
        
        # Check if config exists
        config = await config_repo.get_by_key(key)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Configuration not found"
            )
        
        # Update config value
        await config_repo.set_value(key, config_update.value)
        
        logger.info(f"Config updated: {key}")
        
        return ApiResponseDTO(
            success=True,
            message="Configuration updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update configuration"
        )


@router.delete("/{key}",
               response_model=ApiResponseDTO,
               summary="Delete config",
               description="Delete configuration (admin only)")
async def delete_config(
    key: str,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Delete configuration (admin only)"""
    try:
        config_repo = get_config_repo()
        
        # Check if config exists
        config = await config_repo.get_by_key(key)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Configuration not found"
            )
        
        # Delete config
        await config_repo.delete_by_key(key)
        
        logger.info(f"Config deleted: {key}")
        
        return ApiResponseDTO(
            success=True,
            message="Configuration deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete configuration"
        )