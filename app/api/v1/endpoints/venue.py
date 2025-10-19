"""

Enhanced Venue Management API Endpoints

Refactored with standardized patterns, workspace isolation, and comprehensive CRUD

"""

from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Query

from datetime import datetime



from  app.models.schemas import Venue, VenueOperatingHours, SubscriptionPlan, SubscriptionStatus, VenueStatus

from app.models.dto import (

  VenueCreateDTO, VenueUpdateDTO, VenueResponseDTO, VenueWorkspaceListDTO, 

  ApiResponseDTO, PaginatedResponseDTO

)

from app.core.base_endpoint import WorkspaceIsolatedEndpoint

from app.database.firestore import get_venue_repo, VenueRepository

from app.core.security import get_current_user, get_current_admin_user

from app.core.logging_config import get_logger

from app.core.error_recovery import ErrorRecoveryMixin



logger = get_logger(__name__)

router = APIRouter()





def clean_venue_status(venue_data: Dict[str, Any]) -> Dict[str, Any]:

  """Clean and normalize venue status field"""

  if 'status' in venue_data:

    status_value = venue_data['status']

    # Handle cases where status might be incorrectly formatted

    if isinstance(status_value, str):

      # Remove any extra quotes that might be present

      cleaned_status = status_value.strip("'\"")

      # Validate against enum values

      valid_statuses = [e.value for e in VenueStatus]

      if cleaned_status in valid_statuses:

        venue_data['status'] = cleaned_status

      else:

        venue_data['status'] = VenueStatus.ACTIVE.value

    else:

      venue_data['status'] = VenueStatus.ACTIVE.value

  else:

    venue_data['status'] = VenueStatus.ACTIVE.value

   

  return venue_data





class VenuesEndpoint(WorkspaceIsolatedEndpoint[Venue, VenueCreateDTO, VenueUpdateDTO]):

  """Enhanced Venues endpoint with workspace isolation and comprehensive CRUD"""

   

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

   

  async def _prepare_create_data(self, 

                 data: Dict[str, Any], 

                 current_user: Optional[Dict[str, Any]]) -> Dict[str, Any]:

    """Prepare venue data before creation"""

    # Set owner and admin

    if current_user:

      data['owner_id'] = current_user['id']

      data['admin_id'] = current_user['id']

       

      # Set workspace from current user if not provided

      if not data.get('workspace_id'):

        data['workspace_id'] = current_user.get('workspace_id')

     

    # Set default values

    data['is_active'] = True

    data['is_verified'] = False

    data['rating'] = 0.0

    data['total_reviews'] = 0

     

    return data

   

  async def _validate_create_permissions(self, 

                     data: Dict[str, Any], 

                     current_user: Optional[Dict[str, Any]]):

    """Validate venue creation permissions"""

    # Basic permission check - only admin and superadmin can create venues

    if not current_user:

      raise HTTPException(

        status_code=status.HTTP_401_UNAUTHORIZED,

        detail="Authentication required"

      )

   

  async def _validate_access_permissions(self, 

                     item: Dict[str, Any], 

                     current_user: Optional[Dict[str, Any]]):

    """Validate venue access permissions"""

    if not current_user:

      return # Public access allowed for venue details

     

    # Call parent workspace validation

    await super()._validate_access_permissions(item, current_user)

     

    # Basic access validation handled by parent class

   

  async def _build_query_filters(self, 

                 filters: Optional[Dict[str, Any]], 

                 search: Optional[str],

                 current_user: Optional[Dict[str, Any]]) -> List[tuple]:

    """Build query filters for venue search"""

    query_filters = []

     

    # Add workspace filter for non-admin users

    if current_user:

      from app.core.security import _get_user_role

      user_role = await _get_user_role(current_user)

      if user_role not in ['admin', 'superadmin']:

        workspace_id = current_user.get('workspace_id')

        if workspace_id:

          query_filters.append(('workspace_id', '==', workspace_id))

     

    # Add additional filters

    if filters:

      for field, value in filters.items():

        if value is not None:

          query_filters.append((field, '==', value))

     

    return query_filters

   

  async def get_items(self, 

            page: int = 1, 

            page_size: int = 10,

            search: Optional[str] = None,

            filters: Optional[Dict[str, Any]] = None,

            current_user: Optional[Dict[str, Any]] = None):

    """Get paginated list of venues with proper status handling"""

    try:

      repo = self.get_repository()

       

      # Build query filters

      query_filters = await self._build_query_filters(filters, search, current_user)

       

      # Get all items matching filters

      all_items = await repo.query(query_filters) if query_filters else await repo.get_all()

       

      # Apply text search if provided

      if search:

        search_lower = search.lower()

        # Basic text search - override in subclasses for more sophisticated search

        all_items = [

          item for item in all_items

          if any(search_lower in str(value).lower() for value in item.values() if isinstance(value, str))

        ]

       

      # Filter items based on user permissions

      filtered_items = await self._filter_items_for_user(all_items, current_user)

       

      # Calculate pagination

      total = len(filtered_items)

      start_idx = (page - 1) * page_size

      end_idx = start_idx + page_size

      items_page = filtered_items[start_idx:end_idx]

       

      # Convert to model objects with proper status handling

      items = []

      for item in items_page:

        item = clean_venue_status(item)

        items.append(VenueResponseDTO(**item))

       

      # Calculate pagination metadata

      total_pages = (total + page_size - 1) // page_size

      has_next = page < total_pages

      has_prev = page > 1

       

      from app.models.dto import PaginatedResponse

      return PaginatedResponse(

        success=True,

        data=items,

        total=total,

        page=page,

        page_size=page_size,

        total_pages=total_pages,

        has_next=has_next,

        has_prev=has_prev

      )

       

    except HTTPException:

      raise

    except Exception as e:

      logger.error(f"Error getting venues list: {e}")

      raise HTTPException(

        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

        detail="Failed to get venues list"

      )

   

  async def search_venues_by_text(self, 

                 search_term: str,

                 current_user: Optional[Dict[str, Any]] = None) -> List[Venue]:

    """Search venues by name, description, or cuisine"""

    repo = self.get_repository()

     

    # Build base filters

    base_filters = await self._build_query_filters(None, None, current_user)

     

    # Search in multiple fields

    search_fields = ['name', 'description', 'address', 'cuisine_types']

    matching_venues = await repo.search_text(

      search_fields=search_fields,

      search_term=search_term,

      additional_filters=base_filters,

      limit=50

    )

     

    # Clean and add default status if missing

    venues = []

    for venue in matching_venues:

      venue = clean_venue_status(venue)

      venues.append(VenueResponseDTO(**venue))

    return venues

   

  async def get_venues_by_subscription_status(self, 

                       status: SubscriptionStatus,

                       current_user: Dict[str, Any]) -> List[Venue]:

    """Get venues by subscription status"""

    repo = self.get_repository()

     

    # Build filters

    filters = [('subscription_status', '==', status.value)]

     

    # Add workspace filter for non-admin users

    from  app.core.security import _get_user_role

    user_role = await _get_user_role(current_user)

    if user_role not in ['admin', 'superadmin']:

      workspace_id = current_user.get('workspace_id')

      if workspace_id:

        filters.append(('workspace_id', '==', workspace_id))

     

    venues_data = await repo.query(filters)

    # Clean and add default status if missing

    venues = []

    for venue in venues_data:

      venue = clean_venue_status(venue)

      venues.append(VenueResponseDTO(**venue))

    return venues

   

  async def get_item(self, 

           item_id: str, 

           current_user: Optional[Dict[str, Any]]):

    """Get venue by ID with proper status handling"""

    try:

      repo = self.get_repository()

      item = await repo.get_by_id(item_id)

       

      if not item:

        raise HTTPException(

          status_code=status.HTTP_404_NOT_FOUND,

          detail="Venue not found"

        )

       

      # Validate access

      await self._validate_access_permissions(item, current_user)

       

      # Clean and ensure status field is properly set

      item = clean_venue_status(item)

       

      return VenueResponseDTO(**item)

       

    except HTTPException:

      raise

    except Exception as e:

      logger.error(f"Error getting venue: {e}")

      raise HTTPException(

        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

        detail="Failed to get venue"

      )

   

  async def get_venue_analytics(self, 

                venue_id: str,

                current_user: Dict[str, Any]) -> Dict[str, Any]:

    """Get basic analytics for a venue"""

    repo = self.get_repository()

     

    # Validate access

    venue_data = await repo.get_by_id(venue_id)

    if not venue_data:

      raise HTTPException(

        status_code=status.HTTP_404_NOT_FOUND,

        detail="Venue not found"

      )

     

    await self._validate_access_permissions(venue_data, current_user)

     

    # Get related data counts

    from app.database.firestore import (

      get_menu_item_repo, get_table_repo, get_order_repo, get_customer_repo

    )

     

    menu_repo = get_menu_item_repo()

    table_repo = get_table_repo()

    order_repo = get_order_repo()

    customer_repo = get_customer_repo()

     

    # Count items

    menu_items = await menu_repo.get_by_venue(venue_id)

    tables = await table_repo.get_by_venue(venue_id)

    orders = await order_repo.get_by_venue(venue_id, limit=100) # Recent orders

    customers = await customer_repo.get_by_venue(venue_id)

     

    return {

      "venue_id": venue_id,

      "total_menu_items": len(menu_items),

      "total_tables": len(tables),

      "recent_orders": len(orders),

      "total_customers": len(customers),

      "rating": venue_data.get('rating', 0.0),

      "total_reviews": venue_data.get('total_reviews', 0),

      "subscription_status": venue_data.get('subscription_status'),

      "is_active": venue_data.get('is_active', False)

    }





# Initialize endpoint

venues_endpoint = VenuesEndpoint()





# =============================================================================

# PUBLIC ENDPOINTS (No Authentication Required)

# =============================================================================



@router.get("/public", 

      response_model=PaginatedResponseDTO,

      summary="Get public venues",

      description="Get paginated list of active venues (public endpoint)")

async def get_public_venues(

  page: int = Query(1, ge=1, description="Page number"),

  page_size: int = Query(10, ge=1, le=50, description="Items per page"),

  search: Optional[str] = Query(None, description="Search by name or cuisine"),

  cuisine_type: Optional[str] = Query(None, description="Filter by cuisine type"),

  price_range: Optional[str] = Query(None, description="Filter by price range")

):

  """Get public venues (no authentication required)"""

  try:

    repo = get_venue_repo()

     

    # Build filters for public venues

    filters = [('is_active', '==', True)]

     

    if cuisine_type:

      # Note: This is a simplified filter - in practice, you'd need array-contains

      filters.append(('cuisine_types', 'array-contains', cuisine_type))

     

    if price_range:

      filters.append(('price_range', '==', price_range))

     

    # Get filtered venues

    all_venues = await repo.query(filters)

     

    # Apply text search if provided

    if search:

      search_lower = search.lower()

      all_venues = [

        venue for venue in all_venues

        if (search_lower in venue.get('name', '').lower() or

          search_lower in venue.get('description', '').lower() or

          any(search_lower in cuisine.lower() for cuisine in venue.get('cuisine_types', [])))

      ]

     

    # Calculate pagination

    total = len(all_venues)

    start_idx = (page - 1) * page_size

    end_idx = start_idx + page_size

    venues_page = all_venues[start_idx:end_idx]

     

    # Convert to Venue objects - clean and add default status if missing

    venues = []

    for venue in venues_page:

      venue = clean_venue_status(venue)

      venues.append(VenueResponseDTO(**venue))

     

    # Calculate pagination metadata

    total_pages = (total + page_size - 1) // page_size

    has_next = page < total_pages

    has_prev = page > 1

     

    logger.info(f"Public venues retrieved: {len(venues)} of {total}")

     

    return PaginatedResponseDTO(

      success=True,

      data=venues,

      total=total,

      page=page,

      page_size=page_size,

      total_pages=total_pages,

      has_next=has_next,

      has_prev=has_prev

    )

     

  except Exception as e:

    logger.error(f"Error getting public venues: {e}")

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail="Failed to get venues"

    )





@router.get("/public/{venue_id}", 

      response_model=VenueResponseDTO,

      summary="Get public venue details",

      description="Get venue details by ID (public endpoint)")

async def get_public_venue(venue_id: str):

  """Get venue by ID (public endpoint)"""

  try:

    repo = get_venue_repo()

    venue = await repo.get_by_id(venue_id)

     

    if not venue:

      raise HTTPException(

        status_code=status.HTTP_404_NOT_FOUND,

        detail="Venue not found"

      )

     

    # Only return active venues for public access

    if not venue.get('is_active', False):

      raise HTTPException(

        status_code=status.HTTP_404_NOT_FOUND,

        detail="Venue not found"

      )

     

    # Clean and add default status if missing

    venue = clean_venue_status(venue)

     

    # Debug: Log the actual status value to understand the issue

    logger.info(f"Venue {venue_id} status value: {repr(venue.get('status'))}")

     

    logger.info(f"Public venue retrieved: {venue_id}")

    return VenueResponseDTO(**venue)

     

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"Error getting public venue {venue_id}: {e}")

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail="Failed to get venue"

    )





# =============================================================================

# WORKSPACE VENUS API ENDPOINTS

# =============================================================================



@router.get("/workspace/{workspace_id}/venues", 

      response_model=List[VenueWorkspaceListDTO],

      summary="Get venues by workspace ID",

      description="Get simplified venue list for workspace (Venus API)")

async def get_venues_by_workspace(

  workspace_id: str,

  current_user: Dict[str, Any] = Depends(get_current_user)

):

  """Get simplified venue list for workspace (Venus API)"""

  try:

    # Verify workspace access

    from  app.core.security import verify_workspace_access

    await verify_workspace_access(workspace_id, current_user)

     

    repo = get_venue_repo()

    venues_data = await repo.get_by_workspace(workspace_id)

     

    # Convert to simplified venue DTOs with only required data

    venues = []

    for venue in venues_data:

      venue = clean_venue_status(venue)

       

      # Create simplified location info

      location_info = {}

      if venue.get('location'):

        location_info = {

          'city': venue['location'].get('city', ''),

          'state': venue['location'].get('state', ''),

          'country': venue['location'].get('country', ''),

          'address': venue['location'].get('address', '')

        }

       

      # Create simplified venue DTO

      simplified_venue = VenueWorkspaceListDTO(

        id=venue['id'],

        name=venue.get('name', ''),

        description=venue.get('description'),

        location=location_info,

        phone=venue.get('phone'),

        email=venue.get('email'),

        is_active=venue.get('is_active', False),

        is_open=venue.get('is_open', False),

        status=venue.get('status', VenueStatus.ACTIVE),

        subscription_status=venue.get('subscription_status', SubscriptionStatus.ACTIVE),

        created_at=venue.get('created_at', datetime.utcnow()),

        updated_at=venue.get('updated_at', datetime.utcnow())

      )

      venues.append(simplified_venue)

     

    logger.info(f"Retrieved {len(venues)} simplified venues for workspace: {workspace_id}")

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



@router.get("", 

      response_model=PaginatedResponseDTO,

      summary="Get venues",

      description="Get paginated list of venues (authenticated)")

async def get_venues(

  page: int = Query(1, ge=1, description="Page number"),

  page_size: int = Query(10, ge=1, le=100, description="Items per page"),

  search: Optional[str] = Query(None, description="Search by name or description"),

  subscription_status: Optional[SubscriptionStatus] = Query(None, description="Filter by subscription status"),

  is_active: Optional[bool] = Query(None, description="Filter by active status"),

  current_user: Dict[str, Any] = Depends(get_current_admin_user)

):

  """Get venues with pagination and filtering"""

  filters = {}

  if subscription_status:

    filters['subscription_status'] = subscription_status.value

  if is_active is not None:

    filters['is_active'] = is_active

   

  return await venues_endpoint.get_items(

    page=page,

    page_size=page_size,

    search=search,

    filters=filters,

    current_user=current_user

  )





@router.post("", 

       response_model=ApiResponseDTO,

       status_code=status.HTTP_201_CREATED,

       summary="Create venue",

       description="Create a new venue")

async def create_venue(

  venue_data: VenueCreateDTO,

  current_user: Dict[str, Any] = Depends(get_current_admin_user)

):

  """Create a new venue"""

  return await venues_endpoint.create_item(venue_data, current_user)





@router.get("/my-venues", 

      response_model=List[VenueResponseDTO],

      summary="Get my venues",

      description="Get venues owned by current user")

async def get_my_venues(current_user: Dict[str, Any] = Depends(get_current_admin_user)):

  """Get current user's venues"""

  try:

    repo = get_venue_repo()

    venues_data = await repo.get_by_owner(current_user["id"])

     

    # Clean and add default status if missing

    venues = []

    for venue in venues_data:

      venue = clean_venue_status(venue)

      venues.append(VenueResponseDTO(**venue))

     

    logger.info(f"Retrieved {len(venues)} venues for user {current_user['id']}")

    return venues

     

  except Exception as e:

    logger.error(f"Error getting user venues: {e}")

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail="Failed to get venues"

    )





@router.get("/{venue_id}", 

      response_model=VenueResponseDTO,

      summary="Get venue by ID",

      description="Get specific venue by ID")

async def get_venue(

  venue_id: str,

  current_user: Dict[str, Any] = Depends(get_current_user)

):

  """Get venue by ID"""

  return await venues_endpoint.get_item(venue_id, current_user)





@router.put("/{venue_id}", 

      response_model=ApiResponseDTO,

      summary="Update venue",

      description="Update venue information")

async def update_venue(

  venue_id: str,

  venue_update: VenueUpdateDTO,

  current_user: Dict[str, Any] = Depends(get_current_admin_user)

):

  """Update venue information"""

  return await venues_endpoint.update_item(venue_id, venue_update, current_user)





@router.delete("/{venue_id}", 

        response_model=ApiResponseDTO,

        summary="Delete venue",

        description="Delete venue (hard delete)")

async def delete_venue(

  venue_id: str,

  current_user: Dict[str, Any] = Depends(get_current_admin_user)

):

  """Delete venue (hard delete - permanently removes venue)"""

  try:

    logger.info(f"Venue deletion requested for venue_id: {venue_id} by user: {current_user.get('id')}")

    result = await venues_endpoint.delete_item(venue_id, current_user, soft_delete=False)

    logger.info(f"Venue deletion completed for venue_id: {venue_id}")

    return result

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"Error deleting venue {venue_id}: {e}")

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail="Failed to delete venue"

    )





@router.post("/{venue_id}/deactivate", 

       response_model=ApiResponseDTO,

       summary="Deactivate venue",

       description="Deactivate venue (soft delete)")

async def deactivate_venue(

  venue_id: str,

  current_user: Dict[str, Any] = Depends(get_current_admin_user)

):

  """Deactivate venue (soft delete)"""

  try:

    logger.info(f"Venue deactivation requested for venue_id: {venue_id} by user: {current_user.get('id')}")

    result = await venues_endpoint.delete_item(venue_id, current_user, soft_delete=True)

    logger.info(f"Venue deactivation completed for venue_id: {venue_id}")

    return result

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"Error deactivating venue {venue_id}: {e}")

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail="Failed to deactivate venue"

    )





@router.post("/{venue_id}/activate", 

       response_model=ApiResponseDTO,

       summary="Activate venue",

       description="Activate deactivated venue")

async def activate_venue(

  venue_id: str,

  current_user: Dict[str, Any] = Depends(get_current_admin_user)

):

  """Activate venue"""

  try:

    repo = get_venue_repo()

     

    # Check if venue exists

    venue = await repo.get_by_id(venue_id)

    if not venue:

      raise HTTPException(

        status_code=status.HTTP_404_NOT_FOUND,

        detail="Venue not found"

      )

     

    # Validate access permissions

    await venues_endpoint._validate_access_permissions(venue, current_user)

     

    # Activate venue

    await repo.update(venue_id, {"is_active": True})

     

    logger.info(f"Venue activated: {venue_id}")

    return ApiResponseDTO(

      success=True,

      message="Venue activated successfully"

    )

     

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"Error activating venue {venue_id}: {e}")

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail="Failed to activate venue"

    )





# =============================================================================

# SEARCH ENDPOINTS

# =============================================================================



@router.get("/search/text", 

      response_model=List[VenueResponseDTO],

      summary="Search venues",

      description="Search venues by name, description, or cuisine")

async def search_venues(

  q: str = Query(..., min_length=2, description="Search query"),

  current_user: Dict[str, Any] = Depends(get_current_user)

):

  """Search venues by text"""

  try:

    venues = await venues_endpoint.search_venues_by_text(q, current_user)

     

    logger.info(f"Venue search performed: '{q}' - {len(venues)} results")

    return venues

     

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"Error searching venues: {e}")

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail="Search failed"

    )





@router.get("/filter/subscription/{status}", 

      response_model=List[VenueResponseDTO],

      summary="Get venues by subscription status",

      description="Get venues filtered by subscription status")

async def get_venues_by_subscription(

  status: SubscriptionStatus,

  current_user: Dict[str, Any] = Depends(get_current_admin_user)

):

  """Get venues by subscription status"""

  try:

    venues = await venues_endpoint.get_venues_by_subscription_status(status, current_user)

     

    logger.info(f"Venues retrieved by subscription status '{status}': {len(venues)}")

    return venues

     

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"Error getting venues by subscription: {e}")

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail="Failed to get venues"

    )





# =============================================================================

# ANALYTICS ENDPOINTS

# =============================================================================



@router.get("/{venue_id}/analytics", 

      response_model=Dict[str, Any],

      summary="Get venue analytics",

      description="Get basic analytics for a venue")

async def get_venue_analytics(

  venue_id: str,

  current_user: Dict[str, Any] = Depends(get_current_admin_user)

):

  """Get venue analytics"""

  try:

    analytics = await venues_endpoint.get_venue_analytics(venue_id, current_user)

     

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



@router.post("/{venue_id}/logo", 

       response_model=ApiResponseDTO,

       summary="Upload venue logo",

       description="Upload venue logo image")

async def upload_venue_logo(

  venue_id: str,

  file: UploadFile = File(...),

  current_user: Dict[str, Any] = Depends(get_current_admin_user)

):

  """Upload venue logo to Cloud Storage"""

  try:

    # Validate venue access

    venue = await venues_endpoint.get_item(venue_id, current_user)

     

    # Upload logo using storage service

    from  app.services.storage_service import get_storage_service

    storage_service = get_storage_service()

    logo_url = await storage_service.upload_image(file, "venues", venue_id)

     

    # Update venue with logo URL

    repo = get_venue_repo()

    await repo.update(venue_id, {"logo_url": logo_url})

     

    logger.info(f"Logo uploaded for venue: {venue_id}")

    return ApiResponseDTO(

      success=True,

      message="Logo uploaded successfully",

      data={"logo_url": logo_url}

    )

     

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



@router.put("/{venue_id}/hours", 

      response_model=ApiResponseDTO,

      summary="Update operating hours",

      description="Update venue operating hours")

async def update_operating_hours(

  venue_id: str,

  operating_hours: List[VenueOperatingHours],

  current_user: Dict[str, Any] = Depends(get_current_admin_user)

):

  """Update venue operating hours"""

  try:

    # Validate venue access

    venue = await venues_endpoint.get_item(venue_id, current_user)

     

    # Update operating hours

    repo = get_venue_repo()

    hours_data = [hours.dict() for hours in operating_hours]

    await repo.update(venue_id, {"operating_hours": hours_data})

     

    logger.info(f"Operating hours updated for venue: {venue_id}")

    return ApiResponseDTO(

      success=True,

      message="Operating hours updated successfully"

    )

     

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"Error updating operating hours for venue {venue_id}: {e}")

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail="Failed to update operating hours"

    )





@router.get("/{venue_id}/hours", 

      response_model=List[VenueOperatingHours],

      summary="Get operating hours",

      description="Get venue operating hours")

async def get_operating_hours(

  venue_id: str,

  current_user: Dict[str, Any] = Depends(get_current_user)

):

  """Get venue operating hours"""

  try:

    venue = await venues_endpoint.get_item(venue_id, current_user)

     

    operating_hours = venue.operating_hours or []

    return operating_hours

     

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"Error getting operating hours for venue {venue_id}: {e}")

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail="Failed to get operating hours"

    )





# =============================================================================

# SUBSCRIPTION MANAGEMENT ENDPOINTS

# =============================================================================



@router.put("/{venue_id}/subscription", 

      response_model=ApiResponseDTO,

      summary="Update subscription",

      description="Update venue subscription plan and status")

async def update_subscription(

  venue_id: str,

  subscription_plan: SubscriptionPlan,

  subscription_status: SubscriptionStatus,

  current_user: Dict[str, Any] = Depends(get_current_admin_user)

):

  """Update venue subscription"""

  try:

    # Validate venue access

    venue = await venues_endpoint.get_item(venue_id, current_user)

     

    # Update subscription

    repo = get_venue_repo()

    await repo.update(venue_id, {

      "subscription_plan": subscription_plan.value,

      "subscription_status": subscription_status.value

    })

     

    logger.info(f"Subscription updated for venue: {venue_id}")

    return ApiResponseDTO(

      success=True,

      message="Subscription updated successfully"

    )

     

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"Error updating subscription for venue {venue_id}: {e}")

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail="Failed to update subscription"

    )





# =============================================================================

# DATA MAINTENANCE ENDPOINTS

# =============================================================================



@router.post("/fix-venue-status", 

       response_model=ApiResponseDTO,

       summary="Fix venue status data",

       description="Fix any venues with incorrect status values")

async def fix_venue_status_data(

  current_user: Dict[str, Any] = Depends(get_current_admin_user)

):

  """Fix venue status data for all venues"""

  try:

    # Only allow superadmin to run this

    from app.core.security import _get_user_role

    user_role = await _get_user_role(current_user)

    if user_role != 'superadmin':

      raise HTTPException(

        status_code=status.HTTP_403_FORBIDDEN,

        detail="Only superadmin can run data maintenance"

      )

     

    repo = get_venue_repo()

    all_venues = await repo.get_all()

     

    fixed_count = 0

    for venue in all_venues:

      original_status = venue.get('status')

      cleaned_venue = clean_venue_status(venue.copy())

      new_status = cleaned_venue.get('status')

       

      # If status was changed, update the venue

      if original_status != new_status:

        await repo.update(venue['id'], {'status': new_status})

        fixed_count += 1

        logger.info(f"Fixed venue {venue['id']} status from {repr(original_status)} to {repr(new_status)}")

     

    logger.info(f"Venue status data maintenance completed. Fixed {fixed_count} venues.")

     

    return ApiResponseDTO(

      success=True,

      message=f"Venue status data fixed. Updated {fixed_count} venues.",

      data={"fixed_count": fixed_count, "total_venues": len(all_venues)}

    )

     

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"Error fixing venue status data: {e}")

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail="Failed to fix venue status data"

    )





@router.get("/{venue_id}/users", 

      response_model=List[Dict[str, Any]],

      summary="Get venue users",

      description="Get all users assigned to a specific venue")

async def get_venue_users(

  venue_id: str,

  current_user: Dict[str, Any] = Depends(get_current_admin_user)

):

  """Get all users assigned to a specific venue"""

  try:

    # Validate venue access

    venue = await venues_endpoint.get_item(venue_id, current_user)

     

    # Get user repository

    from app.core.dependency_injection import get_repository_manager

    user_repo = get_repository_manager().get_repository('user')

     

    # Get users assigned to this venue

    venue_users = await user_repo.get_by_venue(venue_id)

     

    # Format user data for response

    formatted_users = []

    for user in venue_users:

      formatted_user = {

        "id": user.get('id'),

        "email": user.get('email'),

        "first_name": user.get('first_name'),

        "last_name": user.get('last_name'),

        "phone": user.get('phone'),

        "role_id": user.get('role_id'),

        "is_active": user.get('is_active', True),

        "is_verified": user.get('is_verified', False),

        "last_login": user.get('last_login'),

        "created_at": user.get('created_at'),

        "updated_at": user.get('updated_at'),

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