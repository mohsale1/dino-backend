"""
Table Area Management API Endpoints
Manages table areas/sections within venues with proper Firestore integration
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Depends
import uuid
from datetime import datetime

from app.core.security import get_current_user, get_current_admin_user
from app.core.logging_config import get_logger
from app.models.dto import (
    ApiResponse, 
    TableAreaResponseDTO as TableArea,
    TableAreaCreateDTO as TableAreaCreate, 
    TableAreaUpdateDTO as TableAreaUpdate
)

logger = get_logger(__name__)
router = APIRouter()


@router.get("/venues/{venue_id}/areas", 
            response_model=List[TableArea],
            summary="Get venue areas",
            description="Get all table areas for a venue")
async def get_venue_areas(
    venue_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get all table areas for a venue"""
    try:
        from app.database.firestore import get_venue_repo, get_table_area_repo
        venue_repo = get_venue_repo()
        area_repo = get_table_area_repo()
        
        # Validate venue exists and user has access
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
        
        # Get areas from database
        areas_data = await area_repo.get_by_venue_id(venue_id)
        
        # Convert to TableArea objects
        areas = []
        for area_data in areas_data:
            # Map is_active to active for API compatibility
            area_data['active'] = area_data.get('is_active', True)
            areas.append(TableArea(**area_data))
        
        logger.info(f"Retrieved {len(areas)} areas for venue: {venue_id}")
        return areas
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting venue areas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get venue areas"
        )


@router.post("/areas", 
             response_model=ApiResponse,
             summary="Create table area",
             description="Create a new table area")
async def create_area(
    area_data: TableAreaCreate,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Create a new table area"""
    try:
        from app.database.firestore import get_venue_repo, get_table_area_repo
        venue_repo = get_venue_repo()
        area_repo = get_table_area_repo()
        
        # Validate venue exists and user has access
        venue = await venue_repo.get_by_id(area_data.venue_id)
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
        
        # Check if area name already exists for this venue
        existing_area = await area_repo.get_by_name(area_data.venue_id, area_data.name)
        if existing_area:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Area name already exists for this venue"
            )
        
        # Prepare area data for creation
        area_dict = area_data.dict()
        # Map 'active' to 'is_active' for database storage
        area_dict['is_active'] = area_dict.pop('active', True)
        
        # Create area in database
        created_area = await area_repo.create(area_dict)
        
        # Map is_active back to active for response
        created_area['active'] = created_area.get('is_active', True)
        
        logger.info(f"Area created: {created_area['id']} for venue {area_data.venue_id}")
        return ApiResponse(
            success=True,
            message="Table area created successfully",
            data=created_area
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating area: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create area"
        )


@router.put("/areas/{area_id}", 
            response_model=ApiResponse,
            summary="Update table area",
            description="Update table area information")
async def update_area(
    area_id: str,
    area_data: TableAreaUpdate,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Update table area"""
    try:
        from app.database.firestore import get_venue_repo, get_table_area_repo
        venue_repo = get_venue_repo()
        area_repo = get_table_area_repo()
        
        # Get existing area
        existing_area = await area_repo.get_by_id(area_id)
        if not existing_area:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Table area not found"
            )
        
        # Validate venue exists and user has access
        venue = await venue_repo.get_by_id(existing_area['venue_id'])
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
        
        # Prepare update data
        update_dict = area_data.dict(exclude_unset=True)
        
        # Handle active/is_active mapping
        if 'active' in update_dict:
            update_dict['is_active'] = update_dict.pop('active')
        
        # Check if name is being updated and doesn't conflict
        if 'name' in update_dict and update_dict['name'] != existing_area.get('name'):
            existing_name_area = await area_repo.get_by_name(
                existing_area['venue_id'], 
                update_dict['name']
            )
            if existing_name_area and existing_name_area['id'] != area_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Area name already exists for this venue"
                )
        
        # Update area in database
        updated_area = await area_repo.update(area_id, update_dict)
        
        # Map is_active back to active for response
        updated_area['active'] = updated_area.get('is_active', True)
        
        logger.info(f"Area updated: {area_id}")
        return ApiResponse(
            success=True,
            message="Table area updated successfully",
            data=updated_area
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating area: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update area"
        )


@router.delete("/areas/{area_id}", 
               response_model=ApiResponse,
               summary="Delete table area",
               description="Delete table area")
async def delete_area(
    area_id: str,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Delete table area"""
    try:
        from app.database.firestore import get_venue_repo, get_table_area_repo, get_table_repo
        venue_repo = get_venue_repo()
        area_repo = get_table_area_repo()
        table_repo = get_table_repo()
        
        # Get existing area
        existing_area = await area_repo.get_by_id(area_id)
        if not existing_area:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Table area not found"
            )
        
        # Validate venue exists and user has access
        venue = await venue_repo.get_by_id(existing_area['venue_id'])
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
        
        # Check if area has tables assigned to it
        tables_in_area = await table_repo.query([("area_id", "==", area_id)])
        if tables_in_area:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete area: {len(tables_in_area)} tables are assigned to this area. Please reassign or delete tables first."
            )
        
        # Delete area from database
        await area_repo.delete(area_id)
        
        logger.info(f"Area deleted: {area_id}")
        return ApiResponse(
            success=True,
            message="Table area deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting area: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete area"
        )


@router.get("/areas/{area_id}/tables", 
            response_model=List[Dict[str, Any]],
            summary="Get area tables",
            description="Get all tables in a specific area")
async def get_area_tables(
    area_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get all tables in an area"""
    try:
        from app.database.firestore import get_table_area_repo, get_table_repo
        area_repo = get_table_area_repo()
        table_repo = get_table_repo()
        
        # Validate area exists
        area = await area_repo.get_by_id(area_id)
        if not area:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Table area not found"
            )
        
        # Check permissions
        from app.core.security import _get_user_role
        user_role = await _get_user_role(current_user)
        
        if user_role not in ['superadmin', 'admin', 'operator']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Get tables in this area
        tables = await table_repo.query([("area_id", "==", area_id)])
        
        logger.info(f"Retrieved {len(tables)} tables for area: {area_id}")
        return tables
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting area tables: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get area tables"
        )


@router.get("/areas/{area_id}",
            response_model=TableArea,
            summary="Get table area by ID",
            description="Get a specific table area by its ID")
async def get_area_by_id(
    area_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get table area by ID"""
    try:
        from app.database.firestore import get_table_area_repo
        area_repo = get_table_area_repo()
        
        # Get area from database
        area_data = await area_repo.get_by_id(area_id)
        if not area_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Table area not found"
            )
        
        # Check permissions
        from app.core.security import _get_user_role
        user_role = await _get_user_role(current_user)
        
        if user_role not in ['superadmin', 'admin', 'operator']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Map is_active to active for API compatibility
        area_data['active'] = area_data.get('is_active', True)
        
        logger.info(f"Retrieved area: {area_id}")
        return TableArea(**area_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting area by ID: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get area"
        )