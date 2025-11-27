"""
User Management API Endpoints
Comprehensive user management with profiles and administration
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel

from app.models.entities import User
from app.models.requests import (
    UserCreateDTO, UserUpdateDTO, UserResponseDTO,
    ApiResponseDTO, SimpleApiResponseDTO,
    PaginatedResponseDTO
)
from app.core.base_endpoint import WorkspaceIsolatedEndpoint
from app.database.repository_manager import get_user_repo
from app.database.validated_repository import get_validated_user_repo, ValidatedUserRepository
from app.core.security import get_current_user, get_password_hash
from app.core.logging import get_logger
from app.core.utils import validate_required_fields, raise_validation_error

logger = get_logger(__name__)
router = APIRouter()


class UserEndpoint(WorkspaceIsolatedEndpoint[User, UserCreateDTO, UserUpdateDTO]):
    """User endpoint with standardized CRUD operations"""
    
    def __init__(self):
        super().__init__(
            model_class=User,
            create_schema=UserCreateDTO,
            update_schema=UserUpdateDTO,
            collection_name="users",
            require_auth=True,
            require_admin=False
        )
    
    def get_repository(self) -> ValidatedUserRepository:
        return get_validated_user_repo()
    
    async def _prepare_create_data(self, 
                                  data: Dict[str, Any], 
                                  current_user: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare user data before creation"""
        # Remove confirm_password field
        data.pop('confirm_password', None)
        
        # Set default values
        data['is_active'] = True
        data['is_verified'] = False
        data['email_verified'] = False
        data['phone_verified'] = False
        
        return data
    
    async def _validate_create_permissions(self, 
                                         data: Dict[str, Any], 
                                         current_user: Optional[Dict[str, Any]]):
        """Validate user creation permissions"""
        if not current_user:
            return  # Public registration allowed
        
        # Note: workspace_id field removed from users schema
        # Workspace validation would need alternative logic
    
    async def _validate_update_permissions(self, 
                                         item: Dict[str, Any], 
                                         current_user: Optional[Dict[str, Any]]):
        """Validate user update permissions"""
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        # Users can update their own profile
        if item['id'] == current_user['id']:
            return
        
        # Simplified permission check - admin can update any user, users can update themselves
        from app.core.security import _get_user_role
        user_role = await _get_user_role(current_user)
        
        if user_role not in ['admin', 'superadmin'] and item['id'] != current_user['id']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this user"
            )
    
    async def _build_query_filters(self, 
                                  filters: Optional[Dict[str, Any]], 
                                  search: Optional[str],
                                  current_user: Optional[Dict[str, Any]]) -> List[tuple]:
        """Build query filters for user search"""
        query_filters = []
        
        # Note: workspace_id field removed from users schema
        # Workspace filtering would need alternative logic
        
        # Add additional filters
        if filters:
            for field, value in filters.items():
                if value is not None:
                    query_filters.append((field, '==', value))
        
        return query_filters
    
    async def search_users_by_text(self, 
                                  search_term: str,
                                  current_user: Dict[str, Any]) -> List[User]:
        """Search users by name, email, or phone"""
        repo = self.get_repository()
        
        # Build base filters
        base_filters = await self._build_query_filters(None, None, current_user)
        
        # Search in multiple fields
        search_fields = ['first_name', 'last_name', 'email', 'phone']
        matching_users = await repo.search_text(
            search_fields=search_fields,
            search_term=search_term,
            additional_filters=base_filters,
            limit=50
        )
        
        return [UserResponseDTO(**user) for user in matching_users]


# Initialize endpoint
user_endpoint = UserEndpoint()


# =============================================================================
# PROFILE MANAGEMENT ENDPOINTS
# =============================================================================
# Note: Registration and login endpoints are in auth.py

@router.get("/profile", 
            response_model=UserResponseDTO,
            summary="Get user profile",
            description="Get current user's profile information")
async def get_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get current user profile"""
    return UserResponseDTO(**current_user)


@router.put("/profile", 
            response_model=ApiResponseDTO,
            summary="Update user profile",
            description="Update current user's profile information")
async def update_user_profile(
    update_data: UserUpdateDTO,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update user profile"""
    try:
        user_repo = get_user_repo()
        
        # Check if email is being updated and is unique
        if hasattr(update_data, 'email') and update_data.email and update_data.email != current_user.get("email"):
            existing_user = await user_repo.get_by_email(update_data.email)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already in use"
                )
        
        # Check if phone number is being updated and is unique
        if hasattr(update_data, 'phone') and update_data.phone and update_data.phone != current_user.get("phone"):
            existing_phone = await user_repo.get_by_phone(update_data.phone)
            if existing_phone:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phone number already in use"
                )
        
        # Update user
        updated_user = await get_auth_service().update_user(current_user['id'], update_data.model_dump(exclude_unset=True))
        
        logger.info(f"User profile updated: {current_user['id']}")
        return ApiResponseDTO(
            success=True,
            message="Profile updated successfully",
            data=UserResponseDTO(**updated_user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update failed"
        )


# =============================================================================
# USER MANAGEMENT ENDPOINTS (Admin)
# =============================================================================

@router.get("", 
            response_model=PaginatedResponseDTO,
            summary="Get users",
            description="Get paginated list of users (open access)")
async def get_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by name, email, or phone number"),
    role_id: Optional[str] = Query(None, description="Filter by role ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get users with pagination and filtering"""
    try:
        logger.info(f"GET /users called - page: {page}, page_size: {page_size}, search: {search}, role_id: {role_id}, is_active: {is_active}")
        
        # Get user repository directly
        user_repo = get_user_repo()
        
        # Build filters
        query_filters = []
        if role_id:
            query_filters.append(('role_id', '==', role_id))
        if is_active is not None:
            query_filters.append(('is_active', '==', is_active))
        
        # Get all users first (for total count)
        if query_filters:
            all_users = await user_repo.query(query_filters)
        else:
            all_users = await user_repo.get_all()
        
        logger.info(f"Found {len(all_users)} total users in database")
        
        # Apply search filter if provided
        if search:
            search_term = search.lower()
            filtered_users = []
            for user in all_users:
                # Search in name, email, phone
                if (search_term in user.get('first_name', '').lower() or
                    search_term in user.get('last_name', '').lower() or
                    search_term in user.get('email', '').lower() or
                    search_term in user.get('phone', '').lower()):
                    filtered_users.append(user)
            all_users = filtered_users
            logger.info(f"After search filter: {len(all_users)} users")
        
        # Calculate pagination
        total = len(all_users)
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        
        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_users = all_users[start_idx:end_idx]
        
        # Remove sensitive data and convert to response format
        response_users = []
        for user in paginated_users:
            # Remove sensitive fields
            user_copy = user.copy()
            user_copy.pop('hashed_password', None)
            
            # Convert to UserResponseDTO format
            try:
                user_response = UserResponseDTO(**user_copy)
                response_users.append(user_response.model_dump(mode='json'))
            except Exception as e:
                logger.warning(f"Error converting user {user.get('id', 'unknown')} to response format: {e}")
                # Fallback: include basic fields
                response_users.append({
                    'id': user.get('id'),
                    'email': user.get('email'),
                    'first_name': user.get('first_name'),
                    'last_name': user.get('last_name'),
                    'phone': user.get('phone'),
                    'role_id': user.get('role_id'),
                    'is_active': user.get('is_active', True),
                    'created_at': user.get('created_at'),
                    'updated_at': user.get('updated_at')
                })
        
        logger.info(f"Returning {len(response_users)} users for page {page}")
        
        return PaginatedResponseDTO(
            success=True,
            data=response_users,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
        
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get users"
        )


@router.post("", 
             response_model=ApiResponseDTO,
             status_code=status.HTTP_201_CREATED,
             summary="Create user",
             description="Create a new user (open access)")
async def create_user(
    user_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new user with pre-hashed password"""
    try:
        logger.info(f"POST /users called with data: {user_data}")
        
        # Basic validation using shared utility
        required_fields = ['email', 'phone', 'first_name', 'last_name', 'password', 'role_id']
        missing_fields = validate_required_fields(user_data, required_fields)
        if missing_fields:
            raise_validation_error(missing_fields)
        
        # Get user repository
        user_repo = get_user_repo()
        
        # Check if email already exists
        existing_email = await user_repo.get_by_email(user_data['email'])
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
        
        # Check if phone already exists
        existing_phone = await user_repo.get_by_phone(user_data['phone'])
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already exists"
            )
        
        # Validate role_id exists
        from app.database.repository_manager import get_role_repo
        role_repo = get_role_repo()
        role = await role_repo.get_by_id(user_data['role_id'])
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role_id: Role does not exist"
            )
        
        # Hash password with BCrypt
        try:
            server_hash = get_password_hash(user_data['password'])
            logger.info(f"Password hashed successfully for user creation")
        except ValueError as e:
            logger.warning(f"Password validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        
        # Generate consistent UUID for user ID
        import uuid
        user_id = str(uuid.uuid4())
        
        # Prepare user data
        new_user_data = {
            'id': user_id,  # Set consistent UUID format
            'email': user_data['email'],
            'phone': user_data['phone'],
            'first_name': user_data['first_name'],
            'last_name': user_data['last_name'],
            'hashed_password': server_hash,  # Store the properly processed server hash
            'role_id': user_data['role_id'],
            'venue_ids': user_data.get('venue_ids', []),  # Default to empty array if not provided
            'is_active': True,
            'is_verified': False,
            'email_verified': False,
            'phone_verified': False,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Create user with specific UUID (returns the full created user data, not just ID)
        created_user = await user_repo.create(new_user_data, doc_id=user_id)
        
        # Remove hashed_password from response
        created_user.pop('hashed_password', None)
        
        logger.info(f"User created successfully: {user_data['email']}")
        return ApiResponseDTO(
            success=True,
            message="User created successfully",
            data=created_user
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )


@router.get("/{user_id}", 
            response_model=UserResponseDTO,
            summary="Get user by ID",
            description="Get specific user by ID")
async def get_user(
    user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get user by ID"""
    return await user_endpoint.get_item(user_id, current_user)


@router.put("/{user_id}", 
            response_model=SimpleApiResponseDTO,
            summary="Update user",
            description="Update user by ID")
async def update_user(
    user_id: str,
    update_data: UserUpdateDTO,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update user by ID"""
    try:
        # Get the user repository
        user_repo = get_user_repo()
        
        # Get the user to validate it exists and check permissions
        user = await user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Validate update permissions
        await user_endpoint._validate_update_permissions(user, current_user)
        
        # Prepare update data
        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No data provided for update"
            )
        
        # Check for unique constraints if email or phone is being updated
        if 'email' in update_dict and update_dict['email'] != user.get('email'):
            existing_user = await user_repo.get_by_email(update_dict['email'])
            if existing_user and existing_user['id'] != user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already in use"
                )
        
        if 'phone' in update_dict and update_dict['phone'] != user.get('phone'):
            existing_phone = await user_repo.get_by_phone(update_dict['phone'])
            if existing_phone and existing_phone['id'] != user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phone number already in use"
                )
        
        # Update the user
        await user_repo.update(user_id, update_dict)
        
        logger.info(f"User updated successfully: {user_id}")
        
        # Return success message without user data
        return SimpleApiResponseDTO(
            success=True,
            message="User data updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )


@router.put("/{user_id}/deactivate", 
            response_model=SimpleApiResponseDTO,
            summary="Deactivate user",
            description="Deactivate user by ID (set is_active to False)")
async def deactivate_user(
    user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Deactivate user (set is_active to False)"""
    try:
        user_repo = get_user_repo()
        
        # Check if user exists
        user = await user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Validate permissions
        await user_endpoint._validate_update_permissions(user, current_user)
        
        # Deactivate user by setting is_active to False
        await user_repo.update(user_id, {"is_active": False})
        
        logger.info(f"User deactivated: {user_id} by {current_user['id']}")
        return SimpleApiResponseDTO(
            success=True,
            message="User deactivated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate user"
        )


@router.put("/{user_id}/activate", 
            response_model=SimpleApiResponseDTO,
            summary="Activate user",
            description="Activate user by ID (set is_active to True)")
async def activate_user(
    user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Activate user (set is_active to True)"""
    try:
        user_repo = get_user_repo()
        
        # Check if user exists
        user = await user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Validate permissions
        await user_endpoint._validate_update_permissions(user, current_user)
        
        # Activate user by setting is_active to True
        await user_repo.update(user_id, {"is_active": True})
        
        logger.info(f"User activated: {user_id} by {current_user['id']}")
        return SimpleApiResponseDTO(
            success=True,
            message="User activated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate user"
        )


# =============================================================================
# SEARCH ENDPOINTS
# =============================================================================

@router.get("/search/text", 
            response_model=List[UserResponseDTO],
            summary="Search users",
            description="Search users by name, email, or phone")
async def search_users(
    q: str = Query(..., min_length=2, description="Search query"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Search users by text"""
    try:
        users = await user_endpoint.search_users_by_text(q, current_user)
        
        logger.info(f"User search performed: '{q}' - {len(users)} results")
        return users
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in user search: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User search failed"
        )


# =============================================================================
# ADDRESS MANAGEMENT ENDPOINTS - TEMPORARILY DISABLED
# =============================================================================
# Note: UserAddress schema was removed during optimization
# These endpoints can be re-enabled when address management is needed

# =============================================================================
# USER DATA ENDPOINTS
# =============================================================================

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
            from app.core.security import get_user_primary_venue
            primary_venue = await get_user_primary_venue(current_user)
            
            # Get workspace information if venue exists
            workspace_data = None
            if primary_venue and primary_venue.get('workspace_id'):
                workspace_id = primary_venue['workspace_id']
                try:
                    from app.database.repository_manager import get_workspace_repo
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


@router.get("/me/data", summary="Get user data")
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


@router.post("/me/refresh-data", summary="Refresh user data")
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


# =============================================================================
# USER PREFERENCES AND ADDRESS MANAGEMENT
# =============================================================================

class UserAddress(BaseModel):
    """User address model"""
    id: Optional[str] = None
    address_line_1: str
    address_line_2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str = "India"
    is_default: bool = False


class UserPreferences(BaseModel):
    """User preferences model"""
    language: str = "en"
    timezone: str = "Asia/Kolkata"
    currency: str = "INR"
    notifications_enabled: bool = True
    email_notifications: bool = True
    sms_notifications: bool = False
    theme: str = "light"


@router.get("/me/addresses", 
            response_model=List[UserAddress],
            summary="Get user addresses",
            description="Get all addresses for current user")
async def get_user_addresses(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get user addresses"""
    try:
        user_repo = get_user_repo()
        
        # Get user data
        user = await user_repo.get_by_id(current_user['id'])
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Return addresses
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


@router.post("/me/addresses", 
             response_model=ApiResponseDTO,
             summary="Add user address",
             description="Add new address for current user")
async def add_user_address(
    address: UserAddress,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Add user address"""
    try:
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
        return ApiResponseDTO(
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


@router.put("/me/addresses/{address_id}", 
            response_model=ApiResponseDTO,
            summary="Update user address",
            description="Update existing address")
async def update_user_address(
    address_id: str,
    address: UserAddress,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update user address"""
    try:
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
        return ApiResponseDTO(
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


@router.delete("/me/addresses/{address_id}", 
               response_model=ApiResponseDTO,
               summary="Delete user address",
               description="Delete user address")
async def delete_user_address(
    address_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete user address"""
    try:
        user_repo = get_user_repo()
        
        # Get current addresses
        user = await user_repo.get_by_id(current_user['id'])
        addresses = user.get('addresses', [])
        
        # Find and remove address
        addresses = [addr for addr in addresses if addr['id'] != address_id]
        
        # Update user
        await user_repo.update(current_user['id'], {'addresses': addresses})
        
        logger.info(f"Address deleted for user: {current_user['id']}") 
        return ApiResponseDTO(
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


@router.get("/me/preferences", 
            response_model=UserPreferences,
            summary="Get user preferences",
            description="Get user preferences and settings")
async def get_user_preferences(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get user preferences"""
    try:
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


@router.put("/me/preferences", 
            response_model=ApiResponseDTO,
            summary="Update user preferences",
            description="Update user preferences and settings")
async def update_user_preferences(
    preferences: UserPreferences,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update user preferences"""
    try:
        user_repo = get_user_repo()
        
        # Update user preferences
        await user_repo.update(current_user['id'], {
            'preferences': preferences.dict()
        })
        
        logger.info(f"Preferences updated for user: {current_user['id']}")
        return ApiResponseDTO(
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


@router.get("/me/statistics", 
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
        user_repo = get_user_repo()
        
        # Build filters
        filters = []
        if workspace_id:
            filters.append(('workspace_id', '==', workspace_id))
        if venue_id:
            filters.append(('venue_id', '==', venue_id))
        
        # Get users
        users = await user_repo.query(filters) if filters else await user_repo.get_all()
        
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
                from datetime import timedelta
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


# =============================================================================
# SECURITY ENDPOINTS
# =============================================================================
# Note: Password change endpoint is in auth.py (/auth/change-password)