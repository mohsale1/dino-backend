"""
Tour Management API Endpoints
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any
from datetime import datetime

from app.models.dto import ApiResponseDTO
from app.core.security import get_current_user, get_current_user_id
from app.core.logging_config import get_logger
from app.database.firestore import get_user_repo

logger = get_logger(__name__)
router = APIRouter()

@router.get("/status", response_model=ApiResponseDTO)
async def get_tour_status(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get current user's tour completion status"""
    try:
        return ApiResponseDTO(
            success=True,
            message="Tour status retrieved successfully",
            data={
                "user_id": current_user["id"],
                "first_login_completed": current_user.get("first_login_completed", False),
                "tour_completed": current_user.get("tour_completed", False),
                "tour_completed_at": current_user.get("tour_completed_at"),
                "tour_skipped": current_user.get("tour_skipped", False),
                "should_show_tour": not current_user.get("tour_completed", False) and not current_user.get("tour_skipped", False)
            }
        )
    except Exception as e:
        logger.error(f"Error getting tour status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get tour status"
        )

@router.post("/complete", response_model=ApiResponseDTO)
async def complete_tour(current_user_id: str = Depends(get_current_user_id)):
    """Mark tour as completed for current user"""
    try:
        user_repo = get_user_repo()
        
        # Update user tour completion status
        await user_repo.update(current_user_id, {
            "tour_completed": True,
            "tour_completed_at": datetime.utcnow(),
            "tour_skipped": False,
            "updated_at": datetime.utcnow()
        })
        
        logger.info(f"Tour completed for user: {current_user_id}")
        
        return ApiResponseDTO(
            success=True,
            message="Tour completed successfully",
            data={
                "user_id": current_user_id,
                "tour_completed": True,
                "completed_at": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Error completing tour for user {current_user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete tour"
        )

@router.post("/skip", response_model=ApiResponseDTO)
async def skip_tour(current_user_id: str = Depends(get_current_user_id)):
    """Mark tour as skipped for current user"""
    try:
        user_repo = get_user_repo()
        
        # Update user tour skip status
        await user_repo.update(current_user_id, {
            "tour_skipped": True,
            "tour_completed": False,
            "updated_at": datetime.utcnow()
        })
        
        logger.info(f"Tour skipped for user: {current_user_id}")
        
        return ApiResponseDTO(
            success=True,
            message="Tour skipped successfully",
            data={
                "user_id": current_user_id,
                "tour_skipped": True,
                "skipped_at": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Error skipping tour for user {current_user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to skip tour"
        )

@router.post("/restart", response_model=ApiResponseDTO)
async def restart_tour(current_user_id: str = Depends(get_current_user_id)):
    """Reset tour status to allow user to take tour again"""
    try:
        user_repo = get_user_repo()
        
        # Reset tour status
        await user_repo.update(current_user_id, {
            "tour_completed": False,
            "tour_skipped": False,
            "tour_completed_at": None,
            "updated_at": datetime.utcnow()
        })
        
        logger.info(f"Tour restarted for user: {current_user_id}")
        
        return ApiResponseDTO(
            success=True,
            message="Tour restarted successfully",
            data={
                "user_id": current_user_id,
                "tour_completed": False,
                "tour_skipped": False,
                "restarted_at": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Error restarting tour for user {current_user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to restart tour"
        )

@router.post("/first-login-complete", response_model=ApiResponseDTO)
async def complete_first_login(current_user_id: str = Depends(get_current_user_id)):
    """Mark first login as completed for current user"""
    try:
        user_repo = get_user_repo()
        
        # Update first login completion status
        await user_repo.update(current_user_id, {
            "first_login_completed": True,
            "updated_at": datetime.utcnow()
        })
        
        logger.info(f"First login completed for user: {current_user_id}")
        
        return ApiResponseDTO(
            success=True,
            message="First login completed successfully",
            data={
                "user_id": current_user_id,
                "first_login_completed": True,
                "completed_at": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Error completing first login for user {current_user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete first login"
        )