"""
Venue Status Management API Endpoints
Additional endpoints for venue status and operational management
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from datetime import datetime

from app.core.security import get_current_user, get_current_admin_user
from app.core.logging_config import get_logger
from app.models.dto import ApiResponse

logger = get_logger(__name__)
router = APIRouter()


class VenueStatusUpdate(BaseModel):
    is_open: bool
    reason: Optional[str] = None


@router.post("/{venue_id}/toggle-status", 
             response_model=ApiResponse,
             summary="Toggle venue status",
             description="Toggle venue open/closed status")
async def toggle_venue_status(
    venue_id: str,
    status_update: VenueStatusUpdate,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Toggle venue open/closed status"""
    try:
        from app.database.firestore import get_venue_repo
        venue_repo = get_venue_repo()
        
        # Get venue
        venue = await venue_repo.get_by_id(venue_id)
        if not venue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Venue not found"
            )
        
        # Check permissions
        from app.core.security import _get_user_role
        user_role = await _get_user_role(current_user)
        
        if user_role != 'superadmin':
            # Check if user has access to this venue
            if (venue.get('admin_id') != current_user['id'] and 
                venue.get('owner_id') != current_user['id']):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Not authorized for this venue"
                )
        
        # Update venue status
        update_data = {
            'is_open': status_update.is_open,
            'status_updated_at': datetime.utcnow(),
            'status_updated_by': current_user['id']
        }
        
        if status_update.reason:
            update_data['status_reason'] = status_update.reason
        
        await venue_repo.update(venue_id, update_data)
        
        status_text = "opened" if status_update.is_open else "closed"
        logger.info(f"Venue {venue_id} {status_text} by user {current_user['id']}")
        
        return ApiResponse(
            success=True,
            message=f"Venue {status_text} successfully",
            data={
                "venue_id": venue_id,
                "is_open": status_update.is_open,
                "updated_at": update_data['status_updated_at'].isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling venue status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update venue status"
        )


@router.post("/{venue_id}/activate", 
             response_model=ApiResponse,
             summary="Activate venue",
             description="Activate deactivated venue")
async def activate_venue(
    venue_id: str,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Activate venue"""
    try:
        from app.database.firestore import get_venue_repo
        venue_repo = get_venue_repo()
        
        # Get venue
        venue = await venue_repo.get_by_id(venue_id)
        if not venue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Venue not found"
            )
        
        # Check permissions
        from app.core.security import _get_user_role
        user_role = await _get_user_role(current_user)
        
        if user_role != 'superadmin':
            if (venue.get('admin_id') != current_user['id'] and 
                venue.get('owner_id') != current_user['id']):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Not authorized for this venue"
                )
        
        # Activate venue
        await venue_repo.update(venue_id, {
            'is_active': True,
            'activated_at': datetime.utcnow(),
            'activated_by': current_user['id']
        })
        
        logger.info(f"Venue activated: {venue_id} by user {current_user['id']}")
        return ApiResponse(
            success=True,
            message="Venue activated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating venue: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate venue"
        )


@router.post("/{venue_id}/deactivate", 
             response_model=ApiResponse,
             summary="Deactivate venue",
             description="Deactivate venue")
async def deactivate_venue(
    venue_id: str,
    reason: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Deactivate venue"""
    try:
        from app.database.firestore import get_venue_repo
        venue_repo = get_venue_repo()
        
        # Get venue
        venue = await venue_repo.get_by_id(venue_id)
        if not venue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Venue not found"
            )
        
        # Check permissions
        from app.core.security import _get_user_role
        user_role = await _get_user_role(current_user)
        
        if user_role != 'superadmin':
            if (venue.get('admin_id') != current_user['id'] and 
                venue.get('owner_id') != current_user['id']):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Not authorized for this venue"
                )
        
        # Deactivate venue
        update_data = {
            'is_active': False,
            'deactivated_at': datetime.utcnow(),
            'deactivated_by': current_user['id']
        }
        
        if reason:
            update_data['deactivation_reason'] = reason
        
        await venue_repo.update(venue_id, update_data)
        
        logger.info(f"Venue deactivated: {venue_id} by user {current_user['id']}")
        return ApiResponse(
            success=True,
            message="Venue deactivated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating venue: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate venue"
        )


@router.get("/{venue_id}/status", 
            response_model=Dict[str, Any],
            summary="Get venue status",
            description="Get current venue operational status")
async def get_venue_status(
    venue_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """Get venue status (public endpoint)"""
    try:
        from app.database.firestore import get_venue_repo
        venue_repo = get_venue_repo()
        
        # Get venue
        venue = await venue_repo.get_by_id(venue_id)
        if not venue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Venue not found"
            )
        
        # Check if venue is active (for public access)
        if not current_user and not venue.get('is_active', False):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Venue not found"
            )
        
        # Get operating hours
        operating_hours = venue.get('operating_hours', [])
        
        # Determine current status
        is_open = venue.get('is_open', False)
        is_active = venue.get('is_active', False)
        
        # Calculate next status change
        next_status_change = None
        if operating_hours:
            # This would be implemented with proper time zone handling
            # For now, return basic status
            pass
        
        status_info = {
            "venue_id": venue_id,
            "venue_name": venue.get('name'),
            "is_active": is_active,
            "is_open": is_open,
            "current_status": "open" if (is_active and is_open) else "closed",
            "operating_hours": operating_hours,
            "next_status_change": next_status_change,
            "last_updated": venue.get('status_updated_at'),
            "status_reason": venue.get('status_reason')
        }
        
        return status_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting venue status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get venue status"
        )


@router.get("/{venue_id}/control-panel-status", 
            response_model=Dict[str, Any],
            summary="Get venue status for control panel",
            description="Get simplified venue status for control panel display")
async def get_control_panel_status(
    venue_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get simplified venue status for control panel"""
    try:
        from app.database.firestore import get_venue_repo
        venue_repo = get_venue_repo()
        
        # Get venue
        venue = await venue_repo.get_by_id(venue_id)
        if not venue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Venue not found"
            )
        
        # Check permissions
        from app.core.security import _get_user_role
        user_role = await _get_user_role(current_user)
        
        if user_role not in ['superadmin', 'admin', 'operator']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Determine current status
        is_open = venue.get('is_open', False)
        is_active = venue.get('is_active', False)
        
        # Create status message
        if is_active and is_open:
            status_message = "Open for Orders"
            status_detail = "Accepting orders"
        elif is_active and not is_open:
            status_message = "Closed"
            status_detail = "Not accepting orders"
        else:
            status_message = "Inactive"
            status_detail = "Venue is inactive"
        
        control_panel_status = {
            "venue_id": venue_id,
            "venue_name": venue.get('name', 'Unknown Venue'),
            "status_message": status_message,
            "status_detail": status_detail,
            "is_open": is_open,
            "is_active": is_active,
            "last_updated": venue.get('status_updated_at'),
            "updated_by": venue.get('status_updated_by')
        }
        
        return control_panel_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting control panel status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get control panel status"
        )