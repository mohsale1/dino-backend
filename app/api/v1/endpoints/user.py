"""
User Management API Endpoints
Comprehensive user management with authentication, profiles, and administration
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer

from app.models.schemas import User
from app.models.dto import (
    UserCreateDTO, AdminUserCreateDTO, UserUpdateDTO, UserLoginDTO, UserResponseDTO,
    AuthTokenDTO, ApiResponseDTO, SimpleApiResponseDTO,
    PaginatedResponseDTO
)
from app.core.base_endpoint import WorkspaceIsolatedEndpoint
from app.database.firestore import get_user_repo, UserRepository
from app.database.validated_repository import get_validated_user_repo, ValidatedUserRepository
from app.services.validation_service import get_validation_service
from app.core.dependency_injection import get_auth_service
from app.core.security import get_current_user, get_current_admin_user
from app.core.unified_password_security import password_handler
from app.core.logging_config import get_logger
from app.core.common_utils import validate_required_fields, raise_validation_error, remove_sensitive_fields, create_success_response

logger = get_logger(__name__)
router = APIRouter()
security = HTTPBearer()


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
# AUTHENTICATION ENDPOINTS
# =============================================================================

@router.post("/register", 
             response_model=AuthTokenDTO,
             status_code=status.HTTP_201_CREATED,
             summary="Register new user",
             description="Register a new user account. Public endpoint - no authentication required.")
async def register_user(user_data: UserCreateDTO):
    """Register a new user with comprehensive validation"""
    try:
        # Get validation service
        validation_service = get_validation_service()
        
        # Convert Pydantic model to dict for validation
        user_dict = user_data.model_dump()
        
        # Validate user data (this will check uniqueness, format, etc.)
        validation_errors = await validation_service.validate_user_data(user_dict, is_update=False)
        if validation_errors:
            validation_service.raise_validation_exception(validation_errors)
        
        # Register user (auth_service will handle password hashing)
        user = await get_auth_service().register_user(user_data)
        
        # Login user immediately after registration
        login_data = UserLoginDTO(email=user_data.email, password=user_data.password)
        token = await get_auth_service().login_user(login_data)
        
        logger.info(f"User registered successfully: {user_data.email}")
        return token
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", 
             response_model=AuthTokenDTO,
             summary="User login",
             description="Authenticate user and return JWT token")
async def login_user(login_data: UserLoginDTO):
    """Login user"""
    try:
        token = await get_auth_service().login_user(login_data)
        
        # Update last login
        user_repo = get_user_repo()
        await user_repo.update(token.user.id, {"last_login": token.user.created_at})
        
        logger.info(f"User logged in successfully: {login_data.email}")
        return token
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error logging in user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


# =============================================================================
# PROFILE MANAGEMENT ENDPOINTS
# =============================================================================

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
        from app.database.firestore import get_role_repo
        role_repo = get_role_repo()
        role = await role_repo.get_by_id(user_data['role_id'])
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role_id: Role does not exist"
            )
        
        # Handle password using unified password handler
        # This will detect if password is client-hashed and process accordingly
        server_hash, is_client_hashed = password_handler.handle_password_input(
            user_data['password'],
            require_client_hash=True  # Enforce client hashing for admin user creation
        )
        
        logger.info(f"Password processed - Client hashed: {is_client_hashed}")
        
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
# SECURITY ENDPOINTS
# =============================================================================

@router.post("/change-password", 
             response_model=ApiResponseDTO,
             summary="Change password",
             description="Change user password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Change user password"""
    try:
        success = await get_auth_service().change_password(
            current_user['id'], 
            current_password, 
            new_password
        )
        
        if success:
            logger.info(f"Password changed for user: {current_user['id']}")
            return ApiResponseDTO(
                success=True,
                message="Password changed successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to change password"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )


@router.post("/deactivate", 
             response_model=ApiResponseDTO,
             summary="Deactivate account",
             description="Deactivate current user account")
async def deactivate_account(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Deactivate user account"""
    try:
        success = await get_auth_service().deactivate_user(current_user['id'])
        
        if success:
            logger.info(f"Account deactivated for user: {current_user['id']}")
            return ApiResponseDTO(
                success=True,
                message="Account deactivated successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to deactivate account"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate account"
        )