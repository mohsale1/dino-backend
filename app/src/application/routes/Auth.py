from fastapi import APIRouter, HTTPException, status, Depends, Query
from src.schemas.Auth import LoginRequest, LoginResponse, RefreshTokenRequest, RefreshTokenResponse, SignupRequest, SignupResponse, ChangePasswordRequest
from src.application.services.Auth import ApplicationAuthService
from src.base.BaseSchema import BaseResponse
from src.core.Security import decode_token, verify_token_type, verify_password, get_password_hash
from src.core.Dependencies import get_current_application_user
from src.repositories.UserRepository import UserRepository
from typing import Dict, Any

router = APIRouter(prefix="/auth", tags=["Application Auth"])

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Application user login"""
    auth_service = ApplicationAuthService()
    
    result = auth_service.login(request.email, request.password)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    return result

@router.get("/validate-referral", response_model=BaseResponse)
async def validate_referral_code(code: str = Query(..., min_length=4, max_length=4, description="4-digit referral code")):
    """
    Validate referral code (4-digit system user ID)
    Returns user details if valid
    """
    from src.repositories.UserRepository import UserRepository
    
    try:
        # Check if code is exactly 4 digits
        if not code.isdigit() or len(code) != 4:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Referral code must be a 4-digit number"
            )
        
        # Check if system user exists with this ID
        system_user_repo = UserRepository("system_users")
        user = system_user_repo.get_by_id(code)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid referral code. User not found."
            )
        
        if not user.get('is_active', False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Referral code is inactive. Please contact support."
            )
        
        # Return user details (without sensitive info)
        return {
            "success": True,
            "message": "Referral code is valid",
            "data": {
                "user_id": user.get('id'),
                "email": user.get('email'),
                "first_name": user.get('first_name'),
                "last_name": user.get('last_name'),
                "role": user.get('role', {}).get('name', 'Unknown')
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error validating referral code: {str(e)}"
        )

@router.post("/signup", response_model=SignupResponse)
async def signup(request: SignupRequest):
    """
    Complete signup process for new workspace
    Creates workspace, organization, and admin user
    Validates referral code and tracks who onboarded the workspace
    """
    auth_service = ApplicationAuthService()
    
    try:
        # Prepare workspace data
        workspace_data = {
            "name": request.workspace_name,
            "description": request.workspace_description,
        }
        
        organization_data = request.organization.model_dump()
        admin_data = request.admin_user.model_dump()
        
        # Prepare billing data
        billing_data = {
            "billing_name": request.billing_name,
            "billing_email": request.billing_email,
            "billing_phone": request.billing_phone,
            "billing_address": request.billing_address,
            "billing_city": request.billing_city,
            "billing_state": request.billing_state,
            "billing_postal_code": request.billing_postal_code,
            "billing_country": request.billing_country,
        }
        
        # Execute signup with referral code validation
        result = auth_service.signup(request.referral_code, workspace_data, organization_data, admin_data, billing_data)
        
        return SignupResponse(
            workspace=result['workspace'],
            organization=result['organization'],
            admin_user=result['admin_user'],
            message="Signup successful. You can now login with your credentials."
        )
        
    except Exception as e:
        error_message = str(e)
        
        # Handle specific error cases
        if "already exists" in error_message:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_message
            )
        elif "not found" in error_message:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"System configuration error: {error_message}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """Refresh access token"""
    if not verify_token_type(request.refresh_token, "refresh"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    payload = decode_token(request.refresh_token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    auth_service = ApplicationAuthService()
    
    token_data = {
        "sub": payload.get("sub"),
        "email": payload.get("email"),
        "user_type": "application"
    }
    
    access_token = auth_service.create_access_token(token_data)
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.get("/me", response_model=BaseResponse)
async def get_current_user(current_user: Dict[str, Any] = Depends(get_current_application_user)):
    """Get current application user with full details"""
    from src.repositories.UserRepository import UserRepository
    from src.repositories.WorkspaceRepository import WorkspaceRepository
    from src.repositories.OrganizationRepository import OrganizationRepository
    
    user_repo = UserRepository("application_users")
    workspace_repo = WorkspaceRepository()
    org_repo = OrganizationRepository()
    
    # Get full user details
    user_id = current_user.get('id')
    user = user_repo.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get workspace details
    workspace = None
    if user.get('workspace_id'):
        workspace = workspace_repo.get_by_id(user['workspace_id'])
    
    # Get organization (venue) details
    venue = None
    if user.get('organization_id'):
        venue = org_repo.get_by_id(user['organization_id'])
    
    return {
        "success": True,
        "message": "User retrieved successfully",
        "data": {
            "user": {
                "id": user.get('id'),
                "email": user.get('email'),
                "first_name": user.get('first_name'),
                "last_name": user.get('last_name'),
                "phone": user.get('phone'),
                "role": current_user.get('role', {}).get('name', 'operator'),
                "venue_ids": [user.get('organization_id')] if user.get('organization_id') else [],
                "is_active": user.get('is_active', True),
                "created_at": user.get('created_at'),
                "updated_at": user.get('updated_at')
            },
            "workspace": workspace,
            "venue": venue
        }
    }

@router.get("/me/data", response_model=BaseResponse)
async def get_current_user_data(current_user: Dict[str, Any] = Depends(get_current_application_user)):
    """Get current application user data (alias for /me for compatibility)"""
    return await get_current_user(current_user)


@router.post("/change-password", response_model=BaseResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: Dict[str, Any] = Depends(get_current_application_user)
):
    """Change password for the currently authenticated application user"""
    user_repo = UserRepository("application_users")

    user_id = current_user.get('id')
    user = user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verify old password
    if not verify_password(request.old_password, user.get('password_hash', '')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Prevent reuse of the same password
    if verify_password(request.new_password, user.get('password_hash', '')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password"
        )

    # Update password
    new_hash = get_password_hash(request.new_password)
    success = user_repo.update(user_id, {"password_hash": new_hash})

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password"
        )

    return {
        "success": True,
        "message": "Password changed successfully"
    }