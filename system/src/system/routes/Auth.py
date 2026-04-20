from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.schemas.Auth import LoginRequest, LoginResponse, RefreshTokenRequest, RefreshTokenResponse, ChangePasswordRequest
from src.system.services.Auth import SystemAuthService
from src.base.BaseSchema import BaseResponse
from src.core.Security import decode_token, verify_token_type
from src.config.Database import get_db
from src.system.middleware.RoleCheck import SystemPermissionCheck
from typing import Dict, Any

router = APIRouter(prefix='/auth', tags=['System Auth'])

@router.post('/login')
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    service = SystemAuthService(db)
    result = await service.login(request.email, request.password)
    if not result:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid email or password')
    return result

@router.post('/refresh', response_model=RefreshTokenResponse)
async def refresh_token(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    if not verify_token_type(request.refresh_token, 'refresh'):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid refresh token')
    payload = decode_token(request.refresh_token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid refresh token')
    service = SystemAuthService(db)
    token_data = {'sub': payload.get('sub'), 'email': payload.get('email'), 'user_type': 'system'}
    access_token = service.create_access_token(token_data)
    return {'access_token': access_token, 'token_type': 'bearer'}

@router.get('/me', response_model=BaseResponse)
async def get_current_user(user: Dict[str, Any] = Depends(SystemPermissionCheck.require_authenticated)):
    return {'success': True, 'message': 'User retrieved successfully', 'data': user}

@router.post('/change-password', response_model=BaseResponse)
async def change_password(
    request: ChangePasswordRequest,
    user: Dict[str, Any] = Depends(SystemPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db)
):
    service = SystemAuthService(db)
    try:
        success = await service.change_password(user['id'], request.old_password, request.new_password)
        if not success:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Failed to change password. Please check your current password.')
        return {'success': True, 'message': 'Password changed successfully', 'data': None}
    except Exception as e:
        error_message = str(e)
        if 'incorrect' in error_message.lower() or 'invalid' in error_message.lower():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Current password is incorrect')
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_message)
