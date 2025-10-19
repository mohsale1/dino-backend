"""
User Data API Endpoint - Simplified Structure
Provides basic user data with venue and workspace information
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime

from app.core.security import (
    get_current_user, 
    get_user_primary_venue
)
from app.core.logging_config import get_logger
from app.database.firestore import get_workspace_repo

logger = get_logger(__name__)
router = APIRouter()


class UserDataService:
    """Simplified user data service"""
    
    @staticmethod
    async def get_user_data(current_user: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get simplified user data with venue and workspace information
        """
        try:
            user_id = current_user['id']
            user_role = current_user.get('role', 'operator')
            
            # Get user's primary venue (can be None)
            primary_venue = await get_user_primary_venue(current_user)
            
            # Get workspace information if venue exists
            workspace_data = None
            if primary_venue and primary_venue.get('workspace_id'):
                workspace_id = primary_venue['workspace_id']
                try:
                    workspace_repo = get_workspace_repo()
                    workspace_data = await workspace_repo.get_by_id(workspace_id)
                except Exception as e:
                    logger.warning(f"Could not fetch workspace data: {e}")
                    workspace_data = None
            
            # Prepare simplified response data
            response_data = {
                'user': {
                    'id': current_user['id'],
                    'email': current_user['email'],
                    'first_name': current_user['first_name'],
                    'last_name': current_user['last_name'],
                    'phone': current_user.get('phone', ''),
                    'role': user_role,
                    'is_active': current_user.get('is_active', True),
                    'created_at': current_user.get('created_at'),
                    'updated_at': current_user.get('updated_at')
                },
                'venue': primary_venue,  # Can be None
                'workspace': workspace_data  # Can be None
            }
            
            logger.info(f"User data retrieved successfully for user: {user_id}, venue: {primary_venue['id'] if primary_venue else 'None'}")
            return response_data
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting user data: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve user data"
            )


@router.get("/user-data", summary="Get user data")
async def get_user_data(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get user data with venue and workspace information
    Returns the structure: {data: {user, venue, workspace}, timestamp}
    """
    try:
        user_data = await UserDataService.get_user_data(current_user)
        
        return {
            "data": user_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_user_data endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user data"
        )


@router.post("/refresh-user-data", summary="Refresh user data")
async def refresh_user_data(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Refresh user data (same as get_user_data but with POST method for cache busting)
    """
    try:
        user_data = await UserDataService.get_user_data(current_user)
        
        return {
            "data": user_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in refresh_user_data endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh user data"
        )