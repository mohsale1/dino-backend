"""

Authentication API Endpoints

"""

from fastapi import APIRouter, HTTPException, status, Depends, Query

from typing import Dict, Any

from datetime import datetime, timedelta



from  app.models.schemas import User

from app.models.dto import (

  UserCreateDTO, UserLoginDTO, UserUpdateDTO, UserResponseDTO,

  AuthTokenDTO, ApiResponseDTO, WorkspaceRegistrationDTO,

  RefreshTokenRequest, ChangePasswordRequest, GetSaltRequest, ClientHashedLoginRequest

)

from app.services.validation_service import get_validation_service

from app.core.dependency_injection import get_auth_service

from app.core.security import get_current_user, get_current_user_id

from app.core.common_utils import create_success_response

from app.core.config import settings

from app.core.logging_config import get_logger

from app.core.user_utils import convert_user_to_response_dto



logger = get_logger(__name__)

router = APIRouter()



@router.post("/register", response_model=ApiResponseDTO, status_code=status.HTTP_201_CREATED)

async def register_workspace(registration_data: WorkspaceRegistrationDTO):

  """

  Complete workspace registration with venue and owner user creation

   

  This endpoint creates:

  1. A new workspace with workspace details

  2. A new venue under the workspace with venue details 

  3. A new user (owner) with personal details and superadmin role

  4. Links all entities together properly

  """

  try:

    from app.database.firestore import get_workspace_repo, get_venue_repo, get_user_repo, get_role_repo

    from app.core.unified_password_security import password_handler

    import uuid

     

    logger.info(f"Starting workspace registration for email: {registration_data.owner_email}")

     

    # Get repositories

    workspace_repo = get_workspace_repo()

    venue_repo = get_venue_repo()

    user_repo = get_user_repo()

    role_repo = get_role_repo()

     

    # Check if email already exists

    existing_user = await user_repo.get_by_email(registration_data.owner_email)

    if existing_user:

      raise HTTPException(

        status_code=status.HTTP_400_BAD_REQUEST,

        detail="User with this email already exists"

      )

     

    # Generate unique IDs

    workspace_id = str(uuid.uuid4())

    venue_id = str(uuid.uuid4())

    user_id = str(uuid.uuid4())

     

    # Generate unique workspace name from display name

    workspace_name = registration_data.workspace_name.lower().replace(" ", "_").replace("-", "_")

    workspace_name = f"{workspace_name}_{workspace_id[:8]}"

     

    current_time = datetime.utcnow()

     

    # Get superadmin role_id

    superadmin_role = await role_repo.get_by_name("superadmin")

    if not superadmin_role:

      raise HTTPException(

        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

        detail="Superadmin role not found in system"

      )

     

    # Handle password using unified handler

    try:

      server_hash, is_client_hashed = password_handler.handle_password_input(

        registration_data.owner_password,

        require_client_hash=True # Enforce client hashing for registration

      )

      logger.info(f"Registration with {'client-hashed' if is_client_hashed else 'processed'} password for email: {registration_data.owner_email}")

    except ValueError as e:

      logger.warning(f"Registration password error for email {registration_data.owner_email}: {e}")

      raise HTTPException(

        status_code=status.HTTP_400_BAD_REQUEST,

        detail=str(e)

      )

     

    # Validate phone numbers

    venue_phone = registration_data.get_venue_phone_number()

    if not venue_phone:

      raise HTTPException(

        status_code=status.HTTP_400_BAD_REQUEST,

        detail="Venue phone number is required. Please provide venuePhone or ownerPhone."

      )

     

    owner_phone = registration_data.get_owner_phone_number()

    if not owner_phone:

      raise HTTPException(

        status_code=status.HTTP_400_BAD_REQUEST,

        detail="Owner phone number is required. Please provide ownerPhone."

      )

     

    # 1. Create Workspace

    workspace_data = {

      "id": workspace_id,

      "name": workspace_name,

      "description": registration_data.workspace_description,

      "is_active": True,

      "created_at": current_time,

      "updated_at": current_time

    }

     

    # 2. Create Venue

    venue_data = {

      "id": venue_id,

      "name": registration_data.venue_name,

      "description": registration_data.venue_description,

      "location": registration_data.venue_location.model_dump(),

      "phone": venue_phone,

      "email": registration_data.venue_email or registration_data.owner_email,

      "price_range": registration_data.price_range.value,

      "subscription_plan": "basic",

      "subscription_status": "active",

      "admin_id": user_id,

      "is_active": True,

      "rating_total": 0.0,

      "rating_count": 0,

      "created_at": current_time,

      "updated_at": current_time,

      "workspace_id": workspace_id

    }

     

    # 3. Create User (Owner with superadmin role)

    user_data = {

      "id": user_id,

      "email": registration_data.owner_email,

      "phone": owner_phone,

      "first_name": registration_data.owner_first_name,

      "last_name": registration_data.owner_last_name,

      "hashed_password": server_hash,

      "role_id": superadmin_role["id"],

      "is_active": True,

      "email_verified": False,

      "phone_verified": False,

      "created_at": current_time,

      "updated_at": current_time,

      "last_login": None,

      "venue_ids": [venue_id] # Use correct field name

    }

     

    # Create all records in sequence with rollback on failure

    try:

      # Create workspace first with specific document ID

      created_workspace = await workspace_repo.create(workspace_data, doc_id=workspace_id)

      actual_workspace_id = created_workspace.get("id", workspace_id)

      logger.info(f"Workspace created with ID: {actual_workspace_id}")

       

      # Update venue data with actual workspace ID (should be the same as workspace_id)

      venue_data["workspace_id"] = actual_workspace_id

       

      # Create venue with specific document ID

      created_venue = await venue_repo.create(venue_data, doc_id=venue_id)

      actual_venue_id = created_venue.get("id", venue_id)

      logger.info(f"Venue created with ID: {actual_venue_id}")

       

      # Update user data with actual venue ID (should be the same as venue_id)

      user_data["venue_ids"] = [actual_venue_id]

       

      # Create user with specific document ID

      created_user = await user_repo.create(user_data, doc_id=user_id)

      actual_user_id = created_user.get("id", user_id)

      logger.info(f"User created with ID: {actual_user_id}")

       

      logger.info("Entity creation completed successfully")

       

      # Log successful registration

      logger.info(f"Complete workspace registration successful", extra={

        "workspace_id": actual_workspace_id,

        "venue_id": actual_venue_id,

        "user_id": actual_user_id,

        "owner_email": registration_data.owner_email

      })

       

      return ApiResponseDTO(

        success=True,

        message="Workspace, venue, and owner account created successfully. You can now login with your credentials.",

        data={

          "workspace": {

            "id": actual_workspace_id,

            "name": workspace_name

          },

          "venue": {

            "id": actual_venue_id,

            "name": registration_data.venue_name

          },

          "owner": {

            "id": actual_user_id,

            "first_name": registration_data.owner_first_name,

            "last_name": registration_data.owner_last_name,

            "role_id": superadmin_role["id"],

            "role_name": "superadmin"

          }

        }

      )

       

    except Exception as creation_error:

      # Rollback on failure

      logger.error(f"Registration failed during creation: {creation_error}")

       

      # Attempt cleanup (best effort)

      try:

        # Use actual IDs if they were created, otherwise use generated IDs

        cleanup_workspace_id = locals().get('actual_workspace_id', workspace_id)

        cleanup_venue_id = locals().get('actual_venue_id', venue_id)

        cleanup_user_id = locals().get('actual_user_id', user_id)

         

        await workspace_repo.delete(cleanup_workspace_id)

        await venue_repo.delete(cleanup_venue_id) 

        await user_repo.delete(cleanup_user_id)

        logger.info("Cleanup completed after registration failure")

      except Exception as cleanup_error:

        logger.error(f"Cleanup failed: {cleanup_error}")

         

      raise HTTPException(

        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

        detail="Registration failed during record creation. Please try again."

      )

       

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"Workspace registration failed: {e}", exc_info=True)

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail="Workspace registration failed. Please try again."

    )



@router.post("/login", response_model=AuthTokenDTO)

async def login_user(login_data: UserLoginDTO):

  """Login user with support for both plain text and hashed passwords"""

  try:

    from  app.database.firestore import get_user_repo

    from app.core.security import create_access_token

    from app.core.unified_password_security import login_tracker

    from app.core.unified_password_security import password_handler

     

    logger.info(f"Login attempt for email: {login_data.email}")

     

    user_repo = get_user_repo()

     

    # Check if account is locked

    if login_tracker.is_locked(login_data.email):

      remaining_time = login_tracker.get_remaining_lockout_time(login_data.email)

      raise HTTPException(

        status_code=status.HTTP_423_LOCKED,

        detail=f"Account locked. Try again in {remaining_time} seconds."

      )

     

    # Get user by email

    user = await user_repo.get_by_email(login_data.email)

     

    if not user:

      login_tracker.record_failed_attempt(login_data.email)

      raise HTTPException(

        status_code=status.HTTP_401_UNAUTHORIZED,

        detail="Invalid credentials"

      )

     

    # Check if user is active

    if not user.get('is_active', True):

      raise HTTPException(

        status_code=status.HTTP_401_UNAUTHORIZED,

        detail="Account is deactivated"

      )

     

    # Verify password using unified handler

    stored_hash = user.get("hashed_password", "")

     

    try:

      password_valid = password_handler.verify_password_input(

        login_data.password, 

        stored_hash, 

        require_client_hash=True # Enforce client hashing

      )

       

      if password_valid:

        logger.info(f"Successful password verification for user: {login_data.email}")

      else:

        logger.warning(f"Invalid password for user: {login_data.email}")

         

    except ValueError as e:

      # Handle client hashing requirement errors

      logger.warning(f"Password format error for user {login_data.email}: {e}")

      login_tracker.record_failed_attempt(login_data.email)

      raise HTTPException(

        status_code=status.HTTP_400_BAD_REQUEST,

        detail=str(e)

      )

     

    if not password_valid:

      login_tracker.record_failed_attempt(login_data.email)

      raise HTTPException(

        status_code=status.HTTP_401_UNAUTHORIZED,

        detail="Invalid credentials"

      )

     

    # Successful login

    login_tracker.record_successful_attempt(login_data.email)

     

    # Update last login

    await user_repo.update(user["id"], {

      "last_login": datetime.utcnow(),

      "updated_at": datetime.utcnow()

    })

     

    # Create JWT tokens (both access and refresh)

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    access_token = create_access_token(

      data={"sub": user["id"]},

      expires_delta=access_token_expires

    )

     

    # Create refresh token

    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    refresh_token = create_access_token(

      data={"sub": user["id"], "type": "refresh"},

      expires_delta=refresh_token_expires

    )

     

    # Convert user data to UserResponseDTO

    user_response_dto = convert_user_to_response_dto(user)

     

    logger.info(f"Successful login for user: {user['id']}")

     

    return AuthTokenDTO(

      access_token=access_token,

      refresh_token=refresh_token,

      token_type="bearer",

      expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,

      user=user_response_dto

    )

     

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"Login failed with unexpected error: {e}", exc_info=True)

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail="Login failed"

    )



@router.get("/me", response_model=UserResponseDTO)

async def get_current_user_info(current_user: Dict[str, Any] = Depends(get_current_user)):

  """Get current user information"""

  try:

    return convert_user_to_response_dto(current_user)

  except Exception as e:

    logger.error(f"Failed to get current user info: {e}", exc_info=True)

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail="Failed to retrieve user information"

    )



@router.put("/me", response_model=ApiResponseDTO)

async def update_current_user(

  user_update: UserUpdateDTO,

  current_user_id: str = Depends(get_current_user_id)

):

  """Update current user information"""

  try:

    # Convert to dict and remove None values

    update_data = user_update.model_dump(exclude_unset=True)

     

    if not update_data:

      raise HTTPException(

        status_code=status.HTTP_400_BAD_REQUEST,

        detail="No data provided for update"

      )

     

    user = await get_auth_service().update_user(current_user_id, update_data)

    return ApiResponseDTO(

      success=True,

      message="User updated successfully",

      data=user

    )

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"User update failed: {e}", exc_info=True)

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail=f"Update failed: {str(e)}"

    )



@router.post("/change-password", response_model=ApiResponseDTO)

async def change_password(

  request_data: ChangePasswordRequest,

  current_user: Dict[str, Any] = Depends(get_current_user)

):

  """Change user password with enhanced security"""

  try:

    from app.core.unified_password_security import login_tracker

    from app.database.firestore import get_user_repo

    from app.core.unified_password_security import password_handler

     

    user_repo = get_user_repo()

    user_id = current_user["id"]

     

    logger.info(f"Password change request for user: {user_id}")

     

    # Get current user data

    user_data = await user_repo.get_by_id(user_id)

    if not user_data:

      raise HTTPException(

        status_code=status.HTTP_404_NOT_FOUND,

        detail="User not found"

      )

     

    stored_hash = user_data.get("hashed_password", "")

     

    try:

      # Verify current password

      current_password_valid = password_handler.verify_password_input(

        request_data.current_password, 

        stored_hash, 

        require_client_hash=True

      )

       

      if not current_password_valid:

        login_tracker.record_failed_attempt(f"password_change_{user_id}")

        raise HTTPException(

          status_code=status.HTTP_400_BAD_REQUEST,

          detail="Current password is incorrect"

        )

       

      # Handle new password

      new_server_hash, is_client_hashed = password_handler.handle_password_input(

        request_data.new_password,

        require_client_hash=True

      )

       

      # Check if new password is different from current

      if password_handler.verify_password_input(request_data.new_password, stored_hash, require_client_hash=True):

        raise HTTPException(

          status_code=status.HTTP_400_BAD_REQUEST,

          detail="New password must be different from current password"

        )

       

      logger.info(f"Password change validation successful for user: {user_id}")

       

    except ValueError as e:

      logger.warning(f"Password change format error for user {user_id}: {e}")

      login_tracker.record_failed_attempt(f"password_change_{user_id}")

      raise HTTPException(

        status_code=status.HTTP_400_BAD_REQUEST,

        detail=str(e)

      )

     

    # Update password

    await user_repo.update(user_id, {

      "hashed_password": new_server_hash,

      "updated_at": datetime.utcnow()

    })

     

    # Record successful password change

    login_tracker.record_successful_attempt(f"password_change_{user_id}")

     

    logger.info(f"Password changed successfully for user: {user_id}")

     

    return ApiResponseDTO(

      success=True,

      message="Password changed successfully",

      data={

        "changed_at": datetime.utcnow().isoformat()

      }

    )

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"Password change failed for user {current_user.get('id')}: {e}", exc_info=True)

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail="Password change failed"

    )



@router.post("/refresh", response_model=AuthTokenDTO)

async def refresh_token(request_data: RefreshTokenRequest):

  """Refresh JWT token"""

  try:

    from app.database.firestore import get_user_repo

    from app.core.security import verify_token, create_access_token

     

    logger.info("Token refresh attempt")

     

    # Verify the refresh token

    try:

      payload = verify_token(request_data.refresh_token)

    except HTTPException as e:

      logger.warning(f"Refresh token verification failed: {e.detail}")

      raise HTTPException(

        status_code=status.HTTP_401_UNAUTHORIZED,

        detail="Invalid or expired refresh token"

      )

     

    user_id = payload.get("sub")

    token_type = payload.get("type")

     

    if not user_id:

      raise HTTPException(

        status_code=status.HTTP_401_UNAUTHORIZED,

        detail="Invalid refresh token - missing user ID"

      )

     

    # Allow refresh tokens without explicit type for backward compatibility

    if token_type and token_type != "refresh":

      raise HTTPException(

        status_code=status.HTTP_401_UNAUTHORIZED,

        detail="Invalid token type"

      )

     

    # Get user from database

    user_repo = get_user_repo()

    user = await user_repo.get_by_id(user_id)

     

    if not user:

      raise HTTPException(

        status_code=status.HTTP_401_UNAUTHORIZED,

        detail="User not found"

      )

     

    # Check if user is active

    if not user.get('is_active', True):

      raise HTTPException(

        status_code=status.HTTP_401_UNAUTHORIZED,

        detail="User account is deactivated"

      )

     

    # Create new tokens

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    access_token = create_access_token(

      data={"sub": user["id"]},

      expires_delta=access_token_expires

    )

     

    # Create new refresh token

    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    new_refresh_token = create_access_token(

      data={"sub": user["id"], "type": "refresh"},

      expires_delta=refresh_token_expires

    )

     

    # Convert user data to UserResponseDTO

    user_response_dto = convert_user_to_response_dto(user)

     

    logger.info(f"Token refresh successful for user: {user['id']}")

     

    return AuthTokenDTO(

      access_token=access_token,

      refresh_token=new_refresh_token,

      token_type="bearer",

      expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,

      user=user_response_dto

    )

     

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"Token refresh failed: {e}", exc_info=True)

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail=f"Token refresh failed: {str(e)}"

    )



@router.get("/permissions", response_model=ApiResponseDTO)

async def get_user_permissions(current_user: Dict[str, Any] = Depends(get_current_user)):

  """Get current user's permissions"""

  try:

    from  app.services.role_permission_service import role_permission_service

    from app.database.firestore import get_role_repo, get_permission_repo

     

    # Get user's role and permissions

    role_repo = get_role_repo()

    user_role_id = current_user.get('role_id')

     

    if not user_role_id:

      raise HTTPException(

        status_code=status.HTTP_400_BAD_REQUEST,

        detail="User has no role assigned"

      )

     

    # Get role with permissions

    role = await role_repo.get_by_id(user_role_id)

    if not role:

      raise HTTPException(

        status_code=status.HTTP_404_NOT_FOUND,

        detail="User role not found"

      )

     

    # Get permissions from role

    permissions = role.get('permission_ids', [])

     

    # Get detailed permission information

    perm_repo = get_permission_repo()

    detailed_permissions = []

     

    for perm_id in permissions:

      perm = await perm_repo.get_by_id(perm_id)

      if perm:

        detailed_permissions.append({

          'id': perm['id'],

          'name': perm['name'],

          'resource': perm['resource'],

          'action': perm['action'],

          'scope': perm['scope'],

          'description': perm['description']

        })

     

    # Get dashboard permissions using the role we already have

    dashboard_permissions = await role_permission_service.get_role_dashboard_permissions_with_role(role['name'])

     

    return ApiResponseDTO(

      success=True,

      message="User permissions retrieved successfully",

      data={

        'user_id': current_user['id'],

        'role': {

          'id': role['id'],

          'name': role['name'],

          'display_name': role.get('display_name', role['name']),

          'description': role.get('description', '')

        },

        'permissions': detailed_permissions,

        'dashboard_permissions': dashboard_permissions,

        'permission_count': len(detailed_permissions)

      }

    )

     

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"Error getting user permissions: {e}", exc_info=True)

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail="Failed to get user permissions"

    )



@router.post("/refresh-permissions", response_model=ApiResponseDTO)

async def refresh_user_permissions(current_user: Dict[str, Any] = Depends(get_current_user)):

  """Refresh current user's permissions (for real-time updates)"""

  try:

    from app.services.role_permission_service import role_permission_service

    from app.database.firestore import get_role_repo, get_permission_repo

     

    # Get user's role and permissions

    role_repo = get_role_repo()

    user_role_id = current_user.get('role_id')

     

    if not user_role_id:

      raise HTTPException(

        status_code=status.HTTP_400_BAD_REQUEST,

        detail="User has no role assigned"

      )

     

    # Get role with permissions

    role = await role_repo.get_by_id(user_role_id)

    if not role:

      raise HTTPException(

        status_code=status.HTTP_404_NOT_FOUND,

        detail="User role not found"

      )

     

    # Get permissions from role

    permissions = role.get('permission_ids', [])

     

    # Get detailed permission information

    perm_repo = get_permission_repo()

    detailed_permissions = []

     

    for perm_id in permissions:

      perm = await perm_repo.get_by_id(perm_id)

      if perm:

        detailed_permissions.append({

          'id': perm['id'],

          'name': perm['name'],

          'resource': perm['resource'],

          'action': perm['action'],

          'scope': perm['scope'],

          'description': perm['description']

        })

     

    # Get dashboard permissions using the role we already have

    dashboard_permissions = await role_permission_service.get_role_dashboard_permissions_with_role(role['name'])

     

    return ApiResponseDTO(

      success=True,

      message="User permissions refreshed successfully",

      data={

        'user_id': current_user['id'],

        'role': {

          'id': role['id'],

          'name': role['name'],

          'display_name': role.get('display_name', role['name']),

          'description': role.get('description', '')

        },

        'permissions': detailed_permissions,

        'dashboard_permissions': dashboard_permissions,

        'permission_count': len(detailed_permissions),

        'refreshed_at': datetime.utcnow().isoformat()

      }

    )

     

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"Error refreshing user permissions: {e}", exc_info=True)

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail="Failed to refresh user permissions"

    )



@router.post("/logout", response_model=ApiResponseDTO)

async def logout_user():

  """Logout user (client-side token removal)"""

  return ApiResponseDTO(

    success=True,

    message="Logged out successfully. Please remove the token from client storage.",

    data={

      "logged_out_at": datetime.utcnow().isoformat(),

      "action": "logout_completed"

    }

  )



@router.post("/debug-token", response_model=ApiResponseDTO)

async def debug_token(request_data: RefreshTokenRequest):

  """Debug JWT token (development only)"""

  try:

    from jose import jwt

    from app.core.config import settings

     

    if settings.is_production:

      raise HTTPException(

        status_code=status.HTTP_404_NOT_FOUND,

        detail="Endpoint not available in production"

      )

     

    token = request_data.refresh_token

     

    # Try to decode without verification first

    try:

      unverified_payload = jwt.get_unverified_claims(token)

      logger.info(f"Unverified token payload: {unverified_payload}")

    except Exception as e:

      logger.error(f"Failed to get unverified claims: {e}")

      unverified_payload = None

     

    # Try to decode with verification

    try:

      verified_payload = jwt.decode(

        token, 

        settings.SECRET_KEY, 

        algorithms=[settings.ALGORITHM]

      )

      verification_status = "success"

      verification_error = None

    except Exception as e:

      verified_payload = None

      verification_status = "failed"

      verification_error = str(e)

     

    return ApiResponseDTO(

      success=True,

      message="Token debug information",

      data={

        "unverified_payload": unverified_payload,

        "verified_payload": verified_payload,

        "verification_status": verification_status,

        "verification_error": verification_error,

        "secret_key_length": len(settings.SECRET_KEY),

        "algorithm": settings.ALGORITHM

      }

    )

     

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"Token debug failed: {e}", exc_info=True)

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail=f"Debug failed: {str(e)}"

    )



@router.put("/deactivate/{venue_id}", response_model=ApiResponseDTO)

async def deactivate_venue(

  venue_id: str,

  current_user: Dict[str, Any] = Depends(get_current_user)

):

  """Deactivate venue by venue ID (updates is_active field to False)"""

  try:

    from app.database.firestore import get_venue_repo

    from app.core.security import _get_user_role

     

    venue_repo = get_venue_repo()

     

    # Check if venue exists

    venue = await venue_repo.get_by_id(venue_id)

    if not venue:

      raise HTTPException(

        status_code=status.HTTP_404_NOT_FOUND,

        detail="Venue not found"

      )

     

    # Check permissions - get user role from role_id

    user_role = await _get_user_role(current_user)

    venue_admin_id = venue.get('admin_id')

     

    # Only superadmin or venue owner can deactivate venues

    if not (user_role == 'superadmin' or current_user['id'] == venue_admin_id):

      raise HTTPException(

        status_code=status.HTTP_403_FORBIDDEN,

        detail="Insufficient permissions to deactivate this venue"

      )

     

    # Update venue deactivation status

    await venue_repo.update(venue_id, {"is_active": False})

     

    logger.info(f"Venue deactivated: {venue_id} by user: {current_user['id']}")

     

    return ApiResponseDTO(

      success=True,

      message="Venue deactivated successfully. Record preserved with is_active set to False.",

      data={

        "venue_id": venue_id, 

        "venue_name": venue.get('name'),

        "is_active": False,

        "action": "deactivated"

      }

    )

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"Venue deactivation failed: {e}", exc_info=True)

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail=f"Venue deactivation failed: {str(e)}"

    )



@router.put("/activate/{venue_id}", response_model=ApiResponseDTO)

async def activate_venue(

  venue_id: str,

  current_user: Dict[str, Any] = Depends(get_current_user)

):

  """Activate venue by venue ID (updates is_active field to True)"""

  try:

    from  app.database.firestore import get_venue_repo

    from app.core.security import _get_user_role

     

    venue_repo = get_venue_repo()

     

    # Check if venue exists

    venue = await venue_repo.get_by_id(venue_id)

    if not venue:

      raise HTTPException(

        status_code=status.HTTP_404_NOT_FOUND,

        detail="Venue not found"

      )

     

    # Check permissions - get user role from role_id

    user_role = await _get_user_role(current_user)

    venue_admin_id = venue.get('admin_id')

     

    # Only superadmin or venue owner can activate venues

    if not (user_role == 'superadmin' or current_user['id'] == venue_admin_id):

      raise HTTPException(

        status_code=status.HTTP_403_FORBIDDEN,

        detail="Insufficient permissions to activate this venue"

      )

     

    # Update venue activation status

    await venue_repo.update(venue_id, {"is_active": True})

     

    logger.info(f"Venue activated: {venue_id} by user: {current_user['id']}")

     

    return ApiResponseDTO(

      success=True,

      message="Venue activated successfully. Record updated with is_active set to True.",

      data={

        "venue_id": venue_id, 

        "venue_name": venue.get('name'),

        "is_active": True,

        "action": "activated"

      }

    )

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"Venue activation failed: {e}", exc_info=True)

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail=f"Venue activation failed: {str(e)}"

    )



@router.post("/get-salt", response_model=ApiResponseDTO)

async def get_user_salt(request_data: GetSaltRequest):

  """Get user salt for client-side password hashing"""

  try:

    from app.database.firestore import get_user_repo

    from app.core.unified_password_security import FIXED_CLIENT_SALT

    import hashlib

     

    user_repo = get_user_repo()

     

    # Get user by email

    user = await user_repo.get_by_email(request_data.email)

     

    if not user:

      # For security, don't reveal if user exists or not

      # Return a deterministic salt based on email for non-existent users

      fake_salt = hashlib.sha256(f"fake_salt_{request_data.email}".encode()).hexdigest()[:64]

      return ApiResponseDTO(

        success=True,

        message="Salt retrieved",

        data={"salt": fake_salt}

      )

     

    # Get or generate user salt

    user_salt = user.get("password_salt")

    if not user_salt:

      # For the unified system, we use a fixed salt approach

      # Return the fixed salt used by the system

      from app.core.unified_password_security import FIXED_CLIENT_SALT

      user_salt = FIXED_CLIENT_SALT

     

    return ApiResponseDTO(

      success=True,

      message="Salt retrieved",

      data={"salt": user_salt}

    )

     

  except Exception as e:

    logger.error(f"Error getting user salt: {e}", exc_info=True)

    # Return fake salt to prevent timing attacks

    import hashlib

    fake_salt = hashlib.sha256(f"error_salt_{request_data.email}".encode()).hexdigest()[:64]

    return ApiResponseDTO(

      success=True,

      message="Salt retrieved",

      data={"salt": fake_salt}

    )



@router.post("/login-hashed", response_model=AuthTokenDTO)

async def login_with_hashed_password(login_data: ClientHashedLoginRequest):

  """Login with client-side hashed password"""

  try:

    from app.database.firestore import get_user_repo

    from app.core.unified_password_security import FIXED_CLIENT_SALT

    from app.core.security import create_access_token

    from app.core.unified_password_security import login_tracker

     

    logger.info(f"Hashed login attempt for email: {login_data.email}")

     

    user_repo = get_user_repo()

     

    # Check if account is locked

    if login_tracker.is_locked(login_data.email):

      remaining_time = login_tracker.get_remaining_lockout_time(login_data.email)

      raise HTTPException(

        status_code=status.HTTP_423_LOCKED,

        detail=f"Account locked. Try again in {remaining_time} seconds."

      )

     

    # Get user by email

    user = await user_repo.get_by_email(login_data.email)

     

    if not user:

      login_tracker.record_failed_attempt(login_data.email)

      raise HTTPException(

        status_code=status.HTTP_401_UNAUTHORIZED,

        detail="Invalid credentials"

      )

     

    # Check if user is active

    if not user.get('is_active', True):

      raise HTTPException(

        status_code=status.HTTP_401_UNAUTHORIZED,

        detail="Account is deactivated"

      )

     

    # Get user salt

    user_salt = user.get("password_salt")

    if not user_salt:

      # User doesn't have salt - might be legacy user

      logger.info(f"Migrating legacy user to client-hashed password: {user['id']}")

       

      # Use fixed salt from unified system

      from app.core.unified_password_security import FIXED_CLIENT_SALT

      user_salt = FIXED_CLIENT_SALT

       

      # For now, reject client hash login for legacy users

      # They need to use regular login first to migrate

      raise HTTPException(

        status_code=status.HTTP_400_BAD_REQUEST,

        detail="Account needs migration. Please use regular login first."

      )

     

    # Verify client-hashed password using unified handler

    stored_hash = user.get("hashed_password", "")

    from app.core.unified_password_security import password_handler

    if not password_handler.verify_password(login_data.password_hash, stored_hash):

      login_tracker.record_failed_attempt(login_data.email)

      raise HTTPException(

        status_code=status.HTTP_401_UNAUTHORIZED,

        detail="Invalid credentials"

      )

     

    # Successful login

    login_tracker.record_successful_attempt(login_data.email)

     

    # Update last login

    await user_repo.update(user["id"], {

      "last_login": datetime.utcnow(),

      "updated_at": datetime.utcnow()

    })

     

    # Create JWT tokens (both access and refresh)

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    access_token = create_access_token(

      data={"sub": user["id"]},

      expires_delta=access_token_expires

    )

     

    # Create refresh token

    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    refresh_token = create_access_token(

      data={"sub": user["id"], "type": "refresh"},

      expires_delta=refresh_token_expires

    )

     

    # Convert user data to UserResponseDTO

    user_response_dto = convert_user_to_response_dto(user)

     

    logger.info(f"Successful hashed login for user: {user['id']}")

     

    return AuthTokenDTO(

      access_token=access_token,

      refresh_token=refresh_token,

      token_type="bearer",

      expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,

      user=user_response_dto

    )

     

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"Hashed login failed: {e}", exc_info=True)

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail="Login failed"

    )



@router.get("/client-hash-info", response_model=ApiResponseDTO)

async def get_client_hash_info():

  """Get information for implementing client-side password hashing"""

  try:

    from app.core.unified_password_security import get_client_hashing_info

     

    hash_info = get_client_hashing_info()

     

    return ApiResponseDTO(

      success=True,

      message="Client hashing information retrieved",

      data=hash_info

    )

     

  except Exception as e:

    logger.error(f"Failed to get client hash info: {e}", exc_info=True)

    return ApiResponseDTO(

      success=False,

      message=f"Failed to get client hash info: {str(e)}",

      data={"error": str(e)}

    )



@router.get("/config-check", response_model=ApiResponseDTO)

async def check_auth_config():

  """Check authentication configuration (development only)"""

  try:

    from  app.core.config import settings

     

    if settings.is_production:

      raise HTTPException(

        status_code=status.HTTP_404_NOT_FOUND,

        detail="Endpoint not available in production"

      )

     

    return ApiResponseDTO(

      success=True,

      message="Authentication configuration",

      data={

        "jwt_auth_enabled": settings.is_jwt_auth_enabled,

        "secret_key_configured": bool(settings.SECRET_KEY and settings.SECRET_KEY != "your-super-secret-jwt-key-change-this-in-production-at-least-32-characters-long"),

        "secret_key_length": len(settings.SECRET_KEY) if settings.SECRET_KEY else 0,

        "algorithm": settings.ALGORITHM,

        "access_token_expire_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES,

        "refresh_token_expire_days": settings.REFRESH_TOKEN_EXPIRE_DAYS,

        "environment": settings.ENVIRONMENT,

        "is_production": settings.is_production,

        "is_development": settings.is_development

      }

    )

     

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"Config check failed: {e}", exc_info=True)

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail=f"Config check failed: {str(e)}"

    )



@router.get("/user-role-debug", response_model=ApiResponseDTO)

async def debug_user_role(current_user: Dict[str, Any] = Depends(get_current_user)):

  """Debug user role information (development only)"""

  try:

    from app.core.config import settings

    from app.core.security import _get_user_role

     

    if settings.is_production:

      raise HTTPException(

        status_code=status.HTTP_404_NOT_FOUND,

        detail="Endpoint not available in production"

      )

     

    # Get the resolved role

    resolved_role = await _get_user_role(current_user)

     

    return ApiResponseDTO(

      success=True,

      message="User role debug information",

      data={

        "user_id": current_user.get("id"),

        "email": current_user.get("email"),

        "role_id": current_user.get("role_id"),

        "direct_role_field": current_user.get("role"),

        "resolved_role": resolved_role,

        "venue_ids": current_user.get("venue_ids", []),

        "workspace_id": current_user.get("workspace_id"),

        "is_active": current_user.get("is_active"),

        "has_admin_privileges": resolved_role in ['admin', 'superadmin'],

        "has_superadmin_privileges": resolved_role == 'superadmin'

      }

    )

     

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"User role debug failed: {e}", exc_info=True)

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail=f"User role debug failed: {str(e)}"

    )



@router.get("/workspace-debug", response_model=ApiResponseDTO)

async def debug_workspace_access(

  venue_id: str = Query(..., description="Venue ID to check access for"),

  current_user: Dict[str, Any] = Depends(get_current_user)

):

  """Debug workspace access for venue (development only)"""

  try:

    from app.core.config import settings

    from app.core.security import _get_user_role

    from app.database.firestore import get_venue_repo

     

    if settings.is_production:

      raise HTTPException(

        status_code=status.HTTP_404_NOT_FOUND,

        detail="Endpoint not available in production"

      )

     

    # Get user role

    resolved_role = await _get_user_role(current_user)

     

    # Get venue information

    venue_repo = get_venue_repo()

    venue = await venue_repo.get_by_id(venue_id)

     

    return ApiResponseDTO(

      success=True,

      message="Workspace access debug information",

      data={

        "user": {

          "id": current_user.get("id"),

          "email": current_user.get("email"),

          "role": resolved_role,

          "workspace_id": current_user.get("workspace_id"),

          "venue_ids": current_user.get("venue_ids", [])

        },

        "venue": {

          "id": venue_id,

          "exists": venue is not None,

          "name": venue.get("name") if venue else None,

          "workspace_id": venue.get("workspace_id") if venue else None,

          "admin_id": venue.get("admin_id") if venue else None

        },

        "access_check": {

          "is_superadmin": resolved_role == 'superadmin',

          "is_admin": resolved_role in ['admin', 'superadmin'],

          "workspace_match": current_user.get("workspace_id") == venue.get("workspace_id") if venue else False,

          "should_have_access": resolved_role in ['admin', 'superadmin'] or (current_user.get("workspace_id") == venue.get("workspace_id") if venue else False)

        }

      }

    )

     

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"Workspace debug failed: {e}", exc_info=True)

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail=f"Workspace debug failed: {str(e)}"

    )