"""
Enhanced Venue Management API Endpoints
Refactored with clean 3-layer architecture
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Query
from pydantic import BaseModel
from datetime import datetime

from app.models.entities import Venue, VenueOperatingHours, SubscriptionPlan, SubscriptionStatus, VenueStatus
from app.models.requests import (
    VenueCreateDTO, VenueUpdateDTO, VenueResponseDTO, VenueWorkspaceListDTO, 
    ApiResponseDTO, PaginatedResponseDTO
)
from app.core.base_endpoint import WorkspaceIsolatedEndpoint
from app.database.repository_manager import get_venue_repo, get_role_repo
from app.repositories import VenueRepository
from app.core.security import get_current_user, get_current_admin_user, verify_workspace_access, _get_user_role
from app.core.logging import get_logger
from app.services.venue import get_venue_service, clean_venue_status
from app.core.dependencies import get_repository_manager

logger = get_logger(__name__)
router = APIRouter()
venue_service = get_venue_service()


class VenuesEndpoint(WorkspaceIsolatedEndpoint[Venue, VenueCreateDTO, VenueUpdateDTO]):
    """Enhanced Venues endpoint with workspace isolation"""
    
    def __init__(self):
        super().__init__(
            model_class=Venue,
            create_schema=VenueCreateDTO,
            update_schema=VenueUpdateDTO,
            collection_name="venues",
            require_auth=True,
            require_admin=True
        )
    
    def get_repository(self) -> VenueRepository:
        return get_venue_repo()
    
    async def _prepare_create_data(self, data: Dict[str, Any], current_user: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare venue data before creation"""
        if current_user:
            data['owner_id'] = current_user['id']
            data['admin_id'] = current_user['id']
            if not data.get('workspace_id'):
                data['workspace_id'] = current_user.get('workspace_id')
        
        data['is_active'] = True
        data['is_verified'] = False
        data['rating'] = 0.0
        data['total_reviews'] = 0
        
        # Ensure is_open is set (default to True if not provided)
        if 'is_open' not in data:
            data['is_open'] = True
        
        # Set default theme to classic
        if 'theme' not in data:
            data['theme'] = 'classic'
        
        # Always set country to India
        if 'location' in data and isinstance(data['location'], dict):
            data['location']['country'] = 'India'
        
        return data
    
    async def _validate_create_permissions(self, data: Dict[str, Any], current_user: Optional[Dict[str, Any]]):
        """Validate venue creation permissions"""
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
    
    async def _validate_access_permissions(self, item: Dict[str, Any], current_user: Optional[Dict[str, Any]]):
        """Validate venue access permissions"""
        if not current_user:
            return
        await super()._validate_access_permissions(item, current_user)
    
    async def _build_query_filters(self, filters: Optional[Dict[str, Any]], search: Optional[str], current_user: Optional[Dict[str, Any]]) -> List[tuple]:
        """Build query filters for venue search"""
        query_filters = []
        
        if current_user:
            user_role = await _get_user_role(current_user)
            if user_role not in ['admin', 'superadmin']:
                workspace_id = current_user.get('workspace_id')
                if workspace_id:
                    query_filters.append(('workspace_id', '==', workspace_id))
        
        if filters:
            for field, value in filters.items():
                if value is not None:
                    query_filters.append((field, '==', value))
        
        return query_filters
    
    async def get_items(self, page: int = 1, page_size: int = 10, search: Optional[str] = None, filters: Optional[Dict[str, Any]] = None, current_user: Optional[Dict[str, Any]] = None):
        """Get paginated list of venues"""
        try:
            repo = self.get_repository()
            query_filters = await self._build_query_filters(filters, search, current_user)
            
            all_items = await repo.query(query_filters) if query_filters else await repo.get_all()
            
            if search:
                search_lower = search.lower()
                all_items = [
                    item for item in all_items
                    if any(search_lower in str(value).lower() for value in item.values() if isinstance(value, str))
                ]
            
            filtered_items = await self._filter_items_for_user(all_items, current_user)
            
            total = len(filtered_items)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            items_page = filtered_items[start_idx:end_idx]
            
            items = [VenueResponseDTO(**clean_venue_status(item)) for item in items_page]
            
            total_pages = (total + page_size - 1) // page_size
            
            from app.models.requests import PaginatedResponse
            return PaginatedResponse(
                success=True,
                data=items,
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting venues list: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get venues list"
            )
    
    async def get_item(self, item_id: str, current_user: Optional[Dict[str, Any]]):
        """Get venue by ID"""
        try:
            repo = self.get_repository()
            item = await repo.get_by_id(item_id)
            
            if not item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Venue not found"
                )
            
            await self._validate_access_permissions(item, current_user)
            return VenueResponseDTO(**clean_venue_status(item))
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting venue: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get venue"
            )


# Initialize endpoint
venues_endpoint = VenuesEndpoint()


# =============================================================================
# PUBLIC ENDPOINTS
# =============================================================================

@router.get("/public", response_model=PaginatedResponseDTO, summary="Get public venues")
async def get_public_venues(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    search: Optional[str] = Query(None),
    cuisine_type: Optional[str] = Query(None),
    price_range: Optional[str] = Query(None)
):
    """Get public venues (no authentication required)"""
    try:
        repo = get_venue_repo()
        filters = [('is_active', '==', True)]
        
        if cuisine_type:
            filters.append(('cuisine_types', 'array_contains', cuisine_type))
        if price_range:
            filters.append(('price_range', '==', price_range))
        
        all_venues = await repo.query(filters)
        
        if search:
            search_lower = search.lower()
            all_venues = [
                venue for venue in all_venues
                if (search_lower in venue.get('name', '').lower() or
                    search_lower in venue.get('description', '').lower() or
                    any(search_lower in cuisine.lower() for cuisine in venue.get('cuisine_types', [])))
            ]
        
        total = len(all_venues)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        venues_page = all_venues[start_idx:end_idx]
        
        venues = [VenueResponseDTO(**clean_venue_status(venue)) for venue in venues_page]
        
        total_pages = (total + page_size - 1) // page_size
        
        logger.info(f"Public venues retrieved: {len(venues)} of {total}")
        
        return PaginatedResponseDTO(
            success=True,
            data=venues,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
    except Exception as e:
        logger.error(f"Error getting public venues: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get venues"
        )


@router.get("/public/{venue_id}", response_model=VenueResponseDTO, summary="Get public venue details")
async def get_public_venue(venue_id: str):
    """Get venue by ID (public endpoint)"""
    try:
        repo = get_venue_repo()
        venue = await repo.get_by_id(venue_id)
        
        if not venue or not venue.get('is_active', False):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Venue not found"
            )
        
        logger.info(f"Public venue retrieved: {venue_id}")
        return VenueResponseDTO(**clean_venue_status(venue))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting public venue {venue_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get venue"
        )


# =============================================================================
# WORKSPACE ENDPOINTS
# =============================================================================

@router.get("/workspace/{workspace_id}/venues", response_model=List[Dict[str, Any]], summary="Get venues by workspace")
async def get_venues_by_workspace(workspace_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get simplified venue list for workspace"""
    try:
        await verify_workspace_access(workspace_id, current_user)
        
        repo = get_venue_repo()
        venues_data = await repo.get_by_workspace(workspace_id)
        
        venues = []
        for venue in venues_data:
            location_info = {}
            if venue.get('location'):
                location_info = {
                    'city': venue['location'].get('city', ''),
                    'state': venue['location'].get('state', ''),
                    'country': venue['location'].get('country', ''),
                    'address': venue['location'].get('address', ''),
                    'postal_code': venue['location'].get('postal_code', '')
                }
            
            simplified_venue = {
                'id': venue['id'],
                'name': venue.get('name', ''),
                'description': venue.get('description'),
                'location': location_info,
                'phone': venue.get('phone'),
                'email': venue.get('email'),
                'venue_type': venue.get('venue_type'),
                'price_range': venue.get('price_range'),
                'theme': venue.get('theme'),
                'image_url': venue.get('image_url'),
                'is_active': venue.get('is_active', False),
                'is_open': venue.get('is_open', False),
                'created_at': venue.get('created_at', datetime.utcnow()),
                'updated_at': venue.get('updated_at', datetime.utcnow())
            }
            venues.append(simplified_venue)
        
        logger.info(f"Retrieved {len(venues)} venues for workspace: {workspace_id}")
        return venues
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting venues for workspace {workspace_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get workspace venues"
        )


# =============================================================================
# AUTHENTICATED ENDPOINTS
# =============================================================================

@router.get("", response_model=PaginatedResponseDTO, summary="Get venues")
async def get_venues(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    subscription_status: Optional[SubscriptionStatus] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Get venues with pagination and filtering"""
    filters = {}
    if subscription_status:
        filters['subscription_status'] = subscription_status.value
    if is_active is not None:
        filters['is_active'] = is_active
    
    return await venues_endpoint.get_items(page, page_size, search, filters, current_user)


@router.post("", response_model=ApiResponseDTO, status_code=status.HTTP_201_CREATED, summary="Create venue")
async def create_venue(venue_data: VenueCreateDTO, current_user: Dict[str, Any] = Depends(get_current_admin_user)):
    """Create a new venue"""
    return await venues_endpoint.create_item(venue_data, current_user)


@router.get("/my-venues", response_model=List[VenueResponseDTO], summary="Get my venues")
async def get_my_venues(current_user: Dict[str, Any] = Depends(get_current_admin_user)):
    """Get current user's venues"""
    try:
        repo = get_venue_repo()
        venues_data = await repo.get_by_owner(current_user["id"])
        venues = [VenueResponseDTO(**clean_venue_status(venue)) for venue in venues_data]
        
        logger.info(f"Retrieved {len(venues)} venues for user {current_user['id']}")
        return venues
    except Exception as e:
        logger.error(f"Error getting user venues: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get venues"
        )


@router.get("/{venue_id}", response_model=VenueResponseDTO, summary="Get venue by ID")
async def get_venue(venue_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get venue by ID"""
    return await venues_endpoint.get_item(venue_id, current_user)


@router.put("/{venue_id}", response_model=ApiResponseDTO, summary="Update venue")
async def update_venue(venue_id: str, venue_update: VenueUpdateDTO, current_user: Dict[str, Any] = Depends(get_current_admin_user)):
    """Update venue information"""
    # Ensure country is always set to India
    update_data = venue_update.dict(exclude_unset=True)
    if 'location' in update_data and isinstance(update_data['location'], dict):
        update_data['location']['country'] = 'India'
        # Recreate the DTO with updated data
        venue_update = VenueUpdateDTO(**update_data)
    
    return await venues_endpoint.update_item(venue_id, venue_update, current_user)


@router.delete("/{venue_id}", response_model=ApiResponseDTO, summary="Delete venue")
async def delete_venue(venue_id: str, current_user: Dict[str, Any] = Depends(get_current_admin_user)):
    """Delete venue (hard delete)"""
    try:
        logger.info(f"Venue deletion requested for {venue_id} by {current_user.get('id')}")
        result = await venues_endpoint.delete_item(venue_id, current_user, soft_delete=False)
        logger.info(f"Venue deletion completed for {venue_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting venue {venue_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete venue"
        )


@router.post("/{venue_id}/deactivate", response_model=ApiResponseDTO, summary="Deactivate venue")
async def deactivate_venue(venue_id: str, reason: Optional[str] = None, current_user: Dict[str, Any] = Depends(get_current_admin_user)):
    """Deactivate venue (soft delete)"""
    try:
        venue = await venues_endpoint.get_item(venue_id, current_user)
        await venue_service.deactivate_venue(venue_id, current_user['id'], reason)
        
        return ApiResponseDTO(success=True, message="Venue deactivated successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating venue {venue_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate venue"
        )


@router.post("/{venue_id}/activate", response_model=ApiResponseDTO, summary="Activate venue")
async def activate_venue(venue_id: str, current_user: Dict[str, Any] = Depends(get_current_admin_user)):
    """Activate venue"""
    try:
        venue = await venues_endpoint.get_item(venue_id, current_user)
        await venue_service.activate_venue(venue_id, current_user['id'])
        
        return ApiResponseDTO(success=True, message="Venue activated successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating venue {venue_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate venue"
        )


# =============================================================================
# ANALYTICS ENDPOINTS
# =============================================================================

@router.get("/{venue_id}/analytics", response_model=Dict[str, Any], summary="Get venue analytics")
async def get_venue_analytics(venue_id: str, current_user: Dict[str, Any] = Depends(get_current_admin_user)):
    """
    Get venue analytics - redirects to dashboard service for comprehensive analytics
    
    For detailed analytics, use:
    - GET /api/v1/dashboard (main dashboard)
    - GET /api/v1/dashboard/analytics (comprehensive analytics)
    - GET /api/v1/dashboard/analytics/revenue (revenue analytics)
    - GET /api/v1/dashboard/analytics/menu (menu analytics)
    """
    try:
        venue = await venues_endpoint.get_item(venue_id, current_user)
        
        # Use dashboard service for comprehensive analytics
        from app.services.dashboard import DashboardService
        dashboard_service = DashboardService()
        analytics = await dashboard_service.get_venue_dashboard(venue_id)
        
        logger.info(f"Analytics retrieved for venue: {venue_id}")
        return analytics
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting venue analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get analytics"
        )


# =============================================================================
# MEDIA UPLOAD ENDPOINTS
# =============================================================================

@router.post("/{venue_id}/logo", response_model=ApiResponseDTO, summary="Upload venue logo")
async def upload_venue_logo(venue_id: str, file: UploadFile = File(...), current_user: Dict[str, Any] = Depends(get_current_admin_user)):
    """Upload venue logo"""
    try:
        venue = await venues_endpoint.get_item(venue_id, current_user)
        
        from app.services.storage import get_storage_service
        storage_service = get_storage_service()
        logo_url = await storage_service.upload_image(file, "venues", venue_id)
        
        repo = get_venue_repo()
        await repo.update(venue_id, {"logo_url": logo_url})
        
        logger.info(f"Logo uploaded for venue: {venue_id}")
        return ApiResponseDTO(success=True, message="Logo uploaded successfully", data={"logo_url": logo_url})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading logo for venue {venue_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload logo"
        )


# =============================================================================
# OPERATING HOURS ENDPOINTS
# =============================================================================

@router.put("/{venue_id}/hours", response_model=ApiResponseDTO, summary="Update operating hours")
async def update_operating_hours(venue_id: str, operating_hours: List[VenueOperatingHours], current_user: Dict[str, Any] = Depends(get_current_admin_user)):
    """Update venue operating hours"""
    try:
        venue = await venues_endpoint.get_item(venue_id, current_user)
        hours_data = [hours.dict() for hours in operating_hours]
        await venue_service.update_operating_hours(venue_id, hours_data)
        
        return ApiResponseDTO(success=True, message="Operating hours updated successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating operating hours for venue {venue_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update operating hours"
        )


@router.get("/{venue_id}/hours", response_model=List[VenueOperatingHours], summary="Get operating hours")
async def get_operating_hours(venue_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get venue operating hours"""
    try:
        venue = await venues_endpoint.get_item(venue_id, current_user)
        return venue.operating_hours or []
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting operating hours for venue {venue_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get operating hours"
        )


# =============================================================================
# SUBSCRIPTION MANAGEMENT
# =============================================================================

@router.put("/{venue_id}/subscription", response_model=ApiResponseDTO, summary="Update subscription")
async def update_subscription(venue_id: str, subscription_plan: SubscriptionPlan, subscription_status: SubscriptionStatus, current_user: Dict[str, Any] = Depends(get_current_admin_user)):
    """Update venue subscription"""
    try:
        venue = await venues_endpoint.get_item(venue_id, current_user)
        await venue_service.update_subscription(venue_id, subscription_plan.value, subscription_status.value)
        
        return ApiResponseDTO(success=True, message="Subscription updated successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating subscription for venue {venue_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update subscription"
        )


# =============================================================================
# STATUS MANAGEMENT
# =============================================================================

class VenueStatusUpdate(BaseModel):
    """Venue status update model"""
    is_open: bool
    reason: Optional[str] = None


@router.post("/{venue_id}/toggle-status", response_model=ApiResponseDTO, summary="Toggle venue status")
async def toggle_venue_status(venue_id: str, status_update: VenueStatusUpdate, current_user: Dict[str, Any] = Depends(get_current_admin_user)):
    """Toggle venue open/closed status"""
    try:
        venue = await venues_endpoint.get_item(venue_id, current_user)
        result = await venue_service.toggle_venue_status(venue_id, status_update.is_open, status_update.reason, current_user['id'])
        
        status_text = "opened" if status_update.is_open else "closed"
        return ApiResponseDTO(success=True, message=f"Venue {status_text} successfully", data=result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling venue status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update venue status"
        )


@router.get("/{venue_id}/status", response_model=Dict[str, Any], summary="Get venue status")
async def get_venue_status(venue_id: str, current_user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """Get venue status"""
    try:
        status_info = await venue_service.get_venue_status_info(venue_id)
        if not status_info:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venue not found")
        
        if not current_user and not status_info.get('is_active'):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venue not found")
        
        return status_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting venue status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get venue status"
        )


@router.get("/{venue_id}/control-panel-status", response_model=Dict[str, Any], summary="Get control panel status")
async def get_control_panel_status(venue_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get simplified venue status for control panel"""
    try:
        user_role = await _get_user_role(current_user)
        if user_role not in ['superadmin', 'admin', 'operator']:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        
        status_info = await venue_service.get_control_panel_status(venue_id)
        if not status_info:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venue not found")
        
        return status_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting control panel status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get control panel status"
        )


# =============================================================================
# DATA MAINTENANCE
# =============================================================================

@router.post("/fix-venue-status", response_model=ApiResponseDTO, summary="Fix venue status data")
async def fix_venue_status_data(current_user: Dict[str, Any] = Depends(get_current_admin_user)):
    """Fix venue status data for all venues"""
    try:
        user_role = await _get_user_role(current_user)
        if user_role != 'superadmin':
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only superadmin can run data maintenance")
        
        result = await venue_service.fix_all_venue_statuses()
        
        return ApiResponseDTO(
            success=True,
            message=f"Venue status data fixed. Updated {result['fixed_count']} venues.",
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fixing venue status data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fix venue status data"
        )


@router.get("/{venue_id}/users", response_model=List[Dict[str, Any]], summary="Get venue users")
async def get_venue_users(venue_id: str, current_user: Dict[str, Any] = Depends(get_current_admin_user)):
    """Get all users assigned to a specific venue"""
    try:
        user_repo = get_repository_manager().get_repository('user')
        role_repo = get_role_repo()
        
        venue_users = await user_repo.get_by_venue(venue_id)
        
        formatted_users = []
        for user in venue_users:
            role_id = user.get('role_id')
            role_name = 'operator'
            role_display_name = 'Operator'
            
            if role_id:
                try:
                    role = await role_repo.get_by_id(role_id)
                    if role:
                        role_name = role.get('name', 'operator')
                        role_display_name = role.get('display_name', role_name.title())
                except Exception as e:
                    logger.warning(f"Could not fetch role for role_id {role_id}: {e}")
            
            first_name = user.get('first_name', '')
            last_name = user.get('last_name', '')
            is_active = user.get('is_active', True)
            last_login = user.get('last_login')
            email = user.get('email', '')
            phone = user.get('phone', '')
            workspace_id = user.get('workspace_id', '')
            venue_id_val = user.get('venue_id', '')
            
            if last_login and hasattr(last_login, 'isoformat'):
                last_login = last_login.isoformat()
            
            # Determine status text
            status = "Active" if is_active else "Inactive"
            
            formatted_user = {
                "id": user.get('id'),
                "name": f"{first_name} {last_name}",
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "phone": phone,
                "role": role_name,
                "role_display_name": role_display_name,
                "status": status,
                "is_active": is_active,
                "workspace_id": workspace_id,
                "venue_id": venue_id_val,
                "created_at": user.get('created_at'),
                "updated_at": user.get('updated_at'),
                "role_id": role_id,
                "last_login": last_login,
            }
            formatted_users.append(formatted_user)
        
        logger.info(f"Retrieved {len(formatted_users)} users for venue: {venue_id}")
        return formatted_users
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting venue users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get venue users"
        )
