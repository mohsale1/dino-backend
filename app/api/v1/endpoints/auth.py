"""
Authentication API Endpoints
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any
from datetime import datetime, timedelta

from app.models.requests import (
    UserLoginDTO, UserUpdateDTO, UserResponseDTO,
    AuthTokenDTO, ApiResponseDTO, WorkspaceRegistrationDTO,
    RefreshTokenRequest, ChangePasswordRequest
)
from app.core.dependencies import get_auth_service
from app.core.security import get_current_user, get_current_user_id
from app.core.config import settings
from app.core.logging import get_logger
from app.core.utils import convert_user_to_response_dto

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
        from app.database.repository_manager import get_workspace_repo, get_venue_repo, get_user_repo, get_role_repo
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
        
        # Hash password with BCrypt
        from app.core.security import get_password_hash
        
        # Debug: Log password length
        pwd_len = len(registration_data.owner_password)
        pwd_bytes_len = len(registration_data.owner_password.encode('utf-8'))
        logger.info(f"Registration password length: {pwd_len} chars, {pwd_bytes_len} bytes")
        
        try:
            server_hash = get_password_hash(registration_data.owner_password)
            logger.info(f"Registration password hashed for email: {registration_data.owner_email}")
        except ValueError as e:
            error_msg = str(e) if str(e) else "Password validation failed"
            logger.warning(f"Registration password validation error for email {registration_data.owner_email}: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        except Exception as e:
            error_msg = str(e) if str(e) else "Password hashing failed"
            logger.error(f"Registration password hashing error for email {registration_data.owner_email}: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
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
            "theme": "classic",
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
            "venue_ids": [venue_id]  # Use correct field name
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
    """Login user with plain text password"""
    try:
        from app.database.repository_manager import get_user_repo
        from app.core.security import create_access_token, verify_password, login_tracker
        
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
        
        # Verify password with BCrypt
        stored_hash = user.get("hashed_password", "")
        password_valid = verify_password(login_data.password, stored_hash)
        
        if not password_valid:
            logger.warning(f"Invalid password for user: {login_data.email}")
            login_tracker.record_failed_attempt(login_data.email)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        logger.info(f"Successful password verification for user: {login_data.email}")
        
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
    """Change user password"""
    try:
        from app.core.security import login_tracker, verify_password, get_password_hash
        from app.database.repository_manager import get_user_repo
        
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
        
        # Verify current password
        current_password_valid = verify_password(request_data.current_password, stored_hash)
        
        if not current_password_valid:
            login_tracker.record_failed_attempt(f"password_change_{user_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Check if new password is different from current
        if verify_password(request_data.new_password, stored_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from current password"
            )
        
        # Hash new password
        try:
            new_server_hash = get_password_hash(request_data.new_password)
            logger.info(f"Password change validation successful for user: {user_id}")
        except ValueError as e:
            logger.warning(f"Password validation error for user {user_id}: {e}")
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
        from app.database.repository_manager import get_user_repo
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
        from app.services.authorization import role_permission_service
        from app.database.repository_manager import get_role_repo, get_permission_repo
        
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