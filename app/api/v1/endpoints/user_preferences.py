"""
User Preferences and Address Management API Endpoints
Additional endpoints for user profile management
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

from app.core.security import get_current_user
from app.core.logging_config import get_logger
from app.models.dto import ApiResponse

logger = get_logger(__name__)
router = APIRouter()


class UserAddress(BaseModel):
    id: Optional[str] = None
    address_line_1: str
    address_line_2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str = "India"
    is_default: bool = False


class UserPreferences(BaseModel):
    language: str = "en"
    timezone: str = "Asia/Kolkata"
    currency: str = "INR"
    notifications_enabled: bool = True
    email_notifications: bool = True
    sms_notifications: bool = False
    theme: str = "light"


@router.get("/addresses", 
            response_model=List[UserAddress],
            summary="Get user addresses",
            description="Get all addresses for current user")
async def get_user_addresses(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get user addresses"""
    try:
        from app.database.firestore import get_user_repo
        user_repo = get_user_repo()
        
        # Get user data
        user = await user_repo.get_by_id(current_user['id'])
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Return addresses (mock data for now)
        addresses = user.get('addresses', [])
        return [UserAddress(**addr) for addr in addresses]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user addresses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get addresses"
        )


@router.post("/addresses", 
             response_model=ApiResponse,
             summary="Add user address",
             description="Add new address for current user")
async def add_user_address(
    address: UserAddress,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Add user address"""
    try:
        from app.database.firestore import get_user_repo
        import uuid
        
        user_repo = get_user_repo()
        
        # Get current addresses
        user = await user_repo.get_by_id(current_user['id'])
        addresses = user.get('addresses', [])
        
        # Add new address
        new_address = address.dict()
        new_address['id'] = str(uuid.uuid4())
        
        # If this is the first address or marked as default, make it default
        if not addresses or address.is_default:
            # Remove default from other addresses
            for addr in addresses:
                addr['is_default'] = False
            new_address['is_default'] = True
        
        addresses.append(new_address)
        
        # Update user
        await user_repo.update(current_user['id'], {'addresses': addresses})
        
        logger.info(f"Address added for user: {current_user['id']}")
        return ApiResponse(
            success=True,
            message="Address added successfully",
            data=new_address
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding user address: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add address"
        )


@router.put("/addresses/{address_id}", 
            response_model=ApiResponse,
            summary="Update user address",
            description="Update existing address")
async def update_user_address(
    address_id: str,
    address: UserAddress,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update user address"""
    try:
        from app.database.firestore import get_user_repo
        user_repo = get_user_repo()
        
        # Get current addresses
        user = await user_repo.get_by_id(current_user['id'])
        addresses = user.get('addresses', [])
        
        # Find and update address
        address_found = False
        for i, addr in enumerate(addresses):
            if addr['id'] == address_id:
                updated_address = address.dict()
                updated_address['id'] = address_id
                
                # Handle default address logic
                if address.is_default:
                    # Remove default from other addresses
                    for other_addr in addresses:
                        if other_addr['id'] != address_id:
                            other_addr['is_default'] = False
                
                addresses[i] = updated_address
                address_found = True
                break
        
        if not address_found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Address not found"
            )
        
        # Update user
        await user_repo.update(current_user['id'], {'addresses': addresses})
        
        logger.info(f"Address updated for user: {current_user['id']}")
        return ApiResponse(
            success=True,
            message="Address updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user address: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update address"
        )


@router.delete("/addresses/{address_id}", 
               response_model=ApiResponse,
               summary="Delete user address",
               description="Delete user address")
async def delete_user_address(
    address_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete user address"""
    try:
        from app.database.firestore import get_user_repo
        user_repo = get_user_repo()
        
        # Get current addresses
        user = await user_repo.get_by_id(current_user['id'])
        addresses = user.get('addresses', [])
        
        # Find and remove address
        addresses = [addr for addr in addresses if addr['id'] != address_id]
        
        # Update user
        await user_repo.update(current_user['id'], {'addresses': addresses})
        
        logger.info(f"Address deleted for user: {current_user['id']}")
        return ApiResponse(
            success=True,
            message="Address deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user address: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete address"
        )


@router.get("/preferences", 
            response_model=UserPreferences,
            summary="Get user preferences",
            description="Get user preferences and settings")
async def get_user_preferences(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get user preferences"""
    try:
        from app.database.firestore import get_user_repo
        user_repo = get_user_repo()
        
        # Get user data
        user = await user_repo.get_by_id(current_user['id'])
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Return preferences with defaults
        preferences = user.get('preferences', {})
        return UserPreferences(**preferences)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get preferences"
        )


@router.put("/preferences", 
            response_model=ApiResponse,
            summary="Update user preferences",
            description="Update user preferences and settings")
async def update_user_preferences(
    preferences: UserPreferences,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update user preferences"""
    try:
        from app.database.firestore import get_user_repo
        user_repo = get_user_repo()
        
        # Update user preferences
        await user_repo.update(current_user['id'], {
            'preferences': preferences.dict()
        })
        
        logger.info(f"Preferences updated for user: {current_user['id']}")
        return ApiResponse(
            success=True,
            message="Preferences updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences"
        )


@router.get("/statistics", 
            response_model=Dict[str, Any],
            summary="Get user statistics",
            description="Get user statistics for workspace/venue")
async def get_user_statistics(
    workspace_id: Optional[str] = None,
    venue_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get user statistics"""
    try:
        from app.database.firestore import get_user_repo
        user_repo = get_user_repo()
        
        # Build filters
        filters = []
        if workspace_id:
            filters.append(('workspace_id', '==', workspace_id))
        if venue_id:
            filters.append(('venue_id', '==', venue_id))
        
        # Get users
        users = await user_repo.query(filters)
        
        # Calculate statistics
        total_users = len(users)
        active_users = len([u for u in users if u.get('is_active', False)])
        
        # Count by role
        users_by_role = {}
        recent_logins = 0
        
        for user in users:
            role = user.get('role', 'unknown')
            users_by_role[role] = users_by_role.get(role, 0) + 1
            
            # Count recent logins (last 7 days)
            last_login = user.get('last_login')
            if last_login:
                from datetime import datetime, timedelta
                if isinstance(last_login, str):
                    last_login = datetime.fromisoformat(last_login.replace('Z', '+00:00'))
                if last_login > datetime.utcnow() - timedelta(days=7):
                    recent_logins += 1
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "users_by_role": users_by_role,
            "recent_logins": recent_logins
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user statistics"
        )