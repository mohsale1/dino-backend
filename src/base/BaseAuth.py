from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from src.config.Settings import settings
from src.core.Security import verify_password, get_password_hash
from src.base.BaseRepository import BaseRepository

class BaseAuth:
    """Base authentication service"""
    
    def __init__(self, user_repository: BaseRepository, role_repository: BaseRepository):
        self.user_repository = user_repository
        self.role_repository = role_repository
    
    def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with email and password"""
        user = self.user_repository.get_by_field("email", email)
        
        if not user:
            return None
        
        if not user.get('is_active', False):
            return None
        
        if not verify_password(password, user.get('password_hash', '')):
            return None
        
        return user
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    def create_refresh_token(self, data: dict) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            return payload
        except JWTError:
            return None
    
    def get_user_with_role(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user with role information (sanitized for response)"""
        user = self.user_repository.get_by_id(user_id)
        
        if not user:
            return None
        
        role = self.role_repository.get_by_id(user.get('role_id', ''))
        
        # Remove sensitive fields
        user.pop('password_hash', None)
        user.pop('is_deleted', None)
        user.pop('created_by', None)
        user.pop('is_system', None)
        
        # Clean role data
        if role:
            role_clean = {
                'id': role.get('id'),
                'name': role.get('name'),
                'role_type': role.get('role_type'),
                'permissions': role.get('permissions', [])
            }
            user['role'] = role_clean
            # Also add role name as string for frontend compatibility
            user['role_name'] = role.get('name')
        
        return user
    
    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        """Change user password"""
        # Get user
        user = self.user_repository.get_by_id(user_id)
        
        if not user:
            raise Exception("User not found")
        
        # Verify old password
        if not verify_password(old_password, user.get('password_hash', '')):
            raise Exception("Current password is incorrect")
        
        # Hash new password
        new_password_hash = get_password_hash(new_password)
        
        # Update password
        success = self.user_repository.update(user_id, {
            'password_hash': new_password_hash,
            'updated_at': datetime.now(timezone.utc)
        })
        
        return success
